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
 * own, through a cursor of their own (the noscan space). A collection marks
 * from the roots by the layouts (precise words followed, ambiguous ones
 * validated against the start bits), sets the line marks of what it marked,
 * and then keeps only live objects' start bits (decision 14) and classifies
 * every block by its free lines, which the next allocations are bumped
 * through, zeroed as each hole is entered.
 *
 * Collections are of two kinds (section 3.5). The mark bits are sticky: a
 * full collection alone clears them, so the objects allocated since the last
 * collection are the unmarked ones, the young. A minor collection, run once
 * the nursery's blocks are taken, marks only young objects and sweeps only
 * the blocks they are in, taking as roots, besides the usual ones, the old
 * objects the write barrier logged and the cards it marked since (an old
 * object or slot a pointer was stored into). A full collection stops the
 * world, except one the heap's growth asks for after a full collection that
 * took longer than a pause may (QUEST_GC_PAUSE): that one runs as a cycle,
 * marking in slices between which the program runs (section 3.10). On arm64
 * the stacks' frames are scanned precisely, by the stack maps each unit
 * registers (section 3.3); other frames' words are ambiguous. */

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

#define Q_GC_LINE            ((size_t)1 << Q_GC_LINE_BITS)                 /* 128 bytes */
#define Q_GC_BLOCK_BITS      15
#define Q_GC_BLOCK           ((size_t)1 << Q_GC_BLOCK_BITS)                /* 32 KB */
#define Q_GC_BLOCK_LINES     (Q_GC_BLOCK / Q_GC_LINE)                      /* 256 */
#define Q_GC_BLOCK_BITMAP    (Q_GC_BLOCK / 64)                             /* bytes of a bitmap per block: 512 */
#define Q_GC_MEDIUM          Q_GC_LINE          /* an allocation over a line is medium: from the overflow cursor */
#define Q_GC_LARGE           ((size_t)8 << 10)  /* an allocation of 8 KB and up is large: a run of blocks */
#define Q_GC_MIN_HEAP        ((size_t)64 << 20) /* the heap's size before the first collection, and its least */
#define Q_GC_GROWTH          2                  /* the heap may grow to this times the blocks in use after a collection */
#define Q_GC_NURSERY         ((size_t)64 << 20) /* blocks taken between minor collections (QUEST_GC_NURSERY megabytes) */
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
    uint8_t  young;      /* allocated into since the last collection (a run's head for the run) */
    uint32_t run;        /* QB_LARGE_HEAD: the blocks of its run; QB_LARGE_TAIL: the blocks back to its head */
    uint32_t live_lines; /* QB_SMALL: after the last collection */
    uint32_t pad2;
} QBlock;

/* The reserve, and the metadata beside it; the first two are what the
 * header's inline allocation reads */
uintptr_t        quest_gc_heap_lo = 0;
uintptr_t        quest_gc_heap_hi = 0;
uint8_t         *quest_gc_start_bits = NULL;   /* a bit per 8 bytes of the reserve, by (address - heap_lo) >> 3 */
uint8_t         *quest_gc_cards = NULL;        /* a byte per card (Q_GC_CARD_BITS), set by the slot barrier */
static size_t    quest_gc_block_n = 0;         /* blocks in the reserve */
static size_t    quest_gc_high_water = 0;      /* blocks ever taken; those beyond are fresh */
static QBlock   *quest_gc_blocks = NULL;
uint8_t         *quest_gc_lines = NULL;        /* a mark byte per line, by (address - heap_lo) >> 7; the slot
                                                  barrier reads it: a slot in an unmarked line is a young object's */
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

/* Generations (section 3.5): the mark bits are sticky, cleared by a full
 * collection alone, so the young objects are the unmarked ones, in the holes
 * allocated into since the last collection. The young blocks are those holes'
 * blocks, which a minor collection sweeps; the log holds the old objects the
 * barrier saw a pointer stored into since the last collection, which a minor
 * collection scans as roots; the nursery is the blocks taken between minor
 * collections (QUEST_GC_NURSERY megabytes, 0 for full collections alone) */
static size_t    *quest_gc_young = NULL;
static size_t     quest_gc_young_n = 0, quest_gc_young_cap = 0;
static uintptr_t *quest_gc_log = NULL;
static size_t     quest_gc_log_n = 0, quest_gc_log_cap = 0;
static size_t    *quest_gc_dirty = NULL;      /* the cards the slot barrier marked since the last collection */
static size_t     quest_gc_dirty_n = 0, quest_gc_dirty_cap = 0;
static size_t     quest_gc_nursery_blocks = Q_GC_NURSERY / Q_GC_BLOCK;
static size_t     quest_gc_nursery_adapted = Q_GC_NURSERY / Q_GC_BLOCK;   /* the nursery now (below) */
static bool       quest_gc_minor = false;     /* the collection in progress is a minor one */

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

/* Incremental marking (section 3.10): a full collection the heap's growth
 * asks for marks in slices, between which the program runs (a cycle), if
 * the last full collection took longer than a pause may; one asked for
 * outright (quest_gc_collect, a checking mode's) stops the world, and
 * finishes a cycle that is under way. A small heap's full collections stop
 * the world, then: they are a few milliseconds each, and a cycle's cost, a
 * call for every allocation while it runs and a scan of every object born
 * in it, is paid at each of them (tailmerge, whose 15 MB are marked 1,500
 * times, took 1.16 of its time with every one a cycle). While a cycle runs the inline
 * allocation's limits equal its cursors, so every allocation takes the slow
 * path, which does the cycle's next slice and makes the object marked; the
 * limits themselves are kept here */
static bool      quest_gc_incremental = true;      /* QUEST_GC_INCREMENTAL=0: every full collection stops the world */
/* QUEST_GC_PAUSE, in milliseconds: after a full collection that took longer,
 * the next is a cycle */
static uint64_t  quest_gc_pause_goal_ns = 10 * 1000000;
static uint64_t  quest_gc_last_full_ns = 0;        /* what the last full collection took, its marking and its sweep */
static bool      quest_gc_cycle = false;
static uintptr_t quest_gc_hidden_limit[2] = { 0, 0 };
static uint64_t  quest_gc_cycle_debt = 0;          /* bytes allocated in the cycle since its last slice */
static size_t    quest_gc_pace = 4;                /* bytes marked per byte allocated (QUEST_GC_PACE) */
static size_t    quest_gc_slice_bytes = 32 << 10;  /* bytes allocated between slices (QUEST_GC_SLICE, in KB) */
static uint64_t  quest_gc_slice_most = 1 << 20;    /* bytes a slice marks at most: a large allocation's share is spread */
static uint64_t  quest_gc_final_budget = 2 << 20;  /* bytes the final pause marks before it gives the rest to slices */
static unsigned  quest_gc_cycle_retries = 0;       /* final pauses of this cycle that gave up */
#define Q_GC_FINAL_RETRIES 3
#define Q_GC_SCAN_PIECE ((size_t)128 << 10)        /* a larger object is scanned by a cycle in pieces of this */
static uintptr_t quest_gc_piece = 0;               /* such an object, part scanned, and where its next piece is */
static uintptr_t quest_gc_piece_at = 0;
static uint64_t  quest_gc_cycle_ns = 0;            /* this cycle's pauses so far */
static uint64_t  quest_gc_cycle_slices = 0;
static uint64_t  quest_gc_cycle_first_ns = 0;

/* The statistics (QUEST_GC_STATS) */
static uint64_t quest_gc_collections = 0;
static uint64_t quest_gc_pause_ns = 0, quest_gc_pause_max_ns = 0;
static uint64_t quest_gc_allocated_blocks = 0;     /* blocks taken over the run, small and large */
static uint64_t quest_gc_hole_bytes = 0;           /* bytes of the holes entered: allocation's volume, about */
static uint64_t quest_gc_holes = 0;                /* the holes entered, a large object's run counting as one */
static size_t   quest_gc_used_max = 0;
static uint64_t quest_gc_live_bytes = 0, quest_gc_live_bytes_max = 0;   /* at the last collection, headers included */
static uint64_t quest_gc_live_objects = 0;
static uint64_t quest_gc_live_lines = 0, quest_gc_live_lines_max = 0;   /* lines marked, large runs' included */
static uint64_t quest_gc_large_live = 0;
static uint64_t quest_gc_minors = 0;               /* minor collections; quest_gc_collections counts the full ones */
static uint64_t quest_gc_minor_pause_ns = 0, quest_gc_minor_pause_max_ns = 0;
static uint64_t quest_gc_young_bytes = 0;          /* hole bytes entered since the last collection */
static uint64_t quest_gc_survived_bytes = 0, quest_gc_survived_objects = 0;   /* by minor collections, in all */
static uint64_t quest_gc_logged = 0;               /* objects logged, in all */
static uint64_t quest_gc_cards_dirtied = 0;        /* cards marked, in all */
static uint64_t quest_gc_cycles = 0;               /* full collections that marked in slices */
static uint64_t quest_gc_slices = 0, quest_gc_slice_ns = 0, quest_gc_slice_max_ns = 0;
static uint64_t quest_gc_final_ns = 0, quest_gc_final_max_ns = 0, quest_gc_first_ns = 0, quest_gc_first_max_ns = 0;
static uint64_t quest_gc_final_retried = 0;        /* final pauses that gave their work back to slices */
static uint64_t quest_gc_born_bytes = 0;           /* allocated while a cycle marked, and so born marked */
static int      quest_gc_stats = 0;                /* 1: a summary at exit; 2: a line per collection too */

/* The checking modes */
int    quest_gc_check_flags = 0;
size_t quest_gc_check_pending = 0;
/* QUEST_GC_TRAP=k: quest_gc_trap is called, for a debugger's breakpoint,
 * before the kth collection of either kind, the number a check's report
 * gives */
static uint64_t quest_gc_trap_at = 0;
__attribute__((noinline, used)) void quest_gc_trap(void) { __asm__ volatile(""); }

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

static void *quest_gc_map_at(void *hint, size_t bytes) {
    void *p = mmap(hint, bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
    return p == MAP_FAILED ? NULL : p;
}

/* Where the next of the collector's ranges is asked for: the heap's tables
 * follow the heap, which leaves the pages above the binary, where the system
 * would have put them, to what must be near it (the JIT's regions, within
 * adrp's 4 GB of the runtime: quest_code_reserve) */
static uintptr_t quest_gc_map_next = 0;

static void *quest_gc_map(size_t bytes) {
    void *p = quest_gc_map_at((void *)quest_gc_map_next, bytes);
    if (p != NULL && quest_gc_map_next != 0) {
        quest_gc_map_next = ((uintptr_t)p + bytes + ((uintptr_t)1 << 20) - 1) & ~(((uintptr_t)1 << 20) - 1);
    }
    return p;
}

/* Where the heap is asked for (a hint, which the system may decline): high
 * in the address space, above any integer a program is likely to hold. An
 * ambiguous word (a QVal of a type parameter, a stack word) that holds an
 * integer equal to an object's address keeps that object alive, and under
 * QUEST_GC_CHECK=barriers reads as a store without a barrier when the
 * object is young. Where the system places a range by itself (0x70_0000_0000
 * on Darwin), the compiler's packed source locations, a file's number above
 * bit 32, were such integers once its heap passed 4 GB. */
#define Q_GC_HEAP_HINT ((uintptr_t)1 << 46)

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
        heap = quest_gc_map_at((void *)Q_GC_HEAP_HINT, reserve);
        if (heap != NULL) break;
        reserve /= 2;
    }
    if (heap == NULL) quest_gc_fatal("out of memory: no range can be reserved for the heap");
    quest_gc_map_next = (uintptr_t)heap + reserve;
    /* The first block starts at a block boundary */
    uintptr_t lo = ((uintptr_t)heap + Q_GC_BLOCK - 1) & ~(uintptr_t)(Q_GC_BLOCK - 1);
    quest_gc_heap_lo = lo;
    quest_gc_block_n = (reserve - (lo - (uintptr_t)heap)) >> Q_GC_BLOCK_BITS;
    quest_gc_heap_hi = lo + ((uintptr_t)quest_gc_block_n << Q_GC_BLOCK_BITS);
    quest_gc_blocks = (QBlock *)quest_gc_map(quest_gc_block_n * sizeof(QBlock));
    quest_gc_lines = (uint8_t *)quest_gc_map(quest_gc_block_n * Q_GC_BLOCK_LINES);
    quest_gc_marks = (uint8_t *)quest_gc_map(quest_gc_block_n * Q_GC_BLOCK_BITMAP);
    quest_gc_start_bits = (uint8_t *)quest_gc_map(quest_gc_block_n * Q_GC_BLOCK_BITMAP);
    quest_gc_cards = (uint8_t *)quest_gc_map(quest_gc_block_n * (Q_GC_BLOCK >> Q_GC_CARD_BITS));
    if (quest_gc_blocks == NULL || quest_gc_lines == NULL || quest_gc_marks == NULL || quest_gc_start_bits == NULL ||
        quest_gc_cards == NULL) {
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

static void quest_gc_collect_kind(bool minor);

/* Holds collections off until the matching release (quest_runtime.h): the
 * holds in force. While one is, nothing collects, so every object allocated
 * since the first stays young, and the stores among them need no barriers */
static unsigned quest_gc_held = 0;
void quest_gc_hold(void) { quest_gc_held++; }
void quest_gc_release(void) { if (quest_gc_held > 0) quest_gc_held--; }
void quest_gc_release_all(void) { quest_gc_held = 0; }

/* The nursery: the configured blocks, doubled while more than a quarter of
 * the young bytes survive a minor collection (a program building a structure
 * it keeps, whose minor collections would mark what the next full one marks
 * again), up to a quarter of the heap's target, beyond which minor
 * collections stop (every eighth full collection then runs one at that
 * largest size to see whether the program has changed its ways); and halved
 * back toward the configured blocks while under a sixteenth survives. Under
 * a checking mode at least a quarter of the heap, so that the walks a minor
 * collection makes (the young blocks', and under `barriers` the old
 * generation's) stay a fraction of the run */
#define Q_GC_NO_NURSERY ((size_t)-1)
static unsigned quest_gc_fulls_without_nursery = 0;
static size_t quest_gc_nursery_now(void) {
    size_t n = quest_gc_nursery_adapted;
    if (quest_gc_check_flags != 0 && n != Q_GC_NO_NURSERY && quest_gc_used / 4 > n) n = quest_gc_used / 4;
    return n;
}

static size_t quest_gc_nursery_cap(void) {
    size_t cap = quest_gc_target / 4;
    return cap < quest_gc_nursery_blocks ? quest_gc_nursery_blocks : cap;
}

static void quest_gc_adapt_nursery(uint64_t young, uint64_t survived) {
    size_t cap = quest_gc_nursery_cap();
    if (survived * 4 > young) {
        quest_gc_nursery_adapted = quest_gc_nursery_adapted * 2 <= cap ? quest_gc_nursery_adapted * 2 : Q_GC_NO_NURSERY;
    } else if (survived * 16 < young && quest_gc_nursery_adapted / 2 >= quest_gc_nursery_blocks) {
        quest_gc_nursery_adapted /= 2;
    }
}

/* Whether taking n more blocks should collect first: the heap has reached its
 * target, or the nursery is full; something was allocated since the last
 * collection (else the live data needs the growth); and collection is on */
static bool quest_gc_should_collect(size_t n) {
    if (quest_gc_never_collect || quest_gc_held != 0 || quest_gc_collecting || quest_gc_cycle ||
        quest_gc_taken_since_collection == 0) {
        return false;
    }
    return quest_gc_used + n > quest_gc_target ||
           (quest_gc_nursery_blocks != 0 && quest_gc_taken_since_collection >= quest_gc_nursery_now());
}

/* Collects before taking n blocks: a minor collection when the heap is under
 * its target, and a full one when it is not, or when the minor one left it
 * so. The full one starts a cycle, which the allocations after this one
 * carry on (they take free blocks until it ends, so the heap passes its
 * target by what the cycle's pace lets the program allocate meanwhile) */
static void quest_gc_cycle_start(void);
static void quest_gc_collect_before(size_t n) {
    if (quest_gc_nursery_blocks != 0 && quest_gc_used + n <= quest_gc_target) quest_gc_collect_kind(true);
    if (quest_gc_used + n > quest_gc_target) {
        if (quest_gc_incremental && quest_gc_last_full_ns >= quest_gc_pause_goal_ns) quest_gc_cycle_start();
        else quest_gc_collect_kind(false);
    }
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
        blk->young = 0;
    }
    quest_gc_blocks[b].young = 1;
    quest_gc_push(&quest_gc_young, &quest_gc_young_n, &quest_gc_young_cap, b);
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
    if (!quest_gc_blocks[b].young) {
        quest_gc_blocks[b].young = 1;
        quest_gc_push(&quest_gc_young, &quest_gc_young_n, &quest_gc_young_cap, b);
    }
    cursor[k] = start;
    limit[k] = start + bytes;
    quest_gc_hole_bytes += bytes;
    quest_gc_holes++;
    quest_gc_young_bytes += bytes;
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
    if (quest_gc_should_collect(n)) quest_gc_collect_before(n);
    size_t b = quest_gc_take_run(k, n);
    uintptr_t start = quest_gc_block_start(b);
    if (!quest_gc_blocks[b].fresh) memset((void *)start, 0, total);
    quest_gc_hole_bytes += total;
    quest_gc_holes++;
    quest_gc_young_bytes += total;
    return (void *)start;
}

/* A medium object, from the overflow cursor of its space, which takes fresh
 * holes (whole free blocks) so that the small cursor's holes are not skipped
 * for want of room */
static void *quest_gc_alloc_medium(size_t total, unsigned k) {
    if (total > quest_gc_over_limit[k] - quest_gc_over_cursor[k]) {
        if (quest_gc_should_collect(1)) quest_gc_collect_before(1);
        size_t b = quest_gc_take_free_block(k, QB_SMALL);
        quest_gc_enter_hole(quest_gc_over_cursor, quest_gc_over_limit, k, b, 0, Q_GC_BLOCK_LINES);
    }
    uintptr_t p = quest_gc_over_cursor[k];
    quest_gc_over_cursor[k] = p + total;
    return (void *)p;
}

static void quest_gc_check_tick(size_t sz, size_t header);
static void quest_gc_note_site(uintptr_t obj);
/* The checking modes only the collector reads, with quest_runtime.h's:
 * `stress` (quest_gc_stress_tick) and `sites` (quest_gc_note_site) */
#define QUEST_GC_CHECK_STRESS 128
#define QUEST_GC_CHECK_SITES  256

/* `total` zeroed bytes (headers included) for an object of the layout, when
 * the inline fast path's hole has no room, or a checking mode is on, which
 * counts the allocation first (and may collect then): the next hole, a
 * recyclable block's, a free block's, or, for medium and large allocations,
 * their own paths; collecting first when the heap has reached its target */
static inline __attribute__((always_inline)) void *quest_gc_alloc_slow_body(size_t total, const QLayout *layout) {
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
            quest_gc_collect_before(1);
            continue;
        }
        quest_gc_current[k] = quest_gc_take_free_block(k, QB_SMALL);
        quest_gc_current_line[k] = 0;
    }
}

static void quest_gc_cycle_step(size_t bytes);
static void quest_gc_born(uintptr_t base, size_t total, const QLayout *layout, size_t prefix);

/* The body is inline here so that the frame above the slow path's is still
 * the allocating function's, which `allocations` and `sites` read. The
 * header word is stored here, the inline path's caller storing it only for
 * what it bumps itself (quest_runtime.h): an object allocated while a cycle
 * marks has the collector's flags in it. A cycle's slice comes first, and
 * may end the cycle; while one runs, the limits are shown to the body and
 * hidden again after, so that the next allocation comes here too */
void *quest_gc_alloc_slow(size_t total, const QLayout *layout) {
    if (quest_gc_cycle) {
        quest_gc_cycle_step(total);
        if (quest_gc_cycle) {
            quest_gc_limit[0] = quest_gc_hidden_limit[0];
            quest_gc_limit[1] = quest_gc_hidden_limit[1];
        }
    }
    void *p = quest_gc_alloc_slow_body(total, layout);
    size_t prefix = quest_gc_prefix_of(layout);
    if (quest_gc_cycle) {
        quest_gc_born((uintptr_t)p, total, layout, prefix);
        for (unsigned k = 0; k < 2; ++k) {
            quest_gc_hidden_limit[k] = quest_gc_limit[k];
            quest_gc_limit[k] = quest_gc_cursor[k];
        }
    } else {
        ((uintptr_t *)p)[prefix / sizeof(uintptr_t) - 1] = (uintptr_t)layout;
    }
    if ((quest_gc_check_flags & QUEST_GC_CHECK_SITES) != 0) quest_gc_note_site((uintptr_t)p + prefix);
    return p;
}

/* ---------------------------------------------------------------------------
 * Write barriers and roots
 * ------------------------------------------------------------------------ */

static uintptr_t quest_gc_start_before(size_t b, uintptr_t a);
static uintptr_t quest_gc_large_object(size_t b);

static void quest_gc_log_push(uintptr_t obj) {
    if (quest_gc_log_n == quest_gc_log_cap) {
        size_t cap = quest_gc_log_cap > 0 ? 2 * quest_gc_log_cap : 4096;
        uintptr_t *grown = (uintptr_t *)realloc(quest_gc_log, cap * sizeof *grown);
        if (grown == NULL) quest_gc_fatal("out of memory in the collector's log");
        quest_gc_log = grown;
        quest_gc_log_cap = cap;
    }
    quest_gc_log[quest_gc_log_n++] = obj;
}

/* The barrier's slow path: logs the object if a collection has marked it and
 * nothing has logged it since (the inline fast path tests the same, so a
 * call from native code, which cannot inline it, is complete here); an
 * option's payload is logged as its option */
void quest_barrier_log(void *obj) {
    uintptr_t *p = (uintptr_t *)obj;
    if (p[-1] < Q_BARRIER_TAG_LIMIT) p -= 1;
    obj = p;
    uintptr_t *h = p - 1;
    if ((*h & (Q_HEADER_OLD | Q_HEADER_LOGGED)) != Q_HEADER_OLD) return;
    if (!quest_gc_in_heap((uintptr_t)obj)) return;
    ((uint8_t *)h)[6] |= 1u;    /* the mutator's byte of the header: Q_HEADER_LOGGED */
    quest_gc_logged++;
    quest_gc_log_push((uintptr_t)obj);
}

/* The slot barrier's slow path: marks the slot's card and lists it for the
 * next minor collection, which scans the dirty cards' words (the inline fast
 * path tests the card first, so a call from native code is complete here) */
void quest_barrier_card(uint8_t *card) {
    if (*card != 0) return;
    *card = 1;
    quest_gc_cards_dirtied++;
    quest_gc_push(&quest_gc_dirty, &quest_gc_dirty_n, &quest_gc_dirty_cap, (size_t)(card - quest_gc_cards));
}

/* Counts per layout, for the report */
typedef struct QLayoutCount {
    const QLayout *layout;
    uint64_t       objects;
    uint64_t       ambiguous;         /* ambiguous words */
    uint64_t       suspicious;        /* scalar words that are addresses of heap objects */
    uint64_t       ambiguous_heap;    /* ambiguous words that are addresses of heap objects */
    uint64_t       logged;            /* objects of the layout the log held at minor collections */
    uint64_t       logged_bytes;      /* their bytes, scanned whole */
} QLayoutCount;
static QLayoutCount *quest_gc_count_of(const QLayout *layout);

/* Empties the log: each logged object's bit is cleared, and, in a minor
 * collection, its words are scanned, since the pointers stored into it since
 * the last collection may be the only ones at young objects */
static void quest_gc_scan_object(uintptr_t obj);
static void quest_gc_drain_log(bool scan) {
    for (size_t i = 0; i < quest_gc_log_n; ++i) {
        uintptr_t obj = quest_gc_log[i];
        ((uint8_t *)obj)[-2] &= (uint8_t)~1u;    /* byte 6 of the header word, which is at obj - 8 */
        const QLayout *l = quest_layout_of((const void *)obj);
        if (scan && (quest_gc_check_flags & QUEST_GC_CHECK_REPORT) != 0) {
            QLayoutCount *c = quest_gc_count_of(l);
            c->logged++;
            c->logged_bytes += quest_gc_object_bytes(obj, l);
        }
        if (scan && (l->flags & Q_LAYOUT_NOSCAN) == 0) quest_gc_scan_object(obj);
    }
    quest_gc_log_n = 0;
}

/* Scans the words of the object at obj that lie in [lo, hi), by its layout */
static void quest_gc_scan_object_range(uintptr_t obj, uintptr_t lo, uintptr_t hi);

/* Scans a card's words by the old objects they belong to: the object that
 * starts at or before the card and reaches into it, and those that start in
 * it. A young object's words are left to marking: the barrier marks a card
 * whatever the age of the slot's object, and scanning a dead young object's
 * would keep what it points at alive */
static void quest_gc_scan_card(size_t card) {
    uintptr_t lo = quest_gc_heap_lo + (card << Q_GC_CARD_BITS), hi = lo + ((uintptr_t)1 << Q_GC_CARD_BITS);
    size_t b = quest_gc_block_of(lo);
    const QBlock *blk = &quest_gc_blocks[b];
    if (blk->state == QB_FREE) return;
    if (blk->state == QB_LARGE_TAIL) {
        b -= blk->run;
        blk = &quest_gc_blocks[b];
    }
    if (blk->state == QB_LARGE_HEAD) {
        uintptr_t obj = quest_gc_large_object(b);
        if (obj != 0 && quest_gc_bit(quest_gc_marks, obj)) quest_gc_scan_object_range(obj, lo, hi);
        return;
    }
    uintptr_t obj = quest_gc_start_before(b, lo);
    if (obj != 0 && quest_gc_bit(quest_gc_marks, obj)) quest_gc_scan_object_range(obj, lo, hi);
    uintptr_t first = (lo - quest_gc_heap_lo) >> 3;     /* the card's first word's index */
    for (size_t i = 0; i < ((size_t)1 << Q_GC_CARD_BITS) / 64; ++i) {
        unsigned m = quest_gc_start_bits[(first >> 3) + i] & quest_gc_marks[(first >> 3) + i];
        if (i == 0) m &= ~1u;                            /* the object at lo was scanned above */
        while (m != 0) {
            unsigned bit = (unsigned)__builtin_ctz(m);
            m &= m - 1;
            quest_gc_scan_object_range(quest_gc_heap_lo + ((first + i * 8 + bit) << 3), lo, hi);
        }
    }
}

/* Empties the dirty cards: in a minor collection each is scanned first, since
 * the pointers stored into it since the last collection may be the only ones
 * at young objects */
static void quest_gc_drain_cards(bool scan) {
    for (size_t i = 0; i < quest_gc_dirty_n; ++i) {
        size_t card = quest_gc_dirty[i];
        quest_gc_cards[card] = 0;
        if (scan) quest_gc_scan_card(card);
    }
    quest_gc_dirty_n = 0;
}

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
        /* The run's lines, for the slot barrier's test */
        memset(quest_gc_block_lines(b), 1, (size_t)quest_gc_blocks[b].run * Q_GC_BLOCK_LINES);
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

static void quest_gc_scan_object_range(uintptr_t obj, uintptr_t lo, uintptr_t hi) {
    const QLayout *l = quest_layout_of((const void *)obj);
    if ((l->flags & Q_LAYOUT_NOSCAN) != 0) return;
    uintptr_t end = obj + quest_gc_object_bytes(obj, l);
    if (lo < obj) lo = obj;
    if (hi > end) hi = end;
    if (lo >= hi) return;
    const uintptr_t *words = (const uintptr_t *)obj;
    size_t from = (lo - obj) >> 3, to = (hi - obj) >> 3;
    switch (l->form) {
    case Q_LAYOUT_FIXED:
        for (size_t i = from; i < to; ++i) {
            if (l->kinds[i] == Q_WORD_POINTER) quest_gc_mark_word(words[i], false);
            else if (l->kinds[i] == Q_WORD_AMBIGUOUS) quest_gc_mark_word(words[i], true);
        }
        break;
    case Q_LAYOUT_ARRAY: {
        size_t elements = l->size / 8;
        for (size_t i = from; i < to; ++i) {
            uint8_t kind = i < elements ? l->kinds[i] : l->kinds[l->words + (i - elements) % l->element_words];
            if (kind == Q_WORD_POINTER) quest_gc_mark_word(words[i], false);
            else if (kind == Q_WORD_AMBIGUOUS) quest_gc_mark_word(words[i], true);
        }
        break;
    }
    default:
        for (size_t i = from; i < to; ++i) {
            uint8_t kind = l->kinds[i % l->element_words];
            if (kind == Q_WORD_POINTER) quest_gc_mark_word(words[i], false);
            else if (kind == Q_WORD_AMBIGUOUS) quest_gc_mark_word(words[i], true);
        }
        break;
    }
}

/* A root slot of `words` words, scanned as ambiguous: a root table's entry
 * may be a global of generic code, and validation costs nothing wrong */
static void quest_gc_mark_root(void *slot, size_t words) {
    quest_gc_scan_range((const uintptr_t *)slot, (const uintptr_t *)slot + words);
}

/* ---------------------------------------------------------------------------
 * Stack maps (section 3.3)
 * ------------------------------------------------------------------------ */

/* A unit's frame table, as the arm64 backend writes it (qr_frames;
 * docs/arm64.md section 3.13), which the unit registers when it starts:
 *
 *     int32   the unit's first function, in bytes from the table
 *     uint32  the functions listed, n
 *     n of    uint32 the function's start, in bytes from the first function's
 *             uint32 its description, in bytes from the table
 *
 * in the order of their code, then the descriptions, each a sequence of
 * unsigned LEB128 numbers:
 *
 *     the words from the frame's lowest address to its frame record
 *     the pairs of callee-saved registers the prologue saves, a bit each, in
 *         the order it pushes them below the record (x20 and x19 first)
 *     the words at the frame's lowest addresses with no description (the
 *         outgoing arguments and the stack slots), scanned as ambiguous
 *     the calls listed, then for each, in the order of their code:
 *         its return address, in instructions from the call before's (the
 *             first's from the function's start)
 *         the callee-saved registers live across it, two bits each from x19
 *             (1 a pointer, 2 an ambiguous word)
 *         the frame's words live across it, their number and then each as
 *             twice its index from the frame's lowest address, plus 1 for an
 *             ambiguous word
 *
 * A function that enters a try is not listed: its handler reads slots where
 * liveness does not see it, so its frame is scanned whole, like C's. A table
 * of no functions is the placeholder a unit compiled through C registers. */
typedef struct QFrameUnit { uintptr_t text; const uint32_t *table; } QFrameUnit;
static QFrameUnit *quest_gc_frame_units = NULL;
static size_t      quest_gc_frame_unit_n = 0, quest_gc_frame_unit_cap = 0;
static bool        quest_gc_frame_units_sorted = true;
static bool        quest_gc_use_maps = true;      /* QUEST_GC_MAPS=0 scans every frame whole */
static uint64_t    quest_gc_frames_mapped = 0, quest_gc_frames_unmapped = 0;

void quest_register_frames(const void *table) {
    const uint32_t *t = (const uint32_t *)table;
    if (t[1] == 0) return;
    if (quest_gc_frame_unit_n == quest_gc_frame_unit_cap) {
        size_t cap = quest_gc_frame_unit_cap > 0 ? 2 * quest_gc_frame_unit_cap : 64;
        QFrameUnit *grown = (QFrameUnit *)realloc(quest_gc_frame_units, cap * sizeof *grown);
        if (grown == NULL) quest_gc_fatal("out of memory registering frame tables");
        quest_gc_frame_units = grown;
        quest_gc_frame_unit_cap = cap;
    }
    QFrameUnit *u = &quest_gc_frame_units[quest_gc_frame_unit_n++];
    u->text = (uintptr_t)table + (uintptr_t)(intptr_t)(int32_t)t[0];
    u->table = t;
    quest_gc_frame_units_sorted = false;
}

static int quest_gc_frame_unit_order(const void *a, const void *b) {
    uintptr_t x = ((const QFrameUnit *)a)->text, y = ((const QFrameUnit *)b)->text;
    return x < y ? -1 : x > y;
}

static inline uint64_t quest_gc_leb(const uint8_t **p) {
    uint64_t n = 0;
    unsigned shift = 0;
    for (;;) {
        uint8_t b = *(*p)++;
        n |= (uint64_t)(b & 0x7f) << shift;
        if ((b & 0x80) == 0) return n;
        shift += 7;
    }
}

/* What a frame holds across the call that returns to `ra`: the bytes from
 * its lowest address to its frame record, the pairs it saved, the words at
 * its lowest addresses to scan as ambiguous, the callee-saved registers live
 * across the call, and its live words (as the table has them) */
typedef struct QFrameMap {
    size_t         below;
    unsigned       saved;
    size_t         ambiguous_words;
    uint32_t       registers;
    size_t         slot_n;
    const uint8_t *slots;
} QFrameMap;

/* The map of the call that returns to ra, if a registered table lists it */
static bool quest_gc_frame_map(uintptr_t ra, QFrameMap *m) {
    if (!quest_gc_frame_units_sorted) {
        qsort(quest_gc_frame_units, quest_gc_frame_unit_n, sizeof *quest_gc_frame_units, quest_gc_frame_unit_order);
        quest_gc_frame_units_sorted = true;
    }
    /* The last unit that starts at or before ra, then its last such function */
    size_t lo = 0, hi = quest_gc_frame_unit_n;
    while (lo < hi) {
        size_t mid = lo + (hi - lo) / 2;
        if (quest_gc_frame_units[mid].text <= ra) lo = mid + 1; else hi = mid;
    }
    if (lo == 0) return false;
    const QFrameUnit *u = &quest_gc_frame_units[lo - 1];
    uintptr_t at = ra - u->text;
    if (at > UINT32_MAX) return false;
    const uint32_t *functions = u->table + 2;
    size_t flo = 0, fhi = u->table[1];
    while (flo < fhi) {
        size_t mid = flo + (fhi - flo) / 2;
        if (functions[2 * mid] <= at) flo = mid + 1; else fhi = mid;
    }
    if (flo == 0) return false;
    uint64_t target = (at - functions[2 * (flo - 1)]) / 4;
    const uint8_t *p = (const uint8_t *)u->table + functions[2 * (flo - 1) + 1];
    m->below = (size_t)quest_gc_leb(&p) * 8;
    m->saved = (unsigned)quest_gc_leb(&p);
    m->ambiguous_words = (size_t)quest_gc_leb(&p);
    uint64_t calls = quest_gc_leb(&p), offset = 0;
    for (uint64_t i = 0; i < calls; ++i) {
        offset += quest_gc_leb(&p);
        if (offset > target) return false;
        uint32_t registers = (uint32_t)quest_gc_leb(&p);
        size_t n = (size_t)quest_gc_leb(&p);
        if (offset == target) {
            m->registers = registers;
            m->slot_n = n;
            m->slots = p;
            return true;
        }
        for (size_t k = 0; k < n; ++k) (void)quest_gc_leb(&p);
    }
    return false;
}

/* The callee-saved registers whose owners are not known yet, marked as
 * ambiguous words where they were last saved (below) */
static void quest_gc_flush_saved(const uintptr_t **saved) {
    for (unsigned r = 0; r < 10; ++r) {
        if (saved[r] != NULL) quest_gc_mark_word(*saved[r], true);
        saved[r] = NULL;
    }
}

/* The stack from here to its base, the registers first spilled into a
 * jmp_buf on it. The frame records are walked from this function's (a
 * record is the caller's frame pointer and the return address into the
 * caller, and on arm64 every function that calls keeps one): a caller whose
 * call a frame table lists is a mapped frame, of which only the words the
 * table gives are scanned, as pointers or as ambiguous words; everything
 * else, C's frames, the frames of functions that enter a try, and this
 * walk's own, is scanned conservatively, as the whole stack was before the
 * tables. A callee-saved register live across a mapped frame's call is
 * where the youngest frame after it saved it: `saved` has that place for
 * each of x19 to x28 while every frame since is mapped, the mapped frames'
 * prologues being described; past an unmapped frame, which may have saved a
 * register anywhere in its frame or not at all, the places known so far are
 * scanned as ambiguous words and forgotten, the frame itself being scanned
 * whole, so a register's value is always seen, precisely when the frames
 * between are mapped. A register no mapped frame has live is not scanned
 * where a mapped frame saved it, nor is a dead slot: the retention the tables
 * end (docs/arm64-performance-review.md section 3.2). */
static void quest_gc_scan_stack(void) {
    jmp_buf regs;
    _setjmp(regs);
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
    base &= ~(uintptr_t)7;
    uintptr_t cursor = (uintptr_t)&regs & ~(uintptr_t)7;
#if defined(__aarch64__)
    if (quest_gc_use_maps && quest_gc_frame_unit_n > 0) {
        const uintptr_t *saved[10] = { NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL };
        uintptr_t fp = (uintptr_t)__builtin_frame_address(0);
        while ((fp & 7) == 0 && fp >= cursor && fp + 16 <= base) {
            uintptr_t caller = ((const uintptr_t *)fp)[0], ra = ((const uintptr_t *)fp)[1];
            if ((caller & 7) != 0 || caller <= fp || caller + 16 > base) break;
            QFrameMap m;
            if (quest_gc_frame_map(ra, &m) && caller - fp >= m.below + 16) {
                quest_gc_frames_mapped++;
                const uintptr_t *sp = (const uintptr_t *)(caller - m.below);
                quest_gc_scan_range((const uintptr_t *)cursor, sp + m.ambiguous_words);
                const uint8_t *p = m.slots;
                for (size_t k = 0; k < m.slot_n; ++k) {
                    uint64_t slot = quest_gc_leb(&p);
                    quest_gc_mark_word(sp[slot >> 1], (slot & 1) != 0);
                }
                for (unsigned r = 0; r < 10; ++r) {
                    unsigned kind = (m.registers >> (2 * r)) & 3;
                    if (kind != 0 && saved[r] != NULL) quest_gc_mark_word(*saved[r], kind == 2);
                }
                /* The kth pair the prologue saved is 16 * (k + 1) bytes
                 * below the record, its even register (x20 of x20 and x19)
                 * first; pairs from the sixth on are d8 to d15 */
                const uintptr_t *record = (const uintptr_t *)caller;
                unsigned k = 0;
                for (unsigned pair = 0; pair < 9; ++pair) {
                    if ((m.saved & (1u << pair)) == 0) continue;
                    if (pair < 5) {
                        saved[2 * pair + 1] = record - 2 * (k + 1);
                        saved[2 * pair] = record - 2 * (k + 1) + 1;
                    }
                    k++;
                }
                cursor = caller;
            } else {
                quest_gc_frames_unmapped++;
                quest_gc_flush_saved(saved);
            }
            fp = caller;
        }
        quest_gc_flush_saved(saved);
    }
#endif
    quest_gc_scan_range((const uintptr_t *)cursor, (const uintptr_t *)base);
}

static void quest_gc_mark_roots(void) {
    for (size_t i = 0; i < quest_gc_root_table_n; ++i) {
        for (const QRootEntry *e = quest_gc_root_tables[i]; e->slot != NULL; ++e) quest_gc_mark_root(e->slot, e->words);
    }
    quest_runtime_roots(quest_gc_mark_root);
    quest_code_roots(quest_gc_mark_root);
    quest_serialization_roots(quest_gc_mark_root);
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
        memset(quest_gc_block_lines(b), 0, Q_GC_BLOCK_LINES);
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
            blk->young = 0;
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
            blk->young = 0;
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
    quest_gc_young_n = 0;
}

/* After a minor collection's marking: the young blocks alone are swept, as a
 * full sweep sweeps every block (only live objects validate, the live lines
 * recounted, each block classified), the old recyclable blocks not yet
 * allocated into keep their holes, and the cursors start over. The young
 * list is kept for the checks, and emptied by the collection's end. */
static void quest_gc_sweep_young(void) {
    /* The free list keeps the blocks the last full collection left; the dead young blocks join it */
    for (unsigned k = 0; k < 2; ++k) {
        size_t rest = quest_gc_recyclable_n[k] - quest_gc_recyclable_next[k];
        memmove(quest_gc_recyclable[k], quest_gc_recyclable[k] + quest_gc_recyclable_next[k], rest * sizeof(size_t));
        quest_gc_recyclable_n[k] = rest;
        quest_gc_recyclable_next[k] = 0;
        quest_gc_cursor[k] = quest_gc_limit[k] = 0;
        quest_gc_over_cursor[k] = quest_gc_over_limit[k] = 0;
        quest_gc_current[k] = Q_GC_NO_BLOCK;
        quest_gc_current_line[k] = 0;
    }
    for (size_t i = 0; i < quest_gc_young_n; ++i) {
        size_t b = quest_gc_young[i];
        QBlock *blk = &quest_gc_blocks[b];
        blk->young = 0;
        switch (blk->state) {
        case QB_SMALL: {
            uint64_t *starts = (uint64_t *)quest_gc_block_bits(quest_gc_start_bits, b);
            const uint64_t *marks = (const uint64_t *)quest_gc_block_bits(quest_gc_marks, b);
            for (size_t j = 0; j < Q_GC_BLOCK_BITMAP / 8; ++j) starts[j] &= marks[j];
            const uint8_t *lm = quest_gc_block_lines(b);
            uint32_t live = 0;
            for (size_t j = 0; j < Q_GC_BLOCK_LINES; ++j) live += lm[j];
            quest_gc_live_lines -= blk->live_lines;
            quest_gc_live_lines += live;
            blk->fresh = 0;
            blk->live_lines = live;
            if (live == 0) {
                blk->state = QB_FREE;
                quest_gc_used--;
                if (quest_gc_poison) memset((void *)quest_gc_block_start(b), Q_GC_POISON, Q_GC_BLOCK);
                quest_gc_push(&quest_gc_free, &quest_gc_free_n, &quest_gc_free_cap, b);
            } else if (live < Q_GC_BLOCK_LINES) {
                unsigned k = blk->space;
                quest_gc_push(&quest_gc_recyclable[k], &quest_gc_recyclable_n[k], &quest_gc_recyclable_cap[k], b);
                if (quest_gc_poison) quest_gc_poison_block(b);
            }
            break;
        }
        case QB_LARGE_HEAD: {
            size_t run = blk->run;
            uintptr_t obj = quest_gc_large_object(b);
            if (obj != 0 && quest_gc_bit(quest_gc_marks, obj)) {
                quest_gc_live_lines += run * Q_GC_BLOCK_LINES;
                blk->fresh = 0;
            } else {
                if (obj != 0) quest_gc_clear_bit(quest_gc_start_bits, obj);
                if (quest_gc_poison) memset((void *)quest_gc_block_start(b), Q_GC_POISON, run * Q_GC_BLOCK);
                for (size_t j = 0; j < run; ++j) {
                    quest_gc_blocks[b + j].state = QB_FREE;
                    quest_gc_blocks[b + j].fresh = 0;
                    quest_gc_push(&quest_gc_free, &quest_gc_free_n, &quest_gc_free_cap, b + j);
                }
                quest_gc_used -= run;
            }
            break;
        }
        default:
            quest_gc_fatal("the collector found a young block that is neither small nor a run's head");
        }
    }
    quest_gc_taken_since_collection = 0;
}

static void quest_gc_check_heap(void);
static void quest_gc_check_young(void);
static void quest_gc_check_barriers(void);
static void quest_gc_check_roots(void);

/* Stops the world (there is one mutator, and it is here), marks, and sweeps.
 * A full collection clears every mark and marks everything; a minor one keeps
 * the marks, so marking from the roots and the log stops at every old object
 * and visits the young ones alone, and sweeps the young blocks alone. */
static bool quest_gc_cycle_finish(bool force);
static void quest_gc_collect_kind(bool minor) {
    if (!quest_gc_ready) quest_gc_setup();
    if (quest_gc_collecting || quest_gc_held != 0) return;
    if (quest_gc_cycle) {
        /* A minor collection waits for the cycle (its marks are being made
         * again); a full one is the cycle's, finished now */
        if (!minor) quest_gc_cycle_finish(true);
        return;
    }
    quest_gc_collecting = true;
    quest_gc_minor = minor;
    if (quest_gc_trap_at != 0 && quest_gc_collections + quest_gc_minors + 1 == quest_gc_trap_at) quest_gc_trap();
    uint64_t t0 = quest_gc_now_ns();
    uint64_t before_bytes = quest_gc_live_bytes, before_objects = quest_gc_live_objects;
    uint64_t young = quest_gc_young_bytes;
    size_t logged = quest_gc_log_n, dirty = quest_gc_dirty_n;
    quest_gc_work_n = 0;
    if (minor) {
        quest_gc_minors++;
        if ((quest_gc_check_flags & QUEST_GC_CHECK_BARRIERS) != 0) quest_gc_check_barriers();
        t0 = quest_gc_now_ns();
        quest_gc_drain_log(true);
        quest_gc_drain_cards(true);
    } else {
        quest_gc_collections++;
        quest_gc_live_bytes = 0;
        quest_gc_live_objects = 0;
        quest_gc_large_live = 0;
        quest_gc_drain_log(false);
        quest_gc_drain_cards(false);
        quest_gc_clear_marks();
    }
    uint64_t t1 = quest_gc_now_ns();
    quest_gc_mark_roots();
    uint64_t t2 = quest_gc_now_ns();
    while (quest_gc_work_n > 0) quest_gc_scan_object(quest_gc_work[--quest_gc_work_n]);
    uint64_t t3 = quest_gc_now_ns();
    if (minor) quest_gc_sweep_young(); else quest_gc_sweep();
    quest_gc_young_bytes = 0;
    uint64_t t4 = quest_gc_now_ns();
    uint64_t pause = t4 - t0;
    if (minor) {
        quest_gc_minor_pause_ns += pause;
        if (pause > quest_gc_minor_pause_max_ns) quest_gc_minor_pause_max_ns = pause;
        quest_gc_survived_bytes += quest_gc_live_bytes - before_bytes;
        quest_gc_survived_objects += quest_gc_live_objects - before_objects;
        quest_gc_adapt_nursery(young, quest_gc_live_bytes - before_bytes);
    } else {
        quest_gc_pause_ns += pause;
        quest_gc_last_full_ns = pause;
        if (pause > quest_gc_pause_max_ns) quest_gc_pause_max_ns = pause;
        if (quest_gc_nursery_adapted == Q_GC_NO_NURSERY && ++quest_gc_fulls_without_nursery % 8 == 0) {
            quest_gc_nursery_adapted = quest_gc_nursery_cap();
        }
    }
    if (quest_gc_live_bytes > quest_gc_live_bytes_max) quest_gc_live_bytes_max = quest_gc_live_bytes;
    if (quest_gc_live_lines > quest_gc_live_lines_max) quest_gc_live_lines_max = quest_gc_live_lines;
    if (quest_gc_stats >= 2) {
        if (minor) {
            fprintf(stderr, "quest: gc minor #%" PRIu64 ": young %" PRIu64 " KB, survived %" PRIu64 " KB (%" PRIu64
                    " objects), logged %zu, cards %zu, %.2f ms, roots %.2f ms, mark %.2f ms, sweep %.2f ms, nursery "
                    "%zu KB, heap %zu KB, %.2f ms\n", quest_gc_minors, young >> 10,
                    (quest_gc_live_bytes - before_bytes) >> 10, quest_gc_live_objects - before_objects, logged, dirty,
                    (double)(t1 - t0) / 1e6, (double)(t2 - t1) / 1e6, (double)(t3 - t2) / 1e6, (double)(t4 - t3) / 1e6,
                    quest_gc_nursery_adapted == Q_GC_NO_NURSERY ? (size_t)0 : (quest_gc_nursery_adapted * Q_GC_BLOCK) >> 10,
                    (quest_gc_used * Q_GC_BLOCK) >> 10,
                    (double)pause / 1e6);
        } else {
            fprintf(stderr, "quest: gc #%" PRIu64 ": live %" PRIu64 " KB in %" PRIu64 " KB of lines, heap %zu KB, "
                    "%.2f ms\n", quest_gc_collections, quest_gc_live_bytes >> 10,
                    (quest_gc_live_lines * Q_GC_LINE) >> 10, (quest_gc_used * Q_GC_BLOCK) >> 10, (double)pause / 1e6);
        }
    }
    if ((quest_gc_check_flags & QUEST_GC_CHECK_LAYOUTS) != 0) {
        if (minor) quest_gc_check_young(); else quest_gc_check_heap();
    }
    if ((quest_gc_check_flags & QUEST_GC_CHECK_ROOTS) != 0) quest_gc_check_roots();
    quest_gc_young_n = 0;
    quest_gc_minor = false;
    quest_gc_collecting = false;
}

/* A full collection now */
void quest_gc_collect(void) { quest_gc_collect_kind(false); }

/* ---------------------------------------------------------------------------
 * Incremental marking (section 3.10)
 * ------------------------------------------------------------------------ */

#define QUEST_GC_CHECK_INCREMENTAL 512
static void quest_gc_check_cycle(void);
static void quest_gc_incremental_done(void);

/* A cycle's first pause: a full collection's start (the marks cleared, the
 * log and the cards emptied), then the roots marked, their objects left on
 * the work list for the slices. Until the cycle's sweep the line marks are
 * the marker's, so allocation takes no hole they would show: the current
 * holes are kept, being free already, and after them only free blocks */
static void quest_gc_cycle_start(void) {
    if (quest_gc_collecting || quest_gc_held != 0 || quest_gc_cycle || quest_gc_never_collect) return;
    quest_gc_collecting = true;
    if (quest_gc_trap_at != 0 && quest_gc_collections + quest_gc_minors + 1 == quest_gc_trap_at) quest_gc_trap();
    uint64_t t0 = quest_gc_now_ns();
    quest_gc_collections++;
    quest_gc_cycles++;
    quest_gc_live_bytes = 0;
    quest_gc_live_objects = 0;
    quest_gc_large_live = 0;
    quest_gc_drain_log(false);
    quest_gc_drain_cards(false);
    quest_gc_clear_marks();
    for (unsigned k = 0; k < 2; ++k) {
        quest_gc_current[k] = Q_GC_NO_BLOCK;
        quest_gc_recyclable_next[k] = quest_gc_recyclable_n[k];
        quest_gc_hidden_limit[k] = quest_gc_limit[k];
    }
    quest_gc_work_n = 0;
    quest_gc_piece = 0;
    quest_gc_mark_roots();
    quest_gc_cycle = true;
    quest_gc_cycle_debt = 0;
    quest_gc_cycle_retries = 0;
    quest_gc_cycle_slices = 0;
    uint64_t pause = quest_gc_now_ns() - t0;
    quest_gc_cycle_ns = pause;
    quest_gc_cycle_first_ns = pause;
    quest_gc_first_ns += pause;
    if (pause > quest_gc_first_max_ns) quest_gc_first_max_ns = pause;
    if (pause > quest_gc_pause_max_ns) quest_gc_pause_max_ns = pause;
    quest_gc_collecting = false;
}

/* An object allocated while a cycle marks is born marked, with its header
 * saying old, and, unless it holds no pointers, logged: the stores that
 * initialize it have no barriers, so the next slice scans it from the log,
 * by which time they are made or the compilers' barriers have logged it
 * again (section 3.5), and without that a pointer loaded from an object the
 * marker has not reached, stored here, and overwritten there would be
 * missed. The header word is stored here, flags and all */
static void quest_gc_born(uintptr_t base, size_t total, const QLayout *layout, size_t prefix) {
    uintptr_t obj = base + prefix;
    bool scanned = (layout->flags & Q_LAYOUT_NOSCAN) == 0;
    /* A large one goes to the work list, not the log, to be scanned in
     * pieces as the marker's own large objects are */
    bool logged = scanned && total <= Q_GC_SCAN_PIECE;
    ((uintptr_t *)obj)[-1] = (uintptr_t)layout | Q_HEADER_OLD | (logged ? Q_HEADER_LOGGED : 0);
    uintptr_t i = (obj - quest_gc_heap_lo) >> 3;
    quest_gc_start_bits[i >> 3] |= (uint8_t)(1u << (i & 7));
    quest_gc_marks[i >> 3] |= (uint8_t)(1u << (i & 7));
    size_t b = quest_gc_block_of(obj);
    if (quest_gc_blocks[b].state == QB_SMALL) {
        uintptr_t from = (base - quest_gc_heap_lo) >> Q_GC_LINE_BITS;
        uintptr_t to = (base + total - 1 - quest_gc_heap_lo) >> Q_GC_LINE_BITS;
        for (uintptr_t ln = from; ln <= to; ++ln) quest_gc_lines[ln] = 1;
    } else {
        quest_gc_large_live += total;
        memset(quest_gc_block_lines(b), 1, (size_t)quest_gc_blocks[b].run * Q_GC_BLOCK_LINES);
    }
    quest_gc_live_bytes += total;
    quest_gc_live_objects++;
    quest_gc_born_bytes += total;
    if (logged) quest_gc_log_push(obj);
    else if (scanned) quest_gc_push_work(obj);
}

/* Marks from the work list until `budget` bytes of objects are scanned (at
 * least one object, or one piece of a large one), or the list is empty and
 * no object is left part scanned. A large object is scanned a piece at a
 * time, so that a table of a million words is not one pause: what a later
 * piece holds is read when the piece is scanned, and a store into an earlier
 * one finds the object marked, and so logs it or marks its card */
static void quest_gc_mark_some(uint64_t budget) {
    uint64_t done = 0;
    while (quest_gc_piece != 0 || quest_gc_work_n > 0) {
        if (quest_gc_piece == 0) {
            uintptr_t obj = quest_gc_work[--quest_gc_work_n];
            size_t size = quest_gc_object_bytes(obj, quest_layout_of((const void *)obj));
            if (size <= Q_GC_SCAN_PIECE) {
                quest_gc_scan_object(obj);
                done += size;
                if (done >= budget) break;
                continue;
            }
            quest_gc_piece = obj;
            quest_gc_piece_at = obj;
        }
        uintptr_t end = quest_gc_piece +
                        quest_gc_object_bytes(quest_gc_piece, quest_layout_of((const void *)quest_gc_piece));
        uintptr_t hi = end - quest_gc_piece_at > Q_GC_SCAN_PIECE ? quest_gc_piece_at + Q_GC_SCAN_PIECE : end;
        quest_gc_scan_object_range(quest_gc_piece, quest_gc_piece_at, hi);
        done += hi - quest_gc_piece_at;
        quest_gc_piece_at = hi;
        if (hi == end) quest_gc_piece = 0;
        if (done >= budget) break;
    }
}

/* A slice, from the allocation slow path: once the program has allocated a
 * slice's worth since the last, what the barriers logged and the cards they
 * marked are scanned, as a minor collection scans them, and the work list is
 * marked from, the pace's bytes for each byte allocated, a megabyte at
 * most. Under `incremental`
 * every allocation has a slice, of one object. Not while collections are held
 * off (the stores a hold covers have no barriers). When the list is empty the
 * cycle tries to end */
static void quest_gc_cycle_step(size_t bytes) {
    quest_gc_cycle_debt += bytes;
    if (quest_gc_held != 0 || quest_gc_collecting) return;
    bool checking = (quest_gc_check_flags & QUEST_GC_CHECK_INCREMENTAL) != 0;
    if (!checking && quest_gc_cycle_debt < quest_gc_slice_bytes) return;
    /* What the allocation since the last slice has earned, up to a slice's
     * most: the rest of a large allocation's is left owing, so the slices
     * after this one, one at each allocation until it is paid, mark it */
    uint64_t budget = checking ? 0 : quest_gc_cycle_debt * quest_gc_pace;
    if (budget > quest_gc_slice_most) {
        budget = quest_gc_slice_most;
        quest_gc_cycle_debt -= quest_gc_slice_most / quest_gc_pace;
    } else {
        quest_gc_cycle_debt = 0;
    }
    quest_gc_collecting = true;
    uint64_t t0 = quest_gc_now_ns();
    quest_gc_drain_log(true);
    quest_gc_drain_cards(true);
    quest_gc_mark_some(budget);
    uint64_t pause = quest_gc_now_ns() - t0;
    quest_gc_cycle_ns += pause;
    quest_gc_cycle_slices++;
    quest_gc_slices++;
    quest_gc_slice_ns += pause;
    if (pause > quest_gc_slice_max_ns) quest_gc_slice_max_ns = pause;
    if (pause > quest_gc_pause_max_ns) quest_gc_pause_max_ns = pause;
    quest_gc_collecting = false;
    if (quest_gc_work_n == 0 && quest_gc_piece == 0) quest_gc_cycle_finish(false);
}

/* A cycle's last pause: the log and the cards scanned, the roots marked
 * again (the stack and the registers, where the program may have put a
 * pointer it loaded from an object the marker had not reached and then
 * overwrote, and the root tables, whose stores have no barriers), and the
 * marking finished; then the sweep and the rest of a full collection. What
 * the roots expose is unbounded in principle, so unless forced the pause
 * marks its budget and, if work is left, gives it back to the slices and
 * tries again when they have emptied the list, a few times at most before it
 * finishes whatever is left. Whether the cycle ended */
static bool quest_gc_cycle_finish(bool force) {
    if (quest_gc_collecting || quest_gc_held != 0) return false;
    quest_gc_collecting = true;
    bool checking = (quest_gc_check_flags & QUEST_GC_CHECK_INCREMENTAL) != 0;
    uint64_t t0 = quest_gc_now_ns();
    quest_gc_drain_log(true);
    quest_gc_drain_cards(true);
    quest_gc_mark_roots();
    if (!force && quest_gc_cycle_retries < Q_GC_FINAL_RETRIES) {
        quest_gc_mark_some(checking ? 0 : quest_gc_final_budget);
        if (quest_gc_work_n > 0 || quest_gc_piece != 0) {
            quest_gc_cycle_retries++;
            quest_gc_final_retried++;
            uint64_t pause = quest_gc_now_ns() - t0;
            quest_gc_cycle_ns += pause;
            quest_gc_final_ns += pause;
            if (pause > quest_gc_final_max_ns) quest_gc_final_max_ns = pause;
            if (pause > quest_gc_pause_max_ns) quest_gc_pause_max_ns = pause;
            quest_gc_collecting = false;
            return false;
        }
    }
    quest_gc_mark_some(UINT64_MAX);
    if (checking) quest_gc_check_cycle();
    quest_gc_cycle = false;
    quest_gc_sweep();
    quest_gc_young_bytes = 0;
    uint64_t pause = quest_gc_now_ns() - t0;
    quest_gc_cycle_ns += pause;
    quest_gc_final_ns += pause;
    if (pause > quest_gc_final_max_ns) quest_gc_final_max_ns = pause;
    if (pause > quest_gc_pause_max_ns) quest_gc_pause_max_ns = pause;
    quest_gc_pause_ns += quest_gc_cycle_ns;
    quest_gc_last_full_ns = quest_gc_cycle_ns;
    if (quest_gc_nursery_adapted == Q_GC_NO_NURSERY && ++quest_gc_fulls_without_nursery % 8 == 0) {
        quest_gc_nursery_adapted = quest_gc_nursery_cap();
    }
    if (quest_gc_live_bytes > quest_gc_live_bytes_max) quest_gc_live_bytes_max = quest_gc_live_bytes;
    if (quest_gc_live_lines > quest_gc_live_lines_max) quest_gc_live_lines_max = quest_gc_live_lines;
    if (quest_gc_stats >= 2) {
        fprintf(stderr, "quest: gc #%" PRIu64 ": live %" PRIu64 " KB in %" PRIu64 " KB of lines, heap %zu KB, %.2f ms"
                " in a cycle: first pause %.2f ms, %" PRIu64 " slices, last pause %.2f ms, %u retries\n",
                quest_gc_collections, quest_gc_live_bytes >> 10, (quest_gc_live_lines * Q_GC_LINE) >> 10,
                (quest_gc_used * Q_GC_BLOCK) >> 10, (double)quest_gc_cycle_ns / 1e6,
                (double)quest_gc_cycle_first_ns / 1e6, quest_gc_cycle_slices, (double)pause / 1e6,
                quest_gc_cycle_retries);
    }
    if ((quest_gc_check_flags & QUEST_GC_CHECK_LAYOUTS) != 0) quest_gc_check_heap();
    if ((quest_gc_check_flags & QUEST_GC_CHECK_ROOTS) != 0) quest_gc_check_roots();
    quest_gc_young_n = 0;
    quest_gc_collecting = false;
    if (checking) quest_gc_incremental_done();
    return true;
}

/* ---------------------------------------------------------------------------
 * The checking modes
 * ------------------------------------------------------------------------ */

/* How many bytes are allocated between the collections a check mode forces:
 * the default, and QUEST_GC_CHECK_INTERVAL in bytes */
static size_t quest_gc_check_interval = 64u << 20;


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

/* The `sites` mode: which code allocated each object, for a failing check's
 * report. The slow path's three callers (the allocating function, a runtime
 * function or compiled code, and the two above it) are read from the frame
 * records before each allocation and kept by the object's address in a
 * direct-mapped table outside the heap, where a later object at an address
 * that shares the slot replaces an earlier one's; a report names the
 * functions by dladdr, so compiled code's are its C or assembly symbols */
#define Q_GC_SITE_SLOTS ((size_t)1 << 20)
#define Q_GC_SITE_DEPTH 3
typedef struct QSite {
    uintptr_t obj;
    uintptr_t ra[Q_GC_SITE_DEPTH];
} QSite;
static QSite    *quest_gc_sites = NULL;
static uintptr_t quest_gc_site_pending[Q_GC_SITE_DEPTH];

/* Called from the slow path's frame, before the allocation */
static inline __attribute__((always_inline)) void quest_gc_site_read(void **slow) {
    void **frame = slow;
    for (size_t i = 0; i < Q_GC_SITE_DEPTH; ++i) {
        quest_gc_site_pending[i] = frame != NULL ? (uintptr_t)frame[1] : 0;
        frame = frame != NULL ? (void **)frame[0] : NULL;
        /* A frame record chain rises; anything else is not one */
        if (frame != NULL && ((uintptr_t)frame & 7) != 0) frame = NULL;
    }
}

static void quest_gc_note_site(uintptr_t obj) {
    if (quest_gc_sites == NULL) {
        quest_gc_sites = (QSite *)calloc(Q_GC_SITE_SLOTS, sizeof(QSite));
        if (quest_gc_sites == NULL) quest_gc_fatal("gc check: out of memory");
    }
    QSite *site = &quest_gc_sites[(obj >> 4) & (Q_GC_SITE_SLOTS - 1)];
    site->obj = obj;
    memcpy(site->ra, quest_gc_site_pending, sizeof site->ra);
}

/* Prints what allocated the object at w, or the object w points into (an
 * option's payload, a string's or an array's data), if `sites` kept it */
static void quest_gc_print_site(const char *what, uintptr_t w) {
    if (quest_gc_sites == NULL) return;
    for (uintptr_t obj = w; obj + 32 >= w && obj != 0; obj -= 8) {
        const QSite *site = &quest_gc_sites[(obj >> 4) & (Q_GC_SITE_SLOTS - 1)];
        if (site->obj != obj) continue;
        fprintf(stderr, "quest: gc check: %s %#" PRIxPTR " was allocated", what, obj);
        for (size_t i = 0; i < Q_GC_SITE_DEPTH && site->ra[i] != 0; ++i) {
            const char *symbol = "?";
#if defined(__APPLE__) || defined(__linux__)
            Dl_info info;
            if (dladdr((const void *)site->ra[i], &info) != 0 && info.dli_sname != NULL) symbol = info.dli_sname;
#endif
            fprintf(stderr, "%s %s", i == 0 ? " by" : ", called by", symbol);
        }
        fputc('\n', stderr);
        return;
    }
}

/* Which collection a failing check ran at: under `stress` the collections
 * fall by the count of allocations, so the number names the same one in the
 * next run (QUEST_GC_TRAP) */
static void quest_gc_check_where(void) {
    fprintf(stderr, "quest: gc check: at collection %" PRIu64 " (%s)\n", quest_gc_collections + quest_gc_minors,
            quest_gc_minor ? "minor" : "full");
}

Q_NORETURN static void quest_gc_check_fail(const QLayout *layout, const void *obj, const char *what, size_t word,
                                           uintptr_t value) {
    quest_gc_check_where();
    fprintf(stderr, "quest: gc check: layout %s: object %p: %s", layout->name, obj, what);
    if (word != (size_t)-1) fprintf(stderr, " at word %zu (value %#" PRIxPTR ")", word, value);
    fputc('\n', stderr);
    /* The object's first words, for the diagnosis */
    size_t n = layout->form == Q_LAYOUT_FIXED ? layout->words : word + 4;
    if (n > 16) n = 16;
    fprintf(stderr, "quest: gc check: words:");
    for (size_t i = 0; i < n; ++i) fprintf(stderr, " %#" PRIxPTR, ((const uintptr_t *)obj)[i]);
    fputc('\n', stderr);
    quest_gc_print_site("the object", (uintptr_t)obj);
    if (word != (size_t)-1) quest_gc_print_site("the word's object", value);
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
        quest_gc_check_where();
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

/* After a minor collection: walks the young blocks' live objects, which are
 * the ones that collection changed (the old blocks' were walked after the
 * last full collection, and a logged object's words were validated as it was
 * scanned) */
static void quest_gc_check_young(void) {
    quest_gc_checks++;
    for (size_t i = 0; i < quest_gc_young_n; ++i) {
        size_t b = quest_gc_young[i];
        const QBlock *blk = &quest_gc_blocks[b];
        if (blk->state == QB_LARGE_HEAD) {
            uintptr_t obj = quest_gc_large_object(b);
            if (obj != 0) quest_gc_check_object(obj, quest_gc_block_start(b), false);
            continue;
        }
        if (blk->state != QB_SMALL) continue;
        const uint8_t *starts = quest_gc_block_bits(quest_gc_start_bits, b);
        uintptr_t prev_end = quest_gc_block_start(b);
        for (size_t j = 0; j < Q_GC_BLOCK_BITMAP; ++j) {
            unsigned m = starts[j];
            while (m != 0) {
                unsigned bit = (unsigned)__builtin_ctz(m);
                m &= m - 1;
                uintptr_t obj = quest_gc_block_start(b) + (((uintptr_t)j * 8 + bit) << 3);
                prev_end = quest_gc_check_object(obj, prev_end, true);
            }
        }
    }
}

/* The `barriers` check, before a minor collection uses the log: the object w
 * is the address of or into, if it is young (unmarked); then every old object
 * that is not logged is scanned by its layout, and a pointer of its at a young
 * object, or an ambiguous word at one's start or payload, in a card that is
 * not dirty, is a store no barrier logged or marked */
static uintptr_t quest_gc_young_target(uintptr_t w) {
    if (!quest_gc_in_heap(w)) return 0;
    uintptr_t a = w & ~(uintptr_t)7;
    size_t b = quest_gc_block_of(a);
    const QBlock *blk = &quest_gc_blocks[b];
    if (blk->state == QB_FREE) return 0;
    if (blk->state == QB_LARGE_TAIL) {
        b -= blk->run;
        blk = &quest_gc_blocks[b];
    }
    uintptr_t obj = blk->state == QB_LARGE_HEAD ? quest_gc_large_object(b) : quest_gc_start_before(b, a);
    if (obj == 0 || a < obj || a >= obj + quest_gc_object_bytes(obj, quest_layout_of((const void *)obj))) return 0;
    return quest_gc_bit(quest_gc_marks, obj) ? 0 : obj;
}

static void quest_gc_check_barrier_word(const QLayout *layout, uintptr_t obj, size_t word, uint8_t kind) {
    if (kind != Q_WORD_POINTER && kind != Q_WORD_AMBIGUOUS) return;
    uintptr_t w = ((const uintptr_t *)obj)[word];
    if (w == 0) return;
    uintptr_t target = quest_gc_young_target(w);
    if (target == 0) return;
    /* An ambiguous word may be an integer (a packed location, say) that
     * happens to fall in a young object; a pointer in one is at an object or
     * at its payload (the word after its tag, or after its byte count and
     * descriptor), so only those are reported */
    if (kind == Q_WORD_AMBIGUOUS && w != target && w != target + 8 && w != target + 16) return;
    if (quest_gc_cards[(obj + word * 8 - quest_gc_heap_lo) >> Q_GC_CARD_BITS] != 0) return;    /* the card is dirty */
    quest_gc_check_fail(layout, (const void *)obj, kind == Q_WORD_POINTER ?
                        "an old object, not logged, with a pointer at a young object in a clean card: a store without "
                        "a barrier" :
                        "an old object, not logged, with an ambiguous word at a young object in a clean card: a store "
                        "without a barrier",
                        word, w);
}

static void quest_gc_check_barrier_object(uintptr_t obj) {
    const QLayout *l = quest_layout_of((const void *)obj);
    if (!quest_gc_bit(quest_gc_marks, obj)) return;                         /* young: scanned by the collection */
    if ((((const uintptr_t *)obj)[-1] & Q_HEADER_LOGGED) != 0) return;      /* logged: scanned by the collection */
    if ((l->flags & Q_LAYOUT_NOSCAN) != 0) return;
    switch (l->form) {
    case Q_LAYOUT_FIXED:
        for (size_t i = 0; i < l->words; ++i) quest_gc_check_barrier_word(l, obj, i, l->kinds[i]);
        break;
    case Q_LAYOUT_ARRAY: {
        for (size_t i = 0; i < l->words; ++i) quest_gc_check_barrier_word(l, obj, i, l->kinds[i]);
        int64_t n = *(const int64_t *)(obj + l->length_offset);
        size_t word = l->size / 8;
        for (int64_t e = 0; e < n; ++e) {
            for (size_t k = 0; k < l->element_words; ++k) quest_gc_check_barrier_word(l, obj, word++, l->kinds[l->words + k]);
        }
        break;
    }
    default: {
        size_t n = quest_sized_bytes((const void *)obj) / 8;
        for (size_t i = 0; i < n; ++i) quest_gc_check_barrier_word(l, obj, i, l->kinds[i % l->element_words]);
        break;
    }
    }
}

static void quest_gc_check_barriers(void) {
    for (size_t b = 0; b < quest_gc_high_water; ++b) {
        const QBlock *blk = &quest_gc_blocks[b];
        if (blk->state == QB_LARGE_HEAD) {
            uintptr_t obj = quest_gc_large_object(b);
            if (obj != 0) quest_gc_check_barrier_object(obj);
            b += blk->run - 1;
            continue;
        }
        if (blk->state != QB_SMALL) continue;
        const uint8_t *starts = quest_gc_block_bits(quest_gc_start_bits, b);
        for (size_t i = 0; i < Q_GC_BLOCK_BITMAP; ++i) {
            unsigned m = starts[i];
            while (m != 0) {
                unsigned bit = (unsigned)__builtin_ctz(m);
                m &= m - 1;
                quest_gc_check_barrier_object(quest_gc_block_start(b) + (((uintptr_t)i * 8 + bit) << 3));
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
    quest_gc_cover(quest_gc_hidden_limit, 2);
    quest_gc_cover(&quest_gc_piece, 1);
    quest_gc_cover(&quest_gc_piece_at, 1);
    quest_gc_cover(quest_gc_over_cursor, 2);
    quest_gc_cover(quest_gc_over_limit, 2);
    quest_gc_cover(&quest_gc_heap_lo, 1);
    quest_gc_cover(&quest_gc_heap_hi, 1);
    quest_gc_cover(&quest_gc_check_pending, 1);
    quest_gc_cover(&quest_gc_check_interval, 1);
    quest_gc_cover(&quest_gc_cards_dirtied, 1);
    quest_gc_cover(&quest_gc_dirty_n, 1);
    quest_gc_cover(&quest_gc_dirty_cap, 1);
    quest_gc_cover(&quest_gc_logged, 1);
    quest_gc_cover(&quest_gc_log_n, 1);
    quest_gc_cover(&quest_gc_log_cap, 1);
    quest_gc_cover(&quest_gc_young_n, 1);
    quest_gc_cover(&quest_gc_young_cap, 1);
    quest_gc_cover(&quest_gc_nursery_blocks, 1);
    quest_gc_cover(&quest_gc_nursery_adapted, 1);
    quest_gc_cover(&quest_gc_fulls_without_nursery, 1);
    quest_gc_cover(&quest_gc_minors, 1);
    quest_gc_cover(&quest_gc_minor_pause_ns, 1);
    quest_gc_cover(&quest_gc_minor_pause_max_ns, 1);
    quest_gc_cover(&quest_gc_young_bytes, 1);
    quest_gc_cover(&quest_gc_survived_bytes, 1);
    quest_gc_cover(&quest_gc_survived_objects, 1);
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
    quest_gc_cover(&quest_gc_holes, 1);
    quest_gc_cover(&quest_gc_frames_mapped, 1);
    quest_gc_cover(&quest_gc_frames_unmapped, 1);
    quest_gc_cover(&quest_gc_frame_unit_cap, 1);
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
    quest_serialization_roots(quest_gc_cover);
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

static void quest_gc_force_by_count(void) {
    if (quest_gc_collect_every == 0 || quest_gc_allocated_objects % quest_gc_collect_every != 0) return;
    if (quest_gc_collect_trap != 0 && quest_gc_forced >= quest_gc_collect_trap) return;
    quest_gc_forced++;
    if (quest_gc_forced == quest_gc_collect_trap) quest_gc_trap();
    fprintf(stderr, "FORCED %" PRIu64 "\n", quest_gc_forced);
    quest_gc_collect();
}

/* The `stress` mode: a collection before every allocation, with what the
 * other modes check at each, so that an object is old one allocation after
 * its own and whatever the roots miss is reclaimed (and under `poison`
 * overwritten) at once: a store without a barrier, an initializing store with
 * an allocation before it, and a pointer a stack map or a root table leaves
 * out all fail within a few allocations of the fault, in a test of a few
 * lines. The collections are minor but for each sixteenth, a full one, which
 * is the one that reclaims an old object the roots miss.
 *
 * What bounds the cost: QUEST_GC_STRESS is how many allocations pass between
 * collections (1 by default), and that count doubles each time the
 * collections since the last doubling have walked QUEST_GC_STRESS_BUDGET
 * megabytes of heap (256 by default; 0 never doubles it), a collection
 * counted as the heap in use. So a test of a few thousand allocations is
 * checked at every one, and the compiler, with a heap of tens of megabytes,
 * at its first few hundred and then at a thinning sample, for a second or
 * two in all. The collections fall
 * by count, so a failure repeats, and a check's report gives its collection's
 * number (QUEST_GC_TRAP stops before it) */
static uint64_t quest_gc_stress_every = 1, quest_gc_stress_budget = 256 * ((1u << 20) / Q_GC_BLOCK);
static uint64_t quest_gc_stress_since = 0, quest_gc_stress_forced = 0, quest_gc_stress_walked = 0;

static void quest_gc_stress_tick(void) {
    if (quest_gc_never_collect || quest_gc_held != 0 || quest_gc_collecting) return;
    if (++quest_gc_stress_since < quest_gc_stress_every) return;
    quest_gc_stress_since = 0;
    quest_gc_stress_forced++;
    quest_gc_stress_walked += quest_gc_used + 1;
    if (quest_gc_stress_budget != 0 && quest_gc_stress_walked >= quest_gc_stress_budget) {
        quest_gc_stress_walked = 0;
        quest_gc_stress_every *= 2;
    }
    quest_gc_collect_kind(quest_gc_nursery_blocks != 0 && quest_gc_stress_forced % 16 != 0);
}

/* The `incremental` mode: a cycle is always under way, its slices one object
 * each, one before every allocation, and each cycle's marks are checked
 * against a stop-the-world marking of the same heap (quest_gc_check_cycle),
 * so that an object a barrier let slip past the marker is reported at the
 * end of the cycle that lost it, not when its memory is used again. As
 * `stress`, the cost is bounded by thinning: once the cycles have walked
 * QUEST_GC_STRESS_BUDGET megabytes of heap (each walks it twice), a gap of
 * allocations is left between a cycle and the next, 1024 and then doubling */
static uint64_t quest_gc_incremental_gap = 0, quest_gc_incremental_since = 0, quest_gc_incremental_walked = 0;

static void quest_gc_incremental_tick(void) {
    if (quest_gc_cycle || quest_gc_never_collect || quest_gc_held != 0 || quest_gc_collecting) return;
    if (quest_gc_incremental_since++ < quest_gc_incremental_gap) return;
    quest_gc_incremental_since = 0;
    quest_gc_cycle_start();
}

static void quest_gc_incremental_done(void) {
    quest_gc_incremental_walked += 2 * (quest_gc_used + 1);
    if (quest_gc_stress_budget != 0 && quest_gc_incremental_walked >= quest_gc_stress_budget) {
        quest_gc_incremental_walked = 0;
        quest_gc_incremental_gap = quest_gc_incremental_gap == 0 ? 1024 : 2 * quest_gc_incremental_gap;
    }
}

/* At the end of a cycle's marking, under `incremental`: the same heap is
 * marked again from the same roots with the world stopped, and an object
 * that marking reaches and the cycle did not mark is one the cycle would
 * have freed in use. The cycle's own marks, which may hold more (what died
 * while it ran), are put back for the sweep */
static void quest_gc_check_cycle(void) {
    size_t bytes = quest_gc_high_water * Q_GC_BLOCK_BITMAP;
    uint8_t *cycle = (uint8_t *)malloc(bytes > 0 ? bytes : 1);
    if (cycle == NULL) quest_gc_fatal("out of memory checking a cycle's marks");
    memcpy(cycle, quest_gc_marks, bytes);
    uint64_t live_bytes = quest_gc_live_bytes, live_objects = quest_gc_live_objects, large = quest_gc_large_live;
    memset(quest_gc_marks, 0, bytes);
    quest_gc_work_n = 0;
    quest_gc_mark_roots();
    while (quest_gc_work_n > 0) quest_gc_scan_object(quest_gc_work[--quest_gc_work_n]);
    for (size_t i = 0; i < bytes; ++i) {
        unsigned lost = quest_gc_marks[i] & (unsigned)~cycle[i] & 0xffu;
        if (lost != 0) {
            uintptr_t obj = quest_gc_heap_lo + (((uintptr_t)i * 8 + (unsigned)__builtin_ctz(lost)) << 3);
            quest_gc_check_fail(quest_layout_of((const void *)obj), (const void *)obj,
                                "reached from the roots, but not marked by the cycle that just ended", (size_t)-1, 0);
        }
    }
    memcpy(quest_gc_marks, cycle, bytes);
    free(cycle);
    quest_gc_live_bytes = live_bytes;
    quest_gc_live_objects = live_objects;
    quest_gc_large_live = large;
}

/* Called by the slow path before each allocation while a mode is on: counts
 * it, and forces a collection (which runs the checks) when enough has been
 * allocated since the last. Not inline, so that its frame record is one
 * below the slow path's, as `allocations` and `sites` take it to be */
__attribute__((noinline)) static void quest_gc_check_tick(size_t sz, size_t header) {
    quest_gc_allocated_objects++;
    if ((quest_gc_check_flags & QUEST_GC_CHECK_COLLECT) != 0 && quest_gc_collect_every != 0) {
        quest_gc_force_by_count();
        return;
    }
    if ((quest_gc_check_flags & QUEST_GC_CHECK_SITES) != 0) {
        void **frame = (void **)__builtin_frame_address(0);
        quest_gc_site_read(frame != NULL ? (void **)frame[0] : NULL);
    }
    if ((quest_gc_check_flags & QUEST_GC_CHECK_STRESS) != 0) quest_gc_stress_tick();
    if ((quest_gc_check_flags & QUEST_GC_CHECK_INCREMENTAL) != 0) quest_gc_incremental_tick();
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
    if (quest_gc_check_pending >= quest_gc_check_due() && quest_gc_held == 0) {
        quest_gc_check_pending = 0;
        if (!quest_gc_never_collect) quest_gc_collect();
    }
}

static void quest_gc_print_stats(void) {
    fprintf(stderr, "quest: gc stats: collections %" PRIu64 ", pauses %.1f ms (max %.2f ms), allocated %" PRIu64
            " MB in %" PRIu64 " holes, heap max %zu MB, live max %" PRIu64 " KB in %" PRIu64 " KB of lines, live now %"
            PRIu64 " KB in %" PRIu64 " KB of lines (%" PRIu64 " objects, %" PRIu64 " KB large)\n",
            quest_gc_collections, (double)quest_gc_pause_ns / 1e6, (double)quest_gc_pause_max_ns / 1e6,
            quest_gc_hole_bytes >> 20, quest_gc_holes, (quest_gc_used_max * Q_GC_BLOCK) >> 20,
            quest_gc_live_bytes_max >> 10,
            (quest_gc_live_lines_max * Q_GC_LINE) >> 10, quest_gc_live_bytes >> 10,
            (quest_gc_live_lines * Q_GC_LINE) >> 10, quest_gc_live_objects, quest_gc_large_live >> 10);
    fprintf(stderr, "quest: gc minors: %" PRIu64 ", pauses %.1f ms (max %.2f ms), survived %" PRIu64 " KB (%" PRIu64
            " objects), logged %" PRIu64 " objects, %" PRIu64 " cards\n", quest_gc_minors,
            (double)quest_gc_minor_pause_ns / 1e6, (double)quest_gc_minor_pause_max_ns / 1e6,
            quest_gc_survived_bytes >> 10, quest_gc_survived_objects, quest_gc_logged, quest_gc_cards_dirtied);
    if (quest_gc_cycles > 0) {
        fprintf(stderr, "quest: gc cycles: %" PRIu64 ", first pauses %.1f ms (max %.2f ms), %" PRIu64 " slices %.1f ms "
                "(max %.2f ms), last pauses %.1f ms (max %.2f ms), %" PRIu64 " retried, %" PRIu64 " MB born marked\n",
                quest_gc_cycles, (double)quest_gc_first_ns / 1e6, (double)quest_gc_first_max_ns / 1e6, quest_gc_slices,
                (double)quest_gc_slice_ns / 1e6, (double)quest_gc_slice_max_ns / 1e6, (double)quest_gc_final_ns / 1e6,
                (double)quest_gc_final_max_ns / 1e6, quest_gc_final_retried, quest_gc_born_bytes >> 20);
    }
    if (quest_gc_frame_unit_n > 0) {
        fprintf(stderr, "quest: gc frames: %" PRIu64 " scanned by their tables, %" PRIu64 " whole, of %zu units' "
                "tables\n", quest_gc_frames_mapped, quest_gc_frames_unmapped, quest_gc_frame_unit_n);
    }
    if ((quest_gc_check_flags & QUEST_GC_CHECK_STRESS) != 0) {
        fprintf(stderr, "quest: gc stress: %" PRIu64 " collections forced, the last every %" PRIu64 " allocations of %"
                PRIu64 "\n", quest_gc_stress_forced, quest_gc_stress_every, quest_gc_allocated_objects);
    }
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
    fprintf(stderr, "quest: gc barriers: %" PRIu64 " objects logged, %" PRIu64 " cards marked\n", quest_gc_logged,
            quest_gc_cards_dirtied);
    fprintf(stderr, "quest: gc check: %" PRIu64 " checks, %" PRIu64 " objects\n", quest_gc_checks,
            quest_gc_objects_checked);
    fprintf(stderr, "quest: gc allocated: %" PRIu64 " objects, %" PRIu64 " bytes, %" PRIu64 " header bytes\n",
            quest_gc_allocated_objects, quest_gc_allocated_bytes, quest_gc_allocated_headers);
    if (quest_gc_count_n == 0) return;
    fprintf(stderr, "%12s %12s %12s %12s %12s %12s  %s\n", "objects", "ambiguous", "amb.heap", "suspicious", "logged",
            "logged KB", "layout");
    for (size_t i = 0; i < quest_gc_count_n; ++i) {
        const QLayoutCount *c = &quest_gc_counts[i];
        fprintf(stderr, "%12" PRIu64 " %12" PRIu64 " %12" PRIu64 " %12" PRIu64 " %12" PRIu64 " %12" PRIu64 "  %s\n",
                c->objects, c->ambiguous, c->ambiguous_heap, c->suspicious, c->logged, c->logged_bytes >> 10,
                c->layout->name);
    }
    fflush(stderr);
}

/* Reads QUEST_GC_CHECK, a comma-separated list of modes (`layouts`, `roots`,
 * `poison`, `collect`, which only forces the collections the others would, or
 * one every QUEST_GC_COLLECT_EVERY allocations, `allocations`, `barriers`,
 * `stress`, `sites`, and `report`, which prints the counts at exit),
 * QUEST_GC_CHECK_INTERVAL, QUEST_GC_STRESS (allocations between a stress
 * collection and the next), QUEST_GC_STRESS_BUDGET (megabytes walked before
 * that count doubles), QUEST_GC_TRAP (the collection quest_gc_trap is called
 * before), QUEST_GC_STATS (1 for a summary at exit, `each` for a line per
 * collection too), QUEST_GC_MIN_HEAP (megabytes), QUEST_GC_NURSERY (megabytes
 * between minor collections; 0 for full collections alone), QUEST_GC_MAPS
 * (0 to scan every frame whole, the frame tables unread), and
 * QUEST_GC_CHECK_CHILDREN (the modes of the programs this one runs) */
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
            else if (n == 8 && strncmp(p, "barriers", 8) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_BARRIERS;
            else if (n == 6 && strncmp(p, "stress", 6) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_STRESS;
            else if (n == 5 && strncmp(p, "sites", 5) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_SITES;
            else if (n == 11 && strncmp(p, "incremental", 11) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_INCREMENTAL;
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
    const char *stress = getenv("QUEST_GC_STRESS");
    if (stress != NULL && stress[0] != '\0' && strtoull(stress, NULL, 10) > 0) {
        quest_gc_stress_every = strtoull(stress, NULL, 10);
    }
    const char *budget = getenv("QUEST_GC_STRESS_BUDGET");
    if (budget != NULL && budget[0] != '\0') {
        quest_gc_stress_budget = strtoull(budget, NULL, 10) * ((1u << 20) / Q_GC_BLOCK);
    }
    /* QUEST_GC_INCREMENTAL=0: full collections stop the world; QUEST_GC_PAUSE:
     * the milliseconds a full collection may take stopping the world before
     * the next is a cycle (0: every one the heap asks for is a cycle);
     * QUEST_GC_PACE: bytes a cycle marks per byte allocated; QUEST_GC_SLICE:
     * kilobytes allocated between a cycle's slices */
    const char *incremental = getenv("QUEST_GC_INCREMENTAL");
    if (incremental != NULL && incremental[0] == '0') quest_gc_incremental = false;
    const char *goal = getenv("QUEST_GC_PAUSE");
    if (goal != NULL && goal[0] != '\0') quest_gc_pause_goal_ns = strtoull(goal, NULL, 10) * 1000000;
    const char *pace = getenv("QUEST_GC_PACE");
    if (pace != NULL && pace[0] != '\0' && strtoull(pace, NULL, 10) > 0) {
        quest_gc_pace = (size_t)strtoull(pace, NULL, 10);
    }
    const char *slice = getenv("QUEST_GC_SLICE");
    if (slice != NULL && slice[0] != '\0') quest_gc_slice_bytes = (size_t)strtoull(slice, NULL, 10) << 10;
    const char *trap_at = getenv("QUEST_GC_TRAP");
    if (trap_at != NULL && trap_at[0] != '\0') quest_gc_trap_at = strtoull(trap_at, NULL, 10);
    const char *stats = getenv("QUEST_GC_STATS");
    if (stats != NULL && stats[0] != '\0') quest_gc_stats = strcmp(stats, "each") == 0 ? 2 : 1;
    const char *min_heap = getenv("QUEST_GC_MIN_HEAP");
    if (min_heap != NULL && min_heap[0] != '\0') {
        unsigned long long mb = strtoull(min_heap, NULL, 10);
        if (mb > 0) quest_gc_min_heap_blocks = (size_t)(mb << 20) / Q_GC_BLOCK;
    }
    const char *nursery = getenv("QUEST_GC_NURSERY");
    if (nursery != NULL && nursery[0] != '\0') {
        quest_gc_nursery_blocks = (size_t)(strtoull(nursery, NULL, 10) << 20) / Q_GC_BLOCK;
        quest_gc_nursery_adapted = quest_gc_nursery_blocks;
    }
    if (getenv("QUEST_GC_NEVER") != NULL) quest_gc_never_collect = true;
    /* QUEST_GC_MAPS=0: every frame scanned whole, the frame tables unread */
    const char *maps = getenv("QUEST_GC_MAPS");
    if (maps != NULL && maps[0] == '0') quest_gc_use_maps = false;
    /* QUEST_GC_CHECK_CHILDREN: the modes of the programs this one runs, in
     * place of its own, so that a compiler can run under the plain checks
     * and the program it builds and runs under `stress` (tools/check) */
    const char *children = getenv("QUEST_GC_CHECK_CHILDREN");
    if (children != NULL) {
        setenv("QUEST_GC_CHECK", children, 1);
        unsetenv("QUEST_GC_CHECK_CHILDREN");
    }
    if (quest_gc_check_flags != 0 || quest_gc_stats != 0) atexit(quest_gc_at_exit);
}

void quest_gc_init(void) {
    quest_gc_read_options();
    quest_gc_setup();
}
