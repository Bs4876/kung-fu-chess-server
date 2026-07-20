"""Scripted end-to-end regression test chaining together everything the
networking layer does, against one real running server: login -> matched
play -> disconnect -> forfeit -> ELO update -> matchmaking timeout -> rooms.
Extends the existing server/tests/integration/test_integration.py precedent
(several real modules wired together, nothing mocked) to the whole net/
subsystem. Each piece already has its own focused unit/integration
coverage elsewhere; this test's job is proving they all still compose
correctly end-to-end, not re-deriving every edge case again.

Matchmaking/disconnect timings are overridden to be fast (see serve()'s
overrides) so the matchmaking timeout and forfeit are both reachable
without waiting on the real ~1-minute/25-second config defaults - keeps
this test fast and non-flaky to run repeatedly.
"""

import asyncio

import pytest
import websockets

from model.position import Position
from net import protocol
from net.ws_server import serve
from persistence.db import connect as connect_db
from persistence.users_repository import UsersRepository


@pytest.fixture
async def running_server(tmp_path):
    db_path = tmp_path / "test.db"
    server = await serve(
        host="localhost", port=0, log_dir=tmp_path, db_path=db_path,
        matchmaking_tick_ms=20, matchmaking_wait_ms=150, disconnect_grace_ms=150,
    )
    port = server.sockets[0].getsockname()[1]
    yield port, db_path
    server.close()
    await server.wait_closed()


async def _login(ws, username: str) -> dict:
    await ws.send(protocol.encode(protocol.login(username)))
    response = protocol.decode(await ws.recv())
    assert response["success"] is True
    return response


async def test_full_networking_flow(running_server):
    port, db_path = running_server
    uri = f"ws://localhost:{port}"

    # --- 1. Login -------------------------------------------------------
    async with websockets.connect(uri) as white_ws, websockets.connect(uri) as black_ws:
        await _login(white_ws, "alice")
        await _login(black_ws, "bob")

        # --- 2. Matchmaking pairs them (both default ELO -> within range) --
        await white_ws.send(protocol.encode(protocol.play()))
        await black_ws.send(protocol.encode(protocol.play()))
        assert protocol.decode(await white_ws.recv())["type"] == protocol.MATCHMAKING_STATUS
        assert protocol.decode(await black_ws.recv())["type"] == protocol.MATCHMAKING_STATUS
        white_start = protocol.decode(await asyncio.wait_for(white_ws.recv(), timeout=3))
        black_start = protocol.decode(await asyncio.wait_for(black_ws.recv(), timeout=3))
        assert white_start["type"] == protocol.GAME_START
        game_id = white_start["game_id"]

        # --- 3. Play one real move (broadcast to both seated players) --------
        await white_ws.send(protocol.encode(protocol.request_move(game_id, Position(6, 0), Position(5, 0))))
        assert protocol.decode(await white_ws.recv())["type"] == protocol.MOVE_ACCEPTED
        assert protocol.decode(await black_ws.recv())["type"] == protocol.MOVE_ACCEPTED

        # --- 4. Disconnect + forfeit (no rejoin this time) -------------------
        await white_ws.close()
        disconnected = protocol.decode(await black_ws.recv())
        assert disconnected["type"] == protocol.OPPONENT_DISCONNECTED
        assert disconnected["forfeit_in_ms"] == 150

        forfeit = protocol.decode(await asyncio.wait_for(black_ws.recv(), timeout=3))
        assert forfeit["type"] == protocol.GAME_OVER
        assert forfeit["reason"] == "opponent_disconnected"
        assert forfeit["winner"] == black_start["color"]

    # --- 5. ELO updated for both real (non-bot) players ---------------------
    users = UsersRepository(connect_db(db_path))
    alice_elo = users.get_by_username("alice").elo
    bob_elo = users.get_by_username("bob").elo
    assert (alice_elo, bob_elo) != (1200, 1200)  # both moved away from the DEFAULT_ELO starting point
    winner_username = "bob" if black_start["color"] == forfeit["winner"] else "alice"
    assert (bob_elo if winner_username == "bob" else alice_elo) > 1200

    # --- 6. A lone player with no human opponent times out with an error ----
    async with websockets.connect(uri) as lone_ws:
        await _login(lone_ws, "carol")
        await lone_ws.send(protocol.encode(protocol.play()))
        assert protocol.decode(await lone_ws.recv())["type"] == protocol.MATCHMAKING_STATUS
        timeout_result = protocol.decode(await asyncio.wait_for(lone_ws.recv(), timeout=3))
        assert timeout_result["type"] == protocol.ERROR
        assert timeout_result["code"] == "no_opponent_found"

    # --- 7. Rooms: a second, manual way into a game --------------------------
    async with websockets.connect(uri) as creator_ws, websockets.connect(uri) as joiner_ws:
        await _login(creator_ws, "dave")
        await _login(joiner_ws, "erin")

        await creator_ws.send(protocol.encode(protocol.create_room("Dave's room")))
        created = protocol.decode(await creator_ws.recv())
        assert created["type"] == protocol.ROOM_CREATED

        await joiner_ws.send(protocol.encode(protocol.join_room(created["room_id"])))
        joiner_start = protocol.decode(await joiner_ws.recv())
        creator_start = protocol.decode(await asyncio.wait_for(creator_ws.recv(), timeout=3))
        assert joiner_start["type"] == creator_start["type"] == protocol.GAME_START
        assert joiner_start["game_id"] == creator_start["game_id"]

        # --- 8. A third connection watches the now-running room ------------
        async with websockets.connect(uri) as viewer_ws:
            await _login(viewer_ws, "frank")

            await viewer_ws.send(protocol.encode(protocol.list_rooms()))
            room_list = protocol.decode(await viewer_ws.recv())
            assert room_list["type"] == protocol.ROOM_LIST
            listed = next(r for r in room_list["rooms"] if r["id"] == created["room_id"])
            assert listed["status"] == "running"
            assert listed["occupants"] == 2

            await viewer_ws.send(protocol.encode(protocol.watch_room(created["room_id"])))
            watch_start = protocol.decode(await viewer_ws.recv())
            assert watch_start["type"] == protocol.GAME_START
            assert watch_start["color"] is None
            assert watch_start["game_id"] == creator_start["game_id"]

            # A move by a real player is broadcast to the viewer too.
            await creator_ws.send(protocol.encode(
                protocol.request_move(creator_start["game_id"], Position(6, 0), Position(5, 0))
            ))
            viewer_broadcast = protocol.decode(await asyncio.wait_for(viewer_ws.recv(), timeout=3))
            assert viewer_broadcast["type"] == protocol.MOVE_ACCEPTED

            # A viewer's own move request is rejected, not applied.
            await viewer_ws.send(protocol.encode(
                protocol.request_move(creator_start["game_id"], Position(1, 0), Position(2, 0))
            ))
            rejected = protocol.decode(await asyncio.wait_for(viewer_ws.recv(), timeout=3))
            assert rejected["type"] == protocol.ERROR
            assert rejected["code"] == "bad_message"
