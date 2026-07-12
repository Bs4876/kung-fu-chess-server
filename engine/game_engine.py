from model.board import Board, EMPTY
from model.position import Position
from rules.rule_engine import RuleEngine
from realtime.real_time_arbiter import RealTimeArbiter
from realtime.motion import CollisionEvent


class MoveResult:
    def __init__(self, is_accepted: bool, reason: str):
        self.is_accepted = is_accepted
        self.reason = reason


class GameSnapshot:
    def __init__(self, board: Board, game_over: bool):
        self._board = board
        self.game_over = game_over
        self.rows = board.rows
        self.cols = board.cols

    def get_piece(self, pos) -> str:
        return self._board.get_piece(pos)

    @property
    def board(self):
        return self._board


class GameEngine:
    def __init__(self, board: Board):
        self._board = board
        self._rule_engine = RuleEngine()
        self._arbiter = RealTimeArbiter()
        self._game_over = False

    @property
    def game_over(self) -> bool:
        return self._game_over

    def request_jump(self, pos: Position) -> None:
        if self._game_over or self._arbiter.has_active_motion_for(pos):
            return
        token = self._board.get_piece(pos)
        if token == EMPTY:
            return
        self._arbiter.start_jump(token, pos)

    def request_move(self, source: Position, destination: Position) -> MoveResult:
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
        events = self._arbiter.advance_time(ms)
        for event in events:
            if isinstance(event, CollisionEvent):
                self._apply_collision(event)
            else:
                self._apply_arrival(event)

    def _apply_collision(self, event: CollisionEvent) -> None:
        if self._board.get_piece(event.pos) != event.piece_token:
            return
        self._board.replace_piece(event.pos, EMPTY)
        if event.piece_token[1] == "K":
            self._game_over = True

    def snapshot(self) -> GameSnapshot:
        return GameSnapshot(self._board, self._game_over)

    def _apply_arrival(self, event) -> None:
        src, dst = event.src, event.dst
        if self._board.get_piece(src) != event.piece_token:
            return
        if event.expected_target is not None and self._board.get_piece(dst) != event.expected_target:
            return
        target = self._board.get_piece(dst)
        if target != EMPTY and target[0] == event.piece_token[0]:
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
