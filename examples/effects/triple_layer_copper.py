# Triple-layer parallax with copper colours
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/triplanes.ab3
#
# Three independent scrolling layers using shared bitplanes and copper
# colour gradients. Each layer gets its own colour cycling via the copper,
# creating a parallax effect with just 3 bitplanes. The layers move in
# different sinusoidal patterns.

from amiga import Display, Bitmap, Shape, palette, copper, Color, joy, clamp, run, sin_table, cos_table

display = Display(320, 270, bitplanes=3)
bm_fg = Bitmap(480, 500, bitplanes=3)
bm_bg = Bitmap(480, 500, bitplanes=3)

# Build trig tables for smooth motion
sin_lut1 = sin_table(720)
cos_lut1 = cos_table(720)

# Create a simple tile shape (32x32 checkerboard)
tile_bm = Bitmap(32, 32, bitplanes=1)
tile_bm.clear()
tile_bm.box_filled(0, 0, 31, 31, 1)
tile_bm.box_filled(5, 5, 27, 27, 0)
tile = Shape.grab(tile_bm, 0, 0, 32, 32)

# Fill bitmaps with tiled patterns
for bmp in [bm_fg, bm_bg]:
    bmp.clear()
    for x in range(15):
        for y in range(15):
            display.blit(tile, x * 32, y * 32)

# Copper colour gradients for each layer
# Layer 1 (colour register 1): red gradient
for n in range(0, 270, 9):
    r = clamp(n // 9, 0, 14)
    copper.color_at(scanline=n, register=1, color=Color(r + 1, 0, 0))

# Layer 2 (colour register 2): green gradient
for n in range(0, 270, 9):
    g = clamp(n // 9, 0, 14)
    copper.color_at(scanline=n, register=2, color=Color(0, g + 1, 0))

# Layer 3 (colour register 4): blue gradient
for n in range(0, 270, 9):
    b = clamp(n // 9, 0, 14)
    copper.color_at(scanline=n, register=4, color=Color(0, 0, b + 1))

t = 0

def update():
    global t
    t = (t + 1) % 360

    # Each layer scrolls with a different sinusoidal pattern
    fx = int(64 + sin_lut1[t * 2 % 720] * 32)
    fy = int(64 + cos_lut1[t % 720] * 32)
    bx = int(64 + sin_lut1[t % 720] * 32)
    by = int(64 + cos_lut1[t * 2 % 720] * 32)

    display.scroll_to(fx, fy)

run(update, until=joy.button(0))
