from model.position import Position
from state.game_events import MoveAccepted
from ui_components.moves_log_panel import MovesLogPanel


def test_white_move_is_logged_with_cell_names_and_timestamp():
    panel = MovesLogPanel()
    panel.handle_event(MoveAccepted(source=Position(6, 4), destination=Position(4, 4), token="wP", timestamp_ms=3200))
    assert panel.white_lines() == ["P e2-e4 [3.2s]"]
    assert panel.black_lines() == []


def test_black_move_is_logged_separately_from_white():
    panel = MovesLogPanel()
    panel.handle_event(MoveAccepted(source=Position(1, 4), destination=Position(3, 4), token="bP", timestamp_ms=2100))
    assert panel.black_lines() == ["P e7-e5 [2.1s]"]
    assert panel.white_lines() == []


def test_each_side_s_lines_are_most_recent_first():
    panel = MovesLogPanel()
    panel.handle_event(MoveAccepted(source=Position(6, 4), destination=Position(4, 4), token="wP", timestamp_ms=1000))
    panel.handle_event(MoveAccepted(source=Position(6, 3), destination=Position(4, 3), token="wP", timestamp_ms=5000))
    assert panel.white_lines() == ["P d2-d4 [5.0s]", "P e2-e4 [1.0s]"]


def test_starts_with_no_lines_for_either_side():
    panel = MovesLogPanel()
    assert panel.white_lines() == []
    assert panel.black_lines() == []
