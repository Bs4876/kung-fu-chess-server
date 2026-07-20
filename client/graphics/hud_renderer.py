"""Composes the rendered board with a panel on each side (White left, Black right)."""

import ui_config
from graphics.protocols import SpriteSource


class HudRenderer:
    """Draws board_canvas in the centre, White panel on the left, Black panel on the right."""

    def __init__(self, sprite_loader: SpriteSource):
        self._sprites = sprite_loader
        self._panel_width = ui_config.PANEL_WIDTH

    def compose(self, board_canvas, moves_log_panel, score_panel, player_labels):
        board_height, board_width = board_canvas.img.shape[:2]
        full_width = board_width + self._panel_width * 2

        scene = self._sprites.load_panel_background(full_width, board_height)

        # fill both side panels with creamy background
        bg = ui_config.HUD_PANEL_BG_COLOR
        scene.img[:, :self._panel_width] = bg
        scene.img[:, self._panel_width + board_width:] = bg

        board_canvas.draw_on(scene, self._panel_width, 0)

        self._draw_side_panel(
            scene,
            player_labels.white_name,
            score_panel.white_score,
            moves_log_panel.white_lines(),
            x=ui_config.HUD_LEFT_PADDING_PX,
            board_height=board_height,
        )
        self._draw_side_panel(
            scene,
            player_labels.black_name,
            score_panel.black_score,
            moves_log_panel.black_lines(),
            x=self._panel_width + board_width + ui_config.HUD_LEFT_PADDING_PX,
            board_height=board_height,
        )
        return scene

    def _draw_side_panel(self, scene, name: str, score: int, lines: list,
                         x: int, board_height: int) -> None:
        pad = ui_config.HUD_LEFT_PADDING_PX
        panel_right = x - pad + self._panel_width - pad

        y = ui_config.HUD_TOP_PADDING_PX
        scene.put_text(name, x, y, ui_config.HUD_TITLE_FONT_SIZE,
                       color=ui_config.HUD_TITLE_COLOR, thickness=ui_config.HUD_TITLE_THICKNESS)

        y += ui_config.HUD_LINE_HEIGHT_PX + ui_config.HUD_TITLE_TO_SCORE_GAP_PX
        scene.put_text(f"Score: {score}", x, y, ui_config.HUD_SCORE_FONT_SIZE,
                       color=ui_config.HUD_SCORE_COLOR)

        # divider line under score
        y += ui_config.HUD_SCORE_TO_DIVIDER_GAP_PX
        div_color = ui_config.HUD_DIVIDER_COLOR
        scene.img[y:y+1, x:panel_right] = div_color

        y += ui_config.HUD_SCORE_TO_MOVES_GAP_PX - ui_config.HUD_SCORE_TO_DIVIDER_GAP_PX
        for line in lines:
            y += ui_config.HUD_LINE_HEIGHT_PX
            if y >= board_height - ui_config.HUD_LINE_HEIGHT_PX:
                break
            scene.put_text(line, x, y, ui_config.HUD_LINE_FONT_SIZE,
                           color=ui_config.HUD_TEXT_COLOR)
