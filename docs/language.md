# Python Subset

amipython is not full Python. It is a restricted subset sufficient for game logic, tailored for game development and static compilation to C89.

## Supported Features

- Variables with type annotations (`x: int = 42`)
- Functions with annotated parameters and return types
- `if`/`elif`/`else`, `while`, `for i in range()`
- `break`, `continue`, `pass`
- `global` declarations
- `print()` with multiple arguments
- Basic types: `int`, `float`, `bool`, `str`
- Arithmetic with Python semantics (floor division, modulo, power)
- Boolean operators: `and`, `or`, `not`
- Comparison chaining: `a < b < c`
- `from amiga import ...` for engine types and builtins

## Planned Features

- Collections: `list` (typed, homogeneous), `tuple`
- Classes with type-annotated fields (maps to C structs)
- f-strings (limited)

## Type System

amipython uses implicit static typing — a variable holds one type throughout its lifetime. Types are inferred from assignments and annotations:

```python
x: int = 42          # explicit annotation
y = 3.14             # inferred as float
name = "hello"       # inferred as str
flag = True          # inferred as bool
```

### Type Mapping

| Python | C89 | Notes |
|---|---|---|
| `int` | `LONG` | 32-bit — vbcc's `int` is 16-bit on 68k |
| `float` | `double` | IEEE 754 double |
| `bool` | `LONG` | 0 or 1 |
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

- `eval()`, `exec()`, `getattr()`, `setattr()`
- Metaclasses, decorators, generators, closures
- `*args`, `**kwargs` (except engine constructor kwargs)
- List comprehensions, dict comprehensions
- `try`/`except`, `with`, `yield`
- `import` (except `from amiga import ...`)
- Dynamic typing, duck typing
- Garbage collection — all memory is statically allocated or arena-managed
