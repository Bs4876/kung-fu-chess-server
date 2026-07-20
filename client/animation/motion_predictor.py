"""Pure pixel interpolation for a piece currently mid-flight.

The engine never exposes a mid-flight position (see GameFacade) - this is what
turns a (source, destination, progress) prediction into an actual pixel to draw at.
"""


def interpolate_pixel(source, destination, progress: float, cell_size: int) -> tuple[float, float]:
    """Linearly interpolate the top-left pixel of a piece moving source -> destination.

    progress: 0.0 at the start of the motion, 1.0 once it's predicted to arrive.
    """
    src_x, src_y = source.col * cell_size, source.row * cell_size
    dst_x, dst_y = destination.col * cell_size, destination.row * cell_size
    x = src_x + (dst_x - src_x) * progress
    y = src_y + (dst_y - src_y) * progress
    return x, y
