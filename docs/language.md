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
| `list[T]` | Fixed-capacity array | Max 64 elements. T can be int, float, bool, dataclass, or engine type (Shape, Bitmap, etc.) |

## Supported Python Builtins

| Builtin | Notes |
|---|---|
| `print()` | Multiple args, int/float/bool/str |
| `range(n)`, `range(a,b)`, `range(a,b,step)` | For loops |
| `int()` | Float-to-int conversion |
| `float()` | Int-to-float conversion |
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
- Maximum 64 elements per list (trig tables can be larger)
- `for item in list:` gives a pointer for struct lists (mutations persist)
- `list[idx]` for element access by index
- `.append(item)` and `.remove(item)` supported
- `len(list)` returns current count

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
bm.clear()                              # fill with colour 0
```

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

joy.left()      # True if joystick held left
joy.right()     # True if joystick held right
joy.up()        # True if joystick held up
joy.down()      # True if joystick held down
joy.button(0)   # True if fire button pressed
```

In Python preview, arrow keys substitute for joystick directions.

### Engine Builtins

Top-level functions from the engine:

```python
wait_mouse()            # wait for left mouse button click
vwait(1)                # wait for 1 vertical blank (1/50th second)
vwait(3)                # wait for 3 vertical blanks (slower animation)
rnd(100)                # random integer 0-99
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
