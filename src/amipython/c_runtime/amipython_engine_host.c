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

void amipython_bitmap_clear_rect(AmipyBitmap *bm, LONG x, LONG y, LONG w, LONG h) {
    printf("[bitmap] clear_rect %ld,%ld %ldx%ld\n", x, y, w, h);
    (void)bm;
}

void amipython_bitmap_copy_from(AmipyBitmap *dst, AmipyBitmap *src,
                                LONG x, LONG y, LONG w, LONG h) {
    printf("[bitmap] copy_from %ld,%ld %ldx%ld\n", x, y, w, h);
    (void)dst; (void)src;
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

void amipython_palette_fade(LONG level) {
    printf("[palette] fade %ld\n", level);
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

static BOOL s_host_prev_btn[2] = { FALSE, FALSE };
BOOL amipython_joy_button_pressed(LONG port) {
    BOOL curr = amipython_joy_button(port);
    LONG idx = (port == 0) ? 0 : 1;
    BOOL r = (curr && !s_host_prev_btn[idx]) ? TRUE : FALSE;
    s_host_prev_btn[idx] = curr;
    printf("[input] joy_button_pressed port=%ld -> %d\n", port, r);
    return r;
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

void amipython_shuffle(LONG *items, LONG count) {
    LONG i, j, tmp;
    for (i = count - 1; i > 0; i--) {
        j = amipython_rnd(i + 1);
        tmp = items[i]; items[i] = items[j]; items[j] = tmp;
    }
    printf("[shuffle] count=%ld\n", count);
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

#include <stdarg.h>
void amipython_bitmap_print_at_multi(AmipyBitmap *bm, LONG x, LONG y, LONG color, LONG n, ...) {
    va_list ap;
    LONG i;
    va_start(ap, n);
    printf("[bitmap] print_at_multi %ld,%ld color=%ld:", x, y, color);
    for (i = 0; i < n; i++) {
        const char *s = va_arg(ap, const char *);
        if (!s) s = "";
        printf(" \"%s\"", s);
    }
    printf("\n");
    va_end(ap);
    (void)bm;
}

void amipython_bitmap_print_centered(AmipyBitmap *bm, LONG y, const char *text, LONG color) {
    printf("[bitmap] print_centered y=%ld color=%ld \"%s\"\n", y, color, text);
    (void)bm;
}
void amipython_bitmap_print_centered_multi(AmipyBitmap *bm, LONG y, LONG color, LONG n, ...) {
    va_list ap; LONG i;
    va_start(ap, n);
    printf("[bitmap] print_centered_multi y=%ld color=%ld:", y, color);
    for (i = 0; i < n; i++) {
        const char *s = va_arg(ap, const char *); if (!s) s = "";
        printf(" \"%s\"", s);
    }
    printf("\n");
    va_end(ap);
    (void)bm;
}
void amipython_bitmap_print_right(AmipyBitmap *bm, LONG x_right, LONG y, const char *text, LONG color) {
    printf("[bitmap] print_right x_right=%ld y=%ld color=%ld \"%s\"\n",
           x_right, y, color, text);
    (void)bm;
}
void amipython_bitmap_print_right_multi(AmipyBitmap *bm, LONG x_right, LONG y, LONG color, LONG n, ...) {
    va_list ap; LONG i;
    va_start(ap, n);
    printf("[bitmap] print_right_multi x_right=%ld y=%ld color=%ld:", x_right, y, color);
    for (i = 0; i < n; i++) {
        const char *s = va_arg(ap, const char *); if (!s) s = "";
        printf(" \"%s\"", s);
    }
    printf("\n");
    va_end(ap);
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

BOOL amipython_joy_left(void) {
    printf("[input] joy_left\n");
    return FALSE;
}

BOOL amipython_joy_right(void) {
    printf("[input] joy_right\n");
    return FALSE;
}

BOOL amipython_joy_up(void) {
    printf("[input] joy_up\n");
    return FALSE;
}

BOOL amipython_joy_down(void) {
    printf("[input] joy_down\n");
    return FALSE;
}

BOOL amipython_joy_left_pressed(void) {
    printf("[input] joy_left_pressed\n");
    return FALSE;
}
BOOL amipython_joy_right_pressed(void) {
    printf("[input] joy_right_pressed\n");
    return FALSE;
}
BOOL amipython_joy_up_pressed(void) {
    printf("[input] joy_up_pressed\n");
    return FALSE;
}
BOOL amipython_joy_down_pressed(void) {
    printf("[input] joy_down_pressed\n");
    return FALSE;
}

BOOL amipython_key_pressed(LONG code) {
    printf("[input] key_pressed 0x%02lx\n", code);
    return FALSE;
}
BOOL amipython_key_just_pressed(LONG code) {
    printf("[input] key_just_pressed 0x%02lx\n", code);
    return FALSE;
}
BOOL amipython_key_just_released(LONG code) {
    printf("[input] key_just_released 0x%02lx\n", code);
    return FALSE;
}

/* --- Sound effects (host: trace only) --- */
void amipython_sfx_load(LONG slot, const char *path) {
    printf("[sfx] load slot=%ld \"%s\"\n", slot, path);
}
void amipython_sfx_load_embedded(LONG slot, const UBYTE *data, ULONG size, UWORD rate) {
    printf("[sfx] load_embedded slot=%ld size=%lu rate=%u\n",
           slot, (unsigned long)size, (unsigned)rate);
    (void)data;
}
void amipython_sfx_play(LONG slot, LONG channel, LONG volume) {
    printf("[sfx] play slot=%ld channel=%ld volume=%ld\n", slot, channel, volume);
}
void amipython_sfx_stop(LONG slot) {
    printf("[sfx] stop slot=%ld\n", slot);
}

/* --- Storage (host: in-memory map so load round-trips save in tests) --- */
#include <string.h>
#include <stdlib.h>

typedef struct { char name[32]; int kind; LONG *ints; LONG count; char *s; } _StorageEntry;
static _StorageEntry s_storage[16];
static LONG s_storage_count = 0;

static _StorageEntry *_storage_find(const char *name) {
    LONG i;
    for (i = 0; i < s_storage_count; i++) {
        if (strcmp(s_storage[i].name, name) == 0) return &s_storage[i];
    }
    return NULL;
}

static _StorageEntry *_storage_slot(const char *name) {
    _StorageEntry *e = _storage_find(name);
    if (e) {
        if (e->ints) { free(e->ints); e->ints = NULL; }
        if (e->s) { free(e->s); e->s = NULL; }
        return e;
    }
    if (s_storage_count >= 16) return NULL;
    e = &s_storage[s_storage_count++];
    strncpy(e->name, name, 31);
    e->name[31] = 0;
    e->ints = NULL; e->count = 0; e->s = NULL; e->kind = 0;
    return e;
}

void amipython_storage_save_int_list(const char *name, const LONG *items, LONG count) {
    _StorageEntry *e = _storage_slot(name);
    printf("[storage] save_int_list %s count=%ld\n", name, count);
    if (!e) return;
    e->kind = 0;
    e->ints = (LONG *)malloc(sizeof(LONG) * (size_t)count);
    if (e->ints) {
        memcpy(e->ints, items, sizeof(LONG) * (size_t)count);
        e->count = count;
    }
}

BOOL amipython_storage_load_int_list(const char *name, LONG *items, LONG *count_out, LONG capacity) {
    _StorageEntry *e;
    LONG n;
    printf("[storage] load_int_list %s\n", name);
    e = _storage_find(name);
    if (!e || e->kind != 0 || !e->ints) { *count_out = 0; return FALSE; }
    n = e->count < capacity ? e->count : capacity;
    memcpy(items, e->ints, sizeof(LONG) * (size_t)n);
    *count_out = n;
    return TRUE;
}

void amipython_storage_save_str(const char *name, const char *value) {
    _StorageEntry *e;
    size_t len;
    const char *src = value ? value : "";
    printf("[storage] save_str %s=%s\n", name, src);
    e = _storage_slot(name);
    if (!e) return;
    e->kind = 1;
    len = strlen(src);
    e->s = (char *)malloc(len + 1);
    if (e->s) memcpy(e->s, src, len + 1);
}

const char *amipython_storage_load_str(const char *name) {
    _StorageEntry *e = _storage_find(name);
    printf("[storage] load_str %s\n", name);
    if (!e || e->kind != 1 || !e->s) return "";
    return e->s;
}

BOOL amipython_storage_exists(const char *name) {
    BOOL r;
    r = _storage_find(name) != NULL;
    printf("[storage] exists %s -> %d\n", name, r);
    return r;
}

void amipython_tilemap_init(AmipyTilemap *tm, const UBYTE *tileset_data,
    LONG ts_w, LONG ts_h, LONG ts_bp,
    LONG w, LONG h, LONG bp, LONG tile_size, LONG map_w, LONG map_h) {
    tm->width = (UWORD)w;
    tm->height = (UWORD)h;
    tm->bitplanes = (UBYTE)bp;
    tm->mapW = (UWORD)map_w;
    tm->mapH = (UWORD)map_h;
    tm->tileShift = 4;
    tm->pShadowTiles = 0;
    tm->pBlockingFlags = 0;
    tm->blockingCount = 0;
    printf("[tilemap] init %ldx%ld %ldbp tile=%ld map=%ldx%ld\n", w, h, bp, tile_size, map_w, map_h);
    (void)tileset_data; (void)ts_w; (void)ts_h; (void)ts_bp;
}

void amipython_tilemap_show(AmipyTilemap *tm) {
    printf("[tilemap] show\n");
    (void)tm;
}

void amipython_tilemap_camera(AmipyTilemap *tm, LONG x, LONG y) {
    printf("[tilemap] camera %ld,%ld\n", x, y);
    (void)tm;
}

void amipython_tilemap_scroll(AmipyTilemap *tm, LONG dx, LONG dy) {
    printf("[tilemap] scroll %ld,%ld\n", dx, dy);
    (void)tm;
}

void amipython_tilemap_set_tile(AmipyTilemap *tm, LONG x, LONG y, LONG tile) {
    printf("[tilemap] set_tile %ld,%ld=%ld\n", x, y, tile);
    (void)tm;
}

LONG amipython_tilemap_get_tile(AmipyTilemap *tm, LONG x, LONG y) {
    printf("[tilemap] get_tile %ld,%ld\n", x, y);
    (void)tm;
    return 0;
}

BOOL amipython_tilemap_is_blocking(AmipyTilemap *tm, LONG pixel_x, LONG pixel_y) {
    LONG tx, ty, tile;
    if (!tm->pBlockingFlags || tm->blockingCount == 0) return FALSE;
    tx = pixel_x >> tm->tileShift;
    ty = pixel_y >> tm->tileShift;
    if (tx < 0 || tx >= tm->mapW || ty < 0 || ty >= tm->mapH) return TRUE;
    tile = 0; /* would read from shadow tiles if available */
    if (tm->pShadowTiles) {
        tile = tm->pShadowTiles[tx * tm->mapH + ty];
    }
    if (tile >= 0 && tile < tm->blockingCount) {
        return tm->pBlockingFlags[tile] ? TRUE : FALSE;
    }
    return FALSE;
}

void amipython_tilemap_set_blocking(AmipyTilemap *tm, const UBYTE *flags, LONG count) {
    tm->pBlockingFlags = flags;
    tm->blockingCount = (UBYTE)count;
    printf("[tilemap] set_blocking (%ld tile types)\n", count);
}

void amipython_tilemap_draw_shape(AmipyTilemap *tm, AmipyShape *shape, LONG world_x, LONG world_y) {
    printf("[tilemap] draw_shape at %ld,%ld\n", world_x, world_y);
    (void)tm; (void)shape;
}

void amipython_tilemap_process(AmipyTilemap *tm) {
    (void)tm;
}
