from types import SimpleNamespace

from graphics.renderer import BoardRenderer
from model.board import EMPTY
from model.position import Position


def config(frames_per_sec=5, is_loop=True, next_state="idle", frame_count=5):
    return SimpleNamespace(
        frames_per_sec=frames_per_sec, is_loop=is_loop, next_state=next_state, frame_count=frame_count
    )


class FakeDrawable:
    def __init__(self, tag):
        self.tag = tag

    def draw_on(self, canvas, x, y):
        canvas.draws.append((self.tag, x, y))


class FakeCanvas:
    def __init__(self, rows, cols, cell_size):
        self.draws = []
        self.texts = []
        self.img = SimpleNamespace(shape=(rows * cell_size, cols * cell_size, 4))

    def put_text(self, text, x, y, font_size, color=None, thickness=1):
        self.texts.append((text, x, y))


class FakeSpriteSource:
    """Satisfies both PieceRenderer's and OverlayRenderer's needs, since
    BoardRenderer builds real instances of each rather than fakes of them."""

    def __init__(self, cell_size=100):
        self._cell_size = cell_size

    def load_board(self, rows, cols):
        return FakeCanvas(rows, cols, self._cell_size)

    def load_selection_highlight(self):
        return FakeDrawable("selection")

    def load_halt_flash(self):
        return FakeDrawable("halt_flash")

    def load_cooldown_fade_frame(self, fraction):
        return FakeDrawable(f"cooldown_fade_{fraction}")

    def load_legal_destination_highlight(self, is_capture):
        return FakeDrawable("legal_capture" if is_capture else "legal_move")

    def load_state_config(self, token, state):
        return config()

    def load_frame(self, token, state, frame_index):
        return FakeDrawable(f"{token}_{state}_{frame_index}")


class FakeSnapshot:
    def __init__(self, tokens: dict, rows=3, cols=3):
        self._tokens = tokens
        self.rows = rows
        self.cols = cols

    def get_piece(self, pos):
        return self._tokens.get(pos, EMPTY)


def build(cell_size=100):
    return BoardRenderer(FakeSpriteSource(cell_size), cell_size)


def test_render_loads_a_board_sized_canvas():
    renderer = build()
    canvas = renderer.render(FakeSnapshot({}, rows=2, cols=4), dt_ms=16)
    assert canvas.img.shape == (200, 400, 4)


def test_render_draws_pieces_onto_the_board_canvas():
    renderer = build()
    canvas = renderer.render(FakeSnapshot({Position(0, 0): "wR"}), dt_ms=16)
    assert canvas.draws == [("wR_idle_1", 0, 0)]


def test_render_draws_the_selection_highlight_after_the_pieces():
    renderer = build()
    canvas = renderer.render(FakeSnapshot({Position(0, 0): "wR"}), dt_ms=16, selected=Position(0, 0))
    assert canvas.draws == [("wR_idle_1", 0, 0), ("selection", 0, 0)]


def test_render_draws_legal_move_and_capture_hints():
    renderer = build()
    canvas = renderer.render(FakeSnapshot({}), dt_ms=16,
                             legal_move_cells=[Position(0, 1)], legal_capture_cells=[Position(1, 0)])
    assert canvas.draws == [("legal_move", 100, 0), ("legal_capture", 0, 100)]


def test_render_draws_the_game_over_banner():
    renderer = build()
    canvas = renderer.render(FakeSnapshot({}), dt_ms=16, game_over=True)
    assert canvas.texts == [("GAME OVER", 100, 150)]


def test_render_returns_a_fresh_canvas_each_call():
    renderer = build()
    first = renderer.render(FakeSnapshot({}), dt_ms=16)
    second = renderer.render(FakeSnapshot({}), dt_ms=16)
    assert first is not second
