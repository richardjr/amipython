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
from amiga._builtins import wait_mouse, vwait, rnd, run, sin_table, cos_table

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
    "wait_mouse",
    "vwait",
    "rnd",
    "run",
    "sin_table",
    "cos_table",
]
