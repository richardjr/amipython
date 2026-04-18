"""Grid pattern — demonstrates list[int] as a 2D board using subscript assignment.

Tetris uses this exact layout: a flat list of length W*H indexed as y*W+x,
mutated in place with `board[y * W + x] = value`. This example fills a small
grid with a checkerboard then draws it as coloured tiles.
"""

from amiga import Display, Bitmap, palette, wait_mouse

W: int = 8
H: int = 6
TILE: int = 20

board: list[int] = []
for i in range(W * H):
    board.append(0)

for y in range(H):
    for x in range(W):
        if (x + y) % 2 == 0:
            board[y * W + x] = 1
        else:
            board[y * W + x] = 2

board[0] = 3
board[W * H - 1] = 3

display = Display(320, 200, bitplanes=3)
bm = Bitmap(320, 200, bitplanes=3)

palette.aga(1, 60, 60, 120)
palette.aga(2, 120, 60, 60)
palette.aga(3, 255, 255, 0)

ox: int = (320 - W * TILE) // 2
oy: int = (200 - H * TILE) // 2

for y in range(H):
    for x in range(W):
        c: int = board[y * W + x]
        if c > 0:
            bm.box_filled(ox + x * TILE, oy + y * TILE,
                          ox + x * TILE + TILE - 1, oy + y * TILE + TILE - 1, c)

display.show(bm)
wait_mouse()
