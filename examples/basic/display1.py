from amiga import Display, Bitmap, palette, wait_mouse

display = Display(320, 256, bitplanes=5)
bm = Bitmap(320, 256, bitplanes=5)

for i in range(32):
    palette.aga(i, i * 8, i * 8, i * 8)

for i in range(31, 0, -1):
    bm.circle_filled(160, 128, i * 4, i)

display.show(bm)
wait_mouse()
