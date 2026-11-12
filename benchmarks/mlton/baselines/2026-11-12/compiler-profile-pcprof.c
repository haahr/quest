/* A program counter sampler for macOS (docs/profiling.md section 4), loaded
 * into a program with DYLD_INSERT_LIBRARIES; tools/perf/profile.py builds and
 * runs it. A thread of its own wakes every PCPROF_INTERVAL_US microseconds
 * (1000 by default), and records the program counter of each of the
 * program's other threads that is running, suspending each while it reads
 * it, as sample(1) does. At exit it stops and writes to PCPROF_OUT the main
 * executable's slide, then each sample's program counter, image, and symbol,
 * from dladdr, which knows a binary's local symbols unless it is stripped.
 *
 * It does not use SIGPROF and ITIMER_PROF: macOS posts that signal at the
 * thread's next return to user mode, typically from a system call, so the
 * samples of a program that calls the system now and then pile up on the
 * calls (wc-scanStream showed 88 percent in read, where it spends 2). Only
 * running threads are sampled, so the samples weigh code by the CPU time
 * spent in it, as a profiling timer would, and a thread blocked in the
 * kernel (a collector's idle marker) is not sampled at all. A thread in a
 * system call that is running in the kernel is sampled at its user program
 * counter, in libsystem_kernel. */

#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <mach/mach.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define PCPROF_MAX (1 << 22)

static uintptr_t     pcprof_pcs[PCPROF_MAX];
static volatile int  pcprof_n;
static volatile int  pcprof_stop;
static pthread_t     pcprof_thread;
static long          pcprof_us = 1000;

/* The program counter of thread, if it is running. The run state is read
 * before the thread is suspended, since a suspended thread is no longer
 * running; it is then suspended while its registers are read, so that they
 * are its own and not half updated. */
static void pcprof_take(thread_act_t thread) {
    struct thread_basic_info info;
    mach_msg_type_number_t count = THREAD_BASIC_INFO_COUNT;
    if (thread_info(thread, THREAD_BASIC_INFO, (thread_info_t)&info, &count) != KERN_SUCCESS
        || info.run_state != TH_STATE_RUNNING || thread_suspend(thread) != KERN_SUCCESS) {
        return;
    }
    arm_thread_state64_t state;
    mach_msg_type_number_t n = ARM_THREAD_STATE64_COUNT;
    if (thread_get_state(thread, ARM_THREAD_STATE64, (thread_state_t)&state, &n) == KERN_SUCCESS
        && pcprof_n < PCPROF_MAX) {
        pcprof_pcs[pcprof_n++] = (uintptr_t)arm_thread_state64_get_pc(state);
    }
    thread_resume(thread);
}

static void *pcprof_run(void *unused) {
    (void)unused;
    thread_act_t self = mach_thread_self();
    struct timespec interval = { pcprof_us / 1000000, (pcprof_us % 1000000) * 1000 };
    while (!pcprof_stop) {
        nanosleep(&interval, NULL);
        thread_act_array_t threads;
        mach_msg_type_number_t count;
        if (task_threads(mach_task_self(), &threads, &count) != KERN_SUCCESS) continue;
        for (mach_msg_type_number_t k = 0; k < count; k++) {
            if (threads[k] != self && !pcprof_stop) pcprof_take(threads[k]);
            mach_port_deallocate(mach_task_self(), threads[k]);
        }
        vm_deallocate(mach_task_self(), (vm_address_t)threads, count * sizeof threads[0]);
    }
    mach_port_deallocate(mach_task_self(), self);
    return NULL;
}

static void pcprof_write(void) {
    pcprof_stop = 1;
    pthread_join(pcprof_thread, NULL);
    const char *path = getenv("PCPROF_OUT");
    char name[1024]; snprintf(name, sizeof name, "%s.%d", path != NULL ? path : "pcprof.out", (int)getpid());
    FILE *out = fopen(name, "w");
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
    if (interval != NULL && atol(interval) > 0) pcprof_us = atol(interval);
    if (pthread_create(&pcprof_thread, NULL, pcprof_run, NULL) == 0) atexit(pcprof_write);
}
