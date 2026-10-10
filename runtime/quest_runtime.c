/*
 * Quest C Runtime Implementation
 * Part of Step 4: Bootstrap C Transpiler
 */

#include "quest_runtime.h"

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

QArrayWideRecord *quest_array_new_wide_record(int64_t len, QRecordVal init_val) {
    if (len < 0) {
        quest_raise_array_error();
    }
    QArrayWideRecord *arr = (QArrayWideRecord *)quest_alloc(
        sizeof(QArrayWideRecord) + (size_t)len * sizeof(QRecordVal)
    );
    arr->length = len;
    for (int64_t i = 0; i < len; ++i) {
        arr->data[i] = init_val;
    }
    return arr;
}

QArrayWideVariant *quest_array_new_wide_variant(int64_t len, QVariantVal init_val) {
    if (len < 0) {
        quest_raise_array_error();
    }
    QArrayWideVariant *arr = (QArrayWideVariant *)quest_alloc(
        sizeof(QArrayWideVariant) + (size_t)len * sizeof(QVariantVal)
    );
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

/* The ^^ operator and real.exp: a zero base with a negative exponent is a pole, like division by zero, and
   raises real.error; so does a NaN result (a negative base with a non-integral exponent). Overflow is an
   infinity. */
double quest_real_pow(double base, double exp) {
    if (base == 0.0 && exp < 0.0) {
        quest_raise_real_error();
    }
    return quest_real_result(pow(base, exp));
}

/* Exception handling globals */
Q_THREAD_LOCAL QExceptionHandler *quest_current_exception_handler = NULL;
Q_THREAD_LOCAL QExceptionState    quest_current_exception = { NULL, { .u = 0 } };

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

void quest_raise(const QException *exc, QVal payload) {
    if (quest_current_exception_handler == NULL) {
        const char *name = (exc != NULL && exc->name != NULL) ? exc->name : "<unknown>";
        fprintf(stderr, "Exception: %s\n", name);
        exit(1);
    }
    quest_current_exception.exc = exc;
    quest_current_exception.payload = payload;
    longjmp(quest_current_exception_handler->env_jmp, 1);
}

void quest_raise_array_error(void) {
    quest_raise(&quest_exc_arrayOp_error, Q_OK_VAL);
}

void quest_raise_string_error(void) {
    quest_raise(&quest_exc_string_error, Q_OK_VAL);
}

void quest_raise_variant_error(void) {
    quest_raise(&quest_exc_variant_error, Q_OK_VAL);
}

void quest_raise_dynamic_error(void) {
    quest_raise(&quest_exc_dynamic_error, Q_OK_VAL);
}

void quest_option_ordinal_error(int64_t n, int64_t count) {
    fprintf(stderr, "Option ordinal %lld out of bounds (0 <= ordinal < %lld)\n", (long long)n, (long long)count);
    exit(1);
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

void quest_raise_int_error(void) {
    quest_raise(&quest_exc_int_error, Q_OK_VAL);
}

void quest_raise_real_error(void) {
    quest_raise(&quest_exc_real_error, Q_OK_VAL);
}

void quest_raise_word_error(void) {
    quest_raise(&quest_exc_word_error, Q_OK_VAL);
}

void quest_raise_system_error(void) {
    quest_raise(&quest_exc_system_error, Q_OK_VAL);
}

/* Writes a real as the interpreter does (Python's repr): the shortest digits that read back as the same value, in
 * positional notation when the decimal exponent is in [-4, 16) and in scientific notation otherwise. */
static void quest_put_real(double r) {
    if (isnan(r)) {
        fputs("nan", stdout);
        return;
    }
    if (isinf(r)) {
        fputs(r > 0.0 ? "inf" : "-inf", stdout);
        return;
    }
    char buf[40];
    for (int precision = 1; precision <= 17; ++precision) {
        snprintf(buf, sizeof buf, "%.*e", precision - 1, r);
        if (strtod(buf, NULL) == r) break;
    }
    const char *p = buf;
    if (*p == '-') {
        putchar('-');
        ++p;
    }
    char digits[24];
    int n = 0;
    for (; *p != '\0' && *p != 'e'; ++p) {
        if (*p >= '0' && *p <= '9') digits[n++] = *p;
    }
    while (n > 1 && digits[n - 1] == '0') --n;
    digits[n] = '\0';
    int exponent = *p == 'e' ? atoi(p + 1) : 0;
    if (exponent < -4 || exponent >= 16) {
        putchar(digits[0]);
        if (n > 1) printf(".%s", digits + 1);
        printf("e%c%02d", exponent < 0 ? '-' : '+', exponent < 0 ? -exponent : exponent);
    } else if (exponent < 0) {
        fputs("0.", stdout);
        for (int i = 0; i < -exponent - 1; ++i) putchar('0');
        fputs(digits, stdout);
    } else {
        for (int i = 0; i <= exponent; ++i) putchar(i < n ? digits[i] : '0');
        putchar('.');
        fputs(n > exponent + 1 ? digits + exponent + 1 : "0", stdout);
    }
}

/* Writes a character of a char or string literal, escaped as the interpreter does */
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

/* Writes prefix, val, suffix, and a newline. kind says how to write the value, as the interpreter writes a value of
 * that type (format_value_with_type): a base type (Int, Real, Bool, Char, String, Ok, or Word), "fun" for a
 * function, "hidden" for a value of an abstract type, and anything else as <val> (compiled code writes values of
 * other types with quest_print_typed). */
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

/* Writes the result of an expression of type type_name, whose value is formatted by that name (see
 * quest_print_value); nothing for Ok */
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
            /* Cardelli §6.7: a subkind for the type component, then, as for tuples, a prefix of the components with
             * matching names, covariant immutable and invariant var components */
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
            /* An abstract type operator's applications are equal when their arguments are equal types */
            const QOpaqueTypeDescriptor *s = (const QOpaqueTypeDescriptor *)sub->extra;
            const QOpaqueTypeDescriptor *t = (const QOpaqueTypeDescriptor *)super_type->extra;
            if (result && sub != super_type && (s != NULL || t != NULL)) {
                result = s != NULL && t != NULL && s->arg_count == t->arg_count;
                for (size_t i = 0; result && i < t->arg_count; ++i) {
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
            /* Type parameters with equal bounds; contravariant value parameters, invariant var parameters, covariant
             * out parameters and result (the parameter descriptors refer to type parameters by index) */
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

/* An offset table lets code that knows a record only by a record type, its view, find the fields of a payload laid
 * out as another record type, its layout: entry i is the byte offset in the payload of the view's i-th field in name
 * order (record descriptors list their fields in name order). All tables live in one map keyed by (view, layout),
 * pre-populated with the static tables of compiled code and completed on demand from the two descriptors. Keys are
 * descriptor pointers; two descriptors of one type merely give two equal tables. */

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

/* True if a field stored at type `stored` must be converted to be read at type `viewed`: it is stored at a proper
 * subtype, or in a different layout (one of them stores a type parameter generically) */
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
            /* A var field is updated through the view, so it must be stored as the view stores it */
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

QVal quest_slot_read(const QTypeDescriptor *t, const void *slot) {
    if (t == NULL || slot == NULL) return (QVal){ .p = NULL };
    if (t->kind == QTYPE_KIND_STORED) {
        const QStoredDescriptor *st = (const QStoredDescriptor *)t->extra;
        if (st->storage == NULL) return *(const QVal *)slot;
        t = st->storage;
    }
    switch (t->kind) {
        case QTYPE_KIND_INT:
        case QTYPE_KIND_BOOL:
        case QTYPE_KIND_CHAR:
            return (QVal){ .i = *(const int64_t *)slot };
        case QTYPE_KIND_REAL:
            return (QVal){ .r = *(const double *)slot };
        case QTYPE_KIND_RECORD:
            return (QVal){ .p = (void *)quest_record_box(*(const QRecordVal *)slot) };
        case QTYPE_KIND_VARIANT:
            return (QVal){ .p = (void *)quest_variant_box(*(const QVariantVal *)slot) };
        default:
            return (QVal){ .p = *(void * const *)slot };
    }
}

void quest_slot_write(const QTypeDescriptor *t, void *slot, QVal v) {
    if (t == NULL || slot == NULL) return;
    if (t->kind == QTYPE_KIND_STORED) {
        const QStoredDescriptor *st = (const QStoredDescriptor *)t->extra;
        if (st->storage == NULL) {
            *(QVal *)slot = v;
            return;
        }
        t = st->storage;
    }
    switch (t->kind) {
        case QTYPE_KIND_INT:
        case QTYPE_KIND_BOOL:
        case QTYPE_KIND_CHAR:
            *(int64_t *)slot = v.i;
            break;
        case QTYPE_KIND_REAL:
            *(double *)slot = v.r;
            break;
        case QTYPE_KIND_RECORD:
            *(QRecordVal *)slot = *(const QRecordVal *)v.p;
            break;
        case QTYPE_KIND_VARIANT:
            *(QVariantVal *)slot = *(const QVariantVal *)v.p;
            break;
        default:
            *(void **)slot = v.p;
            break;
    }
}

/* Copies the elements of a tuple-shaped block (a tuple, or an option case's payload) from `from` to `to` layout */
static void quest_convert_elements(const void *src, const QTypeDescriptor *from, void *dst, const QTypeDescriptor *to) {
    const QTupleTypeDescriptor *f_meta = (const QTupleTypeDescriptor *)from->extra;
    const QTupleTypeDescriptor *t_meta = (const QTupleTypeDescriptor *)to->extra;
    if (f_meta == NULL || t_meta == NULL) return;
    for (size_t i = 0; i < t_meta->element_count && i < f_meta->element_count; ++i) {
        const QTupleElementDescriptor *fe = &f_meta->elements[i];
        const QTupleElementDescriptor *te = &t_meta->elements[i];
        QVal v = quest_slot_read(fe->type, (const char *)src + fe->offset);
        quest_slot_write(te->type, (char *)dst + te->offset, quest_convert(v, fe->type, te->type));
    }
}

/* Option values point to { int64_t tag; union of case payloads } with each payload laid out as its tuple type */
typedef struct QOptionLayout {
    int64_t tag;
    union {
        QRecordVal r;
        QVal       v;
    } u;
} QOptionLayout;

static QVal quest_convert_option(QVal v, const QTypeDescriptor *from, const QTypeDescriptor *to) {
    const QVariantTypeDescriptor *f_meta = (const QVariantTypeDescriptor *)from->extra;
    const QVariantTypeDescriptor *t_meta = (const QVariantTypeDescriptor *)to->extra;
    const char *src = (const char *)v.p;
    if (src == NULL || f_meta == NULL || t_meta == NULL) return v;
    int64_t tag = *(const int64_t *)src;
    if (tag < 0 || (size_t)tag >= f_meta->case_count) return v;
    const QVariantCaseDescriptor *fc = &f_meta->cases[tag];
    const QVariantCaseDescriptor *tc = NULL;
    for (size_t j = 0; j < t_meta->case_count; ++j) {
        if (strcmp(t_meta->cases[j].name, fc->name) == 0) {
            tc = &t_meta->cases[j];
            break;
        }
    }
    if (tc == NULL) quest_raise_dynamic_error();
    char *dst = (char *)quest_alloc(to->size > 0 ? to->size : sizeof(QOptionLayout));
    *(int64_t *)dst = tc->tag_index;
    size_t payload_offset = offsetof(QOptionLayout, u);
    if (fc->payload_type != NULL && tc->payload_type != NULL) {
        if (fc->payload_type->kind == QTYPE_KIND_TUPLE && tc->payload_type->kind == QTYPE_KIND_TUPLE) {
            quest_convert_elements(src + payload_offset, fc->payload_type, dst + payload_offset, tc->payload_type);
        } else {
            QVal p = quest_slot_read(fc->payload_type, src + payload_offset);
            quest_slot_write(tc->payload_type, dst + payload_offset, quest_convert(p, fc->payload_type, tc->payload_type));
        }
    }
    return (QVal){ .p = dst };
}

/* True if a tuple-shaped descriptor has var components */
static bool quest_tuple_has_var(const QTypeDescriptor *d) {
    const QTupleTypeDescriptor *meta = (const QTupleTypeDescriptor *)d->extra;
    for (size_t i = 0; meta != NULL && i < meta->element_count; ++i) {
        if (meta->elements[i].is_var) return true;
    }
    return false;
}

/* Reads and writes an auto value's component in its payload (see QAutoComponentDescriptor) */
static QVal quest_auto_component_read(const QAutoComponentDescriptor *c, const char *payload) {
    const void *slot = payload + c->offset;
    return c->storage != NULL ? quest_slot_read(c->storage, slot) : *(const QVal *)slot;
}

static void quest_auto_component_write(const QAutoComponentDescriptor *c, char *payload, QVal v) {
    void *slot = payload + c->offset;
    if (c->storage != NULL) quest_slot_write(c->storage, slot, v);
    else *(QVal *)slot = v;
}

/* Re-stores an auto value's components in the layout of auto type `to` (keeping its type component) */
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
        /* A component of the type component's type is a value of that type whatever its storage */
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
    exit(1);
}

/* How a value stored as a type parameter is held: in its QVal form, as a value of its own type, or in the
 * representation of the parameter's bound, viewed at the bound (generic code views such values at the bound) */
static const QTypeDescriptor *quest_stored_representation(const QTypeDescriptor *d) {
    if (d == NULL || d->kind != QTYPE_KIND_STORED) return d;
    const QStoredDescriptor *st = (const QStoredDescriptor *)d->extra;
    return st->storage != NULL ? st->storage : st->type;
}

QVal quest_convert(QVal v, const QTypeDescriptor *from, const QTypeDescriptor *to) {
    if (from == NULL || to == NULL) return v;
    from = quest_stored_representation(from);
    to = quest_stored_representation(to);
    /* A record is viewed at `to` from its own layout, whatever view it had: code that knows a value only as of a
     * type parameter's bound may view it at the bound or at its own type */
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
            if (quest_layout_equivalent(from, to)) return v;
            return quest_convert_option(v, from, to);
        case QTYPE_KIND_TUPLE: {
            if (v.p == NULL || to->extra == NULL || quest_layout_equivalent(from, to)) return v;
            if (quest_tuple_has_var(to)) quest_layout_conversion_error(from, to);
            void *dst = quest_alloc(to->size > 0 ? to->size : sizeof(void *));
            quest_convert_elements(v.p, from, dst, to);
            return (QVal){ .p = dst };
        }
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

/* Descriptors of the same type describe the same layout unless one stores a type parameter generically (as a QVal,
 * QTYPE_KIND_STORED) where the other stores the type argument's own representation. The two agree in memory for
 * scalars and pointers, but not for records and variants (16 bytes inline, or a pointer to a boxed copy); in
 * registers (function parameters and results) only integers and pointers agree. Recursive descriptors are compared
 * coinductively. */

#define Q_EQUIV_TRAIL_MAX 64
static Q_THREAD_LOCAL QSubtypePair quest_equiv_trail[Q_EQUIV_TRAIL_MAX];
static Q_THREAD_LOCAL size_t quest_equiv_trail_len = 0;

static bool quest_layout_equiv_rec(const QTypeDescriptor *a, const QTypeDescriptor *b);

/* Whether a slot or a parameter holding a value stored generically (`st`) holds it as `other` does. Stored as the
 * type parameter's bound, a value has the bound's representation and is viewed at the bound. */
static bool quest_stored_equivalent(const QStoredDescriptor *st, const QTypeDescriptor *other, bool in_register) {
    if (st->storage != NULL) return quest_layout_equiv_rec(st->storage, other);
    switch (other->kind) {
        case QTYPE_KIND_RECORD:
        case QTYPE_KIND_VARIANT:
            return false;
        case QTYPE_KIND_REAL:
        case QTYPE_KIND_BOOL:
        case QTYPE_KIND_CHAR:
        case QTYPE_KIND_OK:
            return !in_register;
        case QTYPE_KIND_INT:
        case QTYPE_KIND_STRING:
        case QTYPE_KIND_OPAQUE:
        case QTYPE_KIND_BOUND_VAR:
            return true;
        default:
            return quest_layout_equiv_rec(st->type, other);
    }
}

static bool quest_place_equivalent(const QTypeDescriptor *a, const QTypeDescriptor *b, bool in_register) {
    if (a == b) return true;
    if (a == NULL || b == NULL) return false;
    bool a_stored = a->kind == QTYPE_KIND_STORED, b_stored = b->kind == QTYPE_KIND_STORED;
    if (a_stored && b_stored) {
        const QStoredDescriptor *sa = (const QStoredDescriptor *)a->extra;
        const QStoredDescriptor *sb = (const QStoredDescriptor *)b->extra;
        if ((sa->storage == NULL) != (sb->storage == NULL)) return false;
        return sa->storage != NULL ? quest_layout_equiv_rec(sa->storage, sb->storage)
                                   : quest_layout_equiv_rec(sa->type, sb->type);
    }
    if (a_stored) return quest_stored_equivalent((const QStoredDescriptor *)a->extra, b, in_register);
    if (b_stored) return quest_stored_equivalent((const QStoredDescriptor *)b->extra, a, in_register);
    return quest_layout_equiv_rec(a, b);
}

bool quest_slot_layout_equivalent(const QTypeDescriptor *a, const QTypeDescriptor *b) {
    return quest_place_equivalent(a, b, false);
}

static bool quest_layout_equiv_rec(const QTypeDescriptor *a, const QTypeDescriptor *b) {
    if (a == b) return true;
    if (a == NULL || b == NULL) return false;
    if (a->kind == QTYPE_KIND_STORED || b->kind == QTYPE_KIND_STORED) return quest_place_equivalent(a, b, false);
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
                         quest_place_equivalent(sa->elements[i].type, sb->elements[i].type, false);
            }
            break;
        }
        case QTYPE_KIND_RECORD: {
            /* Record values carry their payload's layout; their offset tables depend on the view's field types */
            const QRecordTypeDescriptor *ra = (const QRecordTypeDescriptor *)a->extra;
            const QRecordTypeDescriptor *rb = (const QRecordTypeDescriptor *)b->extra;
            size_t na = ra != NULL ? ra->field_count : 0, nb = rb != NULL ? rb->field_count : 0;
            result = na == nb;
            for (size_t i = 0; result && i < nb; ++i) {
                result = strcmp(ra->fields[i].name, rb->fields[i].name) == 0 &&
                         ra->fields[i].is_var == rb->fields[i].is_var &&
                         quest_place_equivalent(ra->fields[i].type, rb->fields[i].type, false);
            }
            break;
        }
        case QTYPE_KIND_VARIANT:
        case QTYPE_KIND_OPTION: {
            const QVariantTypeDescriptor *va = (const QVariantTypeDescriptor *)a->extra;
            const QVariantTypeDescriptor *vb = (const QVariantTypeDescriptor *)b->extra;
            size_t na = va != NULL ? va->case_count : 0, nb = vb != NULL ? vb->case_count : 0;
            result = na == nb;
            for (size_t i = 0; result && i < nb; ++i) {
                const QVariantCaseDescriptor *ca = &va->cases[i], *cb = &vb->cases[i];
                result = strcmp(ca->name, cb->name) == 0 && ca->tag_index == cb->tag_index &&
                         (ca->payload_type == NULL) == (cb->payload_type == NULL) &&
                         (ca->payload_type == NULL || quest_place_equivalent(ca->payload_type, cb->payload_type, false));
            }
            break;
        }
        case QTYPE_KIND_ARRAY: {
            const QArrayTypeDescriptor *ea = (const QArrayTypeDescriptor *)a->extra;
            const QArrayTypeDescriptor *eb = (const QArrayTypeDescriptor *)b->extra;
            result = ea != NULL && eb != NULL && quest_place_equivalent(ea->element_type, eb->element_type, false);
            break;
        }
        case QTYPE_KIND_FUN: {
            const QFunTypeDescriptor *fa = (const QFunTypeDescriptor *)a->extra;
            const QFunTypeDescriptor *fb = (const QFunTypeDescriptor *)b->extra;
            result = fa != NULL && fb != NULL && fa->param_count == fb->param_count &&
                     fa->quantifier_count == fb->quantifier_count;
            for (size_t i = 0; result && i < fb->param_count; ++i) {
                const QFunParamDescriptor *pa = &fa->params[i], *pb = &fb->params[i];
                /* var and out parameters are pointers to slots */
                result = pa->is_var == pb->is_var && pa->is_out == pb->is_out &&
                         quest_place_equivalent(pa->type, pb->type, !(pa->is_var || pa->is_out));
            }
            if (result) result = quest_place_equivalent(fa->result_type, fb->result_type, true);
            break;
        }
        case QTYPE_KIND_AUTO: {
            const QAutoTypeDescriptor *aa = (const QAutoTypeDescriptor *)a->extra;
            const QAutoTypeDescriptor *ab = (const QAutoTypeDescriptor *)b->extra;
            result = aa != NULL && ab != NULL && aa->component_count >= ab->component_count;
            for (size_t i = 0; result && i < ab->component_count; ++i) {
                const QAutoComponentDescriptor *ca = &aa->components[i], *cb = &ab->components[i];
                result = ca->offset == cb->offset && (ca->storage == NULL) == (cb->storage == NULL) &&
                         (ca->storage == NULL || quest_layout_equiv_rec(ca->storage, cb->storage)) &&
                         quest_place_equivalent(ca->type, cb->type, false);
            }
            break;
        }
        case QTYPE_KIND_EXCEPTION: {
            const QExceptionTypeDescriptor *xa = (const QExceptionTypeDescriptor *)a->extra;
            const QExceptionTypeDescriptor *xb = (const QExceptionTypeDescriptor *)b->extra;
            result = xa != NULL && xb != NULL && quest_place_equivalent(xa->payload_type, xb->payload_type, false);
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
    return quest_place_equivalent(a, b, false);
}

/* How a parameter or result of type d is passed: integers and pointers alike, other scalars, records, and variants
 * each their own way (Ok parameters are passed as QVals, and Ok results not at all) */
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

/* The nodes of a template reachable from its root, each with its instance (NULL until made) and whether it reaches
 * a hole (nodes that do not are their own instances) */
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
                f(cx, m->components[i].storage);
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
} QInstContext;

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

/* Fills the instance of template node n, whose descriptor was allocated already */
static void quest_inst_fill(const QInstContext *cx, QInstNode *n) {
    const QTypeDescriptor *d = n->tmpl;
    QTypeDescriptor *out = n->inst;
    *out = *d;
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
                comp->storage = quest_inst_of(cx, m->components[i].storage);
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
            out->extra = c;
            break;
        }
        case QTYPE_KIND_HOLE: {
            const QHoleDescriptor *h = (const QHoleDescriptor *)d->extra;
            QStoredDescriptor *c = (QStoredDescriptor *)quest_alloc(sizeof(QStoredDescriptor));
            c->type = cx->args[h->index];
            c->storage = quest_inst_of(cx, h->storage);
            out->kind = QTYPE_KIND_STORED;
            out->name = c->type != NULL ? c->type->name : d->name;
            out->size = c->storage != NULL ? c->storage->size : sizeof(QVal);
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
    /* Which nodes reach a hole: iterate to a fixed point, since templates may be cyclic */
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
    QInstContext cx = { &w, args };
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
    if (stored != NULL && stored[i] != NULL) return quest_convert(quest_slot_read(stored[i], slot), stored[i], field_type);
    return quest_slot_read(field_type, slot);
}

/* Writes a string literal, escaped as the interpreter does */
static void quest_put_string(const QString *s) {
    putchar('"');
    for (int64_t i = 0; s != NULL && i < s->length; ++i) quest_put_escaped_char((unsigned char)s->data[i], '"');
    putchar('"');
}

/* The tuples, records, and arrays being written, so that a cyclic value is cut off as the interpreter does */
#define Q_PRINT_NESTING_MAX 256
static const void *quest_print_nesting[Q_PRINT_NESTING_MAX];
static int quest_print_depth = 0;

/* Starts writing the aggregate at p, or returns false (writing opening and " ... end") if p is already being
 * written; a true result is matched by a call of quest_print_leave */
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

/* Writes the elements of a tuple-shaped block (a tuple, or an option case's payload) laid out as t */
static void quest_put_elements(const char *base, const QTypeDescriptor *t, const QTypeDescriptor *witness) {
    const QTupleTypeDescriptor *meta = (const QTupleTypeDescriptor *)t->extra;
    for (size_t i = 0; meta != NULL && i < meta->element_count; ++i) {
        const QTupleElementDescriptor *e = &meta->elements[i];
        putchar(' ');
        if (e->name != NULL && e->name[0] != '\0') printf("%s=", e->name);
        quest_put_value(quest_slot_read(e->type, base + e->offset), e->type, witness);
    }
}

/* Writes a tuple-shaped block as `tuple ... end` */
static void quest_put_tuple(const char *base, const QTypeDescriptor *t, const QTypeDescriptor *witness) {
    if (!quest_print_enter(base, "tuple")) return;
    quest_put_elements(base, t, witness);
    fputs(" end", stdout);
    quest_print_leave();
}

/* Writes a value of the type t as the interpreter does (format_value_with_type). witness is the type component of
 * the auto value whose components are being written, which a component's type refers to as its type parameter. */
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
            quest_put_tuple((const char *)v.p, t, witness);
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
            /* A variant is a QVariantVal; an option points to its tag followed by its payload, laid out as the
             * payload's tuple type (see QOptionLayout) */
            int64_t tag = t->kind == QTYPE_KIND_VARIANT ? ((const QVariantVal *)v.p)->tag : *(const int64_t *)v.p;
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
                    const char *payload = (const char *)v.p + offsetof(QOptionLayout, u);
                    if (payload_type->kind == QTYPE_KIND_TUPLE) {
                        quest_put_tuple(payload, payload_type, witness);
                    } else {
                        quest_put_value(quest_slot_read(payload_type, payload), payload_type, witness);
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
            /* Records and variants are stored in wide arrays, any other element as its QVal form */
            int64_t length = ((const QArray *)v.p)->length;
            for (int64_t i = 0; i < length; ++i) {
                QVal e;
                if (elem != NULL && elem->kind == QTYPE_KIND_RECORD) {
                    e = (QVal){ .p = &((QArrayWideRecord *)v.p)->data[i] };
                } else if (elem != NULL && elem->kind == QTYPE_KIND_VARIANT) {
                    e = (QVal){ .p = &((QArrayWideVariant *)v.p)->data[i] };
                } else {
                    e = ((const QArray *)v.p)->data[i];
                }
                putchar(' ');
                quest_put_value(e, elem, witness);
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
                /* Records and variants are stored inline, any other component as its QVal form */
                QVal cv = c->storage != NULL ? quest_slot_read(c->storage, payload + c->offset)
                                              : *(const QVal *)(payload + c->offset);
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
            /* An auto value's components refer to its type component as the innermost type parameter */
            if (witness != NULL && t == &quest_type_bound_vars[0]) {
                quest_put_value(v, witness, NULL);
            } else {
                fputs("<hidden>", stdout);
            }
            return;
        case QTYPE_KIND_OPAQUE:
            /* Word.T is a library type with literals of its own; any other abstract type's values are hidden */
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

#include <unistd.h>
#include <sys/stat.h>
#include <dirent.h>
#include <errno.h>

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
    char buf[64];
    /* Quest writes negation as ~, including for negative zero and negative infinity. */
    bool is_neg = signbit(r);
    double abs_r = is_neg ? -r : r;
    if (isinf(abs_r)) {
        snprintf(buf, sizeof(buf), "%sinf", is_neg ? "~" : "");
    } else if (abs_r < 9223372036854775808.0 && abs_r == (double)(int64_t)abs_r) {
        snprintf(buf, sizeof(buf), "%s%.1f", is_neg ? "~" : "", abs_r);
    } else {
        snprintf(buf, sizeof(buf), "%s%g", is_neg ? "~" : "", abs_r);
    }
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

/* An integral real as an Int; an infinity or a value outside Int's range raises real.error. */
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
    if (t != NULL && t->kind == QTYPE_KIND_REAL && x.r == 0.0) {
        x.u = 0;
    }
    return quest_hash_mix64(x.u);
}

/* Builtins initialization */
void quest_builtins_init(int argc, char **argv) {
    quest_writer_init_std();
    quest_reader_init_std();
    quest_system_init(argc, argv);
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
