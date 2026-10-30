"""The arm64 backend's assembly (questlang/codegen/arm64, docs/arm64.md section 3.11) assembles: the questlang test
arm64_assemble prints a unit of the SSA built by hand as assembly, and this test assembles its golden with clang -c,
as a unit's .s is, and checks the symbols the object defines and refers to."""

from __future__ import annotations

from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "bootstrap" / "python"))

from quest.codegen.c.compiler_runner import find_c_compiler

GOLDEN = ROOT / "tests" / "golden" / "run" / "questlang" / "arm64_assemble.out"


@unittest.skipUnless(sys.platform == "darwin" and platform.machine() == "arm64", "Darwin arm64 assembly")
class TestArm64(unittest.TestCase):
    def assemble(self, source: str) -> tuple[subprocess.CompletedProcess, dict[str, str]]:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "unit.s"
            obj = Path(tmp) / "unit.o"
            src.write_text(source)
            result = subprocess.run([find_c_compiler(), "-c", str(src), "-o", str(obj)],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            symbols: dict[str, str] = {}
            if result.returncode == 0:
                for line in subprocess.run(["nm", str(obj)], stdout=subprocess.PIPE, text=True).stdout.splitlines():
                    fields = line.split()
                    symbols[fields[-1]] = fields[-2]
            return result, symbols

    def test_the_golden_assembles(self) -> None:
        result, symbols = self.assemble(GOLDEN.read_text())
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout, "")
        # Exported functions and data are global, the rest local
        self.assertEqual(symbols["_qv_test_swap"], "T")
        self.assertEqual(symbols["_main"], "T")
        self.assertEqual(symbols["_qv_mod_test_record"], "D")
        for name in ("_qf_many", "_qf_caller", "_qf_memory", "_qf_try"):
            self.assertEqual(symbols[name], "t")
        self.assertEqual(symbols["_qr_table"], "s")
        for name in ("__setjmp", "_quest_pop_handler", "_quest_current_exception_handler", "_quest_type_Int"):
            self.assertEqual(symbols[name], "U")

    def test_conventions(self) -> None:
        text = GOLDEN.read_text()
        # Every function has a frame record, and unwind information
        self.assertEqual(text.count("stp x29, x30, [sp, #-16]!"), text.count(".cfi_startproc"))
        self.assertEqual(text.count(".cfi_startproc"), text.count(".cfi_endproc"))
        # A thread-local through its descriptor, an undefined symbol through the GOT
        self.assertIn("_quest_current_exception_handler@TLVPPAGE", text)
        self.assertIn("_quest_type_Int+48", text)
        self.assertIn("ldr x9, [x9, _quest_type_Int@GOTPAGEOFF]", text)
        # The narrow arguments are packed on the stack, a byte each
        self.assertTrue(re.search(r"strb w9, \[sp, #40\]\n.*\n\tstrb w9, \[sp, #41\]", text), text)
        self.assertIn("ldrb w9, [x29, #57]", text)

    def test_a_malformed_unit_fails(self) -> None:
        # The check can fail: an unknown instruction does not assemble
        result, _ = self.assemble(GOLDEN.read_text().replace("\tmov x29, sp\n", "\tmov x29, spx\n", 1))
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
