"""Pygame backend singleton — manages window, palette, events, and frame timing."""

from __future__ import annotations

import weakref

try:
    import pygame
except ImportError:
    pygame = None

from amiga._constants import PAL_FPS, MAX_PALETTE, DEFAULT_SCALE


def _require_pygame() -> None:
    if pygame is None:
        raise ImportError(
            "pygame-ce is required for the amiga preview module.\n"
            "Install it with: pip install pygame-ce"
        )


class Backend:
    """Singleton managing the pygame window and shared state."""

    _instance: Backend | None = None

    def __init__(self) -> None:
        self._initialized = False
        self._screen = None
        self._scale = DEFAULT_SCALE
        self._palette: list[tuple[int, int, int]] = [(0, 0, 0)] * MAX_PALETTE
        self._width = 320
        self._height = 256
        self._running = True
        self._clock = None
        self._surfaces: weakref.WeakSet = weakref.WeakSet()
        self._active_surface = None  # surface set by display.show()
        self._active_tilemap = None  # set by tilemap.show()
        # Per-scanline palette overrides recorded by copper.color_at().
        # Each entry is (scanline, register, ocs_color_word).
        self._copper_calls: list[tuple[int, int, int]] = []

    @classmethod
    def get(cls) -> Backend:
        if cls._instance is None:
            cls._instance = Backend()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — for testing."""
        if cls._instance and cls._instance._initialized:
            pygame.quit()
        cls._instance = None

    def ensure_init(self, width: int, height: int) -> None:
        """Create the pygame window if not already done."""
        if self._initialized:
            return
        _require_pygame()
        self._width = width
        self._height = height
        pygame.init()
        win_w = width * self._scale
        win_h = height * self._scale
        self._screen = pygame.display.set_mode((win_w, win_h))
        pygame.display.set_caption("amipython preview")
        self._clock = pygame.time.Clock()
        self._initialized = True

    def register_surface(self, surface: pygame.Surface) -> None:
        """Track a surface so palette changes propagate to it."""
        self._surfaces.add(surface)
        surface.set_palette(self._palette)

    def sync_palette(self) -> None:
        """Push current palette to all tracked surfaces."""
        for surface in self._surfaces:
            surface.set_palette(self._palette)

    def present(self, surface: pygame.Surface) -> None:
        """Scale an 8-bit surface to the window and flip.

        If copper.color_at() has been called, walks scanlines and applies
        per-scanline palette overrides so the gradient is visible on the
        same surface the C runtime would render on hardware.
        """
        if not self._initialized:
            return
        if self._copper_calls:
            surface = self._render_with_copper(surface)
        scaled = pygame.transform.scale(
            surface, (self._width * self._scale, self._height * self._scale)
        )
        self._screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def _render_with_copper(self, indexed: pygame.Surface) -> pygame.Surface:
        """Apply copper colour splits — for each scanline, blit one row at
        a time with the effective palette for that line. The 1-row blits
        run native pygame code and are fast enough for preview."""
        w, h = indexed.get_size()
        # Group calls by scanline so we apply all changes at the same Y in one pass.
        overrides_by_y: dict[int, list[tuple[int, int]]] = {}
        for y, reg, color in self._copper_calls:
            overrides_by_y.setdefault(y, []).append((reg, color))

        cur_pal = list(self._palette)
        # Stash the original surface palette so we can put it back at the end —
        # otherwise other code that holds a reference to `indexed` would see the
        # mutated final-scanline palette next frame.
        saved_pal = indexed.get_palette()

        rgb = pygame.Surface((w, h))
        for y in range(h):
            ovr = overrides_by_y.get(y)
            if ovr:
                for reg, ocs_color in ovr:
                    r4 = (ocs_color >> 8) & 0xF
                    g4 = (ocs_color >> 4) & 0xF
                    b4 = ocs_color & 0xF
                    cur_pal[reg] = (r4 * 17, g4 * 17, b4 * 17)
                indexed.set_palette(cur_pal)
            elif y == 0:
                # First row — make sure we start from base.
                indexed.set_palette(cur_pal)
            rgb.blit(indexed, (0, y), (0, y, w, 1))

        indexed.set_palette(saved_pal)
        return rgb

    def pump_events(self) -> list:
        """Process pygame events. Returns the event list."""
        if not self._initialized:
            return []
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self._running = False
        return events

    def wait_vblank(self) -> None:
        """Tick at PAL frame rate."""
        if self._clock:
            self._clock.tick(PAL_FPS)
