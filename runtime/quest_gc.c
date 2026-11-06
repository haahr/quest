/* The collector's side of the runtime (docs/collector.md): the layouts of the
 * objects the runtime allocates, the collector's initialization, and the
 * checking modes of QUEST_GC_CHECK. Allocation itself is the header's inline
 * quest_alloc and its variants, which prepend a header word naming each
 * object's layout; while the collector is Boehm's, the header is the only use
 * the layouts have, and the `layouts` mode is what checks them. */

#include "quest_runtime.h"

#include <inttypes.h>
#include <stdlib.h>
#include <string.h>

#ifndef QUEST_NOGC
#  include <gc/gc_mark.h>
#endif
#if defined(__APPLE__)
#  include <dlfcn.h>
#  include <mach-o/getsect.h>
#  include <mach-o/ldsyms.h>
#elif defined(__linux__)
#  include <dlfcn.h>
extern char __data_start[];
extern char _end[];
#endif

/* ---------------------------------------------------------------------------
 * The runtime's layouts
 *
 * Each object the runtime allocates names one of these. A fixed layout lists
 * its words' kinds; an array layout its header's words and then its element's;
 * a sized layout its element's alone. The kinds are checked against the C
 * structs' sizes where a static assertion can (quest_gc_check_layout checks
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
Q_ARRAY(quest_layout_array_scalar, "QArray(scalar)", 8, 0, 1, S, S);
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
 * Initialization and the checking modes
 * ------------------------------------------------------------------------ */

int    quest_gc_check_flags = 0;
size_t quest_gc_check_pending = 0;

/* ---------------------------------------------------------------------------
 * Write barriers and root tables
 * ------------------------------------------------------------------------ */

/* How many times each barrier was called: with an object, and with a slot */
static uint64_t quest_barrier_counts[2];

void quest_barrier(const void *obj)   { (void)obj;  quest_barrier_counts[0]++; }
void quest_barrier_slot(const void *slot) { (void)slot; quest_barrier_counts[1]++; }

/* The root tables registered, outside the collected heap */
static const QRootEntry **quest_gc_root_tables = NULL;
static size_t             quest_gc_root_table_n = 0;
static size_t             quest_gc_root_table_cap = 0;

void quest_register_roots(const QRootEntry *roots) {
    if (quest_gc_root_table_n == quest_gc_root_table_cap) {
        size_t cap = quest_gc_root_table_cap > 0 ? 2 * quest_gc_root_table_cap : 64;
        const QRootEntry **grown = (const QRootEntry **)realloc((void *)quest_gc_root_tables, cap * sizeof *grown);
        if (grown == NULL) { fprintf(stderr, "quest: out of memory registering roots\n"); exit(70); }
        quest_gc_root_tables = grown;
        quest_gc_root_table_cap = cap;
    }
    quest_gc_root_tables[quest_gc_root_table_n++] = roots;
}

/* How many bytes are allocated between checks of the heap: the default, and
 * QUEST_GC_CHECK_INTERVAL in bytes */
static size_t quest_gc_check_interval = 64u << 20;

/* Counts per layout, for the report */
typedef struct QLayoutCount {
    const QLayout *layout;
    uint64_t       objects;
    uint64_t       ambiguous;         /* ambiguous words */
    uint64_t       suspicious;        /* scalar words that are addresses of heap objects */
    uint64_t       ambiguous_heap;    /* ambiguous words that are addresses of heap objects */
    uint64_t       dangling;          /* pointer words to freed objects, in objects resurrected conservatively */
} QLayoutCount;

static QLayoutCount *quest_gc_counts = NULL;
static size_t        quest_gc_count_n = 0;
static uint64_t      quest_gc_checks = 0;
static uint64_t      quest_gc_objects_checked = 0;
static uint64_t      quest_gc_foreign = 0;  /* objects of the collector's own, without a header */
/* What was allocated while a mode was on: objects, their bytes, their
 * headers' bytes, and what Boehm's 16-byte granules make of each with and
 * without its header, for the growth the headers cost (docs/collector.md
 * step 1) */
static uint64_t      quest_gc_allocated_objects = 0;
static uint64_t      quest_gc_allocated_bytes = 0;
static uint64_t      quest_gc_allocated_headers = 0;
static uint64_t      quest_gc_granules_with = 0;
static uint64_t      quest_gc_granules_without = 0;

static uint64_t quest_gc_granules(uint64_t bytes) { return (bytes + 15) / 16 * 16; }

#ifndef QUEST_NOGC

static size_t quest_gc_count_cap = 0;

static QLayoutCount *quest_gc_count_of(const QLayout *layout) {
    for (size_t i = 0; i < quest_gc_count_n; ++i) {
        if (quest_gc_counts[i].layout == layout) return &quest_gc_counts[i];
    }
    if (quest_gc_count_n == quest_gc_count_cap) {
        size_t cap = quest_gc_count_cap > 0 ? 2 * quest_gc_count_cap : 64;
        /* The counts are the checker's own, outside the collected heap */
        QLayoutCount *grown = (QLayoutCount *)realloc(quest_gc_counts, cap * sizeof(QLayoutCount));
        if (grown == NULL) { fprintf(stderr, "quest: gc check: out of memory\n"); exit(70); }
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

/* Whether w is the address of (or into) an object of the collected heap, and
 * whether it is in the heap's range at all */
static bool quest_gc_in_heap(uintptr_t w)  { return GC_is_heap_ptr((const void *)w) != 0; }
static bool quest_gc_is_object(uintptr_t w) { return GC_base((void *)w) != NULL; }

/* Checks one word of kind `kind` */
static void quest_gc_check_word(const QLayout *layout, const void *obj, QLayoutCount *c, size_t word, uint8_t kind) {
    uintptr_t w = ((const uintptr_t *)obj)[word];
    switch (kind) {
    case Q_WORD_POINTER:
        /* Null, outside the heap (static data, code, the stack), or an
         * object's address or inside one (a proxy's tagged address, a
         * record's payload, an embedded box) */
        if (w != 0 && quest_gc_in_heap(w) && !quest_gc_is_object(w)) {
            /* A pointer into the heap at nothing allocated: dangling. Boehm
             * marks conservatively, so a dead object that a stale stack word
             * points at is enumerated as reachable with the words it died
             * with, among them pointers to objects freed since, and nothing
             * tells such an object from a live one; so a dangling pointer is
             * counted, per layout, and the report shows where they are. The
             * collector of docs/collector.md never resurrects a dead object
             * (its decision 14), and the check can be strict then. */
            c->dangling++;
        }
        break;
    case Q_WORD_SCALAR:
        if (w != 0 && quest_gc_in_heap(w) && quest_gc_is_object(w)) c->suspicious++;
        break;
    case Q_WORD_AMBIGUOUS:
        c->ambiguous++;
        if (w != 0 && quest_gc_in_heap(w) && quest_gc_is_object(w)) c->ambiguous_heap++;
        break;
    default:
        quest_gc_check_fail(layout, obj, "a word of an unknown kind in its layout", word, (uintptr_t)kind);
    }
}

/* Checks a reachable object: its layout's sizes against the allocation's, and
 * each described word */
static void quest_gc_check_object(void *base, size_t bytes, void *client_data) {
    (void)client_data;
    const uintptr_t *words = (const uintptr_t *)base;
    const QLayout *layout;
    const void *obj;
    size_t size;       /* the object's bytes after its header */
    bool sized = (words[0] & 1u) != 0;
    if (sized) {
        layout = (const QLayout *)(words[1] & Q_HEADER_LAYOUT_MASK);
        obj = words + 2;
        size = (size_t)(words[0] >> 1);
        if (bytes < size + 2 * sizeof(uintptr_t)) {
            quest_gc_check_fail(layout, obj, "a sized allocation smaller than its recorded size", (size_t)-1, 0);
        }
    } else {
        layout = (const QLayout *)(words[0] & Q_HEADER_LAYOUT_MASK);
        obj = words + 1;
        size = bytes - sizeof(uintptr_t);
    }
    /* The collector's own internal objects are reachable too, and have no
     * header: a first word that is zero, or not the address of static data
     * laid out as a layout is, marks one, which is counted and skipped */
    if (layout == NULL || GC_is_heap_ptr(layout) || layout->form > Q_LAYOUT_SIZED) {
        quest_gc_foreign++;
        return;
    }
    QLayoutCount *c = quest_gc_count_of(layout);
    quest_gc_objects_checked++;
    c->objects++;
    if ((layout->flags & Q_LAYOUT_NOSCAN) != 0) return;
    switch (layout->form) {
    case Q_LAYOUT_FIXED: {
        if (sized) quest_gc_check_fail(layout, obj, "a fixed layout on a sized allocation", (size_t)-1, 0);
        if (size < layout->size) {
            quest_gc_check_fail(layout, obj, "an allocation smaller than its layout", (size_t)-1, 0);
        }
        if (layout->words != (layout->size + 7) / 8) {
            quest_gc_check_fail(layout, obj, "a layout whose words do not cover its size", (size_t)-1, 0);
        }
        for (size_t i = 0; i < layout->words; ++i) quest_gc_check_word(layout, obj, c, i, layout->kinds[i]);
        break;
    }
    case Q_LAYOUT_ARRAY: {
        if (sized) quest_gc_check_fail(layout, obj, "an array layout on a sized allocation", (size_t)-1, 0);
        if (size < layout->size) {
            quest_gc_check_fail(layout, obj, "an allocation smaller than its layout", (size_t)-1, 0);
        }
        int64_t n = *(const int64_t *)((const char *)obj + layout->length_offset);
        if (n < 0 || (size - layout->size) / 8 < (uint64_t)n * layout->element_words) {
            quest_gc_check_fail(layout, obj, "an element count its allocation cannot hold", (size_t)-1, (uintptr_t)n);
        }
        for (size_t i = 0; i < layout->words; ++i) quest_gc_check_word(layout, obj, c, i, layout->kinds[i]);
        size_t word = layout->size / 8;
        for (int64_t e = 0; e < n; ++e) {
            for (size_t k = 0; k < layout->element_words; ++k) {
                quest_gc_check_word(layout, obj, c, word++, layout->kinds[layout->words + k]);
            }
        }
        break;
    }
    case Q_LAYOUT_SIZED: {
        if (!sized) quest_gc_check_fail(layout, obj, "a sized layout on an allocation without a size", (size_t)-1, 0);
        size_t words_in = size / 8;
        for (size_t word = 0; word < words_in; ++word) {
            quest_gc_check_word(layout, obj, c, word, layout->kinds[word % layout->element_words]);
        }
        break;
    }
    default:
        quest_gc_check_fail(layout, obj, "a layout of an unknown form", (size_t)-1, (uintptr_t)layout->form);
    }
}

static void *quest_gc_enumerate(void *client_data) {
    GC_enumerate_reachable_objects_inner(quest_gc_check_object, client_data);
    return NULL;
}

/* Collects, then walks every reachable object by its layout */
void quest_gc_check_heap(void) {
    quest_gc_checks++;
    GC_gcollect();
    GC_call_with_alloc_lock(quest_gc_enumerate, NULL);
}

/* The roots check: every word of the program's data segment that is the
 * address of (or into) a heap object must lie in a registered root table or
 * in a root the runtime lists, or the collector of step 3 would not know it.
 * The covered slots are gathered on each check (a few hundred); an uncovered
 * word is reported with its symbol, and the program fails at exit. */
typedef struct QRootSlot { uintptr_t low, high; } QRootSlot;
static QRootSlot *quest_gc_covered = NULL;
static size_t     quest_gc_covered_n = 0, quest_gc_covered_cap = 0;
static uint64_t   quest_gc_uncovered = 0;

static void quest_gc_cover(void *slot, size_t words) {
    if (quest_gc_covered_n == quest_gc_covered_cap) {
        size_t cap = quest_gc_covered_cap > 0 ? 2 * quest_gc_covered_cap : 256;
        QRootSlot *grown = (QRootSlot *)realloc(quest_gc_covered, cap * sizeof *grown);
        if (grown == NULL) { fprintf(stderr, "quest: gc check: out of memory\n"); exit(70); }
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
        if (w == 0 || !quest_gc_in_heap(w) || !quest_gc_is_object(w)) continue;
        if (quest_gc_is_covered((uintptr_t)p)) continue;
        quest_gc_uncovered++;
        const char *symbol = "?";
        Dl_info info;
        if (dladdr((const void *)p, &info) != 0 && info.dli_sname != NULL) symbol = info.dli_sname;
        fprintf(stderr, "quest: gc check: root %p (%s, in %s) holds the heap pointer %#" PRIxPTR
                " but no root table or listed root covers it\n", (const void *)p, symbol, name, w);
    }
}

/* The checker's own counters, whose values can look like heap addresses, so
 * that the scan passes over them as it does a covered root */
static void quest_gc_skip_own_counters(void) {
    quest_gc_cover(&quest_gc_check_pending, 1);
    quest_gc_cover(&quest_gc_check_interval, 1);
    quest_gc_cover(quest_barrier_counts, 2);
    quest_gc_cover(&quest_gc_checks, 1);
    quest_gc_cover(&quest_gc_objects_checked, 1);
    quest_gc_cover(&quest_gc_foreign, 1);
    quest_gc_cover(&quest_gc_allocated_objects, 1);
    quest_gc_cover(&quest_gc_allocated_bytes, 1);
    quest_gc_cover(&quest_gc_allocated_headers, 1);
    quest_gc_cover(&quest_gc_granules_with, 1);
    quest_gc_cover(&quest_gc_granules_without, 1);
    quest_gc_cover(&quest_gc_uncovered, 1);
    quest_gc_cover(&quest_gc_count_n, 1);
    quest_gc_cover(&quest_gc_count_cap, 1);
    quest_gc_cover(&quest_gc_root_table_n, 1);
    quest_gc_cover(&quest_gc_root_table_cap, 1);
    quest_gc_cover(&quest_gc_covered_n, 1);
    quest_gc_cover(&quest_gc_covered_cap, 1);
}

static void quest_gc_check_roots(void) {
    quest_gc_covered_n = 0;
    quest_gc_skip_own_counters();
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

#else  /* QUEST_NOGC: nothing enumerates the heap, so nothing is checked */

void quest_gc_check_heap(void) { quest_gc_checks++; }
static void quest_gc_check_roots(void) {}
static uint64_t quest_gc_uncovered = 0;

#endif

/* A check walks the whole heap, so between checks at least four times the
 * heap's size is allocated, whatever the interval asks, which keeps the
 * checks to a fraction of a program's time however large its heap */
static size_t quest_gc_check_due(void) {
    size_t due = quest_gc_check_interval;
#ifndef QUEST_NOGC
    size_t heap = 4 * GC_get_heap_size();
    if (heap > due) due = heap;
#endif
    return due;
}

void quest_gc_check_tick(size_t sz, size_t header) {
    quest_gc_allocated_objects++;
    quest_gc_allocated_bytes += sz;
    quest_gc_allocated_headers += header;
    quest_gc_granules_with += quest_gc_granules(sz + header);
    quest_gc_granules_without += quest_gc_granules(sz);
    quest_gc_check_pending += sz;
    if (quest_gc_check_pending >= quest_gc_check_due()) {
        quest_gc_check_pending = 0;
        if ((quest_gc_check_flags & QUEST_GC_CHECK_LAYOUTS) != 0) quest_gc_check_heap();
        if ((quest_gc_check_flags & QUEST_GC_CHECK_ROOTS) != 0) quest_gc_check_roots();
    }
}

/* At exit: a last check, and with `report`, the counts per layout */
static void quest_gc_check_at_exit(void) {
    if ((quest_gc_check_flags & QUEST_GC_CHECK_LAYOUTS) != 0) quest_gc_check_heap();
    if ((quest_gc_check_flags & QUEST_GC_CHECK_ROOTS) != 0) {
        quest_gc_check_roots();
        if (quest_gc_uncovered > 0) {
            fprintf(stderr, "quest: gc check: %" PRIu64 " roots uncovered\n", quest_gc_uncovered);
            fflush(stderr);
            abort();
        }
    }
    if ((quest_gc_check_flags & QUEST_GC_CHECK_REPORT) == 0) return;
    fprintf(stderr, "quest: gc barriers: %" PRIu64 " on objects, %" PRIu64 " on slots\n", quest_barrier_counts[0],
            quest_barrier_counts[1]);
    fprintf(stderr, "quest: gc check: %" PRIu64 " checks, %" PRIu64 " objects, %" PRIu64 " foreign\n",
            quest_gc_checks, quest_gc_objects_checked, quest_gc_foreign);
    fprintf(stderr, "quest: gc allocated: %" PRIu64 " objects, %" PRIu64 " bytes, %" PRIu64 " header bytes; "
            "in Boehm's granules %" PRIu64 " bytes with headers, %" PRIu64 " without\n",
            quest_gc_allocated_objects, quest_gc_allocated_bytes, quest_gc_allocated_headers, quest_gc_granules_with,
            quest_gc_granules_without);
    if (quest_gc_count_n == 0) return;
    fprintf(stderr, "%12s %12s %12s %12s %10s  %s\n", "objects", "ambiguous", "amb.heap", "suspicious", "dangling",
            "layout");
    for (size_t i = 0; i < quest_gc_count_n; ++i) {
        const QLayoutCount *c = &quest_gc_counts[i];
        fprintf(stderr, "%12" PRIu64 " %12" PRIu64 " %12" PRIu64 " %12" PRIu64 " %10" PRIu64 "  %s\n", c->objects,
                c->ambiguous, c->ambiguous_heap, c->suspicious, c->dangling, c->layout->name);
    }
    fflush(stderr);
}

/* Reads QUEST_GC_CHECK, a comma-separated list of modes (`layouts`, and
 * `report`, which prints the counts at exit), and QUEST_GC_CHECK_INTERVAL */
static void quest_gc_read_options(void) {
    const char *modes = getenv("QUEST_GC_CHECK");
    if (modes == NULL || modes[0] == '\0') return;
    const char *p = modes;
    while (*p != '\0') {
        const char *end = strchr(p, ',');
        size_t n = end != NULL ? (size_t)(end - p) : strlen(p);
        if (n == 7 && strncmp(p, "layouts", 7) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_LAYOUTS;
        else if (n == 6 && strncmp(p, "report", 6) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_REPORT;
        else if (n == 5 && strncmp(p, "roots", 5) == 0) quest_gc_check_flags |= QUEST_GC_CHECK_ROOTS;
        else if (n > 0) {
            fprintf(stderr, "quest: QUEST_GC_CHECK: unknown mode '%.*s'\n", (int)n, p);
            exit(70);
        }
        p = end != NULL ? end + 1 : p + n;
    }
    const char *interval = getenv("QUEST_GC_CHECK_INTERVAL");
    if (interval != NULL && interval[0] != '\0') {
        unsigned long long bytes = strtoull(interval, NULL, 10);
        if (bytes > 0) quest_gc_check_interval = (size_t)bytes;
    }
    if (quest_gc_check_flags != 0) atexit(quest_gc_check_at_exit);
}

void quest_gc_init(void) {
#ifndef QUEST_NOGC
    GC_INIT();
#endif
    quest_gc_read_options();
}
