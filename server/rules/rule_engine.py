from model.board import EMPTY
from model.piece import Piece
from model.position import Position
from rules.piece_rules import legal_destinations as _piece_legal_destinations


class MoveValidation:
    def __init__(self, is_valid: bool, reason: str):
        self.is_valid = is_valid
        self.reason = reason


OK = MoveValidation(True, "ok")


class RuleEngine:
    def validate_move(self, board, source: Position, destination: Position) -> MoveValidation:
        if not board.in_bounds(source) or not board.in_bounds(destination):
            return MoveValidation(False, "outside_board")

        piece = board.get_piece(source)
        if piece == EMPTY:
            return MoveValidation(False, "empty_source")

        target = board.get_piece(destination)
        if target != EMPTY and target[0] == piece[0]:
            return MoveValidation(False, "friendly_destination")

        if destination not in self.legal_destinations(board, source):
            return MoveValidation(False, "illegal_piece_move")

        return OK

    def legal_destinations(self, board, source: Position) -> set:
        """All destinations source's piece could legally move to right now -
        movement pattern + board bounds + not landing on a friendly piece,
        the same rule validate_move checks a single destination against. For
        UI move-hint highlighting; empty (or out of bounds) if there's no
        piece at source to move at all."""
        if not board.in_bounds(source):
            return set()
        piece = board.get_piece(source)
        if piece == EMPTY:
            return set()
        return _piece_legal_destinations(board, _token_to_piece(piece, source))


def _token_to_piece(token: str, pos: Position):
    return Piece.from_token(token, pos)


