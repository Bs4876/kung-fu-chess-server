import io
import main


def run(input_text):
    stdin = io.StringIO(input_text)
    stdout = io.StringIO()
    main.main(stdin=stdin, stdout=stdout)
    return stdout.getvalue().strip()


# ── Board parsing ────────────────────────────────────────────────────────────

def test_parse_empty_board_3x3():
    assert run("Board:\n. . .\n. . .\n. . .\nCommands:\nprint board") == ". . .\n. . .\n. . ."


def test_parse_rectangular_board_3x4():
    assert run("Board:\nwK . . bK\n. . . .\nwR . . bR\nCommands:\nprint board") == "wK . . bK\n. . . .\nwR . . bR"


def test_parse_piece_tokens_and_colors():
    assert run("Board:\nwK . bQ\n. wN .\nbP . wR\nCommands:\nprint board") == "wK . bQ\n. wN .\nbP . wR"


def test_reject_unknown_token():
    assert run("Board:\nwK xZ\n. .\nCommands:\nprint board") == "ERROR UNKNOWN_TOKEN"


def test_reject_row_width_mismatch():
    assert run("Board:\nwK . .\n. bK\nCommands:\nprint board") == "ERROR ROW_WIDTH_MISMATCH"


# ── Controller / selection ───────────────────────────────────────────────────

def test_select_piece_by_center_click():
    assert run("Board:\nwK . .\n. . .\n. . .\nCommands:\nclick 50 50\nclick 150 150\nwait 1000\nprint board") == ". . .\n. wK .\n. . ."


def test_click_empty_cell_does_not_select():
    assert run("Board:\nwK . .\n. . .\n. . .\nCommands:\nclick 150 150\nclick 250 250\nwait 1000\nprint board") == "wK . .\n. . .\n. . ."


def test_click_outside_board_is_ignored():
    assert run("Board:\nwK . .\n. . .\n. . .\nCommands:\nclick 350 50\nclick -10 50\nprint board") == "wK . .\n. . .\n. . ."


def test_clicking_another_piece_replaces_selection():
    assert run("Board:\nwR . wK\n. . .\nCommands:\nclick 50 50\nclick 250 50\nclick 250 150\nwait 1000\nprint board") == "wR . .\n. . wK"


# ── Movement rules ───────────────────────────────────────────────────────────

def test_king_one_step_valid():
    assert run("Board:\nwK . .\n. . .\n. . .\nCommands:\nclick 50 50\nclick 150 150\nwait 1000\nprint board") == ". . .\n. wK .\n. . ."


def test_king_two_steps_invalid():
    assert run("Board:\nwK . .\n. . .\n. . .\nCommands:\nclick 50 50\nclick 250 250\nwait 1000\nprint board") == "wK . .\n. . .\n. . ."


def test_rook_straight_valid():
    assert run("Board:\nwR . .\nCommands:\nclick 50 50\nclick 250 50\nwait 2000\nprint board") == ". . wR"


def test_rook_diagonal_invalid():
    assert run("Board:\nwR . .\n. . .\n. . .\nCommands:\nclick 50 50\nclick 150 150\nwait 1000\nprint board") == "wR . .\n. . .\n. . ."


def test_bishop_diagonal_valid():
    assert run("Board:\nwB . .\n. . .\n. . .\nCommands:\nclick 50 50\nclick 250 250\nwait 2000\nprint board") == ". . .\n. . .\n. . wB"


def test_knight_L_valid():
    assert run("Board:\nwN . .\n. . .\n. . .\nCommands:\nclick 50 50\nclick 150 250\nwait 3000\nprint board") == ". . .\n. . .\n. wN ."


def test_queen_diagonal_valid():
    assert run("Board:\nwQ . .\n. . .\n. . .\nCommands:\nclick 50 50\nclick 250 250\nwait 2000\nprint board") == ". . .\n. . .\n. . wQ"


def test_rook_blocked_by_own_piece():
    assert run("Board:\nwR wP .\nCommands:\nclick 50 50\nclick 250 50\nwait 2000\nprint board") == "wR wP ."


def test_bishop_blocked_by_own_piece():
    assert run("Board:\nwB . .\n. wP .\n. . .\nCommands:\nclick 50 50\nclick 250 250\nwait 2000\nprint board") == "wB . .\n. wP .\n. . ."


def test_knight_jumps_over_blockers():
    assert run("Board:\nwN wP .\nwP . .\n. . .\nCommands:\nclick 50 50\nclick 150 250\nwait 3000\nprint board") == ". wP .\nwP . .\n. wN ."


def test_cannot_capture_own_piece():
    assert run("Board:\nwR . wP\nCommands:\nclick 50 50\nclick 250 50\nwait 2000\nprint board") == "wR . wP"


def test_rook_captures_enemy_at_destination():
    assert run("Board:\nwR . bR\nCommands:\nclick 50 50\nclick 250 50\nwait 2000\nprint board") == ". . wR"


def test_pawn_cannot_capture_forward():
    assert run("Board:\n. bR .\n. wP .\n. . .\nCommands:\nclick 150 150\nclick 150 50\nwait 1000\nprint board") == ". bR .\n. wP .\n. . ."


def test_knight_cannot_land_on_friendly_piece():
    assert run("Board:\n. wP .\n. . .\nwN . .\nCommands:\nclick 50 250\nclick 150 50\nwait 1000\nprint board") == ". wP .\n. . .\nwN . ."


def test_cannot_start_move_through_friendly_piece():
    assert run("Board:\n. . .\nwR wP .\n. . .\nCommands:\nclick 50 150\nclick 250 150\nwait 2000\nprint board") == ". . .\nwR wP .\n. . ."


# ── Real-time timing ─────────────────────────────────────────────────────────

def test_one_cell_move_before_arrival_board_unchanged():
    assert run("Board:\nwR . .\nCommands:\nclick 50 50\nclick 150 50\nwait 500\nprint board") == "wR . ."


def test_two_cell_move_before_and_after_arrival():
    assert run("Board:\nwR . .\nCommands:\nclick 50 50\nclick 250 50\nwait 1000\nprint board\nwait 1000\nprint board") == "wR . .\n. . wR"


def test_no_cooldown_state_in_common_route():
    assert run("Board:\nwR . .\nCommands:\nclick 50 50\nclick 150 50\nwait 1000\nprint board") == ". wR ."


def test_can_move_again_after_arrival_without_cooldown():
    assert run("Board:\nwR . .\nCommands:\nclick 50 50\nclick 150 50\nwait 1000\nclick 150 50\nclick 250 50\nwait 1000\nprint board") == ". . wR"


def test_piece_is_ready_after_arrival_without_cooldown():
    assert run("Board:\nwR . .\nCommands:\nclick 50 50\nclick 150 50\nwait 1000\nclick 150 50\nclick 250 50\nwait 1000\nprint board") == ". . wR"


def test_moving_piece_ignores_redirect():
    assert run("Board:\nwR . .\nCommands:\nclick 50 50\nclick 250 50\nwait 1000\nclick 50 50\nclick 150 50\nwait 1000\nprint board") == ". . wR"


# ── Common route constraints ─────────────────────────────────────────────────

def test_opposite_colors_do_not_move_concurrently_in_common_route():
    assert run("Board:\nwR . .\n. . .\nbR . .\nCommands:\nclick 50 50\nclick 250 50\nclick 50 250\nclick 250 250\nwait 2000\nprint board") == ". . wR\n. . .\nbR . ."


def test_premove_does_not_execute_in_common_route():
    assert run("Board:\nwR . .\nCommands:\nclick 50 50\nclick 150 50\nclick 50 50\nclick 250 50\nwait 2000\nprint board") == ". wR ."


def test_dynamic_block_tactic_not_in_common_route():
    assert run("Board:\n. . . .\nwQ . . bK\n. . bP .\n. . . .\nCommands:\nclick 50 150\nclick 350 150\nwait 200\nclick 250 250\nclick 250 150\nwait 3000\nprint board") == ". . . .\n. . . wQ\n. . bP .\n. . . ."


# ── Capture and game over ────────────────────────────────────────────────────

def test_king_capture_ends_game():
    assert run("Board:\nwR . bK\nCommands:\nclick 50 50\nclick 250 50\nwait 2000\nprint board") == ". . wR"


def test_no_moves_after_game_over():
    assert run("Board:\nwR . bK\nbR . .\nCommands:\nclick 50 50\nclick 250 50\nwait 2000\nclick 50 150\nclick 150 150\nwait 1000\nprint board") == ". . wR\nbR . ."


def test_enemy_collision_white_started_first():
    assert run("Board:\nwR . . bR\nCommands:\nclick 50 50\nclick 350 50\nclick 350 50\nclick 50 50\nwait 3000\nprint board") == ". . . wR"


def test_enemy_collision_black_started_first():
    assert run("Board:\nwR . . bR\nCommands:\nclick 350 50\nclick 50 50\nclick 50 50\nclick 350 50\nwait 3000\nprint board") == "bR . . ."



# ── Pawn rules ───────────────────────────────────────────────────────────────

def test_white_pawn_moves_one_step():
    assert run("Board:\n. . . .\n. . . .\n. wP . .\n. . . .\nCommands:\nclick 150 250\nclick 150 150\nwait 1000\nprint board") == ". . . .\n. wP . .\n. . . .\n. . . ."


def test_black_pawn_moves_one_step():
    assert run("Board:\n. . . .\n. bP . .\n. . . .\n. . . .\nCommands:\nclick 150 150\nclick 150 250\nwait 1000\nprint board") == ". . . .\n. . . .\n. bP . .\n. . . ."


def test_pawn_no_double_move():
    assert run("Board:\n. . .\n. . .\n. wP .\n. . .\nCommands:\nclick 150 250\nclick 150 50\nwait 2000\nprint board") == ". . .\n. . .\n. wP .\n. . ."


def test_pawn_captures_diagonally():
    assert run("Board:\n. . . .\n. . . .\nbP . . .\n. wP . .\nCommands:\nclick 150 350\nclick 50 250\nwait 1000\nprint board") == ". . . .\n. . . .\nwP . . .\n. . . ."


def test_pawn_cannot_capture_forward():
    assert run("Board:\n. bR .\n. wP .\n. . .\nCommands:\nclick 150 150\nclick 150 50\nwait 1000\nprint board") == ". bR .\n. wP .\n. . ."
