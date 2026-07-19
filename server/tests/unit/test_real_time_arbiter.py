from model.position import Position
from realtime.real_time_arbiter import RealTimeArbiter
from realtime.motion import Motion, ArrivalEvent, CollisionEvent
TEST_COOLDOWN_MS = 500


def test_no_active_motion_initially():
    arb = RealTimeArbiter()
    assert not arb.has_active_motion()


def test_has_active_motion_after_start():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 2))
    assert arb.has_active_motion()


def test_one_cell_arrives_after_1000ms():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 1))
    events = arb.advance_time(1000)
    assert len(events) == 1
    assert events[0].piece_token == "wR"
    assert events[0].src == Position(0, 0)
    assert events[0].dst == Position(0, 1)


def test_two_cells_arrives_after_2000ms():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 2))
    events = arb.advance_time(2000)
    assert len(events) == 1


def test_not_arrived_before_full_time():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 1))
    events = arb.advance_time(999)
    assert len(events) == 0
    assert arb.has_active_motion()


def test_partial_wait_then_remaining():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 1))
    arb.advance_time(500)
    assert arb.has_active_motion()
    events = arb.advance_time(500)
    assert len(events) == 1
    assert not arb.has_active_motion()


def test_no_active_motion_after_arrival():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 1))
    arb.advance_time(1000)
    assert not arb.has_active_motion()



def test_diagonal_uses_max_distance():
    arb = RealTimeArbiter()
    arb.start_motion("wB", Position(0, 0), Position(3, 3))
    events = arb.advance_time(2999)
    assert len(events) == 0
    events = arb.advance_time(1)
    assert len(events) == 1


def test_airborne_destinations_returns_jump_dsts():
    arb = RealTimeArbiter()
    arb.start_jump("wR", Position(1, 1), Position(1, 1))
    dsts = arb.airborne_destinations()
    assert Position(1, 1) in dsts
    assert dsts[Position(1, 1)] == "wR"


def test_airborne_destinations_reflects_jump_target_not_source():
    arb = RealTimeArbiter()
    arb.start_jump("wR", Position(1, 1), Position(3, 3))
    dsts = arb.airborne_destinations()
    assert Position(3, 3) in dsts
    assert Position(1, 1) not in dsts


def test_jump_arrives_after_jump_travel_time():
    from config import JUMP_TRAVEL_TIME
    arb = RealTimeArbiter()
    arb.start_jump("wR", Position(0, 0), Position(0, 0))
    events = arb.advance_time(JUMP_TRAVEL_TIME)
    assert len(events) == 1
    assert events[0].piece_token == "wR"
    assert events[0].src == Position(0, 0)
    assert events[0].dst == Position(0, 0)
    assert events[0].is_jump


def test_jump_to_different_destination_arrives_there():
    from config import JUMP_TRAVEL_TIME
    arb = RealTimeArbiter()
    arb.start_jump("wR", Position(0, 0), Position(3, 3))
    events = arb.advance_time(JUMP_TRAVEL_TIME)
    assert len(events) == 1
    assert events[0].src == Position(0, 0)
    assert events[0].dst == Position(3, 3)
    assert events[0].is_jump


def test_motion_with_explicit_travel_time():
    from realtime.motion import Motion
    m = Motion("wR", Position(0, 0), Position(0, 5), start_time=0, travel_time=500)
    assert m.arrival_time == 500


def test_has_active_motion_for_true_for_moving_source():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 2))
    assert arb.has_active_motion_for(Position(0, 0))


def test_has_active_motion_for_false_for_unrelated_position():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 2))
    assert not arb.has_active_motion_for(Position(1, 1))


def test_has_active_motion_for_false_when_no_motions():
    arb = RealTimeArbiter()
    assert not arb.has_active_motion_for(Position(0, 0))


def test_has_active_motion_for_true_for_jumping_position():
    arb = RealTimeArbiter()
    arb.start_jump("wR", Position(1, 1), Position(1, 1))
    assert arb.has_active_motion_for(Position(1, 1))


def test_has_active_motion_for_false_after_arrival():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 1))
    arb.advance_time(1000)
    assert not arb.has_active_motion_for(Position(0, 0))


def test_multiple_concurrent_motions_tracked_independently():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 2))
    arb.start_motion("bR", Position(2, 2), Position(2, 0))
    assert arb.has_active_motion_for(Position(0, 0))
    assert arb.has_active_motion_for(Position(2, 2))
    assert not arb.has_active_motion_for(Position(0, 2))


# ── Motion.path_positions ─────────────────────────────────────────────────────

def test_path_positions_for_straight_horizontal_motion():
    m = Motion("wR", Position(0, 0), Position(0, 3), start_time=0)
    assert m.path_positions() == [
        (1000, Position(0, 1)),
        (2000, Position(0, 2)),
        (3000, Position(0, 3)),
    ]


def test_path_positions_for_diagonal_motion():
    m = Motion("bB", Position(2, 0), Position(0, 2), start_time=0)
    assert m.path_positions() == [
        (1000, Position(1, 1)),
        (2000, Position(0, 2)),
    ]


def test_path_positions_empty_for_knight_shaped_motion():
    m = Motion("wN", Position(0, 0), Position(2, 1), start_time=0)
    assert m.path_positions() == []


def test_straight_line_meeting_time_is_none_when_either_motion_is_knight_shaped():
    from realtime.motion import straight_line_meeting_time
    # Both start at the exact same cell at the exact same instant - as
    # obvious a "collision" as two paths can share, if evaluated as plain
    # straight lines - yet still None, since a knight has no path at all.
    knight = Motion("wN", Position(0, 0), Position(2, 1), start_time=0)
    other = Motion("bR", Position(0, 0), Position(0, 3), start_time=0)
    assert straight_line_meeting_time(knight, other) is None
    assert straight_line_meeting_time(other, knight) is None


# ── Collision between moving pieces ──────────────────────────────────────────
#
# Different colors crossing paths: the motion that started later survives and
# eats the one that started earlier (asymmetric, not mutual destruction).
# Same color crossing paths: the later motion halts at the last safe cell
# before the meeting point instead of colliding with its own side.

def test_head_on_crossing_different_colors_only_earlier_one_dies():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 4))  # started first -> earlier
    arb.start_motion("bR", Position(0, 4), Position(0, 0))  # started second -> later, survives
    events = arb.advance_time(4000)
    collisions = [e for e in events if isinstance(e, CollisionEvent)]
    arrivals = [e for e in events if isinstance(e, ArrivalEvent)]
    assert {e.piece_token for e in collisions} == {"wR"}
    assert {e.piece_token for e in arrivals} == {"bR"}
    assert not arb.has_active_motion_for(Position(0, 0))


def test_collision_fires_exactly_at_shared_tick():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 4))
    arb.start_motion("bR", Position(0, 4), Position(0, 0))
    events = arb.advance_time(1999)
    assert events == []
    assert arb.has_active_motion_for(Position(0, 0))
    events = arb.advance_time(1)
    assert len(events) == 1
    assert isinstance(events[0], CollisionEvent)
    assert events[0].piece_token == "wR"
    assert not arb.has_active_motion_for(Position(0, 0))
    assert arb.has_active_motion_for(Position(0, 4))


def test_crossing_perpendicular_paths_different_colors_only_earlier_one_dies():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 4))  # started first -> earlier, dies
    arb.start_motion("bB", Position(2, 0), Position(0, 2))  # started second -> later, survives, arrives (0,2) at t=2000
    events = arb.advance_time(2000)
    collisions = [e for e in events if isinstance(e, CollisionEvent)]
    arrivals = [e for e in events if isinstance(e, ArrivalEvent)]
    assert {e.piece_token for e in collisions} == {"wR"}
    assert {e.piece_token for e in arrivals} == {"bB"}
    assert not arb.has_active_motion_for(Position(0, 0))


def test_crossing_paths_same_color_later_one_halts_before_meeting_point():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 4))  # started first -> earlier, unaffected
    arb.start_motion("wB", Position(2, 0), Position(0, 2))  # started second -> later, halts before (0,2)
    events = arb.advance_time(2000)
    assert len(events) == 1
    assert isinstance(events[0], ArrivalEvent)
    assert events[0].piece_token == "wB"
    assert events[0].dst == Position(1, 1)  # last safe cell before the (0,2) meeting point
    assert not arb.has_active_motion_for(Position(2, 0))
    assert arb.has_active_motion_for(Position(0, 0))  # wR unaffected, still en route to (0,4)


def test_same_color_collision_on_first_step_halts_at_source():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 5))  # started first -> earlier, unaffected
    arb.start_motion("wB", Position(0, 2), Position(0, 0))  # started second -> later, meets at (0,1) on its first step
    events = arb.advance_time(1000)
    assert len(events) == 1
    halted = events[0]
    assert halted.piece_token == "wB"
    assert halted.dst == Position(0, 2)  # no safe cell reached yet, halts at its own source


def test_odd_distance_head_on_paths_still_collide_between_cell_centers():
    # 3 cells apart, same speed, head-on: they'd cross at col 1.5 (t=1500) -
    # never both resting on the same integer cell at the same integer tick,
    # but their continuous paths still genuinely cross each other.
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 3))  # started first -> earlier, dies
    arb.start_motion("bR", Position(0, 3), Position(0, 0))  # started second -> later, survives
    events = arb.advance_time(3000)
    collisions = [e for e in events if isinstance(e, CollisionEvent)]
    arrivals = [e for e in events if isinstance(e, ArrivalEvent)]
    assert {e.piece_token for e in collisions} == {"wR"}
    assert {e.piece_token for e in arrivals} == {"bR"}


def test_odd_distance_head_on_collision_fires_exactly_at_the_crossing_tick():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 3))
    arb.start_motion("bR", Position(0, 3), Position(0, 0))
    events = arb.advance_time(1499)
    assert events == []
    events = arb.advance_time(1)  # crosses t=1500, the midpoint between col 1 and col 2
    assert len(events) == 1
    assert isinstance(events[0], CollisionEvent)


def test_odd_distance_same_color_paths_halt_at_the_last_safe_cell():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 3))  # started first -> earlier, unaffected
    arb.start_motion("wB", Position(0, 3), Position(0, 0))  # started second -> halts before crossing at t=1500
    events = arb.advance_time(1500)
    assert len(events) == 1
    halted = events[0]
    assert halted.piece_token == "wB"
    assert halted.dst == Position(0, 2)  # 1 full cell traveled (col 3 -> 2) before the col-1.5 crossing
    assert arb.has_active_motion_for(Position(0, 0))  # wR unaffected, still en route to (0,3)


def test_unrelated_motions_do_not_collide():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 1))
    arb.start_motion("bR", Position(2, 0), Position(2, 1))
    events = arb.advance_time(1000)
    assert len(events) == 2
    assert all(isinstance(e, ArrivalEvent) for e in events)


# ── Cooldown after arrival ────────────────────────────────────────────────────

def test_no_cooldown_initially():
    arb = RealTimeArbiter()
    assert not arb.is_on_cooldown(Position(0, 0))


def test_start_cooldown_marks_position_active():
    arb = RealTimeArbiter()
    arb.start_cooldown(Position(0, 0), TEST_COOLDOWN_MS)
    assert arb.is_on_cooldown(Position(0, 0))


def test_cooldown_is_per_position():
    arb = RealTimeArbiter()
    arb.start_cooldown(Position(0, 0), TEST_COOLDOWN_MS)
    assert not arb.is_on_cooldown(Position(1, 1))


def test_cooldown_expires_after_duration():
    arb = RealTimeArbiter()
    arb.start_cooldown(Position(0, 0), TEST_COOLDOWN_MS)
    arb.advance_time(TEST_COOLDOWN_MS - 1)
    assert arb.is_on_cooldown(Position(0, 0))
    arb.advance_time(1)
    assert not arb.is_on_cooldown(Position(0, 0))


def test_different_durations_are_respected_independently():
    arb = RealTimeArbiter()
    arb.start_cooldown(Position(0, 0), 3000)
    arb.start_cooldown(Position(1, 1), 1500)
    arb.advance_time(1500)
    assert arb.is_on_cooldown(Position(0, 0))
    assert not arb.is_on_cooldown(Position(1, 1))


def test_arrivals_within_one_wait_are_processed_in_chronological_order():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 2))  # arrives at 2000, started first
    arb.start_motion("bP", Position(5, 5), Position(5, 6))  # arrives at 1000, started second
    events = arb.advance_time(2000)
    assert [e.piece_token for e in events] == ["bP", "wR"]


def test_third_unrelated_motion_unaffected_by_earlier_collided_pair():
    arb = RealTimeArbiter()
    arb.start_motion("wR", Position(0, 0), Position(0, 4))
    arb.start_motion("bR", Position(0, 4), Position(0, 0))
    arb.start_motion("wB", Position(5, 5), Position(5, 6))
    events = arb.advance_time(4000)
    assert len(events) == 3
    collided_tokens = {e.piece_token for e in events if isinstance(e, CollisionEvent)}
    assert collided_tokens == {"wR"}
    arrived_tokens = {e.piece_token for e in events if isinstance(e, ArrivalEvent)}
    assert arrived_tokens == {"bR", "wB"}
