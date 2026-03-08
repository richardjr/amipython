"""Shape class — grabbed region of a bitmap for blitting."""

from __future__ import annotations

import inspect
from pathlib import Path

from amiga._backend import Backend, _require_pygame

try:
    import pygame
except ImportError:
    pygame = None


class Shape:
    """A rectangular region grabbed from a bitmap for blitting.

    Maps to AmipyShape in the C runtime. Created via Shape.grab() or Shape.load().
    """

    def __init__(self, surface: pygame.Surface) -> None:
        self._surface = surface
        self.width = surface.get_width()
        self.height = surface.get_height()

    @staticmethod
    def grab(bm, x: int, y: int, w: int, h: int) -> Shape:
        """Grab a rectangular region from a bitmap.

        Creates a copy of the pixels in the specified region.
        """
        _require_pygame()
        region = bm._surface.subsurface(pygame.Rect(x, y, w, h)).copy()
        return Shape(region)

    @staticmethod
    def load(path: str) -> Shape:
        """Load a shape from a PNG or IFF image file.

        Color index 0 is treated as transparent for blitting.
        Path is resolved relative to the calling script's directory.
        """
        _require_pygame()
        caller_dir = Path(inspect.stack()[1].filename).parent
        full_path = caller_dir / path
        image = pygame.image.load(str(full_path))
        # Convert to 8-bit indexed surface matching our palette
        surface = image.convert(8)
        Backend.get().register_surface(surface)
        return Shape(surface)
