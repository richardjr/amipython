# Double-buffered tile scrolling
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/dbscrolling.ab3
#
# Horizontal tile-based scrolling with double buffering. The tilemap
# is wider than the display; as the viewport scrolls, new tile columns
# are blitted in at the edges. Joystick or arrow keys control scroll
# direction, with acceleration and momentum.
#
# This demonstrates the Tilemap object which handles the oversized
# bitmap, tile column replacement, and QWrap scroll offset internally.

from amiga import Display, Tilemap, joy, key, run

display = Display(320, 192, bitplanes=3, double_buffer=True)
tilemap = Tilemap.load("data/scrollmap", tile_shape="data/block")

accel = 0.25
speed_x = 0.0

def update():
    global speed_x

    if joy.x(1) == -1 or key.held(key.LEFT):
        speed_x -= accel
        if speed_x < -8:
            speed_x += accel
    elif joy.x(1) == 1 or key.held(key.RIGHT):
        speed_x += accel
        if speed_x > 8:
            speed_x -= accel
    elif joy.y(1) != 0 or key.held(key.DOWN):
        speed_x = 0.0

    tilemap.scroll(speed_x, 0)

run(update, until=lambda: joy.button(1) or key.pressed(key.ESC))
