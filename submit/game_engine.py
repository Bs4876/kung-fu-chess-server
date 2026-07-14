from board import Board, EMPTY
from position import Position
from rule_engine import RuleEngine
from real_time_arbiter import RealTimeArbiter
from motion import CollisionEvent


class MoveResult:
    def __init__(self, is_accepted: bool, reason: str):
        """Outcome of a move request: whether it was accepted, and why/why not."""
        self.is_accepted = is_accepted
        self.reason = reason


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

    @property
    def game_over(self) -> bool:
        """Whether a king has been captured and the game has ended."""
        return self._game_over

    def request_jump(self, source: Position, destination: Position) -> None:
        """Start a jump from source to destination, bypassing normal move legality.

        Ignored if the game is over, the piece is already moving, or destination is
        out of bounds. Unlike a move, a jump that lands on an occupied square kills
        whatever is there even if it's the same color as the jumping piece.
        """
        if self._game_over or self._arbiter.has_active_motion_for(source):
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
        validation = self._rule_engine.validate_move(self._board, source, destination)
        if not validation.is_valid:
            return MoveResult(False, validation.reason)
        token = self._board.get_piece(source)
        expected_target = self._board.get_piece(destination)
        self._arbiter.start_motion(token, source, destination, expected_target=expected_target)
        return MoveResult(True, "ok")

    def wait(self, ms: int) -> None:
        """Advance real-time motion by ms and apply any collisions/arrivals that occur."""
        events = self._arbiter.advance_time(ms)
        for event in events:
            if isinstance(event, CollisionEvent):
                self._apply_collision(event)
            else:
                self._apply_arrival(event)

    def _apply_collision(self, event: CollisionEvent) -> None:
        """Remove a piece that collided mid-motion; ending the game if it was a king."""
        if self._board.get_piece(event.pos) != event.piece_token:
            return
        self._board.replace_piece(event.pos, EMPTY)
        if event.piece_token[1] == "K":
            self._game_over = True

    def snapshot(self) -> GameSnapshot:
        """Capture the current board and game-over state as an immutable GameSnapshot."""
        return GameSnapshot(self._board, self._game_over)

    def _apply_arrival(self, event) -> None:
        """Apply a piece's arrival at its destination: capture, promotion, or cancel if preempted."""
        src, dst = event.src, event.dst
        if self._board.get_piece(src) != event.piece_token:
            return
        if event.expected_target is not None and self._board.get_piece(dst) != event.expected_target:
            return
        if src == dst:
            return  # returned to where it already stood; never a real landing
        target = self._board.get_piece(dst)
        if target != EMPTY and target[0] == event.piece_token[0] and not event.is_jump:
            return
        airborne = event.airborne_dsts
        if dst in airborne and airborne[dst][0] != event.piece_token[0]:
            self._board.replace_piece(src, EMPTY)
            return
        if target != EMPTY and target[1] == "K":
            self._game_over = True
        token = event.piece_token
        if token[1] == "P" and (dst.row == 0 or dst.row == self._board.rows - 1):
            token = token[0] + "Q"
        self._board.move_piece(src, dst)
        if token != event.piece_token:
            self._board.replace_piece(dst, token)
