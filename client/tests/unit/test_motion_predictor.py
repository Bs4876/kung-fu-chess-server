from animation.motion_predictor import interpolate_pixel
from model.position import Position

CELL_SIZE = 100


def test_zero_progress_is_the_source_pixel():
    x, y = interpolate_pixel(Position(0, 0), Position(0, 3), 0.0, CELL_SIZE)
    assert (x, y) == (0, 0)


def test_full_progress_is_the_destination_pixel():
    x, y = interpolate_pixel(Position(0, 0), Position(0, 3), 1.0, CELL_SIZE)
    assert (x, y) == (300, 0)


def test_halfway_progress_is_the_midpoint():
    x, y = interpolate_pixel(Position(0, 0), Position(0, 4), 0.5, CELL_SIZE)
    assert (x, y) == (200, 0)


def test_interpolates_both_axes_diagonally():
    x, y = interpolate_pixel(Position(0, 0), Position(2, 2), 0.5, CELL_SIZE)
    assert (x, y) == (100, 100)


def test_moving_toward_a_smaller_row_or_col_decreases_the_pixel():
    x, y = interpolate_pixel(Position(4, 4), Position(2, 2), 0.5, CELL_SIZE)
    assert (x, y) == (300, 300)
