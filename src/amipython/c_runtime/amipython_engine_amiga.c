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
static AmipyBitmap *s_pActiveBitmap = 0;  /* user bitmap linked via show() */

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
        /* User bitmap was redirected to pBfr->pBack in display_show.
         * viewDestroy destroys pBfr->pBack, so null out user ptr to avoid double-free. */
        if (s_pActiveBitmap) {
            s_pActiveBitmap->pBitmap = 0;
        }
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
        TAG_SIMPLEBUFFER_USE_X_SCROLLING, 0,
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

static void _dirtyExpand(AmipyBitmap *bm, WORD x1, WORD y1, WORD x2, WORD y2);

void amipython_display_blit(AmipyDisplay *d, AmipyShape *shape, LONG x, LONG y) {
    if (s_pActiveBitmap && s_pActiveBitmap->pBitmap && shape->pBitmap) {
        blitWait();
        blitCopy(
            shape->pBitmap, 0, 0,
            s_pActiveBitmap->pBitmap, (WORD)x, (WORD)y,
            shape->width, shape->height,
            MINTERM_COOKIE
        );
        _dirtyExpand(s_pActiveBitmap, (WORD)x, (WORD)y,
                     (WORD)(x + (LONG)shape->width - 1),
                     (WORD)(y + (LONG)shape->height - 1));
    }
    (void)d;
}

void amipython_display_show(AmipyDisplay *d, AmipyBitmap *bm) {
    /* Track state */
    s_pActiveDisplay = d;
    s_pActiveBitmap = bm;
    _flushPendingPalette(d);

    /* Redirect user bitmap to display buffer.
     * Copy content, then point user bitmap at display's bitmap.
     * Old bitmap is leaked (TODO: fix after debugging). */
    if (bm->pBitmap && d->pBfr && d->pBfr->pBack) {
        UBYTE i;
        tBitMap *pSrc = bm->pBitmap;
        tBitMap *pDst = d->pBfr->pBack;
        ULONG ulSize = (ULONG)pDst->BytesPerRow * pDst->Rows;
        for (i = 0; i < pDst->Depth; ++i) {
            CopyMem(pSrc->Planes[i], pDst->Planes[i], ulSize);
        }
        /* Skip bitmapDestroy for now — test if it's causing the hang */
        bm->pBitmap = d->pBfr->pBack;
    }

    /* Load view + take over hardware */
    viewLoad(d->pView);
    systemUnuse();
}

static void _dirtyReset(AmipyBitmap *bm) {
    bm->dirtyX1 = (WORD)bm->width;
    bm->dirtyY1 = (WORD)bm->height;
    bm->dirtyX2 = 0;
    bm->dirtyY2 = 0;
    bm->hasDirty = 0;
}

static void _dirtyExpand(AmipyBitmap *bm, WORD x1, WORD y1, WORD x2, WORD y2) {
    if (x1 < bm->dirtyX1) bm->dirtyX1 = x1;
    if (y1 < bm->dirtyY1) bm->dirtyY1 = y1;
    if (x2 > bm->dirtyX2) bm->dirtyX2 = x2;
    if (y2 > bm->dirtyY2) bm->dirtyY2 = y2;
    bm->hasDirty = 1;
}

void amipython_bitmap_init(AmipyBitmap *bm, LONG w, LONG h, LONG bp) {
    bm->width = (UWORD)w;
    bm->height = (UWORD)h;
    bm->bitplanes = (UBYTE)bp;
    bm->pBitmap = bitmapCreate((UWORD)w, (UWORD)h, (UBYTE)bp, BMF_CLEAR);
    _dirtyReset(bm);
}

void amipython_bitmap_circle_filled(AmipyBitmap *bm, LONG cx, LONG cy, LONG r, LONG color) {
    /* Midpoint circle scanline fill using blitRect for each horizontal span.
     * Each span is a 1-pixel-high filled rectangle. */
    LONG x = 0;
    LONG y = r;
    LONG d = 1 - r;
    LONG bw = (LONG)bm->width;
    LONG bh = (LONG)bm->height;
    /* Dirty rect: bounding box of the circle, clamped to bitmap */
    {
        WORD dx1 = (WORD)(cx - r), dy1 = (WORD)(cy - r);
        WORD dx2 = (WORD)(cx + r), dy2 = (WORD)(cy + r);
        if (dx1 < 0) dx1 = 0;
        if (dy1 < 0) dy1 = 0;
        if (dx2 >= (WORD)bw) dx2 = (WORD)(bw - 1);
        if (dy2 >= (WORD)bh) dy2 = (WORD)(bh - 1);
        if (dx1 <= dx2 && dy1 <= dy2) _dirtyExpand(bm, dx1, dy1, dx2, dy2);
    }

    if (r <= 0) {
        if (cx >= 0 && cx < bw && cy >= 0 && cy < bh) {
            chunkyToPlanar((UBYTE)color, (UWORD)cx, (UWORD)cy, bm->pBitmap);
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

void amipython_bitmap_box_filled(AmipyBitmap *bm, LONG x1, LONG y1, LONG x2, LONG y2, LONG color) {
    if (bm->pBitmap && x1 <= x2 && y1 <= y2) {
        UWORD bw = (UWORD)(x2 - x1 + 1);
        UWORD bh = (UWORD)(y2 - y1 + 1);
        _dirtyExpand(bm, (WORD)x1, (WORD)y1, (WORD)x2, (WORD)y2);
        blitWait();
        blitRect(bm->pBitmap, (UWORD)x1, (UWORD)y1, bw, bh, (UBYTE)color);
    }
}

void amipython_bitmap_clear(AmipyBitmap *bm) {
    if (bm->pBitmap) {
        blitWait();
        if (bm->hasDirty) {
            /* Only clear the area that was drawn to */
            UWORD cw = (UWORD)(bm->dirtyX2 - bm->dirtyX1 + 1);
            UWORD ch = (UWORD)(bm->dirtyY2 - bm->dirtyY1 + 1);
            blitRect(bm->pBitmap, (UWORD)bm->dirtyX1, (UWORD)bm->dirtyY1, cw, ch, 0);
            _dirtyReset(bm);
        } else {
            blitRect(bm->pBitmap, 0, 0, bm->width, bm->height, 0);
        }
    }
}

void amipython_bitmap_plot(AmipyBitmap *bm, LONG x, LONG y, LONG color) {
    if (bm->pBitmap && x >= 0 && x < (LONG)bm->width
        && y >= 0 && y < (LONG)bm->height) {
        _dirtyExpand(bm, (WORD)x, (WORD)y, (WORD)x, (WORD)y);
        chunkyToPlanar((UBYTE)color, (UWORD)x, (UWORD)y, bm->pBitmap);
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

void amipython_vwait(LONG n) {
    LONG i;
    if (s_pActiveDisplay && s_pActiveDisplay->pVPort) {
        for (i = 0; i < n; i++) {
            blitWait();
            vPortWaitForEnd(s_pActiveDisplay->pVPort);
            copProcessBlocks();
        }
    }
}

void amipython_shape_grab(AmipyShape *shape, AmipyBitmap *bm, LONG x, LONG y, LONG w, LONG h) {
    /* Round width up to next multiple of 16 — blitter operates on words */
    UWORD uw = (UWORD)((w + 15) & ~15);
    UWORD uh = (UWORD)h;
    shape->width = uw;
    shape->height = uh;
    shape->bitplanes = bm->bitplanes;
    shape->pBitmap = bitmapCreate(uw, uh, bm->bitplanes, BMF_CLEAR);
    if (shape->pBitmap && bm->pBitmap) {
        blitWait();
        blitCopy(
            bm->pBitmap, (WORD)x, (WORD)y,
            shape->pBitmap, 0, 0,
            uw, uh,
            MINTERM_COOKIE
        );
    }
}

static UWORD s_uwJoyIgnoreCount = 10;  /* ignore first 10 frames (Amiberry LMB quirk) */

BOOL amipython_joy_button(LONG port) {
    mouseProcess();
    if (s_uwJoyIgnoreCount > 0) {
        s_uwJoyIgnoreCount--;
        return FALSE;
    }
    return mouseUse(MOUSE_PORT_1, MOUSE_LMB) ? TRUE : FALSE;
    (void)port;
}

LONG amipython_mouse_x(void) {
    mouseProcess();
    return (LONG)mouseGetX(MOUSE_PORT_1);
}

LONG amipython_mouse_y(void) {
    mouseProcess();
    return (LONG)mouseGetY(MOUSE_PORT_1);
}

LONG amipython_rnd(LONG n) {
    /* Simple LCG — adequate for games */
    static ULONG s_seed = 12345;
    if (n <= 0) return 0;
    s_seed = s_seed * 1103515245UL + 12345;
    return (LONG)((s_seed >> 16) % (ULONG)n);
}

static float _sin_approx(float x) {
    /* Taylor series sin(x) — 5 terms, adequate for lookup tables.
     * Normalize x to [-pi, pi] range first. */
    float x2, x3, x5, x7;
    float pi = 3.14159265f;
    /* Reduce to [-pi, pi] */
    while (x > pi) x -= 2.0f * pi;
    while (x < -pi) x += 2.0f * pi;
    x2 = x * x;
    x3 = x2 * x;
    x5 = x3 * x2;
    x7 = x5 * x2;
    return x - x3 / 6.0f + x5 / 120.0f - x7 / 5040.0f;
}

void amipython_sin_table(float *out, LONG n) {
    LONG i;
    float step = 6.28318530f / (float)n;  /* 2*pi / n */
    for (i = 0; i < n; i++) {
        out[i] = _sin_approx((float)i * step);
    }
}

void amipython_cos_table(float *out, LONG n) {
    LONG i;
    float step = 6.28318530f / (float)n;
    float half_pi = 1.57079632f;
    for (i = 0; i < n; i++) {
        out[i] = _sin_approx((float)i * step + half_pi);
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

void amipython_display_blit(AmipyDisplay *d, AmipyShape *shape, LONG x, LONG y) {
    amipython_print_str("[display] blit ");
    _print_uword(shape->width);
    amipython_print_str("x");
    _print_uword(shape->height);
    amipython_print_str(" at ");
    amipython_print_long(x);
    amipython_print_str(",");
    amipython_print_long(y);
    amipython_print_str("\n");
    (void)d;
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

void amipython_bitmap_box_filled(AmipyBitmap *bm, LONG x1, LONG y1, LONG x2, LONG y2, LONG color) {
    amipython_print_str("[bitmap] box_filled ");
    amipython_print_long(x1);
    amipython_print_str(",");
    amipython_print_long(y1);
    amipython_print_str("-");
    amipython_print_long(x2);
    amipython_print_str(",");
    amipython_print_long(y2);
    amipython_print_str(" color=");
    amipython_print_long(color);
    amipython_print_str("\n");
    (void)bm;
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

void amipython_shape_grab(AmipyShape *shape, AmipyBitmap *bm, LONG x, LONG y, LONG w, LONG h) {
    shape->width = (UWORD)w;
    shape->height = (UWORD)h;
    shape->data = 0;
    amipython_print_str("[shape] grab ");
    amipython_print_long(w);
    amipython_print_str("x");
    amipython_print_long(h);
    amipython_print_str("\n");
    (void)bm; (void)x; (void)y;
}

BOOL amipython_joy_button(LONG port) {
    amipython_print_str("[input] joy_button port=");
    amipython_print_long(port);
    amipython_print_str("\n");
    return TRUE;  /* Always TRUE so loops terminate in vamos */
}

LONG amipython_mouse_x(void) {
    amipython_print_str("[input] mouse_x\n");
    return 160;
}

LONG amipython_mouse_y(void) {
    amipython_print_str("[input] mouse_y\n");
    return 128;
}

void amipython_wait_mouse(void) {
    amipython_print_str("[input] wait_mouse\n");
}

void amipython_vwait(LONG n) {
    amipython_print_str("[input] vwait ");
    amipython_print_long(n);
    amipython_print_str("\n");
}

LONG amipython_rnd(LONG n) {
    /* Simple LCG */
    static ULONG s_seed = 12345;
    if (n <= 0) return 0;
    s_seed = s_seed * 1103515245UL + 12345;
    return (LONG)((s_seed >> 16) % (ULONG)n);
}

void amipython_sin_table(float *out, LONG n) {
    amipython_print_str("[math] sin_table ");
    amipython_print_long(n);
    amipython_print_str("\n");
    (void)out;
}

void amipython_cos_table(float *out, LONG n) {
    amipython_print_str("[math] cos_table ");
    amipython_print_long(n);
    amipython_print_str("\n");
    (void)out;
}

#endif /* ACE_ENGINE */
