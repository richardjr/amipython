# Dual playfield parallax scrolling
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/dualpf.ab3
#
# Two independent layers (foreground and background) scroll in opposite
# sinusoidal patterns, creating a parallax effect. The foreground has
# random lines, the background has random circles.

from amiga import DualPlayfield, Bitmap, joy, sin, cos, rnd, run

fg = Bitmap(640, 512, bitplanes=3)
bg = Bitmap(640, 512, bitplanes=3)

# Foreground: random lines
for i in range(256):
    fg.line(rnd(640), rnd(512), rnd(640), rnd(512), rnd(7))

# Background: random filled circles
for i in range(256):
    bg.circle_filled(rnd(640), rnd(512), rnd(15), rnd(7))

display = DualPlayfield(fg, bg)
r = 0.0

def update():
    global r
    x1 = int(160 + sin(r) * 160)
    y1 = int(128 + cos(r) * 128)
    x2 = int(160 - sin(r) * 160)
    y2 = int(128 - cos(r) * 128)
    display.scroll_fg(x1, y1)
    display.scroll_bg(x2, y2)
    r += 0.05

run(update, until=joy.button(0))
