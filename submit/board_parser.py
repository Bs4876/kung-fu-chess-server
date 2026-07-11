from board import Board, EMPTY

VALID_COLORS = {"w", "b"}
VALID_KINDS = {"R", "B", "Q", "N", "K", "P"}


class BoardParser:
    def parse(self, text: str) -> Board:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise ValueError("Empty board definition")
        matrix = [line.split() for line in lines]
        cols = len(matrix[0])
        for row in matrix:
            if len(row) != cols:
                raise ValueError("Inconsistent row length")
            for token in row:
                if token != EMPTY and (len(token) != 2 or token[0] not in VALID_COLORS or token[1] not in VALID_KINDS):
                    raise ValueError(f"Invalid token: {token}")
        return Board(matrix)
