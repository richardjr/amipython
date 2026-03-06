# Orbiting ball animation
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/blitzballs.ab3
#           Original by V. A. Hill (NZ Amiga Mag)
#
# A ball shape orbits in a circular path using pre-computed sin/cos
# tables. The orbit phase advances each frame, cycling through 8
# bitmap pages for smooth animation. Adapted to a simpler single-shape
# orbit to fit the amipython model.

from amiga import Display, Bitmap, Shape, palette, joy, run, sin_table, cos_table, wrap

display = Display(320, 256, bitplanes=2, double_buffer=True)

# Set up a simple 4-colour palette
palette.set(0, 0, 0, 0)
palette.set(1, 15, 9, 9)
palette.set(2, 10, 0, 0)
palette.set(3, 12, 0, 0)

# Create a small ball shape by drawing on a temporary bitmap
tmp = Bitmap(24, 32, bitplanes=2)
tmp.circle_filled(12, 20, 11, 3)
tmp.circle(12, 20, 11, 2)
tmp.circle(12, 20, 10, 2)
ball = Shape.grab(tmp, 0, 9, 24, 32)
ball.set_origin("center")

# Pre-compute orbit path (720 entries for sub-degree precision)
ORBIT_RADIUS = 110
orbit_x = cos_table(720)
orbit_y = sin_table(720)

r = 0

def update():
    global r

    # Calculate ball position on circular orbit
    idx = int(r) % 720
    x = 160 + int(orbit_x[idx] * ORBIT_RADIUS)
    y = 128 + int(orbit_y[idx] * ORBIT_RADIUS)

    display.blit(ball, x, y)

    r = wrap(r + 3, 0, 720)

run(update, until=joy.button(0))
