"""Owns pending-motion bookkeeping for GameFacade: predicting where an
in-flight piece should be drawn, reconciled away once GameEngine reports
the motion resolved (see state/outcome_translator.py for turning that
resolution into a UI-facing event - a separate concern from bookkeeping).

Split out of GameFacade so GameFacade itself only has to coordinate the
engine + this tracker + the event stream, instead of also being the one
holding and mutating the pending-motion dict directly.
"""


class PendingMotion:
    """A piece's predicted travel from source to destination, for animation only.

    Timed with the exact same constants the server itself uses (imported, never
    re-derived), so the predicted pixel motion tracks the real one closely. Its
    resolution (arrival/capture/halt/promotion) is never guessed from this -
    that comes straight from GameEngine.wait()'s return value instead.
    """

    def __init__(self, source, destination, token: str, duration_ms: float, is_jump: bool):
        self.source = source
        self.destination = destination
        self.token = token
        self.duration_ms = duration_ms
        self.is_jump = is_jump
        self.elapsed_ms = 0.0

    def advance(self, dt_ms: int) -> None:
        self.elapsed_ms += dt_ms

    @property
    def progress(self) -> float:
        """0.0 at the start of the motion, 1.0 once predicted to have arrived."""
        if self.duration_ms <= 0:
            return 1.0
        return min(self.elapsed_ms / self.duration_ms, 1.0)


class MotionTracker:
    """Pure bookkeeping - no Subject/publish or event-translation dependency,
    so it's testable with plain outcome objects in, pending-dict state out."""

    def __init__(self):
        self._pending: dict = {}

    def start(self, source, destination, token: str, duration_ms: float, is_jump: bool) -> None:
        self._pending[source] = PendingMotion(source, destination, token, duration_ms, is_jump)

    def pending(self) -> dict:
        """Read-only view of in-flight motions, keyed by their source cell."""
        return dict(self._pending)

    def advance_all(self, dt_ms: int) -> None:
        for motion in self._pending.values():
            motion.advance(dt_ms)
        self._drop_expired()

    def _drop_expired(self) -> None:
        """Drop any motion whose predicted travel time has fully elapsed
        without GameFacade ever reconciling it via reconcile().

        Normally reconcile() removes a motion the same tick its progress hits
        1.0, since duration_ms is derived from the same constants the server
        times its own motion with. But a motion the engine silently rejected
        (or otherwise never resolves - e.g. a jump onto a square another
        piece got to first) never produces a resolving outcome at all, so
        without this it would stay pending forever, permanently frozen at its
        predicted destination pixel - drawn as a stuck ghost duplicate of
        whatever piece is actually resting there.
        """
        expired = [source for source, motion in self._pending.items() if motion.progress >= 1.0]
        for source in expired:
            del self._pending[source]

    def reconcile(self, outcome) -> None:
        """Drop the pending motion this engine outcome resolved, if any - an
        outcome may come from a motion this tracker never tracked, e.g. one
        started directly on the engine."""
        self._pending.pop(outcome.source, None)
