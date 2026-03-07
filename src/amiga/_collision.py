"""Collision module — sprite/playfield collision detection for preview."""

from __future__ import annotations

from amiga._backend import Backend

try:
    import pygame
except ImportError:
    pygame = None


class _CollisionModule:
    """Collision detection singleton. Checks sprite overlap with playfield colors."""

    def __init__(self):
        self._registrations: list[tuple[int, int]] = []  # (color, mask)

    def register(self, *, color: int, mask: int) -> None:
        """Register a playfield color index for collision detection."""
        self._registrations.append((color, mask))

    def check(self) -> None:
        """Check all active sprites against registered playfield colors.

        Sets the collided flag on any sprite whose pixels overlap with
        registered colors on the active bitmap surface.
        """
        backend = Backend.get()
        sprites = getattr(backend, '_sprites', {})
        active = backend._active_surface

        if not sprites or active is None or not self._registrations:
            for sprite in sprites.values():
                sprite._collided_flag = False
            return

        # Build set of collision colors
        coll_colors = {color for color, mask in self._registrations}

        # Read raw palette indices via PixelArray (no numpy dependency)
        pa = pygame.PixelArray(active)
        w, h = active.get_width(), active.get_height()

        for sprite in sprites.values():
            sprite._collided_flag = False
            if not sprite._visible:
                continue
            sx, sy = sprite._x, sprite._y
            hit = False
            for py in range(sprite.height):
                if hit:
                    break
                for px in range(sprite.width):
                    bx = sx + px
                    by = sy + py
                    if 0 <= bx < w and 0 <= by < h:
                        if int(pa[bx][by]) in coll_colors:
                            sprite._collided_flag = True
                            hit = True
                            break
        del pa


collision = _CollisionModule()
