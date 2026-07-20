"""Single-process WebSocket server entrypoint.

Login gates matchmaking: a connection must send login/register before play
is accepted. Matchmaking (net/matchmaking.py) pairs authenticated sessions
within MATCH_ELO_RANGE, giving up with an error after MATCHMAKING_WAIT_MS if
no human match is found - superseding the earlier anonymous-lobby pairing
now that there's login/ELO to actually match on.
"""

import asyncio
from pathlib import Path

import websockets

from bus.event_bus import EventBus
from chess_io.board_parser import BoardParser
from config import (
    DB_PATH, DISCONNECT_GRACE_MS, GAME_LOG_DIR, MATCHMAKING_TICK_MS, MATCHMAKING_WAIT_MS, WS_HOST, WS_PORT,
)
from model.starting_position import STARTING_POSITION
from net import auth, protocol
from net.game_room import GameRoom
from net.matchmaking import Matchmaking
from net.room_registry import RoomRegistry
from net.session import Session
from persistence.db import connect as connect_db
from persistence.elo_updater import EloUpdater
from persistence.event_log import EventLogWriter
from persistence.users_repository import UsersRepository

_ROOM_HANDLERS = {
    protocol.REQUEST_MOVE: GameRoom.handle_request_move,
    protocol.REQUEST_JUMP: GameRoom.handle_request_jump,
}


class GameRegistry:
    """Tracks every currently-active GameRoom by game_id, so a dropped
    connection's rejoin_game request can find its way back to the right
    room. Also the single place new rooms get their game_id from."""

    def __init__(self, bus: EventBus, disconnect_grace_ms: int = DISCONNECT_GRACE_MS):
        self._bus = bus
        self._disconnect_grace_ms = disconnect_grace_ms
        self._rooms: dict[str, GameRoom] = {}
        self._next_id = 1

    def new_room(self) -> GameRoom:
        room = GameRoom(
            str(self._next_id), BoardParser().parse(STARTING_POSITION), self._bus,
            disconnect_grace_ms=self._disconnect_grace_ms,
        )
        self._next_id += 1
        room.start()
        self._rooms[room.game_id] = room
        return room

    def get(self, game_id: str) -> GameRoom | None:
        return self._rooms.get(game_id)


class ConnectionHandler:
    """Owns one connection's whole lifecycle: login/session state, routing
    each inbound message to the right matchmaking/rooms/room-scoped action,
    and cleanup on disconnect. One instance per websocket, built fresh by
    make_handler() below.

    Unlike GameRoom/Matchmaking/RoomRegistry, this used to be a nested
    closure with no way to unit-test routing/rejoin/room logic without a
    real socket (see server/tests/integration/test_ws_integration.py and
    test_full_flow.py) - pulling it out into a class with the same methods
    (self. in place of closure captures/nonlocal) makes it directly
    testable with fakes the same way those other classes already are, with
    no change in behavior."""

    def __init__(self, websocket, matchmaking: Matchmaking, rooms: RoomRegistry, games: GameRegistry,
                 users: UsersRepository):
        self._websocket = websocket
        self._matchmaking = matchmaking
        self._rooms = rooms
        self._games = games
        self._users = users
        self.session = Session()
        self._room: GameRoom | None = None
        self._viewing_room: GameRoom | None = None  # kept separate from
        # _room so a viewer's request_move/request_jump never reaches
        # _ROOM_HANDLERS below

    async def send(self, message: dict) -> None:
        await self._websocket.send(protocol.encode(message))

    async def require_authenticated(self) -> bool:
        if self.session.is_authenticated:
            return True
        await self.send(protocol.error("not_authenticated", "log in first"))
        return False

    async def enter_room(self, game_room: GameRoom) -> None:
        self._room = game_room
        color = game_room.color_of(self._websocket)
        await self.send(protocol.game_start(game_room.game_id, color, game_room.state_version, game_room.snapshot()))

    async def start_matchmaking(self) -> None:
        if not await self.require_authenticated():
            return
        await self.send(protocol.matchmaking_status("searching"))
        game_room = await self._matchmaking.play(self._websocket, self.session.user)
        if game_room is None:
            await self.send(protocol.error("no_opponent_found", "no opponent found within the time limit"))
            return
        await self.enter_room(game_room)

    async def rejoin(self, message: dict) -> None:
        target = self._games.get(message.get("game_id"))
        color = target.color_of_player(self.session.user) if target is not None else None
        if target is None or color is None or target.ended:
            await self.send(protocol.error("cannot_rejoin", "no active game to rejoin"))
            return
        target.rejoin(self._websocket, color)
        await self.enter_room(target)

    async def create_room(self, message: dict) -> None:
        if not await self.require_authenticated():
            return
        room_id = self._rooms.create_room(message["name"], self._websocket, self.session.user)
        await self.send(protocol.room_created(room_id))
        await self.enter_room(await self._rooms.await_join(room_id))

    async def _watch(self, game_room: GameRoom) -> None:
        game_room.add_viewer(self._websocket)
        self._viewing_room = game_room
        # color=None marks this as a viewer's catch-up snapshot rather than
        # a seated player's game_start.
        await self.send(protocol.game_start(game_room.game_id, None, game_room.state_version, game_room.snapshot()))

    async def join_room(self, message: dict) -> None:
        if not await self.require_authenticated():
            return
        room_id = message["room_id"]
        game_room = self._rooms.join_room(room_id, self._websocket, self.session.user)
        if game_room is not None:
            await self.enter_room(game_room)
            return
        # Not joinable as the 2nd player (already running, or never
        # existed) - the same Join action falls back to seating as a
        # viewer if the room is in fact already running, so one button
        # covers both cases (matches the course spec's single Join
        # action - see net/room_registry.py's own docstring).
        game_room = self._rooms.watch_room(room_id)
        if game_room is None:
            await self.send(protocol.error("cannot_join_room", "room not found"))
            return
        await self._watch(game_room)

    async def watch_room(self, message: dict) -> None:
        if not await self.require_authenticated():
            return
        game_room = self._rooms.watch_room(message["room_id"])
        if game_room is None:
            await self.send(protocol.error("cannot_watch_room", "room not found or not yet running"))
            return
        await self._watch(game_room)

    async def route(self, message: dict) -> None:
        message_type = message["type"]
        if message_type == protocol.LOGIN:
            await self.send(auth.handle_login(message, self.session, self._users))
        elif message_type == protocol.PLAY:
            await self.start_matchmaking()
        elif message_type == protocol.CANCEL_MATCHMAKING:
            self._matchmaking.cancel(self._websocket)
        elif message_type == protocol.REJOIN_GAME:
            await self.rejoin(message)
        elif message_type == protocol.LIST_ROOMS:
            await self.send(protocol.room_list(self._rooms.list_rooms()))
        elif message_type == protocol.CREATE_ROOM:
            await self.create_room(message)
        elif message_type == protocol.JOIN_ROOM:
            await self.join_room(message)
        elif message_type == protocol.CANCEL_ROOM:
            self._rooms.cancel_room(message["room_id"], self._websocket)
        elif message_type == protocol.WATCH_ROOM:
            await self.watch_room(message)
        elif self._room is not None and message_type in _ROOM_HANDLERS:
            _ROOM_HANDLERS[message_type](self._room, message)
        else:
            await self.send(protocol.error("bad_message", f"unexpected message: {message_type}"))

    async def dispatch(self, text: str) -> None:
        try:
            message = protocol.decode(text)
        except ValueError as exc:
            await self.send(protocol.error("bad_message", str(exc)))
            return

        try:
            await self.route(message)
        except Exception as exc:
            # A well-formed-but-malformed message (e.g. request_move
            # missing "source") or any other bug in a single handler must
            # not take this connection down - let alone the room's other,
            # perfectly well-behaved player. asyncio.CancelledError is a
            # BaseException, not Exception, so real task cancellation
            # (server shutdown, etc.) still propagates.
            try:
                await self.send(protocol.error("bad_message", f"could not process {message['type']}: {exc}"))
            except Exception:
                pass  # the connection itself may already be the thing that's gone

    async def run(self) -> None:
        try:
            async for text in self._websocket:
                await self.dispatch(text)
        finally:
            self._matchmaking.cancel(self._websocket)
            if self._room is not None:
                self._room.leave(self._websocket)
            if self._viewing_room is not None:
                self._viewing_room.leave_viewer(self._websocket)


def make_handler(matchmaking: Matchmaking, rooms: RoomRegistry, games: GameRegistry, users: UsersRepository):
    """Build the per-connection coroutine websockets.serve calls for each client."""

    async def handler(websocket) -> None:
        await ConnectionHandler(websocket, matchmaking, rooms, games, users).run()

    return handler


async def serve(
    host: str = WS_HOST, port: int = WS_PORT, log_dir: Path = GAME_LOG_DIR, db_path: Path = DB_PATH,
    matchmaking_tick_ms: int = MATCHMAKING_TICK_MS, matchmaking_wait_ms: int = MATCHMAKING_WAIT_MS,
    disconnect_grace_ms: int = DISCONNECT_GRACE_MS,
):
    """Start listening on host:port. Returns the running Server (already
    accepting connections) - callers manage its lifetime themselves
    (`server.close()` + `await server.wait_closed()`). Returning it rather
    than blocking here is what lets tests bind an ephemeral port (port=0)
    and read back which one the OS actually picked via `server.sockets`.
    `log_dir`/`db_path` default to the real GAME_LOG_DIR/DB_PATH, and the
    matchmaking/disconnect timings to their real config defaults, but all
    are overridable so tests can point at a temp dir and run matchmaking's
    timeout/forfeit timing fast instead of waiting on real wall-clock
    seconds (see server/tests/integration/test_full_flow.py).
    """
    bus = EventBus()
    users = UsersRepository(connect_db(db_path))
    bus.subscribe_all(EventLogWriter(log_dir))
    bus.subscribe_all(EloUpdater(users))

    games = GameRegistry(bus, disconnect_grace_ms=disconnect_grace_ms)
    matchmaking = Matchmaking(games.new_room, tick_ms=matchmaking_tick_ms, wait_ms=matchmaking_wait_ms)
    matchmaking.start()
    rooms = RoomRegistry(games.new_room)

    return await websockets.serve(make_handler(matchmaking, rooms, games, users), host, port)


async def _serve_forever(host: str = WS_HOST, port: int = WS_PORT) -> None:
    server = await serve(host, port)
    print(f"Server listening on {host}:{port}")
    async with server:
        await asyncio.Future()  # run until cancelled/interrupted


if __name__ == "__main__":
    asyncio.run(_serve_forever())
