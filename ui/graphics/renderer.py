"""Composes one frame: the board background plus every piece currently on it."""

from model.board import EMPTY
from model.position import Position


class BoardRenderer:
    """Draws a GameSnapshot onto a fresh canvas each call.

    A fresh board.png copy is loaded every frame (via sprite_loader) rather than
    reused, because Img.draw_on mutates pixels in place with no way to undo a draw.
    """

    def __init__(self, sprite_loader, cell_size: int):
        self._sprites = sprite_loader
        self._cell_size = cell_size

    def render(self, snapshot):
        """Return a new Img with the board and every occupied cell's sprite drawn on it."""
        canvas = self._sprites.load_board(snapshot.rows, snapshot.cols)
        self._draw_pieces(canvas, snapshot)
        return canvas

    def _draw_pieces(self, canvas, snapshot) -> None:
        for row in range(snapshot.rows):
            for col in range(snapshot.cols):
                token = snapshot.get_piece(Position(row, col))
                if token != EMPTY:
                    self._draw_piece(canvas, token, row, col)

    def _draw_piece(self, canvas, token: str, row: int, col: int) -> None:
        sprite = self._sprites.load_idle_sprite(token)
        sprite.draw_on(canvas, col * self._cell_size, row * self._cell_size)
