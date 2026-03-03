# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**amipython** — A Python-to-Amiga game development toolchain. Transpiles a Python subset to C89, cross-compiles to native 68k Amiga executables. Inspired by the AMOS Basic / Blitz Basic model of "friendly language + purpose-built game runtime."

## Architecture

Pipeline: `game.py → amipython transpiler (Python, host) → game.c (C89) → m68k cross-compiler (vbcc/amiga-gcc) → Amiga Hunk binary → Amiberry/vamos`

Components:
1. **Transpiler** — Python program, parses Python subset, emits C89 calling game engine API
2. **Game runtime** — C library for 68k, handles Amiga hardware (built on ACE engine). Covers Blitter, Copper, sprites, tilemaps, input, audio, chip/fast RAM
3. **Asset pipeline** — PNG→bitplanes, WAV→8SVX, Tiled→Amiga tilemaps
4. **Build system** — transpile → cross-compile → link → optionally launch Amiberry
5. **Amiberry integration** — headless mode (`-G`), directory mounting (`-m`), IPC socket

## Key Design Decisions

- **C89 output** — works with vbcc (smallest binaries) and amiga-gcc; no C++ STL issues on 68k
- **No garbage collection** — static allocation + arena allocators for 512KB-2MB RAM targets
- **Custom transpiler** — game-aware builtins, chip/fast RAM control, minimal binary size
- **ACE game engine** as runtime base — [AmigaPorts/ACE](https://github.com/AmigaPorts/ACE)

## Python Subset Rules

- Implicit static typing — variables hold one type throughout lifetime
- Classes with type annotations → C structs
- `list[Type]` → typed arrays/linked lists
- No dynamic features: no eval, getattr, metaclasses, decorators, generators, closures
- No garbage collection — static allocation + arena allocators
- Game builtins (`Display`, `Sprite`, `Tilemap`, etc.) map to engine C API calls
- `run(update_fn, until=condition)` is the game loop — handles VWait, double buffer, QBlit/UnQueue

## API Design Pattern

Blitz Basic's numbered-slot model (`BitMap 0`, `Shape 0`) becomes named Python objects. The `run()` function abstracts double buffering, VWait timing, and blit queue management. See README.md for complete Blitz→amipython mapping with 12 side-by-side examples.

Key modules: `Display`, `DualPlayfield`, `Bitmap`, `Shape`, `Sprite`, `Tilemap`, `BlitQueue`, `palette`, `copper`, `collision`, `joy`, `mouse`, `key`, `sound`

## Cross-Compilation

- **vbcc** — preferred, smallest binaries. Docker: `walkero/docker4amigavbcc:latest-m68k`
- **Bebbo's amiga-gcc** — alternative, fastest code. Docker: `amigadev/crosstools:m68k-amigaos`
- **vasm** / **vlink** — assembler and linker for 68k / Amiga Hunk format

## Testing

- **vamos** (from amitools) — headless CLI binary runner, no ROM needed. Primary tool for Phase 1 CLI programs.
- **Amiberry** — full Amiga emulator (requires Kickstart ROM + Workbench). Needed for Phase 2+ when display/hardware features are used. Supports headless mode (`-G`), directory mounting (`-m`), IPC at `/tmp/amiberry.sock`.

## Implementation Phases

1. **Phase 1** — Transpiler core (done): parse Python subset, emit C89, end-to-end hello world
2. **Phase 2** — Display + drawing: Display, Bitmap, primitives, palette
3. **Phase 3** — Game loop + sprites/bobs: run(), double buffer, Shape, Sprite
4. **Phase 4** — Input + scrolling: joy, key, mouse, Tilemap
5. **Phase 5** — Copper, collision, dual playfield, audio

## Commands

```bash
amipython transpile game.py      # transpile only → game.c + amipython.h
amipython build game.py          # transpile + cross-compile via Docker → game (Amiga binary)
pytest                           # run all tests (excluding Docker cross-compilation)
pytest -m docker                 # run Docker cross-compilation test only
pytest -v                        # verbose test output
```

## vbcc Cross-Compilation Notes

- vbcc `+aos68k` does **not** define `AMIGA` — the build command passes `-DAMIGA` explicitly
- `-lmieee` (IEEE math library) is only linked when the program uses float types — its startup code breaks vamos
- On Amiga, I/O uses dos.library `Output()`/`Write()` directly (vamos-compatible); the host path uses `printf()`
- Float helper functions are guarded behind `#ifdef AMIPYTHON_USE_FLOAT` to avoid pulling in the IEEE math library for int-only programs
- Install amitools from git main: `pip install "git+https://github.com/cnvogelg/amitools.git@main#egg=amitools"` (pip release has version mismatch with machine68k)
