# Top-down dungeon crawler / shooter
# Navigate a tilemap with 8-direction movement and fire projectiles.
# Loads map from Tiled JSON with blocking tile support.
#
# Controls: WASD/Arrow keys to move, Space/LMB to fire, ESC to quit

from dataclasses import dataclass
from amiga import Bitmap, Shape, Tilemap, palette, joy, rnd, run

# --- Palette (OCS 12-bit: 0-15 per channel) ---
palette.set(0, 0, 0, 0)        # black (transparent)
palette.set(1, 2, 3, 2)        # dark green-gray (floor)
palette.set(2, 5, 5, 5)        # medium gray (wall shadow / floor detail)
palette.set(3, 8, 8, 8)        # light gray (wall)
palette.set(4, 0, 12, 0)       # bright green (door / player)
palette.set(5, 0, 8, 8)        # teal (console)
palette.set(6, 8, 4, 0)        # brown (crate)
palette.set(7, 15, 15, 15)     # white (bullet / highlight)

# --- Load tilemap from Tiled JSON ---
tm = Tilemap.load_tiled("data/map.json", 320, 200, bitplanes=3)

# --- Load player sprite sheet (8 directions, 16x16 each) ---
player_sheet = Bitmap.load("data/player.png")
player_shapes: list[Shape] = []
# 0=N, 1=NE, 2=E, 3=SE, 4=S, 5=SW, 6=W, 7=NW
for i in range(8):
    player_shapes.append(Shape.grab(player_sheet, 0, i * 16, 16, 16))

# --- Load bullet shape ---
bullet_shape = Shape.load("data/bullet.png")

# --- Data structures ---
@dataclass
class Bullet:
    x: int
    y: int
    dx: int
    dy: int
    alive: int

MAX_BULLETS: int = 8
BULLET_SPEED: int = 4
PLAYER_SPEED: int = 2

bullets: list[Bullet] = []
for i in range(MAX_BULLETS):
    bullets.append(Bullet(x=0, y=0, dx=0, dy=0, alive=0))

# Direction vectors: 0=N, 1=NE, 2=E, 3=SE, 4=S, 5=SW, 6=W, 7=NW
dir_dx: list[int] = []
dir_dx.append(0)
dir_dx.append(1)
dir_dx.append(1)
dir_dx.append(1)
dir_dx.append(0)
dir_dx.append(-1)
dir_dx.append(-1)
dir_dx.append(-1)
dir_dy: list[int] = []
dir_dy.append(-1)
dir_dy.append(-1)
dir_dy.append(0)
dir_dy.append(1)
dir_dy.append(1)
dir_dy.append(1)
dir_dy.append(0)
dir_dy.append(-1)

# Player state — start in the bottom open area
player_x: int = 19 * 16 + 4
player_y: int = 22 * 16 + 4
player_dir: int = 0
prev_fire: int = 0
fire_cooldown: int = 0
done: bool = False

# Map pixel bounds
map_pw: int = 40 * 16
map_ph: int = 25 * 16

tm.show()


def update():
    global player_x, player_y, player_dir
    global prev_fire, fire_cooldown, done

    # --- Input ---
    move_x: int = 0
    move_y: int = 0
    if joy.left():
        move_x = -PLAYER_SPEED
    if joy.right():
        move_x = PLAYER_SPEED
    if joy.up():
        move_y = -PLAYER_SPEED
    if joy.down():
        move_y = PLAYER_SPEED

    # Update facing direction based on input
    if move_x != 0 or move_y != 0:
        if move_x == 0 and move_y < 0:
            player_dir = 0       # N
        if move_x > 0 and move_y < 0:
            player_dir = 1       # NE
        if move_x > 0 and move_y == 0:
            player_dir = 2       # E
        if move_x > 0 and move_y > 0:
            player_dir = 3       # SE
        if move_x == 0 and move_y > 0:
            player_dir = 4       # S
        if move_x < 0 and move_y > 0:
            player_dir = 5       # SW
        if move_x < 0 and move_y == 0:
            player_dir = 6       # W
        if move_x < 0 and move_y < 0:
            player_dir = 7       # NW

    # --- Player movement with collision (X and Y independent for wall sliding) ---
    # Collision box inset: 3px from each edge of 16x16 sprite
    if move_x != 0:
        nx: int = player_x + move_x
        x_ok: int = 1
        if tm.is_blocking(nx + 3, player_y + 3):
            x_ok = 0
        if tm.is_blocking(nx + 12, player_y + 3):
            x_ok = 0
        if tm.is_blocking(nx + 3, player_y + 12):
            x_ok = 0
        if tm.is_blocking(nx + 12, player_y + 12):
            x_ok = 0
        if x_ok == 1:
            player_x = nx

    if move_y != 0:
        ny: int = player_y + move_y
        y_ok: int = 1
        if tm.is_blocking(player_x + 3, ny + 3):
            y_ok = 0
        if tm.is_blocking(player_x + 12, ny + 3):
            y_ok = 0
        if tm.is_blocking(player_x + 3, ny + 12):
            y_ok = 0
        if tm.is_blocking(player_x + 12, ny + 12):
            y_ok = 0
        if y_ok == 1:
            player_y = ny

    # --- Firing ---
    if fire_cooldown > 0:
        fire_cooldown = fire_cooldown - 1

    fire: int = 0
    if joy.button(1):
        fire = 1

    if fire == 1 and prev_fire == 0 and fire_cooldown == 0:
        fired: int = 0
        for b in bullets:
            if b.alive == 0 and fired == 0:
                # Spawn bullet from center of player
                b.x = player_x + 4
                b.y = player_y + 4
                b.dx = dir_dx[player_dir] * BULLET_SPEED
                b.dy = dir_dy[player_dir] * BULLET_SPEED
                b.alive = 1
                fired = 1
                fire_cooldown = 8
    prev_fire = fire

    # --- Update bullets ---
    for b in bullets:
        if b.alive == 1:
            b.x = b.x + b.dx
            b.y = b.y + b.dy
            # Kill on wall hit
            if tm.is_blocking(b.x + 7, b.y + 7):
                b.alive = 0
            # Kill if out of map
            if b.x < 0 or b.x >= map_pw or b.y < 0 or b.y >= map_ph:
                b.alive = 0

    # --- Camera follows player (centered) ---
    cam_x: int = player_x - 152
    cam_y: int = player_y - 92
    tm.camera(cam_x, cam_y)

    # --- Draw player ---
    tm.draw_shape(player_shapes[player_dir], player_x, player_y)

    # --- Draw bullets ---
    for b in bullets:
        if b.alive == 1:
            tm.draw_shape(bullet_shape, b.x, b.y)


run(update, until=lambda: done)
