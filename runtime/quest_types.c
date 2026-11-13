/*
 * Quest C Runtime: Type Descriptors
 *
 * The base types' descriptors and subtyping on descriptors (quest_is_subtype),
 * and constructing descriptors at run time: records, tuples, functions, the
 * abstract types of modules (docs/dynamic.md §2.3), and auto values.
 */

/* The POSIX functions -std=c99 hides on Linux (glibc) */
#if defined(__linux__) && !defined(_GNU_SOURCE)
#define _GNU_SOURCE
#endif

#include "quest_runtime_internal.h"

/* Universal subtyping predicate forward declaration */
bool quest_is_subtype(const QTypeDescriptor *sub, const QTypeDescriptor *super_type);

/* Statically pre-allocated base type descriptors */
const QTypeDescriptor quest_type_Word = {
    .kind = QTYPE_KIND_OPAQUE,
    .name = "word.T",
    .size = sizeof(QVal),
    .alignment = sizeof(QVal),
    .is_subtype = quest_is_subtype,
    .extra = NULL
};

const QTypeDescriptor quest_type_Int = {
    .kind = QTYPE_KIND_INT,
    .name = "Int",
    .size = sizeof(QInt),
    .alignment = sizeof(QInt),
    .is_subtype = quest_is_subtype,
    .extra = NULL
};

const QTypeDescriptor quest_type_Real = {
    .kind = QTYPE_KIND_REAL,
    .name = "Real",
    .size = sizeof(QReal),
    .alignment = sizeof(QReal),
    .is_subtype = quest_is_subtype,
    .extra = NULL
};

const QTypeDescriptor quest_type_Bool = {
    .kind = QTYPE_KIND_BOOL,
    .name = "Bool",
    .size = sizeof(QInt),
    .alignment = sizeof(QInt),
    .is_subtype = quest_is_subtype,
    .extra = NULL
};

const QTypeDescriptor quest_type_Char = {
    .kind = QTYPE_KIND_CHAR,
    .name = "Char",
    .size = sizeof(QInt),
    .alignment = sizeof(QInt),
    .is_subtype = quest_is_subtype,
    .extra = NULL
};

const QTypeDescriptor quest_type_String = {
    .kind = QTYPE_KIND_STRING,
    .name = "String",
    .size = sizeof(void *),
    .alignment = sizeof(void *),
    .is_subtype = quest_is_subtype,
    .extra = NULL
};

const QTypeDescriptor quest_type_Ok = {
    .kind = QTYPE_KIND_OK,
    .name = "Ok",
    .size = sizeof(QInt),
    .alignment = sizeof(QInt),
    .is_subtype = quest_is_subtype,
    .extra = NULL
};


const QTypeDescriptor quest_type_EmptyTuple = {
    .kind = QTYPE_KIND_TUPLE,
    .name = "Tuple end",
    .size = sizeof(void *),
    .alignment = sizeof(void *),
    .is_subtype = quest_is_subtype,
    .extra = NULL
};

#define Q_BOUND_VAR(i) { .kind = QTYPE_KIND_BOUND_VAR, .name = "#" #i, .size = sizeof(QVal), \
    .alignment = sizeof(QVal), .is_subtype = quest_is_subtype, .extra = NULL }
const QTypeDescriptor quest_type_bound_vars[Q_MAX_BOUND_VARS] = {
    Q_BOUND_VAR(0), Q_BOUND_VAR(1), Q_BOUND_VAR(2), Q_BOUND_VAR(3), Q_BOUND_VAR(4), Q_BOUND_VAR(5),
    Q_BOUND_VAR(6), Q_BOUND_VAR(7), Q_BOUND_VAR(8), Q_BOUND_VAR(9), Q_BOUND_VAR(10), Q_BOUND_VAR(11),
    Q_BOUND_VAR(12), Q_BOUND_VAR(13), Q_BOUND_VAR(14), Q_BOUND_VAR(15), Q_BOUND_VAR(16), Q_BOUND_VAR(17),
    Q_BOUND_VAR(18), Q_BOUND_VAR(19), Q_BOUND_VAR(20), Q_BOUND_VAR(21), Q_BOUND_VAR(22), Q_BOUND_VAR(23),
    Q_BOUND_VAR(24), Q_BOUND_VAR(25), Q_BOUND_VAR(26), Q_BOUND_VAR(27), Q_BOUND_VAR(28), Q_BOUND_VAR(29),
    Q_BOUND_VAR(30), Q_BOUND_VAR(31),
};

/* Global Interning Table for Type Descriptors */
static char *quest_dup_str(const char *s) {
    if (s == NULL) return NULL;
    size_t len = strlen(s);
    char *copy = (char *)quest_alloc_bytes(len + 1);
    memcpy(copy, s, len + 1);
    return copy;
}

/* The trail of quest_is_subtype: the pairs (sub, super_type) whose proofs are
 * in progress, innermost last; each call that compares parts pushes its pair
 * and pops it when it returns. Descriptors of recursive types are cyclic, so a proof can come back
 * to a pair it is already proving. That pair is assumed to hold (the proof is
 * coinductive): every way of following the two types has been compared up to
 * the cycle without finding a difference, so there is none. Without the
 * assumption, comparing Rec(L) Option nil cons with head: Int tail: L end end
 * with itself, through the separate descriptors two units emit for it, would
 * never end. Its pairs are QSubtypePairs (quest_runtime_internal.h).
 *
 * The trail grows as deep comparisons need, in C memory; its pairs in use
 * are roots (quest_runtime_roots), since a descriptor being compared may be
 * reachable from nothing else */
static Q_THREAD_LOCAL QSubtypePair *quest_subtyping_trail = NULL;
static Q_THREAD_LOCAL size_t quest_subtyping_trail_len = 0, quest_subtyping_trail_cap = 0;

/* Whether the type sub describes is a subtype of the one super_type describes,
 * compared structurally (docs/c-representation.md §6.4.4, Subtyping
 * Verification), as the type checkers compare types (types/subtyping in both
 * compilers, docs/type-system.md §3.2) but without caching. Stored descriptors
 * are looked through, and equal pointers are equal types. By kind of
 * super_type:
 *
 *   - Int, Real, Bool, Char, String, Ok, bound type variables, and holes: the
 *     same descriptor only;
 *   - tuples: a prefix, with names equal where super_type names an element,
 *     and covariant elements, or invariant and var when super_type's is var
 *     (any tuple is a subtype of Tuple end);
 *   - records: every field of super_type, by name, covariant, or invariant
 *     and var when super_type's is var;
 *   - variants and options: every case of sub in super_type, by name, with a
 *     payload in both or neither, covariant, or invariant when either is var;
 *   - arrays and exceptions: invariant in the element or payload type;
 *   - functions: as many parameters, each of the same mode, and type
 *     parameters, equal bounds, contravariant value parameters, invariant var
 *     parameters, covariant out parameters and result;
 *   - opaque types: the same name, and equal arguments for an application;
 *   - auto types: a bound within super_type's, if it has one, then a prefix
 *     of components with equal names and var-ness, covariant, or invariant
 *     when var.
 *
 * Covariant means sub's part is a subtype of super_type's, contravariant the
 * reverse, and invariant both. Pairs met again while being proved are assumed
 * to hold (the trail, above), which grows as deeply nested types need */
bool quest_is_subtype(const QTypeDescriptor *sub, const QTypeDescriptor *super_type) {
    /* A value stored as a type parameter has its type argument's type */
    sub = quest_stored_type(sub);
    super_type = quest_stored_type(super_type);
    if (sub == super_type) return true;
    if (sub == NULL || super_type == NULL) return false;

    /* Cycle detection trail */
    for (size_t i = 0; i < quest_subtyping_trail_len; ++i) {
        if (quest_subtyping_trail[i].sub == sub && quest_subtyping_trail[i].super_type == super_type) {
            return true;
        }
    }
    if (quest_subtyping_trail_len == quest_subtyping_trail_cap) {
        size_t cap = quest_subtyping_trail_cap > 0 ? 2 * quest_subtyping_trail_cap : 64;
        QSubtypePair *grown = (QSubtypePair *)realloc(quest_subtyping_trail, cap * sizeof *grown);
        if (grown == NULL) {
            fprintf(stderr, "quest: out of memory comparing types\n");
            abort();
        }
        quest_subtyping_trail = grown;
        quest_subtyping_trail_cap = cap;
    }
    quest_subtyping_trail[quest_subtyping_trail_len++] = (QSubtypePair){ sub, super_type };

    bool result = false;

    switch (super_type->kind) {
        case QTYPE_KIND_INT:
        case QTYPE_KIND_REAL:
        case QTYPE_KIND_BOOL:
        case QTYPE_KIND_CHAR:
        case QTYPE_KIND_STRING:
        case QTYPE_KIND_OK:
            result = (sub == super_type);
            break;

        case QTYPE_KIND_AUTO: {
            /* Cardelli §6.7: a subkind for the type component, then, as for
             * tuples, a prefix of the components with matching names, covariant
             * immutable and invariant var components */
            if (sub->kind != QTYPE_KIND_AUTO) { result = false; break; }
            const QAutoTypeDescriptor *s = (const QAutoTypeDescriptor *)sub->extra;
            const QAutoTypeDescriptor *t = (const QAutoTypeDescriptor *)super_type->extra;
            if (s == NULL || t == NULL) { result = (s == t); break; }
            if (t->bound != NULL && (s->bound == NULL || !quest_is_subtype(s->bound, t->bound))) {
                result = false;
                break;
            }
            if (s->component_count < t->component_count) { result = false; break; }
            bool match = true;
            for (size_t i = 0; i < t->component_count && match; ++i) {
                const QAutoComponentDescriptor *sc = &s->components[i];
                const QAutoComponentDescriptor *tc = &t->components[i];
                if (strcmp(sc->name, tc->name) != 0 || sc->is_var != tc->is_var) {
                    match = false;
                } else if (tc->is_var) {
                    match = quest_is_subtype(sc->type, tc->type) && quest_is_subtype(tc->type, sc->type);
                } else {
                    match = quest_is_subtype(sc->type, tc->type);
                }
            }
            result = match;
            break;
        }

        case QTYPE_KIND_EXCEPTION: {
            /* Invariant payload type */
            if (sub->kind != QTYPE_KIND_EXCEPTION) { result = false; break; }
            const QExceptionTypeDescriptor *s = (const QExceptionTypeDescriptor *)sub->extra;
            const QExceptionTypeDescriptor *t = (const QExceptionTypeDescriptor *)super_type->extra;
            if (s == NULL || t == NULL) { result = (s == t); break; }
            result = quest_is_subtype(s->payload_type, t->payload_type) &&
                     quest_is_subtype(t->payload_type, s->payload_type);
            break;
        }

        case QTYPE_KIND_OPAQUE: {
            result = (sub == super_type) ||
                     (sub->kind == QTYPE_KIND_OPAQUE && sub->name != NULL && super_type->name != NULL &&
                      strcmp(sub->name, super_type->name) == 0);
            /* An abstract type operator's applications are equal when their
             * arguments are equal types */
            const QOpaqueTypeDescriptor *s = (const QOpaqueTypeDescriptor *)sub->extra;
            const QOpaqueTypeDescriptor *t = (const QOpaqueTypeDescriptor *)super_type->extra;
            size_t s_args = s != NULL ? s->arg_count : 0, t_args = t != NULL ? t->arg_count : 0;
            if (result && sub != super_type && (s_args != 0 || t_args != 0)) {
                result = s_args == t_args;
                for (size_t i = 0; result && i < t_args; ++i) {
                    result = quest_is_subtype(s->args[i], t->args[i]) && quest_is_subtype(t->args[i], s->args[i]);
                }
            }
            break;
        }

        case QTYPE_KIND_ARRAY: {
            if (sub->kind != QTYPE_KIND_ARRAY) { result = false; break; }
            const QArrayTypeDescriptor *s = (const QArrayTypeDescriptor *)sub->extra;
            const QArrayTypeDescriptor *t = (const QArrayTypeDescriptor *)super_type->extra;
            if (s == NULL || t == NULL) { result = false; break; }
            result = quest_is_subtype(s->element_type, t->element_type) &&
                     quest_is_subtype(t->element_type, s->element_type);
            break;
        }

        case QTYPE_KIND_TUPLE: {
            /* Tuple end is a supertype of every tuple (and only of tuples) */
            if (sub->kind != QTYPE_KIND_TUPLE) { result = false; break; }
            const QTupleTypeDescriptor *s = (const QTupleTypeDescriptor *)sub->extra;
            const QTupleTypeDescriptor *t = (const QTupleTypeDescriptor *)super_type->extra;
            if (t == NULL || t->element_count == 0) { result = true; break; }
            if (s == NULL || s->element_count < t->element_count) { result = false; break; }
            bool match = true;
            for (size_t i = 0; i < t->element_count; ++i) {
                if (t->elements[i].name != NULL) {
                    if (s->elements[i].name == NULL || strcmp(s->elements[i].name, t->elements[i].name) != 0) {
                        match = false;
                        break;
                    }
                }
                /* A var element, as a record's var field: the value's is var too, of the same type */
                if (t->elements[i].is_var) {
                    if (!s->elements[i].is_var || !quest_is_subtype(s->elements[i].type, t->elements[i].type) ||
                        !quest_is_subtype(t->elements[i].type, s->elements[i].type)) {
                        match = false;
                        break;
                    }
                } else if (!quest_is_subtype(s->elements[i].type, t->elements[i].type)) {
                    match = false;
                    break;
                }
            }
            result = match;
            break;
        }

        case QTYPE_KIND_RECORD: {
            if (sub->kind != QTYPE_KIND_RECORD) { result = false; break; }
            const QRecordTypeDescriptor *s = (const QRecordTypeDescriptor *)sub->extra;
            const QRecordTypeDescriptor *t = (const QRecordTypeDescriptor *)super_type->extra;
            if (t == NULL || t->field_count == 0) { result = true; break; }
            if (s == NULL) { result = false; break; }
            bool match = true;
            for (size_t j = 0; j < t->field_count; ++j) {
                const QRecordFieldDescriptor *tf = &t->fields[j];
                const QRecordFieldDescriptor *sf = NULL;
                for (size_t i = 0; i < s->field_count; ++i) {
                    if (s->fields[i].name != NULL && strcmp(s->fields[i].name, tf->name) == 0) {
                        sf = &s->fields[i];
                        break;
                    }
                }
                if (sf == NULL) { match = false; break; }
                if (tf->is_var) {
                    if (!sf->is_var) { match = false; break; }
                    if (!quest_is_subtype(sf->type, tf->type) || !quest_is_subtype(tf->type, sf->type)) {
                        match = false;
                        break;
                    }
                } else {
                    if (!quest_is_subtype(sf->type, tf->type)) {
                        match = false;
                        break;
                    }
                }
            }
            result = match;
            break;
        }

        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION: {
            if (sub->kind != QTYPE_KIND_VARIANT && sub->kind != QTYPE_KIND_OPTION) {
                result = false;
                break;
            }
            const QVariantTypeDescriptor *s = (const QVariantTypeDescriptor *)sub->extra;
            const QVariantTypeDescriptor *t = (const QVariantTypeDescriptor *)super_type->extra;
            if (s == NULL || s->case_count == 0) { result = true; break; }
            if (t == NULL) { result = false; break; }
            bool match = true;
            for (size_t i = 0; i < s->case_count; ++i) {
                const QVariantCaseDescriptor *sc = &s->cases[i];
                const QVariantCaseDescriptor *tc = NULL;
                for (size_t j = 0; j < t->case_count; ++j) {
                    if (t->cases[j].name != NULL && strcmp(t->cases[j].name, sc->name) == 0) {
                        tc = &t->cases[j];
                        break;
                    }
                }
                if (tc == NULL) { match = false; break; }
                if (sc->payload_type == NULL) {
                    if (tc->payload_type != NULL) { match = false; break; }
                } else {
                    if (tc->payload_type == NULL) { match = false; break; }
                    if (sc->is_var || tc->is_var) {
                        if (!quest_is_subtype(sc->payload_type, tc->payload_type) ||
                            !quest_is_subtype(tc->payload_type, sc->payload_type)) {
                            match = false;
                            break;
                        }
                    } else {
                        if (!quest_is_subtype(sc->payload_type, tc->payload_type)) {
                            match = false;
                            break;
                        }
                    }
                }
            }
            result = match;
            break;
        }

        case QTYPE_KIND_FUN: {
            if (sub->kind != QTYPE_KIND_FUN) { result = false; break; }
            const QFunTypeDescriptor *s = (const QFunTypeDescriptor *)sub->extra;
            const QFunTypeDescriptor *t = (const QFunTypeDescriptor *)super_type->extra;
            if (s == NULL || t == NULL) { result = (s == t); break; }
            if (s->param_count != t->param_count || s->quantifier_count != t->quantifier_count) {
                result = false;
                break;
            }
            /* Type parameters with equal bounds; contravariant value
             * parameters, invariant var parameters, covariant out parameters
             * and result (the parameter descriptors refer to type parameters by
             * index) */
            bool match = true;
            for (size_t i = 0; i < s->quantifier_count && match; ++i) {
                const QTypeDescriptor *sb = s->quantifier_bounds != NULL ? s->quantifier_bounds[i] : NULL;
                const QTypeDescriptor *tb = t->quantifier_bounds != NULL ? t->quantifier_bounds[i] : NULL;
                if (sb == NULL || tb == NULL) {
                    match = sb == tb;
                } else {
                    match = quest_is_subtype(sb, tb) && quest_is_subtype(tb, sb);
                }
            }
            for (size_t i = 0; i < s->param_count && match; ++i) {
                const QFunParamDescriptor *sp = &s->params[i];
                const QFunParamDescriptor *tp = &t->params[i];
                if (sp->is_var != tp->is_var || sp->is_out != tp->is_out) {
                    match = false;
                } else if (sp->is_var) {
                    match = quest_is_subtype(sp->type, tp->type) && quest_is_subtype(tp->type, sp->type);
                } else if (sp->is_out) {
                    match = quest_is_subtype(sp->type, tp->type);
                } else {
                    match = quest_is_subtype(tp->type, sp->type);
                }
            }
            if (match && s->result_type != t->result_type) {
                match = s->result_type != NULL && t->result_type != NULL &&
                        quest_is_subtype(s->result_type, t->result_type);
            }
            result = match;
            break;
        }

        default:
            result = (sub == super_type);
            break;
    }

    quest_subtyping_trail_len--;
    return result;
}


/* ------------------------------------------------------------------------- */
/* Type Descriptor Constructors & Helpers                                    */
/* ------------------------------------------------------------------------- */

/* Descriptors made at run time, for tests of the runtime (tests/python): each
 * call makes a new descriptor, which two of the same type are then equal as
 * quest_is_subtype compares them, not by address. Compiled code emits its
 * descriptors statically and never calls these. */

const QTypeDescriptor *quest_make_array_descriptor(const QTypeDescriptor *element_desc) {

    const char *elem_name = (element_desc && element_desc->name) ? element_desc->name : "Unknown";
    size_t name_len = strlen("Array()") + strlen(elem_name) + 1;
    char *arr_name = (char *)quest_alloc_bytes(name_len);
    snprintf(arr_name, name_len, "Array(%s)", elem_name);

    /* Allocate array descriptor */
    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor), &quest_layout_descriptor);
    desc->kind = QTYPE_KIND_ARRAY;
    desc->name = arr_name;
    desc->size = sizeof(void *);
    desc->alignment = sizeof(void *);
    desc->is_subtype = quest_is_subtype;

    QArrayTypeDescriptor *arr_meta = (QArrayTypeDescriptor *)quest_alloc(sizeof(QArrayTypeDescriptor), &quest_layout_array_descriptor);
    arr_meta->element_type = element_desc;
    quest_barrier(desc);
    desc->extra = arr_meta;

    return desc;
}

const QTypeDescriptor *quest_make_opaque_descriptor(const char *name) {
    const char *dup_name = name != NULL ? quest_dup_str(name) : "Opaque";
    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor), &quest_layout_descriptor);
    desc->kind = QTYPE_KIND_OPAQUE;
    desc->name = dup_name;
    desc->size = sizeof(QVal);
    desc->alignment = sizeof(QVal);
    desc->is_subtype = quest_is_subtype;
    desc->extra = NULL;
    /* Not interned: each call makes a new descriptor. Its identity is its
     * name all the same, since quest_is_subtype takes two opaque
     * descriptors of the same name (and equal arguments) as equal */
    return desc;
}

typedef struct QAbstractTypeEntry {
    const char                *name;
    size_t                     arity;
    const QTypeDescriptor     *rep;
    struct QAbstractTypeEntry *next;
} QAbstractTypeEntry;

static QAbstractTypeEntry *quest_abstract_types = NULL;

static QAbstractTypeEntry *quest_find_abstract_type(const char *name) {
    for (QAbstractTypeEntry *e = quest_abstract_types; e != NULL; e = e->next) {
        if (strcmp(e->name, name) == 0) return e;
    }
    return NULL;
}

void quest_register_abstract_type(const char *name, size_t arity, const QTypeDescriptor *rep) {
    if (quest_find_abstract_type(name) != NULL) return;
    QAbstractTypeEntry *e = (QAbstractTypeEntry *)quest_alloc(sizeof(QAbstractTypeEntry), &quest_layout_abstract_type_entry);
    e->name = name;
    e->arity = arity;
    e->rep = rep;
    e->next = quest_abstract_types;
    quest_abstract_types = e;
}

const QTypeDescriptor *quest_registered_abstract_rep(
    const char *name, size_t arg_count, const QTypeDescriptor *const *args, bool *registered
) {
    const QAbstractTypeEntry *e = name != NULL ? quest_find_abstract_type(name) : NULL;
    if (registered != NULL) *registered = e != NULL;
    if (e == NULL || e->arity != arg_count) return NULL;
    return arg_count > 0 ? quest_instantiate_descriptor(e->rep, arg_count, args) : e->rep;
}

const QTypeDescriptor *quest_abstract_type_rep(const QTypeDescriptor *desc) {
    if (desc == NULL || desc->kind != QTYPE_KIND_OPAQUE) return NULL;
    const QOpaqueTypeDescriptor *m = (const QOpaqueTypeDescriptor *)desc->extra;
    if (m != NULL && m->rep != NULL) return m->rep;
    return quest_registered_abstract_rep(desc->name, m != NULL ? m->arg_count : 0, m != NULL ? m->args : NULL, NULL);
}

const QTypeDescriptor *quest_make_record_descriptor(
    const char *name, size_t size, size_t alignment, size_t field_count, const QRecordFieldDescriptor *fields
) {
    const char *rec_name = name ? name : "Record end";

    const char *dup_name = quest_dup_str(rec_name);
    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor), &quest_layout_descriptor);
    desc->kind = QTYPE_KIND_RECORD;
    desc->name = dup_name;
    desc->size = size;
    desc->alignment = alignment > 0 ? alignment : sizeof(void *);
    desc->is_subtype = quest_is_subtype;

    size_t meta_size = sizeof(QRecordTypeDescriptor) + sizeof(QRecordFieldDescriptor) * field_count;
    QRecordTypeDescriptor *meta = (QRecordTypeDescriptor *)quest_alloc(meta_size, &quest_layout_record_descriptor);
    meta->field_count = field_count;
    if (fields != NULL && field_count > 0) {
        memcpy((void *)meta->fields, fields, sizeof(QRecordFieldDescriptor) * field_count);
    }
    quest_barrier(desc);
    desc->extra = meta;
    return desc;
}

const QTypeDescriptor *quest_make_variant_descriptor(
    const char *name, size_t size, size_t alignment, size_t case_count, const QVariantCaseDescriptor *cases
) {
    const char *var_name = name ? name : "Variant end";

    const char *dup_name = quest_dup_str(var_name);
    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor), &quest_layout_descriptor);
    desc->kind = QTYPE_KIND_VARIANT;
    desc->name = dup_name;
    desc->size = size > 0 ? size : sizeof(QVariantVal);
    desc->alignment = alignment > 0 ? alignment : sizeof(void *);
    desc->is_subtype = quest_is_subtype;

    size_t meta_size = sizeof(QVariantTypeDescriptor) + sizeof(QVariantCaseDescriptor) * case_count;
    QVariantTypeDescriptor *meta = (QVariantTypeDescriptor *)quest_alloc(meta_size, &quest_layout_variant_descriptor);
    meta->case_count = case_count;
    if (cases != NULL && case_count > 0) {
        memcpy((void *)meta->cases, cases, sizeof(QVariantCaseDescriptor) * case_count);
    }
    quest_barrier(desc);
    desc->extra = meta;
    return desc;
}

const QTypeDescriptor *quest_make_fun_descriptor(
    const char *name, size_t param_count, const QFunParamDescriptor *params, const QTypeDescriptor *result_type
) {
    const char *fn_name = name ? name : "Fun()";

    const char *dup_name = quest_dup_str(fn_name);
    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor), &quest_layout_descriptor);
    desc->kind = QTYPE_KIND_FUN;
    desc->name = dup_name;
    desc->size = sizeof(QClosure);
    desc->alignment = sizeof(void *);
    desc->is_subtype = quest_is_subtype;

    size_t meta_size = sizeof(QFunTypeDescriptor) + sizeof(QFunParamDescriptor) * param_count;
    QFunTypeDescriptor *meta = (QFunTypeDescriptor *)quest_alloc(meta_size, &quest_layout_fun_descriptor);
    meta->param_count = param_count;
    meta->result_type = result_type;
    meta->adapt = NULL;
    meta->invoke = NULL;
    meta->quantifier_count = 0;
    meta->quantifier_bounds = NULL;
    if (params != NULL && param_count > 0) {
        memcpy((void *)meta->params, params, sizeof(QFunParamDescriptor) * param_count);
    }
    quest_barrier(desc);
    desc->extra = meta;
    return desc;
}

QAuto *quest_auto_new(const QTypeDescriptor *type_desc, QVal payload) {
    QAuto *a = (QAuto *)quest_alloc(sizeof(QAuto), &quest_layout_auto);
    a->type_desc = type_desc;
    a->payload = payload;
    return a;
}

QAuto *quest_dynamic_copy(const QAuto *d) {
    if (d == NULL || d->type_desc == NULL) {
        quest_raise_dynamic_error();
    }
    QVal *component = (QVal *)quest_alloc(sizeof(QVal), &quest_layout_component);
    *component = *(const QVal *)d->payload.p;
    return quest_auto_new(d->type_desc, (QVal){ .p = component });
}

/* This file's global roots, for the collector and its roots check */
void quest_types_roots(QRootVisitor add) {
    if (quest_subtyping_trail_len > 0) add(quest_subtyping_trail, 2 * quest_subtyping_trail_len);
    add(&quest_abstract_types, 1);
}
