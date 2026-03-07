/*
 * amipython_engine.h — Engine type definitions and function declarations.
 *
 * On host: paired with amipython_engine_host.c (printf trace stubs).
 * On Amiga+ACE: paired with amipython_engine_amiga.c (real ACE graphics).
 * On Amiga+vbcc: paired with amipython_engine_amiga.c (dos.library trace stubs).
 */

#ifndef AMIPYTHON_ENGINE_H
#define AMIPYTHON_ENGINE_H

#include "amipython.h"

/* On Amiga, UWORD/UBYTE come from exec/types.h (via amipython.h).
   On host, define them. */
#ifndef AMIGA
typedef unsigned short UWORD;
typedef unsigned char UBYTE;
#endif

#ifdef ACE_ENGINE
/* ACE-backed structs hold pointers to ACE objects */
struct tView;
struct _tVPort;
struct _tSimpleBufferManager;
struct BitMap;

typedef struct {
    UWORD width, height;
    UBYTE bitplanes;
    struct tView *pView;
    struct _tVPort *pVPort;
    struct _tSimpleBufferManager *pBfr;
} AmipyDisplay;

typedef struct {
    UWORD width, height;
    UBYTE bitplanes;
    struct BitMap *pBitmap;
    /* Dirty rect for efficient clear — tracks bounding box of drawn area */
    WORD dirtyX1, dirtyY1, dirtyX2, dirtyY2;
    UBYTE hasDirty;
} AmipyBitmap;

/* ACE lifecycle — called from generated main() */
void amipython_engine_create(void);
void amipython_engine_destroy(void);

#else
/* Host / vbcc stubs — simple data-only structs */
typedef struct {
    UWORD width, height;
    UBYTE bitplanes;
} AmipyDisplay;

typedef struct {
    UWORD width, height;
    UBYTE bitplanes;
} AmipyBitmap;

/* No-op lifecycle on non-ACE builds */
#define amipython_engine_create()  ((void)0)
#define amipython_engine_destroy() ((void)0)
#endif

#ifdef ACE_ENGINE
/* Shape holds an ACE bitmap for blitting */
typedef struct {
    UWORD width, height;
    UBYTE bitplanes;
    struct BitMap *pBitmap;  /* planar bitmap in chip RAM */
} AmipyShape;
#else
/* Host / vbcc stubs — simple data-only struct */
typedef struct {
    UWORD width, height;
    UBYTE *data;
} AmipyShape;
#endif

void amipython_display_init(AmipyDisplay *d, LONG w, LONG h, LONG bp);
void amipython_display_show(AmipyDisplay *d, AmipyBitmap *bm);
void amipython_display_blit(AmipyDisplay *d, AmipyShape *shape, LONG x, LONG y);
void amipython_bitmap_init(AmipyBitmap *bm, LONG w, LONG h, LONG bp);
void amipython_bitmap_circle_filled(AmipyBitmap *bm, LONG cx, LONG cy, LONG r, LONG color);
void amipython_bitmap_box_filled(AmipyBitmap *bm, LONG x1, LONG y1, LONG x2, LONG y2, LONG color);
void amipython_bitmap_clear(AmipyBitmap *bm);
void amipython_bitmap_plot(AmipyBitmap *bm, LONG x, LONG y, LONG color);
void amipython_shape_grab(AmipyShape *shape, AmipyBitmap *bm, LONG x, LONG y, LONG w, LONG h);
void amipython_palette_aga(LONG reg, LONG r, LONG g, LONG b);
void amipython_palette_set(LONG reg, LONG r, LONG g, LONG b);
BOOL amipython_joy_button(LONG port);
void amipython_wait_mouse(void);
void amipython_vwait(LONG n);
LONG amipython_rnd(LONG n);
LONG amipython_mouse_x(void);
LONG amipython_mouse_y(void);
void amipython_sin_table(float *out, LONG n);
void amipython_cos_table(float *out, LONG n);

#endif /* AMIPYTHON_ENGINE_H */
