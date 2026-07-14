from config import COOLDOWN_MS

from model.position import Position
from state.game_events import MoveAccepted, PieceArrived, PieceCaptured, PieceHalted, Promotion
from ui_components.cooldown_tracker import FRAME_COUNT, CooldownTracker


def test_starts_with_no_active_fades():
    assert CooldownTracker().active_fade_frames() == {}


def test_piece_arrived_starts_a_cooldown_at_the_destination():
    tracker = CooldownTracker()
    tracker.handle_event(PieceArrived(source=Position(0, 0), destination=Position(0, 3), token="wR"))
    assert Position(0, 3) in tracker.active_fade_frames()


def test_promotion_starts_a_cooldown_at_its_position():
    tracker = CooldownTracker()
    tracker.handle_event(Promotion(position=Position(0, 0), from_token="wP", to_token="wQ"))
    assert Position(0, 0) in tracker.active_fade_frames()


def test_capture_with_known_capturer_starts_a_cooldown():
    tracker = CooldownTracker()
    tracker.handle_event(PieceCaptured(position=Position(4, 3), captured_token="bP", by_token="wR"))
    assert Position(4, 3) in tracker.active_fade_frames()


def test_mid_flight_kill_does_not_start_a_cooldown():
    tracker = CooldownTracker()
    tracker.handle_event(PieceCaptured(position=Position(4, 3), captured_token="wB", by_token=None))
    assert tracker.active_fade_frames() == {}


def test_piece_halted_starts_a_cooldown_at_the_resting_cell():
    tracker = CooldownTracker()
    tracker.handle_event(PieceHalted(source=Position(2, 0), resting_at=Position(1, 1), token="wB"))
    assert Position(1, 1) in tracker.active_fade_frames()


def test_unrelated_events_are_ignored():
    tracker = CooldownTracker()
    tracker.handle_event(MoveAccepted(source=Position(0, 0), destination=Position(0, 1), token="wR"))
    assert tracker.active_fade_frames() == {}


def test_frame_index_starts_near_one_and_increases_toward_frame_count():
    tracker = CooldownTracker()
    tracker.handle_event(PieceArrived(source=Position(0, 0), destination=Position(0, 3), token="wR"))
    first = tracker.active_fade_frames()[Position(0, 3)]
    tracker.tick(COOLDOWN_MS // 2)
    middle = tracker.active_fade_frames()[Position(0, 3)]
    assert first == 1
    assert first < middle <= FRAME_COUNT


def test_cooldown_expires_and_stops_being_reported():
    tracker = CooldownTracker()
    tracker.handle_event(PieceArrived(source=Position(0, 0), destination=Position(0, 3), token="wR"))
    tracker.tick(COOLDOWN_MS)
    assert tracker.active_fade_frames() == {}
