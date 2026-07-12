from board import EMPTY
from position import Position


def _sliding_destinations(board, src, directions):
    destinations = set()
    for dr, dc in directions:
        r, c = src.row + dr, src.col + dc
        while board.in_bounds(Position(r, c)):
            token = board.get_piece(Position(r, c))
            destinations.add(Position(r, c))
            if token != EMPTY:
                break
            r += dr
            c += dc
    return destinations


def _filter_friendly(destinations, board, piece_color):
    return {p for p in destinations if board.get_piece(p)[0] != piece_color}


def _step_destinations(board, piece, offsets):
    destinations = set()
    for dr, dc in offsets:
        pos = Position(piece.cell.row + dr, piece.cell.col + dc)
        if board.in_bounds(pos):
            token = board.get_piece(pos)
            if token == EMPTY or token[0] != piece.color:
                destinations.add(pos)
    return destinations


class SlidingRule:
    DIRECTIONS = []

    def legal_destinations(self, board, piece):
        return _filter_friendly(_sliding_destinations(board, piece.cell, self.DIRECTIONS), board, piece.color)


class RookRule(SlidingRule):
    DIRECTIONS = [(0, 1), (0, -1), (1, 0), (-1, 0)]


class BishopRule(SlidingRule):
    DIRECTIONS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


class QueenRule(SlidingRule):
    DIRECTIONS = [(0, 1), (0, -1), (1, 0), (-1, 0),
                  (1, 1), (1, -1), (-1, 1), (-1, -1)]


class KnightRule:
    JUMPS = [(2, 1), (2, -1), (-2, 1), (-2, -1),
             (1, 2), (1, -2), (-1, 2), (-1, -2)]

    def legal_destinations(self, board, piece):
        return _step_destinations(board, piece, self.JUMPS)


class KingRule:
    DIRECTIONS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]

    def legal_destinations(self, board, piece):
        return _step_destinations(board, piece, self.DIRECTIONS)


class PawnRule:
    def legal_destinations(self, board, piece):
        forward = -1 if piece.color == "w" else 1
        start_row = board.rows - 2 if piece.color == "w" else 1
        destinations = set()
        src = piece.cell

        fwd = Position(src.row + forward, src.col)
        if board.in_bounds(fwd) and board.get_piece(fwd) == EMPTY:
            destinations.add(fwd)
            double = Position(src.row + 2 * forward, src.col)
            if src.row == start_row and board.in_bounds(double) and board.get_piece(double) == EMPTY:
                destinations.add(double)

        for dc in (-1, 1):
            diag = Position(src.row + forward, src.col + dc)
            if board.in_bounds(diag):
                token = board.get_piece(diag)
                if token != EMPTY and token[0] != piece.color:
                    destinations.add(diag)

        return destinations


RULES = {
    "rook": RookRule(),
    "bishop": BishopRule(),
    "queen": QueenRule(),
    "knight": KnightRule(),
    "king": KingRule(),
    "pawn": PawnRule(),
}


def legal_destinations(board, piece):
    return RULES[piece.kind].legal_destinations(board, piece)
