"""The IR's textual form (docs/ir.md §10), for dumps, goldens, and debugging.

Variables print as their hints, made distinct within a unit by a numeric suffix (x, x.1, ...) in the order they are
bound, and temporaries (no hint) as %1, %2, ...; types print as Quest types, with alias names.
"""

from __future__ import annotations

import json
from typing import Optional

from quest.ir import nodes as ir
from quest.ir.walk import global_variables, statement_binders, walk_statements
from quest.types import format_type_compact


class _Printer:
    def __init__(self) -> None:
        self.names: dict[int, str] = {}
        self.used: dict[str, int] = {}
        self.lines: list[str] = []

    # Names

    def bind(self, var: ir.Var) -> str:
        if id(var) in self.names:
            return self.names[id(var)]
        hint = var.hint
        n = self.used.get(hint, 0)
        self.used[hint] = n + 1
        if not hint:
            # A temporary: numbered, apart from the program's own names
            name = f"%{n + 1}"
        else:
            name = hint if n == 0 else f"{hint}.{n}"
        self.names[id(var)] = name
        return name

    def name(self, var: ir.Var) -> str:
        # A variable used before (or without) its binder prints with a mark, which the verifier reports
        return self.names.get(id(var)) or f"{var.hint}?"

    def atom(self, a: ir.Atom) -> str:
        if isinstance(a, ir.Var):
            return self.name(a)
        v = a.value
        if v is None:
            return "ok"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, str):
            if a.shape.kind == "char":
                return repr(v)
            return json.dumps(v)
        return repr(v)

    def atoms(self, atoms: tuple[ir.Atom, ...]) -> str:
        return ", ".join(self.atom(a) for a in atoms)

    @staticmethod
    def type(t) -> str:
        return format_type_compact(t)

    def type_args(self, types: tuple) -> str:
        return f" [{' '.join(self.type(t) for t in types)}]" if types else ""

    def decl(self, var: ir.Var) -> str:
        return f"{self.bind(var)}: {self.type(var.type)}"

    # Operations

    def callee(self, var: Optional[ir.Var], module: Optional[ir.ModuleRef], member: Optional[str]) -> str:
        return f"{module.name}.{member}" if var is None else self.name(var)

    def op(self, o) -> str:
        match o:
            case ir.Var() | ir.Const():
                return self.atom(o)
            case ir.Prim(op=op, args=args):
                return f"prim {op}({self.atoms(args)})"
            case ir.Call(callee=callee, type_args=type_args, args=args, module=module, member=member):
                return f"call {self.callee(callee, module, member)}{self.type_args(type_args)}({self.atoms(args)})"
            case ir.TypeApp(callee=callee, type_args=type_args, module=module, member=member):
                return f"type_app {self.callee(callee, module, member)}{self.type_args(type_args)}"
            case ir.ModuleMember(module=module, member=member):
                return f"member {module.name}.{member}" if member is not None else f"module {module.name}"
            case ir.Builtin(name=name):
                return f"builtin {name}"
            case ir.External(symbol=symbol):
                return f"external {json.dumps(symbol)}"
            case ir.CallExternal(symbol=symbol, type_args=type_args, args=args):
                return f"call external {json.dumps(symbol)}{self.type_args(type_args)}({self.atoms(args)})"
            case ir.MakeClosure(code=code, captures=captures, type_args=type_args):
                return f"closure {self.name(code.var)} {{{self.atoms(captures)}}}{self.type_args(type_args)}"
            case ir.EnvField(env=env, index=index):
                return f"env_field({self.atom(env)}, {index})"
            case ir.Convert(value=v, plan=plan):
                return f"convert({self.atom(v)}, {plan.kind})"
            case ir.MakeTuple(args=args, type_components=type_components):
                types = "".join(f"Let {n} = {self.type(t)} " for n, t in type_components)
                return f"tuple({types}{self.atoms(args)})"
            case ir.TupleField(tuple=t, index=index):
                return f"tuple_field({self.atom(t)}, {index})"
            case ir.MakeRecord(fields=fields):
                return "record(" + ", ".join(
                    f"{'var ' if is_var else ''}{n} = {self.atom(a)}" for n, a, is_var in fields
                ) + ")"
            case ir.RecordField(record=r, name=name):
                return f"record_field({self.atom(r)}, {name})"
            case ir.MakeVariant(tag=tag, payload=payload):
                return f"variant({tag}{', ' + self.atom(payload) if payload is not None else ''})"
            case ir.MakeOption(tag=tag, payload=payload, ordinal=ordinal):
                head = tag if ordinal is None else f"#{self.atom(ordinal)}"
                return f"option({head}{', ' + self.atom(payload) if payload is not None else ''})"
            case ir.IsTag(value=v, tag=tag):
                return f"is_tag({self.atom(v)}, {tag})"
            case ir.Payload(value=v, tag=tag):
                return f"payload({self.atom(v)}, {tag})"
            case ir.Ordinal(value=v):
                return f"ordinal({self.atom(v)})"
            case ir.MakeArray(args=args):
                return f"array({self.atoms(args)})"
            case ir.ArrayRep(count=count, init=init):
                return f"array_rep({self.atom(count)}, {self.atom(init)})"
            case ir.Index(array=a, index=i):
                return f"index({self.atom(a)}, {self.atom(i)})"
            case ir.MakeAuto(witness=w, payload=p):
                return f"auto[{self.type(w)}]({self.atom(p)})"
            case ir.MakeException(name=name, payload_type=pt):
                payload = pt is not None and self.type(pt) != "Ok"
                return f"exception {name}{': ' + self.type(pt) if payload else ''}"
            case ir.ExceptionPayload(exception=e):
                return f"exception_payload({self.atom(e)})"
            case ir.Addr(var=var, base=base, name=name, index=index, cell=cell):
                if var is not None:
                    return f"addr {self.name(var)}"
                if cell is not None:
                    return f"cell({self.atom(cell)})"
                if name is not None:
                    return f"addr {self.atom(base)}.{name}"
                if isinstance(index, int):
                    return f"addr {self.atom(base)}.#{index}"
                return f"addr {self.atom(base)}[{self.atom(index)}]"
            case ir.Load(address=a):
                return f"load {self.atom(a)}"
            case _:
                raise TypeError(f"not an IR operation: {o!r}")

    # Statements

    def emit(self, depth: int, text: str) -> None:
        self.lines.append("  " * depth + text)

    def body(self, body: ir.Body, depth: int) -> None:
        for s in body.statements:
            self.statement(s, depth)

    def block(self, head: str, body: ir.Body, depth: int, tail: str = "}") -> None:
        self.emit(depth, head + " {")
        self.body(body, depth + 1)
        self.emit(depth, tail)

    def function(self, f: ir.Function, depth: int) -> None:
        tps = (" [" + " ".join(f"{tp.name}::{tp.kind}" for tp in f.type_params) + "]") if f.type_params else ""
        params = ", ".join(f"{'' if mode == 'value' else mode + ' '}{self.decl(v)}" for v, mode in f.params)
        # A lifted function's environment, which has no Quest type
        env = f" {{{self.bind(f.env)}}}" if f.env is not None else ""
        self.block(f"fun {self.name(f.var)}{env}{tps}({params}): {self.type(f.result_type)}", f.body, depth)

    def statement(self, s, depth: int) -> None:
        match s:
            case ir.Let(var=var, value=value):
                text = self.op(value)
                self.emit(depth, f"let {self.decl(var)} = {text}")
            case ir.VarDecl(var=var, init=init):
                if init is None:
                    self.emit(depth, f"var {self.decl(var)}")
                else:
                    self.emit(depth, f"var {self.decl(var)} = {self.atom(init)}")
            case ir.Declare(var=var):
                self.emit(depth, f"declare {self.decl(var)}")
            case ir.Assign(var=var, value=value):
                self.emit(depth, f"{self.name(var)} := {self.atom(value)}")
            case ir.Store(value=value, base=base, name=name, index=index, address=address):
                if address is not None:
                    target = f"*{self.atom(address)}"
                elif name is not None:
                    target = f"{self.atom(base)}.{name}"
                elif isinstance(index, int):
                    target = f"{self.atom(base)}.#{index}"
                else:
                    target = f"{self.atom(base)}[{self.atom(index)}]"
                self.emit(depth, f"store {target} := {self.atom(value)}")
            case ir.Do(value=value):
                self.emit(depth, f"do {self.op(value)}")
            case ir.Funs(functions=functions, recursive=recursive):
                # Members of a recursive group are named before their bodies, which refer to one another
                if recursive:
                    for f in functions:
                        self.bind(f.var)
                self.emit(depth, "funs rec {" if recursive else "funs {")
                for f in functions:
                    if not recursive:
                        self.bind(f.var)
                    self.function(f, depth + 1)
                self.emit(depth, "}")
            case ir.LetRec(vars=vars_, body=body):
                decls = ", ".join(self.decl(v) for v in vars_)
                self.block(f"let rec ({decls})", body, depth)
            case ir.If(cond=cond, then_body=then_body, else_body=else_body):
                self.emit(depth, f"if {self.atom(cond)} {{")
                self.body(then_body, depth + 1)
                if else_body.statements:
                    self.emit(depth, "} else {")
                    self.body(else_body, depth + 1)
                self.emit(depth, "}")
            case ir.Switch(value=value, cases=cases, else_body=else_body):
                self.emit(depth, f"switch tag({self.atom(value)}) {{")
                for c in cases:
                    binder = f" ({self.decl(c.binder)})" if c.binder is not None else ""
                    self.block(f"case {', '.join(c.tags)}{binder}:", c.body, depth + 1)
                if else_body is not None:
                    self.block("else:", else_body, depth + 1)
                self.emit(depth, "}")
            case ir.Inspect(value=value, cases=cases, else_body=else_body):
                self.emit(depth, f"inspect {self.atom(value)} {{")
                for c in cases:
                    binders = ", ".join(self.decl(b) for b in c.binders)
                    exact = " exact" if c.exact else ""
                    self.block(f"case {self.type(c.match_type)}{exact} ({binders}):", c.body, depth + 1)
                if else_body is not None:
                    self.block("else:", else_body, depth + 1)
                self.emit(depth, "}")
            case ir.Loop(label=label, body=body):
                self.block(f"loop {label}", body, depth)
            case ir.Try(body=body, exception=exception, handler=handler, catches=catches):
                if catches is None:
                    self.emit(depth, "try {")
                elif catches is ir.CATCH_ALL:
                    self.emit(depth, "try catching all {")
                else:
                    self.emit(depth, f"try catching ({self.atoms(catches)}) {{")
                self.body(body, depth + 1)
                self.emit(depth, f"}} handle ({self.decl(exception)}) {{")
                self.body(handler, depth + 1)
                self.emit(depth, "}")
            case ir.Join(label=label, params=params, continuation=continuation, body=body):
                decls = ", ".join(self.decl(p) for p in params)
                self.emit(depth, f"join {label}({decls}) {{")
                self.body(continuation, depth + 1)
                self.emit(depth, "} in {")
                self.body(body, depth + 1)
                self.emit(depth, "}")
            case ir.Echo(value=value, type=t, prefix=prefix):
                self.emit(depth, f"echo {json.dumps(prefix)} {self.atom(value)} : {self.type(t)}")
            case ir.EchoText(text=text):
                self.emit(depth, f"echo {json.dumps(text)}")
            case ir.Return(value=value):
                self.emit(depth, f"return {self.atom(value)}")
            case ir.Jump(label=label, args=args):
                self.emit(depth, f"jump {label}({self.atoms(args)})")
            case ir.Break(label=label):
                self.emit(depth, f"break {label}")
            case ir.Continue(label=label):
                self.emit(depth, f"continue {label}")
            case ir.Raise(exception=e, payload=p):
                self.emit(depth, f"raise {self.atom(e)}{' with ' + self.atom(p) if p is not None else ''}")
            case ir.Reraise(exception=e):
                self.emit(depth, f"reraise {self.atom(e)}")
            case ir.Unreachable():
                self.emit(depth, "unreachable")
            case _:
                raise TypeError(f"not an IR statement: {s!r}")


def format_unit(unit: ir.Unit) -> str:
    """The textual form of a unit: its modules, then its main body."""
    p = _Printer()
    for i in unit.imports:
        p.emit(0, f"import {i.name} = {json.dumps(i.module_path)} : {i.interface_path}")
    # The unit's functions, after closure conversion, are named before any is printed, as closures refer to them, and
    # so are the globals they use (the variables the top levels bind outside loops), printed after them
    for f in unit.functions:
        p.bind(f.var)
    if unit.functions:
        globals_ = global_variables(unit)
        for body in [*(m.init for m in unit.modules), unit.main]:
            for s in walk_statements(body, into_functions=False):
                for v in statement_binders(s):
                    if id(v) in globals_:
                        p.bind(v)
    for f in unit.functions:
        p.function(f, 0)
    for m in unit.modules:
        p.emit(0, f"module {m.name} : {m.interface_name} {{")
        p.body(m.init, 1)
        p.emit(1, "export " + ", ".join(f"{n} = {p.name(v)}" for n, v in m.members.items()))
        p.emit(0, "}")
    p.block("main", unit.main, 0)
    return "\n".join(p.lines) + "\n"


def format_body(body: ir.Body) -> str:
    p = _Printer()
    p.body(body, 0)
    return "\n".join(p.lines) + "\n"
