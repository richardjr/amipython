# Joystick and mouse input display
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/mouseOfTwo.ab3
#           and blitzmode examples/mouse.ab3
#
# Shows real-time mouse position, joystick direction and button state.
# Demonstrates the input APIs: mouse.x/y, joy.left/right/up/down,
# joy.button and key.pressed.

from amiga import Display, Bitmap, mouse, joy, key, K_ESC, run

display = Display(320, 200, bitplanes=2)
bm = Bitmap(320, 200, bitplanes=2)
display.show(bm)

def update():
    bm.print_at(0, 0, "Mouse X = ", mouse.x, "   ")
    bm.print_at(0, 8, "Mouse Y = ", mouse.y, "   ")
    bm.print_at(0, 24, "Joy left  = ", joy.left(), "  ")
    bm.print_at(0, 32, "Joy right = ", joy.right(), "  ")
    bm.print_at(0, 40, "Joy up    = ", joy.up(), "  ")
    bm.print_at(0, 48, "Joy down  = ", joy.down(), "  ")
    bm.print_at(0, 56, "Joy fire  = ", joy.button(1), "  ")
    if key.pressed(K_ESC):
        bm.print_at(0, 72, "ESC held    ")
    else:
        bm.print_at(0, 72, "ESC not held")

run(update, until=lambda: joy.button(0))
