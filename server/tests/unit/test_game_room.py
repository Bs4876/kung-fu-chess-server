import asyncio
import json

from bus.event_bus import EventBus
from model.board import Board
from net import protocol
from net.game_room import GameEnded, GameRoom


def board_from(rows):
    return Board([row.split() for row in rows])


class FakeSocket:
    """A minimal stand-in for a websockets connection: just records what
    GameRoom broadcasts to it, decoded back to a dict for easy assertions."""

    def __init__(self):
        self.sent = []

    async def send(self, text: str) -> None:
        self.sent.append(json.loads(text))


async def _flush():
    """Let GameRoom's fire-and-forget socket.send tasks actually run."""
    await asyncio.sleep(0)


class FakeUser:
    """Stands in for persistence.users_repository.User - just enough
    (.username) for GameRoom.color_of_player's username-based lookup."""

    def __init__(self, username: str):
        self.username = username


async def test_join_assigns_white_then_black_then_rejects_a_third():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    assert room.join(FakeSocket()) == "white"
    assert room.join(FakeSocket()) == "black"
    assert room.join(FakeSocket()) is None


async def test_color_of_reports_each_sockets_assigned_color():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    white, black = FakeSocket(), FakeSocket()
    room.join(white)
    room.join(black)
    assert room.color_of(white) == "white"
    assert room.color_of(black) == "black"


def test_color_of_returns_none_for_an_unseated_socket():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    assert room.color_of(FakeSocket()) is None


async def test_leave_frees_the_slot_for_reuse():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    socket = FakeSocket()
    room.join(socket)
    room.leave(socket)
    assert room.join(FakeSocket()) == "white"


async def test_viewer_receives_broadcasts_alongside_seated_players():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    white, black, viewer = FakeSocket(), FakeSocket(), FakeSocket()
    room.join(white)
    room.join(black)
    room.add_viewer(viewer)

    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 0, "col": 2}})
    await _flush()

    assert viewer.sent[-1]["type"] == protocol.MOVE_ACCEPTED


async def test_leave_viewer_stops_further_broadcasts_to_it():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    socket, viewer = FakeSocket(), FakeSocket()
    room.join(socket)
    room.add_viewer(viewer)
    room.leave_viewer(viewer)

    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 0, "col": 2}})
    await _flush()

    assert viewer.sent == []


def test_leave_viewer_on_a_socket_that_was_never_a_viewer_does_nothing():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    room.leave_viewer(FakeSocket())  # must not raise


async def test_accepted_move_broadcasts_move_accepted_to_every_seated_player():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    white, black = FakeSocket(), FakeSocket()
    room.join(white)
    room.join(black)

    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 0, "col": 2}})
    await _flush()

    for socket in (white, black):
        assert socket.sent[-1]["type"] == protocol.MOVE_ACCEPTED


async def test_illegal_move_broadcasts_move_rejected():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    socket = FakeSocket()
    room.join(socket)

    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 1, "col": 1}})
    await _flush()

    assert socket.sent[-1]["type"] == protocol.MOVE_REJECTED
    assert socket.sent[-1]["reason"] == "illegal_piece_move"


async def test_jump_broadcasts_jump_started_to_every_seated_player():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    white, black = FakeSocket(), FakeSocket()
    room.join(white)
    room.join(black)

    room.handle_request_jump({"source": {"row": 0, "col": 0}, "destination": {"row": 2, "col": 2}})
    await _flush()

    for socket in (white, black):
        assert socket.sent[-1]["type"] == protocol.JUMP_STARTED


async def test_arrival_increments_state_version_and_broadcasts_the_outcome():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    socket = FakeSocket()
    room.join(socket)
    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 0, "col": 2}})
    await _flush()

    room._engine.wait(2000)
    await _flush()

    arrivals = [m for m in socket.sent if m["type"] == protocol.ARRIVED]
    assert len(arrivals) == 1
    assert room.state_version == 1
    assert arrivals[0]["state_version"] == 1


async def test_king_capture_broadcasts_game_over_with_the_correct_winner():
    room = GameRoom("1", board_from(["wR . bK", ". . .", ". . ."]), EventBus())
    socket = FakeSocket()
    room.join(socket)
    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 0, "col": 2}})
    await _flush()

    room._engine.wait(2000)
    await _flush()

    game_over_messages = [m for m in socket.sent if m["type"] == protocol.GAME_OVER]
    assert len(game_over_messages) == 1
    assert game_over_messages[0]["winner"] == "white"


async def test_outcomes_are_published_onto_the_bus_under_the_game_topic():
    bus = EventBus()
    received = []
    bus.subscribe("game.1", received.append)
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), bus)

    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 0, "col": 2}})
    room._engine.wait(2000)

    assert len(received) == 1


async def test_join_carries_an_opaque_player_identity_through_to_color_of():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    alice = object()
    room.join(FakeSocket(), player=alice)
    assert room._players["white"] is alice


async def test_join_defaults_player_to_none_for_anonymous_sockets():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    room.join(FakeSocket())
    assert room._players["white"] is None


async def test_game_ended_is_published_onto_the_bus_with_both_players_and_the_winner():
    bus = EventBus()
    received = []
    bus.subscribe("game.1", received.append)
    room = GameRoom("1", board_from(["wR . bK", ". . .", ". . ."]), bus)
    alice, bob = object(), object()
    room.join(FakeSocket(), player=alice)
    room.join(FakeSocket(), player=bob)

    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 0, "col": 2}})
    room._engine.wait(2000)

    game_ended = [e for e in received if isinstance(e, GameEnded)]
    assert game_ended == [GameEnded(game_id="1", white_player=alice, black_player=bob, winner="white")]


async def test_color_of_player_finds_a_seated_players_color():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    alice, bob = FakeUser("alice"), FakeUser("bob")
    room.join(FakeSocket(), player=alice)
    room.join(FakeSocket(), player=bob)
    assert room.color_of_player(alice) == "white"
    assert room.color_of_player(bob) == "black"


async def test_color_of_player_matches_by_username_not_object_identity():
    """A reconnecting session's User comes from a fresh DB query (a
    different Python object) - color_of_player must still recognize it as
    the same player it originally seated."""
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    room.join(FakeSocket(), player=FakeUser("alice"))
    assert room.color_of_player(FakeUser("alice")) == "white"


def test_color_of_player_returns_none_for_an_unseated_player():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    assert room.color_of_player(FakeUser("nobody")) is None


def test_color_of_player_returns_none_for_none():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus())
    assert room.color_of_player(None) is None


async def test_leave_mid_game_broadcasts_opponent_disconnected_to_the_remaining_player():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus(), disconnect_grace_ms=100)
    remaining, leaving = FakeSocket(), FakeSocket()
    room.join(remaining)
    room.join(leaving)

    room.leave(leaving)
    await _flush()

    assert remaining.sent[-1]["type"] == protocol.OPPONENT_DISCONNECTED
    assert remaining.sent[-1]["forfeit_in_ms"] == 100
    room.stop()


async def test_disconnect_forfeits_to_the_remaining_player_once_the_grace_window_elapses():
    bus = EventBus()
    received = []
    bus.subscribe("game.1", received.append)
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), bus, disconnect_grace_ms=20)
    remaining, leaving = FakeSocket(), FakeSocket()
    room.join(remaining, player=object())
    room.join(leaving, player=object())

    room.leave(leaving)
    await asyncio.sleep(0.06)

    game_over_messages = [m for m in remaining.sent if m["type"] == protocol.GAME_OVER]
    assert len(game_over_messages) == 1
    assert game_over_messages[0]["reason"] == "opponent_disconnected"
    assert game_over_messages[0]["winner"] == "white"  # "remaining" was seated first -> white
    assert any(isinstance(e, GameEnded) and e.winner == "white" for e in received)


async def test_rejoining_within_the_grace_window_cancels_the_forfeit():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus(), disconnect_grace_ms=50)
    remaining, leaving = FakeSocket(), FakeSocket()
    room.join(remaining)
    room.join(leaving)

    room.leave(leaving)
    reconnected = FakeSocket()
    room.rejoin(reconnected, "black")
    await asyncio.sleep(0.08)  # well past the original grace window

    assert room.color_of(reconnected) == "black"
    assert not any(m["type"] == protocol.GAME_OVER for m in remaining.sent)
    room.stop()


async def test_leave_after_the_game_already_ended_does_not_start_a_forfeit_timer():
    room = GameRoom("1", board_from(["wR . bK", ". . .", ". . ."]), EventBus(), disconnect_grace_ms=20)
    winner_socket, loser_socket = FakeSocket(), FakeSocket()
    room.join(winner_socket)
    room.join(loser_socket)
    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 0, "col": 2}})
    room._engine.wait(2000)  # king capture - game already over
    await _flush()

    room.leave(winner_socket)
    await _flush()

    assert not any(m["type"] == protocol.OPPONENT_DISCONNECTED for m in loser_socket.sent)


async def test_moves_are_ignored_once_the_game_has_ended_by_forfeit():
    room = GameRoom("1", board_from(["wR . .", ". . .", ". . ."]), EventBus(), disconnect_grace_ms=10)
    remaining, leaving = FakeSocket(), FakeSocket()
    room.join(remaining)
    room.join(leaving)
    room.leave(leaving)
    await asyncio.sleep(0.05)  # forfeited by now

    remaining.sent.clear()
    room.handle_request_move({"source": {"row": 0, "col": 0}, "destination": {"row": 0, "col": 2}})
    await _flush()

    assert remaining.sent == []
