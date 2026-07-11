from model.board import Board, EMPTY
from model.position import Position
from engine.game_engine import GameEngine


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


def test_arrival_skipped_when_piece_no_longer_at_source():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    b.move_piece(Position(0, 0), Position(0, 1))  # piece moved away
    engine.wait(2000)
    assert b.get_piece(Position(0, 2)) == EMPTY


def test_arrival_skipped_when_friendly_at_destination():
    b = board_from(["wR . wP", ". . .", ". . ."])
    engine = GameEngine(b)
    # force a motion directly on arbiter to bypass rule check
    engine._arbiter.start_motion("wR", Position(0, 0), Position(0, 2))
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == "wR"
    assert b.get_piece(Position(0, 2)) == "wP"
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    snap = engine.snapshot()
    assert snap.get_piece(Position(0, 0)) == "wR"
    assert not snap.game_over


def test_snapshot_get_piece_delegates_to_board():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    snap = engine.snapshot()
    assert snap.get_piece(Position(0, 0)) == "wR"
    assert snap.get_piece(Position(0, 1)) == EMPTY


def test_snapshot_board_property():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    snap = engine.snapshot()
    assert snap.board is b


def test_request_jump_ignored_when_game_over():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine._game_over = True
    engine.request_jump(Position(0, 0))  # should not raise


def test_request_jump_ignored_when_motion_active():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.request_jump(Position(0, 0))  # should not raise


def test_request_jump_ignored_on_empty_cell():
    b = board_from([". . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0))  # should not raise


def test_request_jump_starts_jump_motion():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0))
    engine.wait(1000)
    assert b.get_piece(Position(0, 0)) == "wR"  # jump returns to same cell


def test_pawn_promotes_on_last_row_white():
    b = board_from([". . .", "wP . .", ". . ."])
    engine = GameEngine(b)
    engine._arbiter.start_motion("wP", Position(1, 0), Position(2, 0))
    engine.wait(1000)
    assert b.get_piece(Position(2, 0)) == "wQ"


def test_pawn_promotes_on_last_row_black():
    b = board_from([". . .", "bP . .", ". . ."])
    engine = GameEngine(b)
    engine._arbiter.start_motion("bP", Position(1, 0), Position(0, 0))
    engine.wait(1000)
    assert b.get_piece(Position(0, 0)) == "bQ"


def test_airborne_collision_removes_attacker():
    # wR moves 1 cell (arrives at 1000ms); bR jump started 500ms earlier so still airborne at 1000ms
    b = board_from(["wR bR .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine._arbiter._clock = -500  # jump started 500ms before move
    engine._arbiter.start_jump("bR", Position(0, 1))  # arrival_time = -500 + 1000 = 500
    engine._arbiter._clock = 0
    engine._arbiter.start_motion("wR", Position(0, 0), Position(0, 1))  # arrival_time = 1000
    engine.wait(1000)  # clock=1000: motion arrives, jump already arrived (500) -> in airborne_dsts
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 1)) == "bR"

