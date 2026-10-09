"""Artifacts record the ABI version, and only fresh artifacts with the current version are reused."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.build.abi import ABI_VERSION, PRODUCER, recorded_abi
from quest.build.engine import BuildEngine, BuildError
from quest.diagnostics import QuestTypeError
from quest.env import Environment
from quest.interface_compiler import compile_interface_file, ensure_interface_artifacts, load_interface_from_qi_file
from quest.module_compiler import compile_module_file
from quest.module_loader import resolve_interface_file

CALC_INT = "interface Calc export add(a: Int b: Int): Int end;\n"
CALC_MOD = "module calc : Calc export let add(a: Int b: Int): Int = a + b; end;\n"
APP = (
    "import c = calc : Calc;\n"
    "import writer: Writer;\n"
    "import conv: Conv;\n"
    "writer.putString(writer.output conv.int(c.add(40 2)));\n"
)


def _set_recorded_abi(artifact: Path, abi: int) -> None:
    data = json.loads(artifact.read_text(encoding="utf-8"))
    (data["value"] if "value" in data else data)["abi"] = abi
    artifact.write_text(json.dumps(data), encoding="utf-8")


class TestAbiVersion(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.build_dir = self.root / ".build"
        (self.root / "calc.int.quest").write_text(CALC_INT, encoding="utf-8")
        (self.root / "calc.mod.quest").write_text(CALC_MOD, encoding="utf-8")
        (self.root / "app.quest").write_text(APP, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_artifacts_record_abi_and_producer(self) -> None:
        h_file, qi_file = compile_interface_file(self.root / "calc.int.quest", output_dir=self.root)
        self.assertEqual(recorded_abi(qi_file), ABI_VERSION)
        self.assertEqual(json.loads(qi_file.read_text(encoding="utf-8"))["value"]["producer"], PRODUCER)
        self.assertTrue(h_file.read_text(encoding="utf-8").startswith(f"/* quest abi {ABI_VERSION} producer"))
        compile_module_file(self.root / "calc.mod.quest", output_dir=self.root, include_paths=[self.root])
        qm = json.loads((self.root / "calc.qm").read_text(encoding="utf-8"))
        self.assertEqual((qm["abi"], qm["producer"]), (ABI_VERSION, PRODUCER))

    def test_interface_with_other_abi_is_rebuilt(self) -> None:
        qi_file, _, _ = ensure_interface_artifacts("Calc", self.root, [self.root], self.build_dir)
        _set_recorded_abi(qi_file, ABI_VERSION + 1)
        time.sleep(0.01)
        qi_file, _, _ = ensure_interface_artifacts("Calc", self.root, [self.root], self.build_dir)
        self.assertEqual(recorded_abi(qi_file), ABI_VERSION)

    def test_precompiled_interface_with_other_abi_is_an_error(self) -> None:
        _, qi_file = compile_interface_file(self.root / "calc.int.quest", output_dir=self.root)
        (self.root / "calc.int.quest").unlink()
        _set_recorded_abi(qi_file, ABI_VERSION + 1)
        with self.assertRaises(QuestTypeError):
            ensure_interface_artifacts("Calc", self.root, [self.root], self.build_dir)
        with self.assertRaises(QuestTypeError):
            load_interface_from_qi_file(qi_file, Environment())

    def test_fresh_qi_is_preferred_to_source_only_with_current_abi(self) -> None:
        source = (self.root / "calc.int.quest").resolve()
        self.assertEqual(resolve_interface_file("Calc", self.root, []), source)
        time.sleep(0.01)
        _, qi_file = compile_interface_file(self.root / "calc.int.quest", output_dir=self.root)
        self.assertEqual(resolve_interface_file("Calc", self.root, []), qi_file.resolve())
        _set_recorded_abi(qi_file, ABI_VERSION + 1)
        self.assertEqual(resolve_interface_file("Calc", self.root, []), source)

    def _engine(self) -> BuildEngine:
        return BuildEngine(build_dir=self.build_dir, include_paths=[self.root], log_file=self.build_dir / "build.log")

    def test_module_with_other_abi_is_recompiled(self) -> None:
        self.assertIn("calc", self._engine().build_main(self.root / "app.quest").compiled_units)
        self.assertNotIn("calc", self._engine().build_main(self.root / "app.quest").compiled_units)
        _set_recorded_abi(self.build_dir / "calc.qm", ABI_VERSION + 1)
        self.assertIn("calc", self._engine().build_main(self.root / "app.quest").compiled_units)

    def test_fresh_artifacts_next_to_the_source_are_used(self) -> None:
        compile_interface_file(self.root / "calc.int.quest", output_dir=self.root)
        compile_module_file(self.root / "calc.mod.quest", output_dir=self.root, include_paths=[self.root])
        res = self._engine().build_main(self.root / "app.quest")
        self.assertNotIn("calc", res.compiled_units)
        self.assertFalse((self.build_dir / "calc.o").exists())

    def test_precompiled_module_with_other_abi_is_an_error(self) -> None:
        compile_interface_file(self.root / "calc.int.quest", output_dir=self.root)
        compile_module_file(self.root / "calc.mod.quest", output_dir=self.root, include_paths=[self.root])
        (self.root / "calc.mod.quest").unlink()
        _set_recorded_abi(self.root / "calc.qm", ABI_VERSION + 1)
        with self.assertRaises(BuildError):
            self._engine().build_main(self.root / "app.quest")


if __name__ == "__main__":
    unittest.main()
