# Keyboard typing demo
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/blitzIO_Blitzkeys.ab3
#
# Displays typed characters on screen. A simple text input demo
# showing key.char() for reading keyboard input.

from amiga import Display, Bitmap, joy, key, run

display = Display(320, 256, bitplanes=3)
bm = Bitmap(320, 256, bitplanes=3)
display.show(bm)

bm.print_at(0, 0, "Type Away ..... (Click mouse to exit)")

cursor_x = 0
cursor_y = 2

def update():
    global cursor_x, cursor_y
    ch = key.char()
    if ch:
        bm.print_at(cursor_x, cursor_y, ch)
        cursor_x += 1
        if cursor_x >= 40:
            cursor_x = 0
            cursor_y += 1
            if cursor_y >= 32:
                cursor_y = 2
                bm.clear()
                bm.print_at(0, 0, "Type Away ..... (Click mouse to exit)")

run(update, until=joy.button(0))
