"""Dependencies between the compiler's packages: compilation does not depend on
the interpreters, and only C compilation reaches the C backend, directly or
through other modules (not the IR, nor what every backend shares, nor the type
checker and the loading of interfaces).

The import graph is read from the sources (every `import` and `from ... import`,
including those inside functions, which run only when called), so a dependency
is found whether or not the tests exercise it."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent / "bootstrap" / "python" / "quest"

# What compiles Quest to C: none of it may reach the interpreters
COMPILATION = (
    "quest.build",
    "quest.codegen",
    "quest.ir",
    "quest.modules",
    "quest.syntax",
    "quest.typechecker",
    "quest.types",
    "quest.values",
)
INTERPRETERS = ("quest.interpreter", "quest.repl")
# C compilation: the C backend (which writes interfaces' C headers too), and
# what drives it (the build engine, compiling module files, and the pipeline,
# whose phases include C's). Only these may import the C backend.
C_COMPILATION = (
    "quest.build",
    "quest.codegen.c",
    "quest.modules.module_compiler",
    "quest.pipeline",
)
# What runs the pipeline, and so reaches the C backend through it
PIPELINE_CLIENTS = ("quest.repl", "quest.testing")
C_BACKEND = ("quest.codegen.c",)


def _modules() -> dict[str, Path]:
    found = {}
    for path in PACKAGE_DIR.rglob("*.py"):
        parts = path.relative_to(PACKAGE_DIR.parent).with_suffix("").parts
        found[".".join(parts[:-1] if parts[-1] == "__init__" else parts)] = path
    return found


def _within(name: str, packages: tuple[str, ...]) -> bool:
    return any(name == p or name.startswith(p + ".") for p in packages)


def import_graph() -> dict[str, set[str]]:
    """Each module of the quest package, and the quest modules importing it
    runs."""
    modules = _modules()

    def resolve(name: str) -> str | None:
        # The module an imported name is, or is defined in
        while name and name not in modules:
            name = name.rpartition(".")[0]
        return name or None

    graph: dict[str, set[str]] = {}
    for name, path in modules.items():
        imported = set()
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("quest"):
                candidates = [f"{node.module}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Import):
                candidates = [a.name for a in node.names if a.name.startswith("quest")]
            else:
                continue
            imported.update(m for m in map(resolve, candidates) if m is not None and m != name)
        # Importing a module runs its packages' __init__ modules first
        package = name
        while "." in package:
            package = package.rpartition(".")[0]
            if package in modules and package != name:
                imported.add(package)
        graph[name] = imported
    return graph


def reached(graph: dict[str, set[str]], sources: tuple[str, ...], targets: tuple[str, ...]) -> list[str]:
    """The import paths from modules within sources to modules within
    targets."""
    return paths_to(graph, [m for m in graph if _within(m, sources)], targets)


def paths_to(graph: dict[str, set[str]], starts: list[str], targets: tuple[str, ...]) -> list[str]:
    """The import paths from the modules starts to modules within targets."""
    paths = {m: [m] for m in starts}
    stack = list(paths)
    while stack:
        module = stack.pop()
        for imported in graph[module]:
            if imported not in paths:
                paths[imported] = paths[module] + [imported]
                stack.append(imported)
    return sorted(" -> ".join(path) for m, path in paths.items() if _within(m, targets))


class TestDependencies(unittest.TestCase):
    def test_compilation_does_not_reach_the_interpreters(self) -> None:
        graph = import_graph()
        self.assertIn("quest.codegen.c.printer", graph)
        self.assertEqual(reached(graph, COMPILATION, INTERPRETERS), [], "compilation imports the interpreters")

    def test_only_c_compilation_imports_the_c_backend(self) -> None:
        graph = import_graph()
        self.assertIn("quest.codegen.layout", graph)
        importers = sorted(
            f"{m} -> {i}" for m, imported in graph.items() for i in imported
            if _within(i, C_BACKEND) and not _within(m, C_COMPILATION)
        )
        self.assertEqual(importers, [], "imports of the C backend from outside C compilation")

    def test_only_c_compilation_reaches_the_c_backend(self) -> None:
        graph = import_graph()
        self.assertIn("quest.modules.interface_compiler", graph)
        outside = [m for m in graph if not _within(m, C_COMPILATION + PIPELINE_CLIENTS)]
        self.assertEqual(paths_to(graph, outside, C_BACKEND), [], "modules outside C compilation reach the C backend")

    def test_the_front_end_does_not_reach_later_phases(self) -> None:
        """Tokenizing, parsing, and desugaring (quest.syntax) need no types,
        scopes, units, or back end."""
        # The package's __init__, which every import of a submodule runs,
        # re-exports the whole compiler
        graph = {m: imported - {"quest"} for m, imported in import_graph().items()}
        self.assertIn("quest.syntax.desugar", graph)
        later = (
            "quest.types", "quest.typechecker", "quest.modules", "quest.build", "quest.pipeline", "quest.ir",
            "quest.codegen", "quest.interpreter", "quest.values",
        )
        self.assertEqual(reached(graph, ("quest.syntax",), later), [], "the front end reaches later phases")

if __name__ == "__main__":
    unittest.main()
