"""Copper module — per-scanline palette overrides (preview-side emulation).

Mirrors the Amiga ``copper.color_at(scanline, register, color)`` API. Each
call records a (scanline, register, ocs_color) tuple that the backend will
apply when presenting frames — at scanline N the palette register R becomes
the given OCS colour, and that change persists down the screen until another
call (or end of frame).

``Color(r, g, b)`` is a small helper that packs three 0..15 OCS components
into the same 12-bit word the C runtime carries — the transpiler inlines the
expression so user code reads naturally on both paths.
"""

from __future__ import annotations

from amiga._backend import Backend


class _CopperModule:
    def color_at(self, *, scanline: int, register: int, color: int) -> None:
        backend = Backend.get()
        backend._copper_calls.append(
            (int(scanline), int(register), int(color) & 0xFFF)
        )


copper = _CopperModule()


def Color(r: int, g: int, b: int) -> int:
    """Pack three OCS 4-bit channels (0..15) into a 12-bit colour word."""
    return ((int(r) & 0xF) << 8) | ((int(g) & 0xF) << 4) | (int(b) & 0xF)
