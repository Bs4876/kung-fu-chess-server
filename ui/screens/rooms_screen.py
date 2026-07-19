"""Manual create/join room list - a second, human-driven way into a
networked game alongside HomeScreen's Play button. Polls list_rooms every
ROOMS_POLL_INTERVAL_MS while open rather than needing the server to push
updates (see net/room_registry.py's own docstring for the same reasoning).

Unlike HomeScreen's Play (which blocks the render thread waiting to be
matched - see ui/main.py), this screen is fully non-blocking: create/join
are both fire-and-forget sends, and whatever comes back (room_list,
room_created, game_start, error) is handled in tick() the same way
NetworkGameFacade itself handles inbound messages.
"""

import cv2

import ui_config
from net import protocol
from ui_widgets.button import Button
from ui_widgets.canvas import blank_canvas
from ui_widgets.room_list_view import RoomListView
from ui_widgets.text_input import TextInput


class RoomsScreen:
    def __init__(
        self, client, on_game_start, on_back,
        width: int = ui_config.ROOMS_SCREEN_WIDTH, height: int = ui_config.ROOMS_SCREEN_HEIGHT,
    ):
        """client: an already-connected, already-logged-in ws_client-shaped
        object. on_game_start(client, start_message) is called once a
        game_start arrives (either because this screen's own room filled,
        or because it successfully joined someone else's). on_back() is
        called when Back is clicked."""
        self._client = client
        self._on_game_start = on_game_start
        self._on_back = on_back
        self._width = width
        self._height = height
        self._status = ""
        self._poll_elapsed_ms = ui_config.ROOMS_POLL_INTERVAL_MS  # poll immediately on the first tick

        self._name_field = TextInput(40, 90, 280, 44)
        self._create_button = Button("Create", x=330, y=90, width=110, height=44)
        self._back_button = Button("Back", x=width - 130, y=height - 70, width=90, height=44)
        self._room_list_view = RoomListView(40, 160, width - 80, row_height=40)

    def tick(self, dt_ms: int) -> None:
        self._poll_elapsed_ms += dt_ms
        if self._poll_elapsed_ms >= ui_config.ROOMS_POLL_INTERVAL_MS:
            self._poll_elapsed_ms = 0
            self._client.send(protocol.list_rooms())
        for message in self._client.recv_all():
            self._handle_message(message)

    def render(self):
        canvas = blank_canvas(self._width, self._height, ui_config.ROOMS_SCREEN_BG_COLOR)
        canvas.put_text("Rooms", 40, 50, ui_config.HOME_SCREEN_TITLE_FONT_SIZE,
                        color=ui_config.ROOMS_SCREEN_TITLE_COLOR, thickness=2)
        self._name_field.draw_on(canvas)
        self._create_button.draw_on(canvas)
        self._back_button.draw_on(canvas)
        self._room_list_view.draw_on(canvas)
        if self._status:
            canvas.put_text(self._status, 40, self._height - 40, 0.6, color=ui_config.ROOMS_SCREEN_STATUS_COLOR)
        return canvas

    def handle_mouse(self, event, x, y, flags, param) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if self._name_field.contains(x, y):
            self._name_field.focused = True
        elif self._create_button.contains(x, y):
            self._create_button_clicked()
        elif self._back_button.contains(x, y):
            self._on_back()
            return
        room_id = self._room_list_view.hit_test(x, y)
        if room_id is not None:
            self._client.send(protocol.join_room(room_id))

    def handle_key(self, key: int | None) -> None:
        self._name_field.handle_key(key)

    def _create_button_clicked(self) -> None:
        if self._name_field.text:
            self._client.send(protocol.create_room(self._name_field.text))

    def _handle_message(self, message: dict) -> None:
        if message["type"] == protocol.ROOM_LIST:
            self._room_list_view.set_rooms(message["rooms"])
        elif message["type"] == protocol.ROOM_CREATED:
            self._status = f'Waiting for an opponent in "{self._name_field.text}"...'
        elif message["type"] == protocol.GAME_START:
            self._on_game_start(self._client, message)
        elif message["type"] == protocol.ERROR:
            self._status = message["message"]
