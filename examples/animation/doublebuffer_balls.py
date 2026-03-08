# Double-buffered bouncing balls
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/doublebuffer.ab3
#
# Demonstrates flicker-free animation using double buffering with QBlit queues.
# The run() function handles VWait, buffer swap, and UnQueue/QBlit automatically.
# Try increasing the ball count -- double buffering eliminates the flicker
# that the single-buffer version (bouncing_blits.py) would show.

from dataclasses import dataclass
from amiga import Display, Shape, joy, rnd, run

@dataclass
class Ball:
    x: float
    y: float
    xs: float
    ys: float

display = Display(320, 200, bitplanes=3, double_buffer=True)
ball_shape = Shape.load("data/ball.png")

# Create 12 bouncing balls
balls: list[Ball] = []
for i in range(12):
    balls.append(Ball(
        x=rnd(280) + 10,
        y=rnd(160) + 10,
        xs=(rnd(100) / 100.0 - 0.5) * 8,
        ys=(rnd(100) / 100.0 - 0.5) * 8,
    ))

def update():
    for b in balls:
        b.x += b.xs
        b.y += b.ys

        if b.x < 10 or b.x > 290:
            b.xs = -b.xs
        if b.y < 10 or b.y > 170:
            b.ys = -b.ys

        display.blit(ball_shape, b.x, b.y)

run(update, until=joy.button(0))
