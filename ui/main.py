"""Stage 1: draw a single static frame of the opening position and show it."""

import server_bridge  # noqa: F401  (must run before any server-rooted import below)

import ui_config
from chess_io.board_parser import BoardParser
from config import CELL_SIZE
from engine.game_engine import GameEngine
from graphics.renderer import BoardRenderer
from graphics.sprite_loader import SpriteLoader
from model.starting_position import STARTING_POSITION


def build_engine() -> GameEngine:
    """Parse the standard opening position into a real, running GameEngine."""
    board = BoardParser().parse(STARTING_POSITION)
    return GameEngine(board)


def main() -> None:
    engine = build_engine()
    sprite_loader = SpriteLoader(ui_config.ASSETS_DIR, ui_config.SKIN, CELL_SIZE)
    renderer = BoardRenderer(sprite_loader, CELL_SIZE)

    canvas = renderer.render(engine.snapshot())
    canvas.show()  # blocking one-shot window; fine until Stage 2 adds a real loop


if __name__ == "__main__":
    main()
