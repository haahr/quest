/*
 * Quest C Runtime: Printing Values
 *
 * Formatting reals as the interpreter does (the shortest digits that read back
 * as the value), and printing values for echo, by their descriptors, as the
 * interpreters print them.
 */

/* The POSIX functions -std=c99 hides on Linux (glibc) */
#if defined(__linux__) && !defined(_GNU_SOURCE)
#define _GNU_SOURCE
#endif

#include "quest_runtime_internal.h"

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
   docs/type-system.md §6.3.2. */
void quest_format_real(double r, char *out, size_t n) {
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

/* A character of a char or string literal, escaped as the interpreter writes
 * it, into out (at most 4 characters and a NUL); returns its length */
static int quest_escape_char(unsigned char c, char quote, char out[5]) {
    switch (c) {
        case '\n': return snprintf(out, 5, "\\n");
        case '\t': return snprintf(out, 5, "\\t");
        case '\r': return snprintf(out, 5, "\\r");
        case '\\': return snprintf(out, 5, "\\\\");
        default: break;
    }
    if (c == (unsigned char)quote) return snprintf(out, 5, "\\%c", c);
    if (c >= 32 && c <= 126) return snprintf(out, 5, "%c", c);
    return snprintf(out, 5, "\\x%02x", c);
}

/* Writes a character of a char or string literal, escaped */
static void quest_put_escaped_char(unsigned char c, char quote) {
    char out[5];
    fwrite(out, 1, (size_t)quest_escape_char(c, quote, out), stdout);
}

/* Appends a character of a char or string literal, escaped */
void quest_sb_append_escaped(QStringBuilder *b, unsigned char c, char quote) {
    char out[5];
    int n = quest_escape_char(c, quote, out);
    for (int i = 0; i < n; ++i) quest_sb_append_char(b, (QChar)out[i]);
}

/* The REPL's results, captured while the JIT runs an input (docs/jit.md
 * section 3.8): the echo printers below write to the capture's stream, made
 * stdout while they write, rather than to stdout, so the program's own output
 * is not captured */
static FILE  *quest_echo_stream = NULL;
static char  *quest_echo_buffer = NULL;
static size_t quest_echo_length = 0;

void quest_echo_capture(void) {
    if (quest_echo_stream != NULL) {
        fclose(quest_echo_stream);
        free(quest_echo_buffer);
    }
    quest_echo_buffer = NULL;
    quest_echo_length = 0;
    quest_echo_stream = open_memstream(&quest_echo_buffer, &quest_echo_length);
}

QString *quest_echo_captured(void) {
    if (quest_echo_stream == NULL) return quest_string_new("", 0);
    fclose(quest_echo_stream);
    QString *s = quest_string_new(quest_echo_buffer, (int64_t)quest_echo_length);
    free(quest_echo_buffer);
    quest_echo_stream = NULL;
    quest_echo_buffer = NULL;
    return s;
}

/* An echo printer's body runs with stdout the capture's stream, if any */
#define Q_ECHO_BEGIN                                       \
    FILE *q_echo_saved = stdout;                           \
    if (quest_echo_stream != NULL) stdout = quest_echo_stream
#define Q_ECHO_END stdout = q_echo_saved

/* Writes text and a newline: what echo shows of a phrase without a value (a
 * declaration of a type, say) */
void quest_echo_text(const char *text) {
    Q_ECHO_BEGIN;
    fputs(text, stdout);
    putchar('\n');
    Q_ECHO_END;
}

/* Writes prefix, val, suffix, and a newline. kind says how to write the value,
 * as the interpreter writes a value of that type (format_value_with_type): a
 * base type (Int, Real, Bool, Char, String, Ok, or Word), "fun" for a function,
 * "hidden" for a value of an abstract type, and anything else as <val>
 * (compiled code writes values of other types with quest_print_typed). */
void quest_print_value(const char *prefix, QVal val, const char *kind, const char *suffix) {
    Q_ECHO_BEGIN;
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
    Q_ECHO_END;
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
    if (quest_print_depth < Q_PRINT_NESTING_MAX) quest_print_nesting[quest_print_depth] = NULL;
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

void quest_write_exception(FILE *out, const QExceptionState *state) {
    fputs((state->exc != NULL && state->exc->name != NULL) ? state->exc->name : "<unknown>", out);
    if (state->payload_type == NULL || state->payload_text == NULL) return;
    fputs(" with ", out);
    /* quest_put_value writes to stdout */
    fflush(stdout);
    FILE *saved = stdout;
    stdout = out;
    quest_put_value(state->payload, state->payload_type, NULL);
    stdout = saved;
    fprintf(out, ":%s", state->payload_text);
}

void quest_print_typed(const char *prefix, QVal val, const QTypeDescriptor *type, const char *suffix) {
    Q_ECHO_BEGIN;
    fputs(prefix, stdout);
    quest_put_value(val, type, NULL);
    fputs(suffix, stdout);
    putchar('\n');
    Q_ECHO_END;
}

/* This file's global roots, for the collector and its roots check */
void quest_print_roots(QRootVisitor add) {
    add(&quest_echo_buffer, 1);
    add(quest_print_nesting, Q_PRINT_NESTING_MAX);
}
