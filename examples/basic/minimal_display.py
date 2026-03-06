from amiga import Display, Bitmap, palette, wait_mouse

display = Display(320, 256, bitplanes=5)
bm = Bitmap(320, 256, bitplanes=5)

palette.aga(1, 255, 0, 0)
palette.aga(2, 0, 255, 0)
palette.aga(3, 0, 0, 255)

bm.circle_filled(160, 128, 60, 1)
bm.circle_filled(160, 128, 40, 2)
bm.circle_filled(160, 128, 20, 3)

display.show(bm)
wait_mouse()
