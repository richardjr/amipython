"""Joy module — joystick/mouse button and direction input."""

from __future__ import annotations

try:
    import pygame
except ImportError:
    pygame = None

from amiga._backend import Backend


class _JoyModule:
    """Joystick input singleton. Port 0 = mouse, port 1 = joystick."""

    def __init__(self):
        self._prev_btn = [False, False]
        self._prev_left = False
        self._prev_right = False
        self._prev_up = False
        self._prev_down = False

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
            return bool(pygame.mouse.get_pressed()[0] or keys[pygame.K_SPACE])
        else:
            # Joystick fire: Space or LAlt (matches Amiberry WSAD layout)
            return bool(keys[pygame.K_SPACE] or keys[pygame.K_LALT])

    def button_pressed(self, port: int = 0) -> bool:
        """Edge-triggered button — True only on the frame of a 0→1 transition."""
        curr = self.button(port)
        idx = 0 if port == 0 else 1
        result = curr and not self._prev_btn[idx]
        self._prev_btn[idx] = curr
        return result

    def left(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        keys = pygame.key.get_pressed()
        return bool(keys[pygame.K_LEFT] or keys[pygame.K_a])

    def right(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        keys = pygame.key.get_pressed()
        return bool(keys[pygame.K_RIGHT] or keys[pygame.K_d])

    def up(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        keys = pygame.key.get_pressed()
        return bool(keys[pygame.K_UP] or keys[pygame.K_w])

    def down(self) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        keys = pygame.key.get_pressed()
        return bool(keys[pygame.K_DOWN] or keys[pygame.K_s])

    def left_pressed(self) -> bool:
        curr = self.left()
        r = curr and not self._prev_left
        self._prev_left = curr
        return r

    def right_pressed(self) -> bool:
        curr = self.right()
        r = curr and not self._prev_right
        self._prev_right = curr
        return r

    def up_pressed(self) -> bool:
        curr = self.up()
        r = curr and not self._prev_up
        self._prev_up = curr
        return r

    def down_pressed(self) -> bool:
        curr = self.down()
        r = curr and not self._prev_down
        self._prev_down = curr
        return r


joy = _JoyModule()
