from model.position import Position
from state.game_events import PieceHalted
from ui_components.halt_flash import HaltFlashTracker
from ui_config import HALT_FLASH_DURATION_MS


def test_starts_with_no_active_flashes():
    assert HaltFlashTracker().active_positions() == []


def test_halt_event_activates_a_flash_at_the_resting_cell():
    tracker = HaltFlashTracker()
    tracker.handle_event(PieceHalted(source=Position(2, 0), resting_at=Position(1, 1), token="wB"))
    assert tracker.active_positions() == [Position(1, 1)]


def test_flash_is_still_active_just_before_its_duration_elapses():
    tracker = HaltFlashTracker()
    tracker.handle_event(PieceHalted(source=Position(2, 0), resting_at=Position(1, 1), token="wB"))
    tracker.tick(HALT_FLASH_DURATION_MS - 1)
    assert Position(1, 1) in tracker.active_positions()


def test_flash_expires_once_its_duration_elapses():
    tracker = HaltFlashTracker()
    tracker.handle_event(PieceHalted(source=Position(2, 0), resting_at=Position(1, 1), token="wB"))
    tracker.tick(HALT_FLASH_DURATION_MS)
    assert tracker.active_positions() == []
