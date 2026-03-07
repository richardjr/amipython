# amipython

A Python-to-Amiga game development toolchain. Write games in a Python subset, compile to native 68k Amiga executables.

## Concept

amipython follows the model proven by AMOS Basic and Blitz Basic — a high-level language paired with a purpose-built game runtime. Instead of BASIC, the authoring language is a restricted subset of Python. Instead of an interpreter running on the Amiga, code is cross-compiled to native 68k executables on a modern Linux host.

The goal: a Python developer can write Amiga games without learning 68k assembly, Copper lists, or Blitter registers. The transpiler and runtime handle all hardware complexity.

Every amipython script is valid Python. Run it directly with `python game.py` for an instant pygame preview window, or cross-compile to a native 68k binary for real Amiga hardware.

## Getting Started

### Prerequisites

- Python 3.10+
- gcc (for host-side test compilation)
- Docker (for cross-compiling to Amiga)
- [Amiberry](https://github.com/BlitterStudio/amiberry) + Kickstart 3.1 ROM (for running graphics programs)

### Installation

```bash
git clone https://github.com/3adapt/amipython.git
cd amipython
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,preview]"
```

The `preview` extra installs [pygame-ce](https://pyga.me/) so you can run amipython scripts directly in Python with a visual preview window — no cross-compilation or emulator needed.

For ADF floppy image creation, also install [amitools](https://github.com/cnvogelg/amitools):
```bash
pip install -e ".[adf]"
```

### Hello World (CLI)

```python
x: int = 42
name: str = "Amiga"

def square(n: int) -> int:
    return n * n

print("Hello,", name)
print("square(x) =", square(x))

for i in range(5):
    print("i =", i)
```

```bash
# Transpile to C
amipython transpile hello.py

# Compile and run on host
gcc -std=c89 -pedantic -Wall -o hello hello.c -lm
./hello

# Cross-compile to Amiga and run with vamos
amipython build hello.py
vamos hello
```

### Bouncing Balls (Structs + Lists)

```python
from dataclasses import dataclass
from amiga import Display, Bitmap, Shape, palette, run, joy

@dataclass
class Ball:
    x: float
    y: float
    xs: float
    ys: float

display = Display(320, 200, bitplanes=3)
bm = Bitmap(16, 16, bitplanes=3)
palette.set(1, 15, 0, 0)
bm.circle_filled(8, 8, 7, 1)
ball_shape = Shape.grab(bm, 0, 0, 16, 16)

balls: list[Ball] = []
balls.append(Ball(x=160.0, y=100.0, xs=3.0, ys=2.0))
balls.append(Ball(x=80.0, y=50.0, xs=-2.0, ys=3.0))

screen = Bitmap(320, 200, bitplanes=3)
display.show(screen)

def update():
    screen.clear()
    for b in balls:
        b.x += b.xs
        b.y += b.ys
        if b.x < 10.0 or b.x > 290.0:
            b.xs = -b.xs
        if b.y < 10.0 or b.y > 170.0:
            b.ys = -b.ys
        display.blit(ball_shape, int(b.x), int(b.y))

run(update, until=lambda: joy.button(0))
```

```bash
# Run directly in Python (instant preview window)
python bouncing_balls.py

# Or cross-compile and run on real Amiga hardware
amipython run bouncing_balls.py

# Package as a bootable floppy disk image
amipython adf bouncing_balls.py
```

### Display Example (Graphics)

```python
from amiga import Display, Bitmap, palette, wait_mouse

display = Display(320, 256, bitplanes=5)
bm = Bitmap(320, 256, bitplanes=5)

for i in range(32):
    palette.aga(i, i * 8, i * 8, i * 8)

for i in range(31, 0, -1):
    bm.circle_filled(160, 128, i * 4, i)

display.show(bm)
wait_mouse()
```

```bash
# Run directly in Python (instant preview window)
python examples/basic/display1.py

# Or cross-compile and run on Amiga
amipython run examples/basic/display1.py
```

Running with `python` opens a 3x-scaled preview window using pygame, with faithful OCS palette emulation (indexed colours, 12-bit depth). Click to exit. Cross-compiling with `amipython run` builds a native 68k binary and launches it in [Amiberry](docs/amiberry.md).

### Running the Tests

```bash
pytest               # all tests (excluding Docker)
pytest -m docker     # Docker cross-compilation tests only
pytest -v            # verbose output
```

### Library Usage

```python
from amipython.pipeline import transpile

c_code = transpile('''
x: int = 42
print("Hello from amipython!")
print("x squared =", x * x)
''')
print(c_code)
```

## Architecture

```
 game.py → [transpiler] → game.c → [cross-compiler] → game (68k binary) → [Amiberry/real Amiga]
                                                              ↓
                                                         game.adf (bootable floppy image)
```

The transpiler parses a Python subset and emits C89 calling the game engine API. The engine is a C library built on [ACE (Amiga C Engine)](https://github.com/AmigaPorts/ACE) handling display, Blitter, Copper, sprites, input, audio, and chip/fast RAM. See [full architecture details](docs/architecture.md).

## Python Subset

amipython scripts are valid Python — they run directly with `python game.py` using a pygame preview module. The transpiler supports a static subset designed for game logic:

| Feature | Details |
|---|---|
| **Types** | `int`, `float`, `bool`, `str` |
| **Structs** | `@dataclass` classes with typed fields (maps to C structs) |
| **Lists** | `list[T]` with `.append()`, `.remove()`, `len()`, `for item in list:` |
| **Functions** | Annotated params/return, recursion, `global` |
| **Control flow** | `if`/`elif`/`else`, `while`, `for`/`range()`, `break`, `continue` |
| **Builtins** | `print()`, `range()`, `int()`, `float()`, `abs()`, `len()` |
| **Engine** | `Display`, `Bitmap`, `Shape`, `palette`, `joy`, `run()`, `vwait()`, `rnd()` |

See [Language Subset](docs/language.md) for the full reference including type mapping, arithmetic semantics, and what's deliberately excluded.

## Implementation Phases

| Phase | Status | Scope |
|---|---|---|
| **1. Transpiler Core** | Done | `int`, `float`, `bool`, `str`, functions, control flow, `print()`, arithmetic with Python semantics |
| **2. Display + Drawing** | Done | `Display`, `Bitmap`, palette, `circle_filled`, `plot`, `clear`, `wait_mouse()`. OCS/ECS (max 5 bitplanes / 32 colours) |
| **3. Game Loop + Sprites/Bobs** | Done | `run()`, double buffering, `Shape.grab()`, `display.blit()`, `joy.button()`, `rnd()` |
| **4. Classes + Lists** | Done | `@dataclass` structs, `list[T]`, field access/mutation, list iteration, `len()`, `append()`, `remove()` |
| **5. Copper, Collision, Audio** | Planned | Per-scanline effects, hardware collision, dual playfield, Paula sound |

## Commands

```bash
# Python preview (no compilation needed)
python game.py                       # run directly with pygame preview window

# Transpile and compile
amipython transpile game.py          # Python → C
amipython build game.py              # Python → C → Amiga binary (via Docker)
amipython run game.py                # build + launch in Amiberry
amipython run --no-build game.py     # run existing binary in Amiberry

# Floppy disk image
amipython adf game.py                # build + create bootable 880KB ADF
amipython adf game.py --no-boot      # data-only disk (not bootable)
amipython adf game.py --label MyGame # custom volume label

# Setup
amipython build-ace-image            # build the ACE Docker image (one-time)
```

## Examples

29 examples across 7 categories in `examples/`:

| Category | Examples |
|---|---|
| **basic** | Minimal display, palette bars |
| **drawing** | Circles, polygons, random shapes, mouse lines |
| **animation** | Bouncing ball, double-buffered balls, QBlit queue, 3D vector stars |
| **sprites** | Hardware sprites, priority, collision |
| **scrolling** | Smooth scroll, tile scroll, dual playfield, momentum |
| **effects** | Copper gradients, starfields (horizontal + radial), pixel explosion |
| **input** | Joystick, mouse, keyboard |

All examples use `@dataclass` for data structures and `list[T]` for collections. They run with both `python game.py` (preview) and `amipython run game.py` (real Amiga).

## Documentation

| Document | Contents |
|---|---|
| [Language Subset](docs/language.md) | Supported Python features, data types, type system, engine imports |
| [Blitz Comparison](docs/blitz-comparison.md) | 12 side-by-side Blitz Basic → amipython examples, full API coverage tables |
| [Python Preview](docs/preview.md) | Running scripts directly in Python with pygame, how it works |
| [Running in Amiberry](docs/amiberry.md) | Emulator setup, Kickstart 3.1 requirement, troubleshooting |
| [Architecture](docs/architecture.md) | Build system, cross-compilation, design decisions, prior art |
| [Dev Log](docs/devlog.md) | Technical notes — problems hit, root causes, and solutions |
