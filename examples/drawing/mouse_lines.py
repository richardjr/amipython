# Mouse line drawing
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/mouse.ab3
#
# Draws lines from the centre of the screen to the mouse cursor position.
# Demonstrates mouse input and real-time line drawing.

from amiga import Display, Bitmap, mouse, joy, run

display = Display(320, 256, bitplanes=3)
bm = Bitmap(320, 256, bitplanes=3)
display.show(bm)

def update():
    bm.line(160, 128, mouse.x, mouse.y, 1)

run(update, until=joy.button(0))
