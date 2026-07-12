from model.board import Board, EMPTY
from model.piece import Piece
from model.position import Position
from rules.piece_rules import RookRule, BishopRule, QueenRule, KnightRule, KingRule, PawnRule


def piece(kind, color, row, col):
    return Piece(color=color, kind=kind, cell=Position(row, col))


def board_from(rows):
    return Board([[c for c in row.split()] for row in rows])


# --- Rook ---

def test_rook_slides_along_row_and_col():
    b = board_from(["wR . .", ". . .", ". . ."])
    dests = RookRule().legal_destinations(b, piece("rook", "w", 0, 0))
    assert Position(0, 1) in dests
    assert Position(0, 2) in dests
    assert Position(1, 0) in dests
    assert Position(2, 0) in dests


def test_rook_blocked_by_friendly():
    b = board_from(["wR wP .", ". . .", ". . ."])
    dests = RookRule().legal_destinations(b, piece("rook", "w", 0, 0))
    assert Position(0, 1) not in dests
    assert Position(0, 2) not in dests


def test_rook_captures_enemy_but_not_beyond():
    b = board_from(["wR . bP", ". . .", ". . ."])
    dests = RookRule().legal_destinations(b, piece("rook", "w", 0, 0))
    assert Position(0, 2) in dests
    assert Position(0, 1) in dests  # empty square before enemy


def test_rook_cannot_move_diagonally():
    b = board_from(["wR . .", ". . .", ". . ."])
    dests = RookRule().legal_destinations(b, piece("rook", "w", 0, 0))
    assert Position(1, 1) not in dests


# --- Bishop ---

def test_bishop_slides_diagonally():
    b = board_from(["wB . .", ". . .", ". . ."])
    dests = BishopRule().legal_destinations(b, piece("bishop", "w", 0, 0))
    assert Position(1, 1) in dests
    assert Position(2, 2) in dests


def test_bishop_cannot_move_straight():
    b = board_from(["wB . .", ". . .", ". . ."])
    dests = BishopRule().legal_destinations(b, piece("bishop", "w", 0, 0))
    assert Position(0, 1) not in dests
    assert Position(1, 0) not in dests


# --- Queen ---

def test_queen_combines_rook_and_bishop():
    b = board_from(["wQ . .", ". . .", ". . ."])
    dests = QueenRule().legal_destinations(b, piece("queen", "w", 0, 0))
    assert Position(0, 2) in dests  # rook
    assert Position(2, 0) in dests  # rook
    assert Position(2, 2) in dests  # bishop


# --- Knight ---

def test_knight_jumps_over_blockers():
    b = board_from(["wN wP wP", "wP wP wP", ". . wP", ". wP ."])
    dests = KnightRule().legal_destinations(b, piece("knight", "w", 0, 0))
    assert Position(2, 1) in dests
    assert Position(1, 2) not in dests  # friendly


def test_knight_l_shape_only():
    b = board_from(["wN . . .", ". . . .", ". . . .", ". . . ."])
    dests = KnightRule().legal_destinations(b, piece("knight", "w", 0, 0))
    assert Position(2, 1) in dests
    assert Position(1, 2) in dests
    assert Position(1, 1) not in dests


# --- King ---

def test_king_moves_one_square():
    b = board_from(["wK . .", ". . .", ". . ."])
    dests = KingRule().legal_destinations(b, piece("king", "w", 0, 0))
    assert Position(0, 1) in dests
    assert Position(1, 0) in dests
    assert Position(1, 1) in dests
    assert Position(0, 2) not in dests


def test_king_blocked_by_friendly():
    b = board_from(["wK wP .", "wP . .", ". . ."])
    dests = KingRule().legal_destinations(b, piece("king", "w", 0, 0))
    assert Position(0, 1) not in dests
    assert Position(1, 0) not in dests


# --- Pawn ---

def test_white_pawn_moves_up():
    b = board_from([". . .", "wP . .", ". . ."])
    dests = PawnRule().legal_destinations(b, piece("pawn", "w", 1, 0))
    assert Position(0, 0) in dests
    assert Position(2, 0) not in dests


def test_black_pawn_moves_down():
    b = board_from([". bP .", ". . .", ". . ."])
    dests = PawnRule().legal_destinations(b, piece("pawn", "b", 0, 1))
    assert Position(1, 1) in dests
    assert Position(0, 1) not in dests


def test_pawn_captures_diagonally():
    b = board_from([". bP .", "wP . .", ". . ."])
    dests = PawnRule().legal_destinations(b, piece("pawn", "w", 1, 0))
    assert Position(0, 1) in dests


def test_pawn_blocked_straight():
    b = board_from(["bP . .", "wP . .", ". . ."])
    dests = PawnRule().legal_destinations(b, piece("pawn", "w", 1, 0))
    assert Position(0, 0) not in dests


def test_white_pawn_double_move_from_start_row():
    b = board_from([". . .", ". . .", ". . .", ". wP .", ". . ."])
    dests = PawnRule().legal_destinations(b, piece("pawn", "w", 3, 1))
    assert Position(1, 1) in dests


def test_black_pawn_double_move_from_start_row():
    b = board_from([". . .", ". bP .", ". . .", ". . .", ". . ."])
    dests = PawnRule().legal_destinations(b, piece("pawn", "b", 1, 1))
    assert Position(3, 1) in dests


def test_white_pawn_double_move_blocked_by_piece_directly_ahead():
    b = board_from([". . .", ". . .", ". bR .", ". wP .", ". . ."])
    dests = PawnRule().legal_destinations(b, piece("pawn", "w", 3, 1))
    assert Position(1, 1) not in dests


def test_white_pawn_double_move_not_allowed_outside_start_row():
    b = board_from([". . .", ". . .", ". wP .", ". . .", ". . ."])
    dests = PawnRule().legal_destinations(b, piece("pawn", "w", 2, 1))
    assert Position(0, 1) not in dests


def test_legal_destinations_dispatch():
    from rules.piece_rules import legal_destinations
    b = board_from(["wR . .", ". . .", ". . ."])
    dests = legal_destinations(b, piece("rook", "w", 0, 0))
    assert Position(0, 1) in dests
