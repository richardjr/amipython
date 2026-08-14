# QBlit queue animation (single buffer)
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/qblits.ab3
#
# Moves 10 ball shapes using the QBlit queue system for automatic
# erase/draw management. This is single-buffered -- the run() function
# handles UnQueue and QBlit calls. For flicker-free animation with
# more objects, see doublebuffer_balls.py.
#
# NOTE: aspirational — not yet runnable. Relies on the BlitQueue engine
# feature (automatic QBlit/UnQueue erase management), which is still on
# the Phase 5 todo list: there is no bitmap or display.show() here, so
# nothing is drawn today. For the working blit idiom (explicit bitmap +
# clear each frame), see bouncing_blits.py.

from dataclasses import dataclass
from amiga import Display, Shape, joy, rnd, run

@dataclass
class Ball:
    x: float
    y: float
    xs: float
    ys: float

display = Display(320, 200, bitplanes=3)
ball_shape = Shape.load("data/ball.png")

balls: list[Ball] = []
for i in range(10):
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

run(update, until=lambda: joy.button(0))
