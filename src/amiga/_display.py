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

    def show(self, bm: Bitmap) -> None:
        """Display a bitmap in the preview window."""
        backend = Backend.get()
        backend.ensure_init(self.width, self.height)
        backend.present(bm._surface)
