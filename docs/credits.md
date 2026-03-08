# Credits and Sources

This document credits all third-party code, assets, tools, and references used in the amipython project.

## Core Dependencies

### ACE (Amiga C Engine)
- **Source:** [AmigaPorts/ACE](https://github.com/AmigaPorts/ACE)
- **License:** Mozilla Public License 2.0
- **Usage:** Game engine runtime for display management, Blitter, Copper, input, audio, memory management. Built into the `amipython-ace` Docker image.

### ptplayer (ProTracker Replay Routine)
- **Author:** Frank Wille
- **Source:** Integrated into ACE as `ace/managers/ptplayer.h`
- **License:** MPL 2.0 (as part of ACE)
- **Original:** ProTracker V2.3B Playroutine Version 6.3, originally written in 68k assembly (2013, 2016-2023), rewritten for ACE in C.
- **Usage:** CIA-B interrupt-driven MOD music playback on Amiga hardware.

### Bebbo's amiga-gcc
- **Source:** [codeberg.org/bebbo/amiga-gcc](https://codeberg.org/bebbo/amiga-gcc)
- **License:** GPL (GCC)
- **Usage:** Cross-compiler for m68k-amigaos targets. Used in the Docker build image.

### vbcc / vasm / vlink
- **Source:** [sun.hasenbraten.de/vbcc](http://sun.hasenbraten.de/vbcc/)
- **Author:** Volker Barthelmann (vbcc), Frank Wille (vasm/vlink)
- **Usage:** Alternative C compiler suite for Amiga. Used for non-engine CLI programs.

### pygame-ce
- **Source:** [pygame-ce/pygame-ce](https://github.com/pygame-ce/pygame-ce)
- **License:** LGPL v2.1
- **Usage:** Python preview module rendering and MOD playback via SDL2/SDL_mixer.

### Amiberry
- **Source:** [BlitterStudio/amiberry](https://github.com/BlitterStudio/amiberry)
- **License:** GPL v3
- **Usage:** Amiga emulator for testing compiled binaries.

### amitools / vamos
- **Source:** [cnvogelg/amitools](https://github.com/cnvogelg/amitools)
- **License:** GPL v2
- **Usage:** Headless AmigaOS API emulation for CLI program testing.

### Pillow (PIL)
- **Source:** [python-pillow/Pillow](https://github.com/python-pillow/Pillow)
- **License:** HPND (Historical Permission Notice and Disclaimer)
- **Usage:** PNG image loading and indexed-colour conversion in the asset pipeline.

## Assets

### Demo MOD File (`examples/demo/data/demo.mod`, `examples/sound/data/demo.mod`)
- **Title:** "monday"
- **Format:** ProTracker 31-sample M.K. format, 4 channels, 8 patterns
- **Source:** [steffest/BassoonTracker](https://github.com/steffest/BassoonTracker) demo modules collection
- **Repository License:** MIT (BassoonTracker source code)
- **Music License:** The MOD file itself is a composition from the Amiga demoscene. Individual track licensing is not formally stated, which is typical of tracker music distributed within the scene community. Used here for development and demonstration purposes.
- **Note:** For redistribution, consider replacing with a CC0-licensed composition or an original work.

### Logo Image (`examples/demo/data/logo.png`)
- **Description:** amipython project logo, 192x56, 3 bitplanes (8 colours)
- **Created for:** This project
- **License:** Part of the amipython project

## Reference Projects

These projects were studied for design patterns and architectural decisions:

| Project | URL | Relevance |
|---|---|---|
| AMOS Basic / Blitz Basic | Historical | "Friendly language + game runtime" model |
| AmiBlitz3 | [github.com/AmiBlitz/AmiBlitz3](https://github.com/AmiBlitz/AmiBlitz3) | Blitz Basic successor, source of reference examples |
| Shed Skin | [github.com/shedskin/shedskin](https://github.com/shedskin/shedskin) | Python-to-C++ compiler, type inference patterns |
| Prometeo | [github.com/zanellia/prometeo](https://github.com/zanellia/prometeo) | Python-to-C transpiler with deterministic memory |
| AmigaPython | [github.com/amigazen/amigapython](https://github.com/amigazen/amigapython) | CPython 2.7 port to Amiga |
| MicroPython Amiga | [github.com/jyoberle/micropython-amiga](https://github.com/jyoberle/micropython-amiga) | Lightweight Python interpreter for 68k |
| BassoonTracker | [github.com/steffest/BassoonTracker](https://github.com/steffest/BassoonTracker) | Web MOD tracker, demo MOD files |

## Format References

### ProTracker MOD Format
- **Reference:** [Noisetracker/Soundtracker/Protracker Module Format](https://greg-kennedy.com/tracker/modformat.html)
- **Usage:** `_modCreateFromMem()` in `amipython_engine_amiga.c` parses MOD files from embedded byte arrays. The 31-sample M.K. format layout:
  - Bytes 0-19: Song name
  - Bytes 20-949: 31 sample headers (30 bytes each)
  - Byte 950: Song length, Byte 951: Restart position
  - Bytes 952-1079: Pattern arrangement (128 entries)
  - Bytes 1080-1083: "M.K." format tag
  - Bytes 1084+: Pattern data (N * 1024 bytes), then sample PCM data

### ACE Bitmap Format (.bm)
- **Reference:** ACE source code (`ace/utils/bitmap.h`)
- **Usage:** Asset pipeline converts PNG to planar .bm format at transpile time, or embeds directly as C arrays.
