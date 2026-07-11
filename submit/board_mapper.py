from typing import Optional
from position import Position
from config import CELL_SIZE


class BoardMapper:
    def __init__(self, rows: int, cols: int, cell_size: int = CELL_SIZE):
        self._rows = rows
        self._cols = cols
        self._cell_size = cell_size

    def pixel_to_cell(self, x: int, y: int) -> Optional[Position]:
        col = x // self._cell_size
        row = y // self._cell_size
        if 0 <= row < self._rows and 0 <= col < self._cols:
            return Position(row, col)
        return None
