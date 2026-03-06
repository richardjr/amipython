# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**amipython** — A Python-to-Amiga game development toolchain. Transpiles a Python subset to C89, cross-compiles to native 68k Amiga executables. Scripts also run directly in Python via a pygame-based preview module. Inspired by the AMOS Basic / Blitz Basic model of "friendly language + purpose-built game runtime."

## Architecture

Two paths from the same source:

```
game.py → python game.py          → pygame preview window (instant, for development)
game.py → amipython transpile     → game.c → cross-compile → Amiga Hunk binary → Amiberry
```

Components:
1. **Transpiler** (`src/amipython/`) — Python program, parses Python subset, emits C89 calling game engine API
2. **Game runtime** (`src/amipython/c_runtime/`) — C library for 68k, handles Amiga hardware (built on ACE engine)
3. **Python preview** (`src/amiga/`) — pygame-ce implementation of the same engine API, for running scripts natively in Python
4. **Build system** — transpile → cross-compile → link → optionally launch Amiberry
5. **Amiberry integration** (`src/amipython/amiberry.py`) — minimal boot, KS 3.1, headless mode (`-G`)

## Feature Implementation Rules

**When implementing any new engine feature, ALL THREE must be updated together:**

1. **C runtime** (`src/amipython/c_runtime/amipython_engine_amiga.c` + `_host.c` + `.h`) — the real Amiga implementation (ACE) and host test stubs
2. **Python preview** (`src/amiga/`) — the pygame-based implementation so `python game.py` works
3. **Engine registry** (`src/amipython/engine.py`) — type definitions the transpiler uses to validate and emit code
4. **Transpiler** (`src/amipython/typecheck.py`, `emit.py`, `validate.py`) — if new syntax/patterns are needed
5. **Documentation** (`docs/language.md`) — update the supported features table
6. **Tests** — transpiler tests, host compilation tests, and preview module tests

These must all stay in sync. A feature is not done until it works in all three paths: transpilation, C runtime, and Python preview.

## Key Design Decisions

- **C89 output** — works with vbcc (smallest binaries) and amiga-gcc; no C++ STL issues on 68k
- **No garbage collection** — static allocation + arena allocators for 512KB-2MB RAM targets
- **Custom transpiler** — game-aware builtins, chip/fast RAM control, minimal binary size
- **ACE game engine** as runtime base — [AmigaPorts/ACE](https://github.com/AmigaPorts/ACE)
- **OCS/ECS only** — max 5 bitplanes (32 colours), 12-bit palette. No AGA.
- **Kickstart 3.1 required** — ACE crashes under KS 3.2
- **pygame-ce for preview** — 8-bit indexed surfaces match Amiga's indexed colour hardware

## Python Subset Rules

- Implicit static typing — variables hold one type throughout lifetime
- Classes with type annotations → C structs
- `list[Type]` → typed arrays/linked lists
- No dynamic features: no eval, getattr, metaclasses, decorators, generators, closures
- No garbage collection — static allocation + arena allocators
- Game builtins (`Display`, `Sprite`, `Tilemap`, etc.) map to engine C API calls
- `from amiga import ...` — the only allowed import
- `run(update_fn, until=condition)` is the game loop — handles VWait, double buffer, QBlit/UnQueue

## API Design Pattern

Blitz Basic's numbered-slot model (`BitMap 0`, `Shape 0`) becomes named Python objects. The `run()` function abstracts double buffering, VWait timing, and blit queue management. See `docs/blitz-comparison.md` for 12 side-by-side examples.

Key modules: `Display`, `DualPlayfield`, `Bitmap`, `Shape`, `Sprite`, `Tilemap`, `BlitQueue`, `palette`, `copper`, `collision`, `joy`, `mouse`, `key`, `sound`

## Project Structure

```
src/
  amipython/              # Transpiler + build system
    cli.py                # CLI commands (transpile, build, run, build-ace-image)
    pipeline.py           # Transpile pipeline
    validate.py           # AST validator
    typecheck.py          # Type checker
    emit.py               # C code emitter
    engine.py             # Engine type registry (Display, Bitmap, palette, etc.)
    types.py              # Type system
    docker.py             # Docker cross-compilation
    amiberry.py           # Amiberry launcher
    c_runtime/            # C headers and implementations
      amipython.h         # Core runtime (print, math, types)
      amipython_engine.h  # Engine struct definitions + function declarations
      amipython_engine_amiga.c  # Real ACE implementation + vbcc trace stubs
      amipython_engine_host.c   # Host gcc printf trace stubs
  amiga/                  # Python preview module (pygame-ce)
    __init__.py           # Public API exports
    _backend.py           # Pygame singleton (window, palette, events, clock)
    _bitmap.py            # Bitmap with 8-bit indexed surface
    _display.py           # Display — lazy window on show()
    _palette.py           # OCS 12-bit palette emulation
    _builtins.py          # wait_mouse(), vwait()
    _constants.py         # PAL_FPS, MAX_PALETTE, DEFAULT_SCALE
examples/                 # Example scripts (runnable with both python and amipython)
  basic/                  # Simple display, palette
  drawing/                # Drawing primitives
  animation/              # Bobs, double buffering
  sprites/                # Hardware sprites
  scrolling/              # Scrolling, tilemaps, dual playfield
  effects/                # Copper, starfields, particles
  input/                  # Joystick, mouse, keyboard
docs/                     # Documentation
  preview.md              # Python preview setup and usage
  language.md             # Supported Python subset, type system, engine imports
  blitz-comparison.md     # 12 side-by-side Blitz→amipython examples + feature tables
  amiberry.md             # Emulator setup, KS 3.1 requirement, troubleshooting
  architecture.md         # Design decisions, cross-compilation, prior art
docker/                   # Docker build files
  Dockerfile.ace          # Bebbo's GCC + ACE engine image
  patch_ace.py            # Patches ACE for CLI launch compatibility
amiberry_boot/            # Minimal Amiga boot drive (no Workbench)
  S/Startup-Sequence      # Dynamically written by amipython run
```

## Cross-Compilation

- **vbcc** — for non-engine CLI programs. Docker: `walkero/docker4amigavbcc:latest-m68k`
- **Bebbo's amiga-gcc + ACE** — for engine (graphics) programs. Docker: `amipython-ace` (built with `amipython build-ace-image`)
- Auto-detection: checks for `#include "amipython_engine.h"` to select build path

## Commands

```bash
python game.py                       # run with pygame preview (instant)
amipython transpile game.py          # transpile only → game.c + headers
amipython build game.py              # transpile + cross-compile via Docker
amipython run game.py                # build + launch in Amiberry
amipython run --no-build game.py     # run existing binary in Amiberry
amipython build-ace-image            # build the ACE Docker image (one-time)
pytest                               # all tests (excluding Docker)
pytest -m docker                     # Docker cross-compilation tests only
```

## Implementation Phases

1. **Phase 1** — Transpiler core (done): parse Python subset, emit C89, end-to-end hello world
2. **Phase 2** — Display + drawing (done): Display, Bitmap, primitives, palette, Python preview module
3. **Phase 3** — Game loop + sprites/bobs: run(), double buffer, Shape, Sprite
4. **Phase 4** — Input + scrolling: joy, key, mouse, Tilemap
5. **Phase 5** — Copper, collision, dual playfield, audio

## vbcc Cross-Compilation Notes

- vbcc `+aos68k` does **not** define `AMIGA` — the build command passes `-DAMIGA` explicitly
- `-lmieee` (IEEE math library) is only linked when the program uses float types — its startup code breaks vamos
- On Amiga, I/O uses dos.library `Output()`/`Write()` directly (vamos-compatible); the host path uses `printf()`
- Float helper functions are guarded behind `#ifdef AMIPYTHON_USE_FLOAT` to avoid pulling in the IEEE math library for int-only programs
- Install amitools from git main: `pip install "git+https://github.com/cnvogelg/amitools.git@main#egg=amitools"` (pip release has version mismatch with machine68k)
