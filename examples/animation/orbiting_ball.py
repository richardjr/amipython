# Orbiting ball animation
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/blitzballs.ab3
#           Original by V. A. Hill (NZ Amiga Mag)
#
# A ball shape orbits in a circular path using pre-computed sin/cos
# lookup tables. Uses single-buffer with manual clear for simplicity.

from amiga import Display, Bitmap, Shape, palette, joy, run, sin_table, cos_table

display = Display(320, 200, bitplanes=3)

palette.set(0, 0, 0, 0)
palette.set(1, 15, 0, 0)

# Screen bitmap — also used to draw the ball shape before grab
bm = Bitmap(320, 200, bitplanes=3)
bm.circle_filled(8, 8, 7, 1)
ball = Shape.grab(bm, 0, 0, 16, 16)
bm.clear()

# Pre-compute orbit path as integer offsets (no runtime float math)
orbit_x = cos_table(720, 80)
orbit_y = sin_table(720, 80)

r: int = 0

display.show(bm)

def update():
    global r

    bm.clear()

    # Calculate ball position on circular orbit
    idx: int = r % 720
    x: int = 148 + orbit_x[idx]
    y: int = 88 + orbit_y[idx]

    display.blit(ball, x, y)

    r = (r + 3) % 720

run(update, until=lambda: joy.button(0))
