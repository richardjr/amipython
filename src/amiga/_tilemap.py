"""Tilemap — tile-based scrolling display for the Python preview."""

from __future__ import annotations

import inspect
import json
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
        self._blocking_tiles: set[int] = set()
        self._pending_blits: list = []

        # Load tileset
        caller_dir = Path(inspect.stack()[1].filename).parent
        self._load_tileset(str(caller_dir / tileset_path))

    @classmethod
    def load_tiled(cls, json_path: str, width: int, height: int, *,
                   bitplanes: int = 3) -> Tilemap:
        """Load a tilemap from a Tiled JSON export.

        Reads map dimensions, tile data, tileset image, and custom tile
        properties (e.g. "blocking") from the Tiled JSON format.
        """
        caller_dir = Path(inspect.stack()[1].filename).parent
        full_path = caller_dir / json_path

        with open(full_path) as f:
            data = json.load(f)

        map_w = data["width"]
        map_h = data["height"]
        tile_size = data["tilewidth"]

        # Find first tileset
        ts_info = data["tilesets"][0]
        firstgid = ts_info["firstgid"]
        tileset_image = ts_info["image"]

        # Resolve tileset image relative to JSON file
        json_dir = full_path.parent
        tileset_full = str(json_dir / tileset_image)

        # Create instance without calling __init__
        tm = cls.__new__(cls)
        tm.width = width
        tm.height = height
        tm.bitplanes = bitplanes
        tm.tile_size = tile_size
        tm.map_w = map_w
        tm.map_h = map_h
        tm._cam_x = 0
        tm._cam_y = 0
        tm._tile_data = [[0] * map_h for _ in range(map_w)]
        tm._tiles = []
        tm._surface = None
        tm._blocking_tiles = set()
        tm._pending_blits = []

        # Load tileset image
        tm._load_tileset(tileset_full)

        # Extract blocking properties from tileset
        if "tiles" in ts_info:
            for tile_info in ts_info["tiles"]:
                tile_id = tile_info["id"]
                for prop in tile_info.get("properties", []):
                    if prop["name"] == "blocking" and prop.get("value", False):
                        tm._blocking_tiles.add(tile_id)

        # Load tile data from first tile layer (row-major, 1-indexed GIDs)
        for layer in data["layers"]:
            if layer["type"] == "tilelayer":
                layer_data = layer["data"]
                for i, gid in enumerate(layer_data):
                    if gid > 0:
                        tile_idx = gid - firstgid
                        x = i % map_w
                        y = i // map_w
                        tm._tile_data[x][y] = tile_idx
                break  # first tile layer only

        return tm

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

    def get_tile(self, x: int, y: int) -> int:
        """Return tile index at tile coordinates (x, y). Returns -1 if out of bounds."""
        if 0 <= x < self.map_w and 0 <= y < self.map_h:
            return self._tile_data[x][y]
        return -1

    def is_blocking(self, pixel_x: int, pixel_y: int) -> bool:
        """Check if the tile at pixel position is blocking.

        Out-of-bounds positions are treated as blocking.
        """
        tx = pixel_x // self.tile_size
        ty = pixel_y // self.tile_size
        if tx < 0 or tx >= self.map_w or ty < 0 or ty >= self.map_h:
            return True
        tile = self._tile_data[tx][ty]
        return tile in self._blocking_tiles

    def draw_shape(self, shape, world_x: int, world_y: int) -> None:
        """Queue a shape to be drawn at world coordinates.

        Shapes are rendered after tiles during _redraw(), then cleared.
        Color index 0 is treated as transparent.
        """
        self._pending_blits.append((shape, world_x, world_y))

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

        # Draw pending shapes (sprites/bullets) on top of tiles
        for shape, wx, wy in self._pending_blits:
            sx = wx - self._cam_x
            sy = wy - self._cam_y
            if hasattr(shape, '_surface') and shape._surface is not None:
                shape._surface.set_colorkey(0)
                self._surface.blit(shape._surface, (sx, sy))
        self._pending_blits.clear()
