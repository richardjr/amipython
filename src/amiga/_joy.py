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

        Port 0 checks the left mouse button.
        Port 1 checks joystick button 1.
        """
        if pygame is None:
            return False
        backend = Backend.get()
        backend.pump_events()
        if port == 0:
            return pygame.mouse.get_pressed()[0]
        else:
            if pygame.joystick.get_count() > 0:
                joy = pygame.joystick.Joystick(0)
                return joy.get_button(0)
        return False

    def left(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        return pygame.key.get_pressed()[pygame.K_LEFT]

    def right(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        return pygame.key.get_pressed()[pygame.K_RIGHT]

    def up(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        return pygame.key.get_pressed()[pygame.K_UP]

    def down(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        return pygame.key.get_pressed()[pygame.K_DOWN]


joy = _JoyModule()
