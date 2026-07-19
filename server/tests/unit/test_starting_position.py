from chess_io.board_parser import BoardParser
from model.position import Position
from model.starting_position import STARTING_POSITION


def test_starting_position_parses_into_a_standard_8x8_board():
    board = BoardParser().parse(STARTING_POSITION)
    assert board.rows == 8
    assert board.cols == 8


def test_starting_position_places_each_back_rank_correctly():
    board = BoardParser().parse(STARTING_POSITION)
    assert board.get_piece(Position(0, 0)) == "bR"
    assert board.get_piece(Position(0, 4)) == "bK"
    assert board.get_piece(Position(7, 4)) == "wK"
    assert board.get_piece(Position(7, 7)) == "wR"


def test_starting_position_places_a_full_row_of_pawns_for_each_side():
    board = BoardParser().parse(STARTING_POSITION)
    assert all(board.get_piece(Position(1, col)) == "bP" for col in range(8))
    assert all(board.get_piece(Position(6, col)) == "wP" for col in range(8))
