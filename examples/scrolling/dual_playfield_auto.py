# Dual playfield with automatic foreground scroll
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/dualplayfield.ab3
#
# A simpler dual playfield demo: the foreground layer auto-scrolls
# horizontally at a constant speed, while the background stays fixed.
# The foreground bitmap is twice the display width, with the right half
# being a copy of the left half for seamless wrapping.

from amiga import DualPlayfield, Bitmap, joy, rnd, wrap, run

# Foreground: twice the display width for seamless wrap
fg = Bitmap(640, 200, bitplanes=3)
for k in range(10):
    fg.circle_filled(rnd(256) + 32, rnd(200), rnd(24) + 8, rnd(7) + 1)

# Copy left half to right half for seamless scrolling
fg.copy_region(0, 0, 320, 200, 320, 0)

# Background: random boxes
bg = Bitmap(320, 200, bitplanes=3)
for k in range(50):
    bg.box_filled(rnd(320), rnd(100) + 50, rnd(320), rnd(100) + 50, rnd(7) + 1)

display = DualPlayfield(fg, bg)

x = 0

def update():
    global x
    x = int(wrap(x + 2, 0, 320))
    display.scroll_fg(x, 0)

run(update, until=joy.button(0))
