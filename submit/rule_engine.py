from board import EMPTY
from piece import Piece
from position import Position
from piece_rules import legal_destinations


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

        if destination not in legal_destinations(board, Piece.from_token(piece, source)):
            return MoveValidation(False, "illegal_piece_move")

        return OK
