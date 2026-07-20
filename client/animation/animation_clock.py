"""Per-frame delta-time source for the render loop."""

import time


class Clock:
    """Reports milliseconds elapsed between successive tick() calls.

    Takes an injectable time source (defaults to time.perf_counter) so tests
    can control the passage of time without waiting on a real clock.
    """

    def __init__(self, time_source=time.perf_counter):
        self._time_source = time_source
        self._last_time = self._time_source()

    def tick(self) -> int:
        """Return milliseconds elapsed since the previous tick() call."""
        now = self._time_source()
        elapsed_ms = int((now - self._last_time) * 1000)
        self._last_time = now
        return elapsed_ms
