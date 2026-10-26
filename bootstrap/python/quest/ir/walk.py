"""Traversals of the IR shared by the passes and the verifier: the bodies a statement contains, the variables it
binds, the atoms it uses, and the global variables of a unit; and the IR's explicit traversal, which every walker of
nodes' fields uses (fields_of and rebuild, contents, replace_vars, view_map_of), with a case for each class of node."""

from __future__ import annotations

from typing import Any, Callable, Iterator, Optional

from quest.ir import nodes as ir


def statement_bodies(s) -> list[ir.Body]:
    """The bodies a statement contains (not those of the functions a funs statement binds)."""
    match s:
        case ir.If(then_body=t, else_body=e):
            return [t, e]
        case ir.Switch(cases=cases, else_body=e) | ir.Inspect(cases=cases, else_body=e):
            return [c.body for c in cases] + ([e] if e is not None else [])
        case ir.Loop(body=b) | ir.LetRec(body=b):
            return [b]
        case ir.Try(body=b, handler=h):
            return [b, h]
        case ir.Join(continuation=c, body=b):
            return [c, b]
    return []


def statement_binders(s) -> list[ir.Var]:
    """The variables a statement binds itself (not those bound in the bodies it contains)."""
    match s:
        case ir.Let(var=v) | ir.VarDecl(var=v):
            return [v]
        case ir.Funs(functions=functions):
            return [f.var for f in functions]
        case ir.LetRec(vars=vars_):
            return list(vars_)
        case ir.Switch(cases=cases):
            return [c.binder for c in cases if c.binder is not None]
        case ir.Inspect(cases=cases):
            return [b for c in cases for b in c.binders]
        case ir.Try(exception=e):
            return [e]
        case ir.Join(params=params):
            return list(params)
    return []


def _atoms_of(node) -> Iterator[ir.Atom]:
    """The atoms an operation or a statement uses directly (not in the bodies or functions it contains)."""
    if isinstance(node, (ir.Var, ir.Const)):
        yield node
        return
    for v in contents(node):
        if isinstance(v, (ir.Var, ir.Const)):
            yield v
        elif isinstance(v, tuple):
            for item in v:
                if isinstance(item, (ir.Var, ir.Const)):
                    yield item
                elif isinstance(item, tuple):
                    # Record fields: (name, atom, is_var)
                    yield from (part for part in item if isinstance(part, (ir.Var, ir.Const)))


def statement_uses(s) -> list[ir.Atom]:
    """The atoms a statement uses directly: its operation's, or its own (a condition, a value, a jump's arguments);
    not those of the bodies or functions it contains, nor its binders."""
    match s:
        case ir.Let(value=value) | ir.Do(value=value):
            return list(_atoms_of(value))
        case ir.VarDecl(init=init):
            return [init] if init is not None else []
        case ir.Assign(var=var, value=value):
            return [var, value]
        case ir.StoreAt() | ir.StoreField() | ir.StoreComponent() | ir.StoreElement():
            return list(_atoms_of(s))
        case ir.If(cond=a) | ir.Switch(value=a) | ir.Inspect(value=a) | ir.Echo(value=a) | ir.Return(value=a):
            return [a]
        case ir.Jump(args=args):
            return list(args)
        case ir.Raise(exception=e, payload=p):
            return [e] if p is None else [e, p]
        case ir.Reraise(exception=e):
            return [e]
        case ir.Try(catches=catches):
            return list(catches)
    return []


def walk_statements(body: ir.Body, into_functions: bool = True) -> Iterator:
    """Every statement in body and the bodies it contains (and in the functions funs statements bind, unless
    into_functions is false), in order."""
    for s in body.statements:
        yield s
        if into_functions and isinstance(s, ir.Funs):
            for f in s.functions:
                yield from walk_statements(f.body, into_functions)
        for b in statement_bodies(s):
            yield from walk_statements(b, into_functions)


def global_variables(unit: ir.Unit) -> set[int]:
    """The variables (by identity) a unit's main body and its modules' initializers bind outside loops and functions:
    each is bound at most once in a run, and is a global, which functions use rather than capture."""
    found: set[int] = set()

    def visit(body: ir.Body) -> None:
        for s in body.statements:
            found.update(id(v) for v in statement_binders(s))
            if not isinstance(s, ir.Loop):
                for b in statement_bodies(s):
                    visit(b)

    for m in unit.modules:
        visit(m.init)
    visit(unit.main)
    return found


# The explicit traversal: a case for each class of node

def fields_of(node) -> Optional[tuple]:
    """The values of an IR node's fields, in order; None for a value that is not an IR node."""
    accessor = _FIELDS_OF.get(type(node))
    return accessor(node) if accessor is not None else None


def contents(node) -> Optional[tuple]:
    """The values of an IR node's fields, in order, but for its descriptor operands (ir.DESCRIPTOR_FIELDS) and the
    describe pass's other results (an inspect's witness, a unit's static data): what the program computes, as the
    passes before describe make it; None for a value that is not an IR node."""
    accessor = _CONTENTS.get(type(node))
    return accessor(node) if accessor is not None else None


def rebuild(node, values: tuple):
    """A new IR node of node's class whose fields are values (as fields_of gives them)."""
    return _REBUILD[type(node)](node, values)


def _replaced(value, f):
    """value with each variable v in it (it, or in the tuples it is) replaced by f(v)."""
    if isinstance(value, ir.Var):
        return f(value)
    if isinstance(value, tuple):
        items = tuple(_replaced(item, f) for item in value)
        return value if all(a is b for a, b in zip(items, value)) else items
    return value


def replace_vars(node, f) -> None:
    """Replaces, in place, each variable v that a statement or operation holds in its fields (directly or in
    tuples; and in a let's or do's operation) by f(v); not those in the bodies, functions, cases, or plans it
    contains, nor a closure's code."""
    match node:
        case ir.Prim():
            node.args = _replaced(node.args, f)
            node.descriptor = _replaced(node.descriptor, f)
        case ir.Call():
            node.callee = _replaced(node.callee, f)
            node.args = _replaced(node.args, f)
            node.descriptors = _replaced(node.descriptors, f)
        case ir.TypeApp():
            node.callee = _replaced(node.callee, f)
            node.descriptors = _replaced(node.descriptors, f)
            node.thunk_params = _replaced(node.thunk_params, f)
        case ir.CallExternal():
            node.args = _replaced(node.args, f)
            node.descriptors = _replaced(node.descriptors, f)
        case ir.MakeClosure():
            node.captures = _replaced(node.captures, f)
            node.descriptors = _replaced(node.descriptors, f)
        case ir.EnvField():
            node.env = _replaced(node.env, f)
        case ir.Convert():
            node.value = _replaced(node.value, f)
        case ir.MakeTuple():
            node.args = _replaced(node.args, f)
        case ir.TupleField():
            node.tuple = _replaced(node.tuple, f)
            node.view_map = _replaced(node.view_map, f)
        case ir.MakeRecord():
            node.fields = _replaced(node.fields, f)
            node.descriptor = _replaced(node.descriptor, f)
            node.view_descriptor = _replaced(node.view_descriptor, f)
        case ir.RecordField():
            node.record = _replaced(node.record, f)
            node.descriptor = _replaced(node.descriptor, f)
            node.view_map = _replaced(node.view_map, f)
        case ir.MakeVariant():
            node.payload = _replaced(node.payload, f)
        case ir.MakeOption():
            node.payload = _replaced(node.payload, f)
            node.ordinal = _replaced(node.ordinal, f)
        case ir.IsTag():
            node.value = _replaced(node.value, f)
            node.view_map = _replaced(node.view_map, f)
        case ir.Payload():
            node.value = _replaced(node.value, f)
            node.view_map = _replaced(node.view_map, f)
        case ir.Ordinal():
            node.value = _replaced(node.value, f)
            node.view_map = _replaced(node.view_map, f)
        case ir.MakeArray():
            node.args = _replaced(node.args, f)
        case ir.ArrayRep():
            node.count = _replaced(node.count, f)
            node.init = _replaced(node.init, f)
        case ir.Index():
            node.array = _replaced(node.array, f)
            node.index = _replaced(node.index, f)
        case ir.MakeAuto():
            node.payload = _replaced(node.payload, f)
            node.descriptor = _replaced(node.descriptor, f)
        case ir.ExceptionPayload():
            node.exception = _replaced(node.exception, f)
        case ir.AddrVar():
            node.var = _replaced(node.var, f)
        case ir.AddrCell():
            node.init = _replaced(node.init, f)
        case ir.AddrField():
            node.base = _replaced(node.base, f)
            node.view_map = _replaced(node.view_map, f)
        case ir.AddrComponent():
            node.base = _replaced(node.base, f)
            node.view_map = _replaced(node.view_map, f)
        case ir.AddrElement():
            node.base = _replaced(node.base, f)
            node.index = _replaced(node.index, f)
        case ir.Load():
            node.address = _replaced(node.address, f)
        case ir.Let():
            node.var = _replaced(node.var, f)
            if isinstance(node.value, (ir.Var, ir.Const)):
                node.value = _replaced(node.value, f)
            else:
                replace_vars(node.value, f)
        case ir.VarDecl():
            node.var = _replaced(node.var, f)
            node.init = _replaced(node.init, f)
        case ir.Assign():
            node.var = _replaced(node.var, f)
            node.value = _replaced(node.value, f)
        case ir.StoreAt():
            node.value = _replaced(node.value, f)
            node.address = _replaced(node.address, f)
        case ir.StoreField():
            node.value = _replaced(node.value, f)
            node.base = _replaced(node.base, f)
            node.view_map = _replaced(node.view_map, f)
        case ir.StoreComponent():
            node.value = _replaced(node.value, f)
            node.base = _replaced(node.base, f)
            node.view_map = _replaced(node.view_map, f)
        case ir.StoreElement():
            node.value = _replaced(node.value, f)
            node.base = _replaced(node.base, f)
            node.index = _replaced(node.index, f)
        case ir.Do():
            if isinstance(node.value, (ir.Var, ir.Const)):
                node.value = _replaced(node.value, f)
            else:
                replace_vars(node.value, f)
        case ir.LetRec():
            node.vars = _replaced(node.vars, f)
        case ir.If():
            node.cond = _replaced(node.cond, f)
        case ir.Switch():
            node.value = _replaced(node.value, f)
            node.view_map = _replaced(node.view_map, f)
        case ir.Inspect():
            node.value = _replaced(node.value, f)
            node.witness = _replaced(node.witness, f)
        case ir.Try():
            node.exception = _replaced(node.exception, f)
            node.catches = _replaced(node.catches, f)
        case ir.Join():
            node.params = _replaced(node.params, f)
        case ir.Echo():
            node.value = _replaced(node.value, f)
            node.descriptor = _replaced(node.descriptor, f)
        case ir.Return():
            node.value = _replaced(node.value, f)
        case ir.Jump():
            node.args = _replaced(node.args, f)
        case ir.Raise():
            node.exception = _replaced(node.exception, f)
            node.payload = _replaced(node.payload, f)
        case ir.Reraise():
            node.exception = _replaced(node.exception, f)


def view_map_of(node) -> Optional[ir.Var]:
    """The view map an operation or a statement reads a value through its type's bound by (after the describe pass),
    if it has one."""
    match node:
        case ir.TupleField() | ir.RecordField() | ir.IsTag() | ir.Payload() | ir.Ordinal() | ir.AddrField() | \
                ir.AddrComponent() | ir.StoreField() | ir.StoreComponent() | ir.Switch():
            return node.view_map
    return None


# The entries of the traversal, a case for each class

_FIELDS_OF: dict[type, Callable[[Any], tuple]] = {
    ir.Var: lambda node: (node.hint, node.type, node.mutable, node.boxed),
    ir.Const: lambda node: (node.value, node.shape),
    ir.StaticDescriptor: lambda node: (node.type, node.echo),
    ir.Instantiate: lambda node: (node.template, node.args),
    ir.DescriptorParam: lambda node: (node.var, node.symbols),
    ir.ViewMapParam: lambda node: (node.var, node.symbol, node.descriptor, node.bound),
    ir.OffsetTable: lambda node: (node.view, node.layout, node.registered),
    ir.TagMap: lambda node: (node.target, node.source),
    ir.StaticData: lambda node: (node.descriptors, node.offset_tables, node.tag_maps, node.types),
    ir.TypeParam: lambda node: (node.name, node.symbol_id, node.kind, node.bound),
    ir.Prim: lambda node: (node.op, node.args, node.offset, node.access, node.descriptor),
    ir.Call: lambda node: (
        node.callee, node.type_args, node.args, node.module, node.member, node.callee_type, node.descriptors,
    ),
    ir.TypeApp: lambda node: (
        node.callee, node.type_args, node.module, node.member, node.callee_type, node.plans, node.thunk_symbols,
        node.descriptors, node.thunk_params,
    ),
    ir.ModuleMember: lambda node: (node.module, node.member),
    ir.Builtin: lambda node: (node.name,),
    ir.External: lambda node: (node.symbol,),
    ir.CallExternal: lambda node: (node.symbol, node.type_args, node.args, node.descriptors),
    ir.MakeClosure: lambda node: (node.code, node.captures, node.type_args, node.descriptors),
    ir.EnvField: lambda node: (node.env, node.index),
    ir.Plan: lambda node: (
        node.kind, node.source, node.target, node.fields, node.layout, node.access, node.thunk_symbols,
        node.descriptors, node.thunk_params, node.tag_map,
    ),
    ir.Convert: lambda node: (node.value, node.plan),
    ir.MakeTuple: lambda node: (node.args, node.type_components, node.embedded),
    ir.TupleField: lambda node: (node.tuple, node.index, node.access, node.view_map),
    ir.MakeRecord: lambda node: (
        node.fields, node.embedded, node.runtime_offsets, node.descriptor, node.offsets, node.view_descriptor,
    ),
    ir.RecordField: lambda node: (node.record, node.name, node.stored, node.descriptor, node.view_map),
    ir.MakeVariant: lambda node: (node.tag, node.payload),
    ir.MakeOption: lambda node: (node.tag, node.payload, node.ordinal, node.offset, node.cases, node.access),
    ir.IsTag: lambda node: (node.value, node.tag, node.access, node.view_map),
    ir.Payload: lambda node: (
        node.value, node.tag, node.offset, node.access, node.components, node.ordinal, node.view_map,
    ),
    ir.Ordinal: lambda node: (node.value, node.cases, node.access, node.view_map),
    ir.MakeArray: lambda node: (node.args,),
    ir.ArrayRep: lambda node: (node.count, node.init, node.offset),
    ir.Index: lambda node: (node.array, node.index, node.offset),
    ir.MakeAuto: lambda node: (node.witness, node.auto_type, node.payload, node.descriptor),
    ir.MakeException: lambda node: (node.name, node.payload_type),
    ir.ExceptionPayload: lambda node: (node.exception,),
    ir.AddrVar: lambda node: (node.var,),
    ir.AddrCell: lambda node: (node.init,),
    ir.AddrField: lambda node: (node.base, node.name, node.view_map),
    ir.AddrComponent: lambda node: (node.base, node.index, node.access, node.view_map),
    ir.AddrElement: lambda node: (node.base, node.index, node.offset),
    ir.Load: lambda node: (node.address,),
    ir.Let: lambda node: (node.var, node.value),
    ir.VarDecl: lambda node: (node.var, node.init),
    ir.Assign: lambda node: (node.var, node.value),
    ir.StoreAt: lambda node: (node.value, node.address),
    ir.StoreField: lambda node: (node.value, node.base, node.name, node.view_map),
    ir.StoreComponent: lambda node: (node.value, node.base, node.index, node.access, node.view_map),
    ir.StoreElement: lambda node: (node.value, node.base, node.index, node.offset),
    ir.Do: lambda node: (node.value,),
    ir.Function: lambda node: (
        node.var, node.type_params, node.params, node.result_type, node.body, node.env, node.trace_name,
        node.descriptor_params, node.view_maps,
    ),
    ir.Funs: lambda node: (node.functions, node.recursive),
    ir.LetRec: lambda node: (node.vars, node.body),
    ir.If: lambda node: (node.cond, node.then_body, node.else_body),
    ir.Case: lambda node: (node.tags, node.body, node.binder, node.components),
    ir.Switch: lambda node: (node.value, node.cases, node.else_body, node.access, node.view_map),
    ir.InspectCase: lambda node: (node.match_type, node.binders, node.body, node.exact, node.arm, node.descriptor),
    ir.InspectArm: lambda node: (
        node.converted, node.exact, node.shared, node.plan, node.layout_error, node.descriptors,
    ),
    ir.Inspect: lambda node: (node.value, node.cases, node.else_body, node.auto_type, node.offset, node.witness),
    ir.Loop: lambda node: (node.label, node.body),
    ir.Try: lambda node: (node.body, node.exception, node.handler, node.catching, node.catches),
    ir.Join: lambda node: (node.label, node.params, node.continuation, node.body),
    ir.Echo: lambda node: (node.value, node.type, node.prefix, node.descriptor),
    ir.EchoText: lambda node: (node.text,),
    ir.Return: lambda node: (node.value,),
    ir.Jump: lambda node: (node.label, node.args),
    ir.Break: lambda node: (node.label,),
    ir.Continue: lambda node: (node.label,),
    ir.Raise: lambda node: (node.exception, node.payload, node.offset),
    ir.Reraise: lambda node: (node.exception,),
    ir.Unreachable: lambda node: (),
    ir.Body: lambda node: (node.statements,),
    ir.Module: lambda node: (
        node.name, node.interface_name, node.init, node.members, node.exports, node.record, node.abstract_types,
    ),
    ir.Import: lambda node: (node.name, node.module_path, node.canonical_path, node.interface_path, node.record_type),
    ir.Unit: lambda node: (
        node.main, node.modules, node.imports, node.functions, node.stage, node.source_map, node.static_data,
    ),
}

_CONTENTS: dict[type, Callable[[Any], tuple]] = {
    ir.Var: lambda node: (node.hint, node.type, node.mutable, node.boxed),
    ir.Const: lambda node: (node.value, node.shape),
    ir.StaticDescriptor: lambda node: (node.type, node.echo),
    ir.Instantiate: lambda node: (node.template, node.args),
    ir.DescriptorParam: lambda node: (node.var, node.symbols),
    ir.ViewMapParam: lambda node: (node.var, node.symbol, node.bound),
    ir.OffsetTable: lambda node: (node.view, node.layout, node.registered),
    ir.TagMap: lambda node: (node.target, node.source),
    ir.StaticData: lambda node: (node.offset_tables, node.tag_maps, node.types),
    ir.TypeParam: lambda node: (node.name, node.symbol_id, node.kind, node.bound),
    ir.Prim: lambda node: (node.op, node.args, node.offset, node.access),
    ir.Call: lambda node: (node.callee, node.type_args, node.args, node.module, node.member, node.callee_type),
    ir.TypeApp: lambda node: (
        node.callee, node.type_args, node.module, node.member, node.callee_type, node.plans, node.thunk_symbols,
    ),
    ir.ModuleMember: lambda node: (node.module, node.member),
    ir.Builtin: lambda node: (node.name,),
    ir.External: lambda node: (node.symbol,),
    ir.CallExternal: lambda node: (node.symbol, node.type_args, node.args),
    ir.MakeClosure: lambda node: (node.code, node.captures, node.type_args),
    ir.EnvField: lambda node: (node.env, node.index),
    ir.Plan: lambda node: (
        node.kind, node.source, node.target, node.fields, node.layout, node.access, node.thunk_symbols,
    ),
    ir.Convert: lambda node: (node.value, node.plan),
    ir.MakeTuple: lambda node: (node.args, node.type_components, node.embedded),
    ir.TupleField: lambda node: (node.tuple, node.index, node.access),
    ir.MakeRecord: lambda node: (node.fields, node.embedded, node.runtime_offsets),
    ir.RecordField: lambda node: (node.record, node.name, node.stored),
    ir.MakeVariant: lambda node: (node.tag, node.payload),
    ir.MakeOption: lambda node: (node.tag, node.payload, node.ordinal, node.offset, node.cases, node.access),
    ir.IsTag: lambda node: (node.value, node.tag, node.access),
    ir.Payload: lambda node: (node.value, node.tag, node.offset, node.access, node.components, node.ordinal),
    ir.Ordinal: lambda node: (node.value, node.cases, node.access),
    ir.MakeArray: lambda node: (node.args,),
    ir.ArrayRep: lambda node: (node.count, node.init, node.offset),
    ir.Index: lambda node: (node.array, node.index, node.offset),
    ir.MakeAuto: lambda node: (node.auto_type, node.payload),
    ir.MakeException: lambda node: (node.name, node.payload_type),
    ir.ExceptionPayload: lambda node: (node.exception,),
    ir.AddrVar: lambda node: (node.var,),
    ir.AddrCell: lambda node: (node.init,),
    ir.AddrField: lambda node: (node.base, node.name),
    ir.AddrComponent: lambda node: (node.base, node.index, node.access),
    ir.AddrElement: lambda node: (node.base, node.index, node.offset),
    ir.Load: lambda node: (node.address,),
    ir.Let: lambda node: (node.var, node.value),
    ir.VarDecl: lambda node: (node.var, node.init),
    ir.Assign: lambda node: (node.var, node.value),
    ir.StoreAt: lambda node: (node.value, node.address),
    ir.StoreField: lambda node: (node.value, node.base, node.name),
    ir.StoreComponent: lambda node: (node.value, node.base, node.index, node.access),
    ir.StoreElement: lambda node: (node.value, node.base, node.index, node.offset),
    ir.Do: lambda node: (node.value,),
    ir.Function: lambda node: (
        node.var, node.type_params, node.params, node.result_type, node.body, node.env, node.trace_name,
        node.descriptor_params, node.view_maps,
    ),
    ir.Funs: lambda node: (node.functions, node.recursive),
    ir.LetRec: lambda node: (node.vars, node.body),
    ir.If: lambda node: (node.cond, node.then_body, node.else_body),
    ir.Case: lambda node: (node.tags, node.body, node.binder, node.components),
    ir.Switch: lambda node: (node.value, node.cases, node.else_body, node.access),
    ir.InspectCase: lambda node: (node.match_type, node.binders, node.body, node.exact, node.arm),
    ir.InspectArm: lambda node: (node.converted, node.exact, node.shared, node.plan, node.layout_error),
    ir.Inspect: lambda node: (node.value, node.cases, node.else_body, node.auto_type, node.offset),
    ir.Loop: lambda node: (node.label, node.body),
    ir.Try: lambda node: (node.body, node.exception, node.handler, node.catching, node.catches),
    ir.Join: lambda node: (node.label, node.params, node.continuation, node.body),
    ir.Echo: lambda node: (node.value, node.type, node.prefix),
    ir.EchoText: lambda node: (node.text,),
    ir.Return: lambda node: (node.value,),
    ir.Jump: lambda node: (node.label, node.args),
    ir.Break: lambda node: (node.label,),
    ir.Continue: lambda node: (node.label,),
    ir.Raise: lambda node: (node.exception, node.payload, node.offset),
    ir.Reraise: lambda node: (node.exception,),
    ir.Unreachable: lambda node: (),
    ir.Body: lambda node: (node.statements,),
    ir.Module: lambda node: (
        node.name, node.interface_name, node.init, node.members, node.exports, node.record, node.abstract_types,
    ),
    ir.Import: lambda node: (node.name, node.module_path, node.canonical_path, node.interface_path, node.record_type),
    ir.Unit: lambda node: (node.main, node.modules, node.imports, node.functions, node.stage, node.source_map),
}

_REBUILD: dict[type, Callable[[Any, tuple], Any]] = {
    ir.Var: lambda node, values: ir.Var(hint=values[0], type=values[1], mutable=values[2], boxed=values[3]),
    ir.Const: lambda node, values: ir.Const(value=values[0], shape=values[1]),
    ir.StaticDescriptor: lambda node, values: ir.StaticDescriptor(type=values[0], echo=values[1]),
    ir.Instantiate: lambda node, values: ir.Instantiate(template=values[0], args=values[1]),
    ir.DescriptorParam: lambda node, values: ir.DescriptorParam(var=values[0], symbols=values[1]),
    ir.ViewMapParam: lambda node, values: ir.ViewMapParam(
        var=values[0], symbol=values[1], descriptor=values[2], bound=values[3],
    ),
    ir.OffsetTable: lambda node, values: ir.OffsetTable(view=values[0], layout=values[1], registered=values[2]),
    ir.TagMap: lambda node, values: ir.TagMap(target=values[0], source=values[1]),
    ir.StaticData: lambda node, values: ir.StaticData(
        descriptors=values[0], offset_tables=values[1], tag_maps=values[2], types=values[3],
    ),
    ir.TypeParam: lambda node, values: ir.TypeParam(
        name=values[0], symbol_id=values[1], kind=values[2], bound=values[3],
    ),
    ir.Prim: lambda node, values: ir.Prim(
        op=values[0], args=values[1], offset=values[2], access=values[3], descriptor=values[4],
    ),
    ir.Call: lambda node, values: ir.Call(
        callee=values[0], type_args=values[1], args=values[2], module=values[3], member=values[4],
        callee_type=values[5], descriptors=values[6],
    ),
    ir.TypeApp: lambda node, values: ir.TypeApp(
        callee=values[0], type_args=values[1], module=values[2], member=values[3], callee_type=values[4],
        plans=values[5], thunk_symbols=values[6], descriptors=values[7], thunk_params=values[8],
    ),
    ir.ModuleMember: lambda node, values: ir.ModuleMember(module=values[0], member=values[1]),
    ir.Builtin: lambda node, values: ir.Builtin(name=values[0]),
    ir.External: lambda node, values: ir.External(symbol=values[0]),
    ir.CallExternal: lambda node, values: ir.CallExternal(
        symbol=values[0], type_args=values[1], args=values[2], descriptors=values[3],
    ),
    ir.MakeClosure: lambda node, values: ir.MakeClosure(
        code=values[0], captures=values[1], type_args=values[2], descriptors=values[3],
    ),
    ir.EnvField: lambda node, values: ir.EnvField(env=values[0], index=values[1]),
    ir.Plan: lambda node, values: ir.Plan(
        kind=values[0], source=values[1], target=values[2], fields=values[3], layout=values[4], access=values[5],
        thunk_symbols=values[6], descriptors=values[7], thunk_params=values[8], tag_map=values[9],
    ),
    ir.Convert: lambda node, values: ir.Convert(value=values[0], plan=values[1]),
    ir.MakeTuple: lambda node, values: ir.MakeTuple(args=values[0], type_components=values[1], embedded=values[2]),
    ir.TupleField: lambda node, values: ir.TupleField(
        tuple=values[0], index=values[1], access=values[2], view_map=values[3],
    ),
    ir.MakeRecord: lambda node, values: ir.MakeRecord(
        fields=values[0], embedded=values[1], runtime_offsets=values[2], descriptor=values[3], offsets=values[4],
        view_descriptor=values[5],
    ),
    ir.RecordField: lambda node, values: ir.RecordField(
        record=values[0], name=values[1], stored=values[2], descriptor=values[3], view_map=values[4],
    ),
    ir.MakeVariant: lambda node, values: ir.MakeVariant(tag=values[0], payload=values[1]),
    ir.MakeOption: lambda node, values: ir.MakeOption(
        tag=values[0], payload=values[1], ordinal=values[2], offset=values[3], cases=values[4], access=values[5],
    ),
    ir.IsTag: lambda node, values: ir.IsTag(value=values[0], tag=values[1], access=values[2], view_map=values[3]),
    ir.Payload: lambda node, values: ir.Payload(
        value=values[0], tag=values[1], offset=values[2], access=values[3], components=values[4], ordinal=values[5],
        view_map=values[6],
    ),
    ir.Ordinal: lambda node, values: ir.Ordinal(value=values[0], cases=values[1], access=values[2], view_map=values[3]),
    ir.MakeArray: lambda node, values: ir.MakeArray(args=values[0]),
    ir.ArrayRep: lambda node, values: ir.ArrayRep(count=values[0], init=values[1], offset=values[2]),
    ir.Index: lambda node, values: ir.Index(array=values[0], index=values[1], offset=values[2]),
    ir.MakeAuto: lambda node, values: ir.MakeAuto(
        witness=values[0], auto_type=values[1], payload=values[2], descriptor=values[3],
    ),
    ir.MakeException: lambda node, values: ir.MakeException(name=values[0], payload_type=values[1]),
    ir.ExceptionPayload: lambda node, values: ir.ExceptionPayload(exception=values[0]),
    ir.AddrVar: lambda node, values: ir.AddrVar(var=values[0]),
    ir.AddrCell: lambda node, values: ir.AddrCell(init=values[0]),
    ir.AddrField: lambda node, values: ir.AddrField(base=values[0], name=values[1], view_map=values[2]),
    ir.AddrComponent: lambda node, values: ir.AddrComponent(
        base=values[0], index=values[1], access=values[2], view_map=values[3],
    ),
    ir.AddrElement: lambda node, values: ir.AddrElement(base=values[0], index=values[1], offset=values[2]),
    ir.Load: lambda node, values: ir.Load(address=values[0]),
    ir.Let: lambda node, values: ir.Let(var=values[0], value=values[1]),
    ir.VarDecl: lambda node, values: ir.VarDecl(var=values[0], init=values[1]),
    ir.Assign: lambda node, values: ir.Assign(var=values[0], value=values[1]),
    ir.StoreAt: lambda node, values: ir.StoreAt(value=values[0], address=values[1]),
    ir.StoreField: lambda node, values: ir.StoreField(
        value=values[0], base=values[1], name=values[2], view_map=values[3],
    ),
    ir.StoreComponent: lambda node, values: ir.StoreComponent(
        value=values[0], base=values[1], index=values[2], access=values[3], view_map=values[4],
    ),
    ir.StoreElement: lambda node, values: ir.StoreElement(
        value=values[0], base=values[1], index=values[2], offset=values[3],
    ),
    ir.Do: lambda node, values: ir.Do(value=values[0]),
    ir.Function: lambda node, values: ir.Function(
        var=values[0], type_params=values[1], params=values[2], result_type=values[3], body=values[4], env=values[5],
        trace_name=values[6], descriptor_params=values[7], view_maps=values[8],
    ),
    ir.Funs: lambda node, values: ir.Funs(functions=values[0], recursive=values[1]),
    ir.LetRec: lambda node, values: ir.LetRec(vars=values[0], body=values[1]),
    ir.If: lambda node, values: ir.If(cond=values[0], then_body=values[1], else_body=values[2]),
    ir.Case: lambda node, values: ir.Case(tags=values[0], body=values[1], binder=values[2], components=values[3]),
    ir.Switch: lambda node, values: ir.Switch(
        value=values[0], cases=values[1], else_body=values[2], access=values[3], view_map=values[4],
    ),
    ir.InspectCase: lambda node, values: ir.InspectCase(
        match_type=values[0], binders=values[1], body=values[2], exact=values[3], arm=values[4], descriptor=values[5],
    ),
    ir.InspectArm: lambda node, values: ir.InspectArm(
        converted=values[0], exact=values[1], shared=values[2], plan=values[3], layout_error=values[4],
        descriptors=values[5],
    ),
    ir.Inspect: lambda node, values: ir.Inspect(
        value=values[0], cases=values[1], else_body=values[2], auto_type=values[3], offset=values[4], witness=values[5],
    ),
    ir.Loop: lambda node, values: ir.Loop(label=values[0], body=values[1]),
    ir.Try: lambda node, values: ir.Try(
        body=values[0], exception=values[1], handler=values[2], catching=values[3], catches=values[4],
    ),
    ir.Join: lambda node, values: ir.Join(label=values[0], params=values[1], continuation=values[2], body=values[3]),
    ir.Echo: lambda node, values: ir.Echo(value=values[0], type=values[1], prefix=values[2], descriptor=values[3]),
    ir.EchoText: lambda node, values: ir.EchoText(text=values[0]),
    ir.Return: lambda node, values: ir.Return(value=values[0]),
    ir.Jump: lambda node, values: ir.Jump(label=values[0], args=values[1]),
    ir.Break: lambda node, values: ir.Break(label=values[0]),
    ir.Continue: lambda node, values: ir.Continue(label=values[0]),
    ir.Raise: lambda node, values: ir.Raise(exception=values[0], payload=values[1], offset=values[2]),
    ir.Reraise: lambda node, values: ir.Reraise(exception=values[0]),
    ir.Unreachable: lambda node, values: ir.Unreachable(),
    ir.Body: lambda node, values: ir.Body(statements=values[0]),
    ir.Module: lambda node, values: ir.Module(
        name=values[0], interface_name=values[1], init=values[2], members=values[3], exports=values[4],
        record=values[5], abstract_types=values[6],
    ),
    ir.Import: lambda node, values: ir.Import(
        name=values[0], module_path=values[1], canonical_path=values[2], interface_path=values[3],
        record_type=values[4],
    ),
    ir.Unit: lambda node, values: ir.Unit(
        main=values[0], modules=values[1], imports=values[2], functions=values[3], stage=values[4],
        source_map=values[5], static_data=values[6],
    ),
}
