# Simple sprite movement
# Based on: AmiBlitz3/Sourcecodes/Examples/blitzmode examples/sprites_GetaSprite.ab3
#
# Creates a 64x64 pixel sprite from drawn boxes, then moves it across
# the screen. Demonstrates sprite creation from bitmap data, hardware
# sprite palette setup, and ShowSprite positioning.

from amiga import Display, Bitmap, Sprite, palette, vwait, wait_mouse

display = Display(320, 256, bitplanes=2)
bm = Bitmap(320, 256, bitplanes=2)

# Draw a coloured square pattern to grab as a sprite
bm.box_filled(0, 0, 63, 63, 1)
bm.box_filled(8, 8, 55, 55, 2)
bm.box_filled(16, 16, 47, 47, 3)

# Grab the drawn pattern as a hardware sprite
player = Sprite.grab(bm, 0, 0, 64, 64)

# Clear the bitmap for the background
bm.clear()
display.show(bm)

# Set sprite palette colours
# A 64-pixel-wide sprite uses 4 channels, so set palette for channels 0-1
for k in range(2):
    palette.set(k * 4 + 17, 15, 15, 0)   # yellow
    palette.set(k * 4 + 18, 15, 8, 0)    # orange
    palette.set(k * 4 + 19, 15, 4, 0)    # dark orange

# Animate the sprite moving across the screen
for k in range(320):
    vwait()
    player.show(k, 100, channel=0)

wait_mouse()
