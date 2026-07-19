"""Real end-to-end smoke tests over actual sockets - proving the asyncio
tick loop, protocol encoding, matchmaking, and GameRoom wiring all work
together. Most protocol/room/matchmaking behavior is covered without a
socket in tests/unit/ (with fast injectable timing); this file stays
deliberately small and uses the real (short-ish) config defaults.
"""

import asyncio

import pytest
import websockets

from model.position import Position
from net import protocol
from net.ws_server import serve


@pytest.fixture
async def running_server(tmp_path):
    server = await serve(host="localhost", port=0, log_dir=tmp_path, db_path=tmp_path / "test.db")
    port = server.sockets[0].getsockname()[1]
    yield port
    server.close()
    await server.wait_closed()


async def _register_and_login(ws, username: str) -> None:
    await ws.send(protocol.encode(protocol.register(username, "hunter2")))
    response = protocol.decode(await ws.recv())
    assert response["success"] is True


async def _play_and_match(white_ws, black_ws) -> tuple[dict, dict]:
    """Register+log in both sockets as alice/bob, send play on both, and
    return their (white_start, black_start) game_start messages once matched."""
    await _register_and_login(white_ws, "alice")
    await _register_and_login(black_ws, "bob")
    await white_ws.send(protocol.encode(protocol.play()))
    await black_ws.send(protocol.encode(protocol.play()))
    assert protocol.decode(await white_ws.recv())["type"] == protocol.MATCHMAKING_STATUS
    assert protocol.decode(await black_ws.recv())["type"] == protocol.MATCHMAKING_STATUS
    white_start = protocol.decode(await asyncio.wait_for(white_ws.recv(), timeout=3))
    black_start = protocol.decode(await asyncio.wait_for(black_ws.recv(), timeout=3))
    assert white_start["type"] == protocol.GAME_START
    return white_start, black_start


async def test_two_matched_players_play_a_full_move_over_real_sockets(running_server):
    uri = f"ws://localhost:{running_server}"

    async with websockets.connect(uri) as white_ws, websockets.connect(uri) as black_ws:
        white_start, black_start = await _play_and_match(white_ws, black_ws)
        assert {white_start["color"], black_start["color"]} == {"white", "black"}
        assert white_start["game_id"] == black_start["game_id"]

        await white_ws.send(protocol.encode(protocol.request_move(
            white_start["game_id"], Position(6, 0), Position(5, 0),
        )))

        accepted = protocol.decode(await white_ws.recv())
        assert accepted["type"] == protocol.MOVE_ACCEPTED

        arrived = protocol.decode(await asyncio.wait_for(white_ws.recv(), timeout=3))
        assert arrived["type"] == protocol.ARRIVED


async def test_register_then_login_over_a_real_socket(running_server):
    uri = f"ws://localhost:{running_server}"

    async with websockets.connect(uri) as ws:
        await ws.send(protocol.encode(protocol.register("alice", "hunter2")))
        register_response = protocol.decode(await ws.recv())
        assert register_response["success"] is True
        assert register_response["username"] == "alice"

        await ws.send(protocol.encode(protocol.login("alice", "wrong password")))
        failed_login = protocol.decode(await ws.recv())
        assert failed_login["success"] is False

        await ws.send(protocol.encode(protocol.login("alice", "hunter2")))
        ok_login = protocol.decode(await ws.recv())
        assert ok_login["success"] is True
        assert ok_login["elo"] == register_response["elo"]


async def test_play_before_logging_in_is_rejected(running_server):
    uri = f"ws://localhost:{running_server}"

    async with websockets.connect(uri) as ws:
        await ws.send(protocol.encode(protocol.play()))
        response = protocol.decode(await ws.recv())
        assert response["type"] == protocol.ERROR
        assert response["code"] == "not_authenticated"


async def test_disconnect_then_rejoin_resumes_the_same_game(running_server):
    uri = f"ws://localhost:{running_server}"

    white_ws = await websockets.connect(uri)
    black_ws = await websockets.connect(uri)
    try:
        white_start, _black_start = await _play_and_match(white_ws, black_ws)
        game_id = white_start["game_id"]

        await white_ws.close()
        disconnected_notice = protocol.decode(await black_ws.recv())
        assert disconnected_notice["type"] == protocol.OPPONENT_DISCONNECTED

        async with websockets.connect(uri) as reconnect_ws:
            await reconnect_ws.send(protocol.encode(protocol.login("alice", "hunter2")))
            login_response = protocol.decode(await reconnect_ws.recv())
            assert login_response["success"] is True

            await reconnect_ws.send(protocol.encode(protocol.rejoin_game(game_id)))
            rejoined = protocol.decode(await reconnect_ws.recv())
            assert rejoined["type"] == protocol.GAME_START
            assert rejoined["game_id"] == game_id
            assert rejoined["color"] == white_start["color"]
    finally:
        await black_ws.close()


async def test_rejoining_an_unknown_game_id_is_rejected(running_server):
    uri = f"ws://localhost:{running_server}"

    async with websockets.connect(uri) as ws:
        await _register_and_login(ws, "alice")
        await ws.send(protocol.encode(protocol.rejoin_game("no-such-game")))
        response = protocol.decode(await ws.recv())
        assert response["type"] == protocol.ERROR
        assert response["code"] == "cannot_rejoin"


async def test_create_then_join_a_room_over_real_sockets(running_server):
    uri = f"ws://localhost:{running_server}"

    async with websockets.connect(uri) as creator_ws, websockets.connect(uri) as joiner_ws:
        await _register_and_login(creator_ws, "alice")
        await _register_and_login(joiner_ws, "bob")

        # create_room blocks the creator's own connection until someone
        # joins (mirrors matchmaking's play()) - the rest of the server,
        # including joiner_ws's own messages, keeps running concurrently.
        await creator_ws.send(protocol.encode(protocol.create_room("Alice's room")))
        created = protocol.decode(await creator_ws.recv())
        assert created["type"] == protocol.ROOM_CREATED
        room_id = created["room_id"]

        await joiner_ws.send(protocol.encode(protocol.list_rooms()))
        listing = protocol.decode(await joiner_ws.recv())
        assert listing["type"] == protocol.ROOM_LIST
        assert any(r["id"] == room_id and r["name"] == "Alice's room" for r in listing["rooms"])

        await joiner_ws.send(protocol.encode(protocol.join_room(room_id)))
        joiner_start = protocol.decode(await joiner_ws.recv())
        creator_start = protocol.decode(await asyncio.wait_for(creator_ws.recv(), timeout=3))

        assert joiner_start["type"] == protocol.GAME_START
        assert creator_start["type"] == protocol.GAME_START
        assert joiner_start["game_id"] == creator_start["game_id"]
        assert {joiner_start["color"], creator_start["color"]} == {"white", "black"}


async def test_joining_an_unknown_room_id_is_rejected(running_server):
    uri = f"ws://localhost:{running_server}"

    async with websockets.connect(uri) as ws:
        await _register_and_login(ws, "alice")
        await ws.send(protocol.encode(protocol.join_room("no-such-room")))
        response = protocol.decode(await ws.recv())
        assert response["type"] == protocol.ERROR
        assert response["code"] == "cannot_join_room"
