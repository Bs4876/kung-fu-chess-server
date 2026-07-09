from model.board import Board, EMPTY
from model.position import Position
from game_engine_pkg.game_engine import GameEngine


def board_from(rows):
    return Board([[c for c in row.split()] for row in rows])


def test_valid_move_accepted():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    result = engine.request_move(Position(0, 0), Position(0, 2))
    assert result.is_accepted
    assert result.reason == "ok"


def test_invalid_move_rejected():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    result = engine.request_move(Position(0, 0), Position(1, 1))
    assert not result.is_accepted
    assert result.reason == "illegal_piece_move"


def test_game_over_rejects_move():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine._game_over = True
    result = engine.request_move(Position(0, 0), Position(0, 2))
    assert not result.is_accepted
    assert result.reason == "game_over"


def test_motion_in_progress_rejects_second_move():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    result = engine.request_move(Position(0, 0), Position(0, 1))
    assert not result.is_accepted
    assert result.reason == "motion_in_progress"


def test_piece_arrives_after_wait():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 2)) == "wR"


def test_piece_not_arrived_before_full_time():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(1999)
    assert b.get_piece(Position(0, 0)) == "wR"


def test_capture_enemy_on_arrival():
    b = board_from(["wR . bP", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(2000)
    assert b.get_piece(Position(0, 2)) == "wR"


def test_king_capture_sets_game_over():
    b = board_from(["wR . bK", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(2000)
    assert engine.game_over


def test_move_rejected_after_king_captured():
    b = board_from(["wR . bK", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(2000)
    result = engine.request_move(Position(0, 2), Position(0, 0))
    assert not result.is_accepted
    assert result.reason == "game_over"


def test_snapshot_returns_board_and_game_over():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    snap = engine.snapshot()
    assert snap.board is b
    assert not snap.game_over
