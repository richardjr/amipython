# Dual playfield with automatic foreground scroll
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/dualplayfield.ab3
#
# A simpler dual playfield demo: the foreground layer auto-scrolls
# horizontally at a constant speed, while the background stays fixed.
# The foreground bitmap is twice the display width, with the right half
# being a copy of the left half for seamless wrapping.
#
# NOTE: aspirational — `DualPlayfield` is not yet implemented. ACE doesn't
# expose hardware dual-playfield mode and the manager has been deferred to a
# future engine project; see project-vault ADR 0002 (hardware-dual-playfield).

from amiga import DualPlayfield, Bitmap, palette, joy, rnd, run

# Foreground: twice the display width for seamless wrap
fg = Bitmap(640, 200, bitplanes=3)
for k in range(10):
    fg.circle_filled(rnd(256) + 32, rnd(200), rnd(24) + 8, rnd(7) + 1)

# Background: random boxes
bg = Bitmap(320, 200, bitplanes=3)
for k in range(50):
    bg.box_filled(rnd(320), rnd(100) + 50, rnd(320), rnd(100) + 50, rnd(7) + 1)

# OCS dual-playfield palettes:
#   regs 0..7  -> playfield A (foreground; reg 0 transparent)
#   regs 8..15 -> playfield B (background; reg 8 transparent)
palette.set(0, 0, 0, 0)   # PFA transparent
for i in range(1, 8):
    palette.set(i, i * 2, 14, 4)
palette.set(8, 0, 0, 4)   # PFB base (bg colour)
for i in range(9, 16):
    palette.set(i, 14, (i - 8) * 2, 2)

display = DualPlayfield(fg, bg)
display.show()

x: int = 0

def update():
    global x
    x = (x + 2) % 320
    display.scroll_fg(x, 0)

run(update, until=lambda: joy.button(0))
