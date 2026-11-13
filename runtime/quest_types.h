/*
 * Quest C Runtime Interface: Type Descriptors
 *
 * Type descriptors, the run-time descriptions of types that generic code,
 * views, dynamic values, and echo use (docs/c-representation.md §6.4): the
 * kinds, the metadata of each, templates and holes, auto types and values;
 * and the base types' descriptors (quest_types.c).
 *
 * Part of quest_runtime.h, which includes it after the representation of
 * values; its bytes are in the ABI corpus's digest of the runtime's
 * interface with that header's.
 */

#ifndef QUEST_RUNTIME_H
#error "include quest_runtime.h, which includes quest_types.h"
#endif

#ifndef QUEST_TYPES_H
#define QUEST_TYPES_H

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
 *   module's abstract type by its global name, "geo/coord.P").
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

/* A field of a record type: its name, its type, its byte offset in a payload laid out as this record type (after
 * the QRecordHeader), and whether it is var (mutable) */
typedef struct QRecordFieldDescriptor {
    const char            *name;
    const QTypeDescriptor *type;
    size_t                 offset;
    bool                   is_var;
} QRecordFieldDescriptor;

/* A record type's fields, sorted by name, the order in which compiled code lays out payloads and offset tables: entry
 * i of an offset table for viewing a value at this type is the offset of fields[i] (quest_record_field_offset) */
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

/* A case of a variant or option type. A variant case's payload_type is its one type (Ok, or NULL, for a case
 * without a value); an option case's is the tuple type of its components, or NULL. tag_index is the case's tag in
 * this type's numbering, which is also its index in cases. */
typedef struct QVariantCaseDescriptor {
    const char            *name;
    const QTypeDescriptor *payload_type;
    int64_t                tag_index;
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

#endif
