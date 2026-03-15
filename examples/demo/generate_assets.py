#!/usr/bin/env python3
"""Generate game assets: tileset, player sprites, bullet, and Tiled JSON map.

Run from examples/demo/:
    python generate_assets.py
"""

import json
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

TILE_SIZE = 16

# OCS 12-bit palette (0-15 per channel, displayed as value*17 in 8-bit)
# Index: (R4, G4, B4) -> (R8, G8, B8)
PALETTE_OCS = [
    (0, 0, 0),      # 0: black (transparent)
    (2, 3, 2),      # 1: dark green-gray (floor)
    (5, 5, 5),      # 2: medium gray (floor detail / wall shadow)
    (8, 8, 8),      # 3: light gray (wall)
    (0, 12, 0),     # 4: bright green (door / player)
    (0, 8, 8),      # 5: teal (console / tech)
    (8, 4, 0),      # 6: brown (crate)
    (15, 15, 15),   # 7: white (bullet / highlight)
]

# Expand to 8-bit RGB for PIL
PALETTE_RGB = []
for r, g, b in PALETTE_OCS:
    PALETTE_RGB.extend([r * 17, g * 17, b * 17])
# Pad to 256 colors
PALETTE_RGB.extend([0] * (768 - len(PALETTE_RGB)))


def make_indexed(w, h):
    """Create an 8-bit indexed PIL image with our palette."""
    img = Image.new("P", (w, h), 0)
    img.putpalette(PALETTE_RGB)
    return img


def draw_rect(img, x1, y1, x2, y2, color):
    """Fill a rectangle with a color index."""
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            if 0 <= x < img.width and 0 <= y < img.height:
                img.putpixel((x, y), color)


def draw_border(img, x1, y1, x2, y2, color):
    """Draw a 1px border rectangle."""
    for x in range(x1, x2 + 1):
        img.putpixel((x, y1), color)
        img.putpixel((x, y2), color)
    for y in range(y1, y2 + 1):
        img.putpixel((x1, y), color)
        img.putpixel((x2, y), color)


# ---------------------------------------------------------------------------
# Tileset: 8 tiles in a vertical strip (16 x 128)
# ---------------------------------------------------------------------------
def generate_tileset():
    ts = TILE_SIZE
    num_tiles = 8
    img = make_indexed(ts, ts * num_tiles)

    def tile_offset(tile_idx):
        return tile_idx * ts

    # Tile 0: Floor — dark with subtle dot pattern
    y0 = tile_offset(0)
    draw_rect(img, 0, y0, 15, y0 + 15, 1)
    for dy in range(0, 16, 4):
        for dx in range(0, 16, 4):
            img.putpixel((dx, y0 + dy), 2)

    # Tile 1: Wall — solid light gray with border
    y0 = tile_offset(1)
    draw_rect(img, 0, y0, 15, y0 + 15, 3)
    draw_border(img, 0, y0, 15, y0 + 15, 2)
    # Brick-like horizontal lines
    for x in range(1, 15):
        img.putpixel((x, y0 + 4), 2)
        img.putpixel((x, y0 + 8), 2)
        img.putpixel((x, y0 + 12), 2)

    # Tile 2: Wall shadow — darker wall edge
    y0 = tile_offset(2)
    draw_rect(img, 0, y0, 15, y0 + 15, 2)
    # Top highlight
    for x in range(16):
        img.putpixel((x, y0), 3)

    # Tile 3: Door — floor with green vertical stripe
    y0 = tile_offset(3)
    draw_rect(img, 0, y0, 15, y0 + 15, 1)
    draw_rect(img, 6, y0, 9, y0 + 15, 4)
    # Door frame
    img.putpixel((6, y0), 3)
    img.putpixel((9, y0), 3)
    img.putpixel((6, y0 + 15), 3)
    img.putpixel((9, y0 + 15), 3)

    # Tile 4: Crate — brown with cross pattern
    y0 = tile_offset(4)
    draw_rect(img, 0, y0, 15, y0 + 15, 6)
    draw_border(img, 0, y0, 15, y0 + 15, 3)
    draw_border(img, 1, y0 + 1, 14, y0 + 14, 2)
    # Cross
    for i in range(2, 14):
        img.putpixel((i, y0 + 7), 3)
        img.putpixel((i, y0 + 8), 3)
        img.putpixel((7, y0 + i), 3)
        img.putpixel((8, y0 + i), 3)

    # Tile 5: Console — teal with white screen
    y0 = tile_offset(5)
    draw_rect(img, 0, y0, 15, y0 + 15, 5)
    draw_border(img, 0, y0, 15, y0 + 15, 2)
    # Screen area
    draw_rect(img, 3, y0 + 3, 12, y0 + 8, 7)
    draw_border(img, 3, y0 + 3, 12, y0 + 8, 2)
    # Buttons below screen
    draw_rect(img, 4, y0 + 11, 5, y0 + 12, 4)
    draw_rect(img, 7, y0 + 11, 8, y0 + 12, 7)
    draw_rect(img, 10, y0 + 11, 11, y0 + 12, 4)

    # Tile 6: Alt floor — slightly lighter
    y0 = tile_offset(6)
    draw_rect(img, 0, y0, 15, y0 + 15, 2)
    for dy in range(0, 16, 8):
        for dx in range(0, 16, 8):
            img.putpixel((dx + 2, y0 + dy + 2), 1)

    # Tile 7: Hazard — floor with red/white warning X
    y0 = tile_offset(7)
    draw_rect(img, 0, y0, 15, y0 + 15, 1)
    # X pattern
    for i in range(16):
        img.putpixel((i, y0 + i), 7)
        img.putpixel((15 - i, y0 + i), 7)

    img.save(OUT / "tiles.png")
    print(f"Wrote {OUT / 'tiles.png'}")
    return num_tiles


# ---------------------------------------------------------------------------
# Player sprites: 8 directions in a vertical strip (16 x 128)
# Directions: 0=N, 1=NE, 2=E, 3=SE, 4=S, 5=SW, 6=W, 7=NW
# ---------------------------------------------------------------------------
def generate_player():
    ts = TILE_SIZE
    img = make_indexed(ts, ts * 8)

    # Direction vectors (dx, dy) for each of 8 directions
    dirs = [
        (0, -1),   # 0: N
        (1, -1),   # 1: NE
        (1, 0),    # 2: E
        (1, 1),    # 3: SE
        (0, 1),    # 4: S
        (-1, 1),   # 5: SW
        (-1, 0),   # 6: W
        (-1, -1),  # 7: NW
    ]

    for idx, (ddx, ddy) in enumerate(dirs):
        y0 = idx * ts
        cx, cy = 7, 7  # center of tile

        # Body: 6x6 filled square (color 4 = green)
        draw_rect(img, cx - 3 + 0, y0 + cy - 3, cx + 2 + 0, y0 + cy + 2, 4)

        # Eyes/face indicator (color 7 = white) — 2 dots near front
        if ddy < 0:  # facing up
            img.putpixel((cx - 1, y0 + cy - 2), 7)
            img.putpixel((cx + 1, y0 + cy - 2), 7)
        elif ddy > 0:  # facing down
            img.putpixel((cx - 1, y0 + cy + 2), 7)
            img.putpixel((cx + 1, y0 + cy + 2), 7)
        if ddx > 0 and ddy == 0:  # facing right
            img.putpixel((cx + 2, y0 + cy - 1), 7)
            img.putpixel((cx + 2, y0 + cy + 1), 7)
        elif ddx < 0 and ddy == 0:  # facing left
            img.putpixel((cx - 3, y0 + cy - 1), 7)
            img.putpixel((cx - 3, y0 + cy + 1), 7)

        # Gun barrel: 4 pixels extending in facing direction (color 7 = white)
        for step in range(1, 5):
            gx = cx + ddx * (3 + step)
            gy = cy + ddy * (3 + step)
            if 0 <= gx < ts and 0 <= gy < ts:
                img.putpixel((gx, y0 + gy), 7)
                # Make barrel 2px wide for cardinal directions
                if ddx == 0 and 0 <= gx + 1 < ts:
                    img.putpixel((gx + 1, y0 + gy), 7)
                if ddy == 0 and 0 <= gy + 1 < ts:
                    img.putpixel((gx, y0 + gy + 1), 7)

    img.save(OUT / "player.png")
    print(f"Wrote {OUT / 'player.png'}")


# ---------------------------------------------------------------------------
# Bullet sprite: 16x16 with small bright dot
# ---------------------------------------------------------------------------
def generate_bullet():
    ts = TILE_SIZE
    img = make_indexed(ts, ts)

    # 4x4 bright dot in center
    draw_rect(img, 6, 6, 9, 9, 7)
    # Core pixel brighter (still 7, max palette)
    img.putpixel((7, 7), 7)
    img.putpixel((8, 7), 7)
    img.putpixel((7, 8), 7)
    img.putpixel((8, 8), 7)

    img.save(OUT / "bullet.png")
    print(f"Wrote {OUT / 'bullet.png'}")


# ---------------------------------------------------------------------------
# Tiled JSON map (40 x 25 tiles)
# ---------------------------------------------------------------------------
def generate_map(num_tiles):
    MAP_W = 40
    MAP_H = 25

    # Start with all floor (tile 0)
    grid = [[0] * MAP_W for _ in range(MAP_H)]

    def fill(x1, y1, x2, y2, t):
        for y in range(y1, min(y2 + 1, MAP_H)):
            for x in range(x1, min(x2 + 1, MAP_W)):
                grid[y][x] = t

    def put(x, y, t):
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            grid[y][x] = t

    # Outer walls
    fill(0, 0, 39, 0, 1)
    fill(0, 24, 39, 24, 1)
    fill(0, 0, 0, 24, 1)
    fill(39, 0, 39, 24, 1)

    # Wall shadow below outer top wall
    fill(1, 1, 38, 1, 2)

    # --- Upper section (rows 0-7) ---
    # Vertical wall at x=9, rows 1-6
    fill(9, 1, 9, 6, 1)
    # Vertical wall at x=20, rows 1-6
    fill(20, 1, 20, 6, 1)
    # Horizontal wall at row 7
    fill(1, 7, 38, 7, 1)
    # Wall shadow at row 8
    fill(1, 8, 38, 8, 2)

    # Doors in upper walls
    put(9, 4, 3)    # left room door
    put(20, 4, 3)   # center room door
    put(5, 7, 3)    # corridor door left
    put(15, 7, 3)   # corridor door center
    put(5, 8, 1)    # fix shadow under door
    put(15, 8, 1)   # fix shadow under door

    # --- Middle section (rows 7-13) ---
    # Vertical wall at x=26, rows 7-13
    fill(26, 7, 26, 13, 1)
    # Horizontal wall at row 13
    fill(1, 13, 38, 13, 1)
    # Wall shadow at row 14
    fill(1, 14, 38, 14, 2)

    # Doors in middle walls
    put(26, 10, 3)  # right room door
    put(9, 13, 3)   # corridor door left
    put(30, 13, 3)  # corridor door right
    put(9, 14, 1)   # fix shadow
    put(30, 14, 1)  # fix shadow

    # --- Lower section (rows 13-20) ---
    # Vertical wall at x=11, rows 14-19
    fill(11, 14, 11, 19, 1)
    # Vertical wall at x=28, rows 14-19
    fill(28, 14, 28, 19, 1)
    # Horizontal wall at row 20
    fill(1, 20, 38, 20, 1)
    # Wall shadow at row 21
    fill(1, 21, 38, 21, 2)

    # Doors in lower walls
    put(11, 17, 3)  # left room door
    put(28, 17, 3)  # right room door
    put(16, 20, 3)  # corridor door left
    put(23, 20, 3)  # corridor door right
    put(16, 21, 1)  # fix shadow
    put(23, 21, 1)  # fix shadow

    # --- Bottom open area (rows 20-24) ---
    # (kept open for now)

    # --- Furniture ---
    # Crates in lower rooms
    put(3, 18, 4)
    put(4, 18, 4)
    put(3, 19, 4)
    put(35, 18, 4)
    put(36, 18, 4)
    put(36, 19, 4)

    # Crates in upper right area
    put(25, 3, 4)
    put(29, 3, 4)
    put(25, 5, 4)
    put(29, 5, 4)

    # Consoles
    put(3, 3, 5)
    put(4, 3, 5)
    put(14, 3, 5)
    put(15, 3, 5)
    put(32, 10, 5)
    put(33, 10, 5)
    put(15, 16, 5)
    put(16, 16, 5)

    # Hazard markings in bottom area
    put(10, 22, 7)
    put(10, 23, 7)
    put(29, 22, 7)
    put(29, 23, 7)

    # Alt floor in some rooms
    fill(22, 2, 24, 5, 6)
    fill(30, 2, 38, 5, 6)

    # Convert to Tiled JSON data (row-major, 1-indexed GIDs)
    # firstgid = 1, so tile 0 -> GID 1, tile 1 -> GID 2, etc.
    FIRST_GID = 1
    data = []
    for y in range(MAP_H):
        for x in range(MAP_W):
            data.append(grid[y][x] + FIRST_GID)

    # Blocking tiles: wall (1), wall shadow (2), crate (4), console (5)
    blocking_ids = [1, 2, 4, 5]

    tiled_json = {
        "compressionlevel": -1,
        "height": MAP_H,
        "infinite": False,
        "layers": [
            {
                "data": data,
                "height": MAP_H,
                "id": 1,
                "name": "Ground",
                "opacity": 1,
                "type": "tilelayer",
                "visible": True,
                "width": MAP_W,
                "x": 0,
                "y": 0,
            }
        ],
        "nextlayerid": 2,
        "nextobjectid": 1,
        "orientation": "orthogonal",
        "renderorder": "right-down",
        "tiledversion": "1.11.0",
        "tileheight": TILE_SIZE,
        "tilewidth": TILE_SIZE,
        "tilesets": [
            {
                "columns": 1,
                "firstgid": FIRST_GID,
                "image": "tiles.png",
                "imageheight": TILE_SIZE * num_tiles,
                "imagewidth": TILE_SIZE,
                "margin": 0,
                "name": "tiles",
                "spacing": 0,
                "tilecount": num_tiles,
                "tileheight": TILE_SIZE,
                "tilewidth": TILE_SIZE,
                "tiles": [
                    {
                        "id": tid,
                        "properties": [
                            {
                                "name": "blocking",
                                "type": "bool",
                                "value": True,
                            }
                        ],
                    }
                    for tid in blocking_ids
                ],
            }
        ],
        "type": "map",
        "version": "1.10",
        "width": MAP_W,
    }

    with open(OUT / "map.json", "w") as f:
        json.dump(tiled_json, f, indent=2)
    print(f"Wrote {OUT / 'map.json'}")


if __name__ == "__main__":
    num_tiles = generate_tileset()
    generate_player()
    generate_bullet()
    generate_map(num_tiles)
    print("Done!")
