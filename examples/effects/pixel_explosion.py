# Pixel explosion effect
# Based on: AmiBlitz3/Sourcecodes/Examples/Blitzlib examples/mildred_2DPixelExplosion.ab3
#           Original by Mikkel Loekke (FlameDuck), optimised by Sami Naatanen
#
# Adapted to OCS planar display (8 colours instead of 256-colour chunky).
# Particles explode outward from the centre in random directions, fading
# out over time. When the fade completes, the explosion resets.
# Demonstrates particle systems with pre-computed trig lookup tables and
# a fixed particle pool that is re-seeded in place on each reset.

from dataclasses import dataclass
from amiga import Display, Bitmap, palette, joy, rnd, run, sin_table, cos_table

@dataclass
class Particle:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0

NUM_PARTICLES = 200

display = Display(320, 256, bitplanes=3)
bm = Bitmap(320, 256, bitplanes=3)
display.show(bm)

# White-to-dark greyscale palette for fading
palette.set(0, 0, 0, 0)
palette.set(1, 2, 2, 2)
palette.set(2, 4, 4, 4)
palette.set(3, 6, 6, 6)
palette.set(4, 8, 8, 8)
palette.set(5, 10, 10, 10)
palette.set(6, 12, 12, 12)
palette.set(7, 15, 15, 15)

sin_lut = sin_table(360)
cos_lut = cos_table(360)

particles: list[Particle] = []
for i in range(NUM_PARTICLES):
    particles.append(Particle())

phase: int = 0

def reset_explosion():
    global phase
    phase = 0
    for p in particles:
        a = rnd(360)
        s = rnd(44) * 0.1 + 0.5
        p.x = 160.0
        p.y = 128.0
        p.vx = cos_lut[a] * s
        p.vy = sin_lut[a] * s

reset_explosion()

def update():
    global phase

    bm.clear()

    # Current brightness (fades from 7 down to 1)
    color = 7 - phase // 36
    if color < 1:
        color = 1

    offscreen = 0
    for p in particles:
        px = int(p.x)
        py = int(p.y)
        if px > 0 and px < 320 and py > 0 and py < 256:
            bm.plot(px, py, color)
            p.x -= p.vx
            p.y -= p.vy
        else:
            offscreen += 1

    phase += 2
    if phase >= 252 or offscreen >= NUM_PARTICLES:
        reset_explosion()

run(update, until=lambda: joy.button(0))
