# Tilemap scrolling demo
# Smooth tile-based scrolling with joystick control.
# Uses ACE's tileBufferManager for hardware-accelerated scrolling.
#
# Tiles: 0=floor, 1=wall, 2=wall_top, 3=door, 4=console,
#         5=pipe_h, 6=pipe_v, 7=vent

from amiga import Tilemap, palette, joy, run

# Alien Breed-style palette (OCS 12-bit: 0-15 per channel)
palette.set(0, 0, 0, 0)        # black (background)
palette.set(1, 1, 1, 1)        # very dark grey-green (deep shadow)
palette.set(2, 2, 2, 2)        # dark grey-green (floor base)
palette.set(3, 4, 4, 3)        # medium grey-green (floor highlight)
palette.set(4, 5, 5, 5)        # light grey (wall/metal)
palette.set(5, 7, 7, 6)        # bright grey (highlights, rivets)
palette.set(6, 0, 9, 6)        # tech green (screens, status)
palette.set(7, 11, 3, 2)       # warning red (lights, hazard)

# Create tilemap: 320x200 display, 3 bitplanes, 16px tiles, 40x30 map
tm = Tilemap("data/scifi_tiles.png", 320, 200, bitplanes=3,
             tile_size=16, map_w=40, map_h=30)

# Build a space station map using set_tile calls
# Helper: fill a rectangular region
def fill_region(x1: int, y1: int, x2: int, y2: int, tile: int):
    y = y1
    while y <= y2:
        x = x1
        while x <= x2:
            tm.set_tile(x, y, tile)
            x = x + 1
        y = y + 1

# Fill everything with floor first
fill_region(0, 0, 39, 29, 0)

# Outer walls
fill_region(0, 0, 39, 0, 1)   # top
fill_region(0, 29, 39, 29, 1) # bottom
fill_region(0, 0, 0, 29, 1)   # left
fill_region(39, 0, 39, 29, 1) # right

# Wall accent (top edges)
fill_region(1, 1, 38, 1, 2)
fill_region(1, 28, 38, 28, 2)

# Horizontal divider walls
fill_region(1, 10, 38, 10, 1)
fill_region(1, 11, 38, 11, 2)
fill_region(1, 20, 38, 20, 1)
fill_region(1, 21, 38, 21, 2)

# Vertical divider walls (upper section)
fill_region(10, 1, 10, 10, 1)
fill_region(20, 1, 20, 10, 1)
fill_region(30, 1, 30, 10, 1)

# Vertical divider walls (lower section)
fill_region(10, 20, 10, 29, 1)
fill_region(29, 20, 29, 29, 1)

# Doors in dividers
tm.set_tile(10, 4, 3)
tm.set_tile(20, 4, 3)
tm.set_tile(30, 4, 3)
tm.set_tile(10, 9, 3)
tm.set_tile(20, 9, 3)
tm.set_tile(30, 9, 3)
tm.set_tile(15, 10, 3)
tm.set_tile(35, 10, 3)
tm.set_tile(5, 20, 3)
tm.set_tile(24, 20, 3)
tm.set_tile(10, 24, 3)
tm.set_tile(29, 24, 3)

# Computer consoles
tm.set_tile(3, 3, 4)
tm.set_tile(7, 3, 4)
tm.set_tile(13, 6, 4)
tm.set_tile(17, 6, 4)
tm.set_tile(33, 3, 4)
tm.set_tile(36, 3, 4)
tm.set_tile(5, 15, 4)
tm.set_tile(6, 15, 4)
tm.set_tile(7, 15, 4)
tm.set_tile(8, 15, 4)
tm.set_tile(27, 15, 4)
tm.set_tile(28, 15, 4)
tm.set_tile(29, 15, 4)
tm.set_tile(30, 15, 4)
tm.set_tile(15, 27, 4)
tm.set_tile(16, 27, 4)
tm.set_tile(17, 27, 4)
tm.set_tile(18, 27, 4)
tm.set_tile(19, 27, 4)
tm.set_tile(20, 27, 4)
tm.set_tile(21, 27, 4)
tm.set_tile(22, 27, 4)

# Horizontal pipes
fill_region(2, 8, 5, 8, 5)
fill_region(21, 8, 26, 8, 5)
fill_region(2, 27, 9, 27, 5)
fill_region(30, 27, 37, 27, 5)

# Vertical pipes
tm.set_tile(23, 6, 6)
tm.set_tile(23, 7, 6)
tm.set_tile(13, 23, 6)
tm.set_tile(13, 24, 6)
tm.set_tile(13, 25, 6)
tm.set_tile(24, 23, 6)
tm.set_tile(24, 24, 6)
tm.set_tile(24, 25, 6)

# Vents
tm.set_tile(22, 3, 7)
tm.set_tile(6, 25, 7)
tm.set_tile(33, 7, 7)
tm.set_tile(35, 7, 7)
tm.set_tile(33, 25, 7)

tm.show()

scroll_speed = 2

def update():
    dx = 0
    dy = 0
    if joy.left():
        dx = -scroll_speed
    if joy.right():
        dx = scroll_speed
    if joy.up():
        dy = -scroll_speed
    if joy.down():
        dy = scroll_speed
    tm.scroll(dx, dy)

run(update, until=lambda: joy.button(0))
