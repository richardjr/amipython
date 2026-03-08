# Graphic equaliser demo (sprite sheet)
#
# Demonstrates the sprite sheet pattern: load one PNG image,
# grab multiple shapes from different positions.
# 8 EQ bars animated with random levels and smoothing.
# Uses 3 bitplanes (8 colours).

from dataclasses import dataclass
from amiga import Display, Bitmap, Shape, palette, joy, music, rnd, run

music.load("data/demo.mod")

SCREEN_W: int = 320
SCREEN_H: int = 200
NUM_BARS: int = 8
NUM_LEVELS: int = 9
BAR_W: int = 16
BAR_H: int = 32

# Load sprite sheet and grab each frame as a shape
sheet = Bitmap.load("data/eq_bars.png")
bars: list[Shape] = []
for i in range(NUM_LEVELS):
    bars.append(Shape.grab(sheet, i * BAR_W, 0, BAR_W, BAR_H))

@dataclass
class Bar:
    level: int
    target: int

display = Display(SCREEN_W, SCREEN_H, bitplanes=3)
bm = Bitmap(SCREEN_W, SCREEN_H, bitplanes=3)

# Palette: same as demo — dark background, blue-white tones
palette.set(0, 0, 0, 0)
palette.set(1, 3, 3, 5)
palette.set(2, 5, 5, 7)
palette.set(3, 7, 7, 10)
palette.set(4, 9, 9, 12)
palette.set(5, 11, 11, 14)
palette.set(6, 13, 13, 15)
palette.set(7, 15, 15, 15)

bm.print_at(72, 16, "SPRITE SHEET DEMO", color=7)
bm.print_at(56, 32, "GRAPHIC EQUALISER", color=6)

# Centre the 8 bars on screen
EQ_X: int = (SCREEN_W - NUM_BARS * BAR_W) // 2
EQ_Y: int = 80

eq: list[Bar] = []
for i in range(NUM_BARS):
    eq.append(Bar(level=0, target=0))

frame: int = 0

display.show(bm)
music.play()

def update():
    global frame
    frame = frame + 1

    # Pick new random targets every 6 frames
    if frame % 6 == 0:
        for b in eq:
            b.target = rnd(NUM_LEVELS)

    # Smooth each bar toward its target
    for b in eq:
        if b.level < b.target:
            b.level = b.level + 1
        if b.level > b.target:
            b.level = b.level - 1

    # Clear EQ area and redraw
    bm.box_filled(EQ_X, EQ_Y, EQ_X + NUM_BARS * BAR_W - 1, EQ_Y + BAR_H - 1, 0)
    for i in range(NUM_BARS):
        display.blit(bars[eq[i].level], EQ_X + i * BAR_W, EQ_Y)

run(update, until=lambda: joy.button(0))
music.stop()
