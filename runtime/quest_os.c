/*
 * Quest C Runtime: The System
 *
 * The primitives of the standard library's system, os, and process modules:
 * the program's arguments, environment variables, files and directories and
 * their stats, and running other programs, waiting for them or not; and the
 * Jupyter kernel's interrupts, a SIGINT the code the JIT compiles raises as
 * an exception.
 */

/* The POSIX functions -std=c99 hides on Linux (glibc) */
#if defined(__linux__) && !defined(_GNU_SOURCE)
#define _GNU_SOURCE
#endif

#include "quest_runtime_internal.h"

#include <limits.h>
#include <unistd.h>
#include <sys/stat.h>
#include <dirent.h>
#include <errno.h>
#include <poll.h>
#include <spawn.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <signal.h>

/* System module primitives */
QArray *quest_system_args = NULL;

void quest_system_init(int argc, char **argv) {
    if (argc < 0) argc = 0;
    /* No collection between the strings and the array: the strings are held
     * outside the heap meanwhile, and the array's stores have no barrier */
    quest_gc_hold();
    QString **strings = (QString **)malloc((size_t)(argc > 0 ? argc : 1) * sizeof(QString *));
    if (strings == NULL) quest_raise_system_error();
    for (int i = 0; i < argc; i++) {
        const char *arg = (argv != NULL && argv[i] != NULL) ? argv[i] : "";
        strings[i] = quest_string_new(arg, (int64_t)strlen(arg));
    }
    quest_system_args = quest_array_new(argc, (QVal){ .p = NULL }, &quest_layout_array_pointer);
    for (int i = 0; i < argc; i++) quest_system_args->data[i].p = strings[i];
    free(strings);
    quest_gc_release();
}

/* Interrupts in a Jupyter kernel's driver (docs/jupyter-kernel.md section 5):
 * the driver, given --kernel, installs a SIGINT handler that sets a flag, and
 * the code the JIT compiles for a cell checks it at function entries and loop
 * headers (ssa/passes/interrupts), raising `interrupted`. None of these is in
 * quest_runtime.h: only the driver, through os/code's symbol, and the code the
 * JIT links use them, so that a binary that never asks for interrupts is as
 * before. The flag is a word, which the driver reads and clears through
 * os/value, and which an aligned store from the handler writes at once on the
 * machines the runtime runs on (arm64, x86-64). */
extern volatile int64_t quest_interrupt_pending;
extern const QException quest_exc_interrupted;
void quest_interrupt_install(void);
Q_NORETURN void quest_interrupt_raise(void);

volatile int64_t quest_interrupt_pending;
const QException quest_exc_interrupted = { "interrupted" };

static void quest_interrupt_on_sigint(int sig) {
    (void)sig;
    quest_interrupt_pending = 1;
}

void quest_interrupt_install(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = quest_interrupt_on_sigint;
    sa.sa_flags = SA_RESTART;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGINT, &sa, NULL);
}

void quest_interrupt_raise(void) {
    quest_interrupt_pending = 0;
    quest_raise(&quest_exc_interrupted, Q_OK_VAL);
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
    /* No collection until the array is filled: the names are held outside
     * the heap meanwhile, and the array's stores have no barrier */
    quest_gc_hold();

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

    QArray *res = quest_array_new((int64_t)count, (QVal){ .p = NULL }, &quest_layout_array_pointer);
    for (size_t i = 0; i < count; i++) {
        res->data[i].p = entries[i];
    }
    free(entries);
    quest_gc_release();
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
    QString *out_s = quest_string_new(out.data != NULL ? out.data : "", (int64_t)out.len);
    QString *err_s = quest_string_new(err.data != NULL ? err.data : "", (int64_t)err.len);
    QVal *result = (QVal *)quest_alloc(3 * sizeof(QVal), &quest_layout_run_result);
    result[0].i = WIFEXITED(status) ? WEXITSTATUS(status) : WIFSIGNALED(status) ? -WTERMSIG(status) : -1;
    result[1].p = out_s;
    result[2].p = err_s;
    free(out.data);
    free(err.data);
    return result;
}

/* os/fileStats (see quest_runtime.h) */
void *quest_filestats_stat(const QString *path, bool follow) {
    if (path == NULL || path->data == NULL) quest_raise_system_error();
    struct stat st;
    QVal *result = (QVal *)quest_alloc(9 * sizeof(QVal), &quest_layout_file_stats);
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

/* os/process (see quest_runtime.h). A child's standard output and error go to
 * unlinked temp files rather than pipes, so that nothing has to drain them while
 * it runs. The live list holds every child not yet reaped, so that waitAny can
 * reap with waitpid(-1) and record the status on whichever handle it belongs
 * to; being static, it also keeps those handles alive for the collector. */
struct QProcess {
    pid_t pid;
    bool done;
    int status;
    int out_fd, err_fd;
    void *result;
    struct QProcess *next_live;
};

static QProcess *quest_process_live = NULL;



static int quest_process_temp_file(void) {
    const char *dir = getenv("TMPDIR");
    if (dir == NULL || dir[0] == '\0') dir = "/tmp";
    size_t n = strlen(dir) + sizeof("/quest-process-XXXXXX");
    char *name = (char *)malloc(n);
    if (name == NULL) return -1;
    snprintf(name, n, "%s/quest-process-XXXXXX", dir);
    int fd = mkstemp(name);
    if (fd >= 0) unlink(name);
    free(name);
    if (fd >= 0) fcntl(fd, F_SETFD, FD_CLOEXEC);
    return fd;
}

static void quest_process_reaped(QProcess *p, int status) {
    p->done = true;
    p->status = status;
    for (QProcess **link = &quest_process_live; *link != NULL; link = &(*link)->next_live) {
        if (*link == p) {
            quest_barrier_slot(link);
            *link = p->next_live;
            break;
        }
    }
    p->next_live = NULL;
}

static QProcess *quest_process_spawn_with(const QArray *args, const QString *dir) {
    if (args == NULL || args->length == 0) quest_raise_system_error();
    if (dir != NULL && dir->data == NULL) quest_raise_system_error();
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

    int out_fd = quest_process_temp_file();
    int err_fd = out_fd >= 0 ? quest_process_temp_file() : -1;
    if (err_fd < 0) {
        if (out_fd >= 0) close(out_fd);
        free(argv);
        quest_raise_system_error();
    }
    posix_spawn_file_actions_t actions;
    posix_spawn_file_actions_init(&actions);
    posix_spawn_file_actions_adddup2(&actions, out_fd, STDOUT_FILENO);
    posix_spawn_file_actions_adddup2(&actions, err_fd, STDERR_FILENO);
    if (dir != NULL) posix_spawn_file_actions_addchdir_np(&actions, dir->data);
    pid_t pid;
    int spawned = posix_spawnp(&pid, argv[0], &actions, NULL, argv, environ);
    posix_spawn_file_actions_destroy(&actions);
    free(argv);
    if (spawned != 0) {
        close(out_fd);
        close(err_fd);
        quest_raise_system_error();
    }

    QProcess *p = (QProcess *)quest_alloc(sizeof(QProcess), &quest_layout_process);
    p->pid = pid;
    p->done = false;
    p->status = 0;
    p->out_fd = out_fd;
    p->err_fd = err_fd;
    p->result = NULL;
    p->next_live = quest_process_live;
    quest_process_live = p;
    return p;
}

QProcess *quest_process_spawn(const QArray *args) {
    return quest_process_spawn_with(args, NULL);
}

QProcess *quest_process_spawn_in(const QArray *args, const QString *dir) {
    if (dir == NULL) quest_raise_system_error();
    return quest_process_spawn_with(args, dir);
}

int64_t quest_process_pid(const QProcess *p) {
    return (int64_t)p->pid;
}

bool quest_process_is_done(QProcess *p) {
    if (!p->done) {
        int status;
        pid_t r;
        do {
            r = waitpid(p->pid, &status, WNOHANG);
        } while (r < 0 && errno == EINTR);
        if (r < 0) quest_raise_system_error();
        if (r == p->pid) quest_process_reaped(p, status);
    }
    return p->done;
}

/* The whole of a temp file a child wrote */
static bool quest_process_read_back(int fd, QRunBuffer *b) {
    if (lseek(fd, 0, SEEK_SET) < 0) return false;
    char chunk[65536];
    for (;;) {
        ssize_t n = read(fd, chunk, sizeof(chunk));
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) return false;
        if (n == 0) return true;
        if (!quest_run_append(b, chunk, (size_t)n)) return false;
    }
}

void *quest_process_wait(QProcess *p) {
    if (p->result != NULL) return p->result;
    while (!p->done) {
        int status;
        pid_t r = waitpid(p->pid, &status, 0);
        if (r == p->pid) {
            quest_process_reaped(p, status);
        } else if (r < 0 && errno != EINTR) {
            quest_raise_system_error();
        }
    }
    QRunBuffer out = { NULL, 0, 0 }, err = { NULL, 0, 0 };
    bool read_back = quest_process_read_back(p->out_fd, &out) && quest_process_read_back(p->err_fd, &err);
    if (!read_back) {
        free(out.data);
        free(err.data);
        quest_raise_system_error();
    }
    close(p->out_fd);
    close(p->err_fd);
    p->out_fd = p->err_fd = -1;

    /* Laid out as Tuple code: Int stdout: String stderr: String end, as
     * system.run's result is */
    int status = p->status;
    QString *out_s = quest_string_new(out.data != NULL ? out.data : "", (int64_t)out.len);
    QString *err_s = quest_string_new(err.data != NULL ? err.data : "", (int64_t)err.len);
    QVal *result = (QVal *)quest_alloc(3 * sizeof(QVal), &quest_layout_run_result);
    result[0].i = WIFEXITED(status) ? WEXITSTATUS(status) : WIFSIGNALED(status) ? -WTERMSIG(status) : -1;
    result[1].p = out_s;
    result[2].p = err_s;
    free(out.data);
    free(err.data);
    quest_barrier(p);
    p->result = result;
    return result;
}

int64_t quest_process_wait_any(const QArray *ps) {
    if (ps == NULL || ps->length == 0) quest_raise_system_error();
    for (;;) {
        for (int64_t i = 0; i < ps->length; i++) {
            if (((QProcess *)ps->data[i].p)->done) return i;
        }
        int status;
        pid_t r = waitpid(-1, &status, 0);
        if (r < 0) {
            if (errno == EINTR) continue;
            quest_raise_system_error();
        }
        for (QProcess *p = quest_process_live; p != NULL; p = p->next_live) {
            if (p->pid == r) {
                quest_process_reaped(p, status);
                break;
            }
        }
    }
}

void quest_process_kill(QProcess *p, int64_t sig) {
    if (sig < 0 || sig > INT_MAX) quest_raise_system_error();
    /* A child that has exited but not been reaped is still there to signal */
    if (p->done) return;
    if (kill(p->pid, (int)sig) != 0 && errno != ESRCH) quest_raise_system_error();
}

bool quest_system_is_terminal(int64_t fd) {
    return fd >= 0 && fd <= INT_MAX && isatty((int)fd);
}

/* This file's global roots, for the collector and its roots check */
void quest_os_roots(QRootVisitor add) {
    add(&quest_system_args, 1);
    add(&quest_process_live, 1);
}
