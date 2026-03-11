# Palette fade demo
# Shows the amipython logo and slowly fades up and down.

from amiga import Display, Bitmap, Shape, palette, vwait, run, joy

SCREEN_W: int = 320
SCREEN_H: int = 200

display = Display(SCREEN_W, SCREEN_H, bitplanes=3)
bm = Bitmap(SCREEN_W, SCREEN_H, bitplanes=3)

palette.set(0, 0, 0, 0)
palette.set(1, 3, 3, 5)
palette.set(2, 5, 5, 7)
palette.set(3, 7, 7, 10)
palette.set(4, 9, 9, 12)
palette.set(5, 11, 11, 14)
palette.set(6, 13, 13, 15)
palette.set(7, 15, 15, 15)

logo = Shape.load("data/logo.png")

display.show(bm)
display.blit(logo, 64, 72)

level: int = 0
direction: int = 1

def update():
    global level, direction

    level = level + direction
    if level >= 15:
        level = 15
        direction = -1
    if level <= 0:
        level = 0
        direction = 1

    palette.fade(level)
    vwait(3)

run(update, until=lambda: joy.button(0))
