# Keyboard input with RawStatus
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/blitzIO_RawStatus.ab3
#
# Displays whether the RETURN key is currently held down or released.
# Demonstrates key.pressed() for polling keyboard state in a game loop.

from amiga import Display, Bitmap, joy, key, K_RETURN, run

display = Display(320, 256, bitplanes=3)
bm = Bitmap(320, 256, bitplanes=3)
display.show(bm)

bm.print_at(0, 0, "Hold RETURN ... (click mouse to exit)")

def update():
    if key.pressed(K_RETURN):
        bm.print_at(0, 16, "RETURN is currently: Down")
    else:
        bm.print_at(0, 16, "RETURN is currently: Up  ")

run(update, until=lambda: joy.button(0))
