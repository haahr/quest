#!/usr/bin/env python3
"""The bootstrap compiler's entry point, which ./questboot runs: quest/driver/main
on the command line."""

import os
import sys

# bootstrap/python, where the quest package is
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quest.driver.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
