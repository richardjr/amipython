# Sprite collision detection
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/sprites1.ab3
#           (sprites_Collision.ab3 / "death star collision example")
#
# A crosshair follows the mouse pointer. When it overlaps the "death star"
# circle drawn in colour 15, a collision is detected.

from amiga import Display, Bitmap, Sprite, palette, collision, mouse, joy, rnd, run

display = Display(320, 200, bitplanes=4)
bm = Bitmap(320, 200, bitplanes=4)

# Set up palette
palette.set(14, 0, 15, 0)    # green for crosshair + text
palette.set(15, 15, 15, 15)  # white death star

# Draw a small box to use as the sprite graphic
bm.box_filled(0, 0, 7, 7, 1)
player = Sprite.grab(bm, 0, 0, 8, 8)
bm.clear()

# Draw the "death star" in colour 15
bm.circle_filled(160, 100, 40, 15)

# Register colour 15 as a collision target (mask=4)
collision.register(color=15, mask=4)

display.show(bm)
mouse.set_pointer(player)

# Track previous crosshair position for erase
ox: int = 160
oy: int = 100

def update():
    global ox, oy
    mx: int = mouse.x
    my: int = mouse.y

    # Erase old crosshair (draw over in black)
    bm.line(ox - 12, oy, ox + 12, oy, 0)
    bm.line(ox, oy - 12, ox, oy + 12, 0)

    # Restore death star where old crosshair may have cut through it
    bm.circle_filled(160, 100, 40, 15)

    # Check collision BEFORE drawing crosshair — otherwise we read
    # the crosshair colour (14) instead of the circle colour (15)
    collision.check()

    # Draw new crosshair
    bm.line(mx - 12, my, mx + 12, my, 14)
    bm.line(mx, my - 12, mx, my + 12, 14)

    # Show status
    if player.collided():
        bm.print_at(0, 0, "BANG!", color=15)
    else:
        bm.print_at(0, 0, "MISS", color=14)

    ox = mx
    oy = my

run(update, until=lambda: joy.button(0))
