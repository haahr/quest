// Forces collections at fixed allocation counts, so that builds of one program
// can be compared at the same points (docs/profiling.md section 6): the
// collector otherwise collects where its own heuristics say, which differ
// between builds that keep different amounts alive, and between runs.
//
//     GCAT_EVERY=N  collect after every Nth allocation, printing "FORCED k"
//                   to standard error before the kth such collection
//     GCAT_TRAP=k   call gcat_stop, for a debugger's breakpoint, just before
//                   the kth, and force none after it
//
// Loaded with DYLD_INSERT_LIBRARIES, it interposes GC_malloc and
// GC_malloc_atomic, which compiled Quest calls through the runtime.
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

extern void *GC_malloc(size_t);
extern void *GC_malloc_atomic(size_t);
extern void GC_gcollect(void);

// Where a debugger stops at GCAT_TRAP
__attribute__((noinline, used)) void gcat_stop(void) { __asm__ volatile(""); }

static long count, every = -1, trap, forced;

static void report(void) { fprintf(stderr, "ALLOCATIONS %ld\n", count); }

static void tick(void) {
    if (every < 0) {
        const char *e = getenv("GCAT_EVERY"), *t = getenv("GCAT_TRAP");
        every = e ? atol(e) : 0;
        trap = t ? atol(t) : 0;
        atexit(report);
    }
    count++;
    if (every > 0 && count % every == 0) {
        forced++;
        if (forced == trap) gcat_stop();
        fprintf(stderr, "FORCED %ld\n", forced);
        GC_gcollect();
        if (forced == trap) every = 0;
    }
}

static void *gcat_malloc(size_t n) {
    tick();
    return GC_malloc(n);
}

static void *gcat_malloc_atomic(size_t n) {
    tick();
    return GC_malloc_atomic(n);
}

__attribute__((used)) static struct {
    const void *replacement, *original;
} interposers[] __attribute__((section("__DATA,__interpose"))) = {
    {(const void *)gcat_malloc, (const void *)GC_malloc},
    {(const void *)gcat_malloc_atomic, (const void *)GC_malloc_atomic},
};
