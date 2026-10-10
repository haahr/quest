"""Unit tests for Quest Module & Interface File Loader (module_loader.py).

Tests:
- Search of -I include paths, and the current directory's precedence over them
- Strict validation: single definition, name matching, interface conformance
- Circular dependency detection
- Errors in imported units located in their own files

Programs importing units beside them are golden tests in tests/source/modules: case normalization in file search
(capitalized_unit_names), interfaces importing interfaces (interface_imports_interface), and modules shared by their
importers (diamond_dependency).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure bootstrap/python is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.diagnostics import QuestTypeError
from quest.env import Environment
from quest.interpreter import RuntimeEnvironment
from quest.pipeline import CompilerContext, CompilerOptions, default_pipeline
from quest.runtime import QInt, QOk, QRecord, QString


class TestModuleFileImports(unittest.TestCase):
    """Tests for file-based module and interface imports."""

    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.temp_dir_obj.name)
        self.pipeline = default_pipeline()

    def tearDown(self):
        self.temp_dir_obj.cleanup()

    def _write_file(self, filename: str, content: str, directory: Path | None = None) -> Path:
        target_dir = directory or self.temp_dir
        path = target_dir / filename
        path.write_text(content.strip() + "\n", encoding="utf-8")
        return path

    def _run_pipeline(self, file_path: Path, options: CompilerOptions | None = None):
        source_text = file_path.read_text(encoding="utf-8")
        ctx = CompilerContext.create(source_text, file_name=str(file_path), options=options)
        res = self.pipeline.execute(source_text, file_name=str(file_path), options=options, ctx=ctx)
        return res, ctx

    def test_include_path_search(self):
        """Tests that files in -I directories are found when not in current dir."""
        lib_dir = self.temp_dir / "lib"
        lib_dir.mkdir()

        self._write_file(
            "greeter.int.quest",
            """
            interface Greeter
            export
                greet(name: String): String
            end;
            """,
            directory=lib_dir,
        )

        self._write_file(
            "greeter.mod.quest",
            """
            module greeter : Greeter
            export
                let greet(name: String): String = "Hello " <> name;
            end;
            """,
            directory=lib_dir,
        )

        app_dir = self.temp_dir / "app"
        app_dir.mkdir()
        main_quest = self._write_file(
            "main.quest",
            """
            import greeter: Greeter;
            let msg = greeter.greet("World");
            """,
            directory=app_dir,
        )

        options = CompilerOptions(include_paths=[lib_dir])
        res, ctx = self._run_pipeline(main_quest, options=options)
        self.assertTrue(res.success, f"Pipeline failed: {res.diagnostics}")
        self.assertEqual(ctx.runtime_env.lookup("msg"), QString("Hello World"))

    def test_current_directory_precedence_over_include_path(self):
        """Tests that active file directory shadows files in -I include paths."""
        inc_dir = self.temp_dir / "inc"
        inc_dir.mkdir()

        self._write_file(
            "config.int.quest",
            """
            interface Config
            export
                value: Int
            end;
            """,
            directory=inc_dir,
        )
        self._write_file(
            "config.mod.quest",
            """
            module config : Config
            export
                let value = 100;
            end;
            """,
            directory=inc_dir,
        )

        app_dir = self.temp_dir / "app"
        app_dir.mkdir()
        self._write_file(
            "config.int.quest",
            """
            interface Config
            export
                value: Int
            end;
            """,
            directory=app_dir,
        )
        self._write_file(
            "config.mod.quest",
            """
            module config : Config
            export
                let value = 999;
            end;
            """,
            directory=app_dir,
        )

        main_quest = self._write_file(
            "main.quest",
            """
            import config: Config;
            let v = config.value;
            """,
            directory=app_dir,
        )

        options = CompilerOptions(include_paths=[inc_dir])
        res, ctx = self._run_pipeline(main_quest, options=options)
        self.assertTrue(res.success, f"Pipeline failed: {res.diagnostics}")
        self.assertEqual(ctx.runtime_env.lookup("v"), QInt(999))

    def test_missing_interface_file_raises_error(self):
        """Tests that referencing a nonexistent interface raises QuestTypeError."""
        main_quest = self._write_file(
            "main.quest",
            """
            import foo: NonExistentIface;
            """,
        )
        res, _ = self._run_pipeline(main_quest)
        self.assertFalse(res.success)
        self.assertTrue(any("cannot find interface file for 'NonExistentIface'" in d.message for d in res.diagnostics))

    def test_missing_module_file_raises_error(self):
        """Tests that referencing a nonexistent module raises QuestTypeError."""
        self._write_file(
            "dummy.int.quest",
            """
            interface Dummy
            export
                x: Int
            end;
            """,
        )
        main_quest = self._write_file(
            "main.quest",
            """
            import missingMod: Dummy;
            """,
        )
        res, _ = self._run_pipeline(main_quest)
        self.assertFalse(res.success)
        self.assertTrue(any("cannot find module file for 'missingMod'" in d.message for d in res.diagnostics))

    def test_multiple_phrases_in_interface_file_rejected(self):
        """Tests that an interface file with more than one top-level phrase is rejected."""
        self._write_file(
            "bad.int.quest",
            """
            let x = 1;
            interface Bad
            export
                y: Int
            end;
            """,
        )
        main_quest = self._write_file(
            "main.quest",
            """
            import : Bad;
            """,
        )
        res, _ = self._run_pipeline(main_quest)
        self.assertFalse(res.success)
        self.assertTrue(any("must contain only a single interface declaration" in d.message for d in res.diagnostics))

    def test_non_interface_in_interface_file_rejected(self):
        """Tests that a .int.quest containing a non-interface phrase is rejected."""
        self._write_file(
            "notiface.int.quest",
            """
            let x = 1;
            """,
        )
        main_quest = self._write_file(
            "main.quest",
            """
            import : NotIface;
            """,
        )
        res, _ = self._run_pipeline(main_quest)
        self.assertFalse(res.success)
        self.assertTrue(any("Expected interface declaration" in d.message for d in res.diagnostics))

    def test_interface_name_mismatch_rejected(self):
        """Tests that an interface whose declared name doesn't match filename is rejected."""
        self._write_file(
            "mismatch.int.quest",
            """
            interface ActualName
            export
                x: Int
            end;
            """,
        )
        main_quest = self._write_file(
            "main.quest",
            """
            import : Mismatch;
            """,
        )
        res, _ = self._run_pipeline(main_quest)
        self.assertFalse(res.success)
        self.assertTrue(any("which does not match file name" in d.message for d in res.diagnostics))

    def test_module_name_mismatch_rejected(self):
        """Tests that a module whose declared name doesn't match filename is rejected."""
        self._write_file(
            "iface.int.quest",
            """
            interface Iface
            export
                x: Int
            end;
            """,
        )
        self._write_file(
            "modname.mod.quest",
            """
            module DifferentName : Iface
            export
                let x = 10;
            end;
            """,
        )
        main_quest = self._write_file(
            "main.quest",
            """
            import modname: Iface;
            """,
        )
        res, _ = self._run_pipeline(main_quest)
        self.assertFalse(res.success)
        self.assertTrue(any("which does not match file name" in d.message for d in res.diagnostics))

    def test_module_interface_mismatch_rejected(self):
        """Tests that a module implementing a different interface than expected is rejected."""
        self._write_file(
            "iface1.int.quest",
            """
            interface Iface1
            export
                x: Int
            end;
            """,
        )
        self._write_file(
            "iface2.int.quest",
            """
            interface Iface2
            export
                y: Int
            end;
            """,
        )
        self._write_file(
            "m.mod.quest",
            """
            module m : Iface1
            export
                let x = 1;
            end;
            """,
        )
        main_quest = self._write_file(
            "main.quest",
            """
            import m: Iface2;
            """,
        )
        res, _ = self._run_pipeline(main_quest)
        self.assertFalse(res.success)
        self.assertTrue(any("expected 'Iface2'" in d.message for d in res.diagnostics))

    def test_circular_interface_dependency_detected(self):
        """Tests that a cycle in interface imports is detected."""
        self._write_file(
            "cyca.int.quest",
            """
            interface CycA
            import : CycB
            export
                x: Int
            end;
            """,
        )
        self._write_file(
            "cycb.int.quest",
            """
            interface CycB
            import : CycA
            export
                y: Int
            end;
            """,
        )
        main_quest = self._write_file(
            "main.quest",
            """
            import : CycA;
            """,
        )
        res, _ = self._run_pipeline(main_quest)
        self.assertFalse(res.success)
        self.assertTrue(any("Cyclic dependency detected in interface imports" in d.message for d in res.diagnostics))

    def test_circular_module_dependency_detected(self):
        """Tests that a cycle in module imports is detected."""
        self._write_file(
            "modia.int.quest",
            """
            interface ModIA
            export
                a(dummy: Ok): Int
            end;
            """,
        )
        self._write_file(
            "modib.int.quest",
            """
            interface ModIB
            export
                b(dummy: Ok): Int
            end;
            """,
        )
        self._write_file(
            "modma.mod.quest",
            """
            module modma : ModIA
            import modmb: ModIB
            export
                let a(dummy: Ok): Int = modmb.b(ok);
            end;
            """,
        )
        self._write_file(
            "modmb.mod.quest",
            """
            module modmb : ModIB
            import modma: ModIA
            export
                let b(dummy: Ok): Int = modma.a(ok);
            end;
            """,
        )
        main_quest = self._write_file(
            "main.quest",
            """
            import modma: ModIA;
            """,
        )
        res, _ = self._run_pipeline(main_quest)
        self.assertFalse(res.success)
        self.assertTrue(any("Cyclic dependency detected in module imports" in d.message for d in res.diagnostics))


class TestDiagnosticsInImportedUnits(unittest.TestCase):
    """An error in an imported unit is reported in the unit's own file, in every phase (docs/diagnostics.md §4.4).

    Error tests cover typecheck; this covers C compilation, where a module's body is compiled only when the program
    is linked, which no error test reaches (its typecheck precursor reports the error first).
    """

    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.temp_dir_obj.name)
        (self.temp_dir / "cnt.int.quest").write_text("interface Cnt\nexport\n    get(): Int\nend;\n")
        (self.temp_dir / "cnt.mod.quest").write_text(
            'module cnt : Cnt\nexport\n\n    let get(): Int = "oops";\nend;\n'
        )
        (self.temp_dir / "usecnt.quest").write_text("import cnt: Cnt;\ncnt.get();\n")

    def tearDown(self):
        self.temp_dir_obj.cleanup()

    def _driver_stderr(self, phase: str) -> str:
        import subprocess
        root = Path(__file__).resolve().parent.parent.parent
        env = dict(os.environ, PYTHONPATH=str(root / "bootstrap" / "python"))
        proc = subprocess.run(
            [
                sys.executable, str(root / "bootstrap" / "python" / "quest_driver.py"),
                "--stop-after", phase, "--build-dir", str(self.temp_dir / "build"), "usecnt.quest",
            ],
            cwd=self.temp_dir, env=env, capture_output=True, text=True,
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        return proc.stderr

    def test_module_body_error_is_located_in_the_module(self):
        for phase in ("typecheck", "run_c_compiled"):
            with self.subTest(phase=phase):
                stderr = self._driver_stderr(phase)
                self.assertIn("cnt.mod.quest:4:22: error: Type mismatch", stderr)
                self.assertIn('let get(): Int = "oops";', stderr)
                self.assertNotIn("Traceback", stderr)

    def test_import_that_loaded_the_unit_is_noted(self):
        stderr = self._driver_stderr("typecheck")
        self.assertIn("::: usecnt.quest:1:11", stderr)
        self.assertIn("note: imported here", stderr)


if __name__ == "__main__":
    unittest.main()
