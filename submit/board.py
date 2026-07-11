EMPTY = "."


class Board:
    def __init__(self, matrix):
        if not matrix:
            raise ValueError("Board matrix cannot be empty")
        self._rows = len(matrix)
        self._cols = len(matrix[0])
        for row in matrix:
            if len(row) != self._cols:
                raise ValueError("All rows must have the same length")
        self._matrix = [list(row) for row in matrix]

    @property
    def rows(self):
        return self._rows

    @property
    def cols(self):
        return self._cols

    def in_bounds(self, pos) -> bool:
        return 0 <= pos.row < self._rows and 0 <= pos.col < self._cols

    def get_piece(self, pos) -> str:
        if not self.in_bounds(pos):
            raise IndexError(f"Position out of bounds: {pos}")
        return self._matrix[pos.row][pos.col]

    def set_piece(self, pos, token: str) -> None:
        if not self.in_bounds(pos):
            raise IndexError(f"Position out of bounds: {pos}")
        if token != EMPTY and self._matrix[pos.row][pos.col] != EMPTY:
            raise ValueError(f"Cell {pos} already occupied")
        self._matrix[pos.row][pos.col] = token

    def move_piece(self, src, dst) -> None:
        token = self.get_piece(src)
        self._matrix[dst.row][dst.col] = token
        self._matrix[src.row][src.col] = EMPTY

    def replace_piece(self, pos, token: str) -> None:
        if not self.in_bounds(pos):
            raise IndexError(f"Position out of bounds: {pos}")
        self._matrix[pos.row][pos.col] = token
