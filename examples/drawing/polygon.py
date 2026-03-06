# Polygon drawing demo
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/Poly.ab3
#
# Draws a filled polygon shape on an 8-colour display.
# Demonstrates the polygon_filled() drawing primitive.

from amiga import Display, Bitmap, palette, wait_mouse

display = Display(320, 256, bitplanes=3)
bm = Bitmap(320, 256, bitplanes=3)

# Set up some colours
palette.set(0, 0, 0, 0)
palette.set(1, 15, 0, 0)
palette.set(2, 0, 15, 0)
palette.set(3, 0, 0, 15)
palette.set(4, 15, 15, 0)
palette.set(5, 15, 0, 15)
palette.set(6, 0, 15, 15)
palette.set(7, 15, 15, 15)

# Draw a star-like polygon (10 vertices)
points = [
    (160, 0),
    (196, 64),
    (240, 96),
    (196, 128),
    (240, 196),
    (160, 128),
    (80, 196),
    (120, 128),
    (80, 96),
    (120, 64),
]

bm.polygon_filled(points, 5)

display.show(bm)
wait_mouse()
