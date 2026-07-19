"""One real end-to-end test of the ui-side networking stack against an
actual running server - proving WsClient's background-thread bridge and
NetworkGameFacade's message handling work together over a real socket
(test_network_game_facade.py covers the rest of NetworkGameFacade's
behavior against a fake transport, without needing a socket at all).
"""

import asyncio

import pytest

from model.position import Position
from net.ws_server import serve
from network.network_game_facade import connect


@pytest.fixture
async def running_server(tmp_path):
    server = await serve(host="localhost", port=0, log_dir=tmp_path)
    port = server.sockets[0].getsockname()[1]
    yield port
    server.close()
    await server.wait_closed()


async def test_two_network_game_facades_play_a_full_move_over_a_real_socket(running_server):
    uri = f"ws://localhost:{running_server}"

    # connect() blocks (waiting on the WS handshake, then on game_start,
    # which itself doesn't arrive until the server's AnonymousLobby pairs
    # this connection with a second one) - run both concurrently on worker
    # threads, or the first call would block forever waiting for a second
    # player who never gets the chance to connect.
    white, black = await asyncio.gather(
        asyncio.to_thread(connect, uri),
        asyncio.to_thread(connect, uri),
    )
    assert {white.color, black.color} == {"white", "black"}

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
