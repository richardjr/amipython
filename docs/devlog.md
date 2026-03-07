# Development Log

Technical notes from building amipython — problems hit, root causes found, and solutions applied. Intended as a reference for future development.

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
