"""Palette module — emulates Amiga OCS 12-bit indexed colour palette."""

from __future__ import annotations

from amiga._backend import Backend
from amiga._constants import MAX_PALETTE


class _PaletteModule:
    """Singleton emulating the Amiga colour palette hardware."""

    def __init__(self) -> None:
        # Target palette stores unscaled 8-bit RGB tuples per register
        self._target_colors: dict[int, tuple[int, int, int]] = {}
        self._fade_level: int = 15  # 0=black, 15=full brightness

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
        self._target_colors[reg] = (r4 * 17, g4 * 17, b4 * 17)
        self._apply(reg)

    def set(self, reg: int, r: int, g: int, b: int) -> None:
        """Set colour register with OCS 4-bit values (0-15)."""
        if reg < 0 or reg >= MAX_PALETTE:
            return
        self._target_colors[reg] = ((r & 0xF) * 17, (g & 0xF) * 17, (b & 0xF) * 17)
        self._apply(reg)

    def fade(self, level: int) -> None:
        """Fade all palette entries. level 0=black, 15=full brightness."""
        if level < 0:
            level = 0
        if level > 15:
            level = 15
        self._fade_level = level
        for reg in self._target_colors:
            self._apply(reg)

    def _apply(self, reg: int) -> None:
        """Apply a single register with current fade level."""
        r8, g8, b8 = self._target_colors[reg]
        level = self._fade_level
        r_faded = (r8 * level) // 15
        g_faded = (g8 * level) // 15
        b_faded = (b8 * level) // 15
        self._set_rgb(reg, r_faded, g_faded, b_faded)

    def _set_rgb(self, reg: int, r8: int, g8: int, b8: int) -> None:
        backend = Backend.get()
        backend._palette[reg] = (r8, g8, b8)
        backend.sync_palette()


palette = _PaletteModule()
