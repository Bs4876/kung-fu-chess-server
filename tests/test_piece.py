import pytest

from model.piece import Piece
from model.position import Position


def test_piece_equality_and_hash():
    p1 = Piece(color="w", kind="rook", cell=Position(0, 0))
    p2 = Piece(color="w", kind="rook", cell=Position(0, 0))
    assert p1 == p2
    assert hash(p1) == hash(p2)


def test_piece_repr_includes_kind_and_position():
    p = Piece(color="b", kind="knight", cell=Position(3, 4))
    assert "knight" in repr(p)
    assert "Position(3, 4)" in repr(p)


def test_piece_token_property():
    p = Piece(color="w", kind="queen", cell=Position(1, 2))
    assert p.token == "wQ"
    assert p.symbol == "Q"


def test_piece_from_token_constructs_correct_piece():
    p = Piece.from_token("bP", Position(5, 5), state="moving")
    assert p.color == "b"
    assert p.kind == "pawn"
    assert p.cell == Position(5, 5)
    assert p.state == "moving"
    assert p.id == "bP@5,5"


def test_piece_invalid_token_raises():
    with pytest.raises(ValueError):
        Piece.from_token("xZ", Position(0, 0))


def test_piece_invalid_state_raises():
    with pytest.raises(ValueError):
        Piece(color="w", kind="king", cell=Position(0, 0), state="flying")
