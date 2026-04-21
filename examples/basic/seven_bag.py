"""Seven-bag randomiser — the classic Tetris piece-draw pattern.

`shuffle(lst)` does an in-place Fisher-Yates shuffle. The 7-bag rule is:
keep drawing from a shuffled bag of all 7 pieces until empty, then refill
and shuffle again. This guarantees every piece appears once per 7 draws
without enforcing strict-cycle predictability.
"""

from amiga import Display, Bitmap, palette, wait_mouse, shuffle

display = Display(320, 200, bitplanes=3)
screen = Bitmap(320, 200, bitplanes=3)

palette.aga(1, 60, 220, 240)
palette.aga(2, 240, 220, 40)
palette.aga(3, 200, 80, 240)
palette.aga(4, 40, 220, 60)
palette.aga(5, 240, 60, 60)
palette.aga(6, 240, 140, 40)
palette.aga(7, 60, 100, 240)

bag: list[int] = []
for i in range(7):
    bag.append(i)

# Show two full bag draws (14 pieces) as rows of coloured blocks.
for draw in range(2):
    shuffle(bag)
    for i in range(7):
        sx: int = 30 + i * 36
        sy: int = 40 + draw * 60
        color: int = bag[i] + 1
        screen.box_filled(sx, sy, sx + 32, sy + 32, color)

screen.print_at(20, 20, "DRAW 1:", color=1)
screen.print_at(20, 80, "DRAW 2:", color=1)
screen.print_at(20, 150, "EACH DRAW CONTAINS ALL 7 COLOURS", color=2)

display.show(screen)
wait_mouse()
