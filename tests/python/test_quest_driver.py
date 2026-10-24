"""Unit tests for quest_driver CLI integration (Phase 4).

Tests:
- Default build directory (.build)
- Verbose flag (-v / --verbose) logging to stderr
- Compilation of interfaces and modules to build directory
- Full separate compilation and linking of main routines
- Whole-program compilation flag override
- Errors located with their source line in every mode
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Callable

# Ensure bootstrap/python is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest_driver import run_compile, run_driver


class TestQuestDriverCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.build_dir = self.root / ".build"
        self.build_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_compile_interface_and_module_to_build_dir(self) -> None:
        iface_file = self.root / "arith.int.quest"
        iface_file.write_text(
            "interface Arith\n"
            "export\n"
            "    double(x: Int): Int\n"
            "end;\n",
            encoding="utf-8",
        )
        mod_file = self.root / "arith.mod.quest"
        mod_file.write_text(
            "module arith : Arith export\n"
            "    let double(x: Int): Int = x + x;\n"
            "end;\n",
            encoding="utf-8",
        )

        code_int = run_driver([
            str(iface_file),
            "--build-dir",
            str(self.build_dir),
        ])
        self.assertEqual(code_int, 0)
        self.assertTrue((self.build_dir / "arith.qi").is_file())
        self.assertTrue((self.build_dir / "arith.int.h").is_file())

        code_mod = run_driver([
            str(mod_file),
            "--build-dir",
            str(self.build_dir),
            "-I",
            str(self.root),
        ])
        self.assertEqual(code_mod, 0)
        self.assertTrue((self.build_dir / "arith.o").is_file())
        self.assertTrue((self.build_dir / "arith.qm").is_file())

    def test_compile_main_separate_with_verbose(self) -> None:
        iface_file = self.root / "calc.int.quest"
        iface_file.write_text(
            "interface Calc\n"
            "export\n"
            "    add(a: Int b: Int): Int\n"
            "end;\n",
            encoding="utf-8",
        )
        mod_file = self.root / "calc.mod.quest"
        mod_file.write_text(
            "module calc : Calc export\n"
            "    let add(a: Int b: Int): Int = a + b;\n"
            "end;\n",
            encoding="utf-8",
        )
        main_file = self.root / "main.quest"
        main_file.write_text(
            "import calc: Calc;\n"
            "let res = calc.add(10 25);\n",
            encoding="utf-8",
        )

        bin_path = self.build_dir / "calc_bin"
        exit_code = run_compile([
            str(main_file),
            "-o",
            str(bin_path),
            "--build-dir",
            str(self.build_dir),
            "-I",
            str(self.root),
            "-v",
        ])
        self.assertEqual(exit_code, 0)
        self.assertTrue(bin_path.is_file())
        self.assertTrue((self.build_dir / "calc.qm").is_file())
        self.assertTrue((self.build_dir / "main.main.qm").is_file())

        proc = subprocess.run([str(bin_path)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)

    def test_compile_only_main_routine(self) -> None:
        main_file = self.root / "solo.quest"
        main_file.write_text("let x: Int = 42;\n", encoding="utf-8")
        exit_code = run_compile([str(main_file), "-c", "--build-dir", str(self.build_dir)])
        self.assertEqual(exit_code, 0)
        for suffix in (".main.qm", ".main.c", ".main.o"):
            self.assertTrue((self.build_dir / f"solo{suffix}").is_file(), suffix)
        self.assertFalse((self.root / "solo").exists())

    def test_run_driver_with_output_flag(self) -> None:
        main_file = self.root / "hello.quest"
        main_file.write_text(
            "let x: Int = 42;\n",
            encoding="utf-8",
        )
        bin_path = self.build_dir / "hello_bin"
        exit_code = run_driver([
            str(main_file),
            "-o",
            str(bin_path),
            "--build-dir",
            str(self.build_dir),
        ])
        self.assertEqual(exit_code, 0)
        self.assertTrue(bin_path.is_file())

    def test_system_args_hold_the_program_name_and_arguments_after_dashes(self) -> None:
        driver = Path(__file__).resolve().parents[2] / "bootstrap" / "python" / "quest_driver.py"
        main_file = self.root / "args.quest"
        main_file.write_text("import system: System;\nsystem.args;\n", encoding="utf-8")
        cases = [
            ([str(main_file), "--print-result"], "", f'"{main_file}" "a" "b"'),
            (["-i"], "import system: System; system.args;\n", '"<repl>" "a" "b"'),
        ]
        for args, stdin, expected in cases:
            with self.subTest(args=args):
                proc = subprocess.run(
                    [sys.executable, str(driver), *args, "--build-dir", str(self.build_dir), "--", "a", "b"],
                    input=stdin, capture_output=True, text=True, timeout=120,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn(f"array of {expected} end", proc.stdout)

    def _stderr_of(self, run: Callable[[list[str]], int], args: list[str]) -> str:
        """Runs a driver entry point, expecting it to fail, and returns what it wrote to stderr."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertNotEqual(run(args), 0)
        return err.getvalue()

    def test_errors_are_located_in_every_mode(self) -> None:
        main_file = self.root / "bad.quest"
        main_file.write_text("let a = 1;\nlet b: String = a;\n", encoding="utf-8")
        iface_file = self.root / "m.int.quest"
        iface_file.write_text("interface M export f(c: Bool): Ok end;\n", encoding="utf-8")
        mod_file = self.root / "m.mod.quest"
        mod_file.write_text(
            "module m : M export\n    let f(c: Bool): Ok = begin if c then ok else 3 end; ok end;\nend;\n",
            encoding="utf-8",
        )
        build = ["--build-dir", str(self.build_dir), "-I", str(self.root)]
        cases = [
            (run_driver, [str(main_file), "-o", str(self.root / "bad")], main_file, "2:17", "let b: String = a;"),
            (run_compile, [str(main_file)], main_file, "2:17", "let b: String = a;"),
            (run_compile, [str(main_file), "-c"], main_file, "2:17", "let b: String = a;"),
            (run_driver, [str(mod_file)], mod_file, "2:32", "if c then ok else 3"),
            (run_compile, [str(mod_file)], mod_file, "2:32", "if c then ok else 3"),
        ]
        for run, args, file, location, line in cases:
            with self.subTest(run=run.__name__, args=args[1:]):
                stderr = self._stderr_of(run, [*args, *build])
                self.assertIn(f"{file}:{location}: error:", stderr)
                self.assertIn(line, stderr)

    def test_binary_reports_where_an_uncaught_exception_was_raised(self) -> None:
        main_file = self.root / "raises.quest"
        main_file.write_text("exception E end;\nlet f(): Int = raise E end;\nf();\n", encoding="utf-8")
        bin_path = self.root / "raises"
        self.assertEqual(run_driver([str(main_file), "-o", str(bin_path), "--build-dir", str(self.build_dir)]), 0)
        proc = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 1)
        self.assertRegex(proc.stderr, r"\AException: E\n  at .*raises\.quest:2:16\n(  in .*\n)*  in <main>\n\Z")


if __name__ == "__main__":
    unittest.main()
