from model.piece import Piece
from model.piece_values import PIECE_VALUES
from model.position import Position


def test_piece_values_has_an_entry_for_every_known_piece_kind():
    # Cross-checked against Piece's own token round-trip so a new piece kind
    # added there can't silently be left unscored here.
    known_symbols = {Piece.from_token(f"w{kind}", Position(0, 0)).symbol for kind in "RNBQKP"}
    assert known_symbols == set(PIECE_VALUES)


def test_piece_values_match_standard_chess_material_values():
    assert PIECE_VALUES == {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0}
