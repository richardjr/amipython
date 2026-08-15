"""Multi-module example — sibling `from <mod> import ...` spliced into one unit.

    python examples/basic/multi_module/main.py         # preview
    amipython run --out build examples/basic/multi_module/main.py

Arrow keys / joystick move the cursor over a scrambled grid, fire re-scrambles.
Exercises: sibling modules, `[v] * N` sized lists, `list[str]` name tables,
struct-by-reference parameters, and a 320x256 display with blits on the
bottom rows.
"""
from amiga import Display, Bitmap, Shape, palette, joy, key, run, K_ESC
from state import G, grid, COLOUR_NAMES, GRID_W, GRID_H, CELL
from logic import scramble, move_cursor, cell_under_cursor

display = Display(320, 256, bitplanes=4)
bm = Bitmap(320, 256, bitplanes=4)

palette.set(0, 0, 0, 0)
palette.set(1, 5, 5, 6)      # steel
palette.set(2, 9, 4, 2)      # rust
palette.set(3, 3, 8, 3)      # moss
palette.set(4, 14, 10, 2)    # amber
palette.set(5, 15, 15, 15)   # cursor / text
palette.set(6, 2, 2, 3)      # void

# Cursor frame shape: draw, grab, clear
bm.box_filled(0, 0, CELL - 1, CELL - 1, 5)
bm.box_filled(2, 2, CELL - 3, CELL - 3, 0)
cursor = Shape.grab(bm, 0, 0, CELL, CELL)
bm.clear()

GRID_Y: int = 24     # grid occupies y 24..215, HUD sits below at 224..255


def cell_colour(v: int) -> int:
    if v == 0:
        return 6
    return v


def draw_cell(cx: int, cy: int):
    x: int = cx * CELL
    y: int = GRID_Y + cy * CELL
    bm.box_filled(x, y, x + CELL - 1, y + CELL - 1, cell_colour(grid[cy * GRID_W + cx]))


def draw_grid():
    for cy in range(GRID_H):
        for cx in range(GRID_W):
            draw_cell(cx, cy)


def draw_hud():
    bm.print_at(8, 8, "TURN", G.turn, "STEPS", G.steps, color=5)
    bm.print_at(8, 232, "CELL", COLOUR_NAMES[cell_under_cursor()], "     ", color=5)
    bm.print_at(160, 232, "FIRE=SCRAMBLE ESC=QUIT", color=5)


def draw_cursor():
    display.blit(cursor, G.cursor_x * CELL, GRID_Y + G.cursor_y * CELL)


scramble()
draw_grid()
draw_hud()
draw_cursor()
display.show(bm)


def update():
    moved: bool = False
    old_x: int = G.cursor_x
    old_y: int = G.cursor_y
    if joy.left_pressed():
        moved = move_cursor(G, -1, 0)
    elif joy.right_pressed():
        moved = move_cursor(G, 1, 0)
    elif joy.up_pressed():
        moved = move_cursor(G, 0, -1)
    elif joy.down_pressed():
        moved = move_cursor(G, 0, 1)
    if joy.button_pressed(0):
        scramble()
        draw_grid()
        moved = True
    if moved:
        draw_cell(old_x, old_y)
        draw_cursor()
        draw_hud()


run(update, until=lambda: key.pressed(K_ESC))
