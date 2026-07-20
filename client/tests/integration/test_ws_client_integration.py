"""One real end-to-end test of the ui-side networking stack against an
actual running server - proving WsClient's background-thread bridge and
NetworkGameFacade's message handling work together over a real socket,
through the full login -> play -> matched flow (test_network_game_facade.py
covers the rest of NetworkGameFacade's behavior against a fake transport,
without needing a socket at all).
"""

import asyncio

import pytest

from model.position import Position
from net import protocol
from net.ws_server import serve
from network.network_game_facade import NetworkGameFacade, wait_for_game_start
from network.ws_client import WsClient


@pytest.fixture
async def running_server(tmp_path):
    server = await serve(host="localhost", port=0, log_dir=tmp_path, db_path=tmp_path / "test.db")
    port = server.sockets[0].getsockname()[1]
    yield port
    server.close()
    await server.wait_closed()


def _register_login_and_play(uri: str, username: str) -> NetworkGameFacade:
    """Blocking: connect, log in (creating the account on first login - see
    net/auth.py), send play, and wait for game_start (skipping any
    matchmaking_status preamble) - everything NetworkGameFacade needs before
    it can be constructed."""
    client = WsClient(uri)
    client.send(protocol.login(username))
    login_result = client.recv_one_blocking()
    assert login_result["success"] is True
    client.send(protocol.play())
    start = wait_for_game_start(client)
    return NetworkGameFacade(client, start)


async def test_two_network_game_facades_play_a_full_move_over_a_real_socket(running_server):
    uri = f"ws://localhost:{running_server}"

    # Both of these block (WS handshake, login round trip, then game_start) -
    # run them concurrently on worker threads, or the first call would sit
    # in matchmaking forever waiting for a second player who never gets the
    # chance to connect.
    white, black = await asyncio.gather(
        asyncio.to_thread(_register_login_and_play, uri, "alice"),
        asyncio.to_thread(_register_login_and_play, uri, "bob"),
    )
    assert {white.color, black.color} == {"white", "black"}
    assert white.game_id == black.game_id

    white.request_move(Position(6, 0), Position(5, 0))
    await asyncio.sleep(0.3)  # let the request/move_accepted round trip land
    white.tick(0)
    black.tick(0)
    # move_accepted only starts prediction - the board itself only updates on arrival.
    assert Position(6, 0) in white.pending_motions()
    assert Position(6, 0) in black.pending_motions()
    assert white.snapshot().get_piece(Position(6, 0)) == "wP"

    await asyncio.sleep(1.2)  # MOVE_TRAVEL_TIME_PER_CELL(1000ms) for 1 cell, plus margin
    white.tick(0)
    black.tick(0)
    assert white.snapshot().get_piece(Position(6, 0)) == "."
    assert white.snapshot().get_piece(Position(5, 0)) == "wP"
    assert black.snapshot().get_piece(Position(6, 0)) == "."
    assert black.snapshot().get_piece(Position(5, 0)) == "wP"


async def test_on_event_hook_fires_for_connect_send_recv_and_close(running_server):
    uri = f"ws://localhost:{running_server}"
    events: list[tuple[str, dict]] = []

    # WsClient.__init__ blocks its calling thread until connected - run it
    # (and the rest of the exchange) on a worker thread, the same way
    # _register_login_and_play above does, or it would deadlock the
    # pytest-asyncio loop this test and running_server's own server share.
    def _connect_send_and_close() -> None:
        client = WsClient(uri, on_event=lambda kind, payload: events.append((kind, payload)))
        client.send(protocol.login("frank"))
        client.recv_one_blocking()
        client.close()

    await asyncio.to_thread(_connect_send_and_close)
    await asyncio.sleep(0.1)  # let the background thread's close() event land

    kinds = [kind for kind, _payload in events]
    assert kinds[0] == "connect"
    assert "send" in kinds
    assert "recv" in kinds
    assert kinds[-1] == "close"
