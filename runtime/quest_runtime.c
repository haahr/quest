/*
 * Quest C Runtime Implementation
 * Part of Step 4: Bootstrap C Transpiler
 */

/* pthread_getattr_np, for the stack guard on Linux (glibc) */
#if defined(__linux__) && !defined(_GNU_SOURCE)
#define _GNU_SOURCE
#endif

#include "quest_runtime.h"

#ifndef QUEST_NOGC
/* The collector grows the heap rather than collect once its free space falls
 * below a third of the heap (Boehm's default free space divisor, 3); with a
 * divisor of 1, the heap grows to about twice the live data. Collection took
 * most of the self-hosted compiler's time, and the larger heap cut its build of
 * itself by more than a quarter. It is set before main calls GC_INIT, which
 * lets GC_FREE_SPACE_DIVISOR in the environment override it. */
__attribute__((constructor)) static void quest_gc_configure(void) {
    GC_set_free_space_divisor(1);
}
#endif

QString *quest_string_new(const char *src, int64_t len) {
    if (len < 0 && src != NULL) {
        len = (int64_t)strlen(src);
    }
    QString *s = (QString *)quest_alloc(sizeof(QString));
    s->length = len;
    s->capacity = len;
    s->data = (char *)quest_alloc_atomic(len + 1);
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
    QString *res = (QString *)quest_alloc(sizeof(QString));
    res->length = total;
    res->capacity = total;
    res->data = (char *)quest_alloc_atomic(total + 1);
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
    char *buf = (char *)quest_alloc((size_t)size + 1);
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
    char *buf = (char *)quest_alloc((size_t)total + 1);
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
    char *buf = (char *)quest_alloc((size_t)total + 1);
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

QArray *quest_array_new(int64_t len, QVal init_val) {
    if (len < 0) {
        quest_raise_array_error();
    }
    QArray *arr = (QArray *)quest_alloc(sizeof(QArray) + (size_t)len * sizeof(QVal));
    arr->length = len;
    for (int64_t i = 0; i < len; ++i) {
        arr->data[i] = init_val;
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

/* Exception handling globals */
Q_THREAD_LOCAL QExceptionHandler *quest_current_exception_handler = NULL;
Q_THREAD_LOCAL QExceptionState    quest_current_exception = { NULL, { .u = 0 }, NULL, NULL };

/* Built-in singleton exception descriptors */
const QException quest_exc_arrayOp_error = { "arrayOp.error" };
const QException quest_exc_string_error  = { "string.error" };
const QException quest_exc_variant_error = { "variant.tagMismatch" };
const QException quest_exc_dynamic_error = { "dynamic.error" };
const QException quest_exc_writer_error  = { "writer.error" };
const QException quest_exc_reader_error  = { "reader.error" };
const QException quest_exc_ascii_error   = { "ascii.error" };
const QException quest_exc_int_error     = { "int.error" };
const QException quest_exc_real_error    = { "real.error" };
const QException quest_exc_word_error    = { "word.error" };
const QException quest_exc_system_error  = { "system.error" };

const QException *quest_alloc_exception(const char *name) {
    QException *exc = (QException *)quest_alloc(sizeof(QException));
    exc->name = name ? name : "Exception";
    return exc;
}

/* ------------------------------------------------------------------------- */
/* Tracebacks (docs/exceptions.md §5)                                        */
/* ------------------------------------------------------------------------- */

/* The registered function tables, and their entries sorted by start, made when
 * frames are first named */
typedef struct QFuncTables {
    const QFuncEntry   *entries;
    size_t              count;
    struct QFuncTables *next;
} QFuncTables;

static QFuncTables *quest_func_tables = NULL;
static QFuncEntry  *quest_funcs_sorted = NULL;
static size_t       quest_funcs_count = 0;

void quest_register_funcs(const QFuncEntry *entries, size_t count) {
    QFuncTables *t = (QFuncTables *)malloc(sizeof(QFuncTables));
    if (t == NULL) return;
    t->entries = entries;
    t->count = count;
    t->next = quest_func_tables;
    quest_func_tables = t;
    free(quest_funcs_sorted);
    quest_funcs_sorted = NULL;
}

static int quest_func_entry_compare(const void *a, const void *b) {
    uintptr_t x = (uintptr_t)((const QFuncEntry *)a)->addr, y = (uintptr_t)((const QFuncEntry *)b)->addr;
    return x < y ? -1 : x > y;
}

/* The frame name of the function starting at start, or NULL for one with no
   frame (in the runtime, the C library, or made by the compiler's passes):
   functions are matched by their exact starts, never by proximity */
static const char *quest_frame_name(const void *start) {
    if (start == NULL) return NULL;
    if (quest_funcs_sorted == NULL) {
        size_t n = 0;
        for (QFuncTables *t = quest_func_tables; t != NULL; t = t->next) n += t->count;
        quest_funcs_sorted = (QFuncEntry *)malloc((n > 0 ? n : 1) * sizeof(QFuncEntry));
        if (quest_funcs_sorted == NULL) return NULL;
        quest_funcs_count = 0;
        for (QFuncTables *t = quest_func_tables; t != NULL; t = t->next) {
            memcpy(quest_funcs_sorted + quest_funcs_count, t->entries, t->count * sizeof(QFuncEntry));
            quest_funcs_count += t->count;
        }
        qsort(quest_funcs_sorted, quest_funcs_count, sizeof(QFuncEntry), quest_func_entry_compare);
    }
    QFuncEntry key = { start, NULL };
    const QFuncEntry *e = (const QFuncEntry *)bsearch(&key, quest_funcs_sorted, quest_funcs_count, sizeof(QFuncEntry),
                                                      quest_func_entry_compare);
    return e != NULL ? e->name : NULL;
}

/* Prints frames, most recent first, collapsing a run of the same frame name */
typedef struct QFramePrinter {
    const char *name;
    int64_t     count;
} QFramePrinter;

static void quest_frames_flush(QFramePrinter *p) {
    if (p->name == NULL) return;
    fprintf(stderr, "  in %s\n", p->name);
    if (p->count > 1) fprintf(stderr, "  ... %s repeated %lld more times\n", p->name, (long long)(p->count - 1));
    p->name = NULL;
    p->count = 0;
}

static void quest_frames_add(QFramePrinter *p, const void *start, int64_t count) {
    const char *name = quest_frame_name(start);
    if (name == NULL) return;
    if (p->name != NULL && strcmp(p->name, name) == 0) {
        p->count += count;
        return;
    }
    quest_frames_flush(p);
    p->name = name;
    p->count = count;
}

#if defined(__APPLE__) || (defined(__linux__) && defined(__GLIBC__))
#include <unwind.h>
#define Q_HAVE_UNWIND 1
#ifdef __APPLE__
#include <dlfcn.h>
#endif

/* The start of the function containing pc. Linux's unwind tables (.eh_frame)
   describe each function on its own, so the unwinder's start is the function's.
   macOS's compact unwind tables describe a run of adjacent functions whose
   prologues are alike as one, so the unwinder's start may be an earlier
   function's: the symbol table's start (which has static functions, unless the
   binary is stripped) is the function's own, if it is no earlier. */
static const void *quest_function_start(void *pc) {
    void *start = _Unwind_FindEnclosingFunction(pc);
#ifdef __APPLE__
    Dl_info info;
    if (dladdr(pc, &info) != 0 && info.dli_saddr != NULL && (uintptr_t)info.dli_saddr >= (uintptr_t)start &&
        (uintptr_t)info.dli_saddr <= (uintptr_t)pc) {
        start = info.dli_saddr;
    }
#endif
    return start;
}

/* The start of the function of each frame of the stack, from the platform's
 * unwind tables, for a visitor */
typedef void (*QFrameVisitor)(const void *start, void *arg);

typedef struct QStackWalk {
    QFrameVisitor visit;
    void         *arg;
} QStackWalk;

static _Unwind_Reason_Code quest_walk_frame(struct _Unwind_Context *context, void *arg) {
    QStackWalk *walk = (QStackWalk *)arg;
    uintptr_t ip = (uintptr_t)_Unwind_GetIP(context);
    if (ip == 0) return _URC_END_OF_STACK;
    /* ip is the return address, which follows the call: a call to a noreturn
     * helper may end its function */
    walk->visit(quest_function_start((void *)(ip - 1)), walk->arg);
    return _URC_NO_REASON;
}

static void quest_walk_stack(QFrameVisitor visit, void *arg) {
    QStackWalk walk = { visit, arg };
    _Unwind_Backtrace(quest_walk_frame, &walk);
}

static void quest_print_live_frame(const void *start, void *arg) {
    quest_frames_add((QFramePrinter *)arg, start, 1);
}

static void quest_capture_frame(const void *start, void *arg) {
    QTrace *trace = (QTrace *)arg;
    if (quest_frame_name(start) == NULL) return;
    if (trace->n_runs > 0 && trace->starts[trace->n_runs - 1] == start) {
        trace->counts[trace->n_runs - 1]++;
    } else if (trace->n_runs < Q_MAX_TRACE_RUNS) {
        trace->starts[trace->n_runs] = start;
        trace->counts[trace->n_runs] = 1;
        trace->n_runs++;
    } else {
        trace->truncated = true;
    }
}
#endif

/* Prints the frames of the live stack, where an uncaught error is being
 * reported */
static void quest_print_live_frames(void) {
#ifdef Q_HAVE_UNWIND
    QFramePrinter printer = { NULL, 0 };
    quest_walk_stack(quest_print_live_frame, &printer);
    quest_frames_flush(&printer);
#endif
}

/* The frames of the live stack, captured at a raise a handler might catch and
 * raise again (§5.4) */
static const QTrace *quest_capture_trace(void) {
#ifdef Q_HAVE_UNWIND
    QTrace *trace = (QTrace *)quest_alloc_atomic(sizeof(QTrace));
    trace->n_runs = 0;
    trace->truncated = false;
    quest_walk_stack(quest_capture_frame, trace);
    return trace;
#else
    return NULL;
#endif
}

static void quest_print_trace(const QTrace *trace) {
    QFramePrinter printer = { NULL, 0 };
    for (int i = 0; i < trace->n_runs; ++i) quest_frames_add(&printer, trace->starts[i], trace->counts[i]);
    quest_frames_flush(&printer);
    if (trace->truncated) fprintf(stderr, "  ... (traceback truncated)\n");
}

/* Ends the program after an error's message has been printed, printing the site
   it was raised at, if known, which the driver reads to locate the error in the
   source (docs/exceptions.md §2.2), and the frames running there: those
   captured at the raise, if any, else the live stack's */
static Q_NORETURN void quest_fail_with(const char *loc, const QTrace *trace) {
    if (loc != NULL) fprintf(stderr, "  at %s\n", loc);
    if (trace != NULL) {
        quest_print_trace(trace);
    } else {
        quest_print_live_frames();
    }
    exit(1);
}

static Q_NORETURN void quest_fail_at(const char *loc) {
    quest_fail_with(loc, NULL);
}

/* Whether a handler from h out will catch exc (docs/exceptions.md §5.1): 1 if
   one will, 0 if none will, -1 if one might (its patterns are computed when it
   runs) */
static int quest_handlers_catch(const QExceptionHandler *h, const QException *exc) {
    for (; h != NULL; h = h->prev) {
        if (h->n_catches == Q_CATCH_ALL) return 1;
        if (h->n_catches == Q_CATCH_UNKNOWN) return -1;
        for (int64_t i = 0; i < h->n_catches; ++i) {
            if (h->catches[i] == exc) return 1;
        }
    }
    return 0;
}

void quest_reraise(QExceptionState state) {
    switch (quest_handlers_catch(quest_current_exception_handler, state.exc)) {
        case 0: {
            const char *name = (state.exc != NULL && state.exc->name != NULL) ? state.exc->name : "<unknown>";
            fprintf(stderr, "Exception: %s\n", name);
            quest_fail_with(state.loc, state.trace);
        }
        case -1:
            if (state.trace == NULL) state.trace = quest_capture_trace();
            break;
        default:
            break;
    }
    quest_current_exception = state;
    longjmp(quest_current_exception_handler->env_jmp, 1);
}

void quest_raise_at(const QException *exc, QVal payload, const char *loc) {
    quest_reraise((QExceptionState){ exc, payload, loc, NULL });
}

void quest_raise(const QException *exc, QVal payload) {
    quest_raise_at(exc, payload, NULL);
}

void quest_raise_array_error_at(const char *loc) {
    quest_raise_at(&quest_exc_arrayOp_error, Q_OK_VAL, loc);
}

void quest_raise_array_error(void) {
    quest_raise_array_error_at(NULL);
}

void quest_raise_string_error(void) {
    quest_raise(&quest_exc_string_error, Q_OK_VAL);
}

void quest_raise_variant_error_at(const char *loc) {
    quest_raise_at(&quest_exc_variant_error, Q_OK_VAL, loc);
}

void quest_raise_variant_error(void) {
    quest_raise_variant_error_at(NULL);
}

void quest_raise_dynamic_error_at(const char *loc) {
    quest_raise_at(&quest_exc_dynamic_error, Q_OK_VAL, loc);
}

void quest_raise_dynamic_error(void) {
    quest_raise_dynamic_error_at(NULL);
}

void quest_option_ordinal_error_at(int64_t n, int64_t count, const char *loc) {
    fprintf(stderr, "Option ordinal %lld out of bounds (0 <= ordinal < %lld)\n", (long long)n, (long long)count);
    quest_fail_at(loc);
}

void quest_option_ordinal_error(int64_t n, int64_t count) {
    quest_option_ordinal_error_at(n, count, NULL);
}

void quest_raise_writer_error(void) {
    quest_raise(&quest_exc_writer_error, Q_OK_VAL);
}

void quest_raise_reader_error(void) {
    quest_raise(&quest_exc_reader_error, Q_OK_VAL);
}

void quest_raise_ascii_error(void) {
    quest_raise(&quest_exc_ascii_error, Q_OK_VAL);
}

void quest_raise_int_error_at(const char *loc) {
    quest_raise_at(&quest_exc_int_error, Q_OK_VAL, loc);
}

void quest_raise_int_error(void) {
    quest_raise_int_error_at(NULL);
}

void quest_raise_real_error_at(const char *loc) {
    quest_raise_at(&quest_exc_real_error, Q_OK_VAL, loc);
}

void quest_raise_real_error(void) {
    quest_raise_real_error_at(NULL);
}

void quest_raise_word_error(void) {
    quest_raise(&quest_exc_word_error, Q_OK_VAL);
}

void quest_raise_system_error(void) {
    quest_raise(&quest_exc_system_error, Q_OK_VAL);
}

/* Reads back the decimal d1.d2d3...dn * 10^x. */
static double quest_decimal_value(const char *digits, int nd, int x) {
    char buf[48];
    snprintf(buf, sizeof(buf), "%c.%.*se%d", digits[0], nd - 1, digits + 1, x);
    return strtod(buf, NULL);
}

/* Adds delta (+1 or -1) to the last of nd digits; returns false when the result
 * would gain or lose a digit. */
static int quest_digits_step(char *digits, int nd, int delta) {
    for (int i = nd - 1; i >= 0; i--) {
        int d = digits[i] - '0' + delta;
        if (d >= 0 && d <= 9) { digits[i] = (char)('0' + d); return digits[0] != '0'; }
        digits[i] = delta > 0 ? '0' : '9';
    }
    return 0;
}

/* The shortest decimal digits that read back as r (finite, > 0), choosing the
   one nearest r when several of that length do, as Python's repr does. Sets *x
   so that r is about d1.d2d3... * 10^x; returns the digit count. */
static int quest_shortest_digits(double r, char *digits, int *x) {
    for (int p = 1; p <= 17; p++) {
        char sci[40];
        snprintf(sci, sizeof(sci), "%.*e", p - 1, r);  /* the correctly rounded p-digit decimal */
        char *e = strchr(sci, 'e');
        int nd = 0;
        for (char *c = sci; c < e; c++) if (*c != '.') digits[nd++] = *c;
        *x = atoi(e + 1);
        if (quest_decimal_value(digits, nd, *x) == r) return nd;
        /* Beside a power of two the doubles' spacing differs on each side, so a
           p-digit neighbor of the nearest decimal can read back as r when the
           nearest does not. */
        for (int delta = -1; delta <= 1; delta += 2) {
            char cand[20];
            memcpy(cand, digits, (size_t)nd);
            if (quest_digits_step(cand, nd, delta) && quest_decimal_value(cand, nd, *x) == r) {
                memcpy(digits, cand, (size_t)nd);
                return nd;
            }
        }
    }
    return 17;  /* not reached: 17 significant digits always read back */
}

/* Formats r without its sign, as the interpreter does (Python's repr): the
   shortest digits that read back as r, in fixed notation for 1e-5 <= |r| < 1e16
   (with ".0" when integral), otherwise d[.ddd]e+XX; an infinity is "inf". The
   caller writes the sign, "~" for conv.real and "-" for displays. See
   docs/type-system.md §6.3.1. */
static void quest_format_real(double r, char *out, size_t n) {
    r = fabs(r);
    if (isinf(r)) { snprintf(out, n, "inf"); return; }
    if (r == 0.0) { snprintf(out, n, "0.0"); return; }
    char digits[20];
    int x;
    int nd = quest_shortest_digits(r, digits, &x);
    while (nd > 1 && digits[nd - 1] == '0') nd--;
    digits[nd] = '\0';
    int decpt = x + 1;  /* r = 0.d1d2... * 10^decpt */
    if (decpt <= -4 || decpt > 16) {
        if (nd == 1) snprintf(out, n, "%ce%c%02d", digits[0], x < 0 ? '-' : '+', abs(x));
        else snprintf(out, n, "%c.%se%c%02d", digits[0], digits + 1, x < 0 ? '-' : '+', abs(x));
    } else if (decpt <= 0) {
        snprintf(out, n, "0.%.*s%s", -decpt, "0000", digits);
    } else if (decpt >= nd) {
        snprintf(out, n, "%s%.*s.0", digits, decpt - nd, "0000000000000000");
    } else {
        snprintf(out, n, "%.*s.%s", decpt, digits, digits + decpt);
    }
}

/* Writes a real as the interpreter does: conv.real's digits, with "-" rather
 * than "~" for negatives */
static void quest_put_real(double r) {
    char buf[48];
    quest_format_real(r, buf, sizeof(buf));
    if (signbit(r)) putchar('-');
    fputs(buf, stdout);
}

/* Writes a character of a char or string literal, escaped as the interpreter
 * does */
static void quest_put_escaped_char(unsigned char c, char quote) {
    switch (c) {
        case '\n': fputs("\\n", stdout); return;
        case '\t': fputs("\\t", stdout); return;
        case '\r': fputs("\\r", stdout); return;
        case '\\': fputs("\\\\", stdout); return;
        default: break;
    }
    if (c == (unsigned char)quote) {
        putchar('\\');
        putchar(c);
    } else if (c >= 32 && c <= 126) {
        putchar(c);
    } else {
        printf("\\x%02x", c);
    }
}

/* Writes prefix, val, suffix, and a newline. kind says how to write the value,
 * as the interpreter writes a value of that type (format_value_with_type): a
 * base type (Int, Real, Bool, Char, String, Ok, or Word), "fun" for a function,
 * "hidden" for a value of an abstract type, and anything else as <val>
 * (compiled code writes values of other types with quest_print_typed). */
void quest_print_value(const char *prefix, QVal val, const char *kind, const char *suffix) {
    fputs(prefix, stdout);
    if (strcmp(kind, "Int") == 0) {
        printf("%lld", (long long)val.i);
    } else if (strcmp(kind, "Real") == 0) {
        quest_put_real(val.r);
    } else if (strcmp(kind, "Bool") == 0) {
        fputs(val.i ? "true" : "false", stdout);
    } else if (strcmp(kind, "Char") == 0) {
        putchar('\'');
        quest_put_escaped_char((unsigned char)val.i, '\'');
        putchar('\'');
    } else if (strcmp(kind, "String") == 0) {
        const QString *s = (const QString *)val.p;
        putchar('"');
        for (int64_t i = 0; s != NULL && i < s->length; ++i) quest_put_escaped_char((unsigned char)s->data[i], '"');
        putchar('"');
    } else if (strcmp(kind, "Ok") == 0) {
        fputs("ok", stdout);
    } else if (strcmp(kind, "Word") == 0 || strcmp(kind, "Word.T") == 0 || strcmp(kind, "word.T") == 0) {
        printf("16#%llx#", (unsigned long long)val.u);
    } else if (strcmp(kind, "fun") == 0) {
        fputs("<fun>", stdout);
    } else if (strcmp(kind, "hidden") == 0) {
        fputs("<hidden>", stdout);
    } else {
        fputs("<val>", stdout);
    }
    fputs(suffix, stdout);
    putchar('\n');
}

/* Writes the result of an expression of type type_name, whose value is
 * formatted by that name (see quest_print_value); nothing for Ok */
void quest_print_val(QVal val, const char *type_name) {
    if (type_name == NULL || strcmp(type_name, "Ok") == 0) return;
    bool is_word = strcmp(type_name, "Word") == 0 || strcmp(type_name, "word.T") == 0;
    char suffix[256];
    snprintf(suffix, sizeof suffix, " : %s", is_word ? "Word.T" : type_name);
    quest_print_value("", val, type_name, suffix);
}

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
typedef struct QTypeDescriptorEntry {
    const QTypeDescriptor       *desc;
    struct QTypeDescriptorEntry *next;
} QTypeDescriptorEntry;

#define Q_TYPE_INTERN_TABLE_SIZE 256
static QTypeDescriptorEntry *quest_type_intern_buckets[Q_TYPE_INTERN_TABLE_SIZE];
static bool quest_type_intern_initialized = false;

/* FNV-1a 64-bit hash for descriptor canonical names */
static uint64_t quest_hash_string(const char *s) {
    uint64_t h = 14695981039346656037ULL;
    if (s == NULL) return h;
    for (; *s; ++s) {
        h ^= (uint64_t)(unsigned char)(*s);
        h *= 1099511628211ULL;
    }
    return h;
}

static void quest_init_type_intern_table(void) {
    if (quest_type_intern_initialized) return;
    quest_type_intern_initialized = true;

    /* Register base types in table */
    const QTypeDescriptor *base_descs[] = {
        &quest_type_Int,
        &quest_type_Real,
        &quest_type_Bool,
        &quest_type_Char,
        &quest_type_String,
        &quest_type_Ok,
        &quest_type_EmptyTuple,
        NULL
    };

    for (int i = 0; base_descs[i] != NULL; ++i) {
        const QTypeDescriptor *d = base_descs[i];
        uint64_t h = quest_hash_string(d->name) % Q_TYPE_INTERN_TABLE_SIZE;
        QTypeDescriptorEntry *entry = (QTypeDescriptorEntry *)quest_alloc(sizeof(QTypeDescriptorEntry));
        entry->desc = d;
        entry->next = quest_type_intern_buckets[h];
        quest_type_intern_buckets[h] = entry;
    }
}

const QTypeDescriptor *quest_intern_type_descriptor(const QTypeDescriptor *desc) {
    if (desc == NULL) return NULL;
    quest_init_type_intern_table();

    /* Check if already in table by canonical name match */
    uint64_t h = quest_hash_string(desc->name) % Q_TYPE_INTERN_TABLE_SIZE;
    for (QTypeDescriptorEntry *cur = quest_type_intern_buckets[h]; cur != NULL; cur = cur->next) {
        if (cur->desc == desc) {
            return cur->desc;
        }
        if (cur->desc->name != NULL && desc->name != NULL && strcmp(cur->desc->name, desc->name) == 0) {
            return cur->desc;
        }
    }

    /* Not found: insert into bucket */
    QTypeDescriptorEntry *entry = (QTypeDescriptorEntry *)quest_alloc(sizeof(QTypeDescriptorEntry));
    entry->desc = desc;
    entry->next = quest_type_intern_buckets[h];
    quest_type_intern_buckets[h] = entry;
    return desc;
}

static char *quest_dup_str(const char *s) {
    if (s == NULL) return NULL;
    size_t len = strlen(s);
    char *copy = (char *)quest_alloc_atomic(len + 1);
    memcpy(copy, s, len + 1);
    return copy;
}

#define Q_SUBTYPE_TRAIL_MAX 64
typedef struct QSubtypePair {
    const QTypeDescriptor *sub;
    const QTypeDescriptor *super_type;
} QSubtypePair;

static Q_THREAD_LOCAL QSubtypePair quest_subtyping_trail[Q_SUBTYPE_TRAIL_MAX];
static Q_THREAD_LOCAL size_t quest_subtyping_trail_len = 0;

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
    if (quest_subtyping_trail_len >= Q_SUBTYPE_TRAIL_MAX) {
        return false;
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
                if (!quest_is_subtype(s->elements[i].type, t->elements[i].type)) {
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
        quest_record_dicts = (QRecordDictEntry *)quest_alloc(sizeof(QRecordDictEntry) * quest_record_dicts_capacity);
        memset(quest_record_dicts, 0, sizeof(QRecordDictEntry) * quest_record_dicts_capacity);
        for (size_t i = 0; i < old_capacity; ++i) {
            if (old[i].view != NULL) *quest_record_dict_slot(old[i].view, old[i].layout) = old[i];
        }
    }
    QRecordDictEntry *e = quest_record_dict_slot(view, layout);
    if (e->view == NULL) {
        e->view = view;
        e->layout = layout;
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
    size_t *dict = (size_t *)quest_alloc(sizeof(size_t) * slots + sizeof(QRecordStoredTypes));
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
                stored_types = (const QTypeDescriptor **)quest_alloc(sizeof(const QTypeDescriptor *) * n);
                memset((void *)stored_types, 0, sizeof(const QTypeDescriptor *) * n);
            }
            stored_types[j] = lf->type;
        }
    }
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
    QProxy *proxy = (QProxy *)quest_alloc(sizeof(QProxy));
    proxy->orig = orig;
    proxy->stored = from;
    proxy->view = to;
    if (to->kind == QTYPE_KIND_OPTION) {
        const QVariantTypeDescriptor *f_meta = (const QVariantTypeDescriptor *)from->extra;
        const QVariantTypeDescriptor *t_meta = (const QVariantTypeDescriptor *)to->extra;
        size_t n = f_meta != NULL ? f_meta->case_count : 0;
        int64_t *tags = (int64_t *)quest_alloc(sizeof(int64_t) * (n > 0 ? n : 1));
        for (size_t i = 0; i < n; ++i) {
            tags[i] = -1;
            for (size_t j = 0; t_meta != NULL && j < t_meta->case_count; ++j) {
                if (strcmp(t_meta->cases[j].name, f_meta->cases[i].name) == 0) {
                    tags[i] = (int64_t)j;
                    break;
                }
            }
        }
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
        proxy->cache = (QVal *)quest_alloc(sizeof(QVal) * n + n);
        proxy->cached = (uint8_t *)(proxy->cache + n);
    }
    if (!proxy->cached[i]) {
        proxy->cache[i] = quest_convert(v, from, to);
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
    quest_slot_write((char *)proxy->orig + fe->offset, fe->type == te->type ? v : quest_convert(v, te->type, fe->type));
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
 * decides it for the type (may_be_proxied in codegen/layout.py), or less often:
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
 * codegen/layout.py) */
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
    char *dst = (char *)quest_alloc(to->size > 0 ? to->size : sizeof(void *));
    if (to->kind == QTYPE_KIND_TUPLE) {
        const QTupleTypeDescriptor *f_meta = (const QTupleTypeDescriptor *)from->extra;
        const QTupleTypeDescriptor *t_meta = (const QTupleTypeDescriptor *)to->extra;
        for (size_t i = 0; f_meta != NULL && i < t_meta->element_count && i < f_meta->element_count; ++i) {
            if (t_meta->elements[i].is_var) quest_layout_conversion_error(from, to);
            QVal e = quest_tuple_element(v.p, from, i);
            quest_slot_write(dst + t_meta->elements[i].offset,
                             quest_convert(e, f_meta->elements[i].type, t_meta->elements[i].type));
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
            QVal e = quest_option_element(v.p, from, i);
            quest_slot_write((void *)slot, quest_convert(e, quest_payload_element_type(fc->payload_type, i),
                                                         quest_payload_element_type(tc->payload_type, i)));
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
    char *payload = (char *)quest_alloc(t_meta->payload_size > 0 ? t_meta->payload_size : sizeof(QVal));
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
        QInstNode *nodes = (QInstNode *)quest_alloc(sizeof(QInstNode) * capacity);
        if (w->count > 0) memcpy(nodes, w->nodes, sizeof(QInstNode) * w->count);
        w->nodes = nodes;
        w->capacity = capacity;
    }
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
    char *out = (char *)quest_alloc(cap);
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
    void *copy = quest_alloc(size);
    memcpy(copy, src, size);
    return copy;
}

/* Fills the instance of template node n, whose descriptor was allocated
 * already */
static void quest_inst_fill(const QInstContext *cx, QInstNode *n) {
    const QTypeDescriptor *d = n->tmpl;
    QTypeDescriptor *out = n->inst;
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
            out->extra = c;
            break;
        }
        case QTYPE_KIND_ARRAY: {
            QArrayTypeDescriptor *c = (QArrayTypeDescriptor *)quest_alloc(sizeof(QArrayTypeDescriptor));
            c->element_type = quest_inst_of(cx, ((const QArrayTypeDescriptor *)d->extra)->element_type);
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
                    (const QTypeDescriptor **)quest_alloc(sizeof(QTypeDescriptor *) * m->quantifier_count);
                for (size_t i = 0; i < m->quantifier_count; ++i) bounds[i] = quest_inst_of(cx, m->quantifier_bounds[i]);
                c->quantifier_bounds = bounds;
            }
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
            out->extra = c;
            break;
        }
        case QTYPE_KIND_EXCEPTION: {
            QExceptionTypeDescriptor *c = (QExceptionTypeDescriptor *)quest_alloc(sizeof(QExceptionTypeDescriptor));
            c->payload_type = quest_inst_of(cx, ((const QExceptionTypeDescriptor *)d->extra)->payload_type);
            out->extra = c;
            break;
        }
        case QTYPE_KIND_OPAQUE: {
            const QOpaqueTypeDescriptor *m = (const QOpaqueTypeDescriptor *)d->extra;
            QOpaqueTypeDescriptor *c = (QOpaqueTypeDescriptor *)quest_alloc(sizeof(QOpaqueTypeDescriptor));
            const QTypeDescriptor **args = (const QTypeDescriptor **)quest_alloc(sizeof(QTypeDescriptor *) * (m->arg_count + 1));
            for (size_t i = 0; i < m->arg_count; ++i) args[i] = quest_inst_of(cx, m->args[i]);
            c->arg_count = m->arg_count;
            c->args = args;
            c->rep = m->rep;
            out->extra = c;
            break;
        }
        case QTYPE_KIND_HOLE: {
            const QHoleDescriptor *h = (const QHoleDescriptor *)d->extra;
            QStoredDescriptor *c = (QStoredDescriptor *)quest_alloc(sizeof(QStoredDescriptor));
            c->type = cx->args[h->index];
            c->storage = quest_inst_of(cx, h->storage);
            c->viewed = false;
            out->kind = QTYPE_KIND_STORED;
            out->name = c->type != NULL ? c->type->name : d->name;
            out->size = sizeof(QVal);
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
        int64_t *index = (int64_t *)quest_alloc(sizeof(int64_t) * (n ? n : 1));
        const QTypeDescriptor **from = (const QTypeDescriptor **)quest_alloc(sizeof(void *) * (n ? n : 1));
        const QTypeDescriptor **to = (const QTypeDescriptor **)quest_alloc(sizeof(void *) * (n ? n : 1));
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
        const QTypeDescriptor **from = (const QTypeDescriptor **)quest_alloc(sizeof(void *) * (n ? n : 1));
        const QTypeDescriptor **to = (const QTypeDescriptor **)quest_alloc(sizeof(void *) * (n ? n : 1));
        for (size_t k = 0; k < n; ++k) {
            to[k] = tb->elements[k].type;
            from[k] = ta != NULL && k < ta->element_count ? quest_view_from(ta->elements[k].type, to[k]) : NULL;
        }
        m->from = from;
        m->to = to;
        return;
    }
    if ((a->kind == QTYPE_KIND_VARIANT || a->kind == QTYPE_KIND_OPTION) && b->kind == a->kind) {
        const QVariantTypeDescriptor *va = (const QVariantTypeDescriptor *)a->extra;
        const QVariantTypeDescriptor *vb = (const QVariantTypeDescriptor *)b->extra;
        size_t na = va != NULL ? va->case_count : 0, nb = vb != NULL ? vb->case_count : 0;
        int64_t *index = (int64_t *)quest_alloc(sizeof(int64_t) * (na ? na : 1));
        for (size_t i = 0; i < na; ++i) {
            const QVariantCaseDescriptor *c = quest_case_named(vb, va->cases[i].name);
            if (c == NULL) quest_raise_dynamic_error();
            index[va->cases[i].tag_index] = c->tag_index;
        }
        m->index = index;
        if (a->kind == QTYPE_KIND_VARIANT) {
            const QTypeDescriptor **from = (const QTypeDescriptor **)quest_alloc(sizeof(void *) * (nb ? nb : 1));
            const QTypeDescriptor **to = (const QTypeDescriptor **)quest_alloc(sizeof(void *) * (nb ? nb : 1));
            for (size_t k = 0; k < nb; ++k) {
                const QVariantCaseDescriptor *c = quest_case_named(va, vb->cases[k].name);
                to[k] = vb->cases[k].payload_type;
                from[k] = c != NULL ? quest_view_from(c->payload_type, to[k]) : NULL;
            }
            m->from = from;
            m->to = to;
            return;
        }
        /* An option's cases' components, flattened (a payload that is not a
         * tuple is one) */
        size_t *start = (size_t *)quest_alloc(sizeof(size_t) * (nb + 1));
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
        const QTypeDescriptor **from = (const QTypeDescriptor **)quest_alloc(sizeof(void *) * (total ? total : 1));
        const QTypeDescriptor **to = (const QTypeDescriptor **)quest_alloc(sizeof(void *) * (total ? total : 1));
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
    QViewMapEntry *e = (QViewMapEntry *)quest_alloc(sizeof(QViewMapEntry));
    e->map.actual = actual;
    e->map.bound = bound;
    quest_fill_view_map(&e->map);
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
        if (w.nodes[i].has_hole) w.nodes[i].inst = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor));
    }
    QInstContext cx = { &w, args, arg_count };
    for (size_t i = 0; i < w.count; ++i) {
        if (w.nodes[i].has_hole) quest_inst_fill(&cx, &w.nodes[i]);
    }
    const QTypeDescriptor *inst = quest_inst_of(&cx, template_desc);

    QInstCacheEntry *e = (QInstCacheEntry *)quest_alloc(sizeof(QInstCacheEntry));
    e->tmpl = template_desc;
    e->arg_count = arg_count;
    e->args = (const QTypeDescriptor **)quest_alloc(sizeof(QTypeDescriptor *) * (arg_count + 1));
    if (arg_count > 0) memcpy((void *)e->args, args, sizeof(QTypeDescriptor *) * arg_count);
    e->inst = inst;
    e->next = quest_inst_cache[bucket];
    quest_inst_cache[bucket] = e;
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

/* Writes a string literal, escaped as the interpreter does */
static void quest_put_string(const QString *s) {
    putchar('"');
    for (int64_t i = 0; s != NULL && i < s->length; ++i) quest_put_escaped_char((unsigned char)s->data[i], '"');
    putchar('"');
}

/* The tuples, records, and arrays being written, so that a cyclic value is cut
 * off as the interpreter does */
#define Q_PRINT_NESTING_MAX 256
static const void *quest_print_nesting[Q_PRINT_NESTING_MAX];
static int quest_print_depth = 0;

/* Starts writing the aggregate at p, or returns false (writing opening and "
 * ... end") if p is already being written; a true result is matched by a call
 * of quest_print_leave */
static bool quest_print_enter(const void *p, const char *opening) {
    for (int i = 0; p != NULL && i < quest_print_depth && i < Q_PRINT_NESTING_MAX; ++i) {
        if (quest_print_nesting[i] == p) {
            printf("%s ... end", opening);
            return false;
        }
    }
    if (quest_print_depth < Q_PRINT_NESTING_MAX) quest_print_nesting[quest_print_depth] = p;
    ++quest_print_depth;
    fputs(opening, stdout);
    return true;
}

static void quest_print_leave(void) {
    --quest_print_depth;
}

static void quest_put_value(QVal v, const QTypeDescriptor *t, const QTypeDescriptor *witness);

/* Writes the elements of a tuple of type t, or of the payload (of tuple type t)
 * of an option of type opt_t, with its type components among them (through a
 * proxy, or not) */
static void quest_put_elements(const void *v, const QTypeDescriptor *t, const QTypeDescriptor *opt_t,
                               const QTypeDescriptor *witness) {
    const QTupleTypeDescriptor *meta = (const QTupleTypeDescriptor *)t->extra;
    if (meta == NULL) return;
    size_t c = 0;
    for (size_t i = 0; i <= meta->element_count; ++i) {
        for (; c < meta->component_count && meta->components[c].position <= i; ++c) {
            printf(" %s", meta->components[c].text);
        }
        if (i == meta->element_count) break;
        const QTupleElementDescriptor *e = &meta->elements[i];
        putchar(' ');
        if (e->name != NULL && e->name[0] != '\0') printf("%s=", e->name);
        QVal ev = opt_t != NULL ? quest_option_element(v, opt_t, i) : quest_tuple_element(v, t, i);
        quest_put_value(ev, e->type, witness);
    }
}

/* Writes a tuple-shaped block as `tuple ... end` */
static void quest_put_tuple(const void *v, const QTypeDescriptor *t, const QTypeDescriptor *opt_t,
                            const QTypeDescriptor *witness) {
    if (!quest_print_enter(quest_unproxy(v), "tuple")) return;
    quest_put_elements(v, t, opt_t, witness);
    fputs(" end", stdout);
    quest_print_leave();
}

/* Writes a value of the type t as the interpreter does
 * (format_value_with_type). witness is the type component of the auto value
 * whose components are being written, which a component's type refers to as its
 * type parameter. */
static void quest_put_value(QVal v, const QTypeDescriptor *t, const QTypeDescriptor *witness) {
    if (t == NULL) {
        fputs("<val>", stdout);
        return;
    }
    switch (t->kind) {
        case QTYPE_KIND_INT:
            printf("%lld", (long long)v.i);
            return;
        case QTYPE_KIND_REAL:
            quest_put_real(v.r);
            return;
        case QTYPE_KIND_BOOL:
            fputs(v.i ? "true" : "false", stdout);
            return;
        case QTYPE_KIND_CHAR:
            putchar('\'');
            quest_put_escaped_char((unsigned char)v.i, '\'');
            putchar('\'');
            return;
        case QTYPE_KIND_STRING:
            quest_put_string((const QString *)v.p);
            return;
        case QTYPE_KIND_OK:
            fputs("ok", stdout);
            return;
        case QTYPE_KIND_FUN:
            fputs("<fun>", stdout);
            return;
        case QTYPE_KIND_TUPLE:
            quest_put_tuple(v.p, t, NULL, witness);
            return;
        case QTYPE_KIND_RECORD: {
            const QRecordVal *rec = (const QRecordVal *)v.p;
            const QRecordTypeDescriptor *meta = (const QRecordTypeDescriptor *)t->extra;
            if (rec == NULL || meta == NULL || meta->field_count == 0) {
                fputs("record end", stdout);
                return;
            }
            if (!quest_print_enter(rec->val, "record")) return;
            /* The fields are sorted by name, as the interpreter writes them */
            for (size_t i = 0; i < meta->field_count; ++i) {
                printf(" %s=", meta->fields[i].name);
                quest_put_value(quest_record_field_value(*rec, t, i), meta->fields[i].type, witness);
            }
            fputs(" end", stdout);
            quest_print_leave();
            return;
        }
        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION: {
            const QVariantTypeDescriptor *meta = (const QVariantTypeDescriptor *)t->extra;
            const char *opening = t->kind == QTYPE_KIND_VARIANT ? "variant" : "option";
            if (v.p == NULL || meta == NULL) {
                fputs("<val>", stdout);
                return;
            }
            /* A variant is a QVariantVal; an option points to its tag followed
             * by its payload, laid out as the payload's tuple type; an option
             * may be a proxy (quest_option_tag, quest_option_element) */
            int64_t tag = t->kind == QTYPE_KIND_VARIANT ? ((const QVariantVal *)v.p)->tag : quest_option_tag(v.p);
            if (tag < 0 || (size_t)tag >= meta->case_count) {
                fputs("<val>", stdout);
                return;
            }
            const QVariantCaseDescriptor *c = &meta->cases[tag];
            printf("%s %s", opening, c->name);
            const QTypeDescriptor *payload_type = c->payload_type;
            if (payload_type != NULL && payload_type->kind != QTYPE_KIND_OK) {
                fputs(" with ", stdout);
                if (t->kind == QTYPE_KIND_VARIANT) {
                    quest_put_value(((const QVariantVal *)v.p)->payload, payload_type, witness);
                } else {
                    if (payload_type->kind == QTYPE_KIND_TUPLE) {
                        quest_put_tuple(v.p, payload_type, t, witness);
                    } else {
                        quest_put_value(quest_option_element(v.p, t, 0), payload_type, witness);
                    }
                }
            }
            fputs(" end", stdout);
            return;
        }
        case QTYPE_KIND_ARRAY: {
            const QTypeDescriptor *elem = ((const QArrayTypeDescriptor *)t->extra)->element_type;
            if (v.p == NULL) {
                fputs("array of end", stdout);
                return;
            }
            if (!quest_print_enter(v.p, "array of")) return;
            /* Each element is its QVal form (records and variants boxed) */
            int64_t length = ((const QArray *)v.p)->length;
            for (int64_t i = 0; i < length; ++i) {
                putchar(' ');
                quest_put_value(((const QArray *)v.p)->data[i], elem, witness);
            }
            fputs(" end", stdout);
            quest_print_leave();
            return;
        }
        case QTYPE_KIND_AUTO: {
            const QAuto *a = (const QAuto *)v.p;
            const QAutoTypeDescriptor *meta = (const QAutoTypeDescriptor *)t->extra;
            if (a == NULL || meta == NULL) {
                fputs("<val>", stdout);
                return;
            }
            printf("auto :%s with", a->type_desc != NULL ? a->type_desc->name : "?");
            const char *payload = (const char *)a->payload.p;
            for (size_t i = 0; payload != NULL && i < meta->component_count; ++i) {
                const QAutoComponentDescriptor *c = &meta->components[i];
                QVal cv = quest_slot_read(payload + c->offset);
                printf(" %s=", c->name);
                quest_put_value(cv, c->type, a->type_desc);
            }
            fputs(" end", stdout);
            return;
        }
        case QTYPE_KIND_EXCEPTION: {
            const QException *exc = (const QException *)v.p;
            printf("exception %s", exc != NULL && exc->name != NULL ? exc->name : "?");
            return;
        }
        case QTYPE_KIND_BOUND_VAR:
            /* An auto value's components refer to its type component as the
             * innermost type parameter */
            if (witness != NULL && t == &quest_type_bound_vars[0]) {
                quest_put_value(v, witness, NULL);
            } else {
                fputs("<hidden>", stdout);
            }
            return;
        case QTYPE_KIND_STORED:
            /* A value laid out as generic code stores its type argument:
             * converted to that type's own layout */
            quest_put_value(quest_convert(v, t, quest_stored_type(t)), quest_stored_type(t), witness);
            return;
        case QTYPE_KIND_HOLE:
            /* Only in descriptor templates, which no value has */
            fputs("<hidden>", stdout);
            return;
        case QTYPE_KIND_OPAQUE:
            /* Word.T is a library type with literals of its own; any other
             * abstract type's values are hidden */
            if (t->name != NULL && (strcmp(t->name, "Word.T") == 0 || strcmp(t->name, "word.T") == 0)) {
                printf("16#%llx#", (unsigned long long)v.u);
            } else {
                fputs("<hidden>", stdout);
            }
            return;
    }
    fputs("<val>", stdout);
}

void quest_print_typed(const char *prefix, QVal val, const QTypeDescriptor *type, const char *suffix) {
    fputs(prefix, stdout);
    quest_put_value(val, type, NULL);
    fputs(suffix, stdout);
    putchar('\n');
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
        int64_t *tagmap = (int64_t *)quest_alloc(sizeof(int64_t) * s_meta->case_count);
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
        cached = (QVariantAdapterCacheEntry *)quest_alloc(sizeof(QVariantAdapterCacheEntry));
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

/* ------------------------------------------------------------------------- */
/* Type Descriptor Constructors & Helpers                                    */
/* ------------------------------------------------------------------------- */

const QTypeDescriptor *quest_make_array_descriptor(const QTypeDescriptor *element_desc) {
    quest_init_type_intern_table();

    const char *elem_name = (element_desc && element_desc->name) ? element_desc->name : "Unknown";
    size_t name_len = strlen("Array()") + strlen(elem_name) + 1;
    char *arr_name = (char *)quest_alloc_atomic(name_len);
    snprintf(arr_name, name_len, "Array(%s)", elem_name);

    /* Check if already interned */
    uint64_t h = quest_hash_string(arr_name) % Q_TYPE_INTERN_TABLE_SIZE;
    for (QTypeDescriptorEntry *cur = quest_type_intern_buckets[h]; cur != NULL; cur = cur->next) {
        if (cur->desc->name != NULL && strcmp(cur->desc->name, arr_name) == 0) {
            return cur->desc;
        }
    }

    /* Allocate array descriptor */
    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor));
    desc->kind = QTYPE_KIND_ARRAY;
    desc->name = arr_name;
    desc->size = sizeof(void *);
    desc->alignment = sizeof(void *);
    desc->is_subtype = quest_is_subtype;

    QArrayTypeDescriptor *arr_meta = (QArrayTypeDescriptor *)quest_alloc(sizeof(QArrayTypeDescriptor));
    arr_meta->element_type = element_desc;
    desc->extra = arr_meta;

    return quest_intern_type_descriptor(desc);
}

const QTypeDescriptor *quest_make_opaque_descriptor(const char *name) {
    /* Opaque types use unique pointer identity for encapsulation */
    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor));
    desc->kind = QTYPE_KIND_OPAQUE;
    desc->name = name != NULL ? quest_dup_str(name) : "Opaque";
    desc->size = sizeof(QVal);
    desc->alignment = sizeof(QVal);
    desc->is_subtype = quest_is_subtype;
    desc->extra = NULL;
    /* Do NOT intern: each opaque type creation has unique nominal identity */
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
    QAbstractTypeEntry *e = (QAbstractTypeEntry *)quest_alloc(sizeof(QAbstractTypeEntry));
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
    quest_init_type_intern_table();
    const char *rec_name = name ? name : "Record end";

    uint64_t h = quest_hash_string(rec_name) % Q_TYPE_INTERN_TABLE_SIZE;
    for (QTypeDescriptorEntry *cur = quest_type_intern_buckets[h]; cur != NULL; cur = cur->next) {
        if (cur->desc->name != NULL && strcmp(cur->desc->name, rec_name) == 0) {
            return cur->desc;
        }
    }

    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor));
    desc->kind = QTYPE_KIND_RECORD;
    desc->name = quest_dup_str(rec_name);
    desc->size = size;
    desc->alignment = alignment > 0 ? alignment : sizeof(void *);
    desc->is_subtype = quest_is_subtype;

    size_t meta_size = sizeof(QRecordTypeDescriptor) + sizeof(QRecordFieldDescriptor) * field_count;
    QRecordTypeDescriptor *meta = (QRecordTypeDescriptor *)quest_alloc(meta_size);
    meta->field_count = field_count;
    if (fields != NULL && field_count > 0) {
        memcpy((void *)meta->fields, fields, sizeof(QRecordFieldDescriptor) * field_count);
    }
    desc->extra = meta;
    return quest_intern_type_descriptor(desc);
}

const QTypeDescriptor *quest_make_tuple_descriptor(
    const char *name, size_t size, size_t alignment, size_t element_count, const QTupleElementDescriptor *elements
) {
    if (element_count == 0) return &quest_type_EmptyTuple;
    quest_init_type_intern_table();
    const char *tup_name = name ? name : "Tuple end";

    uint64_t h = quest_hash_string(tup_name) % Q_TYPE_INTERN_TABLE_SIZE;
    for (QTypeDescriptorEntry *cur = quest_type_intern_buckets[h]; cur != NULL; cur = cur->next) {
        if (cur->desc->name != NULL && strcmp(cur->desc->name, tup_name) == 0) {
            return cur->desc;
        }
    }

    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor));
    desc->kind = QTYPE_KIND_TUPLE;
    desc->name = quest_dup_str(tup_name);
    desc->size = size;
    desc->alignment = alignment > 0 ? alignment : sizeof(void *);
    desc->is_subtype = quest_is_subtype;

    size_t meta_size = sizeof(QTupleTypeDescriptor) + sizeof(QTupleElementDescriptor) * element_count;
    QTupleTypeDescriptor *meta = (QTupleTypeDescriptor *)quest_alloc(meta_size);
    meta->element_count = element_count;
    if (elements != NULL && element_count > 0) {
        memcpy((void *)meta->elements, elements, sizeof(QTupleElementDescriptor) * element_count);
    }
    desc->extra = meta;
    return quest_intern_type_descriptor(desc);
}

const QTypeDescriptor *quest_make_variant_descriptor(
    const char *name, size_t size, size_t alignment, size_t case_count, const QVariantCaseDescriptor *cases
) {
    quest_init_type_intern_table();
    const char *var_name = name ? name : "Variant end";

    uint64_t h = quest_hash_string(var_name) % Q_TYPE_INTERN_TABLE_SIZE;
    for (QTypeDescriptorEntry *cur = quest_type_intern_buckets[h]; cur != NULL; cur = cur->next) {
        if (cur->desc->name != NULL && strcmp(cur->desc->name, var_name) == 0) {
            return cur->desc;
        }
    }

    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor));
    desc->kind = QTYPE_KIND_VARIANT;
    desc->name = quest_dup_str(var_name);
    desc->size = size > 0 ? size : sizeof(QVariantVal);
    desc->alignment = alignment > 0 ? alignment : sizeof(void *);
    desc->is_subtype = quest_is_subtype;

    size_t meta_size = sizeof(QVariantTypeDescriptor) + sizeof(QVariantCaseDescriptor) * case_count;
    QVariantTypeDescriptor *meta = (QVariantTypeDescriptor *)quest_alloc(meta_size);
    meta->case_count = case_count;
    if (cases != NULL && case_count > 0) {
        memcpy((void *)meta->cases, cases, sizeof(QVariantCaseDescriptor) * case_count);
    }
    desc->extra = meta;
    return quest_intern_type_descriptor(desc);
}

const QTypeDescriptor *quest_make_fun_descriptor(
    const char *name, size_t param_count, const QFunParamDescriptor *params, const QTypeDescriptor *result_type
) {
    quest_init_type_intern_table();
    const char *fn_name = name ? name : "Fun()";

    uint64_t h = quest_hash_string(fn_name) % Q_TYPE_INTERN_TABLE_SIZE;
    for (QTypeDescriptorEntry *cur = quest_type_intern_buckets[h]; cur != NULL; cur = cur->next) {
        if (cur->desc->name != NULL && strcmp(cur->desc->name, fn_name) == 0) {
            return cur->desc;
        }
    }

    QTypeDescriptor *desc = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor));
    desc->kind = QTYPE_KIND_FUN;
    desc->name = quest_dup_str(fn_name);
    desc->size = sizeof(QClosure);
    desc->alignment = sizeof(void *);
    desc->is_subtype = quest_is_subtype;

    size_t meta_size = sizeof(QFunTypeDescriptor) + sizeof(QFunParamDescriptor) * param_count;
    QFunTypeDescriptor *meta = (QFunTypeDescriptor *)quest_alloc(meta_size);
    meta->param_count = param_count;
    meta->result_type = result_type;
    meta->adapt = NULL;
    meta->invoke = NULL;
    meta->quantifier_count = 0;
    meta->quantifier_bounds = NULL;
    if (params != NULL && param_count > 0) {
        memcpy((void *)meta->params, params, sizeof(QFunParamDescriptor) * param_count);
    }
    desc->extra = meta;
    return quest_intern_type_descriptor(desc);
}

QAuto *quest_auto_new(const QTypeDescriptor *type_desc, QVal payload) {
    QAuto *a = (QAuto *)quest_alloc(sizeof(QAuto));
    a->type_desc = type_desc;
    a->payload = payload;
    return a;
}

QAuto *quest_dynamic_copy(const QAuto *d) {
    if (d == NULL || d->type_desc == NULL) {
        quest_raise_dynamic_error();
    }
    QVal *component = (QVal *)quest_alloc(sizeof(QVal));
    *component = *(const QVal *)d->payload.p;
    return quest_auto_new(d->type_desc, (QVal){ .p = component });
}

/* ------------------------------------------------------------------------- */
/* Standard Library Implementation                                           */
/* ------------------------------------------------------------------------- */

#include <limits.h>
#include <unistd.h>
#include <sys/stat.h>
#include <dirent.h>
#include <errno.h>
#include <poll.h>
#include <spawn.h>
#include <sys/wait.h>

/* System module primitives */
QArray *quest_system_args = NULL;

void quest_system_init(int argc, char **argv) {
    if (argc < 0) argc = 0;
    quest_system_args = quest_array_new(argc, (QVal){ .p = NULL });
    for (int i = 0; i < argc; i++) {
        const char *arg = (argv != NULL && argv[i] != NULL) ? argv[i] : "";
        quest_system_args->data[i].p = quest_string_new(arg, (int64_t)strlen(arg));
    }
}

void quest_system_exit(int64_t code) {
    exit((int)code);
}

QString *quest_system_getenv(const QString *var) {
    if (var == NULL || var->data == NULL) return quest_string_new("", 0);
    const char *val = getenv(var->data);
    if (val == NULL) {
        return quest_string_new("", 0);
    }
    return quest_string_new(val, (int64_t)strlen(val));
}

bool quest_system_file_exists(const QString *path) {
    if (path == NULL || path->data == NULL) return false;
    return access(path->data, F_OK) == 0;
}

bool quest_system_is_file(const QString *path) {
    if (path == NULL || path->data == NULL) return false;
    struct stat st;
    if (stat(path->data, &st) != 0) return false;
    return S_ISREG(st.st_mode);
}

bool quest_system_is_directory(const QString *path) {
    if (path == NULL || path->data == NULL) return false;
    struct stat st;
    if (stat(path->data, &st) != 0) return false;
    return S_ISDIR(st.st_mode);
}

static int quest_mkdir_recursive(char *path) {
    char *p = path;
    if (*p == '/') p++;
    while (*p) {
        if (*p == '/') {
            *p = '\0';
            if (mkdir(path, 0777) != 0 && errno != EEXIST) {
                *p = '/';
                return -1;
            }
            *p = '/';
        }
        p++;
    }
    if (mkdir(path, 0777) != 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

void quest_system_make_directory(const QString *path) {
    if (path == NULL || path->data == NULL || path->length == 0) {
        quest_raise_system_error();
    }
    char *buf = (char *)malloc((size_t)path->length + 1);
    if (buf == NULL) {
        quest_raise_system_error();
    }
    memcpy(buf, path->data, (size_t)path->length + 1);
    int res = quest_mkdir_recursive(buf);
    free(buf);
    if (res != 0) {
        quest_raise_system_error();
    }
}

void quest_system_remove_file(const QString *path) {
    if (path == NULL || path->data == NULL) {
        quest_raise_system_error();
    }
    if (unlink(path->data) != 0) {
        quest_raise_system_error();
    }
}

void quest_system_remove_directory(const QString *path) {
    if (path == NULL || path->data == NULL) {
        quest_raise_system_error();
    }
    if (rmdir(path->data) != 0) {
        quest_raise_system_error();
    }
}

void quest_system_rename_file(const QString *old_path, const QString *new_path) {
    if (old_path == NULL || old_path->data == NULL ||
        new_path == NULL || new_path->data == NULL) {
        quest_raise_system_error();
    }
    if (rename(old_path->data, new_path->data) != 0) {
        quest_raise_system_error();
    }
}

QString *quest_system_current_directory(void) {
    char buf[4096];
    if (getcwd(buf, sizeof(buf)) == NULL) {
        quest_raise_system_error();
    }
    return quest_string_new(buf, (int64_t)strlen(buf));
}

void quest_system_change_directory(const QString *path) {
    if (path == NULL || path->data == NULL) {
        quest_raise_system_error();
    }
    if (chdir(path->data) != 0) {
        quest_raise_system_error();
    }
}

static int quest_strcmp_qsort(const void *a, const void *b) {
    const QString *s1 = *(const QString * const *)a;
    const QString *s2 = *(const QString * const *)b;
    return strcmp(s1->data, s2->data);
}

QArray *quest_system_list_directory(const QString *path) {
    if (path == NULL || path->data == NULL) {
        quest_raise_system_error();
    }
    DIR *dir = opendir(path->data);
    if (dir == NULL) {
        quest_raise_system_error();
    }

    size_t count = 0;
    size_t cap = 16;
    QString **entries = (QString **)malloc(cap * sizeof(QString *));
    if (entries == NULL) {
        closedir(dir);
        quest_raise_system_error();
    }

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        if (count >= cap) {
            cap *= 2;
            QString **new_entries = (QString **)realloc(entries, cap * sizeof(QString *));
            if (new_entries == NULL) {
                free(entries);
                closedir(dir);
                quest_raise_system_error();
            }
            entries = new_entries;
        }
        entries[count++] = quest_string_new(entry->d_name, (int64_t)strlen(entry->d_name));
    }
    closedir(dir);

    if (count > 1) {
        qsort(entries, count, sizeof(QString *), quest_strcmp_qsort);
    }

    QArray *res = quest_array_new((int64_t)count, (QVal){ .p = NULL });
    for (size_t i = 0; i < count; i++) {
        res->data[i].p = entries[i];
    }
    free(entries);
    return res;
}

/* A growing byte buffer for a child's output */
typedef struct QRunBuffer {
    char  *data;
    size_t len;
    size_t cap;
} QRunBuffer;

static bool quest_run_append(QRunBuffer *b, const char *src, size_t n) {
    if (b->len + n > b->cap) {
        size_t cap = b->cap > 0 ? b->cap : 4096;
        while (cap < b->len + n) cap *= 2;
        char *data = (char *)realloc(b->data, cap);
        if (data == NULL) return false;
        b->data = data;
        b->cap = cap;
    }
    memcpy(b->data + b->len, src, n);
    b->len += n;
    return true;
}

/* Reads the child's standard output and error until both end, polling so that
 * neither pipe fills while the other is read */
static bool quest_run_collect(int out_fd, int err_fd, QRunBuffer *out, QRunBuffer *err) {
    struct pollfd fds[2] = { { out_fd, POLLIN, 0 }, { err_fd, POLLIN, 0 } };
    QRunBuffer *bufs[2] = { out, err };
    int open_count = 2;
    char chunk[8192];
    while (open_count > 0) {
        if (poll(fds, 2, -1) < 0) {
            if (errno == EINTR) continue;
            return false;
        }
        for (int i = 0; i < 2; i++) {
            if (fds[i].fd < 0 || fds[i].revents == 0) continue;
            ssize_t n = read(fds[i].fd, chunk, sizeof(chunk));
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) {
                fds[i].fd = -1;
                open_count--;
            } else if (!quest_run_append(bufs[i], chunk, (size_t)n)) {
                return false;
            }
        }
    }
    return true;
}

extern char **environ;

void *quest_system_run(const QArray *args) {
    if (args == NULL || args->length == 0) quest_raise_system_error();
    size_t argc = (size_t)args->length;
    char **argv = (char **)malloc((argc + 1) * sizeof(char *));
    if (argv == NULL) quest_raise_system_error();
    for (size_t i = 0; i < argc; i++) {
        const QString *arg = (const QString *)args->data[i].p;
        if (arg == NULL || arg->data == NULL) {
            free(argv);
            quest_raise_system_error();
        }
        argv[i] = arg->data;
    }
    argv[argc] = NULL;

    int out_pipe[2], err_pipe[2];
    if (pipe(out_pipe) != 0) {
        free(argv);
        quest_raise_system_error();
    }
    if (pipe(err_pipe) != 0) {
        close(out_pipe[0]);
        close(out_pipe[1]);
        free(argv);
        quest_raise_system_error();
    }
    posix_spawn_file_actions_t actions;
    posix_spawn_file_actions_init(&actions);
    posix_spawn_file_actions_adddup2(&actions, out_pipe[1], STDOUT_FILENO);
    posix_spawn_file_actions_adddup2(&actions, err_pipe[1], STDERR_FILENO);
    posix_spawn_file_actions_addclose(&actions, out_pipe[0]);
    posix_spawn_file_actions_addclose(&actions, err_pipe[0]);
    posix_spawn_file_actions_addclose(&actions, out_pipe[1]);
    posix_spawn_file_actions_addclose(&actions, err_pipe[1]);
    pid_t pid;
    int spawned = posix_spawnp(&pid, argv[0], &actions, NULL, argv, environ);
    posix_spawn_file_actions_destroy(&actions);
    free(argv);
    close(out_pipe[1]);
    close(err_pipe[1]);
    if (spawned != 0) {
        close(out_pipe[0]);
        close(err_pipe[0]);
        quest_raise_system_error();
    }

    QRunBuffer out = { NULL, 0, 0 }, err = { NULL, 0, 0 };
    bool collected = quest_run_collect(out_pipe[0], err_pipe[0], &out, &err);
    close(out_pipe[0]);
    close(err_pipe[0]);
    int status;
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR) {
            collected = false;
            break;
        }
    }
    if (!collected) {
        free(out.data);
        free(err.data);
        quest_raise_system_error();
    }

    /* Laid out as Tuple code: Int stdout: String stderr: String end; a child killed
     * by a signal has its negated number as its code, as in Python */
    QVal *result = (QVal *)quest_alloc(3 * sizeof(QVal));
    result[0].i = WIFEXITED(status) ? WEXITSTATUS(status) : WIFSIGNALED(status) ? -WTERMSIG(status) : -1;
    result[1].p = quest_string_new(out.data != NULL ? out.data : "", (int64_t)out.len);
    result[2].p = quest_string_new(err.data != NULL ? err.data : "", (int64_t)err.len);
    free(out.data);
    free(err.data);
    return result;
}

/* os/fileStats (see quest_runtime.h) */
void *quest_filestats_stat(const QString *path, bool follow) {
    if (path == NULL || path->data == NULL) quest_raise_system_error();
    struct stat st;
    QVal *result = (QVal *)quest_alloc(9 * sizeof(QVal));
    if ((follow ? stat(path->data, &st) : lstat(path->data, &st)) != 0) {
        if (errno != ENOENT && errno != ENOTDIR) quest_raise_system_error();
        result[0].i = -1;
        for (int i = 1; i < 9; i++) result[i].i = 0;
        return result;
    }
#ifdef __APPLE__
    struct timespec times[3] = { st.st_atimespec, st.st_mtimespec, st.st_ctimespec };
#else
    struct timespec times[3] = { st.st_atim, st.st_mtim, st.st_ctim };
#endif
    result[0].i = S_ISREG(st.st_mode) ? 0 : S_ISDIR(st.st_mode) ? 1 : S_ISLNK(st.st_mode) ? 2 : 3;
    result[1].i = (QInt)st.st_size;
    result[2].i = (QInt)(st.st_mode & 07777);
    for (int i = 0; i < 3; i++) {
        /* Computed as Python computes st_mtime and st_mtime_ns, so that the
         * two agree exactly */
        result[3 + i].r = (double)times[i].tv_sec + (double)times[i].tv_nsec * 1e-9;
        result[6 + i].i = (QInt)times[i].tv_sec * 1000000000 + (QInt)times[i].tv_nsec;
    }
    return result;
}

bool quest_system_is_terminal(int64_t fd) {
    return fd >= 0 && fd <= INT_MAX && isatty((int)fd);
}

/* Writer module primitives */
QWriter quest_writer_output_val = { NULL, false, false };
QWriter quest_writer_err_val    = { NULL, false, false };

static void quest_writer_init_std(void) {
    if (quest_writer_output_val.file == NULL) {
        quest_writer_output_val.file = stdout;
        quest_writer_output_val.is_file = false;
        quest_writer_output_val.is_closed = false;
    }
    if (quest_writer_err_val.file == NULL) {
        quest_writer_err_val.file = stderr;
        quest_writer_err_val.is_file = false;
        quest_writer_err_val.is_closed = false;
    }
}

QWriter *quest_writer_file(const QString *name) {
    if (name == NULL || name->data == NULL) {
        quest_raise_writer_error();
    }
    FILE *f = fopen(name->data, "w");
    if (f == NULL) {
        quest_raise_writer_error();
    }
    QWriter *w = (QWriter *)quest_alloc(sizeof(QWriter));
    w->file = f;
    w->is_file = true;
    w->is_closed = false;
    return w;
}

void quest_writer_put_string(QWriter *w, const QString *s) {
    if (w == NULL || w->is_closed || w->file == NULL || s == NULL) {
        quest_raise_writer_error();
    }
    if (s->length > 0) {
        size_t written = fwrite(s->data, 1, (size_t)s->length, w->file);
        if (written != (size_t)s->length) {
            quest_raise_writer_error();
        }
    }
}

void quest_writer_put_char(QWriter *w, QChar ch) {
    if (w == NULL || w->is_closed || w->file == NULL) {
        quest_raise_writer_error();
    }
    if (fputc((int)ch, w->file) == EOF) {
        quest_raise_writer_error();
    }
}

void quest_writer_put_substring(QWriter *w, const QString *s, int64_t start, int64_t size) {
    if (w == NULL || w->is_closed || w->file == NULL || s == NULL) {
        quest_raise_writer_error();
    }
    if (start < 0 || size < 0 || start + size > s->length) {
        quest_raise_writer_error();
    }
    if (size > 0) {
        size_t written = fwrite(s->data + start, 1, (size_t)size, w->file);
        if (written != (size_t)size) {
            quest_raise_writer_error();
        }
    }
}

void quest_writer_flush(QWriter *w) {
    if (w == NULL || w->is_closed || w->file == NULL) {
        quest_raise_writer_error();
    }
    if (fflush(w->file) != 0) {
        quest_raise_writer_error();
    }
}

void quest_writer_close(QWriter *w) {
    if (w == NULL) {
        quest_raise_writer_error();
    }
    if (!w->is_closed) {
        if (w->is_file && w->file != NULL) {
            fclose(w->file);
        } else if (w->file != NULL) {
            fflush(w->file);
        }
        w->is_closed = true;
    }
}

/* Reader module primitives */
QReader quest_reader_input_val = { NULL, -1, false, false };

static void quest_reader_init_std(void) {
    if (quest_reader_input_val.file == NULL) {
        quest_reader_input_val.file = stdin;
        quest_reader_input_val.peek_char = -1;
        quest_reader_input_val.is_file = false;
        quest_reader_input_val.is_closed = false;
    }
}

QReader *quest_reader_file(const QString *name) {
    if (name == NULL || name->data == NULL) {
        quest_raise_reader_error();
    }
    FILE *f = fopen(name->data, "r");
    if (f == NULL) {
        quest_raise_reader_error();
    }
    QReader *r = (QReader *)quest_alloc(sizeof(QReader));
    r->file = f;
    r->peek_char = -1;
    r->is_file = true;
    r->is_closed = false;
    return r;
}

bool quest_reader_more(QReader *r) {
    if (r == NULL || r->is_closed || r->file == NULL) {
        quest_raise_reader_error();
    }
    if (r->peek_char != -1) {
        return true;
    }
    int ch = fgetc(r->file);
    if (ch == EOF) {
        return false;
    }
    r->peek_char = ch;
    return true;
}

bool quest_reader_ready(QReader *r) {
    if (r == NULL || r->is_closed || r->file == NULL) {
        quest_raise_reader_error();
    }
    return quest_reader_more(r);
}

QChar quest_reader_get_char(QReader *r) {
    if (r == NULL || r->is_closed || r->file == NULL) {
        quest_raise_reader_error();
    }
    int ch;
    if (r->peek_char != -1) {
        ch = r->peek_char;
        r->peek_char = -1;
    } else {
        ch = fgetc(r->file);
    }
    if (ch == EOF) {
        quest_raise_reader_error();
    }
    return (QChar)(unsigned char)ch;
}

QString *quest_reader_get_string(QReader *r, int64_t size) {
    if (r == NULL || r->is_closed || r->file == NULL || size < 0) {
        quest_raise_reader_error();
    }
    if (size == 0) {
        return quest_string_new("", 0);
    }
    char *buf = (char *)quest_alloc_atomic((size_t)size + 1);
    int64_t count = 0;
    if (r->peek_char != -1) {
        buf[count++] = (char)r->peek_char;
        r->peek_char = -1;
    }
    if (count < size) {
        size_t n = fread(buf + count, 1, (size_t)(size - count), r->file);
        count += (int64_t)n;
    }
    buf[count] = 0;
    QString *res = (QString *)quest_alloc(sizeof(QString));
    res->length = count;
    res->capacity = count;
    res->data = buf;
    return res;
}

void quest_reader_get_substring(QReader *r, QString *s, int64_t start, int64_t size) {
    if (r == NULL || r->is_closed || r->file == NULL || s == NULL ||
        start < 0 || size < 0 || start + size > s->length) {
        quest_raise_reader_error();
    }
    if (size == 0) return;
    int64_t count = 0;
    if (r->peek_char != -1) {
        s->data[start + count++] = (char)r->peek_char;
        r->peek_char = -1;
    }
    if (count < size) {
        size_t n = fread(s->data + start + count, 1, (size_t)(size - count), r->file);
        if ((int64_t)n < size - count) {
            quest_raise_reader_error();
        }
    }
}

void quest_reader_close(QReader *r) {
    if (r == NULL) {
        quest_raise_reader_error();
    }
    if (!r->is_closed) {
        if (r->is_file && r->file != NULL) {
            fclose(r->file);
        }
        r->is_closed = true;
        r->peek_char = -1;
    }
}

/* Conv module primitives */
QString *quest_conv_okay(void) {
    return quest_string_new("ok", 2);
}

QString *quest_conv_bool(bool b) {
    return b ? quest_string_new("true", 4) : quest_string_new("false", 5);
}

QString *quest_conv_int(int64_t n) {
    char buf[64];
    if (n < 0) {
        if (n == QUEST_INT_MIN) {
            snprintf(buf, sizeof(buf), "~9223372036854775808");
        } else {
            snprintf(buf, sizeof(buf), "~%lld", (long long)-n);
        }
    } else {
        snprintf(buf, sizeof(buf), "%lld", (long long)n);
    }
    return quest_string_new(buf, (int64_t)strlen(buf));
}

QString *quest_conv_real(double r) {
    char buf[48];
    /* Quest writes negation as ~, including for negative zero and negative
     * infinity. */
    buf[0] = '~';
    bool is_neg = signbit(r);
    quest_format_real(r, buf + (is_neg ? 1 : 0), sizeof(buf) - 1);
    return quest_string_new(buf, (int64_t)strlen(buf));
}

QString *quest_conv_char(QChar ch) {
    char buf[8];
    buf[0] = '\'';
    buf[1] = (char)ch;
    buf[2] = '\'';
    buf[3] = 0;
    return quest_string_new(buf, 3);
}

QString *quest_conv_string(const QString *s) {
    if (s == NULL) return quest_string_new("\"\"", 2);
    int64_t len = s->length;
    char *buf = (char *)quest_alloc_atomic((size_t)(len + 3));
    buf[0] = '"';
    if (len > 0) memcpy(buf + 1, s->data, (size_t)len);
    buf[len + 1] = '"';
    buf[len + 2] = 0;
    QString *res = (QString *)quest_alloc(sizeof(QString));
    res->length = len + 2;
    res->capacity = len + 2;
    res->data = buf;
    return res;
}

/* Strutil module primitives */
double quest_strutil_to_real(const QString *s) {
    /* strutil.tryToReal has checked the syntax; strtod rounds correctly, and
     * overflows to an infinity */
    return s == NULL ? 0.0 : strtod(s->data, NULL);
}

/* StringBuilder native buffer (see quest_runtime.h) */
QStringBuilder *quest_sb_new(void) {
    QStringBuilder *b = (QStringBuilder *)quest_alloc(sizeof(QStringBuilder));
    b->buffer = (char *)quest_alloc_atomic(QUEST_SB_BUFFER_SIZE);
    return b;
}

/* Adds a finished chunk of len bytes at data, which the chunk takes over */
static void quest_sb_add_chunk(QStringBuilder *b, char *data, int64_t len) {
    if (b->chunk_count == b->chunk_capacity) {
        int64_t capacity = b->chunk_capacity ? b->chunk_capacity * 2 : 8;
        QString **chunks = (QString **)quest_alloc((size_t)capacity * sizeof(QString *));
        if (b->chunk_count > 0) memcpy(chunks, b->chunks, (size_t)b->chunk_count * sizeof(QString *));
        b->chunks = chunks;
        b->chunk_capacity = capacity;
    }
    QString *chunk = (QString *)quest_alloc(sizeof(QString));
    chunk->length = len;
    chunk->capacity = len;
    chunk->data = data;
    b->chunks[b->chunk_count++] = chunk;
}

/* Turns a nonempty working buffer into a chunk, and starts a new one */
static void quest_sb_flush(QStringBuilder *b) {
    if (b->used == 0) return;
    quest_sb_add_chunk(b, b->buffer, b->used);
    b->buffer = (char *)quest_alloc_atomic(QUEST_SB_BUFFER_SIZE);
    b->used = 0;
}

static void quest_sb_append_bytes(QStringBuilder *b, const char *data, int64_t len) {
    if (len <= 0) return;
    b->length += len;
    if (len > QUEST_SB_LONG_APPEND) {
        quest_sb_flush(b);
        char *copy = (char *)quest_alloc_atomic((size_t)len);
        memcpy(copy, data, (size_t)len);
        quest_sb_add_chunk(b, copy, len);
        return;
    }
    if (b->used + len > QUEST_SB_BUFFER_SIZE) quest_sb_flush(b);
    memcpy(b->buffer + b->used, data, (size_t)len);
    b->used += len;
}

void quest_sb_append_string(QStringBuilder *b, const QString *s) {
    if (s != NULL) quest_sb_append_bytes(b, s->data, s->length);
}

void quest_sb_append_char(QStringBuilder *b, QChar ch) {
    if (b->used == QUEST_SB_BUFFER_SIZE) quest_sb_flush(b);
    b->buffer[b->used++] = ch;
    b->length++;
}

void quest_sb_append_int(QStringBuilder *b, int64_t n) {
    char buf[32];
    int len;
    if (n == QUEST_INT_MIN) len = snprintf(buf, sizeof(buf), "~9223372036854775808");
    else if (n < 0) len = snprintf(buf, sizeof(buf), "~%lld", (long long)-n);
    else len = snprintf(buf, sizeof(buf), "%lld", (long long)n);
    quest_sb_append_bytes(b, buf, len);
}

void quest_sb_append_real(QStringBuilder *b, double r) {
    char buf[48];
    /* As conv.real: ~ for negatives, including negative zero and negative
     * infinity */
    buf[0] = '~';
    bool is_neg = signbit(r);
    quest_format_real(r, buf + (is_neg ? 1 : 0), sizeof(buf) - 1);
    quest_sb_append_bytes(b, buf, (int64_t)strlen(buf));
}

void quest_sb_append_bool(QStringBuilder *b, bool v) {
    if (v) quest_sb_append_bytes(b, "true", 4);
    else quest_sb_append_bytes(b, "false", 5);
}

void quest_sb_append_word(QStringBuilder *b, uint64_t w) {
    char buf[32];
    int len = snprintf(buf, sizeof(buf), "%llu", (unsigned long long)w);
    quest_sb_append_bytes(b, buf, len);
}

void quest_sb_append_sub(QStringBuilder *b, const QString *s, int64_t start, int64_t size) {
    if (s == NULL || start < 0 || size < 0 || start > s->length - size) {
        quest_raise_string_error();
    }
    quest_sb_append_bytes(b, s->data + start, size);
}

void quest_sb_append_repeat(QStringBuilder *b, QChar ch, int64_t n) {
    if (n < 0) {
        quest_raise_string_error();
    }
    b->length += n;
    while (n > 0) {
        if (b->used == QUEST_SB_BUFFER_SIZE) quest_sb_flush(b);
        int64_t count = QUEST_SB_BUFFER_SIZE - b->used;
        if (count > n) count = n;
        memset(b->buffer + b->used, (int)(unsigned char)ch, (size_t)count);
        b->used += count;
        n -= count;
    }
}

void quest_sb_clear(QStringBuilder *b) {
    /* Drop the chunks, so that the collector can reclaim them */
    if (b->chunk_count > 0) memset(b->chunks, 0, (size_t)b->chunk_count * sizeof(QString *));
    b->chunk_count = 0;
    b->used = 0;
    b->length = 0;
}

int64_t quest_sb_length(const QStringBuilder *b) {
    return b->length;
}

QString *quest_sb_to_string(const QStringBuilder *b) {
    QString *s = (QString *)quest_alloc(sizeof(QString));
    s->length = b->length;
    s->capacity = b->length;
    s->data = (char *)quest_alloc_atomic((size_t)b->length + 1);
    int64_t offset = 0;
    for (int64_t i = 0; i < b->chunk_count; ++i) {
        memcpy(s->data + offset, b->chunks[i]->data, (size_t)b->chunks[i]->length);
        offset += b->chunks[i]->length;
    }
    if (b->used > 0) memcpy(s->data + offset, b->buffer, (size_t)b->used);
    s->data[b->length] = 0;
    return s;
}

/* Ascii module primitives */
QChar quest_ascii_char(int64_t n) {
    if (n < 0 || n > 255) {
        quest_raise_ascii_error();
    }
    return (QChar)(unsigned char)n;
}

int64_t quest_ascii_val(QChar ch) {
    return (int64_t)(unsigned char)ch;
}

/* RealOp primitives */
double quest_real_from_int(int64_t n) {
    return (double)n;
}

double quest_real_log(double r) {
    if (r <= 0.0) {
        quest_raise_real_error();
    }
    return log(r);
}

/* An integral real as an Int; an infinity or a value outside Int's range raises
 * real.error. */
static int64_t quest_real_to_int(double r) {
    if (!(r >= -9223372036854775808.0 && r < 9223372036854775808.0)) {
        quest_raise_real_error();
    }
    return (int64_t)r;
}

int64_t quest_real_floor(double r) {
    return quest_real_to_int(floor(r));
}

int64_t quest_real_round(double r) {
    return quest_real_to_int(round(r));
}

double quest_real_div(double a, double b) {
    return quest_real_divide(a, b);
}

double quest_real_exp(double a, double b) {
    return quest_real_pow(a, b);
}

/* Word module primitives */
uint64_t quest_word_not_bits(uint64_t w) {
    return ~w;
}

uint64_t quest_word_and_bits(uint64_t w1, uint64_t w2) {
    return w1 & w2;
}

uint64_t quest_word_or_bits(uint64_t w1, uint64_t w2) {
    return w1 | w2;
}

uint64_t quest_word_xor_bits(uint64_t w1, uint64_t w2) {
    return w1 ^ w2;
}

uint64_t quest_word_shift_val(uint64_t w, int64_t count) {
    return quest_word_shift(w, count);
}

uint64_t quest_word_rotate_val(uint64_t w, int64_t count) {
    return quest_word_rotate(w, count);
}

uint64_t quest_word_extract_val(uint64_t w, int64_t pos, int64_t width) {
    return quest_word_extract(w, pos, width);
}

uint64_t quest_word_replace_val(uint64_t w, uint64_t val, int64_t pos, int64_t width) {
    return quest_word_replace(w, val, pos, width);
}

int64_t quest_word_pop_count_val(uint64_t w) {
    return quest_word_pop_count(w);
}

int64_t quest_word_count_leading_zeros_val(uint64_t w) {
    return quest_word_count_leading_zeros(w);
}

int64_t quest_word_count_trailing_zeros_val(uint64_t w) {
    return quest_word_count_trailing_zeros(w);
}

bool quest_word_get_bit_val(uint64_t w, int64_t pos) {
    return quest_word_get_bit(w, pos);
}

uint64_t quest_word_set_bit_val(uint64_t w, int64_t pos) {
    return quest_word_set_bit(w, pos);
}

uint64_t quest_word_clear_bit_val(uint64_t w, int64_t pos) {
    return quest_word_clear_bit(w, pos);
}

uint64_t quest_word_add(uint64_t w1, uint64_t w2) {
    return w1 + w2;
}

uint64_t quest_word_sub(uint64_t w1, uint64_t w2) {
    return w1 - w2;
}

uint64_t quest_word_mul(uint64_t w1, uint64_t w2) {
    return w1 * w2;
}

uint64_t quest_word_div_val(uint64_t w1, uint64_t w2) {
    return quest_word_div(w1, w2);
}

uint64_t quest_word_mod_val(uint64_t w1, uint64_t w2) {
    return quest_word_mod(w1, w2);
}

int64_t quest_word_to_int(uint64_t w) {
    return (int64_t)w;
}

uint64_t quest_word_from_int(int64_t n) {
    return (uint64_t)n;
}

bool quest_word_lt(uint64_t w1, uint64_t w2) {
    return w1 < w2;
}

bool quest_word_le(uint64_t w1, uint64_t w2) {
    return w1 <= w2;
}

bool quest_word_gt(uint64_t w1, uint64_t w2) {
    return w1 > w2;
}

bool quest_word_ge(uint64_t w1, uint64_t w2) {
    return w1 >= w2;
}

double quest_word_to_real_val(uint64_t w) {
    double r = ((QVal){ .u = w }).r;
    if (isnan(r)) {
        /* NaN bit patterns have no Real value. */
        quest_raise_word_error();
    }
    return r;
}

uint64_t quest_word_from_real_val(double r) {
    return ((QVal){ .r = r }).u;
}

uint64_t quest_hash_mix(uint64_t w) {
    return quest_hash_mix64(w);
}

uint64_t quest_hash_combine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b97f4a7c15ULL + (h1 << 6) + (h1 >> 2));
}

/* Hashes consistently with is (quest_val_is): ~0.0 hashes as 0.0. */
uint64_t quest_identity_hash(const QTypeDescriptor *t, QVal x) {
    if (t != NULL && t->kind == QTYPE_KIND_STORED) t = ((const QStoredDescriptor *)t->extra)->type;
    if (t != NULL && t->kind == QTYPE_KIND_REAL && x.r == 0.0) {
        x.u = 0;
    }
    if (t != NULL && (t->kind == QTYPE_KIND_TUPLE || t->kind == QTYPE_KIND_OPTION)) {
        /* A proxy hashes as the object it is a view of, as is compares them */
        x.p = quest_unproxy(x.p);
    }
    return quest_hash_mix64(x.u);
}

/* ============================================================================
 * Running out of stack
 *
 * Compiled code does not check its depth, so runaway recursion runs into the
 * guard page below the main thread's stack. A handler for the fault, on a stack
 * of its own, reports it as an uncaught stack.overflow, with the frames
 * running, and ends the program, as quest_reraise ends it for any uncaught
 * exception; the interpreters raise stack.overflow as an exception a program
 * can catch (docs/exceptions.md §6). Reporting is not async-signal-safe, but
 * the program is ending, and a fault in the middle of the allocator or stdio
 * is unlikely. Any other fault is left to the default action.
 * ============================================================================
 */

#if defined(__APPLE__) || (defined(__linux__) && defined(__GLIBC__))
#include <pthread.h>
#include <signal.h>
#define Q_HAVE_STACK_GUARD 1

/* How far a fault's address may be from the stack's low end, below it (a large
 * frame skips past the guard page) or above it, to be an overflow */
#define Q_STACK_REACH_BELOW ((uintptr_t)1 << 20)
#define Q_STACK_REACH_ABOVE ((uintptr_t)1 << 16)

static uintptr_t quest_stack_low = 0;
static char quest_signal_stack[1 << 18];

static void quest_on_fault(int sig, siginfo_t *info, void *context) {
    (void)context;
    uintptr_t addr = (uintptr_t)info->si_addr;
    if (quest_stack_low != 0 && addr + Q_STACK_REACH_BELOW >= quest_stack_low &&
        addr < quest_stack_low + Q_STACK_REACH_ABOVE) {
        fflush(stdout);
        fprintf(stderr, "Exception: stack.overflow\n");
        quest_fail_with(NULL, NULL);
    }
    /* Returning faults again, with the default action */
    signal(sig, SIG_DFL);
}

static void quest_install_stack_guard(void) {
    pthread_t self = pthread_self();
#ifdef __APPLE__
    quest_stack_low = (uintptr_t)pthread_get_stackaddr_np(self) - pthread_get_stacksize_np(self);
#else
    pthread_attr_t attr;
    void *low = NULL;
    size_t size = 0;
    if (pthread_getattr_np(self, &attr) != 0) return;
    if (pthread_attr_getstack(&attr, &low, &size) == 0) quest_stack_low = (uintptr_t)low;
    pthread_attr_destroy(&attr);
#endif
    stack_t ss;
    ss.ss_sp = quest_signal_stack;
    ss.ss_size = sizeof quest_signal_stack;
    ss.ss_flags = 0;
    if (sigaltstack(&ss, NULL) != 0) return;
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = quest_on_fault;
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, NULL);
    sigaction(SIGBUS, &sa, NULL);
}
#endif

/* Builtins initialization */
void quest_builtins_init(int argc, char **argv) {
    quest_writer_init_std();
    quest_reader_init_std();
    quest_system_init(argc, argv);
#ifdef Q_HAVE_STACK_GUARD
    quest_install_stack_guard();
#endif
}

/* ============================================================================
 * Built-in Operator Trampolines & Closures (Cardelli §4.2)
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

/* Real arithmetic */
static QReal qv_sym_plus_plus_trampoline(void *env, QReal a, QReal b) { (void)env; return a + b; }
QClosure qv_sym_plus_plus_closure = { (void *)qv_sym_plus_plus_trampoline, NULL };

static QReal qv_sym_minus_minus_trampoline(void *env, QReal a, QReal b) { (void)env; return a - b; }
QClosure qv_sym_minus_minus_closure = { (void *)qv_sym_minus_minus_trampoline, NULL };

static QReal qv_sym_star_star_trampoline(void *env, QReal a, QReal b) { (void)env; return a * b; }
QClosure qv_sym_star_star_closure = { (void *)qv_sym_star_star_trampoline, NULL };

static QReal qv_sym_slash_slash_trampoline(void *env, QReal a, QReal b) { (void)env; return a / b; }
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
