# Repository URL: https://github.com/Bs4876/kung-fu-chess-server

import sys
from chess_io.board_parser import BoardParser
from chess_io.board_printer import BoardPrinter
from engine.game_engine import GameEngine
from input.board_mapper import BoardMapper
from input.controller import Controller
from config import CELL_SIZE


def main(parser=None, stdin=None, stdout=None):
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    parser = parser or BoardParser()

    input_text = stdin.read().strip()
    if not input_text:
        return

    lines = [line.strip() for line in input_text.splitlines()]
    board_lines, command_lines = _split_input(lines)

    if not board_lines:
        print("ERROR No Board definition found", file=stdout)
        return

    try:
        board = parser.parse("\n".join(board_lines))
    except ValueError as e:
        msg = str(e)
        if "Inconsistent" in msg:
            print("ERROR ROW_WIDTH_MISMATCH", file=stdout)
        elif "Invalid token" in msg:
            print("ERROR UNKNOWN_TOKEN", file=stdout)
        else:
            print(f"ERROR {msg}", file=stdout)
        return

    engine = GameEngine(board)
    printer = BoardPrinter()
    mapper = BoardMapper(rows=board.rows, cols=board.cols, cell_size=CELL_SIZE)
    controller = Controller(engine, mapper)

    for command in command_lines:
        parts = command.split()
        if not parts:
            continue

        if parts[0] == "click" and len(parts) == 3:
            controller.click(int(parts[1]), int(parts[2]))

        elif parts[0] == "jump" and len(parts) == 5:
            source = mapper.pixel_to_cell(int(parts[1]), int(parts[2]))
            destination = mapper.pixel_to_cell(int(parts[3]), int(parts[4]))
            if source is not None and destination is not None:
                engine.request_jump(source, destination)

        elif parts[0] == "wait" and len(parts) == 2:
            engine.wait(int(parts[1]))

        elif parts[0] == "print" and len(parts) == 2 and parts[1] == "board":
            print(printer.print(engine.snapshot()), file=stdout)


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


if __name__ == "__main__":
    main()
