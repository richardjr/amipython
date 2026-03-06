# Python Preview Mode

amipython scripts can run directly in Python with a visual preview window — no cross-compilation or Amiga emulator needed. This is the fastest way to iterate on your game.

## Setup

Install with the `preview` extra to get [pygame-ce](https://pyga.me/):

```bash
pip install -e ".[preview]"
```

## Usage

Run any amipython script directly:

```bash
python examples/basic/display1.py
python examples/basic/minimal_display.py
```

A window opens showing the output at 3x scale (320x256 becomes 960x768). Click the left mouse button to exit.

## How It Works

The `from amiga import ...` statement imports from a real Python package (`src/amiga/`) that implements the same API as the Amiga C runtime, using pygame for rendering.

The key to faithful emulation is **indexed colour palettes**. Pygame's 8-bit Surface mode stores colour indices per pixel, not RGB values. When you call `palette.set(1, 15, 0, 0)`, every pixel already drawn with colour index 1 changes to red — exactly how Amiga hardware works.

### Two ways to run the same script

```
game.py ──→ python game.py          → pygame window (instant preview)
         └→ amipython run game.py   → transpile → compile → Amiberry (real Amiga)
```

The Python preview and the Amiga binary produce visually identical output because both paths implement the same API with the same palette model.

## What's Supported

The preview module currently implements the Phase 2 API:

| Feature | Status |
|---|---|
| `Display(w, h, bitplanes=)` | Supported — creates scaled preview window |
| `Bitmap(w, h, bitplanes=)` | Supported — 8-bit indexed surface |
| `bm.circle_filled(cx, cy, r, color)` | Supported |
| `bm.plot(x, y, color)` | Supported |
| `bm.clear()` | Supported |
| `display.show(bm)` | Supported |
| `palette.aga(reg, r, g, b)` | Supported — OCS 12-bit downscale |
| `palette.set(reg, r, g, b)` | Supported — direct OCS 4-bit values |
| `wait_mouse()` | Supported — waits for LMB click |
| `vwait()` | Supported — 50fps PAL timing |

Future phases will add `run()`, sprites, shapes, input, scrolling, copper, and more.

## Palette Fidelity

The preview matches Amiga OCS hardware colour depth:

- `palette.aga(reg, r, g, b)` takes 8-bit values (0-255), downscales to 4-bit (0-15), then expands back to 8-bit for display. This produces exactly 16 distinct levels per channel: 0, 17, 34, 51, ..., 238, 255.
- `palette.set(reg, r, g, b)` takes direct OCS 4-bit values (0-15), expanded to 8-bit the same way.
- Colour index 0 is always the background colour.

## Display Scaling

The internal surface runs at Amiga resolution (e.g. 320x256). The preview window scales this 3x using nearest-neighbour interpolation to preserve the pixel-art look. The window title shows "amipython preview".

## Limitations

- **No `run()` game loop yet** — scripts using `run(update, until=...)` won't work until Phase 3
- **No input modules** — `joy`, `mouse`, `key` are not yet implemented in the preview
- **No sprites/shapes** — `Sprite`, `Shape`, `display.blit()` are not yet implemented
- **No copper effects** — `copper.color_at()` per-scanline palette changes are not emulated
- **No scrolling** — `display.scroll_to()` is not yet implemented
- **No sound** — Paula audio is not emulated

These will be added as the corresponding transpiler phases are implemented.

## Architecture

```
src/amiga/
    __init__.py       # Public API exports
    _backend.py       # Pygame singleton: window, palette, events, 50fps clock
    _bitmap.py        # Bitmap with 8-bit indexed surface
    _display.py       # Display — lazy window creation on show()
    _palette.py       # OCS 12-bit palette emulation
    _builtins.py      # wait_mouse(), vwait()
    _constants.py     # PAL_FPS=50, MAX_PALETTE=256, DEFAULT_SCALE=3
```

The backend is a singleton — only one window exists at a time. All Bitmap surfaces are tracked via weak references so palette changes propagate automatically.
