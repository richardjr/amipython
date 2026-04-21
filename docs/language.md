# Python Subset

amipython is not full Python. It is a restricted subset sufficient for game logic, tailored for game development and static compilation to C89.

## Supported Features

- Variables with type annotations (`x: int = 42`)
- Functions with annotated parameters and return types
- `if`/`elif`/`else`, `while`, `for i in range()`, `for item in list_var`
- `break`, `continue`, `pass`
- `global` declarations
- `print()` with multiple arguments
- Basic types: `int`, `float`, `bool`, `str`
- `@dataclass` classes (maps to C structs)
- `list[T]` typed lists with `.append()`, `.remove()`, `len()`
- Arithmetic with Python semantics (floor division, modulo, power)
- Boolean operators: `and`, `or`, `not`
- Comparison chaining: `a < b < c`
- `from amiga import ...` for engine types and builtins
- `from dataclasses import dataclass` for struct definitions

## Supported Python Data Types

| Python Type | C89 Type | Notes |
|---|---|---|
| `int` | `LONG` | 32-bit signed (vbcc int is 16-bit on 68k) |
| `float` | `float` | IEEE single-precision |
| `bool` | `BOOL` | 0 or 1 |
| `str` | `const char *` | Immutable literals only |
| `@dataclass class` | `typedef struct` | Fields: int, float, bool only. No methods, no inheritance |
| `list[T]` | Fixed-capacity array | Max 256 elements. T can be int, float, bool, dataclass, or engine type (Shape, Bitmap, etc.) |

## Supported Python Builtins

| Builtin | Notes |
|---|---|
| `print()` | Multiple args, int/float/bool/str |
| `range(n)`, `range(a,b)`, `range(a,b,step)` | For loops |
| `int()` | Float-to-int conversion |
| `float()` | Int-to-float conversion |
| `str()` | Int or bool → str (e.g. `str(42) == "42"`, `str(True) == "True"`) |
| `abs()` | Absolute value |
| `len()` | List length |

## Type System

amipython uses implicit static typing — a variable holds one type throughout its lifetime. Types are inferred from assignments and annotations:

```python
x: int = 42          # explicit annotation
y = 3.14             # inferred as float
name = "hello"       # inferred as str
flag = True          # inferred as bool
```

### Strings

String literals are immutable `const char *` values. Concatenation, slicing,
and formatting operators are not supported. To render a number as a string,
use `str()` or `int_to_str()`:

```python
from amiga import int_to_str

a: str = str(42)             # "42"
b: str = str(True)           # "True"
c: str = str(-7)             # "-7"
d: str = int_to_str(score, 6)    # "000123" — zero-padded to width 6
e: str = int_to_str(-5, 4)        # "-005" — sign kept, width includes sign
```

- `str(x)` accepts **int** or **bool** (no `str(float)` — rounding rules are
  surprising; do your own formatting via `int()` if needed).
- `int_to_str(n, width)` always zero-pads; the sign counts toward width.
- Returned strings live in a small runtime ring buffer (4 slots). You can use
  several conversions in one expression (`print(str(a), str(b), str(c), str(d))`)
  but do not **store** the returned pointer past the next few conversions —
  if you need to keep a formatted value, print it immediately or assign it
  to a `str` variable **right after** the conversion.

### Dataclass Structs

Use `@dataclass` from Python's stdlib to define data structs:

```python
from dataclasses import dataclass

@dataclass
class Ball:
    x: float
    y: float
    speed: float = 1.0   # default value

b = Ball(x=10.0, y=20.0)       # speed defaults to 1.0
b.x += 0.5                      # field access and mutation
```

This maps to C:
```c
typedef struct {
    float x;
    float y;
    float speed;
} Ball;

Ball b;
b.x = 10.0f;
b.y = 20.0f;
b.speed = 1.0f;
b.x += 0.5f;
```

Struct rules:
- Fields must be `int`, `float`, or `bool`
- No methods — use standalone functions
- No inheritance
- Constructor uses keyword arguments only

### Typed Lists

Lists are fixed-capacity (64 elements) typed arrays:

```python
from dataclasses import dataclass

@dataclass
class Ball:
    x: float
    y: float

balls: list[Ball] = []
balls.append(Ball(x=10.0, y=20.0))

for b in balls:
    b.x += 1.0    # b is a reference — mutations persist

n = len(balls)     # current count
```

This maps to C:
```c
Ball balls_items[64];
LONG balls_count = 0;

balls_items[balls_count].x = 10.0f;
balls_items[balls_count].y = 20.0f;
balls_count++;

for (b_idx = 0; b_idx < balls_count; b_idx++) {
    b = &balls_items[b_idx];
    b->x += 1.0f;
}

n = balls_count;
```

List rules:
- Element type can be `int`, `float`, `bool`, or a `@dataclass` struct
- Maximum 256 elements per list (trig tables can be larger via `sin_table(n)` / `cos_table(n)`)
- `for item in list:` gives a pointer for struct lists (mutations persist)
- `list[idx]` for element read access
- `list[idx] = value` for in-place mutation (index must be `int`, value must match the element type)
- `.append(item)` and `.remove(item)` supported
- `len(list)` returns current count

#### Using a flat list as a 2D grid

Nested `list[list[T]]` is not supported. For 2D data, use a flat list indexed as `y * WIDTH + x`:

```python
W: int = 10
H: int = 20

board: list[int] = []
for i in range(W * H):
    board.append(0)

# Read
cell = board[y * W + x]

# Write
board[y * W + x] = 1
```

This is the standard layout for game grids (Tetris wells, tile maps, collision masks).

### Type Mapping

| Python | C89 | Notes |
|---|---|---|
| `int` | `LONG` | 32-bit — vbcc's `int` is 16-bit on 68k |
| `float` | `float` | IEEE single-precision |
| `bool` | `BOOL` | 0 or 1 |
| `str` | `const char *` | String literals only (no mutation) |

### Arithmetic Semantics

Python's arithmetic rules are preserved in the generated C:

- **Floor division** (`//`): rounds toward negative infinity, not zero (`-7 // 2 == -4`)
- **Modulo** (`%`): result has the sign of the divisor (`-7 % 2 == 1`)
- **Power** (`**`): mapped to `amipython_power()` helper
- **Int/float promotion**: `int + float` promotes to `float`

## Engine Imports

Game engine types are imported from the `amiga` module:

```python
from amiga import Display, Bitmap, palette, wait_mouse
```

This import works in two contexts:
- **Python preview** (`python game.py`) — imports from `src/amiga/`, a pygame-based implementation
- **Transpilation** (`amipython transpile game.py`) — the transpiler recognises `from amiga import` and generates the corresponding C code

### Engine Objects

Objects like `Display` and `Bitmap` are created with constructors that support keyword arguments:

```python
display = Display(320, 256, bitplanes=5)
bm = Bitmap(320, 256, bitplanes=5)
```

These map to C structs with init functions:
```c
AmipyDisplay display;
AmipyBitmap bm;
amipython_display_init(&display, 320, 256, 5);
amipython_bitmap_init(&bm, 320, 256, 5);
```

### Drawing Methods

`Bitmap` objects support these drawing primitives:

```python
bm.circle_filled(cx, cy, r, color)     # filled circle
bm.box_filled(x1, y1, x2, y2, color)   # filled rectangle
bm.plot(x, y, color)                    # single pixel
bm.line(x1, y1, x2, y2, color)          # single-pixel line
bm.clear()                              # fill entire bitmap with colour 0
bm.clear_rect(x, y, w, h)               # fill one region with colour 0
```

### Text Rendering

`print_at` uses a built-in 8x8 bitmap font. It accepts one or more positional
text pieces — strings, ints, and bools are rendered with single-glyph-width
gaps between them (no manual string concatenation needed):

```python
bm.print_at(10, 20, "HELLO")                            # single string
bm.print_at(10, 20, "HELLO", color=2)                   # with color
bm.print_at(10, 20, "SCORE", score, "lines", lines)     # multi-arg, mixed types
bm.print_at(10, 40, "SCORE", int_to_str(score, 6))      # zero-padded score

bm.print_centered(40, "AMITETRIS")                      # horizontally centered
bm.print_centered(80, "SCORE", int_to_str(score, 6))    # centered, multi-arg

bm.print_right(300, 100, "final", int_to_str(score, 6)) # right edge at x=300
```

- Positional args after `x, y` accept `str`, `int`, or `bool` — int/bool are
  converted via `str()` automatically at the call site.
- `color=` is a keyword argument (default 1).
- Each glyph is 8×8 pixels, rendered directly to the bitmap (self-clearing —
  the background is filled with colour 0 before the glyph is drawn).

**Avoid flicker on HUD text.** `print_at` already clears each glyph cell
before drawing, so a full `bm.clear()` on every frame is redundant — and,
combined with a value that changes every frame, it produces visible
redraw flicker. The clean pattern is to paint the static labels once
before `run()` starts, then only repaint a numeric cell on frames when
its value actually changes:

```python
prev_score: int = -1

def update():
    global prev_score
    # ... gameplay ...
    if score != prev_score:
        screen.print_at(140, 30, int_to_str(score, 6))
        prev_score = score

draw_labels()                      # once, before the loop
run(update, until=lambda: False)
```

See `examples/basic/score_display.py` for the full pattern.

### Shapes (Blittable Graphics)

Shapes are rectangular graphics grabbed from a bitmap or loaded from image files:

```python
# Procedural: draw then grab
bm.circle_filled(8, 8, 7, 1)           # draw on the display bitmap
ball = Shape.grab(bm, 0, 0, 16, 16)    # grab the region as a shape
bm.clear()                              # clear the source drawing

# From file: load a PNG or IFF image
ball = Shape.load("data/ball.png")      # PNG converted to .bm at build time

display.blit(ball, x, y)               # blit the shape at runtime
```

Shape rules:
- Draw the shape on the **display bitmap** (`bm`), not a separate small bitmap
- Shape width is automatically rounded up to a multiple of 16 (blitter word alignment)
- Use `display.blit(shape, x, y)` to draw — coordinates must keep the shape within screen bounds
- `Shape.load()` accepts `.png` or `.iff` files — converted to ACE `.bm` format at build time
- Color index 0 in loaded images is treated as transparent (mask auto-generated)

### Sprite Sheets

Load a single image and grab multiple shapes from it:

```python
from amiga import Bitmap, Shape

sheet = Bitmap.load("data/eq_bars.png")    # 144x32 sprite sheet
bars: list[Shape] = []
for i in range(9):
    bars.append(Shape.grab(sheet, i * 16, 0, 16, 32))

# Use individual frames:
display.blit(bars[frame_index], x, y)
```

`list[Shape]` supports all standard list operations. Engine types (Shape, Bitmap, etc.) can be used as list element types alongside int, float, bool, and dataclass types.

### Loading Bitmaps from Files

Full bitmaps can be loaded from image files with palette auto-extraction:

```python
bg = Bitmap.load("data/background.png")  # palette applied automatically
display.show(bg)
```

- Palette is extracted from the image and applied via `palette.set()` calls
- Supports PNG (indexed) and IFF ILBM formats
- Images are converted to ACE `.bm` format at build time (zero runtime overhead)

### Engine Modules

Singleton modules like `palette` and `music` are called directly:

```python
palette.aga(0, 255, 0, 0)     # 8-bit RGB, downscaled to OCS 12-bit
palette.set(0, 15, 0, 0)      # direct OCS 4-bit values
palette.fade(7)                # fade all colours: 0=black, 15=full brightness
```

### Music (ProTracker MOD Playback)

Background music playback using ProTracker MOD files:

```python
from amiga import music

music.load("data/song.mod")   # embed MOD at transpile time
music.play()                   # start playback (loops forever)
music.stop()                   # stop playback
music.volume(48)               # 0-64, default 64
```

- MOD file is embedded in the binary at transpile time (same approach as images)
- On Amiga: uses ACE's ptplayer (CIA-B interrupt timing, runs autonomously)
- In Python preview: uses pygame.mixer for MOD playback
- No per-frame calls needed — music plays via interrupt

### Sound Effects (One-shot Samples)

One-shot sample playback that runs alongside MOD music. Samples are loaded
from WAV files at transpile time — the data is converted to 8-bit signed
mono and embedded directly in the binary, so there is no runtime file I/O.

```python
from amiga import sfx

sfx.load(0, "data/lock.wav")
sfx.load(1, "data/clear.wav")
sfx.load(2, "data/blip.wav")

sfx.play(0)                              # default: channel=2, volume=64
sfx.play(1, channel=3, volume=48)        # specific channel + volume
sfx.stop(0)
```

- Slots are `0..7`. WAV must be PCM 8-bit unsigned or 16-bit signed; stereo
  channels are averaged to mono.
- `channel` picks one of the four Paula channels (`0..3`). Channels 0 and 1
  are typically left-hand, 2 and 3 right-hand. MOD playback uses all four
  concurrently, so pick a channel whose current MOD voice you can afford to
  interrupt (channel 2 or 3 for SFX is a common compromise).
- `volume` is `0..64` (ACE convention). Default 64.
- In the Python preview, playback uses `pygame.mixer.Sound` on the same
  channel index — volume maps linearly to pygame's 0.0..1.0 range.

### Storage (Persistent State)

Save game state (high scores, player name, settings) to a tiny binary file
that survives reboots. Data lives at `PROGDIR:<name>.dat` on Amiga and at
`~/.amipython/<script-stem>/<name>.dat` in the Python preview.

```python
from amiga import storage

# Integer lists (high scores, unlocked levels, save-slot flags).
scores: list[int] = []
for i in range(5):
    scores.append(0)               # default values

storage.load_int_list("scores", scores)      # populates in place if the
                                              # file exists; no-op if missing
scores[0] = 1234
storage.save_int_list("scores", scores)

# Strings (player name, last-selected skin).
storage.save_str("name", "RJR")
name: str = storage.load_str("name")   # "" if not saved yet

if storage.exists("scores"):
    ...
```

- `save_int_list(name, items)` — writes the list's current contents.
- `load_int_list(name, items)` — overwrites the list's contents in place.
  Returns `False` and leaves the list unchanged if the file is missing or
  malformed, so initialise the list to sensible defaults **before** calling.
- `save_str(name, value)` / `load_str(name) -> str` — strings up to 65535
  bytes. `load_str` returns `""` if nothing is saved.
- `exists(name) -> bool` — probe without loading.

File format is a tight `"AMPY"` + version + kind + big-endian payload — same
bytes on both platforms so a preview save is technically portable, though in
practice you save on the target.

### Tilemap (Hardware Scrolling)

Tile-based scrolling maps using ACE's tileBufferManager for hardware-accelerated scrolling:

```python
from amiga import Tilemap, palette, joy, run

tm = Tilemap("data/tiles.png", 320, 200, bitplanes=3,
             tile_size=16, map_w=40, map_h=30)

# Set tiles (column-major: x, y, tile_index)
tm.set_tile(5, 3, 1)

tm.show()              # create display and render initial tiles
tm.scroll(2, 0)        # scroll by dx, dy pixels
tm.camera(100, 50)     # set absolute camera position

def update():
    if joy.left():
        tm.scroll(-2, 0)
    if joy.right():
        tm.scroll(2, 0)

run(update, until=lambda: joy.button(0))
```

- Tileset PNG is a vertical strip — one tile per row, 16px wide
- Tilemap creates its own display (replaces `Display`/`Bitmap`)
- On Amiga: uses ACE tileBuffer with hardware fine scrolling (BPLCON1) and incremental edge redraws
- In Python preview: pygame-based tile rendering with camera offset
- `tile_size` must be a power of 2 (16 recommended for word-aligned blitter speed)
- Map is column-major internally: `set_tile(x, y, tile_index)`

### Joystick Directions

```python
from amiga import joy

# Held-state — True every frame the input is down.
joy.left()      # True if joystick held left
joy.right()     # True if joystick held right
joy.up()        # True if joystick held up
joy.down()      # True if joystick held down
joy.button(0)   # True every frame the fire button is held on port 0

# Edge-triggered — True only on the frame the input transitions 0→1.
joy.left_pressed()     # one tap = one True
joy.right_pressed()
joy.up_pressed()
joy.down_pressed()
joy.button_pressed(0)  # one tap = one True per port (independent latches)
```

Use the `*_pressed()` variants for actions that should fire exactly once per
press — menu selection, rotate, hard drop, confirm. Use the held-state variants
for continuous motion — walking, soft drop, aiming.

In Python preview, arrow keys (or WASD) substitute for joystick directions,
Space for fire on port 1, and LMB (or Space) for fire on port 0.

### Keyboard

```python
from amiga import key
from amiga import (
    K_A, K_B, K_C, K_D, K_E, K_F, K_G, K_H, K_I, K_J, K_K, K_L, K_M,
    K_N, K_O, K_P, K_Q, K_R, K_S, K_T, K_U, K_V, K_W, K_X, K_Y, K_Z,
    K_0, K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9,
    K_LEFT, K_RIGHT, K_UP, K_DOWN, K_SPACE, K_RETURN, K_ESC,
)

if key.pressed(K_SPACE):          # True while held
    ...
if key.just_pressed(K_P):         # True once per press (edge up)
    toggle_pause()
if key.just_released(K_ESC):      # True once per release (edge down)
    quit_to_title()
```

The `K_*` constants are Amiga raw-key codes — they transpile to `#define`
lines in the generated C (matching ACE's `KEY_*` codes). Only import the
ones your program actually references; unused constants are not emitted.

Use `just_pressed` for menu selection, rotate, pause, commit. Use `pressed`
for walk/hold behaviours. Use `just_released` for "release-to-exit" flows.

### Engine Builtins

Top-level functions from the engine:

```python
wait_mouse()            # wait for left mouse button click
vwait(1)                # wait for 1 vertical blank (1/50th second)
vwait(3)                # wait for 3 vertical blanks (slower animation)
rnd(100)                # random integer 0-99
shuffle(lst)            # Fisher-Yates shuffle a list[int] in place
int_to_str(42, 6)       # zero-padded decimal: "000042" (for scores, counters)
int_to_str(-5, 4)       # sign-preserving: "-005"
sin_table(720)          # list of 720 pre-computed sin values (0 to 2*pi)
cos_table(720)          # list of 720 pre-computed cos values (0 to 2*pi)
sin_table(720, 80)      # list of 720 pre-computed int(sin * 80) values
cos_table(720, 80)      # list of 720 pre-computed int(cos * 80) values
```

### Lookup Tables

Pre-computed trig tables for fast angle calculations — essential for smooth animation on 7MHz 68000:

```python
from amiga import sin_table, cos_table

# Integer-scaled tables (recommended for game loops — pure integer math)
orbit_x = cos_table(720, 80)    # list[int], 720 entries pre-scaled by 80
orbit_y = sin_table(720, 80)

x = 160 + orbit_x[idx]          # integer add only
y = 128 + orbit_y[idx]

# Float tables (for static calculations only)
orbit_x = cos_table(720)        # list[float], 720 entries
x = 160 + int(orbit_x[idx] * radius)
```

All table values are computed at transpile time in Python and embedded as initialized C arrays — zero runtime float math on the Amiga.

This maps to C:
```c
LONG orbit_x_items[720] = {80, 79, 79, ...};  /* pre-computed */
LONG orbit_x_count = 720;

x = 160 + orbit_x_items[idx];
```

## Not Supported (by design)

- `dict`, `set`, `frozenset`, `tuple` — too dynamic for 68k static allocation
- `None` — no null pointers; all variables must be initialized
- `bytes`, `bytearray`, `complex` — not needed for game logic
- String operations (concatenation, slicing, methods) — strings are immutable literals
- `@dataclass` methods — structs are data-only, use standalone functions
- Nested lists, `list[list[T]]` — flat structures only
- List comprehensions, generator expressions — use explicit for loops
- Dynamic memory allocation — fixed-capacity arrays, stack structs
- `*args`, `**kwargs` on user functions
- Closures, decorators (except `@dataclass`), generators, `yield`
- `try`/`except`, `with`, `async`/`await`
- `import` (except `from dataclasses import dataclass` and `from amiga import ...`)
- `eval()`, `exec()`, `getattr()`, `setattr()`
- Metaclasses, duck typing
- Garbage collection — all memory is statically allocated or arena-managed
