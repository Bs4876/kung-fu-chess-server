from model.position import Position


class BoardPrinter:
    def print(self, board) -> str:
        rows = []
        for r in range(board.rows):
            rows.append(" ".join(board.get_piece(Position(r, c)) for c in range(board.cols)))
        return "\n".join(rows)
