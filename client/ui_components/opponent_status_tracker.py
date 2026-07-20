"""Tracks the opponent's disconnect-forfeit countdown, for a banner overlay
drawn on the board - the network counterpart to game_over_banner.py."""

from state.game_events import OpponentDisconnected, OpponentReconnected


class OpponentStatusTracker:
    def __init__(self):
        self._remaining_ms: int | None = None

    def handle_event(self, event) -> None:
        if isinstance(event, OpponentDisconnected):
            self._remaining_ms = event.forfeit_in_ms
        elif isinstance(event, OpponentReconnected):
            self._remaining_ms = None

    def tick(self, dt_ms: int) -> None:
        if self._remaining_ms is not None:
            self._remaining_ms = max(0, self._remaining_ms - dt_ms)

    def seconds_remaining(self) -> int | None:
        """Whole seconds left before auto-forfeit, rounded up so the
        displayed count never shows 0 while time is still actually left."""
        if self._remaining_ms is None:
            return None
        return (self._remaining_ms + 999) // 1000
