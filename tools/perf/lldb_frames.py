"""lldb commands for finding what a program's frames keep alive
(docs/profiling.md section 6), loaded with `command script import`:

    deadroots ASM NM   for each frame of a Quest function, the words that
                       point into the collector's heap but hold no value live
                       across the call the frame is in, by the annotations
                       QUEST_LIVE_SLOTS=1 puts in ASM (the program's
                       assembly) at the return addresses that NM (nm's
                       listing of the program's _live_ symbols) gives

Each is printed as DEAD (a slot, below the frame's saved registers) or SAVED
(a callee-saved register the frame saved for its caller, which is dead or live
by the caller's annotation, not the frame's)."""

import re
import struct
import subprocess

import lldb


def heap_regions(target: lldb.SBTarget) -> list[tuple[int, int]]:
    """The collector's heap: the range the runtime reserved, between its
    quest_gc_heap_lo and the blocks it has taken (runtime/quest_gc.c)."""
    def global_value(name: str) -> int:
        return target.FindFirstGlobalVariable(name).GetValueAsUnsigned()
    lo = global_value("quest_gc_heap_lo")
    return [(lo, lo + global_value("quest_gc_high_water") * 32768)]


def in_heap(regions: list[tuple[int, int]], word: int) -> bool:
    return any(lo <= word < hi for lo, hi in regions)


def annotations(path: str) -> dict[str, tuple[int, set[int]]]:
    """Each _live_ label's frame size and live slot offsets, from the comment
    before it"""
    found, pending = {}, None
    for line in open(path):
        m = re.match(r"// live \(frame (\d+)\): (.*)", line)
        if m:
            pending = (int(m.group(1)), set(int(x) for x in re.findall(r"sp\+(\d+) ", m.group(2) + " ")))
        elif "_live_" in line and line.rstrip().endswith(":") and pending:
            found[line.strip()[1:-1]] = pending
    return found


def deadroots(debugger, command, result, internal_dict):
    """The deadroots command (see the module docstring): command is "ASM NM".

    Walks the selected thread's stack, skipping the innermost frame, which is
    stopped where the user stopped it rather than at a call, and the
    outermost, which has no caller frame to bound it. Every other frame's PC is
    a return address; when NM names it as a _live_ label that ASM annotates,
    the frame's words, from its SP up to its caller's SP, are checked. A word
    that points into the heap (heap_regions) at an offset the annotation does
    not list as live is printed: as DEAD if it is below the annotated frame
    size, else as SAVED. A word is only a candidate: an integer that happens
    to look like a heap address is printed too. result is unused; the lines
    go to standard output."""
    asm, nm = command.split()
    live = annotations(asm)
    labels = {}
    for line in open(nm):
        address, _, name = line.split()
        labels[int(address, 16)] = name[1:]
    process = debugger.GetSelectedTarget().GetProcess()
    thread = process.GetSelectedThread()
    regions = heap_regions(debugger.GetSelectedTarget())
    frames = [thread.GetFrameAtIndex(i) for i in range(thread.GetNumFrames())]
    for i in range(1, len(frames) - 1):
        frame = frames[i]
        label = labels.get(frame.GetPC())
        if label is None or label not in live:
            continue
        size, offsets = live[label]
        lo, hi = frame.GetSP(), frames[i + 1].GetSP()
        error = lldb.SBError()
        data = process.ReadMemory(lo, hi - lo, error)
        if not error.Success():
            continue
        words = struct.unpack("<%dQ" % ((hi - lo) // 8), data[: (hi - lo) // 8 * 8])
        for k, word in enumerate(words):
            if in_heap(regions, word) and 8 * k not in offsets:
                kind = "DEAD" if 8 * k < size else "SAVED"
                print(f"{kind} frame {i} {label} sp+{8 * k} {word:#x}")


def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand(f"command script add -f {__name__}.deadroots deadroots")
