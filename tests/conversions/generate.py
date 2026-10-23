"""Generates the conversion matrix: golden tests of values converted between representations in compiled code.

Compiled code lays out a type that mentions a type parameter generically in polymorphic code (a QVal for each value
of the parameter) and natively elsewhere, and converts values between the two, and between subtypes, wherever a value
crosses: polymorphic calls, closures, type applications, dynamic values, subsumption, and stores (docs/ir.md §8.3,
docs/c-representation.md §5.1). The interpreter has no layouts, so its output is the expected output.

Each context below gives one program, tests/source/conversions/CONTEXT.quest, exercising every shape (a type operator
over a type parameter) at every type argument; each cell prints a label, so that a failure points at its cell.

    python tests/conversions/generate.py           # regenerate the programs
    python run_tests.py -k conversions/ --update-golden    # then regenerate their goldens (from the interpreter)

Cells listed in KNOWN_FAILURES compile but behave differently in C, for a recorded reason; they are generated into
CONTEXT_known_failures.quest, which skips the compiled phase. Cells listed in REJECTED are compile-time errors of C
generation (conversions that would copy mutable data), checked by tests/python/test_conversion_rejections.py.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT_DIR / "tests" / "source" / "conversions"


@dataclass(frozen=True)
class Arg:
    """A type argument: its name, two sample values, and how to print a value of it."""
    name: str
    value: str
    other: str
    show: str  # a format with one {} for the value

    def shown(self, expr: str) -> str:
        return self.show.format(expr)


ARGS = (
    Arg("Int", "7", "8", "conv.int({})"),
    Arg("Bool", "true", "false", "conv.bool({})"),
    Arg("Real", "2.5", "3.5", "conv.real({})"),
    Arg("Char", "'q'", "'r'", "conv.char({})"),
    Arg("String", '"s"', '"t"', "{}"),
    Arg("P", "record a = 4 end", "record a = 9 end", "conv.int({}.a)"),
    Arg("V", "variant p of V with 5 end", "variant p of V with 6 end", "conv.int(case {} when p with k then k else 0 end)"),
    Arg("B", "tuple let a = 6 end", "tuple let a = 7 end", "conv.int({}.a)"),
)

ARG_DECLS = """Let P = Record a: Int end;
Let V = Variant p: Int q: Bool end;
Let B = Tuple a: Int end;"""


@dataclass(frozen=True)
class Shape:
    """A type over a type parameter: its declaration (if any), the type at an argument, how to make a value of it from
    a value of the argument, and how to get the argument's value back."""
    name: str
    decl: Optional[str]
    type_of: str  # a format with {A}
    make: str  # a format with {A} and {v}
    get: str  # a format with {s}
    # A pointer to a tuple or option (or a recursive one), whose identity `is` can observe
    has_identity: bool = False
    # A wider type of which the shape at {A} is a supertype, and a value of it made from {v}
    wider: Optional[tuple[str, str]] = None

    def at(self, a: str) -> str:
        return self.type_of.format(A=a)

    def made(self, a: str, v: str) -> str:
        return self.make.format(A=a, v=v)

    def got(self, s: str) -> str:
        return self.get.format(s=s)


SHAPES = (
    Shape("Bare", None, "{A}", "{v}", "{s}"),
    Shape(
        "Box", "Let Box = Fun(A::TYPE) Tuple x: A end;", "Box({A})", "tuple let x = {v} end", "{s}.x",
        has_identity=True, wider=("Tuple x: {A} y: Int end", "tuple let x = {v} let y = 1 end"),
    ),
    Shape(
        "Wide", "Let Wide = Fun(A::TYPE) Tuple n: Int x: A end;", "Wide({A})", "tuple let n = 1 let x = {v} end",
        "{s}.x", has_identity=True,
    ),
    Shape(
        "Maybe", "Let Maybe = Fun(A::TYPE) Option none some with value: A end end;", "Maybe({A})",
        "option some of Maybe({A}) with let value = {v} end", "{s}!some.value", has_identity=True,
    ),
    Shape(
        "Holder", "Let Holder = Fun(A::TYPE) Record x: A end;", "Holder({A})", "record x = {v} end", "{s}.x",
        wider=("Record x: {A} y: Int end", "record x = {v} y = 1 end"),
    ),
    Shape(
        "Tagged", "Let Tagged = Fun(A::TYPE) Variant v: A n: Int end;", "Tagged({A})",
        "variant v of Tagged({A}) with {v} end", "{s}!v",
        wider=("Variant v: {A} end", "variant v of Variant v: {A} end with {v} end"),
    ),
    Shape("Arr", None, "Array({A})", "array of {v} end", "{s}[0]", has_identity=True),
    Shape("Thunk", "Let Thunk = Fun(A::TYPE) All(u: Int) A;", "Thunk({A})", "fun(u: Int): {A} {v}", "{s}(0)"),
    Shape(
        "List", "Let Rec List(A::TYPE) = Option nil cons with head: A tail: List(A) end end;", "List({A})",
        "option cons of List({A}) with let head = {v} let tail = option nil of List({A}) end end", "{s}!cons.head", has_identity=True,
    ),
    Shape(
        "Nest", "Let Nest = Fun(A::TYPE) Tuple first: Box(A) n: Int end;", "Nest({A})",
        "tuple let first = tuple let x = {v} end let n = 2 end", "{s}.first.x", has_identity=True,
    ),
)


@dataclass(frozen=True)
class Context:
    """A place where values convert: generic definitions per shape, and the code of one cell (shape, argument)."""
    name: str
    description: str
    defs: Callable[[Shape], list[str]]
    cell: Callable[[Shape, Arg, str], list[str]]  # the cell's statements, given a unique suffix for its names
    applies: Callable[[Shape, Arg], bool] = lambda shape, arg: True
    imports: tuple[str, ...] = ()


def _print(label: str, expr: str) -> str:
    return f'print("{label}: " <> {expr});'


def _direct_defs(shape: Shape) -> list[str]:
    return [
        f"let get{shape.name}(A::TYPE s: {shape.at('A')}): A = {shape.got('s')};",
        f"let make{shape.name}(A::TYPE v: A): {shape.at('A')} = {shape.made('A', 'v')};",
    ]


def _direct_cell(shape: Shape, arg: Arg, k: str) -> list[str]:
    t = arg.name
    return [
        f"let s{k}: {shape.at(t)} = {shape.made(t, arg.value)};",
        _print(f"{shape.name}/{t} argument", arg.shown(f"get{shape.name}(:{t} s{k})")),
        _print(f"{shape.name}/{t} result", arg.shown(shape.got(f"make{shape.name}(:{t} {arg.other})"))),
    ]


def _first_class_defs(shape: Shape) -> list[str]:
    s_a = shape.at("A")
    return _direct_defs(shape) + [
        f"let getF{shape.name}: All(A::TYPE s: {s_a}) A = get{shape.name};",
        f"let makeF{shape.name}: All(A::TYPE v: A) {s_a} = make{shape.name};",
    ]


def _first_class_cell(shape: Shape, arg: Arg, k: str) -> list[str]:
    t = arg.name
    return [
        f"let s{k}: {shape.at(t)} = {shape.made(t, arg.value)};",
        _print(f"{shape.name}/{t} argument", arg.shown(f"getF{shape.name}(:{t} s{k})")),
        _print(f"{shape.name}/{t} result", arg.shown(shape.got(f"makeF{shape.name}(:{t} {arg.other})"))),
    ]


def _type_app_cell(shape: Shape, arg: Arg, k: str) -> list[str]:
    t = arg.name
    return [
        f"let s{k}: {shape.at(t)} = {shape.made(t, arg.value)};",
        f"let g{k} = get{shape.name}(:{t});",
        f"let m{k} = make{shape.name}(:{t});",
        _print(f"{shape.name}/{t} argument", arg.shown(f"g{k}(s{k})")),
        _print(f"{shape.name}/{t} result", arg.shown(shape.got(f"m{k}({arg.other})"))),
    ]


def _closure_defs(shape: Shape) -> list[str]:
    s_a = shape.at("A")
    return [
        f"let apply{shape.name}(A::TYPE f: All(s: {s_a}) A s: {s_a}): A = f(s);",
        f"let build{shape.name}(A::TYPE f: All(v: A) {s_a} v: A): {s_a} = f(v);",
        f"let getter{shape.name}(A::TYPE): All(s: {s_a}) A = fun(s: {s_a}): A {shape.got('s')};",
    ]


def _closure_cell(shape: Shape, arg: Arg, k: str) -> list[str]:
    t = arg.name
    s_t = shape.at(t)
    return [
        f"let s{k}: {s_t} = {shape.made(t, arg.value)};",
        _print(
            f"{shape.name}/{t} closure argument",
            arg.shown(f"apply{shape.name}(:{t} fun(s: {s_t}): {t} {shape.got('s')} s{k})"),
        ),
        _print(
            f"{shape.name}/{t} closure result",
            arg.shown(shape.got(f"build{shape.name}(:{t} fun(v: {t}): {s_t} {shape.made(t, 'v')} {arg.other})")),
        ),
        _print(f"{shape.name}/{t} closure from generic code", arg.shown(f"getter{shape.name}(:{t})(s{k})")),
    ]


def _nested_defs(shape: Shape) -> list[str]:
    return []


NESTED_PRELUDE = [
    "let id(A::TYPE x: A): A = x;",
    "let boxed(A::TYPE x: A): Tuple x: A end = tuple let x = x end;",
    "let idF: All(A::TYPE x: A) A = id;",
]


def _nested_cell(shape: Shape, arg: Arg, k: str) -> list[str]:
    t = arg.name
    s_t = shape.at(t)
    return [
        f"let s{k}: {s_t} = {shape.made(t, arg.value)};",
        _print(f"{shape.name}/{t} as a type argument", arg.shown(shape.got(f"id(:{s_t} s{k})"))),
        _print(f"{shape.name}/{t} as a component", arg.shown(shape.got(f"boxed(:{s_t} s{k}).x"))),
        _print(f"{shape.name}/{t} through a first-class value", arg.shown(shape.got(f"idF(:{s_t} s{k})"))),
    ]


def _dynamic_defs(shape: Shape) -> list[str]:
    s_a = shape.at("A")
    return [
        f"let pack{shape.name}(A::TYPE s: {s_a}): Dynamic = dynamic.new(:{s_a} s);",
        f"let unpack{shape.name}(A::TYPE d: Dynamic): A = {shape.got(f'dynamic.be(:{s_a} d)')};",
    ]


def _dynamic_cell(shape: Shape, arg: Arg, k: str) -> list[str]:
    t = arg.name
    s_t = shape.at(t)
    return [
        f"let s{k}: {s_t} = {shape.made(t, arg.value)};",
        _print(
            f"{shape.name}/{t} packed generically",
            arg.shown(shape.got(f"dynamic.be(:{s_t} pack{shape.name}(:{t} s{k}))")),
        ),
        _print(
            f"{shape.name}/{t} unpacked generically",
            arg.shown(f"unpack{shape.name}(:{t} dynamic.new(:{s_t} s{k}))"),
        ),
    ]


def _subsumption_cell(shape: Shape, arg: Arg, k: str) -> list[str]:
    t = arg.name
    wider_t, wider_v = shape.wider
    return [
        f"let w{k}: {wider_t.format(A=t)} = {wider_v.format(A=t, v=arg.value)};",
        f"let s{k}: {shape.at(t)} = w{k};",
        _print(f"{shape.name}/{t} subsumed", arg.shown(shape.got(f"s{k}"))),
        _print(f"{shape.name}/{t} subsumed argument", arg.shown(f"get{shape.name}(:{t} w{k})")),
    ]


def _store_defs(shape: Shape) -> list[str]:
    s_a = shape.at("A")
    return [
        f"let put{shape.name}(A::TYPE a: Array({s_a}) s: {s_a}): Ok = a[0] := s;",
        f"let first{shape.name}(A::TYPE a: Array({s_a})): A = {shape.got('a[0]')};",
    ]


def _store_cell(shape: Shape, arg: Arg, k: str) -> list[str]:
    t = arg.name
    s_t = shape.at(t)
    return [
        f"let a{k}: Array({s_t}) = array of {shape.made(t, arg.value)} end;",
        _print(f"{shape.name}/{t} read generically", arg.shown(f"first{shape.name}(:{t} a{k})")),
        f"put{shape.name}(:{t} a{k} {shape.made(t, arg.other)});",
        _print(f"{shape.name}/{t} stored generically", arg.shown(shape.got(f"a{k}[0]"))),
    ]


def _identity_defs(shape: Shape) -> list[str]:
    s_a = shape.at("A")
    return [
        f"let same{shape.name}(A::TYPE s: {s_a}): {s_a} = s;",
        f"let sameF{shape.name}: All(A::TYPE s: {s_a}) {s_a} = same{shape.name};",
    ]


def _identity_cell(shape: Shape, arg: Arg, k: str) -> list[str]:
    t = arg.name
    return [
        f"let s{k}: {shape.at(t)} = {shape.made(t, arg.value)};",
        _print(f"{shape.name}/{t} identity", f"conv.bool(same{shape.name}(:{t} s{k}) is s{k})"),
        _print(f"{shape.name}/{t} identity through a first-class value", f"conv.bool(sameF{shape.name}(:{t} s{k}) is s{k})"),
    ]


CONTEXTS = (
    Context("direct_calls", "direct calls of polymorphic functions, as arguments and results", _direct_defs, _direct_cell),
    Context(
        "first_class", "calls of polymorphic functions through first-class values, which are not specialized",
        _first_class_defs, _first_class_cell,
    ),
    Context(
        "type_application", "polymorphic functions applied to types only, used as values", _direct_defs, _type_app_cell,
    ),
    Context(
        "closures", "closures passed to and returned from polymorphic functions", _closure_defs, _closure_cell,
        applies=lambda shape, arg: shape.name != "Bare",
    ),
    Context(
        "type_arguments", "the shapes themselves as type arguments, and as components of generic tuples",
        _nested_defs, _nested_cell, applies=lambda shape, arg: shape.name != "Bare",
    ),
    Context(
        "dynamic", "dynamic values made and narrowed in generic code", _dynamic_defs, _dynamic_cell,
        # The type checker rejects dynamic values whose types mention a type parameter inside mutable data
        applies=lambda shape, arg: shape.name not in ("Bare", "Arr"), imports=("dynamic: Dynamic",),
    ),
    Context(
        "subsumption", "values of wider types used at the shapes, directly and as arguments", _direct_defs,
        _subsumption_cell, applies=lambda shape, arg: shape.wider is not None,
    ),
    Context(
        "stores", "arrays of the shapes read and written by generic code", _store_defs, _store_cell,
        applies=lambda shape, arg: shape.name != "Bare",
    ),
    Context(
        "identity", "identity (is) of values passed through polymorphic functions", _identity_defs, _identity_cell,
        applies=lambda shape, arg: shape.has_identity,
    ),
)

COPIES_CHANGE_IDENTITY = "the task Conversions that copy change object identity in C"

# (context, shape, argument) -> why compiled code behaves differently (a docs/tasklist.md task where there is one)
KNOWN_FAILURES: dict[tuple[str, str, str], str] = {
    ("identity", shape, arg): f"a copy through the first-class value ({COPIES_CHANGE_IDENTITY})"
    for shape in ("Box", "Wide", "Maybe", "List", "Nest")
    for arg in ("P", "V")
}

# (context, shape, argument) -> the compile-time error of C generation: unspecialized calls that would have to copy
# mutable data laid out differently (an array of records or variants; an array of closures returning a value that
# a register holds differently from a QVal)
MUTABLE_DATA_ERROR = "would copy mutable data"
REJECTED: dict[tuple[str, str, str], str] = {
    **{(ctx, "Arr", arg): MUTABLE_DATA_ERROR for ctx in ("first_class", "type_application", "identity") for arg in ("P", "V")},
    **{("stores", "Thunk", arg): MUTABLE_DATA_ERROR for arg in ("Bool", "Real", "Char")},
}


def _program(context: Context, cells: list[tuple[Shape, Arg]], known: bool) -> str:
    shapes = [s for s in SHAPES if any(cs is s for cs, _ in cells)]
    lines = [
        f"(* Generated by tests/conversions/generate.py; do not edit. Conversion matrix: {context.description}. *)",
    ]
    if known:
        lines.append(
            "(* Cells that compiled code gets wrong, each for the reason given, so the compiled phase is skipped *)"
        )
        lines.append("(* @skip-phase: tokenize, parse, typecheck, ir_core, run_c_compiled *)")
    else:
        lines.append("(* @skip-phase: tokenize, parse, typecheck, ir_core *)")
    lines.append("")
    lines.append("import writer: Writer;")
    lines.append("import conv: Conv;")
    lines.extend(f"import {imp};" for imp in context.imports)
    lines.append("")
    lines.append('let print(s: String): Ok = writer.putString(writer.output s <> "\\n");')
    lines.append(ARG_DECLS)
    for shape in SHAPES:
        if shape.decl is not None and (shape in shapes or shape.name == "Box"):
            lines.append(shape.decl)
    if context.name == "type_arguments":
        lines.extend(NESTED_PRELUDE)
    for shape in shapes:
        lines.append("")
        lines.extend(context.defs(shape))
    for i, (shape, arg) in enumerate(cells):
        lines.append("")
        reason = KNOWN_FAILURES.get((context.name, shape.name, arg.name))
        if reason is not None:
            lines.append(f"(* {shape.name}/{arg.name}: {reason} *)")
        lines.extend(context.cell(shape, arg, f"N{i}"))
    return "\n".join(lines) + "\n"


def cells_of(context: Context) -> list[tuple[Shape, Arg]]:
    return [(shape, arg) for shape in SHAPES for arg in ARGS if context.applies(shape, arg)]


def program_for(context_name: str, shape_name: str, arg_name: str) -> str:
    """The program of one cell alone (for the unit test of rejected cells)."""
    context = next(c for c in CONTEXTS if c.name == context_name)
    shape = next(s for s in SHAPES if s.name == shape_name)
    arg = next(a for a in ARGS if a.name == arg_name)
    return _program(context, [(shape, arg)], known=False)


def generate() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for context in CONTEXTS:
        cells = cells_of(context)
        regular = [
            c for c in cells
            if (context.name, c[0].name, c[1].name) not in KNOWN_FAILURES
            and (context.name, c[0].name, c[1].name) not in REJECTED
        ]
        known = [c for c in cells if (context.name, c[0].name, c[1].name) in KNOWN_FAILURES]
        for name, group, is_known in ((context.name, regular, False), (f"{context.name}_known_failures", known, True)):
            path = OUT_DIR / f"{name}.quest"
            if group:
                path.write_text(_program(context, group, is_known))
                written.append(path)
            elif path.exists():
                path.unlink()
    return written


if __name__ == "__main__":
    for path in generate():
        print(path.relative_to(ROOT_DIR))
    sys.exit(0)
