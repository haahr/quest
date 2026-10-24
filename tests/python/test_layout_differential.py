"""The compiler's static judgement of layouts (generic_layout_agrees) against the runtime's (quest_layout_equivalent).

For each pair of a type over a type parameter, S(A), and a type argument T, a generated program makes a dynamic value
of S(T) in generic code, called through a first-class value so that it is not specialized (whose descriptor is S's template instantiated at T, describing the generic layout) and
another in code that knows T (whose descriptor describes the native layout). A harness appended to the program's C
asks the runtime whether values laid out natively can be used as laid out generically. Wherever the compiler says
the layouts agree, the runtime must: otherwise compiled code would use a value through the wrong struct. Where only
the runtime says they agree, the compiler is merely conservative (it converts a value the runtime would return
unchanged), which is reported but allowed.
"""

from __future__ import annotations

import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))
sys.path.insert(0, str(ROOT_DIR / "tests" / "conversions"))
os.environ["QUEST_CHECK_CANONICAL"] = "1"

import generate  # noqa: E402
import quest.syntax.ast as ast  # noqa: E402
from quest.codegen import compile_c_source, run_binary  # noqa: E402
from quest.codegen.c_types import generic_layout_agrees  # noqa: E402
from quest.typechecker.elaborate_types import elaborate_type_binding, elaborate_type_binding_group  # noqa: E402
from quest.env import Environment, TypeSymbol  # noqa: E402
from quest.config import CompilerOptions  # noqa: E402
from quest.pipeline import CompilerContext, compile_pipeline, link_dependencies  # noqa: E402
from quest.types import TYPE_KIND  # noqa: E402
from tests.python.helpers import elaborate_test_type, parse_phrase  # noqa: E402

# Dynamic values cannot have types that mention a type parameter inside mutable data, and the bare parameter is
# trivially laid out alike
SHAPES = [s for s in generate.SHAPES if s.name not in ("Arr", "Bare")]
RANDOM_PAIRS = 60
SEED = 20261022


def _pairs() -> list[tuple[list[generate.Shape], generate.Arg]]:
    pairs = [([shape], arg) for shape in SHAPES for arg in generate.ARGS]
    rng = random.Random(SEED)
    for _ in range(RANDOM_PAIRS):
        depth = rng.choice((2, 2, 3))
        pairs.append(([rng.choice(SHAPES) for _ in range(depth)], rng.choice(generate.ARGS)))
    return pairs


def _type(shapes: list[generate.Shape], inner: str) -> str:
    for shape in reversed(shapes):
        inner = shape.at(inner)
    return inner


def _value(shapes: list[generate.Shape], arg: generate.Arg) -> str:
    t, v = arg.name, arg.value
    for shape in reversed(shapes):
        v = shape.made(t, v)
        t = shape.at(t)
    return v


class TestLayoutDifferential(unittest.TestCase):
    def setUp(self) -> None:
        self.env = Environment()
        symbol = self.env.current_scope.declare_type(
            TypeSymbol(name="A", symbol_id=self.env.fresh_symbol_id(), kind=TYPE_KIND)
        )
        self.a_id = symbol.symbol_id
        for source in [d for d in generate.ARG_DECLS.splitlines()] + [s.decl for s in generate.SHAPES if s.decl]:
            binding = parse_phrase(source)
            if isinstance(binding, ast.TypeBindingGroup):
                elaborate_type_binding_group(binding, self.env)
            else:
                elaborate_type_binding(binding, self.env)

    def static_agrees(self, shapes: list[generate.Shape], arg: generate.Arg) -> bool:
        generic = elaborate_test_type(_type(shapes, "A"), self.env)
        return generic_layout_agrees(generic, {self.a_id: elaborate_test_type(arg.name, self.env)})

    def runtime_agrees(self, pairs: list[tuple[list[generate.Shape], generate.Arg]]) -> list[bool]:
        packs: dict[str, int] = {}
        lines = ["import dynamic: Dynamic;", generate.ARG_DECLS]
        lines.extend(s.decl for s in generate.SHAPES if s.decl)
        for shapes, _ in pairs:
            generic = _type(shapes, "A")
            if generic not in packs:
                packs[generic] = len(packs)
                i = packs[generic]
                lines.append(f"let packD{i}(A::TYPE s: {generic}): Dynamic = dynamic.new(:{generic} s);")
                # Called through a first-class value, so that calls are not specialized at record or variant types
                lines.append(f"let pack{i}: All(A::TYPE s: {generic}) Dynamic = packD{i};")
        for k, (shapes, arg) in enumerate(pairs):
            native = _type(shapes, arg.name)
            value = _value(shapes, arg)
            lines.append(f"let dg{k} = pack{packs[_type(shapes, 'A')]}(:{arg.name} {value});")
            lines.append(f"let dn{k} = dynamic.new(:{native} {value});")
        lines.append("ok")
        build_dir = tempfile.TemporaryDirectory()
        self.addCleanup(build_dir.cleanup)
        source = "\n".join(lines) + "\n"
        options = CompilerOptions(build_dir=Path(build_dir.name))
        ctx = CompilerContext.create(source_text=source, file_name="<layouts>", options=options)
        res = compile_pipeline().execute(source, "<layouts>", options=options, ctx=ctx)
        self.assertTrue(res.success, [d.message for d in res.diagnostics])
        c_code = res.artifacts["codegen_c"]
        # The modules the program imports (dynamic), compiled on their own and linked with it
        objects = link_dependencies(ctx)
        program_main = "int main(int argc, char **argv) {"
        self.assertEqual(c_code.count(program_main), 1)
        c_code = c_code.replace(program_main, "static int quest_program_main(int argc, char **argv) {")
        harness = [
            "int main(int argc, char **argv) {",
            "    quest_program_main(argc, argv);",
        ]
        harness.extend(
            f'    printf("%d\\n", quest_layout_equivalent(g_dn{k}->type_desc, g_dg{k}->type_desc) ? 1 : 0);'
            for k in range(len(pairs))
        )
        harness.extend(["    return 0;", "}"])
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "layouts"
            compile_c_source(
                c_code + "\n#include <stdio.h>\n" + "\n".join(harness) + "\n", output_path=binary,
                extra_objects=objects,
            )
            proc = run_binary(binary, timeout=60.0)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        results = proc.stdout.split()
        self.assertEqual(len(results), len(pairs))
        return [r == "1" for r in results]

    def test_static_agreement_implies_runtime_agreement(self) -> None:
        pairs = _pairs()
        runtime = self.runtime_agrees(pairs)
        conservative = []
        for (shapes, arg), at_runtime in zip(pairs, runtime):
            label = f"{_type(shapes, 'A')} at {arg.name}"
            static = self.static_agrees(shapes, arg)
            with self.subTest(pair=label):
                self.assertFalse(static and not at_runtime, f"{label}: the compiler says the layouts agree")
            if at_runtime and not static:
                conservative.append(label)
        if conservative:
            print(f"\n{len(conservative)} of {len(pairs)} pairs judged only conservatively by the compiler:", file=sys.stderr)
            for label in conservative[:10]:
                print(f"  {label}", file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
