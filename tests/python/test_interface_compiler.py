"""Unit tests for Quest Interface Compiler (.int.quest -> .h + .qi).

Verifies Phase 4.16 Step 1:
- Compilation of interfaces with abstract types (erased to QVal in C headers).
- Compilation of manifest types (Def Point = Record ... end).
- Interface dependencies (import : Other) and recursive header inclusions.
- JSON/JSOG serialization parity using shadow Quest record schema.
- Direct loading of Scope from .qi files without .int.quest on disk.
- CLI driver invocation via `quest -c <file>.int.quest`.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from quest.types.env import Environment
from quest.codegen.c.headers import compile_interface_with_header
from quest.modules.interface_compiler import format_type_for_qi, load_interface_from_qi_file
from quest.types import (
    INT_TYPE, TYPE_KIND, QOptionField, QOptionType, QTupleField, QTupleType, QTypeVar, QVariantField,
    QVariantType,
)
from quest.types.model import QTupleTypeBinding, QTupleTypeFormal
from quest.modules.loader import load_interface


class TestInterfaceCompiler(unittest.TestCase):
    """Test suite for interface compilation (.int.quest -> .h and .qi)."""

    def test_tuple_type_components_in_qi_types(self) -> None:
        """A tuple type's type components are written in .qi type syntax (formals and bindings)."""
        a = QTupleTypeFormal("A", 70001, TYPE_KIND)
        x = QTupleField("x", QTypeVar("A", 70001, TYPE_KIND), False)
        t = QTupleType((a, x, QTupleTypeBinding("B", INT_TYPE, None)))
        self.assertEqual(format_type_for_qi(t), "Tuple A::TYPE x: A Let B= Int end")

    def test_mutable_components_in_qi_types(self) -> None:
        """An option's case keeps its payload's var fields and nameless components, and a variant its cases' var
        marks, so that a manifest type read back from a .qi is the one its interface declares."""
        payload = QTupleType((QTupleField("x", INT_TYPE, True), QTupleField(None, INT_TYPE, False)))
        option = QOptionType((QOptionField("a", payload), QOptionField("b", None)))
        self.assertEqual(format_type_for_qi(option), "Option a with var x: Int :Int end b end")
        variant = QVariantType((QVariantField("c", INT_TYPE, True), QVariantField("d", None, False)))
        self.assertEqual(format_type_for_qi(variant), "Variant var c: Int d end")

    def test_compile_simple_interface(self) -> None:
        src = """
interface Counter
export
    T::TYPE
    new(init: Int): T
    inc(c: T): T
    get(c: T): Int
end;
"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "counter.int.quest"
            p.write_text(src, encoding="utf-8")

            h_path, qi_path = compile_interface_with_header(p)
            self.assertTrue(h_path.exists())
            self.assertTrue(qi_path.exists())

            # Verify C header
            h_text = h_path.read_text(encoding="utf-8")
            self.assertIn("#ifndef QUEST_INTF_COUNTER_H", h_text)
            self.assertIn("typedef QVal quest_type_Counter_T;", h_text)
            self.assertIn("typedef QVal (*quest_sig_Counter_new)(QInt init);", h_text)
            self.assertIn("typedef QVal (*quest_sig_Counter_inc)(QVal c);", h_text)
            self.assertIn("typedef QInt (*quest_sig_Counter_get)(QVal c);", h_text)

            # Verify .qi metadata
            qi_text = qi_path.read_text(encoding="utf-8")
            self.assertIn('"name":"Counter"', qi_text)
            self.assertIn('"name":"T"', qi_text)
            self.assertIn('"isManifest":false', qi_text)
            self.assertIn('"name":"new"', qi_text)

            # Verify loading Scope from .qi
            env = Environment()
            scope = load_interface_from_qi_file(qi_path, env)
            self.assertIn("T", scope.types)
            self.assertIsNone(scope.types["T"].definition)
            self.assertIn("new", scope.values)
            self.assertIn("inc", scope.values)
            self.assertIn("get", scope.values)

    def test_compile_manifest_types(self) -> None:
        src = """
interface Geometry
export
    Def Point = Record x: Int y: Int end
    Shape::TYPE
    origin: Point
    area(s: Shape): Real
end;
"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "geometry.int.quest"
            p.write_text(src, encoding="utf-8")

            h_path, qi_path = compile_interface_with_header(p)
            h_text = h_path.read_text(encoding="utf-8")
            self.assertIn("typedef struct quest_rec_Geometry_Point", h_text)
            self.assertIn("QInt x;", h_text)
            self.assertIn("QInt y;", h_text)
            self.assertIn("typedef QRecordVal quest_type_Geometry_Point;", h_text)
            self.assertIn("typedef QVal quest_type_Geometry_Shape;", h_text)

            env = Environment()
            scope = load_interface_from_qi_file(qi_path, env)
            self.assertIn("Point", scope.types)
            self.assertIsNotNone(scope.types["Point"].definition)
            self.assertIn("Shape", scope.types)
            self.assertIsNone(scope.types["Shape"].definition)

    def test_mutually_recursive_types_round_trip(self) -> None:
        from quest.codegen.c.types import qtype_to_c_type
        from quest.codegen.layout import type_tag
        from quest.typechecker.elaborate_types import elaborate_type_binding_group
        from quest.types import QAliasType, QRecGroupType, is_type_equal
        from tests.python.helpers import parse_phrase

        group_src = "Def Rec Wood = Record trees: Array(Tree) end and Tree = Variant leaf: Int node: Wood end"
        src = f"""
interface Forests
export
    {group_src}
    Def Pair = Tuple w: Wood t: Tree end
    node(trees: Array(Tree)): Tree
end;
"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "forests.int.quest"
            p.write_text(src, encoding="utf-8")
            _, qi_path = compile_interface_with_header(p)
            qi_text = qi_path.read_text(encoding="utf-8")
            # Members record their bodies and a shared group number
            self.assertIn('"group":1', qi_text)
            self.assertIn('"manifestType":"Record trees: Array(Tree) end"', qi_text)

            env = Environment()
            scope = load_interface_from_qi_file(qi_path, env)
            wood, tree = scope.types["Wood"], scope.types["Tree"]
            self.assertIsInstance(wood.definition, QRecGroupType)
            self.assertIsInstance(tree.definition, QRecGroupType)
            self.assertIs(wood.definition.bindings, tree.definition.bindings)
            self.assertEqual([b[1] for b in wood.definition.bindings], [wood.symbol_id, tree.symbol_id])

            # The loaded types are the types elaborated from source, with the same C representation
            source_env = Environment()
            source_wood, source_tree = elaborate_type_binding_group(parse_phrase(group_src + ";"), source_env)
            self.assertTrue(is_type_equal(wood.definition, source_wood.definition))
            self.assertTrue(is_type_equal(tree.definition, source_tree.definition))
            self.assertEqual(type_tag(wood.definition), type_tag(source_wood.definition))
            param_type = scope.values["node"].type_val.params[0].type_val
            self.assertEqual(qtype_to_c_type(param_type), "QArray *")
            pair_fields = scope.types["Pair"].definition.fields
            self.assertIsInstance(pair_fields[1].type_val, QAliasType)
            self.assertIs(pair_fields[1].type_val.target, tree.definition)

    def test_compile_interface_inheritance(self) -> None:
        c_src = """
interface BaseCounter
export
    T::TYPE
    new(init: Int): T
end;
"""
        ext_src = """
interface ExtCounter
import : BaseCounter
export
    reset(c: BaseCounter.T): BaseCounter.T
end;
"""
        with tempfile.TemporaryDirectory() as td:
            p_base = Path(td) / "basecounter.int.quest"
            p_base.write_text(c_src, encoding="utf-8")
            compile_interface_with_header(p_base)

            p_ext = Path(td) / "extcounter.int.quest"
            p_ext.write_text(ext_src, encoding="utf-8")
            h_ext, qi_ext = compile_interface_with_header(p_ext)

            h_text = h_ext.read_text(encoding="utf-8")
            self.assertIn('#include "basecounter.int.h"', h_text)
            self.assertIn("quest_sig_ExtCounter_reset", h_text)

            env = Environment()
            env.include_paths = [Path(td)]
            scope = load_interface_from_qi_file(qi_ext, env)
            self.assertIn("T", scope.types)
            self.assertIn("reset", scope.values)

    def test_module_loader_loads_qi_without_source(self) -> None:
        src = """
interface Tokenizer
export
    Token::TYPE
    nextToken(): Token
end;
"""
        with tempfile.TemporaryDirectory() as td:
            intf_file = Path(td) / "tokenizer.int.quest"
            intf_file.write_text(src, encoding="utf-8")
            _, qi_path = compile_interface_with_header(intf_file)

            # Delete the source interface file: only tokenizer.qi remains!
            intf_file.unlink()
            self.assertTrue(qi_path.exists())
            self.assertFalse(intf_file.exists())

            env = Environment()
            env.include_paths = [Path(td)]
            scope = load_interface("Tokenizer", env)
            self.assertIn("Token", scope.types)
            self.assertIn("nextToken", scope.values)

    def test_driver_cli_compile_only_interface(self) -> None:
        src = """
interface Calc
export
    add(a: Int b: Int): Int
end;
"""
        with tempfile.TemporaryDirectory() as td:
            intf_file = Path(td) / "calc.int.quest"
            intf_file.write_text(src, encoding="utf-8")

            driver_path = Path(__file__).parent.parent.parent / "bootstrap" / "python" / "quest_driver.py"
            cmd = [sys.executable, str(driver_path), "-c", str(intf_file)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Driver failed: {res.stderr}")

            h_file = Path(td) / "calc.int.h"
            qi_file = Path(td) / "calc.qi"
            self.assertTrue(h_file.exists())
            self.assertTrue(qi_file.exists())


if __name__ == "__main__":
    unittest.main()
