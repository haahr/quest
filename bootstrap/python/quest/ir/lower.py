"""Lowering from the typed AST to Core IR (docs/ir.md §12, step 3).

value(e) lowers an expression, emitting statements into the current body, and returns the atom holding its value;
effect(e) lowers one for its effect alone. An expression producing a value on several paths (if, case, inspect, try)
joins them through a join point, after which lowering continues in the join point's continuation. After a terminator
(raise, exit), lowering continues in a discarded body, so that no statement follows a terminator.

Every typed-AST symbol is mapped to one IR variable when its binder is lowered; uses look the variable up by symbol.
A use of a variable whose binder is not in the unit (an imported module, a module's member) is a module reference or a
module member, and a use of a built-in value is a constant or a built-in function.
"""

from __future__ import annotations

from typing import Optional

from quest.config import CompilerOptions
from quest.env import Environment, ValueSymbol
from quest.ir import nodes as ir
from quest.ir.shapes import shape
from quest.typed_ast import (
    TypedApp,
    TypedArray,
    TypedArrayRep,
    TypedAssign,
    TypedAuto,
    TypedBlock,
    TypedBool,
    TypedCase,
    TypedChar,
    TypedDefKind,
    TypedDerefCell,
    TypedException,
    TypedExit,
    TypedExpr,
    TypedExprStmt,
    TypedExternal,
    TypedFor,
    TypedFun,
    TypedIf,
    TypedImport,
    TypedIndex,
    TypedIndexAssign,
    TypedIndexRef,
    TypedInfix,
    TypedInspect,
    TypedInt,
    TypedInterface,
    TypedLetType,
    TypedLetTypeGroup,
    TypedLetValue,
    TypedLetValueGroup,
    TypedLoop,
    TypedModule,
    TypedNativeBinding,
    TypedNode,
    TypedOk,
    TypedOption,
    TypedProgram,
    TypedRaise,
    TypedReal,
    TypedRecord,
    TypedSelect,
    TypedSelectRef,
    TypedString,
    TypedTry,
    TypedTuple,
    TypedTupleSelectRef,
    TypedTypeApp,
    TypedTypeWitness,
    TypedVar,
    TypedVarCell,
    TypedVariant,
    TypedVariantAssert,
    TypedVariantCheck,
    TypedWhile,
)
from quest.types import (
    BOOL_TYPE,
    CHAR_TYPE,
    EXCEPTION_TYPE,
    INFIX_OPERATORS,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    QAllType,
    QFunType,
    QType,
    QVarType,
    QOutType,
    binds_module,
    format_type_compact,
)

_BUILTIN_FUNCTIONS = frozenset(INFIX_OPERATORS) | {"is", "isnot", "not", "extent", "ordinal"}


class LoweringError(Exception):
    """A typed program the lowering does not handle (a gap in the lowering, not an error in the program)."""


class _Lowerer:
    def __init__(self, env: Environment, echo: bool, print_result: bool) -> None:
        self.vars: dict[int, ir.Var] = {}
        self.builtins: dict[int, str] = {
            sym.symbol_id: name for name, sym in env.base_scope.values.items() if isinstance(sym, ValueSymbol)
        }
        self.echo = echo
        self.print_result = print_result
        self.body = ir.Body()
        self.loops: list[str] = []
        self.label_counts: dict[str, int] = {}
        self.imports: list[str] = []
        # Exceptions declared inside an expression, whose names the enclosing scope sees: mutable variables declared
        # before the binding containing them, assigned where they are made, and read (not addressed) where used
        self.hoisted: set[int] = set()

    # Building

    def emit(self, statement) -> None:
        self.body.statements.append(statement)

    def terminate(self, terminator) -> None:
        """Emits a terminator; what follows it is unreachable, and goes into a body that is discarded."""
        self.emit(terminator)
        self.body = ir.Body()

    def fresh(self, hint: str, t: QType, mutable: bool = False) -> ir.Var:
        return ir.Var(hint, shape(t), t, mutable)

    def label(self, prefix: str) -> str:
        n = self.label_counts.get(prefix, 0) + 1
        self.label_counts[prefix] = n
        return f"{prefix}{n}"

    def let(self, op, t: QType, into: Optional[ir.Var] = None, hint: str = "") -> ir.Var:
        var = into if into is not None else self.fresh(hint, t)
        self.emit(ir.Let(var, op))
        return var

    def bind_symbol(self, symbol: ValueSymbol, t: Optional[QType] = None, mutable: bool = False) -> ir.Var:
        if symbol.symbol_id in self.vars:
            raise LoweringError(f"symbol '{symbol.name}' (#{symbol.symbol_id}) is bound twice")
        var = self.fresh(symbol.name, t if t is not None else symbol.type_val, mutable)
        self.vars[symbol.symbol_id] = var
        return var

    def in_body(self, body: ir.Body):
        """Lowers into another body for the duration of a with block."""
        lowerer = self

        class _Into:
            def __enter__(self_inner):
                self_inner.saved = lowerer.body
                lowerer.body = body
                return body

            def __exit__(self_inner, *exc):
                lowerer.body = self_inner.saved
                return False

        return _Into()

    def const(self, value, t: QType) -> ir.Const:
        return ir.Const(value, shape(t))

    def copy_into(self, atom: ir.Atom, into: Optional[ir.Var]) -> ir.Atom:
        if into is None:
            return atom
        self.emit(ir.Let(into, atom))
        return into

    # Values

    def value(self, e: TypedExpr, into: Optional[ir.Var] = None) -> ir.Atom:
        """Lowers e, returning the atom that holds its value (into, if given)."""
        match e:
            case TypedInt(value=v):
                return self.copy_into(self.const(v, INT_TYPE), into)
            case TypedReal(value=v):
                return self.copy_into(self.const(v, REAL_TYPE), into)
            case TypedBool(value=v):
                return self.copy_into(self.const(v, BOOL_TYPE), into)
            case TypedChar(value=v):
                return self.copy_into(self.const(v, CHAR_TYPE), into)
            case TypedString(value=v):
                return self.copy_into(self.const(v, STRING_TYPE), into)
            case TypedOk():
                return self.copy_into(self.const(None, OK_TYPE), into)
            case TypedVar():
                return self.var_value(e, into)
            case TypedDerefCell(target=target):
                if isinstance(target, TypedVar) and (var := self.vars.get(target.symbol.symbol_id)) and var.mutable:
                    # Reading a mutable variable
                    return self.copy_into(var, into)
                return self.let(ir.Load(self.value(target)), e.type_val, into)
            case TypedExternal(symbol=symbol, inline_template=template):
                return self.let(ir.External(symbol, template), e.type_val, into)
            case TypedFun():
                var = into if into is not None else self.fresh("f", e.type_val)
                self.emit(ir.Funs((self.function(e, var),)))
                return var
            case TypedApp():
                return self.call(e, into)
            case TypedTypeApp(func=func, type_args=type_args):
                callee, module, member = self.callee(func)
                return self.let(ir.TypeApp(callee, tuple(type_args), module, member), e.type_val, into)
            case TypedInfix(left=left, op=op, right=right):
                l = self.value(left)
                r = self.value(right)
                return self.let(ir.Prim(op, (l, r)), e.type_val, into)
            case TypedRecord(fields=fields):
                atoms = tuple((f.name, self.value(f.value), f.is_var) for f in fields)
                return self.let(ir.MakeRecord(atoms), e.type_val, into)
            case TypedTuple():
                return self.tuple(e, into)
            case TypedSelect(target=target, field=fld):
                return self.select(e, target, fld, into)
            case TypedIndex(target=target, index=index):
                a = self.value(target)
                i = self.value(index)
                return self.let(ir.Index(a, i), e.type_val, into)
            case TypedArray(elements=elements):
                return self.let(ir.MakeArray(tuple(self.value(x) for x in elements)), e.type_val, into)
            case TypedArrayRep(count=count, init_val=init):
                n = self.value(count)
                v = self.value(init)
                return self.let(ir.ArrayRep(n, v), e.type_val, into)
            case TypedVarCell(value=v):
                return self.let(ir.Addr(cell=self.value(v)), e.type_val, into)
            case TypedSelectRef(target=target, field=fld):
                return self.let(ir.Addr(base=self.value(target), name=fld), e.type_val, into)
            case TypedIndexRef(target=target, index=index):
                a = self.value(target)
                i = self.value(index)
                return self.let(ir.Addr(base=a, index=i), e.type_val, into)
            case TypedTupleSelectRef(target=target, index=index, field=fld):
                t = self.value(target)
                return self.let(ir.Addr(base=t, index=self.tuple_index(target.type_val, index, fld)), e.type_val, into)
            case TypedVariant(tag=tag, payload=payload):
                p = self.value(payload) if payload is not None else None
                return self.let(ir.MakeVariant(tag, p), e.type_val, into)
            case TypedOption(tag=tag, payload=payload, ordinal_expr=ordinal_expr):
                ordinal = self.value(ordinal_expr) if ordinal_expr is not None else None
                p = self.value(payload) if payload is not None else None
                return self.let(ir.MakeOption(tag, p, ordinal), e.type_val, into)
            case TypedVariantCheck(target=target, tag=tag):
                return self.let(ir.IsTag(self.value(target), tag), e.type_val, into)
            case TypedVariantAssert(target=target, tag=tag):
                return self.let(ir.Payload(self.value(target), tag), e.type_val, into)
            case TypedAuto(witness_type=witness, auto_type=auto_type, payload=payload):
                return self.let(ir.MakeAuto(witness, auto_type, self.value(payload)), e.type_val, into)
            case TypedException(name=name, payload_type=payload_type, symbol=symbol):
                if symbol is not None and (hoisted := self.vars.get(symbol.symbol_id)) is not None:
                    made = self.let(ir.MakeException(name, payload_type), e.type_val)
                    self.emit(ir.Assign(hoisted, made))
                    return self.copy_into(hoisted, into)
                if symbol is not None:
                    bound = self.bind_symbol(symbol, e.type_val)
                    self.emit(ir.Let(bound, ir.MakeException(name, payload_type)))
                    return self.copy_into(bound, into)
                return self.let(ir.MakeException(name, payload_type), e.type_val, into)
            case TypedBlock(bindings=bindings, result=result):
                for b in bindings:
                    self.binding(b)
                return self.value(result, into)
            case TypedIf() | TypedCase() | TypedInspect() | TypedTry():
                if e.type_val is OK_TYPE:
                    self.effect(e)
                    return self.copy_into(self.const(None, OK_TYPE), into)
                return self.joined(e, into)
            case TypedWhile() | TypedLoop() | TypedFor() | TypedAssign() | TypedIndexAssign():
                self.effect(e)
                return self.copy_into(self.const(None, OK_TYPE), into)
            case TypedRaise() | TypedExit():
                self.effect(e)
                # Unreachable: the value is never used
                return self.let(ir.Load(self.const(None, OK_TYPE)), e.type_val, into)
            case _:
                raise LoweringError(f"lowering {type(e).__name__} is not implemented")

    def var_value(self, e: TypedVar, into: Optional[ir.Var]) -> ir.Atom:
        sym_id = e.symbol.symbol_id
        var = self.vars.get(sym_id)
        if var is not None:
            if var.mutable and id(var) not in self.hoisted:
                # A mutable variable not read through a dereference is passed by address (@x)
                return self.let(ir.Addr(var=var), e.type_val, into)
            return self.copy_into(var, into)
        if sym_id in self.builtins:
            name = self.builtins[sym_id]
            if name in ("true", "false"):
                return self.copy_into(self.const(name == "true", BOOL_TYPE), into)
            if name == "ok":
                return self.copy_into(self.const(None, OK_TYPE), into)
            return self.let(ir.Builtin(name), e.type_val, into)
        if binds_module(e.name, e.type_val):
            return self.let(ir.ModuleMember(e.name), e.type_val, into)
        raise LoweringError(f"variable '{e.name}' (#{sym_id}) has no binder in the unit")

    def module_path(self, e: TypedExpr) -> Optional[str]:
        """The module e names (as written), if it is a reference to a module rather than a value."""
        if isinstance(e, TypedVar) and e.symbol.symbol_id not in self.vars and binds_module(e.name, e.type_val):
            return e.name
        return None

    def callee(self, func: TypedExpr) -> tuple[Optional[ir.Var], Optional[str], Optional[str]]:
        """What a call or type application applies: a variable, or a module's member."""
        if isinstance(func, TypedSelect) and (module := self.module_path(func.target)) is not None:
            return None, module, func.field
        atom = self.value(func)
        if not isinstance(atom, ir.Var):
            raise LoweringError(f"calling a constant: {func}")
        return atom, None, None

    def call(self, e: TypedApp, into: Optional[ir.Var]) -> ir.Atom:
        func, type_args = e.func, ()
        while isinstance(func, TypedTypeApp):
            type_args = tuple(func.type_args) + type_args
            func = func.func
        if isinstance(func, TypedVar) and func.symbol.symbol_id in self.builtins:
            name = self.builtins[func.symbol.symbol_id]
            if name in _BUILTIN_FUNCTIONS:
                args = tuple(self.value(a) for a in e.args)
                op = ir.Ordinal(args[0]) if name == "ordinal" else ir.Prim(name, args)
                return self.let(op, e.type_val, into)
        callee, module, member = self.callee(func)
        args = tuple(self.argument(a) for a in e.args)
        call = ir.Call(callee, type_args, args, module, member)
        return self.let(call, e.type_val, into)

    def argument(self, a: TypedExpr) -> ir.Atom:
        # A var or out argument is an address: a mutable variable (TypedVar) or a reference node, which value() lowers
        # to addresses; a value argument is a value
        return self.value(a)

    def tuple_index(self, tuple_type: QType, index: int, fld: Optional[str]) -> int:
        s = shape(tuple_type)
        if s.kind != "tuple":
            raise LoweringError(f"tuple component of a {s.kind}")
        if fld is not None:
            for i, c in enumerate(s.components):
                if c.name == fld:
                    return i
        if 0 <= index < len(s.components):
            return index
        raise LoweringError(f"tuple {tuple_type} has no component {fld or index}")

    def select(self, e: TypedSelect, target: TypedExpr, fld: str, into: Optional[ir.Var]) -> ir.Atom:
        if (module := self.module_path(target)) is not None:
            return self.let(ir.ModuleMember(module, fld), e.type_val, into)
        base = self.value(target)
        s = shape(target.type_val)
        if s.kind == "tuple":
            return self.let(ir.TupleField(base, self.tuple_index(target.type_val, -1, fld)), e.type_val, into)
        return self.let(ir.RecordField(base, fld), e.type_val, into)

    def tuple(self, e: TypedTuple, into: Optional[ir.Var]) -> ir.Atom:
        labels = e.labels if e.labels else (None,) * len(e.elements)
        values: dict[int, ir.Atom] = {}
        type_components: list[tuple[str, QType]] = []
        rec_first = {group[0]: group for group in e.rec_groups}
        rec_members = {i for group in e.rec_groups for i in group}
        for i, (element, label) in enumerate(zip(e.elements, labels)):
            if isinstance(element, TypedTypeWitness):
                type_components.append((element.name, element.witness_type))
                continue
            if i in rec_first:
                # Recursive components: functions that see one another, through their labels
                group = rec_first[i]
                functions = []
                for k in group:
                    sym = labels[k]
                    var = self.bind_symbol(sym) if sym is not None else self.fresh("f", e.elements[k].type_val)
                    values[k] = var
                    functions.append((e.elements[k], var))
                funs = []
                for fun_e, var in functions:
                    if not isinstance(fun_e, TypedFun):
                        raise LoweringError("recursive tuple components other than functions")
                    funs.append(self.function(fun_e, var))
                self.emit(ir.Funs(tuple(funs), recursive=True))
                continue
            if i in rec_members:
                continue
            if label is None:
                values[i] = self.value(element)
                continue
            # A label names its component's value for the later components. The members of a simultaneous group
            # refer to the bindings their labels shadow by other symbols, so binding each label as its value is
            # computed is the same as binding them all after the group
            var = self.bind_symbol(label, element.type_val)
            values[i] = self.value(element, var)
        atoms = []
        for i, element in enumerate(e.elements):
            if isinstance(element, TypedTypeWitness):
                continue
            atoms.append(values[i])
        return self.let(ir.MakeTuple(tuple(atoms), tuple(type_components)), e.type_val, into)

    def joined(self, e: TypedExpr, into: Optional[ir.Var]) -> ir.Atom:
        """A value produced on several paths: each path jumps to a join point with its value."""
        result = into if into is not None else self.fresh("r", e.type_val)
        label = self.label("k")
        join = ir.Join(label, (result,), ir.Body(), ir.Body())
        self.emit(join)
        with self.in_body(join.body):
            self.branches(e, lambda branch: self.jump_with(label, branch))
        self.body = join.continuation
        return result

    def jump_with(self, label: str, branch: TypedExpr) -> None:
        atom = self.value(branch)
        if not self.body.terminated:
            self.terminate(ir.Jump(label, (atom,)))

    # Effects

    def effect(self, e: TypedExpr) -> None:
        """Lowers e for its effect alone."""
        match e:
            case TypedIf() | TypedCase() | TypedInspect() | TypedTry():
                self.branches(e, self.effect)
            case TypedBlock(bindings=bindings, result=result):
                for b in bindings:
                    self.binding(b)
                self.effect(result)
            case TypedWhile(cond=cond, body=body):
                label = self.label("L")
                loop = ir.Loop(label, ir.Body())
                self.emit(loop)
                self.loops.append(label)
                with self.in_body(loop.body):
                    c = self.value(cond)
                    then_body = ir.Body()
                    self.emit(ir.If(c, then_body, ir.Body([ir.Break(label)])))
                    with self.in_body(then_body):
                        self.effect(body)
                self.loops.pop()
            case TypedLoop(body=body):
                label = self.label("L")
                loop = ir.Loop(label, ir.Body())
                self.emit(loop)
                self.loops.append(label)
                with self.in_body(loop.body):
                    self.effect(body)
                self.loops.pop()
            case TypedFor():
                self.for_loop(e)
            case TypedExit():
                if not self.loops:
                    raise LoweringError("exit outside a loop")
                self.terminate(ir.Break(self.loops[-1]))
            case TypedAssign(target=target, value=value):
                self.assign(target, value)
            case TypedIndexAssign(target=target, index=index, value=value):
                a = self.value(target)
                i = self.value(index)
                v = self.value(value)
                self.emit(ir.Store(v, base=a, index=i))
            case TypedRaise(exc=exc, payload=payload):
                x = self.value(exc)
                p = self.value(payload) if payload is not None else None
                self.terminate(ir.Raise(x, p))
            case TypedApp() if e.type_val is OK_TYPE:
                atom = self.call(e, None)
                # A call for its effect: its result is not used (Ok)
                last = self.body.statements[-1] if self.body.statements else None
                if isinstance(last, ir.Let) and last.var is atom and isinstance(last.value, ir.Call):
                    self.body.statements[-1] = ir.Do(last.value)
            case _:
                self.value(e)

    def assign(self, target: TypedExpr, value: TypedExpr) -> None:
        match target:
            case TypedVar() if (var := self.vars.get(target.symbol.symbol_id)) is not None and var.mutable:
                v = self.value(value)
                self.emit(ir.Assign(var, v))
            case TypedSelect(target=base_e, field=fld):
                base = self.value(base_e)
                v = self.value(value)
                s = shape(base_e.type_val)
                if s.kind == "tuple":
                    self.emit(ir.Store(v, base=base, index=self.tuple_index(base_e.type_val, -1, fld)))
                else:
                    self.emit(ir.Store(v, base=base, name=fld))
            case _:
                address = self.value(target)
                v = self.value(value)
                self.emit(ir.Store(v, address=address))

    def for_loop(self, e: TypedFor) -> None:
        start = self.value(e.start)
        stop = self.value(e.stop)
        counter = self.fresh(e.var_name, INT_TYPE, mutable=True)
        self.emit(ir.VarDecl(counter, start))
        label = self.label("L")
        loop = ir.Loop(label, ir.Body())
        self.emit(loop)
        self.loops.append(label)
        with self.in_body(loop.body):
            more = self.let(ir.Prim(">=" if e.is_downto else "<=", (counter, stop)), BOOL_TYPE)
            then_body = ir.Body()
            self.emit(ir.If(more, then_body, ir.Body([ir.Break(label)])))
            with self.in_body(then_body):
                i = self.bind_symbol(e.symbol, INT_TYPE)
                self.emit(ir.Let(i, counter))
                self.effect(e.body)
                if not self.body.terminated:
                    step = self.let(ir.Prim("-" if e.is_downto else "+", (counter, self.const(1, INT_TYPE))), INT_TYPE)
                    self.emit(ir.Assign(counter, step))
        self.loops.pop()

    def branches(self, e: TypedExpr, lower_branch) -> None:
        """Lowers the branches of an if, case, inspect, or try, each with lower_branch (into the branch's body)."""
        match e:
            case TypedIf(cond=cond, then_branch=then_e, else_branch=else_e):
                c = self.value(cond)
                stmt = ir.If(c, ir.Body(), ir.Body())
                self.emit(stmt)
                with self.in_body(stmt.then_body):
                    lower_branch(then_e)
                with self.in_body(stmt.else_body):
                    lower_branch(else_e)
            case TypedCase(target=target, branches=branches, else_branch=else_e):
                v = self.value(target)
                cases = []
                for br in branches:
                    binder = None
                    if br.binder is not None:
                        binder = self.bind_symbol(br.binder)
                    case = ir.Case(tuple(br.tags), ir.Body(), binder)
                    with self.in_body(case.body):
                        lower_branch(br.body)
                    cases.append(case)
                else_body = None
                if else_e is not None:
                    else_body = ir.Body()
                    with self.in_body(else_body):
                        lower_branch(else_e)
                self.emit(ir.Switch(v, tuple(cases), else_body))
            case TypedInspect(target=target, branches=branches, else_branch=else_e, auto_type=auto_type):
                v = self.value(target)
                cases = []
                for br in branches:
                    binders = tuple(self.bind_symbol(b) for b in br.binders)
                    case = ir.InspectCase(br.match_type, binders, ir.Body(), br.exact)
                    with self.in_body(case.body):
                        lower_branch(br.body)
                    cases.append(case)
                else_body = None
                if else_e is not None:
                    else_body = ir.Body()
                    with self.in_body(else_body):
                        lower_branch(else_e)
                self.emit(ir.Inspect(v, tuple(cases), else_body, auto_type))
            case TypedTry(body=body_e, branches=branches, else_branch=else_e):
                exception = self.fresh("e", EXCEPTION_TYPE)
                stmt = ir.Try(ir.Body(), exception, ir.Body())
                self.emit(stmt)
                with self.in_body(stmt.body):
                    lower_branch(body_e)
                with self.in_body(stmt.handler):
                    self.handler(exception, branches, else_e, lower_branch)
            case _:
                raise LoweringError(f"branches of {type(e).__name__}")

    def handler(self, exception: ir.Var, branches, else_e, lower_branch) -> None:
        """A try's handler: the branches' patterns tested in order against the exception, else the else branch, or
        the exception raised again."""
        if not branches:
            if else_e is not None:
                lower_branch(else_e)
            else:
                self.terminate(ir.Raise(exception))
            return
        br, rest = branches[0], branches[1:]
        pattern = self.value(br.exc_pattern)
        matches = self.let(ir.Prim("is", (exception, pattern)), BOOL_TYPE)
        stmt = ir.If(matches, ir.Body(), ir.Body())
        self.emit(stmt)
        with self.in_body(stmt.then_body):
            if br.binder is not None:
                self.emit(ir.Let(self.bind_symbol(br.binder), ir.ExceptionPayload(exception)))
            lower_branch(br.body)
        with self.in_body(stmt.else_body):
            self.handler(exception, rest, else_e, lower_branch)

    # Functions

    def function(self, e: TypedFun, var: ir.Var) -> ir.Function:
        t = e.type_val
        type_params: tuple[ir.TypeParam, ...] = ()
        inner = t
        if isinstance(t, QAllType):
            type_params = tuple(
                ir.TypeParam(q.name, q.symbol_id, q.bound, shape(q.bound.bound) if hasattr(q.bound, "bound") else None)
                for q in t.quantifiers
            )
            inner = t.body
        result_t = inner.result_type if isinstance(inner, QFunType) else inner
        params = []
        for p in e.params:
            mode = "var" if p.is_var else "out" if p.is_out else "value"
            param_t = p.type_val
            if isinstance(param_t, (QVarType, QOutType)):
                param_t = param_t.element_type
            params.append((self.bind_symbol(p.symbol, param_t, mutable=mode != "value"), mode))
        body = ir.Body()
        saved_loops, self.loops = self.loops, []
        with self.in_body(body):
            # The body is a scope of its own: exceptions made inside it are visible throughout it
            self.hoist_exceptions(e.body)
            result = self.value(e.body)
            if not self.body.terminated:
                self.terminate(ir.Return(result))
        self.loops = saved_loops
        return ir.Function(var, type_params, tuple(params), shape(result_t), body, result_t)

    # Bindings

    def hoist_exceptions(self, b: TypedNode) -> None:
        """Declares, before b, the named exceptions made inside b whose names b's scope sees (not those b is itself,
        or binds directly, nor those inside functions and blocks, which bind them in their own scopes)."""
        direct = b.expr if isinstance(b, TypedExprStmt) else b.value if isinstance(b, TypedLetValue) else b
        for exc in _named_exceptions_in(b):
            if exc is direct or exc.symbol is None or exc.symbol.symbol_id in self.vars:
                continue
            var = self.bind_symbol(exc.symbol, exc.type_val, mutable=True)
            self.hoisted.add(id(var))
            self.emit(ir.VarDecl(var, self.const(None, exc.type_val)))

    def binding(self, b: TypedNode, show: bool = False) -> None:
        self.hoist_exceptions(b)
        match b:
            case TypedLetValue(value=value, is_rec=True) if not isinstance(value, TypedFun):
                self.rec_values((b,), show)
            case TypedLetValue(name=name, value=value, symbol=symbol):
                if isinstance(value, TypedFun):
                    var = self.bind_symbol(symbol)
                    self.emit(ir.Funs((self.function(value, var),), recursive=b.is_rec))
                    if show:
                        self.emit(ir.EchoText(f"let {name}:{_display(symbol.type_val)} = <fun>"))
                    return
                if symbol.is_var:
                    init = self.value(value)
                    var = self.bind_symbol(symbol, mutable=True)
                    self.emit(ir.VarDecl(var, init))
                else:
                    if b.is_rec:
                        raise LoweringError("recursive values other than functions")
                    # The value is lowered before the variable is bound, so that it refers to any binding it shadows
                    var = ir.Var(symbol.name, shape(symbol.type_val), symbol.type_val)
                    self.value(value, var)
                    if symbol.symbol_id in self.vars:
                        raise LoweringError(f"symbol '{name}' is bound twice")
                    self.vars[symbol.symbol_id] = var
                if show:
                    self.echo_binding(name, symbol, var)
            case TypedLetValueGroup(members=members, is_rec=True) if not all(
                isinstance(m.value, TypedFun) for m in members
            ):
                self.rec_values(members, show)
            case TypedLetValueGroup(members=members, is_rec=True):
                vars_ = [self.bind_symbol(m.symbol) for m in members]
                functions = tuple(self.function(m.value, v) for m, v in zip(members, vars_))
                self.emit(ir.Funs(functions, recursive=True))
                if show:
                    for m in members:
                        self.emit(ir.EchoText(f"let {m.name}:{_display(m.symbol.type_val)} = <fun>"))
            case TypedLetValueGroup(members=members):
                # Simultaneous: every member's value refers to the bindings the members shadow, which their symbols
                # keep apart, so lowering them in order and binding each as it is computed is the same
                for m in members:
                    self.binding(m, show)
            case TypedExprStmt(expr=expr):
                self.phrase_expr(expr, show)
            case TypedLetType(name=name, symbol=symbol):
                if show:
                    kind_str = str(symbol.kind)
                    if symbol.definition is not None:
                        self.emit(ir.EchoText(f"Let {name}::{kind_str} = {symbol.definition}"))
                    else:
                        self.emit(ir.EchoText(f"Let {name}::{kind_str}"))
            case TypedLetTypeGroup(members=members):
                for m in members:
                    self.binding(m, show)
            case TypedDefKind(name=name, symbol=symbol):
                if show:
                    self.emit(ir.EchoText(f"DEF {name} = {symbol.kind}"))
            case TypedException():
                self.phrase_expr(b, show)
            case TypedImport(items=items):
                for item in items:
                    self.imports.extend(item.names)
            case TypedInterface() | TypedNativeBinding() | TypedModule():
                raise LoweringError(f"{type(b).__name__} inside a block")
            case TypedExpr():
                self.phrase_expr(b, show)
            case _:
                raise LoweringError(f"lowering binding {type(b).__name__} is not implemented")

    def rec_values(self, members, show: bool) -> None:
        """Recursive values (and functions) declared together: each member's value is computed into its variable in
        a let rec, where closures may refer to all of them."""
        vars_ = tuple(self.bind_symbol(m.symbol) for m in members)
        group = ir.LetRec(vars_, ir.Body())
        self.emit(group)
        with self.in_body(group.body):
            for m, var in zip(members, vars_):
                if isinstance(m.value, TypedFun):
                    self.emit(ir.Funs((self.function(m.value, var),)))
                else:
                    self.value(m.value, var)
        if show:
            for m, var in zip(members, vars_):
                if isinstance(m.value, TypedFun):
                    self.emit(ir.EchoText(f"let {m.name}:{_display(m.symbol.type_val)} = <fun>"))
                else:
                    self.echo_binding(m.name, m.symbol, var)

    def phrase_expr(self, e: TypedExpr, show: bool) -> None:
        if isinstance(e, TypedException) and e.name:
            self.value(e)
            if show:
                self.emit(ir.EchoText(f"exception {e.name}"))
            return
        if e.type_val is OK_TYPE:
            self.effect(e)
            return
        atom = self.value(e)
        if show:
            self.emit(ir.Echo(atom, e.type_val, ""))

    def echo_binding(self, name: str, symbol: ValueSymbol, var: ir.Var) -> None:
        prefix = f"let {'var ' if symbol.is_var else ''}{name}:{_display(symbol.type_val)} = "
        if symbol.type_val is OK_TYPE:
            self.emit(ir.EchoText(prefix + "ok"))
        else:
            self.emit(ir.Echo(var, symbol.type_val, prefix))

    # Units

    def module(self, m: TypedModule) -> ir.Module:
        init = ir.Body()
        members: dict[str, ir.Var] = {}
        with self.in_body(init):
            for b in m.bindings:
                match b:
                    case TypedNativeBinding(name=name, symbol=symbol, inline_template=template, type_val=t):
                        var = self.fresh(name, t)
                        self.emit(ir.Let(var, ir.External(symbol, template)))
                        members[name] = var
                    case TypedImport(items=items):
                        for item in items:
                            self.imports.extend(item.names)
                    case _:
                        self.binding(b)
                        for member in (b.members if isinstance(b, (TypedLetValueGroup, TypedLetTypeGroup)) else (b,)):
                            if isinstance(member, TypedLetValue):
                                members[member.name] = self.vars[member.symbol.symbol_id]
        return ir.Module(m.name, m.interface_name, init, members)

    def program(self, prog: TypedProgram) -> ir.Unit:
        main = ir.Body()
        modules: list[ir.Module] = []
        phrases = prog.phrases
        with self.in_body(main):
            for i, phrase in enumerate(phrases):
                show = self.echo or (self.print_result and i == len(phrases) - 1)
                match phrase:
                    case TypedModule():
                        if not phrase.is_precompiled:
                            modules.append(self.module(phrase))
                    case TypedInterface():
                        pass
                    case _:
                        self.binding(phrase, show)
        return ir.Unit(main, modules, tuple(self.imports))


def _named_exceptions_in(node) -> list[TypedException]:
    """The named exceptions made in node whose names bind in node's scope: not inside functions or blocks."""
    found: list[TypedException] = []

    def scan(n) -> None:
        if n is None or isinstance(n, (QType, str, int, float, bool, TypedFun, TypedBlock, ValueSymbol)):
            return
        if isinstance(n, TypedException):
            if n.name:
                found.append(n)
            return
        if isinstance(n, (list, tuple)):
            for item in n:
                scan(item)
        elif isinstance(n, TypedNode):
            for f in n.__dataclass_fields__:
                scan(getattr(n, f))

    scan(node)
    return found


def _display(t: QType) -> str:
    return format_type_compact(t)


def lower_program(
    prog: TypedProgram,
    env: Environment,
    options: Optional[CompilerOptions] = None,
    echo: bool = False,
    print_result: bool = True,
) -> ir.Unit:
    """Lowers a typed program to a Core IR unit."""
    if options is not None:
        echo = bool(getattr(options, "echo", echo))
    return _Lowerer(env, echo, print_result).program(prog)
