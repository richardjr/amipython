# Copper colour splits with animated line patterns
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/lineswithcopsplit.ab3
#           Original: "Lines by Spectre in Blitz II"
#
# Creates animated Lissajous-like line patterns using cosine lookup tables,
# with copper colour splits changing the background colour at different
# scanlines. Double-buffered for smooth animation. Cycles through multiple
# pattern presets.

from amiga import Display, Bitmap, palette, copper, Color, joy, cos_table, run

display = Display(320, 270, bitplanes=1, double_buffer=True)
bm0 = Bitmap(320, 270, bitplanes=1)
bm1 = Bitmap(320, 270, bitplanes=1)

NUM_LINES = 50

# Base palette
palette.set(0, 0, 0, 15)   # dark blue background
palette.set(1, 15, 15, 0)  # yellow lines

# Copper colour splits: gradient the background down the screen
for i in range(1, 8):
    copper.color_at(scanline=i * 5 + 160, register=0, color=Color(0, 0, 8 + i))

# Build cosine lookup table (720 entries for smooth animation)
cx = cos_table(720)

# Pre-compute line endpoint offsets
px1: list[int] = [0] * (NUM_LINES + 1)
py1: list[int] = [0] * (NUM_LINES + 1)
px2: list[int] = [0] * (NUM_LINES + 1)
py2: list[int] = [0] * (NUM_LINES + 1)

for i in range(1, NUM_LINES + 1):
    px1[i] = i * 4 - 4
    py1[i] = i * 4 - 4
    px2[i] = i * 4 + 56
    py2[i] = i * 4 + 56

# Pattern data: each set of 8 values defines a unique animation
patterns = [
    (7, 10, 10, 7, 90, 0, 50, 0),
    (12, 9, 9, 12, 0, 0, 50, 0),
    (12, 9, 9, 12, 245, 60, 0, 0),
    (5, 10, 10, 10, 100, 0, 0, 0),
]

pattern_idx = 0
xi, yi, xi2, yi2, x2, y2, x, y = patterns[pattern_idx]
t = 0

def update():
    global x, y, x2, y2, t, pattern_idx, xi, yi, xi2, yi2

    bm = display.current_bitmap()
    bm.clear()

    x = (x + xi) % 360
    y = (y + yi) % 360
    x2 = (x2 + xi2) % 360
    y2 = (y2 + yi2) % 360

    # Draw the line pattern
    for i in range(1, NUM_LINES + 1):
        x1_pos = int(cx[(x + px1[i]) % 720] * 125) + 160
        y1_pos = int(cx[(y + py1[i]) % 720] * 125) + 128
        x2_pos = int(cx[(x2 + px2[i]) % 720] * 125) + 160
        y2_pos = int(cx[(y2 + py2[i]) % 720] * 125) + 128
        bm.line(x1_pos, y1_pos, x2_pos, y2_pos, 1)

    t += 1
    if t >= 600:
        # Move to next pattern
        t = 0
        pattern_idx = (pattern_idx + 1) % len(patterns)
        xi, yi, xi2, yi2, x2, y2, x, y = patterns[pattern_idx]

run(update, until=joy.button(0))
