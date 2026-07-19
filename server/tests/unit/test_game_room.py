import asyncio
import json

from bus.event_bus import EventBus
from model.board import Board
from net import protocol
from net.game_room import GameRoom


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
