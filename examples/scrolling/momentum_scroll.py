# Momentum scroller with seamless wrapping
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/scroller.ab3
#
# Random circles on a bitmap that wraps seamlessly in both axes.
# Mouse speed adds momentum; the viewport glides with inertia.
# Demonstrates wrap() for seamless scrolling and clamp() for speed limits.

from amiga import Display, Bitmap, mouse, joy, rnd, wrap, clamp, run

display = Display(320, 256, bitplanes=3)
bm = Bitmap(640, 512, bitplanes=3)

# Draw random circles in the top-left quadrant
for i in range(150):
    bm.circle_filled(rnd(288) + 16, rnd(224) + 16, rnd(16), rnd(8))

# Duplicate quadrants for seamless wrapping
bm.copy_region(0, 0, 320, 256, 320, 0)    # copy to right half
bm.copy_region(0, 0, 640, 256, 0, 256)    # copy to bottom half

display.show(bm)
x = 0.0
y = 0.0
xa = 0.0
ya = 0.0

def update():
    global x, y, xa, ya
    xa = clamp(xa + mouse.x_speed, -20, 20)
    ya = clamp(ya + mouse.y_speed, -20, 20)
    x = wrap(x + xa, 0, 320)
    y = wrap(y + ya, 0, 256)
    display.scroll_to(int(x), int(y))

run(update, until=joy.button(0))
