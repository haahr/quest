"""Shadow-mode cross-checks for compiler optimizations.

Each optimization of the type checker (symbol indexing, substitution sharing, hash-consing,
subtype caching) keeps its original, unoptimized algorithm available as a reference. When the
corresponding shadow check is enabled, both paths run and any disagreement raises
ShadowMismatch immediately, so a test run under shadow mode proves the optimization is
observationally equivalent on that input.

Checks are process-wide and are enabled from the driver (--shadow-<name> or --shadow-all).
Nested in-process compilations (interfaces, modules) inherit them automatically.
"""

from __future__ import annotations

import argparse

# Registry of known checks: name -> one-line description.
SHADOW_CHECKS: dict[str, str] = {}

_enabled: set[str] = set()


class ShadowMismatch(AssertionError):
    """Raised when an optimized path disagrees with its reference implementation."""


def register_check(name: str, description: str) -> str:
    """Registers a shadow check name (idempotent) and returns it."""
    SHADOW_CHECKS[name] = description
    return name


def enable(name: str) -> None:
    if name == "all":
        _enabled.update(SHADOW_CHECKS)
        return
    if name not in SHADOW_CHECKS:
        raise ValueError(f"Unknown shadow check '{name}' (known: {', '.join(sorted(SHADOW_CHECKS))})")
    _enabled.add(name)


def disable_all() -> None:
    _enabled.clear()


def is_enabled(name: str) -> bool:
    return name in _enabled


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Adds --shadow-all and one --shadow-<name> flag per registered check to a CLI parser."""
    parser.add_argument(
        "--shadow-all",
        dest="shadow_all",
        action="store_true",
        help="Enable every shadow-mode cross-check (slow; for verifying optimizations).",
    )
    for name, description in sorted(SHADOW_CHECKS.items()):
        parser.add_argument(
            f"--shadow-{name}",
            dest=f"shadow_{name.replace('-', '_')}",
            action="store_true",
            help=f"Shadow check: {description}",
        )


def apply_arguments(parsed: argparse.Namespace) -> None:
    """Enables the shadow checks selected by flags added with add_arguments."""
    if getattr(parsed, "shadow_all", False):
        enable("all")
    for name in SHADOW_CHECKS:
        if getattr(parsed, f"shadow_{name.replace('-', '_')}", False):
            enable(name)


def mismatch(name: str, message: str) -> ShadowMismatch:
    """Builds a ShadowMismatch for check `name`; callers raise the result."""
    return ShadowMismatch(f"[shadow-{name}] {message}")
