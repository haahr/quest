"""Checks that a self-hosted driver's compile command, and the options it shares
with the bootstrap's driver (--dump-after among them), do what the bootstrap's
do.

Each case is a command line, which both drivers run in a fresh directory of
their own holding the programs below. They must exit with the same status and
write the same diagnostics, leave the same files (and the same main-unit
artifacts in .build), and the binaries they leave must print the same. Their
standard output must be the same too, except that of a case that writes C, which
the two compilers write differently (docs/testing.md section 2.8): it must be C.
run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/compile_command.py DRIVER
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BOOTSTRAP = ROOT_DIR / "quest"

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
    actual = run([driver], args)
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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    driver = str(Path(sys.argv[1]).resolve())
    problems = [problem for args, writes_c in CASES for problem in check(driver, args, writes_c)]
    for problem in problems:
        print(problem)
    print(f"{len(CASES)} command lines compared, {len(problems)} differences")
    sys.exit(1 if problems else 0)
