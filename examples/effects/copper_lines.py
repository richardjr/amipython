# Copper colour splits with animated line patterns
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/lineswithcopsplit.ab3
#           Original: "Lines by Spectre in Blitz II"
#
# Creates animated Lissajous-like line patterns using a cosine lookup
# table, with copper colour splits changing the background colour at
# different scanlines. Cycles through multiple pattern presets stored as
# a flat list (8 values per pattern).

from amiga import Display, Bitmap, palette, copper, Color, joy, cos_table, run

display = Display(320, 200, bitplanes=1)
bm = Bitmap(320, 200, bitplanes=1)
display.show(bm)

NUM_LINES = 50
NUM_PATTERNS = 4

# Base palette
palette.set(0, 0, 0, 15)   # dark blue background
palette.set(1, 15, 15, 0)  # yellow lines

# Copper colour splits: gradient the background near the bottom
for i in range(1, 8):
    copper.color_at(scanline=i * 5 + 130, register=0, color=Color(0, 0, 8 + i))

# Cosine lookup table (720 entries for smooth animation)
cx_lut = cos_table(720)

# Pre-computed line endpoint offsets (index 0 unused, lines are 1..NUM_LINES)
px1: list[int] = []
py1: list[int] = []
px2: list[int] = []
py2: list[int] = []
for i in range(NUM_LINES + 1):
    px1.append(i * 4 - 4)
    py1.append(i * 4 - 4)
    px2.append(i * 4 + 56)
    py2.append(i * 4 + 56)

# Pattern data: 8 values per pattern — xi, yi, xi2, yi2, x2, y2, x, y
patterns: list[int] = []
patterns.append(7); patterns.append(10); patterns.append(10); patterns.append(7)
patterns.append(90); patterns.append(0); patterns.append(50); patterns.append(0)
patterns.append(12); patterns.append(9); patterns.append(9); patterns.append(12)
patterns.append(0); patterns.append(0); patterns.append(50); patterns.append(0)
patterns.append(12); patterns.append(9); patterns.append(9); patterns.append(12)
patterns.append(245); patterns.append(60); patterns.append(0); patterns.append(0)
patterns.append(5); patterns.append(10); patterns.append(10); patterns.append(10)
patterns.append(100); patterns.append(0); patterns.append(0); patterns.append(0)

pattern_idx: int = 0
xi: int = 7
yi: int = 10
xi2: int = 10
yi2: int = 7
x2: int = 90
y2: int = 0
x: int = 50
y: int = 0
t: int = 0

def update():
    global x, y, x2, y2, t, pattern_idx, xi, yi, xi2, yi2

    bm.clear()

    x = (x + xi) % 360
    y = (y + yi) % 360
    x2 = (x2 + xi2) % 360
    y2 = (y2 + yi2) % 360

    # Draw the line pattern
    for i in range(1, NUM_LINES + 1):
        x1_pos = int(cx_lut[(x + px1[i]) % 720] * 125) + 160
        y1_pos = int(cx_lut[(y + py1[i]) % 720] * 90) + 100
        x2_pos = int(cx_lut[(x2 + px2[i]) % 720] * 125) + 160
        y2_pos = int(cx_lut[(y2 + py2[i]) % 720] * 90) + 100
        bm.line(x1_pos, y1_pos, x2_pos, y2_pos, 1)

    t += 1
    if t >= 600:
        # Move to the next pattern preset
        t = 0
        pattern_idx = (pattern_idx + 1) % NUM_PATTERNS
        base = pattern_idx * 8
        xi = patterns[base]
        yi = patterns[base + 1]
        xi2 = patterns[base + 2]
        yi2 = patterns[base + 3]
        x2 = patterns[base + 4]
        y2 = patterns[base + 5]
        x = patterns[base + 6]
        y = patterns[base + 7]

run(update, until=lambda: joy.button(0))
