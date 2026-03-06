/*
 * amipython_engine_amiga.c — Amiga engine implementations.
 *
 * ACE_ENGINE: Real graphics via ACE game engine (Bebbo GCC + CMake build).
 * Otherwise: dos.library trace stubs for vbcc/vamos testing.
 */

#include "amipython_engine.h"

#ifdef ACE_ENGINE
/* ================================================================
 * ACE-backed implementation
 * ================================================================ */

#include <ace/managers/system.h>
#include <ace/managers/memory.h>
#include <ace/managers/log.h>
#include <ace/managers/timer.h>
#include <ace/managers/blit.h>
#include <ace/managers/copper.h>
#include <ace/managers/mouse.h>
#include <ace/managers/viewport/simplebuffer.h>
#include <ace/utils/extview.h>
#include <ace/utils/bitmap.h>
#include <ace/utils/chunky.h>
#include <ace/utils/palette.h>

/* Global ACE state — the display that's currently active */
static AmipyDisplay *s_pActiveDisplay = 0;

/* Palette buffer — stores colors set before display.show() */
#define PALETTE_MAX 256
static UWORD s_pPaletteBuffer[PALETTE_MAX];
static UBYTE s_bPaletteBuffered[PALETTE_MAX];
static UBYTE s_bHasPendingPalette = 0;

void amipython_engine_create(void) {
    systemCreate();
    logOpen(0);
    memCreate();
    timerCreate();
    blitManagerCreate();
    copCreate();
    mouseCreate(MOUSE_PORT_1);
}

void amipython_engine_destroy(void) {
    if (s_pActiveDisplay && s_pActiveDisplay->pView) {
        viewLoad(0);
        systemUse();
        viewDestroy(s_pActiveDisplay->pView);
        s_pActiveDisplay->pView = 0;
        s_pActiveDisplay->pVPort = 0;
        s_pActiveDisplay->pBfr = 0;
    }
    mouseDestroy();
    copDestroy();
    blitManagerDestroy();
    timerDestroy();
    memDestroy();
    logClose();
    systemDestroy();
}

void amipython_display_init(AmipyDisplay *d, LONG w, LONG h, LONG bp) {
    d->width = (UWORD)w;
    d->height = (UWORD)h;
    d->bitplanes = (UBYTE)bp;
    d->pView = 0;
    d->pVPort = 0;
    d->pBfr = 0;

    d->pView = viewCreate(0, TAG_DONE);
    d->pVPort = vPortCreate(0,
        TAG_VPORT_VIEW, d->pView,
        TAG_VPORT_BPP, (UWORD)bp,
        TAG_VPORT_WIDTH, (UWORD)w,
        TAG_VPORT_HEIGHT, (UWORD)h,
        TAG_DONE
    );
    d->pBfr = simpleBufferCreate(0,
        TAG_SIMPLEBUFFER_VPORT, d->pVPort,
        TAG_SIMPLEBUFFER_BITMAP_FLAGS, BMF_CLEAR,
        TAG_DONE
    );
}

static void _flushPendingPalette(AmipyDisplay *d) {
    if (s_bHasPendingPalette && d->pVPort) {
        LONG maxColors = 1L << d->bitplanes;
        LONG i;
        for (i = 0; i < maxColors && i < PALETTE_MAX; i++) {
            if (s_bPaletteBuffered[i]) {
                d->pVPort->pPalette[i] = s_pPaletteBuffer[i];
                s_bPaletteBuffered[i] = 0;
            }
        }
        s_bHasPendingPalette = 0;
    }
}

void amipython_display_show(AmipyDisplay *d, AmipyBitmap *bm) {
    /* Copy the user bitmap into the display's back buffer, then activate */
    if (bm->pBitmap && d->pBfr) {
        blitCopyAligned(
            bm->pBitmap, 0, 0,
            d->pBfr->pBack, 0, 0,
            d->width, d->height
        );
    }

    /* Apply any palette entries that were buffered before display was active */
    s_pActiveDisplay = d;
    _flushPendingPalette(d);

    /* Load view THEN hand over hardware (ACE pattern) */
    viewLoad(d->pView);
    systemUnuse();

    vPortWaitForEnd(d->pVPort);
}

void amipython_bitmap_init(AmipyBitmap *bm, LONG w, LONG h, LONG bp) {
    bm->width = (UWORD)w;
    bm->height = (UWORD)h;
    bm->bitplanes = (UBYTE)bp;
    bm->pBitmap = bitmapCreate((UWORD)w, (UWORD)h, (UBYTE)bp, BMF_CLEAR);
}

void amipython_bitmap_circle_filled(AmipyBitmap *bm, LONG cx, LONG cy, LONG r, LONG color) {
    /* Midpoint circle scanline fill using blitRect for each horizontal span.
     * Each span is a 1-pixel-high filled rectangle. */
    LONG x = 0;
    LONG y = r;
    LONG d = 1 - r;
    LONG bw = (LONG)bm->width;
    LONG bh = (LONG)bm->height;

    if (r <= 0) {
        if (cx >= 0 && cx < bw && cy >= 0 && cy < bh) {
            chunkyToPlanar(bm->pBitmap, (UWORD)cx, (UWORD)cy, (UBYTE)color);
        }
        return;
    }

    while (x <= y) {
        /* Draw 4 horizontal spans covering 8 octants */
        LONG x1, x2, ty;

        /* Span at cy - y */
        x1 = cx - x; x2 = cx + x; ty = cy - y;
        if (ty >= 0 && ty < bh) {
            if (x1 < 0) x1 = 0;
            if (x2 >= bw) x2 = bw - 1;
            if (x1 <= x2)
                blitRect(bm->pBitmap, (UWORD)x1, (UWORD)ty, (UWORD)(x2 - x1 + 1), 1, (UBYTE)color);
        }
        /* Span at cy + y */
        ty = cy + y;
        if (ty >= 0 && ty < bh) {
            if (x1 < 0) x1 = 0;
            if (x2 >= bw) x2 = bw - 1;
            if (x1 <= x2)
                blitRect(bm->pBitmap, (UWORD)x1, (UWORD)ty, (UWORD)(x2 - x1 + 1), 1, (UBYTE)color);
        }
        /* Span at cy - x */
        x1 = cx - y; x2 = cx + y; ty = cy - x;
        if (ty >= 0 && ty < bh) {
            if (x1 < 0) x1 = 0;
            if (x2 >= bw) x2 = bw - 1;
            if (x1 <= x2)
                blitRect(bm->pBitmap, (UWORD)x1, (UWORD)ty, (UWORD)(x2 - x1 + 1), 1, (UBYTE)color);
        }
        /* Span at cy + x */
        ty = cy + x;
        if (ty >= 0 && ty < bh) {
            if (x1 < 0) x1 = 0;
            if (x2 >= bw) x2 = bw - 1;
            if (x1 <= x2)
                blitRect(bm->pBitmap, (UWORD)x1, (UWORD)ty, (UWORD)(x2 - x1 + 1), 1, (UBYTE)color);
        }

        if (d < 0) {
            d += 2 * x + 3;
        } else {
            d += 2 * (x - y) + 5;
            y--;
        }
        x++;
    }
}

void amipython_bitmap_clear(AmipyBitmap *bm) {
    if (bm->pBitmap) {
        blitRect(bm->pBitmap, 0, 0, bm->width, bm->height, 0);
    }
}

void amipython_bitmap_plot(AmipyBitmap *bm, LONG x, LONG y, LONG color) {
    if (bm->pBitmap && x >= 0 && x < (LONG)bm->width
        && y >= 0 && y < (LONG)bm->height) {
        chunkyToPlanar(bm->pBitmap, (UWORD)x, (UWORD)y, (UBYTE)color);
    }
}

void amipython_palette_aga(LONG reg, LONG r, LONG g, LONG b) {
    /* ACE uses OCS 12-bit palette: 0xRGB, each 4 bits.
     * Our API takes 8-bit r/g/b — downscale to 4-bit. */
    UWORD color;
    if (reg < 0 || reg >= PALETTE_MAX) return;
    color = (UWORD)(((r >> 4) & 0xF) << 8)
          | (UWORD)(((g >> 4) & 0xF) << 4)
          | (UWORD)((b >> 4) & 0xF);
    if (s_pActiveDisplay && s_pActiveDisplay->pVPort) {
        if (reg < (1L << s_pActiveDisplay->bitplanes)) {
            s_pActiveDisplay->pVPort->pPalette[reg] = color;
        }
    } else {
        /* Buffer for later application when display.show() is called */
        s_pPaletteBuffer[reg] = color;
        s_bPaletteBuffered[reg] = 1;
        s_bHasPendingPalette = 1;
    }
}

void amipython_palette_set(LONG reg, LONG r, LONG g, LONG b) {
    /* Direct OCS 4-bit values */
    UWORD color;
    if (reg < 0 || reg >= PALETTE_MAX) return;
    color = (UWORD)((r & 0xF) << 8) | (UWORD)((g & 0xF) << 4) | (UWORD)(b & 0xF);
    if (s_pActiveDisplay && s_pActiveDisplay->pVPort) {
        if (reg < (1L << s_pActiveDisplay->bitplanes)) {
            s_pActiveDisplay->pVPort->pPalette[reg] = color;
        }
    } else {
        s_pPaletteBuffer[reg] = color;
        s_bPaletteBuffered[reg] = 1;
        s_bHasPendingPalette = 1;
    }
}

void amipython_wait_mouse(void) {
    /* Poll until left mouse button is clicked */
    while (!mouseUse(MOUSE_PORT_1, MOUSE_LMB)) {
        mouseProcess();
        if (s_pActiveDisplay && s_pActiveDisplay->pVPort) {
            vPortWaitForEnd(s_pActiveDisplay->pVPort);
        }
    }
}

void amipython_vwait(void) {
    if (s_pActiveDisplay && s_pActiveDisplay->pVPort) {
        vPortWaitForEnd(s_pActiveDisplay->pVPort);
    }
}

#else
/* ================================================================
 * dos.library trace stubs (vbcc / vamos)
 * ================================================================ */

static void _print_uword(UWORD val) {
    amipython_print_long((LONG)val);
}

void amipython_display_init(AmipyDisplay *d, LONG w, LONG h, LONG bp) {
    d->width = (UWORD)w;
    d->height = (UWORD)h;
    d->bitplanes = (UBYTE)bp;
    amipython_print_str("[display] init ");
    amipython_print_long(w);
    amipython_print_str("x");
    amipython_print_long(h);
    amipython_print_str(" ");
    amipython_print_long(bp);
    amipython_print_str("bp\n");
}

void amipython_display_show(AmipyDisplay *d, AmipyBitmap *bm) {
    amipython_print_str("[display] show ");
    _print_uword(bm->width);
    amipython_print_str("x");
    _print_uword(bm->height);
    amipython_print_str(" on ");
    _print_uword(d->width);
    amipython_print_str("x");
    _print_uword(d->height);
    amipython_print_str("\n");
}

void amipython_bitmap_init(AmipyBitmap *bm, LONG w, LONG h, LONG bp) {
    bm->width = (UWORD)w;
    bm->height = (UWORD)h;
    bm->bitplanes = (UBYTE)bp;
    amipython_print_str("[bitmap] init ");
    amipython_print_long(w);
    amipython_print_str("x");
    amipython_print_long(h);
    amipython_print_str(" ");
    amipython_print_long(bp);
    amipython_print_str("bp\n");
}

void amipython_bitmap_circle_filled(AmipyBitmap *bm, LONG cx, LONG cy, LONG r, LONG color) {
    amipython_print_str("[bitmap] circle_filled ");
    amipython_print_long(cx);
    amipython_print_str(",");
    amipython_print_long(cy);
    amipython_print_str(" r=");
    amipython_print_long(r);
    amipython_print_str(" color=");
    amipython_print_long(color);
    amipython_print_str("\n");
}

void amipython_bitmap_clear(AmipyBitmap *bm) {
    amipython_print_str("[bitmap] clear ");
    _print_uword(bm->width);
    amipython_print_str("x");
    _print_uword(bm->height);
    amipython_print_str("\n");
}

void amipython_bitmap_plot(AmipyBitmap *bm, LONG x, LONG y, LONG color) {
    amipython_print_str("[bitmap] plot ");
    amipython_print_long(x);
    amipython_print_str(",");
    amipython_print_long(y);
    amipython_print_str(" color=");
    amipython_print_long(color);
    amipython_print_str("\n");
}

void amipython_palette_aga(LONG reg, LONG r, LONG g, LONG b) {
    amipython_print_str("[palette] aga ");
    amipython_print_long(reg);
    amipython_print_str(" r=");
    amipython_print_long(r);
    amipython_print_str(" g=");
    amipython_print_long(g);
    amipython_print_str(" b=");
    amipython_print_long(b);
    amipython_print_str("\n");
}

void amipython_palette_set(LONG reg, LONG r, LONG g, LONG b) {
    amipython_print_str("[palette] set ");
    amipython_print_long(reg);
    amipython_print_str(" r=");
    amipython_print_long(r);
    amipython_print_str(" g=");
    amipython_print_long(g);
    amipython_print_str(" b=");
    amipython_print_long(b);
    amipython_print_str("\n");
}

void amipython_wait_mouse(void) {
    amipython_print_str("[input] wait_mouse\n");
}

void amipython_vwait(void) {
    amipython_print_str("[input] vwait\n");
}

#endif /* ACE_ENGINE */
