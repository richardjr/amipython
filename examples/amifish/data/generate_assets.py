#!/usr/bin/env python3
"""Generate amifish sprites + logo as 8-bit indexed PNGs.

Design constraints (so the same PNG works in pygame preview AND on real
Amiga hardware sprites):

1. Real Amiga hardware sprites are 2-bitplane (4 colours, including
   transparent). The C runtime's `Sprite.grab` copies only the LOWER TWO
   bitplanes of the source bitmap; upper bits are silently discarded.

2. Each hardware sprite channel-pair has its own colour palette slot:
       channels 0/1 → palette regs 17, 18, 19 (16 = transparent)
       channels 2/3 → palette regs 21, 22, 23
       channels 4/5 → palette regs 25, 26, 27
       channels 6/7 → palette regs 29, 30, 31

3. Pygame preview reads pixel values directly through the PNG palette,
   so each cell needs to draw with PNG indices that *also* render
   correctly under the screen's playfield palette. We satisfy both by
   choosing per-cell pixel values whose lower-2-bits encode the sprite
   colour 1/2/3 we want, while the higher bits select a unique PNG
   palette slot per kind:

       cell 0 (boat,      ch0): pixel values 0, 1, 2, 3
       cell 1 (hook,      ch1): values 0, 3            (only white visible)
       cell 2 (small a,   ch2): values 0, 5, 6, 7      (lower 2 bits = 0,1,2,3)
       cell 3 (small b,   ch3): values 0, 5, 6, 7
       cell 4 (medium,    ch4): values 0, 9, 10, 11
       cell 5 (large,     ch5): values 0, 9, 10, 11
       cell 6 (rare,      ch6): values 0, 13, 14, 15
       cell 7 (eel,       ch7): values 0, 13, 14, 15

   On Amiga, the lower 2 bits of every value pick sprite colour 1/2/3
   in that channel-pair's palette slot. In preview, the PNG palette
   index renders directly in pygame.

Run from examples/amifish/data/:
    python generate_assets.py
"""

from pathlib import Path
from PIL import Image

OUT = Path(__file__).parent
OUT.mkdir(exist_ok=True)


# PNG palette: 16 colours, OCS-fidelity (every channel a multiple of 17 so the
# value survives `>>4 then *17` round-tripping into 4-bit OCS regs).
#
# Indices 4, 8, 12 are intentionally black so a stray pixel at those values
# reads as transparent on Amiga (lower 2 bits = 0).
PALETTE_RGB_TUPLES = [
    (0, 0, 0),         # 0  transparent (and screen sky-deep / sea-deep)
    (255, 238, 68),    # 1  yellow         (boat hull)              -> reg 17
    (136, 68, 17),     # 2  brown          (boat trim, mast)        -> reg 18
    (255, 255, 255),   # 3  white          (boat highlight, hook)   -> reg 19
    (0, 0, 0),         # 4  unused
    (255, 153, 34),    # 5  orange         (small fish body)        -> reg 21
    (204, 102, 17),    # 6  dark orange    (small fish detail)      -> reg 22
    (238, 238, 238),   # 7  off-white      (small fish eye)         -> reg 23
    (0, 0, 0),         # 8  unused
    (68, 204, 68),     # 9  green          (medium/large fish body) -> reg 25
    (17, 102, 17),     # 10 dark green     (medium/large detail)    -> reg 26
    (221, 238, 221),   # 11 pale green     (medium/large eye)       -> reg 27
    (0, 0, 0),         # 12 unused
    (170, 51, 238),    # 13 violet         (rare/eel body)          -> reg 29
    (255, 238, 68),    # 14 bright yellow  (rare/eel zap)           -> reg 30
    (255, 221, 221),   # 15 pale pink      (rare/eel highlight)     -> reg 31
]

PALETTE_RGB: list[int] = []
for r, g, b in PALETTE_RGB_TUPLES:
    PALETTE_RGB.extend([r, g, b])
PALETTE_RGB.extend([0] * (768 - len(PALETTE_RGB)))


def make_indexed(w: int, h: int) -> Image.Image:
    img = Image.new("P", (w, h), 0)
    img.putpalette(PALETTE_RGB)
    return img


def fill_rect(img: Image.Image, x1: int, y1: int, x2: int, y2: int, c: int) -> None:
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            if 0 <= x < img.width and 0 <= y < img.height:
                img.putpixel((x, y), c)


def put(img: Image.Image, x: int, y: int, c: int) -> None:
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), c)


# ---------------------------------------------------------------------------
# Sprite sheet — 16×16 cells, 8 cells stacked vertically (16×128 image).
# Cell index N lives at y in [N*16, N*16+15].
# ---------------------------------------------------------------------------
CELL = 16
N_CELLS = 8


def y0(idx: int) -> int:
    return idx * CELL


def draw_boat(img: Image.Image, idx: int) -> None:
    """Cell 0 — boat with angler (ch0 palette: yellow / brown / white)."""
    base = y0(idx)
    # Hull (yellow, value 1)
    fill_rect(img, 2, base + 11, 13, base + 13, 1)
    fill_rect(img, 3, base + 10, 12, base + 10, 1)
    # Bottom waterline (brown, value 2)
    fill_rect(img, 4, base + 14, 11, base + 14, 2)
    # Mast (brown)
    fill_rect(img, 7, base + 3, 7, base + 9, 2)
    # Angler torso (white, value 3) — using value 3 so it renders white on
    # Amiga sprite reg 19; pygame shows PNG[3] = white too.
    fill_rect(img, 6, base + 7, 8, base + 9, 3)
    # Angler head (also white, smaller box)
    fill_rect(img, 6, base + 5, 8, base + 6, 3)
    # Fishing rod (brown diagonal toward upper-right)
    put(img, 9, base + 7, 2)
    put(img, 10, base + 6, 2)
    put(img, 11, base + 5, 2)
    put(img, 12, base + 4, 2)
    put(img, 13, base + 3, 2)
    # Hull glints
    put(img, 5, base + 11, 3)
    put(img, 10, base + 12, 3)


def draw_hook(img: Image.Image, idx: int) -> None:
    """Cell 1 — hook (ch1 shares ch0 palette; only colour 3 = white used)."""
    base = y0(idx)
    fill_rect(img, 7, base + 0, 7, base + 8, 3)   # vertical line
    put(img, 7, base + 9, 3)                       # hook curve
    put(img, 6, base + 10, 3)
    put(img, 6, base + 11, 3)
    put(img, 7, base + 12, 3)
    put(img, 8, base + 12, 3)
    put(img, 9, base + 11, 3)
    put(img, 9, base + 9, 3)                       # barb


def draw_fish(img: Image.Image, idx: int, body: int, detail: int, eye: int,
              x1: int, y1: int, x2: int, y2: int) -> None:
    """Generic fish — `body / detail / eye` are the three PNG palette indices
    for this cell's channel-pair (1/2/3 lower-bits-wise).
    Bounding box (x1..x2, y1..y2) is *inside* the cell."""
    base = y0(idx)
    cy = (y1 + y2) // 2
    # Body
    fill_rect(img, x1 + 2, base + y1, x2 - 2, base + y2, body)
    # Tail
    put(img, x1, base + y1, body)
    put(img, x1, base + y2, body)
    put(img, x1 + 1, base + cy, body)
    # Head taper
    put(img, x2 - 1, base + cy, body)
    put(img, x2, base + cy, body)
    # Eye dot (transparent inside a small white spot)
    put(img, x2 - 2, base + y1 + 1, 0)
    put(img, x2 - 3, base + y1 + 1, eye)
    # Belly highlight
    fill_rect(img, x1 + 3, base + y2, x2 - 3, base + y2, detail)
    # Top fin
    put(img, (x1 + x2) // 2, base + y1 - 1, detail)


def draw_eel(img: Image.Image, idx: int, body: int, zap: int, eye: int) -> None:
    """Cell 7 — eel: violet body with yellow zap dots, white eye."""
    base = y0(idx)
    fill_rect(img, 1, base + 7, 14, base + 9, body)
    put(img, 4, base + 6, body)
    put(img, 11, base + 10, body)
    # Zaps along the back
    put(img, 3, base + 5, zap)
    put(img, 7, base + 5, zap)
    put(img, 10, base + 5, zap)
    put(img, 13, base + 5, zap)
    # Eye
    put(img, 13, base + 7, 0)
    put(img, 12, base + 7, eye)
    put(img, 14, base + 8, 0)


def generate_sprites() -> None:
    img = make_indexed(CELL, CELL * N_CELLS)
    draw_boat(img, 0)
    draw_hook(img, 1)
    # Slot 0/1 small fish (ch2/3, palette indices 5/6/7)
    draw_fish(img, 2, body=5, detail=6, eye=7,  x1=2, y1=6, x2=12, y2=9)
    draw_fish(img, 3, body=5, detail=6, eye=7,  x1=2, y1=6, x2=12, y2=9)
    # Slot 2/3 medium + large fish (ch4/5, palette 9/10/11) — same colours,
    # different silhouette so the player can tell them apart.
    draw_fish(img, 4, body=9, detail=10, eye=11, x1=1, y1=5, x2=14, y2=10)
    draw_fish(img, 5, body=9, detail=10, eye=11, x1=0, y1=4, x2=15, y2=11)
    # Slot 4/5 rare + eel (ch6/7, palette 13/14/15)
    draw_fish(img, 6, body=13, detail=14, eye=15, x1=2, y1=5, x2=13, y2=10)
    draw_eel(img,  7, body=13, zap=14, eye=15)
    img.save(OUT / "sprites.png")
    print(f"Wrote {OUT / 'sprites.png'}")


# ---------------------------------------------------------------------------
# Logo — "AMIFISH" in a chunky 7×7 pixel font, 60×16. Drawn on the playfield
# (not a sprite), so it just needs to look right under the screen palette.
# Uses palette index 4 (yellow on the sprite-PNG palette but we'll re-set
# screen palette in amifish.py so this index is irrelevant on Amiga).
#
# To keep visual consistency in pygame preview AND after amifish.py resets
# its screen palette, the logo uses indices that map to "yellow with cyan
# shadow" in BOTH palettes. Since the sprite PNG palette and the screen
# palette won't share index meanings post-reset, we pick a pair that is
# easy to express either way: index 1 (yellow → also dark-blue sky in
# screen palette) for the foreground? No — that won't work in screen pal.
#
# Simplest: write the logo with screen-palette indices that mean what we
# want under the screen palette (yellow = 4, blue = 3 — see amifish.py
# palette setup). That means in pygame preview's *initial* PNG palette the
# colours look "different" — but the logo only displays after amifish.py
# has reset the screen palette, at which point values render correctly.
# ---------------------------------------------------------------------------

LOGO_GLYPHS = {
    "A": [
        "  ###  ",
        " #   # ",
        "#     #",
        "#######",
        "#     #",
        "#     #",
        "#     #",
    ],
    "M": [
        "#     #",
        "##   ##",
        "# # # #",
        "#  #  #",
        "#     #",
        "#     #",
        "#     #",
    ],
    "I": [
        "#######",
        "   #   ",
        "   #   ",
        "   #   ",
        "   #   ",
        "   #   ",
        "#######",
    ],
    "F": [
        "#######",
        "#      ",
        "#      ",
        "#####  ",
        "#      ",
        "#      ",
        "#      ",
    ],
    "S": [
        " ##### ",
        "#     #",
        "#      ",
        " ##### ",
        "      #",
        "#     #",
        " ##### ",
    ],
    "H": [
        "#     #",
        "#     #",
        "#     #",
        "#######",
        "#     #",
        "#     #",
        "#     #",
    ],
}


def draw_glyph(img: Image.Image, ox: int, oy: int, ch: str,
               fg: int, shadow: int) -> None:
    rows = LOGO_GLYPHS[ch]
    for ry, row in enumerate(rows):
        for rx, c in enumerate(row):
            if c == "#":
                put(img, ox + rx + 1, oy + ry + 1, shadow)
    for ry, row in enumerate(rows):
        for rx, c in enumerate(row):
            if c == "#":
                put(img, ox + rx, oy + ry, fg)


def generate_logo() -> None:
    """Logo is a Shape blitted onto the playfield — its pixel values index
    into the SCREEN palette (regs 0..15) at blit time, not into the PNG's
    own palette. We use index 4 (yellow on the screen palette set by
    amifish.py) for the foreground and index 5 (brown) for the drop shadow
    so it reads correctly on the deep-blue title-screen sky.

    The PNG's own palette doesn't match those colours initially — pygame
    preview will look "wrong" at load time — but `Shape.load` registers
    the surface with the backend, so when amifish.py later calls
    palette.set(4, ...) / palette.set(5, ...) the surface's palette
    syncs to the right colours for both rendering paths."""
    text = "AMIFISH"
    w = len(text) * 8 + 4
    h = 16
    img = make_indexed(w, h)
    for i, ch in enumerate(text):
        draw_glyph(img, ox=2 + i * 8, oy=4, ch=ch, fg=4, shadow=5)
    img.save(OUT / "logo.png")
    print(f"Wrote {OUT / 'logo.png'}")


if __name__ == "__main__":
    generate_sprites()
    generate_logo()
    print("Done.")
