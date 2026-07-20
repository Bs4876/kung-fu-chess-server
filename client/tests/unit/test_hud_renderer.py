import numpy as np

import ui_config
from graphics.hud_renderer import HudRenderer


class FakeSpriteSource:
    def load_panel_background(self, width, height):
        return FakeScene(width, height)


class FakeScene:
    def __init__(self, width, height):
        self.img = np.zeros((height, width, 4), dtype=np.uint8)
        self.texts = []

    def put_text(self, text, x, y, font_size, color=None, thickness=1):
        self.texts.append((text, x, y))


class FakeBoardCanvas:
    def __init__(self, width=300, height=300):
        self.img = np.zeros((height, width, 4), dtype=np.uint8)
        self.draws = []

    def draw_on(self, target, x, y):
        self.draws.append((x, y))


class FakePlayerLabels:
    def __init__(self, white="Alice", black="Bob"):
        self.white_name = white
        self.black_name = black


class FakeMovesLogPanel:
    def __init__(self, white_lines=None, black_lines=None):
        self._white = white_lines or []
        self._black = black_lines or []

    def white_lines(self):
        return self._white

    def black_lines(self):
        return self._black


class FakeScorePanel:
    def __init__(self, white_score=0, black_score=0):
        self.white_score = white_score
        self.black_score = black_score


def build():
    return HudRenderer(FakeSpriteSource())


def test_scene_is_board_size_plus_a_panel_on_each_side():
    hud = build()
    board = FakeBoardCanvas(width=300, height=400)
    scene = hud.compose(board, FakeMovesLogPanel(), FakeScorePanel(), FakePlayerLabels())
    assert scene.img.shape[1] == 300 + ui_config.PANEL_WIDTH * 2
    assert scene.img.shape[0] == 400


def test_board_is_drawn_offset_past_the_left_panel():
    hud = build()
    board = FakeBoardCanvas()
    hud.compose(board, FakeMovesLogPanel(), FakeScorePanel(), FakePlayerLabels())
    assert board.draws == [(ui_config.PANEL_WIDTH, 0)]


def test_player_names_are_drawn_in_their_own_panel():
    hud = build()
    board = FakeBoardCanvas(width=300)
    scene = hud.compose(board, FakeMovesLogPanel(), FakeScorePanel(), FakePlayerLabels("Alice", "Bob"))
    names = [t for t in scene.texts if t[0] in ("Alice", "Bob")]
    black_x = ui_config.PANEL_WIDTH + 300 + ui_config.HUD_LEFT_PADDING_PX
    assert names == [
        ("Alice", ui_config.HUD_LEFT_PADDING_PX, ui_config.HUD_TOP_PADDING_PX),
        ("Bob", black_x, ui_config.HUD_TOP_PADDING_PX),
    ]


def test_scores_are_drawn_for_each_side():
    hud = build()
    board = FakeBoardCanvas(width=300)
    scores = FakeScorePanel(white_score=5, black_score=2)
    scene = hud.compose(board, FakeMovesLogPanel(), scores, FakePlayerLabels())
    score_texts = [t[0] for t in scene.texts if t[0].startswith("Score")]
    assert score_texts == ["Score: 5", "Score: 2"]


def test_moves_log_lines_are_drawn_for_each_side_in_order():
    hud = build()
    board = FakeBoardCanvas(width=300)
    log = FakeMovesLogPanel(white_lines=["e2-e4"], black_lines=["e7-e5", "d7-d5"])
    scene = hud.compose(board, log, FakeScorePanel(), FakePlayerLabels())
    reserved = {"Alice", "Bob", "Score: 0"}
    line_texts = [t[0] for t in scene.texts if t[0] not in reserved]
    assert line_texts == ["e2-e4", "e7-e5", "d7-d5"]


def test_moves_log_lines_stop_before_running_off_the_bottom_of_the_board():
    hud = build()
    board = FakeBoardCanvas(width=300, height=200)
    many_lines = [f"move{i}" for i in range(20)]
    log = FakeMovesLogPanel(white_lines=many_lines)
    scene = hud.compose(board, log, FakeScorePanel(), FakePlayerLabels())
    drawn = [t[0] for t in scene.texts if t[0].startswith("move")]
    assert drawn == many_lines[:3]


def test_both_side_panels_get_the_background_fill_and_the_board_area_does_not():
    hud = build()
    board = FakeBoardCanvas(width=300, height=100)
    scene = hud.compose(board, FakeMovesLogPanel(), FakeScorePanel(), FakePlayerLabels())
    bg = ui_config.HUD_PANEL_BG_COLOR
    assert tuple(scene.img[0, 0]) == bg
    assert tuple(scene.img[0, ui_config.PANEL_WIDTH + 300]) == bg
    assert tuple(scene.img[0, ui_config.PANEL_WIDTH]) == (0, 0, 0, 0)
