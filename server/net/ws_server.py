"""Single-process WebSocket server entrypoint.

Pairs connections two at a time through AnonymousLobby (see its own
docstring for why this is deliberately trivial, throwaway scaffolding) - no
login/matchmaking/rooms yet (those land in later stages, all reusing
GameRoom unchanged).
"""

import asyncio
from pathlib import Path

import websockets

from bus.event_bus import EventBus
from chess_io.board_parser import BoardParser
from config import GAME_LOG_DIR, WS_HOST, WS_PORT
from model.starting_position import STARTING_POSITION
from net import protocol
from net.anonymous_lobby import AnonymousLobby
from net.game_room import GameRoom
from persistence.event_log import EventLogWriter

_HANDLERS = {
    protocol.REQUEST_MOVE: GameRoom.handle_request_move,
    protocol.REQUEST_JUMP: GameRoom.handle_request_jump,
}


def _new_starting_board():
    return BoardParser().parse(STARTING_POSITION)


async def _dispatch(room: GameRoom, websocket, text: str) -> None:
    try:
        message = protocol.decode(text)
        handler = _HANDLERS[message["type"]]
    except (ValueError, KeyError) as exc:
        await websocket.send(protocol.encode(protocol.error("bad_message", str(exc))))
        return
    handler(room, message)


def make_handler(lobby: AnonymousLobby):
    """Build the per-connection coroutine websockets.serve calls for each client."""

    async def handler(websocket) -> None:
        room = await lobby.join(websocket)
        color = room.color_of(websocket)
        await websocket.send(protocol.encode(protocol.game_start(room.game_id, color, room.state_version, room.snapshot())))
        try:
            async for text in websocket:
                await _dispatch(room, websocket, text)
        finally:
            room.leave(websocket)

    return handler


async def serve(host: str = WS_HOST, port: int = WS_PORT, log_dir: Path = GAME_LOG_DIR):
    """Start listening on host:port, pairing connections two at a time.

    Returns the running Server (already accepting connections) - callers
    manage its lifetime themselves (`server.close()` + `await
    server.wait_closed()`). Returning it rather than blocking here is what
    lets tests bind an ephemeral port (port=0) and read back which one the
    OS actually picked via `server.sockets`. `log_dir` defaults to the real
    GAME_LOG_DIR but is overridable so tests can point it at a temp dir
    instead of writing into the repo.
    """
    bus = EventBus()
    bus.subscribe_all(EventLogWriter(log_dir))
    lobby = AnonymousLobby(bus, _new_starting_board)
    return await websockets.serve(make_handler(lobby), host, port)


async def _serve_forever(host: str = WS_HOST, port: int = WS_PORT) -> None:
    server = await serve(host, port)
    async with server:
        await asyncio.Future()  # run until cancelled/interrupted


if __name__ == "__main__":
    asyncio.run(_serve_forever())
