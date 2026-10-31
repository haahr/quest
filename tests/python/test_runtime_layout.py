"""The self-hosted compiler's tables of the runtime's layouts (questlang/codegen/runtimeLayout, docs/arm64.md section 3.3)
and functions (questlang/codegen/runtimeFunctions, docs/backend-improvements.md section 3.5) agree with
runtime/quest_runtime.h: the questlang tests codegen_runtime_layout and codegen_runtime_functions print the tables as C
assertions, and this test compiles their goldens against the header. A change to either that the other does not follow
fails here (and a change to a table changes its golden, which its questlang test checks)."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "bootstrap" / "python"))

from quest.codegen.c.compiler_runner import base_c_flags, find_c_compiler, get_runtime_dir

GOLDEN = ROOT / "tests" / "golden" / "run" / "questlang" / "codegen_runtime_layout.out"
FUNCTIONS_GOLDEN = ROOT / "tests" / "golden" / "run" / "questlang" / "codegen_runtime_functions.out"


def compiles(source: str) -> subprocess.CompletedProcess:
    """Whether source, after the header, compiles"""
    compiler = find_c_compiler()
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "check.c"
        src.write_text('#include <stddef.h>\n#include "quest_runtime.h"\n\n' + source)
        return subprocess.run(
            [compiler, *base_c_flags(compiler), "-DQUEST_NOGC", f"-I{get_runtime_dir()}", "-fsyntax-only", str(src)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


class TestRuntimeLayout(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(GOLDEN.exists(), f"missing {GOLDEN}")
        self.assertions = GOLDEN.read_text()

    def test_the_table_covers_what_generated_code_uses(self) -> None:
        for name in ("QClosure", "QArray", "QString", "QExceptionState", "QTypeDescriptor", "QFunTypeDescriptor",
                     "QTupleTypeDescriptor", "QRecordFieldDescriptor", "QVariantCaseDescriptor", "QAuto"):
            self.assertIn(f"sizeof({name}) ==", self.assertions)
        self.assertIn("QTYPE_KIND_STORED == 17", self.assertions)

    def test_the_header_agrees(self) -> None:
        compiler = find_c_compiler()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "layout.c"
            src.write_text('#include <stddef.h>\n#include "quest_runtime.h"\n\n' + self.assertions)
            result = subprocess.run(
                [compiler, *base_c_flags(compiler), "-DQUEST_NOGC", f"-I{get_runtime_dir()}", "-fsyntax-only", str(src)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_wrong_layout_fails(self) -> None:
        # The check can fail: an assertion off by one does not compile
        compiler = find_c_compiler()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "wrong.c"
            src.write_text('#include <stddef.h>\n#include "quest_runtime.h"\n\n'
                           "static_assert(offsetof(QClosure, env) == 9, wrong_QClosure_env);\n")
            result = subprocess.run(
                [compiler, *base_c_flags(compiler), "-DQUEST_NOGC", f"-I{get_runtime_dir()}", "-fsyntax-only", str(src)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.assertNotEqual(result.returncode, 0)


class TestRuntimeFunctions(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(FUNCTIONS_GOLDEN.exists(), f"missing {FUNCTIONS_GOLDEN}")
        self.assertions = FUNCTIONS_GOLDEN.read_text()

    def test_the_table_covers_what_the_builder_calls(self) -> None:
        for name in ("quest_alloc", "quest_convert", "quest_reraise", "quest_record_view", "quest_builtins_init"):
            self.assertIn(f"__typeof__({name})", self.assertions)

    def test_the_header_agrees(self) -> None:
        result = compiles(self.assertions)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_wrong_prototype_fails(self) -> None:
        # The check can fail: a parameter of the wrong type does not compile
        result = compiles("static_assert(__builtin_types_compatible_p(__typeof__(quest_alloc), void * (int)), "
                          "wrong_quest_alloc);\n")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
