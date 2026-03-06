# Copper gradient background
# Based on: AmiBlitz3 copper techniques used across multiple examples
#
# Creates a smooth colour gradient down the screen using the copper
# coprocessor. Each scanline gets a slightly different background colour,
# producing a sky-like gradient from dark blue at the top to orange at
# the bottom. No CPU cost -- the copper handles it all in hardware.

from amiga import Display, Bitmap, palette, copper, Color, wait_mouse

display = Display(320, 256, bitplanes=1)
bm = Bitmap(320, 256, bitplanes=1)

# Base palette
palette.set(0, 0, 0, 0)
palette.set(1, 15, 15, 15)

# Draw some simple scenery with the single bitplane
# (foreground colour only)
bm.line(0, 200, 160, 140, 1)
bm.line(160, 140, 320, 200, 1)
for y in range(200, 256):
    bm.line(0, y, 320, y, 1)

# Set up a copper gradient on colour register 0 (background)
# Top: dark blue (0,0,8) -> Middle: purple (8,0,8) -> Bottom: orange (15,8,0)
for scanline in range(256):
    if scanline < 128:
        # Blue to purple
        r = scanline // 16
        g = 0
        b = 8 + scanline // 32
    else:
        # Purple to orange
        t = scanline - 128
        r = 8 + t // 16
        g = t // 16
        b = max(0, 8 - t // 16)

    r = min(r, 15)
    g = min(g, 15)
    b = min(b, 15)
    copper.color_at(scanline=scanline, register=0, color=Color(r, g, b))

display.show(bm)
wait_mouse()
