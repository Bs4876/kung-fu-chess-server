import io
import sys
import runpy
import main
from chess_io.board_parser import BoardParser


def run(input_text, parser=None):
    stdin = io.StringIO(input_text)
    stdout = io.StringIO()
    main.main(parser=parser, stdin=stdin, stdout=stdout)
    return stdout.getvalue().strip()


def test_board_parser_raises_on_empty_text():
    import pytest
    with pytest.raises(ValueError, match="Empty board definition"):
        BoardParser().parse("")


def test_board_parser_raises_on_whitespace_only():
    import pytest
    with pytest.raises(ValueError, match="Empty board definition"):
        BoardParser().parse("   \n  ")


def test_main_empty_input_produces_no_output():
    assert run("") == ""


def test_main_no_board_section_prints_error():
    assert run("Commands:\nprint board") == "ERROR No Board definition found"


def test_main_generic_parser_error():
    class BadParser:
        def parse(self, text):
            raise ValueError("something unexpected")
    assert run("Board:\nwK .\nCommands:\nprint board", parser=BadParser()) == "ERROR something unexpected"


def test_main_empty_command_ignored():
    class InjectEmptyParser(BoardParser):
        pass

    stdin = io.StringIO("Board:\nwK .\nCommands:\nprint board")
    stdout = io.StringIO()
    original_split = main._split_input

    def patched_split(lines):
        board, cmds = original_split(lines)
        return board, [""] + cmds

    real_split = main._split_input
    main._split_input = patched_split
    try:
        main.main(stdin=stdin, stdout=stdout)
    finally:
        main._split_input = real_split

    assert stdout.getvalue().strip() == "wK ."


def test_split_input_skips_empty_lines():
    board_lines, command_lines = main._split_input(["Board:", "", "wK .", "Commands:", "", "print board"])
    assert board_lines == ["wK ."]
    assert command_lines == ["print board"]


def test_main_entrypoint():
    stdin = io.StringIO("")
    stdout = io.StringIO()
    original_stdin, original_stdout = sys.stdin, sys.stdout
    sys.stdin = stdin
    sys.stdout = stdout
    try:
        runpy.run_path(main.__file__, run_name="__main__")
    finally:
        sys.stdin = original_stdin
        sys.stdout = original_stdout


def test_main_jump_command():
    result = run("Board:\nwR . .\nCommands:\njump 50 50\nwait 1000\nprint board")
    assert "wR" in result


def test_main_jump_outside_board_ignored():
    result = run("Board:\nwR . .\nCommands:\njump 9999 9999\nprint board")
    assert "wR" in result
