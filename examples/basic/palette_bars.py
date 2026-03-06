# Palette colour bars
# Based on: AmiBlitz3/Sourcecodes/Examples/Classic examples/colour.ab3
#
# Displays all available colours as horizontal bars, showing the full
# OCS/ECS palette. Demonstrates palette.set() with 4-bit RGB values
# and basic filled rectangle drawing.

from amiga import Display, Bitmap, palette, wait_mouse

display = Display(320, 256, bitplanes=5)
bm = Bitmap(320, 256, bitplanes=5)

# Set up a rainbow palette across 32 colours
palette.set(0, 0, 0, 0)       # black background
palette.set(1, 15, 0, 0)      # red
palette.set(2, 15, 4, 0)
palette.set(3, 15, 8, 0)      # orange
palette.set(4, 15, 12, 0)
palette.set(5, 15, 15, 0)     # yellow
palette.set(6, 12, 15, 0)
palette.set(7, 8, 15, 0)      # yellow-green
palette.set(8, 4, 15, 0)
palette.set(9, 0, 15, 0)      # green
palette.set(10, 0, 15, 4)
palette.set(11, 0, 15, 8)     # cyan-green
palette.set(12, 0, 15, 12)
palette.set(13, 0, 15, 15)    # cyan
palette.set(14, 0, 12, 15)
palette.set(15, 0, 8, 15)     # sky blue
palette.set(16, 0, 4, 15)
palette.set(17, 0, 0, 15)     # blue
palette.set(18, 4, 0, 15)
palette.set(19, 8, 0, 15)     # indigo
palette.set(20, 12, 0, 15)
palette.set(21, 15, 0, 15)    # magenta
palette.set(22, 15, 0, 12)
palette.set(23, 15, 0, 8)     # rose
palette.set(24, 15, 0, 4)
palette.set(25, 4, 4, 4)      # dark grey
palette.set(26, 6, 6, 6)
palette.set(27, 8, 8, 8)      # mid grey
palette.set(28, 10, 10, 10)
palette.set(29, 12, 12, 12)   # light grey
palette.set(30, 14, 14, 14)
palette.set(31, 15, 15, 15)   # white

# Draw colour bars
bar_height = 256 // 32
for i in range(32):
    y = i * bar_height
    bm.box_filled(0, y, 319, y + bar_height - 1, i)

display.show(bm)
wait_mouse()
