from amiga import Display, Bitmap, palette, wait_mouse

display = Display(320, 256, bitplanes=8)
bm = Bitmap(320, 256, bitplanes=8)

for i in range(256):
    palette.aga(i, i, i, i)

for i in range(255, 0, -1):
    bm.circle_filled(160, 128, i // 2, i)

display.show(bm)
wait_mouse()
