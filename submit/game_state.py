from board import Board


class GameState:
    def __init__(self, board: Board, game_over: bool = False):
        self._board = board
        self._game_over = game_over

    @property
    def board(self) -> Board:
        return self._board

    @property
    def game_over(self) -> bool:
        return self._game_over
