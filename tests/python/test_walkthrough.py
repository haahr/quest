"""Checks that the excerpts docs/walkthrough.md shows are what the compilers
print.

An excerpt is a fenced block preceded by a comment naming a file and what it
shows:

    <!-- excerpt: examples/argmax/argmax.quest typecheck -->

The second word is `source` for the file itself, or a phase given to
`--stop-after`, and any further words are options for the driver (`--echo`). A
line of the excerpt that is only `...` stands for any number of lines, and `...`
within a line for any text; otherwise the excerpt's lines must appear as they
are, consecutive and in order. Runs of spaces and tabs after a line's
indentation compare as one space, so tokens' tab-separated columns can be
aligned.

The bootstrap prints the output, unless the comment starts with `self-hosted`:

    <!-- excerpt: self-hosted examples/argmax/argmax.quest ssa -->

which has ./quest print it. Its later phases (the SSA and arm64 assembly) name
values, blocks, labels, and registers by numbers that any change to the
optimizer may shift, so for those excerpts the numbers are compared as wildcards:
`%57` and `%3`, `b12` and `b4`, `x21` and `x3` are alike, though `x21` and `d3`
are not.
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
WALKTHROUGH = ROOT_DIR / "docs" / "walkthrough.md"

EXCERPT = re.compile(r"<!-- excerpt: (?P<spec>[^>]*?) -->\n```[a-z]*\n(?P<body>.*?)\n```", re.DOTALL)

# What the self-hosted compiler numbers: SSA values (%57), blocks (b12), the
# assembly's labels (Lf1_b12), and registers (x21, w0, d8)
NUMBERED = re.compile(r"(%|\bLf\d+_b|\b[bxwd])\d+\b")


def normalize(line: str) -> str:
    indent = len(line) - len(line.lstrip(" "))
    return line[:indent] + re.sub(r"[ \t]+", " ", line[indent:]).rstrip()


def unnumber(text: str) -> str:
    return NUMBERED.sub(lambda m: m.group(1) + "#", text)


def excerpt_pattern(body: str, renumbered: bool) -> re.Pattern[str]:
    parts = []
    for line in body.split("\n"):
        if line.strip() == "...":
            parts.append(r"(?:[^\n]*\n)*?")
        else:
            line = normalize(line)
            if renumbered:
                line = unnumber(line)
            pieces = line.split("...")
            parts.append(".*?".join(re.escape(piece) for piece in pieces) + r"\n")
    return re.compile("^" + "".join(parts), re.MULTILINE)


class TestWalkthrough(unittest.TestCase):

    outputs: dict[tuple[str, ...], str] = {}
    # A build directory for each compiler, so that no unit cached in the
    # tree's .build by an earlier compiler is linked
    build_dirs = {compiler: tempfile.TemporaryDirectory(prefix=f"quest-walkthrough-{compiler}-")
                  for compiler in ("bootstrap", "self-hosted")}

    def output_of(self, spec: tuple[str, ...]) -> str:
        if spec not in self.outputs:
            compiler = "bootstrap"
            arguments = spec
            if spec[0] == "self-hosted":
                compiler, arguments = "self-hosted", spec[1:]
            path, what, *options = arguments
            if what == "source":
                text = (ROOT_DIR / path).read_text(encoding="utf-8")
            else:
                environment = os.environ.copy()
                if compiler == "bootstrap":
                    environment["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
                    command = [sys.executable, str(ROOT_DIR / "bootstrap" / "python" / "quest_driver.py")]
                    timeout = 120
                else:
                    # The launcher builds the compiler's stages first if they
                    # are stale, which takes minutes
                    command = [str(ROOT_DIR / "quest")]
                    timeout = 1800
                process = subprocess.run(
                    [*command, "--stop-after", what, "--build-dir", self.build_dirs[compiler].name, *options, path],
                    capture_output=True, text=True, cwd=ROOT_DIR, env=environment, timeout=timeout,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                text = process.stdout
            text = "\n".join(normalize(line) for line in text.split("\n")) + "\n"
            if compiler == "self-hosted":
                text = unnumber(text)
            self.outputs[spec] = text
        return self.outputs[spec]

    def test_excerpts_match_the_compiler(self) -> None:
        text = WALKTHROUGH.read_text(encoding="utf-8")
        excerpts = list(EXCERPT.finditer(text))
        self.assertGreater(len(excerpts), 0)
        for match in excerpts:
            spec = tuple(match["spec"].split())
            line = text.count("\n", 0, match.start()) + 1
            with self.subTest(line=line, spec=" ".join(spec)):
                pattern = excerpt_pattern(match["body"], spec[0] == "self-hosted")
                found = pattern.search(self.output_of(spec))
                self.assertIsNotNone(found, f"docs/walkthrough.md:{line}: excerpt not found in {' '.join(spec)}")


if __name__ == "__main__":
    unittest.main()
