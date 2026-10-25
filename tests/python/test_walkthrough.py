"""Checks that the excerpts docs/walkthrough.md shows are what the compiler prints.

An excerpt is a fenced block preceded by a comment naming a file and what it shows:

    <!-- excerpt: examples/argmax/argmax.quest typecheck -->

The second word is `source` for the file itself, or a phase given to `--stop-after`, and any further words are
options for the driver (`--echo`). A line of the excerpt that is only `...` stands for any number of lines, and `...`
within a line for any text; otherwise the excerpt's lines must appear as they are, consecutive and in order. Runs of
spaces and tabs after a line's indentation compare as one space, so tokens' tab-separated columns can be aligned.
"""

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
WALKTHROUGH = ROOT_DIR / "docs" / "walkthrough.md"

EXCERPT = re.compile(r"<!-- excerpt: (?P<spec>[^>]*?) -->\n```[a-z]*\n(?P<body>.*?)\n```", re.DOTALL)


def normalize(line: str) -> str:
    indent = len(line) - len(line.lstrip(" "))
    return line[:indent] + re.sub(r"[ \t]+", " ", line[indent:]).rstrip()


def excerpt_pattern(body: str) -> re.Pattern[str]:
    parts = []
    for line in body.split("\n"):
        if line.strip() == "...":
            parts.append(r"(?:[^\n]*\n)*?")
        else:
            pieces = normalize(line).split("...")
            parts.append(".*?".join(re.escape(piece) for piece in pieces) + r"\n")
    return re.compile("^" + "".join(parts), re.MULTILINE)


class TestWalkthrough(unittest.TestCase):

    outputs: dict[tuple[str, ...], str] = {}

    def output_of(self, spec: tuple[str, ...]) -> str:
        if spec not in self.outputs:
            path, what, *options = spec
            if what == "source":
                text = (ROOT_DIR / path).read_text(encoding="utf-8")
            else:
                environment = os.environ.copy()
                environment["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
                process = subprocess.run(
                    [sys.executable, str(ROOT_DIR / "bootstrap" / "python" / "quest_driver.py"),
                     "--stop-after", what, *options, path],
                    capture_output=True, text=True, cwd=ROOT_DIR, env=environment, timeout=120,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                text = process.stdout
            self.outputs[spec] = "\n".join(normalize(line) for line in text.split("\n")) + "\n"
        return self.outputs[spec]

    def test_excerpts_match_the_compiler(self) -> None:
        text = WALKTHROUGH.read_text(encoding="utf-8")
        excerpts = list(EXCERPT.finditer(text))
        self.assertGreater(len(excerpts), 0)
        for match in excerpts:
            spec = tuple(match["spec"].split())
            line = text.count("\n", 0, match.start()) + 1
            with self.subTest(line=line, spec=" ".join(spec)):
                found = excerpt_pattern(match["body"]).search(self.output_of(spec))
                self.assertIsNotNone(found, f"docs/walkthrough.md:{line}: excerpt not found in {' '.join(spec)}")


if __name__ == "__main__":
    unittest.main()
