# Smooth hardware scrolling with mouse
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/smoothscrolling.ab3
#
# Draws random dots on an oversized bitmap, then scrolls the viewport
# by following the mouse position. Demonstrates hardware scroll registers
# via display.scroll_to().

from amiga import Display, Bitmap, mouse, joy, rnd, run

display = Display(320, 200, bitplanes=3)
bm = Bitmap(640, 400, bitplanes=3)

# Scatter 1000 random dots across the oversized bitmap
for k in range(1000):
    bm.plot(rnd(640), rnd(400), rnd(7) + 1)

display.show(bm)

def update():
    display.scroll_to(mouse.x, mouse.y)

run(update, until=joy.button(0))
