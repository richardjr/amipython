"""Shape class — grabbed region of a bitmap for blitting."""

from __future__ import annotations

from amiga._backend import _require_pygame

try:
    import pygame
except ImportError:
    pygame = None


class Shape:
    """A rectangular region grabbed from a bitmap for blitting.

    Maps to AmipyShape in the C runtime. Created via Shape.grab().
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
