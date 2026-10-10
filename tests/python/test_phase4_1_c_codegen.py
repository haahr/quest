"""Tests of C compilation that golden tests cannot express: the compile pipeline's phases, --nogc, and the
`quest compile` command. The programs of Phase 4.1 are golden tests (language/c_codegen_basics)."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from quest.codegen import compile_c_source, run_binary
from quest.pipeline import CompilerOptions, compile_pipeline
from quest_driver import run_driver


class TestPhase41Codegen(unittest.TestCase):
    """Tests C emitter, runtime foundation, host compilation, and CLI driver."""

    def compile_quest(self, code: str, nogc: bool = False) -> subprocess.CompletedProcess[str]:
        """Helper to compile Quest code snippet to binary and run it."""
        pipeline = compile_pipeline()
        res = pipeline.execute(code, "<test>")
        self.assertTrue(res.success, f"Pipeline failed: {res.diagnostics}")
        c_code = res.artifacts.get("codegen_c")
        self.assertIsNotNone(c_code)

        with tempfile.NamedTemporaryFile(suffix="", delete=False) as f:
            bin_path = Path(f.name)

        try:
            compile_c_source(c_code, output_path=bin_path, nogc=nogc)
            proc = run_binary(bin_path)
            return proc
        finally:
            if bin_path.exists():
                bin_path.unlink()

    def test_pipeline_phases(self):
        """Verifies compile_pipeline registers the expected phases."""
        p = compile_pipeline()
        self.assertEqual(p.phase_names(), ["tokenize", "parse", "typecheck", "codegen_c"])

    def test_nogc_compilation(self):
        """Compiles and runs strings, functions, closures, and arrays with --nogc (the same programs without it are
        golden tests, such as language/c_codegen_basics, which have no directive for compiler flags)."""
        code = """
        let greeting = "Quest " <> "C Backend";
        let f(x: Int): Int = x + 10;
        let makeAdder(x: Int)(y: Int): Int = x + y;
        let add10 = makeAdder(10);
        let arr = array of 1 2 3 end;
        tuple greeting f(5) add10(5) arr[1] end
        """
        proc = self.compile_quest(code, nogc=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('tuple "Quest C Backend" 15 15 2 end', proc.stdout)

    def test_cli_driver_compile_and_run(self):
        """Tests quest compile CLI end-to-end."""
        with tempfile.NamedTemporaryFile(suffix=".quest", mode="w", delete=False) as src_f:
            src_f.write("let x = 123; x\n")
            src_path = Path(src_f.name)

        bin_path = src_path.with_suffix(".bin")

        try:
            exit_code = run_driver([
                "compile", str(src_path), "-o", str(bin_path), "--build-dir", str(src_path.with_suffix(".build")),
            ])
            self.assertEqual(exit_code, 0)
            self.assertTrue(bin_path.exists())

            proc = run_binary(bin_path)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("123 : Int", proc.stdout)
        finally:
            shutil.rmtree(src_path.with_suffix(".build"), ignore_errors=True)
            if src_path.exists():
                src_path.unlink()
            if bin_path.exists():
                bin_path.unlink()


if __name__ == "__main__":
    unittest.main()
