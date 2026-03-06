# amipython

A Python-to-Amiga game development toolchain. Write games in a Python subset, compile to native 68k Amiga executables.

## Concept

amipython follows the model proven by AMOS Basic and Blitz Basic — a high-level language paired with a purpose-built game runtime. Instead of BASIC, the authoring language is a restricted subset of Python. Instead of an interpreter running on the Amiga, code is cross-compiled to native 68k executables on a modern Linux host.

The goal: a Python developer can write Amiga games without learning 68k assembly, Copper lists, or Blitter registers. The transpiler and runtime handle all hardware complexity.

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
pip install -e ".[dev]"
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
# Build and run in Amiberry (one step)
amipython run examples/basic/display1.py
```

This produces greyscale concentric circles on a 32-colour OCS display. See [Running in Amiberry](docs/amiberry.md) for setup.

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
 game.py → [transpiler] → game.c → [cross-compiler] → game (68k binary) → [Amiberry/vamos]
```

The transpiler parses a Python subset and emits C89 calling the game engine API. The engine is a C library built on [ACE (Amiga C Engine)](https://github.com/AmigaPorts/ACE) handling display, Blitter, Copper, sprites, input, audio, and chip/fast RAM. See [full architecture details](docs/architecture.md).

## Implementation Phases

| Phase | Status | Scope |
|---|---|---|
| **1. Transpiler Core** | Done | `int`, `float`, `bool`, `str`, functions, control flow, `print()`, arithmetic with Python semantics |
| **2. Display + Drawing** | Done | `Display`, `Bitmap`, palette, `circle_filled`, `plot`, `clear`, `wait_mouse()`. OCS/ECS (max 5 bitplanes / 32 colours) |
| **3. Game Loop + Sprites/Bobs** | Planned | `run()`, double buffering, `Shape`, `Sprite`, blitting |
| **4. Input + Scrolling** | Planned | `joy`, `key`, `mouse`, `Tilemap` |
| **5. Copper, Collision, Audio** | Planned | Per-scanline effects, hardware collision, dual playfield, Paula sound |

## Commands

```bash
amipython transpile game.py          # Python → C
amipython build game.py              # Python → C → Amiga binary (via Docker)
amipython run game.py                # build + launch in Amiberry
amipython run --no-build game.py     # run existing binary in Amiberry
amipython build-ace-image            # build the ACE Docker image (one-time)
```

## Documentation

| Document | Contents |
|---|---|
| [Language Subset](docs/language.md) | Supported Python features, type system, engine imports |
| [Blitz Comparison](docs/blitz-comparison.md) | 12 side-by-side Blitz Basic → amipython examples, full API coverage tables |
| [Running in Amiberry](docs/amiberry.md) | Emulator setup, Kickstart 3.1 requirement, troubleshooting |
| [Architecture](docs/architecture.md) | Build system, cross-compilation, design decisions, prior art |
