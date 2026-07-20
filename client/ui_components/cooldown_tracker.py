"""Tracks which cells are cooling down so the renderer can fade a highlight
out over that window.

Mirrors exactly where server's GameEngine._apply_arrival calls
arbiter.start_cooldown(dst, ...): on a clean arrival, a promotion, an
arrival-that-captures, and a mid-flight halt at a new cell - but *not* a
mid-flight kill (nothing is left resting there to cool down). The duration
matches whichever of MOVE_COOLDOWN_MS/JUMP_COOLDOWN_MS the server itself used
for that same landing, via each event's is_jump flag.
"""

from config import JUMP_COOLDOWN_MS, MOVE_COOLDOWN_MS

from state.game_events import PieceArrived, PieceCaptured, PieceHalted, Promotion


class _Cooldown:
    def __init__(self, duration_ms: int):
        self.elapsed_ms = 0
        self.duration_ms = duration_ms


class CooldownTracker:
    def __init__(self):
        self._cooldowns: dict = {}

    def handle_event(self, event) -> None:
        landing = self._landing(event)
        if landing is not None:
            position, duration_ms = landing
            self._cooldowns[position] = _Cooldown(duration_ms)

    def _landing(self, event):
        if isinstance(event, PieceArrived):
            return event.destination, self._duration_for(event)
        if isinstance(event, Promotion):
            return event.position, self._duration_for(event)
        if isinstance(event, PieceCaptured) and event.by_token is not None:
            return event.position, self._duration_for(event)
        if isinstance(event, PieceHalted):
            return event.resting_at, self._duration_for(event)
        return None

    @staticmethod
    def _duration_for(event) -> int:
        return JUMP_COOLDOWN_MS if event.is_jump else MOVE_COOLDOWN_MS

    def tick(self, dt_ms: int) -> None:
        for position in list(self._cooldowns):
            cooldown = self._cooldowns[position]
            cooldown.elapsed_ms += dt_ms
            if cooldown.elapsed_ms >= cooldown.duration_ms:
                del self._cooldowns[position]

    def active_fade_frames(self) -> dict:
        """Position -> fraction (0.0 = just started/most opaque, 1.0 = fully faded)."""
        return {
            pos: min(cd.elapsed_ms / cd.duration_ms, 1.0)
            for pos, cd in self._cooldowns.items()
        }
