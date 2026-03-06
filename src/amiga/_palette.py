"""Palette module — emulates Amiga OCS 12-bit indexed colour palette."""

from __future__ import annotations

from amiga._backend import Backend
from amiga._constants import MAX_PALETTE


class _PaletteModule:
    """Singleton emulating the Amiga colour palette hardware."""

    def aga(self, reg: int, r: int, g: int, b: int) -> None:
        """Set colour register with 8-bit RGB values, downscaled to OCS 12-bit.

        Matches amipython_palette_aga() in the C runtime: each channel is
        shifted right 4 bits (8-bit → 4-bit), then expanded back to 8-bit
        for display (multiply by 17).
        """
        if reg < 0 or reg >= MAX_PALETTE:
            return
        r4 = (r >> 4) & 0xF
        g4 = (g >> 4) & 0xF
        b4 = (b >> 4) & 0xF
        self._set_rgb(reg, r4 * 17, g4 * 17, b4 * 17)

    def set(self, reg: int, r: int, g: int, b: int) -> None:
        """Set colour register with OCS 4-bit values (0-15)."""
        if reg < 0 or reg >= MAX_PALETTE:
            return
        self._set_rgb(reg, (r & 0xF) * 17, (g & 0xF) * 17, (b & 0xF) * 17)

    def _set_rgb(self, reg: int, r8: int, g8: int, b8: int) -> None:
        backend = Backend.get()
        backend._palette[reg] = (r8, g8, b8)
        backend.sync_palette()


palette = _PaletteModule()
