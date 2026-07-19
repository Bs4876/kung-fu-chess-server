import numpy as np

from ui_widgets.room_list_view import RoomListView
from vendor.img import Img


def make_canvas(width: int = 400, height: int = 400) -> Img:
    canvas = Img()
    canvas.img = np.zeros((height, width, 4), dtype=np.uint8)
    return canvas


def rooms(*ids):
    return [{"id": room_id, "name": f"Room {room_id}", "occupants": 1, "capacity": 2} for room_id in ids]


def test_hit_test_returns_none_with_no_rooms_set():
    view = RoomListView(0, 0, 300)
    assert view.hit_test(10, 10) is None


def test_hit_test_finds_the_join_button_for_the_right_row():
    view = RoomListView(0, 0, 300, row_height=40)
    view.set_rooms(rooms("a", "b"))
    # second row's Join button is roughly at y=40..74, x near the right edge
    assert view.hit_test(view.width - 10, 50) == "b"


def test_hit_test_outside_any_row_returns_none():
    view = RoomListView(0, 0, 300, row_height=40)
    view.set_rooms(rooms("a"))
    assert view.hit_test(5, 5) is None  # left edge, not over a Join button


def test_max_rows_truncates_the_displayed_list():
    view = RoomListView(0, 0, 300, row_height=40, max_rows=2)
    view.set_rooms(rooms("a", "b", "c"))
    assert view.hit_test(view.width - 10, 40 * 2 + 10) is None  # third row never gets a button


def test_set_rooms_replaces_the_previous_list():
    view = RoomListView(0, 0, 300, row_height=40)
    view.set_rooms(rooms("a"))
    view.set_rooms(rooms("b"))
    assert view.hit_test(view.width - 10, 10) == "b"


def test_draw_on_with_no_rooms_does_not_raise():
    view = RoomListView(0, 0, 300)
    view.draw_on(make_canvas())


def test_draw_on_with_rooms_does_not_raise():
    view = RoomListView(0, 0, 300, row_height=40)
    view.set_rooms(rooms("a", "b"))
    view.draw_on(make_canvas())
