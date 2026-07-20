from model.position import Position
from state.game_events import MoveAccepted, PieceCaptured
from ui_components.score_panel import ScorePanel


def test_starts_at_zero_zero():
    panel = ScorePanel()
    assert panel.white_score == 0
    assert panel.black_score == 0
    assert panel.summary() == "White: 0   Black: 0"


def test_white_capture_credits_white_with_the_captured_piece_s_value():
    panel = ScorePanel()
    panel.handle_event(PieceCaptured(position=Position(4, 3), captured_token="bP", by_token="wR"))
    assert panel.white_score == 1
    assert panel.black_score == 0


def test_black_capture_credits_black_with_the_captured_piece_s_value():
    panel = ScorePanel()
    panel.handle_event(PieceCaptured(position=Position(4, 3), captured_token="wP", by_token="bR"))
    assert panel.black_score == 1
    assert panel.white_score == 0


def test_capturing_a_queen_credits_nine_points():
    panel = ScorePanel()
    panel.handle_event(PieceCaptured(position=Position(4, 3), captured_token="bQ", by_token="wR"))
    assert panel.white_score == 9


def test_capturing_a_rook_credits_five_points():
    panel = ScorePanel()
    panel.handle_event(PieceCaptured(position=Position(4, 3), captured_token="bR", by_token="wQ"))
    assert panel.white_score == 5


def test_capturing_a_knight_or_bishop_credits_three_points():
    panel = ScorePanel()
    panel.handle_event(PieceCaptured(position=Position(4, 3), captured_token="bN", by_token="wR"))
    panel.handle_event(PieceCaptured(position=Position(2, 1), captured_token="bB", by_token="wR"))
    assert panel.white_score == 6


def test_capturing_a_king_credits_zero_points():
    panel = ScorePanel()
    panel.handle_event(PieceCaptured(position=Position(4, 3), captured_token="bK", by_token="wR"))
    assert panel.white_score == 0


def test_capture_with_unknown_capturer_is_not_credited_to_either_side():
    panel = ScorePanel()
    panel.handle_event(PieceCaptured(position=Position(4, 3), captured_token="wB", by_token=None))
    assert panel.white_score == 0
    assert panel.black_score == 0


def test_non_capture_events_are_ignored():
    panel = ScorePanel()
    panel.handle_event(MoveAccepted(source=Position(0, 0), destination=Position(0, 1), token="wR"))
    assert panel.white_score == 0
    assert panel.black_score == 0
