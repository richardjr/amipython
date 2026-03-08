# Music playback demo
# Plays a ProTracker MOD file as background music.
# Press left mouse button to exit.

from amiga import Display, Bitmap, palette, joy, music, run

music.load("data/demo.mod")

display = Display(320, 200, bitplanes=3)
bm = Bitmap(320, 200, bitplanes=3)
palette.set(0, 0, 0, 5)
palette.set(1, 15, 15, 15)
bm.print_at(80, 96, "MUSIC PLAYING", 1)
display.show(bm)
music.play()

def update():
    pass

run(update, until=lambda: joy.button(0))
music.stop()
