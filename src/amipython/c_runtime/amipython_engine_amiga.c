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

static void _dirtyReset(AmipyBitmap *bm);
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
     * Use blitCopy (not CopyMem) — handles different bitmap formats
     * (e.g. interleaved SimpleBuffer vs non-interleaved user bitmap). */
    if (bm->pBitmap && d->pBfr && d->pBfr->pBack) {
        blitWait();
        blitCopy(
            bm->pBitmap, 0, 0,
            d->pBfr->pBack, 0, 0,
            bm->width, bm->height,
            MINTERM_COOKIE
        );
        bm->pBitmap = d->pBfr->pBack;
        _dirtyReset(bm);
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
        blitWait();
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

static AmipySprite *s_pPointerSprite = 0;

void amipython_mouse_set_pointer(AmipySprite *sprite) {
    s_pPointerSprite = sprite;
    /* Disable all sprite DMA to hide the system mouse pointer.
     * DMACON at 0xDFF096: writing without SETCLR (bit 15) clears bits.
     * Bit 5 = sprite DMA enable. */
    *((volatile UWORD *)0xDFF096) = 0x0020;
}

void amipython_sprite_grab(AmipySprite *sprite, AmipyBitmap *bm, LONG x, LONG y, LONG w, LONG h) {
    UWORD uw = (UWORD)((w + 15) & ~15);
    UWORD uh = (UWORD)h;
    sprite->width = uw;
    sprite->height = uh;
    sprite->bitplanes = bm->bitplanes;
    sprite->ubChannel = 0;
    sprite->bCollided = 0;
    sprite->pBitmap = bitmapCreate(uw, uh, bm->bitplanes, BMF_CLEAR);
    if (sprite->pBitmap && bm->pBitmap) {
        blitWait();
        blitCopy(
            bm->pBitmap, (WORD)x, (WORD)y,
            sprite->pBitmap, 0, 0,
            uw, uh,
            MINTERM_COOKIE
        );
    }
}

void amipython_sprite_show(AmipySprite *sprite, LONG x, LONG y, LONG channel) {
    /* TODO: Use ACE sprite manager or direct copper/DMA */
    sprite->ubChannel = (UBYTE)channel;
    (void)x; (void)y;
}

BOOL amipython_sprite_collided(AmipySprite *sprite) {
    return sprite->bCollided ? TRUE : FALSE;
}

static LONG s_coll_color = 0;
static LONG s_coll_mask = 0;

void amipython_collision_register(LONG color, LONG mask) {
    s_coll_color = color;
    s_coll_mask = mask;
}

static UBYTE _readPixel(tBitMap *pBm, UWORD uwX, UWORD uwY) {
    /* Read a chunky pixel value from a planar bitmap */
    UWORD uwOffset = uwY * pBm->BytesPerRow + (uwX >> 3);
    UBYTE ubBit = 0x80 >> (uwX & 7);
    UBYTE color = 0;
    UBYTE i;
    for (i = 0; i < pBm->Depth; i++) {
        if (pBm->Planes[i][uwOffset] & ubBit) {
            color |= (1 << i);
        }
    }
    return color;
}

void amipython_collision_check(void) {
    /* Software collision: check if pointer sprite area overlaps
     * registered collision color on the active bitmap. */
    LONG mx, my;
    if (!s_pPointerSprite || !s_pActiveBitmap || !s_pActiveBitmap->pBitmap) return;
    s_pPointerSprite->bCollided = 0;
    blitWait();
    mouseProcess();
    mx = (LONG)mouseGetX(MOUSE_PORT_1);
    my = (LONG)mouseGetY(MOUSE_PORT_1);
    /* Check a small area around the mouse position */
    if (mx >= 0 && mx < (LONG)s_pActiveBitmap->width
        && my >= 0 && my < (LONG)s_pActiveBitmap->height) {
        if (_readPixel(s_pActiveBitmap->pBitmap, (UWORD)mx, (UWORD)my) == (UBYTE)s_coll_color) {
            s_pPointerSprite->bCollided = 1;
        }
    }
}

void amipython_bitmap_line(AmipyBitmap *bm, LONG x1, LONG y1, LONG x2, LONG y2, LONG color) {
    LONG bw = (LONG)bm->width, bh = (LONG)bm->height;
    if (!bm->pBitmap) return;
    {
        WORD d1 = (WORD)(x1 < x2 ? x1 : x2);
        WORD d2 = (WORD)(y1 < y2 ? y1 : y2);
        WORD d3 = (WORD)(x1 > x2 ? x1 : x2);
        WORD d4 = (WORD)(y1 > y2 ? y1 : y2);
        if (d1 < 0) d1 = 0; if (d2 < 0) d2 = 0;
        if (d3 >= (WORD)bw) d3 = (WORD)(bw-1);
        if (d4 >= (WORD)bh) d4 = (WORD)(bh-1);
        _dirtyExpand(bm, d1, d2, d3, d4);
    }
    blitWait();
    /* Optimise horizontal and vertical lines using blitRect */
    if (y1 == y2) {
        /* Horizontal line */
        LONG lx = x1 < x2 ? x1 : x2;
        LONG rx = x1 > x2 ? x1 : x2;
        if (lx < 0) lx = 0;
        if (rx >= bw) rx = bw - 1;
        if (y1 >= 0 && y1 < bh && lx <= rx) {
            blitRect(bm->pBitmap, (UWORD)lx, (UWORD)y1, (UWORD)(rx - lx + 1), 1, (UBYTE)color);
        }
    } else if (x1 == x2) {
        /* Vertical line */
        LONG ty = y1 < y2 ? y1 : y2;
        LONG by = y1 > y2 ? y1 : y2;
        if (ty < 0) ty = 0;
        if (by >= bh) by = bh - 1;
        if (x1 >= 0 && x1 < bw && ty <= by) {
            blitRect(bm->pBitmap, (UWORD)x1, (UWORD)ty, 1, (UWORD)(by - ty + 1), (UBYTE)color);
        }
    } else {
        /* General Bresenham */
        LONG dx, dy, sx, sy, err, e2;
        dx = x2 - x1; if (dx < 0) dx = -dx;
        dy = y2 - y1; if (dy < 0) dy = -dy;
        sx = x1 < x2 ? 1 : -1;
        sy = y1 < y2 ? 1 : -1;
        err = dx - dy;
        for (;;) {
            if (x1 >= 0 && x1 < bw && y1 >= 0 && y1 < bh) {
                chunkyToPlanar((UBYTE)color, (UWORD)x1, (UWORD)y1, bm->pBitmap);
            }
            if (x1 == x2 && y1 == y2) break;
            e2 = 2 * err;
            if (e2 > -dy) { err -= dy; x1 += sx; }
            if (e2 < dx)  { err += dx; y1 += sy; }
        }
    }
}

/* 8x8 bitmap font — printable ASCII subset (A-Z, 0-9, punctuation, space) */
static const UBYTE s_font8x8[][8] = {
    /* 0x20 ' ' */ {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    /* 0x21 '!' */ {0x18,0x18,0x18,0x18,0x18,0x00,0x18,0x00},
    /* 0x22 '"' */ {0x6C,0x6C,0x00,0x00,0x00,0x00,0x00,0x00},
    /* 0x23 '#' */ {0x6C,0xFE,0x6C,0x6C,0xFE,0x6C,0x00,0x00},
    /* 0x24 '$' */ {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    /* 0x25 '%' */ {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    /* 0x26 '&' */ {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    /* 0x27 ''' */ {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    /* 0x28 '(' */ {0x0C,0x18,0x30,0x30,0x30,0x18,0x0C,0x00},
    /* 0x29 ')' */ {0x30,0x18,0x0C,0x0C,0x0C,0x18,0x30,0x00},
    /* 0x2A '*' */ {0x00,0x66,0x3C,0xFF,0x3C,0x66,0x00,0x00},
    /* 0x2B '+' */ {0x00,0x18,0x18,0x7E,0x18,0x18,0x00,0x00},
    /* 0x2C ',' */ {0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x30},
    /* 0x2D '-' */ {0x00,0x00,0x00,0x7E,0x00,0x00,0x00,0x00},
    /* 0x2E '.' */ {0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x00},
    /* 0x2F '/' */ {0x06,0x0C,0x18,0x30,0x60,0xC0,0x00,0x00},
    /* 0x30 '0' */ {0x3C,0x66,0x6E,0x76,0x66,0x66,0x3C,0x00},
    /* 0x31 '1' */ {0x18,0x38,0x18,0x18,0x18,0x18,0x7E,0x00},
    /* 0x32 '2' */ {0x3C,0x66,0x06,0x0C,0x18,0x30,0x7E,0x00},
    /* 0x33 '3' */ {0x3C,0x66,0x06,0x1C,0x06,0x66,0x3C,0x00},
    /* 0x34 '4' */ {0x0C,0x1C,0x3C,0x6C,0x7E,0x0C,0x0C,0x00},
    /* 0x35 '5' */ {0x7E,0x60,0x7C,0x06,0x06,0x66,0x3C,0x00},
    /* 0x36 '6' */ {0x1C,0x30,0x60,0x7C,0x66,0x66,0x3C,0x00},
    /* 0x37 '7' */ {0x7E,0x06,0x0C,0x18,0x30,0x30,0x30,0x00},
    /* 0x38 '8' */ {0x3C,0x66,0x66,0x3C,0x66,0x66,0x3C,0x00},
    /* 0x39 '9' */ {0x3C,0x66,0x66,0x3E,0x06,0x0C,0x38,0x00},
    /* 0x3A ':' */ {0x00,0x18,0x18,0x00,0x18,0x18,0x00,0x00},
    /* 0x3B ';' */ {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    /* 0x3C '<' */ {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    /* 0x3D '=' */ {0x00,0x00,0x7E,0x00,0x7E,0x00,0x00,0x00},
    /* 0x3E '>' */ {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    /* 0x3F '?' */ {0x3C,0x66,0x06,0x0C,0x18,0x00,0x18,0x00},
    /* 0x40 '@' */ {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    /* 0x41 'A' */ {0x3C,0x66,0x66,0x7E,0x66,0x66,0x66,0x00},
    /* 0x42 'B' */ {0x7C,0x66,0x66,0x7C,0x66,0x66,0x7C,0x00},
    /* 0x43 'C' */ {0x3C,0x66,0x60,0x60,0x60,0x66,0x3C,0x00},
    /* 0x44 'D' */ {0x78,0x6C,0x66,0x66,0x66,0x6C,0x78,0x00},
    /* 0x45 'E' */ {0x7E,0x60,0x60,0x7C,0x60,0x60,0x7E,0x00},
    /* 0x46 'F' */ {0x7E,0x60,0x60,0x7C,0x60,0x60,0x60,0x00},
    /* 0x47 'G' */ {0x3C,0x66,0x60,0x6E,0x66,0x66,0x3E,0x00},
    /* 0x48 'H' */ {0x66,0x66,0x66,0x7E,0x66,0x66,0x66,0x00},
    /* 0x49 'I' */ {0x3C,0x18,0x18,0x18,0x18,0x18,0x3C,0x00},
    /* 0x4A 'J' */ {0x06,0x06,0x06,0x06,0x66,0x66,0x3C,0x00},
    /* 0x4B 'K' */ {0x66,0x6C,0x78,0x70,0x78,0x6C,0x66,0x00},
    /* 0x4C 'L' */ {0x60,0x60,0x60,0x60,0x60,0x60,0x7E,0x00},
    /* 0x4D 'M' */ {0x63,0x77,0x7F,0x6B,0x63,0x63,0x63,0x00},
    /* 0x4E 'N' */ {0x66,0x76,0x7E,0x7E,0x6E,0x66,0x66,0x00},
    /* 0x4F 'O' */ {0x3C,0x66,0x66,0x66,0x66,0x66,0x3C,0x00},
    /* 0x50 'P' */ {0x7C,0x66,0x66,0x7C,0x60,0x60,0x60,0x00},
    /* 0x51 'Q' */ {0x3C,0x66,0x66,0x66,0x6A,0x6C,0x36,0x00},
    /* 0x52 'R' */ {0x7C,0x66,0x66,0x7C,0x6C,0x66,0x66,0x00},
    /* 0x53 'S' */ {0x3C,0x66,0x60,0x3C,0x06,0x66,0x3C,0x00},
    /* 0x54 'T' */ {0x7E,0x18,0x18,0x18,0x18,0x18,0x18,0x00},
    /* 0x55 'U' */ {0x66,0x66,0x66,0x66,0x66,0x66,0x3C,0x00},
    /* 0x56 'V' */ {0x66,0x66,0x66,0x66,0x66,0x3C,0x18,0x00},
    /* 0x57 'W' */ {0x63,0x63,0x63,0x6B,0x7F,0x77,0x63,0x00},
    /* 0x58 'X' */ {0x66,0x66,0x3C,0x18,0x3C,0x66,0x66,0x00},
    /* 0x59 'Y' */ {0x66,0x66,0x66,0x3C,0x18,0x18,0x18,0x00},
    /* 0x5A 'Z' */ {0x7E,0x06,0x0C,0x18,0x30,0x60,0x7E,0x00},
};

void amipython_bitmap_print_at(AmipyBitmap *bm, LONG x, LONG y, const char *text, LONG color) {
    LONG cx = x;
    LONG bw = (LONG)bm->width, bh = (LONG)bm->height;
    if (!bm->pBitmap || !text) return;
    _dirtyExpand(bm, (WORD)x, (WORD)y,
                 (WORD)(x + 8 * 20), (WORD)(y + 8));  /* rough estimate */
    blitWait();
    while (*text) {
        UBYTE ch = (UBYTE)*text;
        const UBYTE *glyph;
        LONG row, col;
        /* Map lowercase to uppercase */
        if (ch >= 'a' && ch <= 'z') ch = ch - 'a' + 'A';
        /* Get glyph from font table (0x20 to 0x5A range) */
        if (ch >= 0x20 && ch <= 0x5A) {
            glyph = s_font8x8[ch - 0x20];
        } else {
            glyph = s_font8x8[0]; /* space */
        }
        for (row = 0; row < 8; row++) {
            UBYTE bits = glyph[row];
            for (col = 0; col < 8; col++) {
                LONG bx = cx + col, by = y + row;
                if (bx >= 0 && bx < bw && by >= 0 && by < bh) {
                    if (bits & (0x80 >> col)) {
                        chunkyToPlanar((UBYTE)color, (UWORD)bx, (UWORD)by, bm->pBitmap);
                    } else {
                        chunkyToPlanar(0, (UWORD)bx, (UWORD)by, bm->pBitmap);
                    }
                }
            }
        }
        cx += 8;
        text++;
    }
}

void amipython_display_sprites_behind(AmipyDisplay *d, LONG from_channel) {
    /* TODO: Set sprite priority via BPLCON2 */
    (void)d; (void)from_channel;
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

void amipython_mouse_set_pointer(AmipySprite *sprite) {
    amipython_print_str("[input] mouse_set_pointer\n");
    (void)sprite;
}

void amipython_sprite_grab(AmipySprite *sprite, AmipyBitmap *bm, LONG x, LONG y, LONG w, LONG h) {
    amipython_print_str("[sprite] grab\n");
    (void)sprite; (void)bm; (void)x; (void)y; (void)w; (void)h;
}

void amipython_sprite_show(AmipySprite *sprite, LONG x, LONG y, LONG channel) {
    amipython_print_str("[sprite] show\n");
    (void)sprite; (void)x; (void)y; (void)channel;
}

BOOL amipython_sprite_collided(AmipySprite *sprite) {
    (void)sprite;
    return FALSE;
}

void amipython_collision_register(LONG color, LONG mask) {
    amipython_print_str("[collision] register\n");
    (void)color; (void)mask;
}

void amipython_collision_check(void) {
    amipython_print_str("[collision] check\n");
}

void amipython_bitmap_line(AmipyBitmap *bm, LONG x1, LONG y1, LONG x2, LONG y2, LONG color) {
    amipython_print_str("[bitmap] line\n");
    (void)bm; (void)x1; (void)y1; (void)x2; (void)y2; (void)color;
}

void amipython_bitmap_print_at(AmipyBitmap *bm, LONG x, LONG y, const char *text, LONG color) {
    amipython_print_str("[bitmap] print_at ");
    amipython_print_str(text);
    amipython_print_str("\n");
    (void)bm; (void)x; (void)y; (void)color;
}

void amipython_display_sprites_behind(AmipyDisplay *d, LONG from_channel) {
    amipython_print_str("[display] sprites_behind\n");
    (void)d; (void)from_channel;
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
