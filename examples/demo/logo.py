# Minimal logo display test
# Just loads a logo PNG and displays it on a blue background.

from amiga import Display, Bitmap, Shape, palette, joy, run

display = Display(320, 200, bitplanes=3)
bm = Bitmap(320, 200, bitplanes=3)

# Blue background, white foreground
palette.set(0, 0, 0, 5)
palette.set(1, 3, 3, 5)
palette.set(2, 5, 5, 7)
palette.set(3, 7, 7, 10)
palette.set(4, 9, 9, 12)
palette.set(5, 11, 11, 14)
palette.set(6, 13, 13, 15)
palette.set(7, 15, 15, 15)

logo = Shape.load("data/logo.png")

display.show(bm)

def update():
    display.blit(logo, 64, 72)

run(update, until=lambda: joy.button(0))
