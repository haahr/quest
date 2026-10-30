"""Builds, checks, and times the MLton benchmarks converted to Quest.

Each benchmark is a Standard ML program in sml/ (from MLton's benchmark/tests)
and its conversion, NAME.quest. A program does its work n times, n being its
first argument (1 if none); the SML originals are given the same n through
Main.doit. Programs run in a scratch directory holding a copy of DATA/, so the
files some of them write are kept apart from the tree.

    run.py reference [NAME...]   run the originals (built with MLton) once and
                                 record their output in expected/
    run.py check [NAME...]       run the conversions once and compare their
                                 output with expected/
    run.py time [NAME...]        time the conversions (and with --mlton the
                                 originals) at the suite's counts, scaled by
                                 --scale, or at --count
    run.py report FILE...        summarize the times recorded with --results:
                                 each system's time and its ratio to MLton's
                                 at the same count, and their geometric means

A benchmark's output is its standard output, its exit status, and the files it
writes. Builds go to .build/ here: the conversions are built by ./quest, the
self-hosted compiler (or --compiler, such as ./questboot), the originals by
mlton. With --interpret, the conversions are not built but run by the
compiler's tree-walking interpreter (--stop-after interpret).
docs/benchmarks.md describes the baseline these make.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SML_DIR = HERE / "sml"
DATA_DIR = HERE / "DATA"
EXPECTED_DIR = HERE / "expected"
BUILD_DIR = HERE / ".build"

# MLton's counts (benchmark/main.sml), each about 30 to 45 seconds of a
# MLton-compiled program on its authors' machine in 2022
COUNTS = {
    "barnes-hut": 32768, "boyer": 12288, "checksum": 12288, "count-graphs": 12, "DLXSimulator": 6,
    "even-odd": 24, "fft": 16, "fib": 32, "flat-array": 49152, "hamlet": 384, "imp-for": 4096,
    "knuth-bendix": 3072, "lexgen": 1536, "life": 32, "logic": 256, "mandelbrot": 6, "matrix-multiply": 192,
    "md5": 12, "mlyacc": 3072, "model-elimination": 4, "mpuz": 128, "nucleic": 4096,
    "output1": 12, "peek": 192, "pidigits": 4096, "psdes-random": 24, "ratio-regions": 1536, "ray": 1536,
    "raytrace": 96, "simple": 1024, "smith-normal-form": 192, "string-concat": 256, "tailfib": 512,
    "tailmerge": 24576, "tak": 32, "tensor": 6, "tsp": 16, "tyan": 384, "vector32-concat": 48,
    "vector64-concat": 32, "vector-rev": 96, "vliw": 1024, "wc-input1": 16384, "wc-scanStream": 32768,
    "zebra": 64, "zern": 16384,
}


class BuildError(Exception):
    """A conversion that does not compile, with the compiler's diagnostics."""


# The benchmarks whose Main.testit (from the SML/NJ suite) prints their results,
# which check compares too: the conversions run testit when given it as their
# argument. The other testits print nothing, or (boyer's) are hidden.
TESTIT = {"life", "logic", "mandelbrot", "tsp"}


# Programs of MLton's benchmark/tests that are not in the suite, and why
OMITTED = {
    "fxp": "not a benchmark: an XML parser with no Main.doit and no input, which MLton's suite omits too",
    "merge": "recurses 200000 calls deep, needing about 10 MB of stack, more than macOS lets a process have",
}


def timeless_metis(stdout: str) -> str:
    """model-elimination's output without what depends on the time it takes:
    its progress lines, one per CPU-time slice of its search, and the times it
    prints."""
    lines = [line for line in stdout.split("\n") if not line.startswith("[m(")]
    return re.sub(r"User: \S+  System: \S+  Real: \S+", "User: -  System: -  Real: -", "\n".join(lines))


# Programs whose output depends on how long they take, and the part of it check
# compares: Quest cannot read the clock
TIMELESS = {"model-elimination": timeless_metis}


def benchmark_names(requested: list[str]) -> list[str]:
    names = requested or sorted(p.stem for p in SML_DIR.glob("*.sml") if p.stem not in OMITTED)
    unknown = [n for n in names if not (SML_DIR / f"{n}.sml").is_file()]
    if unknown:
        sys.exit(f"unknown benchmarks: {', '.join(unknown)}")
    return names


def build_original(name: str) -> Path:
    """The MLton build of the original, Main.doit given its count as the first
    argument (or, with testit, Main.testit run on standard output)."""
    out_dir = BUILD_DIR / "mlton"
    out_dir.mkdir(parents=True, exist_ok=True)
    binary = out_dir / name
    source = SML_DIR / f"{name}.sml"
    if binary.is_file() and binary.stat().st_mtime >= source.stat().st_mtime:
        return binary
    main = out_dir / f"{name}-main.sml"
    testit = ('                      ["testit"] => Main.testit TextIO.stdOut\n                    | '
              if name in TESTIT else "                      ")
    main.write_text(
        "val _ = (case CommandLine.arguments () of\n"
        f"{testit}n :: _ => Main.doit (valOf (Int.fromString n))\n"
        "                    | [] => Main.doit 1)\n",
        encoding="utf-8")
    mlb = out_dir / f"{name}.mlb"
    mlb.write_text(f"$(SML_LIB)/basis/basis.mlb\n$(SML_LIB)/basis/mlton.mlb\n$(SML_LIB)/basis/unsafe.mlb\n"
                   f"{source}\n{main}\n", encoding="utf-8")
    subprocess.run(["mlton", "-output", str(binary), str(mlb)], check=True)
    return binary


BUILD_SECONDS: dict[str, float] = {}


def build_conversion(name: str, compiler: list[str], backend: str | None = None) -> Path:
    """The Quest build of the conversion, with backend if one is named, into a
    build directory of its own; BUILD_SECONDS records how long it took."""
    out_dir = BUILD_DIR / ("quest" if backend is None else f"quest-{backend}")
    out_dir.mkdir(parents=True, exist_ok=True)
    binary = out_dir / name
    source = HERE / f"{name}.quest"
    if not source.is_file():
        raise FileNotFoundError(f"{source.relative_to(ROOT)} does not exist")
    backend_args = [] if backend is None else ["--backend", backend]
    started = time.monotonic()
    proc = subprocess.run([*compiler, *backend_args, "--build-dir", str(out_dir / "units"), "-o", str(binary),
                           str(source)], capture_output=True, text=True)
    BUILD_SECONDS[name] = time.monotonic() - started
    if proc.returncode != 0:
        raise BuildError(proc.stderr.strip() or proc.stdout.strip())
    return binary


def deep_stack() -> None:
    """Raises the stack limit to its maximum before a benchmark runs: the SML
    originals assume a deep stack (MLton's grows on the heap), and some recurse
    hundreds of thousands of calls deep, which an 8 MB stack does not hold."""
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    try:
        resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
    except (ValueError, OSError):
        pass  # some systems (recent macOS among them) refuse; the benchmark runs with soft


def interpreted(name: str, compiler: list[str]) -> list[str]:
    """The command that runs the conversion in the compiler's interpreter."""
    source = HERE / f"{name}.quest"
    if not source.is_file():
        raise FileNotFoundError(f"{source.relative_to(ROOT)} does not exist")
    # The interpreter builds the modules the program imports, in a build
    # directory of its own rather than the scratch directory's .build/
    build = BUILD_DIR / "interpret" / Path(compiler[0]).name
    return [*compiler, "--build-dir", str(build), "--stop-after", "interpret", str(source)]


def run_in_scratch(program: Path | list[str], count: int | str,
                   timeout: float) -> tuple[str, int, dict[str, bytes], float, str]:
    """Standard output, exit status, the files written or changed, the seconds
    taken, and standard error, of running program (a binary, or a command) with
    count in a scratch directory holding a copy of DATA/."""
    with tempfile.TemporaryDirectory() as d:
        work = Path(d)
        shutil.copytree(DATA_DIR, work / "DATA")
        before = {p.relative_to(work).as_posix(): p.read_bytes() for p in work.rglob("*") if p.is_file()}
        start = time.perf_counter()
        command = [str(program)] if isinstance(program, Path) else program
        proc = subprocess.run([*command, str(count)], cwd=work, stdin=subprocess.DEVNULL, capture_output=True,
                              preexec_fn=deep_stack,
                              timeout=timeout)
        elapsed = time.perf_counter() - start
        written = {}
        for p in sorted(work.rglob("*")):
            rel = p.relative_to(work).as_posix()
            if p.is_file() and before.get(rel) != p.read_bytes():
                written[rel] = p.read_bytes()
        return proc.stdout.decode("latin-1"), proc.returncode, written, elapsed, proc.stderr.decode("latin-1")


def file_digests(written: dict[str, bytes]) -> str:
    """The files a benchmark wrote, as lines of their paths, sizes, and SHA-256
    digests: some are large (ray's image is 786 KB)."""
    return "".join(f"{rel} {len(data)} {hashlib.sha256(data).hexdigest()}\n" for rel, data in sorted(written.items()))


def record(name: str, stdout: str, status: int, written: dict[str, bytes], suffix: str = "") -> None:
    EXPECTED_DIR.mkdir(exist_ok=True)
    (EXPECTED_DIR / f"{name}{suffix}.out").write_text(f"{stdout}[exit {status}]\n", encoding="latin-1")
    files = EXPECTED_DIR / f"{name}{suffix}.files"
    if written:
        files.write_text(file_digests(written), encoding="utf-8")
    else:
        files.unlink(missing_ok=True)


def differences(name: str, stdout: str, status: int, written: dict[str, bytes], suffix: str = "") -> list[str]:
    problems = []
    expected_out = (EXPECTED_DIR / f"{name}{suffix}.out").read_text(encoding="latin-1")
    timeless = TIMELESS.get(name, lambda s: s)
    if timeless(f"{stdout}[exit {status}]\n") != timeless(expected_out):
        problems.append(f"{'testit ' if suffix else ''}standard output or exit status differs")
    files = EXPECTED_DIR / f"{name}{suffix}.files"
    expected = files.read_text(encoding="utf-8") if files.is_file() else ""
    if file_digests(written) != expected:
        problems.append("the files written differ")
    return problems


def time_runs(name: str, system: str, program: Path | list[str], count: int, args: argparse.Namespace) -> list[float]:
    """The seconds each of --runs runs of program took, appended to --results
    if given. A run that times out ends the runs, and is recorded as taking
    longer than --timeout. A run at count 1 must print what expected/ holds;
    one that does not is recorded with the first line of its standard error."""
    seconds: list[float] = []
    timed_out = False
    wrong = None
    for _ in range(args.runs):
        try:
            stdout, status, written, elapsed, stderr = run_in_scratch(program, count, args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            break
        seconds.append(elapsed)
        if count == 1 and differences(name, stdout, status, written):
            errors = [line for line in stderr.splitlines() if "error" in line.lower()]
            wrong = re.sub(r"^\S+:\d+:\d+: ", "", (errors or stderr.splitlines() or ["(no error)"])[0])
            break
    if args.results:
        entry = {"name": name, "system": system, "count": count, "seconds": seconds}
        if timed_out:
            entry["timeout"] = args.timeout
        if wrong is not None:
            entry["wrong"] = wrong
        Path(args.results).parent.mkdir(parents=True, exist_ok=True)
        with open(args.results, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    if timed_out:
        raise subprocess.TimeoutExpired(system, args.timeout)
    if wrong is not None:
        raise BuildError(f"{system} printed the wrong output: {wrong}")
    return seconds


def median(xs: list[float]) -> float:
    xs = sorted(xs)
    return (xs[len(xs) // 2] + xs[(len(xs) - 1) // 2]) / 2


def geomean(xs: list[float]) -> float:
    return math.exp(sum(map(math.log, xs)) / len(xs))


def ratio_text(r: float) -> str:
    return f"{r:.3f}" if r < 0.1 else f"{r:.2f}" if r < 10 else f"{r:.1f}" if r < 1000 else f"{r:.0f}"


def report(paths: list[str], exclude: list[str]) -> int:
    """Prints, for each Quest system, a Markdown table of its median time on
    each benchmark and MLton's at the same count, the ratio of the two, and the
    geometric mean of the ratios, over every benchmark and over those not in
    exclude. A later entry for a benchmark, system, and count replaces an
    earlier one. A run that timed out shows as >TIMEOUT, its ratio a lower
    bound, and makes the means lower bounds. A run that printed the wrong
    output shows as failed, and counts in no mean."""
    entries: dict[tuple[str, str, int], dict] = {}
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                e = json.loads(line)
                entries[e["name"], e["system"], e["count"]] = e
    for system in sorted({s for _, s, _ in entries if s != "mlton"}):
        print(f"| Benchmark | n | MLton | {system} | Ratio |\n|---|--:|--:|--:|--:|")
        ratios: dict[str, float] = {}
        bounded = failed = 0
        for (name, s, count), e in sorted(entries.items(), key=lambda kv: kv[0][0].lower()):
            base = entries.get((name, "mlton", count))
            if s != system or base is None or not base["seconds"]:
                continue
            m = median(base["seconds"])
            if e.get("wrong") is not None:
                failed += 1
                print(f"| {name} | {count} | {m:.2f} | failed: {e['wrong']} | |")
                continue
            mark = ""
            if e.get("timeout") is not None:
                t, mark = e["timeout"], ">"
                bounded += 1
            else:
                t = median(e["seconds"])
            ratios[name] = t / m
            print(f"| {name} | {count} | {m:.2f} | {mark}{t:.2f} | {mark}{ratio_text(t / m)} |")
        mark = ">" if bounded else ""
        if ratios:
            print(f"| **geometric mean** ({len(ratios)}) | | | | **{mark}{geomean(list(ratios.values())):.2f}** |")
            kept = [r for n, r in ratios.items() if n not in exclude]
            if exclude and kept:
                print(f"| geometric mean without {', '.join(exclude)} ({len(kept)}) | | | | {mark}{geomean(kept):.2f} |")
        if failed:
            print(f"\n{failed} failed")
        print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("reference", "check", "time", "report"))
    parser.add_argument("names", nargs="*")
    parser.add_argument("--compiler", default=str(ROOT / "quest"),
                        help="the Quest compiler (default ./quest, the self-hosted one)")
    parser.add_argument("--scale", type=float, default=1.0, help="multiply the suite's counts by this (time)")
    parser.add_argument("--count", type=int, help="run every program at this count (time)")
    parser.add_argument("--mlton", action="store_true", help="also time the originals (time)")
    parser.add_argument("--mlton-only", action="store_true", help="time only the originals (time)")
    parser.add_argument("--backend", help="build the conversions with this backend: c, ssac, or arm64 (check, time)")
    parser.add_argument("--interpret", action="store_true",
                        help="run the conversions in the compiler's interpreter (check, time)")
    parser.add_argument("--runs", type=int, default=1, help="time each program this many times (time)")
    parser.add_argument("--results", help="append the times to this file, as JSON lines (time)")
    parser.add_argument("--timeout", type=float, default=3600.0, help="seconds a run may take")
    parser.add_argument("--exclude", default="", help="benchmarks to leave out of a second mean, NAME,... (report)")
    args = parser.parse_intermixed_args()
    if args.command == "report":
        return report(args.names, [n for n in args.exclude.split(",") if n])
    names = benchmark_names(args.names)
    # Programs run in a scratch directory, so a compiler named by a path is named by its absolute one
    compiler = [str(Path(args.compiler).resolve()) if "/" in args.compiler else args.compiler]
    system = Path(args.compiler).name + (" interpret" if args.interpret else "") + \
        (f" {args.backend}" if args.backend else "")

    def conversion(name: str) -> Path | list[str]:
        return interpreted(name, compiler) if args.interpret else build_conversion(name, compiler, args.backend)

    failed = []
    for name in names:
        try:
            if args.command == "reference":
                binary = build_original(name)
                record(name, *run_in_scratch(binary, 1, args.timeout)[:3])
                if name in TESTIT:
                    record(name, *run_in_scratch(binary, "testit", args.timeout)[:3], suffix="-testit")
                print(f"{name}: recorded")
            elif args.command == "check":
                binary = conversion(name)
                problems = differences(name, *run_in_scratch(binary, 1, args.timeout)[:3])
                if name in TESTIT:
                    problems += differences(name, *run_in_scratch(binary, "testit", args.timeout)[:3], suffix="-testit")
                print(f"{name}: {'ok' if not problems else '; '.join(problems)}")
                if problems:
                    failed.append(name)
            else:
                count = args.count or max(1, round(COUNTS[name] * args.scale))
                line = f"{name:20} n={count:<7}"
                if args.mlton or args.mlton_only:
                    mlton_seconds = median(time_runs(name, "mlton", build_original(name), count, args))
                    line += f" mlton {mlton_seconds:9.2f}s"
                if not args.mlton_only:
                    quest_seconds = median(time_runs(name, system, conversion(name), count, args))
                    line += f" {system} {quest_seconds:9.2f}s"
                    if name in BUILD_SECONDS:
                        line += f" (built in {BUILD_SECONDS[name]:.1f}s)"
                    if args.mlton:
                        line += f"  ratio {quest_seconds / mlton_seconds:7.1f}"
                print(line, flush=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, BuildError) as err:
            print(f"{name}: {err}")
            failed.append(name)
    if failed:
        print(f"failed: {' '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
