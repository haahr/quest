"""The IR verifier (docs/ir.md §9): checks a unit's invariants for its stage, after every pass, in tests.

Core invariants, checked here:

- every operation's arguments are atoms (variables or constants);
- every variable is bound by exactly one binder, and used only in its scope: after its let or declaration in the
  same body (or a body within it), within its function, case, handler, or join point's continuation;
- a module reference is to a module the unit defines or imports;
- a function does not use a mutable variable of an enclosing function (closures do not capture mutable locals;
  mutable variables of a unit's or module's top level are globals, which any function may use);
- a jump names a join point whose body encloses it, and passes as many values as the join point has parameters; a
  break or continue names an enclosing loop; neither crosses a function's boundary;
- a return occurs only in a function's body;
- a terminator is the last statement of its body;
- an ordinal, and an option made by ordinal, record the cases of the option's static type as written, the same
  cases as its shape's (in any order), and an option's payload records its case's ordinal.

After closure conversion (the closed stage), also: no funs statement remains; every closure is of one of the unit's
functions; and those functions use only their parameters, their environment, and the unit's globals (the variables
its top levels bind outside loops).

After the represent pass (the represented stage), also: every value is used in the representation its use requires
(a let's copy, an assignment, a return, a jump's argument, and a call's arguments and result have the C
representations of what they bind, assign, return, or pass to), the conversions between being convert operations.

After the describe pass (the described stage), also: every run-time use of a type has its descriptor operands (type
arguments, auto values' witnesses, inspect cases and arms, `is` of QVal words, record literals, stored field reads,
echo, and the plans that convert by descriptor), and a function its type parameters' descriptor variables; every
descriptor variable an operand uses is bound where it is used (by the enclosing function, by the thunk of the adapt
plan or type application it is in, which may use only its own, or by the inspect whose arm it is in) and of the
descriptor type; no static descriptor or template mentions a type parameter whose descriptor is in scope (it must be
described by its variable) or, in a thunk, one of the enclosing function's; and the static descriptors and tables
operations refer to are the unit's static data.

verify_unit returns the problems found; check_unit raises if there are any. The verifier runs when
QUEST_CHECK_IR=1, which the test runners set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields, is_dataclass
from typing import Optional

from quest.ir import nodes as ir
from quest.ir.walk import global_variables


def ir_checks_enabled() -> bool:
    return os.environ.get("QUEST_CHECK_IR") == "1"


@dataclass(frozen=True)
class _Scope:
    """What is in scope at a point: variables, join points (label to arity), loops, and the enclosing function."""
    vars: frozenset[int]
    joins: tuple[tuple[str, int], ...] = ()
    loops: tuple[str, ...] = ()
    in_function: bool = False
    # Mutable variables of enclosing functions, which a nested function must not use
    outer_mutables: frozenset[int] = frozenset()
    # Mutable variables of the current function (or top level), and whether this is a top level (unit or module)
    local_mutables: frozenset[int] = frozenset()
    top_level: bool = True

    def with_vars(self, *vs: ir.Var) -> _Scope:
        mutables = self.local_mutables | {id(v) for v in vs if v.mutable}
        return _Scope(self.vars | {id(v) for v in vs}, self.joins, self.loops, self.in_function, self.outer_mutables,
                      mutables, self.top_level)


class _Verifier:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.bound: set[int] = set()
        # The modules the unit defines and imports, which module references must be
        self.modules: set[int] = set()
        # After closure conversion, the unit's functions, which closures must be of (None before)
        self.functions: Optional[set[int]] = None
        self.represented = False

    def problem(self, text: str) -> None:
        self.problems.append(text)

    def bind(self, var: ir.Var, where: str) -> None:
        if id(var) in self.bound:
            self.problem(f"{where}: variable '{var.hint}' is bound more than once")
        self.bound.add(id(var))
        if var.shape is None:
            self.problem(f"{where}: variable '{var.hint}' has no shape")

    def use(self, a: ir.Atom, scope: _Scope, where: str) -> None:
        if isinstance(a, ir.Const):
            return
        if not isinstance(a, ir.Var):
            self.problem(f"{where}: an argument is not an atom: {type(a).__name__}")
            return
        if id(a) not in scope.vars:
            self.problem(f"{where}: variable '{a.hint}' is used outside its scope")
        elif id(a) in scope.outer_mutables:
            self.problem(f"{where}: function uses mutable variable '{a.hint}' of an enclosing function")

    def operation(self, o, scope: _Scope, where: str) -> None:
        if isinstance(o, (ir.Var, ir.Const)):
            self.use(o, scope, where)
            return
        if not is_dataclass(o) or isinstance(o, (ir.Body, ir.Function)):
            self.problem(f"{where}: not an operation: {type(o).__name__}")
            return
        if isinstance(o, ir.Convert) and not self.represented:
            self.problem(f"{where}: convert before the represent pass")
        if isinstance(o, (ir.MakeClosure, ir.EnvField)) and self.functions is None:
            self.problem(f"{where}: {type(o).__name__} before closure conversion")
        if isinstance(o, ir.MakeClosure) and self.functions is not None and id(o.code) not in self.functions:
            self.problem(f"{where}: a closure of a function that is not the unit's")
        for f in fields(o):
            v = getattr(o, f.name)
            if f.name == "type_components" or f.name in ir.DESCRIPTOR_FIELDS:
                continue
            if f.name == "module":
                if v is not None and id(v) not in self.modules:
                    self.problem(f"{where}: reference to a module that is not the unit's or imported by it")
                continue
            if isinstance(v, (ir.Var, ir.Const)):
                self.use(v, scope, where)
            elif isinstance(v, tuple):
                for item in v:
                    if isinstance(item, (ir.Var, ir.Const)):
                        self.use(item, scope, where)
                    elif isinstance(item, tuple):
                        # Record fields: (name, atom, is_var)
                        for part in item:
                            if isinstance(part, (ir.Var, ir.Const)):
                                self.use(part, scope, where)

    def option_cases(self, o, var: ir.Var, where: str) -> None:
        """Checks the cases an option operation counts ordinals in (ir.Ordinal, ir.MakeOption, ir.Payload)."""
        from quest.codegen.layout import resolved_shape
        from quest.ir.shapes import shape

        def option_shape(t):
            s = resolved_shape(shape(t)) if t is not None else None
            return s if s is not None and s.kind == "option" else None

        def check(cases: tuple[str, ...], t) -> None:
            s = option_shape(t)
            if s is not None and sorted(cases) != sorted(c.name for c in s.cases):
                self.problem(f"{where}: an ordinal counts in cases ({' '.join(cases)}) of an option of type {t}")

        match o:
            case ir.Ordinal(value=v, cases=cases):
                check(cases, v.type if isinstance(v, ir.Var) else None)
            case ir.MakeOption(ordinal=ordinal, cases=cases) if ordinal is not None:
                check(cases, var.type)
            case ir.Payload(value=ir.Var() as v, tag=tag, ordinal=ordinal):
                if option_shape(v.type) is not None and ordinal is None:
                    self.problem(f"{where}: the payload of option case {tag} without its ordinal")

    def function(self, f: ir.Function, scope: _Scope) -> None:
        where = f"function '{f.var.hint}'"
        # A nested function may use the enclosing functions' values but not their mutable variables; the top level's
        # mutable variables are globals
        outer_mutables = scope.outer_mutables | (frozenset() if scope.top_level else scope.local_mutables)
        inner = _Scope(scope.vars, (), (), True, outer_mutables, frozenset(), False)
        if f.env is not None:
            self.bind(f.env, where)
            inner = inner.with_vars(f.env)
        for v, mode in f.params:
            self.bind(v, where)
            if mode not in ("value", "var", "out"):
                self.problem(f"{where}: parameter '{v.hint}' has mode '{mode}'")
            if (mode != "value") != v.mutable:
                self.problem(f"{where}: parameter '{v.hint}' is {mode} but {'' if v.mutable else 'not '}mutable")
        inner = inner.with_vars(*(v for v, _ in f.params))
        self.body(f.body, inner, where)

    def body(self, body: ir.Body, scope: _Scope, where: str) -> _Scope:
        for i, s in enumerate(body.statements):
            if isinstance(s, ir.TERMINATORS) and i != len(body.statements) - 1:
                self.problem(f"{where}: a {type(s).__name__.lower()} is followed by other statements")
            scope = self.statement(s, scope, where)
        return scope

    def statement(self, s, scope: _Scope, where: str) -> _Scope:
        match s:
            case ir.Let(var=var, value=value):
                self.operation(value, scope, where)
                self.option_cases(value, var, where)
                self.bind(var, where)
                if var.mutable:
                    self.problem(f"{where}: let binds mutable variable '{var.hint}'")
                return scope.with_vars(var)
            case ir.VarDecl(var=var, init=init):
                if init is not None:
                    self.use(init, scope, where)
                self.bind(var, where)
                if not var.mutable:
                    self.problem(f"{where}: var declares immutable variable '{var.hint}'")
                return scope.with_vars(var)
            case ir.Assign(var=var, value=value):
                self.use(var, scope, where)
                self.use(value, scope, where)
                if not var.mutable:
                    self.problem(f"{where}: assignment to immutable variable '{var.hint}'")
            case ir.Store():
                self.operation(s, scope, where)
            case ir.Do(value=value):
                self.operation(value, scope, where)
            case ir.Funs(functions=functions, recursive=recursive):
                if self.functions is not None:
                    self.problem(f"{where}: a funs statement after closure conversion")
                for f in functions:
                    self.bind(f.var, where)
                inner = scope.with_vars(*(f.var for f in functions)) if recursive else scope
                for f in functions:
                    self.function(f, inner)
                return scope.with_vars(*(f.var for f in functions))
            case ir.LetRec(vars=vars_, body=body):
                # The body computes the variables' values (binding them with lets), and closures it makes may refer
                # to them; they are in scope after it
                inner = scope.with_vars(*vars_)
                self.body(body, inner, where)
                return scope.with_vars(*vars_)
            case ir.If(cond=cond, then_body=then_body, else_body=else_body):
                self.use(cond, scope, where)
                self.body(then_body, scope, where)
                self.body(else_body, scope, where)
            case ir.Switch(value=value, cases=cases, else_body=else_body):
                self.use(value, scope, where)
                for c in cases:
                    inner = scope
                    if c.binder is not None:
                        self.bind(c.binder, where)
                        inner = scope.with_vars(c.binder)
                    self.body(c.body, inner, where)
                if else_body is not None:
                    self.body(else_body, scope, where)
            case ir.Inspect(value=value, cases=cases, else_body=else_body):
                self.use(value, scope, where)
                for c in cases:
                    for b in c.binders:
                        self.bind(b, where)
                    self.body(c.body, scope.with_vars(*c.binders), where)
                if else_body is not None:
                    self.body(else_body, scope, where)
            case ir.Loop(label=label, body=body):
                if label in scope.loops:
                    self.problem(f"{where}: loop label '{label}' is already in use")
                inner = _Scope(scope.vars, scope.joins, scope.loops + (label,), scope.in_function,
                               scope.outer_mutables, scope.local_mutables, scope.top_level)
                self.body(body, inner, where)
            case ir.Try(body=body, exception=exception, handler=handler, catches=catches):
                if isinstance(catches, tuple):
                    for c in catches:
                        self.use(c, scope, where)
                self.body(body, scope, where)
                self.bind(exception, where)
                self.body(handler, scope.with_vars(exception), where)
            case ir.Join(label=label, params=params, continuation=continuation, body=body):
                if any(lbl == label for lbl, _ in scope.joins):
                    self.problem(f"{where}: join label '{label}' is already in use")
                for p in params:
                    self.bind(p, where)
                self.body(continuation, scope.with_vars(*params), where)
                inner = _Scope(scope.vars, scope.joins + ((label, len(params)),), scope.loops, scope.in_function,
                               scope.outer_mutables, scope.local_mutables, scope.top_level)
                self.body(body, inner, where)
            case ir.Echo(value=value):
                self.use(value, scope, where)
            case ir.EchoText():
                pass
            case ir.Return(value=value):
                self.use(value, scope, where)
                if not scope.in_function:
                    self.problem(f"{where}: return outside a function")
            case ir.Jump(label=label, args=args):
                for a in args:
                    self.use(a, scope, where)
                arity = next((n for lbl, n in scope.joins if lbl == label), None)
                if arity is None:
                    self.problem(f"{where}: jump to '{label}', which is not an enclosing join point")
                elif arity != len(args):
                    self.problem(f"{where}: jump to '{label}' passes {len(args)} values for {arity} parameters")
            case ir.Break(label=label) | ir.Continue(label=label):
                if label not in scope.loops:
                    self.problem(f"{where}: {type(s).__name__.lower()} of '{label}', which is not an enclosing loop")
            case ir.Raise(exception=e, payload=p):
                self.use(e, scope, where)
                if p is not None:
                    self.use(p, scope, where)
            case ir.Reraise(exception=e):
                self.use(e, scope, where)
            case ir.Unreachable():
                pass
            case _:
                self.problem(f"{where}: not a statement: {type(s).__name__}")
        return scope


def verify_unit(unit: ir.Unit) -> list[str]:
    """The problems of a unit at its stage (empty when it satisfies every invariant)."""
    v = _Verifier()
    v.modules = {id(m) for m in unit.modules} | {id(i) for i in unit.imports}
    if unit.at_least("closed"):
        v.functions = {id(f) for f in unit.functions}
    v.represented = unit.at_least("represented")
    top = _Scope(frozenset())
    # A module's members are visible to the code after its definition (by name, through the module), not as
    # variables; each module's initializer is its own top level
    for m in unit.modules:
        v.body(m.init, top, f"module '{m.name}'")
    v.body(unit.main, top, "main")
    if unit.at_least("closed"):
        # Lifted functions use their parameters, their environment, and the unit's globals
        globals_scope = _Scope(frozenset(global_variables(unit)))
        for f in unit.functions:
            v.function(f, globals_scope)
    if unit.at_least("represented"):
        v.problems.extend(_representation_problems(unit))
    if unit.at_least("described"):
        v.problems.extend(_descriptor_problems(unit))
    return v.problems


def _representation_problems(unit: ir.Unit) -> list[str]:
    """The uses of values in another representation than their use requires, after the represent pass: a value's
    representation is its type's, or for a boxed value its slot representation (a boxed mutable variable reads its
    value, and is assigned its box); and the slots of aggregates (components being made or stored, locations, cells)
    take records and variants boxed."""
    from quest.codegen.layout import is_boxed_in_slots, representation, resolved_shape, slot_representation
    from quest.ir.written import fun_signature
    from quest.ir.shapes import shape
    from quest.ir.walk import statement_binders, walk_statements

    problems: list[str] = []

    def rep(t) -> Optional[str]:
        return None if shape(t).kind == "ok" else representation(t)

    def atom_type(a):
        return a.type if isinstance(a, ir.Var) else a.shape.type

    def is_box(a) -> bool:
        """Whether an atom is a box (a boxed value; a boxed mutable variable's use reads the value)."""
        return isinstance(a, ir.Var) and a.boxed and not a.mutable

    def have(a) -> Optional[str]:
        return slot_representation(a.type) if is_box(a) else rep(atom_type(a))

    def target(var: ir.Var) -> Optional[str]:
        return slot_representation(var.type) if var.boxed else rep(var.type)

    def expect(a, want: Optional[str], where: str) -> None:
        had = have(a)
        if had is not None and want is not None and had != want:
            problems.append(f"{where}: a {had} used as a {want}")

    def slot(a, s, where: str, embedded: bool = False) -> None:
        """a, stored into a slot of shape s (embedded: boxed in the aggregate's allocation)."""
        if s is None or s.kind == "ok":
            return
        if is_boxed_in_slots(s) and not embedded and not is_box(a):
            problems.append(f"{where}: a record or variant stored into a slot unboxed")
        elif (not is_boxed_in_slots(s) or embedded) and is_box(a):
            problems.append(f"{where}: a box stored into a slot that does not take one")

    def located(a):
        s = shape(atom_type(a))
        return s.element if s.kind in ("cell", "out") else s

    def callee_type(call: ir.Call):
        if call.callee is not None:
            return call.callee.type
        if isinstance(call.module, ir.Module):
            return call.module.members[call.member].type
        return call.callee_type

    bodies = [(m.init, None) for m in unit.modules] + [(unit.main, None)] + [(f.body, f) for f in unit.functions]
    for body, function in bodies:
        where = f"function '{function.var.hint}'" if function is not None else "a top level"
        joins: dict[str, tuple] = {}
        for s in walk_statements(body, into_functions=False):
            for v in statement_binders(s):
                if v.boxed and not is_boxed_in_slots(shape(v.type)):
                    problems.append(f"{where}: variable '{v.hint}' is boxed, but not of a record or variant type")
            match s:
                case ir.Join(label=label, params=params):
                    joins[label] = params
                case ir.Let(var=var, value=ir.Var() | ir.Const() as a):
                    expect(a, target(var), f"{where}: let {var.hint}")
                case ir.Let(value=ir.Call() as call) | ir.Do(value=ir.Call() as call):
                    params, result_t = fun_signature(callee_type(call))
                    for p, a in zip(params, call.args):
                        if not (p.is_var or p.is_out):
                            expect(a, rep(p.type_val), f"{where}: an argument of {p.name}")
                    if isinstance(s, ir.Let):
                        expect(s.var, rep(result_t), f"{where}: the result of a call")
                case ir.Let(var=var, value=ir.MakeTuple(args=args, embedded=embedded)):
                    for i, (a, c) in enumerate(zip(args, shape(var.type).components)):
                        slot(a, c.shape, f"{where}: component {i} of {var.hint}", i in embedded)
                case ir.Let(var=var, value=ir.MakeRecord(fields=fields, embedded=embedded)):
                    for i, (n, a, _) in enumerate(fields):
                        slot(a, shape(atom_type(a)), f"{where}: field {n} of {var.hint}", i in embedded)
                case ir.Let(var=var, value=ir.MakeArray(args=args)):
                    for a in args:
                        slot(a, shape(var.type).element, f"{where}: an element of {var.hint}")
                case ir.Let(var=var, value=ir.ArrayRep(init=a)):
                    slot(a, shape(var.type).element, f"{where}: the element of {var.hint}")
                case ir.Let(value=ir.Addr(cell=a)) if a is not None:
                    slot(a, shape(atom_type(a)), f"{where}: a cell")
                case ir.Let(var=var, value=ir.MakeVariant(tag=tag, payload=a)) if a is not None:
                    vs = resolved_shape(shape(var.type))
                    case = vs.case(tag) if vs.kind == "variant" else None
                    slot(a, case.shape if case is not None else None, f"{where}: the payload of {var.hint}")
                case ir.Raise(exception=e, payload=a) if a is not None:
                    es = shape(atom_type(e))
                    slot(a, es.element if es.kind == "exception" else None, f"{where}: a raised payload")
                case ir.Echo(value=a, type=t):
                    slot(a, shape(t), f"{where}: an echoed value")
                case ir.Store(value=a, address=p) if p is not None:
                    slot(a, located(p), f"{where}: a store")
                case ir.Store(value=a, base=b, index=i) if isinstance(i, int):
                    slot(a, resolved_shape(shape(atom_type(b))).components[i].shape, f"{where}: a store")
                case ir.Store(value=a, base=b, name=None):
                    slot(a, shape(atom_type(b)).element, f"{where}: a store")
                case ir.VarDecl(var=var, init=init) if init is not None:
                    expect(init, target(var), f"{where}: var {var.hint}")
                case ir.Assign(var=var, value=value):
                    expect(value, target(var), f"{where}: {var.hint} :=")
                case ir.Return(value=value) if function is not None:
                    expect(value, rep(function.result_type), f"{where}: return")
        for s in walk_statements(body, into_functions=False):
            if isinstance(s, ir.Jump) and s.label in joins:
                for p, a in zip(joins[s.label], s.args):
                    expect(a, target(p), f"{where}: jump {s.label}")
    return problems


@dataclass(frozen=True)
class _DescriptorScope:
    """The descriptor variables in scope, and the symbols of the type parameters a static descriptor must not mention
    (those described by variables here, and in a thunk, the enclosing function's too)."""
    vars: frozenset[int]
    symbols: frozenset[int]

    def thunk(self, params) -> _DescriptorScope:
        return _DescriptorScope(frozenset(id(p.var) for p in params),
                                self.symbols | {s for p in params for s in p.symbols})

    def with_params(self, params) -> _DescriptorScope:
        return _DescriptorScope(self.vars | {id(p.var) for p in params},
                                self.symbols | {s for p in params for s in p.symbols})


def _descriptor_problems(unit: ir.Unit) -> list[str]:
    """The descriptor operands missing, unbound, or ill-formed after the describe pass, and the static descriptors and
    tables operations refer to that are not the unit's static data."""
    from quest.codegen.layout import representation
    from quest.ir.describe import free_type_vars
    from quest.ir.shapes import shape
    from quest.ir.walk import statement_bodies, walk_statements

    problems: list[str] = []
    data = unit.static_data
    if data is None:
        return ["the described unit has no static data"]
    static_keys = {((True, id(d.type)) if d.echo else (False, id(shape(d.type)))) for d in data.descriptors}
    offset_tables = {id(t) for t in data.offset_tables}
    tag_maps = {id(t) for t in data.tag_maps}
    bound: set[int] = set()
    handler_vars: set[int] = set()

    def bind(params, where: str) -> None:
        for p in params:
            if id(p.var) in bound:
                problems.append(f"{where}: descriptor variable '{p.var.hint}' is bound more than once")
            bound.add(id(p.var))
            if p.var.type is not ir.DESCRIPTOR_TYPE:
                problems.append(f"{where}: descriptor variable '{p.var.hint}' is not of the descriptor type")

    def closed(t, scope: _DescriptorScope, where: str) -> None:
        mentioned = free_type_vars(t, lambda sid: sid in scope.symbols)
        if mentioned:
            names = ", ".join(v.name for v in mentioned)
            problems.append(f"{where}: the static descriptor of {t} mentions {names}, whose descriptor is a variable")

    def descriptor(d, scope: _DescriptorScope, where: str) -> None:
        if isinstance(d, ir.Var):
            if id(d) not in scope.vars:
                problems.append(f"{where}: descriptor variable '{d.hint}' is used outside its scope")
        elif isinstance(d, ir.StaticDescriptor):
            key = (True, id(d.type)) if d.echo else (False, id(shape(d.type)))
            if key not in static_keys:
                problems.append(f"{where}: the static descriptor of {d.type} is not in the unit's static data")
            closed(d.type, scope, where)
        elif isinstance(d, ir.Instantiate):
            if (False, id(shape(d.template))) not in static_keys:
                problems.append(f"{where}: the template {d.template} is not in the unit's static data")
            closed(d.template, scope, where)
            for a in d.args:
                descriptor(a, scope, where)
        else:
            problems.append(f"{where}: a descriptor operand is missing")

    def descriptors(ds, n: int, scope: _DescriptorScope, where: str) -> None:
        if len(ds) != n:
            problems.append(f"{where}: {len(ds)} descriptors for {n} type arguments")
        for d in ds:
            descriptor(d, scope, where)

    def plan(p: Optional[ir.Plan], scope: _DescriptorScope, where: str) -> None:
        if p is None:
            return
        wanted = {"record_view": 1, "view": 2, "runtime": 2}.get(p.kind, 0)
        if len(p.descriptors) != wanted:
            problems.append(f"{where}: a {p.kind} plan with {len(p.descriptors)} descriptors")
        for d in p.descriptors:
            descriptor(d, scope, where)
        if p.kind == "variant_tags" and (p.tag_map is None or id(p.tag_map) not in tag_maps):
            problems.append(f"{where}: a variant_tags plan whose tag map is not in the unit's static data")
        if p.kind == "adapt":
            if len(p.thunk_params) != len(p.thunk_symbols):
                problems.append(f"{where}: an adapt plan's thunk has {len(p.thunk_params)} descriptor parameters")
            bind(p.thunk_params, where)
            scope = scope.thunk(p.thunk_params)
        for f in p.fields:
            plan(f, scope, where)

    def operation(o, scope: _DescriptorScope, where: str) -> None:
        match o:
            case ir.Call() | ir.CallExternal() | ir.MakeClosure():
                descriptors(o.descriptors, len(o.type_args), scope, where)
            case ir.TypeApp():
                descriptors(o.descriptors, len(o.type_args), scope, where)
                inner = scope
                if o.thunk_params is not None:
                    if len(o.thunk_params) != len(o.thunk_symbols):
                        problems.append(f"{where}: a type application's thunk has {len(o.thunk_params)} descriptor "
                                        f"parameters")
                    bind(o.thunk_params, where)
                    inner = scope.thunk(o.thunk_params)
                for p in o.plans:
                    plan(p, inner, where)
            case ir.Convert(plan=p):
                plan(p, scope, where)
            case ir.Prim(op="is" | "isnot", args=args):
                a = args[0]
                t = a.type if isinstance(a, ir.Var) else a.shape.type
                if not (isinstance(a, ir.Var) and id(a) in handler_vars) and representation(t) == "QVal":
                    descriptor(o.descriptor, scope, where)
            case ir.MakeAuto():
                descriptor(o.descriptor, scope, where)
            case ir.RecordField(stored=True):
                descriptor(o.descriptor, scope, where)
            case ir.MakeRecord():
                descriptor(o.descriptor, scope, where)
                if o.runtime_offsets:
                    descriptor(o.view_descriptor, scope, where)
                elif o.offsets is None or id(o.offsets) not in offset_tables:
                    problems.append(f"{where}: a record whose offset table is not in the unit's static data")

    def body(b: ir.Body, scope: _DescriptorScope, where: str) -> None:
        for s in b.statements:
            match s:
                case ir.Let(value=value) | ir.Do(value=value):
                    operation(value, scope, where)
                case ir.Try(exception=e):
                    handler_vars.add(id(e))
                case ir.Echo(type=t, descriptor=d) if d is not None:
                    descriptor(d, scope, where)
                case ir.Inspect(auto_type=auto_t, cases=cases, witness=witness) if auto_t is not None:
                    if witness is None:
                        problems.append(f"{where}: an inspect of an auto value without its witness")
                        armed = scope
                    else:
                        bind((witness,), where)
                        armed = scope.with_params((witness,))
                    for c in cases:
                        descriptor(c.descriptor, scope, where)
                        if c.binders and c.arm is not None:
                            arm = c.arm
                            if len(arm.descriptors) != len(arm.converted):
                                problems.append(f"{where}: an inspect arm without its components' descriptors")
                            for how, pair in zip(arm.converted, arm.descriptors):
                                if (how is None) != (pair is None):
                                    problems.append(f"{where}: an inspect arm's component {how} has descriptors "
                                                    f"{pair}")
                                for d in pair or ():
                                    descriptor(d, armed, where)
                            plan(arm.plan, armed, where)
            for inner in statement_bodies(s):
                body(inner, scope, where)

    top = _DescriptorScope(frozenset(), frozenset())
    for m in unit.modules:
        where = f"module '{m.name}'"
        body(m.init, top, where)
        for _, _, d in m.abstract_types:
            descriptor(d, top, where)
    body(unit.main, top, "main")
    for f in unit.functions:
        where = f"function '{f.var.hint}'"
        if [p.symbols for p in f.descriptor_params] != [(tp.symbol_id,) for tp in f.type_params]:
            problems.append(f"{where}: its descriptor parameters are not its type parameters'")
        bind(f.descriptor_params, where)
        body(f.body, top.with_params(f.descriptor_params), where)
        # View maps: each of a type parameter of the function, at the bound, and every one used is the function's
        own_descriptors = {id(p.var) for p in f.descriptor_params}
        for m in f.view_maps:
            if m.var.type is not ir.VIEW_MAP_TYPE or id(m.descriptor) not in own_descriptors:
                problems.append(f"{where}: view map {m.var.hint} is not of one of its type parameters")
            descriptor(m.bound, top.with_params(f.descriptor_params), where)
        maps = {id(m.var) for m in f.view_maps}
        for s in walk_statements(f.body, into_functions=False):
            values = [s.value] if isinstance(s, (ir.Let, ir.Do)) else []
            for o in [s] + values:
                vm = getattr(o, "view_map", None)
                if vm is not None and id(vm) not in maps:
                    problems.append(f"{where}: an operation reads through a view map that is not the function's")
    for table in data.offset_tables:
        for d in table.registered or ():
            descriptor(d, top, "the unit's offset tables")
    return problems


def check_unit(unit: ir.Unit) -> None:
    """Raises if the unit violates an invariant."""
    problems = verify_unit(unit)
    if problems:
        raise AssertionError("internal: the IR is not well formed:\n  " + "\n  ".join(problems[:20]))
