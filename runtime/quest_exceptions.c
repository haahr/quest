/*
 * Quest C Runtime: Exceptions
 *
 * The built-in exceptions, raising and catching (quest_raise, quest_reraise),
 * and tracebacks: the function tables compiled units register, walking the
 * stack, and printing an uncaught exception's frames (docs/exceptions.md §5).
 * Last, the guard that reports running out of stack as an uncaught
 * stack.overflow (§6).
 */

/* pthread_getattr_np, for the stack guard on Linux (glibc) */
#if defined(__linux__) && !defined(_GNU_SOURCE)
#define _GNU_SOURCE
#endif

#include "quest_runtime_internal.h"

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
    QException *exc = (QException *)quest_alloc(sizeof(QException), &quest_layout_exception);
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

/* Prints frames to out, most recent first, collapsing a run of the same frame
   name */
typedef struct QFramePrinter {
    FILE       *out;
    const char *name;
    int64_t     count;
} QFramePrinter;

static void quest_frames_flush(QFramePrinter *p) {
    if (p->name == NULL) return;
    fprintf(p->out, "  in %s\n", p->name);
    if (p->count > 1) fprintf(p->out, "  ... %s repeated %lld more times\n", p->name, (long long)(p->count - 1));
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

#if defined(__APPLE__) && defined(__aarch64__)
#include <dlfcn.h>
#include <pthread.h>
#define Q_HAVE_UNWIND 1
#define Q_FRAME_POINTER_WALK 1
#elif defined(__APPLE__) || (defined(__linux__) && defined(__GLIBC__))
#include <unwind.h>
#define Q_HAVE_UNWIND 1
#endif

#ifdef Q_HAVE_UNWIND
/* The start of the function containing pc, cached by pc (code is never
   unloaded), since a program that raises often from the same calls would
   otherwise spend most of its time finding them.

   On Darwin arm64 it is the symbol table's start (which has static functions,
   unless the binary is stripped), from dladdr. Elsewhere it is the unwinder's:
   Linux's unwind tables (.eh_frame) describe each function on its own. */
#define Q_FUNCTION_START_CACHE 1024

typedef struct QFunctionStart {
    const void *pc;
    const void *start;
} QFunctionStart;

static Q_THREAD_LOCAL QFunctionStart quest_function_starts[Q_FUNCTION_START_CACHE];

/* The functions whose code no image describes, registered by os/code
   (quest_code_add_function) for the JIT's code (docs/jit.md §3.6), each from
   its start up to its limit, kept in order of their starts */
typedef struct QFunctionRange {
    const void *start;
    const void *limit;
} QFunctionRange;

static QFunctionRange *quest_function_ranges = NULL;
static size_t          quest_function_ranges_count = 0;
static size_t          quest_function_ranges_capacity = 0;

static const void *quest_registered_function_start(const void *pc) {
    size_t low = 0, high = quest_function_ranges_count;
    while (low < high) {
        size_t mid = low + (high - low) / 2;
        if ((uintptr_t)pc < (uintptr_t)quest_function_ranges[mid].start) {
            high = mid;
        } else if ((uintptr_t)pc >= (uintptr_t)quest_function_ranges[mid].limit) {
            low = mid + 1;
        } else {
            return quest_function_ranges[mid].start;
        }
    }
    return NULL;
}

/* Registers a function from start up to limit; the JIT fills its arena from
   its start, so a function's start is usually above every earlier one's */
void quest_code_add_function(void *start, void *limit) {
    if (quest_function_ranges_count == quest_function_ranges_capacity) {
        size_t          capacity = quest_function_ranges_capacity > 0 ? 2 * quest_function_ranges_capacity : 64;
        QFunctionRange *ranges = (QFunctionRange *)realloc(quest_function_ranges, capacity * sizeof(QFunctionRange));
        if (ranges == NULL) return;
        quest_function_ranges = ranges;
        quest_function_ranges_capacity = capacity;
    }
    size_t i = quest_function_ranges_count++;
    while (i > 0 && (uintptr_t)quest_function_ranges[i - 1].start > (uintptr_t)start) {
        quest_function_ranges[i] = quest_function_ranges[i - 1];
        --i;
    }
    quest_function_ranges[i] = (QFunctionRange){ start, limit };
}

static const void *quest_function_start(void *pc) {
    uintptr_t       h = (uintptr_t)pc;
    QFunctionStart *cached = &quest_function_starts[((h >> 2) ^ (h >> 12)) % Q_FUNCTION_START_CACHE];
    if (cached->pc == pc) return cached->start;
    const void *start = quest_registered_function_start(pc);
    if (start == NULL) {
#ifdef Q_FRAME_POINTER_WALK
        Dl_info info;
        start = dladdr(pc, &info) != 0 ? info.dli_saddr : NULL;
#else
        start = _Unwind_FindEnclosingFunction(pc);
#endif
    }
    cached->pc = pc;
    cached->start = start;
    return start;
}

/* The start of the function of each frame of the stack, for a visitor */
typedef void (*QFrameVisitor)(const void *start, void *arg);

#ifdef Q_FRAME_POINTER_WALK
/* Every function on Darwin arm64 that calls another keeps a frame record, x29
   pointing at its caller's x29 and the return address: the arm64 backend's
   always, and clang's, which keeps frame pointers in non-leaf functions. A
   raise is a call, so every frame below it has one, and the walk follows the
   chain from fp to the stack's base (docs/exceptions.md §5.3). Unlike the
   unwinder, it needs no unwind information, so it steps through code that has
   none. */
static void quest_walk_frames_from(uintptr_t fp, QFrameVisitor visit, void *arg) {
    uintptr_t base = (uintptr_t)pthread_get_stackaddr_np(pthread_self());
    while (fp != 0 && (fp & 7) == 0 && fp < base) {
        const uintptr_t *record = (const uintptr_t *)fp;
        uintptr_t        ret = record[1];
        if (ret == 0) break;
        /* ret is the return address, which follows the call: a call to a
         * noreturn helper may end its function */
        visit(quest_function_start((void *)(ret - 1)), arg);
        if (record[0] <= fp) break;
        fp = record[0];
    }
}

static void quest_walk_stack(QFrameVisitor visit, void *arg) {
    quest_walk_frames_from((uintptr_t)__builtin_frame_address(0), visit, arg);
}
#else
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
#endif

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
#else
void quest_code_add_function(void *start, void *limit) {
    (void)start;
    (void)limit;
}
#endif

/* Prints the frames of the live stack, where an uncaught error is being
 * reported */
static void quest_print_live_frames(void) {
#ifdef Q_HAVE_UNWIND
    QFramePrinter printer = { stderr, NULL, 0 };
    quest_walk_stack(quest_print_live_frame, &printer);
    quest_frames_flush(&printer);
#endif
}

/* The frames of the live stack, captured at a raise a handler might catch and
 * raise again (§5.4) */
static const QTrace *quest_capture_trace(void) {
#ifdef Q_HAVE_UNWIND
    QTrace *trace = (QTrace *)quest_alloc(sizeof(QTrace), &quest_layout_trace);
    trace->n_runs = 0;
    trace->truncated = false;
    quest_walk_stack(quest_capture_frame, trace);
    return trace;
#else
    return NULL;
#endif
}

static void quest_print_trace(const QTrace *trace, FILE *out) {
    QFramePrinter printer = { out, NULL, 0 };
    for (int i = 0; i < trace->n_runs; ++i) quest_frames_add(&printer, trace->starts[i], trace->counts[i]);
    quest_frames_flush(&printer);
    if (trace->truncated) fprintf(out, "  ... (traceback truncated)\n");
}

/* os/code's frames of a raised exception (quest_code.c): the lines the
   runtime prints for one uncaught */
QString *quest_code_frames(QRaised *r) {
    char  *text = NULL;
    size_t length = 0;
    FILE  *out = open_memstream(&text, &length);
    if (out == NULL) return quest_string_new("", 0);
    if (r->state.trace != NULL) quest_print_trace(r->state.trace, out);
    fclose(out);
    QString *s = quest_string_new(text, (int64_t)length);
    free(text);
    return s;
}

/* Ends the program after an error's message has been printed, printing the site
   it was raised at, if known, which the driver reads to locate the error in the
   source (docs/exceptions.md §2.2), and the frames running there: those
   captured at the raise, if any, else the live stack's */
static Q_NORETURN void quest_fail_with(const char *loc, const QTrace *trace) {
    if (loc != NULL) fprintf(stderr, "  at %s\n", loc);
    if (trace != NULL) {
        quest_print_trace(trace, stderr);
    } else {
        quest_print_live_frames();
    }
    exit(1);
}

Q_NORETURN void quest_fail_at(const char *loc) {
    quest_fail_with(loc, NULL);
}

/* Whether a handler from h out will catch exc (docs/exceptions.md §5.1): 1 if
   one will, 0 if none will, -1 if one might (its patterns are computed when it
   runs) or will and needs the frames (an else branch naming the exception,
   which it may raise again) */
static int quest_handlers_catch(const QExceptionHandler *h, const QException *exc) {
    for (; h != NULL; h = h->prev) {
        if (h->n_catches == Q_CATCH_ALL) return 1;
        if (h->n_catches == Q_CATCH_UNKNOWN || h->n_catches == Q_CATCH_ALL_TRACED) return -1;
        for (int64_t i = 0; i < h->n_catches; ++i) {
            if (h->catches[i] == exc) return 1;
        }
    }
    return 0;
}

/* Resumes a native handler (docs/arm64.md §3.6): its stack and frame pointers
   restored, at its resume address */
static Q_NORETURN void quest_resume_native(const QExceptionHandler *h) {
#if defined(__aarch64__)
    __asm__ volatile("mov sp, %0\n\tmov x29, %1\n\tbr %2" : : "r"(h->sp), "r"(h->fp), "r"(h->resume) : "memory");
    __builtin_unreachable();
#else
    (void)h;
    abort();
#endif
}

/* Raises the exception that state describes; every raise, first or again,
 * ends here. Traceback frames can be read only from the live stack, before
 * the jump to a handler unwinds it, so the handler chain is searched first
 * (quest_handlers_catch, docs/exceptions.md §5.1), from the innermost handler
 * installed (a handler that raises again has already removed its own):
 *
 *   - none will catch it: write "Exception: " and the exception to stderr,
 *     then exit(1) after writing the raise site and the frames: those captured
 *     at an earlier raise if any, else the live stack's (quest_fail_with);
 *   - one might, or one will that may raise it again (an else branch naming
 *     it): capture the frames now (§5.4), unless state already has frames
 *     from an earlier raise, which are kept, as they show where it began;
 *   - one will: no frames are needed.
 *
 * Then it becomes quest_current_exception, every hold on collections is
 * released (quest_gc_release_all: the operation that held them is abandoned),
 * and control passes to the innermost handler, which tests its patterns and
 * raises again if none match: a native handler (arm64 code, docs/arm64.md §3.6)
 * by restoring its stack and frame pointers and branching to its resume
 * address, a C handler by Q_LONGJMP to its setjmp. Does not return */
void quest_reraise(QExceptionState state) {
    switch (quest_handlers_catch(quest_current_exception_handler, state.exc)) {
        case 0:
            fputs("Exception: ", stderr);
            quest_write_exception(stderr, &state);
            fputc('\n', stderr);
            quest_fail_with(state.loc, state.trace);
        case -1:
            if (state.trace == NULL) state.trace = quest_capture_trace();
            break;
        default:
            break;
    }
    quest_current_exception = state;
    /* A raise leaves every operation of the runtime's that held collections
     * off */
    quest_gc_release_all();
    if (quest_current_exception_handler->resume != NULL) quest_resume_native(quest_current_exception_handler);
    Q_LONGJMP(quest_current_exception_handler->env_jmp, 1);
}

void quest_raise_at(const QException *exc, QVal payload, const char *loc) {
    quest_reraise((QExceptionState){ exc, payload, loc, NULL, NULL, NULL });
}

void quest_raise_typed_at(const QException *exc, QVal payload, const QTypeDescriptor *type, const char *text,
                          const char *loc) {
    quest_reraise((QExceptionState){ exc, payload, loc, NULL, type, text });
}

void quest_raise(const QException *exc, QVal payload) {
    quest_raise_at(exc, payload, NULL);
}

QRaised *quest_raised_capture(const QExceptionState *state) {
    QRaised *r = quest_alloc(sizeof(QRaised), &quest_layout_raised);
    r->state = *state;
    return r;
}

QVal quest_raised_reraise(const QTypeDescriptor *a, QRaised *r) {
    (void)a;
    quest_reraise(r->state);
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
    uintptr_t addr = (uintptr_t)info->si_addr;
    if (quest_stack_low != 0 && addr + Q_STACK_REACH_BELOW >= quest_stack_low &&
        addr < quest_stack_low + Q_STACK_REACH_ABOVE) {
        fflush(stdout);
        fprintf(stderr, "Exception: stack.overflow\n");
        /* Nothing to check at exit: the handler's stack is not the one the
         * collector would scan */
        quest_gc_check_flags = 0;
#ifdef Q_FRAME_POINTER_WALK
        /* The handler runs on a stack of its own, so the frames are walked
         * from the faulting function's: its pc, then its x29's chain */
        const ucontext_t *uc = (const ucontext_t *)context;
        QFramePrinter     printer = { stderr, NULL, 0 };
        quest_frames_add(&printer, quest_function_start((void *)uc->uc_mcontext->__ss.__pc), 1);
        quest_walk_frames_from((uintptr_t)uc->uc_mcontext->__ss.__fp, quest_print_live_frame, &printer);
        quest_frames_flush(&printer);
        exit(1);
#else
        (void)context;
        quest_fail_with(NULL, NULL);
#endif
    }
    /* Returning faults again, with the default action */
    signal(sig, SIG_DFL);
}

void quest_install_stack_guard(void) {
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
#else
/* Without a guard, a stack overflow is the fault's default action */
void quest_install_stack_guard(void) {}
#endif

/* This file's global roots, for the collector and its roots check */
void quest_exceptions_roots(QRootVisitor add) {
    add(&quest_current_exception, sizeof(QExceptionState) / sizeof(void *));
    add(&quest_current_exception_handler, 1);
    add(&quest_func_tables, 1);
    add(&quest_function_ranges, 1);
}
