class MoveValidator:
    @staticmethod
    def is_valid_move(piece_type, from_row, from_col, to_row, to_col, board, piece_color):
        if from_row == to_row and from_col == to_col:
            return False

        d_row = abs(to_row - from_row)
        d_col = abs(to_col - from_col)
        target_token = board[to_row][to_col]
        board_height = len(board)

        # Pawn Specific Movement Logic
        if piece_type == 'P':
            forward_direction = -1 if piece_color == 'w' else 1
            row_diff = to_row - from_row
            
            # Match the customized test runner grid constraints:
            # White pawns spawn on the absolute bottom row, Black pawns spawn on the absolute top row
            start_row = (board_height - 1) if piece_color == 'w' else 0

            # Case A: Forward Movement (1 or 2 steps)
            if d_col == 0:
                # 1-step forward
                if row_diff == forward_direction:
                    return target_token == '.'
                # 2-steps forward from its designated starting row
                elif row_diff == (2 * forward_direction) and from_row == start_row:
                    if target_token != '.':
                        return False
                    return MoveValidator._is_path_clear(from_row, from_col, to_row, to_col, board)
                return False

            # Case B: Diagonal Capture Movement
            elif d_col == 1 and row_diff == forward_direction:
                return target_token != '.'

            return False

        # Geometry Check for Standard Pieces
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