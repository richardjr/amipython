"""Storage module — persistent key-value storage for game state (high scores, etc.).

On Amiga the transpiled code writes `PROGDIR:<name>.dat` via dos.library.
In the preview we write under `~/.amipython/<script-stem>/<name>.dat` so
each amipython script has its own storage namespace.

File format matches the Amiga runtime:
    bytes 0-3 : magic "AMPY"
    byte  4   : version (1)
    byte  5   : kind — 0=int_list, 1=str
    int_list  : bytes 6-9 = count (BE32), then count * 4 bytes BE32
    str       : bytes 6-7 = length (BE16), then length bytes
"""

from __future__ import annotations

import inspect
import os
import struct
from pathlib import Path

MAGIC = b"AMPY"
VERSION = 1
KIND_INT_LIST = 0
KIND_STR = 1


def _base_dir() -> Path:
    """Derive the per-script storage directory from the calling script path."""
    for frame in inspect.stack():
        fn = frame.filename
        if "amiga/" in fn or fn.endswith("amiga/_storage.py"):
            continue
        stem = Path(fn).stem
        d = Path.home() / ".amipython" / stem
        d.mkdir(parents=True, exist_ok=True)
        return d
    d = Path.home() / ".amipython" / "default"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(name: str) -> Path:
    return _base_dir() / f"{name}.dat"


class _StorageModule:
    """Persistent storage singleton."""

    def exists(self, name: str) -> bool:
        return _path(name).exists()

    def save_int_list(self, name: str, items) -> None:
        count = len(items)
        with open(_path(name), "wb") as f:
            f.write(MAGIC)
            f.write(bytes([VERSION, KIND_INT_LIST]))
            f.write(struct.pack(">I", count))
            for v in items:
                f.write(struct.pack(">i", int(v)))

    def load_int_list(self, name: str, items) -> bool:
        """Populate `items` in place from the stored list.

        Returns False (and leaves the list unchanged) if the file doesn't exist
        or is malformed. Returns True on success. Matches the in-place semantics
        of the C runtime where the list's items[] buffer is overwritten.
        """
        p = _path(name)
        if not p.exists():
            return False
        try:
            with open(p, "rb") as f:
                header = f.read(10)
                if len(header) != 10 or header[:4] != MAGIC or header[5] != KIND_INT_LIST:
                    return False
                count = struct.unpack(">I", header[6:10])[0]
                loaded = [struct.unpack(">i", f.read(4))[0] for _ in range(count)]
        except (OSError, struct.error):
            return False
        # Replace list contents in place.
        items.clear()
        items.extend(loaded)
        return True

    def save_str(self, name: str, value: str) -> None:
        b = value.encode("utf-8")
        if len(b) > 0xFFFF:
            b = b[:0xFFFF]
        with open(_path(name), "wb") as f:
            f.write(MAGIC)
            f.write(bytes([VERSION, KIND_STR]))
            f.write(struct.pack(">H", len(b)))
            f.write(b)

    def load_str(self, name: str) -> str:
        p = _path(name)
        if not p.exists():
            return ""
        try:
            with open(p, "rb") as f:
                header = f.read(8)
                if len(header) != 8 or header[:4] != MAGIC or header[5] != KIND_STR:
                    return ""
                length = struct.unpack(">H", header[6:8])[0]
                return f.read(length).decode("utf-8", errors="replace")
        except OSError:
            return ""


storage = _StorageModule()
