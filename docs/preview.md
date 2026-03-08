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
| `rnd(n)` | Supported |
| `run(update, until=...)` | Supported — 50fps game loop |
| `Shape.grab(bm, x, y, w, h)` | Supported |
| `Shape.load(path)` | Supported — loads PNG |
| `display.blit(shape, x, y)` | Supported |
| `Sprite.grab(bm, x, y, w, h)` | Supported |
| `sprite.show(x, y, channel=)` | Supported |
| `joy.button(port)` | Supported |
| `mouse.x` / `mouse.y` | Supported |
| `mouse.set_pointer(sprite)` | Supported |
| `collision.register(color=, mask=)` | Supported |
| `collision.check()` | Supported |
| `bm.box_filled(...)` | Supported |
| `bm.line(...)` | Supported |
| `bm.print_at(x, y, text)` | Supported |
| `sin_table(n)` / `cos_table(n)` | Supported |
| `music.load(path)` | Supported — loads MOD via pygame.mixer |
| `music.play()` / `music.stop()` | Supported |
| `music.volume(vol)` | Supported — 0-64 |

Not yet implemented: copper effects, dual playfield, scrolling, keyboard input.

## Palette Fidelity

The preview matches Amiga OCS hardware colour depth:

- `palette.aga(reg, r, g, b)` takes 8-bit values (0-255), downscales to 4-bit (0-15), then expands back to 8-bit for display. This produces exactly 16 distinct levels per channel: 0, 17, 34, 51, ..., 238, 255.
- `palette.set(reg, r, g, b)` takes direct OCS 4-bit values (0-15), expanded to 8-bit the same way.
- Colour index 0 is always the background colour.

## Display Scaling

The internal surface runs at Amiga resolution (e.g. 320x256). The preview window scales this 3x using nearest-neighbour interpolation to preserve the pixel-art look. The window title shows "amipython preview".

## Limitations

- **No copper effects** — `copper.color_at()` per-scanline palette changes are not emulated
- **No scrolling** — `display.scroll_to()` is not yet implemented
- **No keyboard input** — `key` module is not yet implemented
- **No dual playfield** — `DualPlayfield` is not yet implemented

## Architecture

```
src/amiga/
    __init__.py       # Public API exports
    _backend.py       # Pygame singleton: window, palette, events, 50fps clock
    _bitmap.py        # Bitmap with 8-bit indexed surface
    _display.py       # Display — lazy window creation on show()
    _palette.py       # OCS 12-bit palette emulation
    _builtins.py      # wait_mouse(), vwait(), rnd(), run(), sin_table(), cos_table()
    _shape.py         # Shape — grab/load, blitting
    _sprite.py        # Sprite — hardware sprite emulation
    _joy.py           # Joystick input
    _mouse.py         # Mouse input
    _collision.py     # Collision detection
    _music.py         # ProTracker MOD playback via pygame.mixer
    _constants.py     # PAL_FPS=50, MAX_PALETTE=256, DEFAULT_SCALE=3
```

The backend is a singleton — only one window exists at a time. All Bitmap surfaces are tracked via weak references so palette changes propagate automatically.
