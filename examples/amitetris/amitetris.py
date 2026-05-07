"""amitetris — basic Tetris clone built on amipython Stage 1 + Stage 2 features.

Scenes: TITLE → PLAY → GAMEOVER → TITLE.

Controls:
    Left / Right arrow  — shift piece one column (edge-triggered).
    Up arrow            — rotate piece clockwise (edge-triggered).
    Down arrow          — soft drop (held).
    Fire (Space / LMB)  — hard drop (edge-triggered); also starts / confirms.
    P                   — pause.
    ESC                 — abandon current game.

High scores persist to PROGDIR:scores.dat (Amiga) or
~/.amipython/amitetris/scores.dat (preview).

Stage-2 features used:
    shuffle()            — 7-bag piece randomiser
    bm.print_centered    — title, pause, game-over banners
    bm.print_right       — right-aligned score-panel values
    bm.clear_rect        — region redraws (panel values, pause banner, next preview)
"""

from dataclasses import dataclass
from amiga import Display, Bitmap, palette, run, rnd
from amiga import joy, key, int_to_str, shuffle, storage, music, sfx
from amiga import K_P, K_ESC

# --- SFX slots ---
SFX_LOCK: int = 0
SFX_ROTATE: int = 1
SFX_CLEAR: int = 2
SFX_TETRIS: int = 3
SFX_GAMEOVER: int = 4

# --- Geometry ---
W: int = 10
H: int = 20
CELL: int = 8
BOARD_X: int = 120
BOARD_Y: int = 20
PANEL_X: int = 210

# --- Piece data: 7 pieces × 4 rotations × 4 cells, each cell index 0..15. ---
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


# --- Board: flat int list. 0 = empty, 1..7 = piece index + 1 = palette colour. ---
board: list[int] = []
for i in range(W * H):
    board.append(0)

# --- 7-bag randomiser state: bag[0..6] reshuffled every time it empties. ---
bag: list[int] = []
for i in range(7):
    bag.append(i)
bag_pos: int = 7   # forces initial fill on first draw

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
prev_paused: bool = False
prev_score: int = -1
prev_lines: int = -1
prev_level: int = -1

# --- Top-5 high scores ---
top_scores: list[int] = []
for i in range(5):
    top_scores.append(0)

storage.load_int_list("scores", top_scores)

# --- Display setup ---
display = Display(320, 200, bitplanes=3)
screen = Bitmap(320, 200, bitplanes=3)

palette.aga(0, 10, 10, 30)
palette.aga(1, 60, 220, 240)   # I
palette.aga(2, 240, 220, 40)   # O
palette.aga(3, 200, 80, 240)   # T
palette.aga(4, 40, 220, 60)    # S
palette.aga(5, 240, 60, 60)    # Z
palette.aga(6, 240, 140, 40)   # L
palette.aga(7, 60, 100, 240)   # J

display.show(screen)

# --- Audio ---
music.load("data/music.mod")
sfx.load(SFX_LOCK, "data/lock.wav")
sfx.load(SFX_ROTATE, "data/rotate.wav")
sfx.load(SFX_CLEAR, "data/clear.wav")
sfx.load(SFX_TETRIS, "data/tetris.wav")
sfx.load(SFX_GAMEOVER, "data/gameover.wav")
music.play()
music.volume(24)   # 0..64 — keep music in the background so SFX dominate


# ================================================================
# Starfield — top-down drifting stars in the left margin only.
# x < STAR_BAND_X is a clean band in both scenes (well starts at BOARD_X=120;
# title text only reaches down to x=84 in the worst case), so animated stars
# never collide with UI and we can simply plot 0 to erase. Speeds 1..3, with
# the fastest stars rendered in bright yellow for parallax depth.
# ================================================================

STAR_BAND_X: int = 80
NUM_STARS: int = 50


@dataclass
class Star:
    x: int
    y: int
    speed: int
    color: int


stars: list[Star] = []
for i in range(NUM_STARS):
    spd: int = 1 + rnd(3)
    col: int = 1
    if spd >= 3:
        col = 2
    stars.append(Star(
        x=rnd(STAR_BAND_X),
        y=rnd(200),
        speed=spd,
        color=col,
    ))


def animate_stars():
    for star in stars:
        screen.plot(star.x, star.y, 0)
        new_y: int = star.y + star.speed
        if new_y >= 200:
            new_y = new_y - 200
        star.y = new_y
        screen.plot(star.x, new_y, star.color)


# ================================================================
# 7-bag randomiser
# ================================================================

def draw_next_from_bag() -> int:
    global bag_pos
    if bag_pos >= 7:
        shuffle(bag)
        bag_pos = 0
    v: int = bag[bag_pos]
    bag_pos = bag_pos + 1
    return v


# ================================================================
# Piece / board utilities
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
    next_piece = draw_next_from_bag()
    rot = 0
    px = 3
    py = 0


def reset_game():
    global score, lines_cleared, level, drop_counter, paused, prev_paused
    global prev_score, prev_lines, prev_level, next_piece, bag_pos
    for i in range(W * H):
        board[i] = 0
    score = 0
    lines_cleared = 0
    level = 1
    drop_counter = 0
    paused = False
    prev_paused = False
    prev_score = -1
    prev_lines = -1
    prev_level = -1
    bag_pos = 7
    next_piece = draw_next_from_bag()
    spawn_piece()


def commit_high_score(final_score: int):
    inserted: bool = False
    for i in range(5):
        if not inserted and final_score > top_scores[i]:
            j: int = 4
            while j > i:
                top_scores[j] = top_scores[j - 1]
                j = j - 1
            top_scores[i] = final_score
            inserted = True
    # storage.save_int_list("scores", top_scores)  # disabled — diagnosing write-protected disk hang


# ================================================================
# Drawing helpers
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


# Score / lines / level are right-aligned under their labels so digits don't
# jitter when they gain a digit. Right edge ends at the end of "LINES" etc.
PANEL_RIGHT: int = PANEL_X + 6 * 8   # "SCORE" is 5 chars but pad to 6.


def refresh_panel():
    global prev_score, prev_lines, prev_level
    if score != prev_score:
        screen.clear_rect(PANEL_X, 28, 7 * 8, 8)
        screen.print_right(PANEL_RIGHT, 28, int_to_str(score, 6), color=2)
        prev_score = score
    if lines_cleared != prev_lines:
        screen.clear_rect(PANEL_X, 60, 7 * 8, 8)
        screen.print_right(PANEL_RIGHT, 60, int_to_str(lines_cleared, 3), color=2)
        prev_lines = lines_cleared
    if level != prev_level:
        screen.clear_rect(PANEL_X, 92, 7 * 8, 8)
        screen.print_right(PANEL_RIGHT, 92, int_to_str(level, 2), color=2)
        prev_level = level


NEXT_X: int = PANEL_X
NEXT_Y: int = 134
NEXT_BOX_W: int = 5 * CELL
NEXT_BOX_H: int = 4 * CELL


def draw_next_preview():
    screen.clear_rect(NEXT_X, NEXT_Y, NEXT_BOX_W, NEXT_BOX_H)
    for i in range(4):
        c: int = piece_cell(next_piece, 0, i)
        cx: int = c % 4
        cy: int = c // 4
        sx: int = NEXT_X + cx * CELL
        sy: int = NEXT_Y + cy * CELL
        screen.box_filled(sx, sy, sx + CELL - 2, sy + CELL - 2, next_piece + 1)


PAUSE_Y: int = 92
PAUSE_H: int = 10


def draw_pause_banner(on: bool):
    # Pause text is centered across the whole screen. Clear the band either
    # way; board cells in that band are repainted by the next frame's logic
    # and animated stars in the left margin re-emerge as their drift advances
    # past the band (no instant redraw — the dark band reads as "paused").
    screen.clear_rect(0, PAUSE_Y, 320, PAUSE_H)
    if on:
        screen.print_centered(PAUSE_Y, "PAUSED", color=2)


# ================================================================
# Scene: TITLE
# ================================================================

def enter_title():
    enter_title_or_play_restore_bg()
    screen.clear()
    screen.print_centered(24, "AMITETRIS", color=2)
    screen.print_centered(54, "HIGH SCORES", color=1)
    for i in range(5):
        screen.print_at(88, 74 + i * 12,
                        int_to_str(i + 1, 1), ".", color=1)
        screen.print_right(232, 74 + i * 12,
                           int_to_str(top_scores[i], 6), color=2)
    screen.print_centered(156, "PRESS FIRE TO START", color=1)
    screen.print_centered(176, "ESC TO QUIT", color=2)


def update_title():
    global scene, quit_flag
    animate_stars()
    if joy.button_pressed(0):
        scene = SCENE_PLAY
    if key.just_pressed(K_ESC):
        quit_flag = True


# ================================================================
# Scene: PLAY
# ================================================================

def enter_play():
    enter_title_or_play_restore_bg()
    reset_game()
    screen.clear()
    draw_frame()
    draw_panel_labels()
    draw_board()
    draw_next_preview()


def update_play():
    global px, py, rot, drop_counter, scene
    global score, lines_cleared, level, paused, prev_paused

    if key.just_pressed(K_P):
        paused = not paused

    # On pause transitions, draw or clear the banner; on unpause we
    # additionally repaint the board cells that were underneath it.
    if paused != prev_paused:
        draw_pause_banner(paused)
        if not paused:
            for y in range(H):
                sy_top: int = BOARD_Y + y * CELL
                if sy_top + CELL <= PAUSE_Y or sy_top >= PAUSE_Y + PAUSE_H:
                    continue
                for x in range(W):
                    c: int = board[y * W + x]
                    draw_cell(x, y, c)
        prev_paused = paused

    if paused:
        return

    # Drift the starfield every active frame (skipped when paused so the
    # field freezes with the gameplay).
    animate_stars()

    if key.just_pressed(K_ESC):
        scene = SCENE_GAMEOVER
        return

    # Belt-and-braces game-over checks:
    #
    #   1. The current piece is somehow already colliding. Shouldn't happen
    #      under normal flow, but if it does we're stuck — end the game.
    #   2. NO piece of any type can spawn at the default position (3, 0)
    #      without colliding. The board is truly full at the top.
    #
    # Both checks are evaluated every frame so the game can never "not end."
    if piece_collides(piece, rot, px, py):
        scene = SCENE_GAMEOVER
        return

    any_fits: bool = False
    probe_p: int = 0
    for probe_p in range(7):
        if not any_fits:
            if not piece_collides(probe_p, 0, 3, 0):
                any_fits = True
    if not any_fits:
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
            sfx.play(SFX_ROTATE, volume=40)

    # Hard drop
    if joy.button_pressed(0):
        while not piece_collides(piece, rot, px, py + 1):
            py = py + 1
        drop_counter = 999

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
            draw_piece(piece, rot, px, py, piece + 1)
            locked = True
            sfx.play(SFX_LOCK, volume=48)
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
            draw_board()
            if n >= 4:
                sfx.play(SFX_TETRIS, volume=64)
            else:
                sfx.play(SFX_CLEAR, volume=56)

        spawn_piece()
        draw_next_preview()

        if piece_collides(piece, rot, px, py):
            scene = SCENE_GAMEOVER
            return

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
        sfx.play(SFX_GAMEOVER, volume=64)
        gameover_entered = True
    # Dark red background so the scene transition is visually obvious even
    # if individual glyph cells fail to paint on some hardware.
    palette.aga(0, 80, 0, 0)
    screen.clear()
    screen.print_centered(48, "GAME OVER", color=5)
    screen.print_centered(80, "FINAL", int_to_str(score, 6), color=2)
    screen.print_centered(100, "LINES", int_to_str(lines_cleared, 3), color=1)
    screen.print_centered(120, "LEVEL", int_to_str(level, 2), color=1)
    screen.print_centered(156, "PRESS FIRE TO CONTINUE", color=2)


def enter_title_or_play_restore_bg():
    # Title/play use the dark-blue background; reset after a game-over cycle.
    palette.aga(0, 10, 10, 30)


def update_gameover():
    global scene, gameover_entered
    if joy.button_pressed(0):
        scene = SCENE_TITLE
        gameover_entered = False


# ================================================================
# Main loop — single run() with a scene dispatcher.
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


next_piece = draw_next_from_bag()
spawn_piece()
run(update, until=lambda: quit_flag)
