# Starfield test - no image loading
from dataclasses import dataclass
from amiga import Display, Bitmap, palette, joy, rnd, run

@dataclass
class Star:
    x: int
    y: int
    speed: int
    color: int

SCREEN_W: int = 320
SCREEN_H: int = 200

display = Display(SCREEN_W, SCREEN_H, bitplanes=3)
bm = Bitmap(SCREEN_W, SCREEN_H, bitplanes=3)

palette.set(0, 0, 0, 0)
palette.set(1, 3, 3, 5)
palette.set(2, 5, 5, 7)
palette.set(3, 7, 7, 10)
palette.set(4, 9, 9, 12)
palette.set(5, 11, 11, 14)
palette.set(6, 13, 13, 15)
palette.set(7, 15, 15, 15)

stars: list[Star] = []

for i in range(20):
    stars.append(Star(x=rnd(SCREEN_W), y=rnd(SCREEN_H), speed=1, color=rnd(2) + 1))

for i in range(20):
    stars.append(Star(x=rnd(SCREEN_W), y=rnd(SCREEN_H), speed=3, color=rnd(2) + 3))

for i in range(20):
    stars.append(Star(x=rnd(SCREEN_W), y=rnd(SCREEN_H), speed=5, color=rnd(3) + 5))

display.show(bm)

def update():
    bm.clear()
    for star in stars:
        star.x = star.x - star.speed
        if star.x < 0:
            star.x = SCREEN_W - 1
            star.y = rnd(SCREEN_H)
        bm.plot(star.x, star.y, star.color)

run(update, until=lambda: joy.button(0))
