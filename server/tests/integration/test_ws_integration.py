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


async def _login(ws, username: str) -> None:
    await ws.send(protocol.encode(protocol.login(username)))
    response = protocol.decode(await ws.recv())
    assert response["success"] is True


async def _play_and_match(white_ws, black_ws) -> tuple[dict, dict]:
    """Register+log in both sockets as alice/bob, send play on both, and
    return their (white_start, black_start) game_start messages once matched."""
    await _login(white_ws, "alice")
    await _login(black_ws, "bob")
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


async def test_malformed_move_gets_an_error_and_does_not_crash_the_connection_or_the_room(running_server):
    uri = f"ws://localhost:{running_server}"

    async with websockets.connect(uri) as white_ws, websockets.connect(uri) as black_ws:
        white_start, _black_start = await _play_and_match(white_ws, black_ws)

        # A well-formed envelope with a known type but missing the fields
        # its handler needs (request_move with no "destination") must not
        # take the connection down.
        await white_ws.send(protocol.encode({"type": protocol.REQUEST_MOVE, "source": {"row": 6, "col": 0}}))
        error_response = protocol.decode(await white_ws.recv())
        assert error_response["type"] == protocol.ERROR
        assert error_response["code"] == "bad_message"

        # The same (still-open) connection, and the room it's in, both keep
        # working normally afterward - the bad message didn't crash anything.
        await white_ws.send(protocol.encode(protocol.request_move(
            white_start["game_id"], Position(6, 0), Position(5, 0),
        )))
        accepted = protocol.decode(await white_ws.recv())
        assert accepted["type"] == protocol.MOVE_ACCEPTED


async def test_logging_in_twice_reuses_the_same_account_over_a_real_socket(running_server):
    uri = f"ws://localhost:{running_server}"

    async with websockets.connect(uri) as first_ws, websockets.connect(uri) as second_ws:
        await first_ws.send(protocol.encode(protocol.login("alice")))
        first_login = protocol.decode(await first_ws.recv())
        assert first_login["success"] is True
        assert first_login["username"] == "alice"

        # A second connection logging in with the same username - no
        # password, per the "just for presentation" spec - reuses the same
        # account (created by the first login) rather than erroring or
        # creating a duplicate.
        await second_ws.send(protocol.encode(protocol.login("alice")))
        second_login = protocol.decode(await second_ws.recv())
        assert second_login["success"] is True
        assert second_login["elo"] == first_login["elo"]


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
            await reconnect_ws.send(protocol.encode(protocol.login("alice")))
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
        await _login(ws, "alice")
        await ws.send(protocol.encode(protocol.rejoin_game("no-such-game")))
        response = protocol.decode(await ws.recv())
        assert response["type"] == protocol.ERROR
        assert response["code"] == "cannot_rejoin"


async def test_create_then_join_a_room_over_real_sockets(running_server):
    uri = f"ws://localhost:{running_server}"

    async with websockets.connect(uri) as creator_ws, websockets.connect(uri) as joiner_ws:
        await _login(creator_ws, "alice")
        await _login(joiner_ws, "bob")

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
        await _login(ws, "alice")
        await ws.send(protocol.encode(protocol.join_room("no-such-room")))
        response = protocol.decode(await ws.recv())
        assert response["type"] == protocol.ERROR
        assert response["code"] == "cannot_join_room"
