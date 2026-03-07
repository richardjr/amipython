# Sprite priority (Z-ordering)
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/sprites_InFront.ab3
#
# Shows the same sprite at two different Y positions using different
# hardware sprite channels. Channel 0 is in front of the bitmap,
# channel 4 is behind it. A large circle on the bitmap demonstrates
# the depth ordering. Channels 4-7 are set behind the playfield
# with sprites_behind().

from amiga import Display, Bitmap, Sprite, palette, vwait, wait_mouse

display = Display(320, 256, bitplanes=2)
bm = Bitmap(320, 256, bitplanes=2)

# Create a small coloured sprite
bm.box_filled(0, 0, 15, 15, 1)
bm.box_filled(2, 2, 13, 13, 2)
bm.box_filled(4, 4, 11, 11, 3)
player = Sprite.grab(bm, 0, 0, 16, 16)

# Clear and draw a large ring on the bitmap
bm.clear()
bm.circle_filled(160, 100, 90, 3)
bm.circle_filled(160, 100, 80, 0)

display.show(bm)

# Set sprite palette
palette.set(17, 15, 15, 0)
palette.set(18, 15, 8, 0)
palette.set(19, 15, 4, 0)

# Channels 4-7 render behind the playfield
display.sprites_behind(from_channel=4)

# Move both sprites across the screen
for k in range(320):
    vwait(1)
    player.show(k, 20, channel=0)    # in front of bitmap
    player.show(k, 120, channel=4)   # behind bitmap

wait_mouse()
