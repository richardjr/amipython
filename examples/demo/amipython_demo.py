# Alien Breed starfield demo
# Inspired by Team17's Alien Breed (1991) title sequence
#
# Multi-speed parallax starfield scrolling right-to-left.
# Three depth layers with different speeds and brightness.
# Uses 3 bitplanes (8 colours) for star brightness variation.
# Loads an amipython logo PNG and blits it over the starfield.
# Graphic equaliser at bottom-left using sprite sheet pattern.

from dataclasses import dataclass
from amiga import Display, Bitmap, Shape, palette, joy, music, rnd, run

@dataclass
class Star:
    x: int
    y: int
    speed: int
    color: int

@dataclass
class Bar:
    level: int
    target: int

music.load("data/demo.mod")

SCREEN_W: int = 320
SCREEN_H: int = 200
NUM_BARS: int = 8
NUM_LEVELS: int = 9
BAR_W: int = 16
BAR_H: int = 32

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

# Load EQ sprite sheet — 9 frames of bar at different heights
eq_sheet = Bitmap.load("data/eq_bars.png")
eq_bars: list[Shape] = []
for i in range(NUM_LEVELS):
    eq_bars.append(Shape.grab(eq_sheet, i * BAR_W, 0, BAR_W, BAR_H))

# EQ position — bottom left
EQ_X: int = 100 
EQ_Y: int = SCREEN_H - BAR_H - 8

eq: list[Bar] = []
for i in range(NUM_BARS):
    eq.append(Bar(level=0, target=0))

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

frame: int = 0

display.show(bm)
music.play()

def update():
    global frame
    frame = frame + 1
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

    # Graphic equaliser — random targets with smoothing
    if frame % 6 == 0:
        for b in eq:
            b.target = rnd(NUM_LEVELS)

    for b in eq:
        if b.level < b.target:
            b.level = b.level + 1
        if b.level > b.target:
            b.level = b.level - 1

    for i in range(NUM_BARS):
        display.blit(eq_bars[eq[i].level], EQ_X + i * BAR_W, EQ_Y)

run(update, until=lambda: joy.button(0))
music.stop()
