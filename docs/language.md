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
| `list[T]` | Fixed-capacity array | Max 64 elements. T can be int, float, bool, or dataclass |

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
- Maximum 64 elements per list
- `for item in list:` gives a pointer for struct lists (mutations persist)
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

### Engine Modules

Singleton modules like `palette` are called directly:

```python
palette.aga(0, 255, 0, 0)     # 8-bit RGB, downscaled to OCS 12-bit
palette.set(0, 15, 0, 0)      # direct OCS 4-bit values
```

### Engine Builtins

Top-level functions from the engine:

```python
wait_mouse()    # wait for left mouse button click
vwait()         # wait for vertical blank
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
