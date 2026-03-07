"""Mouse module — mouse position input."""

from __future__ import annotations

try:
    import pygame
except ImportError:
    pygame = None

from amiga._backend import Backend


class _MouseModule:
    """Mouse position singleton. Properties return current pointer coordinates."""

    @property
    def x(self) -> int:
        backend = Backend.get()
        if not backend._initialized or pygame is None:
            return 0
        backend.pump_events()
        mx, _ = pygame.mouse.get_pos()
        return mx // backend._scale

    @property
    def y(self) -> int:
        backend = Backend.get()
        if not backend._initialized or pygame is None:
            return 0
        backend.pump_events()
        _, my = pygame.mouse.get_pos()
        return my // backend._scale


mouse = _MouseModule()
