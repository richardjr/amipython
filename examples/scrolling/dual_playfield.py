# Dual playfield parallax scrolling
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/dualpf.ab3
#
# Two independent layers (foreground and background) scroll in opposite
# sinusoidal patterns, creating a parallax effect. The foreground has
# random lines, the background has random circles. Uses pre-scaled
# integer trig tables so the per-frame maths is all-integer.

from amiga import DualPlayfield, Bitmap, palette, joy, rnd, run, sin_table, cos_table

fg = Bitmap(640, 512, bitplanes=3)
bg = Bitmap(640, 512, bitplanes=3)

# Foreground: random lines
for i in range(256):
    fg.line(rnd(640), rnd(512), rnd(640), rnd(512), rnd(7) + 1)

# Background: random filled circles
for i in range(256):
    bg.circle_filled(rnd(640), rnd(512), rnd(15), rnd(7) + 1)

# OCS dual-playfield palettes:
#   regs 0..7  -> playfield A (foreground; reg 0 transparent)
#   regs 8..15 -> playfield B (background; reg 8 transparent)
palette.set(0, 0, 0, 0)
for i in range(1, 8):
    palette.set(i, 14, i * 2, 2)
palette.set(8, 0, 0, 3)
for i in range(9, 16):
    palette.set(i, (i - 8) * 2, 6, 14)

display = DualPlayfield(fg, bg)
display.show()

# Pre-scaled integer trig tables: values in -160..160 / -128..128
sx_lut = sin_table(720, 160)
cy_lut = cos_table(720, 128)

t: int = 0

def update():
    global t
    t = (t + 3) % 720
    fx = 160 + sx_lut[t]
    fy = 128 + cy_lut[t]
    display.scroll_fg(fx, fy)
    display.scroll_bg(320 - fx, 256 - fy)

run(update, until=lambda: joy.button(0))
