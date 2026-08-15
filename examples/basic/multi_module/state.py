"""Shared state module — imported by the other modules.

Shared *mutable scalars* live in the `G` dataclass instance so every module
(and both the Python preview and the transpiled C) see the same value.
Never `global`-rebind an imported name.
"""
from dataclasses import dataclass

GRID_W: int = 20
GRID_H: int = 12
CELL: int = 16
COLOURS: int = 5


@dataclass
class Game:
    turn: int = 0
    cursor_x: int = 3
    cursor_y: int = 3
    steps: int = 0


G = Game()

# Flat grid, sized with a list literal (capacity GRID_W * GRID_H = 240)
grid: list[int] = [0] * (GRID_W * GRID_H)

# String table indexed by colour id
COLOUR_NAMES: list[str] = [""] * COLOURS
COLOUR_NAMES[0] = "VOID"
COLOUR_NAMES[1] = "STEEL"
COLOUR_NAMES[2] = "RUST"
COLOUR_NAMES[3] = "MOSS"
COLOUR_NAMES[4] = "AMBER"
