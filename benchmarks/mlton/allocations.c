// An interposer of the collector's allocators, for allocations.py: it counts
// the calls of GC_malloc and GC_malloc_atomic, and their bytes, by the two
// return addresses above the call (the allocator's caller, and its caller, for
// when the first is the runtime's quest_alloc), and at exit writes a line
// "address1 address2 count bytes" per pair to $QUEST_ALLOCATIONS_OUT, each
// address relative to the program's image as atos -l 0x100000000 reads it, or
// 0 if it is not in the program.
#include <dlfcn.h>
#include <crt_externs.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

void *GC_malloc(size_t);
void *GC_malloc_atomic(size_t);

#define SLOTS (1 << 18)
static uintptr_t keys1[SLOTS], keys2[SLOTS];
static unsigned long counts[SLOTS], bytes[SLOTS];

// The caller of the allocator's caller, by its frame record (x29 on arm64,
// whose ABI keeps frame pointers)
static uintptr_t outer_return(void) {
    void **frame = __builtin_frame_address(1);
    return frame ? (uintptr_t)frame[1] : 0;
}

static void note(uintptr_t ra1, uintptr_t ra2, size_t n) {
    size_t i = ((ra1 >> 2) ^ (ra2 >> 4)) & (SLOTS - 1);
    while (keys1[i] && (keys1[i] != ra1 || keys2[i] != ra2)) i = (i + 1) & (SLOTS - 1);
    keys1[i] = ra1;
    keys2[i] = ra2;
    counts[i]++;
    bytes[i] += n;
}

__attribute__((noinline)) static void *counting_malloc(size_t n) {
    note((uintptr_t)__builtin_return_address(0), outer_return(), n);
    return GC_malloc(n);
}

__attribute__((noinline)) static void *counting_malloc_atomic(size_t n) {
    note((uintptr_t)__builtin_return_address(0), outer_return(), n);
    return GC_malloc_atomic(n);
}

__attribute__((used, section("__DATA,__interpose"))) static struct { void *replacement, *original; } interpose[] = {
    {(void *)counting_malloc, (void *)GC_malloc},
    {(void *)counting_malloc_atomic, (void *)GC_malloc_atomic},
};

static unsigned long relative(uintptr_t address) {
    Dl_info info;
    if (!address || !dladdr((void *)address, &info) || info.dli_fbase != (void *)_NSGetMachExecuteHeader()) return 0;
    return (unsigned long)(address - (uintptr_t)info.dli_fbase + 0x100000000);
}

__attribute__((destructor)) static void dump(void) {
    const char *path = getenv("QUEST_ALLOCATIONS_OUT");
    FILE *f = fopen(path ? path : "/dev/stderr", "w");
    if (!f) return;
    for (size_t i = 0; i < SLOTS; i++) {
        if (keys1[i]) fprintf(f, "0x%lx 0x%lx %lu %lu\n", relative(keys1[i]), relative(keys2[i]), counts[i], bytes[i]);
    }
    fclose(f);
}
