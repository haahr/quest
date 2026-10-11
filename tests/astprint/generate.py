"""Checks the self-hosted AST printer (questlang/syntax/astprint) against the bootstrap compiler's ast_dump.

Each Quest file is parsed by the bootstrap parser, and its Python AST is translated into a Quest program that builds
the corresponding self-hosted AST and prints it with astprint.dump; the program's output must be exactly what
ast_dump prints for the Python AST.

    python tests/astprint/generate.py              # regenerate the golden tests from tests/astprint/*.quest
    python tests/astprint/generate.py --check      # check every parseable .quest file in the repository
    python tests/astprint/generate.py --check --c  # the same, with the programs compiled to C

Each input tests/astprint/NAME.quest gives a golden test, tests/source/questlang/astprint_NAME.quest with
tests/golden/run/questlang/astprint_NAME.out holding ast_dump's output, which runs as part of the test suite;
forms.quest uses every node the parser produces. Run --check after changing the AST or the printer; it takes about
a minute (three with --c).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

import quest.ast as A  # noqa: E402
from quest.grammar import parse_quest_program  # noqa: E402
from quest.tokenizer import Tokenizer  # noqa: E402

HERE = Path(__file__).resolve().parent
TEST_DIR = ROOT_DIR / "tests" / "source" / "questlang"
GOLDEN_DIR = ROOT_DIR / "tests" / "golden" / "run" / "questlang"
DRIVER = ROOT_DIR / "bootstrap" / "python" / "quest_driver.py"


def qstr(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif 32 <= o < 127:
            out.append(ch)
        else:
            out.append(f"\\{o:03d}")
    out.append('"')
    return "".join(out)


def qchar(ch):
    o = ord(ch)
    if ch == "'":
        return "'\\''"
    if ch == "\\":
        return "'\\\\'"
    if 32 <= o < 127:
        return f"'{ch}'"
    return f"'\\{o:03d}'"


def qint(n):
    return f"~{-n}" if n < 0 else str(n)


def qreal(r):
    if r in (float("inf"), float("-inf")):
        return "1.0e400" if r > 0 else "~1.0e400"
    s = repr(r)
    if "e" in s and "." not in s.split("e")[0]:
        mant, exp = s.split("e")
        s = f"{mant}.0e{exp}"
    if "." not in s and "e" not in s:
        s += ".0"
    return s.replace("-", "~").replace("e+", "e")


def qbool(b):
    return "true" if b else "false"


def vec(typ, items):
    if not items:
        return f"vector.new(:{typ})"
    return f"vector.fromArray(:{typ} array of {' '.join(items)} end)"


def some(typ, x):
    return f"maybe.none(:{typ})" if x is None else f"maybe.some(:{typ} {x})"


def strs(items):
    return vec("String", [qstr(s) for s in items])


def mode(m):
    return {"VALUE": "mV", "VAR": "mVar", "OUT": "mOut"}[m.name]


def form(kind, form_tag, **fields):
    if not fields:
        return f"option {form_tag} of ast.{kind} end"
    lets = " ".join(f"let {k} = {v}" for k, v in fields.items())
    return f"option {form_tag} of ast.{kind} with {lets} end"


# Generated expressions are split into helper functions every few levels of nesting, since the bootstrap parser
# recurses once per level
HELPERS = []
DEPTH = [0]
HOIST_EVERY = 6


def hoisted(typ, make):
    DEPTH[0] += 1
    try:
        code = make()
    finally:
        DEPTH[0] -= 1
    if DEPTH[0] % HOIST_EVERY != 0:
        return code
    name = f"h{len(HELPERS)}"
    HELPERS.append(f"let {name}(): {typ} = {code};")
    return f"{name}()"


def t(node):
    """A type or kind node, as a Quest TypeExpr."""
    return hoisted("ast.TypeExpr", lambda: f"ty({tform(node)})")


def opt_t(node):
    return some("ast.TypeExpr", None if node is None else t(node))


def tform(n):
    F = lambda form_tag, **kw: form("TypeForm", form_tag, **kw)  # noqa: E731
    match n:
        case A.KindType():
            return F("kindType")
        case A.KindPower():
            return F("kindPower", bound=t(n.bound))
        case A.KindAll():
            return F("kindAll", paramName=qstr(n.param_name), paramKind=t(n.param_kind), bodyKind=t(n.body_kind))
        case A.KindId():
            return F("kindId", name=qstr(n.name))
        case A.KindManifest():
            return F("kindManifest", interfaceName=qstr(n.interface_name), kindName=qstr(n.kind_name))
        case A.TypePath():
            return F("typePath", path=strs(n.path))
        case A.TypeAll():
            return F("typeAll", quantifiers=vec("ast.Quantifier", [quantifier(q) for q in n.quantifiers]),
                     resultType=t(n.result_type))
        case A.TypeTuple():
            return F("typeTuple", fields=vec("ast.Signature", [signature(f) for f in n.fields]))
        case A.TypeRecord():
            return F("typeRecord", fields=vec("ast.RecordFieldSig", [
                f"tuple let name = {qstr(f.name)} let typeSig = {t(f.type_sig)} let isVar = {qbool(f.is_var)} end"
                for f in n.fields]))
        case A.TypeOption():
            return F("typeOption", variants=vec("ast.OptionFieldSig", [
                f"tuple let tag = {qstr(v.tag)} let payloadSig = "
                f"{vec('ast.FieldSig', [field_sig(f) for f in v.payload_sig])} end"
                for v in n.variants]))
        case A.TypeVariant():
            return F("typeVariant", fields=vec("ast.VariantFieldSig", [
                f"tuple let tag = {qstr(f.tag)} let typeSig = {t(f.type_sig)} let isVar = {qbool(f.is_var)} end"
                for f in n.fields]))
        case A.TypeAuto():
            return F("typeAuto", typeParam=some("String", None if n.type_param is None else qstr(n.type_param)),
                     kindBound=t(n.kind_bound), signature=vec("ast.FieldSig", [field_sig(f) for f in n.signature]))
        case A.TypeFun():
            return F("typeFun", params=vec("ast.TypeFormal", [type_formal(p) for p in n.params]),
                     resultKind=opt_t(n.result_kind), body=t(n.body))
        case A.TypeRec():
            return F("typeRec", varName=qstr(n.var_name), bound=t(n.bound), body=t(n.body))
        case A.TypeApp():
            return F("typeApp", constructor=t(n.constructor), arguments=vec("ast.TypeExpr", [t(a) for a in n.arguments]))
        case A.TypeInfix():
            return F("typeInfix", left=t(n.left), op=qstr(n.op), right=t(n.right))
        case A.TypeArray():
            return F("typeArray", elementType=t(n.element_type))
        case A.TypeVar():
            return F("typeVar", elementType=t(n.element_type))
        case A.TypeOut():
            return F("typeOut", elementType=t(n.element_type))
        case A.TypeManifest():
            return F("typeManifest", moduleName=qstr(n.module_name), typeName=qstr(n.type_name))
        case A.TypeExternal():
            return F("typeExternal", cType=qstr(n.c_type))
    raise NotImplementedError(type(n).__name__)


def quantifier(q):
    return (f"tuple let name = {qstr(q.name)} let bound = {t(q.bound)} let mode = {mode(q.mode)} "
            f"let isType = {qbool(q.is_type)} end")


def field_sig(f):
    return (f"tuple let name = {some('String', None if f.name is None else qstr(f.name))} "
            f"let typeSig = {opt_t(f.type_sig)} let mode = {mode(f.mode)} end")


def type_formal(p):
    return f"tuple let name = {qstr(p.name)} let bound = {t(p.bound)} end"


def type_binding(b):
    return (f"tuple let name = {qstr(b.name)} let typeVal = {t(b.type_val)} "
            f"let params = {vec('ast.TypeFormal', [type_formal(p) for p in b.params])} let bound = {opt_t(b.bound)} "
            f"let isRec = {qbool(b.is_rec)} let isDef = {qbool(b.is_def)} end")


def signature(s):
    S = lambda form_tag, val: f"option {form_tag} of ast.Signature with let val = {val} end"  # noqa: E731
    match s:
        case A.FieldSig():
            return S("sigValue", field_sig(s))
        case A.TypeFormal():
            return S("sigType", type_formal(s))
        case A.TypeBinding():
            return S("sigTypeBinding", type_binding(s))
        case A.TypeBindingGroup():
            return S("sigTypeBindingGroup", vec("ast.TypeBinding", [type_binding(b) for b in s.bindings]))
        case A.DefKindBinding():
            return S("sigKindBinding", f"tuple let name = {qstr(s.name)} let kindVal = {t(s.kind_val)} end")
    raise NotImplementedError(type(s).__name__)


def formal_param(p):
    return f"tuple let name = {qstr(p.name)} let typeAnnot = {opt_t(p.type_annot)} let mode = {mode(p.mode)} end"


def e(node):
    return hoisted("ast.Expr", lambda: f"ex({eform(node)})")


def opt_e(node):
    return some("ast.Expr", None if node is None else e(node))


def es(nodes):
    return vec("ast.Expr", [e(x) for x in nodes])


def opt_s(s):
    return some("String", None if s is None else qstr(s))


def eform(n):
    F = lambda form_tag, **kw: form("ExprForm", form_tag, **kw)  # noqa: E731
    match n:
        case A.ExprInt():
            return F("exprInt", value=qint(n.value), lexeme=qstr(n.lexeme))
        case A.ExprReal():
            return F("exprReal", value=qreal(n.value), lexeme=qstr(n.lexeme))
        case A.ExprChar():
            return F("exprChar", value=qchar(n.value), lexeme=qstr(n.lexeme))
        case A.ExprString():
            return F("exprString", value=qstr(n.value), lexeme=qstr(n.lexeme))
        case A.ExprBool():
            return F("exprBool", value=qbool(n.value))
        case A.ExprOk():
            return F("exprOk")
        case A.ExprId():
            return F("exprId", name=qstr(n.name))
        case A.ExprExternal():
            return F("exprExternal", symbol=qstr(n.symbol))
        case A.TypeArgument():
            return F("typeArg", typeVal=t(n.type_val))
        case A.KindArgument():
            return F("kindArg", kindVal=t(n.kind_val))
        case A.ExprBlock():
            return F("exprBlock", bindings=es(n.bindings))
        case A.ExprIf():
            return F("exprIf", cond=e(n.cond), thenBranch=e(n.then_branch),
                     elsifs=vec("ast.ElsifBranch", [f"tuple let cond = {e(c)} let thenBranch = {e(b)} end"
                                                    for c, b in n.elsifs]),
                     elseBranch=opt_e(n.else_branch))
        case A.ExprWhile():
            return F("exprWhile", cond=e(n.cond), body=e(n.body))
        case A.ExprLoop():
            return F("exprLoop", body=e(n.body))
        case A.ExprExit():
            return F("exprExit")
        case A.ExprFor():
            return F("exprFor", varName=qstr(n.var_name), start=e(n.start), isDownto=qbool(n.is_downto),
                     stop=e(n.stop), body=e(n.body))
        case A.ExprFun():
            return F("exprFun", params=vec("ast.FormalParam", [formal_param(p) for p in n.params]),
                     returnType=opt_t(n.return_type), body=e(n.body),
                     typeParams=vec("ast.TypeFormal", [type_formal(p) for p in n.type_params]))
        case A.ExprApp():
            return F("exprApp", func=e(n.func), args=es(n.args))
        case A.ExprInfix():
            return F("exprInfix", left=e(n.left), op=qstr(n.op), right=e(n.right))
        case A.ExprTuple():
            return F("exprTuple", fields=vec("ast.TupleField", [tuple_field(x) for x in n.fields]))
        case A.ExprRecord():
            return F("exprRecord", fields=vec("ast.RecordBinding", [
                f"tuple let name = {qstr(b.name)} let value = {e(b.value)} let isVar = {qbool(b.is_var)} end"
                for b in n.fields]))
        case A.ExprArray():
            return F("exprArray", elements=es(n.elements), elementType=opt_t(n.element_type))
        case A.ExprArrayRep():
            return F("exprArrayRep", count=e(n.count), initVal=e(n.init_val))
        case A.ExprOption():
            return F("exprOption", tag=opt_s(n.tag), optionType=t(n.option_type), payload=opt_e(n.payload),
                     ordinalExpr=opt_e(n.ordinal_expr))
        case A.ExprVariant():
            return F("exprVariant", tag=qstr(n.tag), variantType=t(n.variant_type), isVar=qbool(n.is_var),
                     payload=opt_e(n.payload))
        case A.ExprAuto():
            return F("exprAuto", witnessType=t(n.witness_type), payload=e(n.payload),
                     witnessName=opt_s(n.witness_name), witnessBound=opt_t(n.witness_bound))
        case A.ExprSelect():
            return F("exprSelect", target=e(n.target), field=qstr(n.field))
        case A.ExprIndex():
            return F("exprIndex", target=e(n.target), index=e(n.index))
        case A.ExprIndexAssign():
            return F("exprIndexAssign", target=e(n.target), index=e(n.index), value=e(n.value))
        case A.ExprVarCell():
            return F("exprVarCell", value=e(n.value))
        case A.ExprDerefCell():
            return F("exprDerefCell", target=e(n.target))
        case A.ExprVariantCheck():
            return F("exprVariantCheck", target=e(n.target), tag=qstr(n.tag))
        case A.ExprVariantAssert():
            return F("exprVariantAssert", target=e(n.target), tag=qstr(n.tag))
        case A.ExprCase():
            return F("exprCase", target=e(n.target), branches=vec("ast.CaseBranch", [
                f"tuple let tags = {strs(b.tags)} let binder = {opt_s(b.binder)} "
                f"let binderType = {opt_t(b.binder_type)} let body = {e(b.body)} end" for b in n.branches]),
                elseBranch=opt_e(n.else_branch))
        case A.ExprInspect():
            return F("exprInspect", target=e(n.target), branches=vec("ast.InspectBranch", [
                f"tuple let matchType = {t(b.match_type)} let binders = "
                + vec("ast.InspectBinder", [f"tuple let name = {qstr(nm)} let typeAnnot = {opt_t(ty)} end"
                                            for nm, ty in b.binders])
                + f" let body = {e(b.body)} end" for b in n.branches]),
                elseBranch=opt_e(n.else_branch))
        case A.ExprException():
            return F("exprException", name=qstr(n.name), typeAnnot=opt_t(n.type_annot))
        case A.ExprRaise():
            return F("exprRaise", exc=e(n.exc), payload=opt_e(n.payload), asType=opt_t(n.as_type))
        case A.ExprTry():
            return F("exprTry", body=e(n.body), branches=vec("ast.TryBranch", [
                f"tuple let excPattern = {e(b.exc_pattern)} let binder = {opt_s(b.binder)} "
                f"let binderType = {opt_t(b.binder_type)} let body = {e(b.body)} end" for b in n.branches]),
                elseBranch=opt_e(n.else_branch))
        case A.LetValueBinding():
            return F("declLetVal", name=qstr(n.name), value=e(n.value),
                     params=vec("ast.FormalParam", [formal_param(p) for p in n.params]),
                     typeAnnot=opt_t(n.type_annot), isRec=qbool(n.is_rec), isVar=qbool(n.is_var))
        case A.LetValueBindingGroup():
            return F("declLetValGroup", bindings=es(n.bindings))
        case A.TypeBinding():
            return F("declTypeBinding", name=qstr(n.name), typeVal=t(n.type_val),
                     params=vec("ast.TypeFormal", [type_formal(p) for p in n.params]),
                     bound=opt_t(n.bound), isRec=qbool(n.is_rec), isDef=qbool(n.is_def))
        case A.TypeBindingGroup():
            return F("declTypeBindingGroup", bindings=es(n.bindings))
        case A.DefKindBinding():
            return F("declDefKind", name=qstr(n.name), kindVal=t(n.kind_val))
        case A.ExprStmt():
            return F("declExprStmt", expr=e(n.expr))
    raise NotImplementedError(type(n).__name__)


def tuple_binding(x):
    return (f"tuple let name = {opt_s(x.name)} let value = {e(x.value)} let typeAnnot = {opt_t(x.type_annot)} "
            f"let isVar = {qbool(x.is_var)} end")


def tuple_field(x):
    if isinstance(x, A.TupleBinding):
        return f"option fieldVal of ast.TupleField with let val = {tuple_binding(x)} end"
    if isinstance(x, A.TupleBindingGroup):
        bindings = vec("ast.TupleFieldBinding", [tuple_binding(b) for b in x.bindings])
        return f"option fieldGroup of ast.TupleField with let val = {bindings} end"
    return f"option fieldDecl of ast.TupleField with let val = {e(x)} end"


def import_item(i):
    paths = None if i.module_paths is None else strs(i.module_paths)
    return (f"tuple let names = {strs(i.names)} let interfaceName = {qstr(i.interface_name)} "
            f"let modulePaths = {some('vector.T(String)', paths)} let interfacePath = {opt_s(i.interface_path)} end")


def imports(items):
    return vec("ast.ImportItem", [import_item(i) for i in items])


def phrase(n):
    F = lambda form_tag, **kw: f"ph({form('PhraseForm', form_tag, **kw)})"  # noqa: E731
    match n:
        case A.ImportPhrase():
            return F("phraseImport", phrase=f"tuple let items = {imports(n.items)} end")
        case A.InterfaceDecl():
            return F("phraseInterface", iface=f"tuple let name = {qstr(n.name)} let signatures = {vec('ast.Signature', [signature(s) for s in n.signatures])} "
                                              f"let imports = {imports(n.imports)} let isUnsound = {qbool(n.is_unsound)} end")
        case A.ModuleDecl():
            return F("phraseModule", modDecl=f"tuple let name = {qstr(n.name)} let interfaceName = "
                                             f"{qstr(n.interface_name)} let bindings = {es(n.bindings)} "
                                             f"let imports = {imports(n.imports)} let isUnsound = {qbool(n.is_unsound)} end")
        case A.BindingNode():
            return F("phraseDecl", decl=e(n))
        case A.Expr():
            return F("phraseExpr", expr=e(n))
    raise NotImplementedError(type(n).__name__)


PRELUDE = """import
    questlang/common/location : questlang/common/Location
    questlang/syntax/ast : questlang/syntax/Ast
    questlang/syntax/astprint : questlang/syntax/AstPrint
    collections/vector : collections/Vector
    util/maybe : util/Maybe
    writer : Writer
;
let sp = location.span("gen.quest" 0 0);
let ty(form: ast.TypeForm): ast.TypeExpr = ast.makeType(sp form);
let ex(form: ast.ExprForm): ast.Expr = ast.makeExpr(sp form);
let ph(form: ast.PhraseForm): ast.Phrase = ast.makePhrase(sp form);
let mV = option modeValue of ast.ParamMode end;
let mVar = option modeVar of ast.ParamMode end;
let mOut = option modeOut of ast.ParamMode end;
"""


def program_source(prog):
    # One function per phrase keeps each expression (and each C function) a manageable size
    HELPERS.clear()
    lines = []
    names = []
    for i, p in enumerate(prog.phrases):
        lines.append(f"let p{i}(): ast.Phrase = {phrase(p)};")
        names.append(f"p{i}()")
    lines = [PRELUDE] + HELPERS + lines
    lines.append(f"let prog = ast.makeProgram(sp {vec('ast.Phrase', names)});")
    lines.append("writer.putString(writer.output astprint.dump(prog));")
    lines.append('writer.putString(writer.output "\\n");')
    return "\n".join(lines) + "\n"


def parse(path: Path) -> A.Program:
    tok = Tokenizer.from_file(str(path))
    return parse_quest_program(tok.tokenize_all(), tok.source_map)


def generate_tests() -> None:
    for source in sorted(HERE.glob("*.quest")):
        prog = parse(source)
        header = (
            f"(* Generated by tests/astprint/generate.py from tests/astprint/{source.name}; do not edit. It builds the\n"
            f"   self-hosted AST of {source.name} and prints it with astprint.dump, which must print what ast_dump\n"
            "   prints. *)\n"
            "(* @skip-phase: tokenize, parse, typecheck *)\n"
            "(* @timeout: 300.0 *)\n"
        )
        program, golden = TEST_DIR / f"astprint_{source.stem}.quest", GOLDEN_DIR / f"astprint_{source.stem}.out"
        program.write_text(header + program_source(prog))
        golden.write_text(A.ast_dump(prog) + "\n")
        print(f"wrote {program.relative_to(ROOT_DIR)} and {golden.relative_to(ROOT_DIR)}")


def check(phase: str, workers: int) -> int:
    sources = sorted(
        p for d in ("lib", "questlang", "tests") for p in (ROOT_DIR / d).rglob("*.quest")
        if "abi" not in p.relative_to(ROOT_DIR).parts
    )
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        cases = []
        for path in sources:
            try:
                prog = parse(path)
            except Exception:
                continue  # files that are meant not to parse
            n = len(cases)
            (work / f"{n}.quest").write_text(program_source(prog))
            cases.append((path, A.ast_dump(prog) + "\n"))
        build = work / "build"

        def run(n: int) -> bool:
            cmd = [sys.executable, str(DRIVER), "-I", str(ROOT_DIR), "--build-dir", str(build),
                   "--stop-after", phase, str(work / f"{n}.quest")]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout + result.stderr == cases[n][1]

        # The first program builds the library modules the others share
        results = [run(0)] if cases else []
        with ThreadPoolExecutor(workers) as pool:
            results += list(pool.map(run, range(1, len(cases))))
    failures = [path for (path, _), ok in zip(cases, results) if not ok]
    for path in failures:
        print(f"MISMATCH {path.relative_to(ROOT_DIR)}")
    print(f"{len(cases) - len(failures)}/{len(cases)} files print the same AST in astprint and ast_dump")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="check every parseable .quest file in the repository")
    parser.add_argument("--c", action="store_true", help="with --check: compile the programs to C")
    parser.add_argument("--workers", type=int, default=8, help="with --check: programs run in parallel")
    args = parser.parse_args()
    if args.check:
        return check("run_c_compiled" if args.c else "interpret", args.workers)
    generate_tests()
    return 0


if __name__ == "__main__":
    sys.exit(main())
