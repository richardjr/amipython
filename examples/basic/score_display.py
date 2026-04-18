"""Score display — demonstrates str() and int_to_str() for rendering numbers.

Tetris-style score/lines/level panel. Press fire to score points, UP to clear
a line, DOWN to level up. Labels are painted once at startup; only the
numeric cells are redrawn, and only on the frames when the values actually
change — the common pattern for flicker-free HUD text.

Controls:
    Fire (Space / LMB)   — +100 score (edge-triggered; one tap = one score)
    Up                   — +1 line
    Down                 — +1 level
    Close the window to exit.
"""

from amiga import Display, Bitmap, palette, int_to_str, joy, run

display = Display(320, 200, bitplanes=3)
screen = Bitmap(320, 200, bitplanes=3)

palette.aga(1, 255, 255, 255)
palette.aga(2, 120, 120, 120)

score: int = 0
lines: int = 0
level: int = 1

prev_score: int = -1
prev_lines: int = -1
prev_level: int = -1


def draw_labels():
    screen.clear()
    screen.print_at(40, 30, "SCORE", color=2)
    screen.print_at(40, 70, "LINES", color=2)
    screen.print_at(40, 110, "LEVEL", color=2)
    screen.print_at(40, 170, "FIRE=+100  UP=LINE  DOWN=LEVEL", color=2)


def update():
    global score, lines, level
    global prev_score, prev_lines, prev_level

    if joy.button_pressed(0):
        score = score + 100
    if joy.up_pressed():
        lines = lines + 1
    if joy.down_pressed():
        level = level + 1

    # Only repaint a numeric cell when its value changes. This eliminates the
    # clear-then-redraw cycle that causes visible flicker in the digits.
    if score != prev_score:
        screen.print_at(140, 30, int_to_str(score, 6), color=1)
        prev_score = score
    if lines != prev_lines:
        screen.print_at(140, 70, int_to_str(lines, 3), color=1)
        prev_lines = lines
    if level != prev_level:
        screen.print_at(140, 110, int_to_str(level, 2), color=1)
        prev_level = level


display.show(screen)
draw_labels()
run(update, until=lambda: False)
