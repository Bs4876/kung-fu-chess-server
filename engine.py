from movement import MoveValidator

class ChessEngine:
    def __init__(self, board_matrix):
        self.board = board_matrix
        self.rows = len(board_matrix)
        self.cols = len(board_matrix[0]) if self.rows > 0 else 0
        self.selected_pos = None  # Stores (row, col)
        self.game_clock = 0       # Cumulative system clock time in milliseconds
        
        # Tracks active movements: (arrival_time, from_row, from_col, to_row, to_col, piece_token)
        self.ongoing_moves = []
        
        # New: Tracks source positions of pieces that are currently traveling and locked
        self.pieces_in_flight = set()

    def click(self, x, y):
        self._refresh_board_state()

        row = y // 100
        col = x // 100

        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return

        # Safeguard: If the clicked square contains a piece currently locked in transit, ignore interaction
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
        moving_piece = self.board[from_row][from_col]
        target_piece = self.board[to_row][to_col]
        
        if moving_piece == '.':
            return

        # Double check that the piece we are trying to move isn't already flying
        if (from_row, from_col) in self.pieces_in_flight:
            return

        piece_type = moving_piece[1]
        piece_color = moving_piece[0]

        if target_piece != '.' and target_piece[0] == moving_piece[0]:
            return

        if not MoveValidator.is_valid_move(piece_type, from_row, from_col, to_row, to_col, self.board, piece_color):
            return

        # Calculate movement duration (1000ms per cell of Chebyshev distance)
        distance = max(abs(to_row - from_row), abs(to_col - from_col))
        travel_time = distance * 1000
        arrival_time = self.game_clock + travel_time

        # Schedule the movement queue and lock the source tile position
        self.ongoing_moves.append((arrival_time, from_row, from_col, to_row, to_col, moving_piece))
        self.pieces_in_flight.add((from_row, from_col))
        
        self.selected_pos = None

    def _refresh_board_state(self):
        """Processes and commits historical movements whose arrival times have been reached."""
        remaining_moves = []
        
        # Sort chronologically to resolve movements in order
        self.ongoing_moves.sort(key=lambda m: m[0])

        for move in self.ongoing_moves:
            arrival_time, from_row, from_col, to_row, to_col, piece_token = move
            
            if self.game_clock >= arrival_time:
                # The piece has arrived! Perform matrix update and unlock positions
                if self.board[from_row][from_col] == piece_token:
                    self.board[from_row][from_col] = '.'
                self.board[to_row][to_col] = piece_token
                
                # Safely release the transit lock on this source square coordinates
                self.pieces_in_flight.discard((from_row, from_col))
            else:
                remaining_moves.append(move)
                
        self.ongoing_moves = remaining_moves