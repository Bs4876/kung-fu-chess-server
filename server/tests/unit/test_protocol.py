import json

import pytest

from config import SCHEMA_VERSION
from engine.game_engine import Arrived, GameSnapshot, MoveResult
from model.board import Board
from model.position import Position
from net import protocol


def test_encode_stamps_schema_version():
    text = protocol.encode({"type": "ping"})
    assert json.loads(text) == {"schema_version": SCHEMA_VERSION, "type": "ping"}


def test_decode_round_trips_encode():
    message = {"type": protocol.REQUEST_MOVE, "source": {"row": 0, "col": 0}}
    assert protocol.decode(protocol.encode(message)) == {**message, "schema_version": SCHEMA_VERSION}


def test_decode_rejects_non_object_json():
    with pytest.raises(ValueError):
        protocol.decode("[1, 2, 3]")


def test_decode_rejects_missing_type():
    with pytest.raises(ValueError):
        protocol.decode(json.dumps({"foo": "bar"}))


def test_position_round_trips_through_wire_dict():
    pos = Position(2, 5)
    assert protocol.position_from_wire(protocol.position_to_wire(pos)) == pos


def test_snapshot_to_wire_includes_board_rows():
    board = Board([["wR", "."], [".", "bK"]])
    snapshot = GameSnapshot(board, game_over=False)
    assert protocol.snapshot_to_wire(snapshot) == {"rows": 2, "cols": 2, "board": [["wR", "."], [".", "bK"]]}


def test_game_start_message_shape():
    snapshot = GameSnapshot(Board([["wR"]]), game_over=False)
    message = protocol.game_start("1", "white", 0, snapshot)
    assert message["type"] == protocol.GAME_START
    assert message["color"] == "white"
    assert message["state_version"] == 0
    assert message["snapshot"]["board"] == [["wR"]]


def test_request_move_message_shape():
    message = protocol.request_move("1", Position(0, 0), Position(0, 2))
    assert message == {
        "type": protocol.REQUEST_MOVE,
        "game_id": "1",
        "source": {"row": 0, "col": 0},
        "destination": {"row": 0, "col": 2},
    }


def test_request_jump_message_shape():
    message = protocol.request_jump("1", Position(0, 0), Position(2, 2))
    assert message == {
        "type": protocol.REQUEST_JUMP,
        "game_id": "1",
        "source": {"row": 0, "col": 0},
        "destination": {"row": 2, "col": 2},
    }


def test_jump_started_message_shape():
    message = protocol.jump_started("1", Position(0, 0), Position(2, 2))
    assert message == {
        "type": protocol.JUMP_STARTED,
        "game_id": "1",
        "source": {"row": 0, "col": 0},
        "destination": {"row": 2, "col": 2},
    }


def test_move_result_accepted():
    message = protocol.move_result("1", Position(0, 0), Position(0, 1), MoveResult(True, "ok"))
    assert message["type"] == protocol.MOVE_ACCEPTED
    assert message["reason"] == "ok"
    assert message["source"] == {"row": 0, "col": 0}
    assert message["destination"] == {"row": 0, "col": 1}


def test_move_result_rejected():
    message = protocol.move_result("1", Position(0, 0), Position(0, 1), MoveResult(False, "cooldown"))
    assert message["type"] == protocol.MOVE_REJECTED
    assert message["reason"] == "cooldown"


def test_outcome_translates_position_fields_and_keeps_scalars():
    arrived = Arrived(source=Position(0, 0), destination=Position(0, 2), token="wR", is_jump=False)
    message = protocol.outcome(protocol.ARRIVED, "1", 3, arrived)
    assert message == {
        "type": protocol.ARRIVED,
        "game_id": "1",
        "state_version": 3,
        "source": {"row": 0, "col": 0},
        "destination": {"row": 0, "col": 2},
        "token": "wR",
        "is_jump": False,
    }


def test_game_over_message_shape():
    message = protocol.game_over("1", 5, "king_capture", "white")
    assert message == {
        "type": protocol.GAME_OVER,
        "game_id": "1",
        "state_version": 5,
        "reason": "king_capture",
        "winner": "white",
    }


def test_error_message_shape():
    assert protocol.error("bad_message", "oops") == {"type": protocol.ERROR, "code": "bad_message", "message": "oops"}
