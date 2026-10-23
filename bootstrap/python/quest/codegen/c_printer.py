"""The C printer (docs/ir.md §8.5): prints a represented IR unit as C, the IR's backend.

It prints what the passes decided: each IR function is a C function taking its closure's environment first (and its
own type parameters' descriptors, then its parameters), each closure a QClosure of one (a static one when it captures
nothing), each variable a C variable of its type's representation (globals for the variables the top levels bind
outside loops, declared at file scope), and each structured statement a C statement: join points and loop exits are
labels, and try regions setjmp handlers, popped on every way out. Conversions are `convert` operations, printed as
their plans say. The declarations of the types it uses (structs, descriptors, function type adapters) and the ABI
of modules (`qv_<module>_<member>`, `qm_<module>`, `qv_mod_<module>_init`) are the current emitter's, so that units
of either backend link together (codegen/c_declarations.py, c_types.py).

Built a slice at a time (docs/ir.md §12, step 5): what a slice does not cover yet raises NotImplementedError, so a
program is compiled correctly or not at all.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any, Optional

from quest.codegen.c_analysis import collect_aggregate_types
from quest.codegen.c_declarations import CDeclarationEmitter
from quest.codegen.c_emitter import CEmitter, _value_kind
from quest.codegen.c_types import (
    MissingDescriptorError,
    RecordNamingContext,
    c_char_literal,
    c_string_literal,
    closure_fn_ptr_type,
    collect_fun_quantifiers,
    descriptor_form,
    is_record_subtype,
    is_tuple_subtype,
    is_variant_subtype,
    mangle_ident,
    mangle_module_ident,
    mangle_module_name,
    module_record_ident,
    qtype_to_c_type,
    qtype_to_name_str,
    qval_unwrap,
    qval_wrap,
    record_struct_name,
    tuple_struct_name,
    type_to_c_tag,
)
from quest.env import Scope
from quest.ir import nodes as ir
from quest.ir.walk import global_variables, statement_binders, statement_bodies, walk_statements
from quest.modules.elaboration import build_record_type_from_scope
from quest.typed_ast import TypedModule
from quest.types import (
    OK_TYPE,
    QAllType,
    QFunType,
    QParam,
    QRecordField,
    QRecordType,
    QTupleType,
    QType,
    QTypeVar,
    QVariantType,
    strip_aliases,
)

_INT_OPS = {"+": "+", "-": "-", "*": "*", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
_REAL_OPS = {"++": "quest_real_add", "--": "quest_real_sub", "**": "quest_real_mul", "//": "quest_real_divide"}
_REAL_RELATIONS = {"<<": "<", "<<=": "<=", ">>": ">", ">>=": ">="}


def _signature(t: QType) -> tuple[tuple, tuple[QParam, ...], QType]:
    """A function type's quantifiers, parameters, and result type."""
    quants, inner = collect_fun_quantifiers(t)
    if isinstance(inner, QFunType):
        return quants, tuple(inner.params), inner.result_type
    return quants, (), inner


class _FunctionState:
    """What printing one C function needs: its locals and the labels and handlers in scope."""

    def __init__(self, function: Optional[ir.Function]) -> None:
        self.function = function
        self.locals: list[tuple[str, str]] = []
        # Labels used by jumps, breaks, and continues (only used labels are printed)
        self.used_labels: set[str] = set()
        # The try handlers entered, innermost last, and for each label the number entered where it is defined
        self.handlers: list[str] = []
        self.label_depth: dict[str, int] = {}
        self.volatile: set[int] = set()


class CPrinter:
    def __init__(self, unit: ir.Unit, env: Any, module_scopes: dict[int, Scope]) -> None:
        self.unit = unit
        self.env = env
        self.ctx = RecordNamingContext()
        self.module_scopes = module_scopes
        self.globals = global_variables(unit)
        self.names: dict[int, str] = {}
        self.used_names: set[str] = set()
        self.code_names: dict[int, str] = {}
        # Closures bound by lets (by variable), whose calls call their functions directly
        self.closures: dict[int, ir.MakeClosure] = {}
        self.handler_vars: set[int] = set()
        self.types: list[QType] = []
        self.descriptors: dict[int, str] = {}
        self.descriptor_params: dict[tuple[int, int], str] = {}
        self.fs = _FunctionState(None)
        self.lines: list[str] = []
        self.indent = 1
        self.tmp = 0

    # Names

    def fresh_name(self, base: str) -> str:
        name = base
        n = 1
        while name in self.used_names:
            n += 1
            name = f"{base}_{n}"
        self.used_names.add(name)
        return name

    def name(self, var: ir.Var) -> str:
        key = id(var)
        if key not in self.names:
            base = mangle_ident(var.hint or "t")
            prefix = "g_" if key in self.globals else "l_"
            self.names[key] = self.fresh_name(prefix + base.removeprefix("qv_"))
        return self.names[key]

    def code_name(self, f: ir.Function) -> str:
        key = id(f)
        if key not in self.code_names:
            self.code_names[key] = self.fresh_name("qf_" + mangle_ident(f.var.hint or "fun").removeprefix("qv_"))
        return self.code_names[key]

    def temp(self, c_type: str) -> str:
        self.tmp += 1
        name = f"_t{self.tmp}"
        self.fs.locals.append((c_type, name))
        return name

    # Types

    def c_type(self, t: QType) -> str:
        self.types.append(t)
        return qtype_to_c_type(t, self.ctx)

    def var_c_type(self, var: ir.Var) -> str:
        if id(var) in self.handler_vars:
            return "QExceptionState"
        return self.c_type(var.type)

    def is_ok(self, t: QType) -> bool:
        return strip_aliases(t) is OK_TYPE

    def descriptor(self, t: QType) -> str:
        """The descriptor of a type: a type parameter's, passed to its function, or a closed type's static one."""
        bare = strip_aliases(t.prune() if hasattr(t, "prune") else t)
        if isinstance(bare, QTypeVar) and bare.symbol_id in self.descriptors:
            return self.descriptors[bare.symbol_id]
        if bare._fv & set(self.descriptors):
            raise NotImplementedError(f"the descriptor of a type mentioning type parameters in scope: {t}")
        self.types.append(t)
        try:
            return descriptor_form(bare, self.ctx).c_expr
        except MissingDescriptorError as e:
            raise NotImplementedError(f"C code generation: {e}") from None

    # Output

    def emit(self, line: str) -> None:
        self.lines.append("    " * self.indent + line)

    # Atoms and operations

    def atom(self, a: ir.Atom) -> str:
        if isinstance(a, ir.Const):
            return self.const(a)
        if self.is_ok(a.type):
            return "Q_OK_VAL"
        name = self.name(a)
        if id(a) in self.handler_vars:
            return f"{name}.exc"
        if a.mutable and self.is_pointer_param(a):
            return f"(*{name})"
        return name

    def is_pointer_param(self, var: ir.Var) -> bool:
        f = self.fs.function
        return f is not None and any(v is var and mode != "value" for v, mode in f.params)

    def const(self, c: ir.Const) -> str:
        v = c.value
        if v is None:
            return "Q_OK_VAL"
        if isinstance(v, bool):
            return "true" if v else "false"
        match c.shape.kind:
            case "int":
                return f"{v}LL" if v >= 0 else f"({v}LL)"
            case "real":
                if math.isinf(v):
                    return "INFINITY" if v > 0 else "(-INFINITY)"
                s = repr(v)
                return s if "e" in s or "." in s else s + ".0"
            case "char":
                return c_char_literal(v)
            case "string":
                return f"quest_string_new({c_string_literal(v)}, {len(v)}LL)"
        raise NotImplementedError(f"constant {v!r} of shape {c.shape.kind}")

    def operation(self, o, result: Optional[ir.Var]) -> str:
        match o:
            case ir.Var() | ir.Const():
                return self.atom(o)
            case ir.Prim(op=op, args=args):
                return self.prim(op, args)
            case ir.Ordinal(value=v):
                return f"(({self.atom(v)})->tag)"
            case ir.Call():
                return self.call(o)
            case ir.ModuleMember(module=module, member=member):
                return self.module_member(module, member)
            case ir.Builtin(name=name):
                return f"(&{mangle_ident(name)}_closure)"
            case ir.External(symbol=symbol):
                t = result.type if result is not None else None
                return f"{symbol}()" if isinstance(t, QFunType) and not t.params else symbol
            case ir.MakeClosure():
                return self.make_closure(o, result)
            case ir.EnvField(env=env, index=index):
                return f"{self.name(env)}->c{index}"
            case ir.Convert(value=v, plan=plan):
                return self.convert(self.atom(v), plan)
            case ir.MakeException(name=name):
                return f"quest_alloc_exception({c_string_literal(name)})"
            case ir.ExceptionPayload(exception=e):
                return qval_unwrap(f"{self.name(e)}.payload", result.type, self.ctx)
            case ir.Addr(var=var) if var is not None:
                if self.is_pointer_param(var):
                    return self.name(var)
                if id(var) in self.fs.volatile:
                    return f"(({self.c_type(var.type)} *)&{self.name(var)})"
                return f"(&{self.name(var)})"
            case ir.Addr(cell=cell) if cell is not None:
                cell_c = self.temp(self.c_type(cell.type if isinstance(cell, ir.Var) else cell.shape.type))
                self.emit(f"{cell_c} = {self.atom(cell)};")
                return f"(&{cell_c})"
            case ir.Load(address=a):
                return f"(*{self.atom(a)})"
        raise NotImplementedError(f"C printing of {type(o).__name__}")

    def convert(self, c: str, plan: ir.Plan) -> str:
        match plan.kind:
            case "box":
                return qval_wrap(c, plan.source)
            case "unbox":
                return qval_unwrap(c, plan.target, self.ctx)
        raise NotImplementedError(f"conversion plan {plan.kind}")

    def prim(self, op: str, args: tuple[ir.Atom, ...]) -> str:
        cs = [self.atom(a) for a in args]
        if op == "not":
            return f"(!({cs[0]}))"
        if op == "extent":
            return f"(({cs[0]})->length)"
        left, right = cs
        if op == "/":
            return f"quest_int_div({left}, {right})"
        if op in ("%", "mod"):
            return f"quest_int_mod({left}, {right})"
        if op in _REAL_OPS:
            return f"{_REAL_OPS[op]}({left}, {right})"
        if op == "^^":
            return f"quest_real_pow({left}, {right})"
        if op == "<>":
            return f"quest_string_concat({left}, {right})"
        if op in ("is", "isnot"):
            t = args[0].type if isinstance(args[0], ir.Var) else args[0].shape.type
            if isinstance(args[0], ir.Var) and id(args[0]) in self.handler_vars:
                t = None
            if t is not None and self.c_type(t) == "QVal":
                negate = "" if op == "is" else "!"
                return f"({negate}quest_val_is({self.descriptor(t)}, {left}, {right}))"
            return f"(({left}) {'==' if op == 'is' else '!='} ({right}))"
        if op in _INT_OPS:
            return f"(({left}) {_INT_OPS[op]} ({right}))"
        if op in _REAL_RELATIONS:
            return f"(({left}) {_REAL_RELATIONS[op]} ({right}))"
        if op == "/\\":
            return f"(({left}) && ({right}))"
        if op == "\\/":
            return f"(({left}) || ({right}))"
        raise NotImplementedError(f"primitive '{op}'")

    def args(self, params: tuple[QParam, ...], args: tuple[ir.Atom, ...]) -> list[str]:
        out = []
        for i, a in enumerate(args):
            out.append(self.atom(a))
        return out

    def call(self, call: ir.Call) -> str:
        descs = [self.descriptor(t) for t in call.type_args]
        if call.callee is None:
            module = call.module
            if isinstance(module, ir.Module):
                member = module.members[call.member]
                return self.call_closure(member, descs, call.args)
            clean = mangle_module_name(module.canonical_path)
            args = descs + self.args((), call.args)
            return f"{mangle_module_ident(clean, call.member)}({', '.join(args)})"
        return self.call_closure(call.callee, descs, call.args)

    def call_closure(self, callee: ir.Var, descs: list[str], args: tuple[ir.Atom, ...]) -> str:
        c_args = descs + self.args((), args)
        known = self.closures.get(id(callee))
        if known is not None and not known.type_args:
            env = "NULL" if not known.captures else f"{self.name(callee)}->env"
            return f"{self.code_name(known.code)}({', '.join([env] + c_args)})"
        fn_ptr = closure_fn_ptr_type(callee.type, self.ctx)
        self.types.append(callee.type)
        clos = self.atom(callee)
        return f"(({fn_ptr})({clos}->fn))({', '.join([f'{clos}->env'] + c_args)})"

    def module_member(self, module: ir.ModuleRef, member: Optional[str]) -> str:
        if isinstance(module, ir.Module):
            if member is None:
                return module_record_ident(mangle_module_name(module.name))
            return self.atom(module.members[member])
        clean = mangle_module_name(module.canonical_path)
        record = module_record_ident(clean)
        if member is None:
            return record
        scope = self.module_scopes.get(id(module))
        if scope is None:
            raise NotImplementedError(f"module {module.name}: its interface is unknown")
        rec_t = build_record_type_from_scope(scope)
        self.types.append(rec_t)
        field = next(f for f in rec_t.fields if f.name == member)
        c_fld = self.c_type(field.type_val)
        dict_t = self.ctx.offset_dict_struct_name(rec_t)
        return f"(*(({c_fld} *)((char *){record}.val + ((const {dict_t} *){record}.dict)->offset_{member})))"

    def make_closure(self, o: ir.MakeClosure, result: Optional[ir.Var]) -> str:
        code = self.code_name(o.code)
        if not o.captures and not o.type_args:
            return f"(&{code}_closure)"
        env = self.temp(f"struct QEnv_{code} *")
        self.emit(f"{env} = (struct QEnv_{code} *)quest_alloc(sizeof(struct QEnv_{code}));")
        for i, t in enumerate(o.type_args):
            self.emit(f"{env}->d{i} = {self.descriptor(t)};")
        for i, a in enumerate(o.captures):
            if self.deferred is not None and isinstance(a, ir.Var) and id(a) in self.deferred[0]:
                # A variable of the let rec being made, which holds its value once the let rec's body has run
                self.deferred[1].append((env, i, a))
                continue
            self.emit(f"{env}->c{i} = {self.atom(a)};")
        clos = self.temp("QClosure *")
        self.emit(f"{clos} = (QClosure *)quest_alloc(sizeof(QClosure));")
        self.emit(f"{clos}->fn = (void *){code};")
        self.emit(f"{clos}->env = (void *){env};")
        return clos

    deferred: Optional[tuple[set[int], list]] = None

    # Statements

    def body(self, body: ir.Body) -> None:
        for s in body.statements:
            self.statement(s)

    def block(self, body: ir.Body) -> None:
        self.indent += 1
        self.body(body)
        self.indent -= 1

    def assign(self, var: ir.Var, value: str) -> None:
        if self.is_ok(var.type):
            if value != "Q_OK_VAL":
                self.emit(f"(void)({value});")
            return
        target = f"(*{self.name(var)})" if var.mutable and self.is_pointer_param(var) else self.name(var)
        self.emit(f"{target} = {value};")

    def leave_to(self, depth: int) -> None:
        """Pops the try handlers entered since depth, for a jump out of them."""
        if len(self.fs.handlers) > depth:
            self.emit(f"quest_current_exception_handler = {self.fs.handlers[depth]}.prev;")

    def statement(self, s) -> None:
        match s:
            case ir.Let(var=var, value=value):
                if isinstance(value, ir.MakeClosure):
                    self.closures[id(var)] = value
                self.assign(var, self.operation(value, var))
            case ir.Do(value=value):
                c = self.operation(value, None)
                self.emit(f"{c};")
            case ir.VarDecl(var=var, init=init):
                self.assign(var, self.atom(init))
            case ir.Declare():
                pass
            case ir.Assign(var=var, value=value):
                self.assign(var, self.atom(value))
            case ir.Store(value=value, address=address) if address is not None:
                self.emit(f"*{self.atom(address)} = {self.atom(value)};")
            case ir.LetRec(vars=vars_, body=body):
                saved = self.deferred
                self.deferred = ({id(v) for v in vars_}, [])
                self.body(body)
                for env, i, var in self.deferred[1]:
                    self.emit(f"{env}->c{i} = {self.atom(var)};")
                self.deferred = saved
            case ir.If(cond=cond, then_body=then_body, else_body=else_body):
                self.emit(f"if ({self.atom(cond)}) {{")
                self.block(then_body)
                if else_body.statements:
                    self.emit("} else {")
                    self.block(else_body)
                self.emit("}")
            case ir.Loop(label=label, body=body):
                self.fs.label_depth[label] = len(self.fs.handlers)
                self.emit("for (;;) {")
                self.block(body)
                if f"{label}_continue" in self.fs.used_labels:
                    self.emit(f"    {label}_continue:;")
                self.emit("}")
                if f"{label}_break" in self.fs.used_labels:
                    self.emit(f"{label}_break:;")
            case ir.Break(label=label) | ir.Continue(label=label):
                which = "break" if isinstance(s, ir.Break) else "continue"
                self.leave_to(self.fs.label_depth[label])
                self.fs.used_labels.add(f"{label}_{which}")
                self.emit(f"goto {label}_{which};")
            case ir.Join(label=label, params=params, continuation=continuation, body=body):
                self.fs.label_depth[label] = len(self.fs.handlers)
                self.emit("{")
                self.block(body)
                self.emit("}")
                end = f"{label}_end"
                if not body.terminated:
                    self.fs.used_labels.add(end)
                    self.emit(f"goto {end};")
                self.emit(f"{label}:;")
                self.emit("{")
                self.block(continuation)
                self.emit("}")
                if end in self.fs.used_labels:
                    self.emit(f"{end}:;")
            case ir.Jump(label=label, args=args):
                join_params = self.join_params[label]
                for p, a in zip(join_params, args):
                    self.assign(p, self.atom(a))
                self.leave_to(self.fs.label_depth[label])
                self.emit(f"goto {label};")
            case ir.Try(body=body, exception=exception, handler=handler):
                h = self.fresh_name("_qh")
                self.emit("{")
                self.indent += 1
                self.emit(f"QExceptionHandler {h};")
                self.emit(f"{h}.prev = quest_current_exception_handler;")
                self.emit(f"quest_current_exception_handler = &{h};")
                self.emit(f"if (setjmp({h}.env_jmp) == 0) {{")
                self.fs.handlers.append(h)
                self.block(body)
                self.fs.handlers.pop()
                if not body.terminated:
                    self.emit(f"    quest_current_exception_handler = {h}.prev;")
                self.emit("} else {")
                self.emit(f"    quest_current_exception_handler = {h}.prev;")
                self.emit(f"    {self.name(exception)} = quest_current_exception;")
                self.block(handler)
                self.emit("}")
                self.indent -= 1
                self.emit("}")
            case ir.Return(value=value):
                self.leave_to(0)
                if self.fs.function is not None and self.is_ok(self.fs.function.result_type):
                    self.emit("return;")
                else:
                    self.emit(f"return {self.atom(value)};")
            case ir.Raise(exception=e, payload=p):
                if id(e) in self.handler_vars and p is None:
                    self.emit(f"quest_raise({self.name(e)}.exc, {self.name(e)}.payload);")
                else:
                    payload = "Q_OK_VAL" if p is None else qval_wrap(self.atom(p), self.atom_type(p))
                    self.emit(f"quest_raise({self.atom(e)}, {payload});")
            case ir.Unreachable():
                self.emit("abort();")
            case ir.Echo(value=value, type=t, prefix=prefix):
                self.echo(prefix, self.atom(value), t, "" if prefix else f" : {qtype_to_name_str(t)}")
            case ir.EchoText(text=text):
                self.emit(f"puts({c_string_literal(text)});")
            case _:
                raise NotImplementedError(f"C printing of {type(s).__name__}")

    def atom_type(self, a: ir.Atom) -> QType:
        return a.type if isinstance(a, ir.Var) else a.shape.type

    def echo(self, prefix: str, value: str, t: QType, suffix: str) -> None:
        wrapped = qval_wrap(value, t)
        if kind := _value_kind(t):
            self.emit(f"quest_print_value({c_string_literal(prefix)}, {wrapped}, {c_string_literal(kind)}, "
                      f"{c_string_literal(suffix)});")
        else:
            self.emit(f"quest_print_typed({c_string_literal(prefix)}, {wrapped}, {self.descriptor(t)}, "
                      f"{c_string_literal(suffix)});")

    # Functions

    def declare_locals(self, body: ir.Body, exclude: set[int]) -> list[tuple[str, str]]:
        """The C declarations of the variables a function (or a top level) binds, but for exclude's."""
        decls = []
        seen = set(exclude)
        for s in walk_statements(body, into_functions=False):
            if isinstance(s, ir.Try):
                self.handler_vars.add(id(s.exception))
            for v in statement_binders(s):
                # A declared variable is bound by its declaration and its let
                if id(v) in seen or self.is_ok(v.type):
                    continue
                seen.add(id(v))
                c_t = self.var_c_type(v)
                if id(v) in self.fs.volatile:
                    c_t += " volatile"
                decls.append((c_t, self.name(v)))
        return decls

    def volatile_vars(self, body: ir.Body) -> set[int]:
        """The variables a try body assigns (or binds, having been declared before it), which C must declare volatile
        for the handler to read them after longjmp."""
        found: set[int] = set()
        declared = {id(s.var) for s in walk_statements(body, into_functions=False) if isinstance(s, ir.Declare)}
        for s in walk_statements(body, into_functions=False):
            if isinstance(s, ir.Try):
                for t in walk_statements(s.body, into_functions=False):
                    if isinstance(t, ir.Assign) or (isinstance(t, ir.Let) and id(t.var) in declared):
                        found.add(id(t.var))
        return found

    def function_signature(self, f: ir.Function) -> str:
        quants, _, _ = _signature(f.var.type)
        own = f.type_params[len(f.type_params) - len(quants):] if quants else ()
        params = ["void *_raw_env"]
        for tp in own:
            params.append(f"const QTypeDescriptor *{self.descriptor_param(f, tp)}")
        for v, mode in f.params:
            c_t = "QVal" if self.is_ok(v.type) else self.c_type(v.type)
            params.append(f"{c_t} {'*' if mode != 'value' else ''}{self.name(v)}")
        ret = "void" if self.is_ok(f.result_type) else self.c_type(f.result_type)
        return f"static Q_UNUSED {ret} {self.code_name(f)}({', '.join(params)})"

    def descriptor_param(self, f: ir.Function, tp: ir.TypeParam) -> str:
        """The C parameter of a function's own type parameter, which holds its descriptor."""
        key = (id(f), tp.symbol_id)
        if key not in self.descriptor_params:
            self.descriptor_params[key] = self.fresh_name(f"descriptor_{tp.name}")
        return self.descriptor_params[key]

    def function(self, f: ir.Function) -> list[str]:
        self.fs = _FunctionState(f)
        self.fs.volatile = self.volatile_vars(f.body)
        saved_descriptors = dict(self.descriptors)
        quants, _, _ = _signature(f.var.type)
        n_captured = len(f.type_params) - len(quants)
        signature = self.function_signature(f)
        prologue: list[str] = []
        for tp in f.type_params[n_captured:]:
            self.descriptors[tp.symbol_id] = self.descriptor_param(f, tp)
            prologue.append(f"(void){self.descriptors[tp.symbol_id]};")
        if f.env is not None:
            env_struct = f"struct QEnv_{self.code_name(f)}"
            prologue.append(f"{env_struct} *{self.name(f.env)} = ({env_struct} *)_raw_env;")
            for i, tp in enumerate(f.type_params[:n_captured]):
                d = self.fresh_name(f"descriptor_{tp.name}")
                self.descriptors[tp.symbol_id] = d
                prologue.append(f"const QTypeDescriptor *{d} = {self.name(f.env)}->d{i};")
                prologue.append(f"(void){d};")
        else:
            prologue.append("(void)_raw_env;")
        exclude = {id(v) for v, _ in f.params}
        decls = self.declare_locals(f.body, exclude)
        self.lines = []
        self.indent = 1
        self.body(f.body)
        body_lines = self.lines
        self.descriptors = saved_descriptors
        out = [signature + " {"]
        out.extend(f"    {line}" for line in prologue)
        out.extend(f"    {c_t} {name};" for c_t, name in decls + self.fs.locals)
        out.extend(body_lines)
        out.append("}")
        out.append("")
        return out

    def env_struct(self, f: ir.Function, closure: ir.MakeClosure) -> list[str]:
        lines = [f"struct QEnv_{self.code_name(f)} {{"]
        for i, _ in enumerate(closure.type_args):
            lines.append(f"    const QTypeDescriptor *d{i};")
        for i, a in enumerate(closure.captures):
            t = a.type if isinstance(a, ir.Var) else a.shape.type
            lines.append(f"    {self.c_type(t)} c{i};")
        if not closure.type_args and not closure.captures:
            lines.append("    char _unused;")
        lines.append("};")
        return lines

    # The unit

    def top_level(self, body: ir.Body) -> tuple[list[tuple[str, str]], list[str]]:
        """A top level's local declarations (its variables bound in loops) and its statements."""
        self.fs = _FunctionState(None)
        self.fs.volatile = self.volatile_vars(body)
        decls = self.declare_locals(body, self.globals)
        self.lines = []
        self.indent = 1
        self.body(body)
        return decls + self.fs.locals, self.lines

    def print_unit(self) -> str:
        self.join_params = {
            s.label: s.params
            for body in [self.unit.main, *(m.init for m in self.unit.modules), *(f.body for f in self.unit.functions)]
            for s in walk_statements(body, into_functions=False)
            if isinstance(s, ir.Join)
        }
        # The closures of each function (for its environment's struct), and those bound by lets (direct calls)
        closures_of: dict[int, ir.MakeClosure] = {}
        for body in [self.unit.main, *(m.init for m in self.unit.modules), *(f.body for f in self.unit.functions)]:
            for s in walk_statements(body, into_functions=False):
                if isinstance(s, ir.Let) and isinstance(s.value, ir.MakeClosure):
                    closures_of.setdefault(id(s.value.code), s.value)
                    self.closures[id(s.var)] = s.value

        functions = []
        for f in self.unit.functions:
            functions.extend(self.function(f))
        module_inits = []
        for m in self.unit.modules:
            module_inits.extend(self.module_init(m))
        main_decls, main_lines = self.top_level(self.unit.main)

        out = ["/* Emitted by the Quest IR C printer */", '#include "quest_runtime.h"', ""]
        out.extend(self.declarations())
        out.extend(self.import_declarations())
        for f in self.unit.functions:
            closure = closures_of.get(id(f))
            if f.env is not None and closure is not None:
                out.extend(self.env_struct(f, closure))
        out.append("")
        for f in self.unit.functions:
            out.append(self.function_signature(f) + ";")
            code = self.code_name(f)
            out.append(f"static Q_UNUSED QClosure {code}_closure = {{ (void *){code}, NULL }};")
        out.append("")
        for v_id, name, c_t in self.global_declarations():
            out.append(f"static {c_t} {name};")
        for m in self.unit.modules:
            clean = mangle_module_name(m.name)
            out.append(f"static QRecordVal {module_record_ident(clean)};")
            out.append(f"static bool qv_mod_{clean}_initialized = false;")
        out.append("")
        out.extend(functions)
        out.extend(module_inits)
        out.append("int main(int argc, char **argv) {")
        out.append("    quest_gc_init();")
        out.append("    quest_builtins_init(argc, argv);")
        for view_t, layout_t in self.needed_dicts:
            dict_name = self.ctx.offset_dict_instance_name(view_t, layout_t)
            out.append(f"    quest_register_record_dict({self.descriptor(view_t)}, {self.descriptor(layout_t)}, "
                       f"&{dict_name});")
        for imp in self.unit.imports:
            out.append(f"    qv_mod_{mangle_module_name(imp.canonical_path)}_init();")
        for m in self.unit.modules:
            out.append(f"    qv_mod_{mangle_module_name(m.name)}_init();")
        out.extend(f"    {c_t} {name};" for c_t, name in main_decls)
        out.extend(main_lines)
        out.append("    return 0;")
        out.append("}")
        out.append("")
        return "\n".join(out)

    def global_declarations(self) -> list[tuple[int, str, str]]:
        found = []
        seen: set[int] = set()
        for body in [self.unit.main, *(m.init for m in self.unit.modules)]:
            for s in walk_statements(body, into_functions=False):
                for v in statement_binders(s):
                    if id(v) in self.globals and id(v) not in seen and not self.is_ok(v.type):
                        seen.add(id(v))
                        found.append((id(v), self.name(v), self.var_c_type(v)))
        return found

    def module_init(self, m: ir.Module) -> list[str]:
        clean = mangle_module_name(m.name)
        decls, lines = self.top_level(m.init)
        out = [f"static void qv_mod_{clean}_init(void) {{",
               f"    if (qv_mod_{clean}_initialized) return;",
               f"    qv_mod_{clean}_initialized = true;"]
        out.extend(f"    {c_t} {name};" for c_t, name in decls)
        out.extend(lines)
        rec_t = QRecordType(tuple(QRecordField(name=n, type_val=v.type) for n, v in m.members.items()))
        self.types.append(rec_t)
        struct = record_struct_name(rec_t, self.ctx)
        out.append(f"    {struct} *_payload = ({struct} *)quest_alloc(sizeof({struct}));")
        out.append(f"    _payload->header.descriptor = {self.descriptor(rec_t)};")
        for n, v in sorted(m.members.items()):
            if not self.is_ok(v.type):
                out.append(f"    _payload->qf_{n} = {self.name(v)};")
        dict_name = self.ctx.offset_dict_instance_name(rec_t, rec_t)
        out.append(f"    {module_record_ident(clean)} = (QRecordVal){{ .val = (void *)_payload, "
                   f".dict = (const void *)&{dict_name} }};")
        out.append("}")
        out.append("")
        return out

    def import_declarations(self) -> list[str]:
        stubs = []
        seen: set[str] = set()
        for imp in self.unit.imports:
            if imp.canonical_path in seen:
                continue
            seen.add(imp.canonical_path)
            scope = self.module_scopes.get(id(imp)) or Scope()
            stubs.append(TypedModule(name=imp.canonical_path, interface_name=imp.interface_path, bindings=(),
                                     scope=scope, is_precompiled=True))
        lines = []
        for stub in stubs:
            clean = mangle_module_name(stub.name)
            lines.append(f"extern QRecordVal {module_record_ident(clean)};")
            lines.append(f"extern void qv_mod_{clean}_init(void);")
        lines.extend(self.decl_emitter.emit_precompiled_module_declarations(SimpleNamespace(sorted_modules=stubs)))
        return lines

    def declarations(self) -> list[str]:
        """The declarations of the types the unit uses: structs, offset tables, descriptors, and adapters."""
        for scope in self.module_scopes.values():
            self.types.append(build_record_type_from_scope(scope))
        emitter = CEmitter()
        emitter.record_ctx = self.ctx
        decl = CDeclarationEmitter(
            record_ctx=self.ctx,
            c_type_fn=lambda t: qtype_to_c_type(t, self.ctx),
            param_sigs_fn=emitter._param_signatures,
        )
        self.decl_emitter = decl
        agg_types, variant_types, all_types = collect_aggregate_types(list(self.types), self.ctx)
        records = [t for _, t in agg_types if isinstance(t, QRecordType)]
        tuples = [t for _, t in agg_types if isinstance(t, QTupleType)]
        needed: dict[tuple[str, str], tuple] = {}
        for t in records:
            needed[(record_struct_name(t, self.ctx),) * 2] = (t, t)
            for s in records:
                if s is not t and is_record_subtype(s, t):
                    needed[(record_struct_name(t, self.ctx), record_struct_name(s, self.ctx))] = (t, s)
        tuple_coercions = {
            (tuple_struct_name(t), tuple_struct_name(s)): (t, s)
            for t in tuples for s in tuples if s is not t and is_tuple_subtype(s, t)
        }
        variant_coercions = {
            (type_to_c_tag(t), type_to_c_tag(s)): (t, s)
            for t in variant_types for s in variant_types if s is not t and is_variant_subtype(s, t)
        }
        self.needed_dicts = list(needed.values())
        lines = []
        lines.extend(decl.emit_forward_typedefs(agg_types))
        lines.extend(decl.emit_aggregate_structs(agg_types))
        lines.extend(decl.emit_evidence_dictionaries(agg_types, self.needed_dicts))
        lines.extend(decl.emit_coercion_tables(list(tuple_coercions.values()), list(variant_coercions.values())))
        lines.extend(decl.emit_type_descriptors(agg_types, variant_types, self.descriptor, all_types))
        lines.extend(emitter._emit_fun_type_adapters(decl.emitted_fun_types))
        return lines


def print_c(unit: ir.Unit, env: Any) -> str:
    """The C translation of a represented unit."""
    scopes: dict[int, Scope] = {}
    for imp in unit.imports:
        scope = None
        if env is not None:
            scope = (
                env.lookup_module(imp.canonical_path)
                or env.lookup_module(imp.module_path)
                or env.lookup_module(imp.name)
                or env.lookup_interface(imp.interface_path)
            )
        if scope is not None:
            scopes[id(imp)] = scope
    return CPrinter(unit, env, scopes).print_unit()
