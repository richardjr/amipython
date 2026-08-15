"""Game logic — no drawing, so it could be unit-tested in plain Python."""
from amiga import rnd
from state import G, Game, grid, GRID_W, GRID_H, COLOURS


def scramble():
    for i in range(GRID_W * GRID_H):
        grid[i] = rnd(COLOURS)
    G.turn += 1


def move_cursor(g: Game, dx: int, dy: int) -> bool:
    """Structs are passed by reference — g IS the caller's Game."""
    nx: int = g.cursor_x + dx
    ny: int = g.cursor_y + dy
    if nx < 0 or nx >= GRID_W or ny < 0 or ny >= GRID_H:
        return False
    g.cursor_x = nx
    g.cursor_y = ny
    g.steps += 1
    return True


def cell_under_cursor() -> int:
    return grid[G.cursor_y * GRID_W + G.cursor_x]
