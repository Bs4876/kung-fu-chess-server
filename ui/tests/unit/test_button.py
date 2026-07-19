import numpy as np

import ui_config
from ui_widgets.button import Button
from vendor.img import Img


def make_canvas(width: int = 400, height: int = 300) -> Img:
    canvas = Img()
    canvas.img = np.zeros((height, width, 4), dtype=np.uint8)
    return canvas


def test_contains_true_inside_the_rect():
    button = Button("Play", x=10, y=20, width=100, height=40)
    assert button.contains(50, 30)


def test_contains_false_outside_the_rect():
    button = Button("Play", x=10, y=20, width=100, height=40)
    assert not button.contains(200, 200)


def test_contains_is_inclusive_of_top_left_and_exclusive_of_bottom_right():
    button = Button("Play", x=0, y=0, width=10, height=10)
    assert button.contains(0, 0)
    assert not button.contains(10, 10)


def test_draw_on_fills_the_button_rect_with_the_background_color():
    button = Button("Play", x=10, y=10, width=20, height=20)
    canvas = make_canvas()
    button.draw_on(canvas)
    assert tuple(canvas.img[15, 15]) == ui_config.BUTTON_BG_COLOR


def test_draw_on_leaves_pixels_outside_the_rect_untouched():
    button = Button("Play", x=10, y=10, width=20, height=20)
    canvas = make_canvas()
    button.draw_on(canvas)
    assert tuple(canvas.img[0, 0]) == (0, 0, 0, 0)
