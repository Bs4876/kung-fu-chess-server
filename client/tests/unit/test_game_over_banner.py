from state.game_events import GameOver, MoveAccepted
from ui_components.game_over_banner import GameOverBanner


def test_starts_not_game_over():
    assert not GameOverBanner().is_game_over


def test_game_over_event_flips_the_flag():
    banner = GameOverBanner()
    banner.handle_event(GameOver())
    assert banner.is_game_over


def test_other_events_do_not_flip_the_flag():
    banner = GameOverBanner()
    banner.handle_event(MoveAccepted(source=None, destination=None, token="wR"))
    assert not banner.is_game_over
