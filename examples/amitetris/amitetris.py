"""amitetris — a basic Tetris clone built on amipython Stage 1 features.

Scenes: TITLE → PLAY → GAMEOVER → TITLE.

Controls:
    Left / Right arrow  — shift piece one column (edge-triggered).
    Up arrow            — rotate piece clockwise (edge-triggered).
    Down arrow          — soft drop (held).
    Fire (Space / LMB)  — hard drop (edge-triggered); also starts / confirms.
    P                   — pause.
    ESC                 — exit current scene (play → game over, title → quit).

High scores persist across runs:
    preview: ~/.amipython/amitetris/scores.dat
    Amiga:   PROGDIR:scores.dat
"""

from amiga import Display, Bitmap, palette, run
from amiga import joy, key, rnd, int_to_str, storage
from amiga import K_P, K_ESC

# --- Geometry ---
W: int = 10
H: int = 20
CELL: int = 8
BOARD_X: int = 120
BOARD_Y: int = 20
PANEL_X: int = 210

# --- Piece data: 7 pieces × 4 rotations × 4 cells. Each cell is an index
# 0..15 into a 4x4 grid (row = idx // 4, col = idx % 4). Flat layout so the
# transpiler can store it as a single `list[int]`. ---
piece_data: list[int] = []

# I
piece_data.append(4); piece_data.append(5); piece_data.append(6); piece_data.append(7)
piece_data.append(2); piece_data.append(6); piece_data.append(10); piece_data.append(14)
piece_data.append(4); piece_data.append(5); piece_data.append(6); piece_data.append(7)
piece_data.append(2); piece_data.append(6); piece_data.append(10); piece_data.append(14)
# O
piece_data.append(1); piece_data.append(2); piece_data.append(5); piece_data.append(6)
piece_data.append(1); piece_data.append(2); piece_data.append(5); piece_data.append(6)
piece_data.append(1); piece_data.append(2); piece_data.append(5); piece_data.append(6)
piece_data.append(1); piece_data.append(2); piece_data.append(5); piece_data.append(6)
# T
piece_data.append(4); piece_data.append(5); piece_data.append(6); piece_data.append(9)
piece_data.append(1); piece_data.append(4); piece_data.append(5); piece_data.append(9)
piece_data.append(1); piece_data.append(4); piece_data.append(5); piece_data.append(6)
piece_data.append(1); piece_data.append(5); piece_data.append(6); piece_data.append(9)
# S
piece_data.append(1); piece_data.append(2); piece_data.append(4); piece_data.append(5)
piece_data.append(0); piece_data.append(4); piece_data.append(5); piece_data.append(9)
piece_data.append(1); piece_data.append(2); piece_data.append(4); piece_data.append(5)
piece_data.append(0); piece_data.append(4); piece_data.append(5); piece_data.append(9)
# Z
piece_data.append(0); piece_data.append(1); piece_data.append(5); piece_data.append(6)
piece_data.append(2); piece_data.append(5); piece_data.append(6); piece_data.append(9)
piece_data.append(0); piece_data.append(1); piece_data.append(5); piece_data.append(6)
piece_data.append(2); piece_data.append(5); piece_data.append(6); piece_data.append(9)
# L
piece_data.append(0); piece_data.append(4); piece_data.append(5); piece_data.append(6)
piece_data.append(0); piece_data.append(1); piece_data.append(4); piece_data.append(8)
piece_data.append(0); piece_data.append(1); piece_data.append(2); piece_data.append(6)
piece_data.append(1); piece_data.append(5); piece_data.append(8); piece_data.append(9)
# J
piece_data.append(2); piece_data.append(4); piece_data.append(5); piece_data.append(6)
piece_data.append(0); piece_data.append(4); piece_data.append(8); piece_data.append(9)
piece_data.append(0); piece_data.append(1); piece_data.append(2); piece_data.append(4)
piece_data.append(0); piece_data.append(1); piece_data.append(5); piece_data.append(9)


# --- Board: flat int list, 0 = empty, 1..7 = piece index + 1 (= palette index) ---
board: list[int] = []
for i in range(W * H):
    board.append(0)

# --- Scenes ---
SCENE_TITLE: int = 0
SCENE_PLAY: int = 1
SCENE_GAMEOVER: int = 2

scene: int = SCENE_TITLE
last_scene: int = -1
quit_flag: bool = False

# --- Current piece state ---
piece: int = 0
rot: int = 0
px: int = 3
py: int = 0
next_piece: int = 0

# --- Gameplay state ---
score: int = 0
lines_cleared: int = 0
level: int = 1
drop_counter: int = 0
paused: bool = False

prev_score: int = -1
prev_lines: int = -1
prev_level: int = -1

# --- Top-5 high scores (persisted) ---
top_scores: list[int] = []
for i in range(5):
    top_scores.append(0)

storage.load_int_list("scores", top_scores)

# --- Display setup ---
display = Display(320, 200, bitplanes=3)
screen = Bitmap(320, 200, bitplanes=3)

palette.aga(0, 10, 10, 30)     # dark blue background
palette.aga(1, 60, 220, 240)   # I  — cyan
palette.aga(2, 240, 220, 40)   # O  — yellow
palette.aga(3, 200, 80, 240)   # T  — purple
palette.aga(4, 40, 220, 60)    # S  — green
palette.aga(5, 240, 60, 60)    # Z  — red
palette.aga(6, 240, 140, 40)   # L  — orange
palette.aga(7, 60, 100, 240)   # J  — blue

display.show(screen)


# ================================================================
# Utilities
# ================================================================

def piece_cell(p: int, r: int, i: int) -> int:
    return piece_data[p * 16 + r * 4 + i]


def piece_collides(p: int, r: int, x: int, y: int) -> bool:
    for i in range(4):
        c: int = piece_cell(p, r, i)
        cx: int = c % 4 + x
        cy: int = c // 4 + y
        if cx < 0 or cx >= W or cy >= H:
            return True
        if cy >= 0:
            if board[cy * W + cx] != 0:
                return True
    return False


def lock_piece():
    for i in range(4):
        c: int = piece_cell(piece, rot, i)
        cx: int = c % 4 + px
        cy: int = c // 4 + py
        if cy >= 0 and cy < H and cx >= 0 and cx < W:
            board[cy * W + cx] = piece + 1


def clear_lines() -> int:
    count: int = 0
    y: int = H - 1
    while y >= 0:
        full: bool = True
        for x in range(W):
            if board[y * W + x] == 0:
                full = False
        if full:
            # Shift everything above down by one row.
            yy: int = y
            while yy > 0:
                for x in range(W):
                    board[yy * W + x] = board[(yy - 1) * W + x]
                yy = yy - 1
            for x in range(W):
                board[x] = 0
            count = count + 1
        else:
            y = y - 1
    return count


def spawn_piece():
    global piece, rot, px, py, next_piece
    piece = next_piece
    next_piece = rnd(7)
    rot = 0
    px = 3
    py = 0


def reset_game():
    global score, lines_cleared, level, drop_counter, paused
    global prev_score, prev_lines, prev_level
    global next_piece
    for i in range(W * H):
        board[i] = 0
    score = 0
    lines_cleared = 0
    level = 1
    drop_counter = 0
    paused = False
    prev_score = -1
    prev_lines = -1
    prev_level = -1
    next_piece = rnd(7)
    spawn_piece()


def commit_high_score(final_score: int):
    # Insert in sorted (descending) order into top_scores[0..4].
    inserted: bool = False
    for i in range(5):
        if not inserted and final_score > top_scores[i]:
            # Shift lower scores down one.
            j: int = 4
            while j > i:
                top_scores[j] = top_scores[j - 1]
                j = j - 1
            top_scores[i] = final_score
            inserted = True
    storage.save_int_list("scores", top_scores)


# ================================================================
# Drawing
# ================================================================

def draw_cell(gx: int, gy: int, color: int):
    sx: int = BOARD_X + gx * CELL
    sy: int = BOARD_Y + gy * CELL
    screen.box_filled(sx, sy, sx + CELL - 2, sy + CELL - 2, color)


def draw_piece(p: int, r: int, x: int, y: int, color: int):
    for i in range(4):
        c: int = piece_cell(p, r, i)
        cx: int = c % 4 + x
        cy: int = c // 4 + y
        if cy >= 0:
            draw_cell(cx, cy, color)


def draw_board():
    for y in range(H):
        for x in range(W):
            c: int = board[y * W + x]
            if c > 0:
                draw_cell(x, y, c)
            else:
                draw_cell(x, y, 0)


def draw_frame():
    # Thin border around the well.
    x1: int = BOARD_X - 1
    y1: int = BOARD_Y - 1
    x2: int = BOARD_X + W * CELL
    y2: int = BOARD_Y + H * CELL
    screen.box_filled(x1, y1, x2, y1, 2)
    screen.box_filled(x1, y2, x2, y2, 2)
    screen.box_filled(x1, y1, x1, y2, 2)
    screen.box_filled(x2, y1, x2, y2, 2)


def draw_panel_labels():
    screen.print_at(PANEL_X, 16, "SCORE", color=1)
    screen.print_at(PANEL_X, 48, "LINES", color=1)
    screen.print_at(PANEL_X, 80, "LEVEL", color=1)
    screen.print_at(PANEL_X, 120, "NEXT", color=1)
    screen.print_at(PANEL_X, 178, "P=PAUSE", color=2)


def refresh_panel():
    global prev_score, prev_lines, prev_level
    if score != prev_score:
        screen.print_at(PANEL_X, 28, int_to_str(score, 6), color=2)
        prev_score = score
    if lines_cleared != prev_lines:
        screen.print_at(PANEL_X, 60, int_to_str(lines_cleared, 3), color=2)
        prev_lines = lines_cleared
    if level != prev_level:
        screen.print_at(PANEL_X, 92, int_to_str(level, 2), color=2)
        prev_level = level


def draw_next_preview():
    # Clear the preview box area (5 cells wide × 4 tall).
    for cy in range(4):
        for cx in range(5):
            sx: int = PANEL_X + cx * CELL
            sy: int = 134 + cy * CELL
            screen.box_filled(sx, sy, sx + CELL - 2, sy + CELL - 2, 0)
    # Render the next piece at its canonical rotation-0 position.
    for i in range(4):
        c: int = piece_cell(next_piece, 0, i)
        cx: int = c % 4
        cy: int = c // 4
        sx: int = PANEL_X + cx * CELL
        sy: int = 134 + cy * CELL
        screen.box_filled(sx, sy, sx + CELL - 2, sy + CELL - 2, next_piece + 1)


# ================================================================
# Scene: TITLE
# ================================================================

def enter_title():
    screen.clear()
    screen.print_at(108, 30, "AMITETRIS", color=2)
    screen.print_at(88, 60, "HIGH SCORES", color=1)
    for i in range(5):
        screen.print_at(88, 80 + i * 12,
                        int_to_str(i + 1, 1),
                        int_to_str(top_scores[i], 6),
                        color=2)
    screen.print_at(60, 160, "PRESS FIRE TO START", color=1)
    screen.print_at(100, 176, "ESC TO QUIT", color=2)


def update_title():
    global scene, quit_flag
    if joy.button_pressed(0):
        scene = SCENE_PLAY
    if key.just_pressed(K_ESC):
        quit_flag = True


# ================================================================
# Scene: PLAY
# ================================================================

def enter_play():
    reset_game()
    screen.clear()
    draw_frame()
    draw_panel_labels()
    draw_board()
    draw_next_preview()


def update_play():
    global px, py, rot, drop_counter, scene
    global score, lines_cleared, level, paused

    if key.just_pressed(K_P):
        paused = not paused
        if paused:
            screen.print_at(136, 100, "PAUSED", color=2)
        else:
            # Repaint the board cells that the PAUSED text overdrew.
            for y in range(10, 14):
                for x in range(2, 8):
                    c: int = board[y * W + x]
                    if c > 0:
                        draw_cell(x, y, c)
                    else:
                        draw_cell(x, y, 0)
    if paused:
        return

    if key.just_pressed(K_ESC):
        scene = SCENE_GAMEOVER
        return

    # Erase the current piece before applying input so we redraw cleanly.
    draw_piece(piece, rot, px, py, 0)

    if joy.left_pressed():
        if not piece_collides(piece, rot, px - 1, py):
            px = px - 1
    if joy.right_pressed():
        if not piece_collides(piece, rot, px + 1, py):
            px = px + 1
    if joy.up_pressed():
        new_rot: int = (rot + 1) % 4
        if not piece_collides(piece, new_rot, px, py):
            rot = new_rot

    # Hard drop
    if joy.button_pressed(0):
        while not piece_collides(piece, rot, px, py + 1):
            py = py + 1
        drop_counter = 999  # force lock this frame

    # Gravity
    fall_rate: int = 30 - level * 2
    if fall_rate < 4:
        fall_rate = 4
    if joy.down():
        fall_rate = 2

    drop_counter = drop_counter + 1
    locked: bool = False
    if drop_counter >= fall_rate:
        drop_counter = 0
        if piece_collides(piece, rot, px, py + 1):
            lock_piece()
            # Repaint the cells we just locked — the erase at the top of
            # this function cleared them and lock_piece() only updates
            # board[]. Without this the locked blocks stay invisible.
            draw_piece(piece, rot, px, py, piece + 1)
            locked = True
        else:
            py = py + 1

    if locked:
        n: int = clear_lines()
        if n > 0:
            if n == 1:
                score = score + 100 * level
            elif n == 2:
                score = score + 300 * level
            elif n == 3:
                score = score + 500 * level
            else:
                score = score + 800 * level
            lines_cleared = lines_cleared + n
            level = 1 + lines_cleared // 10
            # Redraw whole board after lines shifted.
            draw_board()

        spawn_piece()
        draw_next_preview()

        if piece_collides(piece, rot, px, py):
            scene = SCENE_GAMEOVER
            return

    # Draw the current piece at its new position.
    draw_piece(piece, rot, px, py, piece + 1)
    refresh_panel()


# ================================================================
# Scene: GAMEOVER
# ================================================================

gameover_entered: bool = False


def enter_gameover():
    global gameover_entered
    if not gameover_entered:
        commit_high_score(score)
        gameover_entered = True
    screen.clear()
    screen.print_at(108, 50, "GAME OVER", color=5)
    screen.print_at(96, 80, "FINAL", int_to_str(score, 6), color=2)
    screen.print_at(80, 100, "LINES", int_to_str(lines_cleared, 3), color=1)
    screen.print_at(80, 120, "LEVEL", int_to_str(level, 2), color=1)
    screen.print_at(68, 160, "PRESS FIRE TO CONTINUE", color=2)


def update_gameover():
    global scene, gameover_entered
    if joy.button_pressed(0):
        scene = SCENE_TITLE
        gameover_entered = False


# ================================================================
# Main loop — single run() with a scene dispatcher
# ================================================================

def update():
    global last_scene
    if scene != last_scene:
        last_scene = scene
        if scene == SCENE_TITLE:
            enter_title()
        elif scene == SCENE_PLAY:
            enter_play()
        else:
            enter_gameover()

    if scene == SCENE_TITLE:
        update_title()
    elif scene == SCENE_PLAY:
        update_play()
    else:
        update_gameover()


next_piece = rnd(7)
spawn_piece()
run(update, until=lambda: quit_flag)
