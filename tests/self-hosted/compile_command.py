"""Checks that a self-hosted driver's compile command, and the options it shares
with the bootstrap's driver (--dump-after among them), do what the bootstrap's
do.

Each case is a command line, which both drivers run in a fresh directory of
their own holding the programs below. They must exit with the same status and
write the same diagnostics, leave the same files (and the same main-unit
artifacts in .build), and the binaries they leave must print the same. Their
standard output must be the same too, except that of a case that writes C, which
the two compilers write differently (docs/testing.md section 2.8): it must be C.
The bootstrap compiles only through C, so the driver's compile is given
--backend c; and its compile without one goes through arm64, its default,
leaving the main unit's assembly and a binary that prints what C's does.

The SSA's phases, which only the driver has, are checked on its own: each
ssa_NAME phase its usage text names must dump a function, so that a pass the
pipeline runs but the driver does not accept, or the reverse, fails; and the
numbered passes in questlang/ssa/passes/README.md must be those phases' passes,
in order. run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/compile_command.py DRIVER
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BOOTSTRAP = ROOT_DIR / "questboot"

PROGRAMS = {
    "p.quest": "let x = 3\nx + 4\n",
    "w.quest": 'import writer: Writer\nwriter.putString(writer.output "hi\\n")\n1 + 2\n',
    "m.quest": ("import collections/vector: collections/Vector\nlet v = vector.new(:Int)\nvector.append(:Int v 3)\n"
                "vector.length(:Int v)\n"),
}

# Each case's arguments, and whether its standard output is C
CASES = (
    (["compile", "p.quest"], False),
    (["compile", "--print-result", "p.quest", "-o", "q"], False),
    (["compile", "--output", "q", "--print_result", "m.quest"], False),
    (["compile", "--emit-c", "p.quest"], True),
    (["compile", "--emit-c", "p.quest", "-o", "out.c"], False),
    (["compile", "-c", "m.quest"], False),
    (["compile", "-e", "1 + 1", "--print-result"], False),
    (["compile", "--nogc", "--print-result", "m.quest", "-o", "n"], False),
    (["compile", "p.quest", "m.quest"], False),
    (["compile", "--stop-after", "typecheck", "m.quest"], False),
    (["compile", "--stop-after", "codegen_c", "p.quest"], True),
    (["--stop_after", "tokenize", "--show-values", "p.quest"], False),
    (["--eval", "2 + 2"], False),
    # Dumps follow what the program writes, and precede its result
    (["--dump-after", "parse", "w.quest"], False),
    (["--dump-after", "parse", "--echo", "w.quest"], False),
    (["--dump-after", "tokenize", "--dump_after", "typecheck", "w.quest"], False),
    (["--dump-after", "typecheck", "--stop-after", "parse", "w.quest"], False),
    (["--stop-after", "desugar", "--dump-after", "parse", "w.quest"], False),
)


def run(command: list[str], args: list[str]) -> tuple[int, str, str, list[str], dict[str, str]]:
    """What command does with args in a fresh directory: its exit status, its
    output and errors, the files it leaves, and what each binary among them
    prints."""
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    with tempfile.TemporaryDirectory() as d:
        directory = Path(d)
        for name, text in PROGRAMS.items():
            (directory / name).write_text(text, encoding="utf-8")
        p = subprocess.run([*command, *args], capture_output=True, text=True, cwd=directory, env=environment)
        stderr = p.stderr.replace(str(directory.resolve()), "<dir>").replace(str(directory), "<dir>")
        files = sorted(f.name for f in directory.iterdir() if f.name not in PROGRAMS and f.name != ".build")
        build = directory / ".build"
        if build.is_dir():
            files += sorted(".build/" + f.name for f in build.iterdir() if ".main." in f.name)
        printed = {}
        for name in files:
            path = directory / name
            if path.is_file() and os.access(path, os.X_OK):
                printed[name] = subprocess.run([str(path)], capture_output=True, text=True, cwd=directory).stdout
        return p.returncode, p.stdout, stderr, files, printed


def check(driver: str, args: list[str], writes_c: bool) -> list[str]:
    """How the driver's run of args differs from the bootstrap's."""
    expected = run([str(BOOTSTRAP)], args)
    actual = run([driver], ["compile", "--backend", "c", *args[1:]] if args[0] == "compile" else args)
    problems = []
    for i, what in enumerate(("exit status", "output", "errors", "files", "binaries' output")):
        if what == "output" and writes_c:
            for name, result in (("bootstrap", expected), ("driver", actual)):
                if not result[1].startswith("/*") or "#include" not in result[1]:
                    problems.append(f"{' '.join(args)}: the {name}'s output is not C")
        elif expected[i] != actual[i]:
            problems.append(f"{' '.join(args)}: the {what} differs:\n  bootstrap: {expected[i]!r}\n"
                            f"  driver:    {actual[i]!r}")
    return problems


def check_default(driver: str) -> list[str]:
    """How the driver's compile without a backend differs from going through
    arm64: the main unit's artifacts are its assembly's, and the binary
    prints what the bootstrap's does."""
    args = ["compile", "w.quest"]
    expected = run([str(BOOTSTRAP)], args)
    actual = run([driver], args)
    problems = []
    if ".build/w.main.s" not in actual[3] or ".build/w.main.c" in actual[3]:
        problems.append(f"compile w.quest: not through arm64, leaving {actual[3]!r}")
    if actual[4].get("w") != expected[4].get("w"):
        problems.append(f"compile w.quest: the binary prints {actual[4].get('w')!r}, not {expected[4].get('w')!r}")
    return problems


def usage_ssa_phases(driver: str) -> list[str]:
    """The SSA phases the driver's usage text names, in order."""
    text = subprocess.run([driver, "--help"], capture_output=True, text=True).stdout
    return re.findall(r"\b(ssa(?:_[A-Za-z]+)?)\b[,:]", text.split("Phases (")[-1])


def check_ssa_phases(driver: str) -> list[str]:
    """The SSA phases the driver names that do not dump, and how the passes
    README's numbered table differs from them."""
    phases = usage_ssa_phases(driver)
    problems = [] if "ssa_built" in phases and "ssa" in phases else [f"the usage text names SSA phases {phases!r}"]
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "p.quest").write_text(PROGRAMS["p.quest"], encoding="utf-8")
        for phase in phases:
            p = subprocess.run([driver, "--dump-after", phase, "p.quest"], capture_output=True, text=True, cwd=d,
                               env=environment)
            if p.returncode != 0 or "function " not in p.stdout:
                problems.append(f"--dump-after {phase}: exit status {p.returncode}, errors {p.stderr.strip()!r}")
    readme = (ROOT_DIR / "questlang" / "ssa" / "passes" / "README.md").read_text(encoding="utf-8")
    listed = re.findall(r"^\| *\d+ *\| *\[`([A-Za-z]+)`\]", readme, re.MULTILINE)
    passes = [phase.removeprefix("ssa_") for phase in phases if phase not in ("ssa_built", "ssa")]
    if listed != passes:
        problems.append(f"questlang/ssa/passes/README.md numbers the passes {listed!r}, not {passes!r}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    driver = str(Path(sys.argv[1]).resolve())
    problems = [problem for args, writes_c in CASES for problem in check(driver, args, writes_c)]
    problems += check_default(driver)
    ssa_problems = check_ssa_phases(driver)
    for problem in problems + ssa_problems:
        print(problem)
    print(f"{len(CASES) + 1} command lines compared, {len(problems)} differences")
    print(f"{len(usage_ssa_phases(driver))} SSA phases dumped, {len(ssa_problems)} problems")
    problems += ssa_problems
    sys.exit(1 if problems else 0)
