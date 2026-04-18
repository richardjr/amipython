"""Edge-triggered input demo — one tap = one action.

Uses `joy.left_pressed() / right_pressed() / up_pressed() / down_pressed()` so
the cursor moves exactly one tile per directional press, not 50 tiles per second.
`joy.button_pressed(0)` places a marker at the cursor's current cell.

This is the input pattern Tetris needs: rotate and hard-drop must fire once
per press, not once per frame held.

Controls:
    Arrow keys / WASD — step the cursor by one tile.
    Space / LMB       — drop a marker at the current cell.
    Exit: close the window.
"""

from amiga import Display, Bitmap, palette, joy, run

W: int = 10
H: int = 7
TILE: int = 20

OX: int = (320 - W * TILE) // 2
OY: int = (200 - H * TILE) // 2

board: list[int] = []
for i in range(W * H):
    board.append(0)

cx: int = 5
cy: int = 3

display = Display(320, 200, bitplanes=3)
bm = Bitmap(320, 200, bitplanes=3)
screen = Bitmap(320, 200, bitplanes=3)

palette.aga(1, 40, 40, 40)
palette.aga(2, 200, 60, 60)
palette.aga(3, 255, 255, 0)


def draw():
    screen.clear()
    for y in range(H):
        for x in range(W):
            v: int = board[y * W + x]
            if v > 0:
                screen.box_filled(OX + x * TILE, OY + y * TILE,
                                  OX + x * TILE + TILE - 1,
                                  OY + y * TILE + TILE - 1, v)
            else:
                screen.box_filled(OX + x * TILE, OY + y * TILE,
                                  OX + x * TILE + TILE - 1,
                                  OY + y * TILE + TILE - 1, 1)
    # cursor
    screen.box_filled(OX + cx * TILE + 2, OY + cy * TILE + 2,
                      OX + cx * TILE + TILE - 3,
                      OY + cy * TILE + TILE - 3, 3)


display.show(screen)


def update():
    global cx, cy
    if joy.left_pressed() and cx > 0:
        cx = cx - 1
    if joy.right_pressed() and cx < W - 1:
        cx = cx + 1
    if joy.up_pressed() and cy > 0:
        cy = cy - 1
    if joy.down_pressed() and cy < H - 1:
        cy = cy + 1
    if joy.button_pressed(0):
        board[cy * W + cx] = 2
    draw()


run(update, until=lambda: False)
