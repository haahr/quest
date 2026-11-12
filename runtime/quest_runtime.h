/*
 * Quest C Runtime Interface
 *
 * The C representation of Quest values and types and the runtime's interface:
 * what generated code and the runtime's own files (quest_runtime.c, quest_gc.c,
 * quest_serialization.c, ...) agree on. The C that both compilers generate
 * includes this header; the self-hosted compiler's arm64 backend and JIT, which
 * emit machine code, mirror its structs and constants in codegen/runtimeLayout,
 * which a test checks against this header (docs/arm64.md §3.3).
 *
 * The header is part of the artifact contract, the ABI: compiled units and
 * interface artifacts are reused only by a compiler with the same ABI_VERSION
 * (bootstrap/python/quest/config/abi.py, questlang/config/abi.mod.quest), and
 * the ABI corpus records a digest of this file's bytes, so that a change here
 * fails tests/python/test_abi_corpus.py until the version is bumped (or, after
 * a change that is not incompatible, the digest regenerated;
 * docs/build-process.md §5.2.3).
 *
 * In order: portability macros; the representation of values (QVal, strings,
 * closures, arrays, records, variants, options, exceptions); type descriptors,
 * the run-time descriptions of types, with their per-kind metadata, templates,
 * and auto values; exception state, handlers, and tracebacks; the built-in
 * exceptions and base descriptors; the collector's interface (object layouts,
 * write barriers, root and frame tables, allocation); the runtime's functions,
 * from raises and the standard library's primitives to descriptor operations,
 * proxies, conversions, and view maps; inline helpers for checked operations,
 * arithmetic, identity, words, and hashing; built-in operator closures; and the
 * JIT's primitives.
 *
 * docs/c-representation.md describes the representation and the calling
 * convention, docs/collector.md the collector (§3, the design), and
 * docs/exceptions.md the tracebacks.
 */

#ifndef QUEST_RUNTIME_H
#define QUEST_RUNTIME_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <setjmp.h>

#if defined(_MSC_VER)
#  define Q_THREAD_LOCAL __declspec(thread)
#elif defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L && !defined(__STDC_NO_THREADS__)
#  define Q_THREAD_LOCAL _Thread_local
#elif defined(__GNUC__) || defined(__clang__)
#  define Q_THREAD_LOCAL __thread
#else
#  define Q_THREAD_LOCAL
#endif

#if defined(__GNUC__) || defined(__clang__)
#  define Q_UNUSED __attribute__((unused))
#  define Q_NORETURN __attribute__((noreturn))
#else
#  define Q_UNUSED
#  define Q_NORETURN
#endif

/* The runtime's inline helpers are static inline in every translation unit that includes this header, except
   quest_inline.c, which defines Q_INLINE as nothing first, so that the runtime also has an external definition of
   each, under its own name, for code that cannot inline them to call (native code; docs/arm64.md §7.5) */
#ifndef Q_INLINE
#  define Q_INLINE static inline
#endif

/* Compile-time portable layout assertions */
#define Q_ASSERT_CONCAT_(a, b) a##b
#define Q_ASSERT_CONCAT(a, b)  Q_ASSERT_CONCAT_(a, b)

#ifndef static_assert
#  if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
#    define static_assert(cond, msg) _Static_assert(cond, #msg)
#  else
#    define static_assert(cond, msg)        typedef char Q_ASSERT_CONCAT(q_assert_##msg##_, __LINE__)[(cond) ? 1 : -1]
#  endif
#endif

/* 64-bit Universal Value Word (QVal) */
typedef int64_t  QInt;
typedef double   QReal;
typedef bool     QBool;
typedef uint8_t  QChar;   /* A byte, unsigned on every platform (docs/arm64.md §3.9) */
typedef uint64_t QWord;

/* A Bool or Char in an aggregate slot (a tuple component, option payload, record field, or auto payload): a word of
 * its own, as in a QVal (.i), so that every slot is one word and generic code's slots (QVal) agree with native ones */
typedef int64_t  QBoolSlot;
typedef int64_t  QCharSlot;

typedef union QVal {
    void    *p;   /* Heap pointers: strings, arrays, records, tuples, closures */
    QInt     i;   /* 64-bit signed two's complement integer */
    QReal    r;   /* 64-bit IEEE-754 double precision float */
    uint64_t u;   /* 64-bit raw unsigned word for identity checks */
} QVal;

/* String representation: length-prefixed, null-terminated */
typedef struct QString {
    int64_t length;
    int64_t capacity;
    char   *data;
} QString;

/* First-class closure representation: function pointer and environment */
typedef struct QClosure {
    void *fn;   /* C function pointer */
    void *env;  /* Captured environment pointer or NULL */
} QClosure;

/* Array representation: length-prefixed buffer of 64-bit QVal words */
typedef struct QArray {
    int64_t length;
    QVal    data[];
} QArray;

/* Record header: the descriptor of the record payload's own layout, the record type it was created with */
typedef struct QRecordHeader {
    const struct QTypeDescriptor *descriptor;
} QRecordHeader;

/* First-class 16-byte record value: payload pointer and evidence dictionary */
typedef struct QRecordVal {
    void       *val;
    const void *dict;
} QRecordVal;

/* First-class 16-byte variant value: local tag index and payload value */
typedef struct QVariantVal {
    int64_t tag;
    QVal    payload;
} QVariantVal;

/* Standard I/O sink and source representations */
typedef struct QWriter {
    FILE *file;
    bool  is_file;
    bool  is_closed;
} QWriter;

typedef struct QReader {
    FILE *file;
    int   peek_char; /* EOF (-1) if no unread character */
    bool  is_file;
    bool  is_closed;
} QReader;

/* Generic Option header for inspections */
typedef struct QOptionHeader {
    int64_t tag;
    QVal    fields[];
} QOptionHeader;

/* First-class generative exception descriptor */
typedef struct QException {
    const char *name;
} QException;

/* Runtime Type Descriptors (Intensional Type Analysis) */
typedef enum QTypeKind {
    QTYPE_KIND_INT,
    QTYPE_KIND_REAL,
    QTYPE_KIND_BOOL,
    QTYPE_KIND_CHAR,
    QTYPE_KIND_STRING,
    QTYPE_KIND_OK,
    QTYPE_KIND_TUPLE,
    QTYPE_KIND_RECORD,
    QTYPE_KIND_VARIANT,
    QTYPE_KIND_OPTION,
    QTYPE_KIND_ARRAY,
    QTYPE_KIND_FUN,
    QTYPE_KIND_AUTO,
    QTYPE_KIND_EXCEPTION,
    QTYPE_KIND_OPAQUE,
    QTYPE_KIND_BOUND_VAR,  /* A type parameter of an enclosing polymorphic function type (see quest_type_bound_vars) */
    QTYPE_KIND_HOLE,       /* A type parameter of generic code in a descriptor template (QHoleDescriptor) */
    QTYPE_KIND_STORED      /* A type stored as generic code stores a type parameter (QStoredDescriptor) */
} QTypeKind;

typedef struct QTypeDescriptor QTypeDescriptor;

/* A type descriptor: a Quest type described at run time, for the operations that need a value's type, not only its
 * bits: subtyping (dynamic.be, inspect), conversion between layouts (quest_convert), printing (echo, uncaught
 * exceptions), and serialization (dynamic.extern and dynamic.intern). Compiled code emits static descriptors for the
 * types it uses and passes them as the type arguments of polymorphic functions; descriptors of recursive types are
 * cyclic (docs/c-representation.md §6.4.4).
 *
 * name: the type as text. For most kinds it is only for display: compiled code writes the type as printed, cut off at
 *   80 characters, so the name need not identify the type, and descriptors are compared structurally. An opaque
 *   descriptor (an abstract type, or an application of an abstract type operator) is identified by its name (a
 *   module's abstract type by its global name, "geo/coord.P"). quest_intern_type_descriptor and the
 *   quest_make_*_descriptor constructors key their table by name.
 * size, alignment: the size of the C type that holds a value (sizeof(QVal), sizeof(QVariantVal), ...), except that for
 *   a tuple, record, or option it is the size of the struct a value points to (a record's payload). Only
 *   deserialization reads size, to allocate an option; nothing reads alignment, which compiled code always sets to a
 *   word's.
 * is_subtype: always quest_is_subtype, which the runtime calls directly rather than through this field.
 * extra: the kind's metadata, or NULL: QTupleTypeDescriptor (NULL for Tuple end), QRecordTypeDescriptor,
 *   QVariantTypeDescriptor (variants and options), QArrayTypeDescriptor, QFunTypeDescriptor, QAutoTypeDescriptor,
 *   QExceptionTypeDescriptor, QOpaqueTypeDescriptor (or NULL), QHoleDescriptor, and QStoredDescriptor; NULL for the
 *   base types and a bound type variable, which is identified by its address in quest_type_bound_vars. */
struct QTypeDescriptor {
    QTypeKind   kind;
    const char *name;
    size_t      size;
    size_t      alignment;
    bool      (*is_subtype)(const QTypeDescriptor *sub, const QTypeDescriptor *super_type);
    const void *extra;
};

/* Compound descriptor metadata */
typedef struct QArrayTypeDescriptor {
    const QTypeDescriptor *element_type;
} QArrayTypeDescriptor;

typedef struct QRecordFieldDescriptor {
    const char            *name;
    const QTypeDescriptor *type;
    size_t                 offset;
    bool                   is_var;
} QRecordFieldDescriptor;

typedef struct QRecordTypeDescriptor {
    size_t                       field_count;
    const QRecordFieldDescriptor fields[];
} QRecordTypeDescriptor;

typedef struct QTupleElementDescriptor {
    const char            *name;       /* Field label or NULL if anonymous */
    const QTypeDescriptor *type;
    size_t                 offset;     /* Offset in tuple struct */
    bool                   is_var;
} QTupleElementDescriptor;

/* A type component of a tuple type (Let A = Int, or an existential's A::TYPE), which has no slot: only echo writes
 * it, as text, before the value element at position (or after the last, when position is element_count) */
typedef struct QTupleTypeComponentDescriptor {
    size_t      position;
    const char *text;     /* As the interpreter writes it: "Let A = Int", "<Hidden>::TYPE" */
} QTupleTypeComponentDescriptor;

typedef struct QTupleTypeDescriptor {
    size_t                               component_count; /* Type components, in order; none in descriptors */
    const QTupleTypeComponentDescriptor *components;      /* the runtime makes */
    size_t                               element_count;
    const QTupleElementDescriptor        elements[];
} QTupleTypeDescriptor;

typedef struct QVariantCaseDescriptor {
    const char            *name;       /* Case tag identifier */
    const QTypeDescriptor *payload_type; /* NULL for parameterless / Ok payload */
    int64_t                tag_index;  /* Concrete integer discriminant */
    bool                   is_var;
} QVariantCaseDescriptor;

typedef struct QVariantTypeDescriptor {
    size_t                       case_count;
    const QVariantCaseDescriptor cases[];
} QVariantTypeDescriptor;

typedef struct QFunParamDescriptor {
    const QTypeDescriptor *type;
    bool                   is_var;
    bool                   is_out;
} QFunParamDescriptor;

/* Makes a closure of function type `to` from closure orig of function type `from`, a subtype of `to`: the result
 * converts its arguments from `to`'s parameter types to `from`'s and its result from `from`'s result type to `to`'s
 * (see quest_convert). Compiled code supplies one for each function type it describes. */
typedef QClosure *(*QFunAdapter)(const QClosure *orig, const QTypeDescriptor *from, const QTypeDescriptor *to);

/* Calls closure c, of the C signature of the function type it belongs to, with uniform arguments: the descriptors
 * of its type parameters (in .p), then its value arguments in their QVal form (var and out parameters as pointers
 * in .p); returns the result in its QVal form. Compiled code supplies one for each function type it describes. */
typedef QVal (*QFunInvoker)(const QClosure *c, const QVal *args);

/* The environment of a closure made by a QFunAdapter. `direct` is true when orig has the adapted closure's own C
 * signature, so that it is called directly rather than through `from`'s invoker. */
typedef struct QFunAdapterEnv {
    const QClosure        *orig;
    const QTypeDescriptor *from;
    const QTypeDescriptor *to;
    bool                   direct;
} QFunAdapterEnv;

/* A function type, possibly polymorphic: All(A1..An) Fun(params) result. In the parameter and result types (and in
 * later bounds), a type parameter is described by quest_type_bound_vars[i], where i counts binders outward from
 * the reference, as de Bruijn indices do (the last of A1..An is 0 in the body), so equal types have equal
 * descriptors whatever their parameters are named. */
typedef struct QFunTypeDescriptor {
    size_t                    param_count;
    const QTypeDescriptor    *result_type;
    QFunAdapter               adapt;              /* NULL if values of this type cannot be adapted */
    QFunInvoker               invoke;             /* NULL if closures of this type cannot be called uniformly */
    size_t                    quantifier_count;   /* n type parameters, passed as descriptors before the values */
    const QTypeDescriptor *const *quantifier_bounds; /* per type parameter: its bound B for Ai <: B, else NULL */
    const QFunParamDescriptor params[];
} QFunTypeDescriptor;

/* Descriptor templates (Cardelli §4.6 for types used at run time inside generic code). Inside a polymorphic function,
 * a type that mentions the function's type parameters, such as Tuple fst:A snd:Int end, is laid out generically:
 * independently of A's type argument, with each A stored as generic code stores a value of a type parameter (a QVal, or
 * for a bounded one, the type argument's own value in the representation of its bound). Compiled code describes such a
 * type by a template, a descriptor in which each type parameter is a hole, and quest_instantiate_descriptor fills the
 * holes with the run-time type arguments. The result describes the type the value has and the layout the value is in:
 * each hole becomes a QTYPE_KIND_STORED descriptor of its type argument, which subtyping looks through and conversion
 * (quest_convert) unwraps, so that a value laid out generically is converted when it is used at a particular type. */
typedef struct QHoleDescriptor {
    size_t                 index;    /* which type argument */
    const QTypeDescriptor *storage;  /* the type parameter's bound B (for A <: B), in whose representation it is
                                        stored, or NULL */
} QHoleDescriptor;

/* A value of type `type` stored in the representation of a type parameter: as its QVal form when `storage` is NULL,
 * and otherwise in the representation of `storage`, the type parameter's bound. A type parameter's value keeps its
 * own view (generic code holds a value of a bounded type parameter as its type argument holds it, and reads it
 * through the bound by a view map, QViewMap), so it agrees with a value of `type`; a module's abstract type's value
 * is `viewed` at `storage`, as code outside the module holds it. */
typedef struct QStoredDescriptor {
    const QTypeDescriptor *type;
    const QTypeDescriptor *storage;
    bool                   viewed;
} QStoredDescriptor;

/* An application of an abstract type operator (list.T(Int)): opaque, named by the operator; descriptors with
 * arguments are equal when their names are and their arguments are equal types. A module's abstract type is named
 * by its global name (docs/dynamic.md §2.3), and its representation is the one its module registers
 * (quest_register_abstract_type), or for a type read from a module the program does not link, `rep`. */
typedef struct QOpaqueTypeDescriptor {
    size_t                       arg_count;
    const QTypeDescriptor *const *args;
    const QTypeDescriptor        *rep;
} QOpaqueTypeDescriptor;

/* Exception types: Exception(T) */
typedef struct QExceptionTypeDescriptor {
    const QTypeDescriptor *payload_type;
} QExceptionTypeDescriptor;

/* Auto types (Cardelli §4.6): Auto A HasKind with S end. A component's type refers to the type parameter A as
 * quest_type_bound_vars[0]. Components are stored in the layout of Tuple S end with A abstract, each in a slot (its
 * QVal form, a record or variant boxed). Dynamic values are auto values of type Auto A::TYPE with a:A end. */
typedef struct QAutoComponentDescriptor {
    const char            *name;
    const QTypeDescriptor *type;
    size_t                 offset;
    bool                   is_var;
} QAutoComponentDescriptor;

typedef struct QAutoTypeDescriptor {
    const QTypeDescriptor        *bound;          /* B for A <: B, else NULL */
    size_t                        payload_size;
    size_t                        component_count;
    const QAutoComponentDescriptor components[];
} QAutoTypeDescriptor;

/* An auto value: the descriptor of its type component and a pointer to its components */
typedef struct QAuto {
    const QTypeDescriptor *type_desc;
    QVal                   payload;
} QAuto;

/* Frames captured at a raise that a handler might catch and raise again: the starts of the functions running, most
   recent first, a run of calls of the same function kept once with its count (docs/exceptions.md §5.4) */
#define Q_MAX_TRACE_RUNS 64
typedef struct QTrace {
    int         n_runs;
    bool        truncated;
    const void *starts[Q_MAX_TRACE_RUNS];
    int64_t     counts[Q_MAX_TRACE_RUNS];
} QTrace;

/* Thread-local active exception state: the exception raised, its payload, the site it was raised at
   ("file:line:col", or NULL inside an external; docs/exceptions.md §3.3), and the frames captured there, if any,
   which a re-raise keeps; and for a payload of a type other than Ok, its type's descriptor and its type as the raise
   wrote it, by which an uncaught exception's payload is shown as the interpreters show it (docs/exceptions.md §2.1) */
typedef struct QExceptionState {
    const QException      *exc;
    QVal                   payload;
    const char            *loc;
    const QTrace          *trace;
    const QTypeDescriptor *payload_type;
    const char            *payload_text;
} QExceptionState;

/* What a handler catches (docs/exceptions.md §5.1): the n_catches exceptions in catches, or every exception
   (Q_CATCH_ALL, a try with an else branch), or any (Q_CATCH_UNKNOWN, a try whose patterns are computed after the
   exception is caught), or every exception with its frames captured (Q_CATCH_ALL_TRACED, a try whose else branch
   names the exception, which raised.reraise may raise again; docs/raised.md §5) */
#define Q_CATCH_ALL        (-1)
#define Q_CATCH_UNKNOWN    (-2)
#define Q_CATCH_ALL_TRACED (-3)

/* raised.T: an exception caught by an else branch that names it, a heap copy of the handler's state
   (docs/raised.md §6) */
typedef struct QRaised {
    QExceptionState state;
} QRaised;

/* A try sets its handler with Q_SETJMP and a raise jumps to it with Q_LONGJMP. On macOS and the BSDs setjmp and
   longjmp save and restore the signal mask, a system call each, which made exceptions slow; _setjmp and _longjmp skip
   it, and nothing raises from a signal handler or changes the mask in a try. glibc's setjmp saves no mask already. */
#if defined(__APPLE__) || defined(__FreeBSD__) || defined(__NetBSD__) || defined(__OpenBSD__) || defined(__DragonFly__)
#  define Q_SETJMP(env)       _setjmp(env)
#  define Q_LONGJMP(env, val) _longjmp(env, val)
#else
#  define Q_SETJMP(env)       setjmp(env)
#  define Q_LONGJMP(env, val) longjmp(env, val)
#endif

/* Linked node in thread-local exception handler stack: a try's handler, of one of two kinds (docs/arm64.md §3.6). A C
   handler's resume is NULL, and a raise resumes it with Q_LONGJMP to env_jmp. A native handler's is where its code
   resumes, with sp and fp (x29) as they were when it was entered: its function saved every callee-saved register on
   entry, so no other register need be restored. */
typedef struct QExceptionHandler {
    struct QExceptionHandler  *prev;
    const QException *const   *catches;
    int64_t                    n_catches;
    const void                *resume;
    void                      *sp;
    void                      *fp;
    jmp_buf                    env_jmp;
} QExceptionHandler;

/* A generated unit's table of its functions with frames in tracebacks: each one's start and frame name, registered
   when the unit is initialized (docs/exceptions.md §5.2) */
typedef struct QFuncEntry {
    const void *addr;
    const char *name;
} QFuncEntry;

void quest_register_funcs(const QFuncEntry *entries, size_t count);

/* raised (docs/raised.md): the value of an else branch's binder, made from the handler's state, and raising it
   again */
QRaised *quest_raised_capture(const QExceptionState *state);
Q_NORETURN QVal quest_raised_reraise(const QTypeDescriptor *a, QRaised *r);

extern Q_THREAD_LOCAL QExceptionHandler *quest_current_exception_handler;
extern Q_THREAD_LOCAL QExceptionState    quest_current_exception;

/* Built-in singleton exception descriptors */
extern const QException quest_exc_arrayOp_error;
extern const QException quest_exc_string_error;
extern const QException quest_exc_variant_error;
extern const QException quest_exc_dynamic_error;
extern const QException quest_exc_value_error;

/* Pre-allocated static type descriptors for base types */
extern const QTypeDescriptor quest_type_Int;
extern const QTypeDescriptor quest_type_Real;
extern const QTypeDescriptor quest_type_Bool;
extern const QTypeDescriptor quest_type_Char;
extern const QTypeDescriptor quest_type_String;
extern const QTypeDescriptor quest_type_Ok;
extern const QTypeDescriptor quest_type_EmptyTuple;
/* word.T, the external type uint64_t: opaque, and stored as a QVal (.u) */
extern const QTypeDescriptor quest_type_Word;

/* Descriptors of bound type parameters by de Bruijn index (see QFunTypeDescriptor) */
#define Q_MAX_BOUND_VARS 32
extern const QTypeDescriptor quest_type_bound_vars[Q_MAX_BOUND_VARS];

/* Static ABI layout assertions */
static_assert(sizeof(QInt)          == 8, qint_must_be_8_bytes);
static_assert(sizeof(QReal)         == 8, qreal_must_be_8_bytes);
static_assert(sizeof(void *)        == 8, ptr_must_be_8_bytes);
static_assert(sizeof(QVal)          == 8, qval_must_be_8_bytes);
static_assert(sizeof(uint64_t)      == 8, u64_must_be_8_bytes);
static_assert(sizeof(QString)       == 24, qstring_must_be_24_bytes);
static_assert(sizeof(QClosure)      == 16, qclosure_must_be_16_bytes);
static_assert(sizeof(QRecordHeader) == 8, qrecord_header_must_be_8_bytes);
static_assert(sizeof(QRecordVal)    == 16, qrecordval_must_be_16_bytes);
static_assert(offsetof(QRecordVal, dict) == 8, qrecordval_dict_at_offset_8);
static_assert(sizeof(QVariantVal)          == 16, qvariantval_must_be_16_bytes);
static_assert(offsetof(QVariantVal, tag)     == 0,  qvariantval_tag_at_offset_0);
static_assert(offsetof(QVariantVal, payload) == 8,  qvariantval_payload_at_offset_8);
static_assert(sizeof(QException)    == 8, qexception_must_be_8_bytes);
static_assert(sizeof(QExceptionState) == 48, qexception_state_must_be_48_bytes);
static_assert(offsetof(QClosure, env) == 8, qclosure_env_at_offset_8);
static_assert(offsetof(QArray, data)  == 8, qarray_data_at_offset_8);
static_assert(offsetof(QOptionHeader, fields) == 8, qoptionheader_fields_at_offset_8);
static_assert(offsetof(QExceptionState, payload) == 8, qexception_state_payload_at_offset_8);

/* Value constants */
#define Q_OK_VAL    ((QVal){ .u = 0 })
#define Q_TRUE_VAL  ((QVal){ .i = 1 })
#define Q_FALSE_VAL ((QVal){ .i = 0 })

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
    quest_layout_fun_descriptor, quest_layout_auto_descriptor, quest_layout_descriptor_entry,
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

/* Runtime helper prototypes */
QString *quest_string_new(const char *src, int64_t len);
QString *quest_string_alloc(int64_t size, QChar init);
bool     quest_string_is_empty(const QString *s);
int64_t  quest_string_length(const QString *s);
QString *quest_string_concat(const QString *s1, const QString *s2);
bool     quest_string_equal(const QString *s1, const QString *s2);
QChar    quest_string_get_char(const QString *s, int64_t idx);
void     quest_string_set_char(QString *s, int64_t idx, QChar ch);
QString *quest_string_get_sub(const QString *s, int64_t start, int64_t len);
void     quest_string_set_sub(QString *dest, int64_t dest_start, const QString *src, int64_t src_start, int64_t len);
QString *quest_string_cat_sub(const QString *s1, int64_t st1, int64_t sz1,
                              const QString *s2, int64_t st2, int64_t sz2);
QString *quest_string_conc(const QArray *strings);
bool     quest_string_equal_sub(const QString *s1, int64_t st1, int64_t sz1,
                                const QString *s2, int64_t st2, int64_t sz2);
bool     quest_string_precedes(const QString *s1, const QString *s2);
bool     quest_string_precedes_sub(const QString *s1, int64_t st1, int64_t sz1,
                                   const QString *s2, int64_t st2, int64_t sz2);

QArray  *quest_array_new(int64_t len, QVal init_val, const QLayout *layout);
int64_t  quest_array_size(const QArray *a);
double   quest_real_pow(double base, double exp);
const QException *quest_alloc_exception(const char *name);
/* Raises: generated code passes the raise site (docs/exceptions.md §3.3); the runtime's primitives raise with none */
Q_NORETURN void quest_raise(const QException *exc, QVal payload);
Q_NORETURN void quest_raise_at(const QException *exc, QVal payload, const char *loc);
/* A raise with a payload of a type other than Ok: the payload's type's descriptor, and the type as written */
Q_NORETURN void quest_raise_typed_at(const QException *exc, QVal payload, const QTypeDescriptor *type, const char *text,
                                     const char *loc);
Q_NORETURN void quest_reraise(QExceptionState state);
/* Writes the exception as an uncaught one is reported: its name, and with a payload of a type other than Ok, " with ",
   the payload, ":", and its type, as the interpreters write them */
void quest_write_exception(FILE *out, const QExceptionState *state);
Q_NORETURN void quest_raise_array_error(void);
Q_NORETURN void quest_raise_array_error_at(const char *loc);
Q_NORETURN void quest_raise_string_error(void);
Q_NORETURN void quest_raise_variant_error(void);
Q_NORETURN void quest_raise_variant_error_at(const char *loc);
Q_NORETURN void quest_raise_dynamic_error(void);
Q_NORETURN void quest_raise_dynamic_error_at(const char *loc);
Q_NORETURN void quest_option_ordinal_error(int64_t n, int64_t count);
Q_NORETURN void quest_option_ordinal_error_at(int64_t n, int64_t count, const char *loc);
double   quest_real_pow_at(double base, double exp, const char *loc);
void     quest_print_val(QVal val, const char *type_name);
void     quest_print_value(const char *prefix, QVal val, const char *kind, const char *suffix);
void     quest_print_typed(const char *prefix, QVal val, const QTypeDescriptor *type, const char *suffix);
void     quest_echo_text(const char *text);
void     quest_echo_capture(void);
QString *quest_echo_captured(void);

/* Standard library singleton exceptions */
extern const QException quest_exc_writer_error;
extern const QException quest_exc_reader_error;
extern const QException quest_exc_ascii_error;
extern const QException quest_exc_int_error;
extern const QException quest_exc_real_error;
extern const QException quest_exc_word_error;
extern const QException quest_exc_system_error;

Q_NORETURN void quest_raise_writer_error(void);
Q_NORETURN void quest_raise_reader_error(void);
Q_NORETURN void quest_raise_ascii_error(void);
Q_NORETURN void quest_raise_int_error(void);
Q_NORETURN void quest_raise_int_error_at(const char *loc);
Q_NORETURN void quest_raise_real_error(void);
Q_NORETURN void quest_raise_real_error_at(const char *loc);
Q_NORETURN void quest_raise_word_error(void);
Q_NORETURN void quest_raise_system_error(void);

/* System module primitives */
extern QArray *quest_system_args;
void     quest_system_init(int argc, char **argv);
void     quest_system_exit(int64_t code);
QString *quest_system_getenv(const QString *var);
bool     quest_system_file_exists(const QString *path);
bool     quest_system_is_file(const QString *path);
bool     quest_system_is_directory(const QString *path);
void     quest_system_make_directory(const QString *path);
void     quest_system_remove_file(const QString *path);
void     quest_system_remove_directory(const QString *path);
void     quest_system_rename_file(const QString *old_path, const QString *new_path);
QString *quest_system_current_directory(void);
void     quest_system_change_directory(const QString *path);
QArray  *quest_system_list_directory(const QString *path);
/* Runs a program (args[0], found on PATH) with arguments, without a shell,
 * waiting for it: its exit code and output, as a Tuple code: Int stdout:
 * String stderr: String end */
void    *quest_system_run(const QArray *args);
bool     quest_system_is_terminal(int64_t fd);

/* os/fileStats module primitive: stat(2), or lstat(2) when follow is false, as
 * a Tuple kind: Int size: Int mode: Int accessTime: Real modifiedTime: Real
 * changeTime: Real accessNs: Int modifiedNs: Int changeNs: Int end. The kind is
 * 0 for a file, 1 a directory, 2 a symlink, 3 anything else, and -1 when the
 * path names nothing (ENOENT or ENOTDIR); other failures raise system.error */
void    *quest_filestats_stat(const QString *path, bool follow);

/* os/process module primitives: children started without waiting for them, with
 * their standard output and error collected in temp files; quest_process_wait
 * gives a Tuple code: Int stdout: String stderr: String end, as
 * quest_system_run does */
typedef struct QProcess QProcess;
QProcess *quest_process_spawn(const QArray *args);
QProcess *quest_process_spawn_in(const QArray *args, const QString *dir);
int64_t   quest_process_pid(const QProcess *p);
bool      quest_process_is_done(QProcess *p);
void     *quest_process_wait(QProcess *p);
int64_t   quest_process_wait_any(const QArray *ps);
void      quest_process_kill(QProcess *p, int64_t sig);

/* io/readline module primitives (quest_readline.c) */
extern const QException quest_exc_readline_error;
extern const QException quest_exc_readline_end_of_input;
extern const QException quest_exc_readline_interrupted;
bool     quest_readline_editing(void);
QString *quest_readline_read_line(const QString *prompt);
void     quest_readline_add_history(const QString *line);
void     quest_readline_read_history(const QString *path);
void     quest_readline_write_history(const QString *path, int64_t max_lines);

/* Writer module primitives */
extern QWriter quest_writer_output_val;
extern QWriter quest_writer_err_val;
#define quest_writer_output (&quest_writer_output_val)
#define quest_writer_err    (&quest_writer_err_val)

QWriter *quest_writer_file(const QString *name);
void     quest_writer_put_string(QWriter *w, const QString *s);
void     quest_writer_put_char(QWriter *w, QChar ch);
void     quest_writer_put_substring(QWriter *w, const QString *s, int64_t start, int64_t size);
void     quest_writer_flush(QWriter *w);
void     quest_writer_close(QWriter *w);

/* Reader module primitives */
extern QReader quest_reader_input_val;
#define quest_reader_input (&quest_reader_input_val)

QReader *quest_reader_file(const QString *name);
bool     quest_reader_more(QReader *r);
bool     quest_reader_ready(QReader *r);
QChar    quest_reader_get_char(QReader *r);
QString *quest_reader_get_string(QReader *r, int64_t size);
void     quest_reader_get_substring(QReader *r, QString *s, int64_t start, int64_t size);
void     quest_reader_close(QReader *r);

/* Conv module primitives */
QString *quest_conv_okay(void);
QString *quest_conv_bool(bool b);
QString *quest_conv_int(int64_t n);
QString *quest_conv_real(double r);
QString *quest_conv_char(QChar ch);
QString *quest_conv_string(const QString *s);

/* Strutil module primitives */
double   quest_strutil_to_real(const QString *s);

/* StringBuilder (lib/util/stringbuilder) native buffer. Short appends are written into a fixed working buffer;
 * when it fills, it becomes a finished chunk and a new working buffer is started. A string longer than
 * QUEST_SB_LONG_APPEND is copied into a chunk of its own instead of passing through the working buffer.
 * quest_sb_to_string always returns a new string, so the builder can be reused after it. */
#define QUEST_SB_BUFFER_SIZE 512
#define QUEST_SB_LONG_APPEND 256

typedef struct QStringBuilder {
    char     *buffer;       /* working buffer of QUEST_SB_BUFFER_SIZE bytes (pointer-free memory) */
    int64_t   used;         /* bytes used in the working buffer */
    QString **chunks;       /* finished chunks, in order */
    int64_t   chunk_count;
    int64_t   chunk_capacity;
    int64_t   length;       /* total length: the chunks and the working buffer */
} QStringBuilder;

QStringBuilder *quest_sb_new(void);
void     quest_sb_append_string(QStringBuilder *b, const QString *s);
void     quest_sb_append_char(QStringBuilder *b, QChar ch);
void     quest_sb_append_int(QStringBuilder *b, int64_t n);
void     quest_sb_append_real(QStringBuilder *b, double r);
void     quest_sb_append_bool(QStringBuilder *b, bool v);
void     quest_sb_append_word(QStringBuilder *b, uint64_t w);
void     quest_sb_append_sub(QStringBuilder *b, const QString *s, int64_t start, int64_t size);
void     quest_sb_append_repeat(QStringBuilder *b, QChar ch, int64_t n);
void     quest_sb_clear(QStringBuilder *b);
int64_t  quest_sb_length(const QStringBuilder *b);
QString *quest_sb_to_string(const QStringBuilder *b);

/* Ascii module primitives */
QChar   quest_ascii_char(int64_t n);
int64_t quest_ascii_val(QChar ch);

/* IntOp constants & primitives */
#define QUEST_INT_MIN (-9223372036854775807LL - 1LL)
#define QUEST_INT_MAX (9223372036854775807LL)

Q_INLINE int64_t quest_int_abs(int64_t n) {
    if (n == QUEST_INT_MIN) return QUEST_INT_MIN;
    return n < 0 ? -n : n;
}
Q_INLINE int64_t quest_int_min(int64_t a, int64_t b) { return a < b ? a : b; }
Q_INLINE int64_t quest_int_max(int64_t a, int64_t b) { return a > b ? a : b; }

/* RealOp constants & primitives */
#define QUEST_REAL_MIN (-1.7976931348623157e+308)
#define QUEST_REAL_MAX (1.7976931348623157e+308)
#define QUEST_REAL_POS_EPSILON (2.2204460492503131e-16)
#define QUEST_REAL_NEG_EPSILON (-2.2204460492503131e-16)
#define QUEST_REAL_E (2.71828182845904523536)
#define QUEST_REAL_PI (3.14159265358979323846)
#define QUEST_REAL_INFINITY ((double)INFINITY)

double  quest_real_from_int(int64_t n);
double  quest_real_log(double r);
int64_t quest_real_floor(double r);
int64_t quest_real_round(double r);
Q_INLINE double quest_real_abs(double r) { return fabs(r); }
Q_INLINE double quest_real_min(double a, double b) { return a < b ? a : b; }
Q_INLINE double quest_real_max(double a, double b) { return a > b ? a : b; }
double  quest_real_div(double a, double b);
double  quest_real_exp(double a, double b);
double  quest_real_sqrt(double r);
double  quest_real_sin(double r);
double  quest_real_cos(double r);
double  quest_real_tan(double r);
double  quest_real_asin(double r);
double  quest_real_acos(double r);
double  quest_real_atan(double r);
double  quest_real_atan2(double y, double x);
double  quest_real_exponential(double r);
double  quest_real_sinh(double r);
double  quest_real_cosh(double r);
double  quest_real_tanh(double r);
int64_t quest_real_ceil(double r);
int64_t quest_real_trunc(double r);
QString *quest_real_format(double r, QChar style, int64_t digits);

/* Word module primitives */
double   quest_word_to_real_val(uint64_t w);
uint64_t quest_word_from_real_val(double r);

/* Global standard library initialization */
void quest_builtins_init(int argc, char **argv);

/* Type descriptor interning and dynamic operations */
bool                   quest_is_subtype(const QTypeDescriptor *sub, const QTypeDescriptor *super_type);
const QTypeDescriptor *quest_intern_type_descriptor(const QTypeDescriptor *desc);
const QTypeDescriptor *quest_make_array_descriptor(const QTypeDescriptor *element_desc);
const QTypeDescriptor *quest_make_opaque_descriptor(const char *name);

/* Module abstract types (docs/dynamic.md §2.3). Each module registers the abstract types it exports when it is
 * initialized: by global name ("geo/coord.P"), with the number of parameters of an abstract type operator, and the
 * representation (for an operator, a template whose holes are its parameters). */
void                   quest_register_abstract_type(const char *name, size_t arity, const QTypeDescriptor *rep);
/* The registered representation of the abstract type `name` applied to `args`, or NULL if no module registers it;
 * *registered tells whether the name is registered at all (with another arity, the result is NULL) */
const QTypeDescriptor *quest_registered_abstract_rep(
    const char *name, size_t arg_count, const QTypeDescriptor *const *args, bool *registered);
/* The representation of an opaque descriptor that is a module abstract type (or an application of one), or NULL */
const QTypeDescriptor *quest_abstract_type_rep(const QTypeDescriptor *desc);
const QTypeDescriptor *quest_make_record_descriptor(
    const char *name, size_t size, size_t alignment, size_t field_count, const QRecordFieldDescriptor *fields);
const QTypeDescriptor *quest_make_tuple_descriptor(
    const char *name, size_t size, size_t alignment, size_t element_count, const QTupleElementDescriptor *elements);
const QTypeDescriptor *quest_make_variant_descriptor(
    const char *name, size_t size, size_t alignment, size_t case_count, const QVariantCaseDescriptor *cases);
const QTypeDescriptor *quest_make_fun_descriptor(
    const char *name, size_t param_count, const QFunParamDescriptor *params, const QTypeDescriptor *result_type);
QVariantVal            quest_variant_adapt(
    const QTypeDescriptor *sub_desc, const QTypeDescriptor *super_desc, QVal payload);
QAuto                 *quest_auto_new(const QTypeDescriptor *type_desc, QVal payload);

/* The runtime operations of the dynamic module (lib/dynamic.mod.quest), on values of its type T, whose one
 * component is stored as a QVal */
QAuto                 *quest_dynamic_copy(const QAuto *d);

/* Record offset tables (the dict of a QRecordVal): the table for viewing a payload with record layout `layout` at
 * record type `view`. quest_record_dict returns NULL when the layout lacks a field of the view.
 *
 * A table is the byte offsets of the view's fields in name order, followed by a QRecordStoredTypes pointer: NULL
 * when the payload stores every field at the view's type for it, and otherwise, per field, the type the payload
 * stores it at when that differs (a subtype, by depth subtyping) or NULL. Reads of such a field convert it. */
typedef const struct QTypeDescriptor *const *QRecordStoredTypes;
const void            *quest_record_dict(const QTypeDescriptor *view, const QTypeDescriptor *layout);
void                   quest_register_record_dict(
    const QTypeDescriptor *view, const QTypeDescriptor *layout, const void *dict);

/* The layout of a record value's payload, recorded in its header when it was created */
Q_INLINE const QTypeDescriptor *quest_record_layout(QRecordVal rec) {
    return ((const QRecordHeader *)rec.val)->descriptor;
}

/* A record value viewed at record type `view`: its payload with the offset table for the payload's own layout */
Q_INLINE QRecordVal quest_record_view(QRecordVal rec, const QTypeDescriptor *view) {
    if (rec.val == NULL) return rec;
    return (QRecordVal){ .val = rec.val, .dict = quest_record_dict(view, quest_record_layout(rec)) };
}

/* The byte offset in a record value's payload of the i-th field (in name order) of the type it is viewed at */
Q_INLINE size_t quest_record_field_offset(QRecordVal rec, size_t i) {
    return ((const size_t *)rec.dict)[i];
}

/* The stored types of a record value's offset table, for a view with field_count fields (see QRecordStoredTypes) */
Q_INLINE QRecordStoredTypes quest_record_stored_types(QRecordVal rec, size_t field_count) {
    return *(const QRecordStoredTypes *)((const size_t *)rec.dict + (field_count > 0 ? field_count : 1));
}

/* Proxies (docs/c-representation.md §5.8). A tuple or option upcast to a supertype at which its immutable components
 * change view (a record at a supertype, a variant or option whose cases the supertype numbers differently) is not
 * copied: the upcast value is a proxy, a pointer to a QProxy tagged with QUEST_PROXY_TAG in its low bit, holding the
 * original object (never itself a proxy), the descriptor of the type the original's components are stored at, and
 * the descriptor of the type the proxy is used at. Reading a component through a proxy reads it from the original and
 * converts it from its stored type to the view's (quest_convert); writing a var component writes the original. Values
 * of types whose components cannot change view are never proxies (the compiler unwraps one upcast to such a type). */
typedef struct QProxy {
    const void            *orig;
    const QTypeDescriptor *stored;
    const QTypeDescriptor *view;
    const int64_t         *tags;   /* an option's: for each tag of the stored type, the view's tag for its case */
    QVal                  *cache;  /* the immutable elements read so far, converted (NULL until one is read) */
    uint8_t               *cached; /* which of them have been */
} QProxy;

#define QUEST_PROXY_TAG ((uintptr_t)1)

Q_INLINE bool quest_is_proxy(const void *p) {
    return ((uintptr_t)p & QUEST_PROXY_TAG) != 0;
}

Q_INLINE const QProxy *quest_proxy_of(const void *p) {
    return (const QProxy *)((uintptr_t)p - QUEST_PROXY_TAG);
}

/* The object a tuple or option value is: the original of a proxy, or the value itself */
Q_INLINE void *quest_unproxy(const void *p) {
    return quest_is_proxy(p) ? (void *)quest_proxy_of(p)->orig : (void *)p;
}

/* v (a tuple or option of type `from`, or a proxy of one) viewed at type `to`: v's original if its type is laid out as
 * `to` is, and otherwise a proxy of the original (a proxy is never made of a proxy) */
void   *quest_make_proxy(const void *v, const QTypeDescriptor *from, const QTypeDescriptor *to);
/* Through a proxy of a tuple: element i (in its QVal form, at the view's type), its slot in the original (when stored
 * as the view lays it out), and a store into it (a var element, converted to the stored type) */
QVal    quest_proxy_element(const void *p, size_t i);
void   *quest_proxy_slot(const void *p, size_t i);
void    quest_proxy_store(const void *p, size_t i, QVal v);
/* Through a proxy of an option: its tag in the view's numbering, and element i of its case's payload */
int64_t quest_proxy_tag(const void *p);
QVal    quest_proxy_option_element(const void *p, size_t i);
/* The tuple payload of an option's case, which a case's binder shares (var
 * components included): the original's, which follows its tag, viewed at the
 * view's payload type for the case (a proxy of it where a component changes
 * view), through a proxy of the option or through a view map of a bounded type
 * parameter's */
void   *quest_proxy_option_payload(const void *p);
struct QViewMap;
void   *quest_view_option_payload(const void *opt, const struct QViewMap *m);

/* A tuple's element i, an option's tag, and element i of an option's case payload, through a proxy or not, for the
 * runtime's readers of values by descriptor (t: the value's type) */
QVal    quest_tuple_element(const void *tup, const QTypeDescriptor *t, size_t i);
int64_t quest_option_tag(const void *opt);
QVal    quest_option_element(const void *opt, const QTypeDescriptor *t, size_t i);

/* Values in aggregate slots (record fields, tuple elements, option payloads, array elements, auto payloads): every
 * slot is one word holding the value's QVal form (records and variants as pointers to immutable boxes, scalars in
 * their bits, pointers as they are), whatever the slot's type, and generic code's slots (QVal) alike */
Q_INLINE QVal quest_slot_read(const void *slot) {
    return *(const QVal *)slot;
}

Q_INLINE void quest_slot_write(void *slot, QVal v) {
    *(QVal *)slot = v;
}

/* Converts v, the QVal form of a value laid out as `from` describes, to its subtype view laid out as `to` describes:
 * records get the offset table for the view, variants and options their tags in `to`, tuples and auto values are
 * copied with their elements converted, and functions are wrapped by `to`'s adapter. A value whose layout already
 * suits `to` (quest_layout_equivalent) is returned as it is; an array, a tuple with var components, or an exception
 * whose layout does not is a fatal error, since a copy would not share its updates. */
QVal                   quest_convert(QVal v, const QTypeDescriptor *from, const QTypeDescriptor *to);

/* True if values laid out as `a` describes can be used as laid out as `b` describes, which describes the same type:
 * where one stores a type parameter generically and the other does not, the two representations agree. */
bool                   quest_layout_equivalent(const QTypeDescriptor *a, const QTypeDescriptor *b);

/* True if closures of function type `from` have the C signature of closures of function type `to` */
bool                   quest_fun_signature_equivalent(const QTypeDescriptor *from, const QTypeDescriptor *to);

/* The same for a value in a slot (a tuple element, record field, array element, or payload) */
bool                   quest_slot_layout_equivalent(const QTypeDescriptor *a, const QTypeDescriptor *b);

/* The descriptor that `template_desc` (a descriptor with holes, QHoleDescriptor) describes when its holes stand for
 * the type arguments `args`; memoized, so equal arguments give the same descriptor */
const QTypeDescriptor *quest_instantiate_descriptor(
    const QTypeDescriptor *template_desc, size_t arg_count, const QTypeDescriptor *const *args);

/* View maps (docs/c-representation.md §5.1). Generic code holds a value of a type parameter bounded by a record,
 * variant, or option type at its own view, its type argument's, and reads it through the bound by the view map of the
 * type argument at the bound, which a function fetches once for each such type parameter (memoized, so a pair has one
 * map). Parts read through the bound are converted from the type argument's types for them, where those differ. */
typedef struct QViewMap {
    const QTypeDescriptor *actual;  /* the type argument, as its values are held */
    const QTypeDescriptor *bound;
    /* A record's: for each field of the bound (in name order), the field's index among the actual's (in name order).
     * A variant's or option's: for each tag of the actual, the bound's tag for its case. A tuple's: none (its
     * components are the bound's, by position). */
    const int64_t         *index;
    /* The types parts read through the bound are converted from: a record's, for each field of the bound, the
     * actual's type for it; a tuple's, for each component of the bound, the actual's type for it; a variant's, for
     * each case of the bound, the actual's payload type; an option's, for each component of each case of the bound
     * (from component_start), the actual's. NULL where the actual's agrees with the bound's (nothing to convert).
     * `to` holds the bound's. */
    const QTypeDescriptor *const *from;
    const QTypeDescriptor *const *to;
    const size_t          *component_start;  /* an option's: for each case of the bound, its first component's index */
} QViewMap;
const QViewMap *quest_view_map(const QTypeDescriptor *actual, const QTypeDescriptor *bound);

/* Part i of a value read through a view map, from its QVal form: converted from the actual's type for it to the
 * bound's when they differ */
Q_INLINE QVal quest_view_part(const QViewMap *m, size_t i, QVal v) {
    return m->from[i] != NULL ? quest_convert(v, m->from[i], m->to[i]) : v;
}

/* Through a view map of a record type: the slot of field k of the bound (in name order) in a record value at the
 * actual's view, and the field's value (from its QVal form), converted from the type the payload stores it at, or the
 * actual's type for it, to the bound's */
Q_INLINE void *quest_view_record_slot(QRecordVal rec, const QViewMap *m, size_t k) {
    return (char *)rec.val + quest_record_field_offset(rec, (size_t)m->index[k]);
}

Q_INLINE QVal quest_view_record_field(QRecordVal rec, const QViewMap *m, size_t k) {
    size_t j = (size_t)m->index[k];
    QVal v = quest_slot_read((const char *)rec.val + quest_record_field_offset(rec, j));
    size_t field_count = ((const QRecordTypeDescriptor *)m->actual->extra)->field_count;
    QRecordStoredTypes stored = quest_record_stored_types(rec, field_count);
    if (stored != NULL && stored[j] != NULL) return quest_convert(v, stored[j], m->to[k]);
    return quest_view_part(m, k, v);
}

/* Through a view map of a tuple type: component i of a tuple at the actual's view (or a proxy of one), converted to
 * the bound's type for it, and the slot of a var component (the original's, through a proxy) */
Q_INLINE QVal quest_view_tuple_element(const void *tup, const QViewMap *m, size_t i) {
    return quest_view_part(m, i, quest_tuple_element(tup, m->actual, i));
}

Q_INLINE void *quest_view_tuple_slot(const void *tup, const QViewMap *m, size_t i) {
    if (quest_is_proxy(tup)) return quest_proxy_slot(tup, i);
    return (char *)tup + ((const QTupleTypeDescriptor *)m->actual->extra)->elements[i].offset;
}

/* Through a view map of a variant or option type: a value's tag in the bound's numbering, and component j of the
 * payload of case b (the bound's tag) of an option, converted to the bound's type for it */
Q_INLINE int64_t quest_view_option_tag(const void *opt, const QViewMap *m) {
    return m->index[quest_option_tag(opt)];
}

Q_INLINE QVal quest_view_option_component(const void *opt, const QViewMap *m, size_t b, size_t j) {
    return quest_view_part(m, m->component_start[b] + j, quest_option_element(opt, m->actual, j));
}

/* A descriptor's type, looking through QTYPE_KIND_STORED */
Q_INLINE const QTypeDescriptor *quest_stored_type(const QTypeDescriptor *d) {
    return (d != NULL && d->kind == QTYPE_KIND_STORED) ? ((const QStoredDescriptor *)d->extra)->type : d;
}

/* Exits with a fatal error: a value must be converted between layouts but holds mutable data */
void                   quest_layout_conversion_error(const QTypeDescriptor *from, const QTypeDescriptor *to);

/* The i-th field (in name order) of record value rec viewed at record type `view`, converted to the view's type */
QVal                   quest_record_field_value(QRecordVal rec, const QTypeDescriptor *view, size_t i);

Q_INLINE QRecordVal *quest_record_box(QRecordVal rec) {
    QRecordVal *box = (QRecordVal *)quest_alloc(sizeof(QRecordVal), &quest_layout_record_box);
    *box = rec;
    return box;
}

Q_INLINE QVariantVal *quest_variant_box(QVariantVal var) {
    QVariantVal *box = (QVariantVal *)quest_alloc(sizeof(QVariantVal), &quest_layout_variant_box);
    *box = var;
    return box;
}

/* The checked operations take the site of the operation (loc, "file:line:col"), which only their failing branch
   uses; the versions without _at are the runtime's own, with no site. */

Q_INLINE void quest_check_array_bounds_at(const void *arr_ptr, int64_t idx, const char *loc) {
    const QArray *a = (const QArray *)arr_ptr;
    if (a == NULL || idx < 0 || idx >= a->length) {
        quest_raise_array_error_at(loc);
    }
}

Q_INLINE void quest_check_array_bounds(const void *arr_ptr, int64_t idx) {
    quest_check_array_bounds_at(arr_ptr, idx, NULL);
}

/* The count of a new array, which may not be negative */
Q_INLINE int64_t quest_check_array_count_at(int64_t n, const char *loc) {
    if (n < 0) {
        quest_raise_array_error_at(loc);
    }
    return n;
}

/* Int arithmetic wraps (docs/type-system.md §6.3.1): a zero divisor raises int.error, and the one quotient outside
   Int's range, QUEST_INT_MIN / -1, wraps to QUEST_INT_MIN, with remainder 0. C leaves both undefined (and -fwrapv does
   not cover division), so a divisor of -1 is negation, which wraps under -fwrapv. */
Q_INLINE QInt quest_int_div_at(QInt a, QInt b, const char *loc) {
    if (b == 0) {
        quest_raise_int_error_at(loc);
    }
    if (b == -1) {
        return -a;
    }
    return a / b;
}

Q_INLINE QInt quest_int_mod_at(QInt a, QInt b, const char *loc) {
    if (b == 0) {
        quest_raise_int_error_at(loc);
    }
    if (b == -1) {
        return 0;
    }
    return a % b;
}

Q_INLINE QInt quest_int_div(QInt a, QInt b) { return quest_int_div_at(a, b, NULL); }
Q_INLINE QInt quest_int_mod(QInt a, QInt b) { return quest_int_mod_at(a, b, NULL); }

/* Real arithmetic keeps NaN out of Quest: an operation whose IEEE result would be NaN raises real.error.
   Infinities are ordinary Real values. See docs/type-system.md §6.3.2. */
Q_INLINE double quest_real_result_at(double r, const char *loc) {
    if (isnan(r)) {
        quest_raise_real_error_at(loc);
    }
    return r;
}

Q_INLINE double quest_real_result(double r) { return quest_real_result_at(r, NULL); }

Q_INLINE double quest_real_add_at(double a, double b, const char *loc) { return quest_real_result_at(a + b, loc); }
Q_INLINE double quest_real_sub_at(double a, double b, const char *loc) { return quest_real_result_at(a - b, loc); }
Q_INLINE double quest_real_mul_at(double a, double b, const char *loc) { return quest_real_result_at(a * b, loc); }

/* The // operator and real.div: a zero divisor also raises real.error. */
Q_INLINE double quest_real_divide_at(double a, double b, const char *loc) {
    if (b == 0.0) {
        quest_raise_real_error_at(loc);
    }
    return quest_real_result_at(a / b, loc);
}

Q_INLINE double quest_real_add(double a, double b) { return quest_real_add_at(a, b, NULL); }
Q_INLINE double quest_real_sub(double a, double b) { return quest_real_sub_at(a, b, NULL); }
Q_INLINE double quest_real_mul(double a, double b) { return quest_real_mul_at(a, b, NULL); }
Q_INLINE double quest_real_divide(double a, double b) { return quest_real_divide_at(a, b, NULL); }

/* The type is compares values of descriptor t at: a stored type's type, and a module abstract type's
   representation, which is compares its values as (docs/option-values.md section 2) */
const QTypeDescriptor *quest_identity_type(const QTypeDescriptor *t);
/* is on options of type t (or of an abstract type that is one): the same object, or the same case, which has no
   components or is a single-word option type's case with a component and the same component */
bool quest_option_is(const QTypeDescriptor *t, const void *a, const void *b);

/* is on values of a type known only by its descriptor. Bit equality is identity for every type except Real,
   where 0.0 is ~0.0 (NaN, the other case where bits and IEEE equality differ, never occurs), and options. */
Q_INLINE bool quest_val_is(const QTypeDescriptor *t, QVal a, QVal b) {
    if (a.u == b.u) return true;
    t = quest_identity_type(t);
    if (t != NULL && t->kind == QTYPE_KIND_OPTION) return quest_option_is(t, a.p, b.p);
    if (t != NULL && t->kind == QTYPE_KIND_TUPLE) {
        /* A proxy is the object it is a view of */
        return quest_unproxy(a.p) == quest_unproxy(b.p);
    }
    return t != NULL && t->kind == QTYPE_KIND_REAL && a.r == b.r;
}

Q_INLINE int64_t quest_check_option_ordinal_at(int64_t n, int64_t count, const char *loc) {
    if (n < 0 || n >= count) {
        quest_option_ordinal_error_at(n, count, loc);
    }
    return n;
}

Q_INLINE int64_t quest_check_option_ordinal(int64_t n, int64_t count) {
    return quest_check_option_ordinal_at(n, count, NULL);
}

Q_INLINE uint64_t quest_word_shift(uint64_t w, int64_t count) {
    if (count >= 64 || count <= -64) return 0ULL;
    if (count > 0) return w << count;
    if (count < 0) return w >> (-count);
    return w;
}

Q_INLINE uint64_t quest_word_rotate(uint64_t w, int64_t count) {
    int64_t shift = count % 64;
    if (shift < 0) shift += 64;
    if (shift == 0) return w;
    return (w << shift) | (w >> (64 - shift));
}

Q_INLINE uint64_t quest_word_extract(uint64_t w, int64_t pos, int64_t width) {
    if (pos < 0 || pos >= 64 || width <= 0) return 0ULL;
    if (width > 64 - pos) width = 64 - pos;
    uint64_t mask = (width == 64) ? ~0ULL : ((1ULL << width) - 1ULL);
    return (w >> pos) & mask;
}

Q_INLINE uint64_t quest_word_replace(uint64_t w, uint64_t val, int64_t pos, int64_t width) {
    if (pos < 0 || pos >= 64 || width <= 0) return w;
    if (width > 64 - pos) width = 64 - pos;
    uint64_t mask = (width == 64) ? ~0ULL : ((1ULL << width) - 1ULL);
    return (w & ~(mask << pos)) | ((val & mask) << pos);
}

Q_INLINE int64_t quest_word_pop_count(uint64_t w) {
    return (int64_t)__builtin_popcountll(w);
}

Q_INLINE int64_t quest_word_count_leading_zeros(uint64_t w) {
    if (w == 0ULL) return 64;
    return (int64_t)__builtin_clzll(w);
}

Q_INLINE int64_t quest_word_count_trailing_zeros(uint64_t w) {
    if (w == 0ULL) return 64;
    return (int64_t)__builtin_ctzll(w);
}

Q_INLINE bool quest_word_get_bit(uint64_t w, int64_t pos) {
    if (pos < 0 || pos >= 64) return false;
    return ((w >> pos) & 1ULL) != 0;
}

Q_INLINE uint64_t quest_word_set_bit(uint64_t w, int64_t pos) {
    if (pos < 0 || pos >= 64) return w;
    return w | (1ULL << pos);
}

Q_INLINE uint64_t quest_word_clear_bit(uint64_t w, int64_t pos) {
    if (pos < 0 || pos >= 64) return w;
    return w & ~(1ULL << pos);
}

Q_INLINE uint64_t quest_word_div(uint64_t a, uint64_t b) {
    if (b == 0) {
        quest_raise_word_error();
    }
    return a / b;
}

Q_INLINE uint64_t quest_word_mod(uint64_t a, uint64_t b) {
    if (b == 0) {
        quest_raise_word_error();
    }
    return a % b;
}

/* The word module's primitives (lib/word.mod.quest), inline so that a direct call of
 * one compiles to its operator */
Q_INLINE uint64_t quest_word_not_bits(uint64_t w) {
    return ~w;
}

Q_INLINE uint64_t quest_word_and_bits(uint64_t w1, uint64_t w2) {
    return w1 & w2;
}

Q_INLINE uint64_t quest_word_or_bits(uint64_t w1, uint64_t w2) {
    return w1 | w2;
}

Q_INLINE uint64_t quest_word_xor_bits(uint64_t w1, uint64_t w2) {
    return w1 ^ w2;
}

Q_INLINE uint64_t quest_word_shift_val(uint64_t w, int64_t count) {
    return quest_word_shift(w, count);
}

Q_INLINE uint64_t quest_word_rotate_val(uint64_t w, int64_t count) {
    return quest_word_rotate(w, count);
}

Q_INLINE uint64_t quest_word_extract_val(uint64_t w, int64_t pos, int64_t width) {
    return quest_word_extract(w, pos, width);
}

Q_INLINE uint64_t quest_word_replace_val(uint64_t w, uint64_t val, int64_t pos, int64_t width) {
    return quest_word_replace(w, val, pos, width);
}

Q_INLINE int64_t quest_word_pop_count_val(uint64_t w) {
    return quest_word_pop_count(w);
}

Q_INLINE int64_t quest_word_count_leading_zeros_val(uint64_t w) {
    return quest_word_count_leading_zeros(w);
}

Q_INLINE int64_t quest_word_count_trailing_zeros_val(uint64_t w) {
    return quest_word_count_trailing_zeros(w);
}

Q_INLINE bool quest_word_get_bit_val(uint64_t w, int64_t pos) {
    return quest_word_get_bit(w, pos);
}

Q_INLINE uint64_t quest_word_set_bit_val(uint64_t w, int64_t pos) {
    return quest_word_set_bit(w, pos);
}

Q_INLINE uint64_t quest_word_clear_bit_val(uint64_t w, int64_t pos) {
    return quest_word_clear_bit(w, pos);
}

Q_INLINE uint64_t quest_word_add(uint64_t w1, uint64_t w2) {
    return w1 + w2;
}

Q_INLINE uint64_t quest_word_sub(uint64_t w1, uint64_t w2) {
    return w1 - w2;
}

Q_INLINE uint64_t quest_word_mul(uint64_t w1, uint64_t w2) {
    return w1 * w2;
}

/* The high 64 bits of the unsigned 128-bit product (one umulh on arm64) */
Q_INLINE uint64_t quest_word_mul_hi(uint64_t w1, uint64_t w2) {
    return (uint64_t)(((unsigned __int128)w1 * w2) >> 64);
}

Q_INLINE uint64_t quest_word_div_val(uint64_t w1, uint64_t w2) {
    return quest_word_div(w1, w2);
}

Q_INLINE uint64_t quest_word_mod_val(uint64_t w1, uint64_t w2) {
    return quest_word_mod(w1, w2);
}

Q_INLINE int64_t quest_word_to_int(uint64_t w) {
    return (int64_t)w;
}

Q_INLINE uint64_t quest_word_from_int(int64_t n) {
    return (uint64_t)n;
}

Q_INLINE bool quest_word_lt(uint64_t w1, uint64_t w2) {
    return w1 < w2;
}

Q_INLINE bool quest_word_le(uint64_t w1, uint64_t w2) {
    return w1 <= w2;
}

Q_INLINE bool quest_word_gt(uint64_t w1, uint64_t w2) {
    return w1 > w2;
}

Q_INLINE bool quest_word_ge(uint64_t w1, uint64_t w2) {
    return w1 >= w2;
}

/* Hash utilities & SplitMix64 */
Q_INLINE uint64_t quest_hash_mix64(uint64_t z) {
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

uint64_t quest_hash_mix(uint64_t w);
uint64_t quest_hash_combine(uint64_t h1, uint64_t h2);
uint64_t quest_identity_hash(const QTypeDescriptor *t, QVal x);

/* Built-in operator closures (Cardelli §4.2) */
extern QClosure qv_sym_plus_closure;
extern QClosure qv_sym_minus_closure;
extern QClosure qv_sym_star_closure;
extern QClosure qv_sym_slash_closure;
extern QClosure qv_sym_percent_closure;
extern QClosure qv_mod_closure;
extern QClosure qv_sym_lt_closure;
extern QClosure qv_sym_lt_equals_closure;
extern QClosure qv_sym_gt_closure;
extern QClosure qv_sym_gt_equals_closure;
extern QClosure qv_sym_plus_plus_closure;
extern QClosure qv_sym_minus_minus_closure;
extern QClosure qv_sym_star_star_closure;
extern QClosure qv_sym_slash_slash_closure;
extern QClosure qv_sym_caret_caret_closure;
extern QClosure qv_sym_lt_lt_closure;
extern QClosure qv_sym_lt_lt_equals_closure;
extern QClosure qv_sym_gt_gt_closure;
extern QClosure qv_sym_gt_gt_equals_closure;
extern QClosure qv_sym_lt_gt_closure;
extern QClosure qv_sym_slash_backslash_closure;
extern QClosure qv_sym_backslash_slash_closure;

/* The JIT's unsound primitives, lib/os/value and lib/os/code (quest_code.c; docs/jit.md §3.11) */
typedef struct QCodeRegion QCodeRegion;
void        *quest_value_new(const QTypeDescriptor *a, QVal x);
QVal         quest_value_be(const QTypeDescriptor *a, void *v);
void        *quest_value_fetch(void *addr, int64_t displ);
void         quest_value_store(void *addr, int64_t displ, void *w);
QCodeRegion *quest_code_reserve(int64_t size, bool executable);
void        *quest_code_base(QCodeRegion *r);
int64_t      quest_code_size(QCodeRegion *r);
void         quest_code_write32(QCodeRegion *r, int64_t offset, QArray *words);
void         quest_code_write64(QCodeRegion *r, int64_t offset, QArray *words);
void        *quest_code_symbol(const QString *name);
bool         quest_code_is_null(void *v);
void        *quest_code_tlv_getter(void);
bool         quest_code_call(void *entry);
QRaised     *quest_code_last_raised(void);
QString     *quest_code_exception_name(QRaised *r);
QString     *quest_code_raise_site(QRaised *r);
QString     *quest_code_frames(QRaised *r);
void         quest_code_add_roots(void *low, void *high);
void         quest_code_add_function(void *start, void *limit);
void         quest_code_set_args(QArray *args);
/* The GDB JIT interface's descriptor and the function a debugger breaks on (quest_code.c) */
extern struct jit_descriptor __jit_debug_descriptor;
void __jit_debug_register_code(void);

#include "quest_serialization.h"

#endif /* QUEST_RUNTIME_H */
