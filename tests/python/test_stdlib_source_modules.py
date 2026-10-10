"""Integration tests for standard library source modules loaded from lib/.

Verifies that standard library interfaces and modules are loaded directly from
Quest source files (.int.quest and .mod.quest) in lib/. Programs using them are
golden tests (such as stdlib/core_library_modules), run in the interpreter and C.
"""

from __future__ import annotations

import unittest

from quest.env import Environment
from quest.module_loader import (
    DEFAULT_LIB_DIR,
    load_interface,
    load_module,
    resolve_interface_file,
    resolve_module_file,
)


class TestStdlibSourceModules(unittest.TestCase):
    """Test suite verifying standard library loading and execution from lib/ source files."""

    def test_disk_file_resolution(self) -> None:
        """Verifies that all standard library interfaces and modules resolve to lib/ files on disk."""
        modules = [
            ("Writer", "writer"),
            ("Reader", "reader"),
            ("Conv", "conv"),
            ("Ascii", "ascii"),
            ("IntOp", "int"),
            ("RealOp", "real"),
            ("StringOp", "string"),
            ("ArrayOp", "arrayop"),
            ("List", "list"),
            ("System", "system"),
            ("Word", "word"),
            ("Dynamic", "dynamic"),
        ]
        for iface_name, mod_name in modules:
            iface_path = resolve_interface_file(iface_name, None, [])
            self.assertIsNotNone(iface_path, f"Failed to resolve interface {iface_name}")
            self.assertTrue(iface_path.is_file())
            self.assertEqual(iface_path.parent, DEFAULT_LIB_DIR.resolve())

            mod_path = resolve_module_file(mod_name, None, [])
            self.assertIsNotNone(mod_path, f"Failed to resolve module {mod_name}")
            self.assertTrue(mod_path.is_file())
            self.assertEqual(mod_path.parent, DEFAULT_LIB_DIR.resolve())

    def test_module_elaboration_from_disk(self) -> None:
        """Verifies that each module in lib/ elaborates against its interface."""
        modules = [
            ("Writer", "writer"),
            ("Reader", "reader"),
            ("Conv", "conv"),
            ("Ascii", "ascii"),
            ("IntOp", "int"),
            ("RealOp", "real"),
            ("StringOp", "string"),
            ("ArrayOp", "arrayop"),
            ("List", "list"),
            ("System", "system"),
            ("Word", "word"),
            ("Dynamic", "dynamic"),
        ]
        for iface_name, mod_name in modules:
            env = Environment()
            iface_scope = load_interface(iface_name, env)
            self.assertIsNotNone(iface_scope, f"Failed to load interface {iface_name}")
            mod = load_module(mod_name, iface_name, env)
            self.assertEqual(mod.name.lower(), mod_name.lower())
            self.assertEqual(mod.interface_name, iface_name)

if __name__ == "__main__":
    unittest.main()

