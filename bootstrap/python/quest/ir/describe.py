"""Descriptors (docs/ir.md §7, §8.4): the pass after represent that makes run-time types explicit, producing the
described stage.

Every run-time use of a type gets a descriptor operand (ir.Descriptor), made as the uniform quantifier rule says
(docs/c-representation.md §6.4):

- a type parameter in scope is its descriptor variable: a function's type parameters' descriptors are its leading
  parameters (ir.Function.descriptor_params; those its closure supplies are read from its environment), a thunk's
  (an adapter's, or a type application's) its own, and inside an inspect's arms, the auto type's own type parameter
  is the value's type component (ir.Inspect.witness);
- a type that mentions no type parameter in scope is its static descriptor (ir.StaticDescriptor);
- a type that mentions some is its template, a hole for each (codegen/descriptors.py, hole_var), instantiated with
  their descriptors (ir.Instantiate); and the generic layout of a polymorphic callee's type (a `runtime` plan's) is its
  template with a hole for each of the callee's type parameters too, instantiated with the type arguments'
  descriptors.

The uses: type arguments of calls, closures, type applications, and external calls; auto values' witnesses;
inspect cases' types and arms; `is` of QVal words; record literals' types (and views, with runtime offsets); fields
read through stored types; echo; and the plans that convert by descriptor (record_view, view, runtime, and copy's view
fields), including those in the thunks of adapt plans and type applications, which bind descriptor variables of
their own. A thunk is a function of its own, so its plans may use only its own descriptors and static ones: a type
mentioning a type parameter of the enclosing function there is rejected (UnsupportedDescriptor).

The pass also lists the unit's static data (ir.StaticData), which a backend emits: the static descriptors operations
refer to, the static offset tables of record literals (ir.OffsetTable, registered with the runtime for dynamic values
when both types are closed; modules' records among them), and the tag maps of variant_tags plans (ir.TagMap); and
each module's abstract types' registrations (docs/dynamic.md §2.3). An echo of a package with a
prefix, whose line is known statically (its components hidden), becomes an echo of its text.

Descriptor operands are small pure expressions over descriptor variables, not values named by lets: where a backend
evaluates them is its own business (the C printer evaluates each where it is used, as before this pass existed).
"""

from __future__ import annotations

from typing import Any, Optional

from quest.codegen.descriptors import bound_var_index, hole_var
from quest.codegen.layout import own_view, representation, resolved_shape
from quest.ir import nodes as ir
from quest.ir.represent import held_shape
from quest.ir.shapes import shape
from quest.ir.walk import contents, statement_bodies
from quest.ir.written import package_text
from quest.types import (
    QAbstractType,
    QAllKind,
    QPowerKind,
    QRecordField,
    QRecordType,
    QTupleType,
    QType,
    QTypeApp,
    QTypeFun,
    QTypeKind,
    QTypeVar,
    auto_payload_type,
    type_fields,
)
from quest.modules.abstract_types import module_abstract_types


class UnsupportedDescriptor(Exception):
    """A descriptor the pass cannot make: in a thunk, of a type mentioning a type parameter of the enclosing
    function, whose descriptor the thunk is not passed."""


_BASE_VALUE_KINDS = {"int": "Int", "real": "Real", "bool": "Bool", "char": "Char", "string": "String", "ok": "Ok"}


def echo_value_kind(t: QType) -> str:
    """How echo writes a value of type t without a descriptor, as the interpreter does (format_value_with_type):
    "Word", "fun", "hidden", or a base type's name; "" if it writes it by a descriptor of its type."""
    s = shape(t)
    if s.kind == "word":
        return "Word"
    if s.kind in ("fun", "all"):
        return "fun"
    if s.kind == "typevar" or (s.kind == "abstract" and not isinstance(s.structure, QTypeApp)):
        return "hidden"
    return _BASE_VALUE_KINDS.get(s.kind, "")


def free_type_vars(t: QType, wanted) -> list:
    """The type variables (and abstract types) occurring free in t for which wanted(symbol_id) holds, in order of
    appearance."""
    free = t._fv
    if not free or not any(wanted(sid) for sid in free):
        return []
    found: dict[int, Any] = {}
    seen: set[int] = set()

    def visit(node: Any) -> None:
        if id(node) in seen:
            return
        seen.add(id(node))
        if isinstance(node, (QTypeVar, QAbstractType)) and node.symbol_id in free and wanted(node.symbol_id):
            found.setdefault(node.symbol_id, node)
        if isinstance(node, (tuple, list)):
            for item in node:
                visit(item)
        else:
            for part in type_fields(node) or ():
                visit(part)

    visit(t)
    return list(found.values())


_CONSTANT_KINDS = ("int", "real", "bool", "char", "string", "ok", "word")


def _constant(template: QType) -> bool:
    """Whether a template's descriptor is one of the runtime's own, whatever its holes (its shape does not mention
    them): a scalar's, a word's, the empty tuple's, or a bound type parameter's placeholder."""
    s = shape(template)
    if s.kind in _CONSTANT_KINDS or bound_var_index(s.structure) is not None:
        return True
    return isinstance(s.structure, QTupleType) and not s.structure.fields


def _is_function(t: QType) -> bool:
    s = shape(t)
    while s.kind == "all":
        s = s.body
    return s.kind == "fun"


def _type_of(a: ir.Atom) -> QType:
    return a.type if isinstance(a, ir.Var) else a.shape.type


class _Describer:
    def __init__(self, unit: ir.Unit) -> None:
        self.unit = unit
        self.data = ir.StaticData()
        self.static_keys: dict[tuple, ir.StaticDescriptor] = {}
        self.offset_keys: dict[tuple, ir.OffsetTable] = {}
        self.tag_keys: dict[tuple, ir.TagMap] = {}
        # The descriptor variables in scope, by the symbols of the type parameters they describe, and the symbols of
        # type parameters whose descriptors are not available here (an enclosing function's, in a thunk)
        self.scope: dict[int, ir.Var] = {}
        self.unavailable: frozenset[int] = frozenset()
        # The view maps of the function being described, by the symbols of their type parameters
        self.view_maps: dict[int, ir.ViewMapParam] = {}
        # Handlers' exception variables, which `is` compares as exceptions
        self.handler_vars: set[int] = set()

    # Descriptors

    def static(self, t: QType, echo: bool = False) -> ir.StaticDescriptor:
        """The static descriptor of t (a closed type, or a template), listed in the unit's static data."""
        key = (True, id(t)) if echo else (False, id(shape(t)))
        if key not in self.static_keys:
            d = self.static_keys[key] = ir.StaticDescriptor(t, echo)
            self.data.descriptors.append(d)
        return ir.StaticDescriptor(t, echo)

    def check_available(self, t: QType) -> None:
        missing = free_type_vars(t, lambda sid: sid in self.unavailable and sid not in self.scope)
        if missing:
            names = ", ".join(v.name for v in missing)
            raise UnsupportedDescriptor(
                f"C code generation: a thunk converts by the descriptor of '{t}', which mentions the type parameter "
                f"{names} of the function it is made in, whose descriptor it is not passed"
            )

    def describe(self, t: QType) -> ir.Descriptor:
        """The descriptor of t here: a type parameter's variable, a closed type's static descriptor, or the template of
        a type mentioning type parameters in scope (a hole for each), instantiated with their descriptors."""
        var = shape(t).type
        if isinstance(var, (QTypeVar, QAbstractType)) and var.symbol_id in self.scope:
            return self.scope[var.symbol_id]
        if self.unavailable:
            self.check_available(t)
        params = free_type_vars(t, lambda sid: sid in self.scope)
        return self.template(t, params, [self.scope[v.symbol_id] for v in params])

    def template(self, t: QType, holes: list, args: list) -> ir.Descriptor:
        """The descriptor of t with a hole for each of holes (type variables), instantiated with args."""
        if not holes:
            return self.static(t)
        template = t.substitute({v.symbol_id: hole_var(i, v.bound) for i, v in enumerate(holes)})
        if _constant(template):
            return self.static(template)
        self.static(template)
        return ir.Instantiate(template, tuple(args))

    def layout_descriptor(self, t: QType, instantiation: dict[int, QType]) -> ir.Descriptor:
        """The descriptor of a polymorphic callee's type t laid out as the callee lays it out at the call's type
        arguments: its template, a hole for each of the callee's type parameters (and for each in scope),
        instantiated with the type arguments' descriptors (and theirs)."""
        if self.unavailable:
            self.check_available(t)
        params = free_type_vars(t, lambda sid: sid in instantiation)
        in_scope = free_type_vars(t, lambda sid: sid in self.scope and sid not in instantiation)
        args = [self.describe(instantiation[v.symbol_id]) for v in params]
        args.extend(self.scope[v.symbol_id] for v in in_scope)
        return self.template(t, params + in_scope, args)

    def thunk(self, symbols: tuple[tuple[int, ...], ...]):
        """The descriptor parameters of a thunk taking type parameters named by symbols, and enters its scope (a
        context manager, restoring the enclosing scope on exit)."""
        params = tuple(ir.DescriptorParam(ir.Var(f"qd_{k}", ir.DESCRIPTOR_TYPE), syms) for k, syms in enumerate(symbols))
        describer = self

        class _Thunk:
            def __enter__(self_inner):
                self_inner.saved = (describer.scope, describer.unavailable)
                describer.unavailable = describer.unavailable | frozenset(describer.scope)
                describer.scope = {s: p.var for p in params for s in p.symbols}
                return params

            def __exit__(self_inner, *exc):
                describer.scope, describer.unavailable = self_inner.saved
                return False

        return _Thunk()

    # Plans

    def plan(self, p: Optional[ir.Plan]) -> Optional[ir.Plan]:
        """Gives a plan (and the plans in it) the descriptors it converts by, in place."""
        if p is None:
            return None
        match p.kind:
            case "record_view":
                p.descriptors = (self.describe(held_shape(p.target, "record").structure),)
            case "view":
                p.descriptors = (self.describe(p.source), self.describe(p.target))
            case "runtime":
                instantiation, to_generic = p.layout
                generic_t = p.target if to_generic else p.source
                generic_d = self.layout_descriptor(generic_t, instantiation)
                native_d = self.describe(generic_t.substitute(instantiation))
                p.descriptors = (native_d, generic_d) if to_generic else (generic_d, native_d)
            case "variant_tags":
                p.tag_map = self.tag_map(held_shape(p.target, "variant").structure,
                                         held_shape(p.source, "variant").structure)
            case "copy":
                for f in p.fields:
                    self.plan(f)
            case "adapt":
                with self.thunk(p.thunk_symbols) as params:
                    p.thunk_params = params
                    for f in p.fields:
                        self.plan(f)
        return p

    # Static tables

    def tag_map(self, target: QType, source: QType) -> ir.TagMap:
        key = (id(shape(target)), id(shape(source)))
        table = self.tag_keys.get(key)
        if table is None:
            table = self.tag_keys[key] = ir.TagMap(target, source)
            self.data.tag_maps.append(table)
        return table

    def offset_table(self, view: QType, layout: QType, registered: bool) -> ir.OffsetTable:
        key = (id(shape(view)), id(shape(layout)))
        table = self.offset_keys.get(key)
        if table is None:
            table = self.offset_keys[key] = ir.OffsetTable(view, layout)
            self.data.offset_tables.append(table)
        if registered and table.registered is None:
            table.registered = (self.static(view), self.static(layout))
        return table

    # Bodies

    def body(self, body: ir.Body) -> None:
        statements = []
        for s in body.statements:
            statements.append(self.statement(s))
        body.statements = statements

    def statement(self, s):
        match s:
            case ir.Let(var=var, value=value):
                self.operation(value, var)
            case ir.Do(value=value):
                self.operation(value, None)
            case ir.Inspect():
                self.inspect(s)
            case ir.Try(exception=e):
                self.handler_vars.add(id(e))
            case ir.StoreField(base=base) | ir.StoreComponent(base=base):
                s.view_map = self.view_map(base)
            case ir.Switch(value=value):
                s.view_map = self.view_map(value)
            case ir.Echo(value=value, type=t, prefix=prefix):
                text = package_text(t) if prefix else None
                if text is not None:
                    # A package's components are hidden, so its line is known statically (as the interpreter prints
                    # it), from its type as written
                    return ir.EchoText(prefix + text)
                if not echo_value_kind(t):
                    closed = not free_type_vars(t, lambda sid: sid in self.scope)
                    s.descriptor = self.static(t, echo=True) if closed else self.describe(t)
        for b in statement_bodies(s):
            self.body(b)
        return s

    def view_map(self, a: ir.Atom) -> Optional[ir.Var]:
        """The view map a value is read through its type's bound by, if its type is a type parameter in scope bounded by
        a record, variant, option, or tuple type (held at its own view); made for the function on first use."""
        s = shape(_type_of(a))
        held = resolved_shape(s)
        if not own_view(s) or held.kind not in ("record", "variant", "option", "tuple") or s.symbol_id not in self.scope:
            return None
        param = self.view_maps.get(s.symbol_id)
        if param is None:
            name = s.name.replace(".", "_") if s.name else "t"
            param = ir.ViewMapParam(ir.Var(f"view_{name}", ir.VIEW_MAP_TYPE), s.symbol_id, self.scope[s.symbol_id],
                                    self.describe(held.structure))
            self.view_maps[s.symbol_id] = param
        return param.var

    def operation(self, o, result: Optional[ir.Var]) -> None:
        match o:
            case ir.RecordField(record=a) | ir.TupleField(tuple=a) | ir.AddrField(base=a) | ir.AddrComponent(base=a) | \
                    ir.IsTag(value=a) | ir.Payload(value=a) | ir.Ordinal(value=a):
                o.view_map = self.view_map(a)
        match o:
            case ir.Prim(op="is" | "isnot", args=args):
                a = args[0]
                if not (isinstance(a, ir.Var) and id(a) in self.handler_vars):
                    t = _type_of(a)
                    if representation(t) == "QVal":
                        o.descriptor = self.describe(t)
            case ir.Call(type_args=type_args) | ir.CallExternal(type_args=type_args) | \
                    ir.MakeClosure(type_args=type_args):
                o.descriptors = tuple(self.describe(t) for t in type_args)
            case ir.TypeApp(type_args=type_args):
                o.descriptors = tuple(self.describe(t) for t in type_args)
                if o.callee is not None:
                    orig_t = o.callee.type
                elif isinstance(o.module, ir.Module):
                    orig_t = o.module.members[o.member].type
                else:
                    orig_t = o.callee_type
                if _is_function(orig_t):
                    # The instance is a thunk, whose plans convert its arguments and result
                    with self.thunk(o.thunk_symbols) as params:
                        o.thunk_params = params
                        for p in o.plans:
                            self.plan(p)
                else:
                    for p in o.plans:
                        self.plan(p)
            case ir.Convert(plan=plan):
                self.plan(plan)
            case ir.MakeRecord(fields=fields):
                concrete = QRecordType(tuple(
                    QRecordField(name=n, type_val=_type_of(a), is_var=is_var) for n, a, is_var in fields
                ))
                held = held_shape(result.type, "record")
                target = held.structure if held is not None else concrete
                o.descriptor = self.describe(concrete)
                if o.runtime_offsets:
                    o.view_descriptor = self.describe(target)
                else:
                    target_d = self.describe(target)
                    registered = isinstance(o.descriptor, ir.StaticDescriptor) and \
                        isinstance(target_d, ir.StaticDescriptor)
                    o.offsets = self.offset_table(target, concrete, registered)
            case ir.RecordField(record=r, name=name, stored=True):
                rs = held_shape(_type_of(r), "record")
                field = next(c.shape for c in rs.sorted_components() if c.name == name)
                o.descriptor = self.describe(field.type)
            case ir.MakeAuto(witness=witness):
                o.descriptor = self.describe(witness)

    def inspect(self, s: ir.Inspect) -> None:
        auto_t = s.auto_type
        if auto_t is None:
            return
        s.witness = ir.DescriptorParam(ir.Var("witness", ir.DESCRIPTOR_TYPE), (auto_t.symbol_id,))
        stored_t = auto_payload_type(auto_t)
        for case in s.cases:
            case.descriptor = self.describe(case.match_type)
            arm = case.arm
            if not case.binders or arm is None:
                continue
            arm_t = auto_payload_type(auto_t, case.match_type)
            saved = self.scope
            self.scope = {**self.scope, auto_t.symbol_id: s.witness.var}
            try:
                descriptors = []
                for how, stored_f, arm_f in zip(arm.converted, stored_t.value_fields, arm_t.value_fields):
                    if how is None:
                        descriptors.append(None)
                    elif how == "component":
                        to = self.describe(arm_f.type_val)
                        descriptors.append((s.witness.var, to))
                    else:
                        descriptors.append((self.describe(stored_f.type_val), self.describe(arm_f.type_val)))
                arm.descriptors = tuple(descriptors)
                self.plan(arm.plan)
            finally:
                self.scope = saved

    # Functions and modules

    def function(self, f: ir.Function) -> None:
        f.descriptor_params = tuple(
            ir.DescriptorParam(ir.Var(f"descriptor_{tp.name}", ir.DESCRIPTOR_TYPE), (tp.symbol_id,))
            for tp in f.type_params
        )
        self.scope = {p.symbols[0]: p.var for p in f.descriptor_params}
        self.view_maps = {}
        self.body(f.body)
        f.view_maps = tuple(self.view_maps.values())
        self.view_maps = {}
        self.scope = {}

    def module(self, m: ir.Module) -> None:
        self.body(m.init)
        m.abstract_types = self.abstract_types(m.name)

    def abstract_types(self, canon: str) -> tuple[tuple[str, int, ir.StaticDescriptor], ...]:
        """A module's abstract types, each registered with its representation (an operator's as a template whose
        holes are its parameters), for dynamic values (docs/dynamic.md §2.3)."""
        found = []
        for entry in module_abstract_types(canon):
            rep = shape(entry.rep).type
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
            found.append((entry.global_name, arity, self.static(rep)))
        return tuple(found)

    def run(self) -> None:
        for m in self.unit.modules:
            self.module(m)
        self.body(self.unit.main)
        for f in self.unit.functions:
            self.function(f)
        self.data.types = unit_types(self.unit)
        self.unit.static_data = self.data


def unit_types(unit: ir.Unit) -> list[QType]:
    """The types a unit's C declares the aggregates of (ir.StaticData.types), in the order first met: those of its
    variables and functions' results, of the operations' and plans' types (and those plans convert inside), of the
    records its literals make (their own types, from their fields') and the payloads its inspect arms make, of its
    imports' interfaces, and of its offset tables."""
    found: list[QType] = []
    seen_types: set[int] = set()
    seen_nodes: set[int] = set()

    def add(t) -> None:
        if t is not None and id(t) not in seen_types:
            seen_types.add(id(t))
            found.append(t)

    def visit(node) -> None:
        match node:
            case QType():
                add(node)
                return
            case list() | tuple():
                for item in node:
                    visit(item)
                return
            case dict():
                for item in node.values():
                    visit(item)
                return
        # An IR node's fields, or a kind's (a type parameter's), whose types are declared too; nothing else (a shape,
        # a name) holds types
        parts = contents(node)
        if parts is None:
            parts = type_fields(node)
        if parts is None or id(node) in seen_nodes:
            return
        seen_nodes.add(id(node))
        if isinstance(node, ir.MakeRecord):
            add(QRecordType(tuple(QRecordField(name=n, type_val=_type_of(a), is_var=v) for n, a, v in node.fields)))
        elif isinstance(node, ir.Inspect) and node.auto_type is not None:
            for case in node.cases:
                if case.binders:
                    add(auto_payload_type(node.auto_type, case.match_type))
        for part in parts:
            visit(part)

    visit(unit.modules)
    visit(unit.main)
    visit(unit.functions)
    visit(unit.imports)
    for table in unit.static_data.offset_tables if unit.static_data is not None else ():
        add(table.view)
        add(table.layout)
    return found


# The fields of IR nodes whose types C declares no aggregates for: descriptor operands (described by the static data's
# descriptors, which declare what they need) and the static data itself
def describe_unit(unit: ir.Unit) -> ir.Unit:
    """Gives the unit's run-time uses of types their descriptors, in place, returning it."""
    _Describer(unit).run()
    unit.stage = "described"
    return unit
