"""The represent pass's last step (docs/ir.md §8.3): how values are stored into and read from aggregates' slots, and
how tuples and options that may be proxies are read.

Slots (docs/ir.md §4.2). Every slot of an aggregate holds a record or variant boxed (slot_representation in
codegen/layout.py), as does the location a var or out parameter points to. The step makes the boxes explicit:

- an operation that reads a record or variant from a slot (a tuple's component, a record's field, an array's element,
  a location, a module's member, a QVal word unboxed, and a record being made, which is made in its box) binds a
  boxed variable, the box, and a `slot_unbox` conversion binds the value from it; the value's box is remembered (and
  a copy's is its original's), so that storing the value into another slot, or boxing it into a QVal word, reuses the
  box (boxes are immutable) rather than allocating another;
- an operation that stores a record or variant into a slot (a tuple, record, option, or array being made, a store, a
  fresh cell, an assignment of a boxed mutable variable) takes its box: the one remembered, or a new one (a
  `slot_box` conversion); a tuple or record being made boxes the others in its own allocation instead (`embedded`);
- a mutable variable of a record or variant type whose address is taken, and a var or out parameter of one, are
  boxed: they hold their locations' boxes, so that a var or out parameter can point to them as to a slot.

Proxies (docs/c-representation.md §5.8). A tuple or option whose type may be proxied (may_be_proxied) may be a view
of an object of a subtype. Each read of a component (and each write of a tuple's var component, and each address of
one) is DIRECT when the value cannot be a proxy (its type cannot be, or the function made it itself, for a tuple's
component read), ORIGINAL when it may be but the component cannot change view (read from the original's slot), and
PROXY otherwise (checked, and read through the proxy, converted); `is` compares originals (ORIGINAL).

The step also decides how a record's field is read (through the offset table's stored types, when a subtype's payload
may store it at another type) and whether a record literal's offset table is known statically.
"""

from __future__ import annotations

from typing import Optional

from quest.codegen.layout import (
    changes_view,
    is_boxed_in_slots,
    is_record_subtype,
    may_be_proxied,
    resolved_shape,
    shape_representation,
)
from quest.ir import nodes as ir
from quest.ir.shapes import Shape, shape
from quest.ir.walk import statement_bodies, walk_statements
from quest.types import QRecordField, QRecordType, QType, is_type_equal


def _type_of(a: ir.Atom) -> QType:
    return a.type if isinstance(a, ir.Var) else a.shape.type


def _held(t: QType, kind: str) -> Optional[Shape]:
    held = resolved_shape(shape(t))
    return held if held.kind == kind else None


def _tag_shape(t: QType) -> Optional[Shape]:
    return _held(t, "variant") or _held(t, "option")


def _boxed(s: Optional[Shape]) -> bool:
    return s is not None and is_boxed_in_slots(s)


def tuple_access(ts: Shape, index: int, fresh: bool = False) -> str:
    """How component index of a tuple of shape ts is read (or written): DIRECT if the tuple cannot be a proxy (its type
    cannot be, or it is fresh, made by the function reading it), ORIGINAL if the component cannot change view, PROXY
    otherwise."""
    if fresh or not may_be_proxied(ts):
        return ir.DIRECT
    return ir.PROXY if changes_view(ts.components[index].shape) else ir.ORIGINAL


def option_tag_access(os: Shape) -> str:
    """How the tag of an option of shape os is read: through a proxy (PROXY) if it may be one, else DIRECT."""
    return ir.PROXY if may_be_proxied(os) else ir.DIRECT


def option_component_accesses(os: Shape, tag: Optional[str]) -> tuple[str, ...]:
    """How the payload components of case tag of an option of shape os are read: one for each component of a tuple
    payload, or one for a payload that is not a tuple."""
    case = os.case(tag) if tag is not None else None
    if case is None or case.shape is None:
        return ()
    comps = [c.shape for c in case.shape.components] if case.shape.kind == "tuple" else [case.shape]
    if not may_be_proxied(os):
        return tuple(ir.DIRECT for _ in comps)
    return tuple(ir.PROXY if changes_view(c) else ir.ORIGINAL for c in comps)


def _located_shape(address: ir.Atom) -> Shape:
    """The shape of the values at an address (of a var or out location)."""
    s = shape(_type_of(address))
    return s.element if s.kind in ("cell", "out") else s


def _option_case_tag(os: Shape, o: ir.MakeOption) -> Optional[str]:
    """The case whose layout an option being made stores its payload in: its tag's, or for a computed ordinal, a
    constant one's, else the first case's (whose components the union overlays on the others')."""
    if o.ordinal is None:
        return o.tag
    n = o.ordinal.value if isinstance(o.ordinal, ir.Const) else 0
    return os.cases[n].name if 0 <= n < len(os.cases) else os.cases[0].name


class _Slots:
    def __init__(self) -> None:
        # The boxes of the records and variants read from slots (by the variable bound to the value)
        self.boxes: dict[int, ir.Var] = {}
        # The tuples and options the function made (by variable), which are not proxies
        self.fresh: set[int] = set()

    def top_level(self, body: ir.Body) -> None:
        """Decides a function's (or a top level's) slots and reads."""
        self.boxes = {}
        self.fresh = set()
        self.body(body)

    def is_fresh(self, a: ir.Atom) -> bool:
        return isinstance(a, ir.Var) and id(a) in self.fresh

    def slot(self, a: ir.Atom, before: list) -> ir.Atom:
        """A record or variant atom in its slot form: its box (remembered, or a new one, made by a let added to
        before)."""
        if isinstance(a, ir.Var) and a.boxed and not a.mutable:
            return a
        if isinstance(a, ir.Var) and id(a) in self.boxes:
            return self.boxes[id(a)]
        t = _type_of(a)
        box = ir.Var("box", t, boxed=True)
        before.append(ir.Let(box, ir.Convert(a, ir.Plan("slot_box", t, t))))
        return box

    def slot_if_boxed(self, a: ir.Atom, s: Optional[Shape], before: list) -> ir.Atom:
        return self.slot(a, before) if _boxed(s) else a

    def body(self, body: ir.Body) -> None:
        statements: list = []
        for s in body.statements:
            for b in statement_bodies(s):
                self.body(b)
            statements.extend(self.statement(s))
        body.statements = statements

    def statement(self, s) -> list:
        before: list = []
        match s:
            case ir.Let():
                return self.let(s)
            case ir.Do(value=value):
                self.operation(value, None, before)
            case ir.VarDecl(var=var, init=init) if var.boxed and init is not None:
                s.init = self.slot(init, before)
            case ir.Assign(var=var, value=value) if var.boxed:
                s.value = self.slot(value, before)
            case ir.Store(address=address) if address is not None:
                s.value = self.slot_if_boxed(s.value, _located_shape(address), before)
            case ir.Store(base=base, name=name) if name is not None:
                rs = _held(_type_of(base), "record")
                field = next((f.shape for f in rs.sorted_components() if f.name == name), None) if rs else None
                s.value = self.slot_if_boxed(s.value, field, before)
            case ir.Store(base=base, index=index) if isinstance(index, int):
                ts = shape(_type_of(base))
                s.value = self.slot_if_boxed(s.value, ts.components[index].shape, before)
                # A store is never into a fresh tuple's view
                s.access = tuple_access(ts, index)
            case ir.Store(base=base):
                s.value = self.slot_if_boxed(s.value, shape(_type_of(base)).element, before)
            case ir.Switch(value=value, cases=cases):
                ts = _tag_shape(_type_of(value))
                if ts is not None and ts.kind == "option":
                    s.access = option_tag_access(ts)
                    for c in cases:
                        self.option_case(ts, c)
        return before + [s]

    def option_case(self, os: Shape, c: ir.Case) -> None:
        """A switch's case of an option, whose binder takes the payload: a tuple of its components, read as decided, or
        a payload that is not a tuple in its slot form (a boxed variable, from which the value is read)."""
        b = c.binder
        if b is None or shape(b.type).kind == "ok":
            return
        c.components = option_component_accesses(os, c.tags[0])
        if shape(b.type).kind == "tuple":
            return
        case = os.case(c.tags[0])
        payload_s = case.shape if case is not None and case.shape is not None else shape(b.type)
        if _boxed(payload_s):
            box = ir.Var(f"{b.hint}_box" if b.hint else "box", b.type, boxed=True)
            c.binder = box
            c.body.statements.insert(0, ir.Let(b, ir.Convert(box, ir.Plan("slot_unbox", b.type, b.type))))
            self.boxes[id(b)] = box

    def let(self, s: ir.Let) -> list:
        var, value = s.var, s.value
        if isinstance(value, (ir.MakeTuple, ir.MakeOption)) or (isinstance(value, ir.Var) and id(value) in self.fresh):
            self.fresh.add(id(var))
        if isinstance(value, ir.Var):
            if id(value) in self.boxes:
                self.boxes[id(var)] = self.boxes[id(value)]
            return [s]
        if isinstance(value, ir.Const):
            return [s]
        before: list = []
        if not self.operation(value, var, before):
            return before + [s]
        # The operation reads the value in its slot form, a box: bound to a boxed variable, from which the value is read
        box = ir.Var(f"{var.hint}_box" if var.hint else "box", var.type, boxed=True)
        s.var = box
        self.boxes[id(var)] = box
        return before + [s, ir.Let(var, ir.Convert(box, ir.Plan("slot_unbox", var.type, var.type)))]

    def operation(self, o, var: Optional[ir.Var], before: list) -> bool:
        """Decides how an operation reads and stores slots, converting the atoms it stores to their slot forms (by lets
        added to before); returns whether it yields a record or variant in its slot form, which the let binding it
        then binds to a boxed variable."""
        match o:
            case ir.TupleField(tuple=t, index=index):
                ts = shape(_type_of(t))
                o.access = tuple_access(ts, index, self.is_fresh(t))
                return _boxed(ts.components[index].shape)
            case ir.RecordField(record=r, name=name):
                rs = _held(_type_of(r), "record")
                if rs is None:
                    return False
                fields = rs.sorted_components()
                field = next(f for f in fields if f.name == name)
                if not field.is_var and (shape_representation(field.shape) == "QVal" or _may_be_stored_as_subtype(field.shape)):
                    # A subtype's payload may store it at another type: read by the offset table's stored types and
                    # converted, as a value
                    o.stored = True
                    return False
                return _boxed(field.shape)
            case ir.Index(array=a):
                return _boxed(shape(_type_of(a)).element)
            case ir.Load(address=a):
                return _boxed(_located_shape(a))
            case ir.ModuleMember(module=ir.Import(), member=member) if member is not None:
                return var is not None and _boxed(shape(var.type))
            case ir.Convert(value=v, plan=p):
                if p.kind == "unbox" and _boxed(shape(p.target)):
                    # A QVal word holds a record or variant as its box
                    return True
                if p.kind == "box" and isinstance(v, ir.Var) and id(v) in self.boxes:
                    # A record's or variant's QVal word is its box: the one it was read from serves
                    o.value = self.boxes[id(v)]
                return False
            case ir.MakeRecord(fields=fields):
                new_fields = []
                embedded = []
                for i, (name, a, is_var) in enumerate(fields):
                    s = shape(_type_of(a))
                    if s.kind != "ok" and _boxed(s):
                        if isinstance(a, ir.Var) and (a.boxed and not a.mutable or id(a) in self.boxes):
                            a = self.slot(a, before)
                        else:
                            embedded.append(i)
                    new_fields.append((name, a, is_var))
                o.fields = tuple(new_fields)
                o.embedded = tuple(embedded)
                o.runtime_offsets = _runtime_offsets(o, var)
                return var is not None
            case ir.MakeTuple(args=args):
                components = shape(var.type).components if var is not None else ()
                new_args = []
                embedded = []
                for i, a in enumerate(args):
                    if i < len(components) and _boxed(components[i].shape):
                        if isinstance(a, ir.Var) and (a.boxed and not a.mutable or id(a) in self.boxes):
                            a = self.slot(a, before)
                        else:
                            embedded.append(i)
                    new_args.append(a)
                o.args = tuple(new_args)
                o.embedded = tuple(embedded)
            case ir.MakeOption(payload=payload) if var is not None:
                os = _held(var.type, "option")
                tag = _option_case_tag(os, o) if os is not None else None
                if payload is not None and tag is not None:
                    case = os.case(tag)
                    pt = case.shape if case is not None else None
                    if pt is not None and pt.kind == "tuple":
                        ps = shape(_type_of(payload))
                        fresh = self.is_fresh(payload)
                        o.access = tuple(tuple_access(ps, i, fresh) for i in range(len(pt.components)))
                    else:
                        o.payload = self.slot_if_boxed(payload, pt, before)
            case ir.IsTag(value=v) | ir.Ordinal(value=v):
                ts = _tag_shape(_type_of(v))
                if ts is not None and ts.kind == "option":
                    o.access = option_tag_access(ts)
            case ir.Payload(value=v, tag=tag):
                ts = _tag_shape(_type_of(v))
                if ts is not None and ts.kind == "option":
                    o.access = option_tag_access(ts)
                    o.components = option_component_accesses(ts, tag)
            case ir.MakeArray(args=args) if var is not None:
                elem = shape(var.type).element
                o.args = tuple(self.slot_if_boxed(a, elem, before) for a in args)
            case ir.ArrayRep(init=init) if var is not None:
                o.init = self.slot_if_boxed(init, shape(var.type).element, before)
            case ir.Addr(cell=cell) if cell is not None:
                o.cell = self.slot_if_boxed(cell, shape(_type_of(cell)), before)
            case ir.Addr(base=base, index=index) if isinstance(index, int):
                o.access = tuple_access(shape(_type_of(base)), index)
            case ir.Prim(op="is" | "isnot", args=(a, b)):
                t, t2 = _type_of(a), _type_of(b)
                if shape_representation(shape(t)) != "QVal" and (may_be_proxied(shape(t)) or may_be_proxied(shape(t2))):
                    # A proxy is the object it views
                    o.access = ir.ORIGINAL
        return False


def _may_be_stored_as_subtype(s: Shape) -> bool:
    from quest.ir.represent import may_be_stored_as_subtype

    return may_be_stored_as_subtype(s)


def _runtime_offsets(o: ir.MakeRecord, var: Optional[ir.Var]) -> bool:
    """Whether the offset table of a record literal's view (the let's type, or a bounded type parameter's bound) is
    found at run time: when the view is not the literal's type or a supertype of it by width alone."""
    if var is None:
        return False
    concrete = QRecordType(tuple(QRecordField(name=n, type_val=_type_of(a), is_var=v) for n, a, v in o.fields))
    held = _held(var.type, "record")
    target = held.structure if held is not None else concrete
    return not (is_type_equal(target, concrete) or is_record_subtype(concrete, target))


def decide_slots(unit: ir.Unit) -> None:
    """Decides, in place, how the unit's values are stored into and read from slots, and read through proxies."""
    bodies = [m.init for m in unit.modules] + [unit.main] + [f.body for f in unit.functions]
    # The mutable variables of record or variant types whose addresses are taken are held boxed, as are var and out
    # parameters of those types (pointers to locations holding them boxed)
    for body in bodies:
        for s in walk_statements(body, into_functions=False):
            if isinstance(s, ir.Let) and isinstance(s.value, ir.Addr) and s.value.var is not None:
                v = s.value.var
                if _boxed(shape(v.type)):
                    v.boxed = True
    for f in unit.functions:
        for v, mode in f.params:
            if mode != "value" and _boxed(shape(v.type)):
                v.boxed = True
    slots = _Slots()
    for body in bodies:
        slots.top_level(body)
