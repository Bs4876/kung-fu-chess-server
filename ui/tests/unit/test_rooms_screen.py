import cv2

from net import protocol
from screens.rooms_screen import RoomsScreen


class FakeClient:
    def __init__(self):
        self.sent = []
        self._queue = []

    def send(self, message: dict) -> None:
        self.sent.append(message)

    def queue(self, message: dict) -> None:
        self._queue.append(message)

    def recv_all(self) -> list:
        messages, self._queue = self._queue, []
        return messages


def screen_for(on_game_start=None, on_back=None):
    client = FakeClient()
    starts = []
    backs = []
    screen = RoomsScreen(
        client,
        on_game_start=on_game_start or (lambda c, m: starts.append((c, m))),
        on_back=on_back or (lambda: backs.append(True)),
    )
    return screen, client, starts, backs


def test_first_tick_immediately_requests_the_room_list():
    screen, client, _starts, _backs = screen_for()
    screen.tick(0)
    assert client.sent == [protocol.list_rooms()]


def test_tick_polls_again_once_the_interval_elapses():
    screen, client, _starts, _backs = screen_for()
    screen.tick(0)
    client.sent.clear()
    screen.tick(1000)
    assert client.sent == []
    screen.tick(1000)
    assert client.sent == [protocol.list_rooms()]


def _join_button_point(screen) -> tuple[int, int]:
    view = screen._room_list_view
    return (view.x + view.width - 10, view.y + 10)


def test_room_list_message_updates_the_room_list_view():
    screen, client, _starts, _backs = screen_for()
    client.queue(protocol.room_list([{"id": "abc", "name": "Alice's room", "occupants": 1, "capacity": 2}]))
    screen.tick(0)
    join_x, join_y = _join_button_point(screen)
    assert screen._room_list_view.hit_test(join_x, join_y) == "abc"


def test_clicking_join_on_a_room_sends_join_room():
    screen, client, _starts, _backs = screen_for()
    client.queue(protocol.room_list([{"id": "abc", "name": "Alice's room", "occupants": 1, "capacity": 2}]))
    screen.tick(0)
    client.sent.clear()

    join_x, join_y = _join_button_point(screen)
    screen.handle_mouse(cv2.EVENT_LBUTTONDOWN, join_x, join_y, 0, None)

    assert client.sent == [protocol.join_room("abc")]


def test_clicking_create_with_a_name_sends_create_room():
    screen, client, _starts, _backs = screen_for()
    screen._name_field.text = "My Room"
    screen.handle_mouse(cv2.EVENT_LBUTTONDOWN,
                        screen._create_button.x + 5, screen._create_button.y + 5, 0, None)
    assert client.sent == [protocol.create_room("My Room")]


def test_clicking_create_with_an_empty_name_sends_nothing():
    screen, client, _starts, _backs = screen_for()
    screen.handle_mouse(cv2.EVENT_LBUTTONDOWN,
                        screen._create_button.x + 5, screen._create_button.y + 5, 0, None)
    assert client.sent == []


def test_room_created_sets_a_waiting_status():
    screen, client, _starts, _backs = screen_for()
    screen._name_field.text = "My Room"
    client.queue(protocol.room_created("xyz"))
    screen.tick(0)
    assert "My Room" in screen._status


def test_game_start_message_calls_on_game_start_with_the_client_and_message():
    screen, client, starts, _backs = screen_for()
    start_message = protocol.game_start("1", "white", 0, _fake_snapshot())
    client.queue(start_message)
    screen.tick(0)
    assert starts == [(client, start_message)]


def test_error_message_sets_the_status():
    screen, client, _starts, _backs = screen_for()
    client.queue(protocol.error("cannot_join_room", "room not found or already full"))
    screen.tick(0)
    assert screen._status == "room not found or already full"


def test_clicking_back_calls_on_back():
    screen, client, _starts, backs = screen_for()
    screen.handle_mouse(cv2.EVENT_LBUTTONDOWN,
                        screen._back_button.x + 5, screen._back_button.y + 5, 0, None)
    assert backs == [True]


def test_clicking_the_name_field_focuses_it_for_typing():
    screen, client, _starts, _backs = screen_for()
    screen.handle_mouse(cv2.EVENT_LBUTTONDOWN, screen._name_field.x + 5, screen._name_field.y + 5, 0, None)
    screen.handle_key(ord("x"))
    assert screen._name_field.text == "x"


def _fake_snapshot():
    class _Snapshot:
        rows = 1
        cols = 1

        def get_piece(self, pos):
            return "wR"

    return _Snapshot()
