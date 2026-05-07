"""Sprite class — hardware sprite emulation for the preview module."""

from __future__ import annotations

from amiga._backend import Backend, _require_pygame

try:
    import pygame
except ImportError:
    pygame = None


class Sprite:
    """A hardware sprite (emulated in software for preview).

    Maps to AmipySprite in the C runtime. Created via Sprite.grab().
    """

    def __init__(self, surface: pygame.Surface) -> None:
        self._surface = surface
        # Amiga hardware sprites treat colour 0 of their (4-colour) palette
        # as transparent — match that in preview so the sprite cell's
        # background pixels don't render as opaque black.
        if surface.get_bitsize() == 8:
            surface.set_colorkey(0)
        self.width = surface.get_width()
        self.height = surface.get_height()
        self._x = 0
        self._y = 0
        self._channel = 0
        self._visible = False
        self._collided_flag = False

    @staticmethod
    def grab(bm, x: int, y: int, w: int, h: int) -> Sprite:
        """Grab a rectangular region from a bitmap as a sprite."""
        _require_pygame()
        region = bm._surface.subsurface(pygame.Rect(x, y, w, h)).copy()
        return Sprite(region)

    def show(self, x: int, y: int, *, channel: int = 0) -> None:
        """Position the sprite at (x, y) on the given hardware channel."""
        self._x = x
        self._y = y
        self._channel = channel
        self._visible = True
        backend = Backend.get()
        if not hasattr(backend, '_sprites'):
            backend._sprites = {}
        backend._sprites[id(self)] = self

    def collided(self) -> bool:
        """Return True if collision was detected on last check()."""
        return self._collided_flag

    def overlaps(self, other: Sprite) -> bool:
        """AABB overlap test against another sprite based on last show() positions.

        Touching edges count as separate (half-open intervals).
        """
        ax2 = self._x + self.width
        ay2 = self._y + self.height
        bx2 = other._x + other.width
        by2 = other._y + other.height
        if ax2 <= other._x or bx2 <= self._x:
            return False
        if ay2 <= other._y or by2 <= self._y:
            return False
        return True
