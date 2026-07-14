"""Loads the board background and per-piece sprites out of ui/assets, via Img."""

from vendor.img import Img


def token_to_sprite_code(token: str) -> str:
    """Convert a board token like "wR" to a sprite folder code like "RW".

    Board tokens are (color, kind): 'w'/'b' + an uppercase kind letter.
    Sprite folders are named (kind, COLOR): kind letter + uppercase color letter.
    """
    color, kind = token[0], token[1]
    return kind + color.upper()


class SpriteLoader:
    """Loads (and caches) the images needed to draw one frame of the board."""

    def __init__(self, assets_dir, skin: str, cell_size: int):
        self._assets_dir = assets_dir
        self._skin = skin
        self._cell_size = cell_size
        self._idle_cache: dict[str, Img] = {}

    def load_board(self, rows: int, cols: int) -> Img:
        """Load board.png resized to exactly fit an (rows x cols) board of cells."""
        path = self._assets_dir / "board.png"
        size = (cols * self._cell_size, rows * self._cell_size)
        return Img().read(path, size=size)

    def load_idle_sprite(self, token: str) -> Img:
        """Return a piece's first idle-state frame, sized to one board cell.

        Cached per token so repeated draws don't re-decode the same PNG every frame.
        """
        if token not in self._idle_cache:
            code = token_to_sprite_code(token)
            path = (
                self._assets_dir / self._skin / code / "states" / "idle" / "sprites" / "1.png"
            )
            size = (self._cell_size, self._cell_size)
            self._idle_cache[token] = Img().read(path, size=size)
        return self._idle_cache[token]
