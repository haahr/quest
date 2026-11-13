"""Quest Build System package.

Provides whole-program and multi-module build orchestration, and the host C
compiler and linker every backend's objects go through (compiler_runner.py).
"""

from __future__ import annotations

from quest.build.engine import (
    BuildEngine,
    BuildError,
    BuildResult,
    detect_module_cycle,
    interfaces_conform,
    unit_module_refs,
)
from quest.build.logger import BuildLogger

__all__ = [
    "BuildEngine",
    "BuildError",
    "BuildLogger",
    "BuildResult",
    "detect_module_cycle",
    "interfaces_conform",
    "unit_module_refs",
]
