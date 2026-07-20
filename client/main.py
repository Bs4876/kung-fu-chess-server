import server_bridge  # noqa: F401  (must run before any server-rooted import below)

import dialogs
import ui_config
from animation.animation_clock import Clock
from chess_io.board_parser import BoardParser
from config import WS_HOST, WS_PORT
from engine.game_engine import GameEngine
from graphics.window import Window
from model.starting_position import STARTING_POSITION
from net import protocol
from network.network_game_facade import MatchmakingError, NetworkGameFacade, wait_for_game_start
from network.ws_client import WsClient
from persistence.event_log import EventLogWriter
from screens.game_screen import GameScreen
from screens.home_screen import HomeScreen
from screens.screen_manager import ScreenManager
from shell_login import prompt_login
from state.game_facade import GameFacade

_SERVER_URI = f"ws://{WS_HOST}:{WS_PORT}"


def build_local_game_screen() -> GameScreen:
    """Local hot-seat mode: two people sharing one board/mouse, wired to a
    real in-process GameEngine - no server needed. Not reachable from the
    home screen (Play/Rooms always go over the network now), but kept
    available for offline dev/testing without a running ws_server.py."""
    board = BoardParser().parse(STARTING_POSITION)
    return GameScreen(GameFacade(GameEngine(board)))


def main() -> None:
    client_log_writer = EventLogWriter(ui_config.CLIENT_LOG_DIR)

    def on_network_event(kind: str, payload: dict) -> None:
        client_log_writer(("network", {"event": kind, **payload}))

    # Login happens in the shell, before any window exists - per the course
    # spec ("do it in a shell, not via GUI").
    client = WsClient(_SERVER_URI, on_event=on_network_event)
    username, elo = prompt_login(client)

    window = Window(ui_config.WINDOW_TITLE)
    screen_manager = ScreenManager(window)
    clock = Clock()

    def show_home(status: str = "") -> None:
        screen_manager.show(build_home_screen(username, elo, status=status))

    def show_game(start: dict) -> None:
        screen_manager.show(GameScreen(NetworkGameFacade(client, start, event_logger=client_log_writer)))

    def build_home_screen(username: str, elo: int, status: str = "") -> HomeScreen:
        def on_play() -> None:
            # Play requires having already logged in on this same connection
            # (see net/ws_server.py) - matchmaking then blocks this thread
            # until it finds a human within range or, failing that, the
            # server gives up (see net/matchmaking.py); there's no
            # "searching..." UI state for Play yet, so this just waits.
            client.send(protocol.play())
            try:
                start = wait_for_game_start(client)
            except MatchmakingError as exc:
                # "pops up a message that can't find" - a real native popup,
                # not inline screen text.
                dialogs.show_info("Matchmaking", exc.message)
                show_home()
                return
            show_game(start)

        def on_rooms() -> None:
            choice = dialogs.prompt_room_action()
            if choice is None or not choice[1]:
                show_home()
                return
            action, text = choice

            if action == "create":
                client.send(protocol.create_room(text))
                created = client.recv_one_blocking()
                if created["type"] == protocol.ERROR:
                    show_home(status=created["message"])
                    return
                room_id = created["room_id"]
                dialogs.show_info("Room created", f"Room ID: {room_id}\nShare this with your opponent.")
                start = dialogs.wait_for_room_match(client, room_id)
            else:
                client.send(protocol.join_room(text))
                start = client.recv_one_blocking()

            if start is None:
                show_home()
                return
            if start["type"] == protocol.ERROR:
                show_home(status=start["message"])
                return
            show_game(start)

        return HomeScreen(username, elo, on_play, on_rooms, status=status)

    show_home()

    while window.poll():
        window.maintain_aspect_ratio()
        dt_ms = clock.tick()
        scene = screen_manager.render_frame(dt_ms)
        window.show_frame(scene)

    window.close()


if __name__ == "__main__":
    main()
