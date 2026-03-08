# Test display_blit using Shape.grab (no file I/O)
# Draws a white rectangle on the bitmap, grabs it as a shape,
# clears the bitmap, then blits the shape each frame.

from amiga import Display, Bitmap, Shape, palette, joy, run

display = Display(320, 200, bitplanes=3)
bm = Bitmap(320, 200, bitplanes=3)

palette.set(0, 0, 0, 5)
palette.set(7, 15, 15, 15)

# Draw a white box and grab it as a shape
bm.box_filled(0, 0, 63, 15, 7)
logo = Shape.grab(bm, 0, 0, 64, 16)
bm.clear()

display.show(bm)

def update():
    display.blit(logo, 64, 72)

run(update, until=lambda: joy.button(0))
