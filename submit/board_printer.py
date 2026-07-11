from position import Position


class BoardPrinter:
    def print(self, board_or_snapshot) -> str:
        rows = []
        for r in range(board_or_snapshot.rows):
            rows.append(" ".join(board_or_snapshot.get_piece(Position(r, c)) for c in range(board_or_snapshot.cols)))
        return "\n".join(rows)
