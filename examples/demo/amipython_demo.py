# Alien Breed starfield demo
# Inspired by Team17's Alien Breed (1991) title sequence
#
# Multi-speed parallax starfield scrolling right-to-left.
# Three depth layers with different speeds and brightness.
# Uses 3 bitplanes (8 colours) for star brightness variation.
# Loads an amipython logo PNG and blits it over the starfield.

from dataclasses import dataclass
from amiga import Display, Bitmap, Shape, palette, joy, music, rnd, run

@dataclass
class Star:
    x: int
    y: int
    speed: int
    color: int

music.load("data/demo.mod")

SCREEN_W: int = 320
SCREEN_H: int = 200

display = Display(SCREEN_W, SCREEN_H, bitplanes=3)
bm = Bitmap(SCREEN_W, SCREEN_H, bitplanes=3)

# Palette: black background, blue-white star tones per layer
palette.set(0, 0, 0, 0)
palette.set(1, 3, 3, 5)
palette.set(2, 5, 5, 7)
palette.set(3, 7, 7, 10)
palette.set(4, 9, 9, 12)
palette.set(5, 11, 11, 14)
palette.set(6, 13, 13, 15)
palette.set(7, 15, 15, 15)

# Load the amipython logo (192x56, same palette, color 0 = transparent)
logo = Shape.load("data/logo.png")
LOGO_X: int = 64
LOGO_Y: int = 72

stars: list[Star] = []

# Slow layer — dim, distant (20 stars)
for i in range(20):
    stars.append(Star(
        x=rnd(SCREEN_W),
        y=rnd(SCREEN_H),
        speed=1,
        color=rnd(2) + 1,
    ))

# Medium layer (20 stars)
for i in range(20):
    stars.append(Star(
        x=rnd(SCREEN_W),
        y=rnd(SCREEN_H),
        speed=3,
        color=rnd(2) + 3,
    ))

# Fast layer — bright, close (20 stars)
for i in range(20):
    stars.append(Star(
        x=rnd(SCREEN_W),
        y=rnd(SCREEN_H),
        speed=5,
        color=rnd(3) + 5,
    ))

display.show(bm)
music.play()

def update():
    bm.clear()

    # Blit logo first — minimize time logo area is empty (beam racing)
    display.blit(logo, LOGO_X, LOGO_Y)

    for star in stars:
        # Scroll left
        star.x = star.x - star.speed

        # Wrap around off left edge
        if star.x < 0:
            star.x = SCREEN_W - 1
            star.y = rnd(SCREEN_H)

        # Draw at new position
        bm.plot(star.x, star.y, star.color)

run(update, until=lambda: joy.button(0))
music.stop()
