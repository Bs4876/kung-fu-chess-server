"""Tracks which cells are cooling down (server/config.py's COOLDOWN_MS) so the
renderer can fade a highlight out over that window.

Mirrors exactly where server's GameEngine._apply_arrival calls
arbiter.start_cooldown(dst): on a clean arrival, a promotion, an
arrival-that-captures, and a mid-flight halt at a new cell - but *not* a
mid-flight kill (nothing is left resting there to cool down).
"""

from config import COOLDOWN_MS

from state.game_events import PieceArrived, PieceCaptured, PieceHalted, Promotion

FRAME_COUNT = 10  # matches the number of pre-baked ui/assets/cooldown_fade/*.png


class CooldownTracker:
    def __init__(self):
        self._elapsed_ms: dict = {}

    def handle_event(self, event) -> None:
        position = self._landing_position(event)
        if position is not None:
            self._elapsed_ms[position] = 0

    def _landing_position(self, event):
        if isinstance(event, PieceArrived):
            return event.destination
        if isinstance(event, Promotion):
            return event.position
        if isinstance(event, PieceCaptured) and event.by_token is not None:
            return event.position
        if isinstance(event, PieceHalted):
            return event.resting_at
        return None

    def tick(self, dt_ms: int) -> None:
        for position in list(self._elapsed_ms):
            self._elapsed_ms[position] += dt_ms
            if self._elapsed_ms[position] >= COOLDOWN_MS:
                del self._elapsed_ms[position]

    def active_fade_frames(self) -> dict:
        """Position -> 1-based fade frame index (1 = just started, higher = more faded)."""
        frames = {}
        for position, elapsed in self._elapsed_ms.items():
            fraction = min(elapsed / COOLDOWN_MS, 1.0)
            frames[position] = 1 + int(fraction * (FRAME_COUNT - 1))
        return frames
