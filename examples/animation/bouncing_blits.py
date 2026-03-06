# Bouncing blits (single buffer)
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/blits.ab3
#
# Moves two ball shapes around the screen using manual erase/draw blitting.
# This is the simplest animation approach -- without double buffering,
# so increasing the number of objects will cause flicker.
# See doublebuffer_balls.py for the flicker-free version.

from amiga import Display, Bitmap, Shape, joy, rnd, run

class Ball:
    x: float
    y: float
    xs: float
    ys: float

display = Display(320, 200, bitplanes=3)
bm = Bitmap(320, 200, bitplanes=3)

ball_shape = Shape.load("data/ball")

# Create two bouncing balls
balls: list[Ball] = []
for i in range(2):
    balls.append(Ball(
        x=rnd(280) + 10,
        y=rnd(160) + 10,
        xs=(rnd() - 0.5) * 8,
        ys=(rnd() - 0.5) * 8,
    ))

display.show(bm)

def update():
    for b in balls:
        # Erase old position (handled automatically by run())
        # Update position
        b.x += b.xs
        b.y += b.ys

        # Bounce off edges
        if b.x < 10 or b.x > 290:
            b.xs = -b.xs
        if b.y < 10 or b.y > 170:
            b.ys = -b.ys

        # Draw at new position
        display.blit(ball_shape, b.x, b.y)

run(update, until=joy.button(0))
