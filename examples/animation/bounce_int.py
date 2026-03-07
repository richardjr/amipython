from amiga import Display, Bitmap, palette, run, joy, vwait

display = Display(320, 200, bitplanes=3)
bm = Bitmap(320, 200, bitplanes=3)

palette.set(1, 15, 0, 0)

x: int = 160
y: int = 100
xs: int = 3
ys: int = 2

bm.circle_filled(x, y, 8, 1)
display.show(bm)

def update():
    global x, y, xs, ys
    x = x + xs
    y = y + ys
    if x < 10 or x > 290:
        xs = -xs
    if y < 10 or y > 170:
        ys = -ys
    bm.clear()
    bm.circle_filled(x, y, 8, 1)

run(update, until=lambda: joy.button(0))
