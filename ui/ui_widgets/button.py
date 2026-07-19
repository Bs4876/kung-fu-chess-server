"""A pixel-drawn clickable rectangle, built on Img + Window's mouse callback.

The course's Img-only graphics rule means there's no native button widget to
reach for - this is the smallest one that works: a labeled rect plus a
contains(x, y) hit-test, styled the same way the rest of ui/graphics draws
flat-color overlays (see ui_widgets/canvas.py).
"""

import ui_config
from vendor.img import Img


class Button:
    """A labeled clickable rectangle at a fixed position and size."""

    def __init__(self, label: str, x: int, y: int, width: int, height: int):
        self.label = label
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    def draw_on(self, canvas: Img) -> None:
        canvas.img[self.y:self.y + self.height, self.x:self.x + self.width] = ui_config.BUTTON_BG_COLOR
        text_x = self.x + ui_config.BUTTON_LABEL_PADDING_PX
        text_y = self.y + self.height // 2 + 8  # roughly centers the text's baseline vertically
        canvas.put_text(self.label, text_x, text_y, ui_config.BUTTON_FONT_SIZE, color=ui_config.BUTTON_TEXT_COLOR)
