# Random circles drawing demo
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/display1.ab3
#
# Draws concentric filled circles with a greyscale palette.
# Demonstrates basic display setup, palette configuration, and circle drawing.

from amiga import Display, Bitmap, palette, wait_mouse

display = Display(320, 256, bitplanes=5)
bm = Bitmap(320, 256, bitplanes=5)

# Set up a greyscale palette (32 shades)
for i in range(32):
    grey = i * 8
    palette.aga(i, grey, grey, grey)

# Draw concentric filled circles from largest to smallest
# Each ring uses a different colour register
for i in range(31, 0, -1):
    bm.circle_filled(160, 128, i * 4, i)

display.show(bm)
wait_mouse()
