"""Dependencies between the compiler's packages: compilation does not depend on the interpreters.

The import graph is read from the sources (every `import` and `from ... import`, including those inside functions,
which run only when called), so a dependency is found whether or not the tests exercise it."""

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


def _modules() -> dict[str, Path]:
    found = {}
    for path in PACKAGE_DIR.rglob("*.py"):
        parts = path.relative_to(PACKAGE_DIR.parent).with_suffix("").parts
        found[".".join(parts[:-1] if parts[-1] == "__init__" else parts)] = path
    return found


def _within(name: str, packages: tuple[str, ...]) -> bool:
    return any(name == p or name.startswith(p + ".") for p in packages)


def import_graph() -> dict[str, set[str]]:
    """Each module of the quest package, and the quest modules it imports."""
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
        graph[name] = imported
    return graph


class TestDependencies(unittest.TestCase):
    def test_compilation_does_not_reach_the_interpreters(self) -> None:
        graph = import_graph()
        paths = {m: [m] for m in graph if _within(m, COMPILATION)}
        self.assertIn("quest.codegen.c_printer", paths)
        stack = list(paths)
        while stack:
            module = stack.pop()
            for imported in graph[module]:
                if imported not in paths:
                    paths[imported] = paths[module] + [imported]
                    stack.append(imported)
        reached = sorted(" -> ".join(path) for m, path in paths.items() if _within(m, INTERPRETERS))
        self.assertEqual(reached, [], "compilation imports the interpreters")


if __name__ == "__main__":
    unittest.main()
