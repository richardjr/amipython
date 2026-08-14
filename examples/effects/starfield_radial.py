# Radial starfield with mouse control
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/starfield.ab3
#
# Stars fly outward from the centre of the screen. Mouse X rotates the
# field. Stars are brighter (higher colour register) the further they
# travel. Uses pre-computed sin/cos lookup tables for fast polar-to-
# cartesian conversion, and a fixed pool of stars that respawn at the
# centre when they leave the screen.

from dataclasses import dataclass
from amiga import Display, Bitmap, palette, mouse, joy, rnd, run, sin_table, cos_table

@dataclass
class Star:
    angle: int = 0
    dist: float = 0.0
    speed: float = 0.0
    acc: float = 0.0
    sx: int = 160
    sy: int = 128

display = Display(320, 256, bitplanes=3)
bm = Bitmap(320, 256, bitplanes=3)
display.show(bm)

# Pre-computed trig tables (1024 entries, maps to 2*pi)
qsin = sin_table(1024)
qcos = cos_table(1024)

# Greyscale palette: brighter stars are further from centre
for i in range(1, 8):
    palette.set(i, i * 2, i * 2, i * 2)

NUM_STARS = 96

stars: list[Star] = []
for i in range(NUM_STARS):
    stars.append(Star(angle=rnd(1024), acc=rnd(20) * 0.005 + 0.005))

def update():
    mx = mouse.x
    for star in stars:
        # Erase old position
        bm.plot(star.sx, star.sy, 0)

        # Accelerate and move outward
        star.speed += star.acc
        star.dist += star.speed

        # New screen position (polar to cartesian), rotated by mouse X
        star.sx = 160 + int(qcos[(star.angle + mx) % 1024] * star.dist)
        star.sy = 128 + int(qsin[(star.angle + mx) % 1024] * star.dist)

        if star.sx < 0 or star.sx > 319 or star.sy < 0 or star.sy > 255:
            # Respawn at the centre with a fresh direction
            star.angle = rnd(1024)
            star.dist = 0.0
            star.speed = 0.0
            star.acc = rnd(20) * 0.005 + 0.005
            star.sx = 160
            star.sy = 128
        else:
            # Colour based on distance (further = brighter)
            c = int(star.dist) // 20
            if c < 1:
                c = 1
            if c > 7:
                c = 7
            bm.plot(star.sx, star.sy, c)

run(update, until=lambda: joy.button(0))
