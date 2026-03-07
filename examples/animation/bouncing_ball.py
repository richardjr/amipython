from amiga import Display, Bitmap, Shape, palette, run, joy, vwait

display = Display(320, 200, bitplanes=3)
bm = Bitmap(320, 200, bitplanes=3)

palette.set(1, 15, 0, 0)
bm.circle_filled(8, 8, 7, 1)
ball = Shape.grab(bm, 0, 0, 16, 16)
bm.clear()

x: float = 160.0
y: float = 100.0
xs: float = 3.0
ys: float = 2.0

display.show(bm)

def update():
    global x, y, xs, ys
    x = x + xs
    y = y + ys
    if x < 10.0 or x > 290.0:
        xs = -xs
    if y < 10.0 or y > 170.0:
        ys = -ys
    bm.clear()
    display.blit(ball, int(x), int(y))

run(update, until=lambda: joy.button(0))
