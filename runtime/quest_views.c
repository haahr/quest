/*
 * Quest C Runtime: Records, Proxies, and Views
 *
 * What lets a value be used at a supertype (docs/c-representation.md): record
 * offset tables and the dict of a record value (§5.2); proxies, views of
 * tuples and options at a supertype (§5.8); options as values and conversion
 * between layouts (quest_convert); layout equivalence; descriptor templates,
 * filled in with type arguments at run time (§6.4.5), and view maps (§5.1);
 * and dynamic adaptation of records and variants.
 */

/* The POSIX functions -std=c99 hides on Linux (glibc) */
#if defined(__linux__) && !defined(_GNU_SOURCE)
#define _GNU_SOURCE
#endif

#include "quest_runtime_internal.h"

/* ------------------------------------------------------------------------- */
/* Record Offset Tables                                                      */
/* ------------------------------------------------------------------------- */

/* An offset table lets code that knows a record only by a record type, its
 * view, find the fields of a payload laid out as another record type, its
 * layout: entry i is the byte offset in the payload of the view's i-th field in
 * name order (record descriptors list their fields in name order). All tables
 * live in one map keyed by (view, layout), pre-populated with the static tables
 * of compiled code and completed on demand from the two descriptors. Keys are
 * descriptor pointers; two descriptors of one type merely give two equal
 * tables. */

typedef struct QRecordDictEntry {
    const QTypeDescriptor *view;
    const QTypeDescriptor *layout;
    const void            *dict;
} QRecordDictEntry;

static QRecordDictEntry *quest_record_dicts = NULL;  /* open addressing; capacity is a power of two */
static size_t            quest_record_dicts_capacity = 0;
static size_t            quest_record_dicts_count = 0;

static size_t quest_record_dict_hash(const QTypeDescriptor *view, const QTypeDescriptor *layout) {
    uint64_t h = (uint64_t)(uintptr_t)view * 0x9E3779B97F4A7C15ULL;
    h ^= (uint64_t)(uintptr_t)layout + 0x7F4A7C159E3779B9ULL + (h << 6) + (h >> 2);
    return (size_t)(h ^ (h >> 29));
}

static QRecordDictEntry *quest_record_dict_slot(const QTypeDescriptor *view, const QTypeDescriptor *layout) {
    size_t mask = quest_record_dicts_capacity - 1;
    for (size_t i = quest_record_dict_hash(view, layout) & mask; ; i = (i + 1) & mask) {
        QRecordDictEntry *e = &quest_record_dicts[i];
        if (e->view == NULL || (e->view == view && e->layout == layout)) return e;
    }
}

static void quest_record_dicts_insert(const QTypeDescriptor *view, const QTypeDescriptor *layout, const void *dict) {
    if (2 * (quest_record_dicts_count + 1) > quest_record_dicts_capacity) {
        QRecordDictEntry *old = quest_record_dicts;
        size_t old_capacity = quest_record_dicts_capacity;
        quest_record_dicts_capacity = old_capacity ? 2 * old_capacity : 64;
        quest_record_dicts = (QRecordDictEntry *)quest_alloc_sized(sizeof(QRecordDictEntry) * quest_record_dicts_capacity, &quest_layout_record_dict_entries);
        memset(quest_record_dicts, 0, sizeof(QRecordDictEntry) * quest_record_dicts_capacity);
        for (size_t i = 0; i < old_capacity; ++i) {
            if (old[i].view != NULL) *quest_record_dict_slot(old[i].view, old[i].layout) = old[i];
        }
    }
    QRecordDictEntry *e = quest_record_dict_slot(view, layout);
    if (e->view == NULL) {
        /* Each slot's own barrier: the entry may lie across two cards */
        quest_barrier_slot(&e->view);
        e->view = view;
        quest_barrier_slot(&e->layout);
        e->layout = layout;
        quest_barrier_slot(&e->dict);
        e->dict = dict;
        quest_record_dicts_count++;
    }
}

/* True if a field stored at type `stored` must be converted to be read at type
 * `viewed`: it is stored at a proper subtype, or in a different layout (one of
 * them stores a type parameter generically) */
static bool quest_stored_type_differs(const QTypeDescriptor *stored, const QTypeDescriptor *viewed) {
    if (stored == viewed || stored == NULL || viewed == NULL) return false;
    switch (quest_stored_type(viewed)->kind) {
        case QTYPE_KIND_RECORD:
        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION:
        case QTYPE_KIND_TUPLE:
        case QTYPE_KIND_FUN:
            if (!(quest_is_subtype(stored, viewed) && quest_is_subtype(viewed, stored))) return true;
            break;
        default:
            break;
    }
    return !quest_slot_layout_equivalent(stored, viewed);
}

static const void *quest_build_record_dict(const QTypeDescriptor *view, const QTypeDescriptor *layout) {
    if (view->kind != QTYPE_KIND_RECORD || layout->kind != QTYPE_KIND_RECORD) return NULL;
    const QRecordTypeDescriptor *v_meta = (const QRecordTypeDescriptor *)view->extra;
    const QRecordTypeDescriptor *l_meta = (const QRecordTypeDescriptor *)layout->extra;
    size_t n = v_meta != NULL ? v_meta->field_count : 0;
    size_t slots = n > 0 ? n : 1;
    /* Offsets, then the stored types pointer (see QRecordStoredTypes) */
    size_t *dict = (size_t *)quest_alloc_words(slots + 1);
    const QTypeDescriptor **stored_types = NULL;
    dict[0] = 0;
    for (size_t j = 0; j < n; ++j) {
        const char *name = v_meta->fields[j].name;
        const QRecordFieldDescriptor *lf = NULL;
        for (size_t i = 0; l_meta != NULL && i < l_meta->field_count; ++i) {
            if (strcmp(l_meta->fields[i].name, name) == 0) {
                lf = &l_meta->fields[i];
                break;
            }
        }
        if (lf == NULL) return NULL;
        dict[j] = lf->offset;
        if (quest_stored_type_differs(lf->type, v_meta->fields[j].type)) {
            /* A var field is updated through the view, so it must be stored as
             * the view stores it */
            if (v_meta->fields[j].is_var) quest_layout_conversion_error(layout, view);
            if (stored_types == NULL) {
                stored_types = (const QTypeDescriptor **)quest_alloc_sized(sizeof(const QTypeDescriptor *) * n,
                                                                           &quest_layout_pointers);
                memset((void *)stored_types, 0, sizeof(const QTypeDescriptor *) * n);
            }
            stored_types[j] = lf->type;
        }
    }
    quest_barrier(dict);    /* old by now if the stored types' allocation collected */
    *(QRecordStoredTypes *)(dict + slots) = (QRecordStoredTypes)stored_types;
    return dict;
}

/* ------------------------------------------------------------------------- */
/* Proxies                                                                   */
/* ------------------------------------------------------------------------- */

static const QTypeDescriptor *quest_stored_representation(const QTypeDescriptor *d);
static const QTypeDescriptor *quest_concrete_representation(const QTypeDescriptor *d);

static bool quest_proxies_agree(const QTypeDescriptor *from, const QTypeDescriptor *to);

/* The tuple or option descriptor a descriptor stands for (looking through
 * stored and abstract types) */
static const QTypeDescriptor *quest_proxied_type(const QTypeDescriptor *d) {
    return quest_concrete_representation(quest_stored_representation(d));
}

void *quest_make_proxy(const void *v, const QTypeDescriptor *from, const QTypeDescriptor *to) {
    if (v == NULL) return (void *)v;
    const void *orig = v;
    if (quest_is_proxy(v)) {
        orig = quest_proxy_of(v)->orig;
        from = quest_proxy_of(v)->stored;
    }
    from = quest_proxied_type(from);
    to = quest_proxied_type(to);
    if (from == to || (quest_layout_equivalent(from, to) && quest_proxies_agree(from, to))) return (void *)orig;
    QProxy *proxy = (QProxy *)quest_alloc(sizeof(QProxy), &quest_layout_proxy);
    proxy->orig = orig;
    proxy->stored = from;
    proxy->view = to;
    if (to->kind == QTYPE_KIND_OPTION) {
        const QVariantTypeDescriptor *f_meta = (const QVariantTypeDescriptor *)from->extra;
        const QVariantTypeDescriptor *t_meta = (const QVariantTypeDescriptor *)to->extra;
        size_t n = f_meta != NULL ? f_meta->case_count : 0;
        int64_t *tags = (int64_t *)quest_alloc_sized(sizeof(int64_t) * (n > 0 ? n : 1), &quest_layout_ints);
        for (size_t i = 0; i < n; ++i) {
            tags[i] = -1;
            for (size_t j = 0; t_meta != NULL && j < t_meta->case_count; ++j) {
                if (strcmp(t_meta->cases[j].name, f_meta->cases[i].name) == 0) {
                    tags[i] = (int64_t)j;
                    break;
                }
            }
        }
        quest_barrier(proxy);
        proxy->tags = tags;
    }
    return (void *)((uintptr_t)proxy + QUEST_PROXY_TAG);
}

/* An immutable element of a proxy's original, converted, is kept in the proxy's
 * cache (its slot never changes, and conversions make immutable values): a
 * record is viewed, a nested tuple proxied, a closure adapted once */
static QVal quest_proxy_cached(const void *p, size_t i, size_t n, QVal v, const QTypeDescriptor *from,
                               const QTypeDescriptor *to) {
    if (from == to) return v;
    QProxy *proxy = (QProxy *)quest_proxy_of(p);
    if (proxy->cache == NULL) {
        QVal *cache = (QVal *)quest_alloc_sized(sizeof(QVal) * n + n, &quest_layout_proxy_cache);
        quest_barrier(proxy);
        proxy->cache = cache;
        proxy->cached = (uint8_t *)(cache + n);
    }
    if (!proxy->cached[i]) {
        QVal converted = quest_convert(v, from, to);
        quest_barrier_slot(&proxy->cache[i]);
        proxy->cache[i] = converted;
        proxy->cached[i] = 1;
    }
    return proxy->cache[i];
}

QVal quest_proxy_element(const void *p, size_t i) {
    const QProxy *proxy = quest_proxy_of(p);
    const QTupleTypeDescriptor *view = (const QTupleTypeDescriptor *)proxy->view->extra;
    const QTupleElementDescriptor *fe = &((const QTupleTypeDescriptor *)proxy->stored->extra)->elements[i];
    const QTupleElementDescriptor *te = &view->elements[i];
    QVal v = quest_slot_read((const char *)proxy->orig + fe->offset);
    if (fe->type == te->type) return v;
    if (te->is_var) return quest_convert(v, fe->type, te->type);
    return quest_proxy_cached(p, i, view->element_count, v, fe->type, te->type);
}

void *quest_proxy_slot(const void *p, size_t i) {
    const QProxy *proxy = quest_proxy_of(p);
    const QTupleElementDescriptor *fe = &((const QTupleTypeDescriptor *)proxy->stored->extra)->elements[i];
    const QTupleElementDescriptor *te = &((const QTupleTypeDescriptor *)proxy->view->extra)->elements[i];
    /* A var element has the same type in both, but may be laid out differently
     * (a bounded type parameter's) */
    if (!quest_slot_layout_equivalent(fe->type, te->type)) quest_layout_conversion_error(proxy->stored, proxy->view);
    return (char *)proxy->orig + fe->offset;
}

void quest_proxy_store(const void *p, size_t i, QVal v) {
    const QProxy *proxy = quest_proxy_of(p);
    const QTupleElementDescriptor *fe = &((const QTupleTypeDescriptor *)proxy->stored->extra)->elements[i];
    const QTupleElementDescriptor *te = &((const QTupleTypeDescriptor *)proxy->view->extra)->elements[i];
    QVal stored = fe->type == te->type ? v : quest_convert(v, te->type, fe->type);
    quest_barrier_slot((char *)proxy->orig + fe->offset);
    quest_slot_write((char *)proxy->orig + fe->offset, stored);
}

int64_t quest_proxy_tag(const void *p) {
    const QProxy *proxy = quest_proxy_of(p);
    return proxy->tags[*(const int64_t *)proxy->orig];
}

/* An option's case payload follows its tag; a payload that is not a tuple is
 * one slot */
#define Q_OPTION_PAYLOAD_OFFSET sizeof(int64_t)

static QVal quest_payload_element(const char *payload, const QTypeDescriptor *t, size_t i) {
    if (t != NULL && t->kind == QTYPE_KIND_TUPLE) {
        return quest_slot_read(payload + ((const QTupleTypeDescriptor *)t->extra)->elements[i].offset);
    }
    return quest_slot_read(payload);
}

static const QTypeDescriptor *quest_payload_element_type(const QTypeDescriptor *t, size_t i) {
    if (t != NULL && t->kind == QTYPE_KIND_TUPLE) return ((const QTupleTypeDescriptor *)t->extra)->elements[i].type;
    return t;
}

QVal quest_proxy_option_element(const void *p, size_t i) {
    const QProxy *proxy = quest_proxy_of(p);
    int64_t tag = *(const int64_t *)proxy->orig;
    const QVariantCaseDescriptor *fc = &((const QVariantTypeDescriptor *)proxy->stored->extra)->cases[tag];
    const QVariantCaseDescriptor *tc = &((const QVariantTypeDescriptor *)proxy->view->extra)->cases[proxy->tags[tag]];
    QVal v = quest_payload_element((const char *)proxy->orig + Q_OPTION_PAYLOAD_OFFSET, fc->payload_type, i);
    /* The original's case never changes: its payload's elements are cached as a
     * tuple's are */
    size_t n = tc->payload_type != NULL && tc->payload_type->kind == QTYPE_KIND_TUPLE
        ? ((const QTupleTypeDescriptor *)tc->payload_type->extra)->element_count : 1;
    if (tc->payload_type != NULL && tc->payload_type->kind == QTYPE_KIND_TUPLE &&
        ((const QTupleTypeDescriptor *)tc->payload_type->extra)->elements[i].is_var) {
        return quest_convert(v, quest_payload_element_type(fc->payload_type, i),
                             quest_payload_element_type(tc->payload_type, i));
    }
    return quest_proxy_cached(p, i, n, v, quest_payload_element_type(fc->payload_type, i),
                              quest_payload_element_type(tc->payload_type, i));
}

/* The payload of case `tag` of option orig (an original, of type `stored`),
 * viewed at the payload of case `view_tag` of type `view` (the same case) */
static void *quest_option_payload_viewed(const void *orig, const QTypeDescriptor *stored, int64_t tag,
                                         const QTypeDescriptor *view, int64_t view_tag) {
    const QVariantCaseDescriptor *fc = &((const QVariantTypeDescriptor *)quest_proxied_type(stored)->extra)->cases[tag];
    const QVariantCaseDescriptor *tc =
        &((const QVariantTypeDescriptor *)quest_proxied_type(view)->extra)->cases[view_tag];
    QVal payload = { .p = (void *)((const char *)orig + Q_OPTION_PAYLOAD_OFFSET) };
    return quest_convert(payload, fc->payload_type, tc->payload_type).p;
}

void *quest_proxy_option_payload(const void *p) {
    const QProxy *proxy = quest_proxy_of(p);
    int64_t tag = *(const int64_t *)proxy->orig;
    return quest_option_payload_viewed(proxy->orig, proxy->stored, tag, proxy->view, proxy->tags[tag]);
}

void *quest_view_option_payload(const void *opt, const QViewMap *m) {
    const void *orig = quest_unproxy(opt);
    const QTypeDescriptor *stored = quest_is_proxy(opt) ? quest_proxy_of(opt)->stored : m->actual;
    return quest_option_payload_viewed(orig, stored, *(const int64_t *)orig, m->bound, quest_view_option_tag(opt, m));
}

/* Whether a value of type d (a tuple or option) may be a proxy, as the compiler
 * decides it for the type (may_be_proxied in repr/layout.py), or less often:
 * a tuple one of whose components may change view, an option of two or more
 * cases or one of whose payloads' components may. A component may change view
 * when it is view-sensitive or may hold a proxy (a tuple, or an option with a
 * payload, whose subtypes' values may be proxies where its own are not). A
 * component is view-sensitive when values of its subtypes may be represented
 * differently at its type: a record, variant, or auto value, a value stored as
 * a type parameter, a function whose signature mentions a view-sensitive type,
 * or a tuple or option that may be a proxy. (Abstract types, which the compiler
 * counts as view-sensitive, are not here: the runtime cannot tell a module's
 * abstract types from external C types, which are not.) Only values of such
 * types are made proxies at run time; others are copied. */
#define Q_PROXIED_TRAIL_MAX 64

static bool quest_view_sensitive_rec(const QTypeDescriptor *d, const QTypeDescriptor **trail, size_t depth);

/* Whether a component of type d may hold a proxy though values of d itself may
 * not be: a tuple, or an option with a payload (holds_proxies in
 * repr/layout.py) */
static bool quest_holds_proxies(const QTypeDescriptor *d) {
    if (d == NULL) return false;
    if (d->kind == QTYPE_KIND_TUPLE) return true;
    if (d->kind != QTYPE_KIND_OPTION) return false;
    const QVariantTypeDescriptor *meta = (const QVariantTypeDescriptor *)d->extra;
    for (size_t i = 0; meta != NULL && i < meta->case_count; ++i) {
        if (meta->cases[i].payload_type != NULL) return true;
    }
    return false;
}

static bool quest_component_changes_view(const QTypeDescriptor *d, const QTypeDescriptor **trail, size_t depth) {
    return quest_holds_proxies(d) || quest_view_sensitive_rec(d, trail, depth);
}

static bool quest_may_be_proxied_rec(const QTypeDescriptor *d, const QTypeDescriptor **trail, size_t depth) {
    if (d == NULL || depth >= Q_PROXIED_TRAIL_MAX) return false;
    for (size_t i = 0; i < depth; ++i) {
        if (trail[i] == d) return false;
    }
    trail[depth] = d;
    if (d->kind == QTYPE_KIND_TUPLE) {
        const QTupleTypeDescriptor *meta = (const QTupleTypeDescriptor *)d->extra;
        for (size_t i = 0; meta != NULL && i < meta->element_count; ++i) {
            if (quest_component_changes_view(meta->elements[i].type, trail, depth + 1)) return true;
        }
        return false;
    }
    if (d->kind == QTYPE_KIND_OPTION) {
        const QVariantTypeDescriptor *meta = (const QVariantTypeDescriptor *)d->extra;
        if (meta == NULL) return false;
        if (meta->case_count >= 2) return true;
        for (size_t i = 0; i < meta->case_count; ++i) {
            const QTypeDescriptor *p = meta->cases[i].payload_type;
            if (p != NULL && p->kind == QTYPE_KIND_TUPLE && quest_may_be_proxied_rec(p, trail, depth + 1)) return true;
        }
    }
    return false;
}

static bool quest_view_sensitive_rec(const QTypeDescriptor *d, const QTypeDescriptor **trail, size_t depth) {
    if (d == NULL || depth >= Q_PROXIED_TRAIL_MAX) return false;
    switch (d->kind) {
        case QTYPE_KIND_RECORD:
        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_AUTO:
        case QTYPE_KIND_STORED:
        case QTYPE_KIND_BOUND_VAR:
        case QTYPE_KIND_HOLE:
            return true;
        case QTYPE_KIND_TUPLE:
        case QTYPE_KIND_OPTION:
            return quest_may_be_proxied_rec(d, trail, depth);
        case QTYPE_KIND_FUN: {
            for (size_t i = 0; i < depth; ++i) {
                if (trail[i] == d) return false;
            }
            trail[depth] = d;
            const QFunTypeDescriptor *meta = (const QFunTypeDescriptor *)d->extra;
            if (meta == NULL) return false;
            if (meta->quantifier_count > 0) return true;
            for (size_t i = 0; i < meta->param_count; ++i) {
                if (quest_view_sensitive_rec(meta->params[i].type, trail, depth + 1)) return true;
            }
            return quest_view_sensitive_rec(meta->result_type, trail, depth + 1);
        }
        default:
            return false;
    }
}

static bool quest_may_be_proxied(const QTypeDescriptor *d) {
    const QTypeDescriptor *trail[Q_PROXIED_TRAIL_MAX];
    return quest_may_be_proxied_rec(d, trail, 0);
}

static const QTypeDescriptor *quest_stored_representation(const QTypeDescriptor *d);

/* Whether a tuple or option laid out as `from` can be used as `to` as it is, as
 * far as proxies go: no component, at any depth through tuples and options, of
 * a type whose values may be proxies is used at a type whose values never are
 * (which code reads directly). The value itself may be used at such a type: its
 * original serves, as no component of the type changes view. Recursive
 * descriptors are compared coinductively. */
static bool quest_proxies_agree_rec(const QTypeDescriptor *from, const QTypeDescriptor *to, QSubtypePair *trail,
                                    size_t depth) {
    from = quest_stored_representation(from);
    to = quest_stored_representation(to);
    if (from == to || from == NULL || to == NULL || depth >= Q_PROXIED_TRAIL_MAX) return true;
    if (to->kind != QTYPE_KIND_TUPLE && to->kind != QTYPE_KIND_OPTION) return true;
    if (from->kind != to->kind) return true;
    for (size_t i = 0; i < depth; ++i) {
        if (trail[i].sub == from && trail[i].super_type == to) return true;
    }
    if (depth > 0 && !quest_may_be_proxied(to) && quest_may_be_proxied(from)) return false;
    trail[depth] = (QSubtypePair){ from, to };
    if (to->kind == QTYPE_KIND_TUPLE) {
        const QTupleTypeDescriptor *f_meta = (const QTupleTypeDescriptor *)from->extra;
        const QTupleTypeDescriptor *t_meta = (const QTupleTypeDescriptor *)to->extra;
        for (size_t i = 0; f_meta != NULL && t_meta != NULL && i < f_meta->element_count && i < t_meta->element_count; ++i) {
            if (!quest_proxies_agree_rec(f_meta->elements[i].type, t_meta->elements[i].type, trail, depth + 1)) return false;
        }
        return true;
    }
    const QVariantTypeDescriptor *f_meta = (const QVariantTypeDescriptor *)from->extra;
    const QVariantTypeDescriptor *t_meta = (const QVariantTypeDescriptor *)to->extra;
    for (size_t i = 0; f_meta != NULL && t_meta != NULL && i < f_meta->case_count; ++i) {
        const QVariantCaseDescriptor *fc = &f_meta->cases[i];
        for (size_t j = 0; j < t_meta->case_count; ++j) {
            const QVariantCaseDescriptor *tc = &t_meta->cases[j];
            if (fc->name == NULL || tc->name == NULL || strcmp(fc->name, tc->name) != 0) continue;
            if (fc->payload_type != NULL && tc->payload_type != NULL &&
                !quest_proxies_agree_rec(fc->payload_type, tc->payload_type, trail, depth + 1)) {
                return false;
            }
        }
    }
    return true;
}

static bool quest_proxies_agree(const QTypeDescriptor *from, const QTypeDescriptor *to) {
    QSubtypePair trail[Q_PROXIED_TRAIL_MAX];
    return quest_proxies_agree_rec(from, to, trail, 0);
}

/* A copy of v (a tuple or option of type `from`, a proxy or not) laid out as
 * `to`, which values are never proxies of: its components converted. A copy
 * does not share updates of var components, so a tuple with any is a fatal
 * error. */
static QVal quest_copy_viewed(QVal v, const QTypeDescriptor *from, const QTypeDescriptor *to) {
    char *dst = (char *)quest_alloc_sized(to->size > 0 ? to->size : sizeof(void *), &quest_layout_words);
    if (to->kind == QTYPE_KIND_TUPLE) {
        const QTupleTypeDescriptor *f_meta = (const QTupleTypeDescriptor *)from->extra;
        const QTupleTypeDescriptor *t_meta = (const QTupleTypeDescriptor *)to->extra;
        for (size_t i = 0; f_meta != NULL && i < t_meta->element_count && i < f_meta->element_count; ++i) {
            if (t_meta->elements[i].is_var) quest_layout_conversion_error(from, to);
            /* The conversion may allocate, and so collect and leave the copy
             * old: its value first, then the barrier and the store */
            QVal e = quest_convert(quest_tuple_element(v.p, from, i), f_meta->elements[i].type,
                                   t_meta->elements[i].type);
            quest_barrier(dst);
            quest_slot_write(dst + t_meta->elements[i].offset, e);
        }
        return (QVal){ .p = dst };
    }
    const QVariantTypeDescriptor *f_meta = (const QVariantTypeDescriptor *)from->extra;
    const QVariantTypeDescriptor *t_meta = (const QVariantTypeDescriptor *)to->extra;
    int64_t tag = quest_option_tag(v.p);
    if (f_meta == NULL || t_meta == NULL || tag < 0 || (size_t)tag >= f_meta->case_count) return v;
    const QVariantCaseDescriptor *fc = &f_meta->cases[tag];
    const QVariantCaseDescriptor *tc = NULL;
    for (size_t j = 0; j < t_meta->case_count; ++j) {
        if (strcmp(t_meta->cases[j].name, fc->name) == 0) {
            tc = &t_meta->cases[j];
            break;
        }
    }
    if (tc == NULL) quest_raise_dynamic_error();
    *(int64_t *)dst = tc->tag_index;
    if (fc->payload_type != NULL && tc->payload_type != NULL) {
        size_t n = 1;
        if (tc->payload_type->kind == QTYPE_KIND_TUPLE) n = ((const QTupleTypeDescriptor *)tc->payload_type->extra)->element_count;
        for (size_t i = 0; i < n; ++i) {
            const char *slot = dst + Q_OPTION_PAYLOAD_OFFSET;
            if (tc->payload_type->kind == QTYPE_KIND_TUPLE) {
                slot += ((const QTupleTypeDescriptor *)tc->payload_type->extra)->elements[i].offset;
            }
            QVal e = quest_convert(quest_option_element(v.p, from, i), quest_payload_element_type(fc->payload_type, i),
                                   quest_payload_element_type(tc->payload_type, i));
            quest_barrier(dst);
            quest_slot_write((void *)slot, e);
        }
    }
    return (QVal){ .p = dst };
}

QVal quest_tuple_element(const void *tup, const QTypeDescriptor *t, size_t i) {
    if (quest_is_proxy(tup)) return quest_proxy_element(tup, i);
    return quest_slot_read((const char *)tup + ((const QTupleTypeDescriptor *)t->extra)->elements[i].offset);
}

int64_t quest_option_tag(const void *opt) {
    return quest_is_proxy(opt) ? quest_proxy_tag(opt) : *(const int64_t *)opt;
}

QVal quest_option_element(const void *opt, const QTypeDescriptor *t, size_t i) {
    if (quest_is_proxy(opt)) return quest_proxy_option_element(opt, i);
    const QVariantCaseDescriptor *c = &((const QVariantTypeDescriptor *)t->extra)->cases[*(const int64_t *)opt];
    return quest_payload_element((const char *)opt + Q_OPTION_PAYLOAD_OFFSET, c->payload_type, i);
}

/* ============================================================================
 * Options as values (docs/extensions.md, Options as Values), and conversion
 * between layouts (quest_convert)
 *
 * is compares options of a case without components by their case, and those of
 * a single-word option type's case with a component (an option type with one
 * case with components, which has one, not var) by their component; an
 * abstract type's values as its representation's.
 *
 * Then quest_convert, which converts a value from the view and layout of one
 * descriptor to another's (its comment in the header has the cases), with
 * quest_convert_auto, its case for auto values.
 * ========================================================================= */

const QTypeDescriptor *quest_identity_type(const QTypeDescriptor *t) {
    for (int depth = 0; t != NULL && depth < 64; ++depth) {
        if (t->kind == QTYPE_KIND_STORED) {
            t = ((const QStoredDescriptor *)t->extra)->type;
        } else if (t->kind == QTYPE_KIND_OPAQUE) {
            const QTypeDescriptor *rep = quest_abstract_type_rep(t);
            if (rep == NULL) return t;
            t = rep;
        } else {
            return t;
        }
    }
    return t;
}

static size_t quest_case_component_count(const QVariantCaseDescriptor *c) {
    return c->payload_type == NULL ? 0 : ((const QTupleTypeDescriptor *)c->payload_type->extra)->element_count;
}

/* The tag of option type t's single-word case, or -1 if t is not single-word */
static int64_t quest_single_word_case(const QTypeDescriptor *t) {
    const QVariantTypeDescriptor *v = (const QVariantTypeDescriptor *)t->extra;
    int64_t found = -1;
    for (size_t i = 0; i < v->case_count; ++i) {
        size_t n = quest_case_component_count(&v->cases[i]);
        if (n == 0) continue;
        if (found >= 0 || n != 1) return -1;
        if (((const QTupleTypeDescriptor *)v->cases[i].payload_type->extra)->elements[0].is_var) return -1;
        found = (int64_t)i;
    }
    return found;
}

bool quest_option_is(const QTypeDescriptor *t, const void *a, const void *b) {
    if (quest_unproxy(a) == quest_unproxy(b)) return true;
    t = quest_identity_type(t);
    if (t == NULL || t->kind != QTYPE_KIND_OPTION || a == NULL || b == NULL) return false;
    int64_t tag = quest_option_tag(a);
    if (tag != quest_option_tag(b)) return false;
    const QVariantCaseDescriptor *c = &((const QVariantTypeDescriptor *)t->extra)->cases[tag];
    if (quest_case_component_count(c) == 0) return true;
    if (quest_single_word_case(t) != tag) return false;
    const QTypeDescriptor *component = ((const QTupleTypeDescriptor *)c->payload_type->extra)->elements[0].type;
    return quest_val_is(component, quest_option_element(a, t, 0), quest_option_element(b, t, 0));
}

/* An option's identity hash at its type t (quest_identity_type's), as
 * quest_option_is compares options */
uint64_t quest_option_identity_hash(const QTypeDescriptor *t, const void *p) {
    if (p == NULL) return quest_hash_mix64(0);
    int64_t tag = quest_option_tag(p);
    const QVariantCaseDescriptor *c = &((const QVariantTypeDescriptor *)t->extra)->cases[tag];
    if (quest_case_component_count(c) == 0) return quest_hash_mix64(0x9E3779B97F4A7C15ULL ^ (uint64_t)tag);
    if (quest_single_word_case(t) == tag) {
        const QTypeDescriptor *component = ((const QTupleTypeDescriptor *)c->payload_type->extra)->elements[0].type;
        return quest_hash_mix64((uint64_t)tag ^ quest_identity_hash(component, quest_option_element(p, t, 0)));
    }
    return quest_hash_mix64((uint64_t)(uintptr_t)quest_unproxy(p));
}

/* Reads and writes an auto value's component in its payload (see
 * QAutoComponentDescriptor) */
static QVal quest_auto_component_read(const QAutoComponentDescriptor *c, const char *payload) {
    return quest_slot_read(payload + c->offset);
}

static void quest_auto_component_write(const QAutoComponentDescriptor *c, char *payload, QVal v) {
    quest_slot_write(payload + c->offset, v);
}

/* Re-stores an auto value's components in the layout of auto type `to` (keeping
 * its type component) */
static QVal quest_convert_auto(QVal v, const QTypeDescriptor *from, const QTypeDescriptor *to) {
    const QAuto *a = (const QAuto *)v.p;
    const QAutoTypeDescriptor *f_meta = (const QAutoTypeDescriptor *)from->extra;
    const QAutoTypeDescriptor *t_meta = (const QAutoTypeDescriptor *)to->extra;
    if (a == NULL || f_meta == NULL || t_meta == NULL) return v;
    char *payload = (char *)quest_alloc_sized(t_meta->payload_size > 0 ? t_meta->payload_size : sizeof(QVal),
                                              &quest_layout_words);
    for (size_t i = 0; i < t_meta->component_count && i < f_meta->component_count; ++i) {
        const QAutoComponentDescriptor *fc = &f_meta->components[i];
        const QAutoComponentDescriptor *tc = &t_meta->components[i];
        if (tc->is_var) quest_layout_conversion_error(from, to);
        /* A component of the type component's type is a value of that type
         * whatever its storage */
        QVal c = quest_auto_component_read(fc, (const char *)a->payload.p);
        if (fc->type->kind != QTYPE_KIND_BOUND_VAR) c = quest_convert(c, fc->type, tc->type);
        quest_auto_component_write(tc, payload, c);
    }
    return (QVal){ .p = quest_auto_new(a->type_desc, (QVal){ .p = payload }) };
}

void quest_layout_conversion_error(const QTypeDescriptor *from, const QTypeDescriptor *to) {
    (void)from;
    fprintf(stderr,
            "Runtime error: a value used at type %s was laid out by generic code, and converting it would copy "
            "mutable data\n",
            to != NULL && to->name != NULL ? to->name : "?");
    quest_fail_at(NULL);
}

/* How a value stored as a type parameter is held: as a value of its own type
 * (in its QVal form, or in the representation of a bounded parameter's bound,
 * at its own view), or for a module's abstract type, viewed at its bound */
static const QTypeDescriptor *quest_stored_representation(const QTypeDescriptor *d) {
    if (d == NULL || d->kind != QTYPE_KIND_STORED) return d;
    const QStoredDescriptor *st = (const QStoredDescriptor *)d->extra;
    return st->storage != NULL && st->viewed ? st->storage : st->type;
}

/* A module's abstract type is held, as a QVal or as its bound, as its
 * representation is (docs/dynamic.md §3.5) */
static const QTypeDescriptor *quest_concrete_representation(const QTypeDescriptor *d) {
    if (d != NULL && d->kind == QTYPE_KIND_OPAQUE) {
        const QTypeDescriptor *rep = quest_abstract_type_rep(d);
        if (rep != NULL) return quest_stored_representation(rep);
    }
    return d;
}

QVal quest_convert(QVal v, const QTypeDescriptor *from, const QTypeDescriptor *to) {
    if (from == NULL || to == NULL) return v;
    from = quest_concrete_representation(quest_stored_representation(from));
    to = quest_concrete_representation(quest_stored_representation(to));
    /* A record is viewed at `to` from its own layout, whatever view it had:
     * code that knows a value only as of a type parameter's bound may view it
     * at the bound or at its own type */
    if (to->kind == QTYPE_KIND_RECORD && from->kind == QTYPE_KIND_RECORD && v.p != NULL) {
        QRecordVal viewed = quest_record_view(*(const QRecordVal *)v.p, to);
        if (viewed.dict == NULL) quest_raise_dynamic_error();
        if (viewed.dict == ((const QRecordVal *)v.p)->dict) return v;
        return (QVal){ .p = (void *)quest_record_box(viewed) };
    }
    if (from == to || from->kind != to->kind) return v;
    switch (to->kind) {
        case QTYPE_KIND_VARIANT:
            if (v.p == NULL) return v;
            return (QVal){ .p = (void *)quest_variant_box(quest_variant_adapt(from, to, v)) };
        case QTYPE_KIND_OPTION:
        case QTYPE_KIND_TUPLE:
            /* Viewed at `to` through a proxy, not copied (the original's
             * identity and var components are kept), where values of `to` may
             * be proxies */
            if (v.p == NULL || to->extra == NULL) return v;
            if (!quest_is_proxy(v.p) && quest_layout_equivalent(from, to) && quest_proxies_agree(from, to)) return v;
            if (quest_may_be_proxied(to)) return (QVal){ .p = quest_make_proxy(v.p, from, to) };
            if (quest_is_proxy(v.p) && quest_layout_equivalent(quest_proxy_of(v.p)->stored, to)) {
                return (QVal){ .p = (void *)quest_proxy_of(v.p)->orig };
            }
            return quest_copy_viewed(v, from, to);
        case QTYPE_KIND_FUN: {
            const QFunTypeDescriptor *meta = (const QFunTypeDescriptor *)to->extra;
            if (v.p == NULL || meta == NULL || meta->adapt == NULL) return v;
            /* equal types in the same layout: nothing to adapt */
            if (quest_is_subtype(to, from) && quest_layout_equivalent(from, to)) return v;
            return (QVal){ .p = meta->adapt((const QClosure *)v.p, from, to) };
        }
        case QTYPE_KIND_AUTO:
            if (v.p == NULL || quest_layout_equivalent(from, to)) return v;
            return quest_convert_auto(v, from, to);
        case QTYPE_KIND_ARRAY:
        case QTYPE_KIND_EXCEPTION:
            if (v.p != NULL && !quest_layout_equivalent(from, to)) quest_layout_conversion_error(from, to);
            return v;
        default:
            return v;
    }
}

/* ------------------------------------------------------------------------- */
/* Layout Equivalence                                                        */
/* ------------------------------------------------------------------------- */

/* Descriptors of the same type describe the same layout unless one stores a
 * type parameter generically (as a QVal, QTYPE_KIND_STORED) where the other
 * stores the type argument's own representation. Every slot is one word holding
 * a value's QVal form (records and variants boxed), so the two agree in memory;
 * in registers (function parameters and results) only integers and pointers
 * agree. A value stored as a bounded type parameter is its type argument's own,
 * in the bound's representation, which is the type argument's too; a module's
 * abstract type's is viewed at its bound, which agrees only with the bound's
 * own layout. Recursive descriptors are compared coinductively. */

#define Q_EQUIV_TRAIL_MAX 64
static Q_THREAD_LOCAL QSubtypePair quest_equiv_trail[Q_EQUIV_TRAIL_MAX];
static Q_THREAD_LOCAL size_t quest_equiv_trail_len = 0;

static bool quest_layout_equiv_rec(const QTypeDescriptor *a, const QTypeDescriptor *b);

/* Where a value is held: in an aggregate slot (a word holding its QVal form),
 * in a register (a function's parameter or result), or in the cell a var or out
 * parameter points to (natively, a variable of the value's representation, but
 * a record or variant boxed, as in a slot) */
typedef enum QPlace { QPLACE_SLOT, QPLACE_REGISTER, QPLACE_CELL } QPlace;

/* Whether a place holding a value stored generically (`st`) holds it as `other`
 * does. Stored in the representation of a type parameter's bound, a value is
 * held as its type argument's own (which has that representation too); a
 * module's abstract type's is viewed at its bound. */
static bool quest_stored_equivalent(const QStoredDescriptor *st, const QTypeDescriptor *other, QPlace place) {
    if (st->storage != NULL) return quest_layout_equiv_rec(st->viewed ? st->storage : st->type, other);
    switch (other->kind) {
        case QTYPE_KIND_REAL:
        case QTYPE_KIND_RECORD:  /* boxed in slots and cells */
        case QTYPE_KIND_VARIANT:
            return place != QPLACE_REGISTER;
        case QTYPE_KIND_BOOL:
        case QTYPE_KIND_CHAR:
        case QTYPE_KIND_OK:
            return place == QPLACE_SLOT;
        case QTYPE_KIND_INT:
        case QTYPE_KIND_STRING:
        case QTYPE_KIND_OPAQUE:
        case QTYPE_KIND_BOUND_VAR:
            return true;
        default:
            return quest_layout_equiv_rec(st->type, other);
    }
}

static bool quest_place_equivalent(const QTypeDescriptor *a, const QTypeDescriptor *b, QPlace place) {
    if (a == b) return true;
    if (a == NULL || b == NULL) return false;
    bool a_stored = a->kind == QTYPE_KIND_STORED, b_stored = b->kind == QTYPE_KIND_STORED;
    if (a_stored && b_stored) {
        const QStoredDescriptor *sa = (const QStoredDescriptor *)a->extra;
        const QStoredDescriptor *sb = (const QStoredDescriptor *)b->extra;
        if ((sa->storage == NULL) != (sb->storage == NULL) || sa->viewed != sb->viewed) return false;
        return sa->viewed ? quest_layout_equiv_rec(sa->storage, sb->storage)
                          : quest_layout_equiv_rec(sa->type, sb->type);
    }
    if (a_stored) return quest_stored_equivalent((const QStoredDescriptor *)a->extra, b, place);
    if (b_stored) return quest_stored_equivalent((const QStoredDescriptor *)b->extra, a, place);
    return quest_layout_equiv_rec(a, b);
}

bool quest_slot_layout_equivalent(const QTypeDescriptor *a, const QTypeDescriptor *b) {
    return quest_place_equivalent(a, b, QPLACE_SLOT);
}

static bool quest_layout_equiv_rec(const QTypeDescriptor *a, const QTypeDescriptor *b) {
    if (a == b) return true;
    if (a == NULL || b == NULL) return false;
    if (a->kind == QTYPE_KIND_STORED || b->kind == QTYPE_KIND_STORED) return quest_place_equivalent(a, b, QPLACE_SLOT);
    if (a->kind != b->kind) return false;
    for (size_t i = 0; i < quest_equiv_trail_len; ++i) {
        if (quest_equiv_trail[i].sub == a && quest_equiv_trail[i].super_type == b) return true;
    }
    if (quest_equiv_trail_len >= Q_EQUIV_TRAIL_MAX) return false;
    quest_equiv_trail[quest_equiv_trail_len++] = (QSubtypePair){ a, b };

    bool result = true;
    switch (a->kind) {
        case QTYPE_KIND_TUPLE: {
            /* A longer tuple may be used as its prefix */
            const QTupleTypeDescriptor *sa = (const QTupleTypeDescriptor *)a->extra;
            const QTupleTypeDescriptor *sb = (const QTupleTypeDescriptor *)b->extra;
            size_t na = sa != NULL ? sa->element_count : 0, nb = sb != NULL ? sb->element_count : 0;
            result = na >= nb;
            for (size_t i = 0; result && i < nb; ++i) {
                result = sa->elements[i].offset == sb->elements[i].offset &&
                         quest_place_equivalent(sa->elements[i].type, sb->elements[i].type, QPLACE_SLOT);
            }
            break;
        }
        case QTYPE_KIND_RECORD: {
            /* Record values carry their payload's layout; their offset tables
             * depend on the view's field types */
            const QRecordTypeDescriptor *ra = (const QRecordTypeDescriptor *)a->extra;
            const QRecordTypeDescriptor *rb = (const QRecordTypeDescriptor *)b->extra;
            size_t na = ra != NULL ? ra->field_count : 0, nb = rb != NULL ? rb->field_count : 0;
            result = na == nb;
            for (size_t i = 0; result && i < nb; ++i) {
                result = strcmp(ra->fields[i].name, rb->fields[i].name) == 0 &&
                         ra->fields[i].is_var == rb->fields[i].is_var &&
                         quest_place_equivalent(ra->fields[i].type, rb->fields[i].type, QPLACE_SLOT);
            }
            break;
        }
        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION: {
            const QVariantTypeDescriptor *va = (const QVariantTypeDescriptor *)a->extra;
            const QVariantTypeDescriptor *vb = (const QVariantTypeDescriptor *)b->extra;
            size_t na = va != NULL ? va->case_count : 0, nb = vb != NULL ? vb->case_count : 0;
            /* An option whose cases are a prefix of another's may be used as
             * it */
            result = a->kind == QTYPE_KIND_OPTION ? na <= nb : na == nb;
            for (size_t i = 0; result && i < na; ++i) {
                const QVariantCaseDescriptor *ca = &va->cases[i], *cb = &vb->cases[i];
                result = strcmp(ca->name, cb->name) == 0 && ca->tag_index == cb->tag_index &&
                         (ca->payload_type == NULL) == (cb->payload_type == NULL) &&
                         (ca->payload_type == NULL || quest_place_equivalent(ca->payload_type, cb->payload_type, QPLACE_SLOT));
            }
            break;
        }
        case QTYPE_KIND_ARRAY: {
            const QArrayTypeDescriptor *ea = (const QArrayTypeDescriptor *)a->extra;
            const QArrayTypeDescriptor *eb = (const QArrayTypeDescriptor *)b->extra;
            result = ea != NULL && eb != NULL && quest_place_equivalent(ea->element_type, eb->element_type, QPLACE_SLOT);
            break;
        }
        case QTYPE_KIND_FUN: {
            const QFunTypeDescriptor *fa = (const QFunTypeDescriptor *)a->extra;
            const QFunTypeDescriptor *fb = (const QFunTypeDescriptor *)b->extra;
            result = fa != NULL && fb != NULL && fa->param_count == fb->param_count &&
                     fa->quantifier_count == fb->quantifier_count;
            for (size_t i = 0; result && i < fb->param_count; ++i) {
                const QFunParamDescriptor *pa = &fa->params[i], *pb = &fb->params[i];
                /* var and out parameters are pointers to cells */
                result = pa->is_var == pb->is_var && pa->is_out == pb->is_out &&
                         quest_place_equivalent(pa->type, pb->type,
                                                pa->is_var || pa->is_out ? QPLACE_CELL : QPLACE_REGISTER);
            }
            if (result) result = quest_place_equivalent(fa->result_type, fb->result_type, QPLACE_REGISTER);
            break;
        }
        case QTYPE_KIND_AUTO: {
            const QAutoTypeDescriptor *aa = (const QAutoTypeDescriptor *)a->extra;
            const QAutoTypeDescriptor *ab = (const QAutoTypeDescriptor *)b->extra;
            result = aa != NULL && ab != NULL && aa->component_count >= ab->component_count;
            for (size_t i = 0; result && i < ab->component_count; ++i) {
                const QAutoComponentDescriptor *ca = &aa->components[i], *cb = &ab->components[i];
                result = ca->offset == cb->offset && quest_place_equivalent(ca->type, cb->type, QPLACE_SLOT);
            }
            break;
        }
        case QTYPE_KIND_EXCEPTION: {
            const QExceptionTypeDescriptor *xa = (const QExceptionTypeDescriptor *)a->extra;
            const QExceptionTypeDescriptor *xb = (const QExceptionTypeDescriptor *)b->extra;
            result = xa != NULL && xb != NULL && quest_place_equivalent(xa->payload_type, xb->payload_type, QPLACE_SLOT);
            break;
        }
        default:
            result = true;
            break;
    }
    quest_equiv_trail_len--;
    return result;
}

bool quest_layout_equivalent(const QTypeDescriptor *a, const QTypeDescriptor *b) {
    return quest_place_equivalent(a, b, QPLACE_SLOT);
}

/* How a parameter or result of type d is passed: integers and pointers alike,
 * other scalars, records, and variants each their own way (Ok parameters are
 * passed as QVals, and Ok results not at all) */
typedef enum QPassingClass { QPASS_WORD, QPASS_REAL, QPASS_BOOL, QPASS_CHAR, QPASS_RECORD, QPASS_VARIANT, QPASS_VOID } QPassingClass;

static QPassingClass quest_passing_class(const QTypeDescriptor *d, bool is_result) {
    if (d == NULL) return is_result ? QPASS_VOID : QPASS_WORD;
    if (d->kind == QTYPE_KIND_STORED) {
        const QStoredDescriptor *st = (const QStoredDescriptor *)d->extra;
        return st->storage != NULL ? quest_passing_class(st->storage, is_result) : QPASS_WORD;
    }
    switch (d->kind) {
        case QTYPE_KIND_REAL: return QPASS_REAL;
        case QTYPE_KIND_BOOL: return QPASS_BOOL;
        case QTYPE_KIND_CHAR: return QPASS_CHAR;
        case QTYPE_KIND_RECORD: return QPASS_RECORD;
        case QTYPE_KIND_VARIANT: return QPASS_VARIANT;
        case QTYPE_KIND_OK: return is_result ? QPASS_VOID : QPASS_WORD;
        default: return QPASS_WORD;
    }
}

bool quest_fun_signature_equivalent(const QTypeDescriptor *from, const QTypeDescriptor *to) {
    if (from == to) return true;
    const QFunTypeDescriptor *f = (const QFunTypeDescriptor *)from->extra;
    const QFunTypeDescriptor *t = (const QFunTypeDescriptor *)to->extra;
    if (f == NULL || t == NULL || f->param_count != t->param_count || f->quantifier_count != t->quantifier_count) {
        return false;
    }
    for (size_t i = 0; i < t->param_count; ++i) {
        if (t->params[i].is_var || t->params[i].is_out) continue;
        if (quest_passing_class(f->params[i].type, false) != quest_passing_class(t->params[i].type, false)) return false;
    }
    return quest_passing_class(f->result_type, true) == quest_passing_class(t->result_type, true);
}

/* ------------------------------------------------------------------------- */
/* Descriptor Templates                                                      */
/* ------------------------------------------------------------------------- */

/* The nodes of a template reachable from its root, each with its instance (NULL
 * until made) and whether it reaches a hole (nodes that do not are their own
 * instances) */
typedef struct QInstNode {
    const QTypeDescriptor *tmpl;
    QTypeDescriptor       *inst;
    bool                   has_hole;
} QInstNode;

typedef struct QInstWork {
    QInstNode *nodes;
    size_t     count;
    size_t     capacity;
} QInstWork;

static QInstNode *quest_inst_find(QInstWork *w, const QTypeDescriptor *d) {
    for (size_t i = 0; i < w->count; ++i) {
        if (w->nodes[i].tmpl == d) return &w->nodes[i];
    }
    return NULL;
}

/* Calls f on each descriptor that d refers to */
static void quest_desc_children(const QTypeDescriptor *d, void (*f)(void *cx, const QTypeDescriptor *c), void *cx) {
    if (d == NULL || d->extra == NULL) return;
    switch (d->kind) {
        case QTYPE_KIND_TUPLE: {
            const QTupleTypeDescriptor *m = (const QTupleTypeDescriptor *)d->extra;
            for (size_t i = 0; i < m->element_count; ++i) f(cx, m->elements[i].type);
            break;
        }
        case QTYPE_KIND_RECORD: {
            const QRecordTypeDescriptor *m = (const QRecordTypeDescriptor *)d->extra;
            for (size_t i = 0; i < m->field_count; ++i) f(cx, m->fields[i].type);
            break;
        }
        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION: {
            const QVariantTypeDescriptor *m = (const QVariantTypeDescriptor *)d->extra;
            for (size_t i = 0; i < m->case_count; ++i) f(cx, m->cases[i].payload_type);
            break;
        }
        case QTYPE_KIND_ARRAY:
            f(cx, ((const QArrayTypeDescriptor *)d->extra)->element_type);
            break;
        case QTYPE_KIND_FUN: {
            const QFunTypeDescriptor *m = (const QFunTypeDescriptor *)d->extra;
            for (size_t i = 0; i < m->param_count; ++i) f(cx, m->params[i].type);
            f(cx, m->result_type);
            for (size_t i = 0; m->quantifier_bounds != NULL && i < m->quantifier_count; ++i) f(cx, m->quantifier_bounds[i]);
            break;
        }
        case QTYPE_KIND_AUTO: {
            const QAutoTypeDescriptor *m = (const QAutoTypeDescriptor *)d->extra;
            f(cx, m->bound);
            for (size_t i = 0; i < m->component_count; ++i) {
                f(cx, m->components[i].type);
            }
            break;
        }
        case QTYPE_KIND_EXCEPTION:
            f(cx, ((const QExceptionTypeDescriptor *)d->extra)->payload_type);
            break;
        case QTYPE_KIND_OPAQUE: {
            const QOpaqueTypeDescriptor *m = (const QOpaqueTypeDescriptor *)d->extra;
            for (size_t i = 0; i < m->arg_count; ++i) f(cx, m->args[i]);
            break;
        }
        case QTYPE_KIND_HOLE:
            f(cx, ((const QHoleDescriptor *)d->extra)->storage);
            break;
        case QTYPE_KIND_STORED:
            f(cx, ((const QStoredDescriptor *)d->extra)->type);
            f(cx, ((const QStoredDescriptor *)d->extra)->storage);
            break;
        default:
            break;
    }
}

static void quest_inst_collect(void *cx, const QTypeDescriptor *d) {
    QInstWork *w = (QInstWork *)cx;
    if (d == NULL || quest_inst_find(w, d) != NULL) return;
    if (w->count == w->capacity) {
        size_t capacity = w->capacity ? 2 * w->capacity : 16;
        QInstNode *nodes = (QInstNode *)quest_alloc_sized(sizeof(QInstNode) * capacity, &quest_layout_inst_nodes);
        if (w->count > 0) memcpy(nodes, w->nodes, sizeof(QInstNode) * w->count);
        w->nodes = nodes;
        w->capacity = capacity;
    }
    quest_barrier_slot(&w->nodes[w->count]);
    w->nodes[w->count++] = (QInstNode){ d, NULL, d->kind == QTYPE_KIND_HOLE };
    quest_desc_children(d, quest_inst_collect, cx);
}

typedef struct QInstReach {
    QInstWork *w;
    bool       found;
} QInstReach;

static void quest_inst_reach(void *cx, const QTypeDescriptor *c) {
    QInstReach *r = (QInstReach *)cx;
    QInstNode *n = c != NULL ? quest_inst_find(r->w, c) : NULL;
    if (n != NULL && n->has_hole) r->found = true;
}

typedef struct QInstContext {
    QInstWork                    *w;
    const QTypeDescriptor *const *args;
    size_t                        arg_count;
} QInstContext;

/* Descriptors' names are cut off at this many characters, followed by "...", as
   short_type_name (types/dump.py) cuts off static descriptors' names and the
   interpreter the types it prints */
#define Q_DISPLAY_NAME_LIMIT 80

/* The name of an instance of a template node named name: the name with each of
   the template's holes (?0, ?1, ...) replaced by its argument's name, cut off
   as static names are, so that values print with their types (or name itself,
   if it has no holes) */
static const char *quest_inst_name(const QInstContext *cx, const char *name) {
    if (name == NULL || strchr(name, '?') == NULL) return name;
    /* Each occurrence of a hole grows the name by at most the longest
     * argument's name */
    size_t longest = 0, holes = 0, len = 0;
    for (size_t i = 0; i < cx->arg_count; ++i) {
        size_t n = cx->args[i] != NULL && cx->args[i]->name != NULL ? strlen(cx->args[i]->name) : 0;
        if (n > longest) longest = n;
    }
    for (const char *c = name; *c; ++c) holes += (*c == '?');
    size_t cap = strlen(name) + 1 + holes * longest + 3;
    char *out = (char *)quest_alloc_bytes(cap);
    for (const char *c = name; *c;) {
        if (*c == '?' && c[1] >= '0' && c[1] <= '9') {
            char *end = NULL;
            unsigned long index = strtoul(c + 1, &end, 10);
            const QTypeDescriptor *arg = index < cx->arg_count ? cx->args[index] : NULL;
            if (arg != NULL && arg->name != NULL) {
                size_t n = strlen(arg->name);
                memcpy(out + len, arg->name, n);
                len += n;
                c = end;
                continue;
            }
        }
        out[len++] = *c++;
    }
    if (len > Q_DISPLAY_NAME_LIMIT) {
        memcpy(out + Q_DISPLAY_NAME_LIMIT, "...", 3);
        len = Q_DISPLAY_NAME_LIMIT + 3;
    }
    out[len] = '\0';
    return out;
}

/* The instance of template node d */
static const QTypeDescriptor *quest_inst_of(const QInstContext *cx, const QTypeDescriptor *d) {
    if (d == NULL) return NULL;
    QInstNode *n = quest_inst_find(cx->w, d);
    return n != NULL && n->has_hole ? n->inst : d;
}

static void *quest_copy_block(const void *src, size_t size) {
    void *copy = quest_alloc_sized(size, &quest_layout_words);
    memcpy(copy, src, size);
    return copy;
}

/* Fills the instance of template node n, whose descriptor was allocated
 * already */
static void quest_inst_fill(const QInstContext *cx, QInstNode *n) {
    const QTypeDescriptor *d = n->tmpl;
    QTypeDescriptor *out = n->inst;
    quest_barrier(out);
    *out = *d;
    /* An opaque descriptor is compared by its name, an abstract type operator's
     * (its arguments are filled below) */
    if (d->kind != QTYPE_KIND_OPAQUE) out->name = quest_inst_name(cx, d->name);
    switch (d->kind) {
        case QTYPE_KIND_TUPLE: {
            const QTupleTypeDescriptor *m = (const QTupleTypeDescriptor *)d->extra;
            QTupleTypeDescriptor *c = (QTupleTypeDescriptor *)quest_copy_block(
                m, sizeof(QTupleTypeDescriptor) + sizeof(QTupleElementDescriptor) * m->element_count);
            for (size_t i = 0; i < m->element_count; ++i) {
                ((QTupleElementDescriptor *)&c->elements[i])->type = quest_inst_of(cx, m->elements[i].type);
            }
            quest_barrier(out);
            out->extra = c;
            break;
        }
        case QTYPE_KIND_RECORD: {
            const QRecordTypeDescriptor *m = (const QRecordTypeDescriptor *)d->extra;
            QRecordTypeDescriptor *c = (QRecordTypeDescriptor *)quest_copy_block(
                m, sizeof(QRecordTypeDescriptor) + sizeof(QRecordFieldDescriptor) * m->field_count);
            for (size_t i = 0; i < m->field_count; ++i) {
                ((QRecordFieldDescriptor *)&c->fields[i])->type = quest_inst_of(cx, m->fields[i].type);
            }
            quest_barrier(out);
            out->extra = c;
            break;
        }
        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION: {
            const QVariantTypeDescriptor *m = (const QVariantTypeDescriptor *)d->extra;
            QVariantTypeDescriptor *c = (QVariantTypeDescriptor *)quest_copy_block(
                m, sizeof(QVariantTypeDescriptor) + sizeof(QVariantCaseDescriptor) * m->case_count);
            for (size_t i = 0; i < m->case_count; ++i) {
                ((QVariantCaseDescriptor *)&c->cases[i])->payload_type = quest_inst_of(cx, m->cases[i].payload_type);
            }
            quest_barrier(out);
            out->extra = c;
            break;
        }
        case QTYPE_KIND_ARRAY: {
            QArrayTypeDescriptor *c = (QArrayTypeDescriptor *)quest_alloc(sizeof(QArrayTypeDescriptor), &quest_layout_array_descriptor);
            c->element_type = quest_inst_of(cx, ((const QArrayTypeDescriptor *)d->extra)->element_type);
            quest_barrier(out);
            out->extra = c;
            break;
        }
        case QTYPE_KIND_FUN: {
            const QFunTypeDescriptor *m = (const QFunTypeDescriptor *)d->extra;
            QFunTypeDescriptor *c = (QFunTypeDescriptor *)quest_copy_block(
                m, sizeof(QFunTypeDescriptor) + sizeof(QFunParamDescriptor) * m->param_count);
            for (size_t i = 0; i < m->param_count; ++i) {
                ((QFunParamDescriptor *)&c->params[i])->type = quest_inst_of(cx, m->params[i].type);
            }
            c->result_type = quest_inst_of(cx, m->result_type);
            if (m->quantifier_bounds != NULL && m->quantifier_count > 0) {
                const QTypeDescriptor **bounds =
                    (const QTypeDescriptor **)quest_alloc_sized(sizeof(QTypeDescriptor *) * m->quantifier_count,
                                                                &quest_layout_pointers);
                for (size_t i = 0; i < m->quantifier_count; ++i) bounds[i] = quest_inst_of(cx, m->quantifier_bounds[i]);
                quest_barrier(c);
                c->quantifier_bounds = bounds;
            }
            quest_barrier(out);
            out->extra = c;
            break;
        }
        case QTYPE_KIND_AUTO: {
            const QAutoTypeDescriptor *m = (const QAutoTypeDescriptor *)d->extra;
            QAutoTypeDescriptor *c = (QAutoTypeDescriptor *)quest_copy_block(
                m, sizeof(QAutoTypeDescriptor) + sizeof(QAutoComponentDescriptor) * m->component_count);
            c->bound = quest_inst_of(cx, m->bound);
            for (size_t i = 0; i < m->component_count; ++i) {
                QAutoComponentDescriptor *comp = (QAutoComponentDescriptor *)&c->components[i];
                comp->type = quest_inst_of(cx, m->components[i].type);
            }
            quest_barrier(out);
            out->extra = c;
            break;
        }
        case QTYPE_KIND_EXCEPTION: {
            QExceptionTypeDescriptor *c = (QExceptionTypeDescriptor *)quest_alloc(sizeof(QExceptionTypeDescriptor), &quest_layout_exception_descriptor);
            c->payload_type = quest_inst_of(cx, ((const QExceptionTypeDescriptor *)d->extra)->payload_type);
            quest_barrier(out);
            out->extra = c;
            break;
        }
        case QTYPE_KIND_OPAQUE: {
            const QOpaqueTypeDescriptor *m = (const QOpaqueTypeDescriptor *)d->extra;
            QOpaqueTypeDescriptor *c = (QOpaqueTypeDescriptor *)quest_alloc(sizeof(QOpaqueTypeDescriptor), &quest_layout_opaque_descriptor);
            const QTypeDescriptor **args = (const QTypeDescriptor **)quest_alloc_sized(sizeof(QTypeDescriptor *) * (m->arg_count + 1),
                                                                                   &quest_layout_pointers);
            for (size_t i = 0; i < m->arg_count; ++i) args[i] = quest_inst_of(cx, m->args[i]);
            quest_barrier(c);
            c->arg_count = m->arg_count;
            c->args = args;
            c->rep = m->rep;
            quest_barrier(out);
            out->extra = c;
            break;
        }
        case QTYPE_KIND_HOLE: {
            const QHoleDescriptor *h = (const QHoleDescriptor *)d->extra;
            QStoredDescriptor *c = (QStoredDescriptor *)quest_alloc(sizeof(QStoredDescriptor), &quest_layout_stored_descriptor);
            c->type = cx->args[h->index];
            c->storage = quest_inst_of(cx, h->storage);
            c->viewed = false;
            quest_barrier(out);
            out->kind = QTYPE_KIND_STORED;
            out->name = c->type != NULL ? c->type->name : d->name;
            out->size = sizeof(QVal);
            quest_barrier(out);
            out->extra = c;
            break;
        }
        default:
            break;
    }
}

/* Instances made so far, keyed by template and arguments */
typedef struct QInstCacheEntry {
    const QTypeDescriptor       *tmpl;
    size_t                       arg_count;
    const QTypeDescriptor      **args;
    const QTypeDescriptor       *inst;
    struct QInstCacheEntry      *next;
} QInstCacheEntry;

#define Q_INST_CACHE_SIZE 1024
static QInstCacheEntry *quest_inst_cache[Q_INST_CACHE_SIZE];

/* View maps (QViewMap) */

#define Q_VIEW_MAP_CACHE_SIZE 256

typedef struct QViewMapEntry {
    QViewMap              map;
    struct QViewMapEntry *next;
} QViewMapEntry;

static QViewMapEntry *quest_view_maps[Q_VIEW_MAP_CACHE_SIZE];

/* The type a part read through the bound is converted from: the actual's type
 * for it, or NULL when it agrees with the bound's (the same type, in the same
 * layout) */
static const QTypeDescriptor *quest_view_from(const QTypeDescriptor *actual, const QTypeDescriptor *bound) {
    if (actual == NULL || bound == NULL || actual == bound) return NULL;
    if (quest_is_subtype(bound, actual) && quest_layout_equivalent(actual, bound) &&
        quest_proxies_agree(actual, bound)) {
        return NULL;
    }
    return actual;
}

static const QVariantCaseDescriptor *quest_case_named(const QVariantTypeDescriptor *t, const char *name) {
    for (size_t i = 0; t != NULL && i < t->case_count; ++i) {
        if (strcmp(t->cases[i].name, name) == 0) return &t->cases[i];
    }
    return NULL;
}

static void quest_fill_view_map(QViewMap *m) {
    const QTypeDescriptor *a = m->actual, *b = m->bound;
    if (a->kind == QTYPE_KIND_RECORD && b->kind == QTYPE_KIND_RECORD) {
        const QRecordTypeDescriptor *ra = (const QRecordTypeDescriptor *)a->extra;
        const QRecordTypeDescriptor *rb = (const QRecordTypeDescriptor *)b->extra;
        size_t n = rb != NULL ? rb->field_count : 0;
        int64_t *index = (int64_t *)quest_alloc_sized(sizeof(int64_t) * (n ? n : 1), &quest_layout_ints);
        const QTypeDescriptor **from = (const QTypeDescriptor **)quest_alloc_sized(sizeof(void *) * (n ? n : 1), &quest_layout_pointers);
        const QTypeDescriptor **to = (const QTypeDescriptor **)quest_alloc_sized(sizeof(void *) * (n ? n : 1), &quest_layout_pointers);
        for (size_t k = 0; k < n; ++k) {
            index[k] = -1;
            to[k] = rb->fields[k].type;
            for (size_t j = 0; ra != NULL && j < ra->field_count; ++j) {
                if (strcmp(ra->fields[j].name, rb->fields[k].name) == 0) {
                    index[k] = (int64_t)j;
                    from[k] = quest_view_from(ra->fields[j].type, rb->fields[k].type);
                    break;
                }
            }
            if (index[k] < 0) quest_raise_dynamic_error();
        }
        quest_barrier(m);
        m->index = index;
        m->from = from;
        m->to = to;
        return;
    }
    if (a->kind == QTYPE_KIND_TUPLE && b->kind == QTYPE_KIND_TUPLE) {
        /* A tuple's components, by position: the actual's are a
         * prefix-compatible extension of the bound's */
        const QTupleTypeDescriptor *ta = (const QTupleTypeDescriptor *)a->extra;
        const QTupleTypeDescriptor *tb = (const QTupleTypeDescriptor *)b->extra;
        size_t n = tb != NULL ? tb->element_count : 0;
        const QTypeDescriptor **from = (const QTypeDescriptor **)quest_alloc_sized(sizeof(void *) * (n ? n : 1), &quest_layout_pointers);
        const QTypeDescriptor **to = (const QTypeDescriptor **)quest_alloc_sized(sizeof(void *) * (n ? n : 1), &quest_layout_pointers);
        for (size_t k = 0; k < n; ++k) {
            to[k] = tb->elements[k].type;
            from[k] = ta != NULL && k < ta->element_count ? quest_view_from(ta->elements[k].type, to[k]) : NULL;
        }
        quest_barrier(m);
        m->from = from;
        m->to = to;
        return;
    }
    if ((a->kind == QTYPE_KIND_VARIANT || a->kind == QTYPE_KIND_OPTION) && b->kind == a->kind) {
        const QVariantTypeDescriptor *va = (const QVariantTypeDescriptor *)a->extra;
        const QVariantTypeDescriptor *vb = (const QVariantTypeDescriptor *)b->extra;
        size_t na = va != NULL ? va->case_count : 0, nb = vb != NULL ? vb->case_count : 0;
        int64_t *index = (int64_t *)quest_alloc_sized(sizeof(int64_t) * (na ? na : 1), &quest_layout_ints);
        for (size_t i = 0; i < na; ++i) {
            const QVariantCaseDescriptor *c = quest_case_named(vb, va->cases[i].name);
            if (c == NULL) quest_raise_dynamic_error();
            index[va->cases[i].tag_index] = c->tag_index;
        }
        quest_barrier(m);
        m->index = index;
        if (a->kind == QTYPE_KIND_VARIANT) {
            const QTypeDescriptor **from = (const QTypeDescriptor **)quest_alloc_sized(sizeof(void *) * (nb ? nb : 1), &quest_layout_pointers);
            const QTypeDescriptor **to = (const QTypeDescriptor **)quest_alloc_sized(sizeof(void *) * (nb ? nb : 1), &quest_layout_pointers);
            for (size_t k = 0; k < nb; ++k) {
                const QVariantCaseDescriptor *c = quest_case_named(va, vb->cases[k].name);
                to[k] = vb->cases[k].payload_type;
                from[k] = c != NULL ? quest_view_from(c->payload_type, to[k]) : NULL;
            }
            quest_barrier(m);
            m->from = from;
            m->to = to;
            return;
        }
        /* An option's cases' components, flattened (a payload that is not a
         * tuple is one) */
        size_t *start = (size_t *)quest_alloc_sized(sizeof(size_t) * (nb + 1), &quest_layout_ints);
        size_t total = 0;
        for (size_t k = 0; k < nb; ++k) {
            start[k] = total;
            const QTypeDescriptor *p = vb->cases[k].payload_type;
            if (p != NULL && p->kind == QTYPE_KIND_TUPLE) {
                total += p->extra != NULL ? ((const QTupleTypeDescriptor *)p->extra)->element_count : 0;
            } else if (p != NULL) {
                total += 1;
            }
        }
        start[nb] = total;
        const QTypeDescriptor **from = (const QTypeDescriptor **)quest_alloc_sized(sizeof(void *) * (total ? total : 1), &quest_layout_pointers);
        const QTypeDescriptor **to = (const QTypeDescriptor **)quest_alloc_sized(sizeof(void *) * (total ? total : 1), &quest_layout_pointers);
        for (size_t k = 0; k < nb; ++k) {
            const QTypeDescriptor *pb = vb->cases[k].payload_type;
            const QVariantCaseDescriptor *c = quest_case_named(va, vb->cases[k].name);
            const QTypeDescriptor *pa = c != NULL ? c->payload_type : NULL;
            if (pb != NULL && pb->kind != QTYPE_KIND_TUPLE) {
                to[start[k]] = pb;
                from[start[k]] = quest_view_from(pa, pb);
                continue;
            }
            if (pb == NULL || pb->extra == NULL) continue;
            const QTupleTypeDescriptor *tb = (const QTupleTypeDescriptor *)pb->extra;
            const QTupleTypeDescriptor *ta =
                pa != NULL && pa->kind == QTYPE_KIND_TUPLE ? (const QTupleTypeDescriptor *)pa->extra : NULL;
            for (size_t j = 0; j < tb->element_count; ++j) {
                to[start[k] + j] = tb->elements[j].type;
                const QTypeDescriptor *aj = ta != NULL && j < ta->element_count ? ta->elements[j].type : NULL;
                from[start[k] + j] = quest_view_from(aj, tb->elements[j].type);
            }
        }
        quest_barrier(m);
        m->from = from;
        m->to = to;
        m->component_start = start;
        return;
    }
    quest_raise_dynamic_error();
}

const QViewMap *quest_view_map(const QTypeDescriptor *actual, const QTypeDescriptor *bound) {
    actual = quest_concrete_representation(quest_stored_representation(actual));
    bound = quest_stored_type(bound);
    uint64_t h = ((uint64_t)(uintptr_t)actual * 0x9E3779B97F4A7C15ULL) ^ (uint64_t)(uintptr_t)bound;
    size_t bucket = (size_t)((h ^ (h >> 29)) % Q_VIEW_MAP_CACHE_SIZE);
    for (QViewMapEntry *e = quest_view_maps[bucket]; e != NULL; e = e->next) {
        if (e->map.actual == actual && e->map.bound == bound) return &e->map;
    }
    QViewMapEntry *e = (QViewMapEntry *)quest_alloc(sizeof(QViewMapEntry), &quest_layout_view_map_entry);
    e->map.actual = actual;
    e->map.bound = bound;
    quest_fill_view_map(&e->map);
    quest_barrier(e);
    e->next = quest_view_maps[bucket];
    quest_view_maps[bucket] = e;
    return &e->map;
}

const QTypeDescriptor *quest_instantiate_descriptor(
    const QTypeDescriptor *template_desc, size_t arg_count, const QTypeDescriptor *const *args
) {
    uint64_t h = (uint64_t)(uintptr_t)template_desc * 0x9E3779B97F4A7C15ULL;
    for (size_t i = 0; i < arg_count; ++i) {
        h = (h ^ (uint64_t)(uintptr_t)args[i]) * 0x100000001B3ULL;
    }
    size_t bucket = (size_t)((h ^ (h >> 29)) % Q_INST_CACHE_SIZE);
    for (QInstCacheEntry *e = quest_inst_cache[bucket]; e != NULL; e = e->next) {
        if (e->tmpl == template_desc && e->arg_count == arg_count &&
            (arg_count == 0 || memcmp(e->args, args, sizeof(QTypeDescriptor *) * arg_count) == 0)) {
            return e->inst;
        }
    }

    /* The instance's descriptors point at each other and at their names and
     * metadata, allocated between them: no collection until all are filled */
    quest_gc_hold();
    QInstWork w = { NULL, 0, 0 };
    quest_inst_collect(&w, template_desc);
    /* Which nodes reach a hole: iterate to a fixed point, since templates may
     * be cyclic */
    for (bool changed = true; changed;) {
        changed = false;
        for (size_t i = 0; i < w.count; ++i) {
            if (w.nodes[i].has_hole) continue;
            QInstReach r = { &w, false };
            quest_desc_children(w.nodes[i].tmpl, quest_inst_reach, &r);
            if (r.found) {
                w.nodes[i].has_hole = true;
                changed = true;
            }
        }
    }
    for (size_t i = 0; i < w.count; ++i) {
        if (!w.nodes[i].has_hole) continue;
        QTypeDescriptor *inst = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor), &quest_layout_descriptor);
        quest_barrier_slot(&w.nodes[i].inst);    /* the table may be old by now: the allocations may have collected */
        w.nodes[i].inst = inst;
    }
    QInstContext cx = { &w, args, arg_count };
    for (size_t i = 0; i < w.count; ++i) {
        if (w.nodes[i].has_hole) quest_inst_fill(&cx, &w.nodes[i]);
    }
    const QTypeDescriptor *inst = quest_inst_of(&cx, template_desc);

    const QTypeDescriptor **own_args = (const QTypeDescriptor **)quest_alloc_sized(
        sizeof(QTypeDescriptor *) * (arg_count + 1), &quest_layout_pointers);
    if (arg_count > 0) memcpy((void *)own_args, args, sizeof(QTypeDescriptor *) * arg_count);
    QInstCacheEntry *e = (QInstCacheEntry *)quest_alloc(sizeof(QInstCacheEntry), &quest_layout_inst_cache_entry);
    e->tmpl = template_desc;
    e->arg_count = arg_count;
    e->args = own_args;
    e->inst = inst;
    e->next = quest_inst_cache[bucket];
    quest_inst_cache[bucket] = e;
    quest_gc_release();
    return inst;
}

QVal quest_record_field_value(QRecordVal rec, const QTypeDescriptor *view, size_t i) {
    const QRecordTypeDescriptor *meta = (const QRecordTypeDescriptor *)view->extra;
    const QTypeDescriptor *field_type = meta->fields[i].type;
    const void *slot = (const char *)rec.val + quest_record_field_offset(rec, i);
    QRecordStoredTypes stored = quest_record_stored_types(rec, meta->field_count);
    if (stored != NULL && stored[i] != NULL) return quest_convert(quest_slot_read(slot), stored[i], field_type);
    return quest_slot_read(slot);
}


const void *quest_record_dict(const QTypeDescriptor *view, const QTypeDescriptor *layout) {
    if (view == NULL || layout == NULL) return NULL;
    if (quest_record_dicts_capacity > 0) {
        QRecordDictEntry *e = quest_record_dict_slot(view, layout);
        if (e->view != NULL) return e->dict;
    }
    const void *dict = quest_build_record_dict(view, layout);
    if (dict != NULL) quest_record_dicts_insert(view, layout, dict);
    return dict;
}

void quest_register_record_dict(const QTypeDescriptor *view, const QTypeDescriptor *layout, const void *dict) {
    if (view != NULL && layout != NULL && dict != NULL) quest_record_dicts_insert(view, layout, dict);
}

/* ------------------------------------------------------------------------- */
/* Dynamic Aggregate Adaptation Cache & Coercion Functions                   */
/* ------------------------------------------------------------------------- */

typedef struct QVariantAdapterCacheEntry {
    const QTypeDescriptor            *sub_desc;
    const QTypeDescriptor            *super_desc;
    const int64_t                    *tagmap;
    struct QVariantAdapterCacheEntry *next;
} QVariantAdapterCacheEntry;

static QVariantAdapterCacheEntry *quest_variant_adapter_cache = NULL;

QVariantVal quest_variant_adapt(const QTypeDescriptor *sub_desc, const QTypeDescriptor *super_desc, QVal payload) {
    if (payload.p == NULL) {
        return (QVariantVal){ .tag = 0, .payload = (QVal){ .u = 0 } };
    }
    const QVariantVal *orig_var = (const QVariantVal *)payload.p;
    if (sub_desc == super_desc) {
        return *orig_var;
    }

    const QVariantTypeDescriptor *s_meta = (const QVariantTypeDescriptor *)sub_desc->extra;
    const QVariantTypeDescriptor *t_meta = (const QVariantTypeDescriptor *)super_desc->extra;
    if (s_meta == NULL || t_meta == NULL) {
        return *orig_var;
    }

    /* Check tagmap cache */
    QVariantAdapterCacheEntry *cached = NULL;
    for (QVariantAdapterCacheEntry *cur = quest_variant_adapter_cache; cur != NULL; cur = cur->next) {
        if (cur->sub_desc == sub_desc && cur->super_desc == super_desc) {
            cached = cur;
            break;
        }
    }

    if (cached == NULL) {
        int64_t *tagmap = (int64_t *)quest_alloc_sized(sizeof(int64_t) * s_meta->case_count, &quest_layout_ints);
        for (size_t i = 0; i < s_meta->case_count; ++i) {
            const QVariantCaseDescriptor *sc = &s_meta->cases[i];
            int64_t target_idx = -1;
            for (size_t j = 0; j < t_meta->case_count; ++j) {
                if (t_meta->cases[j].name != NULL && strcmp(t_meta->cases[j].name, sc->name) == 0) {
                    target_idx = (int64_t)j;
                    break;
                }
            }
            tagmap[i] = target_idx >= 0 ? target_idx : 0;
        }
        cached = (QVariantAdapterCacheEntry *)quest_alloc(sizeof(QVariantAdapterCacheEntry), &quest_layout_variant_adapter_entry);
        cached->sub_desc = sub_desc;
        cached->super_desc = super_desc;
        cached->tagmap = tagmap;
        cached->next = quest_variant_adapter_cache;
        quest_variant_adapter_cache = cached;
    }

    int64_t target_tag = (orig_var->tag >= 0 && (size_t)orig_var->tag < s_meta->case_count)
                             ? cached->tagmap[orig_var->tag]
                             : 0;

    /* Adapt payload if payload type is a compound subtype */
    QVal adapted_payload = orig_var->payload;
    const QVariantCaseDescriptor *sc = (orig_var->tag >= 0 && (size_t)orig_var->tag < s_meta->case_count)
                                           ? &s_meta->cases[orig_var->tag]
                                           : NULL;
    const QVariantCaseDescriptor *tc = (target_tag >= 0 && (size_t)target_tag < t_meta->case_count)
                                           ? &t_meta->cases[target_tag]
                                           : NULL;
    if (sc != NULL && tc != NULL && sc->payload_type != NULL && tc->payload_type != NULL &&
        sc->payload_type != tc->payload_type) {
        adapted_payload = quest_convert(orig_var->payload, sc->payload_type, tc->payload_type);
    }

    return (QVariantVal){ .tag = target_tag, .payload = adapted_payload };
}

/* This file's global roots, for the collector and its roots check */
void quest_views_roots(QRootVisitor add) {
    add(quest_equiv_trail, 2 * Q_EQUIV_TRAIL_MAX);
    add(&quest_record_dicts, 1);
    add(quest_inst_cache, Q_INST_CACHE_SIZE);
    add(quest_view_maps, Q_VIEW_MAP_CACHE_SIZE);
    add(&quest_variant_adapter_cache, 1);
}
