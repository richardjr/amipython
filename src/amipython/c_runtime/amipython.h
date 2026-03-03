/*
 * amipython.h — Compatibility header for amipython generated code.
 *
 * Provides type definitions and helper functions that work with both
 * host gcc (for fast iteration) and Amiga vbcc (real target).
 *
 * On Amiga: uses dos.library for I/O (vamos-compatible), avoids
 * -lmieee (its startup breaks vamos). Float helpers use integer math.
 * On host: uses stdio.h printf and math.h.
 */

#ifndef AMIPYTHON_H
#define AMIPYTHON_H

#ifdef AMIGA
#include <exec/types.h>
#include <proto/dos.h>
/* LONG, BOOL already defined by exec/types.h */
#else
#include <stdio.h>
#include <math.h>
/* Host typedefs matching Amiga types */
typedef long LONG;
typedef int BOOL;
#ifndef TRUE
#define TRUE 1
#endif
#ifndef FALSE
#define FALSE 0
#endif
#endif

/* Suppress unused-function warnings for helper functions */
#if defined(__GNUC__) || defined(__clang__)
#define AMIPYTHON_HELPER __attribute__((unused)) static
#else
#define AMIPYTHON_HELPER static
#endif

/*
 * I/O functions — use AmigaDOS Write() on Amiga (vamos-compatible),
 * fall back to printf on host.
 */
#ifdef AMIGA

AMIPYTHON_HELPER void amipython_print_str(const char *s) {
    BPTR out = Output();
    LONG len = 0;
    const char *p = s;
    while (*p++) len++;
    Write(out, (APTR)s, len);
}

AMIPYTHON_HELPER void amipython_print_long(LONG val) {
    char buf[12];
    char *p = buf + sizeof(buf) - 1;
    int neg = 0;
    unsigned long uval;
    *p = '\0';
    if (val < 0) { neg = 1; uval = (unsigned long)(-(val + 1)) + 1; }
    else { uval = (unsigned long)val; }
    if (uval == 0) { *--p = '0'; }
    else { while (uval > 0) { *--p = '0' + (char)(uval % 10); uval /= 10; } }
    if (neg) *--p = '-';
    amipython_print_str(p);
}

#ifdef AMIPYTHON_USE_FLOAT
AMIPYTHON_HELPER void amipython_print_float(float val) {
    char buf[32];
    char *p = buf;
    long ipart;
    unsigned long frac;
    long mul;
    int i;
    if (val < 0) { *p++ = '-'; val = -val; }
    ipart = (long)val;
    /* compute 6 fractional digits using integer scaling */
    mul = (long)((val - (float)ipart) * 1000000.0f + 0.5f);
    frac = (unsigned long)mul;
    if (frac >= 1000000UL) { ipart++; frac -= 1000000UL; }
    /* write integer part */
    {
        char ibuf[12];
        char *ip = ibuf + sizeof(ibuf) - 1;
        unsigned long uv = (unsigned long)ipart;
        *ip = '\0';
        if (uv == 0) { *--ip = '0'; }
        else { while (uv > 0) { *--ip = '0' + (char)(uv % 10); uv /= 10; } }
        while (*ip) *p++ = *ip++;
    }
    *p++ = '.';
    for (i = 5; i >= 0; i--) {
        p[i] = '0' + (char)(frac % 10);
        frac /= 10;
    }
    p += 6;
    *p = '\0';
    amipython_print_str(buf);
}
#endif

AMIPYTHON_HELPER void amipython_print_bool(BOOL val) {
    amipython_print_long((LONG)val);
}

AMIPYTHON_HELPER void amipython_print_newline(void) {
    amipython_print_str("\n");
}

AMIPYTHON_HELPER void amipython_print_space(void) {
    amipython_print_str(" ");
}

#else

/* Host: use printf */
#define amipython_print_str(s)    printf("%s", (s))
#define amipython_print_long(v)   printf("%ld", (v))
#ifdef AMIPYTHON_USE_FLOAT
#define amipython_print_float(v)  printf("%f", (double)(v))
#endif
#define amipython_print_bool(v)   printf("%d", (v))
#define amipython_print_newline() printf("\n")
#define amipython_print_space()   printf(" ")

#endif

/* Floor division: Python rounds toward -infinity, C truncates toward zero */
AMIPYTHON_HELPER LONG amipython_floordiv(LONG a, LONG b) {
    LONG q = a / b;
    LONG r = a % b;
    if ((r != 0) && ((r ^ b) < 0)) {
        q--;
    }
    return q;
}

/* Python-style modulo: result has same sign as divisor */
AMIPYTHON_HELPER LONG amipython_mod(LONG a, LONG b) {
    LONG r = a % b;
    if ((r != 0) && ((r ^ b) < 0)) {
        r += b;
    }
    return r;
}

/* Integer power */
AMIPYTHON_HELPER LONG amipython_ipow(LONG base, LONG exp) {
    LONG result = 1;
    if (exp < 0) return 0;
    while (exp > 0) {
        if (exp & 1) result *= base;
        base *= base;
        exp >>= 1;
    }
    return result;
}

/*
 * Float helpers — only compiled when AMIPYTHON_USE_FLOAT is defined.
 * On Amiga/vbcc, float ops require -lmieee (MathIeeeSingBas library).
 * Guarding them avoids pulling in the IEEE library for int-only programs.
 */
#ifdef AMIPYTHON_USE_FLOAT

/* Float power — integer exponent only (Phase 1), no math.h dependency */
AMIPYTHON_HELPER float amipython_fpow(float base, float exp) {
    float result = 1.0f;
    LONG iexp = (LONG)exp;
    LONG i;
    if (iexp < 0) {
        for (i = 0; i > iexp; i--) result /= base;
    } else {
        for (i = 0; i < iexp; i++) result *= base;
    }
    return result;
}

/* Float floor division — no math.h dependency */
AMIPYTHON_HELPER float amipython_floordiv_f(float a, float b) {
    float q = a / b;
    long iq = (long)q;
    /* floor: if result is negative and not exact, round down */
    if (q < 0.0f && (float)iq != q) {
        iq--;
    }
    return (float)iq;
}

/* Float modulo — Python semantics, no math.h dependency */
AMIPYTHON_HELPER float amipython_mod_f(float a, float b) {
    long q = (long)(a / b);
    float r = a - (float)q * b;
    if ((r != 0.0f) && ((r < 0.0f) != (b < 0.0f))) {
        r += b;
    }
    return r;
}

#endif /* AMIPYTHON_USE_FLOAT */

#endif /* AMIPYTHON_H */
