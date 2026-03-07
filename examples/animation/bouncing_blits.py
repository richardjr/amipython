# Bouncing blits (single buffer)
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/blits.ab3
#
# Moves two ball shapes around the screen using manual erase/draw blitting.
# This is the simplest animation approach -- without double buffering,
# so increasing the number of objects will cause flicker.
# See doublebuffer_balls.py for the flicker-free version.

from dataclasses import dataclass
from amiga import Display, Bitmap, Shape, palette, joy, rnd, run

@dataclass
class Ball:
    x: float
    y: float
    xs: float
    ys: float

display = Display(320, 200, bitplanes=3)

# Draw ball shape into a small bitmap and grab it
bm_shape = Bitmap(16, 16, bitplanes=3)
palette.set(1, 15, 0, 0)
bm_shape.circle_filled(8, 8, 7, 1)
ball_shape = Shape.grab(bm_shape, 0, 0, 16, 16)

# Screen bitmap
bm = Bitmap(320, 200, bitplanes=3)

# Create two bouncing balls with random positions and velocities
balls: list[Ball] = []
for i in range(2):
    balls.append(Ball(
        x=float(rnd(280) + 10),
        y=float(rnd(160) + 10),
        xs=float(rnd(7)) - 3.0,
        ys=float(rnd(7)) - 3.0,
    ))

display.show(bm)

def update():
    bm.clear()
    for b in balls:
        b.x += b.xs
        b.y += b.ys

        if b.x < 10.0 or b.x > 290.0:
            b.xs = -b.xs
        if b.y < 10.0 or b.y > 170.0:
            b.ys = -b.ys

        display.blit(ball_shape, int(b.x), int(b.y))

run(update, until=lambda: joy.button(0))
