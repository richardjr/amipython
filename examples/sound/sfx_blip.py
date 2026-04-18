"""SFX demo — one-shot sample playback with sfx.load / sfx.play.

Loads a short WAV "blip" and plays it every time the fire button is pressed.
On transpile, the WAV is converted to 8-bit signed mono and embedded in the
binary — no file I/O at runtime.

Controls:
    Fire (Space / LMB) — plays the blip. One tap = one play (edge-triggered).
    Close the window to exit.
"""

from amiga import Display, Bitmap, palette, sfx, joy, run

display = Display(320, 200, bitplanes=3)
screen = Bitmap(320, 200, bitplanes=3)

palette.aga(1, 200, 200, 200)
palette.aga(2, 255, 120, 40)

sfx.load(0, "data/blip.wav")

flash: int = 0
plays: int = 0


def update():
    global flash, plays
    if joy.button_pressed(0):
        sfx.play(0, volume=56)
        flash = 8
        plays = plays + 1

    screen.clear()
    screen.print_at(80, 40, "SFX BLIP", color=1)
    screen.print_at(80, 70, "PRESS FIRE", color=1)
    screen.print_at(80, 100, "PLAYS:", plays, color=1)

    if flash > 0:
        screen.box_filled(240, 40, 290, 90, 2)
        flash = flash - 1


display.show(screen)
run(update, until=lambda: False)
