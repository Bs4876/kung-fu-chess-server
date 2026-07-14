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
    engine.request_jump(Position(0, 0), Position(0, 1))  # should not raise


def test_request_jump_ignored_when_motion_active():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.request_jump(Position(0, 0), Position(0, 1))  # should not raise


def test_request_jump_ignored_on_empty_cell():
    b = board_from([". . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(0, 1))  # should not raise


def test_request_jump_ignored_when_destination_out_of_bounds():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(5, 5))  # should not raise
    assert not engine._arbiter.has_active_motion_for(Position(0, 0))


def test_request_jump_starts_jump_motion():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(0, 0))
    engine.wait(1000)
    assert b.get_piece(Position(0, 0)) == "wR"  # in-place jump returns to same cell


def test_jump_to_empty_square_relocates_piece():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(0, 2))
    engine.wait(1000)
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 2)) == "wR"


def test_jump_onto_enemy_square_kills_it():
    b = board_from(["wR . bN", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(0, 2))
    engine.wait(1000)
    assert b.get_piece(Position(0, 2)) == "wR"


def test_jump_onto_friendly_square_kills_it_too():
    b = board_from(["wR . wN", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(0, 2))
    engine.wait(1000)
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 2)) == "wR"  # friendly fire: only a jump can do this


def test_jump_onto_friendly_king_ends_the_game():
    b = board_from(["wR . wK", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(0, 2))
    engine.wait(1000)
    assert engine.game_over


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


def test_second_move_of_different_piece_is_accepted_while_first_in_progress():
    b = board_from(["wR . .", ". . .", "bR . ."])
    engine = GameEngine(b)
    first = engine.request_move(Position(0, 0), Position(0, 2))
    second = engine.request_move(Position(2, 0), Position(2, 2))
    assert first.is_accepted
    assert second.is_accepted
    assert second.reason == "ok"


def test_two_different_pieces_arrive_independently():
    b = board_from(["wR . .", ". . .", "bB . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 1))  # 1 cell -> 1000ms
    engine.request_move(Position(2, 0), Position(0, 2))  # 2 diagonal cells -> 2000ms
    engine.wait(1000)
    assert b.get_piece(Position(0, 1)) == "wR"
    assert b.get_piece(Position(2, 0)) == "bB"  # not arrived yet
    engine.wait(1000)
    assert b.get_piece(Position(0, 2)) == "bB"


def test_same_piece_still_rejected_while_its_own_motion_active():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    result = engine.request_move(Position(0, 0), Position(0, 1))
    assert not result.is_accepted
    assert result.reason == "motion_in_progress"


def test_jump_of_other_piece_allowed_while_first_piece_moving():
    b = board_from(["wR . .", ". . .", "bN . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.request_jump(Position(2, 0), Position(2, 0))  # should not raise, different piece
    engine.wait(1000)
    assert b.get_piece(Position(2, 0)) == "bN"  # jump lands back on same cell


def test_move_of_other_piece_allowed_while_first_piece_jumping():
    b = board_from(["wR . .", ". . .", "bN . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(2, 0), Position(2, 0))
    result = engine.request_move(Position(0, 0), Position(0, 1))
    assert result.is_accepted


def test_can_move_again_immediately_after_arrival():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 1))
    engine.wait(1000)
    result = engine.request_move(Position(0, 1), Position(0, 2))
    assert result.is_accepted
    assert result.reason == "ok"


def test_can_jump_immediately_after_arrival():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 1))
    engine.wait(1000)
    engine.request_jump(Position(0, 1), Position(0, 1))
    assert engine._arbiter.has_active_motion_for(Position(0, 1))


def test_capture_cancelled_when_target_changes_before_arrival():
    b = board_from(["wR . bN", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))  # wR commits to capturing bN
    b.replace_piece(Position(0, 2), EMPTY)
    b.replace_piece(Position(0, 2), "bB")  # a different enemy piece takes the cell first
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == "wR"  # motion cancelled, wR stayed put
    assert b.get_piece(Position(0, 2)) == "bB"  # bB untouched


def test_move_to_empty_square_cancelled_when_occupied_before_arrival():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))  # target empty when accepted
    b.replace_piece(Position(0, 2), "bP")  # someone else got there first
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == "wR"
    assert b.get_piece(Position(0, 2)) == "bP"


def test_capture_proceeds_when_target_unchanged():
    b = board_from(["wR . bN", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 2)) == "wR"


def test_colliding_pieces_are_removed_from_board():
    # wR requested first (earlier -> destroyed); bR requested second (later -> survives),
    # but bR's own arrival still expected "wR" at (0,0), which the collision already
    # cleared, so bR's arrival is cancelled and it's left sitting at (0,4).
    b = board_from(["wR . . . bR", ". . . . .", ". . . . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 4))
    engine.request_move(Position(0, 4), Position(0, 0))
    engine.wait(4000)
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 4)) == "bR"


def test_collision_skipped_when_piece_no_longer_at_position():
    b = board_from(["wR . . . bR", ". . . . .", ". . . . ."])
    engine = GameEngine(b)
    engine._arbiter.start_motion("wR", Position(0, 0), Position(0, 4))
    engine._arbiter.start_motion("bR", Position(0, 4), Position(0, 0))
    b.move_piece(Position(0, 0), Position(1, 0))  # wR relocated before the collision resolves
    engine.wait(4000)
    assert b.get_piece(Position(0, 4)) == EMPTY
    assert b.get_piece(Position(1, 0)) == "wR"


def test_king_destroyed_in_collision_ends_game():
    # wK started first (earlier -> destroyed, ends the game); bR started second
    # (later -> survives) and, with no expected_target to veto it, lands at (0,0).
    b = board_from(["wK . . . bR", ". . . . .", ". . . . ."])
    engine = GameEngine(b)
    engine._arbiter.start_motion("wK", Position(0, 0), Position(0, 4))
    engine._arbiter.start_motion("bR", Position(0, 4), Position(0, 0))
    engine.wait(4000)
    assert engine.game_over
    assert b.get_piece(Position(0, 0)) == "bR"
    assert b.get_piece(Position(0, 4)) == EMPTY


def test_airborne_collision_removes_attacker():
    # wR moves 1 cell (arrives at 1000ms); bR jump started 500ms earlier so still airborne at 1000ms
    b = board_from(["wR bR .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine._arbiter._clock = -500  # jump started 500ms before move
    engine._arbiter.start_jump("bR", Position(0, 1), Position(0, 1))  # arrival_time = -500 + 1000 = 500
    engine._arbiter._clock = 0
    engine._arbiter.start_motion("wR", Position(0, 0), Position(0, 1))  # arrival_time = 1000
    engine.wait(1000)  # clock=1000: motion arrives, jump already arrived (500) -> in airborne_dsts
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 1)) == "bR"

