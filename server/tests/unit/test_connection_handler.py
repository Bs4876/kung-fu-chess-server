"""Unit coverage for ConnectionHandler (server/net/ws_server.py), against
fakes/real lightweight collaborators the same way test_game_room.py and
test_room_registry.py already test their own classes - this used to only be
reachable through a real socket (see server/tests/integration/
test_ws_integration.py, test_full_flow.py), which stay in place as the
end-to-end regression check that this refactor didn't change behavior.
"""

import asyncio
import contextlib
import json

from bus.event_bus import EventBus
from model.position import Position
from net import protocol
from net.room_registry import RoomRegistry
from net.ws_server import ConnectionHandler, GameRegistry
from persistence.db import connect as connect_db
from persistence.users_repository import UsersRepository


class FakeSocket:
    """Records what's sent to it, decoded back to a dict - same shape as
    test_game_room.py's own FakeSocket."""

    def __init__(self):
        self.sent = []

    async def send(self, text: str) -> None:
        self.sent.append(json.loads(text))


class FakeIterableSocket(FakeSocket):
    """Adds async iteration over a fixed list of already-encoded inbound
    messages, then stops - standing in for a real connection that closes
    right after sending them, for testing ConnectionHandler.run()'s loop."""

    def __init__(self, messages: list[str]):
        super().__init__()
        self._messages = iter(messages)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._messages)
        except StopIteration:
            raise StopAsyncIteration


class FakeUser:
    def __init__(self, username: str):
        self.username = username


class FakeMatchmaking:
    """Stands in for net.matchmaking.Matchmaking: play() returns whatever
    result a test preset, instead of actually running the timed pairing
    loop - ConnectionHandler only ever awaits play()'s result and calls
    cancel(), it doesn't care how the result was produced."""

    def __init__(self):
        self.cancelled: list = []
        self.result = None

    async def play(self, websocket, user):
        return self.result

    def cancel(self, websocket) -> None:
        self.cancelled.append(websocket)


def handler_for(tmp_path, matchmaking=None):
    users = UsersRepository(connect_db(tmp_path / "test.db"))
    bus = EventBus()
    games = GameRegistry(bus)
    rooms = RoomRegistry(games.new_room)
    socket = FakeSocket()
    handler = ConnectionHandler(socket, matchmaking or FakeMatchmaking(), rooms, games, users)
    return handler, socket


async def _logged_in_handler(tmp_path, matchmaking=None):
    handler, socket = handler_for(tmp_path, matchmaking)
    await handler.route(protocol.login("alice"))
    socket.sent.clear()
    return handler, socket


async def test_login_authenticates_the_session_and_returns_a_login_result(tmp_path):
    handler, socket = handler_for(tmp_path)
    await handler.route(protocol.login("alice"))
    assert socket.sent[-1]["type"] == protocol.LOGIN_RESULT
    assert socket.sent[-1]["success"] is True
    assert handler.session.is_authenticated


async def test_play_before_login_is_rejected(tmp_path):
    handler, socket = handler_for(tmp_path)
    await handler.route(protocol.play())
    assert socket.sent[-1]["type"] == protocol.ERROR
    assert socket.sent[-1]["code"] == "not_authenticated"


async def test_play_enters_the_room_matchmaking_returns(tmp_path):
    matchmaking = FakeMatchmaking()
    handler, socket = await _logged_in_handler(tmp_path, matchmaking)
    room = handler._games.new_room()
    room.join(socket, player=handler.session.user)
    matchmaking.result = room

    await handler.route(protocol.play())

    assert socket.sent[-1]["type"] == protocol.GAME_START
    assert socket.sent[-1]["color"] == "white"
    room.stop()


async def test_play_reports_no_opponent_found_when_matchmaking_gives_up(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)
    await handler.route(protocol.play())
    assert socket.sent[-1]["type"] == protocol.ERROR
    assert socket.sent[-1]["code"] == "no_opponent_found"


async def test_create_room_sends_room_created_then_starts_the_game_once_joined(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)

    create_task = asyncio.create_task(handler.route(protocol.create_room("My Room")))
    await asyncio.sleep(0)  # let create_room send room_created and start awaiting the 2nd player

    assert socket.sent[-1]["type"] == protocol.ROOM_CREATED
    room_id = socket.sent[-1]["room_id"]

    handler._rooms.join_room(room_id, FakeSocket(), FakeUser("bob"))
    await asyncio.wait_for(create_task, timeout=1)

    assert socket.sent[-1]["type"] == protocol.GAME_START
    assert socket.sent[-1]["color"] == "white"


async def test_join_room_seats_the_second_player(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)
    room_id = handler._rooms.create_room("Alice's room", FakeSocket(), FakeUser("creator"))

    await handler.route(protocol.join_room(room_id))

    assert socket.sent[-1]["type"] == protocol.GAME_START
    assert socket.sent[-1]["color"] == "black"


async def test_join_room_falls_back_to_watching_an_already_running_room(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)
    room_id = handler._rooms.create_room("Full room", FakeSocket(), FakeUser("creator"))
    handler._rooms.join_room(room_id, FakeSocket(), FakeUser("joiner"))  # now running/full

    await handler.route(protocol.join_room(room_id))

    assert socket.sent[-1]["type"] == protocol.GAME_START
    assert socket.sent[-1]["color"] is None  # viewer, not a seated player


async def test_join_room_with_an_unknown_id_is_rejected(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)
    await handler.route(protocol.join_room("no-such-room"))
    assert socket.sent[-1]["type"] == protocol.ERROR
    assert socket.sent[-1]["code"] == "cannot_join_room"


async def test_watch_room_seats_as_a_viewer(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)
    room_id = handler._rooms.create_room("Full room", FakeSocket(), FakeUser("creator"))
    handler._rooms.join_room(room_id, FakeSocket(), FakeUser("joiner"))

    await handler.route(protocol.watch_room(room_id))

    assert socket.sent[-1]["type"] == protocol.GAME_START
    assert socket.sent[-1]["color"] is None


async def test_cancel_room_removes_the_pending_room(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)
    create_task = asyncio.create_task(handler.route(protocol.create_room("My Room")))
    await asyncio.sleep(0)
    room_id = socket.sent[-1]["room_id"]

    await handler.route(protocol.cancel_room(room_id))

    assert handler._rooms.list_rooms() == []
    create_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await create_task


async def test_rejoin_reseats_a_previously_disconnected_player(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)
    room = handler._games.new_room()
    room.join(socket, player=handler.session.user)
    room.leave(socket)

    await handler.route(protocol.rejoin_game(room.game_id))

    assert socket.sent[-1]["type"] == protocol.GAME_START
    assert socket.sent[-1]["color"] == "white"
    room.stop()


async def test_rejoin_with_no_matching_game_is_rejected(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)
    await handler.route(protocol.rejoin_game("no-such-game"))
    assert socket.sent[-1]["type"] == protocol.ERROR
    assert socket.sent[-1]["code"] == "cannot_rejoin"


async def test_room_scoped_message_is_routed_to_the_seated_room(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)
    room = handler._games.new_room()
    room.join(socket, player=handler.session.user)
    handler._room = room

    await handler.route(protocol.request_move(room.game_id, Position(0, 0), Position(0, 1)))
    await asyncio.sleep(0)  # let GameRoom's fire-and-forget broadcast run

    assert socket.sent[-1]["type"] in (protocol.MOVE_ACCEPTED, protocol.MOVE_REJECTED)
    room.stop()


async def test_unknown_message_type_gets_a_bad_message_error(tmp_path):
    handler, socket = handler_for(tmp_path)
    await handler.route({"type": "not_a_real_message"})
    assert socket.sent[-1]["type"] == protocol.ERROR
    assert socket.sent[-1]["code"] == "bad_message"


async def test_dispatch_sends_an_error_for_malformed_json(tmp_path):
    handler, socket = handler_for(tmp_path)
    await handler.dispatch("not valid json")
    assert socket.sent[-1]["type"] == protocol.ERROR
    assert socket.sent[-1]["code"] == "bad_message"


async def test_dispatch_recovers_from_a_well_typed_but_incomplete_message(tmp_path):
    handler, socket = await _logged_in_handler(tmp_path)
    room = handler._games.new_room()
    room.join(socket, player=handler.session.user)
    handler._room = room

    # request_move with no "destination" - well-formed envelope, missing field.
    await handler.dispatch(protocol.encode({"type": protocol.REQUEST_MOVE, "source": {"row": 0, "col": 0}}))

    assert socket.sent[-1]["type"] == protocol.ERROR
    assert socket.sent[-1]["code"] == "bad_message"
    room.stop()


async def test_run_cleans_up_matchmaking_room_and_viewer_state_on_disconnect(tmp_path):
    matchmaking = FakeMatchmaking()
    socket = FakeIterableSocket([protocol.encode(protocol.login("alice"))])
    users = UsersRepository(connect_db(tmp_path / "test.db"))
    bus = EventBus()
    games = GameRegistry(bus)
    rooms = RoomRegistry(games.new_room)
    handler = ConnectionHandler(socket, matchmaking, rooms, games, users)

    room = games.new_room()
    room.join(socket, player=object())
    handler._room = room
    viewing_room = games.new_room()
    viewing_room.add_viewer(socket)
    handler._viewing_room = viewing_room

    await handler.run()

    assert socket in matchmaking.cancelled
    assert room.color_of(socket) is None  # leave() freed the seat
    assert socket not in viewing_room._viewers  # leave_viewer() removed it
    room.stop()
    viewing_room.stop()
