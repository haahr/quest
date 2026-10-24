"""Quest Source Position Tracking and Source Maps."""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceLocation:
    """A human-readable source position computed from an offset."""
    file_name: str
    offset: int
    line: int        # 1-indexed
    column: int      # 1-indexed

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


def display_file_name(path: Path) -> str:
    """How diagnostics name a source file found by the compiler (an imported unit): relative to the current
    directory if it is inside it, else its full path."""
    try:
        return str(Path(path).resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


class SourceMap:
    """Maintains source text and computes line/column coordinates from offsets."""

    def __init__(self, source_text: str, file_name: str = "<string>"):
        self.source_text = source_text
        self.file_name = file_name
        self.line_starts: list[int] = [0]
        for index, char in enumerate(source_text):
            if char == "\n":
                self.line_starts.append(index + 1)

    def locate(self, offset: int) -> SourceLocation:
        """Maps a 0-indexed character offset to (line, column)."""
        offset = max(0, min(offset, len(self.source_text)))
        line_index = bisect.bisect_right(self.line_starts, offset) - 1
        line = line_index + 1
        column = offset - self.line_starts[line_index] + 1
        return SourceLocation(self.file_name, offset, line, column)

    def offset_of(self, line: int, column: int) -> int:
        """The 0-indexed character offset of a (1-indexed) line and column, the inverse of locate."""
        line_index = max(0, min(line - 1, len(self.line_starts) - 1))
        return min(self.line_starts[line_index] + max(column - 1, 0), len(self.source_text))
