"""Tests for Phase 4.11: Unified Native Module Mechanism, External Syntax, and Hybrid Modules."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure bootstrap/python is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.codegen import compile_c_source, run_binary
from quest.pipeline import CompilerContext, CompilerOptions, compile_pipeline


class TestPhase411NativeModules(unittest.TestCase):
    """Tests native module integration, external types and values, and hybrid Quest/C modules."""

    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.temp_dir_obj.name)
        self.pipeline = compile_pipeline()

    def tearDown(self):
        self.temp_dir_obj.cleanup()

    def _write_file(self, filename: str, content: str) -> Path:
        p = self.temp_dir / filename
        p.write_text(content.strip() + "\n", encoding="utf-8")
        return p

    def _compile_and_run(
        self, main_path: Path, include_paths: list[Path] | None = None
    ) -> subprocess.CompletedProcess[str]:
        source_text = main_path.read_text(encoding="utf-8")
        opts = CompilerOptions(
            include_paths=include_paths or [self.temp_dir],
            echo=True,
        )
        ctx = CompilerContext.create(source_text, file_name=str(main_path), options=opts)
        res = self.pipeline.execute(source_text, file_name=str(main_path), options=opts, ctx=ctx)
        self.assertTrue(res.success, f"Compilation failed: {res.diagnostics}")
        c_code = res.artifacts.get("codegen_c")
        self.assertIsNotNone(c_code)

        with tempfile.NamedTemporaryFile(suffix="", delete=False) as f:
            bin_path = Path(f.name)

        try:
            compile_c_source(c_code, output_path=bin_path, nogc=False)
            proc = run_binary(bin_path)
            return proc
        finally:
            if bin_path.exists():
                bin_path.unlink()

    def test_external_value_compilation(self):
        """Tests that external value bindings correctly link to C runtime symbols/constants."""
        main_file = self._write_file(
            "main.quest",
            """
            let maxVal: Int = external "QUEST_INT_MAX";
            let minVal: Int = external "QUEST_INT_MIN";
            let gt = maxVal > 0;
            let lt = minVal < 0;
            let res = gt andif {lt};
            res
            """,
        )
        proc = self._compile_and_run(main_file)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("true : Bool", proc.stdout)





if __name__ == "__main__":
    unittest.main()
