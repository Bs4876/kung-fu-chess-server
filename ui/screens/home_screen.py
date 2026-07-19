"""The screen shown right after logging in: a welcome line naming who's
logged in, a "Play" button, and a "Rooms" button - as trivial as this
milestone's home screen is meant to be. Clicking either just reports the
click; ui/main.py owns actually sending the play/rooms commands and
switching screens once a game is found (see build_home_screen in main.py).
"""

import cv2

import ui_config
from ui_widgets.button import Button
from ui_widgets.canvas import blank_canvas


class HomeScreen:
    def __init__(
        self, username: str, elo: int, on_play, on_rooms,
        width: int = ui_config.HOME_SCREEN_WIDTH, height: int = ui_config.HOME_SCREEN_HEIGHT,
    ):
        """on_play/on_rooms: called with no arguments when the matching button is clicked."""
        self._username = username
        self._elo = elo
        self._on_play = on_play
        self._on_rooms = on_rooms
        self._width = width
        self._height = height
        button_width, button_height = 220, 70
        self._play_button = Button(
            "Play",
            x=(width - button_width) // 2,
            y=(height - button_height) // 2,
            width=button_width,
            height=button_height,
        )
        self._rooms_button = Button(
            "Rooms",
            x=(width - button_width) // 2,
            y=(height - button_height) // 2 + button_height + 20,
            width=button_width,
            height=button_height,
        )

    def tick(self, dt_ms: int) -> None:
        pass

    def render(self):
        canvas = blank_canvas(self._width, self._height, ui_config.HOME_SCREEN_BG_COLOR)
        canvas.put_text(
            "Kung Fu Chess",
            self._width // 2 - 170, self._height // 3 - 40,
            ui_config.HOME_SCREEN_TITLE_FONT_SIZE,
            color=ui_config.HOME_SCREEN_TITLE_COLOR, thickness=2,
        )
        canvas.put_text(
            f"Welcome, {self._username} (ELO {self._elo})",
            self._width // 2 - 140, self._height // 3,
            0.7, color=ui_config.HOME_SCREEN_TITLE_COLOR,
        )
        self._play_button.draw_on(canvas)
        self._rooms_button.draw_on(canvas)
        return canvas

    def handle_mouse(self, event, x, y, flags, param) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if self._play_button.contains(x, y):
            self._on_play()
        elif self._rooms_button.contains(x, y):
            self._on_rooms()

    def handle_key(self, key: int | None) -> None:
        pass
