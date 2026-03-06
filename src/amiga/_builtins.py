"""Engine builtin functions — wait_mouse, vwait."""

from __future__ import annotations

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
