from dataclasses import dataclass

from model.board import Board, EMPTY
from model.position import Position
from rules.rule_engine import RuleEngine
from realtime.real_time_arbiter import RealTimeArbiter
from realtime.motion import CollisionEvent
from config import MOVE_COOLDOWN_MS, JUMP_COOLDOWN_MS
from engine.observer import Subject


class MoveResult:
    def __init__(self, is_accepted: bool, reason: str):
        """Outcome of a move request: whether it was accepted, and why/why not."""
        self.is_accepted = is_accepted
        self.reason = reason


@dataclass
class Arrived:
    """A piece completed its travel onto a previously-empty destination cell."""

    source: Position
    destination: Position
    token: str
    is_jump: bool = False


@dataclass
class Captured:
    """An enemy piece is gone: either on arrival (by_token is its capturer),
    or destroyed mid-flight/airborne (by_token is None - no single capturer)."""

    source: Position
    position: Position
    captured_token: str
    by_token: str | None
    is_jump: bool = False


@dataclass
class Halted:
    """A piece stopped short of its intended destination - a mid-flight
    same-color collision - resting at some other cell instead."""

    source: Position
    resting_at: Position
    token: str
    is_jump: bool = False


@dataclass
class Promoted:
    source: Position
    position: Position
    from_token: str
    to_token: str
    is_jump: bool = False


class GameSnapshot:
    def __init__(self, board: Board, game_over: bool):
        """Read-only view of engine state at a point in time, safe to hand to callers."""
        self._board = board
        self.game_over = game_over
        self.rows = board.rows
        self.cols = board.cols

    def get_piece(self, pos) -> str:
        """Return the token at pos ("." if empty)."""
        return self._board.get_piece(pos)

    @property
    def board(self):
        """The underlying board at the time the snapshot was taken."""
        return self._board


class GameEngine:
    def __init__(self, board: Board):
        """Drive a game on board: validates moves, times real-time motion, applies results."""
        self._board = board
        self._rule_engine = RuleEngine()
        self._arbiter = RealTimeArbiter()
        self._game_over = False
        self._events = Subject()

    @property
    def game_over(self) -> bool:
        """Whether a king has been captured and the game has ended."""
        return self._game_over

    def subscribe(self, callback) -> None:
        """Register callback(outcome) to be notified of each Arrived/Captured/
        Halted/Promoted the instant wait() resolves it - the engine is the one
        that identifies the outcome, so it's also the one that publishes it."""
        self._events.subscribe(callback)

    def request_jump(self, source: Position, destination: Position) -> None:
        """Start a jump from source to destination, bypassing normal move legality.

        Ignored if the game is over, the piece is already moving, still on
        cooldown from its last arrival, or destination is out of bounds. Unlike
        a move, a jump that lands on an occupied square kills whatever is there
        even if it's the same color as the jumping piece.
        """
        if self._game_over or self._arbiter.has_active_motion_for(source) or self._arbiter.is_on_cooldown(source):
            return
        if not self._board.in_bounds(destination):
            return
        token = self._board.get_piece(source)
        if token == EMPTY:
            return
        self._arbiter.start_jump(token, source, destination)

    def request_move(self, source: Position, destination: Position) -> MoveResult:
        """Validate and, if legal, start real-time motion of the piece from source to destination."""
        if self._game_over:
            return MoveResult(False, "game_over")
        if self._arbiter.has_active_motion_for(source):
            return MoveResult(False, "motion_in_progress")
        if self._arbiter.is_on_cooldown(source):
            return MoveResult(False, "cooldown")
        validation = self._rule_engine.validate_move(self._board, source, destination)
        if not validation.is_valid:
            return MoveResult(False, validation.reason)
        token = self._board.get_piece(source)
        self._arbiter.start_motion(token, source, destination)
        return MoveResult(True, "ok")

    def legal_destinations(self, source: Position) -> set:
        """All destinations source's piece could legally move to right now,
        for UI move-hint highlighting - not itself a move request, so it
        doesn't check game_over/motion/cooldown the way request_move does."""
        return self._rule_engine.legal_destinations(self._board, source)

    def wait(self, ms: int) -> list:
        """Advance real-time motion by ms, apply any collisions/arrivals that
        occur, and return the domain events (Arrived/Captured/Halted/Promoted)
        each one actually resolved to - in the same order they were resolved.
        Each one is also published to subscribe()'d callbacks as soon as it's
        resolved, not just returned; the list return is kept for callers (and
        tests) that want the whole batch at once.

        This is the single point where "what happened" is known for certain
        (capture vs. halt vs. stale-target cancellation, etc.); returning it
        here means callers never need to re-derive it later by diffing board
        snapshots before/after.
        """
        events = self._arbiter.advance_time(ms)
        outcomes = []
        for event in events:
            if isinstance(event, CollisionEvent):
                outcome = self._apply_collision(event)
            else:
                outcome = self._apply_arrival(event)
            if outcome is not None:
                outcomes.append(outcome)
                self._events.publish(outcome)
        return outcomes

    def _apply_collision(self, event: CollisionEvent):
        """Remove a piece that collided mid-motion; ending the game if it was a king."""
        if self._board.get_piece(event.pos) != event.piece_token:
            return None
        self._board.replace_piece(event.pos, EMPTY)
        if event.piece_token[1] == "K":
            self._game_over = True
        return Captured(source=event.pos, position=event.pos, captured_token=event.piece_token, by_token=None)

    def snapshot(self) -> GameSnapshot:
        """Capture the current board and game-over state as an immutable GameSnapshot."""
        return GameSnapshot(self._board, self._game_over)

    def _apply_arrival(self, event):
        """Apply a piece's arrival at its destination: capture, promotion, or
        halt short of it if a friendly piece already claimed the square.

        Evaluated purely against the board as it is right now - not against
        whatever was there when the move was first requested. A real-time
        race for the same square is resolved the same way regardless of
        which piece's move happens to finish processing first: later arrival
        captures an enemy already there, and is blocked by (backs off from) a
        friendly one, exactly like the mid-flight near-miss case below.
        """
        src, dst = event.src, event.dst
        if self._board.get_piece(src) != event.piece_token:
            return None
        if src == dst:
            # A move redirected/halted back to its own source never actually
            # went anywhere - no landing, no cooldown. A jump requested onto
            # its own square (a deliberate in-place "dodge") is a real,
            # intentional action instead: it still deserves its cooldown, but
            # skips every other landing check below (there's nothing at dst
            # to capture/promote/replace - dst *is* the jumping piece itself).
            if event.is_jump:
                self._arbiter.start_cooldown(dst, JUMP_COOLDOWN_MS)
                return Arrived(source=src, destination=dst, token=event.piece_token, is_jump=True)
            return None
        target = self._board.get_piece(dst)
        if target != EMPTY and target[0] == event.piece_token[0] and not event.is_jump:
            return self._halt_before_friendly(event.piece_token, src, dst)
        airborne = event.airborne_dsts
        if dst in airborne and airborne[dst][0] != event.piece_token[0]:
            self._board.replace_piece(src, EMPTY)
            return Captured(source=src, position=src, captured_token=event.piece_token, by_token=None,
                             is_jump=event.is_jump)
        if target != EMPTY and target[1] == "K":
            self._game_over = True
        token = event.piece_token
        promoted = token[1] == "P" and (dst.row == 0 or dst.row == self._board.rows - 1)
        if promoted:
            token = token[0] + "Q"
        self._board.move_piece(src, dst)
        if token != event.piece_token:
            self._board.replace_piece(dst, token)
        cooldown_ms = JUMP_COOLDOWN_MS if event.is_jump else MOVE_COOLDOWN_MS
        self._arbiter.start_cooldown(dst, cooldown_ms)

        if event.is_halt:
            return Halted(source=src, resting_at=dst, token=event.piece_token, is_jump=event.is_jump)
        if promoted:
            return Promoted(source=src, position=dst, from_token=event.piece_token, to_token=token,
                             is_jump=event.is_jump)
        if target != EMPTY:
            return Captured(source=src, position=dst, captured_token=target, by_token=event.piece_token,
                             is_jump=event.is_jump)
        return Arrived(source=src, destination=dst, token=event.piece_token, is_jump=event.is_jump)

    def _halt_before_friendly(self, token: str, src: Position, dst: Position):
        """Back off to the last cell before dst, the same way a mid-flight
        same-color near-miss does - unless there's no meaningful cell to back
        off to (an adjacent-cell move, or a knight-shaped move with no path
        at all), in which case this just cancels."""
        backoff = self._cell_before(src, dst)
        if backoff is None:
            return None
        self._board.move_piece(src, backoff)
        self._arbiter.start_cooldown(backoff, MOVE_COOLDOWN_MS)
        return Halted(source=src, resting_at=backoff, token=token)

    @staticmethod
    def _cell_before(src: Position, dst: Position) -> Position | None:
        dr, dc = dst.row - src.row, dst.col - src.col
        distance = max(abs(dr), abs(dc))
        if distance <= 1 or not (dr == 0 or dc == 0 or abs(dr) == abs(dc)):
            return None
        step_r, step_c = (dr > 0) - (dr < 0), (dc > 0) - (dc < 0)
        return Position(src.row + step_r * (distance - 1), src.col + step_c * (distance - 1))
