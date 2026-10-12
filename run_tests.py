#!/usr/bin/env python3
"""Quest Bootstrap Compiler Test Runner CLI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure Python 3.10+ (for pattern matching and typing syntax)
if sys.version_info < (3, 10):
    for candidate in (
        "/opt/homebrew/bin/python3",
        "/opt/homebrew/opt/python@3.11/libexec/bin/python",
    ):
        if Path(candidate).is_file():
            os.execv(candidate, [candidate] + sys.argv)
    sys.exit(f"Error: Quest requires Python 3.10+ (found {sys.version.split()[0]})")

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

from quest.testing.runner import main

if __name__ == "__main__":
    sys.exit(main())
