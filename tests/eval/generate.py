#!/usr/bin/env python3
"""Writes tests/golden/self-hosted/eval.out: the bootstrap driver's output for
each program of tests/eval/cases.quest run with `quest -e`, which run_tests.py
--self-hosted compares the self-hosted driver's with (docs/testing.md §2.3).
Run it after changing a program: python tests/eval/generate.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

from quest.syntax.sources import BYTE_ENCODING  # noqa: E402
from quest.testing.runner import DRIVER_SCRIPT, EVAL_GOLDEN, eval_transcript  # noqa: E402


def main() -> None:
    transcript = eval_transcript([sys.executable, str(DRIVER_SCRIPT)])
    EVAL_GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    EVAL_GOLDEN.write_text(transcript, encoding=BYTE_ENCODING)
    print(f"wrote {EVAL_GOLDEN.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
