#!/opt/homebrew/bin/python3.11
"""Times util/regexp against Go's regexp and Python's re
(benchmarks/regexp/README.md, docs/regexp-plan.md step 5).

    benchmarks/regexp/run.py [--repeat N] [--only NAME,...] [--no-python]

It generates the inputs (a log of 100,000 lines and 2 MB of Quest source, ASCII
only, the same each time), builds regexp.quest with ./quest and regexp.go with go, runs
each workload once in each (after one untimed run of each), checks that all of them print the same number,
and prints a table of seconds and of util/regexp's time over Go's.
"""

import argparse
import random
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
WORK = ROOT / ".build" / "regexp-bench"

# Each workload, what it does, and the input it reads
WORKLOADS = [
    ("walk", "the lines walked, and no regexp: the harness's own cost", "log"),
    ("literal", "lines containing ERROR", "log"),
    ("caseless", "lines containing (?i)error", "log"),
    ("alternation", r"lines containing \b(?:timeout|refused|reset|unreachable)\b", "log"),
    ("prefix", r"find user=(\w+) in each line", "log"),
    ("date", r"find a timestamp with six groups in each line", "log"),
    ("anchored", r"find ^([A-Z]+) in each line", "log"),
    ("tokens", "findAll of a tokenizer's pattern over the source", "source"),
    ("replace", r"replaceAll of \s+ over the source", "source"),
]


def generate() -> dict[str, Path]:
    """The inputs, made once: the same bytes every time"""
    WORK.mkdir(parents=True, exist_ok=True)
    log, source = WORK / "log.txt", WORK / "source.txt"
    if not log.exists():
        rng = random.Random(1989)
        levels = ["INFO"] * 6 + ["DEBUG"] * 3 + ["WARN"] * 2 + ["ERROR"]
        words = ["started", "stopped", "request", "served", "cache", "miss", "hit", "queue", "flushed", "retry",
                 "connection", "timeout", "refused", "reset", "unreachable", "error", "ok", "slow", "fast", "done"]
        lines = []
        for i in range(100_000):
            stamp = f"2026-11-{1 + i % 28:02d}T{rng.randrange(24):02d}:{rng.randrange(60):02d}:{rng.randrange(60):02d}"
            message = " ".join(rng.choice(words) for _ in range(rng.randrange(3, 10)))
            user = f" user={rng.choice(['ann', 'bob', 'carol', 'dave', 'eve'])}{rng.randrange(100)}" \
                if rng.random() < 0.4 else ""
            lines.append(f"{rng.choice(levels)} {stamp} service{rng.randrange(8)}: {message}{user}")
        log.write_text("\n".join(lines) + "\n")
    if not source.exists():
        parts, size = [], 0
        files = sorted((ROOT / "lib").rglob("*.quest")) + sorted((ROOT / "questlang").rglob("*.quest"))
        for f in files:
            if size >= 2_000_000:
                break
            # ASCII only: Go matches UTF-8, which this library does not
            text = "".join(c for c in f.read_text(encoding="latin-1") if ord(c) < 128)
            parts.append(text)
            size += len(text)
        source.write_text("".join(parts), encoding="latin-1")
    return {"log": log, "source": source}


def build(no_python: bool) -> dict[str, list[str]]:
    """The command of each implementation"""
    quest = WORK / "regexp-quest"
    done = subprocess.run([str(ROOT / "quest"), "--build-dir", str(WORK / "build"), "-o", str(quest),
                           str(HERE / "regexp.quest")], capture_output=True, text=True)
    if done.returncode != 0:
        sys.exit(f"run.py: regexp.quest did not compile:\n{done.stdout}{done.stderr}")
    go = WORK / "regexp-go"
    done = subprocess.run(["go", "build", "-o", str(go), str(HERE / "regexp.go")], capture_output=True, text=True,
                          cwd=WORK)
    if done.returncode != 0:
        sys.exit(f"run.py: regexp.go did not build:\n{done.stdout}{done.stderr}")
    commands = {"quest": [str(quest)], "go": [str(go)]}
    if not no_python:
        commands["python"] = [sys.executable, "-I", str(HERE / "regexp.py")]
    return commands


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repeat", type=int, default=1, help="how many times each run does its workload")
    parser.add_argument("--only", help="the workloads to run, comma-separated")
    parser.add_argument("--no-python", action="store_true", help="leave out Python's re")
    options = parser.parse_args()
    inputs = generate()
    commands = build(options.no_python)
    chosen = [w for w in WORKLOADS if not options.only or w[0] in options.only.split(",")]
    # One untimed run of each first: the first run after a build pays for
    # loading the program and its input, which would land on one workload
    for command in commands.values():
        subprocess.run([*command, "walk", str(inputs["log"]), "1"], capture_output=True)
    names = list(commands)
    print(f"{'workload':<12} " + " ".join(f"{n:>8}" for n in names) + f" {'quest/go':>9}  result")
    failed = False
    for name, what, input_name in chosen:
        times, results = {}, {}
        for impl, command in commands.items():
            began = time.monotonic()
            done = subprocess.run([*command, name, str(inputs[input_name]), str(options.repeat)],
                                  capture_output=True, text=True)
            times[impl] = time.monotonic() - began
            results[impl] = done.stdout.strip() if done.returncode == 0 else f"exit {done.returncode}: {done.stderr}"
        agree = len(set(results.values())) == 1
        failed |= not agree
        print(f"{name:<12} " + " ".join(f"{times[n]:8.3f}" for n in names)
              + f" {times['quest'] / times['go']:9.2f}  {results['quest'] if agree else results}")
    if failed:
        sys.exit("run.py: the implementations disagree")


if __name__ == "__main__":
    main()
