"""Tracks recently-halted cells (mid-flight same-color collisions) so the
renderer can flash them briefly, as a visual cue that something unusual (not a
normal arrival) just happened there."""

from ui_config import HALT_FLASH_DURATION_MS

from state.game_events import PieceHalted


class HaltFlashTracker:
    def __init__(self):
        self._remaining_ms: dict = {}

    def handle_event(self, event) -> None:
        if isinstance(event, PieceHalted):
            self._remaining_ms[event.resting_at] = HALT_FLASH_DURATION_MS

    def tick(self, dt_ms: int) -> None:
        for pos in list(self._remaining_ms):
            self._remaining_ms[pos] -= dt_ms
            if self._remaining_ms[pos] <= 0:
                del self._remaining_ms[pos]

    def active_positions(self) -> list:
        return list(self._remaining_ms.keys())
