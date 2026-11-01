/* A program counter sampler for macOS (docs/profiling.md section 4), loaded
 * into a program with DYLD_INSERT_LIBRARIES; tools/perf/profile.py builds and
 * runs it. On SIGPROF, every PCPROF_INTERVAL_US microseconds of the
 * process's CPU time (1000 by default), it records the interrupted program
 * counter. At exit it stops the timer and writes to PCPROF_OUT the main
 * executable's slide, then each sample's program counter, image, and symbol,
 * from dladdr, which knows a binary's local symbols unless it is stripped.
 *
 * Samples land on whichever thread the signal is delivered to, the
 * collector's marker threads included, waiting in the kernel. */

#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <sys/ucontext.h>

#define PCPROF_MAX (1 << 22)

static uintptr_t   pcprof_pcs[PCPROF_MAX];
static volatile int pcprof_n;

static void pcprof_sample(int sig, siginfo_t *info, void *context) {
    (void)sig;
    (void)info;
    ucontext_t *uc = (ucontext_t *)context;
    if (pcprof_n < PCPROF_MAX) pcprof_pcs[pcprof_n++] = (uintptr_t)uc->uc_mcontext->__ss.__pc;
}

static void pcprof_write(void) {
    struct itimerval off = { { 0, 0 }, { 0, 0 } };
    setitimer(ITIMER_PROF, &off, NULL);
    const char *path = getenv("PCPROF_OUT");
    FILE *out = fopen(path != NULL ? path : "pcprof.out", "w");
    if (out == NULL) return;
    for (uint32_t k = 0; k < _dyld_image_count(); k++) {
        if (_dyld_get_image_header(k)->filetype == MH_EXECUTE) {
            fprintf(out, "slide %lx\n", (unsigned long)_dyld_get_image_vmaddr_slide(k));
            break;
        }
    }
    int n = pcprof_n;
    for (int k = 0; k < n; k++) {
        Dl_info d;
        if (dladdr((void *)pcprof_pcs[k], &d) != 0 && d.dli_fname != NULL) {
            const char *image = strrchr(d.dli_fname, '/');
            fprintf(out, "%lx %s %s\n", (unsigned long)pcprof_pcs[k], image != NULL ? image + 1 : d.dli_fname,
                    d.dli_sname != NULL ? d.dli_sname : "?");
        } else {
            fprintf(out, "%lx ? ?\n", (unsigned long)pcprof_pcs[k]);
        }
    }
    fclose(out);
}

__attribute__((constructor)) static void pcprof_start(void) {
    const char *interval = getenv("PCPROF_INTERVAL_US");
    long us = interval != NULL ? atol(interval) : 1000;
    struct sigaction action;
    memset(&action, 0, sizeof action);
    action.sa_sigaction = pcprof_sample;
    action.sa_flags = SA_SIGINFO | SA_RESTART;
    sigaction(SIGPROF, &action, NULL);
    struct itimerval timer = { { 0, (int)us }, { 0, (int)us } };
    setitimer(ITIMER_PROF, &timer, NULL);
    atexit(pcprof_write);
}
