/*
 * amipython_engine_host.c — Host stub implementations for testing.
 *
 * Each function prints a trace line so tests can verify the correct
 * sequence of engine calls.
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "amipython_engine.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static int s_joy_button_count = 0;

void amipython_display_init(AmipyDisplay *d, LONG w, LONG h, LONG bp) {
    d->width = (UWORD)w;
    d->height = (UWORD)h;
    d->bitplanes = (UBYTE)bp;
    printf("[display] init %ldx%ld %ldbp\n", w, h, bp);
}

void amipython_display_show(AmipyDisplay *d, AmipyBitmap *bm) {
    printf("[display] show %ux%u on %ux%u\n",
           bm->width, bm->height, d->width, d->height);
}

void amipython_display_blit(AmipyDisplay *d, AmipyShape *shape, LONG x, LONG y) {
    printf("[display] blit %ux%u at %ld,%ld\n", shape->width, shape->height, x, y);
}

void amipython_bitmap_init(AmipyBitmap *bm, LONG w, LONG h, LONG bp) {
    bm->width = (UWORD)w;
    bm->height = (UWORD)h;
    bm->bitplanes = (UBYTE)bp;
    printf("[bitmap] init %ldx%ld %ldbp\n", w, h, bp);
}

void amipython_bitmap_circle_filled(AmipyBitmap *bm, LONG cx, LONG cy, LONG r, LONG color) {
    printf("[bitmap] circle_filled %ld,%ld r=%ld color=%ld\n", cx, cy, r, color);
}

void amipython_bitmap_box_filled(AmipyBitmap *bm, LONG x1, LONG y1, LONG x2, LONG y2, LONG color) {
    printf("[bitmap] box_filled %ld,%ld-%ld,%ld color=%ld\n", x1, y1, x2, y2, color);
    (void)bm;
}

void amipython_bitmap_clear(AmipyBitmap *bm) {
    printf("[bitmap] clear %ux%u\n", bm->width, bm->height);
}

void amipython_bitmap_plot(AmipyBitmap *bm, LONG x, LONG y, LONG color) {
    printf("[bitmap] plot %ld,%ld color=%ld\n", x, y, color);
}

void amipython_palette_aga(LONG reg, LONG r, LONG g, LONG b) {
    printf("[palette] aga %ld r=%ld g=%ld b=%ld\n", reg, r, g, b);
}

void amipython_palette_set(LONG reg, LONG r, LONG g, LONG b) {
    printf("[palette] set %ld r=%ld g=%ld b=%ld\n", reg, r, g, b);
}

void amipython_shape_grab(AmipyShape *shape, AmipyBitmap *bm, LONG x, LONG y, LONG w, LONG h) {
    shape->width = (UWORD)w;
    shape->height = (UWORD)h;
    shape->data = NULL;
    printf("[shape] grab %ldx%ld from %ux%u at %ld,%ld\n", w, h, bm->width, bm->height, x, y);
}

void amipython_shape_load(AmipyShape *shape, const char *path) {
    shape->width = 16;
    shape->height = 16;
    shape->data = NULL;
    printf("[shape] load \"%s\"\n", path);
}

void amipython_shape_load_embedded(AmipyShape *shape, const UBYTE *data, LONG w, LONG h, LONG bp) {
    shape->width = (UWORD)w;
    shape->height = (UWORD)h;
    shape->data = NULL;
    printf("[shape] load_embedded %ldx%ldx%ld\n", w, h, bp);
    (void)data;
}

void amipython_bitmap_load(AmipyBitmap *bm, const char *path) {
    bm->width = 320;
    bm->height = 200;
    bm->bitplanes = 5;
    printf("[bitmap] load \"%s\"\n", path);
}

void amipython_bitmap_load_embedded(AmipyBitmap *bm, const UBYTE *data, LONG w, LONG h, LONG bp) {
    bm->width = (UWORD)w;
    bm->height = (UWORD)h;
    bm->bitplanes = (UBYTE)bp;
    printf("[bitmap] load_embedded %ldx%ldx%ld\n", w, h, bp);
    (void)data;
}

BOOL amipython_joy_button(LONG port) {
    s_joy_button_count++;
    printf("[input] joy_button port=%ld\n", port);
    /* Return TRUE after 3 calls so game loops terminate in tests */
    return (s_joy_button_count > 3) ? TRUE : FALSE;
}

void amipython_wait_mouse(void) {
    printf("[input] wait_mouse\n");
}

void amipython_vwait(LONG n) {
    printf("[input] vwait %ld\n", n);
}

LONG amipython_rnd(LONG n) {
    printf("[rnd] %ld\n", n);
    return n > 0 ? (LONG)(rand() % n) : 0;
}

LONG amipython_mouse_x(void) {
    printf("[input] mouse_x\n");
    return 160;
}

LONG amipython_mouse_y(void) {
    printf("[input] mouse_y\n");
    return 128;
}

void amipython_mouse_set_pointer(AmipySprite *sprite) {
    printf("[input] mouse_set_pointer %ux%u\n", sprite->width, sprite->height);
}

void amipython_sprite_grab(AmipySprite *sprite, AmipyBitmap *bm, LONG x, LONG y, LONG w, LONG h) {
    sprite->width = (UWORD)w;
    sprite->height = (UWORD)h;
    sprite->data = NULL;
    sprite->bCollided = 0;
    printf("[sprite] grab %ldx%ld from %ux%u at %ld,%ld\n", w, h, bm->width, bm->height, x, y);
}

void amipython_sprite_show(AmipySprite *sprite, LONG x, LONG y, LONG channel) {
    printf("[sprite] show %ux%u at %ld,%ld ch=%ld\n", sprite->width, sprite->height, x, y, channel);
}

BOOL amipython_sprite_collided(AmipySprite *sprite) {
    printf("[sprite] collided -> %d\n", sprite->bCollided);
    return sprite->bCollided ? TRUE : FALSE;
}

static LONG s_coll_color = 0;
static LONG s_coll_mask = 0;

void amipython_collision_register(LONG color, LONG mask) {
    s_coll_color = color;
    s_coll_mask = mask;
    printf("[collision] register color=%ld mask=%ld\n", color, mask);
}

void amipython_collision_check(void) {
    printf("[collision] check\n");
}

void amipython_bitmap_line(AmipyBitmap *bm, LONG x1, LONG y1, LONG x2, LONG y2, LONG color) {
    printf("[bitmap] line %ld,%ld-%ld,%ld color=%ld\n", x1, y1, x2, y2, color);
    (void)bm;
}

void amipython_bitmap_print_at(AmipyBitmap *bm, LONG x, LONG y, const char *text, LONG color) {
    printf("[bitmap] print_at %ld,%ld \"%s\" color=%ld\n", x, y, text, color);
    (void)bm;
}

void amipython_display_sprites_behind(AmipyDisplay *d, LONG from_channel) {
    printf("[display] sprites_behind from_channel=%ld\n", from_channel);
    (void)d;
}

void amipython_sin_table(float *out, LONG n) {
    LONG i;
    printf("[math] sin_table %ld\n", n);
    for (i = 0; i < n; i++) {
        out[i] = (float)sin(2.0 * M_PI * (double)i / (double)n);
    }
}

void amipython_cos_table(float *out, LONG n) {
    LONG i;
    printf("[math] cos_table %ld\n", n);
    for (i = 0; i < n; i++) {
        out[i] = (float)cos(2.0 * M_PI * (double)i / (double)n);
    }
}

void amipython_music_load(const char *path) {
    printf("[music] load \"%s\"\n", path);
}

void amipython_music_load_embedded(const UBYTE *data, ULONG size) {
    printf("[music] load_embedded %lu bytes\n", (unsigned long)size);
    (void)data;
}

void amipython_music_play(void) {
    printf("[music] play\n");
}

void amipython_music_stop(void) {
    printf("[music] stop\n");
}

void amipython_music_volume(LONG vol) {
    printf("[music] volume %ld\n", vol);
}
