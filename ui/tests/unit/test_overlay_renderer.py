from graphics.overlay_renderer import OverlayRenderer
from model.position import Position


class FakeOverlay:
    def __init__(self, name):
        self.name = name

    def draw_on(self, canvas, x, y):
        canvas.draws.append((self.name, x, y))


class FakeSpriteSource:
    def load_selection_highlight(self):
        return FakeOverlay("selection")

    def load_halt_flash(self):
        return FakeOverlay("halt_flash")

    def load_cooldown_fade_frame(self, fraction):
        return FakeOverlay(f"cooldown_fade_{fraction}")

    def load_legal_destination_highlight(self, is_capture):
        return FakeOverlay("legal_capture" if is_capture else "legal_move")


class FakeCanvas:
    def __init__(self, height=800):
        self.draws = []
        self.texts = []
        self.img = _FakeImg(height)

    def put_text(self, text, x, y, font_size, color=None, thickness=1):
        self.texts.append((text, x, y))


class _FakeImg:
    def __init__(self, height):
        self.shape = (height, 800, 4)


def build():
    return OverlayRenderer(FakeSpriteSource(), cell_size=100)


def test_no_selection_draws_nothing():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=None, halted_positions=[], cooldown_fade_fractions={}, game_over=False)
    assert canvas.draws == []
    assert canvas.texts == []


def test_selection_is_drawn_at_the_selected_cell_s_pixel():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=Position(1, 2), halted_positions=[], cooldown_fade_fractions={}, game_over=False)
    assert canvas.draws == [("selection", 200, 100)]


def test_one_halt_flash_is_drawn_per_position():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=None, halted_positions=[Position(0, 0), Position(1, 1)],
                   cooldown_fade_fractions={}, game_over=False)
    assert canvas.draws == [("halt_flash", 0, 0), ("halt_flash", 100, 100)]


def test_cooldown_fraction_is_passed_through_to_the_sprite_source_unconverted():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=None, halted_positions=[],
                   cooldown_fade_fractions={Position(2, 0): 0.0}, game_over=False)
    assert canvas.draws == [("cooldown_fade_0.0", 0, 200)]


def test_cooldown_fraction_one_is_passed_through_too():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=None, halted_positions=[],
                   cooldown_fade_fractions={Position(2, 0): 1.0}, game_over=False)
    assert canvas.draws == [("cooldown_fade_1.0", 0, 200)]


def test_one_cooldown_fade_is_drawn_per_position():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=None, halted_positions=[],
                   cooldown_fade_fractions={Position(2, 0): 0.0, Position(0, 1): 1.0}, game_over=False)
    assert canvas.draws == [("cooldown_fade_0.0", 0, 200), ("cooldown_fade_1.0", 100, 0)]


def test_legal_move_cells_are_drawn_green():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=None, halted_positions=[], cooldown_fade_fractions={}, game_over=False,
                   legal_move_cells=[Position(0, 1), Position(1, 0)])
    assert canvas.draws == [("legal_move", 100, 0), ("legal_move", 0, 100)]


def test_legal_capture_cells_are_drawn_red():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=None, halted_positions=[], cooldown_fade_fractions={}, game_over=False,
                   legal_capture_cells=[Position(2, 0)])
    assert canvas.draws == [("legal_capture", 0, 200)]


def test_game_over_banner_is_drawn_only_when_game_is_over():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=None, halted_positions=[], cooldown_fade_fractions={}, game_over=True)
    assert canvas.texts == [("GAME OVER", 100, 400)]


def test_game_over_false_draws_no_banner():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=None, halted_positions=[], cooldown_fade_fractions={}, game_over=False)
    assert canvas.texts == []


def test_all_overlays_can_be_drawn_together_in_order():
    overlays = build()
    canvas = FakeCanvas()
    overlays.draw(canvas, selected=Position(0, 0), halted_positions=[Position(1, 1)],
                   cooldown_fade_fractions={Position(2, 2): 0.0}, game_over=True,
                   legal_move_cells=[Position(0, 3)], legal_capture_cells=[Position(3, 0)])
    assert canvas.draws == [
        ("selection", 0, 0),
        ("legal_move", 300, 0),
        ("legal_capture", 0, 300),
        ("halt_flash", 100, 100),
        ("cooldown_fade_0.0", 200, 200),
    ]
    assert canvas.texts == [("GAME OVER", 100, 400)]
