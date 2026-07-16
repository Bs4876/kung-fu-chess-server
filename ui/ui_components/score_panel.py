"""Subscribes to PieceCaptured events and tallies each side's score by piece value.

Score is fully derived here - the engine has no concept of scoring at all, but
the piece-value table itself is chess domain data, so it lives on server's
model package (model/piece_values.py) rather than in ui_config.py.
"""

from model.piece_values import PIECE_VALUES

from state.game_events import PieceCaptured


class ScorePanel:
    """score = sum of captured enemy pieces' values (PIECE_VALUES)."""

    def __init__(self):
        self.white_score = 0
        self.black_score = 0

    def handle_event(self, event) -> None:
        # A mid-flight kill (by_token is None) has no identifiable capturer to
        # credit, so it's left out of both sides' tally rather than guessed at.
        if isinstance(event, PieceCaptured) and event.by_token is not None:
            self._credit(event.by_token[0], event.captured_token[1])

    def _credit(self, capturing_color: str, captured_type: str) -> None:
        value = PIECE_VALUES[captured_type]
        if capturing_color == "w":
            self.white_score += value
        else:
            self.black_score += value

    def summary(self) -> str:
        return f"White: {self.white_score}   Black: {self.black_score}"
