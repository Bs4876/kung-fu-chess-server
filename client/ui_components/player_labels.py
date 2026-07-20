"""Static player-name labels.

Display-only - the engine has no concept of player identity at all. Real
per-player names are a multiplayer concern for later; for now this just gives
the sidebar a place to show them instead of hardcoding "White"/"Black" text
wherever a name is needed.
"""


class PlayerLabels:
    def __init__(self, white_name: str = "White", black_name: str = "Black"):
        self.white_name = white_name
        self.black_name = black_name
