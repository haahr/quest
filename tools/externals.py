"""Generates questlang/codegen/externals.mod.quest from lib/: the standard
library's members that its modules define as external C functions, and its
external types, which the self-hosted compiler builds in (docs/c-representation.md
section 6.2). A call of such a function from an importer compiles to a call of
the C function itself, which the C compiler can inline.

    tools/externals          rewrite the table from lib/
    tools/externals --check  exit 1 if the table differs from what lib/ gives

The table is committed, and the ABI corpus records it, so a change to it
changes the corpus and must come with a new ABI_VERSION (tests/abi/corpus.py).

A function qualifies if it is a let (not a var) with one or more parameters,
all value parameters, defined as external "symbol", whose parameters' and
result's annotations are base scalar types or the module's own external types:
values of those need no conversion between the caller's representation and the
C function's.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

import quest.syntax.ast as ast  # noqa: E402
from quest.syntax.grammar import parse_quest_program  # noqa: E402
from quest.syntax.sources import SourceMap  # noqa: E402
from quest.syntax.tokenizer import Tokenizer  # noqa: E402

LIB_DIR = ROOT_DIR / "lib"
TABLE = ROOT_DIR / "questlang" / "codegen" / "externals.mod.quest"
SCALARS = frozenset({"Int", "Real", "Bool", "Char", "String", "Ok"})


def module_decl(path: Path) -> ast.ModuleDecl:
    text = path.read_text(encoding="utf-8")
    prog = parse_quest_program(Tokenizer(text, str(path)).tokenize_all(), SourceMap(text, path.name))
    if not (isinstance(prog, ast.Program) and len(prog.phrases) == 1 and isinstance(prog.phrases[0], ast.ModuleDecl)):
        raise SystemExit(f"externals: {path.relative_to(ROOT_DIR)} is not a single module")
    return prog.phrases[0]


def externals() -> tuple[list[tuple[str, ...]], list[tuple[str, ...]]]:
    """The library's external functions, as (module path, name, C symbol), and
    external types, as (module path, name, global name, C type), in the order of
    the modules' paths and of their declarations. A type's global name is its
    module's declared name and its own (process.T), as importers name it."""
    functions: list[tuple[str, ...]] = []
    types: list[tuple[str, ...]] = []
    for path in sorted(LIB_DIR.rglob("*.mod.quest")):
        module = path.relative_to(LIB_DIR).as_posix().removesuffix(".mod.quest")
        decl = module_decl(path)
        own_types = set()
        for b in decl.bindings:
            if isinstance(b, ast.TypeBinding) and isinstance(b.type_val, ast.TypeExternal):
                own_types.add(b.name)
                types.append((module, b.name, f"{decl.name}.{b.name}", b.type_val.c_type))

        def simple(t) -> bool:
            return isinstance(t, ast.TypePath) and len(t.path) == 1 and (t.path[0] in SCALARS or t.path[0] in own_types)

        for b in decl.bindings:
            if (isinstance(b, ast.LetValueBinding) and isinstance(b.value, ast.ExprExternal) and not b.is_var
                    and b.params and all(p.mode == ast.ParamMode.VALUE and simple(p.type_annot) for p in b.params)
                    and simple(b.type_annot)):
                functions.append((module, b.name, b.value.symbol))
    return functions, types


def table_text() -> str:
    functions, types = externals()

    def rows(entries: list[tuple[str, ...]]) -> str:
        return "".join("        array of " + " ".join(f'"{x}"' for x in entry) + " end\n" for entry in entries)

    return (
        "(* Quest Self-Hosted Compiler: The Standard Library's Externals\n"
        " *\n"
        " * Generated from lib/ by tools/externals; do not edit. A change to it\n"
        " * changes the ABI corpus, and needs a new ABI version. *)\n"
        "\n"
        "module externals : Externals export\n"
        "    let functions = array of\n"
        f"{rows(functions)}"
        "    end\n"
        "    let types = array of\n"
        f"{rows(types)}"
        "    end\n"
        "end\n"
    )


def main() -> int:
    text = table_text()
    if sys.argv[1:] == ["--check"]:
        if not TABLE.is_file() or TABLE.read_text(encoding="utf-8") != text:
            print(f"externals: {TABLE.relative_to(ROOT_DIR)} is out of date with lib/; run tools/externals",
                  file=sys.stderr)
            return 1
        return 0
    if sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 2
    TABLE.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
