"""Owns the board's non-piece overlays - split out of BoardRenderer so it's
independently testable without cv2/Img (see protocols.SpriteSource).

Draw order (selection, then legal-destination hints, then halt-flashes, then
cooldown-fades, then the game-over banner) is load-bearing, not cosmetic:
Img.draw_on composites in place onto a shared canvas, and e.g. a legal
destination that's also cooling down from a previous landing legitimately
gets both overlays stacked in this order.
"""

import ui_config
from model.position import Position


class OverlayRenderer:
    def __init__(self, sprite_source, cell_size: int):
        self._sprites = sprite_source
        self._cell_size = cell_size

    def draw(self, canvas, selected: Position | None, halted_positions: list | None,
             cooldown_fade_fractions: dict | None, game_over: bool,
             legal_move_cells: list | None = None, legal_capture_cells: list | None = None,
             disconnect_countdown_seconds: int | None = None) -> None:
        if selected is not None:
            self._draw_selection(canvas, selected)
        for pos in legal_move_cells or []:
            self._draw_legal_destination(canvas, pos, is_capture=False)
        for pos in legal_capture_cells or []:
            self._draw_legal_destination(canvas, pos, is_capture=True)
        for pos in halted_positions or []:
            self._draw_halt_flash(canvas, pos)
        for pos, fraction in (cooldown_fade_fractions or {}).items():
            self._draw_cooldown_fade(canvas, pos, fraction)
        if game_over:
            self._draw_game_over_banner(canvas)
        if disconnect_countdown_seconds is not None:
            self._draw_disconnect_countdown(canvas, disconnect_countdown_seconds)

    def _draw_selection(self, canvas, selected: Position) -> None:
        highlight = self._sprites.load_selection_highlight()
        highlight.draw_on(canvas, selected.col * self._cell_size, selected.row * self._cell_size)

    def _draw_legal_destination(self, canvas, position: Position, is_capture: bool) -> None:
        highlight = self._sprites.load_legal_destination_highlight(is_capture)
        highlight.draw_on(canvas, position.col * self._cell_size, position.row * self._cell_size)

    def _draw_halt_flash(self, canvas, position: Position) -> None:
        flash = self._sprites.load_halt_flash()
        flash.draw_on(canvas, position.col * self._cell_size, position.row * self._cell_size)

    def _draw_cooldown_fade(self, canvas, position: Position, fraction: float) -> None:
        fade = self._sprites.load_cooldown_fade_frame(fraction)
        fade.draw_on(canvas, position.col * self._cell_size, position.row * self._cell_size)

    def _draw_game_over_banner(self, canvas) -> None:
        board_height = canvas.img.shape[0]
        canvas.put_text("GAME OVER", self._cell_size, board_height // 2, ui_config.GAME_OVER_BANNER_FONT_SIZE,
                        color=ui_config.GAME_OVER_BANNER_COLOR, thickness=ui_config.GAME_OVER_BANNER_THICKNESS)

    def _draw_disconnect_countdown(self, canvas, seconds: int) -> None:
        canvas.put_text(
            f"Opponent disconnected - auto-resign in {seconds}s", self._cell_size, self._cell_size // 2,
            ui_config.DISCONNECT_BANNER_FONT_SIZE,
            color=ui_config.DISCONNECT_BANNER_COLOR, thickness=ui_config.DISCONNECT_BANNER_THICKNESS,
        )
