from movement import MoveValidator

class ChessEngine:
    def __init__(self, board_matrix):
        self.board = board_matrix
        self.rows = len(board_matrix)
        self.cols = len(board_matrix[0]) if self.rows > 0 else 0
        self.selected_pos = None  # Stores (row, col) coordinates of selected piece
        self.game_clock = 0       # Cumulative system clock time in milliseconds

    def click(self, x, y):
        row = y // 100
        col = x // 100

        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return

        token = self.board[row][col]

        if token != '.':
            if self.selected_pos is None:
                self.selected_pos = (row, col)
            else:
                curr_row, curr_col = self.selected_pos
                if token[0] == self.board[curr_row][curr_col][0]:
                    self.selected_pos = (row, col)
                else:
                    self._execute_move(curr_row, curr_col, row, col)
        else:
            if self.selected_pos is not None:
                curr_row, curr_col = self.selected_pos
                self._execute_move(curr_row, curr_col, row, col)

    def wait(self, ms):
        self.game_clock += ms

    def print_board(self):
        for row in self.board:
            print(" ".join(row))

    def _execute_move(self, from_row, from_col, to_row, to_col):
        moving_piece = self.board[from_row][from_col]
        target_piece = self.board[to_row][to_col]
        piece_type = moving_piece[1]
        piece_color = moving_piece[0]  # Extract team color prefix ('w' or 'b')

        if target_piece != '.' and target_piece[0] == moving_piece[0]:
            return

        # Pass the piece color to the validation strategy to support direction-sensitive tokens like Pawns
        if not MoveValidator.is_valid_move(piece_type, from_row, from_col, to_row, to_col, self.board, piece_color):
            return

        self.board[to_row][to_col] = self.board[from_row][from_col]
        self.board[from_row][from_col] = '.'
        self.selected_pos = None