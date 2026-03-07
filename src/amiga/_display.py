"""Display class — creates and manages the preview window."""

from __future__ import annotations

from amiga._backend import Backend
from amiga._bitmap import Bitmap


class Display:
    """A display screen. Creates the preview window on show().

    Maps to AmipyDisplay in the C runtime. The window is created lazily
    when show() is first called, matching the Amiga behaviour where
    display_init allocates structs but the view is loaded later.
    """

    def __init__(self, width: int, height: int, *, bitplanes: int = 5) -> None:
        self.width = width
        self.height = height
        self.bitplanes = bitplanes
        self._bm = None  # Current bitmap being displayed

    def show(self, bm: Bitmap) -> None:
        """Display a bitmap in the preview window."""
        self._bm = bm
        backend = Backend.get()
        backend.ensure_init(self.width, self.height)
        backend.present(bm._surface)

    def blit(self, shape, x: int, y: int) -> None:
        """Blit a shape onto the current display bitmap at (x, y)."""
        if self._bm is not None:
            self._bm._surface.blit(shape._surface, (int(x), int(y)))
            Backend.get().present(self._bm._surface)
