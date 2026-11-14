"""The wasm backend's table of the library's externals covers lib/ (docs/wasm-plan.md
section 4.2 and step 9): every external value and function a module of lib/
binds names a C symbol that questlang/wasm/codegen compiles, by name, or is one
this target lacks for now, listed here with what it waits for. A symbol on
neither list is one a change to lib/ added and the table missed; one on both
is one the table has since learned, to take off LACKING.

    python -m unittest tests.python.test_wasm_externals
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CODEGEN = ROOT / "questlang" / "wasm" / "codegen.mod.quest"

# The externals the table compiles to a failure when called, by what they wait for
LACKING = {
    # The mathematical functions, ported to Quest in milestone 4 (section 4.3)
    "quest_real_acos", "quest_real_asin", "quest_real_atan", "quest_real_atan2", "quest_real_cos",
    "quest_real_cosh", "quest_real_exp", "quest_real_exponential", "quest_real_log", "quest_real_sin",
    "quest_real_sinh", "quest_real_tan", "quest_real_tanh",
    # real.format's printf styles, the rest of step 8
    "quest_real_format",
    # dynamic's serialization, milestone 4
    "quest_dynamic_copy", "quest_dynamic_extern", "quest_dynamic_intern",
}

EXTERNAL = re.compile(r'\blet\s+\w+[^=]*=\s*external\s+"([^"]+)"')


def library_externals() -> set[str]:
    symbols = set()
    for path in (ROOT / "lib").rglob("*.mod.quest"):
        symbols.update(EXTERNAL.findall(path.read_text()))
    return symbols


def table_symbols() -> tuple[set[str], set[str]]:
    """The symbols the table names, and the prefixes it handles whole"""
    text = CODEGEN.read_text()
    names = set(re.findall(r'"((?:quest|QUEST)_\w+)"', text))
    prefixes = set(re.findall(r'strutil\.startsWith\(symbol "((?:quest|QUEST)_\w*)"\)', text))
    return names, prefixes


class WasmExternalsTest(unittest.TestCase):
    def test_every_external_is_compiled_or_lacking(self) -> None:
        names, prefixes = table_symbols()

        def compiled(symbol: str) -> bool:
            # an exception value is the base's, by its name
            return (symbol in names or symbol.startswith("(&quest_exc_")
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
