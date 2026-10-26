"""Generates the golden tests of the self-hosted type elaboration
(questlang/typechecker/elaboratetypes) from the bootstrap's.

Each input tests/elaborate/NAME.quest holds cases, separated by lines that are
just "(* ---- *)": programs of type and kind declarations. It gives a golden
test, tests/source/questlang/elaborate_NAME.quest, which parses and desugars
each case with the self-hosted compiler and elaborates its declarations, in
order, in a new environment, printing each symbol declared, or the first error;
tests/golden/run/questlang/elaborate_NAME.out holds what the bootstrap's
elaborate_types gives for each case, which the test must print.

    python tests/elaborate/generate.py

Run it after changing an input; the tests run as part of the test suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))
sys.path.insert(0, str(ROOT_DIR / "tests" / "parser"))

import quest.syntax.ast as A  # noqa: E402
from quest.diagnostics import QuestCompilerError  # noqa: E402
from quest.syntax.desugar import desugar  # noqa: E402
from quest.syntax.grammar import parse_quest_program  # noqa: E402
from quest.syntax.tokenizer import Tokenizer  # noqa: E402
from quest.typechecker.elaborate_types import (  # noqa: E402
    elaborate_kind_binding,
    elaborate_type_binding,
    elaborate_type_binding_group,
)
from quest.types.env import Environment  # noqa: E402

from generate import cases, qstr  # noqa: E402

HERE = Path(__file__).resolve().parent
TEST_DIR = ROOT_DIR / "tests" / "source" / "questlang"
GOLDEN_DIR = ROOT_DIR / "tests" / "golden" / "run" / "questlang"


def expected(name: str, text: str) -> str:
    """What the bootstrap gives for a case: the symbols its declarations
    declare, until an error."""
    tok = Tokenizer(text, name)
    program = desugar(parse_quest_program(tok.tokenize_all(), tok.source_map))
    env = Environment()
    lines = []
    try:
        for phrase in program.phrases:
            match phrase:
                case A.TypeBinding():
                    symbols = [elaborate_type_binding(phrase, env)]
                case A.TypeBindingGroup():
                    symbols = elaborate_type_binding_group(phrase, env)
                case A.DefKindBinding():
                    k = elaborate_kind_binding(phrase, env)
                    lines.append(f"DEF {k.name} = {k.kind}")
                    continue
                case _:
                    raise AssertionError(f"not a type or kind declaration: {phrase}")
            lines.extend(f"{s.name} :: {s.kind} = {s.definition}" for s in symbols)
    except QuestCompilerError as e:
        lines.append(f"error at {e.offset}: {e.message}")
    return "".join(line + "\n" for line in lines)


PRELUDE = """import
    questlang/common/location : questlang/common/Location
    questlang/common/diagnostics : questlang/common/Diagnostics
    questlang/common/diagbag : questlang/common/DiagBag
    questlang/syntax/ast : questlang/syntax/Ast
    questlang/syntax/tokenizer : questlang/syntax/Tokenizer
    questlang/syntax/parser : questlang/syntax/Parser
    questlang/syntax/desugar : questlang/syntax/Desugar
    questlang/types/model : questlang/types/Model
    questlang/types/symbols : questlang/types/Symbols
    questlang/types/env : questlang/types/Env
    questlang/typechecker/elaborateTypes : questlang/typechecker/ElaborateTypes
    collections/vector : collections/Vector
    util/maybe : util/Maybe
    writer : Writer
    conv : Conv
;

let emit(s: String): Ok = begin writer.putString(writer.output s) writer.putString(writer.output "\\n") end;

let show(s: symbols.TypeSymbol): Ok =
    emit(s.name <> " :: " <> model.showKind(s.kind) <> " = " <> model.show(maybe.unwrap(:model.Type s.definition)));

let typeBinding(d: ast.Decl): ast.TypeBinding =
    case d.form
        when declTypeBinding with x then
            tuple
                let offset = d.span.startOffset let name = x.name let typeVal = x.typeVal let params = x.params
                let bound = x.bound let isRec = x.isRec let isDef = x.isDef
            end
        else diagnostics.fail(:ast.TypeBinding "not a type binding" 0)
    end;

(* Elaborates a case's declarations, printing the symbols they declare, until an error *)
let elaborate(index: Int name: String text: String): Ok =
    begin
        emit("-- case " <> conv.int(index))
        let sm = location.newSourceMap(name text)
        let bag = diagbag.new()
        let program = desugar.program(parser.parseProgram(tokenizer.tokenizeAll(tokenizer.new(sm bag)) sm bag))
        let e = env.new()
        try
            for i = 0 upto {vector.length(:ast.Phrase program.form.phrases) - 1} do
                case vector.get(:ast.Phrase program.form.phrases i).form
                    when phraseDecl with p then
                        case p.decl.form
                            when declTypeBinding then show(elaborateTypes.elaborateTypeBinding(typeBinding(p.decl) e))
                            when declTypeBindingGroup with g then
                                begin
                                    let members = vector.map(:ast.Decl :ast.TypeBinding g.bindings typeBinding)
                                    let syms = elaborateTypes.elaborateTypeBindingGroup(members e)
                                    for j = 0 upto {extent syms - 1} do show(syms[j]) end
                                end
                            when declDefKind with k then
                                begin
                                    let sym = elaborateTypes.elaborateKindBinding(k.name k.kindVal e)
                                    emit("DEF " <> sym.name <> " = " <> model.showKind(sym.kind))
                                end
                            else emit("not a type or kind declaration")
                        end
                    else emit("not a type or kind declaration")
                end
            end
        when diagnostics.compilerError with err then
            emit("error at " <> conv.int(err.offset) <> ": " <> err.message)
        end
    end;

"""


def generate_tests() -> None:
    for source in sorted(HERE.glob("*.quest")):
        name = source.name
        header = (
            f"(* Generated by tests/elaborate/generate.py from tests/elaborate/{name}; do not edit. It elaborates the\n"
            "   type and kind declarations of each case with the self-hosted compiler, printing the symbols they declare,\n"
            "   or the first error, as the bootstrap's elaborate_types gives them. *)\n"
            "(* @skip-phase: tokenize, parse, typecheck, ir_core *)\n"
            "(* @timeout: 300.0 *)\n\n"
        )
        texts = cases(source)
        calls = "".join(f"elaborate({i} {qstr(name)} {qstr(text)});\n" for i, text in enumerate(texts))
        program = TEST_DIR / f"elaborate_{source.stem}.quest"
        golden = GOLDEN_DIR / f"elaborate_{source.stem}.out"
        program.write_text(header + PRELUDE + calls)
        golden.write_text("".join(f"-- case {i}\n" + expected(name, text) for i, text in enumerate(texts)))
        print(f"wrote {program.relative_to(ROOT_DIR)} and {golden.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    generate_tests()
