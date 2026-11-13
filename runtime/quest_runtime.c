/*
 * Quest C Runtime Implementation
 *
 * The functions quest_runtime.h declares, which code compiled by either
 * compiler, with any backend, calls. This file holds strings, arrays, and
 * reals; the runtime's roots for the collector; initialization of the
 * builtins; and the built-in operators as closures. The rest is in:
 *
 *   - quest_exceptions.c: the built-in exceptions, raising, tracebacks
 *     (docs/exceptions.md §5), and the stack overflow guard (§6);
 *   - quest_print.c: formatting reals, and printing values for echo;
 *   - quest_types.c: the base types' descriptors, subtyping on descriptors
 *     (quest_is_subtype), and descriptors made at run time;
 *   - quest_views.c: record offset tables and dicts, proxies, options as
 *     values and conversion between layouts (quest_convert), layout
 *     equivalence, descriptor templates and view maps, and dynamic adaptation
 *     of records and variants;
 *   - quest_os.c: the system, os, and process modules' primitives;
 *   - quest_stdlib.c: the rest of the standard library's primitives (writers
 *     and readers, conversions, strings, ascii, reals, words, and hashing);
 *   - quest_gc.c: the collector (docs/collector.md);
 *   - quest_serialization.c: dynamic.extern and dynamic.intern;
 *   - quest_code.c: the JIT's primitives (docs/jit.md);
 *   - quest_readline.c: io/readline;
 *   - quest_inline.c: external definitions of the header's inline helpers.
 *
 * quest_runtime_internal.h declares what these files share with each other
 * but not with compiled code. docs/c-representation.md describes the
 * representation this code works on.
 */

/* The POSIX functions -std=c99 hides on Linux (glibc) */
#if defined(__linux__) && !defined(_GNU_SOURCE)
#define _GNU_SOURCE
#endif

#include "quest_runtime_internal.h"

QString *quest_string_new(const char *src, int64_t len) {
    if (len < 0 && src != NULL) {
        len = (int64_t)strlen(src);
    }
    /* The buffer first: nothing allocates between an object's allocation
     * and the stores that make it, so that they need no write barrier
     * (docs/collector.md section 3.5); the runtime keeps to that order, and
     * barriers the stores that cannot */
    char *data = (char *)quest_alloc_bytes(len + 1);
    QString *s = (QString *)quest_alloc(sizeof(QString), &quest_layout_string);
    s->length = len;
    s->capacity = len;
    s->data = data;
    if (len > 0 && src != NULL) {
        memcpy(s->data, src, (size_t)len);
    }
    s->data[len] = 0;
    return s;
}

QString *quest_string_concat(const QString *s1, const QString *s2) {
    if (s1 == NULL && s2 == NULL) return quest_string_new("", 0);
    if (s1 == NULL) return quest_string_new(s2->data, s2->length);
    if (s2 == NULL) return quest_string_new(s1->data, s1->length);

    int64_t total = s1->length + s2->length;
    char *data = (char *)quest_alloc_bytes(total + 1);
    QString *res = (QString *)quest_alloc(sizeof(QString), &quest_layout_string);
    res->length = total;
    res->capacity = total;
    res->data = data;
    if (s1->length > 0) {
        memcpy(res->data, s1->data, (size_t)s1->length);
    }
    if (s2->length > 0) {
        memcpy(res->data + s1->length, s2->data, (size_t)s2->length);
    }
    res->data[total] = 0;
    return res;
}

bool quest_string_equal(const QString *s1, const QString *s2) {
    if (s1 == s2) return true;
    if (s1 == NULL || s2 == NULL) return false;
    if (s1->length != s2->length) return false;
    return memcmp(s1->data, s2->data, (size_t)s1->length) == 0;
}

QChar quest_string_get_char(const QString *s, int64_t idx) {
    if (s == NULL || idx < 0 || idx >= s->length) {
        quest_raise_string_error();
    }
    return s->data[idx];
}

void quest_string_set_char(QString *s, int64_t idx, QChar ch) {
    if (s == NULL || idx < 0 || idx >= s->length) {
        quest_raise_string_error();
    }
    s->data[idx] = ch;
}

QString *quest_string_get_sub(const QString *s, int64_t start, int64_t len) {
    if (s == NULL || start < 0 || len < 0 || start + len > s->length) {
        quest_raise_string_error();
    }
    return quest_string_new(s->data + start, len);
}

void quest_string_set_sub(QString *dest, int64_t dest_start, const QString *src, int64_t src_start, int64_t len) {
    if (dest == NULL || src == NULL || len < 0 ||
        dest_start < 0 || dest_start + len > dest->length ||
        src_start < 0 || src_start + len > src->length) {
        quest_raise_string_error();
    }
    if (len > 0) {
        memmove(dest->data + dest_start, src->data + src_start, (size_t)len);
    }
}

QString *quest_string_alloc(int64_t size, QChar init) {
    if (size < 0) {
        quest_raise_string_error();
    }
    char *buf = (char *)quest_alloc_bytes((size_t)size + 1);
    memset(buf, (int)init, (size_t)size);
    buf[size] = '\0';
    return quest_string_new(buf, size);
}

bool quest_string_is_empty(const QString *s) {
    return s == NULL || s->length == 0;
}

int64_t quest_string_length(const QString *s) {
    if (s == NULL) return 0;
    return s->length;
}

QString *quest_string_cat_sub(const QString *s1, int64_t st1, int64_t sz1,
                              const QString *s2, int64_t st2, int64_t sz2) {
    if (s1 == NULL || s2 == NULL || st1 < 0 || sz1 < 0 || st1 + sz1 > s1->length ||
        st2 < 0 || sz2 < 0 || st2 + sz2 > s2->length) {
        quest_raise_string_error();
    }
    int64_t total = sz1 + sz2;
    char *buf = (char *)quest_alloc_bytes((size_t)total + 1);
    if (sz1 > 0) memcpy(buf, s1->data + st1, (size_t)sz1);
    if (sz2 > 0) memcpy(buf + sz1, s2->data + st2, (size_t)sz2);
    buf[total] = '\0';
    return quest_string_new(buf, total);
}

QString *quest_string_conc(const QArray *strings) {
    if (strings == NULL) {
        quest_raise_string_error();
    }
    int64_t total = 0;
    for (int64_t i = 0; i < strings->length; ++i) {
        const QString *part = (const QString *)strings->data[i].p;
        if (part != NULL) {
            total += part->length;
        }
    }
    char *buf = (char *)quest_alloc_bytes((size_t)total + 1);
    int64_t offset = 0;
    for (int64_t i = 0; i < strings->length; ++i) {
        const QString *part = (const QString *)strings->data[i].p;
        if (part != NULL && part->length > 0) {
            memcpy(buf + offset, part->data, (size_t)part->length);
            offset += part->length;
        }
    }
    buf[total] = '\0';
    return quest_string_new(buf, total);
}

bool quest_string_equal_sub(const QString *s1, int64_t st1, int64_t sz1,
                            const QString *s2, int64_t st2, int64_t sz2) {
    if (s1 == NULL || s2 == NULL || st1 < 0 || sz1 < 0 || st1 + sz1 > s1->length ||
        st2 < 0 || sz2 < 0 || st2 + sz2 > s2->length) {
        quest_raise_string_error();
    }
    if (sz1 != sz2) return false;
    if (sz1 == 0) return true;
    return memcmp(s1->data + st1, s2->data + st2, (size_t)sz1) == 0;
}

bool quest_string_precedes(const QString *s1, const QString *s2) {
    if (s1 == NULL || s2 == NULL) {
        quest_raise_string_error();
    }
    int64_t min_len = s1->length < s2->length ? s1->length : s2->length;
    int cmp = 0;
    if (min_len > 0) {
        cmp = memcmp(s1->data, s2->data, (size_t)min_len);
    }
    if (cmp != 0) return cmp < 0;
    return s1->length <= s2->length;
}

bool quest_string_precedes_sub(const QString *s1, int64_t st1, int64_t sz1,
                               const QString *s2, int64_t st2, int64_t sz2) {
    if (s1 == NULL || s2 == NULL || st1 < 0 || sz1 < 0 || st1 + sz1 > s1->length ||
        st2 < 0 || sz2 < 0 || st2 + sz2 > s2->length) {
        quest_raise_string_error();
    }
    int64_t min_len = sz1 < sz2 ? sz1 : sz2;
    int cmp = 0;
    if (min_len > 0) {
        cmp = memcmp(s1->data + st1, s2->data + st2, (size_t)min_len);
    }
    if (cmp != 0) return cmp < 0;
    return sz1 <= sz2;
}

QArray *quest_array_new(int64_t len, QVal init_val, const QLayout *layout) {
    if (len < 0) {
        quest_raise_array_error();
    }
    QArray *arr = (QArray *)quest_alloc(sizeof(QArray) + (size_t)len * sizeof(QVal), layout);
    arr->length = len;
    /* quest_alloc's memory is zeroed already: an array of zeros (0, 0.0,
       false, nil) needs no fill, which an arbitrary-precision number's limbs
       are, allocated at their largest and filled in (lib/util/bignum) */
    if (init_val.u != 0) {
        for (int64_t i = 0; i < len; ++i) {
            arr->data[i] = init_val;
        }
    }
    return arr;
}

int64_t quest_array_size(const QArray *a) {
    if (a == NULL) return 0;
    return a->length;
}

/* The ^^ operator and real.exp: a zero base with a negative exponent is a pole,
   like division by zero, and raises real.error; so does a NaN result (a
   negative base with a non-integral exponent). Overflow is an infinity. */
double quest_real_pow_at(double base, double exp, const char *loc) {
    if (base == 0.0 && exp < 0.0) {
        quest_raise_real_error_at(loc);
    }
    return quest_real_result_at(pow(base, exp), loc);
}

double quest_real_pow(double base, double exp) {
    return quest_real_pow_at(base, exp, NULL);
}

/* The runtime's statics and thread-locals that hold heap pointers
 * (docs/collector.md section 3.8); QUEST_GC_CHECK=roots scans the data
 * segment for any this list misses */
void quest_runtime_roots(QRootVisitor add) {
    quest_exceptions_roots(add);
    quest_print_roots(add);
    quest_types_roots(add);
    quest_views_roots(add);
    quest_os_roots(add);
}


/* Builtins initialization */
void quest_builtins_init(int argc, char **argv) {
    quest_writer_init_std();
    quest_reader_init_std();
    quest_system_init(argc, argv);
    quest_install_stack_guard();
}

/* ============================================================================
 * Built-in operators as values (see qv_sym_plus_closure in the header): for
 * each, a trampoline, a C function of the closure calling convention whose
 * environment is unused, and the static closure of it
 * ============================================================================
 */

/* Integer arithmetic */
static QInt qv_sym_plus_trampoline(void *env, QInt a, QInt b) { (void)env; return a + b; }
QClosure qv_sym_plus_closure = { (void *)qv_sym_plus_trampoline, NULL };

static QInt qv_sym_minus_trampoline(void *env, QInt a, QInt b) { (void)env; return a - b; }
QClosure qv_sym_minus_closure = { (void *)qv_sym_minus_trampoline, NULL };

static QInt qv_sym_star_trampoline(void *env, QInt a, QInt b) { (void)env; return a * b; }
QClosure qv_sym_star_closure = { (void *)qv_sym_star_trampoline, NULL };

static QInt qv_sym_slash_trampoline(void *env, QInt a, QInt b) { (void)env; return quest_int_div(a, b); }
QClosure qv_sym_slash_closure = { (void *)qv_sym_slash_trampoline, NULL };

static QInt qv_sym_percent_trampoline(void *env, QInt a, QInt b) { (void)env; return quest_int_mod(a, b); }
QClosure qv_sym_percent_closure = { (void *)qv_sym_percent_trampoline, NULL };

static QInt qv_mod_trampoline(void *env, QInt a, QInt b) { (void)env; return quest_int_mod(a, b); }
QClosure qv_mod_closure = { (void *)qv_mod_trampoline, NULL };

/* Integer relational */
static QBool qv_sym_lt_trampoline(void *env, QInt a, QInt b) { (void)env; return a < b; }
QClosure qv_sym_lt_closure = { (void *)qv_sym_lt_trampoline, NULL };

static QBool qv_sym_lt_equals_trampoline(void *env, QInt a, QInt b) { (void)env; return a <= b; }
QClosure qv_sym_lt_equals_closure = { (void *)qv_sym_lt_equals_trampoline, NULL };

static QBool qv_sym_gt_trampoline(void *env, QInt a, QInt b) { (void)env; return a > b; }
QClosure qv_sym_gt_closure = { (void *)qv_sym_gt_trampoline, NULL };

static QBool qv_sym_gt_equals_trampoline(void *env, QInt a, QInt b) { (void)env; return a >= b; }
QClosure qv_sym_gt_equals_closure = { (void *)qv_sym_gt_equals_trampoline, NULL };

/* Real arithmetic, raising real.error as the operators do (quest_real_result_at) */
static QReal qv_sym_plus_plus_trampoline(void *env, QReal a, QReal b) { (void)env; return quest_real_add(a, b); }
QClosure qv_sym_plus_plus_closure = { (void *)qv_sym_plus_plus_trampoline, NULL };

static QReal qv_sym_minus_minus_trampoline(void *env, QReal a, QReal b) { (void)env; return quest_real_sub(a, b); }
QClosure qv_sym_minus_minus_closure = { (void *)qv_sym_minus_minus_trampoline, NULL };

static QReal qv_sym_star_star_trampoline(void *env, QReal a, QReal b) { (void)env; return quest_real_mul(a, b); }
QClosure qv_sym_star_star_closure = { (void *)qv_sym_star_star_trampoline, NULL };

static QReal qv_sym_slash_slash_trampoline(void *env, QReal a, QReal b) { (void)env; return quest_real_divide(a, b); }
QClosure qv_sym_slash_slash_closure = { (void *)qv_sym_slash_slash_trampoline, NULL };

static QReal qv_sym_caret_caret_trampoline(void *env, QReal a, QReal b) { (void)env; return quest_real_pow(a, b); }
QClosure qv_sym_caret_caret_closure = { (void *)qv_sym_caret_caret_trampoline, NULL };

/* Real relational */
static QBool qv_sym_lt_lt_trampoline(void *env, QReal a, QReal b) { (void)env; return a < b; }
QClosure qv_sym_lt_lt_closure = { (void *)qv_sym_lt_lt_trampoline, NULL };

static QBool qv_sym_lt_lt_equals_trampoline(void *env, QReal a, QReal b) { (void)env; return a <= b; }
QClosure qv_sym_lt_lt_equals_closure = { (void *)qv_sym_lt_lt_equals_trampoline, NULL };

static QBool qv_sym_gt_gt_trampoline(void *env, QReal a, QReal b) { (void)env; return a > b; }
QClosure qv_sym_gt_gt_closure = { (void *)qv_sym_gt_gt_trampoline, NULL };

static QBool qv_sym_gt_gt_equals_trampoline(void *env, QReal a, QReal b) { (void)env; return a >= b; }
QClosure qv_sym_gt_gt_equals_closure = { (void *)qv_sym_gt_gt_equals_trampoline, NULL };

/* String concatenation */
static QString *qv_sym_lt_gt_trampoline(void *env, const QString *a, const QString *b) {
    (void)env;
    return quest_string_concat(a, b);
}
QClosure qv_sym_lt_gt_closure = { (void *)qv_sym_lt_gt_trampoline, NULL };

/* Boolean eager operations */
static QBool qv_sym_slash_backslash_trampoline(void *env, QBool a, QBool b) { (void)env; return a && b; }
QClosure qv_sym_slash_backslash_closure = { (void *)qv_sym_slash_backslash_trampoline, NULL };

static QBool qv_sym_backslash_slash_trampoline(void *env, QBool a, QBool b) { (void)env; return a || b; }
QClosure qv_sym_backslash_slash_closure = { (void *)qv_sym_backslash_slash_trampoline, NULL };
