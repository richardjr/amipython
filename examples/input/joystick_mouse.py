# Joystick and mouse input display
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/mouseOfTwo.ab3
#           and blitzmode examples/mouse.ab3
#
# Shows real-time mouse position, joystick direction, and combined
# input state. Demonstrates all input APIs: mouse.x/y, joy.x/y,
# joy.button, and key.held.

from amiga import Display, Bitmap, mouse, joy, key, run

display = Display(320, 200, bitplanes=2)
bm = Bitmap(320, 200, bitplanes=2)
display.show(bm)

def update():
    bm.print_at(0, 0, f"Mouse X = {mouse.x}    ")
    bm.print_at(0, 1, f"Mouse Y = {mouse.y}    ")
    bm.print_at(0, 2, f"Joy X   = {joy.x(1)}   ")
    bm.print_at(0, 3, f"Joy Y   = {joy.y(1)}   ")
    bm.print_at(0, 4, f"Joy Btn = {joy.button(1)}   ")
    bm.print_at(0, 6, f"Mouse Speed X = {mouse.x_speed}   ")
    bm.print_at(0, 7, f"Mouse Speed Y = {mouse.y_speed}   ")

    if key.held(key.ESC):
        bm.print_at(0, 9, "ESC held   ")
    else:
        bm.print_at(0, 9, "ESC not held")

run(update, until=joy.button(0))
