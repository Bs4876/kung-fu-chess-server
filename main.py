# Repository URL: https://github.com/Bs4876/kung-fu-chess-server

import sys
from game_io.board_parser import BoardParser
from game_io.board_printer import BoardPrinter
from game_engine_pkg.game_engine import GameEngine
from model.board import EMPTY
from model.position import Position

CELL_SIZE = 100


def main():
    input_text = sys.stdin.read().strip()
    if not input_text:
        return

    lines = [line.strip() for line in input_text.splitlines()]
    board_lines, command_lines = _split_input(lines)

    if not board_lines:
        print("ERROR No Board definition found")
        return

    parser = BoardParser()
    try:
        board = parser.parse("\n".join(board_lines))
    except ValueError as e:
        msg = str(e)
        if "Inconsistent" in msg:
            print("ERROR ROW_WIDTH_MISMATCH")
        elif "Invalid token" in msg:
            print("ERROR UNKNOWN_TOKEN")
        else:
            print(f"ERROR {msg}")
        return

    engine = GameEngine(board)
    printer = BoardPrinter()
    selected = [None]

    for command in command_lines:
        parts = command.split()
        if not parts:
            continue

        if parts[0] == "click" and len(parts) == 3:
            _handle_click(int(parts[1]), int(parts[2]), engine, selected, board)

        elif parts[0] == "jump" and len(parts) == 3:
            _handle_jump(int(parts[1]), int(parts[2]), engine, selected, board)

        elif parts[0] == "wait" and len(parts) == 2:
            engine.wait(int(parts[1]))

        elif parts[0] == "print" and len(parts) == 2 and parts[1] == "board":
            print(printer.print(engine.snapshot().board))


def _split_input(lines):
    board_lines = []
    command_lines = []
    in_board = False
    in_commands = False

    for line in lines:
        if not line:
            continue
        if line in ("Board:", "Board"):
            in_board = True
            in_commands = False
            continue
        if line in ("Commands:", "Commands"):
            in_board = False
            in_commands = True
            continue
        if in_board:
            board_lines.append(line)
        elif in_commands:
            command_lines.append(line)

    return board_lines, command_lines


def _handle_click(x, y, engine, selected, board):
    col, row = x // CELL_SIZE, y // CELL_SIZE
    pos = Position(row, col)

    if not board.in_bounds(pos):
        selected[0] = None
        return

    if selected[0] is None:
        if board.get_piece(pos) != EMPTY:
            selected[0] = pos
    else:
        token_at_pos = board.get_piece(pos)
        selected_token = board.get_piece(selected[0])
        if token_at_pos != EMPTY and selected_token != EMPTY and token_at_pos[0] == selected_token[0]:
            selected[0] = pos
        else:
            engine.request_move(selected[0], pos)
            selected[0] = None


def _handle_jump(x, y, engine, selected, board):
    col, row = x // CELL_SIZE, y // CELL_SIZE
    pos = Position(row, col)
    if board.in_bounds(pos) and board.get_piece(pos) != EMPTY:
        engine.request_jump(pos)
        selected[0] = None


if __name__ == "__main__":
    main()
