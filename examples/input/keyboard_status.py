# Keyboard input with RawStatus
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/blitzIO_RawStatus.ab3
#
# Displays whether the F1 key is currently held down or released.
# Demonstrates key.held() for polling keyboard state in a game loop.

from amiga import Display, Bitmap, joy, key, run

display = Display(320, 256, bitplanes=3)
bm = Bitmap(320, 256, bitplanes=3)
display.show(bm)

bm.print_at(0, 0, "Press F1 key ... (click mouse to exit)")

def update():
    if key.held(key.F1):
        bm.print_at(0, 2, "F1 Key is Currently: Down")
    else:
        bm.print_at(0, 2, "F1 Key is Currently: Up  ")

run(update, until=joy.button(0))
