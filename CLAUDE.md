# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project notes

Planning, open tasks, decisions, and meeting notes live in the Obsidian vault:
`/home/richard/Work/projects/projects/amipython/amipython.md`

**Claude: read that file at the start of a session for current status and open tasks.** See `/home/richard/Work/projects/CLAUDE.md` for vault conventions.

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

Key modules: `Display`, `Bitmap`, `Shape`, `Sprite`, `Tilemap`, `palette`, `joy`, `mouse`, `collision`, `music`. Planned: `DualPlayfield` (full), `copper`, `key`, `BlitQueue`.

**Asset pipeline.** `Shape.load(path)` and `Bitmap.load(path)` accept PNG / IFF ILBM. At transpile time `assets.py` collects the asset paths from the generated C, converts them to ACE's planar `.bm` format (with colour-0-keyed masks where applicable), and copies them into the build directory. Music loaded via `music.load(path)` is embedded the same way as a raw MOD byte buffer. ADF output (`amipython adf`) packages the binary plus all `data/` files into a bootable 880KB FFS image via amitools `xdftool` (see `adf.py`).

## Project Structure

```
src/
  amipython/                      # Transpiler + build system
    __main__.py                   # `python -m amipython` entry point
    cli.py                        # Click CLI (transpile, build, run, adf, build-ace-image)
    pipeline.py                   # Orchestrates parse → validate → typecheck → emit → assets
    parse.py                      # Thin wrapper around ast.parse with ParseError reporting
    validate.py                   # AST validator — rejects unsupported Python features
    typecheck.py                  # Type checker — implicit static typing, struct/list inference
    emit.py                       # C89 code emitter
    engine.py                     # Engine type registry (Display, Bitmap, Shape, Sprite, Tilemap, palette, joy, mouse, music, collision, builtins)
    types.py                      # AmipyType enum + VariableInfo / StructInfo
    errors.py                     # Exception types (ParseError, ValidationError, TypeCheckError, EmitError, BuildError)
    assets.py                     # PNG/IFF → ACE .bm planar bitmap conversion + mask generation
    adf.py                        # 880KB ADF floppy image creation via amitools xdftool
    docker.py                     # Docker cross-compilation orchestration (vbcc and ACE images)
    amiberry.py                   # Amiberry launcher — generates .uae config, mounts binary dir
    c_runtime/                    # C headers and implementations (copied beside generated .c)
      amipython.h                 # Core runtime (print, math, types, list helpers)
      amipython_engine.h          # Engine struct definitions + function declarations
      amipython_engine_amiga.c    # Real ACE implementation (built into Amiga binary)
      amipython_engine_host.c     # Host gcc printf trace stubs (used by host compile tests)
      CMakeLists.txt              # ACE build config (copied beside generated .c for Docker build)
  amiga/                          # Python preview module (pygame-ce)
    __init__.py                   # Public API exports — what `from amiga import ...` resolves to
    _backend.py                   # Pygame singleton (window, palette, events, 50fps clock, sprite/tilemap registry)
    _bitmap.py                    # Bitmap with 8-bit indexed surface, drawing primitives, Bitmap.load()
    _display.py                   # Display — lazy window on show(), blit, sprites_behind
    _palette.py                   # OCS 12-bit palette emulation (.aga / .set / .fade)
    _shape.py                     # Shape — grab/load, transparent index 0 for blits
    _sprite.py                    # Sprite — hardware sprite emulation (.grab/.show/.move)
    _tilemap.py                   # Tilemap — tile-based scrolling display, blocking tiles, pending blits
    _joy.py                       # Joystick — button/left/right/up/down (port 0 mouse, port 1 keyboard)
    _mouse.py                     # Mouse — x/y position, set_pointer for sprite-attached cursor
    _collision.py                 # Collision detection — playfield colour register/check
    _music.py                     # ProTracker MOD playback via pygame.mixer (load/play/stop/volume)
    _builtins.py                  # wait_mouse(), vwait(n), rnd(n), run(update, until=), sin_table, cos_table
    _constants.py                 # PAL_FPS=50, MAX_PALETTE=256, DEFAULT_SCALE=3
examples/                         # Example scripts (runnable with both `python` and `amipython`)
  hello.py                        # CLI hello world (Phase 1 — vbcc/vamos path, no engine)
  basic/                          # display1, minimal_display, palette_bars
  drawing/                        # mouse_lines, polygon, random_circles
  animation/                      # bouncing_ball, bouncing_blits, doublebuffer_balls, qblit_balls, orbiting_ball, vector_stars_3d, bounce_int
  sprites/                        # sprite_move, sprite_priority, sprite_collision
  scrolling/                      # smooth_scroll, momentum_scroll, tilemap_scroll, tile_scroll_doublebuffer, dual_playfield, dual_playfield_auto
  effects/                        # copper_gradient, copper_lines, triple_layer_copper, starfield_horizontal, starfield_radial, pixel_explosion, equaliser
  input/                          # joystick_mouse, keyboard_status, keyboard_typing
  palette/                        # fade
  sound/                          # music (MOD playback via ptplayer / pygame.mixer)
  demo/                           # amipython_demo, logo, logo_grab, starfield_nologo, generate_assets — combined showpiece + asset generation script
docs/                             # Documentation
  preview.md                      # Python preview setup, usage, supported API table, palette fidelity
  language.md                     # Supported Python subset, data types, engine imports, builtins
  blitz-comparison.md             # 12 side-by-side Blitz Basic → amipython examples + full feature coverage tables
  amiberry.md                     # Emulator setup, KS 3.1 requirement, ADF flow, troubleshooting
  architecture.md                 # Build system, cross-compilation paths, design decisions, prior art
  credits.md                      # Acknowledgements for ACE, ptplayer, GCC/vbcc, demo MOD/logo assets
  devlog.md                       # Dated technical notes — problems hit, root causes, and solutions
docker/                           # Docker build files
  Dockerfile.ace                  # Bebbo's GCC + ACE engine image (`amipython-ace`)
  patch_ace.py                    # Patches ACE source: removes `_ace_dbg`, guards `_WBenchMsg` NULL deref
amiberry/                         # Sample Amiberry config (reference)
  example.uae                     # Example UAE config showing the layout `amipython run` generates
amiberry_boot/                    # Minimal Amiga boot drive (no Workbench)
  S/Startup-Sequence              # Dynamically written by `amipython run` to launch the binary
tests/                            # Pytest suite
  fixtures/                       # Reference Python sources + expected C output (hello, arithmetic, control_flow, functions, display1)
  test_validate.py                # Validator (accepts/rejects Python features)
  test_typecheck.py               # Type checker (inference, structs, lists)
  test_emit.py                    # C emitter (golden output comparisons)
  test_engine.py                  # Engine registry consistency
  test_pipeline.py                # End-to-end transpile pipeline
  test_assets.py                  # PNG → ACE .bm conversion
  test_adf.py                     # ADF floppy image creation
  test_compile_host.py            # Host gcc compile of generated C (default test target)
  test_compile_amiga.py           # Docker cross-compile via vbcc / ACE (marker: `pytest -m docker`)
  test_amiga_preview.py           # Pygame preview module behaviour
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
amipython adf game.py                # build + package into bootable game.adf
amipython adf --run game.py          # build + create ADF + boot in Amiberry
amipython adf --no-boot game.py      # non-bootable data disk
amipython adf --label MyGame game.py # custom volume label
amipython build-ace-image            # build the ACE Docker image (one-time)
pytest                               # all tests (excluding Docker)
pytest -m docker                     # Docker cross-compilation tests only
```

## Implementation Phases

1. **Phase 1** — Transpiler core (done): parse Python subset, emit C89, end-to-end hello world via vbcc/vamos
2. **Phase 2** — Display + drawing (done): `Display`, `Bitmap`, primitives, palette, Python preview module
3. **Phase 3** — Game loop + sprites/bobs (done): `run()`, double buffer, `Shape.grab/load`, `display.blit`, `joy.button`, `rnd`
4. **Phase 4** — Classes + lists + scrolling (done): `@dataclass` structs, `list[T]`, field access, iteration, `len`, `append`, `remove`, `sin_table`, `cos_table`, `box_filled`, ADF floppy output, `Tilemap`, sprite collision
5. **Phase 5A** — Image/asset loading (done): `Shape.load("data/x.png")`, `Bitmap.load(...)`, PNG/IFF → ACE `.bm` at build time, mask auto-generated from colour 0
6. **Phase 5B** — Music (done): `music.load/play/stop/volume`, MOD embedded at transpile time, ACE ptplayer + pygame.mixer
7. **Phase 5 (remaining)** — Copper effects (per-scanline palette), full dual playfield, keyboard input

## vbcc Cross-Compilation Notes

- vbcc `+aos68k` does **not** define `AMIGA` — the build command passes `-DAMIGA` explicitly
- `-lmieee` (IEEE math library) is only linked when the program uses float types — its startup code breaks vamos
- On Amiga, I/O uses dos.library `Output()`/`Write()` directly (vamos-compatible); the host path uses `printf()`
- Float helper functions are guarded behind `#ifdef AMIPYTHON_USE_FLOAT` to avoid pulling in the IEEE math library for int-only programs
- Install amitools from git main: `pip install "git+https://github.com/cnvogelg/amitools.git@main#egg=amitools"` (pip release has version mismatch with machine68k)
