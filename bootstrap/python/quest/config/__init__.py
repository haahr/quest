"""Compiler configuration, options, and artifact ABI contracts.

This package provides:
- quest.config.options: CompilerOptions dataclass with compilation flags and directories.
- quest.config.abi: ABI version, producer information, and artifact contract verification.
"""

from __future__ import annotations

from quest.config.abi import (
    ABI_VERSION,
    PRODUCER,
    built_from,
    has_current_abi,
    header_stamp,
    incompatible_artifact_message,
    recorded_abi,
)
from quest.config.options import CompilerOptions

__all__ = [
    "ABI_VERSION",
    "CompilerOptions",
    "PRODUCER",
    "built_from",
    "has_current_abi",
    "header_stamp",
    "incompatible_artifact_message",
    "recorded_abi",
]
