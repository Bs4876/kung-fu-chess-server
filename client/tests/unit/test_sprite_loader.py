import ui_config
from graphics.sprite_loader import SpriteLoader, token_to_sprite_code


def test_token_to_sprite_code_converts_color_kind_to_kind_color():
    assert token_to_sprite_code("wR") == "RW"
    assert token_to_sprite_code("bP") == "PB"


def build(cell_size=10):
    return SpriteLoader(assets_dir=None, skin="pieces4", cell_size=cell_size)


def test_cooldown_fade_at_fraction_zero_fills_the_whole_cell():
    frame = build().load_cooldown_fade_frame(0.0)
    assert (frame.img[:, :, 3] == 160).all()


def test_cooldown_fade_at_fraction_one_is_fully_transparent():
    frame = build().load_cooldown_fade_frame(1.0)
    assert (frame.img[:, :, 3] == 0).all()


def test_cooldown_fade_at_fraction_half_fills_the_bottom_half_only():
    frame = build().load_cooldown_fade_frame(0.5)
    alpha = frame.img[:, :, 3]
    assert (alpha[5:] == 160).all()   # bottom half: fully filled
    assert (alpha[:5] == 0).all()     # top half: still empty


def test_cooldown_fade_boundary_row_is_partially_blended():
    # cell_size=10, fraction=0.45 -> exact_filled=5.5: 5 whole filled rows plus
    # one boundary row blended at 50% alpha, not snapped to a whole row.
    frame = build().load_cooldown_fade_frame(0.45)
    alpha = frame.img[:, :, 3]
    assert (alpha[5:] == 160).all()   # rows fully below the boundary
    assert (alpha[4] == 80).all()     # boundary row: half of 160
    assert (alpha[:4] == 0).all()     # still-empty rows above the boundary


def test_cooldown_fade_color_is_pale_yellow_where_filled():
    frame = build().load_cooldown_fade_frame(0.0)
    assert tuple(frame.img[0, 0, :3]) == (150, 255, 255)


def test_legal_destination_highlight_is_green_for_a_plain_move():
    frame = build().load_legal_destination_highlight(is_capture=False)
    assert tuple(frame.img[0, 0]) == ui_config.LEGAL_MOVE_COLOR + (ui_config.LEGAL_DESTINATION_ALPHA,)


def test_legal_destination_highlight_is_red_for_a_capture():
    frame = build().load_legal_destination_highlight(is_capture=True)
    assert tuple(frame.img[0, 0]) == ui_config.LEGAL_CAPTURE_COLOR + (ui_config.LEGAL_DESTINATION_ALPHA,)


def test_legal_destination_highlights_are_independently_cached():
    loader = build()
    move_frame = loader.load_legal_destination_highlight(is_capture=False)
    capture_frame = loader.load_legal_destination_highlight(is_capture=True)
    move_frame.img[0, 0] = 0  # mutate one - must not bleed into the other's cache or a fresh copy
    assert tuple(capture_frame.img[0, 0]) == ui_config.LEGAL_CAPTURE_COLOR + (ui_config.LEGAL_DESTINATION_ALPHA,)
    fresh = loader.load_legal_destination_highlight(is_capture=False)
    assert tuple(fresh.img[0, 0]) == ui_config.LEGAL_MOVE_COLOR + (ui_config.LEGAL_DESTINATION_ALPHA,)
