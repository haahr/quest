/*
 * Quest C Runtime Interface: The Collector
 *
 * The collector's interface (docs/collector.md section 3): object layouts,
 * the runtime's own among them; write barriers; root and frame tables; the
 * checking modes of QUEST_GC_CHECK; holding collections off; and allocation,
 * whose fast path is inline here (quest_gc.c has the rest).
 *
 * Part of quest_runtime.h, which includes it after the representation of
 * values, descriptors, and exceptions; its bytes are in the ABI corpus's
 * digest of the runtime's interface with that header's.
 */

#ifndef QUEST_RUNTIME_H
#error "include quest_runtime.h, which includes quest_gc.h"
#endif

#ifndef QUEST_GC_H
#define QUEST_GC_H

/* Object layouts (docs/collector.md section 3.2). Every allocation is
 * preceded by a header word naming the layout of its words: for each word,
 * whether it is a pointer, a scalar, or ambiguous (a QVal of generic code,
 * whose kind the allocation site did not know), so that a precise collector
 * can scan it, and so that QUEST_GC_CHECK=layouts (runtime/quest_gc.c) can
 * check what the compilers and the runtime say against what the objects hold.
 * A layout has one of three forms. A fixed layout describes an object of a
 * known size, word by word. An array layout describes a header of known size
 * followed by elements, their count an int64_t at length_offset in the header,
 * each element element_words words of the kinds after the header's. A sized
 * layout describes an allocation of a size known only at the call: the
 * allocation records its byte count in the word before the header (shifted
 * left one bit, with the low bit set, which tells the two prefixes apart), and
 * the layout describes a pattern of element_words words that repeats over it.
 * A noscan layout's words are all scalars, so the collector does not scan it. */
#define Q_WORD_SCALAR    0
#define Q_WORD_POINTER   1
#define Q_WORD_AMBIGUOUS 2

#define Q_LAYOUT_FIXED 0
#define Q_LAYOUT_ARRAY 1
#define Q_LAYOUT_SIZED 2

#define Q_LAYOUT_NOSCAN 1u

typedef struct QLayout {
    const char    *name;
    uint32_t       form;
    uint32_t       flags;
    uint32_t       size;          /* fixed: the object's bytes; array: the bytes before its elements; sized: 0 */
    uint32_t       length_offset; /* array: the offset of the int64_t count of elements */
    uint32_t       element_words; /* array, sized: the words of each element */
    uint32_t       words;         /* the fixed words kinds describes: the object's (fixed) or the header's (array) */
    const uint8_t *kinds;         /* the kind of each fixed word, then of each word of an element */
} QLayout;

/* The header word before an object: the layout's address in its low 48 bits,
 * and above them the collector's byte (bits 56 to 63) and the mutator's (48
 * to 55), each written by its side alone (docs/collector.md section 3.2). The
 * collector's holds `old`, set when the object is marked, the generational
 * barrier's hint. */
#define Q_HEADER_LAYOUT_MASK ((uintptr_t)0x0000FFFFFFFFFFFFu)
#define Q_HEADER_OLD         ((uintptr_t)1 << 56)   /* the collector's byte: marked by some collection */
#define Q_HEADER_LOGGED      ((uintptr_t)1 << 48)   /* the mutator's byte: in the log since the last collection */

Q_INLINE const QLayout *quest_layout_of(const void *obj) {
    return (const QLayout *)(((const uintptr_t *)obj)[-1] & Q_HEADER_LAYOUT_MASK);
}

/* The byte count a sized allocation records before its header */
Q_INLINE size_t quest_sized_bytes(const void *obj) {
    return (size_t)(((const uintptr_t *)obj)[-2] >> 1);
}

/* Defines a layout and its kinds (a runtime file's own, with linkage
 * `static`, or one the header declares, with none): fixed, of bytes described
 * word by word; an array, of a header of header_bytes followed by elements of
 * element_words words each, counted by the int64_t at length_offset, the
 * header's kinds then the element's; sized, of a repeating element; and
 * noscan, of pointer-free bytes */
#define Q_LAYOUT_DEF(linkage, cname, text, form, flags, size, length_offset, element_words, ...) \
    static const uint8_t cname##_kinds[] = { __VA_ARGS__ }; \
    linkage const QLayout cname = { text, form, flags, size, length_offset, element_words, \
                                    (form) == Q_LAYOUT_SIZED ? 0 : sizeof cname##_kinds - (element_words), \
                                    cname##_kinds }
#define Q_LAYOUT_FIXED_DEF(linkage, cname, text, bytes, ...) \
    Q_LAYOUT_DEF(linkage, cname, text, Q_LAYOUT_FIXED, 0, bytes, 0, 0, __VA_ARGS__)
#define Q_LAYOUT_ARRAY_DEF(linkage, cname, text, header_bytes, length_offset, element_words, ...) \
    Q_LAYOUT_DEF(linkage, cname, text, Q_LAYOUT_ARRAY, 0, header_bytes, length_offset, element_words, __VA_ARGS__)
#define Q_LAYOUT_SIZED_DEF(linkage, cname, text, ...) \
    Q_LAYOUT_DEF(linkage, cname, text, Q_LAYOUT_SIZED, 0, 0, 0, sizeof cname##_kinds, __VA_ARGS__)
#define Q_LAYOUT_NOSCAN_DEF(linkage, cname, text, bytes) \
    linkage const QLayout cname = { text, Q_LAYOUT_FIXED, Q_LAYOUT_NOSCAN, bytes, 0, 0, 0, NULL }

/* The runtime's own layouts (quest_gc.c), the ones generated code and the
 * header's inline helpers allocate with */
extern const QLayout quest_layout_record_box;      /* a QRecordVal: its payload and dictionary */
extern const QLayout quest_layout_variant_box;     /* a QVariantVal: its tag and payload */
extern const QLayout quest_layout_closure;         /* a QClosure */
extern const QLayout quest_layout_adapter_env;     /* a QFunAdapterEnv */
extern const QLayout quest_layout_array_pointer;   /* a QArray whose elements are pointers */
extern const QLayout quest_layout_array_scalar;    /* a QArray whose elements are scalars */
extern const QLayout quest_layout_array_ambiguous; /* a QArray whose elements are QVals of unknown kind */
extern const QLayout quest_layout_bytes;           /* a sized allocation of pointer-free bytes */
extern const QLayout quest_layout_words;           /* a sized allocation of words of unknown kind */
extern const QLayout quest_layout_ints;            /* a sized allocation of pointer-free words, zeroed */
extern const QLayout quest_layout_pointers;        /* a sized allocation of pointers */
/* The runtime's own (quest_gc.c), named by what they lay out */
extern const QLayout quest_layout_string, quest_layout_exception, quest_layout_auto, quest_layout_component,
    quest_layout_proxy, quest_layout_proxy_cache, quest_layout_raised, quest_layout_trace, quest_layout_writer,
    quest_layout_reader, quest_layout_process, quest_layout_string_builder, quest_layout_code_region,
    quest_layout_run_result, quest_layout_file_stats, quest_layout_descriptor, quest_layout_array_descriptor,
    quest_layout_exception_descriptor, quest_layout_opaque_descriptor, quest_layout_stored_descriptor,
    quest_layout_record_descriptor, quest_layout_tuple_descriptor, quest_layout_variant_descriptor,
    quest_layout_fun_descriptor, quest_layout_auto_descriptor,
    quest_layout_record_dict_entries, quest_layout_inst_nodes, quest_layout_inst_cache_entry,
    quest_layout_view_map_entry, quest_layout_variant_adapter_entry, quest_layout_abstract_type_entry;

/* Write barriers (docs/collector.md section 3.5), called after a store of a
 * word that may be a pointer into an object that already exists, with no call
 * that may collect between the two: with the object, when the store site has
 * its address (a tuple, a box), or with the slot's address when it does not
 * (an array's element, a record's field through its payload, a var or out
 * location, which may be on the stack, a view's slot). Stores that initialize
 * an object being made need neither until a call that may collect has come
 * since its allocation; the compilers log such an object before each later
 * call and after its last store.
 * The object's barrier logs an object a collection has marked (its header's
 * old byte) and that is not in the log already, so that the next minor
 * collection scans it for the young objects it may now point at: the fast
 * path is the header's load, a mask, and a compare, and the slow path
 * (quest_barrier_log) logs. A tuple bound by a case binder is an option's
 * payload, which shares the option's allocation (docs/c-representation.md
 * section 5.3): the word before it is the option's tag, a small integer where
 * a header holds a layout's address, so a word under 65536 says the header,
 * and the object to log, are one word further back. The slot's barrier
 * marks the slot's card, 512 bytes of the heap, dirty, and the next minor
 * collection scans the dirty cards' words by their old objects' layouts, so
 * that a store into a large table costs the table one card's scan, not its
 * own (docs/collector.md section 3.5): the fast path is a range check and
 * two bytes' loads, the slot's line mark (a slot in an unmarked line is a
 * young object's, whose stores need no barrier: an old object's lines are
 * marked, a run's as a whole) and its card, and the slow path
 * (quest_barrier_card) marks and lists the card; a slot outside the heap is
 * a stack or static slot. */
#define Q_BARRIER_TAG_LIMIT ((uintptr_t)1 << 16)
#define Q_GC_LINE_BITS 7
#define Q_GC_CARD_BITS 9
extern uintptr_t quest_gc_heap_lo, quest_gc_heap_hi;
extern uint8_t  *quest_gc_lines;    /* a mark byte per line of the reserve, by (address - heap_lo) >> Q_GC_LINE_BITS */
extern uint8_t  *quest_gc_cards;    /* a byte per card of the reserve, by (address - heap_lo) >> Q_GC_CARD_BITS */
void     quest_barrier_log(void *obj);
void     quest_barrier_card(uint8_t *card);
Q_INLINE void quest_barrier(const void *obj) {
    const uintptr_t *p = (const uintptr_t *)obj;
    uintptr_t h = p[-1];
    if (h < Q_BARRIER_TAG_LIMIT) h = p[-2];
    if ((h & (Q_HEADER_OLD | Q_HEADER_LOGGED)) == Q_HEADER_OLD) quest_barrier_log((void *)obj);
}
Q_INLINE void quest_barrier_slot(const void *slot) {
    uintptr_t off = (uintptr_t)slot - quest_gc_heap_lo;
    if (off < quest_gc_heap_hi - quest_gc_heap_lo && quest_gc_lines[off >> Q_GC_LINE_BITS] != 0) {
        uint8_t *card = quest_gc_cards + (off >> Q_GC_CARD_BITS);
        if (*card == 0) quest_barrier_card(card);
    }
}

/* Root tables (section 3.8): the global slots of a unit that hold heap
 * pointers, each by its address and its words, ending with a null slot,
 * registered when the unit is initialized; and the runtime's own, which each
 * runtime file lists through a callback for the roots check */
typedef struct QRootEntry {
    void   *slot;
    size_t  words;
} QRootEntry;
void     quest_register_roots(const QRootEntry *roots);
/* Frame tables (section 3.3; quest_gc.c has the form): what each frame of a
 * unit's arm64 code holds across each of its calls, by which a collection
 * scans those frames' live words alone. A unit registers its table, qr_frames,
 * when it is initialized; a unit compiled through C registers an empty one */
void     quest_register_frames(const void *table);
typedef void (*QRootVisitor)(void *slot, size_t words);
void     quest_runtime_roots(QRootVisitor add);
void     quest_code_roots(QRootVisitor add);
void     quest_serialization_roots(QRootVisitor add);

/* The checking modes of QUEST_GC_CHECK (docs/collector.md section 7), as bits
 * of quest_gc_check_flags, and the allocation hook of those that count
 * allocations */
#define QUEST_GC_CHECK_LAYOUTS 1
#define QUEST_GC_CHECK_REPORT  2
#define QUEST_GC_CHECK_ROOTS   4
#define QUEST_GC_CHECK_POISON  8
#define QUEST_GC_CHECK_COLLECT 16       /* collect every QUEST_GC_CHECK_INTERVAL bytes, checking nothing */
#define QUEST_GC_CHECK_ALLOCATIONS 32   /* count allocations by their sites, for benchmarks/mlton/allocations.py */
#define QUEST_GC_CHECK_BARRIERS 64      /* at every minor collection, find the old objects' pointers at young ones */
extern int    quest_gc_check_flags;     /* nonzero sends every allocation through the slow path, which counts it */
extern size_t quest_gc_check_pending;   /* bytes allocated since the last forced collection */
/* Reads QUEST_GC_CHECK and the other options, and reserves the heap */
void          quest_gc_init(void);
/* Collects now */
void          quest_gc_collect(void);
/* Holds collections off until the matching release, for an operation of the
 * runtime's that builds a structure of many objects with stores between its
 * allocations (a descriptor's instance, a serialized value's graph): while
 * nothing collects, every object the operation allocates stays young, so the
 * stores among them need no barriers, and a pointer it keeps outside the
 * heap and the stack for a while is not lost. Only a store into an object
 * older than the hold still needs its barrier. The operation must be bounded
 * by its result's size, and must not run the program's code, whose handlers
 * would outlive a raise's release of every hold (quest_reraise) */
void          quest_gc_hold(void);
void          quest_gc_release(void);
void          quest_gc_release_all(void);
/* Registers [low, high) as a region of ambiguous roots (the JIT's data) */
void          quest_gc_add_roots(void *low, void *high);

/* Memory allocation (docs/collector.md section 3.4): an object of sz bytes
 * laid out as layout says, zeroed, after its header (quest_alloc); the same
 * with its byte count recorded, for a sized layout (quest_alloc_sized); and
 * sz pointer-free bytes, which the collector never scans (quest_alloc_bytes).
 * The fast path bumps the cursor of the object's space (pointer-bearing, or
 * pointer-free by its layout) through the current hole and stores the
 * header word, the layout's address; the slow path, which also takes every
 * allocation while a checking mode is on or a full collection is marking
 * (it hides the limits for that), finds the next hole, or collects, and
 * stores the header word itself, with the flags of an object born while a
 * collection marks (section 3.10), which the caller must leave as they are.
 * Either way the object's start bit, by which the collector validates an
 * ambiguous word, is set after. The SSA's backends select the same sequence
 * inline (docs/ssa.md section 4.1). */
extern uintptr_t quest_gc_cursor[2];
extern uintptr_t quest_gc_limit[2];
extern uint8_t  *quest_gc_start_bits;
void *quest_gc_alloc_slow(size_t total, const QLayout *layout);

Q_INLINE unsigned quest_layout_space(const QLayout *layout) {
    return (layout->flags & Q_LAYOUT_NOSCAN) != 0 ? 1u : 0u;
}

/* `total` bytes for an object of the layout, its header word, the one
 * numbered `header`, stored */
Q_INLINE uintptr_t *quest_gc_bump(size_t total, const QLayout *layout, size_t header) {
    unsigned space = quest_layout_space(layout);
    uintptr_t p = quest_gc_cursor[space];
    if (quest_gc_check_flags != 0 || total > quest_gc_limit[space] - p) {
        return (uintptr_t *)quest_gc_alloc_slow(total, layout);
    }
    quest_gc_cursor[space] = p + total;
    ((uintptr_t *)p)[header] = (uintptr_t)layout;
    return (uintptr_t *)p;
}

Q_INLINE void quest_gc_note_start(const void *obj) {
    uintptr_t i = ((uintptr_t)obj - quest_gc_heap_lo) >> 3;
    quest_gc_start_bits[i >> 3] |= (uint8_t)(1u << (i & 7));
}

Q_INLINE void *quest_alloc(size_t sz, const QLayout *layout) {
    uintptr_t *base = quest_gc_bump(sizeof(uintptr_t) + ((sz + 7) & ~(size_t)7), layout, 0);
    quest_gc_note_start(base + 1);
    return base + 1;
}

Q_INLINE void *quest_alloc_sized(size_t sz, const QLayout *layout) {
    uintptr_t *base = quest_gc_bump(2 * sizeof(uintptr_t) + ((sz + 7) & ~(size_t)7), layout, 1);
    base[0] = ((uintptr_t)sz << 1) | 1u;
    quest_gc_note_start(base + 2);
    return base + 2;
}

Q_INLINE void *quest_alloc_bytes(size_t sz) {
    return quest_alloc_sized(sz, &quest_layout_bytes);
}

/* A sized allocation of n words of unknown kind, for the runtime's own
 * structures that hold values of any type */
Q_INLINE void *quest_alloc_words(size_t n) {
    return quest_alloc_sized(n * sizeof(uintptr_t), &quest_layout_words);
}

#endif
