from unittest.mock import MagicMock

from screens.screen_manager import ScreenManager


def build():
    window = MagicMock()
    manager = ScreenManager(window)
    return manager, window


def test_registers_one_mouse_callback_on_construction():
    manager, window = build()
    window.set_mouse_callback.assert_called_once()


def test_show_ticks_the_new_screen_once_and_resizes_the_window_to_its_first_frame():
    manager, window = build()
    screen = MagicMock()
    screen.render.return_value = "frame"
    manager.show(screen)
    screen.tick.assert_called_once_with(0)
    window.resize_to.assert_called_once_with("frame")


def test_render_frame_ticks_with_dt_then_returns_the_rendered_frame():
    manager, window = build()
    screen = MagicMock()
    manager.show(screen)
    screen.reset_mock()
    screen.render.return_value = "frame2"

    result = manager.render_frame(16)

    screen.tick.assert_called_once_with(16)
    assert result == "frame2"


def test_render_frame_forwards_the_windows_last_key_to_the_current_screen():
    manager, window = build()
    screen = MagicMock()
    manager.show(screen)
    screen.reset_mock()
    window.last_key.return_value = 65  # 'A'

    manager.render_frame(16)

    screen.handle_key.assert_called_once_with(65)


def test_mouse_events_are_forwarded_to_the_current_screen():
    manager, window = build()
    handler = window.set_mouse_callback.call_args[0][0]
    screen = MagicMock()
    manager.show(screen)

    handler(1, 10, 20, 0, None)

    screen.handle_mouse.assert_called_once_with(1, 10, 20, 0, None)


def test_mouse_events_before_any_screen_is_shown_are_ignored_not_raised():
    manager, window = build()
    handler = window.set_mouse_callback.call_args[0][0]
    handler(1, 10, 20, 0, None)


def test_switching_screens_stops_forwarding_to_the_old_one():
    manager, window = build()
    handler = window.set_mouse_callback.call_args[0][0]
    first, second = MagicMock(), MagicMock()
    manager.show(first)
    manager.show(second)

    handler(1, 10, 20, 0, None)

    first.handle_mouse.assert_not_called()
    second.handle_mouse.assert_called_once_with(1, 10, 20, 0, None)
