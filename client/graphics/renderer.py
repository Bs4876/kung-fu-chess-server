"""Composes one frame: the board background, every animated piece, and overlays."""

from graphics.overlay_renderer import OverlayRenderer
from graphics.piece_renderer import PieceRenderer
from model.position import Position


class BoardRenderer:
    """Draws a GameSnapshot onto a fresh canvas each call.

    A fresh board.png copy is loaded every frame (via sprite_loader) rather than
    reused, because Img.draw_on mutates pixels in place with no way to undo a draw.
    Piece animation is PieceRenderer's job and overlays are OverlayRenderer's -
    this class just orchestrates: load the background, hand it to each in turn.
    """

    def __init__(self, sprite_loader, cell_size: int):
        self._sprites = sprite_loader
        self._pieces = PieceRenderer(sprite_loader, cell_size)
        self._overlays = OverlayRenderer(sprite_loader, cell_size)

    def render(self, snapshot, dt_ms: int = 0, selected: Position | None = None,
               pending_motions: dict | None = None, halted_positions: list | None = None,
               game_over: bool = False, cooldown_fade_fractions: dict | None = None,
               legal_move_cells: list | None = None, legal_capture_cells: list | None = None,
               disconnect_countdown_seconds: int | None = None):
        """Return a new Img with the board, every piece's current frame, a
        highlight border around the selected cell (if given), green/red hints
        over that piece's legal destinations (if given), a brief red flash
        over any just-halted cells (if given), a fading yellow overlay over
        any cooling-down cells (if given), a game-over banner (if the game
        has ended), and an opponent-disconnected countdown (if given), all
        drawn on it."""
        canvas = self._sprites.load_board(snapshot.rows, snapshot.cols)
        self._pieces.draw(canvas, snapshot, dt_ms, pending_motions)
        self._overlays.draw(canvas, selected, halted_positions, cooldown_fade_fractions, game_over,
                            legal_move_cells, legal_capture_cells, disconnect_countdown_seconds)
        return canvas
