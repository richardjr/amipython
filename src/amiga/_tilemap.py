"""Tilemap — tile-based scrolling display for the Python preview."""

from __future__ import annotations

import inspect
from pathlib import Path

try:
    import pygame
except ImportError:
    pygame = None

from amiga._backend import Backend


class Tilemap:
    """Tile-based scrolling map with hardware-style scrolling.

    The tileset PNG should be a vertical strip — one tile per row.
    """

    def __init__(self, tileset_path: str, width: int, height: int, *,
                 bitplanes: int = 3, tile_size: int = 16,
                 map_w: int = 20, map_h: int = 20):
        self.width = width
        self.height = height
        self.bitplanes = bitplanes
        self.tile_size = tile_size
        self.map_w = map_w
        self.map_h = map_h
        self._cam_x = 0
        self._cam_y = 0
        # Column-major tile data (matching ACE's pTileData[x][y])
        self._tile_data = [[0] * map_h for _ in range(map_w)]
        self._tiles: list = []
        self._surface = None

        # Load tileset
        caller_dir = Path(inspect.stack()[1].filename).parent
        self._load_tileset(str(caller_dir / tileset_path))

    def _load_tileset(self, full_path: str):
        if pygame is None:
            return
        image = pygame.image.load(full_path)
        ts = self.tile_size
        n_tiles = image.get_height() // ts
        self._tiles = []
        for i in range(n_tiles):
            tile_surf = pygame.Surface((ts, ts), depth=8)
            tile_surf.set_palette(image.get_palette())
            tile_surf.blit(image, (0, 0), (0, i * ts, ts, ts))
            self._tiles.append(tile_surf)

    def set_tile(self, x: int, y: int, tile: int) -> None:
        if 0 <= x < self.map_w and 0 <= y < self.map_h:
            self._tile_data[x][y] = tile

    def show(self) -> None:
        backend = Backend.get()
        backend.ensure_init(self.width, self.height)
        if pygame is not None:
            self._surface = pygame.Surface((self.width, self.height), depth=8)
            backend.register_surface(self._surface)
        backend._active_tilemap = self
        self._redraw()
        if self._surface is not None:
            backend._active_surface = self._surface
            backend.present(self._surface)

    def camera(self, x: int, y: int) -> None:
        max_x = self.map_w * self.tile_size - self.width
        max_y = self.map_h * self.tile_size - self.height
        self._cam_x = max(0, min(x, max_x))
        self._cam_y = max(0, min(y, max_y))

    def scroll(self, dx: int, dy: int) -> None:
        self.camera(self._cam_x + dx, self._cam_y + dy)

    def _redraw(self):
        if self._surface is None or pygame is None:
            return
        ts = self.tile_size
        self._surface.fill(0)
        start_tx = self._cam_x // ts
        start_ty = self._cam_y // ts
        off_x = self._cam_x % ts
        off_y = self._cam_y % ts
        tiles_x = self.width // ts + 2
        tiles_y = self.height // ts + 2
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                mx = start_tx + tx
                my = start_ty + ty
                if 0 <= mx < self.map_w and 0 <= my < self.map_h:
                    tile_idx = self._tile_data[mx][my]
                    if 0 <= tile_idx < len(self._tiles):
                        dest_x = tx * ts - off_x
                        dest_y = ty * ts - off_y
                        self._surface.blit(self._tiles[tile_idx], (dest_x, dest_y))
