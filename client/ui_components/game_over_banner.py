"""Tracks whether the game has ended, for a banner overlay drawn on the board."""

from state.game_events import GameOver


class GameOverBanner:
    def __init__(self):
        self.is_game_over = False

    def handle_event(self, event) -> None:
        if isinstance(event, GameOver):
            self.is_game_over = True
