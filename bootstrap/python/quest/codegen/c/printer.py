"""The C printer (docs/ir.md §8.5): prints a represented IR unit as C, the IR's backend.

It prints what the passes decided: each IR function is a C function taking its closure's environment first (and its
own type parameters' descriptors, then its parameters), each closure a QClosure of one (a static one when it captures
nothing), each variable a C variable of its type's representation (globals for the variables the top levels bind
outside loops, declared at file scope), and each structured statement a C statement: join points and loop exits are
labels, and try regions setjmp handlers, popped on every way out. Conversions are `convert` operations, printed as
their plans say. The declarations of the types it uses (structs, descriptors, function type adapters) are
c/declarations.py's, and the representations codegen/layout.py's, spelled in C by c/types.py
(docs/c-representation.md). A module file's unit
exports its interface's members: its record (`qm_<module>`), initializer (`qv_mod_<module>_init`), and a function
for each function or polymorphic value (`qv_<module>_<member>`), the ABI other units link against.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any, Optional

from quest.codegen.c.declarations import CDeclarationEmitter, collect_aggregate_types, module_function_signature
from quest.codegen.c.types import (
    c_char_literal,
    c_string_literal,
    closure_fn_ptr_type,
    descriptor_form,
    MissingDescriptorError,
    qtype_to_c_type,
    qval_unwrap,
    qval_wrap,
    record_struct_name,
    RecordNamingContext,
)
from quest.codegen.layout import (
    collect_fun_quantifiers,
    is_record_subtype,
    is_tuple_subtype,
    is_variant_subtype,
    is_word_type,
    normalize_type,
    option_struct_name,
    qtype_to_name_str,
    tuple_struct_name,
    type_identity_key,
    type_tag,
)
from quest.codegen.descriptors import hole_var
from quest.codegen.symbols import mangle_ident, mangle_module_ident, mangle_module_name, module_record_ident
from quest.types.env import Scope
from quest.diagnostics import MAIN_FRAME, init_frame
from quest.ir import nodes as ir
from quest.ir.represent import (
    _may_be_stored_as_subtype,
    array_element,
    option_type,
    plan,
    record_type,
    shared_signatures,
    tuple_type,
    variant_type,
)
from quest.ir.walk import global_variables, statement_binders, statement_bodies, walk_statements
from quest.modules.elaboration import build_record_type_from_scope
from quest.typechecker.typed_ast import TypedModule
from quest.types import (
    STRING_TYPE,
    QPathType,
    QTupleField,
    QTupleTypeBinding,
    QTupleTypeFormal,
    BOOL_TYPE,
    CHAR_TYPE,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    QAbstractType,
    QAutoType,
    QAllKind,
    QPowerKind,
    QTypeFun,
    QTypeKind,
    auto_payload_type,
    is_type_equal,
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


_BASE_VALUE_KINDS = (
    (INT_TYPE, "Int"), (REAL_TYPE, "Real"), (BOOL_TYPE, "Bool"), (CHAR_TYPE, "Char"), (STRING_TYPE, "String"),
    (OK_TYPE, "Ok"),
)


def _value_kind(t: QType) -> str:
    """How quest_print_value writes a value of type t, as the interpreter does (format_value_with_type), or "" if
    quest_print_typed writes it from its type descriptor."""
    t = normalize_type(t)
    if is_word_type(t):
        return "Word"
    if isinstance(t, (QFunType, QAllType)):
        return "fun"
    if isinstance(t, (QPathType, QTypeVar, QAbstractType)):
        return "hidden"
    return next((kind for base, kind in _BASE_VALUE_KINDS if t is base), "")


def _existential_tuple_display(t: QTupleType) -> str:
    """An existential tuple (a package) as the interpreter prints it: its components hidden."""
    parts: list[str] = []
    for comp in t.components:
        if isinstance(comp, QTupleTypeFormal):
            parts.append(f"<Hidden>::{comp.bound}")
        elif isinstance(comp, QTupleTypeBinding):
            parts.append(f"Let {comp.name} = {comp.type_val}")
        elif isinstance(comp, QTupleField):
            if isinstance(comp.type_val, (QPathType, QTypeVar)):
                elem = "<hidden>"
            elif isinstance(comp.type_val, (QFunType, QAllType)):
                elem = "<fun>"
            else:
                elem = "<val>"
            parts.append(f"{comp.name}={elem}" if comp.name else elem)
    return f"tuple {' '.join(parts)} end" if parts else "tuple end"


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
        self.join_params: dict[str, tuple[ir.Var, ...]] = {}
        self.volatile: set[int] = set()


class CPrinter:
    def __init__(
        self, unit: ir.Unit, env: Any, module_scopes: dict[int, Scope], interface_header: Optional[str] = None
    ) -> None:
        self.unit = unit
        self.interface_header = interface_header
        self.env = env
        self.ctx = RecordNamingContext()
        self.module_scopes = module_scopes
        self.globals = global_variables(unit)
        self.names: dict[int, str] = {}
        self.used_names: set[str] = set()
        self.code_names: dict[int, str] = {}
        # Closures bound by lets (by variable), whose calls call their functions directly
        self.closures: dict[int, ir.MakeClosure] = {}
        # External C functions bound by lets (by variable), which are called directly
        self.externals: dict[int, ir.External] = {}
        self.handler_vars: set[int] = set()
        self.types: list[QType] = []
        self.descriptors: dict[int, str] = {}
        self.descriptor_params: dict[tuple[int, int], str] = {}
        self.fs = _FunctionState(None)
        self.lines: list[str] = []
        self.indent = 1
        self.tmp = 0
        # The thunks printed (adapters and type applications), by what they convert
        self.thunks: dict[tuple, Any] = {}
        self.thunk_decls: list[str] = []
        self.thunk_defs: list[str] = []

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
        """The descriptor of a type: a type parameter's, passed to its function; a closed type's static one; or, for a
        type mentioning type parameters in scope, its template (a hole for each), instantiated with theirs."""
        bare = strip_aliases(t.prune() if hasattr(t, "prune") else t)
        if isinstance(bare, (QTypeVar, QAbstractType)) and bare.symbol_id in self.descriptors:
            return self.descriptors[bare.symbol_id]
        params = self.free_type_vars(bare, lambda v: v.symbol_id in self.descriptors)
        return self.template_descriptor(bare, params, [self.descriptors[v.symbol_id] for v in params])

    def template_descriptor(self, t: QType, holes: list, args: list[str]) -> str:
        """The descriptor of t with a hole for each of holes (type variables), instantiated with args."""
        template = t.substitute({v.symbol_id: hole_var(i, v.bound) for i, v in enumerate(holes)}) if holes else t
        self.types.append(template)
        try:
            form = descriptor_form(template, self.ctx)
        except MissingDescriptorError as e:
            raise NotImplementedError(f"C code generation: {e}") from None
        if form.kind in ("base", "bound_var") or not holes:
            return form.c_expr
        return (
            f"quest_instantiate_descriptor({form.c_expr}, {len(holes)}, "
            f"(const QTypeDescriptor *const[]){{ {', '.join(args)} }})"
        )

    def generic_layout_descriptor(self, t: QType, instantiation: dict[int, QType]) -> str:
        """The descriptor of a polymorphic callee's type t laid out as the callee lays it out at the call's type
        arguments: its template, a hole for each of the callee's type parameters (and for each in scope), instantiated
        with the type arguments' descriptors (and theirs)."""
        bare = strip_aliases(t)
        params = self.free_type_vars(bare, lambda v: v.symbol_id in instantiation)
        in_scope = self.free_type_vars(
            bare, lambda v: v.symbol_id in self.descriptors and v.symbol_id not in instantiation
        )
        args = [self.descriptor(instantiation[v.symbol_id]) for v in params]
        args.extend(self.descriptors[v.symbol_id] for v in in_scope)
        return self.template_descriptor(bare, params + in_scope, args)

    @staticmethod
    def free_type_vars(t: QType, wanted) -> list:
        """The type variables occurring free in t for which wanted holds, in order of appearance."""
        free = getattr(t, "_fv", None)
        if not free:
            return []
        found: dict[int, Any] = {}
        seen: set[int] = set()

        def visit(node: Any) -> None:
            if id(node) in seen:
                return
            seen.add(id(node))
            if isinstance(node, (QTypeVar, QAbstractType)) and node.symbol_id in free and wanted(node):
                found.setdefault(node.symbol_id, node)
            if isinstance(node, (tuple, list)):
                for item in node:
                    visit(item)
            elif dataclasses.is_dataclass(node) and not isinstance(node, type):
                for f in dataclasses.fields(node):
                    visit(getattr(node, f.name))

        visit(t)
        return list(found.values())

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
            case ir.Prim(op=op, args=args, offset=offset):
                return self.prim(op, args, offset)
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
                if t is not None and self.is_function(t):
                    return self.external_closure(o, t)
                return symbol
            case ir.CallExternal(type_args=type_args, args=args):
                return self.external_call(o, [self.descriptor(t) for t in type_args], [self.atom(a) for a in args])
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
            case ir.Addr(base=base, name=name) if name is not None:
                rt = record_type(self.atom_type(base))
                field = next(f for f in rt.fields if f.name == name)
                return self.record_field(self.atom(base), rt, name, field.type_val, as_ref=True)
            case ir.Addr(base=base, index=index) if isinstance(index, int):
                return f"(&({self.atom(base)}->_{index}))"
            case ir.Addr(base=base, index=index, offset=offset):
                return self.array_slot(self.atom(base), self.atom(index), array_element(self.atom_type(base)), offset)
            case ir.MakeTuple(args=args):
                return self.make_tuple(result.type, [self.atom(a) for a in args])
            case ir.TupleField(tuple=t, index=index):
                return f"({self.atom(t)}->_{index})"
            case ir.MakeRecord(fields=fields):
                return self.make_record(fields, result.type)
            case ir.RecordField(record=r, name=name):
                rt = record_type(self.atom_type(r))
                field = next(f for f in rt.fields if f.name == name)
                return self.record_field(self.atom(r), rt, name, field.type_val)
            case ir.MakeVariant(tag=tag, payload=payload):
                vt = variant_type(result.type)
                index = self.tag_index(vt, tag)
                if payload is None:
                    return f"((QVariantVal){{ .tag = {index}LL, .payload = Q_OK_VAL }})"
                case = vt.get_variant(tag)
                case_t = case.type_val if case is not None and case.type_val is not None else self.atom_type(payload)
                return f"((QVariantVal){{ .tag = {index}LL, .payload = {qval_wrap(self.atom(payload), case_t)} }})"
            case ir.MakeOption(tag=tag, payload=payload, ordinal=ordinal, offset=offset):
                return self.make_option(tag, payload, ordinal, result.type, offset)
            case ir.IsTag(value=v, tag=tag):
                vt = self.atom_type(v)
                if (var_t := variant_type(vt)) is not None:
                    return f"({self.atom(v)}.tag == {self.tag_index(var_t, tag)}LL)"
                return f"({self.atom(v)}->tag == {self.tag_index(option_type(vt), tag)}LL)"
            case ir.Payload(value=v, tag=tag, offset=offset):
                return self.payload(v, tag, result.type, offset)
            case ir.MakeArray(args=args):
                return self.make_array(array_element(result.type), [self.atom(a) for a in args], result.type)
            case ir.ArrayRep(count=count, init=init, offset=offset):
                n = f"quest_check_array_count_at({self.atom(count)}, {self.site(offset)})"
                return self.array_new(n, self.atom(init), array_element(result.type))
            case ir.TypeApp():
                return self.type_app(o, result)
            case ir.MakeAuto(witness=witness, auto_type=auto_t, payload=payload):
                return self.make_auto(witness, auto_t, payload)
            case ir.Index(array=a, index=i, offset=offset):
                arr, idx = self.atom(a), self.atom(i)
                self.emit(f"quest_check_array_bounds_at({arr}, {idx}, {self.site(offset)});")
                return self.array_get(arr, idx, array_element(self.atom_type(a)))
        raise NotImplementedError(f"C printing of {type(o).__name__}")

    def convert(self, c: str, plan: ir.Plan) -> str:
        match plan.kind:
            case "box":
                return qval_wrap(c, plan.source)
            case "unbox":
                return qval_unwrap(c, plan.target, self.ctx)
            case "record_view":
                return f"quest_record_view({c}, {self.descriptor(record_type(plan.target))})"
            case "variant_tags":
                source, target = variant_type(plan.source), variant_type(plan.target)
                self.types.extend((source, target))
                v = self.temp("QVariantVal")
                self.emit(f"{v} = {c};")
                tagmap = f"tagmap_{type_tag(target)}_{type_tag(source)}"
                return f"((QVariantVal){{ .tag = {tagmap}[{v}.tag], .payload = {v}.payload }})"
            case "cast":
                return f"(({self.c_type(plan.target)}){c})"
            case "view":
                converted = f"quest_convert({qval_wrap(c, plan.source)}, {self.descriptor(plan.source)}, " \
                            f"{self.descriptor(plan.target)})"
                return qval_unwrap(converted, plan.target, self.ctx)
            case "adapt":
                thunk = self.adapter(plan)
                clos = self.temp("QClosure *")
                self.emit(f"{clos} = (QClosure *)quest_alloc(sizeof(QClosure));")
                self.emit(f"{clos}->fn = (void *){thunk};")
                self.emit(f"{clos}->env = (void *)({c});")
                return clos
            case "runtime":
                instantiation, to_generic = plan.layout
                generic_t = plan.target if to_generic else plan.source
                native_t = generic_t.substitute(instantiation)
                generic_d = self.generic_layout_descriptor(generic_t, instantiation)
                native_d = self.descriptor(native_t)
                from_t, from_d, to_t, to_d = (
                    (native_t, native_d, generic_t, generic_d) if to_generic else (generic_t, generic_d, native_t, native_d)
                )
                converted = f"quest_convert({qval_wrap(c, from_t)}, {from_d}, {to_d})"
                return qval_unwrap(converted, to_t, self.ctx)
            case "copy":
                source, target = tuple_type(plan.source), tuple_type(plan.target)
                src = self.temp(f"{self.c_type(plan.source)}")
                self.emit(f"{src} = {c};")
                fields = []
                for i, (tf, fp) in enumerate(zip(target.value_fields, plan.fields)):
                    fc = f"{src}->_{i}"
                    fields.append(fc if fp is None else self.convert(fc, fp))
                return self.make_tuple(plan.target, fields)
        raise NotImplementedError(f"conversion plan {plan.kind}")

    # Thunks: closures adapted to other signatures, and polymorphic closures applied to types

    def auxiliary(self):
        """Prints an auxiliary function (a thunk) while printing another: the printing state is saved, and restored
        on leaving the with block."""
        printer = self

        class _Saved:
            def __enter__(self_inner):
                self_inner.saved = (printer.fs, printer.lines, printer.indent, dict(printer.descriptors))
                printer.fs = _FunctionState(None)
                printer.lines = []
                printer.indent = 1
                return self_inner

            def __exit__(self_inner, *exc):
                printer.fs, printer.lines, printer.indent, printer.descriptors = self_inner.saved
                return False

        return _Saved()

    def thunk_params(self, quants, params) -> tuple[list[str], list[str], list[str]]:
        """A thunk's parameter declarations (after its environment), and the names of its descriptor and value
        parameters."""
        decls, descs, names = [], [], []
        for k, _ in enumerate(quants):
            descs.append(f"qd_{k}")
            decls.append(f"const QTypeDescriptor *qd_{k}")
        for i, p in enumerate(params):
            names.append(f"qa_{i}")
            c_t = "QVal" if self.is_ok(p.type_val) else self.c_type(p.type_val)
            decls.append(f"{c_t} {'*' if p.is_var or p.is_out else ''}qa_{i}")
        return decls, descs, names

    def thunk(self, name: str, ret: str, decls: list[str], prologue: list[str]) -> None:
        """Adds a thunk's definition, from the lines printed (in auxiliary()) and its own declarations."""
        body = [f"    {line}" for line in prologue]
        body.extend(f"    {c_t} {n};" for c_t, n in self.fs.locals)
        body.extend(self.lines)
        sig = f"static Q_UNUSED {ret} {name}({', '.join(['void *_raw_env'] + decls)})"
        self.thunk_decls.append(sig + ";")
        self.thunk_defs.extend([sig + " {", *body, "}", ""])

    def adapter(self, plan: ir.Plan) -> str:
        """The thunk adapting a closure of plan.source's type to plan.target's (an adapt plan)."""
        key = ("adapt", type_identity_key(plan.source), type_identity_key(plan.target), self.layout_key(plan.layout))
        if key in self.thunks:
            return self.thunks[key]
        name = self.fresh_name("qa_adapt")
        self.thunks[key] = name
        s_quants, _ = collect_fun_quantifiers(plan.source)
        t_quants, t_inner = collect_fun_quantifiers(plan.target)
        s_params, s_result, t_params, t_result = shared_signatures(plan.source, plan.target)
        with self.auxiliary():
            decls, descs, names = self.thunk_params(t_quants, t_params)
            for q, d in zip(s_quants, descs):
                self.descriptors[q.symbol_id] = d
            for q, d in zip(t_quants, descs):
                self.descriptors[q.symbol_id] = d
            args = []
            for p, n, fp in zip(t_params, names, plan.fields):
                args.append(n if fp is None else self.convert(n, fp))
            call = f"(({closure_fn_ptr_type(plan.source, self.ctx)})(orig->fn))({', '.join(['orig->env'] + descs + args)})"
            self.types.extend((plan.source, plan.target))
            self.finish_thunk_call(call, s_result, t_result, plan.fields[-1])
            ret = "void" if self.is_ok(t_result) else self.c_type(t_result)
            self.thunk(name, ret, decls, ["QClosure *orig = (QClosure *)_raw_env;"] + [f"(void){d};" for d in descs])
        return name

    def finish_thunk_call(self, call: str, source_result: QType, target_result: QType, result_plan) -> None:
        if self.is_ok(target_result):
            self.emit(f"{call};")
            self.emit("return;")
            return
        if result_plan is None:
            self.emit(f"return {call};")
            return
        r = self.temp(self.c_type(source_result))
        self.emit(f"{r} = {call};")
        self.emit(f"return {self.convert(r, result_plan)};")

    @staticmethod
    def layout_key(layout) -> tuple:
        if layout is None:
            return ()
        instantiation, to_generic = layout
        return (to_generic, tuple(sorted((k, type_identity_key(t)) for k, t in instantiation.items())))

    def type_app(self, o: ir.TypeApp, result: ir.Var) -> str:
        """A polymorphic value applied to types: a closure binding the type arguments' descriptors (converting its
        arguments to the function's generic layouts and its result back), or, for a polymorphic value of no
        parameters, its value at the type arguments."""
        if o.callee is not None:
            orig_t, clos = o.callee.type, self.atom(o.callee)
        elif isinstance(o.module, ir.Module):
            member = o.module.members[o.member]
            orig_t, clos = member.type, self.atom(member)
        else:
            orig_t, clos = o.callee_type, self.module_member(o.module, o.member)
        quants, inner = collect_fun_quantifiers(orig_t)
        descs = [self.descriptor(t) for t in o.type_args]
        instantiation = {q.symbol_id: t for q, t in zip(quants, o.type_args)}
        self.types.extend((orig_t, result.type))
        if not isinstance(inner, QFunType):
            if o.callee is None and isinstance(o.module, ir.Import):
                call = f"{mangle_module_ident(mangle_module_name(o.module.canonical_path), o.member)}({', '.join(descs)})"
            else:
                fn_ptr = closure_fn_ptr_type(orig_t, self.ctx)
                call = f"(({fn_ptr})({clos}->fn))({', '.join([f'{clos}->env'] + descs)})"
            p = plan(inner, result.type, (instantiation, False))
            return call if p is None else self.convert(call, p)
        thunk, env_struct = self.type_app_thunk(orig_t, result.type, o.type_args)
        env = self.temp(f"{env_struct} *")
        self.emit(f"{env} = ({env_struct} *)quest_alloc(sizeof({env_struct}));")
        self.emit(f"{env}->orig = {clos};")
        for i, d in enumerate(descs):
            self.emit(f"{env}->desc[{i}] = {d};")
        c = self.temp("QClosure *")
        self.emit(f"{c} = (QClosure *)quest_alloc(sizeof(QClosure));")
        self.emit(f"{c}->fn = (void *){thunk};")
        self.emit(f"{c}->env = (void *){env};")
        return c

    def type_app_thunk(self, orig_t: QType, target_t: QType, type_args) -> tuple[str, str]:
        key = ("type_app", type_identity_key(orig_t), type_identity_key(target_t),
               tuple(type_identity_key(t) for t in type_args))
        if key in self.thunks:
            return self.thunks[key]
        name = self.fresh_name("qa_type_app")
        env_struct = f"QTypeAppEnv_{name}"
        self.thunks[key] = (name, env_struct)
        n = len(type_args)
        self.thunk_decls.append(
            f"typedef struct {{ QClosure *orig; const QTypeDescriptor *desc[{max(n, 1)}]; }} {env_struct};"
        )
        o_quants, o_inner = collect_fun_quantifiers(orig_t)
        t_quants, t_inner = collect_fun_quantifiers(target_t)
        o_params = o_inner.params if isinstance(o_inner, QFunType) else ()
        t_params = t_inner.params if isinstance(t_inner, QFunType) else ()
        o_result = o_inner.result_type if isinstance(o_inner, QFunType) else o_inner
        t_result = t_inner.result_type if isinstance(t_inner, QFunType) else t_inner
        # The function's type parameters: those bound stand for the type arguments, the others for the closure's own
        instantiation = {q.symbol_id: t for q, t in zip(o_quants, type_args)}
        for oq, tq in zip(o_quants[n:], t_quants):
            instantiation[oq.symbol_id] = QTypeVar(name=tq.name, symbol_id=tq.symbol_id, bound=tq.bound)
        with self.auxiliary():
            decls, descs, names = self.thunk_params(t_quants, t_params)
            for tq, d in zip(t_quants, descs):
                self.descriptors[tq.symbol_id] = d
            args = []
            for tp, op, a in zip(t_params, o_params, names):
                if tp.is_var or tp.is_out:
                    args.append(a)
                    continue
                p = plan(tp.type_val, op.type_val, (instantiation, True))
                args.append(a if p is None else self.convert(a, p))
            env_descs = [f"_env->desc[{i}]" for i in range(n)]
            call_args = ["_env->orig->env"] + env_descs + descs + args
            call = f"(({closure_fn_ptr_type(orig_t, self.ctx)})(_env->orig->fn))({', '.join(call_args)})"
            self.finish_thunk_call(call, o_result, t_result, plan(o_result, t_result, (instantiation, False)))
            ret = "void" if self.is_ok(t_result) else self.c_type(t_result)
            self.thunk(name, ret, decls, [f"{env_struct} *_env = ({env_struct} *)_raw_env;"]
                       + [f"(void){d};" for d in descs])
        return name, env_struct

    # Aggregates (laid out as docs/c-representation.md §5 says)

    def tag_index(self, t, tag: Optional[str]) -> int:
        cases = t.variants if isinstance(t, QVariantType) else t.options
        return next((i for i, case in enumerate(cases) if case.name == tag), 0)

    def make_tuple(self, t: QType, fields: list[str]) -> str:
        struct = tuple_struct_name(tuple_type(t))
        self.c_type(t)
        tmp = self.temp(f"{struct} *")
        self.emit(f"{tmp} = ({struct} *)quest_alloc(sizeof({struct}));")
        for i, c in enumerate(fields):
            self.emit(f"{tmp}->_{i} = {c};")
        return tmp

    def make_record(self, fields, t: QType) -> str:
        concrete = QRecordType(tuple(
            QRecordField(name=n, type_val=self.atom_type(a), is_var=is_var) for n, a, is_var in fields
        ))
        target = record_type(t) or concrete
        self.types.extend((concrete, target))
        struct = record_struct_name(concrete, self.ctx)
        payload = self.temp(f"{struct} *")
        self.emit(f"{payload} = ({struct} *)quest_alloc(sizeof({struct}));")
        self.emit(f"{payload}->header.descriptor = {self.descriptor(concrete)};")
        for n, a, _ in fields:
            if not self.is_ok(self.atom_type(a)):
                self.emit(f"{payload}->qf_{n} = {self.atom(a)};")
        if is_type_equal(target, concrete) or is_record_subtype(concrete, target):
            dict_expr = f"(const void *)&{self.ctx.offset_dict_instance_name(target, concrete)}"
        else:
            dict_expr = f"quest_record_dict({self.descriptor(target)}, {self.descriptor(concrete)})"
        return f"((QRecordVal){{ .val = (void *){payload}, .dict = {dict_expr} }})"

    def record_field(self, rec: str, rt: QRecordType, name: str, field_t: QType, as_ref: bool = False) -> str:
        """A record's field, through its offset table (a field the payload stores at another type, as its stored
        types say, read as stored and converted)."""
        self.types.append(rt)
        c_fld = self.c_type(field_t)
        dict_t = self.ctx.offset_dict_struct_name(rt)
        ptr = f"(({c_fld} *)((char *){rec}.val + ((const {dict_t} *){rec}.dict)->offset_{name}))"
        if as_ref:
            return ptr
        fields = sorted(rt.fields, key=lambda f: f.name)
        index = next(i for i, f in enumerate(fields) if f.name == name)
        if fields[index].is_var or not (c_fld == "QVal" or _may_be_stored_as_subtype(field_t)):
            return f"(*{ptr})"
        val = self.temp(c_fld)
        stored = f"((const {dict_t} *){rec}.dict)->stored_types"
        converted = qval_unwrap(
            f"quest_convert(quest_slot_read({stored}[{index}], {ptr}), {stored}[{index}], {self.descriptor(field_t)})",
            field_t, self.ctx,
        )
        self.emit(f"if ({stored} != NULL && {stored}[{index}] != NULL) {val} = {converted};")
        self.emit(f"else {val} = *{ptr};")
        return val

    def make_option(self, tag: Optional[str], payload, ordinal, t: QType, offset: Optional[int]) -> str:
        ot = option_type(t)
        self.types.append(ot)
        struct = option_struct_name(ot)
        tmp = self.temp(f"{struct} *")
        self.emit(f"{tmp} = ({struct} *)quest_alloc(sizeof({struct}));")
        if ordinal is not None:
            self.emit(f"{tmp}->tag = quest_check_option_ordinal_at({self.atom(ordinal)}, {len(ot.options)}LL, "
                      f"{self.site(offset)});")
            # The payload is stored as the case of a constant ordinal stores it, and otherwise as the first case
            # does, whose components the union overlays on the other cases' (docs/c-representation.md §5)
            n = ordinal.value if isinstance(ordinal, ir.Const) else 0
            tag = ot.options[n].name if 0 <= n < len(ot.options) else ot.options[0].name
        else:
            self.emit(f"{tmp}->tag = {self.tag_index(ot, tag)}LL;")
        if payload is not None and tag is not None:
            case = ot.get_option(tag)
            pt = normalize_type(case.payload_type) if case is not None and case.payload_type is not None else None
            p = self.atom(payload)
            if isinstance(pt, QTupleType):
                for i, _ in enumerate(pt.value_fields):
                    self.emit(f"{tmp}->u.{tag}._{i} = {p}->_{i};")
            else:
                self.emit(f"{tmp}->u.{tag}.val = {p};")
        return tmp

    def option_field(self, src: str, stored_payload, index: int, wanted: QType) -> str:
        """A component of an option's case, read from the case's struct, in the C type of `wanted`."""
        if not isinstance(stored_payload, QTupleType) or index >= len(stored_payload.value_fields):
            return src
        stored_c = self.c_type(stored_payload.value_fields[index].type_val)
        wanted_c = self.c_type(wanted)
        if stored_c == "QVal" and wanted_c != "QVal":
            return qval_unwrap(src, wanted, self.ctx)
        if stored_c.endswith("*") and wanted_c.endswith("*") and stored_c != wanted_c:
            return f"({wanted_c})({src})"
        return src

    def option_case_tuple(self, opt: str, ot, tag: str, tuple_t: QType, offset: int) -> str:
        """A new tuple of an option's case components (after `offset` components of tuple_t, such as the ordinal)."""
        tt = tuple_type(tuple_t)
        struct = tuple_struct_name(tt)
        self.c_type(tuple_t)
        tmp = self.temp(f"{struct} *")
        self.emit(f"{tmp} = ({struct} *)quest_alloc(sizeof({struct}));")
        case = ot.get_option(tag)
        pt = normalize_type(case.payload_type) if case is not None and case.payload_type is not None else None
        if offset:
            self.emit(f"{tmp}->_0 = {opt}->tag;")
        if isinstance(pt, QTupleType):
            for i, _ in enumerate(pt.value_fields):
                if i + offset < len(tt.value_fields):
                    src = self.option_field(f"{opt}->u.{tag}._{i}", pt, i, tt.value_fields[i + offset].type_val)
                    self.emit(f"{tmp}->_{i + offset} = {src};")
        elif pt is not None:
            self.emit(f"{tmp}->_{offset} = {opt}->u.{tag}.val;")
        return tmp

    def payload(self, v: ir.Atom, tag: str, t: QType, offset: Optional[int]) -> str:
        vt = self.atom_type(v)
        site = self.site(offset)
        if (var_t := variant_type(vt)) is not None:
            index = self.tag_index(var_t, tag)
            self.emit(f"if ({self.atom(v)}.tag != {index}LL) quest_raise_variant_error_at({site});")
            case = var_t.get_variant(tag)
            case_t = case.type_val if case is not None and case.type_val is not None else t
            return qval_unwrap(f"{self.atom(v)}.payload", case_t, self.ctx)
        ot = option_type(vt)
        self.emit(f"if ({self.atom(v)}->tag != {self.tag_index(ot, tag)}LL) quest_raise_variant_error_at({site});")
        return self.option_case_tuple(self.atom(v), ot, tag, t, 1)

    def array_get(self, arr: str, idx: str, elem_t: QType) -> str:
        elem = normalize_type(elem_t)
        if self.wide(elem):
            return f"({arr}->data[{idx}])"
        if self.c_type(elem) == "QVal":
            return f"({arr}->data[{idx}])"
        return qval_unwrap(f"({arr}->data[{idx}])", elem, self.ctx)

    def array_slot(self, arr: str, idx: str, elem_t: QType, offset: Optional[int]) -> str:
        elem = normalize_type(elem_t)
        self.emit(f"quest_check_array_bounds_at({arr}, {idx}, {self.site(offset)});")
        if self.wide(elem):
            return f"(&({arr}->data[{idx}]))"
        c_elem = self.c_type(elem)
        if c_elem == "QVal":
            return f"(&({arr}->data[{idx}]))"
        if elem is INT_TYPE or elem is BOOL_TYPE or elem is CHAR_TYPE:
            return f"(&({arr}->data[{idx}].i))"
        if elem is REAL_TYPE:
            return f"(&({arr}->data[{idx}].r))"
        return f"(({c_elem} *)(&({arr}->data[{idx}].p)))"

    def wide(self, elem: QType) -> bool:
        """Whether an array of elem stores its elements wide (records and variants, 16 bytes each)."""
        return self.c_type(elem) in ("QRecordVal", "QVariantVal")

    def array_new(self, count: str, init: str, elem_t: QType) -> str:
        elem = normalize_type(elem_t)
        match self.c_type(elem):
            case "QRecordVal":
                return f"quest_array_new_wide_record({count}, {init})"
            case "QVariantVal":
                return f"quest_array_new_wide_variant({count}, {init})"
        return f"quest_array_new({count}, {qval_wrap(init, elem)})"

    def make_array(self, elem_t: QType, elements: list[str], t: QType) -> str:
        elem = normalize_type(elem_t)
        n = len(elements)
        c_elem = self.c_type(elem)
        arr = self.temp(self.c_type(t))
        if c_elem in ("QRecordVal", "QVariantVal"):
            struct = "QArrayWideRecord" if c_elem == "QRecordVal" else "QArrayWideVariant"
            self.emit(f"{arr} = ({struct} *)quest_alloc(sizeof({struct}) + (size_t)({n}LL) * sizeof({c_elem}));")
            self.emit(f"{arr}->length = {n}LL;")
            for i, c in enumerate(elements):
                self.emit(f"{arr}->data[{i}LL] = {c};")
        else:
            self.emit(f"{arr} = (QArray *)quest_alloc(sizeof(QArray) + (size_t)({n}LL) * sizeof(QVal));")
            self.emit(f"{arr}->length = {n}LL;")
            for i, c in enumerate(elements):
                self.emit(f"{arr}->data[{i}LL] = {qval_wrap(c, elem)};")
        return arr

    def site(self, offset: Optional[int]) -> str:
        """The site of a raise at offset in the unit's file, as a C string ("file:line:col"), or NULL if it is not
        known (docs/exceptions.md §3.3)."""
        source_map = self.unit.source_map
        if offset is None or source_map is None:
            return "NULL"
        loc = source_map.locate(offset)
        return c_string_literal(f"{loc.file_name}:{loc.line}:{loc.column}")

    def prim(self, op: str, args: tuple[ir.Atom, ...], offset: Optional[int] = None) -> str:
        cs = [self.atom(a) for a in args]
        if op == "not":
            return f"(!({cs[0]}))"
        if op == "extent":
            return f"(({cs[0]})->length)"
        left, right = cs
        if op == "/":
            return f"quest_int_div_at({left}, {right}, {self.site(offset)})"
        if op in ("%", "mod"):
            return f"quest_int_mod_at({left}, {right}, {self.site(offset)})"
        if op in _REAL_OPS:
            return f"{_REAL_OPS[op]}_at({left}, {right}, {self.site(offset)})"
        if op == "^^":
            return f"quest_real_pow_at({left}, {right}, {self.site(offset)})"
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

    @staticmethod
    def is_function(t: QType) -> bool:
        return isinstance(collect_fun_quantifiers(strip_aliases(t))[1], QFunType)

    @staticmethod
    def external_call(o, descs: list[str], args: list[str]) -> str:
        """A call of an external C function (its template filled in, if it has one)."""
        if o.inline_template:
            return o.inline_template.format(*descs, *args)
        return f"{o.symbol}({', '.join(descs + args)})"

    def external_closure(self, o: ir.External, t: QType) -> str:
        """An external C function as a value: a static closure over a thunk calling it."""
        key = ("external", o.symbol, o.inline_template, o.pass_type_descriptors, type_identity_key(t))
        if key in self.thunks:
            return f"(&{self.thunks[key]}_closure)"
        name = self.fresh_name("qx_" + mangle_ident(o.symbol).removeprefix("qv_"))
        self.thunks[key] = name
        quants, params, result_t = _signature(t)
        with self.auxiliary():
            decls, descs, names = self.thunk_params(quants, params)
            call = self.external_call(o, descs if o.pass_type_descriptors else [], names)
            ret = "void" if self.is_ok(result_t) else self.c_type(result_t)
            self.emit(f"{call};" if ret == "void" else f"return {call};")
            self.thunk(name, ret, decls, ["(void)_raw_env;"] + [f"(void){d};" for d in descs])
        self.thunk_decls.append(f"static Q_UNUSED QClosure {name}_closure = {{ (void *){name}, NULL }};")
        return f"(&{name}_closure)"

    def call_closure(self, callee: ir.Var, descs: list[str], args: tuple[ir.Atom, ...]) -> str:
        c_args = descs + self.args((), args)
        external = self.externals.get(id(callee))
        if external is not None:
            return self.external_call(external, descs if external.pass_type_descriptors else [], self.args((), args))
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
                if init is not None:
                    self.assign(var, self.atom(init))
            case ir.Declare():
                pass
            case ir.Assign(var=var, value=value):
                self.assign(var, self.atom(value))
            case ir.Store(value=value, address=address) if address is not None:
                self.emit(f"*{self.atom(address)} = {self.atom(value)};")
            case ir.Store(value=value, base=base, name=name) if name is not None:
                rt = record_type(self.atom_type(base))
                field = next(f for f in rt.fields if f.name == name)
                ptr = self.record_field(self.atom(base), rt, name, field.type_val, as_ref=True)
                self.emit(f"*{ptr} = {self.atom(value)};")
            case ir.Store(value=value, base=base, index=index) if isinstance(index, int):
                self.emit(f"{self.atom(base)}->_{index} = {self.atom(value)};")
            case ir.Store(value=value, base=base, index=index, offset=offset):
                arr, idx = self.atom(base), self.atom(index)
                elem = normalize_type(array_element(self.atom_type(base)))
                self.emit(f"quest_check_array_bounds_at({arr}, {idx}, {self.site(offset)});")
                c = self.atom(value)
                self.emit(f"{arr}->data[{idx}] = {c if self.wide(elem) else qval_wrap(c, elem)};")
            case ir.Switch(value=value, cases=cases, else_body=else_body):
                self.switch(value, cases, else_body)
            case ir.Inspect(value=value, cases=cases, else_body=else_body, auto_type=auto_t, offset=offset):
                self.inspect(value, cases, else_body, auto_t, offset)
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
                # Labels are unique within a function (a clone keeps its original's)
                self.fs.join_params[label] = params
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
                join_params = self.fs.join_params[label]
                for p, a in zip(join_params, args):
                    self.assign(p, self.atom(a))
                self.leave_to(self.fs.label_depth[label])
                self.emit(f"goto {label};")
            case ir.Try(body=body, exception=exception, handler=handler, catches=catches):
                h = self.fresh_name("_qh")
                self.emit("{")
                self.indent += 1
                self.emit(f"QExceptionHandler {h};")
                self.emit(f"{h}.prev = quest_current_exception_handler;")
                self.emit_catches(h, catches)
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
            case ir.Raise(exception=e, payload=p, offset=offset):
                payload = "Q_OK_VAL" if p is None else qval_wrap(self.atom(p), self.atom_type(p))
                self.emit(f"quest_raise_at({self.atom(e)}, {payload}, {self.site(offset)});")
            case ir.Reraise(exception=e):
                self.emit(f"quest_reraise({self.name(e)});")
            case ir.Unreachable():
                self.emit("abort();")
            case ir.Echo(value=value, type=t, prefix=prefix):
                self.echo(prefix, self.atom(value), t, "" if prefix else f" : {qtype_to_name_str(t)}")
            case ir.EchoText(text=text):
                self.emit(f"puts({c_string_literal(text)});")
            case _:
                raise NotImplementedError(f"C printing of {type(s).__name__}")

    def switch(self, value: ir.Atom, cases, else_body: Optional[ir.Body]) -> None:
        vt = self.atom_type(value)
        v = self.atom(value)
        var_t = variant_type(vt)
        t = var_t if var_t is not None else option_type(vt)
        self.types.append(t)
        self.emit(f"switch ({v}{'.tag' if var_t is not None else '->tag'}) {{")
        self.indent += 1
        for c in cases:
            for tag in c.tags:
                self.emit(f"case {self.tag_index(t, tag)}LL:")
            self.emit("{")
            self.indent += 1
            if c.binder is not None and not self.is_ok(c.binder.type):
                if var_t is not None:
                    self.assign(c.binder, qval_unwrap(f"{v}.payload", c.binder.type, self.ctx))
                elif tuple_type(c.binder.type) is not None:
                    self.assign(c.binder, self.option_case_tuple(v, t, c.tags[0], c.binder.type, 0))
                else:
                    self.assign(c.binder, f"{v}->u.{c.tags[0]}.val")
            self.body(c.body)
            self.emit("break;")
            self.indent -= 1
            self.emit("}")
        self.emit("default: {")
        if else_body is not None:
            self.block(else_body)
        else:
            self.emit("    quest_raise_variant_error();")
        self.emit("    break;")
        self.emit("}")
        self.indent -= 1
        self.emit("}")

    # Auto values (docs/c-representation.md §6.4.4): a type component's descriptor and the payload, stored in the
    # witness-independent layout (docs/c-representation.md §8)

    def bounded_param_in_scope(self, t: QType) -> Optional[QType]:
        """The bound B of a type parameter in scope bounded by a record, variant, or option type (A <: B), which
        generic code holds its values viewed at; None for any other type."""
        bare = strip_aliases(t.prune() if hasattr(t, "prune") else t)
        if not isinstance(bare, (QTypeVar, QAbstractType)) or bare.symbol_id not in self.descriptors:
            return None
        if not isinstance(bare.bound, QPowerKind):
            return None
        bound = bare.bound.bound
        if not _may_be_stored_as_subtype(bound) or isinstance(normalize_type(bound), (QFunType, QAllType)):
            return None
        return bound

    @staticmethod
    def is_auto_param(auto_t: QAutoType, t: QType) -> bool:
        bare = strip_aliases(t)
        return isinstance(bare, (QTypeVar, QAbstractType)) and bare.symbol_id == auto_t.symbol_id

    def make_auto(self, witness: QType, auto_t: QAutoType, payload: ir.Atom) -> str:
        stored_t = auto_payload_type(auto_t)
        self.types.extend((auto_t, stored_t))
        c_payload = self.atom(payload)
        desc = self.descriptor(witness)
        if (bound := self.bounded_param_in_scope(witness)) is not None:
            # Generic code holds a value of a bounded type parameter viewed at the bound; concrete code stores the
            # type component's values at their own type, as inspect reads them, so convert them to it
            struct = tuple_struct_name(stored_t)
            p = self.temp(f"{struct} *")
            self.emit(f"{p} = ({struct} *)({c_payload});")
            for i, (sig_f, stored_f) in enumerate(zip(auto_t.signature, stored_t.value_fields)):
                if self.is_auto_param(auto_t, sig_f.type_val):
                    src = f"{p}->_{i}"
                    converted = f"quest_convert({qval_wrap(src, bound)}, {self.descriptor(bound)}, {desc})"
                    self.emit(f"{src} = {qval_unwrap(converted, stored_f.type_val, self.ctx)};")
            c_payload = p
        return f"quest_auto_new({desc}, {qval_wrap(c_payload, stored_t)})"

    def auto_layouts_agree(self, stored_t: QTupleType, arm_t: QTupleType) -> bool:
        """Whether a stored auto payload can be read in place through the arm's struct: each component has the same
        representation, or is stored as a QVal holding a scalar or pointer."""
        for stored_f, arm_f in zip(stored_t.value_fields, arm_t.value_fields):
            stored_c, arm_c = self.c_type(stored_f.type_val), self.c_type(arm_f.type_val)
            if stored_c == arm_c:
                if isinstance(arm_f.type_val, (QFunType, QAllType)) and (
                    closure_fn_ptr_type(stored_f.type_val, self.ctx) != closure_fn_ptr_type(arm_f.type_val, self.ctx)
                ):
                    return False
            elif stored_c != "QVal" or arm_c in ("QRecordVal", "QVariantVal", "void"):
                return False
        return True

    def auto_arm_converted(self, auto_t: QAutoType, stored: str, stored_t: QTupleType, arm_t: QTupleType,
                           tgt: str, param_target: Optional[str] = None) -> str:
        """The components S[T] of an auto value, converted by descriptor from the stored ones (those whose types
        mention the auto type's parameter; the others copied)."""
        arm_struct = tuple_struct_name(arm_t)
        self.types.append(arm_t)
        arm = self.temp(f"{arm_struct} *")
        self.emit(f"{arm} = ({arm_struct} *)quest_alloc(sizeof({arm_struct}));")
        for i, (sig_f, stored_f, arm_f) in enumerate(zip(auto_t.signature, stored_t.value_fields, arm_t.value_fields)):
            src = f"{stored}->_{i}"
            if auto_t.symbol_id not in sig_f.type_val._fv:
                self.emit(f"{arm}->_{i} = {src};")
                continue
            to_desc = self.descriptor(arm_f.type_val)
            if self.is_auto_param(auto_t, sig_f.type_val):
                from_desc = f"{tgt}->type_desc"
                if param_target is not None:
                    to_desc = param_target
            else:
                saved = dict(self.descriptors)
                self.descriptors[auto_t.symbol_id] = f"{tgt}->type_desc"
                try:
                    from_desc = self.descriptor(stored_f.type_val)
                finally:
                    self.descriptors = saved
            as_qval = src if self.c_type(stored_f.type_val) == "QVal" else qval_wrap(src, stored_f.type_val)
            viewed = f"quest_convert({as_qval}, {from_desc}, {to_desc})"
            self.emit(f"{arm}->_{i} = {qval_unwrap(viewed, arm_f.type_val, self.ctx)};")
        return arm

    def inspect(self, value: ir.Atom, cases, else_body: Optional[ir.Body], auto_t: QAutoType,
                offset: Optional[int]) -> None:
        stored_t = auto_payload_type(auto_t)
        stored_struct = tuple_struct_name(stored_t)
        self.types.extend((auto_t, stored_t))
        tgt = self.temp("const QAuto *")
        self.emit(f"{tgt} = {self.atom(value)};")
        stored = self.temp(f"{stored_struct} *")
        self.emit(f"{stored} = ({stored_struct} *){tgt}->payload.p;")
        for i, case in enumerate(cases):
            match_desc = self.descriptor(case.match_type)
            cond = f"quest_is_subtype({tgt}->type_desc, {match_desc})"
            if case.exact:
                cond = f"{cond} && quest_is_subtype({match_desc}, {tgt}->type_desc)"
            self.emit(f"{'if' if i == 0 else '} else if'} ({cond}) {{")
            self.indent += 1
            match_bound = self.bounded_param_in_scope(case.match_type)
            if case.binders:
                arm_t = auto_payload_type(auto_t, case.match_type)
                if match_bound is not None:
                    if any(f.is_var for f in auto_t.signature):
                        raise NotImplementedError(
                            f"C code generation cannot inspect an auto value of type '{auto_t}' at the bounded type "
                            f"parameter '{case.match_type}': its components are converted to the bound, so the var "
                            f"components could not be shared with the auto value"
                        )
                    arm = self.auto_arm_converted(auto_t, stored, stored_t, arm_t, tgt, self.descriptor(match_bound))
                elif case.exact:
                    agree = self.auto_layouts_agree(stored_t, arm_t)
                    if not agree and any(f.is_var for f in auto_t.signature):
                        raise NotImplementedError(
                            f"C code generation cannot inspect an auto value of type '{auto_t}' at type "
                            f"'{case.match_type}': its components need conversion, so the var components could not be "
                            f"shared with the auto value"
                        )
                    arm_struct = tuple_struct_name(arm_t)
                    self.types.append(arm_t)
                    arm = self.temp(f"{arm_struct} *")
                    self.emit(f"if (quest_layout_equivalent({tgt}->type_desc, {match_desc})) {{")
                    if agree:
                        # The binders share the stored components (and so see updates of var components)
                        self.emit(f"    {arm} = ({arm_struct} *){stored};")
                    else:
                        p = plan(stored_t, arm_t)
                        self.indent += 1
                        self.emit(f"{arm} = {stored if p is None else self.convert(stored, p)};")
                        self.indent -= 1
                    self.emit("} else {")
                    self.indent += 1
                    if any(f.is_var for f in auto_t.signature):
                        self.emit(f"quest_layout_conversion_error({tgt}->type_desc, {match_desc});")
                    converted = self.auto_arm_converted(auto_t, stored, stored_t, arm_t, tgt)
                    self.emit(f"{arm} = {converted};")
                    self.indent -= 1
                    self.emit("}")
                else:
                    arm = self.auto_arm_converted(auto_t, stored, stored_t, arm_t, tgt)
                for b in case.binders:
                    p = plan(arm_t, b.type)
                    self.assign(b, arm if p is None else self.convert(arm, p))
            self.body(case.body)
            self.indent -= 1
        if cases:
            self.emit("} else {")
            self.indent += 1
        if else_body is not None:
            self.body(else_body)
        else:
            self.emit(f"quest_raise_dynamic_error_at({self.site(offset)});")
        if cases:
            self.indent -= 1
            self.emit("}")

    def atom_type(self, a: ir.Atom) -> QType:
        return a.type if isinstance(a, ir.Var) else a.shape.type

    def echo(self, prefix: str, value: str, t: QType, suffix: str) -> None:
        bare = strip_aliases(t)
        if prefix and isinstance(bare, QTupleType) and bare.is_existential:
            # A package's components are hidden, so the line is known statically (as the interpreter prints it)
            self.emit(f"puts({c_string_literal(prefix + _existential_tuple_display(bare))});")
            return
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
        # The closures of each function (for its environment's struct), and those bound by lets (direct calls)
        closures_of: dict[int, ir.MakeClosure] = {}
        for body in [self.unit.main, *(m.init for m in self.unit.modules), *(f.body for f in self.unit.functions)]:
            for s in walk_statements(body, into_functions=False):
                if isinstance(s, ir.Let) and isinstance(s.value, ir.MakeClosure):
                    closures_of.setdefault(id(s.value.code), s.value)
                    self.closures[id(s.var)] = s.value
                elif isinstance(s, ir.Let) and isinstance(s.value, ir.External) and self.is_function(s.var.type):
                    # Called directly
                    self.externals[id(s.var)] = s.value

        functions = []
        for f in self.unit.functions:
            functions.extend(self.function(f))
        module_inits = []
        for m in self.unit.modules:
            module_inits.extend(self.module_init(m))
        main_decls, main_lines = self.top_level(self.unit.main)

        module_file = any(m.exports is not None for m in self.unit.modules)
        out = ["/* Emitted by the Quest IR C printer */", '#include "quest_runtime.h"']
        if self.interface_header:
            out.append(f'#include "{self.interface_header}"')
        out.append("")
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
            linkage = "" if m.exports is not None else "static "
            out.append(f"{linkage}QRecordVal {module_record_ident(clean)};")
            out.append(f"static bool qv_mod_{clean}_initialized = false;")
            if m.exports is not None:
                out.append(f"void qv_mod_{clean}_init(void);")
        out.append("")
        out.extend(self.thunk_decls)
        out.append("")
        # The unit's functions with frames in tracebacks (docs/exceptions.md §5.2)
        funcs = self.func_table_entries()
        if funcs:
            for m in self.unit.modules:
                if m.exports is None:
                    out.append(f"static void qv_mod_{mangle_module_name(m.name)}_init(void);")
            if not module_file:
                out.append("int main(int argc, char **argv);")
            out.append("static const QFuncEntry qr_funcs[] = {")
            out.extend(f"    {{ (const void *)&{c_name}, {c_string_literal(name)} }}," for c_name, name in funcs)
            out.append("};")
            out.append("")
        # The offset tables of the records the unit views at supertypes, registered for dynamic values, and its
        # function table
        out.append("static void qr_register_dicts(void) {")
        if funcs:
            out.append("    quest_register_funcs(qr_funcs, sizeof qr_funcs / sizeof qr_funcs[0]);")
        for view_t, layout_t in self.needed_dicts:
            dict_name = self.ctx.offset_dict_instance_name(view_t, layout_t)
            out.append(f"    quest_register_record_dict({self.descriptor(view_t)}, {self.descriptor(layout_t)}, "
                       f"&{dict_name});")
        out.append("}")
        out.append("")
        out.extend(functions)
        out.extend(self.thunk_defs)
        out.extend(module_inits)
        if module_file:
            return "\n".join(out)
        out.append("int main(int argc, char **argv) {")
        out.append("    quest_gc_init();")
        out.append("    quest_builtins_init(argc, argv);")
        out.append("    qr_register_dicts();")
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

    def func_table_entries(self) -> list[tuple[str, str]]:
        """The C functions of the unit that have frames in tracebacks, and their frame names: its functions with names
        (not those the passes made), its modules' initializers, and a program's main."""
        entries = [(self.code_name(f), f.trace_name) for f in self.unit.functions if f.trace_name is not None]
        entries.extend((f"qv_mod_{mangle_module_name(m.name)}_init", init_frame(m.name)) for m in self.unit.modules)
        if not any(m.exports is not None for m in self.unit.modules):
            entries.append(("main", MAIN_FRAME))
        return entries

    def emit_catches(self, handler: str, catches) -> None:
        """Records in a try's handler what it catches (docs/exceptions.md §5.1)."""
        if catches is ir.CATCH_ALL:
            self.emit(f"{handler}.catches = NULL;")
            self.emit(f"{handler}.n_catches = Q_CATCH_ALL;")
        elif catches is None:
            self.emit(f"{handler}.catches = NULL;")
            self.emit(f"{handler}.n_catches = Q_CATCH_UNKNOWN;")
        else:
            array = self.fresh_name("_qc")
            self.emit(f"const QException *{array}[] = {{ {', '.join(self.atom(a) for a in catches)} }};")
            self.emit(f"{handler}.catches = {array};")
            self.emit(f"{handler}.n_catches = {len(catches)};")

    def module_init(self, m: ir.Module) -> list[str]:
        """A module's initializer, which makes its record. A module file's is extern, as are its record and its
        exported functions, and initializes the modules it imports first, as a program's main does."""
        clean = mangle_module_name(m.name)
        decls, lines = self.top_level(m.init)
        linkage = "" if m.exports is not None else "static "
        out = [f"{linkage}void qv_mod_{clean}_init(void) {{",
               f"    if (qv_mod_{clean}_initialized) return;",
               f"    qv_mod_{clean}_initialized = true;"]
        out.extend(f"    {c_t} {name};" for c_t, name in decls)
        out.extend(self.abstract_type_registrations(m.name))
        if m.exports is not None:
            out.append("    qr_register_dicts();")
            out.extend(f"    qv_mod_{mangle_module_name(imp.canonical_path)}_init();" for imp in self.unit.imports)
        out.extend(lines)
        fields = m.members if m.exports is None else m.exports
        rec_t = QRecordType(tuple(QRecordField(name=n, type_val=v.type) for n, v in fields.items()))
        self.types.append(rec_t)
        struct = record_struct_name(rec_t, self.ctx)
        out.append(f"    {struct} *_payload = ({struct} *)quest_alloc(sizeof({struct}));")
        out.append(f"    _payload->header.descriptor = {self.descriptor(rec_t)};")
        for n, v in sorted(fields.items()):
            if not self.is_ok(v.type):
                out.append(f"    _payload->qf_{n} = {self.name(v)};")
        dict_name = self.ctx.offset_dict_instance_name(rec_t, rec_t)
        out.append(f"    {module_record_ident(clean)} = (QRecordVal){{ .val = (void *)_payload, "
                   f".dict = (const void *)&{dict_name} }};")
        out.append("}")
        out.append("")
        if m.exports is not None:
            out.extend(self.exported_functions(m))
        return out

    def exported_functions(self, m: ir.Module) -> list[str]:
        """A module file's exported functions (`qv_<module>_<member>`, c/declarations.py), one for each of its
        interface's functions and polymorphic values, which call its export's closure."""
        clean = mangle_module_name(m.name)
        out = []
        for name, export in m.exports.items():
            sig = module_function_signature(clean, name, export.type, self.c_type)
            if sig is None:
                continue
            ret_c, ident, param_decls = sig
            quants, params, _ = _signature(export.type)
            args = [f"descriptor_{q.name}" for q in quants] + [f"qv_p_{p.name}" for p in params]
            known = self.closures.get(id(export))
            if known is not None and not known.type_args and not known.captures:
                call = f"{self.code_name(known.code)}({', '.join(['NULL'] + args)})"
            else:
                fn_ptr = closure_fn_ptr_type(export.type, self.ctx)
                self.types.append(export.type)
                clos = self.name(export)
                call = f"(({fn_ptr})({clos}->fn))({', '.join([f'{clos}->env'] + args)})"
            out.append(f"{ret_c} {ident}({', '.join(param_decls) or 'void'}) {{")
            out.append(f"    {call};" if ret_c == "void" else f"    return {call};")
            out.append("}")
            out.append("")
        return out

    def abstract_type_registrations(self, canon: str) -> list[str]:
        """Registers a module's abstract types with their representations, for dynamic values (docs/dynamic.md
        §2.3): an abstract type operator's representation as a template whose holes are its parameters."""
        from quest.modules.abstract_types import module_abstract_types

        lines: list[str] = []
        for entry in module_abstract_types(canon):
            rep = strip_aliases(entry.rep)
            arity = 0
            kind = entry.type_var.bound
            while isinstance(kind, QAllKind):
                arity, kind = arity + 1, kind.result_kind
            if not isinstance(kind, (QTypeKind, QPowerKind)) or (arity and isinstance(kind, QPowerKind)):
                continue
            if arity:
                if not isinstance(rep, QTypeFun) or len(rep.params) != arity:
                    continue
                rep = rep.body.substitute({p.symbol_id: hole_var(i, p.bound) for i, p in enumerate(rep.params)})
            try:
                form = descriptor_form(rep, self.ctx)
            except MissingDescriptorError:
                continue
            self.types.append(rep)
            lines.append(f'    quest_register_abstract_type("{entry.global_name}", {arity}, {form.c_expr});')
        return lines

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
        lines.extend(self.decl_emitter.emit_precompiled_module_declarations(stubs))
        return lines

    def declarations(self) -> list[str]:
        """The declarations of the types the unit uses: structs, offset tables, descriptors, and adapters."""
        for scope in self.module_scopes.values():
            self.types.append(build_record_type_from_scope(scope))
        decl = CDeclarationEmitter(self.ctx, lambda t: qtype_to_c_type(t, self.ctx))
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
            (type_tag(t), type_tag(s)): (t, s)
            for t in variant_types for s in variant_types if s is not t and is_variant_subtype(s, t)
        }
        self.needed_dicts = list(needed.values())
        lines = []
        lines.extend(decl.emit_forward_typedefs(agg_types))
        lines.extend(decl.emit_aggregate_structs(agg_types))
        lines.extend(decl.emit_evidence_dictionaries(agg_types, self.needed_dicts))
        lines.extend(decl.emit_coercion_tables(list(tuple_coercions.values()), list(variant_coercions.values())))
        lines.extend(decl.emit_type_descriptors(agg_types, variant_types, self.descriptor, all_types))
        lines.extend(decl.emit_fun_type_adapters(decl.emitted_fun_types))
        return lines


def print_c(unit: ir.Unit, env: Any, interface_header: Optional[str] = None) -> str:
    """The C translation of a represented unit: a program, or a module file (including its interface's C header,
    if it has one)."""
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
    return CPrinter(unit, env, scopes, interface_header).print_unit()
