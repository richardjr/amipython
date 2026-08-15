# Development Log

Technical notes from building amipython — problems hit, root causes found, and solutions applied. Intended as a reference for future development.

## 2026-08-15: Condensed 6x8 font, and storage calls after display.show() hung the Amiga

**Font.** UI-heavy games run out of room at 40 columns. Added a second built-in
font — 5×7 glyphs in a 6×8 cell (53 columns) — selected per bitmap with
`bm.font(6)` / `bm.font(8)`; it applies to every subsequent `print_at` /
`print_centered` / `print_right` (including the gap between variadic pieces),
so no print signature changed. Glyph data lives once in `src/amiga/_font6.py`;
`scripts/gen_font6.py` writes the C table between FONT6 markers in
`amipython_engine_amiga.c`; a test keeps them byte-identical. The C renderer
was generalised to a cell width (`bm->fontWidth`, 0/8 = default) — the erase
rect, the solid block, the row masks and the advance all use it. The preview
had a second, duplicated glyph loop in `print_at` that ignored the font; it now
shares `_render_pieces` (a refactor briefly ate `Bitmap.load`'s
`@staticmethod` — regression test added).

**Write-protected saves.** `storage.save_*` now asks `Info()` for PROGDIR:'s
`id_DiskState` first and silently skips the write when the volume is
write-protected — closes the 2026-04-27 TODO (the ADF flow was verified
booting a game to its title screen).

**Storage hang.** `storage.exists/load/save` call dos.library. Every previous
game did that *before* `display.show()`; a title screen that probes for a
save file *after* the display is up (i.e. after ACE's `systemUnuse()`) hung
the emulator on a black screen — the OS is suspended, so `Open()` never
returns. Fix in the runtime: the DOS-requester bracket that already wraps
every storage call now also does `systemUse()` … `systemUnuse()` when the
system is currently taken over (ACE's sanctioned way to do mid-game file
I/O; the screen may blink for a frame). `storage.exists` also called `Close()`
*after* the restore — reordered. So mid-game saving/loading works now; the
2026-04-27 write-protected-floppy freeze is a separate, still-open issue.

## 2026-08-15: Phase 6 Stage 0 — multi-module, sized lists, by-ref params, --out, masked blits

Driven by a much larger game than the examples (see the vault: amipython ADR
0004). Everything below landed together (386 tests, +22; Docker vbcc + ACE
paths re-verified; Amiberry runs of a 320×256 blit stress).

**Transpiler:**
- **Multi-module programs** (`modules.py`). `from <mod> import a, b` / `*` of a
  sibling `.py` is parsed once and spliced ahead of the importer in
  dependency order; the local import statement is dropped; the C is one unit.
  Enforced: unique top-level names across modules, no rebinding of an
  imported name (`global X` or module-level `X = ...` — Python would make a
  module-local copy while the C shares one variable), imported names must
  exist, no aliases / plain `import` / relative / circular imports. Each
  module's AST is `ast.increment_lineno`'d by 1,000,000 × index so any later
  error's `lineno` decodes to `file:line` (`AmipythonError` gained `filename`
  and `with_location()`; `pipeline.transpile` does the decode).
- **Sized list literals** `xs: list[int] = [0] * N` (also `[""] * N`,
  `[False] * N`, `[1.5] * N`, and unannotated). `N` is const-folded from int
  literals and module-level int constants (`_collect_const_ints`: names bound
  exactly once, at module level, to an int constant expression; recorded on
  `TypeInfo.const_ints`). Sets `list_capacity = max(256, N)` and emits a fill
  loop + `count = N` at the assignment site, so `[0] * (W * H)` grids and
  re-assignment-to-reset both work. Struct lists still use `.append()`.
- **`list[str]`** turned out to work already (`const char *x_items[N]`); now
  documented and tested as string/name tables.
- **Struct and engine-object parameters by reference.** Struct params used to
  crash the emitter (`KeyError: STRUCT` in `_var_decl`); engine-object params
  were passed by value. Both now emit pointer params (`Merc *m`,
  `AmipyBitmap *b`), `is_ref=True` locals (so `->` field access and
  `_obj_addr` method calls just work), and call sites pass `&x` /
  `&xs_items[i]` — or the pointer itself for loop refs and params
  (`_emit_arg` → `_addr`). Typecheck verifies the struct *name* matches and
  the argument is addressable (no `hurt(Merc(...))`). Side fix: `for s in
  shapes: display.blit(s, ...)` used to emit `&s` for an already-pointer loop
  var.

**CLI:** `--out DIR` on transpile/build/run/adf — generated C, headers,
converted assets, binary and .adf land in DIR (Amiberry mounts it as `Run:`).
Build/run/adf share one `_build()` helper. Docker containers now run as the
invoking user (`--user uid:gid`), so build outputs are user-owned and the
CMake build tree can actually be removed (it used to be left root-owned).

**C runtime:**
- **`display.blit` is now a cookie-cut bob** (colour 0 transparent via the
  shape's 1-plane mask, `blitCopyMask`) — the docs always claimed this but the
  runtime and preview were opaque copies. New **`display.block`** is the
  opaque copy (Blitz `Block`), cheaper and right for tiles. Both **clip** to
  the bitmap (vertical exact; a shape hanging off the left edge is clipped in
  16-px steps because the blitter's mask/source pointers must stay
  word-aligned; right edge exact). Preview mirrors via `set_colorkey(0)`.
- **`shape_grab` built the mask on the CPU before the blitter had finished
  copying the shape** — no `blitWait()` between `blitCopy` and
  `_generateShapeMask`. Masks were never used by `display.blit` before, so it
  went unnoticed. Fixed.
- **The old "display height 256 crashes bobs near y≈220" note is resolved**: it
  was an unclipped blit past the bottom of the framebuffer. A 320×256 stress
  (42 masked + opaque 16×16 blits per frame, positions from −12 to the far
  edges, 4 bpl) runs at full 50 fps for minutes on Amiberry with the clipping
  in place. Lesson learnt writing that test: random cookie-cut rings *accumulate*
  — after a few thousand blits the screen is a solid block of ring colour, which
  looks exactly like a corruption bug and isn't one.

**Docs/examples:** `docs/language.md` (Functions, sized lists, string tables,
Multi-module programs, blit/block), `examples/basic/multi_module/` (three
modules exercising all of the above on a 320×256 display).

**Font gap (2026-08-15):** the built-in 8×8 font had blank glyphs for `< > ' ; @ $ % &`
(a menu cursor `>` and apostrophes rendered as nothing on the Amiga; the
preview font lacked them too). Filled in both, with a parity test.

**Same-day follow-ups from the game's Stage 1:** struct field defaults may be
module-level int constants (`hp: int = PLAYER_HP` — folded by `const_int`);
`xs[i].field = v` / `-= v` on struct lists type-checks (the emitter already
handled the target); `[-1] * N` sized literals (Python parses `-1` as a
UnaryOp — folded to a Constant in `sized_list_literal`).

## 2026-08-14: Hardening round — silent wrong-C emission and C-runtime robustness

A code-review sweep found four ways the transpiler emitted wrong C with no
Python-level error, plus several C-runtime traps. All fixed in one pass
(342 tests, +11 regression tests):

**Transpiler:**
- **Annotated assignments bypassed constructor dispatch.** `bm: Bitmap = Bitmap(...)`
  emitted literal Python into the C file — `_emit_ann_assign` had none of
  `_emit_assign`'s engine/static/struct/trig special cases. Now delegates to
  the same path via a synthesized `ast.Assign`.
- **Emit-time variable lookup ignored function scope.** `_get_var_info` scanned
  *every* function's locals in insertion order, so `p` being a loop-ref
  (pointer) in one function made an unrelated value-struct `p` elsewhere emit
  `p->x`. The emitter now tracks `_current_function` and resolves
  current-scope-then-globals only.
- **Required kwargs silently dropped.** Registry kwargs with a `None` default
  (copper.color_at, collision.register) were skipped when missing, shifting
  later args into the wrong C parameter slots. Now a TypeCheckError (plus an
  EmitError backstop).
- **`_collect_for_idx_vars` didn't recurse into `range()` loops** — a list loop
  nested inside `for i in range(n)` produced an undeclared `_idx` C89 variable.
- Typed errors replace crashes for `Shape()`/`Sprite()` direct construction and
  `list[T]` function parameters; `-> None` return annotations are now accepted.
- **`music.load`/`sfx.load` that can't embed are transpile errors.** The
  path-based runtime calls are no-ops on Amiga (no disk loading), so falling
  back to them just produced silence on hardware.

**C runtime:**
- **Second `display.show()` destroyed the live framebuffer** — the redirect
  logic blitted pBack onto itself then `bitmapDestroy`ed it. Now guarded by
  `bm->pBitmap != pBfr->pBack`. `systemUnuse`/`systemUse` are balanced via a
  flag (each show-path used to unuse unconditionally).
- **`engine_destroy` only tore down one display kind** (if/else-if) — now
  independent ifs with a single give-back-to-OS prologue, and the
  `s_pActive*` globals are reset.
- **`box_filled` and `print_at`'s erase pass had no clipping** — negative
  coordinates cast to UWORD wrap to ~65535 and blit outside the allocation
  (clear_rect/copy_from already clipped). `shape_grab` similarly clamps the
  word-aligned grab rect to the source bitmap now.
- **Asset reload leaked chip RAM** — shape re-grab/re-load, bitmap re-load and
  sprite re-grab now free the previous tBitMap/mask first (guarded so the
  display's own framebuffer is never destroyed; emitter zero-inits
  engine-object stack locals so the previous-pointer checks are safe).
- `copper.color_at` validates register 0..31 / scanline 0..255 (out-of-range
  MOVEs would hit unrelated custom registers); preview mirrors the guard.
- `_loadBitmapAsset` rejects paths that would overflow its 128-byte buffer;
  load failures now leave the target struct intact instead of half-written.
- `docker/patch_ace.py` verifies each patch applied and exits non-zero on a
  pattern mismatch (upstream `_ace_dbg` removal is recognised as fine) — an
  upstream ACE change can no longer silently reintroduce the CLI crash.

## 2026-04-27: TODO — `storage.save_*` freezes on write-protected disk under Amiberry

**Status:** Open. Workaround in place (save call commented out in `examples/amitetris/amitetris.py`).

**Symptom:** When the bootable ADF is write-protected (the normal state for a real Amiga floppy and the default for Amiberry), reaching `storage.save_int_list("scores", ...)` at game-over freezes the game. Removing the save call eliminates the hang. Load on startup is unaffected.

**Suspected cause:** `Open(path, MODE_NEWFILE)` against `PROGDIR:` on a write-protected volume triggers DOS's "Volume X is write protected" system requester, which has no window to attach to (ACE has taken over the display) and blocks the calling task indefinitely.

**Attempted fix that did NOT work:** Setting `pr_WindowPtr = (APTR)-1L` on the current `struct Process` for the duration of the file I/O — the standard Amiga technique for suppressing system requesters. Wrapped all five `amipython_storage_*` functions (`amipython_engine_amiga.c`). Game still freezes. So either the requester isn't the actual cause, or `pr_WindowPtr` suppression doesn't apply to this code path under Amiberry.

**Next things to try:**
- Confirm what's actually blocking — add a `kPrintF` / log trace immediately before and after `Open(MODE_NEWFILE)` to see whether `Open()` itself blocks or returns and we hang later.
- Check the disk's write-protect state up front via `Lock()` + `Info()` (`id_DiskState == ID_WRITE_PROTECTED`) and short-circuit before calling `Open()`.
- Try `pr_WindowPtr = NULL` instead of `-1` (some sources disagree on which value suppresses requesters vs. defaulting to the WB screen).
- Check whether ACE's `systemUnuse()` leaves DOS in a state where it can't service file I/O at all on this filesystem layer — if so, the storage API simply can't work mid-game and we'd need to defer writes to engine-shutdown time, or copy the save file off `PROGDIR:` (e.g. to `RAM:`) and let a wrapper script copy it back when the game exits.
- Investigate whether Amiberry-specific ADF mounting differs from a real OFS/FFS write-protected floppy in how it surfaces the error.

**Files involved:** `src/amipython/c_runtime/amipython_engine_amiga.c` (storage section), `examples/amitetris/amitetris.py` (currently has save commented out).

---

## 2025-03-08: ProTracker MOD playback via ptplayer

**Feature:** `music.load()` / `music.play()` / `music.stop()` / `music.volume()` — background music playback.

**Key decision — embed MOD at transpile time:** Same pattern as images. File I/O doesn't work on Amiberry after ACE's `systemCreate()` takes over the hardware. The MOD file bytes are emitted as a `static const UBYTE[]` C array and parsed from memory at runtime.

**Custom `_modCreateFromMem()` loader:** ACE's ptplayer only has `ptplayerModCreateFromPath()` (file I/O). We needed to parse a MOD from an in-memory buffer. The loader:
1. Scans the 128-byte arrangement to find the highest pattern number
2. Allocates chip RAM for pattern data via `memAllocChip()` and copies from the embedded buffer
3. Allocates chip RAM for each of the 31 samples and copies sample PCM data
4. Fills the `tPtplayerMod` struct (which has the same 1084-byte header layout as the MOD file)
5. Sets `isOwningSamples = 1` so `ptplayerModDestroy()` frees the chip RAM

**ACE struct detail:** The `tPtplayerMod` struct uses `pSampleStarts` (not `pSamples`) and the array type is `UWORD *[31]`, not `BYTE *`. The `ulPatternsSize` field must be set for proper cleanup.

**ptplayer lifecycle:** `ptplayerCreate(1)` (PAL) in `engine_create()`, `ptplayerStop()` + `ptplayerModDestroy()` + `ptplayerDestroy()` in `engine_destroy()`. The ptplayer must be destroyed before the view/copper/blitter teardown.

**Files:** `engine.py`, `emit.py` (_embed_music), `amipython_engine.h`, `amipython_engine_amiga.c`, `amipython_engine_host.c`, `src/amiga/_music.py`, `docs/language.md`, `docs/credits.md`

---

## 2025-03-07: Orbiting ball invisible — three blitter issues

**Problem:** The orbiting ball animation (pre-computed sin/cos trig tables, integer math, clear+blit per frame) ran without crashing but showed a completely black screen. The bouncing ball example worked fine with the same C runtime.

**Root cause (three issues found via systematic isolation):**

1. **Shape width must be word-aligned.** The Amiga blitter operates on 16-bit words. A shape created with non-aligned width (e.g., 24 pixels) silently produced garbage or invisible blits. The bouncing ball used 16×16 (already aligned), so it worked.

2. **`blitCopy` from small source bitmap fails with `MINTERM_COOKIE`.** Grabbing a shape from a small temporary bitmap (e.g., `Bitmap(24, 24)`) via `blitCopy` produced empty shape data — the circle pixels weren't copied. Drawing on the main display bitmap `bm` and grabbing from there worked correctly.

3. **`shape_grab` missing `blitWait()`.** The `blitCopy` in `shape_grab` ran immediately after `circle_filled` scanline blits without waiting for the blitter to finish, potentially reading incomplete data.

**Diagnosis approach:** Created increasingly minimal test programs, comparing each variable against the working bouncing ball. The breakthrough was adding a blue background (`palette.set(0, 0, 0, 15)`) to make the display visible — this revealed the ball was being drawn as a *black* circle (empty shape data), not missing entirely. Testing with 16×16 vs 24×24 shapes confirmed the alignment issue. Testing `tmp` bitmap vs `bm` bitmap confirmed the small-source-bitmap issue.

**Fixes:**

1. `shape_grab()` rounds width to next 16-pixel boundary:
   ```c
   UWORD uw = (UWORD)((w + 15) & ~15);
   ```

2. Updated orbiting ball example to draw on `bm` (the display bitmap) and grab from there, matching the proven bouncing ball pattern:
   ```python
   bm = Bitmap(320, 200, bitplanes=3)
   bm.circle_filled(8, 8, 7, 1)
   ball = Shape.grab(bm, 0, 0, 16, 16)
   bm.clear()
   ```

3. Added `blitWait()` before the `blitCopy` in `shape_grab()`.

4. Added `_dirtyExpand()` call in `display_blit()` so dirty rect tracking works for blit operations, not just drawing primitives. Requires a forward declaration since `_dirtyExpand` is defined later in the file.

**Files changed:** `amipython_engine_amiga.c` (shape_grab alignment + blitWait, display_blit dirty tracking), `examples/animation/orbiting_ball.py` (use display bitmap for shape drawing).

**Lesson:** On the Amiga blitter, always use 16-pixel-aligned widths. When debugging invisible graphics, add a contrasting background colour to distinguish "not drawing" from "drawing in colour 0".

---

## 2025-03-07: Display tearing at top of screen

**Problem:** The bouncing ball animation showed visual artifacts at the top of the screen — the ball would disappear and horizontal lines were visible when it moved near y=0.

**Root cause:** Single-buffered display with full-screen blitter clear. The game loop was:

```
update()  -> bitmap_clear() clears entire 320x200x3bp (24KB through blitter)
           -> circle_filled() redraws ball
vwait()   -> waits for beam to reach bottom
```

The PAL vblank period is ~1.4ms (25 lines at 64us each). Clearing 24KB through the blitter takes ~3.4ms — more than double the vblank time. The display beam wraps to the top and starts scanning while the clear is still in progress, showing black where the ball should be.

**Fix (three changes):**

1. **Reorder the game loop** — `vwait()` before `update()`, so drawing starts immediately after vblank when the beam is at the bottom, maximizing time before it wraps to the top:
   ```
   vwait()   -> blitWait, wait for beam, update copper
   update()  -> clear + redraw (starts during vblank)
   ```

2. **Add `blitWait()` in `amipython_vwait()`** before `vPortWaitForEnd()` — ensures all blits from the current frame complete before we sync to the display.

3. **Dirty rect clearing** — `bitmap_clear()` now only erases the bounding box of what was actually drawn, tracked via `dirtyX1/Y1/X2/Y2` fields on `AmipyBitmap`. For a radius-8 circle, this clears ~17x17 pixels instead of 320x200 — a 99% reduction in blitter work, easily fitting within vblank.

**Files changed:** `emit.py` (loop order), `amipython_engine.h` (dirty rect fields), `amipython_engine_amiga.c` (dirty tracking + clear logic).

---

## 2025-03-07: ACE `systemUnuse()` deadlock on Amiberry

**Problem:** Every ACE program hung indefinitely at `systemUnuse()` when running under Amiberry. The display would appear but the program would freeze before entering the game loop. This affected ALL programs, not just ones with extra allocations.

**Root cause:** ACE's `_ace_dbg()` function (compiled into all builds, not just debug) opened `SYS:ace_debug.log` with `MODE_NEWFILE` on every call:

```c
static void _ace_dbg(const char *msg) {
    BPTR fh = Open("SYS:ace_debug.log", 1006);
    if(fh) { Seek(fh,0,1); Write(fh,(APTR)msg,strlen(msg)); Close(fh); }
}
```

On Amiberry's virtual filesystem, this file I/O keeps `DMAF_DISK` (bit 4) active in the hardware DMA control register. When `systemUnuse()` checks `g_pCustom->dmaconr & DMAF_DISK`, it sees disk DMA active and calls `systemFlushIo()`, which sends an `ACTION_FLUSH` packet to the filesystem handler via `DoPkt()` and does `WaitPort()`. The filesystem handler deadlocks because it's still processing the `_ace_dbg` I/O.

The call chain: `systemUnuse()` → `_ace_dbg("su:enter")` (opens file, activates DMAF_DISK) → checks `dmaconr` (sees DMAF_DISK set) → `systemFlushIo()` → `DoPkt(ACTION_FLUSH)` → `WaitPort()` → hang.

**Fix:** Latest ACE from GitHub (main branch) removed `_ace_dbg` entirely. Rebuilt the `amipython-ace` Docker image from latest source. Additionally, `docker/patch_ace.py` patches `_ace_dbg` to a no-op as a defensive measure for older ACE versions:

```python
code = code.replace(
    'static void _ace_dbg(const char *msg) {\n'
    '\tBPTR fh = Open("SYS:ace_debug.log", 1006);\n'
    '\tif(fh) { Seek(fh,0,1); Write(fh,(APTR)msg,strlen(msg)); Close(fh); }\n'
    '}',
    'static void _ace_dbg(const char *msg) { (void)msg; }'
)
```

**Debugging journey:** This took multiple sessions to identify. Early hypotheses included `bitmapCreate()` allocations, copper list corruption, and `systemFlushIo` itself. The breakthrough came from reading ACE's `system.c` source in the Docker container and tracing the `_ace_dbg` calls through `systemUnuse()`. The DMACONR value `0x23d0` confirmed DMAF_DISK was set.

**Lesson:** Always check what file I/O happens before `systemUnuse()`. On emulators with virtual filesystems, disk DMA may behave differently than real hardware.

---

## 2025-03-07: Amiberry LMB startup quirk

**Problem:** `joy.button(0)` (mapped to left mouse button via ACE's `mouseUse`) returned TRUE immediately when the program started in Amiberry, causing game loops with `until=lambda: joy.button(0)` to exit on the first frame.

**Root cause:** Amiberry reports the left mouse button as pressed during the first few frames after startup, likely related to the emulator window gaining focus.

**Fix:** `amipython_joy_button()` ignores the first 10 frames before checking actual input:

```c
static UWORD s_uwJoyIgnoreCount = 10;
BOOL amipython_joy_button(LONG port) {
    mouseProcess();
    if (s_uwJoyIgnoreCount > 0) { s_uwJoyIgnoreCount--; return FALSE; }
    return mouseUse(MOUSE_PORT_1, MOUSE_LMB) ? TRUE : FALSE;
}
```

---

## 2025-03-06: ACE bitmap redirect pattern

**Problem:** Copying the user's bitmap to the display buffer every frame is too expensive. A 320x200x3bp bitmap copy takes significant time and doubles memory usage.

**Solution:** `display_show()` copies the initial bitmap content to the display's SimpleBuffer back buffer, then redirects the user's `AmipyBitmap.pBitmap` pointer to `pBfr->pBack`. All subsequent drawing operations (circle_filled, clear, plot) go directly to the displayed surface with no per-frame copy.

`engine_destroy()` nulls the redirected pointer before `viewDestroy()` frees the buffer, preventing a double-free.

```c
void amipython_display_show(AmipyDisplay *d, AmipyBitmap *bm) {
    /* Copy initial content */
    CopyMem(pSrc->Planes[i], pDst->Planes[i], ulSize);
    /* Redirect — all future drawing goes to display buffer */
    bm->pBitmap = d->pBfr->pBack;
    viewLoad(d->pView);
    systemUnuse();
}
```

---

## 2025-03-06: ACE palette must be set before `viewLoad()`

**Problem:** Palette colours set via `amipython_palette_set()` before `display.show()` weren't visible. The display appeared with default (black) colours.

**Root cause:** ACE's copper list is built from `vPort->pPalette` when `viewLoad()` is called. Colours set on the palette array after `viewLoad()` aren't visible until `copProcessBlocks()` runs.

**Fix:** Buffer palette values before the display is created. `_flushPendingPalette()` copies buffered colours to `vPort->pPalette` just before `viewLoad()`:

```c
static UWORD s_pPaletteBuffer[256];
static UBYTE s_bPaletteBuffered[256];

void amipython_palette_set(LONG reg, LONG r, LONG g, LONG b) {
    if (s_pActiveDisplay && s_pActiveDisplay->pVPort) {
        s_pActiveDisplay->pVPort->pPalette[reg] = color;  /* direct */
    } else {
        s_pPaletteBuffer[reg] = color;  /* buffer for later */
        s_bPaletteBuffered[reg] = 1;
    }
}
```

---

## 2025-03-05: vbcc float linking breaks vamos

**Problem:** Programs using float types crashed immediately when run under vamos (Amiga OS emulator for testing).

**Root cause:** vbcc's `-lmieee` links IEEE math startup code that calls `OpenLibrary("mathieeesingbas.library")`. vamos doesn't provide this library, causing a NULL pointer crash.

**Fix:** Only link `-lmieee` when the generated C code contains `AMIPYTHON_USE_FLOAT`. Integer-only programs skip it entirely. The `#define AMIPYTHON_USE_FLOAT` is emitted by the transpiler only when float variables are detected.

---

## 2025-03-05: Bebbo GCC soft-float and `-lm`

**Problem:** Programs using float types crashed on Amiga when linked with `-lm` (standard math library).

**Root cause:** Bebbo's amiga-gcc soft-float delegates ALL float operations to Amiga math libraries. `-lm` pulls in double-precision functions requiring `mathieeedoubbas.library`, which is NOT in the Kickstart 3.1 ROM — it's a disk-based library that requires a full Workbench installation.

**Fix:** Extract only single-precision `.o` files from libc.a into a custom `libsfloat.a`. The needed objects (`__addsf3`, `__subsf3`, `__mulsf3`, `__divsf3`, `__negsf2`, `__eqsf2`, `__fixsfsi`, `__floatsisf`) only reference `MathIeeeSingBasBase`, which IS in the KS 3.1 ROM:

```cmake
# CMakeLists.txt — extract single-precision float objects
foreach(OBJ __addsf3 __subsf3 __mulsf3 __divsf3 __negsf2 __eqsf2 __fixsfsi __floatsisf)
    execute_process(COMMAND ar x ${LIBC_PATH} ${OBJ}.o WORKING_DIRECTORY ${SFLOAT_DIR})
endforeach()
execute_process(COMMAND ar rcs libsfloat.a ... WORKING_DIRECTORY ${SFLOAT_DIR})
```

---

## 2025-03-04: ACE SimpleBuffer X-scrolling offset

**Problem:** Display showed garbled graphics — bitplane data was offset horizontally, producing vertical stripe artifacts.

**Root cause:** ACE's SimpleBuffer with X-scrolling enabled applies a bitplane pointer offset for smooth scrolling. When the scroll position is 0, the offset should be zero, but the buffer is still allocated wider than the visible area to accommodate scrolling.

**Fix:** Disable X-scrolling when not needed:

```c
d->pBfr = simpleBufferCreate(0,
    TAG_SIMPLEBUFFER_VPORT, d->pVPort,
    TAG_SIMPLEBUFFER_BITMAP_FLAGS, BMF_CLEAR,
    TAG_SIMPLEBUFFER_USE_X_SCROLLING, 0,  /* crucial */
    TAG_DONE
);
```

---

## 2025-03-04: ACE `_WBenchMsg` NULL dereference from CLI

**Problem:** ACE programs crashed immediately when launched from CLI (Startup-Sequence) instead of Workbench.

**Root cause:** ACE's `systemCreate()` does `CurrentDir(_WBenchMsg->sm_ArgList[0].wa_Lock)` unconditionally. When launched from CLI, `_WBenchMsg` is NULL.

**Fix:** `docker/patch_ace.py` wraps the dereference in a NULL guard:

```python
code = code.replace(
    's_bpStartLock = CurrentDir(_WBenchMsg->sm_ArgList[0].wa_Lock);',
    'if(_WBenchMsg) { s_bpStartLock = CurrentDir(_WBenchMsg->sm_ArgList[0].wa_Lock); }'
)
```
