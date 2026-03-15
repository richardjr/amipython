"""Joy module — joystick/mouse button and direction input."""

from __future__ import annotations

try:
    import pygame
except ImportError:
    pygame = None

from amiga._backend import Backend


class _JoyModule:
    """Joystick input singleton. Port 0 = mouse, port 1 = joystick."""

    def button(self, port: int = 0) -> bool:
        """Check if the fire button is pressed on the given port.

        Port 0 checks the left mouse button or Space key.
        Port 1 checks joystick button 1.
        """
        if pygame is None:
            return False
        backend = Backend.get()
        backend.pump_events()
        keys = pygame.key.get_pressed()
        if port == 0:
            return pygame.mouse.get_pressed()[0] or keys[pygame.K_SPACE]
        else:
            # Joystick fire: Space or LAlt (matches Amiberry WSAD layout)
            return keys[pygame.K_SPACE] or keys[pygame.K_LALT]

    def left(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        keys = pygame.key.get_pressed()
        return keys[pygame.K_LEFT] or keys[pygame.K_a]

    def right(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        keys = pygame.key.get_pressed()
        return keys[pygame.K_RIGHT] or keys[pygame.K_d]

    def up(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        keys = pygame.key.get_pressed()
        return keys[pygame.K_UP] or keys[pygame.K_w]

    def down(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        keys = pygame.key.get_pressed()
        return keys[pygame.K_DOWN] or keys[pygame.K_s]


joy = _JoyModule()
