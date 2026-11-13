/*
 * Quest C Runtime: Internal Declarations
 *
 * What the files of the runtime proper (quest_runtime.c, quest_exceptions.c,
 * quest_print.c, quest_types.c, quest_views.c, quest_os.c, and quest_stdlib.c)
 * share with each other but not with compiled code, which sees only
 * quest_runtime.h. Each file keeps the rest of its helpers static.
 */

#ifndef QUEST_RUNTIME_INTERNAL_H
#define QUEST_RUNTIME_INTERNAL_H

#include "quest_runtime.h"

/* Two descriptors being compared, in a proof about a recursive type that is
 * under way: the trail of quest_is_subtype (quest_types.c), and those of
 * proxies and layout equivalence (quest_views.c) */
typedef struct QSubtypePair {
    const QTypeDescriptor *sub;
    const QTypeDescriptor *super_type;
} QSubtypePair;

/* quest_exceptions.c: ends the program after an error's message has been
 * printed, printing the site loc it was raised at, if known, and the frames
 * running; and installs the guard that reports running out of stack (a no-op
 * where there is none) */
Q_NORETURN void quest_fail_at(const char *loc);
void quest_install_stack_guard(void);

/* quest_print.c: formats r without its sign, as the interpreter does; and
 * appends a character of a char or string literal, escaped */
void quest_format_real(double r, char *out, size_t n);
void quest_sb_append_escaped(QStringBuilder *b, unsigned char c, char quote);

/* quest_views.c: an option's identity hash at its type t */
uint64_t quest_option_identity_hash(const QTypeDescriptor *t, const void *p);

/* quest_stdlib.c: set up standard output, standard error, and standard input,
 * which quest_builtins_init does before anything else */
void quest_writer_init_std(void);
void quest_reader_init_std(void);

/* The statics and thread-locals of each file that hold heap pointers, which
 * quest_runtime_roots reports to the collector */
void quest_exceptions_roots(QRootVisitor add);
void quest_print_roots(QRootVisitor add);
void quest_types_roots(QRootVisitor add);
void quest_views_roots(QRootVisitor add);
void quest_os_roots(QRootVisitor add);

#endif
