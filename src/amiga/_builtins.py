"""Engine builtin functions — wait_mouse, vwait, rnd, run, sin_table, cos_table."""

from __future__ import annotations

import math
import random

try:
    import pygame
except ImportError:
    pygame = None

from amiga._backend import Backend


def wait_mouse() -> None:
    """Block until left mouse button is clicked, keeping the window responsive."""
    backend = Backend.get()
    while backend._running:
        events = backend.pump_events()
        if not backend._running:
            break
        if pygame is not None:
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    return
        backend.wait_vblank()


def vwait(n: int = 1) -> None:
    """Wait for n vertical blank intervals (1/50th second each)."""
    backend = Backend.get()
    for _ in range(n):
        if not backend._running:
            break
        backend.pump_events()
        backend.wait_vblank()


def rnd(n: int) -> int:
    """Return a random integer from 0 to n-1."""
    if n <= 0:
        return 0
    return random.randint(0, n - 1)


def run(update_fn, *, until=None) -> None:
    """Game loop — calls update_fn each frame until the until condition is True.

    until should be a callable that returns True to stop the loop.
    """
    backend = Backend.get()
    while backend._running:
        backend.pump_events()
        if not backend._running:
            break
        if until is not None and until():
            break
        # Update mouse-attached sprite position
        mouse_sprite = getattr(backend, '_mouse_sprite', None)
        if mouse_sprite is not None and pygame is not None and backend._initialized:
            mx, my = pygame.mouse.get_pos()
            mouse_sprite._x = mx // backend._scale
            mouse_sprite._y = my // backend._scale
        update_fn()
        if backend._active_surface is not None:
            # Render sprites as overlay before presenting
            sprites = getattr(backend, '_sprites', {})
            if sprites:
                overlay = backend._active_surface.copy()
                for sprite in sprites.values():
                    if sprite._visible:
                        overlay.blit(sprite._surface, (sprite._x, sprite._y))
                backend.present(overlay)
            else:
                backend.present(backend._active_surface)
        backend.wait_vblank()


def sin_table(n: int, scale: int = 0) -> list:
    """Return a list of n pre-computed sin values spanning 0 to 2*pi.

    If scale is given, returns list[int] with values pre-multiplied by scale.
    Otherwise returns list[float].
    """
    if scale:
        return [int(math.sin(2.0 * math.pi * i / n) * scale) for i in range(n)]
    return [math.sin(2.0 * math.pi * i / n) for i in range(n)]


def cos_table(n: int, scale: int = 0) -> list:
    """Return a list of n pre-computed cos values spanning 0 to 2*pi.

    If scale is given, returns list[int] with values pre-multiplied by scale.
    Otherwise returns list[float].
    """
    if scale:
        return [int(math.cos(2.0 * math.pi * i / n) * scale) for i in range(n)]
    return [math.cos(2.0 * math.pi * i / n) for i in range(n)]
