"""Keyboard input demo — pressed, just_pressed, just_released.

Shows all three key query modes. Hold SPACE to fill the left bar. Tap P to
increment a counter by exactly 1 per press (proves edge detection). Release
ESC to exit.

Controls:
    SPACE (held)   — fills left bar while held.
    P (taps)       — increments counter; one press = one increment.
    ESC (release)  — exits the program.
"""

from amiga import Display, Bitmap, palette, key, run
from amiga import K_SPACE, K_P, K_ESC

display = Display(320, 200, bitplanes=3)
screen = Bitmap(320, 200, bitplanes=3)

palette.aga(1, 80, 80, 80)
palette.aga(2, 40, 200, 40)
palette.aga(3, 240, 200, 40)
palette.aga(4, 220, 60, 60)

p_count: int = 0
should_quit: bool = False


def update():
    global p_count, should_quit

    if key.just_pressed(K_P):
        p_count = p_count + 1
    if key.just_released(K_ESC):
        should_quit = True

    screen.clear()

    # Left column: held indicator for SPACE.
    screen.box_filled(20, 20, 120, 180, 1)
    if key.pressed(K_SPACE):
        screen.box_filled(22, 22, 118, 178, 2)

    # Middle column: blocks stacking by P taps (one per tap).
    screen.box_filled(140, 20, 220, 180, 1)
    stack: int = p_count
    if stack > 8:
        stack = 8
    for i in range(stack):
        screen.box_filled(142, 178 - (i + 1) * 18, 218, 178 - i * 18 - 2, 3)

    # Right column: ESC-release flag (lights up just once per press).
    screen.box_filled(240, 20, 300, 80, 1)
    if should_quit:
        screen.box_filled(242, 22, 298, 78, 4)


display.show(screen)
run(update, until=lambda: should_quit)
