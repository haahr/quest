"""The SSA's C printer (questlang/codegen/ssac, docs/arm64.md section 3.14) prints C that clang compiles: the questlang
test ssac_print prints a unit of the SSA built by hand, and this test compiles its golden to an object with the flags
the C backend compiles with and those ssac adds (read from ssac's source, so that they cannot drift apart), and checks
that the object defines and refers to the symbols the unit does."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "bootstrap" / "python"))

from quest.codegen.c.compiler_runner import base_c_flags, find_c_compiler

GOLDEN = ROOT / "tests" / "golden" / "run" / "questlang" / "ssac_print.out"
SSAC = ROOT / "questlang" / "codegen" / "ssac.mod.quest"


def ssac_flags() -> list[str]:
    match = re.search(r"let cFlags = array of(.*?)end", SSAC.read_text(), re.S)
    assert match, "no cFlags in ssac"
    return re.findall(r'"([^"]*)"', match.group(1))


class TestSsac(unittest.TestCase):
    def compile(self, source: str) -> tuple[subprocess.CompletedProcess, str]:
        compiler = find_c_compiler()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "unit.c"
            obj = Path(tmp) / "unit.o"
            src.write_text(source)
            result = subprocess.run([compiler, *base_c_flags(compiler), *ssac_flags(), "-c", str(src), "-o", str(obj)],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            symbols = ""
            if result.returncode == 0:
                symbols = subprocess.run(["nm", str(obj)], stdout=subprocess.PIPE, text=True).stdout
            return result, symbols

    def test_the_flags(self) -> None:
        flags = ssac_flags()
        for flag in ("-fno-strict-aliasing", "-fno-builtin", "-std=gnu11"):
            self.assertIn(flag, flags)

    def test_the_golden_compiles(self) -> None:
        result, symbols = self.compile(GOLDEN.read_text())
        self.assertEqual(result.returncode, 0, result.stdout)
        # Without warnings, as a unit's C is compiled
        self.assertNotIn("warning", result.stdout)
        defined = {line.split()[-1] for line in symbols.splitlines() if re.search(r" [TDS] ", line)}
        undefined = {line.split()[-1] for line in symbols.splitlines() if re.search(r" U ", line)}
        # Exported functions and data are global, the rest local
        self.assertIn("_qv_test_swap", defined)
        self.assertIn("_qv_mod_test_record", {line.split()[-1] for line in symbols.splitlines()
                                               if re.search(r" [CSDB] ", line)})
        self.assertIn("_main", defined)
        # What main reaches refers to the runtime (clang drops the static
        # functions and data nothing reaches)
        for name in ("_quest_pop_handler", "_quest_gc_init", "_quest_current_exception_handler", "__setjmp"):
            self.assertIn(name, undefined)

    def test_a_malformed_unit_fails(self) -> None:
        # The check can fail: a call of an undeclared symbol does not compile
        result, _ = self.compile(GOLDEN.read_text().replace("extern char quest_gc_init[];\n", ""))
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
