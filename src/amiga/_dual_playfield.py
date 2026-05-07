"""DualPlayfield — preview-side OCS dual-playfield emulation.

Mirrors the C runtime's hand-rolled DPF manager (see
``amipython_engine_amiga.c::amipython_dual_playfield_init``). Two source
bitmaps are composited each frame: the background plays the role of OCS
playfield B, the foreground sits on top with its colour 0 transparent —
matching the hardware's BPLCON0-DPF-bit + colour-0-transparent semantics.

This replaces ``Display`` / ``Bitmap`` for the duration of the program. Once
``DualPlayfield(fg, bg)`` is constructed, the user scrolls both layers
independently with ``scroll_fg`` / ``scroll_bg``; ``.show()`` makes it the
backend's active surface.
"""

from __future__ import annotations

from amiga._backend import Backend, _require_pygame

try:
    import pygame
except ImportError:
    pygame = None


# Standard PAL lores DPF window — bitmaps may be larger; only a
# WINDOW_W × WINDOW_H region is visible at any time, with scroll_fg /
# scroll_bg choosing which part of each bitmap shows through.
WINDOW_W = 320
WINDOW_H = 200

# Translation table mapping BG bitmap pixel values 1..7 to palette regs
# 9..15 — the +8 offset OCS DPF mode applies in hardware (PFB indexes
# palette regs 8..15 instead of 0..7). Built once at import time.
_BG_INDEX_REMAP = bytes([0] + [i + 8 for i in range(1, 8)] + list(range(8, 256)))


class DualPlayfield:
    """Preview-side dual playfield: two bitmaps composited each frame."""

    def __init__(self, fg, bg) -> None:
        _require_pygame()
        self._fg = fg
        self._bg = bg
        # Visible window — independent of source bitmap dimensions.
        self.width = WINDOW_W
        self.height = WINDOW_H
        self._scroll_fg = (0, 0)
        self._scroll_bg = (0, 0)
        # The composited surface that gets presented. Created at show() time
        # so it inherits the active palette.
        self._composite: pygame.Surface | None = None

    def show(self) -> None:
        backend = Backend.get()
        backend.ensure_init(self.width, self.height)
        self._composite = pygame.Surface((self.width, self.height), depth=8)
        backend.register_surface(self._composite)
        backend._active_surface = self._composite
        self._refresh()

    def scroll_fg(self, x: int, y: int) -> None:
        self._scroll_fg = (int(x), int(y))
        self._refresh()

    def scroll_bg(self, x: int, y: int) -> None:
        self._scroll_bg = (int(x), int(y))
        self._refresh()

    def _refresh(self) -> None:
        """Re-render the composite surface from the two layers.

        BG paints first (always opaque — OCS DPF has no PFB transparency,
        BG colour 0 just shows palette reg 8). FG layers over with colour 0
        transparent. BG indices are shifted +8 so the user can write the
        natural 0..7 range into the BG bitmap and have palette regs 8..15
        light up — same as the hardware does."""
        if self._composite is None:
            return
        self._composite.fill(0)
        bg_x, bg_y = self._scroll_bg
        fg_x, fg_y = self._scroll_fg
        bg_shifted = self._bg_remapped(self._bg._surface)
        self._tiled_blit(bg_shifted, bg_x, bg_y, transparent=False)
        fg_keyed = self._fg._surface.copy()
        fg_keyed.set_colorkey(0)
        self._tiled_blit(fg_keyed, fg_x, fg_y, transparent=True)
        Backend.get().present(self._composite)

    def _bg_remapped(self, src: pygame.Surface) -> pygame.Surface:
        """Surface copy with BG pixel indices 1..7 remapped to 9..15 so
        composite blits hit the BG palette regs 8..15."""
        out = src.copy()
        with pygame.PixelArray(out) as px:
            for v in range(1, 8):
                px.replace(v, v + 8)
        out.set_palette(Backend.get()._palette)
        return out

    def _tiled_blit(self, src: pygame.Surface, scroll_x: int, scroll_y: int,
                    *, transparent: bool) -> None:
        """Blit `src` onto the composite, wrapping at its edges so that a
        wider/taller source can scroll continuously. The composite is the
        visible window, smaller than (or equal to) the source bitmap."""
        sw, sh = src.get_width(), src.get_height()
        # Reduce scroll into [0, sw) / [0, sh) to keep math simple.
        ox = scroll_x % sw if sw else 0
        oy = scroll_y % sh if sh else 0
        # Always blit at least once at the offset; wrap copies cover the
        # gaps when the visible window crosses the source's right/bottom
        # edges. With composite < source there can be at most 4 sub-blits.
        self._composite.blit(src, (-ox, -oy))
        if ox > 0:
            self._composite.blit(src, (sw - ox, -oy))
        if oy > 0:
            self._composite.blit(src, (-ox, sh - oy))
        if ox > 0 and oy > 0:
            self._composite.blit(src, (sw - ox, sh - oy))
