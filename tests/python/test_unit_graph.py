"""The graph of program units (quest/modules/graph.py, docs/build-process.md §2.1): resolving each import once per
compilation, the names a resolved unit has, sharing loaded units by canonical name, and rolling them back.

The tree used throughout: a program directory prog/ beside an include root lib/, holding

    lib/util/counter.int.quest   interface Counter, importing Base (a sibling)
    lib/util/counter.mod.quest   module counter : Counter
    lib/util/base.int.quest      interface Base
    prog/main.quest              (not read; only its directory matters)
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from quest.modules.graph import (
    ModuleArtifacts,
    Resolver,
    Roots,
    UnitGraph,
    UnitKind,
    file_unit_kind,
    interface_qi_file,
    resolve_interface,
    resolve_module,
    unit_artifact_dir,
)
from quest.modules.loader import load_interface, load_module
from quest.types.env import Environment


class TestUnitGraph(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        self.lib = self.root / "lib"
        self.util = self.lib / "util"
        self.prog = self.root / "prog"
        self.util.mkdir(parents=True)
        self.prog.mkdir()
        (self.util / "base.int.quest").write_text("interface Base export Def T = Int end;\n", encoding="utf-8")
        (self.util / "counter.int.quest").write_text(
            "interface Counter import :Base export new(): Base.T end;\n", encoding="utf-8"
        )
        (self.util / "counter.mod.quest").write_text(
            "module counter : Counter export Def T = Int let new(): T = 0 end;\n", encoding="utf-8"
        )
        self.roots = Roots.of([self.lib], self.prog)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _env(self) -> Environment:
        env = Environment()
        env.current_dir = self.prog
        env.program_dir = self.prog
        env.include_paths = [self.lib]
        return env

    # 1. Resolution

    def test_each_import_is_resolved_once(self) -> None:
        resolver = Resolver()
        first = resolver.interface("util/Counter", self.prog, self.roots)
        self.assertIs(resolver.interface("util/Counter", self.prog, self.roots), first)
        self.assertEqual(first.source, self.util / "counter.int.quest")
        # Another directory or other roots are another resolution.
        self.assertIsNot(resolver.interface("Counter", self.util, self.roots), first)
        self.assertIsNot(resolver.interface("util/Counter", self.prog, Roots.of([], self.prog)), first)

    def test_names_of_a_resolved_unit(self) -> None:
        resolver = Resolver()
        iface = resolver.interface("util/Counter", self.prog, self.roots)
        # The unit's key is its file's path below its root; importers record the declared base name.
        self.assertEqual(iface.canonical_name, "util/counter")
        self.assertEqual(iface.interface_name, "util/Counter")
        self.assertEqual(iface.artifact_name, "util/counter")
        # A sibling import from util/ names the same unit.
        self.assertEqual(resolver.interface("Counter", self.util, self.roots).canonical_name, "util/counter")
        module = resolver.module("util/counter", self.prog, self.roots)
        self.assertEqual((module.source, module.canonical_name), (self.util / "counter.mod.quest", "util/counter"))

    def test_unit_without_a_source_keeps_the_name_imported(self) -> None:
        resolver = Resolver()
        module = resolver.module("nowhere", self.prog, self.roots)
        self.assertIsNone(module.source)
        self.assertEqual(module.canonical_name, "nowhere")
        iface = resolver.interface("Nowhere", self.prog, self.roots)
        self.assertIsNone(iface.unit_file)
        self.assertEqual((iface.canonical_name, iface.interface_name), ("nowhere", "Nowhere"))

    def test_forget_finds_files_created_since(self) -> None:
        resolver = Resolver()
        self.assertIsNone(resolver.module("extra", self.prog, self.roots).source)
        (self.prog / "extra.mod.quest").write_text("module extra : Base export Def T = Int end;\n", encoding="utf-8")
        self.assertIsNone(resolver.module("extra", self.prog, self.roots).source)
        resolver.forget()
        self.assertEqual(resolver.module("extra", self.prog, self.roots).source, self.prog / "extra.mod.quest")

    def test_interface_dependencies_follow_imports_from_each_importer(self) -> None:
        deps = Resolver().interface_dependencies(self.util / "counter.int.quest", [self.lib])
        self.assertEqual([(d.path, d.dir, d.source) for d in deps],
                         [("Base", str(self.util), str(self.util / "base.int.quest"))])

    def test_file_given_directly(self) -> None:
        resolver = Resolver()
        unit = resolver.file(self.util / "counter.mod.quest", self.roots)
        self.assertEqual((unit.kind, unit.canonical_name), (UnitKind.MODULE, "util/counter"))
        self.assertIs(resolver.file(self.util / "counter.mod.quest", self.roots), unit)
        self.assertEqual(resolver.file(self.util / "counter.int.quest", self.roots).canonical_name, "util/counter")

    def test_build_records_imports_as_its_resolver_resolved_them(self) -> None:
        from types import SimpleNamespace

        from quest.build.engine import unit_module_refs

        resolver = Resolver()
        item = SimpleNamespace(
            effective_interface_path="util/Counter", names=("counter",), effective_module_paths=("util/counter",)
        )
        refs = unit_module_refs([item], [], self.prog, [self.lib], self.prog, resolver)
        module = resolver.module("util/counter", self.prog, Roots.of([self.lib], self.prog))
        self.assertEqual([(r.name, r.interface, r.source, r.path) for r in refs],
                         [("util/counter", "util/Counter", str(module.source), "util/counter")])

    def test_unit_files_are_compiled_by_kind(self) -> None:
        from quest.build.engine import compile_unit_file

        build = self.root / ".build"
        compile_unit_file(self.util / "counter.int.quest", [self.lib], build_dir=build)
        self.assertTrue((build / "util" / "counter.qi").is_file())
        self.assertTrue((build / "util" / "counter.int.h").is_file())
        with self.assertRaises(ValueError):
            compile_unit_file(self.prog / "main.quest", [self.lib], build_dir=build)

    # 2. Artifacts

    def test_artifact_paths(self) -> None:
        build = self.root / ".build"
        self.assertEqual(unit_artifact_dir(build, "util/counter"), build / "util")
        self.assertEqual(unit_artifact_dir(build, "counter"), build)
        self.assertEqual(interface_qi_file(build, "util/Counter"), build / "util" / "counter.qi")
        artifacts = ModuleArtifacts.under(build, "util/counter")
        self.assertEqual((artifacts.qm, artifacts.c, artifacts.o),
                         (build / "util/counter.qm", build / "util/counter.mod.c", build / "util/counter.o"))

    def test_file_unit_kinds(self) -> None:
        self.assertEqual(file_unit_kind(Path("a/x.int.quest")), UnitKind.INTERFACE)
        self.assertEqual(file_unit_kind(Path("a/x.mod.quest")), UnitKind.MODULE)
        self.assertEqual(file_unit_kind(Path("a/x.quest")), UnitKind.PROGRAM)

    # 3. Units and their typed forms

    def test_loaded_units_are_shared_by_canonical_name(self) -> None:
        env = self._env()
        scope = load_interface("util/Counter", env)
        self.assertIs(env.units.interface_scope("util/counter"), scope)
        # The sibling import of Base, from util/, is a unit too.
        self.assertIsNotNone(env.units.interface_scope("util/base"))
        # The same file through another path is the same unit.
        env.current_dir = self.util
        self.assertIs(load_interface("Counter", env), scope)
        env.current_dir = self.prog
        typed = load_module("util/counter", "util/Counter", env)
        self.assertIs(env.units.typed_module("util/counter"), typed)
        self.assertIs(resolve_module("util/counter", env), resolve_module("util/counter", env))
        self.assertEqual(resolve_interface("util/Counter", env).source, self.util / "counter.int.quest")

    def test_snapshot_and_restore_forget_units_loaded_since(self) -> None:
        env = self._env()
        load_interface("util/Base", env)
        snap = env.units.snapshot()
        load_interface("util/Counter", env)
        env.units.unit(UnitKind.MODULE, "prebuilt").precompiled = True
        env.units.unit(UnitKind.MODULE, "run").value = object()
        graph = env.units
        env.units.restore(snap)
        self.assertIs(env.units, graph)
        self.assertIsNotNone(env.units.interface_scope("util/base"))
        self.assertIsNone(env.units.interface_scope("util/counter"))
        self.assertFalse(env.units.is_precompiled("prebuilt"))
        self.assertIsNone(env.units.find(UnitKind.MODULE, "run"))

    def test_restore_keeps_values_of_units_loaded_before(self) -> None:
        graph = UnitGraph()
        value = object()
        graph.unit(UnitKind.MODULE, "util/counter").value = value
        snap = graph.snapshot()
        graph.unit(UnitKind.MODULE, "util/counter").value = None
        graph.restore(snap)
        self.assertIs(graph.find(UnitKind.MODULE, "util/counter").value, value)

    def test_new_session_resolves_again(self) -> None:
        graph = UnitGraph()
        roots = Roots.of([self.lib], None)
        first = graph.resolver.module("util/counter", self.lib, roots)
        graph.unit(UnitKind.MODULE, first.canonical_name)
        graph.new_session()
        self.assertIsNot(graph.resolver.module("util/counter", self.lib, roots), first)
        self.assertIsNotNone(graph.find(UnitKind.MODULE, first.canonical_name))

    def test_prebuilt_objects_are_precompiled(self) -> None:
        graph = UnitGraph()
        graph.add_prebuilt_objects([self.util / "counter.o"], [self.lib])
        self.assertTrue(graph.is_precompiled("util/counter"))
        self.assertTrue(graph.is_precompiled("counter"))

    def test_graphs_of_one_session_share_a_resolver(self) -> None:
        resolver = Resolver()
        first, second = UnitGraph(resolver=resolver), UnitGraph(resolver=resolver)
        first.unit(UnitKind.INTERFACE, "util/counter")
        self.assertIsNone(second.find(UnitKind.INTERFACE, "util/counter"))
        self.assertIs(first.resolver, second.resolver)


if __name__ == "__main__":
    unittest.main()
