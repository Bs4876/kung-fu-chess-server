from model.board import Board
from model.game_state import GameState


def make_board():
    return Board([["wK", ".", "bK"]])


def test_initial_game_over_is_false():
    gs = GameState(make_board())
    assert not gs.game_over


def test_board_property_returns_board():
    b = make_board()
    gs = GameState(b)
    assert gs.board is b


def test_game_over_initial_true():
    gs = GameState(make_board(), game_over=True)
    assert gs.game_over
