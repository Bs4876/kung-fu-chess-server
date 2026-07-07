class MoveValidator:
    @staticmethod
    def is_valid_move(piece_type, from_row, from_col, to_row, to_col, board, piece_color):
        # Remaining in the exact same spot is an illegal operation
        if from_row == to_row and from_col == to_col:
            return False

        # Calculate absolute vector deltas
        d_row = abs(to_row - from_row)
        d_col = abs(to_col - from_col)
        target_token = board[to_row][to_col]

        # Step 1: Pawn Specific Movement Logic (New for Iteration 5)
        if piece_type == 'P':
            # Determine the required forward step direction based on team color
            # White pawns move up the matrix (-1), Black pawns move down the matrix (+1)
            forward_direction = -1 if piece_color == 'w' else 1
            row_diff = to_row - from_row

            # Case A: Pure Forward Movement (Must be exactly 1 step forward, same column)
            if d_col == 0 and row_diff == forward_direction:
                # Pawns cannot capture forward; destination cell must be completely empty
                return target_token == '.'

            # Case B: Diagonal Capture Movement (Must be exactly 1 step forward and 1 step sideways)
            elif d_col == 1 and row_diff == forward_direction:
                # Pawns can only move diagonally if they are actively capturing an enemy piece
                return target_token != '.'

            # Any other pawn movement (such as moving 2 cells) is strictly illegal in this iteration
            return False

        # Step 2: Geometry Check for Standard Pieces (From Iteration 3)
        is_geometry_valid = False
        if piece_type == 'K':
            is_geometry_valid = d_row <= 1 and d_col <= 1
        elif piece_type == 'R':
            is_geometry_valid = d_row == 0 or d_col == 0
        elif piece_type == 'B':
            is_geometry_valid = d_row == d_col
        elif piece_type == 'Q':
            is_geometry_valid = (d_row == 0 or d_col == 0) or (d_row == d_col)
        elif piece_type == 'N':
            is_geometry_valid = (d_row == 2 and d_col == 1) or (d_row == 1 and d_col == 2)

        if not is_geometry_valid:
            return False

        # Step 3: Path Obstruction Check (From Iteration 4)
        if piece_type in ['K', 'N']:
            return True

        return MoveValidator._is_path_clear(from_row, from_col, to_row, to_col, board)

    @staticmethod
    def _is_path_clear(from_row, from_col, to_row, to_col, board):
        row_step = 0 if from_row == to_row else (1 if to_row > from_row else -1)
        col_step = 0 if from_col == to_col else (1 if to_col > from_col else -1)

        curr_row = from_row + row_step
        curr_col = from_col + col_step

        while curr_row != to_row or curr_col != to_col:
            if board[curr_row][curr_col] != '.':
                return False
            curr_row += row_step
            curr_col += col_step

        return True