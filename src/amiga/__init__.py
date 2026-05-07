"""amiga — Python-native preview module for amipython game scripts.

Provides Display, Bitmap, palette, and other engine objects so that
amipython scripts can run directly in Python with a visual preview window.

    from amiga import Display, Bitmap, palette, wait_mouse

    display = Display(320, 256, bitplanes=5)
    bm = Bitmap(320, 256, bitplanes=5)
    palette.aga(1, 255, 0, 0)
    bm.circle_filled(160, 128, 60, 1)
    display.show(bm)
    wait_mouse()
"""

from amiga._display import Display
from amiga._bitmap import Bitmap
from amiga._shape import Shape
from amiga._sprite import Sprite
from amiga._palette import palette
from amiga._joy import joy
from amiga._mouse import mouse
from amiga._collision import collision
from amiga._music import music
from amiga._sfx import sfx
from amiga._storage import storage
from amiga._tilemap import Tilemap
from amiga._dual_playfield import DualPlayfield
from amiga._key import (
    key,
    K_A, K_B, K_C, K_D, K_E, K_F, K_G, K_H, K_I, K_J, K_K, K_L, K_M,
    K_N, K_O, K_P, K_Q, K_R, K_S, K_T, K_U, K_V, K_W, K_X, K_Y, K_Z,
    K_0, K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9,
    K_LEFT, K_RIGHT, K_UP, K_DOWN, K_SPACE, K_RETURN, K_ESC,
)
from amiga._builtins import wait_mouse, vwait, rnd, run, sin_table, cos_table, int_to_str, shuffle
from amiga._copper import copper, Color

__all__ = [
    "Display",
    "Bitmap",
    "Shape",
    "Sprite",
    "palette",
    "joy",
    "mouse",
    "collision",
    "music",
    "sfx",
    "storage",
    "Tilemap",
    "DualPlayfield",
    "key",
    "K_A", "K_B", "K_C", "K_D", "K_E", "K_F", "K_G", "K_H", "K_I", "K_J",
    "K_K", "K_L", "K_M", "K_N", "K_O", "K_P", "K_Q", "K_R", "K_S", "K_T",
    "K_U", "K_V", "K_W", "K_X", "K_Y", "K_Z",
    "K_0", "K_1", "K_2", "K_3", "K_4", "K_5", "K_6", "K_7", "K_8", "K_9",
    "K_LEFT", "K_RIGHT", "K_UP", "K_DOWN",
    "K_SPACE", "K_RETURN", "K_ESC",
    "wait_mouse",
    "vwait",
    "rnd",
    "run",
    "sin_table",
    "cos_table",
    "int_to_str",
    "shuffle",
    "copper",
    "Color",
]
