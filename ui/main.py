import server_bridge  # noqa: F401  (must run before any server-rooted import below)

import ui_config
from animation.animation_clock import Clock
from chess_io.board_parser import BoardParser
from config import WS_HOST, WS_PORT
from engine.game_engine import GameEngine
from graphics.window import Window
from model.starting_position import STARTING_POSITION
from network.network_game_facade import connect
from screens.game_screen import GameScreen
from screens.home_screen import HomeScreen
from screens.screen_manager import ScreenManager
from state.game_facade import GameFacade


def build_local_game_screen() -> GameScreen:
    """Local hot-seat mode: two people sharing one board/mouse, wired to a
    real in-process GameEngine - no server needed. Not reachable from the
    home screen (Play always goes over the network now), but kept available
    for offline dev/testing without a running ws_server.py."""
    board = BoardParser().parse(STARTING_POSITION)
    return GameScreen(GameFacade(GameEngine(board)))


def build_network_game_screen() -> GameScreen:
    """Connect to the local server and build a GameScreen wired to a
    NetworkGameFacade.

    connect() blocks the calling thread until paired with an opponent (see
    net/anonymous_lobby.py) - the home screen has no "searching for an
    opponent..." state yet, so clicking Play just waits right here. A later
    stage replaces the anonymous lobby with real matchmaking and adds that
    waiting state; this is deliberately as simple as it can be for now.
    """
    uri = f"ws://{WS_HOST}:{WS_PORT}"
    facade = connect(uri)
    return GameScreen(facade)


def main() -> None:
    window = Window(ui_config.WINDOW_TITLE)
    screen_manager = ScreenManager(window)
    clock = Clock()

    def on_play() -> None:
        screen_manager.show(build_network_game_screen())

    screen_manager.show(HomeScreen(on_play))

    while window.poll():
        window.maintain_aspect_ratio()
        dt_ms = clock.tick()
        scene = screen_manager.render_frame(dt_ms)
        window.show_frame(scene)

    window.close()


if __name__ == "__main__":
    main()
