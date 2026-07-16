"""Wraps GameEngine to add client-side motion prediction and event notifications.

The engine only ever shows a piece "resting at source" or "resting at
destination" (see server/realtime/motion.py - mid-flight positions exist only
for the arbiter's own collision math and are never exposed via GameSnapshot).
Smooth in-flight animation is therefore a client-side prediction, advanced
every tick independently of the engine's own timing - see state/motion_tracker.py.

The engine is the one that identifies each outcome (arrival/capture/halt/
promotion), so it's also the one that publishes it - GameFacade subscribes to
the engine instead of pulling wait()'s return value, and forwards each one
(reconciled against pending-motion bookkeeping in state/motion_tracker.py, then
translated via state/outcome_translator.py into the state/game_events.py types
log/score panels subscribe to) on its own event stream. GameFacade itself just
coordinates: the engine, the tracker, and the event stream.
"""

from config import JUMP_TRAVEL_TIME, MOVE_TRAVEL_TIME_PER_CELL
from model.board import EMPTY

from state.game_events import GameOver, MoveAccepted, MoveRejected
from state.motion_tracker import MotionTracker
from state.observer import Subject
from state.outcome_translator import translate


def _chebyshev_distance(a, b) -> int:
    return max(abs(a.row - b.row), abs(a.col - b.col))


class GameFacade:
    """Adds pending-motion bookkeeping and an event stream on top of a real
    GameEngine.

    Exposes the same request_move/snapshot shape server's Controller already
    expects, so Controller can point at this instead of the raw engine unmodified.
    """

    def __init__(self, engine):
        self._engine = engine
        self._motions = MotionTracker()
        self._events = Subject()
        self._elapsed_ms: int = 0
        self._engine.subscribe(self._on_engine_outcome)

    def _on_engine_outcome(self, outcome) -> None:
        """The engine calls this the instant it resolves an outcome (mid-wait,
        not just once wait() returns); reconcile bookkeeping and forward the
        translated event right away."""
        self._motions.reconcile(outcome)
        self._events.publish(translate(outcome))

    @property
    def game_over(self) -> bool:
        return self._engine.game_over

    def subscribe(self, callback) -> None:
        """Register callback(event) to be notified of MoveAccepted, MoveRejected,
        PieceArrived, PieceCaptured, PieceHalted, Promotion, and GameOver events."""
        self._events.subscribe(callback)

    def snapshot(self):
        return self._engine.snapshot()

    def pending_motions(self) -> dict:
        """Read-only view of in-flight motions, keyed by their source cell."""
        return self._motions.pending()

    def request_move(self, source, destination):
        result = self._engine.request_move(source, destination)
        if result.is_accepted:
            snapshot = self._engine.snapshot()
            token = snapshot.get_piece(source)
            duration_ms = _chebyshev_distance(source, destination) * MOVE_TRAVEL_TIME_PER_CELL
            self._motions.start(source, destination, token, duration_ms, is_jump=False)
            self._events.publish(MoveAccepted(source, destination, token, self._elapsed_ms))
        else:
            self._events.publish(MoveRejected(source, destination, result.reason))
        return result

    def request_jump(self, source, destination) -> None:
        snapshot = self._engine.snapshot()
        token = snapshot.get_piece(source)
        self._engine.request_jump(source, destination)
        # request_jump has no return value to confirm acceptance; a jump silently
        # ignored by the engine (game over, already moving, out of bounds) just
        # never produces a resolution event from wait() later, so it stays
        # pending harmlessly until this same source is used again.
        if token != EMPTY:
            self._motions.start(source, destination, token, JUMP_TRAVEL_TIME, is_jump=True)

    def tick(self, dt_ms: int):
        """Advance the engine's real clock - resolved outcomes get published to
        _on_engine_outcome synchronously, inside this call - and advance
        predicted motions for animation. Returns the fresh snapshot."""
        self._elapsed_ms += dt_ms
        game_over_before = self._engine.game_over
        self._engine.wait(dt_ms)
        curr_snapshot = self._engine.snapshot()

        self._motions.advance_all(dt_ms)

        if curr_snapshot.game_over and not game_over_before:
            self._events.publish(GameOver())
        return curr_snapshot
