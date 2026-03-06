# Architecture

```
 game.py (Python subset game script)
     |
     v
 [amipython transpiler]  — Python, runs on host
     |
     v
 game.c (generated C89 calling engine API)  +  engine (Amiga game runtime)
     |
     v
 [m68k cross-compiler]  — vbcc or Bebbo's amiga-gcc
     |
     v
 game (native Amiga Hunk executable)
     |
     v
 [Amiberry / vamos]  — run and test
```

## Components

1. **amipython transpiler** — A Python program that parses a Python subset and emits C89 code calling the game engine API. Runs on the development host (Linux).

2. **Game runtime / engine** — A C library compiled for 68k that handles all Amiga hardware interaction: screen setup, Copper lists, Blitter, sprites, bobs, tilemaps, double-buffering, input, Paula sound, memory management (chip/fast RAM). Built on top of [ACE (Amiga C Engine)](https://github.com/AmigaPorts/ACE).

3. **Asset pipeline** — Converts modern asset formats to Amiga-native formats: PNG to bitplane sprites, WAV to 8SVX audio, Tiled maps to Amiga tilemap format.

4. **Build system** — Orchestrates the full pipeline: transpile → cross-compile → link → optionally launch Amiberry for testing.

5. **Amiberry integration** — Headless emulator configuration with mounted build output directory for instant test runs.

## Cross-Compilation Toolchain

### Compiler Options

- **vbcc** — Lightweight C89 compiler producing the smallest binaries. C only. Docker: `walkero/docker4amigavbcc:latest-m68k`. Used for non-engine (CLI) programs.
- **Bebbo's amiga-gcc** — GCC fork for m68k-amigaos. C and C++. Fastest code. Docker: `amigadev/crosstools:m68k-amigaos`. Used for engine (graphics) programs via the `amipython-ace` Docker image.

### Build Paths

The build system auto-detects which path to use based on whether the generated C includes engine headers:

- **CLI programs** (Phase 1): vbcc via `walkero/docker4amigavbcc:latest-m68k`
- **Engine programs** (Phase 2+): Bebbo's GCC + CMake + ACE via `amipython-ace` (custom Docker image built with `amipython build-ace-image`)

### Assembler and Linker

- **vasm** — Cross-assembler, DevPac-compatible (`vasmm68k_mot`).
- **vlink** — Cross-linker producing Amiga Hunk-format executables.

### Testing Tools

- **Amiberry** — Full Amiga emulator. Used via `amipython run` which generates a config, mounts the binary, and launches headless (`-G`). Required for display/graphics programs. See [Running in Amiberry](amiberry.md).
- **vamos** — Headless AmigaOS API emulator from [amitools](https://github.com/cnvogelg/amitools). No Kickstart ROM required. CLI-only programs (Phase 1).

## Design Decisions

### Why a custom transpiler instead of Shed Skin / RPython?

| Concern | General transpiler | Custom amipython |
|---|---|---|
| Output language | C++17 (Shed Skin) or verbose C (RPython) | Clean C89 — works with vbcc |
| Runtime overhead | Boehm GC or RPython GC | None — static/arena allocation |
| Game awareness | None — no concept of sprites, screens, sound | First-class game primitives |
| Binary size | Large (STL, GC runtime) | Minimal — only what's used |
| Memory model | Heap with GC | Explicit chip RAM / fast RAM control |
| Generated code quality | Machine-generated, hard to inspect | Readable, optimizable C89 |

### Why C89 target?

- vbcc (the best Amiga C compiler for binary size) supports C89 with partial C99
- No C++ standard library needed — eliminates STL portability issues on 68k
- Simpler generated code, easier to audit and hand-optimize if needed

### Why ACE as the game engine base?

[ACE (Amiga C Engine)](https://github.com/AmigaPorts/ACE) is an actively maintained C game framework that handles display management, Blitter, Copper, tilemaps, input, audio, and chip/fast RAM allocation. ACE targets OCS/ECS compatibility (max 5 bitplanes / 32 colours). It requires Kickstart 3.1 — KS 3.2 is not compatible.

## Prior Art and References

- **AMOS Basic / Blitz Basic** — Proved the "friendly language + game runtime" model on Amiga
- **ACE** — [AmigaPorts/ACE](https://github.com/AmigaPorts/ACE) — Modern C game engine for Amiga
- **Shed Skin** — [shedskin/shedskin](https://github.com/shedskin/shedskin) — Python-subset-to-C++ compiler (reference for type inference)
- **Prometeo** — [zanellia/prometeo](https://github.com/zanellia/prometeo) — Python-to-C transpiler with deterministic memory
- **AmigaPython** — [amigazen/amigapython](https://github.com/amigazen/amigapython) — CPython 2.7 port to Amiga
- **MicroPython Amiga** — [jyoberle/micropython-amiga](https://github.com/jyoberle/micropython-amiga) — Lightweight Python interpreter for 68k
- **Bebbo's amiga-gcc** — [codeberg.org/bebbo/amiga-gcc](https://codeberg.org/bebbo/amiga-gcc) — GCC cross-compiler for m68k-amigaos
- **vbcc/vasm/vlink** — [sun.hasenbraten.de/vbcc](http://sun.hasenbraten.de/vbcc/) — Amiga C compiler suite
- **Amiberry** — [BlitterStudio/amiberry](https://github.com/BlitterStudio/amiberry) — Amiga emulator with IPC/headless support
- **amitools/vamos** — [cnvogelg/amitools](https://github.com/cnvogelg/amitools) — Headless Amiga binary runner
- **AmiBlitz3** — [AmiBlitz/AmiBlitz3](https://github.com/AmiBlitz/AmiBlitz3) — Blitz Basic successor, source of reference examples
