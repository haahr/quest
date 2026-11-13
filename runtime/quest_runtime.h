/*
 * Quest C Runtime Interface
 *
 * The C representation of Quest values and types and the runtime's interface:
 * what generated code and the runtime's own files (quest_runtime.c, quest_gc.c,
 * quest_serialization.c, ...) agree on. The C that both compilers generate
 * includes this header; the self-hosted compiler's arm64 backend and JIT, which
 * emit machine code, mirror its structs and constants in repr/runtimeLayout,
 * which a test checks against this header (docs/arm64.md §3.3).
 *
 * The header is part of the artifact contract, the ABI: compiled units and
 * interface artifacts are reused only by a compiler with the same ABI_VERSION
 * (bootstrap/python/quest/config/abi.py, questlang/config/abi.mod.quest), and
 * the ABI corpus records a digest of the bytes of this file and the two it
 * includes, quest_types.h and quest_gc.h, so that a change to any of them
 * fails tests/python/test_abi_corpus.py until the version is bumped (or, after
 * a change that is not incompatible, the digest regenerated;
 * docs/build-process.md §5.2.3).
 *
 * In order: portability macros; the representation of values (QVal, strings,
 * closures, arrays, records, variants, options, exceptions); type descriptors,
 * the run-time descriptions of types, with their per-kind metadata, templates,
 * auto values, and the base descriptors (quest_types.h); exception state,
 * handlers, and tracebacks; the built-in exceptions; the collector's interface
 * (quest_gc.h: object layouts, write barriers, root and frame tables,
 * allocation); the runtime's functions, from raises and the standard library's
 * primitives to descriptor operations, proxies, conversions, and view maps;
 * inline helpers for checked operations, arithmetic, identity, words, and
 * hashing; built-in operator closures; and the JIT's primitives.
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

/* A string (docs/c-representation.md §3.2): a header holding its length and a pointer to its bytes, a separate
 * pointer-free allocation of length + 1 bytes ending in a NUL, so that data can be passed to C as it is (a string may
 * also hold NULs of its own). Strings are mutable in place (string.setChar, string.setSub) but never change length,
 * so every string literal is a fresh quest_string_new at each evaluation, not shared static data. capacity is always
 * equal to length, and nothing reads it. */
typedef struct QString {
    int64_t length;
    int64_t capacity;
    char   *data;
} QString;

/* A closure (docs/c-representation.md §6.1, §6.2), passed by pointer. fn is a C function whose first parameter is
 * env, followed by the descriptors of the function type's type parameters, then its value parameters in their C
 * types (var and out parameters as pointers); its result is the result type's C type, or void for Ok. A closure is
 * called through a cast of fn to that signature, as ((R (*)(void *, ...))c->fn)(c->env, ...). env points to a
 * struct of the captured variables, or is NULL for a function that captures none, whose closure is a static
 * singleton. */
typedef struct QClosure {
    void *fn;
    void *env;
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

/* A record value, 16 bytes passed by value (in a register pair on arm64; docs/c-representation.md §5.2). val is the
 * payload: a QRecordHeader followed by the fields, sorted by name, one slot each. dict is the offset table of the
 * type the value is viewed at: the byte offset in the payload of each of that type's fields, in name order (see
 * quest_record_dict). A field cannot have one offset for every record type that has it, since a record of one type
 * may be used at any of its supertypes, which drop fields; so code reads field i at val + dict[i]. Viewing a
 * record at a supertype changes dict only, never copying the payload. In a slot (a tuple component, record field,
 * option payload, array element, or auto component) a record is a pointer to a box holding its QRecordVal. */
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

/* An option object (docs/c-representation.md §5.3): its tag, the index of its case among the option type's cases
 * ordered by name, followed in place by the case's components, laid out as a tuple of them */
typedef struct QOptionHeader {
    int64_t tag;
    QVal    fields[];
} QOptionHeader;

/* An exception (docs/c-representation.md §7.1), identified by its address: each evaluation of an exception
 * declaration makes a new one (quest_alloc_exception), so two exceptions of the same name are distinct. name is
 * only for display. */
typedef struct QException {
    const char *name;
} QException;

#include "quest_types.h"

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

/* The state every try and raise share (docs/c-representation.md §7, docs/arm64.md §3.6). The handler is the
   innermost try's, the top of a stack linked through prev. A try pushes its handler (its prev the old top) and, in C,
   calls Q_SETJMP; leaving its body, normally or by a jump or return out of it, pops it. A raise (quest_reraise) does
   not pop: it sets quest_current_exception and transfers to the top handler, which pops itself, reads
   quest_current_exception, and raises it again if none of its patterns match. Both are roots of the collector, since
   a payload may point into the heap. */
extern Q_THREAD_LOCAL QExceptionHandler *quest_current_exception_handler;
extern Q_THREAD_LOCAL QExceptionState    quest_current_exception;

/* Built-in singleton exception descriptors */
extern const QException quest_exc_arrayOp_error;
extern const QException quest_exc_string_error;
extern const QException quest_exc_variant_error;
extern const QException quest_exc_dynamic_error;
extern const QException quest_exc_value_error;


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

#include "quest_gc.h"

/* Strings and arrays: the primitives behind the string and stringOp modules, string literals, <>, and arrays.
 * quest_string_new copies len bytes of src (strlen(src) when len is negative) into a new string. A substring is
 * given by its start and size; an index or substring outside its string, or a negative size, raises string.error,
 * and a negative length given to quest_array_new raises arrayOp.error. Every function that returns a string
 * returns a new one; set_char and set_sub write into their string in place. precedes and precedes_sub are <=
 * by bytes, compared as unsigned. quest_array_new's layout says whether its elements are pointers, scalars, or
 * QVals of unknown kind, for the collector (quest_layout_array_pointer and its siblings). */
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
/* A new exception named name, distinct from every other: an exception declaration's value */
const QException *quest_alloc_exception(const char *name);
/* Raises: generated code passes the raise site (docs/exceptions.md §3.3); the runtime's primitives raise with none */
Q_NORETURN void quest_raise(const QException *exc, QVal payload);
Q_NORETURN void quest_raise_at(const QException *exc, QVal payload, const char *loc);
/* A raise with a payload of a type other than Ok: the payload's type's descriptor, and the type as written */
Q_NORETURN void quest_raise_typed_at(const QException *exc, QVal payload, const QTypeDescriptor *type, const char *text,
                                     const char *loc);
/* Raises the exception state describes, the end of every raise, first or again (a handler none of whose patterns
   match, raised.reraise): passes it to the innermost handler, or, when no handler will catch it, reports it and exits
   with status 1. Keeps state's frames if it has some, so that a traceback shows where the exception was first raised
   (quest_runtime.c has the details; docs/exceptions.md §5.1) */
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

/* Initializes the runtime's part of the standard library, once, from a compiled program's main after quest_gc_init
 * and before any unit's initialization (docs/extensions.md, Runtime Initialization Contract): the standard writers
 * and reader (stdout made line-buffered when QUEST_LINE_BUFFERED is set and nonempty), system.args from argc and
 * argv, and, where the platform has it, the guard that reports a stack overflow (docs/exceptions.md §6) */
void quest_builtins_init(int argc, char **argv);

/* Whether the type sub describes is a subtype of super_type's, compared by structure, not by address (dynamic.be,
 * inspect, and the runtime's own checks) */
bool                   quest_is_subtype(const QTypeDescriptor *sub, const QTypeDescriptor *super_type);
/* Descriptors made at run time, for the runtime's tests (tests/python); compiled code never calls these, and emits
 * its descriptors statically. Each call makes a new descriptor, equal to another of the same type as
 * quest_is_subtype compares them. The record, tuple, variant, and function constructors follow the abstract types
 * below. */
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
/* More descriptors made at run time for the tests (see quest_make_array_descriptor) */
const QTypeDescriptor *quest_make_record_descriptor(
    const char *name, size_t size, size_t alignment, size_t field_count, const QRecordFieldDescriptor *fields);
const QTypeDescriptor *quest_make_variant_descriptor(
    const char *name, size_t size, size_t alignment, size_t case_count, const QVariantCaseDescriptor *cases);
const QTypeDescriptor *quest_make_fun_descriptor(
    const char *name, size_t param_count, const QFunParamDescriptor *params, const QTypeDescriptor *result_type);
/* The variant value that payload points to (a boxed QVariantVal of type sub_desc) viewed at variant type
 * super_desc, a supertype: its tag renumbered to super_desc's tag for the case of the same name, since each variant
 * type numbers its cases on its own (docs/c-representation.md §5.3), and its payload converted (quest_convert) when
 * the two cases' payload types differ. The tag maps are cached by the pair of descriptors' addresses. A NULL payload
 * gives tag 0, and so does a case super_desc lacks, silently: the caller must pass a true supertype, which has every
 * case of sub_desc. */
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
 * records get the offset table for the view, variants their tags in `to` (quest_variant_adapt), tuples and options
 * a proxy (quest_make_proxy) where values of `to` may be proxies and otherwise a copy with their components
 * converted, auto values a copy, and functions are wrapped by `to`'s adapter. A value whose layout already suits
 * `to` (quest_layout_equivalent) is returned as it is; an array, a copied tuple with var components, or an exception
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

/* Hashing, for lib/util/hash: quest_hash_mix64 is SplitMix64's finalizer, which spreads every input bit over the
 * output (quest_hash_mix, hash.mix, calls it); quest_hash_combine folds h2 into h1 in the manner of Boost's
 * hash_combine; quest_identity_hash (hash.identityHash) hashes x at type t so that values is takes as equal hash
 * equally (quest_val_is), most values by their bits (an object's are its address) */
Q_INLINE uint64_t quest_hash_mix64(uint64_t z) {
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

uint64_t quest_hash_mix(uint64_t w);
uint64_t quest_hash_combine(uint64_t h1, uint64_t h2);
uint64_t quest_identity_hash(const QTypeDescriptor *t, QVal x);

/* The built-in operators as values, when a program uses one other than by applying it (passing + to a fold): static
 * closures with no environment, named as repr/symbols mangles the operator's name (qv_sym_ and the names of its
 * characters, or qv_mod for mod) followed by _closure, which compiled code refers to as &qv_sym_plus_closure. Each
 * computes what the operator applied directly does, raising int.error or real.error where it does (quest_runtime.c) */
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
