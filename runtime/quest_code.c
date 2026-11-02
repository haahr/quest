/* Quest Runtime: the JIT's Unsound Primitives
 *
 * The natives of lib/os/value (Cardelli's Value: any value as a word, and the
 * words of memory) and lib/os/code (code regions, the running binary's
 * symbols, calls under an exception handler, and the runtime's registries),
 * which the JIT is built on (docs/jit.md section 3.11). Executable regions are
 * Darwin arm64's (MAP_JIT); elsewhere reserving one raises value.error. */

#include "quest_runtime.h"

#include <dlfcn.h>
#include <string.h>
#include <sys/mman.h>
#if defined(__APPLE__) && defined(__aarch64__)
#include <libkern/OSCacheControl.h>
#include <pthread.h>
#define Q_HAVE_CODE_REGIONS 1
#endif

const QException quest_exc_value_error = { "value.error" };

static Q_NORETURN void quest_value_fail(void) {
    quest_raise(&quest_exc_value_error, Q_OK_VAL);
    __builtin_unreachable();
}

/* ============================================================================
 * os/value
 * ============================================================================ */

/* A slot holds one word, the value's slot representation, so new and be are
   the identity on it */
void *quest_value_new(const QTypeDescriptor *a, QVal x) {
    (void)a;
    return x.p;
}

QVal quest_value_be(const QTypeDescriptor *a, void *v) {
    (void)a;
    return (QVal){ .p = v };
}

static void **quest_value_word(void *addr, int64_t displ) {
    uintptr_t p = (uintptr_t)addr + (uintptr_t)displ;
    if (addr == NULL || (p & 7) != 0) quest_value_fail();
    return (void **)p;
}

void *quest_value_fetch(void *addr, int64_t displ) {
    return *quest_value_word(addr, displ);
}

void quest_value_store(void *addr, int64_t displ, void *w) {
    *quest_value_word(addr, displ) = w;
}

/* ============================================================================
 * os/code: regions
 * ============================================================================ */

struct QCodeRegion {
    char   *base;
    int64_t size;
    bool    executable;
};

QCodeRegion *quest_code_reserve(int64_t size, bool executable) {
    int prot = PROT_READ | PROT_WRITE;
    int flags = MAP_PRIVATE | MAP_ANON;
    if (executable) {
#ifdef Q_HAVE_CODE_REGIONS
        prot |= PROT_EXEC;
        flags |= MAP_JIT;
#else
        quest_value_fail();
#endif
    }
    if (size <= 0) quest_value_fail();
    void *p = mmap(NULL, (size_t)size, prot, flags, -1, 0);
    if (p == MAP_FAILED) quest_value_fail();
    QCodeRegion *r = (QCodeRegion *)quest_alloc(sizeof(QCodeRegion));
    r->base = (char *)p;
    r->size = size;
    r->executable = executable;
    return r;
}

void *quest_code_base(QCodeRegion *r) {
    return r->base;
}

int64_t quest_code_size(QCodeRegion *r) {
    return r->size;
}

/* Copies n words of width bytes into r at offset, with the region writable
   for the thread meanwhile, and the instruction cache made coherent after */
static void quest_code_write(QCodeRegion *r, int64_t offset, const QArray *words, int64_t width) {
    int64_t n = words->length;
    if (offset < 0 || offset % width != 0 || n > (r->size - offset) / width) quest_value_fail();
    char *dest = r->base + offset;
#ifdef Q_HAVE_CODE_REGIONS
    if (r->executable) pthread_jit_write_protect_np(0);
#endif
    for (int64_t i = 0; i < n; ++i) {
        if (width == 4) {
            uint32_t w = (uint32_t)words->data[i].u;
            memcpy(dest + 4 * i, &w, 4);
        } else {
            uint64_t w = words->data[i].u;
            memcpy(dest + 8 * i, &w, 8);
        }
    }
#ifdef Q_HAVE_CODE_REGIONS
    if (r->executable) {
        pthread_jit_write_protect_np(1);
        sys_icache_invalidate(dest, (size_t)(n * width));
    }
#endif
}

void quest_code_write32(QCodeRegion *r, int64_t offset, QArray *words) {
    quest_code_write(r, offset, words, 4);
}

void quest_code_write64(QCodeRegion *r, int64_t offset, QArray *words) {
    quest_code_write(r, offset, words, 8);
}

/* ============================================================================
 * os/code: symbols
 * ============================================================================ */

void *quest_code_symbol(const QString *name) {
    return dlsym(RTLD_DEFAULT, name->data);
}

bool quest_code_is_null(void *v) {
    return v == NULL;
}

/* Compiled code reads a thread-local through its descriptor: it loads the
   descriptor's first word, a function, and calls it with the descriptor in
   x0, and the function returns the variable's address, changing no register
   but x0, x16, and x17. This one returns the descriptor's second word, so a
   descriptor of the loader's, holding the address on the main thread, serves
   for JIT code (docs/jit.md section 3.5). */
#ifdef Q_HAVE_CODE_REGIONS
__asm__(".text\n"
        ".p2align 2\n"
        "_quest_code_tlv_get:\n"
        "\tldr x0, [x0, #8]\n"
        "\tret\n");
extern char quest_code_tlv_get[] __asm__("_quest_code_tlv_get");

void *quest_code_tlv_getter(void) {
    return quest_code_tlv_get;
}
#else
void *quest_code_tlv_getter(void) {
    quest_value_fail();
}
#endif

/* ============================================================================
 * os/code: calls
 * ============================================================================ */

static Q_THREAD_LOCAL QRaised *quest_code_raised = NULL;

/* Calls entry under a handler that catches every exception with its frames,
   as a try whose else branch names the exception does: whatever backend built
   the code that raises, the handler's resume is null, so the raise jumps to
   its env_jmp */
bool quest_code_call(void *entry) {
    QExceptionHandler h;
    h.prev = quest_current_exception_handler;
    h.catches = NULL;
    h.n_catches = Q_CATCH_ALL_TRACED;
    h.resume = NULL;
    h.sp = NULL;
    h.fp = NULL;
    quest_current_exception_handler = &h;
    if (Q_SETJMP(h.env_jmp) == 0) {
        ((void (*)(void))entry)();
        quest_current_exception_handler = h.prev;
        return false;
    }
    quest_current_exception_handler = h.prev;
    quest_code_raised = quest_raised_capture(&quest_current_exception);
    return true;
}

QRaised *quest_code_last_raised(void) {
    return quest_code_raised;
}

QString *quest_code_exception_name(QRaised *r) {
    char *text = NULL;
    size_t length = 0;
    FILE *out = open_memstream(&text, &length);
    quest_write_exception(out, &r->state);
    fclose(out);
    QString *s = quest_string_new(text, (int64_t)length);
    free(text);
    return s;
}

QString *quest_code_raise_site(QRaised *r) {
    const char *loc = r->state.loc != NULL ? r->state.loc : "";
    return quest_string_new(loc, (int64_t)strlen(loc));
}

/* ============================================================================
 * os/code: the runtime's registries
 * ============================================================================ */

void quest_code_add_roots(void *low, void *high) {
#ifndef QUEST_NOGC
    GC_add_roots(low, high);
#else
    (void)low;
    (void)high;
#endif
}

void quest_code_set_args(QArray *args) {
    quest_system_args = args;
}
