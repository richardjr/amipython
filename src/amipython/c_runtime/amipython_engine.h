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
struct _tView;
struct _tVPort;
struct _tSimpleBufferManager;
struct BitMap;

typedef struct {
    UWORD width, height;
    UBYTE bitplanes;
    struct _tView *pView;
    struct _tVPort *pVPort;
    struct _tSimpleBufferManager *pBfr;
} AmipyDisplay;

typedef struct {
    UWORD width, height;
    UBYTE bitplanes;
    struct BitMap *pBitmap;
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

void amipython_display_init(AmipyDisplay *d, LONG w, LONG h, LONG bp);
void amipython_display_show(AmipyDisplay *d, AmipyBitmap *bm);
void amipython_bitmap_init(AmipyBitmap *bm, LONG w, LONG h, LONG bp);
void amipython_bitmap_circle_filled(AmipyBitmap *bm, LONG cx, LONG cy, LONG r, LONG color);
void amipython_bitmap_clear(AmipyBitmap *bm);
void amipython_bitmap_plot(AmipyBitmap *bm, LONG x, LONG y, LONG color);
void amipython_palette_aga(LONG reg, LONG r, LONG g, LONG b);
void amipython_palette_set(LONG reg, LONG r, LONG g, LONG b);
void amipython_wait_mouse(void);
void amipython_vwait(void);

#endif /* AMIPYTHON_ENGINE_H */
