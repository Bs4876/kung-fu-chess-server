from movement import MoveValidator

class ChessEngine:
    def __init__(self, board_matrix):
        self.board = board_matrix
        self.rows = len(board_matrix)
        self.cols = len(board_matrix[0]) if self.rows > 0 else 0
        self.selected_pos = None
        self.game_clock = 0
        self.ongoing_moves = []
        self.pieces_in_flight = set()
        self.game_over = False

    def click(self, x, y):
        self._refresh_board_state()
        if self.game_over:
            return

        row = y // 100
        col = x // 100

        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return

        if (row, col) in self.pieces_in_flight:
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
        self._refresh_board_state()

    def print_board(self):
        self._refresh_board_state()
        for row in self.board:
            print(" ".join(row))

    def _execute_move(self, from_row, from_col, to_row, to_col):
        if self.game_over:
            return

        moving_piece = self.board[from_row][from_col]
        target_piece = self.board[to_row][to_col]
        
        if moving_piece == '.':
            return

        if (from_row, from_col) in self.pieces_in_flight:
            return

        piece_type = moving_piece[1]
        piece_color = moving_piece[0]

        for move in self.ongoing_moves:
            active_piece_token = move[5]
            if active_piece_token[0] != piece_color:
                return

        if target_piece != '.' and target_piece[0] == moving_piece[0]:
            return

        if not MoveValidator.is_valid_move(piece_type, from_row, from_col, to_row, to_col, self.board, piece_color):
            return

        distance = max(abs(to_row - from_row), abs(to_col - from_col))
        travel_time = distance * 1000
        arrival_time = self.game_clock + travel_time

        self.ongoing_moves.append((arrival_time, from_row, from_col, to_row, to_col, moving_piece))
        self.pieces_in_flight.add((from_row, from_col))
        self.selected_pos = None

    def _refresh_board_state(self):
        remaining_moves = []
        self.ongoing_moves.sort(key=lambda m: m[0])

        for move in self.ongoing_moves:
            arrival_time, from_row, from_col, to_row, to_col, piece_token = move
            
            if self.game_over:
                self.pieces_in_flight.discard((from_row, from_col))
                continue

            if self.game_clock >= arrival_time:
                current_target = self.board[to_row][to_col]
                
                if current_target != '.' and current_target[0] == piece_token[0]:
                    self.pieces_in_flight.discard((from_row, from_col))
                    continue

                if current_target != '.' and current_target[1] == 'K':
                    self.game_over = True

                # Upgrade: Pawn Promotion Evaluation upon successful landing
                if piece_token[1] == 'P' and (to_row == 0 or to_row == self.rows - 1):
                    # Replace the token representation with its corresponding color Queen
                    piece_token = piece_token[0] + 'Q'

                if self.board[from_row][from_col] == move[5]: # Verify original token before clearing
                    self.board[from_row][from_col] = '.'
                
                self.board[to_row][to_col] = piece_token
                self.pieces_in_flight.discard((from_row, from_col))
                
                if self.game_over:
                    self.ongoing_moves = []
                    return
            else:
                remaining_moves.append(move)
                
        self.ongoing_moves = remaining_moves