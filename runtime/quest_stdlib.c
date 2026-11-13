/*
 * Quest C Runtime: The Standard Library's Primitives
 *
 * The C primitives of writers and readers (standard output and input among
 * them), conversions, string utilities and builders, ascii, reals, words,
 * and hashing.
 */

/* The POSIX functions -std=c99 hides on Linux (glibc) */
#if defined(__linux__) && !defined(_GNU_SOURCE)
#define _GNU_SOURCE
#endif

#include "quest_runtime_internal.h"

/* Writer module primitives */
QWriter quest_writer_output_val = { NULL, false, false };
QWriter quest_writer_err_val    = { NULL, false, false };

/* Standard output is line-buffered, as at a terminal, when QUEST_LINE_BUFFERED
 * is set and not empty: the Jupyter kernel sets it for the driver it runs, so
 * that a cell's output appears while the cell runs (docs/jupyter-kernel.md). It
 * must be set before anything is written. */
void quest_writer_init_std(void) {
    if (quest_writer_output_val.file == NULL) {
        const char *line = getenv("QUEST_LINE_BUFFERED");
        if (line != NULL && line[0] != '\0') setvbuf(stdout, NULL, _IOLBF, 0);
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
    QWriter *w = (QWriter *)quest_alloc(sizeof(QWriter), &quest_layout_writer);
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

void quest_reader_init_std(void) {
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
    QReader *r = (QReader *)quest_alloc(sizeof(QReader), &quest_layout_reader);
    r->file = f;
    r->peek_char = -1;
    r->is_file = true;
    r->is_closed = false;
    return r;
}

/* Whether r has a character left before its end: one already peeked, or the
 * next, read and kept as the peeked character. Blocks until a character or
 * the end arrives */
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

/* reader.ready: the same as quest_reader_more, so it too may block; there is
 * no test for a character that can be read without waiting */
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
    char *buf = (char *)quest_alloc_bytes((size_t)size + 1);
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
    QString *res = (QString *)quest_alloc(sizeof(QString), &quest_layout_string);
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

/* conv.char and conv.string: quoted, with escapes, as the interpreters write
 * them (and as quest_print_value does) */
QString *quest_conv_char(QChar ch) {
    QStringBuilder *b = quest_sb_new();
    quest_sb_append_char(b, '\'');
    quest_sb_append_escaped(b, ch, '\'');
    quest_sb_append_char(b, '\'');
    return quest_sb_to_string(b);
}

QString *quest_conv_string(const QString *s) {
    QStringBuilder *b = quest_sb_new();
    quest_sb_append_char(b, '"');
    for (int64_t i = 0; s != NULL && i < s->length; ++i) quest_sb_append_escaped(b, (unsigned char)s->data[i], '"');
    quest_sb_append_char(b, '"');
    return quest_sb_to_string(b);
}

/* Strutil module primitives */
double quest_strutil_to_real(const QString *s) {
    /* strutil.tryToReal has checked the syntax; strtod rounds correctly, and
     * overflows to an infinity */
    return s == NULL ? 0.0 : strtod(s->data, NULL);
}

/* StringBuilder native buffer (see quest_runtime.h) */
QStringBuilder *quest_sb_new(void) {
    char *buffer = (char *)quest_alloc_bytes(QUEST_SB_BUFFER_SIZE);
    QStringBuilder *b = (QStringBuilder *)quest_alloc(sizeof(QStringBuilder), &quest_layout_string_builder);
    b->buffer = buffer;
    return b;
}

/* Adds a finished chunk of len bytes at data, which the chunk takes over */
static void quest_sb_add_chunk(QStringBuilder *b, char *data, int64_t len) {
    if (b->chunk_count == b->chunk_capacity) {
        int64_t capacity = b->chunk_capacity ? b->chunk_capacity * 2 : 8;
        QString **chunks = (QString **)quest_alloc_sized((size_t)capacity * sizeof(QString *), &quest_layout_pointers);
        if (b->chunk_count > 0) memcpy(chunks, b->chunks, (size_t)b->chunk_count * sizeof(QString *));
        quest_barrier(b);
        b->chunks = chunks;
        b->chunk_capacity = capacity;
    }
    QString *chunk = (QString *)quest_alloc(sizeof(QString), &quest_layout_string);
    chunk->length = len;
    chunk->capacity = len;
    chunk->data = data;
    quest_barrier_slot(&b->chunks[b->chunk_count]);
    b->chunks[b->chunk_count++] = chunk;
}

/* Turns a nonempty working buffer into a chunk, and starts a new one */
static void quest_sb_flush(QStringBuilder *b) {
    if (b->used == 0) return;
    quest_sb_add_chunk(b, b->buffer, b->used);
    char *buffer = (char *)quest_alloc_bytes(QUEST_SB_BUFFER_SIZE);
    quest_barrier(b);
    b->buffer = buffer;
    b->used = 0;
}

static void quest_sb_append_bytes(QStringBuilder *b, const char *data, int64_t len) {
    if (len <= 0) return;
    b->length += len;
    if (len > QUEST_SB_LONG_APPEND) {
        quest_sb_flush(b);
        char *copy = (char *)quest_alloc_bytes((size_t)len);
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
    char *data = (char *)quest_alloc_bytes((size_t)b->length + 1);
    QString *s = (QString *)quest_alloc(sizeof(QString), &quest_layout_string);
    s->length = b->length;
    s->capacity = b->length;
    s->data = data;
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

/* The libm functions RealOp extends Typeful Programming's with; each raises
 * real.error where its result would be NaN (a negative square root, the sine of
 * an infinity, an arc sine outside [-1, 1]) */
double quest_real_sqrt(double r) { return quest_real_result(sqrt(r)); }
double quest_real_sin(double r) { return quest_real_result(sin(r)); }
double quest_real_cos(double r) { return quest_real_result(cos(r)); }
double quest_real_tan(double r) { return quest_real_result(tan(r)); }
double quest_real_asin(double r) { return quest_real_result(asin(r)); }
double quest_real_acos(double r) { return quest_real_result(acos(r)); }
double quest_real_atan(double r) { return quest_real_result(atan(r)); }
double quest_real_atan2(double y, double x) { return quest_real_result(atan2(y, x)); }
double quest_real_exponential(double r) { return quest_real_result(exp(r)); }
double quest_real_sinh(double r) { return quest_real_result(sinh(r)); }
double quest_real_cosh(double r) { return quest_real_result(cosh(r)); }
double quest_real_tanh(double r) { return quest_real_result(tanh(r)); }

int64_t quest_real_ceil(double r) {
    return quest_real_to_int(ceil(r));
}

int64_t quest_real_trunc(double r) {
    return quest_real_to_int(trunc(r));
}

QString *quest_real_format(double r, QChar style, int64_t digits) {
    if ((style != 'e' && style != 'f' && style != 'g') || digits < 0 || digits > 100) {
        quest_raise_real_error();
    }
    char spec[8];
    snprintf(spec, sizeof spec, "%%.%d%c", (int)digits, (char)style);
    int n = snprintf(NULL, 0, spec, r);
    char *buf = (char *)quest_alloc_bytes((size_t)n + 1);
    snprintf(buf, (size_t)n + 1, spec, r);
    return quest_string_new(buf, n);
}

/* Word module primitives; the rest are static inline in quest_runtime.h */
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
    t = quest_identity_type(t);
    if (t != NULL && t->kind == QTYPE_KIND_REAL && x.r == 0.0) {
        x.u = 0;
    }
    if (t != NULL && t->kind == QTYPE_KIND_OPTION) return quest_option_identity_hash(t, x.p);
    if (t != NULL && t->kind == QTYPE_KIND_TUPLE) {
        /* A proxy hashes as the object it is a view of, as is compares them */
        x.p = quest_unproxy(x.p);
    }
    return quest_hash_mix64(x.u);
}
