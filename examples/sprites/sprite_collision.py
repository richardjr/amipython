# Sprite collision detection
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/sprites1.ab3
#           (sprites_Collision.ab3 / "death star collision example")
#
# A small sprite follows the mouse pointer. When the sprite overlaps
# a filled circle drawn in colour 15 (the "death star"), a collision
# is detected. Demonstrates hardware sprite/playfield collision using
# SetColl, DoColl, and PColl.

from amiga import Display, Bitmap, Sprite, collision, mouse, joy, rnd, run

display = Display(320, 200, bitplanes=4)
bm = Bitmap(320, 200, bitplanes=4)

# Draw a small box to use as the sprite graphic
bm.box_filled(0, 0, 7, 7, 1)
player = Sprite.grab(bm, 0, 0, 8, 8)

# Clear and set up the playfield
bm.clear()

# Scatter some colourful stars (any colour except 15)
for k in range(100):
    bm.plot(rnd(320), rnd(200), rnd(14) + 1)

# Draw the "death star" in colour 15
bm.circle_filled(160, 100, 40, 15)

# Register colour 15 as a collision target (mask=4)
collision.register(color=15, mask=4)

display.show(bm)
mouse.set_pointer(player)

def update():
    collision.check()
    if player.collided():
        bm.print_at(0, 0, "BANG!")
    else:
        bm.print_at(0, 0, "     ")

run(update, until=joy.button(0))
