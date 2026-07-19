import cv2

from screens.home_screen import HomeScreen


def screen_for(on_play, width: int = 400, height: int = 300) -> HomeScreen:
    return HomeScreen(on_play, width=width, height=height)


def test_clicking_the_play_button_calls_on_play():
    called = []
    screen = screen_for(lambda: called.append(True))
    screen.handle_mouse(cv2.EVENT_LBUTTONDOWN, 200, 150, 0, None)  # button is centered on the screen
    assert called == [True]


def test_clicking_outside_the_play_button_does_nothing():
    called = []
    screen = screen_for(lambda: called.append(True))
    screen.handle_mouse(cv2.EVENT_LBUTTONDOWN, 5, 5, 0, None)
    assert called == []


def test_a_non_click_mouse_event_over_the_button_does_nothing():
    called = []
    screen = screen_for(lambda: called.append(True))
    screen.handle_mouse(cv2.EVENT_MOUSEMOVE, 200, 150, 0, None)
    assert called == []


def test_render_returns_a_canvas_sized_to_the_screen():
    screen = screen_for(lambda: None, width=400, height=300)
    canvas = screen.render()
    height, width = canvas.img.shape[:2]
    assert (width, height) == (400, 300)


def test_tick_does_not_raise():
    screen_for(lambda: None).tick(16)
