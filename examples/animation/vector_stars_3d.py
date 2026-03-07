# 3D rotating vector stars
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/vectorstars.ab3
#           Code by xp^tsa
#
# Plots 50 dots in 3D space, rotating them around two axes.
# Mouse Y controls the perspective distance. Demonstrates
# lookup tables, 3D rotation, and perspective projection.
# Uses integer fixed-point math (8.8) to avoid float in the game loop.

from dataclasses import dataclass
from amiga import Display, Bitmap, palette, mouse, joy, rnd, run, sin_table, cos_table

@dataclass
class Star:
    x: int
    y: int
    z: int
    nx: int = 160
    ny: int = 127

display = Display(320, 256, bitplanes=1)
bm = Bitmap(320, 256, bitplanes=1)

palette.aga(0, 32, 22, 33)
palette.aga(1, 200, 200, 200)

display.show(bm)

# Build integer lookup tables (360 entries, scaled by 256 for 8.8 fixed-point)
cos_lut = cos_table(360, 256)
sin_lut = sin_table(360, 256)

# Create 50 random 3D points (coordinate range: -20 to +19)
stars: list[Star] = []
for i in range(50):
    stars.append(Star(
        x=rnd(40) - 20,
        y=rnd(40) - 20,
        z=rnd(40) - 20,
    ))

vx: int = 0
vy: int = 0

def update():
    global vx, vy

    bm.clear()

    # Rotation speeds (degrees per frame)
    vx = (vx + 2) % 360
    vy = (vy + 1) % 360

    distance: int = 40 + mouse.y

    # Pre-fetch trig values (8.8 fixed-point integers)
    cosx: int = cos_lut[vx]
    cosy: int = cos_lut[vy]
    sinx: int = sin_lut[vx]
    siny: int = sin_lut[vy]

    for s in stars:
        # 3D rotation (X then Y axis) — all integer arithmetic
        # Multiply by fixed-point trig, divide by 256 to get back to coordinate scale
        ty: int = (s.y * cosx - s.z * sinx) // 256
        tz: int = (s.y * sinx + s.z * cosx) // 256
        tx: int = (s.x * cosy - tz * siny) // 256
        tz = (s.x * siny + tz * cosy) // 256

        # Perspective projection — pure integer division
        denom: int = distance - tz
        if denom > 0:
            s.nx = 200 * tx // denom + 160
            s.ny = 200 * ty // denom + 127

        # Clip and draw
        if 0 < s.nx and s.nx < 320 and 0 < s.ny and s.ny < 256:
            bm.plot(s.nx, s.ny, 1)

run(update, until=lambda: joy.button(0))
