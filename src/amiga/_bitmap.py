"""Bitmap class — offscreen drawing surface with indexed colours."""

from __future__ import annotations

import inspect
from pathlib import Path

from amiga._backend import Backend, _require_pygame

try:
    import pygame
except ImportError:
    pygame = None


class Bitmap:
    """An offscreen drawing surface using indexed colour palette.

    Maps to AmipyBitmap in the C runtime. All drawing uses colour indices
    (not RGB values), matching Amiga hardware behaviour.
    """

    def __init__(self, width: int, height: int, *, bitplanes: int = 5) -> None:
        _require_pygame()
        self.width = width
        self.height = height
        self.bitplanes = bitplanes
        self._max_colors = 1 << bitplanes
        self._surface = pygame.Surface((width, height), depth=8)
        self._surface.fill(0)
        Backend.get().register_surface(self._surface)

    def circle_filled(self, cx: int, cy: int, r: int, color: int) -> None:
        """Draw a filled circle at (cx, cy) with radius r using colour index."""
        if r <= 0:
            self.plot(cx, cy, color)
            return
        pygame.draw.circle(self._surface, color, (cx, cy), r)

    def plot(self, x: int, y: int, color: int) -> None:
        """Set a single pixel to a colour index."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._surface.set_at((x, y), color)

    def line(self, x1: int, y1: int, x2: int, y2: int, color: int) -> None:
        """Draw a line from (x1,y1) to (x2,y2) using colour index."""
        pygame.draw.line(self._surface, color, (x1, y1), (x2, y2))

    def box_filled(self, x1: int, y1: int, x2: int, y2: int, color: int) -> None:
        """Draw a filled rectangle from (x1,y1) to (x2,y2) using colour index."""
        rect = pygame.Rect(x1, y1, x2 - x1 + 1, y2 - y1 + 1)
        self._surface.fill(color, rect)

    def clear(self) -> None:
        """Fill the entire surface with colour index 0."""
        self._surface.fill(0)

    def clear_rect(self, x: int, y: int, w: int, h: int) -> None:
        """Fill a rectangular region with colour index 0."""
        if w <= 0 or h <= 0:
            return
        rect = pygame.Rect(x, y, w, h).clip(self._surface.get_rect())
        if rect.w > 0 and rect.h > 0:
            self._surface.fill(0, rect)

    def copy_from(self, src: "Bitmap", x: int, y: int, w: int, h: int) -> None:
        """Copy a rectangular region from another bitmap into this bitmap at the
        same coordinates. Used to "erase to backdrop" — fill an area with what's
        on the source bitmap (typically a starfield or background image) so that
        sprites/UI drawn on top can be cleanly removed without scorching the
        backdrop. Mirrors `amipython_bitmap_copy_from` in the C runtime."""
        if w <= 0 or h <= 0:
            return
        rect = pygame.Rect(x, y, w, h).clip(self._surface.get_rect())
        rect = rect.clip(src._surface.get_rect())
        if rect.w > 0 and rect.h > 0:
            self._surface.blit(src._surface, (rect.x, rect.y),
                               area=(rect.x, rect.y, rect.w, rect.h))

    def _render_pieces(self, cx: int, y: int, pieces, color: int) -> None:
        """Internal: render a sequence of text pieces at the given cursor x."""
        for i, piece in enumerate(pieces):
            if isinstance(piece, bool):
                text = "True" if piece else "False"
            else:
                text = str(piece)
            for ch in text:
                glyph = _FONT_8X8.get(ch) or _FONT_8X8.get(' ')
                if glyph:
                    for row in range(8):
                        bits = glyph[row]
                        for col in range(8):
                            bx, by = cx + col, y + row
                            if 0 <= bx < self.width and 0 <= by < self.height:
                                if bits & (0x80 >> col):
                                    self._surface.set_at((bx, by), color)
                                else:
                                    self._surface.set_at((bx, by), 0)
                cx += 8
            if i + 1 < len(pieces):
                cx += 8

    def _pieces_width(self, pieces) -> int:
        total = 0
        for i, piece in enumerate(pieces):
            if isinstance(piece, bool):
                text = "True" if piece else "False"
            else:
                text = str(piece)
            total += len(text) * 8
            if i + 1 < len(pieces):
                total += 8
        return total

    def print_centered(self, y: int, *texts, color: int = 1) -> None:
        """Render one or more text pieces centered horizontally at row y."""
        if not texts:
            return
        x = (self.width - self._pieces_width(texts)) // 2
        self._render_pieces(x, y, texts, color)

    def print_right(self, x_right: int, y: int, *texts, color: int = 1) -> None:
        """Render text pieces right-aligned so the last glyph ends at x_right."""
        if not texts:
            return
        x = x_right - self._pieces_width(texts)
        self._render_pieces(x, y, texts, color)

    def print_at(self, x: int, y: int, *texts, color: int = 1) -> None:
        """Render one or more text pieces at (x, y) separated by single-glyph gaps.

        Accepts any number of positional text args (str/int/bool). Non-str args
        are converted via `str()` — matches transpiled `amipython_str_int` /
        `amipython_str_bool` behaviour.
        """
        if not texts:
            return
        cx = x
        for i, piece in enumerate(texts):
            if isinstance(piece, bool):
                text = "True" if piece else "False"
            elif isinstance(piece, (int, float)):
                text = str(piece)
            else:
                text = str(piece)
            for ch in text:
                glyph = _FONT_8X8.get(ch)
                if glyph is None:
                    glyph = _FONT_8X8.get(' ')
                if glyph:
                    for row in range(8):
                        bits = glyph[row]
                        for col in range(8):
                            bx, by = cx + col, y + row
                            if 0 <= bx < self.width and 0 <= by < self.height:
                                if bits & (0x80 >> col):
                                    self._surface.set_at((bx, by), color)
                                else:
                                    self._surface.set_at((bx, by), 0)
                cx += 8
            if i + 1 < len(texts):
                cx += 8  # one-glyph-wide separator

    @staticmethod
    def load(path: str) -> Bitmap:
        """Load a bitmap from a PNG or IFF file, including palette.

        Extracts the image palette and applies it via palette.set() calls.
        Path is resolved relative to the calling script's directory.
        """
        from amiga._palette import palette

        _require_pygame()
        caller_dir = Path(inspect.stack()[1].filename).parent
        full_path = caller_dir / path
        image = pygame.image.load(str(full_path))
        surface = image.convert(8)
        w, h = surface.get_size()
        # Determine bitplanes from palette
        pal = image.get_palette()
        if pal is not None:
            n_colors = len(pal)
        else:
            n_colors = 256
        depth = 1
        while (1 << depth) < n_colors:
            depth += 1
        if depth > 5:
            depth = 5
        bm = Bitmap.__new__(Bitmap)
        bm.width = w
        bm.height = h
        bm.bitplanes = depth
        bm._max_colors = 1 << depth
        bm._surface = surface
        Backend.get().register_surface(surface)
        # Apply palette from loaded image
        if pal is not None:
            for i, (r, g, b) in enumerate(pal[:bm._max_colors]):
                palette.set(i, r >> 4, g >> 4, b >> 4)
        return bm


# Minimal 8x8 bitmap font — printable ASCII subset
_FONT_8X8 = {
    ' ': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    '!': [0x18, 0x18, 0x18, 0x18, 0x18, 0x00, 0x18, 0x00],
    '"': [0x6C, 0x6C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    '#': [0x6C, 0xFE, 0x6C, 0x6C, 0xFE, 0x6C, 0x00, 0x00],
    '(': [0x0C, 0x18, 0x30, 0x30, 0x30, 0x18, 0x0C, 0x00],
    ')': [0x30, 0x18, 0x0C, 0x0C, 0x0C, 0x18, 0x30, 0x00],
    '*': [0x00, 0x66, 0x3C, 0xFF, 0x3C, 0x66, 0x00, 0x00],
    '+': [0x00, 0x18, 0x18, 0x7E, 0x18, 0x18, 0x00, 0x00],
    ',': [0x00, 0x00, 0x00, 0x00, 0x00, 0x18, 0x18, 0x30],
    '-': [0x00, 0x00, 0x00, 0x7E, 0x00, 0x00, 0x00, 0x00],
    '.': [0x00, 0x00, 0x00, 0x00, 0x00, 0x18, 0x18, 0x00],
    '/': [0x06, 0x0C, 0x18, 0x30, 0x60, 0xC0, 0x00, 0x00],
    '0': [0x3C, 0x66, 0x6E, 0x76, 0x66, 0x66, 0x3C, 0x00],
    '1': [0x18, 0x38, 0x18, 0x18, 0x18, 0x18, 0x7E, 0x00],
    '2': [0x3C, 0x66, 0x06, 0x0C, 0x18, 0x30, 0x7E, 0x00],
    '3': [0x3C, 0x66, 0x06, 0x1C, 0x06, 0x66, 0x3C, 0x00],
    '4': [0x0C, 0x1C, 0x3C, 0x6C, 0x7E, 0x0C, 0x0C, 0x00],
    '5': [0x7E, 0x60, 0x7C, 0x06, 0x06, 0x66, 0x3C, 0x00],
    '6': [0x1C, 0x30, 0x60, 0x7C, 0x66, 0x66, 0x3C, 0x00],
    '7': [0x7E, 0x06, 0x0C, 0x18, 0x30, 0x30, 0x30, 0x00],
    '8': [0x3C, 0x66, 0x66, 0x3C, 0x66, 0x66, 0x3C, 0x00],
    '9': [0x3C, 0x66, 0x66, 0x3E, 0x06, 0x0C, 0x38, 0x00],
    ':': [0x00, 0x18, 0x18, 0x00, 0x18, 0x18, 0x00, 0x00],
    '=': [0x00, 0x00, 0x7E, 0x00, 0x7E, 0x00, 0x00, 0x00],
    '?': [0x3C, 0x66, 0x06, 0x0C, 0x18, 0x00, 0x18, 0x00],
    'A': [0x3C, 0x66, 0x66, 0x7E, 0x66, 0x66, 0x66, 0x00],
    'B': [0x7C, 0x66, 0x66, 0x7C, 0x66, 0x66, 0x7C, 0x00],
    'C': [0x3C, 0x66, 0x60, 0x60, 0x60, 0x66, 0x3C, 0x00],
    'D': [0x78, 0x6C, 0x66, 0x66, 0x66, 0x6C, 0x78, 0x00],
    'E': [0x7E, 0x60, 0x60, 0x7C, 0x60, 0x60, 0x7E, 0x00],
    'F': [0x7E, 0x60, 0x60, 0x7C, 0x60, 0x60, 0x60, 0x00],
    'G': [0x3C, 0x66, 0x60, 0x6E, 0x66, 0x66, 0x3E, 0x00],
    'H': [0x66, 0x66, 0x66, 0x7E, 0x66, 0x66, 0x66, 0x00],
    'I': [0x3C, 0x18, 0x18, 0x18, 0x18, 0x18, 0x3C, 0x00],
    'J': [0x06, 0x06, 0x06, 0x06, 0x66, 0x66, 0x3C, 0x00],
    'K': [0x66, 0x6C, 0x78, 0x70, 0x78, 0x6C, 0x66, 0x00],
    'L': [0x60, 0x60, 0x60, 0x60, 0x60, 0x60, 0x7E, 0x00],
    'M': [0x63, 0x77, 0x7F, 0x6B, 0x63, 0x63, 0x63, 0x00],
    'N': [0x66, 0x76, 0x7E, 0x7E, 0x6E, 0x66, 0x66, 0x00],
    'O': [0x3C, 0x66, 0x66, 0x66, 0x66, 0x66, 0x3C, 0x00],
    'P': [0x7C, 0x66, 0x66, 0x7C, 0x60, 0x60, 0x60, 0x00],
    'Q': [0x3C, 0x66, 0x66, 0x66, 0x6A, 0x6C, 0x36, 0x00],
    'R': [0x7C, 0x66, 0x66, 0x7C, 0x6C, 0x66, 0x66, 0x00],
    'S': [0x3C, 0x66, 0x60, 0x3C, 0x06, 0x66, 0x3C, 0x00],
    'T': [0x7E, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x00],
    'U': [0x66, 0x66, 0x66, 0x66, 0x66, 0x66, 0x3C, 0x00],
    'V': [0x66, 0x66, 0x66, 0x66, 0x66, 0x3C, 0x18, 0x00],
    'W': [0x63, 0x63, 0x63, 0x6B, 0x7F, 0x77, 0x63, 0x00],
    'X': [0x66, 0x66, 0x3C, 0x18, 0x3C, 0x66, 0x66, 0x00],
    'Y': [0x66, 0x66, 0x66, 0x3C, 0x18, 0x18, 0x18, 0x00],
    'Z': [0x7E, 0x06, 0x0C, 0x18, 0x30, 0x60, 0x7E, 0x00],
}
# Add lowercase as copies of uppercase
for _c in range(ord('a'), ord('z') + 1):
    _FONT_8X8[chr(_c)] = _FONT_8X8.get(chr(_c - 32), _FONT_8X8[' '])
