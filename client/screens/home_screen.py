"""The screen shown right after logging in: a welcome line naming who's
logged in, a "Play" button, and a "Rooms" button - as trivial as this
milestone's home screen is meant to be. Clicking either just reports the
click; client/main.py owns actually sending the play/rooms commands and
switching screens once a game is found (see build_home_screen in main.py).
"""

import cv2

import ui_config
import user_settings
from ui_widgets.button import Button
from ui_widgets.canvas import blank_canvas
from vendor.img import Img


def _load_king_sprite(color_code: str) -> Img:
    """Load a king's idle sprite (client/assets/<skin>/K<color_code>/states/idle/
    sprites/1.png - the same folder-naming scheme graphics/sprite_loader.py
    uses for board pieces) at homescreen decoration size, rather than a
    fabricated logo - it's already the game's own art."""
    path = ui_config.ASSETS_DIR / user_settings.SKIN / f"K{color_code}" / "states" / "idle" / "sprites" / "1.png"
    size = (ui_config.HOME_SCREEN_PIECE_SIZE, ui_config.HOME_SCREEN_PIECE_SIZE)
    return Img().read(path, size=size)


class HomeScreen:
    def __init__(
        self, username: str, elo: int, on_play, on_rooms,
        width: int = ui_config.HOME_SCREEN_WIDTH, height: int = ui_config.HOME_SCREEN_HEIGHT,
        status: str = "",
    ):
        """on_play/on_rooms: called with no arguments when the matching
        button is clicked. status: an optional one-line message shown below
        the buttons (e.g. "no opponent found, try again" after a failed
        matchmaking attempt) - the same status-line pattern the now-removed
        LoginScreen/RoomsScreen used to use."""
        self._username = username
        self._elo = elo
        self._on_play = on_play
        self._on_rooms = on_rooms
        self._width = width
        self._height = height
        self._status = status
        self._white_king = _load_king_sprite("W")
        self._black_king = _load_king_sprite("B")
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
        self._draw_king(
            canvas, self._white_king, ui_config.HOME_SCREEN_WHITE_BACKDROP_COLOR, user_settings.WHITE_NAME,
            on_left=True,
        )
        self._draw_king(
            canvas, self._black_king, ui_config.HOME_SCREEN_BLACK_BACKDROP_COLOR, user_settings.BLACK_NAME,
            on_left=False,
        )
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
        if self._status:
            canvas.put_text(
                self._status, self._width // 2 - 140, self._rooms_button.y + self._rooms_button.height + 40,
                0.6, color=ui_config.HOME_SCREEN_STATUS_COLOR,
            )
        return canvas

    def _draw_king(self, canvas, sprite: Img, backdrop_color: tuple, name: str, on_left: bool) -> None:
        """Draws sprite on a filled circular backdrop of backdrop_color,
        flanking the title, with name captioned underneath (the same
        white_name/black_name settings ui_components/player_labels.py shows
        in-game - user_settings.py) - a plain cv2.circle straight onto
        canvas.img, the same "reach past Img for a shape it doesn't provide"
        idiom ui_widgets/button.py already uses for its rectangle."""
        size = ui_config.HOME_SCREEN_PIECE_SIZE
        margin = ui_config.HOME_SCREEN_PIECE_MARGIN_PX
        top = ui_config.HOME_SCREEN_PIECE_TOP_PX
        padding = ui_config.HOME_SCREEN_PIECE_BACKDROP_PADDING_PX
        x = margin if on_left else self._width - margin - size
        center_x = x + size // 2
        radius = size // 2 + padding
        cv2.circle(canvas.img, (center_x, top + size // 2), radius, backdrop_color, thickness=-1, lineType=cv2.LINE_AA)
        sprite.draw_on(canvas, x, top)

        font_size = ui_config.HOME_SCREEN_PIECE_NAME_FONT_SIZE
        (text_width, _text_height), _baseline = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, font_size, 1)
        name_y = top + size + padding + ui_config.HOME_SCREEN_PIECE_NAME_GAP_PX
        canvas.put_text(name, center_x - text_width // 2, name_y, font_size, color=ui_config.HOME_SCREEN_TITLE_COLOR)

    def handle_mouse(self, event, x, y, flags, param) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if self._play_button.contains(x, y):
            self._on_play()
        elif self._rooms_button.contains(x, y):
            self._on_rooms()

    def handle_key(self, key: int | None) -> None:
        pass
