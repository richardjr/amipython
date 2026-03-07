# Horizontal scrolling starfield
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/starscroller.ab3
#
# Stars scroll left across the screen at different speeds, creating a
# parallax depth effect. Faster stars are brighter (higher colour register).
# A simple but effective background effect for side-scrolling games.

from dataclasses import dataclass
from amiga import Display, Bitmap, palette, joy, rnd, vwait, run

@dataclass
class Star:
    speed: int
    x: int
    y: int

display = Display(320, 256, bitplanes=3)
bm = Bitmap(320, 256, bitplanes=3)
display.show(bm)

NUM_STARS = 48

# Greyscale palette: brighter = faster/closer
for i in range(1, 8):
    br = int(4 + i * 1.7)
    palette.set(i, br, br, br)

# Create initial star field
stars: list[Star] = []
for i in range(NUM_STARS):
    stars.append(Star(
        speed=rnd(6) + 1,
        x=rnd(320),
        y=rnd(200),
    ))

def update():
    for star in stars:
        # Erase old position
        bm.plot(star.x, star.y, 0)

        # Move star left
        star.x -= star.speed

        # Wrap around when off-screen
        if star.x < 0:
            star.x = rnd(80) + 240
            star.y = rnd(200)

        # Draw at new position (colour = speed for parallax effect)
        bm.plot(star.x, star.y, star.speed)

    vwait(3)

run(update, until=lambda: joy.button(0))
