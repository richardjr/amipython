# Radial starfield with mouse control
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/starfield.ab3
#
# Stars fly outward from the centre of the screen. Mouse X rotates the
# field, mouse Y adjusts acceleration. Stars are brighter (higher colour
# register) the further they travel. Uses pre-computed sin/cos lookup
# tables for fast polar-to-cartesian conversion.

from dataclasses import dataclass
from amiga import Display, Bitmap, palette, mouse, joy, rnd, clamp, run, sin_table, cos_table

@dataclass
class Star:
    angle: int
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
    br = int(4 + i * 1.7)
    palette.set(i, br, br, br)

stars: list[Star] = []

def update():
    mx = mouse.x

    for star in stars[:]:
        # Erase old position
        bm.plot(star.sx, star.sy, 0)

        # Accelerate and move outward
        star.speed += star.acc
        star.dist += star.speed

        # Calculate new screen position (polar to cartesian)
        star.sx = 160 + int(qcos[(star.angle + mx) & 1023] * star.dist)
        star.sy = 128 + int(qsin[(star.angle + mx) & 1023] * star.dist)

        # Remove stars that leave the screen
        if star.sx < 0 or star.sx > 319 or star.sy < 0 or star.sy > 255:
            stars.remove(star)
        else:
            # Colour based on distance (further = brighter)
            color = clamp(int(star.dist / 20), 1, 7)
            bm.plot(star.sx, star.sy, color)

    # Spawn new stars at the centre
    if len(stars) < 128:
        stars.append(Star(
            angle=rnd(1024),
            acc=rnd() / 32,
        ))

run(update, until=joy.button(0))
