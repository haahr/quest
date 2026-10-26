"""The node families' explicit traversals (docs/self-hosting-refactorings.md §3): each has an entry for every class of
its family, and agrees with the dataclasses' own fields (which the compiler itself no longer reads by reflection) on
every node of real programs: those of the syntax tree, the typed AST, the IR, and the types they mention."""

import ast as python_ast
import dataclasses
import inspect
import unittest
from pathlib import Path

import quest.syntax.ast as syntax
import quest.typechecker.typed_ast as typed
import quest.types.model as model
from quest.config import CompilerOptions
from quest.ir import nodes as ir
from quest.ir import walk
from quest.ir.closure import closure_convert_unit
from quest.ir.describe import describe_unit
from quest.ir.lower import lower_program
from quest.ir.represent import represent_unit
from quest.ir.specialize import specialize_unit
from quest.pipeline import CompilerContext, default_pipeline
import tests.python.helpers  # noqa: F401  (enables the invariant checks)

_ROOT = Path(__file__).resolve().parents[2]
# Programs whose nodes are compared: enough to meet every class that a program can make
_PROGRAMS = sorted((_ROOT / "tests" / "source" / "language").glob("*.quest"))
_DESCRIPTOR_FIELDS = ir.DESCRIPTOR_FIELDS | {"witness", "static_data"}


def _classes(module) -> list[type]:
    """The family's classes with instances (not the bases that only give subclasses an offset)."""
    found = [c for c in vars(module).values()
             if isinstance(c, type) and dataclasses.is_dataclass(c) and c.__module__ == module.__name__]
    bases = {b for c in found for b in c.__mro__[1:] if b in found}
    return [c for c in found if c not in bases]


def _cases(function) -> set[str]:
    """The names of the classes a function's match statement has cases for."""
    names = set()
    for node in python_ast.walk(python_ast.parse(inspect.getsource(function))):
        if isinstance(node, python_ast.MatchClass):
            names.add(python_ast.unparse(node.cls).split(".")[-1])
    return names


def _reflected(node, excluded=frozenset()) -> tuple:
    return tuple(getattr(node, f.name) for f in dataclasses.fields(node) if f.name not in excluded)


class TestEveryClassHasACase(unittest.TestCase):
    def check(self, module, *tables) -> None:
        wanted = set(_classes(module))
        for table in tables:
            self.assertEqual(set(table), wanted)

    def test_types(self):
        self.check(model, model._TYPE_FIELDS, model._REBUILD_TYPE)

    def test_ir(self):
        self.check(ir, walk._FIELDS_OF, walk._REBUILD, walk._CONTENTS)

    def test_typed_ast(self):
        self.check(typed, typed._TYPED_FIELDS, typed._REBUILD_TYPED)

    def test_syntax(self):
        self.check(syntax, syntax._AST_FIELDS, syntax._REBUILD_AST)

    def test_view_maps(self):
        """view_map_of has a case for every class with a view map."""
        wanted = {c.__name__ for c in _classes(ir) if "view_map" in {f.name for f in dataclasses.fields(c)}}
        self.assertEqual(wanted, _cases(walk.view_map_of))


class TestTraversalsAgreeWithFields(unittest.TestCase):
    """Every node of the programs: its fields as the traversal gives them are its dataclass fields, and rebuilding
    it from them makes an equal node (the same one, for interned types)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.nodes: dict[str, dict[int, object]] = {"syntax": {}, "typed": {}, "ir": {}, "types": {}}
        for path in _PROGRAMS:
            source = path.read_text()
            options = CompilerOptions(stop_after="typecheck", include_paths=[_ROOT])
            ctx = CompilerContext.create(source_text=source, file_name=str(path), options=options)
            result = default_pipeline().execute(source, str(path), options=options, ctx=ctx)
            if not result.success:
                continue
            for phase in ("parse", "desugar", "typecheck"):
                cls.collect(result.artifacts[phase])
            try:
                unit = lower_program(result.artifacts["typecheck"], ctx.env, print_result=True)
                cls.collect(unit)
                unit = specialize_unit(unit)
                cls.collect(unit)
                cls.collect(describe_unit(represent_unit(closure_convert_unit(unit))))
            except Exception:
                # (A program the IR does not lower yet, such as one importing a module file)
                continue

    @classmethod
    def collect(cls, root) -> None:
        # (A pass rewrites bodies in place, so each stage is walked afresh)
        seen: set[int] = set()
        stack = [root]
        while stack:
            node = stack.pop()
            if isinstance(node, (list, tuple)):
                stack.extend(node)
                continue
            if isinstance(node, dict):
                stack.extend(node.values())
                continue
            if not dataclasses.is_dataclass(node) or isinstance(node, type):
                continue
            family = ("syntax" if isinstance(node, syntax.ASTNode) else "typed" if isinstance(node, typed.TypedNode)
                      else "ir" if type(node).__module__ == ir.__name__
                      else "types" if type(node).__module__ == model.__name__ else None)
            if family is None or id(node) in seen:
                continue
            seen.add(id(node))
            cls.nodes[family][id(node)] = node
            stack.extend(getattr(node, f.name) for f in dataclasses.fields(node))
            if family == "typed":
                symbol = getattr(node, "symbol", None)
                stack.append(getattr(symbol, "type_val", None))

    def check(self, family: str, fields, rebuild, excluded=frozenset(), same=False) -> None:
        nodes = list(self.nodes[family].values())
        self.assertGreater(len({type(n) for n in nodes}), 10, family)
        for node in nodes:
            parts = fields(node)
            self.assertEqual(parts, _reflected(node, excluded), type(node).__name__)
            copy = rebuild(node, parts)
            self.assertIs(type(copy), type(node))
            if same:
                self.assertIs(copy, node, type(node).__name__)
            else:
                self.assertTrue(all(a is b for a, b in zip(_reflected(copy), _reflected(node))), type(node).__name__)

    def test_types(self):
        self.check("types", model.type_fields, model.rebuild_type, same=True)

    def test_ir(self):
        self.check("ir", walk.fields_of, walk.rebuild)
        for node in self.nodes["ir"].values():
            self.assertEqual(walk.contents(node), _reflected(node, _DESCRIPTOR_FIELDS), type(node).__name__)
            self.assertIs(walk.view_map_of(node), getattr(node, "view_map", None))

    def test_typed_ast(self):
        self.check("typed", typed.typed_fields, typed.rebuild_typed, excluded={"offset"})

    def test_syntax(self):
        self.check("syntax", syntax.ast_fields, syntax.rebuild_ast, excluded={"offset"})

    def test_other_values_have_no_fields(self):
        for value in (None, 1, "s", (), [], {}, ir.Body):
            self.assertIsNone(model.type_fields(value))
            self.assertIsNone(walk.fields_of(value))
            self.assertIsNone(walk.contents(value))
            self.assertIsNone(typed.typed_fields(value))
            self.assertIsNone(syntax.ast_fields(value))


if __name__ == "__main__":
    unittest.main()
