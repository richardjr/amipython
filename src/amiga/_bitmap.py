"""Bitmap class — offscreen drawing surface with indexed colours."""

from __future__ import annotations

from amiga._backend import Backend, _require_pygame

try:
    import pygame
except ImportError:
    pygame = None


class Bitmap:
    """An offscreen drawing surface using indexed colour palette.

    Maps to AmipyBitmap in the C runtime. All drawing uses colour indices
    (not RGB values), matching Amiga hardware behaviour.
    """

    def __init__(self, width: int, height: int, *, bitplanes: int = 5) -> None:
        _require_pygame()
        self.width = width
        self.height = height
        self.bitplanes = bitplanes
        self._max_colors = 1 << bitplanes
        self._surface = pygame.Surface((width, height), depth=8)
        self._surface.fill(0)
        Backend.get().register_surface(self._surface)

    def circle_filled(self, cx: int, cy: int, r: int, color: int) -> None:
        """Draw a filled circle at (cx, cy) with radius r using colour index."""
        if r <= 0:
            self.plot(cx, cy, color)
            return
        pygame.draw.circle(self._surface, color, (cx, cy), r)

    def plot(self, x: int, y: int, color: int) -> None:
        """Set a single pixel to a colour index."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._surface.set_at((x, y), color)

    def clear(self) -> None:
        """Fill the entire surface with colour index 0."""
        self._surface.fill(0)
