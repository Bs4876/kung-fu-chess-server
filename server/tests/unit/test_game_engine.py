from model.board import Board, EMPTY
from model.position import Position
from engine.game_engine import GameEngine, Arrived, Captured, Halted, Promoted
from config import MOVE_COOLDOWN_MS, JUMP_COOLDOWN_MS


def board_from(rows):
    return Board([[c for c in row.split()] for row in rows])


def test_valid_move_accepted():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    result = engine.request_move(Position(0, 0), Position(0, 2))
    assert result.is_accepted
    assert result.reason == "ok"


def test_legal_destinations_delegates_to_the_rule_engine():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    assert engine.legal_destinations(Position(0, 0)) == {
        Position(0, 1), Position(0, 2), Position(1, 0), Position(2, 0),
    }


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


def test_arrival_backs_off_when_friendly_at_destination():
    b = board_from(["wR . wP", ". . .", ". . ."])
    engine = GameEngine(b)
    # force a motion directly on arbiter to bypass rule check
    engine._arbiter.start_motion("wR", Position(0, 0), Position(0, 2))
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 1)) == "wR"  # backs off to the cell before the blocked destination
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


def test_in_place_jump_starts_a_cooldown():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(0, 0))
    engine.wait(1000)  # jump arrives
    result = engine.request_move(Position(0, 0), Position(0, 1))
    assert not result.is_accepted
    assert result.reason == "cooldown"
    engine.wait(JUMP_COOLDOWN_MS)
    result2 = engine.request_move(Position(0, 0), Position(0, 1))
    assert result2.is_accepted


def test_in_place_jump_of_a_king_does_not_end_the_game():
    b = board_from(["wK . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(0, 0))
    engine.wait(1000)
    assert not engine.game_over
    assert b.get_piece(Position(0, 0)) == "wK"


def test_move_halted_back_at_its_own_source_starts_no_cooldown():
    # Mirrors test_same_color_collision_on_first_step_halts_at_source in
    # test_real_time_arbiter.py (two same-color rooks meeting on the second
    # rook's very first step, so it halts right back at its own source): a
    # move that never actually made progress shouldn't cost a cooldown,
    # unlike a deliberate in-place jump.
    b = board_from(["wR . wR . . .", ". . . . . .", ". . . . . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 5))
    engine.request_move(Position(0, 2), Position(0, 0))
    engine.wait(1000)
    assert b.get_piece(Position(0, 2)) == "wR"  # halted at its own source
    result = engine.request_move(Position(0, 2), Position(0, 1))
    assert result.is_accepted  # no cooldown penalty for never having moved


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


def test_move_rejected_during_cooldown_after_arrival():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 1))
    engine.wait(1000)  # arrives, cooldown starts at (0, 1)
    result = engine.request_move(Position(0, 1), Position(0, 2))
    assert not result.is_accepted
    assert result.reason == "cooldown"
    assert b.get_piece(Position(0, 1)) == "wR"


def test_move_accepted_once_cooldown_expires():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 1))
    engine.wait(1000)
    engine.wait(MOVE_COOLDOWN_MS)
    result = engine.request_move(Position(0, 1), Position(0, 2))
    assert result.is_accepted
    assert result.reason == "ok"


def test_jump_rejected_during_cooldown_after_arrival():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 1))
    engine.wait(1000)
    engine.request_jump(Position(0, 1), Position(0, 1))
    assert not engine._arbiter.has_active_motion_for(Position(0, 1))


def test_jump_accepted_once_cooldown_expires():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 1))
    engine.wait(1000)
    engine.wait(MOVE_COOLDOWN_MS)
    engine.request_jump(Position(0, 1), Position(0, 1))
    assert engine._arbiter.has_active_motion_for(Position(0, 1))


def test_cooldown_does_not_block_other_pieces():
    b = board_from(["wR . .", ". . .", "bR . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 1))
    engine.wait(1000)
    result = engine.request_move(Position(2, 0), Position(2, 1))
    assert result.is_accepted


def test_cooldown_after_a_jump_uses_the_shorter_jump_duration():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(0, 1))
    engine.wait(1000)  # jump arrives, cooldown starts at (0, 1)
    still_cooling = engine.request_move(Position(0, 1), Position(0, 2))
    assert not still_cooling.is_accepted
    assert still_cooling.reason == "cooldown"
    engine.wait(JUMP_COOLDOWN_MS)
    now_ready = engine.request_move(Position(0, 1), Position(0, 2))
    assert now_ready.is_accepted


def test_move_cooldown_is_longer_than_jump_cooldown():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 1))
    engine.wait(1000)  # move arrives, cooldown starts at (0, 1)
    engine.wait(JUMP_COOLDOWN_MS)  # long enough for a jump's cooldown, not a move's
    still_cooling = engine.request_move(Position(0, 1), Position(0, 2))
    assert not still_cooling.is_accepted
    assert still_cooling.reason == "cooldown"


def test_capture_targets_whoever_is_actually_there_on_arrival():
    # wR heads toward what it saw as bN at request time - a different enemy
    # (bB) takes the cell before wR arrives; wR still captures whoever's
    # actually there now, not the originally-seen bN.
    b = board_from(["wR . bN", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    b.replace_piece(Position(0, 2), EMPTY)
    b.replace_piece(Position(0, 2), "bB")
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 2)) == "wR"


def test_move_to_empty_square_captures_an_enemy_that_arrived_there_first():
    # No specific capture was ever intended (the square was empty when the
    # move was accepted) - an enemy beating you there is the same same-square
    # race the mid-flight collision system resolves elsewhere: later arrival wins.
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))  # target empty when accepted
    b.replace_piece(Position(0, 2), "bP")  # an enemy got there first
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 2)) == "wR"  # wR arrives later and captures bP


def test_move_to_empty_square_backs_off_when_a_friendly_piece_arrives_first():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))  # target empty when accepted
    b.replace_piece(Position(0, 2), "wN")  # a friendly piece got there first
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 1)) == "wR"  # backs off to the cell before the blocked destination
    assert b.get_piece(Position(0, 2)) == "wN"  # wN untouched


def test_adjacent_move_cancels_when_a_friendly_piece_arrives_first():
    # Only 1 cell away - no cell before the destination to back off to.
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 1))
    b.replace_piece(Position(0, 1), "wN")
    engine.wait(1000)
    assert b.get_piece(Position(0, 0)) == "wR"
    assert b.get_piece(Position(0, 1)) == "wN"


def test_knight_shaped_move_cancels_when_a_friendly_piece_arrives_first():
    # No path at all to back off along (see Motion.is_straight_line).
    b = board_from(["wN . . .", ". . . .", ". . . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(1, 2))
    b.replace_piece(Position(1, 2), "wR")
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == "wN"
    assert b.get_piece(Position(1, 2)) == "wR"


def test_capture_proceeds_when_target_unchanged():
    b = board_from(["wR . bN", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(2000)
    assert b.get_piece(Position(0, 0)) == EMPTY
    assert b.get_piece(Position(0, 2)) == "wR"


def test_colliding_pieces_are_removed_from_board():
    # wR requested first (earlier -> destroyed); bR requested second (later ->
    # survives) and, with its own square now empty (wR just died there),
    # lands normally at (0,0).
    b = board_from(["wR . . . bR", ". . . . .", ". . . . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 4))
    engine.request_move(Position(0, 4), Position(0, 0))
    engine.wait(4000)
    assert b.get_piece(Position(0, 0)) == "bR"
    assert b.get_piece(Position(0, 4)) == EMPTY


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
    # (later -> survives) and lands normally at (0,0).
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


# ── wait()'s returned outcomes ────────────────────────────────────────────────
#
# wait() itself already knows exactly what each resolved motion amounts to
# (arrival/capture/halt/promotion) the instant it happens, so callers (e.g.
# ui's GameFacade) don't need to re-derive it later by diffing board snapshots.

def test_wait_reports_arrived_for_a_plain_move():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    outcomes = engine.wait(2000)
    assert outcomes == [Arrived(Position(0, 0), Position(0, 2), "wR")]


def test_wait_reports_captured_on_arrival_with_the_capturing_token():
    b = board_from(["wR . bN", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    outcomes = engine.wait(2000)
    assert outcomes == [Captured(Position(0, 0), Position(0, 2), "bN", "wR")]


def test_wait_reports_captured_with_no_capturer_on_mid_flight_collision():
    b = board_from(["wR . . . bR", ". . . . .", ". . . . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 4))  # earlier -> dies
    engine.request_move(Position(0, 4), Position(0, 0))  # later -> survives
    outcomes = engine.wait(4000)
    collisions = [o for o in outcomes if isinstance(o, Captured)]
    assert collisions == [Captured(Position(0, 0), Position(0, 0), "wR", None)]


def test_wait_reports_captured_with_no_capturer_on_airborne_interception():
    # The jump itself also lands (in place) within this same wait() call, so
    # its own Arrived outcome is expected alongside wR's airborne-kill Captured.
    b = board_from(["wR bR .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine._arbiter._clock = -500
    engine._arbiter.start_jump("bR", Position(0, 1), Position(0, 1))
    engine._arbiter._clock = 0
    engine._arbiter.start_motion("wR", Position(0, 0), Position(0, 1))
    outcomes = engine.wait(1000)
    captures = [o for o in outcomes if isinstance(o, Captured)]
    assert captures == [Captured(Position(0, 0), Position(0, 0), "wR", None)]


def test_wait_reports_halted_when_resting_short_of_the_intended_destination():
    b = board_from(["wR . . . .", ". . . . .", "wB . . . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 4))  # earlier, unaffected
    engine.request_move(Position(2, 0), Position(0, 2))  # later, halts at (1, 1)
    outcomes = engine.wait(2000)
    halts = [o for o in outcomes if isinstance(o, Halted)]
    assert halts == [Halted(Position(2, 0), Position(1, 1), "wB")]


def test_wait_reports_no_outcome_when_a_halt_lands_back_on_its_own_source():
    # Mirrors test_same_color_collision_on_first_step_halts_at_source in
    # test_real_time_arbiter.py: two same-color pieces meeting on the second
    # one's very first step, so it halts right back at its own source - set up
    # directly on the arbiter, since a request_move here would be rejected as
    # illegal in the first place (its path is blocked by the other piece).
    b = board_from(["wR . wB . . .", ". . . . . .", ". . . . . ."])
    engine = GameEngine(b)
    engine._arbiter.start_motion("wR", Position(0, 0), Position(0, 5))
    engine._arbiter.start_motion("wB", Position(0, 2), Position(0, 0))
    outcomes = engine.wait(1000)
    assert outcomes == []


def test_wait_reports_promoted_when_a_pawn_lands_on_the_back_rank():
    b = board_from([". . .", "wP . .", ". . ."])
    engine = GameEngine(b)
    engine._arbiter.start_motion("wP", Position(1, 0), Position(2, 0))
    outcomes = engine.wait(1000)
    assert outcomes == [Promoted(Position(1, 0), Position(2, 0), "wP", "wQ")]


def test_wait_reports_arrived_for_a_deliberate_in_place_jump():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_jump(Position(0, 0), Position(0, 0))
    outcomes = engine.wait(1000)
    assert outcomes == [Arrived(Position(0, 0), Position(0, 0), "wR", is_jump=True)]


def test_wait_reports_the_capture_of_whoever_is_actually_there():
    b = board_from(["wR . bN", ". . .", ". . ."])
    engine = GameEngine(b)
    engine.request_move(Position(0, 0), Position(0, 2))
    b.replace_piece(Position(0, 2), EMPTY)
    b.replace_piece(Position(0, 2), "bB")
    outcomes = engine.wait(2000)
    assert outcomes == [Captured(source=Position(0, 0), position=Position(0, 2), captured_token="bB", by_token="wR")]


def test_wait_reports_a_halt_when_blocked_by_a_friendly_at_destination():
    b = board_from(["wR . wP", ". . .", ". . ."])
    engine = GameEngine(b)
    engine._arbiter.start_motion("wR", Position(0, 0), Position(0, 2))
    outcomes = engine.wait(2000)
    assert outcomes == [Halted(source=Position(0, 0), resting_at=Position(0, 1), token="wR")]


# ── subscribe()/publish() ─────────────────────────────────────────────────────
#
# The engine is the one that identifies each outcome, so it's also the one
# that publishes it - callers can subscribe instead of only reading wait()'s
# return value.

def test_subscriber_is_notified_of_a_resolved_outcome():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    received = []
    engine.subscribe(received.append)
    engine.request_move(Position(0, 0), Position(0, 2))
    outcomes = engine.wait(2000)
    assert received == outcomes == [Arrived(Position(0, 0), Position(0, 2), "wR")]


def test_subscriber_receives_nothing_when_wait_resolves_no_outcome():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    received = []
    engine.subscribe(received.append)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(1999)  # not arrived yet
    assert received == []


def test_multiple_outcomes_in_one_wait_are_published_in_resolution_order():
    b = board_from(["wR . .", ". . .", "bB . ."])
    engine = GameEngine(b)
    received = []
    engine.subscribe(received.append)
    engine.request_move(Position(0, 0), Position(0, 1))  # 1 cell -> 1000ms
    engine.request_move(Position(2, 0), Position(0, 2))  # 2 diagonal cells -> 2000ms
    outcomes = engine.wait(2000)
    assert received == outcomes
    assert len(received) == 2


def test_multiple_subscribers_all_notified_of_the_same_outcome():
    b = board_from(["wR . .", ". . .", ". . ."])
    engine = GameEngine(b)
    first, second = [], []
    engine.subscribe(first.append)
    engine.subscribe(second.append)
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(2000)
    assert first == second == [Arrived(Position(0, 0), Position(0, 2), "wR")]

