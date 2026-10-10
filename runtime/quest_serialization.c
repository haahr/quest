/*
 * quest_serialization.c
 * Serialization of dynamic values (dynamic.extern and dynamic.intern), format version 1.
 *
 * A serialized dynamic value is one JSON document holding a type table and a value (docs/dynamic.md §2):
 *
 *     {"quest":1,"types":[<type node>,...],"type":<type ref>,"value":<value>}
 *
 * A type ref is a built-in type name or an index into the table; recursive types are cycles in the table. The table
 * is canonical, so that compiled code and the interpreter (bootstrap/python/quest/dynamic_json.py) write the same
 * text for the same value: the writer builds the graph of the types it meets from their descriptors, merges
 * structurally equivalent nodes (the coarsest bisimulation), and numbers the remaining nodes in the order a
 * depth-first walk from the roots first reaches them. Values are written and read by following their type, and
 * records, tuples, and arrays reached more than once are written once, with "@id", and then as {"@ref":n}.
 */

#include "quest_serialization.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <math.h>
#include <ctype.h>

#define Q_FORMAT_VERSION 1
#define Q_PTR_TABLE_SIZE 1024

/* ------------------------------------------------------------------------- */
/* Pointer Tables                                                            */
/* ------------------------------------------------------------------------- */

typedef struct QPtrNode {
    const void      *ptr;
    int              count;
    int              id;
    struct QPtrNode *next;
} QPtrNode;

typedef struct QPtrTable {
    QPtrNode *buckets[Q_PTR_TABLE_SIZE];
} QPtrTable;

static uint64_t quest_ptr_hash(const void *ptr) {
    uintptr_t val = (uintptr_t)ptr;
    return (uint64_t)((val >> 3) ^ (val >> 16)) % Q_PTR_TABLE_SIZE;
}

static QPtrNode *quest_ptr_find(const QPtrTable *table, const void *ptr) {
    if (table == NULL || ptr == NULL) return NULL;
    uint64_t h = quest_ptr_hash(ptr);
    for (QPtrNode *cur = table->buckets[h]; cur != NULL; cur = cur->next) {
        if (cur->ptr == ptr) return cur;
    }
    return NULL;
}

static QPtrNode *quest_ptr_insert_or_inc(QPtrTable *table, const void *ptr) {
    if (table == NULL || ptr == NULL) return NULL;
    uint64_t h = quest_ptr_hash(ptr);
    for (QPtrNode *cur = table->buckets[h]; cur != NULL; cur = cur->next) {
        if (cur->ptr == ptr) {
            cur->count++;
            return cur;
        }
    }
    QPtrNode *node = (QPtrNode *)quest_alloc(sizeof(QPtrNode));
    node->ptr = ptr;
    node->count = 1;
    node->id = 0;
    node->next = table->buckets[h];
    table->buckets[h] = node;
    return node;
}

/* ------------------------------------------------------------------------- */
/* Dynamic Values                                                            */
/* ------------------------------------------------------------------------- */

/* Dynamic.T is Auto A::TYPE with a:A end, whose one component is stored as a QVal. This is its descriptor for
 * values read back; compiled code has its own, which is structurally equal. */
static const struct {
    const QTypeDescriptor         *bound;
    size_t                         payload_size;
    size_t                         component_count;
    const QAutoComponentDescriptor components[1];
} quest_dynamic_meta = {
    .bound = NULL,
    .payload_size = sizeof(QVal),
    .component_count = 1,
    .components = { { .name = "a", .type = &quest_type_bound_vars[0], .storage = NULL, .offset = 0, .is_var = false } },
};

static const QTypeDescriptor quest_type_Dynamic_read = {
    .kind = QTYPE_KIND_AUTO,
    .name = "Dynamic",
    .size = sizeof(QAuto *),
    .alignment = sizeof(void *),
    .is_subtype = quest_is_subtype,
    .extra = &quest_dynamic_meta,
};

/* True for the descriptor of Auto A::TYPE with a:A end */
static bool quest_is_dynamic_type(const QTypeDescriptor *d) {
    if (d == NULL || d->kind != QTYPE_KIND_AUTO || d->extra == NULL) return false;
    const QAutoTypeDescriptor *meta = (const QAutoTypeDescriptor *)d->extra;
    if (meta->bound != NULL || meta->component_count != 1) return false;
    const QAutoComponentDescriptor *c = &meta->components[0];
    return strcmp(c->name, "a") == 0 && !c->is_var && c->type == &quest_type_bound_vars[0];
}

/* The packaged value of a dynamic value */
static QVal quest_dynamic_component(const QAuto *a) {
    return *(const QVal *)a->payload.p;
}

/* ------------------------------------------------------------------------- */
/* JSON Text Output                                                          */
/* ------------------------------------------------------------------------- */

static void quest_write_raw(QWriter *wr, const char *s) {
    size_t len = strlen(s);
    if (len > 0) {
        quest_writer_put_string(wr, quest_string_new(s, (int64_t)len));
    }
}

static void quest_write_json_string(QWriter *wr, const char *s, size_t len) {
    quest_writer_put_char(wr, '"');
    for (size_t i = 0; i < len; ++i) {
        unsigned char c = (unsigned char)s[i];
        switch (c) {
            case '"':  quest_write_raw(wr, "\\\""); break;
            case '\\': quest_write_raw(wr, "\\\\"); break;
            case '\b': quest_write_raw(wr, "\\b"); break;
            case '\f': quest_write_raw(wr, "\\f"); break;
            case '\n': quest_write_raw(wr, "\\n"); break;
            case '\r': quest_write_raw(wr, "\\r"); break;
            case '\t': quest_write_raw(wr, "\\t"); break;
            default:
                if (c < 0x20) {
                    char hex[8];
                    snprintf(hex, sizeof(hex), "\\u%04x", c);
                    quest_write_raw(wr, hex);
                } else {
                    quest_writer_put_char(wr, (QChar)c);
                }
                break;
        }
    }
    quest_writer_put_char(wr, '"');
}

static void quest_write_int(QWriter *wr, int64_t i) {
    char buf[32];
    snprintf(buf, sizeof(buf), "%" PRId64, i);
    quest_write_raw(wr, buf);
}

/* Writes a finite real as Python's repr does: the shortest digits that read back exactly, in positional notation
 * when the decimal exponent is in [-4, 16) (with ".0" for whole numbers), and otherwise as d.ddde+XX */
static void quest_write_real(QWriter *wr, double r) {
    if (isnan(r)) quest_raise_dynamic_error(); /* not a Real value (docs/type-system.md §6.3.1) */
    if (isinf(r)) { quest_write_raw(wr, r > 0 ? "\"Infinity\"" : "\"-Infinity\""); return; }
    char sci[40];
    for (int prec = 0; prec < 17; ++prec) {
        snprintf(sci, sizeof(sci), "%.*e", prec, r);
        if (strtod(sci, NULL) == r) break;
    }
    /* sci is [-]d[.ddd]e[+-]XX: collect the digits and the exponent */
    const char *p = sci;
    bool negative = *p == '-';
    if (negative) ++p;
    char digits[24];
    size_t n = 0;
    for (; *p != 'e'; ++p) {
        if (*p != '.') digits[n++] = *p;
    }
    int exp10 = atoi(p + 1);
    while (n > 1 && digits[n - 1] == '0') --n;
    digits[n] = '\0';

    char out[64];
    size_t len = 0;
    if (negative) out[len++] = '-';
    if (exp10 >= -4 && exp10 < 16) {
        if (exp10 < 0) {
            out[len++] = '0';
            out[len++] = '.';
            for (int i = -1; i > exp10; --i) out[len++] = '0';
            for (size_t i = 0; i < n; ++i) out[len++] = digits[i];
        } else {
            for (int i = 0; i <= exp10; ++i) out[len++] = (size_t)i < n ? digits[i] : '0';
            out[len++] = '.';
            if ((size_t)exp10 + 1 < n) {
                for (size_t i = (size_t)exp10 + 1; i < n; ++i) out[len++] = digits[i];
            } else {
                out[len++] = '0';
            }
        }
        out[len] = '\0';
    } else {
        out[len++] = digits[0];
        if (n > 1) {
            out[len++] = '.';
            for (size_t i = 1; i < n; ++i) out[len++] = digits[i];
        }
        snprintf(out + len, sizeof(out) - len, "e%c%02d", exp10 < 0 ? '-' : '+', exp10 < 0 ? -exp10 : exp10);
    }
    quest_write_raw(wr, out);
}

/* ------------------------------------------------------------------------- */
/* Type Graphs                                                               */
/* ------------------------------------------------------------------------- */

/* A type ref: a node index (>= 0) or one of these built-in types */
enum {
    QREF_OK = -1,
    QREF_BOOL = -2,
    QREF_CHAR = -3,
    QREF_STRING = -4,
    QREF_INT = -5,
    QREF_REAL = -6,
    QREF_DYNAMIC = -7,
};
static const char *const quest_builtin_ref_names[] = { "", "Ok", "Bool", "Char", "String", "Int", "Real", "Dynamic" };
#define Q_BUILTIN_REF_COUNT 7

typedef enum QTypeNodeKind {
    QTN_RECORD,
    QTN_TUPLE,
    QTN_VARIANT,
    QTN_OPTION,
    QTN_ARRAY,
    QTN_FUN,
    QTN_EXCEPTION,
} QTypeNodeKind;

static const char *const quest_type_node_names[] = { "record", "tuple", "variant", "option", "array", "fun", "exception" };
#define Q_TYPE_NODE_KIND_COUNT 7

/* A type node: its constructor and labels (its shape), and the refs of its component types. Labels are field names
 * (with "var " for mutable fields), case tags, or function parameter modes. Children are in the order the node
 * lists them: record fields by name, tuple components and parameters in order (then a function's result), and the
 * cases of a variant or option that have a payload, in declaration order. */
typedef struct QTypeNode {
    QTypeNodeKind kind;
    size_t        label_count;
    const char  **labels;
    bool         *has_payload;
    size_t        child_count;
    int          *children;
} QTypeNode;

typedef struct QTypeGraph {
    QTypeNode *nodes;
    size_t     count;
    size_t     cap;
    QPtrTable  index;      /* descriptor -> node (id is the node index + 1) */
    int       *roots;
    size_t     root_count;
    size_t     root_cap;
    int       *cls;        /* after canonicalization: each node's class */
    int       *number;     /* each class's index in the table, or -1 */
    int       *order;      /* a node of each class, in table order */
    size_t     order_count;
} QTypeGraph;

static const char *quest_var_label(const char *name, bool is_var) {
    if (name == NULL) name = "";
    if (!is_var) return name;
    if (name[0] == '\0') return "var";
    size_t len = strlen(name);
    char *label = (char *)quest_alloc_atomic(len + 5);
    memcpy(label, "var ", 4);
    memcpy(label + 4, name, len + 1);
    return label;
}

static int quest_tg_ref(QTypeGraph *g, const QTypeDescriptor *d);

static int quest_tg_new_node(QTypeGraph *g, const QTypeDescriptor *d) {
    if (g->count == g->cap) {
        size_t cap = g->cap ? g->cap * 2 : 16;
        QTypeNode *nodes = (QTypeNode *)quest_alloc(sizeof(QTypeNode) * cap);
        if (g->count) memcpy(nodes, g->nodes, sizeof(QTypeNode) * g->count);
        g->nodes = nodes;
        g->cap = cap;
    }
    int index = (int)g->count++;
    memset(&g->nodes[index], 0, sizeof(QTypeNode));
    quest_ptr_insert_or_inc(&g->index, d)->id = index + 1;
    return index;
}

/* The ref of a descriptor's type, adding nodes for it and the types it mentions. Raises dynamic.error for types the
 * format cannot express: polymorphic functions, auto types other than Dynamic.T, and abstract types. */
static int quest_tg_ref(QTypeGraph *g, const QTypeDescriptor *d) {
    if (d == NULL) quest_raise_dynamic_error();
    d = quest_stored_type(d);
    switch (d->kind) {
        case QTYPE_KIND_OK: return QREF_OK;
        case QTYPE_KIND_BOOL: return QREF_BOOL;
        case QTYPE_KIND_CHAR: return QREF_CHAR;
        case QTYPE_KIND_STRING: return QREF_STRING;
        case QTYPE_KIND_INT: return QREF_INT;
        case QTYPE_KIND_REAL: return QREF_REAL;
        case QTYPE_KIND_AUTO:
            if (quest_is_dynamic_type(d)) return QREF_DYNAMIC;
            quest_raise_dynamic_error();
            break;
        case QTYPE_KIND_OPAQUE:
        case QTYPE_KIND_BOUND_VAR:
            quest_raise_dynamic_error();
            break;
        default:
            break;
    }
    QPtrNode *found = quest_ptr_find(&g->index, d);
    if (found != NULL) return found->id - 1;

    int index = quest_tg_new_node(g, d);
    QTypeNodeKind kind = QTN_RECORD;
    size_t label_count = 0, child_count = 0;
    const char **labels = NULL;
    bool *has_payload = NULL;
    int *children = NULL;

    switch (d->kind) {
        case QTYPE_KIND_RECORD: {
            const QRecordTypeDescriptor *meta = (const QRecordTypeDescriptor *)d->extra;
            size_t n = meta ? meta->field_count : 0;
            /* Fields by name (insertion sort of their indexes) */
            size_t *by_name = (size_t *)quest_alloc(sizeof(size_t) * (n ? n : 1));
            for (size_t i = 0; i < n; ++i) {
                size_t j = i;
                while (j > 0 && strcmp(meta->fields[by_name[j - 1]].name, meta->fields[i].name) > 0) {
                    by_name[j] = by_name[j - 1];
                    --j;
                }
                by_name[j] = i;
            }
            labels = (const char **)quest_alloc(sizeof(char *) * (n ? n : 1));
            children = (int *)quest_alloc(sizeof(int) * (n ? n : 1));
            for (size_t i = 0; i < n; ++i) {
                const QRecordFieldDescriptor *f = &meta->fields[by_name[i]];
                labels[i] = quest_var_label(f->name, f->is_var);
                children[i] = quest_tg_ref(g, f->type);
            }
            kind = QTN_RECORD;
            label_count = child_count = n;
            break;
        }
        case QTYPE_KIND_TUPLE: {
            const QTupleTypeDescriptor *meta = (const QTupleTypeDescriptor *)d->extra;
            size_t n = meta ? meta->element_count : 0;
            labels = (const char **)quest_alloc(sizeof(char *) * (n ? n : 1));
            children = (int *)quest_alloc(sizeof(int) * (n ? n : 1));
            for (size_t i = 0; i < n; ++i) {
                labels[i] = quest_var_label(meta->elements[i].name, meta->elements[i].is_var);
                children[i] = quest_tg_ref(g, meta->elements[i].type);
            }
            kind = QTN_TUPLE;
            label_count = child_count = n;
            break;
        }
        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION: {
            const QVariantTypeDescriptor *meta = (const QVariantTypeDescriptor *)d->extra;
            size_t n = meta ? meta->case_count : 0;
            labels = (const char **)quest_alloc(sizeof(char *) * (n ? n : 1));
            has_payload = (bool *)quest_alloc(sizeof(bool) * (n ? n : 1));
            children = (int *)quest_alloc(sizeof(int) * (n ? n : 1));
            for (size_t i = 0; i < n; ++i) {
                const QVariantCaseDescriptor *c = &meta->cases[i];
                labels[i] = d->kind == QTYPE_KIND_VARIANT ? quest_var_label(c->name, c->is_var) : c->name;
                has_payload[i] = c->payload_type != NULL;
                if (c->payload_type != NULL) children[child_count++] = quest_tg_ref(g, c->payload_type);
            }
            kind = d->kind == QTYPE_KIND_VARIANT ? QTN_VARIANT : QTN_OPTION;
            label_count = n;
            break;
        }
        case QTYPE_KIND_ARRAY: {
            const QArrayTypeDescriptor *meta = (const QArrayTypeDescriptor *)d->extra;
            if (meta == NULL) quest_raise_dynamic_error();
            children = (int *)quest_alloc(sizeof(int));
            children[0] = quest_tg_ref(g, meta->element_type);
            kind = QTN_ARRAY;
            child_count = 1;
            break;
        }
        case QTYPE_KIND_FUN: {
            const QFunTypeDescriptor *meta = (const QFunTypeDescriptor *)d->extra;
            if (meta == NULL || meta->quantifier_count > 0) quest_raise_dynamic_error();
            size_t n = meta->param_count;
            labels = (const char **)quest_alloc(sizeof(char *) * (n ? n : 1));
            children = (int *)quest_alloc(sizeof(int) * (n + 1));
            for (size_t i = 0; i < n; ++i) {
                const QFunParamDescriptor *p = &meta->params[i];
                labels[i] = p->is_var ? "var" : p->is_out ? "out" : "";
                children[i] = quest_tg_ref(g, p->type);
            }
            children[n] = quest_tg_ref(g, meta->result_type);
            kind = QTN_FUN;
            label_count = n;
            child_count = n + 1;
            break;
        }
        case QTYPE_KIND_EXCEPTION: {
            const QExceptionTypeDescriptor *meta = (const QExceptionTypeDescriptor *)d->extra;
            children = (int *)quest_alloc(sizeof(int));
            children[0] = quest_tg_ref(g, meta != NULL ? meta->payload_type : &quest_type_Ok);
            kind = QTN_EXCEPTION;
            child_count = 1;
            break;
        }
        default:
            quest_raise_dynamic_error();
    }
    QTypeNode *node = &g->nodes[index];
    node->kind = kind;
    node->label_count = label_count;
    node->labels = labels;
    node->has_payload = has_payload;
    node->child_count = child_count;
    node->children = children;
    return index;
}

static void quest_tg_add_root(QTypeGraph *g, int ref) {
    if (g->root_count == g->root_cap) {
        size_t cap = g->root_cap ? g->root_cap * 2 : 8;
        int *roots = (int *)quest_alloc(sizeof(int) * cap);
        if (g->root_count) memcpy(roots, g->roots, sizeof(int) * g->root_count);
        g->roots = roots;
        g->root_cap = cap;
    }
    g->roots[g->root_count++] = ref;
}

static bool quest_tn_same_shape(const QTypeNode *a, const QTypeNode *b) {
    if (a->kind != b->kind || a->label_count != b->label_count || a->child_count != b->child_count) return false;
    for (size_t i = 0; i < a->label_count; ++i) {
        if (strcmp(a->labels[i], b->labels[i]) != 0) return false;
        if (a->has_payload != NULL && a->has_payload[i] != b->has_payload[i]) return false;
    }
    return true;
}

static int quest_tg_class_of(const int *cls, int ref) {
    return ref < 0 ? ref : cls[ref];
}

static void quest_tg_visit(QTypeGraph *g, int ref) {
    if (ref < 0 || g->number[g->cls[ref]] >= 0) return;
    g->number[g->cls[ref]] = (int)g->order_count;
    g->order[g->order_count++] = ref;
    const QTypeNode *node = &g->nodes[ref];
    for (size_t i = 0; i < node->child_count; ++i) quest_tg_visit(g, node->children[i]);
}

/* Merges structurally equivalent nodes (partition refinement from shapes to the coarsest bisimulation) and numbers
 * the classes in the order a depth-first walk from the roots first reaches them */
static void quest_tg_canonicalize(QTypeGraph *g) {
    size_t n = g->count;
    int *cls = (int *)quest_alloc(sizeof(int) * (n ? n : 1));
    int classes = 0;
    for (size_t i = 0; i < n; ++i) {
        cls[i] = -1;
        for (size_t j = 0; j < i; ++j) {
            if (quest_tn_same_shape(&g->nodes[i], &g->nodes[j])) { cls[i] = cls[j]; break; }
        }
        if (cls[i] < 0) cls[i] = classes++;
    }
    while (true) {
        int *next = (int *)quest_alloc(sizeof(int) * (n ? n : 1));
        int next_classes = 0;
        for (size_t i = 0; i < n; ++i) {
            next[i] = -1;
            for (size_t j = 0; j < i && next[i] < 0; ++j) {
                if (cls[j] != cls[i]) continue;
                bool same = true;
                for (size_t k = 0; k < g->nodes[i].child_count && same; ++k) {
                    same = quest_tg_class_of(cls, g->nodes[i].children[k]) ==
                           quest_tg_class_of(cls, g->nodes[j].children[k]);
                }
                if (same) next[i] = next[j];
            }
            if (next[i] < 0) next[i] = next_classes++;
        }
        if (next_classes == classes) break;
        cls = next;
        classes = next_classes;
    }
    g->cls = cls;
    g->number = (int *)quest_alloc(sizeof(int) * (classes ? classes : 1));
    for (int c = 0; c < classes; ++c) g->number[c] = -1;
    g->order = (int *)quest_alloc(sizeof(int) * (classes ? classes : 1));
    g->order_count = 0;
    for (size_t r = 0; r < g->root_count; ++r) quest_tg_visit(g, g->roots[r]);
}

static void quest_write_type_ref(QWriter *wr, const QTypeGraph *g, int ref) {
    if (ref < 0) {
        const char *name = quest_builtin_ref_names[-ref];
        quest_write_json_string(wr, name, strlen(name));
    } else {
        quest_write_int(wr, g->number[g->cls[ref]]);
    }
}

static void quest_write_type_table(QWriter *wr, const QTypeGraph *g) {
    quest_writer_put_char(wr, '[');
    for (size_t t = 0; t < g->order_count; ++t) {
        const QTypeNode *node = &g->nodes[g->order[t]];
        if (t > 0) quest_writer_put_char(wr, ',');
        quest_write_raw(wr, "{\"");
        quest_write_raw(wr, quest_type_node_names[node->kind]);
        quest_write_raw(wr, "\":");
        switch (node->kind) {
            case QTN_RECORD:
                quest_writer_put_char(wr, '{');
                for (size_t i = 0; i < node->label_count; ++i) {
                    if (i > 0) quest_writer_put_char(wr, ',');
                    quest_write_json_string(wr, node->labels[i], strlen(node->labels[i]));
                    quest_writer_put_char(wr, ':');
                    quest_write_type_ref(wr, g, node->children[i]);
                }
                quest_writer_put_char(wr, '}');
                break;
            case QTN_TUPLE:
                quest_writer_put_char(wr, '[');
                for (size_t i = 0; i < node->label_count; ++i) {
                    if (i > 0) quest_writer_put_char(wr, ',');
                    quest_writer_put_char(wr, '[');
                    quest_write_json_string(wr, node->labels[i], strlen(node->labels[i]));
                    quest_writer_put_char(wr, ',');
                    quest_write_type_ref(wr, g, node->children[i]);
                    quest_writer_put_char(wr, ']');
                }
                quest_writer_put_char(wr, ']');
                break;
            case QTN_VARIANT:
            case QTN_OPTION: {
                size_t child = 0;
                quest_writer_put_char(wr, '{');
                for (size_t i = 0; i < node->label_count; ++i) {
                    if (i > 0) quest_writer_put_char(wr, ',');
                    quest_write_json_string(wr, node->labels[i], strlen(node->labels[i]));
                    quest_writer_put_char(wr, ':');
                    if (node->has_payload[i]) {
                        quest_write_type_ref(wr, g, node->children[child++]);
                    } else {
                        quest_write_raw(wr, "null");
                    }
                }
                quest_writer_put_char(wr, '}');
                break;
            }
            case QTN_ARRAY:
            case QTN_EXCEPTION:
                quest_write_type_ref(wr, g, node->children[0]);
                break;
            case QTN_FUN:
                quest_write_raw(wr, "{\"params\":[");
                for (size_t i = 0; i < node->label_count; ++i) {
                    if (i > 0) quest_writer_put_char(wr, ',');
                    quest_writer_put_char(wr, '[');
                    quest_write_json_string(wr, node->labels[i], strlen(node->labels[i]));
                    quest_writer_put_char(wr, ',');
                    quest_write_type_ref(wr, g, node->children[i]);
                    quest_writer_put_char(wr, ']');
                }
                quest_write_raw(wr, "],\"result\":");
                quest_write_type_ref(wr, g, node->children[node->label_count]);
                quest_writer_put_char(wr, '}');
                break;
        }
        quest_writer_put_char(wr, '}');
    }
    quest_writer_put_char(wr, ']');
}

/* ------------------------------------------------------------------------- */
/* Writing: Sharing Scan (Pass 1) and Emission (Pass 2)                      */
/* ------------------------------------------------------------------------- */

/* The component values of an array (records and variants are stored inline in their own array layouts) */
static QVal quest_array_element(const QArray *arr, const QTypeDescriptor *elem_desc, int64_t i) {
    if (elem_desc != NULL && elem_desc->kind == QTYPE_KIND_STORED) {
        /* Elements stored as a type parameter: QVal forms, or values of the parameter's bound */
        elem_desc = ((const QStoredDescriptor *)elem_desc->extra)->storage;
        if (elem_desc == NULL) return arr->data[i];
    }
    if (elem_desc != NULL && elem_desc->kind == QTYPE_KIND_RECORD) {
        return (QVal){ .p = (void *)quest_record_box(((const QArrayWideRecord *)arr)->data[i]) };
    }
    if (elem_desc != NULL && elem_desc->kind == QTYPE_KIND_VARIANT) {
        return (QVal){ .p = (void *)quest_variant_box(((const QArrayWideVariant *)arr)->data[i]) };
    }
    return arr->data[i];
}

/* The case of a variant or option value, and whether it is written as its bare tag. A variant value is a
 * QVariantVal; an option value is its tag followed by the components of its case, laid out as the case's payload
 * tuple type (docs/c-representation.md), so they have no identity of their own and are never shared. Either way
 * the tag comes first. */
static const QVariantCaseDescriptor *quest_variant_case(const QTypeDescriptor *desc, const void *val, bool *bare) {
    const QVariantTypeDescriptor *meta = (const QVariantTypeDescriptor *)desc->extra;
    int64_t tag = val != NULL ? *(const int64_t *)val : -1;
    if (meta == NULL || tag < 0 || (size_t)tag >= meta->case_count) {
        quest_raise_dynamic_error();
    }
    const QVariantCaseDescriptor *c = &meta->cases[tag];
    *bare = c->payload_type == NULL || c->payload_type->kind == QTYPE_KIND_OK;
    if (!*bare && desc->kind == QTYPE_KIND_OPTION &&
        (c->payload_type->kind != QTYPE_KIND_TUPLE || c->payload_type->extra == NULL)) {
        quest_raise_dynamic_error();
    }
    return c;
}

/* The components of an option value's case */
static const char *quest_option_components(const void *opt) {
    return (const char *)opt + sizeof(int64_t);
}

/* Finds the records, tuples, and arrays reached more than once, and adds the types of dynamic values to the type
 * graph, in the order they are written */
/* A value stored as a type parameter (read from its slot in its QVal form, or as a value of the parameter's bound):
 * the value at its own type */
static const QTypeDescriptor *quest_unstore(const QTypeDescriptor *desc, QVal *val) {
    if (desc == NULL || desc->kind != QTYPE_KIND_STORED) return desc;
    const QStoredDescriptor *st = (const QStoredDescriptor *)desc->extra;
    if (st->storage != NULL) *val = quest_convert(*val, st->storage, st->type);
    return st->type;
}

static void quest_scan_value(const QTypeDescriptor *desc, QVal val, QPtrTable *table, QTypeGraph *g) {
    desc = quest_unstore(desc, &val);
    if (desc == NULL) quest_raise_dynamic_error();
    switch (desc->kind) {
        case QTYPE_KIND_INT:
        case QTYPE_KIND_REAL:
        case QTYPE_KIND_BOOL:
        case QTYPE_KIND_CHAR:
        case QTYPE_KIND_STRING:
        case QTYPE_KIND_OK:
            break;

        case QTYPE_KIND_AUTO: {
            const QAuto *a = (const QAuto *)val.p;
            if (!quest_is_dynamic_type(desc) || a == NULL || a->type_desc == NULL) quest_raise_dynamic_error();
            quest_tg_add_root(g, quest_tg_ref(g, a->type_desc));
            quest_scan_value(a->type_desc, quest_dynamic_component(a), table, g);
            break;
        }

        case QTYPE_KIND_RECORD: {
            const QRecordVal *rec = (const QRecordVal *)val.p;
            if (rec == NULL || rec->val == NULL) quest_raise_dynamic_error();
            if (quest_ptr_insert_or_inc(table, rec->val)->count > 1) return;
            const QRecordTypeDescriptor *meta = (const QRecordTypeDescriptor *)desc->extra;
            for (size_t i = 0; meta != NULL && i < meta->field_count; ++i) {
                quest_scan_value(meta->fields[i].type, quest_record_field_value(*rec, desc, i), table, g);
            }
            break;
        }

        case QTYPE_KIND_ARRAY: {
            const QArray *arr = (const QArray *)val.p;
            if (arr == NULL) quest_raise_dynamic_error();
            if (quest_ptr_insert_or_inc(table, arr)->count > 1) return;
            const QArrayTypeDescriptor *meta = (const QArrayTypeDescriptor *)desc->extra;
            const QTypeDescriptor *elem_desc = meta ? meta->element_type : NULL;
            for (int64_t i = 0; i < arr->length; ++i) {
                quest_scan_value(elem_desc, quest_array_element(arr, elem_desc, i), table, g);
            }
            break;
        }

        case QTYPE_KIND_TUPLE: {
            const QTupleTypeDescriptor *meta = (const QTupleTypeDescriptor *)desc->extra;
            if (meta == NULL || meta->element_count == 0) break;
            const void *tup = val.p;
            if (tup == NULL) quest_raise_dynamic_error();
            if (quest_ptr_insert_or_inc(table, tup)->count > 1) return;
            for (size_t i = 0; i < meta->element_count; ++i) {
                const QTupleElementDescriptor *elem = &meta->elements[i];
                quest_scan_value(elem->type, quest_slot_read(elem->type, (const char *)tup + elem->offset), table, g);
            }
            break;
        }

        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION: {
            bool bare;
            const QVariantCaseDescriptor *c = quest_variant_case(desc, val.p, &bare);
            if (bare) break;
            if (desc->kind == QTYPE_KIND_VARIANT) {
                quest_scan_value(c->payload_type, ((const QVariantVal *)val.p)->payload, table, g);
                break;
            }
            const QTupleTypeDescriptor *payload = (const QTupleTypeDescriptor *)c->payload_type->extra;
            for (size_t i = 0; i < payload->element_count; ++i) {
                const QTupleElementDescriptor *elem = &payload->elements[i];
                QVal elem_val = quest_slot_read(elem->type, quest_option_components(val.p) + elem->offset);
                quest_scan_value(elem->type, elem_val, table, g);
            }
            break;
        }

        default:
            /* Functions, exceptions, abstract types: not externable */
            quest_raise_dynamic_error();
    }
}

/* Writes the start of a record, tuple, or array: {"@ref":n} (returning true) if it was written before, or else
 * its "@id" when it is reached more than once */
static bool quest_emit_shared(const void *obj, QPtrTable *table, int *next_id, QWriter *wr, int *id) {
    *id = 0;
    QPtrNode *node = quest_ptr_find(table, obj);
    if (node == NULL || node->count <= 1) return false;
    if (node->id > 0) {
        quest_write_raw(wr, "{\"@ref\":");
        quest_write_int(wr, node->id);
        quest_writer_put_char(wr, '}');
        return true;
    }
    node->id = (*next_id)++;
    *id = node->id;
    return false;
}

static void quest_emit_value(
    const QTypeDescriptor *desc, QVal val, QPtrTable *table, const QTypeGraph *g, int *next_id, QWriter *wr
) {
    desc = quest_unstore(desc, &val);
    switch (desc->kind) {
        case QTYPE_KIND_INT:
            quest_write_int(wr, val.i);
            break;

        case QTYPE_KIND_REAL:
            quest_write_real(wr, val.r);
            break;

        case QTYPE_KIND_BOOL:
            quest_write_raw(wr, val.i ? "true" : "false");
            break;

        case QTYPE_KIND_CHAR: {
            char ch = (char)val.i;
            quest_write_json_string(wr, &ch, 1);
            break;
        }

        case QTYPE_KIND_STRING: {
            const QString *s = (const QString *)val.p;
            quest_write_json_string(wr, s && s->data ? s->data : "", s && s->data ? (size_t)s->length : 0);
            break;
        }

        case QTYPE_KIND_OK:
            quest_write_raw(wr, "null");
            break;

        case QTYPE_KIND_AUTO: {
            const QAuto *a = (const QAuto *)val.p;
            QPtrNode *type_node = quest_ptr_find(&g->index, a->type_desc);
            quest_write_raw(wr, "{\"@type\":");
            int ref = type_node != NULL ? type_node->id - 1 : quest_tg_ref((QTypeGraph *)g, a->type_desc);
            quest_write_type_ref(wr, g, ref);
            quest_write_raw(wr, ",\"@value\":");
            quest_emit_value(a->type_desc, quest_dynamic_component(a), table, g, next_id, wr);
            quest_writer_put_char(wr, '}');
            break;
        }

        case QTYPE_KIND_RECORD: {
            const QRecordVal *rec = (const QRecordVal *)val.p;
            int id;
            if (quest_emit_shared(rec->val, table, next_id, wr, &id)) break;
            quest_writer_put_char(wr, '{');
            bool first = true;
            if (id > 0) {
                quest_write_raw(wr, "\"@id\":");
                quest_write_int(wr, id);
                first = false;
            }
            const QRecordTypeDescriptor *meta = (const QRecordTypeDescriptor *)desc->extra;
            for (size_t i = 0; meta != NULL && i < meta->field_count; ++i) {
                const QRecordFieldDescriptor *f = &meta->fields[i];
                if (!first) quest_writer_put_char(wr, ',');
                first = false;
                quest_write_json_string(wr, f->name, strlen(f->name));
                quest_writer_put_char(wr, ':');
                quest_emit_value(f->type, quest_record_field_value(*rec, desc, i), table, g, next_id, wr);
            }
            quest_writer_put_char(wr, '}');
            break;
        }

        case QTYPE_KIND_ARRAY:
        case QTYPE_KIND_TUPLE: {
            const QTupleTypeDescriptor *tup_meta =
                desc->kind == QTYPE_KIND_TUPLE ? (const QTupleTypeDescriptor *)desc->extra : NULL;
            if (desc->kind == QTYPE_KIND_TUPLE && (tup_meta == NULL || tup_meta->element_count == 0)) {
                quest_write_raw(wr, "[]");
                break;
            }
            int id;
            if (quest_emit_shared(val.p, table, next_id, wr, &id)) break;
            if (id > 0) {
                quest_write_raw(wr, "{\"@id\":");
                quest_write_int(wr, id);
                quest_write_raw(wr, ",\"@items\":");
            }
            quest_writer_put_char(wr, '[');
            if (desc->kind == QTYPE_KIND_ARRAY) {
                const QArray *arr = (const QArray *)val.p;
                const QTypeDescriptor *elem_desc = ((const QArrayTypeDescriptor *)desc->extra)->element_type;
                for (int64_t i = 0; i < arr->length; ++i) {
                    if (i > 0) quest_writer_put_char(wr, ',');
                    quest_emit_value(elem_desc, quest_array_element(arr, elem_desc, i), table, g, next_id, wr);
                }
            } else {
                for (size_t i = 0; i < tup_meta->element_count; ++i) {
                    const QTupleElementDescriptor *elem = &tup_meta->elements[i];
                    if (i > 0) quest_writer_put_char(wr, ',');
                    QVal elem_val = quest_slot_read(elem->type, (const char *)val.p + elem->offset);
                    quest_emit_value(elem->type, elem_val, table, g, next_id, wr);
                }
            }
            quest_writer_put_char(wr, ']');
            if (id > 0) quest_writer_put_char(wr, '}');
            break;
        }

        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION: {
            bool bare;
            const QVariantCaseDescriptor *c = quest_variant_case(desc, val.p, &bare);
            if (bare) {
                quest_write_json_string(wr, c->name, strlen(c->name));
                break;
            }
            quest_writer_put_char(wr, '{');
            quest_write_json_string(wr, c->name, strlen(c->name));
            quest_writer_put_char(wr, ':');
            if (desc->kind == QTYPE_KIND_VARIANT) {
                quest_emit_value(c->payload_type, ((const QVariantVal *)val.p)->payload, table, g, next_id, wr);
            } else {
                const QTupleTypeDescriptor *payload = (const QTupleTypeDescriptor *)c->payload_type->extra;
                quest_writer_put_char(wr, '[');
                for (size_t i = 0; i < payload->element_count; ++i) {
                    const QTupleElementDescriptor *elem = &payload->elements[i];
                    if (i > 0) quest_writer_put_char(wr, ',');
                    QVal elem_val = quest_slot_read(elem->type, quest_option_components(val.p) + elem->offset);
                    quest_emit_value(elem->type, elem_val, table, g, next_id, wr);
                }
                quest_writer_put_char(wr, ']');
            }
            quest_writer_put_char(wr, '}');
            break;
        }

        default:
            quest_raise_dynamic_error();
    }
}

/* ------------------------------------------------------------------------- */
/* Public Serialization Interface                                            */
/* ------------------------------------------------------------------------- */

void quest_dynamic_extern(QWriter *wr, const QAuto *d) {
    if (wr == NULL || wr->is_closed || wr->file == NULL || d == NULL || d->type_desc == NULL) {
        quest_raise_dynamic_error();
    }
    QVal value = quest_dynamic_component(d);

    QPtrTable *table = (QPtrTable *)quest_alloc(sizeof(QPtrTable));
    QTypeGraph *g = (QTypeGraph *)quest_alloc(sizeof(QTypeGraph));
    memset(table, 0, sizeof(*table));
    memset(g, 0, sizeof(*g));

    int root = quest_tg_ref(g, d->type_desc);
    quest_tg_add_root(g, root);
    quest_scan_value(d->type_desc, value, table, g);
    quest_tg_canonicalize(g);

    quest_write_raw(wr, "{\"quest\":1,\"types\":");
    quest_write_type_table(wr, g);
    quest_write_raw(wr, ",\"type\":");
    quest_write_type_ref(wr, g, root);
    quest_write_raw(wr, ",\"value\":");
    int next_id = 1;
    quest_emit_value(d->type_desc, value, table, g, &next_id, wr);
    quest_writer_put_char(wr, '}');
}

/* ------------------------------------------------------------------------- */
/* Reading: Streaming JSON Parser                                            */
/* ------------------------------------------------------------------------- */

typedef enum QJsonKind {
    QJSON_NULL,
    QJSON_BOOL,
    QJSON_INT,
    QJSON_REAL,
    QJSON_STRING,
    QJSON_ARRAY,
    QJSON_OBJECT,
} QJsonKind;

typedef struct QJsonValue QJsonValue;

typedef struct QJsonKeyValue {
    const char *key;
    QJsonValue *val;
} QJsonKeyValue;

struct QJsonValue {
    QJsonKind kind;
    union {
        bool   b;
        int64_t i;
        double  r;
        struct {
            const char *str;
            size_t      len;
        } s;
        struct {
            QJsonValue **items;
            size_t       count;
        } a;
        struct {
            QJsonKeyValue *entries;
            size_t         count;
        } o;
    } u;
};

typedef struct QJsonReader {
    QReader *rd;
    int      peek;
} QJsonReader;

static int quest_json_peek(QJsonReader *jr) {
    if (jr->peek != -1) return jr->peek;
    if (jr->rd == NULL || jr->rd->is_closed) return -1;
    if (!quest_reader_more(jr->rd)) return -1;
    jr->peek = (int)quest_reader_get_char(jr->rd);
    return jr->peek;
}

static int quest_json_next(QJsonReader *jr) {
    int ch = quest_json_peek(jr);
    jr->peek = -1;
    return ch;
}

static void quest_json_skip_ws(QJsonReader *jr) {
    int ch;
    while ((ch = quest_json_peek(jr)) != -1) {
        if (ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n') {
            quest_json_next(jr);
        } else {
            break;
        }
    }
}

static QJsonValue *quest_parse_json_value(QJsonReader *jr);

static QJsonValue *quest_parse_json_string(QJsonReader *jr) {
    quest_json_next(jr); /* consume opening quote */
    size_t cap = 32;
    size_t len = 0;
    char *buf = (char *)quest_alloc_atomic(cap);

    while (1) {
        int ch = quest_json_next(jr);
        if (ch == -1) quest_raise_dynamic_error();
        if (ch == '"') break;
        if (ch == '\\') {
            int esc = quest_json_next(jr);
            if (esc == -1) quest_raise_dynamic_error();
            switch (esc) {
                case '"':  ch = '"'; break;
                case '\\': ch = '\\'; break;
                case '/':  ch = '/'; break;
                case 'b':  ch = '\b'; break;
                case 'f':  ch = '\f'; break;
                case 'n':  ch = '\n'; break;
                case 'r':  ch = '\r'; break;
                case 't':  ch = '\t'; break;
                case 'u': {
                    unsigned int hex = 0;
                    for (int i = 0; i < 4; ++i) {
                        int h = quest_json_next(jr);
                        if (h >= '0' && h <= '9') hex = (hex << 4) | (h - '0');
                        else if (h >= 'a' && h <= 'f') hex = (hex << 4) | (h - 'a' + 10);
                        else if (h >= 'A' && h <= 'F') hex = (hex << 4) | (h - 'A' + 10);
                        else quest_raise_dynamic_error();
                    }
                    if (hex <= 0x7F) {
                        ch = (int)hex;
                    } else if (hex <= 0x7FF) {
                        if (len + 2 >= cap) {
                            cap *= 2;
                            char *nb = (char *)quest_alloc_atomic(cap);
                            memcpy(nb, buf, len);
                            buf = nb;
                        }
                        buf[len++] = (char)(0xC0 | (hex >> 6));
                        buf[len++] = (char)(0x80 | (hex & 0x3F));
                        continue;
                    } else {
                        if (len + 3 >= cap) {
                            cap = cap * 2 + 4;
                            char *nb = (char *)quest_alloc_atomic(cap);
                            memcpy(nb, buf, len);
                            buf = nb;
                        }
                        buf[len++] = (char)(0xE0 | (hex >> 12));
                        buf[len++] = (char)(0x80 | ((hex >> 6) & 0x3F));
                        buf[len++] = (char)(0x80 | (hex & 0x3F));
                        continue;
                    }
                    break;
                }
                default: quest_raise_dynamic_error();
            }
        }
        if (len + 1 >= cap) {
            cap *= 2;
            char *nb = (char *)quest_alloc_atomic(cap);
            memcpy(nb, buf, len);
            buf = nb;
        }
        buf[len++] = (char)ch;
    }
    buf[len] = '\0';
    QJsonValue *val = (QJsonValue *)quest_alloc(sizeof(QJsonValue));
    val->kind = QJSON_STRING;
    val->u.s.str = buf;
    val->u.s.len = len;
    return val;
}

static QJsonValue *quest_parse_json_number(QJsonReader *jr) {
    char buf[128];
    size_t len = 0;
    bool is_real = false;

    int ch = quest_json_peek(jr);
    if (ch == '-') {
        buf[len++] = (char)quest_json_next(jr);
    }
    while ((ch = quest_json_peek(jr)) != -1) {
        if ((ch >= '0' && ch <= '9') || ch == '+' || ch == '-') {
            if (len + 1 < sizeof(buf)) buf[len++] = (char)quest_json_next(jr);
            else quest_raise_dynamic_error();
        } else if (ch == '.' || ch == 'e' || ch == 'E') {
            is_real = true;
            if (len + 1 < sizeof(buf)) buf[len++] = (char)quest_json_next(jr);
            else quest_raise_dynamic_error();
        } else {
            break;
        }
    }
    buf[len] = '\0';
    QJsonValue *val = (QJsonValue *)quest_alloc(sizeof(QJsonValue));
    char *endptr = NULL;
    if (is_real) {
        val->kind = QJSON_REAL;
        val->u.r = strtod(buf, &endptr);
    } else {
        val->kind = QJSON_INT;
        val->u.i = (int64_t)strtoll(buf, &endptr, 10);
    }
    if (endptr == buf) quest_raise_dynamic_error();
    return val;
}

static QJsonValue *quest_parse_json_object(QJsonReader *jr) {
    quest_json_next(jr); /* consume '{' */
    size_t cap = 8;
    size_t count = 0;
    QJsonKeyValue *entries = (QJsonKeyValue *)quest_alloc(sizeof(QJsonKeyValue) * cap);

    quest_json_skip_ws(jr);
    if (quest_json_peek(jr) == '}') {
        quest_json_next(jr);
        QJsonValue *val = (QJsonValue *)quest_alloc(sizeof(QJsonValue));
        val->kind = QJSON_OBJECT;
        val->u.o.entries = entries;
        val->u.o.count = 0;
        return val;
    }

    while (1) {
        quest_json_skip_ws(jr);
        if (quest_json_peek(jr) != '"') quest_raise_dynamic_error();
        QJsonValue *key_node = quest_parse_json_string(jr);
        quest_json_skip_ws(jr);
        if (quest_json_next(jr) != ':') quest_raise_dynamic_error();
        quest_json_skip_ws(jr);
        QJsonValue *val_node = quest_parse_json_value(jr);

        if (count >= cap) {
            cap *= 2;
            QJsonKeyValue *ne = (QJsonKeyValue *)quest_alloc(sizeof(QJsonKeyValue) * cap);
            memcpy(ne, entries, sizeof(QJsonKeyValue) * count);
            entries = ne;
        }
        entries[count].key = key_node->u.s.str;
        entries[count].val = val_node;
        count++;

        quest_json_skip_ws(jr);
        int sep = quest_json_next(jr);
        if (sep == '}') break;
        if (sep == ',') continue;
        quest_raise_dynamic_error();
    }

    QJsonValue *val = (QJsonValue *)quest_alloc(sizeof(QJsonValue));
    val->kind = QJSON_OBJECT;
    val->u.o.entries = entries;
    val->u.o.count = count;
    return val;
}

static QJsonValue *quest_parse_json_array(QJsonReader *jr) {
    quest_json_next(jr); /* consume '[' */
    size_t cap = 8;
    size_t count = 0;
    QJsonValue **items = (QJsonValue **)quest_alloc(sizeof(QJsonValue *) * cap);

    quest_json_skip_ws(jr);
    if (quest_json_peek(jr) == ']') {
        quest_json_next(jr);
        QJsonValue *val = (QJsonValue *)quest_alloc(sizeof(QJsonValue));
        val->kind = QJSON_ARRAY;
        val->u.a.items = items;
        val->u.a.count = 0;
        return val;
    }

    while (1) {
        quest_json_skip_ws(jr);
        QJsonValue *item = quest_parse_json_value(jr);
        if (count >= cap) {
            cap *= 2;
            QJsonValue **ni = (QJsonValue **)quest_alloc(sizeof(QJsonValue *) * cap);
            memcpy(ni, items, sizeof(QJsonValue *) * count);
            items = ni;
        }
        items[count++] = item;

        quest_json_skip_ws(jr);
        int sep = quest_json_next(jr);
        if (sep == ']') break;
        if (sep == ',') continue;
        quest_raise_dynamic_error();
    }

    QJsonValue *val = (QJsonValue *)quest_alloc(sizeof(QJsonValue));
    val->kind = QJSON_ARRAY;
    val->u.a.items = items;
    val->u.a.count = count;
    return val;
}

static QJsonValue *quest_parse_json_value(QJsonReader *jr) {
    quest_json_skip_ws(jr);
    int ch = quest_json_peek(jr);
    if (ch == -1) quest_raise_dynamic_error();

    if (ch == '{') return quest_parse_json_object(jr);
    if (ch == '[') return quest_parse_json_array(jr);
    if (ch == '"') return quest_parse_json_string(jr);
    if ((ch >= '0' && ch <= '9') || ch == '-') return quest_parse_json_number(jr);

    if (ch == 't') {
        const char *t = "true";
        for (int i = 0; t[i]; ++i) {
            if (quest_json_next(jr) != t[i]) quest_raise_dynamic_error();
        }
        QJsonValue *val = (QJsonValue *)quest_alloc(sizeof(QJsonValue));
        val->kind = QJSON_BOOL;
        val->u.b = true;
        return val;
    }
    if (ch == 'f') {
        const char *f = "false";
        for (int i = 0; f[i]; ++i) {
            if (quest_json_next(jr) != f[i]) quest_raise_dynamic_error();
        }
        QJsonValue *val = (QJsonValue *)quest_alloc(sizeof(QJsonValue));
        val->kind = QJSON_BOOL;
        val->u.b = false;
        return val;
    }
    if (ch == 'n') {
        const char *n = "null";
        for (int i = 0; n[i]; ++i) {
            if (quest_json_next(jr) != n[i]) quest_raise_dynamic_error();
        }
        QJsonValue *val = (QJsonValue *)quest_alloc(sizeof(QJsonValue));
        val->kind = QJSON_NULL;
        return val;
    }

    quest_raise_dynamic_error();
    return NULL;
}

static QJsonValue *quest_json_obj_get(const QJsonValue *obj, const char *key) {
    if (obj == NULL || obj->kind != QJSON_OBJECT) return NULL;
    for (size_t i = 0; i < obj->u.o.count; ++i) {
        if (strcmp(obj->u.o.entries[i].key, key) == 0) {
            return obj->u.o.entries[i].val;
        }
    }
    return NULL;
}

/* ------------------------------------------------------------------------- */
/* Reading: Type Tables                                                      */
/* ------------------------------------------------------------------------- */

typedef struct QTypeTable {
    size_t            count;
    QJsonValue      **nodes;
    QTypeDescriptor **descs;
} QTypeTable;

static const char *quest_label_name(const char *label, bool *is_var) {
    if (strncmp(label, "var ", 4) == 0) { *is_var = true; return label + 4; }
    if (strcmp(label, "var") == 0) { *is_var = true; return ""; }
    *is_var = false;
    return label;
}

/* The one key and value of a type node */
static QJsonKeyValue *quest_type_node_entry(QJsonValue *node) {
    if (node == NULL || node->kind != QJSON_OBJECT || node->u.o.count != 1) quest_raise_dynamic_error();
    return &node->u.o.entries[0];
}

static const QTypeDescriptor *quest_table_ref(const QTypeTable *t, const QJsonValue *ref) {
    if (ref == NULL) quest_raise_dynamic_error();
    if (ref->kind == QJSON_INT) {
        if (ref->u.i < 0 || (uint64_t)ref->u.i >= t->count) quest_raise_dynamic_error();
        return t->descs[ref->u.i];
    }
    if (ref->kind != QJSON_STRING) quest_raise_dynamic_error();
    const char *name = ref->u.s.str;
    if (strcmp(name, "Ok") == 0) return &quest_type_Ok;
    if (strcmp(name, "Bool") == 0) return &quest_type_Bool;
    if (strcmp(name, "Char") == 0) return &quest_type_Char;
    if (strcmp(name, "String") == 0) return &quest_type_String;
    if (strcmp(name, "Int") == 0) return &quest_type_Int;
    if (strcmp(name, "Real") == 0) return &quest_type_Real;
    if (strcmp(name, "Dynamic") == 0) return &quest_type_Dynamic_read;
    quest_raise_dynamic_error();
    return NULL;
}

/* Records and variants are stored inline (16 bytes, 16-aligned); every other value in 8 bytes */
static size_t quest_slot_size(const QTypeDescriptor *t) {
    return (t->kind == QTYPE_KIND_RECORD || t->kind == QTYPE_KIND_VARIANT) ? 16 : 8;
}

static void quest_fill_record_desc(const QTypeTable *t, QTypeDescriptor *desc, QJsonValue *body) {
    if (body->kind != QJSON_OBJECT) quest_raise_dynamic_error();
    size_t n = body->u.o.count;
    QRecordTypeDescriptor *meta =
        (QRecordTypeDescriptor *)quest_alloc(sizeof(QRecordTypeDescriptor) + sizeof(QRecordFieldDescriptor) * n);
    QRecordFieldDescriptor *fields = (QRecordFieldDescriptor *)meta->fields;
    /* Fields in name order (insertion sort) */
    for (size_t i = 0; i < n; ++i) {
        bool is_var;
        const char *name = quest_label_name(body->u.o.entries[i].key, &is_var);
        QRecordFieldDescriptor f = { .name = name, .type = quest_table_ref(t, body->u.o.entries[i].val),
                                     .offset = 0, .is_var = is_var };
        size_t j = i;
        while (j > 0 && strcmp(fields[j - 1].name, name) > 0) {
            fields[j] = fields[j - 1];
            --j;
        }
        fields[j] = f;
    }
    /* Fields follow the record header, as in compiled record structs */
    size_t offset = sizeof(QRecordHeader);
    size_t max_align = sizeof(void *);
    for (size_t i = 0; i < n; ++i) {
        size_t sz = quest_slot_size(fields[i].type);
        if (sz > max_align) max_align = sz;
        offset = (offset + sz - 1) & ~(sz - 1);
        fields[i].offset = offset;
        offset += sz;
    }
    meta->field_count = n;
    desc->size = (offset + max_align - 1) & ~(max_align - 1);
    desc->alignment = max_align;
    desc->extra = meta;
}

static void quest_fill_tuple_desc(const QTypeTable *t, QTypeDescriptor *desc, QJsonValue *body) {
    if (body->kind != QJSON_ARRAY) quest_raise_dynamic_error();
    size_t n = body->u.a.count;
    QTupleTypeDescriptor *meta =
        (QTupleTypeDescriptor *)quest_alloc(sizeof(QTupleTypeDescriptor) + sizeof(QTupleElementDescriptor) * n);
    QTupleElementDescriptor *elems = (QTupleElementDescriptor *)meta->elements;
    size_t offset = 0;
    size_t max_align = sizeof(void *);
    for (size_t i = 0; i < n; ++i) {
        QJsonValue *pair = body->u.a.items[i];
        if (pair->kind != QJSON_ARRAY || pair->u.a.count != 2 || pair->u.a.items[0]->kind != QJSON_STRING) {
            quest_raise_dynamic_error();
        }
        bool is_var;
        const char *name = quest_label_name(pair->u.a.items[0]->u.s.str, &is_var);
        elems[i].name = name[0] ? name : NULL;
        elems[i].is_var = is_var;
        elems[i].type = quest_table_ref(t, pair->u.a.items[1]);
        size_t sz = quest_slot_size(elems[i].type);
        if (sz > max_align) max_align = sz;
        offset = (offset + sz - 1) & ~(sz - 1);
        elems[i].offset = offset;
        offset += sz;
    }
    meta->element_count = n;
    desc->size = n ? (offset + max_align - 1) & ~(max_align - 1) : sizeof(void *);
    desc->alignment = max_align;
    desc->extra = meta;
}

static void quest_fill_variant_desc(const QTypeTable *t, QTypeDescriptor *desc, QJsonValue *body) {
    if (body->kind != QJSON_OBJECT) quest_raise_dynamic_error();
    size_t n = body->u.o.count;
    QVariantTypeDescriptor *meta =
        (QVariantTypeDescriptor *)quest_alloc(sizeof(QVariantTypeDescriptor) + sizeof(QVariantCaseDescriptor) * n);
    QVariantCaseDescriptor *cases = (QVariantCaseDescriptor *)meta->cases;
    for (size_t i = 0; i < n; ++i) {
        bool is_var = false;
        const char *label = body->u.o.entries[i].key;
        cases[i].name = desc->kind == QTYPE_KIND_VARIANT ? quest_label_name(label, &is_var) : label;
        cases[i].is_var = is_var;
        QJsonValue *ref = body->u.o.entries[i].val;
        cases[i].payload_type = ref->kind == QJSON_NULL ? NULL : quest_table_ref(t, ref);
        cases[i].tag_index = (int64_t)i;
        /* An option case's components are a tuple type, stored in place in the option value */
        if (desc->kind == QTYPE_KIND_OPTION && cases[i].payload_type != NULL &&
            cases[i].payload_type->kind != QTYPE_KIND_TUPLE) {
            quest_raise_dynamic_error();
        }
    }
    meta->case_count = n;
    desc->size = desc->kind == QTYPE_KIND_OPTION ? sizeof(int64_t) : sizeof(QVariantVal);
    desc->extra = meta;
}

static void quest_fill_fun_desc(const QTypeTable *t, QTypeDescriptor *desc, QJsonValue *body) {
    QJsonValue *params = quest_json_obj_get(body, "params");
    QJsonValue *result = quest_json_obj_get(body, "result");
    if (params == NULL || params->kind != QJSON_ARRAY || result == NULL) quest_raise_dynamic_error();
    size_t n = params->u.a.count;
    QFunTypeDescriptor *meta =
        (QFunTypeDescriptor *)quest_alloc(sizeof(QFunTypeDescriptor) + sizeof(QFunParamDescriptor) * n);
    QFunParamDescriptor *ps = (QFunParamDescriptor *)meta->params;
    for (size_t i = 0; i < n; ++i) {
        QJsonValue *pair = params->u.a.items[i];
        if (pair->kind != QJSON_ARRAY || pair->u.a.count != 2 || pair->u.a.items[0]->kind != QJSON_STRING) {
            quest_raise_dynamic_error();
        }
        const char *mode = pair->u.a.items[0]->u.s.str;
        if (strcmp(mode, "") != 0 && strcmp(mode, "var") != 0 && strcmp(mode, "out") != 0) {
            quest_raise_dynamic_error();
        }
        ps[i].type = quest_table_ref(t, pair->u.a.items[1]);
        ps[i].is_var = strcmp(mode, "var") == 0;
        ps[i].is_out = strcmp(mode, "out") == 0;
    }
    meta->param_count = n;
    meta->result_type = quest_table_ref(t, result);
    meta->adapt = NULL;
    meta->invoke = NULL;
    meta->quantifier_count = 0;
    meta->quantifier_bounds = NULL;
    desc->size = sizeof(QClosure *);
    desc->extra = meta;
}

/* Builds a descriptor for every node of a type table: first each node's kind (which determines how a component of
 * that type is stored), then the nodes' contents, which may refer to any node */
static QTypeTable *quest_read_type_table(QJsonValue *types) {
    if (types == NULL || types->kind != QJSON_ARRAY) quest_raise_dynamic_error();
    QTypeTable *t = (QTypeTable *)quest_alloc(sizeof(QTypeTable));
    t->count = types->u.a.count;
    t->nodes = types->u.a.items;
    t->descs = (QTypeDescriptor **)quest_alloc(sizeof(QTypeDescriptor *) * (t->count ? t->count : 1));
    static const QTypeKind kinds[Q_TYPE_NODE_KIND_COUNT] = {
        QTYPE_KIND_RECORD, QTYPE_KIND_TUPLE, QTYPE_KIND_VARIANT, QTYPE_KIND_OPTION,
        QTYPE_KIND_ARRAY, QTYPE_KIND_FUN, QTYPE_KIND_EXCEPTION,
    };
    static const char *const display_names[Q_TYPE_NODE_KIND_COUNT] = {
        "Record", "Tuple", "Variant", "Option", "Array", "Fun", "Exception",
    };
    for (size_t i = 0; i < t->count; ++i) {
        const char *key = quest_type_node_entry(t->nodes[i])->key;
        int k = 0;
        while (k < Q_TYPE_NODE_KIND_COUNT && strcmp(quest_type_node_names[k], key) != 0) ++k;
        if (k == Q_TYPE_NODE_KIND_COUNT) quest_raise_dynamic_error();
        QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor));
        desc->kind = kinds[k];
        desc->name = display_names[k];
        desc->size = sizeof(void *);
        desc->alignment = sizeof(void *);
        desc->is_subtype = quest_is_subtype;
        desc->extra = NULL;
        t->descs[i] = desc;
    }
    for (size_t i = 0; i < t->count; ++i) {
        QTypeDescriptor *desc = t->descs[i];
        QJsonValue *body = quest_type_node_entry(t->nodes[i])->val;
        switch (desc->kind) {
            case QTYPE_KIND_RECORD: quest_fill_record_desc(t, desc, body); break;
            case QTYPE_KIND_TUPLE: quest_fill_tuple_desc(t, desc, body); break;
            case QTYPE_KIND_VARIANT:
            case QTYPE_KIND_OPTION: quest_fill_variant_desc(t, desc, body); break;
            case QTYPE_KIND_FUN: quest_fill_fun_desc(t, desc, body); break;
            case QTYPE_KIND_ARRAY: {
                QArrayTypeDescriptor *meta = (QArrayTypeDescriptor *)quest_alloc(sizeof(QArrayTypeDescriptor));
                meta->element_type = quest_table_ref(t, body);
                desc->extra = meta;
                break;
            }
            default: {
                QExceptionTypeDescriptor *meta =
                    (QExceptionTypeDescriptor *)quest_alloc(sizeof(QExceptionTypeDescriptor));
                meta->payload_type = quest_table_ref(t, body);
                desc->extra = meta;
                break;
            }
        }
    }
    return t;
}

/* ------------------------------------------------------------------------- */
/* Reading: Values                                                           */
/* ------------------------------------------------------------------------- */

typedef struct QIdEntry {
    int64_t                id;
    void                  *ptr;
    const void            *dict;    /* for records */
    struct QIdEntry       *next;
} QIdEntry;

typedef struct QReadContext {
    const QTypeTable *types;
    QIdEntry         *ids;
} QReadContext;

static QIdEntry *quest_id_find(QReadContext *cx, int64_t id) {
    for (QIdEntry *cur = cx->ids; cur != NULL; cur = cur->next) {
        if (cur->id == id) return cur;
    }
    return NULL;
}

/* Records the object of an "@id" before its contents are read, so that references inside it can reach it */
static void quest_id_insert(QReadContext *cx, const QJsonValue *id_val, void *ptr, const void *dict) {
    if (id_val->kind != QJSON_INT || quest_id_find(cx, id_val->u.i) != NULL) quest_raise_dynamic_error();
    QIdEntry *entry = (QIdEntry *)quest_alloc(sizeof(QIdEntry));
    entry->id = id_val->u.i;
    entry->ptr = ptr;
    entry->dict = dict;
    entry->next = cx->ids;
    cx->ids = entry;
}

/* The object of {"@ref":n}, or NULL if node is not a reference */
static QIdEntry *quest_read_ref(QReadContext *cx, const QJsonValue *node) {
    QJsonValue *ref = quest_json_obj_get(node, "@ref");
    if (ref == NULL) return NULL;
    if (node->u.o.count != 1 || ref->kind != QJSON_INT) quest_raise_dynamic_error();
    QIdEntry *entry = quest_id_find(cx, ref->u.i);
    if (entry == NULL) quest_raise_dynamic_error();
    return entry;
}

static void *quest_alloc_array(const QTypeDescriptor *elem_t, int64_t len) {
    size_t elem_size = (elem_t->kind == QTYPE_KIND_RECORD) ? sizeof(QRecordVal)
                     : (elem_t->kind == QTYPE_KIND_VARIANT) ? sizeof(QVariantVal) : sizeof(QVal);
    QArray *arr = (QArray *)quest_alloc(sizeof(int64_t) + elem_size * (size_t)(len > 0 ? len : 1));
    arr->length = len;
    return arr;
}

static QVal quest_read_value(QReadContext *cx, QJsonValue *node, const QTypeDescriptor *desc);

static QAuto *quest_read_dynamic(QReadContext *cx, QJsonValue *type_ref, QJsonValue *value) {
    const QTypeDescriptor *witness = quest_table_ref(cx->types, type_ref);
    QVal *component = (QVal *)quest_alloc(sizeof(QVal));
    *component = quest_read_value(cx, value, witness);
    return quest_auto_new(witness, (QVal){ .p = component });
}

static QVal quest_read_value(QReadContext *cx, QJsonValue *node, const QTypeDescriptor *desc) {
    if (node == NULL || desc == NULL) quest_raise_dynamic_error();

    switch (desc->kind) {
        case QTYPE_KIND_INT:
            if (node->kind != QJSON_INT) quest_raise_dynamic_error();
            return (QVal){ .i = node->u.i };

        case QTYPE_KIND_REAL:
            if (node->kind == QJSON_REAL) return (QVal){ .r = node->u.r };
            if (node->kind == QJSON_INT) return (QVal){ .r = (double)node->u.i };
            if (node->kind == QJSON_STRING) {
                if (strcmp(node->u.s.str, "Infinity") == 0) return (QVal){ .r = INFINITY };
                if (strcmp(node->u.s.str, "-Infinity") == 0) return (QVal){ .r = -INFINITY };
            }
            quest_raise_dynamic_error();
            break;

        case QTYPE_KIND_BOOL:
            if (node->kind != QJSON_BOOL) quest_raise_dynamic_error();
            return (QVal){ .i = node->u.b ? 1 : 0 };

        case QTYPE_KIND_CHAR:
            if (node->kind != QJSON_STRING || node->u.s.len != 1) quest_raise_dynamic_error();
            return (QVal){ .i = (unsigned char)node->u.s.str[0] };

        case QTYPE_KIND_STRING:
            if (node->kind != QJSON_STRING) quest_raise_dynamic_error();
            return (QVal){ .p = (void *)quest_string_new(node->u.s.str, (int64_t)node->u.s.len) };

        case QTYPE_KIND_OK:
            if (node->kind != QJSON_NULL) quest_raise_dynamic_error();
            return Q_OK_VAL;

        case QTYPE_KIND_AUTO: {
            if (node->kind != QJSON_OBJECT || node->u.o.count != 2) quest_raise_dynamic_error();
            QJsonValue *t_node = quest_json_obj_get(node, "@type");
            QJsonValue *v_node = quest_json_obj_get(node, "@value");
            if (t_node == NULL || v_node == NULL) quest_raise_dynamic_error();
            return (QVal){ .p = (void *)quest_read_dynamic(cx, t_node, v_node) };
        }

        case QTYPE_KIND_RECORD: {
            if (node->kind != QJSON_OBJECT) quest_raise_dynamic_error();
            QIdEntry *shared = quest_read_ref(cx, node);
            if (shared != NULL) {
                QRecordVal rec = { .val = shared->ptr, .dict = shared->dict };
                return (QVal){ .p = quest_record_box(rec) };
            }
            const QRecordTypeDescriptor *meta = (const QRecordTypeDescriptor *)desc->extra;
            QJsonValue *id_val = quest_json_obj_get(node, "@id");
            if (node->u.o.count != meta->field_count + (id_val != NULL ? 1 : 0)) quest_raise_dynamic_error();
            void *buf = quest_alloc(desc->size > 0 ? desc->size : sizeof(void *));
            ((QRecordHeader *)buf)->descriptor = desc;
            const void *dict = quest_record_dict(desc, desc);
            if (id_val != NULL) quest_id_insert(cx, id_val, buf, dict);
            for (size_t i = 0; i < meta->field_count; ++i) {
                const QRecordFieldDescriptor *f = &meta->fields[i];
                QJsonValue *f_node = quest_json_obj_get(node, f->name);
                if (f_node == NULL) quest_raise_dynamic_error();
                quest_slot_write(f->type, (char *)buf + f->offset, quest_read_value(cx, f_node, f->type));
            }
            QRecordVal rec = { .val = buf, .dict = dict };
            return (QVal){ .p = quest_record_box(rec) };
        }

        case QTYPE_KIND_ARRAY:
        case QTYPE_KIND_TUPLE: {
            QJsonValue *items = node;
            QJsonValue *id_val = NULL;
            if (node->kind == QJSON_OBJECT) {
                QIdEntry *shared = quest_read_ref(cx, node);
                if (shared != NULL) return (QVal){ .p = shared->ptr };
                id_val = quest_json_obj_get(node, "@id");
                items = quest_json_obj_get(node, "@items");
                if (id_val == NULL || items == NULL || node->u.o.count != 2) quest_raise_dynamic_error();
            }
            if (items->kind != QJSON_ARRAY) quest_raise_dynamic_error();
            if (desc->kind == QTYPE_KIND_ARRAY) {
                const QTypeDescriptor *elem_t = ((const QArrayTypeDescriptor *)desc->extra)->element_type;
                int64_t len = (int64_t)items->u.a.count;
                QArray *arr = (QArray *)quest_alloc_array(elem_t, len);
                if (id_val != NULL) quest_id_insert(cx, id_val, arr, NULL);
                for (int64_t i = 0; i < len; ++i) {
                    QVal elem = quest_read_value(cx, items->u.a.items[i], elem_t);
                    if (elem_t->kind == QTYPE_KIND_RECORD) {
                        ((QArrayWideRecord *)arr)->data[i] = *(const QRecordVal *)elem.p;
                    } else if (elem_t->kind == QTYPE_KIND_VARIANT) {
                        ((QArrayWideVariant *)arr)->data[i] = *(const QVariantVal *)elem.p;
                    } else {
                        arr->data[i] = elem;
                    }
                }
                return (QVal){ .p = (void *)arr };
            }
            const QTupleTypeDescriptor *meta = (const QTupleTypeDescriptor *)desc->extra;
            size_t n = meta != NULL ? meta->element_count : 0;
            if (items->u.a.count != n) quest_raise_dynamic_error();
            void *tup = quest_alloc(desc->size > 0 ? desc->size : sizeof(void *));
            if (id_val != NULL) quest_id_insert(cx, id_val, tup, NULL);
            for (size_t i = 0; i < n; ++i) {
                const QTupleElementDescriptor *elem = &meta->elements[i];
                quest_slot_write(elem->type, (char *)tup + elem->offset, quest_read_value(cx, items->u.a.items[i], elem->type));
            }
            return (QVal){ .p = tup };
        }

        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION: {
            const QVariantTypeDescriptor *meta = (const QVariantTypeDescriptor *)desc->extra;
            const char *tag;
            QJsonValue *payload = NULL;
            if (node->kind == QJSON_STRING) {
                tag = node->u.s.str;
            } else if (node->kind == QJSON_OBJECT && node->u.o.count == 1) {
                tag = node->u.o.entries[0].key;
                payload = node->u.o.entries[0].val;
            } else {
                quest_raise_dynamic_error();
                return Q_OK_VAL;
            }
            for (size_t i = 0; i < meta->case_count; ++i) {
                const QVariantCaseDescriptor *c = &meta->cases[i];
                if (strcmp(c->name, tag) != 0) continue;
                bool bare = c->payload_type == NULL || c->payload_type->kind == QTYPE_KIND_OK;
                if (bare != (payload == NULL)) quest_raise_dynamic_error();
                if (desc->kind == QTYPE_KIND_VARIANT) {
                    QVariantVal v = {
                        .tag = c->tag_index,
                        .payload = bare ? Q_OK_VAL : quest_read_value(cx, payload, c->payload_type),
                    };
                    return (QVal){ .p = quest_variant_box(v) };
                }
                /* An option: its tag, then its case's components in place, in a block large enough for any case */
                size_t size = 0;
                for (size_t j = 0; j < meta->case_count; ++j) {
                    const QTypeDescriptor *p = meta->cases[j].payload_type;
                    if (p != NULL && p->kind == QTYPE_KIND_TUPLE && p->size > size) size = p->size;
                }
                char *opt = (char *)quest_alloc(sizeof(int64_t) + size);
                *(int64_t *)opt = c->tag_index;
                if (!bare) {
                    const QTupleTypeDescriptor *comps = (const QTupleTypeDescriptor *)c->payload_type->extra;
                    size_t n = comps != NULL ? comps->element_count : 0;
                    if (payload->kind != QJSON_ARRAY || payload->u.a.count != n) quest_raise_dynamic_error();
                    for (size_t k = 0; k < n; ++k) {
                        const QTupleElementDescriptor *elem = &comps->elements[k];
                        QVal elem_val = quest_read_value(cx, payload->u.a.items[k], elem->type);
                        quest_slot_write(elem->type, opt + sizeof(int64_t) + elem->offset, elem_val);
                    }
                }
                return (QVal){ .p = opt };
            }
            quest_raise_dynamic_error();
            break;
        }

        default:
            /* Functions and exceptions are never written */
            quest_raise_dynamic_error();
    }
    return Q_OK_VAL;
}

/* ------------------------------------------------------------------------- */
/* Public Deserialization Interface                                          */
/* ------------------------------------------------------------------------- */

QAuto *quest_dynamic_intern(QReader *rd) {
    if (rd == NULL || rd->is_closed) {
        quest_raise_dynamic_error();
    }

    QJsonReader jr;
    jr.rd = rd;
    jr.peek = -1;

    QJsonValue *root = quest_parse_json_value(&jr);
    if (jr.peek != -1) {
        rd->peek_char = jr.peek;
    }

    if (root == NULL || root->kind != QJSON_OBJECT || root->u.o.count != 4) quest_raise_dynamic_error();
    QJsonValue *version = quest_json_obj_get(root, "quest");
    QJsonValue *type_ref = quest_json_obj_get(root, "type");
    QJsonValue *value = quest_json_obj_get(root, "value");
    if (version == NULL || version->kind != QJSON_INT || version->u.i != Q_FORMAT_VERSION || type_ref == NULL ||
        value == NULL) {
        quest_raise_dynamic_error();
    }
    QReadContext cx = { .types = quest_read_type_table(quest_json_obj_get(root, "types")), .ids = NULL };
    return quest_read_dynamic(&cx, type_ref, value);
}
