/* The collector (docs/collector.md): the heap, allocation's slow path, marking
 * and sweeping, the roots, the statistics, and the checking modes of
 * QUEST_GC_CHECK; and the layouts of the objects the runtime allocates.
 * Allocation's fast path is the header's inline quest_alloc and its variants,
 * which bump a cursor through the current hole and prepend a header word
 * naming each object's layout.
 *
 * The heap is one reserved range of 32 KB blocks of 128-byte lines (section
 * 3.1), with its metadata off to the side: a block table, a mark byte per
 * line, and two bitmaps with a bit per 8 bytes, one of the objects' starts
 * (set by every allocation, by which an interior or ambiguous word finds its
 * object) and one of the marks. An allocation of 8 KB and up takes a run of
 * blocks of its own (section 3.9); pointer-free objects go to blocks of their
 * own, through a cursor of their own (the noscan space). A collection stops
 * the world, marks from the roots by the layouts (precise words followed,
 * ambiguous ones validated against the start bits), sets the line marks of
 * what it marked, and then keeps only live objects' start bits (decision 14)
 * and classifies every block by its free lines, which the next allocations
 * are bumped through, zeroed as each hole is entered. This is step 3 of the
 * plan: stop-the-world and non-generational; the barriers count. */

#define _GNU_SOURCE
#include "quest_runtime.h"

#include <inttypes.h>
#include <pthread.h>
#include <setjmp.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>

#if defined(__APPLE__)
#  include <crt_externs.h>
#  include <dlfcn.h>
#  include <mach-o/getsect.h>
#  include <mach-o/ldsyms.h>
#elif defined(__linux__)
#  include <dlfcn.h>
extern char __data_start[];
extern char _end[];
#endif

#ifndef MAP_NORESERVE
#  define MAP_NORESERVE 0
#endif
#ifndef MAP_ANONYMOUS
#  define MAP_ANONYMOUS MAP_ANON
#endif

/* ---------------------------------------------------------------------------
 * The runtime's layouts
 *
 * Each object the runtime allocates names one of these. A fixed layout lists
 * its words' kinds; an array layout its header's words and then its element's;
 * a sized layout its element's alone. The kinds are checked against the C
 * structs' sizes where a static assertion can (quest_gc_check_object checks
 * the rest when a mode is on).
 * ------------------------------------------------------------------------ */

#define S Q_WORD_SCALAR
#define P Q_WORD_POINTER
#define A Q_WORD_AMBIGUOUS

#define Q_FIXED(cname, text, bytes, ...) Q_LAYOUT_FIXED_DEF(, cname, text, bytes, __VA_ARGS__)
#define Q_FIXED_NOSCAN(cname, text, bytes) Q_LAYOUT_NOSCAN_DEF(, cname, text, bytes)
#define Q_ARRAY(cname, text, header_bytes, length_offset, element_words, ...) \
    Q_LAYOUT_ARRAY_DEF(, cname, text, header_bytes, length_offset, element_words, __VA_ARGS__)
#define Q_SIZED(cname, text, ...) Q_LAYOUT_SIZED_DEF(, cname, text, __VA_ARGS__)

/* The layouts generated code and the header's inline helpers use */
Q_FIXED(quest_layout_record_box, "QRecordVal", 16, P, P);
Q_FIXED(quest_layout_variant_box, "QVariantVal", 16, S, A);
Q_FIXED(quest_layout_closure, "QClosure", 16, P, P);
Q_FIXED(quest_layout_adapter_env, "QFunAdapterEnv", 32, P, P, P, S);
Q_ARRAY(quest_layout_array_pointer, "QArray(pointer)", 8, 0, 1, S, P);
const QLayout quest_layout_array_scalar = { "QArray(scalar)", Q_LAYOUT_ARRAY, Q_LAYOUT_NOSCAN, 8, 0, 1, 1, NULL };
Q_ARRAY(quest_layout_array_ambiguous, "QArray(QVal)", 8, 0, 1, S, A);
const QLayout quest_layout_bytes = { "bytes", Q_LAYOUT_SIZED, Q_LAYOUT_NOSCAN, 0, 0, 1, 0, NULL };
Q_SIZED(quest_layout_words, "words", A);

/* The runtime's values and the structures behind them */
Q_FIXED(quest_layout_string, "QString", 24, S, S, P);
Q_FIXED(quest_layout_exception, "QException", 8, P);
Q_FIXED(quest_layout_auto, "QAuto", 16, P, A);
Q_FIXED(quest_layout_component, "QVal", 8, A);
Q_FIXED(quest_layout_proxy, "QProxy", 48, P, P, P, P, P, P);
Q_FIXED(quest_layout_raised, "QRaised", 48, P, A, P, P, P, P);
Q_FIXED_NOSCAN(quest_layout_trace, "QTrace", sizeof(QTrace));
Q_FIXED(quest_layout_writer, "QWriter", 16, P, S);
Q_FIXED(quest_layout_reader, "QReader", 16, P, S);
Q_FIXED(quest_layout_process, "QProcess", 40, S, S, S, P, P);
Q_FIXED(quest_layout_string_builder, "QStringBuilder", 48, P, S, P, S, S, S);
Q_FIXED(quest_layout_code_region, "QCodeRegion", 24, P, S, S);
Q_FIXED(quest_layout_run_result, "Tuple code: Int stdout: String stderr: String end", 24, S, P, P);
Q_FIXED_NOSCAN(quest_layout_file_stats, "Tuple kind: Int ... changeNs: Int end", 72);
Q_SIZED(quest_layout_pointers, "pointers", P);
const QLayout quest_layout_ints = { "ints", Q_LAYOUT_SIZED, Q_LAYOUT_NOSCAN, 0, 0, 1, 0, NULL };
Q_SIZED(quest_layout_proxy_cache, "QProxy cache", A);

/* Descriptors and the runtime's tables of them */
Q_FIXED(quest_layout_descriptor, "QTypeDescriptor", 48, S, P, S, S, P, P);
Q_FIXED(quest_layout_array_descriptor, "QArrayTypeDescriptor", 8, P);
Q_FIXED(quest_layout_exception_descriptor, "QExceptionTypeDescriptor", 8, P);
Q_FIXED(quest_layout_opaque_descriptor, "QOpaqueTypeDescriptor", 24, S, P, P);
Q_FIXED(quest_layout_stored_descriptor, "QStoredDescriptor", 24, P, P, S);
Q_ARRAY(quest_layout_record_descriptor, "QRecordTypeDescriptor", 8, 0, 4, S, P, P, S, S);
Q_ARRAY(quest_layout_tuple_descriptor, "QTupleTypeDescriptor", 24, 16, 4, S, P, S, P, P, S, S);
Q_ARRAY(quest_layout_variant_descriptor, "QVariantTypeDescriptor", 8, 0, 4, S, P, P, S, S);
Q_ARRAY(quest_layout_fun_descriptor, "QFunTypeDescriptor", 48, 0, 2, S, P, P, P, S, P, P, S);
Q_ARRAY(quest_layout_auto_descriptor, "QAutoTypeDescriptor", 24, 16, 4, P, S, S, P, P, S, S);
Q_FIXED(quest_layout_descriptor_entry, "QTypeDescriptorEntry", 16, P, P);
Q_SIZED(quest_layout_record_dict_entries, "QRecordDictEntry", P, P, P);
Q_SIZED(quest_layout_inst_nodes, "QInstNode", P, P, S);
Q_FIXED(quest_layout_inst_cache_entry, "QInstCacheEntry", 40, P, S, P, P, P);
Q_FIXED(quest_layout_view_map_entry, "QViewMapEntry", 56, P, P, P, P, P, P, P);
Q_FIXED(quest_layout_variant_adapter_entry, "QVariantAdapterCacheEntry", 32, P, P, P, P);
Q_FIXED(quest_layout_abstract_type_entry, "QAbstractTypeEntry", 32, P, S, P, P);

#undef S
#undef P
#undef A

/* ---------------------------------------------------------------------------
 * The heap's geometry and its parameters
 * ------------------------------------------------------------------------ */

#define Q_GC_LINE_BITS       7
#define Q_GC_LINE            ((size_t)1 << Q_GC_LINE_BITS)                 /* 128 bytes */
#define Q_GC_BLOCK_BITS      15
#define Q_GC_BLOCK           ((size_t)1 << Q_GC_BLOCK_BITS)                /* 32 KB */
#define Q_GC_BLOCK_LINES     (Q_GC_BLOCK / Q_GC_LINE)                      /* 256 */
#define Q_GC_BLOCK_BITMAP    (Q_GC_BLOCK / 64)                             /* bytes of a bitmap per block: 512 */
#define Q_GC_MEDIUM          Q_GC_LINE          /* an allocation over a line is medium: from the overflow cursor */
#define Q_GC_LARGE           ((size_t)8 << 10)  /* an allocation of 8 KB and up is large: a run of blocks */
#define Q_GC_MIN_HEAP        ((size_t)64 << 20) /* the heap's size before the first collection, and its least */
#define Q_GC_GROWTH          2                  /* the heap may grow to this times the blocks in use after a collection */
#define Q_GC_RESERVE_DEFAULT ((size_t)64 << 30) /* the virtual range reserved, halved until the system grants it */
#define Q_GC_POISON          0x5A               /* the byte a reclaimed line is filled with under `poison` */

/* The spaces: pointer-bearing objects, and pointer-free ones, which a
 * collection never scans */
#define Q_GC_SCAN   0u
#define Q_GC_NOSCAN 1u

/* A block's state */
enum { QB_FREE = 0, QB_SMALL, QB_LARGE_HEAD, QB_LARGE_TAIL };

typedef struct QBlock {
    uint8_t  state;
    uint8_t  space;      /* QB_SMALL, QB_LARGE_HEAD: which cursor's objects it holds */
    uint8_t  fresh;      /* never allocated into since it was mapped, so zero already */
    uint8_t  pad;
    uint32_t run;        /* QB_LARGE_HEAD: the blocks of its run; QB_LARGE_TAIL: the blocks back to its head */
    uint32_t live_lines; /* QB_SMALL: after the last collection */
    uint32_t pad2;
} QBlock;

/* The reserve, and the metadata beside it; the first two are what the
 * header's inline allocation reads */
uintptr_t        quest_gc_heap_lo = 0;
uint8_t         *quest_gc_start_bits = NULL;   /* a bit per 8 bytes of the reserve, by (address - heap_lo) >> 3 */
static uintptr_t quest_gc_heap_hi = 0;
static size_t    quest_gc_block_n = 0;         /* blocks in the reserve */
static size_t    quest_gc_high_water = 0;      /* blocks ever taken; those beyond are fresh */
static QBlock   *quest_gc_blocks = NULL;
static uint8_t  *quest_gc_lines = NULL;        /* a mark byte per line, by (address - heap_lo) >> 7 */
static uint8_t  *quest_gc_marks = NULL;        /* a bit per 8 bytes, as the start bits */
static bool      quest_gc_ready = false;

/* The cursors: the small allocator's, which the header's inline fast path
 * bumps, and the overflow allocator's for medium objects, per space */
uintptr_t        quest_gc_cursor[2] = { 0, 0 };
uintptr_t        quest_gc_limit[2] = { 0, 0 };
static uintptr_t quest_gc_over_cursor[2] = { 0, 0 };
static uintptr_t quest_gc_over_limit[2] = { 0, 0 };
#define Q_GC_NO_BLOCK ((size_t)-1)
static size_t    quest_gc_current[2] = { Q_GC_NO_BLOCK, Q_GC_NO_BLOCK };  /* the small cursor's block */
static size_t    quest_gc_current_line[2] = { 0, 0 };                     /* where its next hole is sought from */

/* The lists the last collection left: free blocks, and per space the
 * recyclable ones (some lines free), each a stack of block indices outside
 * the heap */
static size_t *quest_gc_free = NULL, quest_gc_free_n = 0, quest_gc_free_cap = 0;
static size_t *quest_gc_recyclable[2] = { NULL, NULL };
static size_t  quest_gc_recyclable_n[2] = { 0, 0 }, quest_gc_recyclable_cap[2] = { 0, 0 };
static size_t  quest_gc_recyclable_next[2] = { 0, 0 };

/* Sizing: blocks in use, the target they may grow to before a collection,
 * and what has been taken since the last one */
static size_t quest_gc_used = 0;
static size_t quest_gc_target = Q_GC_MIN_HEAP / Q_GC_BLOCK;
static size_t quest_gc_taken_since_collection = 0;
static size_t quest_gc_min_heap_blocks = Q_GC_MIN_HEAP / Q_GC_BLOCK;
#ifdef QUEST_NOGC
static bool quest_gc_never_collect = true;    /* --nogc: allocation only */
#else
static bool quest_gc_never_collect = false;
#endif
static bool quest_gc_collecting = false;

/* The statistics (QUEST_GC_STATS) */
static uint64_t quest_gc_collections = 0;
static uint64_t quest_gc_pause_ns = 0, quest_gc_pause_max_ns = 0;
static uint64_t quest_gc_allocated_blocks = 0;     /* blocks taken over the run, small and large */
static uint64_t quest_gc_hole_bytes = 0;           /* bytes of the holes entered: allocation's volume, about */
static size_t   quest_gc_used_max = 0;
static uint64_t quest_gc_live_bytes = 0, quest_gc_live_bytes_max = 0;   /* at the last collection, headers included */
static uint64_t quest_gc_live_objects = 0;
static uint64_t quest_gc_live_lines = 0, quest_gc_live_lines_max = 0;   /* lines marked, large runs' included */
static uint64_t quest_gc_large_live = 0;
static int      quest_gc_stats = 0;                /* 1: a summary at exit; 2: a line per collection too */

/* The checking modes */
int    quest_gc_check_flags = 0;
size_t quest_gc_check_pending = 0;

Q_NORETURN static void quest_gc_fatal(const char *what) {
    fprintf(stderr, "quest: %s\n", what);
    fflush(stderr);
    exit(70);
}

static uint64_t quest_gc_now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000u + (uint64_t)ts.tv_nsec;
}

/* ---------------------------------------------------------------------------
 * Addresses, bits, and blocks
 * ------------------------------------------------------------------------ */

static inline bool quest_gc_in_heap(uintptr_t w) { return w >= quest_gc_heap_lo && w < quest_gc_heap_hi; }
static inline size_t quest_gc_block_of(uintptr_t a) { return (a - quest_gc_heap_lo) >> Q_GC_BLOCK_BITS; }
static inline uintptr_t quest_gc_block_start(size_t b) { return quest_gc_heap_lo + ((uintptr_t)b << Q_GC_BLOCK_BITS); }
static inline uint8_t *quest_gc_block_lines(size_t b) { return quest_gc_lines + ((size_t)b << (Q_GC_BLOCK_BITS - Q_GC_LINE_BITS)); }
static inline uint8_t *quest_gc_block_bits(uint8_t *bits, size_t b) { return bits + (size_t)b * Q_GC_BLOCK_BITMAP; }

static inline bool quest_gc_bit(const uint8_t *bits, uintptr_t a) {
    uintptr_t i = (a - quest_gc_heap_lo) >> 3;
    return ((bits[i >> 3] >> (i & 7)) & 1u) != 0;
}
static inline void quest_gc_clear_bit(uint8_t *bits, uintptr_t a) {
    uintptr_t i = (a - quest_gc_heap_lo) >> 3;
    bits[i >> 3] &= (uint8_t)~(1u << (i & 7));
}

/* The bytes of an object after its header, rounded to words, by its layout,
 * and the bytes before the object (its header, and a sized allocation's
 * byte count) */
static inline size_t quest_gc_prefix_of(const QLayout *l) { return l->form == Q_LAYOUT_SIZED ? 16 : 8; }
static inline size_t quest_gc_object_bytes(uintptr_t obj, const QLayout *l) {
    size_t n;
    switch (l->form) {
    case Q_LAYOUT_FIXED: n = l->size; break;
    case Q_LAYOUT_ARRAY: {
        int64_t count = *(const int64_t *)(obj + l->length_offset);
        n = l->size + (size_t)(count > 0 ? count : 0) * l->element_words * 8;
        break;
    }
    default: n = quest_sized_bytes((const void *)obj); break;
    }
    return (n + 7) & ~(size_t)7;
}

/* ---------------------------------------------------------------------------
 * The reserve and its metadata
 * ------------------------------------------------------------------------ */

static void *quest_gc_map(size_t bytes) {
    void *p = mmap(NULL, bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
    return p == MAP_FAILED ? NULL : p;
}

/* Reserves the heap (QUEST_GC_RESERVE gigabytes, 64 by default, halved until
 * the system grants it) and maps its metadata, all committed only as touched */
static void quest_gc_setup(void) {
    if (quest_gc_ready) return;
    size_t reserve = Q_GC_RESERVE_DEFAULT;
    const char *env = getenv("QUEST_GC_RESERVE");
    if (env != NULL && env[0] != '\0') {
        unsigned long long gb = strtoull(env, NULL, 10);
        if (gb > 0) reserve = (size_t)gb << 30;
    }
    void *heap = NULL;
    while (reserve >= ((size_t)1 << 30)) {
        heap = quest_gc_map(reserve);
        if (heap != NULL) break;
        reserve /= 2;
    }
    if (heap == NULL) quest_gc_fatal("out of memory: no range can be reserved for the heap");
    /* The first block starts at a block boundary */
    uintptr_t lo = ((uintptr_t)heap + Q_GC_BLOCK - 1) & ~(uintptr_t)(Q_GC_BLOCK - 1);
    quest_gc_heap_lo = lo;
    quest_gc_block_n = (reserve - (lo - (uintptr_t)heap)) >> Q_GC_BLOCK_BITS;
    quest_gc_heap_hi = lo + ((uintptr_t)quest_gc_block_n << Q_GC_BLOCK_BITS);
    quest_gc_blocks = (QBlock *)quest_gc_map(quest_gc_block_n * sizeof(QBlock));
    quest_gc_lines = (uint8_t *)quest_gc_map(quest_gc_block_n * Q_GC_BLOCK_LINES);
    quest_gc_marks = (uint8_t *)quest_gc_map(quest_gc_block_n * Q_GC_BLOCK_BITMAP);
    quest_gc_start_bits = (uint8_t *)quest_gc_map(quest_gc_block_n * Q_GC_BLOCK_BITMAP);
    if (quest_gc_blocks == NULL || quest_gc_lines == NULL || quest_gc_marks == NULL || quest_gc_start_bits == NULL) {
        quest_gc_fatal("out of memory: the heap's metadata cannot be mapped");
    }
    quest_gc_target = quest_gc_min_heap_blocks;
    quest_gc_ready = true;
}

/* ---------------------------------------------------------------------------
 * Taking blocks
 * ------------------------------------------------------------------------ */

static void quest_gc_push(size_t **list, size_t *n, size_t *cap, size_t b) {
    if (*n == *cap) {
        size_t grown = *cap > 0 ? 2 * *cap : 1024;
        size_t *p = (size_t *)realloc(*list, grown * sizeof(size_t));
        if (p == NULL) quest_gc_fatal("out of memory in the collector's lists");
        *list = p;
        *cap = grown;
    }
    (*list)[(*n)++] = b;
}

void quest_gc_collect(void);

/* Whether taking n more blocks should collect first: the heap has reached its
 * target, something was allocated since the last collection (else the live
 * data needs the growth), and collection is on */
static bool quest_gc_should_collect(size_t n) {
    return !quest_gc_never_collect && !quest_gc_collecting && quest_gc_taken_since_collection > 0 &&
           quest_gc_used + n > quest_gc_target;
}

static void quest_gc_took(size_t n) {
    quest_gc_used += n;
    quest_gc_taken_since_collection += n;
    quest_gc_allocated_blocks += n;
    if (quest_gc_used > quest_gc_used_max) quest_gc_used_max = quest_gc_used;
}

/* A free block: one the last collection freed, else a fresh one beyond the
 * high-water mark */
static size_t quest_gc_take_free_block(unsigned space, uint8_t state) {
    size_t b;
    for (;;) {
        if (quest_gc_free_n == 0) {
            if (quest_gc_high_water == quest_gc_block_n) quest_gc_fatal("out of memory: the heap's reserve is used up");
            b = quest_gc_high_water++;
            quest_gc_blocks[b].fresh = 1;
            break;
        }
        b = quest_gc_free[--quest_gc_free_n];
        if (quest_gc_blocks[b].state == QB_FREE) break;  /* else taken by a large run since */
    }
    quest_gc_blocks[b].state = state;
    quest_gc_blocks[b].space = (uint8_t)space;
    quest_gc_blocks[b].run = 0;
    quest_gc_blocks[b].live_lines = 0;
    quest_gc_took(1);
    return b;
}

/* A run of n free blocks: the first fit below the high-water mark, else fresh
 * blocks beyond it */
static size_t quest_gc_take_run(unsigned space, size_t n) {
    size_t run = 0, b = 0;
    for (size_t i = 0; i < quest_gc_high_water; ++i) {
        if (quest_gc_blocks[i].state != QB_FREE) { run = 0; continue; }
        if (++run == n) { b = i + 1 - n; break; }
    }
    bool fresh = false;
    if (run < n) {
        if (quest_gc_high_water + n > quest_gc_block_n) quest_gc_fatal("out of memory: the heap's reserve is used up");
        b = quest_gc_high_water;
        quest_gc_high_water += n;
        fresh = true;
    }
    for (size_t i = 0; i < n; ++i) {
        QBlock *blk = &quest_gc_blocks[b + i];
        blk->state = i == 0 ? QB_LARGE_HEAD : QB_LARGE_TAIL;
        blk->space = (uint8_t)space;
        blk->fresh = fresh ? 1 : blk->fresh;
        blk->run = (uint32_t)(i == 0 ? n : i);
        blk->live_lines = 0;
    }
    quest_gc_took(n);
    return b;
}

/* ---------------------------------------------------------------------------
 * Allocation's slow path
 * ------------------------------------------------------------------------ */

/* Enters the hole of lines [a, a + n) of block b with the cursor of space k,
 * zeroing it unless the block is fresh */
static void quest_gc_enter_hole(uintptr_t *cursor, uintptr_t *limit, unsigned k, size_t b, size_t a, size_t n) {
    uintptr_t start = quest_gc_block_start(b) + ((uintptr_t)a << Q_GC_LINE_BITS);
    size_t bytes = n << Q_GC_LINE_BITS;
    if (!quest_gc_blocks[b].fresh) memset((void *)start, 0, bytes);
    cursor[k] = start;
    limit[k] = start + bytes;
    quest_gc_hole_bytes += bytes;
}

/* Moves the small cursor of space k to the next hole of at least `need`
 * lines in its current block, if there is one */
static bool quest_gc_next_hole(unsigned k, size_t need) {
    size_t b = quest_gc_current[k];
    if (b == Q_GC_NO_BLOCK) return false;
    const uint8_t *lm = quest_gc_block_lines(b);
    size_t i = quest_gc_current_line[k];
    while (i < Q_GC_BLOCK_LINES) {
        while (i < Q_GC_BLOCK_LINES && lm[i] != 0) ++i;
        size_t a = i;
        while (i < Q_GC_BLOCK_LINES && lm[i] == 0) ++i;
        if (i - a >= need) {
            quest_gc_enter_hole(quest_gc_cursor, quest_gc_limit, k, b, a, i - a);
            quest_gc_current_line[k] = i;
            return true;
        }
    }
    quest_gc_current[k] = Q_GC_NO_BLOCK;
    return false;
}

static void *quest_gc_alloc_large(size_t total, unsigned k) {
    size_t n = (total + Q_GC_BLOCK - 1) >> Q_GC_BLOCK_BITS;
    if (quest_gc_should_collect(n)) quest_gc_collect();
    size_t b = quest_gc_take_run(k, n);
    uintptr_t start = quest_gc_block_start(b);
    if (!quest_gc_blocks[b].fresh) memset((void *)start, 0, total);
    quest_gc_hole_bytes += total;
    return (void *)start;
}

/* A medium object, from the overflow cursor of its space, which takes fresh
 * holes (whole free blocks) so that the small cursor's holes are not skipped
 * for want of room */
static void *quest_gc_alloc_medium(size_t total, unsigned k) {
    if (total > quest_gc_over_limit[k] - quest_gc_over_cursor[k]) {
        if (quest_gc_should_collect(1)) quest_gc_collect();
        size_t b = quest_gc_take_free_block(k, QB_SMALL);
        quest_gc_enter_hole(quest_gc_over_cursor, quest_gc_over_limit, k, b, 0, Q_GC_BLOCK_LINES);
    }
    uintptr_t p = quest_gc_over_cursor[k];
    quest_gc_over_cursor[k] = p + total;
    return (void *)p;
}

static void quest_gc_check_tick(size_t sz, size_t header);

/* `total` zeroed bytes (headers included) for an object of the layout, when
 * the inline fast path's hole has no room, or a checking mode is on, which
 * counts the allocation first (and may collect then): the next hole, a
 * recyclable block's, a free block's, or, for medium and large allocations,
 * their own paths; collecting first when the heap has reached its target */
void *quest_gc_alloc_slow(size_t total, const QLayout *layout) {
    if (!quest_gc_ready) quest_gc_setup();
    unsigned k = quest_layout_space(layout);
    if (quest_gc_check_flags != 0) {
        size_t prefix = quest_gc_prefix_of(layout);
        quest_gc_check_tick(total - prefix, prefix);
    }
    if (total >= Q_GC_LARGE) return quest_gc_alloc_large(total, k);
    if (total > Q_GC_MEDIUM) return quest_gc_alloc_medium(total, k);
    size_t need = (total + Q_GC_LINE - 1) >> Q_GC_LINE_BITS;
    for (;;) {
        /* The current hole, which has room when a checking mode sent the
         * allocation here, or the next */
        if (total <= quest_gc_limit[k] - quest_gc_cursor[k]) {
            uintptr_t p = quest_gc_cursor[k];
            quest_gc_cursor[k] = p + total;
            return (void *)p;
        }
        if (quest_gc_next_hole(k, need)) continue;
        if (quest_gc_recyclable_next[k] < quest_gc_recyclable_n[k]) {
            quest_gc_current[k] = quest_gc_recyclable[k][quest_gc_recyclable_next[k]++];
            quest_gc_current_line[k] = 0;
            continue;
        }
        if (quest_gc_should_collect(1)) {
            quest_gc_collect();
            continue;
        }
        quest_gc_current[k] = quest_gc_take_free_block(k, QB_SMALL);
        quest_gc_current_line[k] = 0;
    }
}

/* ---------------------------------------------------------------------------
 * Write barriers and roots
 * ------------------------------------------------------------------------ */

/* How many times each barrier was called: with an object, and with a slot */
static uint64_t quest_barrier_counts[2];

void quest_barrier(const void *obj)   { (void)obj;  quest_barrier_counts[0]++; }
void quest_barrier_slot(const void *slot) { (void)slot; quest_barrier_counts[1]++; }

/* The root tables registered, and the ambiguous regions (the JIT's data),
 * outside the collected heap */
static const QRootEntry **quest_gc_root_tables = NULL;
static size_t             quest_gc_root_table_n = 0;
static size_t             quest_gc_root_table_cap = 0;

void quest_register_roots(const QRootEntry *roots) {
    if (quest_gc_root_table_n == quest_gc_root_table_cap) {
        size_t cap = quest_gc_root_table_cap > 0 ? 2 * quest_gc_root_table_cap : 64;
        const QRootEntry **grown = (const QRootEntry **)realloc((void *)quest_gc_root_tables, cap * sizeof *grown);
        if (grown == NULL) quest_gc_fatal("out of memory registering roots");
        quest_gc_root_tables = grown;
        quest_gc_root_table_cap = cap;
    }
    quest_gc_root_tables[quest_gc_root_table_n++] = roots;
}

typedef struct QRootRegion { uintptr_t low, high; } QRootRegion;
static QRootRegion *quest_gc_regions = NULL;
static size_t       quest_gc_region_n = 0, quest_gc_region_cap = 0;

void quest_gc_add_roots(void *low, void *high) {
    if (quest_gc_region_n == quest_gc_region_cap) {
        size_t cap = quest_gc_region_cap > 0 ? 2 * quest_gc_region_cap : 16;
        QRootRegion *grown = (QRootRegion *)realloc(quest_gc_regions, cap * sizeof *grown);
        if (grown == NULL) quest_gc_fatal("out of memory registering roots");
        quest_gc_regions = grown;
        quest_gc_region_cap = cap;
    }
    quest_gc_regions[quest_gc_region_n].low = ((uintptr_t)low + 7) & ~(uintptr_t)7;
    quest_gc_regions[quest_gc_region_n].high = (uintptr_t)high & ~(uintptr_t)7;
    quest_gc_region_n++;
}

/* ---------------------------------------------------------------------------
 * Marking
 * ------------------------------------------------------------------------ */

/* The work list: marked objects whose words are still to be scanned */
static uintptr_t *quest_gc_work = NULL;
static size_t     quest_gc_work_n = 0, quest_gc_work_cap = 0;

static void quest_gc_push_work(uintptr_t obj) {
    if (quest_gc_work_n == quest_gc_work_cap) {
        size_t cap = quest_gc_work_cap > 0 ? 2 * quest_gc_work_cap : 4096;
        uintptr_t *grown = (uintptr_t *)realloc(quest_gc_work, cap * sizeof *grown);
        if (grown == NULL) quest_gc_fatal("out of memory in the collector's work list");
        quest_gc_work = grown;
        quest_gc_work_cap = cap;
    }
    quest_gc_work[quest_gc_work_n++] = obj;
}

/* The object of block b (a small one) that starts at or before a, by the
 * start bits, or 0 if none does */
static uintptr_t quest_gc_start_before(size_t b, uintptr_t a) {
    uintptr_t first = (quest_gc_block_start(b) - quest_gc_heap_lo) >> 3;  /* the block's first word's index */
    uintptr_t wi = (a - quest_gc_heap_lo) >> 3;
    size_t byte = wi >> 3, first_byte = first >> 3;
    unsigned m = quest_gc_start_bits[byte] & ((2u << (wi & 7)) - 1u);
    while (m == 0) {
        if (byte == first_byte) return 0;
        m = quest_gc_start_bits[--byte];
    }
    unsigned hi = 31u - (unsigned)__builtin_clz(m);
    return quest_gc_heap_lo + (((uintptr_t)byte * 8 + hi) << 3);
}

/* The object of a large run headed by block b: the first start bit of the
 * block, after a header, or after a size and a header */
static uintptr_t quest_gc_large_object(size_t b) {
    uintptr_t start = quest_gc_block_start(b);
    if (quest_gc_bit(quest_gc_start_bits, start + 8)) return start + 8;
    if (quest_gc_bit(quest_gc_start_bits, start + 16)) return start + 16;
    return 0;
}

static void quest_gc_mark_object(uintptr_t obj) {
    uintptr_t i = (obj - quest_gc_heap_lo) >> 3;
    uint8_t *mb = &quest_gc_marks[i >> 3];
    uint8_t bit = (uint8_t)(1u << (i & 7));
    if ((*mb & bit) != 0) return;
    *mb |= bit;
    const QLayout *l = quest_layout_of((const void *)obj);
    ((uintptr_t *)obj)[-1] |= Q_HEADER_OLD;
    size_t prefix = quest_gc_prefix_of(l);
    size_t size = quest_gc_object_bytes(obj, l);
    quest_gc_live_bytes += prefix + size;
    quest_gc_live_objects++;
    size_t b = quest_gc_block_of(obj);
    if (quest_gc_blocks[b].state == QB_SMALL) {
        uintptr_t from = (obj - prefix - quest_gc_heap_lo) >> Q_GC_LINE_BITS;
        uintptr_t to = (obj + size - 1 - quest_gc_heap_lo) >> Q_GC_LINE_BITS;
        for (uintptr_t ln = from; ln <= to; ++ln) quest_gc_lines[ln] = 1;
    } else {
        quest_gc_large_live += prefix + size;
    }
    if ((l->flags & Q_LAYOUT_NOSCAN) == 0) quest_gc_push_work(obj);
}

/* Whether the object at obj (a small block's) extends to or past a: a word
 * at its end counts as its (section 3.3) */
static inline bool quest_gc_reaches(uintptr_t obj, uintptr_t a) {
    return a <= obj + quest_gc_object_bytes(obj, quest_layout_of((const void *)obj));
}

/* Marks what the word w refers to, if anything: for a precise word, the
 * object it points at or into; for an ambiguous one, every object the word
 * may stand for (section 3.3): the one it is at or inside, the one it is at
 * the end of, and the one whose header or byte count it is at (a C compiler
 * keeps the address an allocation returned before the header was skipped, and
 * forms a loop's end from an array's base) */
static void quest_gc_mark_word(uintptr_t w, bool ambiguous) {
    if (!quest_gc_in_heap(w)) return;
    uintptr_t a = w & ~(uintptr_t)7;
    size_t b = quest_gc_block_of(a);
    const QBlock *blk = &quest_gc_blocks[b];
    if (blk->state == QB_FREE) return;
    if (blk->state == QB_LARGE_TAIL) {
        b -= blk->run;
        blk = &quest_gc_blocks[b];
    }
    if (blk->state == QB_LARGE_HEAD) {
        uintptr_t obj = quest_gc_large_object(b);
        if (obj != 0 && (a < obj ? ambiguous : quest_gc_reaches(obj, a))) quest_gc_mark_object(obj);
        return;
    }
    uintptr_t obj = quest_gc_start_before(b, a);
    if (obj != 0 && quest_gc_reaches(obj, a)) {
        quest_gc_mark_object(obj);
        if (ambiguous && obj == a) {
            /* The object that ends where this one begins, if one does */
            uintptr_t before = quest_gc_start_before(b, a - 8);
            if (before != 0 && before + quest_gc_object_bytes(before, quest_layout_of((const void *)before)) == a) {
                quest_gc_mark_object(before);
            }
        }
    }
    if (!ambiguous) return;
    /* The object whose header, or whose byte count and header, the word is at */
    uintptr_t next = a + 8;
    if (quest_gc_block_of(next) == b && quest_gc_bit(quest_gc_start_bits, next)) {
        quest_gc_mark_object(next);
    } else if (quest_gc_block_of(next + 8) == b && quest_gc_bit(quest_gc_start_bits, next + 8) &&
               quest_layout_of((const void *)(next + 8))->form == Q_LAYOUT_SIZED) {
        quest_gc_mark_object(next + 8);
    }
}

static void quest_gc_mark_words(const uintptr_t *words, size_t n, const uint8_t *kinds) {
    for (size_t i = 0; i < n; ++i) {
        if (kinds[i] == Q_WORD_POINTER) quest_gc_mark_word(words[i], false);
        else if (kinds[i] == Q_WORD_AMBIGUOUS) quest_gc_mark_word(words[i], true);
    }
}

/* Scans a marked object's words by its layout */
static void quest_gc_scan_object(uintptr_t obj) {
    const QLayout *l = quest_layout_of((const void *)obj);
    const uintptr_t *words = (const uintptr_t *)obj;
    switch (l->form) {
    case Q_LAYOUT_FIXED:
        quest_gc_mark_words(words, l->words, l->kinds);
        break;
    case Q_LAYOUT_ARRAY: {
        quest_gc_mark_words(words, l->words, l->kinds);
        int64_t n = *(const int64_t *)(obj + l->length_offset);
        const uintptr_t *e = words + l->size / 8;
        const uint8_t *kinds = l->kinds + l->words;
        for (int64_t i = 0; i < n; ++i, e += l->element_words) quest_gc_mark_words(e, l->element_words, kinds);
        break;
    }
    default: {
        size_t n = quest_sized_bytes((const void *)obj) / 8;
        for (size_t i = 0; i < n; ++i) {
            uint8_t kind = l->kinds[i % l->element_words];
            if (kind == Q_WORD_POINTER) quest_gc_mark_word(words[i], false);
            else if (kind == Q_WORD_AMBIGUOUS) quest_gc_mark_word(words[i], true);
        }
        break;
    }
    }
}

static void quest_gc_scan_range(const uintptr_t *p, const uintptr_t *end) {
    for (; p < end; ++p) quest_gc_mark_word(*p, true);
}

/* A root slot of `words` words, scanned as ambiguous: a root table's entry
 * may be a global of generic code, and validation costs nothing wrong */
static void quest_gc_mark_root(void *slot, size_t words) {
    quest_gc_scan_range((const uintptr_t *)slot, (const uintptr_t *)slot + words);
}

/* The stack, conservatively, from here to its base, the registers first
 * spilled into a jmp_buf on it */
static void quest_gc_scan_stack(void) {
    jmp_buf regs;
    setjmp(regs);
    uintptr_t base;
#if defined(__APPLE__)
    base = (uintptr_t)pthread_get_stackaddr_np(pthread_self());
#else
    pthread_attr_t attr;
    void *low = NULL;
    size_t size = 0;
    base = 0;
    if (pthread_getattr_np(pthread_self(), &attr) == 0) {
        if (pthread_attr_getstack(&attr, &low, &size) == 0) base = (uintptr_t)low + size;
        pthread_attr_destroy(&attr);
    }
    if (base == 0) quest_gc_fatal("the collector cannot find the stack's base");
#endif
    const uintptr_t *from = (const uintptr_t *)((uintptr_t)&regs & ~(uintptr_t)7);
    quest_gc_scan_range(from, (const uintptr_t *)(base & ~(uintptr_t)7));
}

static void quest_gc_mark_roots(void) {
    for (size_t i = 0; i < quest_gc_root_table_n; ++i) {
        for (const QRootEntry *e = quest_gc_root_tables[i]; e->slot != NULL; ++e) quest_gc_mark_root(e->slot, e->words);
    }
    quest_runtime_roots(quest_gc_mark_root);
    quest_code_roots(quest_gc_mark_root);
    for (size_t i = 0; i < quest_gc_region_n; ++i) {
        quest_gc_scan_range((const uintptr_t *)quest_gc_regions[i].low, (const uintptr_t *)quest_gc_regions[i].high);
    }
    quest_gc_scan_stack();
}

/* ---------------------------------------------------------------------------
 * Collection
 * ------------------------------------------------------------------------ */

static bool quest_gc_poison = false;

/* Fills the free lines of a small block with the poison byte */
static void quest_gc_poison_block(size_t b) {
    const uint8_t *lm = quest_gc_block_lines(b);
    uintptr_t start = quest_gc_block_start(b);
    for (size_t i = 0; i < Q_GC_BLOCK_LINES; ++i) {
        if (lm[i] == 0) memset((void *)(start + (i << Q_GC_LINE_BITS)), Q_GC_POISON, Q_GC_LINE);
    }
}

/* Before marking: every block in use has its marks cleared, and a small one
 * its line marks, which the marker sets afresh */
static void quest_gc_clear_marks(void) {
    for (size_t b = 0; b < quest_gc_high_water; ++b) {
        const QBlock *blk = &quest_gc_blocks[b];
        if (blk->state == QB_FREE) continue;
        memset(quest_gc_block_bits(quest_gc_marks, b), 0, Q_GC_BLOCK_BITMAP);
        if (blk->state == QB_SMALL) memset(quest_gc_block_lines(b), 0, Q_GC_BLOCK_LINES);
    }
}

/* After marking: only live objects keep their start bits, dead large runs
 * are freed, and every block is classified by its live lines, free and
 * recyclable ones listed for the allocators, whose cursors start over */
static void quest_gc_sweep(void) {
    quest_gc_used = 0;
    quest_gc_live_lines = 0;
    quest_gc_free_n = 0;
    for (unsigned k = 0; k < 2; ++k) {
        quest_gc_recyclable_n[k] = 0;
        quest_gc_recyclable_next[k] = 0;
        quest_gc_cursor[k] = quest_gc_limit[k] = 0;
        quest_gc_over_cursor[k] = quest_gc_over_limit[k] = 0;
        quest_gc_current[k] = Q_GC_NO_BLOCK;
        quest_gc_current_line[k] = 0;
    }
    for (size_t b = 0; b < quest_gc_high_water; ++b) {
        QBlock *blk = &quest_gc_blocks[b];
        switch (blk->state) {
        case QB_FREE:
            quest_gc_push(&quest_gc_free, &quest_gc_free_n, &quest_gc_free_cap, b);
            break;
        case QB_SMALL: {
            uint64_t *starts = (uint64_t *)quest_gc_block_bits(quest_gc_start_bits, b);
            const uint64_t *marks = (const uint64_t *)quest_gc_block_bits(quest_gc_marks, b);
            for (size_t i = 0; i < Q_GC_BLOCK_BITMAP / 8; ++i) starts[i] &= marks[i];
            const uint8_t *lm = quest_gc_block_lines(b);
            uint32_t live = 0;
            for (size_t i = 0; i < Q_GC_BLOCK_LINES; ++i) live += lm[i];
            blk->fresh = 0;
            blk->live_lines = live;
            if (live == 0) {
                blk->state = QB_FREE;
                if (quest_gc_poison) memset((void *)quest_gc_block_start(b), Q_GC_POISON, Q_GC_BLOCK);
                quest_gc_push(&quest_gc_free, &quest_gc_free_n, &quest_gc_free_cap, b);
            } else {
                quest_gc_used++;
                quest_gc_live_lines += live;
                if (live < Q_GC_BLOCK_LINES) {
                    unsigned k = blk->space;
                    quest_gc_push(&quest_gc_recyclable[k], &quest_gc_recyclable_n[k], &quest_gc_recyclable_cap[k], b);
                    if (quest_gc_poison) quest_gc_poison_block(b);
                }
            }
            break;
        }
        case QB_LARGE_HEAD: {
            size_t run = blk->run;
            uintptr_t obj = quest_gc_large_object(b);
            if (obj != 0 && quest_gc_bit(quest_gc_marks, obj)) {
                quest_gc_used += run;
                quest_gc_live_lines += run * Q_GC_BLOCK_LINES;
                blk->fresh = 0;
            } else {
                if (obj != 0) quest_gc_clear_bit(quest_gc_start_bits, obj);
                if (quest_gc_poison) memset((void *)quest_gc_block_start(b), Q_GC_POISON, run * Q_GC_BLOCK);
                for (size_t i = 0; i < run; ++i) {
                    quest_gc_blocks[b + i].state = QB_FREE;
                    quest_gc_blocks[b + i].fresh = 0;
                    quest_gc_push(&quest_gc_free, &quest_gc_free_n, &quest_gc_free_cap, b + i);
                }
            }
            b += run - 1;
            break;
        }
        default:
            quest_gc_fatal("the collector found a large run's tail without its head");
        }
    }
    /* The free list is popped from its end: the lowest blocks first */
    for (size_t i = 0, j = quest_gc_free_n; i + 1 < j; ++i, --j) {
        size_t t = quest_gc_free[i];
        quest_gc_free[i] = quest_gc_free[j - 1];
        quest_gc_free[j - 1] = t;
    }
    size_t target = Q_GC_GROWTH * quest_gc_used;
    quest_gc_target = target > quest_gc_min_heap_blocks ? target : quest_gc_min_heap_blocks;
    quest_gc_taken_since_collection = 0;
}

static void quest_gc_check_heap(void);
static void quest_gc_check_roots(void);

/* Stops the world (there is one mutator, and it is here), marks, and sweeps */
void quest_gc_collect(void) {
    if (!quest_gc_ready) quest_gc_setup();
    if (quest_gc_collecting) return;
    quest_gc_collecting = true;
    uint64_t t0 = quest_gc_now_ns();
    quest_gc_collections++;
    quest_gc_live_bytes = 0;
    quest_gc_live_objects = 0;
    quest_gc_large_live = 0;
    quest_gc_work_n = 0;
    quest_gc_clear_marks();
    quest_gc_mark_roots();
    while (quest_gc_work_n > 0) quest_gc_scan_object(quest_gc_work[--quest_gc_work_n]);
    quest_gc_sweep();
    uint64_t pause = quest_gc_now_ns() - t0;
    quest_gc_pause_ns += pause;
    if (pause > quest_gc_pause_max_ns) quest_gc_pause_max_ns = pause;
    if (quest_gc_live_bytes > quest_gc_live_bytes_max) quest_gc_live_bytes_max = quest_gc_live_bytes;
    if (quest_gc_live_lines > quest_gc_live_lines_max) quest_gc_live_lines_max = quest_gc_live_lines;
    if (quest_gc_stats >= 2) {
        fprintf(stderr, "quest: gc #%" PRIu64 ": live %" PRIu64 " KB in %" PRIu64 " KB of lines, heap %zu KB, "
                "%.2f ms\n", quest_gc_collections, quest_gc_live_bytes >> 10, (quest_gc_live_lines * Q_GC_LINE) >> 10,
                (quest_gc_used * Q_GC_BLOCK) >> 10, (double)pause / 1e6);
    }
    if ((quest_gc_check_flags & QUEST_GC_CHECK_LAYOUTS) != 0) quest_gc_check_heap();
    if ((quest_gc_check_flags & QUEST_GC_CHECK_ROOTS) != 0) quest_gc_check_roots();
    quest_gc_collecting = false;
}

/* ---------------------------------------------------------------------------
 * The checking modes
 * ------------------------------------------------------------------------ */

/* How many bytes are allocated between the collections a check mode forces:
 * the default, and QUEST_GC_CHECK_INTERVAL in bytes */
static size_t quest_gc_check_interval = 64u << 20;

/* Counts per layout, for the report */
typedef struct QLayoutCount {
    const QLayout *layout;
    uint64_t       objects;
    uint64_t       ambiguous;         /* ambiguous words */
    uint64_t       suspicious;        /* scalar words that are addresses of heap objects */
    uint64_t       ambiguous_heap;    /* ambiguous words that are addresses of heap objects */
} QLayoutCount;

static QLayoutCount *quest_gc_counts = NULL;
static size_t        quest_gc_count_n = 0;
static size_t        quest_gc_count_cap = 0;
static uint64_t      quest_gc_checks = 0;
static uint64_t      quest_gc_objects_checked = 0;
/* What was allocated while a mode was on: objects, their bytes, and their
 * headers' bytes */
static uint64_t      quest_gc_allocated_objects = 0;
static uint64_t      quest_gc_allocated_bytes = 0;
static uint64_t      quest_gc_allocated_headers = 0;

static QLayoutCount *quest_gc_count_of(const QLayout *layout) {
    for (size_t i = 0; i < quest_gc_count_n; ++i) {
        if (quest_gc_counts[i].layout == layout) return &quest_gc_counts[i];
    }
    if (quest_gc_count_n == quest_gc_count_cap) {
        size_t cap = quest_gc_count_cap > 0 ? 2 * quest_gc_count_cap : 64;
        /* The counts are the checker's own, outside the collected heap */
        QLayoutCount *grown = (QLayoutCount *)realloc(quest_gc_counts, cap * sizeof(QLayoutCount));
        if (grown == NULL) quest_gc_fatal("gc check: out of memory");
        quest_gc_counts = grown;
        quest_gc_count_cap = cap;
    }
    QLayoutCount *c = &quest_gc_counts[quest_gc_count_n++];
    memset(c, 0, sizeof *c);
    c->layout = layout;
    return c;
}

Q_NORETURN static void quest_gc_check_fail(const QLayout *layout, const void *obj, const char *what, size_t word,
                                           uintptr_t value) {
    fprintf(stderr, "quest: gc check: layout %s: object %p: %s", layout->name, obj, what);
    if (word != (size_t)-1) fprintf(stderr, " at word %zu (value %#" PRIxPTR ")", word, value);
    fputc('\n', stderr);
    /* The object's first words, for the diagnosis */
    size_t n = layout->form == Q_LAYOUT_FIXED ? layout->words : word + 4;
    if (n > 16) n = 16;
    fprintf(stderr, "quest: gc check: words:");
    for (size_t i = 0; i < n; ++i) fprintf(stderr, " %#" PRIxPTR, ((const uintptr_t *)obj)[i]);
    fputc('\n', stderr);
    fflush(stderr);
    abort();
}

/* Whether w is the address of (or into) a live object */
static bool quest_gc_is_object(uintptr_t w) {
    if (!quest_gc_in_heap(w)) return false;
    uintptr_t a = w & ~(uintptr_t)7;
    size_t b = quest_gc_block_of(a);
    const QBlock *blk = &quest_gc_blocks[b];
    if (blk->state == QB_FREE) return false;
    if (blk->state == QB_LARGE_TAIL) {
        b -= blk->run;
        blk = &quest_gc_blocks[b];
    }
    uintptr_t obj = blk->state == QB_LARGE_HEAD ? quest_gc_large_object(b) : quest_gc_start_before(b, a);
    if (obj == 0 || a < obj) return false;
    return a < obj + quest_gc_object_bytes(obj, quest_layout_of((const void *)obj));
}

/* Checks one word of kind `kind` */
static void quest_gc_check_word(const QLayout *layout, const void *obj, QLayoutCount *c, size_t word, uint8_t kind) {
    uintptr_t w = ((const uintptr_t *)obj)[word];
    switch (kind) {
    case Q_WORD_POINTER:
        /* Null, outside the heap (static data, code, the stack), or an
         * object's address or inside one (a proxy's tagged address, a
         * record's payload, an embedded box); a live object's pointer to
         * nothing live is a lying layout, since only live objects validate */
        if (w != 0 && quest_gc_in_heap(w) && !quest_gc_is_object(w)) {
            quest_gc_check_fail(layout, obj, "a pointer into the heap at nothing live", word, w);
        }
        break;
    case Q_WORD_SCALAR:
        if (w != 0 && quest_gc_is_object(w)) c->suspicious++;
        break;
    case Q_WORD_AMBIGUOUS:
        c->ambiguous++;
        if (w != 0 && quest_gc_is_object(w)) c->ambiguous_heap++;
        break;
    default:
        quest_gc_check_fail(layout, obj, "a word of an unknown kind in its layout", word, (uintptr_t)kind);
    }
}

/* Checks a live object: its layout, its place (after the previous object,
 * on lines the marker marked), and each described word; returns its end */
static uintptr_t quest_gc_check_object(uintptr_t obj, uintptr_t prev_end, bool small) {
    const QLayout *layout = quest_layout_of((const void *)obj);
    const uintptr_t *words = (const uintptr_t *)obj;
    if (layout == NULL || quest_gc_in_heap((uintptr_t)layout) || layout->form > Q_LAYOUT_SIZED) {
        fprintf(stderr, "quest: gc check: object %p: a header naming no layout (%#" PRIxPTR ")\n", (const void *)obj,
                words[-1]);
        fflush(stderr);
        abort();
    }
    size_t prefix = quest_gc_prefix_of(layout);
    if (obj - prefix < prev_end) quest_gc_check_fail(layout, (const void *)obj, "overlaps the object before it", (size_t)-1, 0);
    if (layout->form == Q_LAYOUT_SIZED && (words[-2] & 1u) == 0) {
        quest_gc_check_fail(layout, (const void *)obj, "a sized layout on an allocation without a size", (size_t)-1, 0);
    }
    size_t size = quest_gc_object_bytes(obj, layout);
    if (small) {
        for (uintptr_t a = obj - prefix; a < obj + size; a += Q_GC_LINE) {
            if (quest_gc_lines[(a - quest_gc_heap_lo) >> Q_GC_LINE_BITS] == 0) {
                quest_gc_check_fail(layout, (const void *)obj, "on a line the marker left free", (size_t)-1, a);
            }
        }
    }
    QLayoutCount *c = quest_gc_count_of(layout);
    quest_gc_objects_checked++;
    c->objects++;
    if ((layout->flags & Q_LAYOUT_NOSCAN) != 0) return obj + size;
    switch (layout->form) {
    case Q_LAYOUT_FIXED:
        if (layout->words != (layout->size + 7) / 8) {
            quest_gc_check_fail(layout, (const void *)obj, "a layout whose words do not cover its size", (size_t)-1, 0);
        }
        for (size_t i = 0; i < layout->words; ++i) quest_gc_check_word(layout, (const void *)obj, c, i, layout->kinds[i]);
        break;
    case Q_LAYOUT_ARRAY: {
        int64_t n = *(const int64_t *)(obj + layout->length_offset);
        if (n < 0) quest_gc_check_fail(layout, (const void *)obj, "a negative element count", (size_t)-1, (uintptr_t)n);
        for (size_t i = 0; i < layout->words; ++i) quest_gc_check_word(layout, (const void *)obj, c, i, layout->kinds[i]);
        size_t word = layout->size / 8;
        for (int64_t e = 0; e < n; ++e) {
            for (size_t k = 0; k < layout->element_words; ++k) {
                quest_gc_check_word(layout, (const void *)obj, c, word++, layout->kinds[layout->words + k]);
            }
        }
        break;
    }
    default: {
        size_t words_in = size / 8;
        for (size_t word = 0; word < words_in; ++word) {
            quest_gc_check_word(layout, (const void *)obj, c, word, layout->kinds[word % layout->element_words]);
        }
        break;
    }
    }
    return obj + size;
}

/* After a collection: walks every live object (the start bits, which the
 * sweep intersected with the marks) by its layout */
static void quest_gc_check_heap(void) {
    quest_gc_checks++;
    for (size_t b = 0; b < quest_gc_high_water; ++b) {
        const QBlock *blk = &quest_gc_blocks[b];
        if (blk->state == QB_LARGE_HEAD) {
            uintptr_t obj = quest_gc_large_object(b);
            if (obj != 0) quest_gc_check_object(obj, quest_gc_block_start(b), false);
            b += blk->run - 1;
            continue;
        }
        if (blk->state != QB_SMALL) continue;
        const uint8_t *starts = quest_gc_block_bits(quest_gc_start_bits, b);
        uintptr_t prev_end = quest_gc_block_start(b);
        for (size_t i = 0; i < Q_GC_BLOCK_BITMAP; ++i) {
            unsigned m = starts[i];
            while (m != 0) {
                unsigned bit = (unsigned)__builtin_ctz(m);
                m &= m - 1;
                uintptr_t obj = quest_gc_block_start(b) + (((uintptr_t)i * 8 + bit) << 3);
                prev_end = quest_gc_check_object(obj, prev_end, true);
            }
        }
    }
}

/* The roots check: every word of the program's data segment that is the
 * address of (or into) a heap object must lie in a registered root table or
 * in a root the runtime lists, or the collector would not know it. The
 * covered slots are gathered on each check (a few hundred); an uncovered
 * word is reported with its symbol, and the program fails at exit. */
typedef struct QRootSlot { uintptr_t low, high; } QRootSlot;
static QRootSlot *quest_gc_covered = NULL;
static size_t     quest_gc_covered_n = 0, quest_gc_covered_cap = 0;
static uint64_t   quest_gc_uncovered = 0;

static void quest_gc_cover(void *slot, size_t words) {
    if (quest_gc_covered_n == quest_gc_covered_cap) {
        size_t cap = quest_gc_covered_cap > 0 ? 2 * quest_gc_covered_cap : 256;
        QRootSlot *grown = (QRootSlot *)realloc(quest_gc_covered, cap * sizeof *grown);
        if (grown == NULL) quest_gc_fatal("gc check: out of memory");
        quest_gc_covered = grown;
        quest_gc_covered_cap = cap;
    }
    quest_gc_covered[quest_gc_covered_n].low = (uintptr_t)slot;
    quest_gc_covered[quest_gc_covered_n].high = (uintptr_t)slot + 8 * words;
    quest_gc_covered_n++;
}

static bool quest_gc_is_covered(uintptr_t address) {
    for (size_t i = 0; i < quest_gc_covered_n; ++i) {
        if (address >= quest_gc_covered[i].low && address < quest_gc_covered[i].high) return true;
    }
    return false;
}

/* The words of one segment of static data */
static void quest_gc_scan_segment(const char *name, const uintptr_t *low, const uintptr_t *high) {
    for (const uintptr_t *p = low; p < high; ++p) {
        uintptr_t w = *p;
        if (w == 0 || !quest_gc_is_object(w)) continue;
        if (quest_gc_is_covered((uintptr_t)p)) continue;
        quest_gc_uncovered++;
        const char *symbol = "?";
        Dl_info info;
        if (dladdr((const void *)p, &info) != 0 && info.dli_sname != NULL) symbol = info.dli_sname;
        fprintf(stderr, "quest: gc check: root %p (%s, in %s) holds the heap pointer %#" PRIxPTR
                " but no root table or listed root covers it\n", (const void *)p, symbol, name, w);
    }
}

/* The collector's own words that may hold heap addresses (its cursors) or
 * values that look like them (its counters), passed over as a covered root
 * would be */
static void quest_gc_skip_own(void) {
    quest_gc_cover(quest_gc_cursor, 2);
    quest_gc_cover(quest_gc_limit, 2);
    quest_gc_cover(quest_gc_over_cursor, 2);
    quest_gc_cover(quest_gc_over_limit, 2);
    quest_gc_cover(&quest_gc_heap_lo, 1);
    quest_gc_cover(&quest_gc_heap_hi, 1);
    quest_gc_cover(&quest_gc_check_pending, 1);
    quest_gc_cover(&quest_gc_check_interval, 1);
    quest_gc_cover(quest_barrier_counts, 2);
    quest_gc_cover(&quest_gc_checks, 1);
    quest_gc_cover(&quest_gc_objects_checked, 1);
    quest_gc_cover(&quest_gc_allocated_objects, 1);
    quest_gc_cover(&quest_gc_allocated_bytes, 1);
    quest_gc_cover(&quest_gc_allocated_headers, 1);
    quest_gc_cover(&quest_gc_uncovered, 1);
    quest_gc_cover(&quest_gc_count_n, 1);
    quest_gc_cover(&quest_gc_count_cap, 1);
    quest_gc_cover(&quest_gc_root_table_n, 1);
    quest_gc_cover(&quest_gc_root_table_cap, 1);
    quest_gc_cover(&quest_gc_covered_n, 1);
    quest_gc_cover(&quest_gc_covered_cap, 1);
    quest_gc_cover(&quest_gc_pause_ns, 1);
    quest_gc_cover(&quest_gc_pause_max_ns, 1);
    quest_gc_cover(&quest_gc_allocated_blocks, 1);
    quest_gc_cover(&quest_gc_hole_bytes, 1);
    quest_gc_cover(&quest_gc_live_bytes, 1);
    quest_gc_cover(&quest_gc_live_bytes_max, 1);
    quest_gc_cover(&quest_gc_live_objects, 1);
    quest_gc_cover(&quest_gc_live_lines, 1);
    quest_gc_cover(&quest_gc_live_lines_max, 1);
    quest_gc_cover(&quest_gc_large_live, 1);
    quest_gc_cover(&quest_gc_collections, 1);
}

static void quest_gc_check_roots(void) {
    quest_gc_covered_n = 0;
    quest_gc_skip_own();
    for (size_t i = 0; i < quest_gc_root_table_n; ++i) {
        for (const QRootEntry *e = quest_gc_root_tables[i]; e->slot != NULL; ++e) quest_gc_cover(e->slot, e->words);
    }
    quest_runtime_roots(quest_gc_cover);
    quest_code_roots(quest_gc_cover);
#if defined(__APPLE__)
    unsigned long size = 0;
    const uint8_t *data = getsegmentdata(&_mh_execute_header, "__DATA", &size);
    if (data != NULL) {
        quest_gc_scan_segment("__DATA", (const uintptr_t *)data, (const uintptr_t *)(data + size - size % 8));
    }
#elif defined(__linux__)
    quest_gc_scan_segment("data", (const uintptr_t *)__data_start, (const uintptr_t *)_end);
#endif
}

/* A check walks the whole heap, so between the collections a mode forces at
 * least four times the heap's size is allocated, whatever the interval asks,
 * which keeps the checks to a fraction of a program's time however large its
 * heap */
static size_t quest_gc_check_due(void) {
    size_t due = quest_gc_check_interval;
    size_t heap = 4 * quest_gc_used * Q_GC_BLOCK;
    if (heap > due) due = heap;
    return due;
}

/* The `allocations` mode (benchmarks/mlton/allocations.py): the allocations
 * and their bytes by the two return addresses above the allocation, the
 * allocating function's (compiled code's, or a runtime function's) and its
 * caller's, in an open-addressed table outside the heap; at exit a line
 * "address1 address2 count bytes" per pair goes to $QUEST_ALLOCATIONS_OUT,
 * each address relative to the program's image as `atos -l 0x100000000` reads
 * it, or 0 when it is not in the program */
#define Q_GC_ALLOCATION_SLOTS (1 << 18)
static uintptr_t     *quest_gc_allocation_keys1, *quest_gc_allocation_keys2;
static unsigned long *quest_gc_allocation_counts, *quest_gc_allocation_bytes;

static void quest_gc_note_allocation(uintptr_t ra1, uintptr_t ra2, size_t n) {
    if (quest_gc_allocation_keys1 == NULL) {
        quest_gc_allocation_keys1 = (uintptr_t *)calloc(Q_GC_ALLOCATION_SLOTS, sizeof(uintptr_t));
        quest_gc_allocation_keys2 = (uintptr_t *)calloc(Q_GC_ALLOCATION_SLOTS, sizeof(uintptr_t));
        quest_gc_allocation_counts = (unsigned long *)calloc(Q_GC_ALLOCATION_SLOTS, sizeof(unsigned long));
        quest_gc_allocation_bytes = (unsigned long *)calloc(Q_GC_ALLOCATION_SLOTS, sizeof(unsigned long));
        if (quest_gc_allocation_bytes == NULL) quest_gc_fatal("gc check: out of memory");
    }
    size_t i = ((ra1 >> 2) ^ (ra2 >> 4)) & (Q_GC_ALLOCATION_SLOTS - 1);
    size_t probes = 0;
    while (quest_gc_allocation_keys1[i] != 0 &&
           (quest_gc_allocation_keys1[i] != ra1 || quest_gc_allocation_keys2[i] != ra2)) {
        i = (i + 1) & (Q_GC_ALLOCATION_SLOTS - 1);
        if (++probes == Q_GC_ALLOCATION_SLOTS) quest_gc_fatal("gc check: too many allocation sites");
    }
    quest_gc_allocation_keys1[i] = ra1;
    quest_gc_allocation_keys2[i] = ra2;
    quest_gc_allocation_counts[i]++;
    quest_gc_allocation_bytes[i] += n;
}

static unsigned long quest_gc_relative_address(uintptr_t address) {
#if defined(__APPLE__)
    Dl_info info;
    if (address == 0 || dladdr((void *)address, &info) == 0 || info.dli_fbase != (void *)_NSGetMachExecuteHeader()) {
        return 0;
    }
    return (unsigned long)(address - (uintptr_t)info.dli_fbase + 0x100000000ul);
#else
    return (unsigned long)address;
#endif
}

static void quest_gc_dump_allocations(void) {
    const char *path = getenv("QUEST_ALLOCATIONS_OUT");
    FILE *f = fopen(path != NULL ? path : "/dev/stderr", "w");
    if (f == NULL || quest_gc_allocation_keys1 == NULL) return;
    for (size_t i = 0; i < Q_GC_ALLOCATION_SLOTS; ++i) {
        if (quest_gc_allocation_keys1[i] == 0) continue;
        fprintf(f, "%#lx %#lx %lu %lu\n", quest_gc_relative_address(quest_gc_allocation_keys1[i]),
                quest_gc_relative_address(quest_gc_allocation_keys2[i]), quest_gc_allocation_counts[i],
                quest_gc_allocation_bytes[i]);
    }
    fclose(f);
}

/* The `collect` mode's forcing by count (tools/perf/retention.py): a
 * collection every QUEST_GC_COLLECT_EVERY allocations, "FORCED k" on standard
 * error before the kth, and with QUEST_GC_COLLECT_TRAP=k a call of
 * quest_gc_trap, for a debugger's breakpoint, just before the kth and no
 * forcing after it */
static uint64_t quest_gc_collect_every = 0, quest_gc_collect_trap = 0, quest_gc_forced = 0;

__attribute__((noinline, used)) void quest_gc_trap(void) { __asm__ volatile(""); }

static void quest_gc_force_by_count(void) {
    if (quest_gc_collect_every == 0 || quest_gc_allocated_objects % quest_gc_collect_every != 0) return;
    if (quest_gc_collect_trap != 0 && quest_gc_forced >= quest_gc_collect_trap) return;
    quest_gc_forced++;
    if (quest_gc_forced == quest_gc_collect_trap) quest_gc_trap();
    fprintf(stderr, "FORCED %" PRIu64 "\n", quest_gc_forced);
    quest_gc_collect();
}

/* Called by the slow path before each allocation while a mode is on: counts
 * it, and forces a collection (which runs the checks) when enough has been
 * allocated since the last */
static void quest_gc_check_tick(size_t sz, size_t header) {
    quest_gc_allocated_objects++;
    if ((quest_gc_check_flags & QUEST_GC_CHECK_COLLECT) != 0 && quest_gc_collect_every != 0) {
        quest_gc_force_by_count();
        return;
    }
    quest_gc_allocated_bytes += sz;
    quest_gc_allocated_headers += header;
    if ((quest_gc_check_flags & QUEST_GC_CHECK_ALLOCATIONS) != 0) {
        /* The allocating function is the slow path's caller: its return
         * address is in the slow path's frame record, which this frame's
         * record points at (x29's chain on arm64, whose ABI keeps frame
         * pointers), and its caller's in the record above that */
        void **frame = (void **)__builtin_frame_address(0);
        void **slow = frame != NULL ? (void **)frame[0] : NULL;
        void **allocating = slow != NULL ? (void **)slow[0] : NULL;
        quest_gc_note_allocation(slow != NULL ? (uintptr_t)slow[1] : 0,
                                 allocating != NULL ? (uintptr_t)allocating[1] : 0, sz + header);
    }
    quest_gc_check_pending += sz;
    if (quest_gc_check_pending >= quest_gc_check_due()) {
        quest_gc_check_pending = 0;
        if (!quest_gc_never_collect) quest_gc_collect();
    }
}

static void quest_gc_print_stats(void) {
    fprintf(stderr, "quest: gc stats: collections %" PRIu64 ", pauses %.1f ms (max %.2f ms), allocated %" PRIu64
            " MB, heap max %zu MB, live max %" PRIu64 " KB in %" PRIu64 " KB of lines, live now %" PRIu64 " KB in %"
            PRIu64 " KB of lines (%" PRIu64 " objects, %" PRIu64 " KB large)\n",
            quest_gc_collections, (double)quest_gc_pause_ns / 1e6, (double)quest_gc_pause_max_ns / 1e6,
            quest_gc_hole_bytes >> 20, (quest_gc_used_max * Q_GC_BLOCK) >> 20, quest_gc_live_bytes_max >> 10,
            (quest_gc_live_lines_max * Q_GC_LINE) >> 10, quest_gc_live_bytes >> 10,
            (quest_gc_live_lines * Q_GC_LINE) >> 10, quest_gc_live_objects, quest_gc_large_live >> 10);
    fflush(stderr);
}

/* At exit: a last collection and its checks, and with `report`, the counts
 * per layout */
static void quest_gc_at_exit(void) {
    if (quest_gc_check_flags != 0 && !quest_gc_never_collect) quest_gc_collect();
    if ((quest_gc_check_flags & QUEST_GC_CHECK_ROOTS) != 0 && quest_gc_uncovered > 0) {
        fprintf(stderr, "quest: gc check: %" PRIu64 " roots uncovered\n", quest_gc_uncovered);
        fflush(stderr);
        abort();
    }
    if (quest_gc_stats != 0) quest_gc_print_stats();
    if ((quest_gc_check_flags & QUEST_GC_CHECK_ALLOCATIONS) != 0) quest_gc_dump_allocations();
    if ((quest_gc_check_flags & QUEST_GC_CHECK_REPORT) == 0) return;
    fprintf(stderr, "quest: gc barriers: %" PRIu64 " on objects, %" PRIu64 " on slots\n", quest_barrier_counts[0],
            quest_barrier_counts[1]);
    fprintf(stderr, "quest: gc check: %" PRIu64 " checks, %" PRIu64 " objects\n", quest_gc_checks,
            quest_gc_objects_checked);
    fprintf(stderr, "quest: gc allocated: %" PRIu64 " objects, %" PRIu64 " bytes, %" PRIu64 " header bytes\n",
            quest_gc_allocated_objects, quest_gc_allocated_bytes, quest_gc_allocated_headers);
    if (quest_gc_count_n == 0) return;
    fprintf(stderr, "%12s %12s %12s %12s  %s\n", "objects", "ambiguous", "amb.heap", "suspicious", "layout");
    for (size_t i = 0; i < quest_gc_count_n; ++i) {
        const QLayoutCount *c = &quest_gc_counts[i];
        fprintf(stderr, "%12" PRIu64 " %12" PRIu64 " %12" PRIu64 " %12" PRIu64 "  %s\n", c->objects, c->ambiguous,
                c->ambiguous_heap, c->suspicious, c->layout->name);
    }
    fflush(stderr);
}

/* Reads QUEST_GC_CHECK, a comma-separated list of modes (`layouts`, `roots`,
 * `poison`, `collect`, which only forces the collections the others would, or
 * one every QUEST_GC_COLLECT_EVERY allocations, `allocations`, and `report`,
 * which prints the counts at exit), QUEST_GC_CHECK_INTERVAL, QUEST_GC_STATS (1
 * for a summary at exit, `each` for a line per collection too), and
 * QUEST_GC_MIN_HEAP (megabytes) */
static void quest_gc_read_options(void) {
    const char *modes = getenv("QUEST_GC_CHECK");
    if (modes != NULL) {
        const char *p = modes;
        while (*p != '\0') {
            const char *end = strchr(p, ',');
            size_t n = end != NULL ? (size_t)(end - p) : strlen(p);
            if (n == 7 && strncmp(p, "layouts", 7) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_LAYOUTS;
            else if (n == 6 && strncmp(p, "report", 6) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_REPORT;
            else if (n == 5 && strncmp(p, "roots", 5) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_ROOTS;
            else if (n == 6 && strncmp(p, "poison", 6) == 0) {
                quest_gc_check_flags |= QUEST_GC_CHECK_POISON;
                quest_gc_poison = true;
            }
            else if (n == 7 && strncmp(p, "collect", 7) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_COLLECT;
            else if (n == 11 && strncmp(p, "allocations", 11) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_ALLOCATIONS;
            else if (n > 0) {
                fprintf(stderr, "quest: QUEST_GC_CHECK: unknown mode '%.*s'\n", (int)n, p);
                exit(70);
            }
            p = end != NULL ? end + 1 : p + n;
        }
    }
    const char *interval = getenv("QUEST_GC_CHECK_INTERVAL");
    if (interval != NULL && interval[0] != '\0') {
        unsigned long long bytes = strtoull(interval, NULL, 10);
        if (bytes > 0) quest_gc_check_interval = (size_t)bytes;
    }
    const char *every = getenv("QUEST_GC_COLLECT_EVERY");
    if (every != NULL && every[0] != '\0') quest_gc_collect_every = strtoull(every, NULL, 10);
    const char *trap = getenv("QUEST_GC_COLLECT_TRAP");
    if (trap != NULL && trap[0] != '\0') quest_gc_collect_trap = strtoull(trap, NULL, 10);
    const char *stats = getenv("QUEST_GC_STATS");
    if (stats != NULL && stats[0] != '\0') quest_gc_stats = strcmp(stats, "each") == 0 ? 2 : 1;
    const char *min_heap = getenv("QUEST_GC_MIN_HEAP");
    if (min_heap != NULL && min_heap[0] != '\0') {
        unsigned long long mb = strtoull(min_heap, NULL, 10);
        if (mb > 0) quest_gc_min_heap_blocks = (size_t)(mb << 20) / Q_GC_BLOCK;
    }
    if (getenv("QUEST_GC_NEVER") != NULL) quest_gc_never_collect = true;
    if (quest_gc_check_flags != 0 || quest_gc_stats != 0) atexit(quest_gc_at_exit);
}

void quest_gc_init(void) {
    quest_gc_read_options();
    quest_gc_setup();
}
