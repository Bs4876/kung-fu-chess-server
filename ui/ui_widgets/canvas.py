"""A blank solid-color canvas for screens that aren't drawing a board (home,
login, rooms) - built directly from a numpy array wrapped in Img, the same
way graphics/sprite_loader.py generates its own flat-color overlays, since
these screens have no board.png-like asset of their own to load and resize.
"""

import numpy as np

from vendor.img import Img


def blank_canvas(width: int, height: int, color: tuple[int, int, int, int]) -> Img:
    """A width x height BGRA canvas filled with one solid color."""
    canvas = Img()
    canvas.img = np.full((height, width, 4), color, dtype=np.uint8)
    return canvas
