# 3D rotating vector stars
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/vectorstars.ab3
#           Code by xp^tsa
#
# Plots 50 dots in 3D space, rotating them around all three axes.
# Mouse Y controls the perspective distance. Double-buffered to
# avoid flicker. Demonstrates lookup tables, 3D rotation, and
# perspective projection.

from dataclasses import dataclass
from amiga import Display, Bitmap, palette, mouse, joy, rnd, run, sin_table, cos_table

@dataclass
class Ball:
    x: float
    y: float
    z: float
    nx: int = 160
    ny: int = 127

display = Display(320, 256, bitplanes=1, double_buffer=True)
bm0 = Bitmap(320, 256, bitplanes=1)
bm1 = Bitmap(320, 256, bitplanes=1)

palette.aga(0, 32, 22, 33)
palette.aga(1, 200, 200, 200)

# Build lookup tables (360 entries, degrees)
cos_lut = cos_table(360)
sin_lut = sin_table(360)

# Create 50 random 3D points
balls: list[Ball] = []
for i in range(50):
    balls.append(Ball(
        x=rnd(40) - 20,
        y=rnd(40) - 20,
        z=rnd(40) - 20,
    ))

vx = 0
vy = 0
vz = 0

def update():
    global vx, vy, vz

    bm = display.current_bitmap()
    bm.clear()

    # Rotation speeds
    vx = (vx + 2) % 360
    vy = (vy + 1) % 360
    vz = (vz + 1) % 360

    distance = 10 + mouse.y

    cosx = cos_lut[vx]
    cosy = cos_lut[vy]
    sinx = sin_lut[vx]
    siny = sin_lut[vy]

    for b in balls:
        # Slowly drift X position
        b.x += 1
        if b.x > 20:
            b.x = -20

        # 3D rotation (X then Y axis)
        ty = (b.y * cosx - b.z * sinx)
        tz = (b.y * sinx + b.z * cosx)
        tx = (b.x * cosy - tz * siny)
        tz = (b.x * siny + tz * cosy)

        # Perspective projection
        if distance - tz != 0:
            b.nx = int(200 * tx / (distance - tz)) + 160
            b.ny = int(200 * ty / (distance - tz)) + 127

        # Clip and draw
        if 0 < b.nx < 320 and 0 < b.ny < 256:
            bm.plot(b.nx, b.ny, 1)

run(update, until=joy.button(0))
