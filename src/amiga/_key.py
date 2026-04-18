"""Key module — keyboard input for the preview.

Maps Amiga raw-key codes (K_LEFT, K_A, ...) to pygame key constants for
input queries. Tracks previous-frame state so `just_pressed` and
`just_released` can be edge-triggered.
"""

from __future__ import annotations

try:
    import pygame
except ImportError:
    pygame = None

from amiga._backend import Backend


# Amiga raw-key codes as used by ACE — matches `KEY_CONSTANTS` in engine.py.
K_A = 0x20; K_B = 0x35; K_C = 0x33; K_D = 0x22; K_E = 0x12
K_F = 0x23; K_G = 0x24; K_H = 0x25; K_I = 0x17; K_J = 0x26
K_K = 0x27; K_L = 0x28; K_M = 0x37; K_N = 0x36; K_O = 0x18
K_P = 0x19; K_Q = 0x10; K_R = 0x13; K_S = 0x21; K_T = 0x14
K_U = 0x16; K_V = 0x34; K_W = 0x11; K_X = 0x32; K_Y = 0x15
K_Z = 0x31
K_1 = 0x01; K_2 = 0x02; K_3 = 0x03; K_4 = 0x04; K_5 = 0x05
K_6 = 0x06; K_7 = 0x07; K_8 = 0x08; K_9 = 0x09; K_0 = 0x0A
K_LEFT = 0x4F; K_RIGHT = 0x4E; K_UP = 0x4C; K_DOWN = 0x4D
K_SPACE = 0x40; K_RETURN = 0x44; K_ESC = 0x45


def _amiga_to_pygame_map():
    if pygame is None:
        return {}
    return {
        K_A: pygame.K_a, K_B: pygame.K_b, K_C: pygame.K_c, K_D: pygame.K_d,
        K_E: pygame.K_e, K_F: pygame.K_f, K_G: pygame.K_g, K_H: pygame.K_h,
        K_I: pygame.K_i, K_J: pygame.K_j, K_K: pygame.K_k, K_L: pygame.K_l,
        K_M: pygame.K_m, K_N: pygame.K_n, K_O: pygame.K_o, K_P: pygame.K_p,
        K_Q: pygame.K_q, K_R: pygame.K_r, K_S: pygame.K_s, K_T: pygame.K_t,
        K_U: pygame.K_u, K_V: pygame.K_v, K_W: pygame.K_w, K_X: pygame.K_x,
        K_Y: pygame.K_y, K_Z: pygame.K_z,
        K_0: pygame.K_0, K_1: pygame.K_1, K_2: pygame.K_2, K_3: pygame.K_3,
        K_4: pygame.K_4, K_5: pygame.K_5, K_6: pygame.K_6, K_7: pygame.K_7,
        K_8: pygame.K_8, K_9: pygame.K_9,
        K_LEFT: pygame.K_LEFT, K_RIGHT: pygame.K_RIGHT,
        K_UP: pygame.K_UP, K_DOWN: pygame.K_DOWN,
        K_SPACE: pygame.K_SPACE, K_RETURN: pygame.K_RETURN, K_ESC: pygame.K_ESCAPE,
    }


class _KeyModule:
    """Keyboard input singleton — held state + edge detection."""

    def __init__(self):
        self._prev: dict[int, bool] = {}
        self._map_cache = None

    def _held(self, code: int) -> bool:
        if pygame is None:
            return False
        Backend.get().pump_events()
        if self._map_cache is None:
            self._map_cache = _amiga_to_pygame_map()
        pg = self._map_cache.get(code)
        if pg is None:
            return False
        keys = pygame.key.get_pressed()
        return bool(keys[pg])

    def pressed(self, code: int) -> bool:
        """True while the key is held."""
        return self._held(code)

    def just_pressed(self, code: int) -> bool:
        """True only on the frame the key transitions up → down."""
        curr = self._held(code)
        prev = self._prev.get(code, False)
        self._prev[code] = curr
        return curr and not prev

    def just_released(self, code: int) -> bool:
        """True only on the frame the key transitions down → up."""
        curr = self._held(code)
        prev = self._prev.get(code, False)
        self._prev[code] = curr
        return prev and not curr


key = _KeyModule()
