# Pixel explosion effect
# Based on: AmiBlitz3/Sourcecodes/Examples/Blitzlib examples/mildred_2DPixelExplosion.ab3
#           Original by Mikkel Loekke (FlameDuck), optimised by Sami Naatanen
#
# Adapted to OCS planar display (8 colours instead of 256-colour chunky).
# Particles explode outward from the centre in random directions, fading
# out over time. When the fade completes, the explosion resets.
# Demonstrates particle systems with pre-computed trig lookup tables.

from amiga import Display, Bitmap, palette, joy, key, rnd, clamp, run, sin_table, cos_table

class Particle:
    x: float
    y: float
    vx: float
    vy: float

NUM_PARTICLES = 500
display = Display(320, 256, bitplanes=3, double_buffer=True)
bm0 = Bitmap(320, 256, bitplanes=3)
bm1 = Bitmap(320, 256, bitplanes=3)

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
phase = 0

def reset_explosion():
    global particles, phase
    particles = []
    phase = 0
    for i in range(NUM_PARTICLES):
        angle = rnd(360)
        speed = rnd() * 4.4 + rnd() * 1.6 + 0.5
        particles.append(Particle(
            x=160.0,
            y=128.0,
            vx=cos_lut[angle] * speed,
            vy=sin_lut[angle] * speed,
        ))

reset_explosion()

def update():
    global phase

    bm = display.current_bitmap()
    bm.clear()

    # Calculate current brightness (fades from 7 down to 1)
    color = clamp(7 - phase // 36, 1, 7)

    offscreen = 0
    for p in particles:
        px = int(p.x)
        py = int(p.y)
        if 0 < px < 320 and 0 < py < 256:
            bm.plot(px, py, color)
            p.x -= p.vx
            p.y -= p.vy
        else:
            offscreen += 1

    phase += 2
    if phase >= 252 or offscreen >= NUM_PARTICLES:
        reset_explosion()

run(update, until=key.pressed(key.ESC))
