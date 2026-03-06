# Running in Amiberry

amipython programs that use display/graphics (Phase 2+) need to run in a full Amiga emulator. [Amiberry](https://github.com/BlitterStudio/amiberry) is the recommended emulator.

## Requirements

- **Amiberry** installed and in your `PATH` (tested with v7.1.1)
- **Kickstart 3.1 ROM** (A1200, rev 40.68) — you must legally own this ROM. KS 3.2 is **not compatible** with ACE programs.
- No Workbench installation needed — amipython uses a minimal boot drive

## Quick Start

```bash
# Build and run in one step
amipython run examples/basic/display1.py

# Or build separately and then run
amipython build examples/basic/display1.py
amipython run --no-build examples/basic/display1.py
```

## Kickstart 3.1 Requirement

The ACE game engine (which amipython uses for graphics) is **incompatible with Kickstart 3.2**. ACE's `systemCreate()` crashes under KS 3.2 due to internal API differences. Kickstart 3.1 (rev 40.68) is the correct ROM for ACE-based programs.

## Directory Setup

amipython expects the Kickstart ROM at:

```
~/Emulation/ROMs/Kickstart v3.1 rev 40.68 (1993)(Commodore)(A1200).rom
```

If your ROM is in a different location, you can symlink it or modify `src/amipython/amiberry.py`.

## How It Works

The `amipython run` command:

1. Transpiles your Python to C
2. Cross-compiles to a native 68k Amiga Hunk binary (via Docker)
3. Generates a temporary `.uae` config that:
   - Boots from a minimal drive (no Workbench) with just a `Startup-Sequence`
   - Mounts the binary's directory as `Run:`
   - The startup-sequence runs `Run:your_binary` directly
4. Launches Amiberry in headless mode (`-G` flag, skips the GUI config screen)

### Minimal Boot

amipython ships with a minimal boot drive at `amiberry_boot/`. This directory contains only a `S/Startup-Sequence` file — no Workbench, no system utilities. The startup-sequence is dynamically written each time to run the target binary.

This approach avoids all Workbench compatibility issues. ACE programs take over the hardware directly and don't need an operating system environment.

### Emulator Configuration

The generated `.uae` config sets up:

- **CPU**: 68020 (A1200 compatible)
- **Chipset**: AGA
- **Chip RAM**: 2MB
- **Motherboard RAM**: 128MB (for development comfort)
- **Display**: 720x568, SDL2, hardware rendering
- **Boot**: DH0 = minimal boot drive, DH1 = binary directory
- **No floppies**, no Workbench

## OCS/ECS Only (No AGA)

Despite the AGA chipset setting in the emulator config, ACE targets OCS/ECS chipset compatibility. This means:

- **Maximum 5 bitplanes** (32 colours) — 6+ bitplanes will crash
- **12-bit palette** — `palette.set(reg, r, g, b)` takes 4-bit values (0-15), `palette.aga(reg, r, g, b)` takes 8-bit values (0-255) but downscales to 4-bit internally
- No HAM, no 256-colour modes
- Programs will run on A500, A600, A1200, and A4000 in OCS mode

## Example Amiberry Config

An example `.uae` config is provided at `amiberry/example.uae`. This shows the settings amipython uses. You can load this in Amiberry's GUI to inspect or modify settings:

```bash
# Launch with the example config
amiberry -G -f amiberry/example.uae
```

Before using, edit the file to set your ROM path and directory paths.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Black screen, hangs | Kickstart 3.2 ROM | Use Kickstart 3.1 (rev 40.68) |
| Crash on startup | 6+ bitplanes requested | Use max 5 bitplanes |
| `LoadModule` error at boot | Workbench 3.2 boot disk with KS 3.1 | Don't use Workbench — amipython's minimal boot handles everything |
| Nothing visible | Drawing with color 0 (background) | Set palette colors and use non-zero color indices |
| Amiberry not found | Not in PATH | Install Amiberry and ensure `amiberry` is on your PATH |
| Mouse click doesn't exit | `wait_mouse()` waits for LMB | Click the left mouse button inside the emulator window |
