from unittest.mock import MagicMock
from model.board import Board, EMPTY
from model.position import Position
from input.board_mapper import BoardMapper
from input.controller import Controller
from engine.game_engine import GameSnapshot


def setup(rows=("wR . .",)):
    board = Board([[c for c in row.split()] for row in rows])
    engine = MagicMock()
    pieces = {}
    for r, row in enumerate(rows):
        for c, token in enumerate(row.split()):
            if token != EMPTY:
                pieces[(r, c)] = token
    engine.snapshot.return_value = GameSnapshot(
        board=Board([[c for c in row.split()] for row in rows]), game_over=False
    )
    mapper = BoardMapper(rows=board.rows, cols=board.cols)
    controller = Controller(engine, mapper)
    return controller, engine, board


def test_first_click_on_piece_sets_selection():
    ctrl, engine, _ = setup()
    ctrl.click(50, 50)
    engine.request_move.assert_not_called()


def test_first_click_on_empty_does_nothing():
    ctrl, engine, _ = setup()
    ctrl.click(150, 50)
    engine.request_move.assert_not_called()


def test_second_click_sends_correct_source_and_destination():
    ctrl, engine, _ = setup()
    ctrl.click(50, 50)
    ctrl.click(250, 50)
    engine.request_move.assert_called_once_with(Position(0, 0), Position(0, 2))


def test_second_click_clears_selection():
    ctrl, engine, _ = setup()
    ctrl.click(50, 50)
    ctrl.click(250, 50)
    engine.request_move.reset_mock()
    ctrl.click(250, 50)
    engine.request_move.assert_not_called()


def test_click_outside_without_selection_does_nothing():
    ctrl, engine, _ = setup()
    ctrl.click(999, 999)
    engine.request_move.assert_not_called()


def test_click_outside_with_selection_clears_selection():
    ctrl, engine, _ = setup()
    ctrl.click(50, 50)
    ctrl.click(999, 999)
    ctrl.click(250, 50)
    engine.request_move.assert_not_called()


def test_clicking_friendly_piece_replaces_selection():
    ctrl, engine, _ = setup(rows=("wR . wK",))
    ctrl.click(50, 50)   # select wR
    ctrl.click(250, 50)  # select wK instead
    engine.request_move.assert_not_called()


def test_second_click_clears_selection_even_on_invalid_move():
    ctrl, engine, _ = setup()
    engine.request_move.return_value = MagicMock(is_accepted=False, reason="illegal_piece_move")
    ctrl.click(50, 50)
    ctrl.click(150, 50)  # empty cell — sends move
    engine.request_move.assert_called_once()
    engine.request_move.reset_mock()
    ctrl.click(150, 50)
    engine.request_move.assert_not_called()
