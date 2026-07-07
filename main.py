import sys
from engine import ChessEngine
from router import TextCommandRouter

def main():
    # Read all input from standard input
    input_text = sys.stdin.read().strip()
    if not input_text:
        return

    # Split the raw input into individual lines
    lines = [line.strip() for line in input_text.splitlines()]
    
    board_matrix = []
    command_lines = []
    in_board = False

    # Extract the board layout and commands directly from text
    for line in lines:
        if not line:
            continue
        if line.startswith("Board:"):
            in_board = True
            continue
        elif line.startswith("Commands:"):
            in_board = False
            continue
        
        if in_board:
            board_matrix.append(line.split())
        else:
            command_lines.append(line)

    if not board_matrix:
        return

    # Initialize the core game engine and text command router
    engine = ChessEngine(board_matrix)
    router = TextCommandRouter(engine)

    # Process each extracted command line sequentially
    for command in command_lines:
        router.process_command(command)

if __name__ == "__main__":
    main()