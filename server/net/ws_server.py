"""Single-process WebSocket server entrypoint.

Login gates matchmaking: a connection must send login/register before play
is accepted. Matchmaking (net/matchmaking.py) pairs authenticated sessions
within MATCH_ELO_RANGE, falling back to a bot after MATCHMAKING_WAIT_MS -
superseding the earlier anonymous-lobby pairing now that there's login/ELO
to actually match on.
"""

import asyncio
from pathlib import Path

import websockets

from bus.event_bus import EventBus
from chess_io.board_parser import BoardParser
from config import DB_PATH, GAME_LOG_DIR, WS_HOST, WS_PORT
from model.starting_position import STARTING_POSITION
from net import auth, protocol
from net.bot_player import BotPlayer
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

    def __init__(self, bus: EventBus):
        self._bus = bus
        self._rooms: dict[str, GameRoom] = {}
        self._next_id = 1

    def new_room(self) -> GameRoom:
        room = GameRoom(str(self._next_id), BoardParser().parse(STARTING_POSITION), self._bus)
        self._next_id += 1
        room.start()
        self._rooms[room.game_id] = room
        return room

    def get(self, game_id: str) -> GameRoom | None:
        return self._rooms.get(game_id)


def start_bot(room: GameRoom, color: str) -> None:
    room.attach_bot(color, BotPlayer(room, color))


def make_handler(matchmaking: Matchmaking, rooms: RoomRegistry, games: GameRegistry, users: UsersRepository):
    """Build the per-connection coroutine websockets.serve calls for each client."""

    async def handler(websocket) -> None:
        session = Session()
        room: GameRoom | None = None

        async def send(message: dict) -> None:
            await websocket.send(protocol.encode(message))

        async def require_authenticated() -> bool:
            if session.is_authenticated:
                return True
            await send(protocol.error("not_authenticated", "log in first"))
            return False

        async def enter_room(game_room: GameRoom) -> None:
            nonlocal room
            room = game_room
            color = room.color_of(websocket)
            await send(protocol.game_start(room.game_id, color, room.state_version, room.snapshot()))

        async def start_matchmaking() -> None:
            if not await require_authenticated():
                return
            await send(protocol.matchmaking_status("searching"))
            await enter_room(await matchmaking.play(websocket, session.user))

        async def rejoin(message: dict) -> None:
            target = games.get(message.get("game_id"))
            color = target.color_of_player(session.user) if target is not None else None
            if target is None or color is None or target.ended:
                await send(protocol.error("cannot_rejoin", "no active game to rejoin"))
                return
            target.rejoin(websocket, color)
            await enter_room(target)

        async def create_room(message: dict) -> None:
            if not await require_authenticated():
                return
            room_id = rooms.create_room(message["name"], websocket, session.user)
            await send(protocol.room_created(room_id))
            await enter_room(await rooms.await_join(room_id))

        async def join_room(message: dict) -> None:
            if not await require_authenticated():
                return
            game_room = rooms.join_room(message["room_id"], websocket, session.user)
            if game_room is None:
                await send(protocol.error("cannot_join_room", "room not found or already full"))
                return
            await enter_room(game_room)

        async def dispatch(text: str) -> None:
            try:
                message = protocol.decode(text)
            except ValueError as exc:
                await send(protocol.error("bad_message", str(exc)))
                return

            message_type = message["type"]
            if message_type == protocol.LOGIN:
                await send(auth.handle_login(message, session, users))
            elif message_type == protocol.REGISTER:
                await send(auth.handle_register(message, session, users))
            elif message_type == protocol.PLAY:
                await start_matchmaking()
            elif message_type == protocol.CANCEL_MATCHMAKING:
                matchmaking.cancel(websocket)
            elif message_type == protocol.REJOIN_GAME:
                await rejoin(message)
            elif message_type == protocol.LIST_ROOMS:
                await send(protocol.room_list(rooms.list_rooms()))
            elif message_type == protocol.CREATE_ROOM:
                await create_room(message)
            elif message_type == protocol.JOIN_ROOM:
                await join_room(message)
            elif message_type == protocol.CANCEL_ROOM:
                rooms.cancel_room(message["room_id"], websocket)
            elif room is not None and message_type in _ROOM_HANDLERS:
                _ROOM_HANDLERS[message_type](room, message)
            else:
                await send(protocol.error("bad_message", f"unexpected message: {message_type}"))

        try:
            async for text in websocket:
                await dispatch(text)
        finally:
            matchmaking.cancel(websocket)
            if room is not None:
                room.leave(websocket)

    return handler


async def serve(
    host: str = WS_HOST, port: int = WS_PORT, log_dir: Path = GAME_LOG_DIR, db_path: Path = DB_PATH,
):
    """Start listening on host:port. Returns the running Server (already
    accepting connections) - callers manage its lifetime themselves
    (`server.close()` + `await server.wait_closed()`). Returning it rather
    than blocking here is what lets tests bind an ephemeral port (port=0)
    and read back which one the OS actually picked via `server.sockets`.
    `log_dir`/`db_path` default to the real GAME_LOG_DIR/DB_PATH but are
    overridable so tests can point them at a temp dir instead of writing
    into the repo.
    """
    bus = EventBus()
    users = UsersRepository(connect_db(db_path))
    bus.subscribe_all(EventLogWriter(log_dir))
    bus.subscribe_all(EloUpdater(users))

    games = GameRegistry(bus)
    matchmaking = Matchmaking(games.new_room, start_bot)
    matchmaking.start()
    rooms = RoomRegistry(games.new_room)

    return await websockets.serve(make_handler(matchmaking, rooms, games, users), host, port)


async def _serve_forever(host: str = WS_HOST, port: int = WS_PORT) -> None:
    server = await serve(host, port)
    async with server:
        await asyncio.Future()  # run until cancelled/interrupted


if __name__ == "__main__":
    asyncio.run(_serve_forever())
