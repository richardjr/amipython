"""Sfx module — one-shot sample playback via pygame.mixer.

Mirrors `amipython_sfx_*` in the engine. Samples are loaded at script-startup
time via `sfx.load(slot, path)` and played with `sfx.play(slot, channel=, volume=)`.
"""

from __future__ import annotations

import inspect
from pathlib import Path

try:
    import pygame
except ImportError:
    pygame = None


SLOT_COUNT = 8


class _SfxModule:
    def __init__(self):
        self._sounds: dict[int, "pygame.mixer.Sound | None"] = {
            i: None for i in range(SLOT_COUNT)
        }
        self._channels: dict[int, "pygame.mixer.Channel | None"] = {}
        self._initialized = False

    def _ensure_init(self) -> None:
        if self._initialized or pygame is None:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2)
            self._initialized = True
        except pygame.error:
            self._initialized = False

    def load(self, slot: int, path: str) -> None:
        if not 0 <= slot < SLOT_COUNT or pygame is None:
            return
        self._ensure_init()
        caller_dir = Path(inspect.stack()[1].filename).parent
        full = caller_dir / path
        if not full.exists():
            return
        try:
            self._sounds[slot] = pygame.mixer.Sound(str(full))
        except pygame.error:
            self._sounds[slot] = None

    def play(self, slot: int, *, channel: int = 2, volume: int = 64) -> None:
        if not 0 <= slot < SLOT_COUNT or pygame is None:
            return
        snd = self._sounds.get(slot)
        if snd is None:
            return
        self._ensure_init()
        ch = self._channels.get(channel)
        if ch is None:
            try:
                ch = pygame.mixer.Channel(channel)
            except (pygame.error, ValueError):
                ch = None
            self._channels[channel] = ch
        if ch is None:
            # Fallback to mixer-managed channel selection.
            snd.set_volume(max(0.0, min(1.0, volume / 64.0)))
            snd.play()
            return
        snd.set_volume(max(0.0, min(1.0, volume / 64.0)))
        ch.play(snd)

    def stop(self, slot: int) -> None:
        if not 0 <= slot < SLOT_COUNT or pygame is None:
            return
        snd = self._sounds.get(slot)
        if snd is not None:
            snd.stop()


sfx = _SfxModule()
