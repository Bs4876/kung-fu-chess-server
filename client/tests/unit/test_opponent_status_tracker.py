from state.game_events import MoveAccepted, OpponentDisconnected, OpponentReconnected
from ui_components.opponent_status_tracker import OpponentStatusTracker


def test_starts_with_no_countdown():
    assert OpponentStatusTracker().seconds_remaining() is None


def test_disconnected_event_starts_the_countdown():
    tracker = OpponentStatusTracker()
    tracker.handle_event(OpponentDisconnected(20_000))
    assert tracker.seconds_remaining() == 20


def test_tick_counts_down():
    tracker = OpponentStatusTracker()
    tracker.handle_event(OpponentDisconnected(20_000))
    tracker.tick(5_000)
    assert tracker.seconds_remaining() == 15


def test_seconds_remaining_rounds_up_so_it_never_shows_zero_early():
    tracker = OpponentStatusTracker()
    tracker.handle_event(OpponentDisconnected(1_500))
    assert tracker.seconds_remaining() == 2


def test_tick_never_goes_negative():
    tracker = OpponentStatusTracker()
    tracker.handle_event(OpponentDisconnected(1_000))
    tracker.tick(5_000)
    assert tracker.seconds_remaining() == 0


def test_reconnected_event_clears_the_countdown():
    tracker = OpponentStatusTracker()
    tracker.handle_event(OpponentDisconnected(20_000))
    tracker.handle_event(OpponentReconnected())
    assert tracker.seconds_remaining() is None


def test_other_events_do_not_affect_the_countdown():
    tracker = OpponentStatusTracker()
    tracker.handle_event(MoveAccepted(source=None, destination=None, token="wR"))
    assert tracker.seconds_remaining() is None
