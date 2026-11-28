"""The wasm backend's table of the library's externals covers lib/ (docs/wasm.md
section 4.2): every external value and function a module of lib/ binds names a
C symbol that questlang/wasm/externals' table has a row for, or that
questlang/wasm/codegen's externalValue names (the library's constants), by name
or by prefix, or is one listed in LACKING with the reason the table does not. A
symbol on neither list is one a change to lib/ added and the table missed; one
on both is one the table compiles, to take off LACKING.

    python -m unittest tests.python.test_wasm_externals
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TABLE = ROOT / "questlang" / "wasm" / "externals.mod.quest"
CODEGEN = ROOT / "questlang" / "wasm" / "codegen.mod.quest"

# The externals of lib/ the table does not compile, each with why
LACKING = {
    # dynamic's serialization, bound in lib/dynamic.mod.quest; on this target
    # lib/dynamic.wasm.mod.quest, the module's wasm variant, replaces it and
    # writes them in Quest (runtime/wasm/dynamic), so the table never sees them
    "quest_dynamic_extern", "quest_dynamic_intern",
}

EXTERNAL = re.compile(r'\blet\s+\w+[^=]*=\s*external\s+"([^"]+)"')


def library_externals() -> set[str]:
    """The C symbols every module of lib/ binds with external, its wasm
    variants included"""
    symbols = set()
    for path in (ROOT / "lib").rglob("*.mod.quest"):
        symbols.update(EXTERNAL.findall(path.read_text()))
    return symbols


def table_symbols() -> tuple[set[str], set[str]]:
    """The symbols the table names, and the prefixes it handles whole (its
    prefixed rows, `let prefix = "..."`)"""
    text = TABLE.read_text() + CODEGEN.read_text()
    prefixes = set(re.findall(r'let prefix = "((?:quest|QUEST)_\w*)"', text))
    names = set(re.findall(r'"((?:quest|QUEST)_\w+)"', text)) - prefixes
    return names, prefixes


class WasmExternalsTest(unittest.TestCase):
    def test_every_external_is_compiled_or_lacking(self) -> None:
        names, prefixes = table_symbols()

        def compiled(symbol: str) -> bool:
            # an exception value is the base's, by its name, and a wasm. symbol,
            # in a module's wasm variant, is one of the backend's intrinsics
            return (symbol in names or symbol.startswith("(&quest_exc_") or symbol.startswith("wasm.")
                    or any(symbol.startswith(p) for p in prefixes))

        symbols = library_externals()
        missed = sorted(s for s in symbols if not compiled(s) and s not in LACKING)
        self.assertEqual(missed, [], "externals of lib/ the wasm backend's table neither compiles nor lists as lacking")
        learned = sorted(s for s in LACKING if compiled(s))
        self.assertEqual(learned, [], "externals the table now compiles, to take off LACKING")
        stale = sorted(s for s in LACKING if s not in symbols)
        self.assertEqual(stale, [], "LACKING names externals lib/ no longer binds")


if __name__ == "__main__":
    unittest.main()
