"""GameScreen wires real ui_components/graphics/input classes against a real
GameFacade, the same way ui/tests/unit/test_game_facade.py favors a real
engine over a mock - the point of this class is the wiring itself holding
together, which a hand-mocked facade would risk hiding.
"""

import cv2

from chess_io.board_parser import BoardParser
from engine.game_engine import GameEngine
from model.position import Position
from screens.game_screen import GameScreen
from state.game_facade import GameFacade


def screen_for(board_text: str) -> GameScreen:
    return GameScreen(GameFacade(GameEngine(BoardParser().parse(board_text))))


def small_board():
    return "wR . .\n" + ". . .\n" * 2


def test_construction_wires_every_facade_channel_without_raising():
    screen_for(small_board())


def test_render_returns_a_canvas_sized_for_the_board_plus_hud_panels():
    screen = screen_for(small_board())
    canvas = screen.render()
    height, width = canvas.img.shape[:2]
    assert height == 3 * 100  # 3 rows * CELL_SIZE
    assert width == 3 * 100 + 220 * 2  # + PANEL_WIDTH on each side


def test_tick_advances_the_facade_and_the_rendered_snapshot_reflects_it():
    screen = screen_for(small_board())
    screen._facade.request_move(Position(0, 0), Position(0, 2))
    screen.tick(2100)  # 2 cells * MOVE_TRAVEL_TIME_PER_CELL(1000)
    assert screen._last_snapshot.get_piece(Position(0, 2)) == "wR"


def test_mouse_click_selects_a_piece_through_the_shared_controller():
    screen = screen_for(small_board())
    # +PANEL_WIDTH(220): the HUD's left panel shifts board-local pixel (50, 50) over.
    screen.handle_mouse(cv2.EVENT_LBUTTONDOWN, 270, 50, 0, None)  # inside cell (0, 0)
    assert screen._controller.selected == Position(0, 0)


def test_king_capture_flips_the_game_over_banner():
    text = ". . . . . . . .\n" * 4 + ". . . bK . . . .\n" + ". . . . . . . .\n" * 2 + ". . . wR . . . .\n"
    screen = screen_for(text)
    screen._facade.request_move(Position(7, 3), Position(4, 3))
    screen.tick(3100)  # 3 cells * MOVE_TRAVEL_TIME_PER_CELL(1000)
    assert screen._game_over_banner.is_game_over


def test_custom_player_names_override_settings_defaults():
    screen = GameScreen(GameFacade(GameEngine(BoardParser().parse(small_board()))), "Alice", "Bob")
    assert screen._player_labels.white_name == "Alice"
    assert screen._player_labels.black_name == "Bob"
