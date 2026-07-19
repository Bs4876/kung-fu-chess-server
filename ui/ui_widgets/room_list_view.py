"""Draws the open-rooms list (net/protocol.py's room_list payload) as
stacked rows, each with its own small "Join" button - built on Img/put_text
like every other widget in this package, plus a hit_test for figuring out
which row's Join button (if any) a click landed on.
"""

import ui_config
from ui_widgets.button import Button
from vendor.img import Img

_JOIN_BUTTON_WIDTH = 80
_ROW_LABEL_FONT_SIZE = 0.6


class RoomListView:
    def __init__(self, x: int, y: int, width: int, row_height: int = 40, max_rows: int = 8):
        self.x = x
        self.y = y
        self.width = width
        self.row_height = row_height
        self.max_rows = max_rows
        self._rooms: list[dict] = []
        self._join_buttons: dict[str, Button] = {}

    def set_rooms(self, rooms: list[dict]) -> None:
        self._rooms = rooms[:self.max_rows]
        self._join_buttons = {
            room["id"]: Button(
                "Join",
                x=self.x + self.width - _JOIN_BUTTON_WIDTH, y=self.y + i * self.row_height,
                width=_JOIN_BUTTON_WIDTH, height=self.row_height - 6,
            )
            for i, room in enumerate(self._rooms)
        }

    def hit_test(self, x: int, y: int) -> str | None:
        """The room_id whose Join button was clicked, or None."""
        for room_id, button in self._join_buttons.items():
            if button.contains(x, y):
                return room_id
        return None

    def draw_on(self, canvas: Img) -> None:
        if not self._rooms:
            canvas.put_text("No open rooms", self.x, self.y + 20, _ROW_LABEL_FONT_SIZE, color=ui_config.TEXT_INPUT_TEXT_COLOR)
            return
        for i, room in enumerate(self._rooms):
            row_y = self.y + i * self.row_height
            label = f"{room['name']} ({room['occupants']}/{room['capacity']})"
            canvas.put_text(label, self.x, row_y + self.row_height - 12, _ROW_LABEL_FONT_SIZE, color=ui_config.TEXT_INPUT_TEXT_COLOR)
            self._join_buttons[room["id"]].draw_on(canvas)
