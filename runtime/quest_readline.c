/*
 * quest_readline.c
 * The io/readline library's externals: line editing and history through the
 * readline API.
 *
 * The build compiles this file with the line editor it finds
 * (docs/self-hosted-repl.md §1.1): GNU readline (QUEST_GNU_READLINE), libedit's
 * readline-compatible API (neither flag), or none (QUEST_NOREADLINE), when
 * readLine reads plain lines. The history is the runtime's own, mirrored into
 * the line editor's, and its file is plain lines.
 *
 * readLine edits through readline's callback interface, waiting for input with
 * select, as CPython's readline module does: a SIGINT, while it waits, sets a
 * flag that ends the wait, and the line is abandoned and readline's state
 * cleaned up, with no longjmp out of the library. Without editing, readLine
 * reads through reader.input's buffer.
 */

#define _POSIX_C_SOURCE 200809L

#include "quest_runtime.h"
#include <errno.h>
#include <signal.h>
#include <unistd.h>
#include <sys/select.h>

#ifndef QUEST_NOREADLINE
#include <readline/readline.h>
#include <readline/history.h>
#endif

const QException quest_exc_readline_error          = { "readline.error" };
const QException quest_exc_readline_end_of_input   = { "readline.endOfInput" };
const QException quest_exc_readline_interrupted    = { "readline.interrupted" };

bool quest_readline_editing(void) {
#ifdef QUEST_NOREADLINE
    return false;
#else
    if (!isatty(STDIN_FILENO) || !isatty(STDOUT_FILENO)) {
        return false;
    }
    const char *term = getenv("TERM");
    return term != NULL && *term != '\0' && strcmp(term, "dumb") != 0 && strcmp(term, "emacs") != 0;
#endif
}

/* A line of reader.input, without its newline; end of input before any byte is
 * readline.endOfInput */
static QString *quest_readline_plain(const QString *prompt) {
    quest_writer_put_string(quest_writer_output, prompt);
    quest_writer_flush(quest_writer_output);
    QStringBuilder *b = quest_sb_new();
    bool any = false;
    while (quest_reader_more(quest_reader_input)) {
        QChar c = quest_reader_get_char(quest_reader_input);
        any = true;
        if (c == '\n') {
            break;
        }
        quest_sb_append_char(b, c);
    }
    if (!any) {
        quest_raise(&quest_exc_readline_end_of_input, Q_OK_VAL);
    }
    return quest_sb_to_string(b);
}

#ifndef QUEST_NOREADLINE

static volatile sig_atomic_t quest_readline_sigint;
static bool quest_readline_done;
static char *quest_readline_line;

static void quest_readline_on_line(char *line) {
    quest_readline_line = line;
    quest_readline_done = true;
    rl_callback_handler_remove();
}

static void quest_readline_on_sigint(int sig) {
    (void)sig;
    quest_readline_sigint = 1;
}

/* An edited line, or NULL at the end of input; *interrupted is set if Ctrl-C
 * abandoned it */
static char *quest_readline_edit(const char *prompt, bool *interrupted) {
    struct sigaction action, previous;
    memset(&action, 0, sizeof action);
    action.sa_handler = quest_readline_on_sigint;
    sigemptyset(&action.sa_mask);
    /* No SA_RESTART, so that the signal ends the select */
    sigaction(SIGINT, &action, &previous);
    quest_readline_sigint = 0;
    quest_readline_done = false;
    quest_readline_line = NULL;
    *interrupted = false;
    rl_callback_handler_install(prompt, quest_readline_on_line);
    while (!quest_readline_done) {
        /* Before waiting too, for a signal that came while readline handled a
         * key */
        if (quest_readline_sigint) {
            rl_free_line_state();
#ifdef QUEST_GNU_READLINE
            rl_callback_sigcleanup();
#endif
            rl_cleanup_after_signal();
            rl_callback_handler_remove();
            *interrupted = true;
            break;
        }
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(STDIN_FILENO, &fds);
        int ready = select(STDIN_FILENO + 1, &fds, NULL, NULL, NULL);
        if (ready < 0) {
            if (errno == EINTR) {
                continue;
            }
            rl_callback_handler_remove();
            sigaction(SIGINT, &previous, NULL);
            quest_raise(&quest_exc_readline_error, Q_OK_VAL);
        }
        rl_callback_read_char();
    }
    sigaction(SIGINT, &previous, NULL);
    return quest_readline_line;
}

#endif

QString *quest_readline_read_line(const QString *prompt) {
    if (prompt == NULL) {
        quest_raise(&quest_exc_readline_error, Q_OK_VAL);
    }
#ifndef QUEST_NOREADLINE
    if (quest_readline_editing()) {
        /* Output written before the prompt appears before it */
        quest_writer_flush(quest_writer_output);
        bool interrupted;
        char *line = quest_readline_edit(prompt->data, &interrupted);
        if (interrupted) {
            quest_raise(&quest_exc_readline_interrupted, Q_OK_VAL);
        }
        if (line == NULL) {
            quest_raise(&quest_exc_readline_end_of_input, Q_OK_VAL);
        }
        QString *result = quest_string_new(line, (int64_t)strlen(line));
        free(line);
        return result;
    }
#endif
    return quest_readline_plain(prompt);
}

/* The history, which the runtime keeps itself, so that its file is plain lines
 * whatever the line editor (whose own files differ: libedit's escapes its
 * lines), and the line editor's history mirrors */
static char **quest_readline_history;
static int64_t quest_readline_history_length;
static int64_t quest_readline_history_capacity;

static void quest_readline_remember(const char *line, size_t length) {
    if (quest_readline_history_length == quest_readline_history_capacity) {
        int64_t capacity = quest_readline_history_capacity == 0 ? 64 : quest_readline_history_capacity * 2;
        char **grown = (char **)realloc(quest_readline_history, (size_t)capacity * sizeof(char *));
        if (grown == NULL) {
            quest_raise(&quest_exc_readline_error, Q_OK_VAL);
        }
        quest_readline_history = grown;
        quest_readline_history_capacity = capacity;
    }
    char *copy = (char *)malloc(length + 1);
    if (copy == NULL) {
        quest_raise(&quest_exc_readline_error, Q_OK_VAL);
    }
    memcpy(copy, line, length);
    copy[length] = '\0';
    quest_readline_history[quest_readline_history_length++] = copy;
#ifndef QUEST_NOREADLINE
    add_history(copy);
#endif
}

void quest_readline_add_history(const QString *line) {
    if (line == NULL) {
        quest_raise(&quest_exc_readline_error, Q_OK_VAL);
    }
    quest_readline_remember(line->data, (size_t)line->length);
}

void quest_readline_read_history(const QString *path) {
    if (path == NULL) {
        quest_raise(&quest_exc_readline_error, Q_OK_VAL);
    }
    FILE *f = fopen(path->data, "rb");
    if (f == NULL) {
        if (errno == ENOENT) {
            return;
        }
        quest_raise(&quest_exc_readline_error, Q_OK_VAL);
    }
    QStringBuilder *b = quest_sb_new();
    int c;
    while ((c = fgetc(f)) != EOF) {
        if (c == '\n') {
            QString *line = quest_sb_to_string(b);
            quest_readline_remember(line->data, (size_t)line->length);
            quest_sb_clear(b);
        } else {
            quest_sb_append_char(b, (QChar)c);
        }
    }
    bool failed = ferror(f) != 0;
    fclose(f);
    if (failed) {
        quest_raise(&quest_exc_readline_error, Q_OK_VAL);
    }
    QString *last = quest_sb_to_string(b);
    if (last->length > 0) {
        quest_readline_remember(last->data, (size_t)last->length);
    }
}

void quest_readline_write_history(const QString *path, int64_t max_lines) {
    if (path == NULL || max_lines < 0) {
        quest_raise(&quest_exc_readline_error, Q_OK_VAL);
    }
    FILE *f = fopen(path->data, "wb");
    if (f == NULL) {
        quest_raise(&quest_exc_readline_error, Q_OK_VAL);
    }
    int64_t first = quest_readline_history_length > max_lines ? quest_readline_history_length - max_lines : 0;
    bool failed = false;
    for (int64_t i = first; i < quest_readline_history_length && !failed; i++) {
        failed = fputs(quest_readline_history[i], f) == EOF || fputc('\n', f) == EOF;
    }
    if (fclose(f) != 0 || failed) {
        quest_raise(&quest_exc_readline_error, Q_OK_VAL);
    }
}
