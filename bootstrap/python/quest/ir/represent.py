"""Representation (docs/ir.md §8.3): inserts `convert` wherever a value's
representation differs from the one its use requires.

A value's representation is its type's (codegen/layout.py: the runtime's, shared
by every backend): an unbounded type parameter's values are held as QVal words,
a bounded one's at their own view (their type argument's) in the bound's
representation, and other types natively (a module's abstract type's viewed at
its bound). A use requires the representation of the type it expects: a call's
argument, its callee's parameter type (in a polymorphic callee, mentioning the
callee's type parameters, so a QVal where the parameter is one); a call's
result, its callee's result type; a component of a tuple, record, variant,
option, or array being made or stored into, the component's type; a component
read, as its aggregate's type gives it; a let's copy, a return, a jump's
argument, and an assignment, the type of what they bind or assign. Where the two
differ, the value is converted by the plan of the pair (`plan`).

The plans box and unbox between QVal and native values, view records at
supertypes, remap variants' tags, cast aggregates whose layouts agree
(unwrapping a proxy where the target cannot be one), view tuples and options
whose components change view through proxies of the originals
(docs/c-representation.md §5.8), copy auto payloads into their stored layouts,
adapt closures, and convert by descriptor at run time; any other change of
representation is reported as unsupported, rather than printed wrong. The pass
also decides what the C printer would otherwise: how inspect cases get their
components (ir.InspectArm), the thunks' plans of type applications, and, in its
last step (ir/slots.py), boxing at slots and reads through proxies.

Every decision is made on shapes (ir/shapes.py). The variables the pass makes
have types as written, with their alias names, which the IR prints (docs/ir.md
§5), found through ir/written.py: the types of the components of a type as
written (written_structure), and the signatures of function types as written,
whose type parameters' symbols are those the call's type arguments and the
callee's parts refer to (a shape's are its canonical form's, named afresh).
"""

from __future__ import annotations


from typing import Any, Optional

from quest.codegen.layout import (
    generic_layout_agrees,
    held_at_bound,
    own_view,
    is_boxed_in_slots,
    generic_layout_copies_mutable_data,
    may_be_proxied,
    resolved_shape,
    shape_representation,
    shape_slot_representation,
    signature_representation,
)
from quest.ir import nodes as ir
from quest.ir.shapes import Shape, shape
from quest.ir.slots import decide_slots, may_be_stored_as_subtype, tuple_access
from quest.ir.walk import statement_bodies
from quest.ir.written import array_element as written_element, fun_signature, quantified, written_structure
from quest.types import (
    auto_payload_type,
    is_kind_equal,
    is_type_equal,
    QAbstractType,
    QFunType,
    QOutType,
    QType,
    QTypeVar,
    QVarType,
    type_fields,
)


class UnsupportedConversion(Exception):
    """A change of representation the represent pass does not handle."""


# The kinds of shapes whose values change view at a supertype: a module's
# abstract type bounded by one is held viewed at its bound
_VIEWED_KINDS = ("record", "variant", "option")


def held_shape(t: QType, kind: str) -> Optional[Shape]:
    """The shape of t's values as they are held, if it is of the kind ("record",
    "variant", or "option"): t's own, or for a type parameter bounded by a type
    of the kind, its bound's (in whose representation they are held, at their
    own view, read through the bound by a view map; a module's abstract type's
    viewed at it)."""
    held = resolved_shape(shape(t))
    return held if held.kind == kind else None


def array_element(t: QType) -> QType:
    """The element type, as written, of an array type."""
    element = written_element(t)
    if element is None:
        raise UnsupportedConversion(f"an array operation on a value of type {t}")
    return element


def _bounded_view(s: Shape) -> bool:
    """Whether s is a module's abstract type's (or an abstract or path type's)
    bounded by a record, variant, or option type, held viewed at its bound."""
    return held_at_bound(s) and resolved_shape(s).kind in _VIEWED_KINDS


def _own_viewed(s: Shape) -> bool:
    """Whether s is a type parameter's bounded by a record, variant, option, or
    tuple type, whose values are held at their own view, so that they change
    view when used at another type."""
    return own_view(s) and resolved_shape(s).kind in _VIEWED_KINDS + ("tuple",)


def _equal(a: QType, b: QType) -> bool:
    return a is b or is_type_equal(a, b)


# The type variables in each type met, by the type's identity (types are
# hash-consed and long-lived)
_TYPE_VARS: dict[int, tuple[Any, frozenset]] = {}


def _type_vars(t: Any) -> frozenset:
    """The type variables (as objects, which carry their bounds) in type t, or
    in a component of one."""
    cached = _TYPE_VARS.get(id(t))
    if cached is not None and cached[0] is t:
        return cached[1]
    found: frozenset = frozenset()
    if isinstance(t, QTypeVar):
        found = frozenset((t,))
    elif isinstance(t, tuple):
        found = frozenset().union(*(_type_vars(item) for item in t))
    elif (parts := type_fields(t)) is not None and t._fv:
        found = frozenset().union(*(_type_vars(part) for part in parts))
    if len(_TYPE_VARS) > 200_000:
        _TYPE_VARS.clear()
    _TYPE_VARS[id(t)] = (t, found)
    return found


def _same_views(a: QType, b: QType) -> bool:
    """Whether two equal types hold their type parameters at the same views: a
    type parameter renamed with another bound (shared_signatures) is the same
    type, but held viewed at another bound."""
    if not (a._fv and b._fv):
        return True
    bounds: dict[int, Any] = {}
    for var in _type_vars(a) | _type_vars(b):
        first = bounds.setdefault(var.symbol_id, var.bound)
        if first is not var.bound and not is_kind_equal(first, var.bound):
            return False
    return True


def _variant_subtype(s: Shape, t: Shape) -> bool:
    """Whether every case of the variant shape s is a case of t, with an equal
    payload."""
    payloads = {c.name: c.shape for c in t.cases}
    for c in s.cases:
        if c.name not in payloads:
            return False
        other = payloads[c.name]
        if c.shape is not other and (c.shape is None or other is None or not is_type_equal(c.shape.type, other.type)):
            return False
    return True


class RejectedConversion(Exception):
    """A conversion that would copy mutable data laid out differently, which
    would then not share its updates: a compile-time error
    (docs/c-representation.md §5.1, Polymorphic Calls)."""


def layout_plan(source: QType, target: QType, layout: tuple[dict[int, QType], bool]) -> Optional[ir.Plan]:
    """How a value passed to or returned from a polymorphic callee converts
    between the callee's generic layout of its type and the native layout at the
    call's type arguments (layout: the instantiation, and whether the value goes
    to the generic layout, target being the callee's type, or comes from it,
    source being)."""
    instantiation, to_generic = layout
    generic_t = target if to_generic else source
    native_t = generic_t.substitute(instantiation)
    generic_s, native_s = shape(generic_t), shape(native_t)
    generic_c, native_c = shape_representation(generic_s), shape_representation(native_s)
    if generic_s.kind in ("fun", "all"):
        return None
    is_record = generic_c == native_c == "QRecordVal"
    if not is_record and (not generic_c.endswith("*") or not native_c.endswith("*")):
        return None
    if generic_layout_agrees(generic_t, instantiation):
        return None if generic_c == native_c else ir.Plan("cast", source, target)
    if generic_layout_copies_mutable_data(generic_t, instantiation):
        raise RejectedConversion(
            f"C code generation cannot pass a value of type '{native_t}' to or from a polymorphic function that lays "
            f"it out as '{generic_t}': the layouts differ, and converting the value would copy mutable data, which "
            f"would then not share its updates"
        )
    return ir.Plan("runtime", source, target, layout=layout)


def shared_signatures(source: QType, target: QType) -> tuple[tuple, QType, tuple, QType]:
    """Two (possibly polymorphic) function types' parameters and results as
    written, target's type parameters renamed to source's, so that they can be
    compared. A renamed parameter keeps target's bound where it is stronger than
    source's ([TIncl Π], types/subtyping.py); both hold its values at their own
    view."""
    s_quants, s_inner = quantified(source)
    t_quants, t_inner = quantified(target)
    if s_quants and len(s_quants) == len(t_quants):
        renamed = {
            tq.symbol_id: QTypeVar(name=sq.name, symbol_id=sq.symbol_id, bound=sq.bound)
            for sq, tq in zip(s_quants, t_quants)
        }
        subst: dict[int, QType] = {}
        for sq, tq in zip(s_quants, t_quants):
            bound = tq.bound.substitute_types(renamed)
            if is_kind_equal(bound, sq.bound):
                bound = sq.bound
            subst[tq.symbol_id] = QTypeVar(name=sq.name, symbol_id=sq.symbol_id, bound=bound)
        t_inner = t_inner.substitute(subst)
    s_params = s_inner.params if isinstance(s_inner, QFunType) else ()
    t_params = t_inner.params if isinstance(t_inner, QFunType) else ()
    s_result = s_inner.result_type if isinstance(s_inner, QFunType) else s_inner
    t_result = t_inner.result_type if isinstance(t_inner, QFunType) else t_inner
    return tuple(s_params), s_result, tuple(t_params), t_result


_ADAPTING: set[tuple] = set()


def adapt_plan(source: QType, target: QType, layout) -> Optional[ir.Plan]:
    """How a closure of type source is used at type target: as it is, when the C
    signatures agree and no argument or result converts, or else wrapped in a
    thunk of target's signature (`adapt`), which converts each argument from
    target's parameter type to source's (the other way from the closure) and the
    result from source's to target's, by the plans in `fields` (the parameters',
    then the result's)."""
    if _equal(source, target) and not (layout is not None and layout[0]):
        return None
    # Recursive function types are compared coinductively: a pair being compared
    # needs no conversion of its own
    key = (id(shape(source)), id(shape(target)), layout is not None and layout[1])
    if key in _ADAPTING:
        return None
    s_params, s_result, t_params, t_result = shared_signatures(source, target)
    if len(s_params) != len(t_params):
        raise UnsupportedConversion(f"converting a function of type {source} to {target}")
    flipped = (layout[0], not layout[1]) if layout is not None else None
    _ADAPTING.add(key)
    try:
        fields = tuple(
            None if tp.is_var or tp.is_out else plan(tp.type_val, sp.type_val, flipped)
            for sp, tp in zip(s_params, t_params)
        ) + (plan(s_result, t_result, layout),)
    finally:
        _ADAPTING.discard(key)
    if all(p is None for p in fields) and signature_representation(source) == signature_representation(target):
        return None
    # The thunk takes target's type parameters, which the fields' types name by
    # source's symbols (shared_signatures) or target's own
    s_quants, _ = quantified(source)
    t_quants, _ = quantified(target)
    thunk_symbols = tuple(
        (tq.symbol_id,) + ((s_quants[k].symbol_id,) if k < len(s_quants) else ()) for k, tq in enumerate(t_quants)
    )
    return ir.Plan("adapt", source, target, fields, layout, thunk_symbols=thunk_symbols)


# The pairs of shapes being planned (with their layouts), for recursive types,
# which are compared coinductively
_PLANNING: set[tuple] = set()


def plan(source: QType, target: QType, layout: Optional[tuple[dict[int, QType], bool]] = None) -> Optional[ir.Plan]:
    """How a value of type source is converted to be used at type target (None
    when it is used as it is). layout is set for a value passed to or returned
    from a polymorphic callee (see layout_plan)."""
    if source is target:
        return None
    key = (id(shape(source)), id(shape(target)), None if layout is None else (id(layout[0]), layout[1]))
    if key in _PLANNING:
        # A pair being planned (a recursive type's component): needs no
        # conversion of its own
        return None
    _PLANNING.add(key)
    try:
        return _unproxied(_plan(source, target, layout))
    finally:
        _PLANNING.discard(key)


def _unproxied(p: Optional[ir.Plan]) -> Optional[ir.Plan]:
    """p, or for a cast from a tuple or option type that may be proxied to one
    that may not, an `unproxy` plan: a value of the target type is never a
    proxy, and its components do not change view, so the original serves."""
    if p is None or p.kind != "cast":
        return p
    source_s, target_s = shape(p.source), shape(p.target)
    if target_s.kind in ("tuple", "option") and may_be_proxied(source_s) and not may_be_proxied(target_s):
        return ir.Plan("unproxy", p.source, p.target)
    return p


def _plan(source: QType, target: QType, layout: Optional[tuple[dict[int, QType], bool]]) -> Optional[ir.Plan]:
    ss, ts = shape(source), shape(target)
    if ss.kind == "ok" or ts.kind == "ok":
        return None
    cs, ct = shape_representation(ss), shape_representation(ts)
    if cs != "QVal" and ct != "QVal" and ss.kind in ("fun", "all") and ts.kind in ("fun", "all"):
        return adapt_plan(source, target, layout)
    if layout is not None and layout[0] and cs != "QVal" and ct != "QVal":
        lp = layout_plan(source, target, layout)
        # A module's abstract type's value is held viewed at its bound, whatever
        # the layouts: a record or variant of another type converts to the
        # bound's view (and back), as below
        if lp is not None or not (_bounded_view(ss) or _bounded_view(ts)):
            return lp
    # A value of a type parameter, held as a QVal word: a scalar or pointer in
    # its bits, a record or variant boxed
    if ct == "QVal" and cs != "QVal":
        return ir.Plan("box", source, target)
    if cs == "QVal" and ct != "QVal":
        return ir.Plan("unbox", source, target)
    if cs == "QVal" or (_equal(source, target) and _same_views(source, target)):
        return None
    if own_view(ss) and own_view(ts) and ss.symbol_id == ts.symbol_id:
        # One type parameter, at whatever bounds (a function used where its
        # parameter's bound is stronger): its values are held at their own view
        # either way
        return None
    if _own_viewed(ss) or _own_viewed(ts):
        # A bounded type parameter's value is held at its own view, its type
        # argument's: used at another type, it is converted by the runtime
        # between the two types' descriptors (a record viewed at the other, a
        # variant's tags remapped, a tuple or option through a proxy)
        return ir.Plan("view", source, target)
    s_held, t_held = resolved_shape(ss), resolved_shape(ts)
    if s_held.kind == t_held.kind == "record":
        return None if _equal(s_held.type, t_held.type) else ir.Plan("record_view", source, target)
    if s_held.kind == t_held.kind == "variant":
        index = {case.name: i for i, case in enumerate(t_held.cases)}
        if all(index.get(case.name) == i for i, case in enumerate(s_held.cases)):
            if not _variant_payloads_change(s_held, t_held):
                return None
            # A payload changes view (a record's view, a tuple or option that
            # may be a proxy where the supertype's cannot be): converted by the
            # runtime, which converts the payload (a variant is a value, so
            # nothing is shared)
            return ir.Plan("view", s_held.structure, t_held.structure)
        if _variant_subtype(s_held, t_held):
            return ir.Plan("variant_tags", source, target)
        # From a bounded type parameter's view at its bound back to the type the
        # caller holds it at: by the runtime, between the two views' descriptors
        # (no static tag map relates them)
        return ir.Plan("view", s_held.structure, t_held.structure)
    if s_held.kind == t_held.kind == "option" and not _equal(s_held.type, t_held.type):
        if not (_bounded_view(ss) or _bounded_view(ts)) and _option_cases_agree(s_held, t_held):
            return None if cs == ct else ir.Plan("cast", source, target)
        # Viewed at a bounded type parameter's bound, or an option of a subtype
        # whose cases are numbered differently or whose payloads change view: a
        # proxy (made by the runtime, between the two views' descriptors)
        return ir.Plan("view", s_held.structure, t_held.structure)
    if ss.kind == ts.kind == "tuple":
        if len(ss.components) < len(ts.components):
            raise UnsupportedConversion(f"converting a tuple of type {source} to {target}")
        pairs = list(zip(ss.components, ts.components))
        fields = tuple(plan(sc.shape.type, tc.shape.type) for sc, tc in pairs)
        # A box or unbox changes no slot: a slot holds a value's QVal form
        changing = [p for p in fields if p is not None and p.kind not in ("box", "unbox")]
        if not changing:
            return None if cs == ct else ir.Plan("cast", source, target)
        # Components change view: a proxy of the tuple, which converts them as
        # they are read (a closure by an adapter, made once per proxy)
        return ir.Plan("view", source, target)
    if cs == ct and ts.kind not in ("fun", "all", "option", "array"):
        return None
    if ss.kind == ts.kind == "array" and cs == ct:
        # An array is shared and assigned through, so its elements cannot change
        # view: it serves as it is when they need no conversion either way (as
        # for a module's abstract type and its definition), or only a box or
        # unbox, which changes no element (an element holds a value's QVal form)
        both_ways = (plan(ss.element.type, ts.element.type), plan(ts.element.type, ss.element.type))
        if all(p is None or p.kind in ("box", "unbox") for p in both_ways):
            return None
    raise UnsupportedConversion(f"converting a value of type {source} ({cs}) to {target} ({ct})")


def _variant_payloads_change(s: Shape, t: Shape) -> bool:
    """Whether a payload of a variant of shape s changes representation as one
    of t's (a supertype's with the same case indices): a payload is a QVal word,
    so boxing changes nothing."""
    payloads = {c.name: c.shape for c in t.cases}
    for c in s.cases:
        other = payloads.get(c.name)
        if c.shape is None or other is None:
            continue
        p = plan(c.shape.type, other.type)
        if p is not None and p.kind not in ("box", "unbox"):
            return True
    return False


def _option_cases_agree(s: Shape, t: Shape) -> bool:
    """Whether an option of shape s is laid out as one of shape t (a supertype):
    each of its cases has the same index in t, with a payload that converts by a
    cast at most (not an unproxy: a payload component that may be a proxy, used
    where its type cannot be one, must be converted, through a proxy of the
    option)."""
    for i, case in enumerate(s.cases):
        if i >= len(t.cases) or t.cases[i].name != case.name:
            return False
        tc = t.cases[i]
        if (case.shape is None) != (tc.shape is None):
            return False
        if case.shape is not None:
            p = plan(case.shape.type, tc.shape.type)
            if p is not None and p.kind != "cast":
                return False
    return True


def is_type_variable(t: QType, symbol_id: int) -> bool:
    """Whether t is the type variable (or abstract type) of the symbol."""
    var = shape(t).type
    return isinstance(var, (QTypeVar, QAbstractType)) and var.symbol_id == symbol_id


def _slots_agree(source: Shape, target: Shape) -> bool:
    """Whether a slot of shape source holds its value as a slot of shape target
    does: the same slot representation, or a QVal word (a value's QVal form,
    which every slot holds)."""
    s_c, t_c = shape_slot_representation(source), shape_slot_representation(target)
    return s_c == t_c or (t_c == "QVal" and s_c != "void")


def auto_payload_plan(payload_t: QType, stored_t: QType, auto_t) -> Optional[ir.Plan]:
    """How an auto value's components are stored, in the auto type's
    witness-independent layout: a component of the type component's type keeps
    its own representation (inspect reads it by the stored type component's
    descriptor), in its QVal form where the layout holds a QVal, which its slot
    already holds (a bounded type parameter's value, at its own view, as the
    witness's); the others convert to their stored types."""
    source = shape(payload_t).components
    target = shape(stored_t).components
    fields = []
    for sig_f, sc, tc in zip(auto_t.signature, source, target):
        if is_type_variable(sig_f.type_val, auto_t.symbol_id) and _slots_agree(sc.shape, tc.shape):
            fields.append(None)
        else:
            fields.append(plan(sc.shape.type, tc.shape.type))
    if all(p is None for p in fields) and all(_slots_agree(sc.shape, tc.shape) for sc, tc in zip(source, target)):
        if shape_representation(shape(payload_t)) == shape_representation(shape(stored_t)):
            return None
        return _unproxied(ir.Plan("cast", payload_t, stored_t))
    payload_s = shape(payload_t)
    access = tuple(tuple_access(payload_s, i) for i in range(len(fields)))
    return ir.Plan("copy", payload_t, stored_t, tuple(fields), access=access)


def auto_layouts_agree(stored_t: QType, arm_t: QType) -> bool:
    """Whether an auto value's stored payload can be read in place as an inspect
    case's components: each component has the same slot representation (a
    closure the same signature representation), or is stored as a QVal holding a
    scalar or pointer."""
    for stored_f, arm_f in zip(shape(stored_t).components, shape(arm_t).components):
        stored_c = shape_slot_representation(stored_f.shape)
        arm_c = shape_slot_representation(arm_f.shape)
        if stored_c == arm_c:
            if arm_f.shape.kind in ("fun", "all") and (
                signature_representation(stored_f.shape.type) != signature_representation(arm_f.shape.type)
            ):
                return False
        elif stored_c != "QVal" or arm_c == "void":
            return False
    return True


def inspect_arm(auto_t, case: ir.InspectCase) -> ir.InspectArm:
    """How an inspect case of an auto value of type auto_t obtains its
    components (ir.InspectArm)."""
    stored_t = auto_payload_type(auto_t)
    arm_t = auto_payload_type(auto_t, case.match_type)
    has_var = any(f.is_var for f in auto_t.signature)
    converted = tuple(
        None if auto_t.symbol_id not in sig_f.type_val._fv
        else "component" if is_type_variable(sig_f.type_val, auto_t.symbol_id)
        else "mentions"
        for sig_f in auto_t.signature
    )
    if not case.exact:
        return ir.InspectArm(converted)
    shared = auto_layouts_agree(stored_t, arm_t)
    if not shared and has_var:
        raise UnsupportedConversion(
            f"C code generation cannot inspect an auto value of type '{auto_t}' at type "
            f"'{case.match_type}': its components need conversion, so the var components could not be "
            f"shared with the auto value"
        )
    return ir.InspectArm(converted, exact=True, shared=shared, plan=None if shared else plan(stored_t, arm_t),
                         layout_error=has_var)


def type_app_plans(orig_t: QType, type_args: tuple[QType, ...],
                   target_t: QType) -> tuple[tuple[Optional[ir.Plan], ...], tuple[tuple[int, ...], ...]]:
    """How a polymorphic value of type orig_t applied to the type arguments is
    used at target_t (ir.TypeApp.plans): for a value of no parameters, its
    value's plan from the generic result at the type arguments; for a function,
    the plans of a thunk of target_t's signature, converting each argument from
    target_t's parameter type to the function's generic one at the type
    arguments (None for var and out parameters), and the result back. The type
    parameters the type arguments do not bind stand for target_t's own, the
    thunk's, whose symbols are returned too (ir.TypeApp.thunk_symbols)."""
    quants, inner = quantified(orig_t)
    instantiation = {q.symbol_id: t for q, t in zip(quants, type_args)}
    if not isinstance(inner, QFunType):
        return (plan(inner, target_t, (instantiation, False)),), ()
    t_quants, t_inner = quantified(target_t)
    for oq, tq in zip(quants[len(type_args):], t_quants):
        instantiation[oq.symbol_id] = QTypeVar(name=tq.name, symbol_id=tq.symbol_id, bound=tq.bound)
    t_params = t_inner.params if isinstance(t_inner, QFunType) else ()
    t_result = t_inner.result_type if isinstance(t_inner, QFunType) else t_inner
    params = tuple(
        None if tp.is_var or tp.is_out else plan(tp.type_val, op.type_val, (instantiation, True))
        for tp, op in zip(t_params, inner.params)
    )
    plans = params + (plan(inner.result_type, t_result, (instantiation, False)),)
    return plans, tuple((tq.symbol_id,) for tq in t_quants)


def _type_of(a: ir.Atom) -> QType:
    return a.type if isinstance(a, ir.Var) else a.shape.type


class _Representer:
    def __init__(self, unit: ir.Unit) -> None:
        self.unit = unit
        self.joins: dict[str, tuple[ir.Var, ...]] = {}
        self.generic_results: list[tuple[QType, QType, dict]] = []
        # The function whose body is being represented (None for a top level)
        self.function: Optional[ir.Function] = None

    def convert(self, a: ir.Atom, target: QType, before: list, layout=None) -> ir.Atom:
        """a, converted to be used at target (by a let added to before), or a
        itself."""
        p = plan(_type_of(a), target, layout)
        if p is None:
            return a
        converted = ir.Var(a.hint if isinstance(a, ir.Var) else "", target)
        before.append(ir.Let(converted, ir.Convert(a, p)))
        return converted

    def body(self, body: ir.Body, function: Optional[ir.Function]) -> None:
        self.function = function
        statements = []
        for s in body.statements:
            if isinstance(s, ir.Join):
                self.joins[s.label] = s.params
            for b in statement_bodies(s):
                self.body(b, function)
            statements.extend(self.statement(s, function))
        body.statements = statements

    def result(self, s: ir.Let, result_t: QType, after: list) -> None:
        """Converts the result of s's operation, of type result_t, to s's
        variable's type."""
        p = plan(result_t, s.var.type)
        if p is not None:
            result = ir.Var(s.var.hint, result_t)
            after.append(ir.Let(s.var, ir.Convert(result, p)))
            s.var = result

    def statement(self, s, function: Optional[ir.Function]) -> list:
        """The statements s becomes: conversions of its operands, s, and a
        conversion of its result."""
        before: list = []
        after: list = []
        match s:
            case ir.Let(var=var, value=ir.Var() | ir.Const() as a):
                s.value = self.convert(a, var.type, before)
            case ir.Let(var=var, value=ir.Call() as call):
                writebacks: list = []
                self.generic_results = []
                result_t = self.call(call, before, writebacks)
                if self.generic_results:
                    # The callee's generic result, converted to its type at the
                    # type arguments, then to the let's
                    generic_t, instantiated_t, instantiation = self.generic_results[0]
                    step = plan(generic_t, instantiated_t, (instantiation, False))
                    if step is not None:
                        instantiated = ir.Var(var.hint, instantiated_t)
                        generic = ir.Var(var.hint, generic_t)
                        after.append(ir.Let(instantiated, ir.Convert(generic, step)))
                        s.var = generic
                        final = plan(instantiated_t, var.type)
                        if final is None:
                            after.append(ir.Let(var, instantiated))
                        else:
                            after.append(ir.Let(var, ir.Convert(instantiated, final)))
                    else:
                        # The generic result is laid out as the native one at
                        # the type arguments
                        self.result(s, instantiated_t, after)
                else:
                    self.result(s, result_t, after)
                after.extend(writebacks)
            case ir.Do(value=ir.Call() as call):
                self.call(call, before, after)
            case ir.Let(var=var, value=value):
                result_t = self.operation(value, var.type, before)
                if result_t is not None:
                    self.result(s, result_t, after)
            case ir.VarDecl(var=var, init=init):
                s.init = self.convert(init, var.type, before)
            case ir.Assign(var=var, value=value):
                s.value = self.convert(value, var.type, before)
            case ir.StoreAt() | ir.StoreField() | ir.StoreComponent() | ir.StoreElement():
                target_t = self.stored_type(s)
                if target_t is not None:
                    s.value = self.convert(s.value, target_t, before)
            case ir.Return(value=value) if function is not None:
                s.value = self.convert(value, function.result_type, before)
            case ir.Jump(label=label, args=args):
                params = self.joins[label]
                s.args = tuple(self.convert(a, p.type, before) for a, p in zip(args, params))
            case ir.Raise(exception=e, payload=p) if p is not None:
                exc_t = written_structure(_type_of(e), "exception")
                if exc_t is not None and exc_t.payload_type is not None:
                    s.payload = self.convert(p, exc_t.payload_type, before)
            case ir.Inspect(cases=cases, auto_type=auto_t) if auto_t is not None:
                for case in cases:
                    self.inspect_case(auto_t, case, function)
        return before + [s] + after

    @staticmethod
    def type_params(function: Optional[ir.Function]) -> set[int]:
        """The symbols of the type parameters in scope in a function's body (its
        own and those its closure supplies), whose descriptors it is passed."""
        return {tp.symbol_id for tp in function.type_params} if function is not None else set()

    def inspect_case(self, auto_t, case: ir.InspectCase, function: Optional[ir.Function]) -> None:
        """Decides how an inspect case obtains its components (its arm), and
        converts them to its binders' types: a binder that needs converting is
        bound by a let at the case's start, from a binder of the arm's type."""
        if not case.binders:
            return
        case.arm = inspect_arm(auto_t, case)
        arm_t = auto_payload_type(auto_t, case.match_type)
        binders = []
        lets = []
        for b in case.binders:
            p = plan(arm_t, b.type)
            if p is None:
                binders.append(b)
                continue
            arm = ir.Var(b.hint, arm_t)
            binders.append(arm)
            lets.append(ir.Let(b, ir.Convert(arm, p)))
        case.binders = tuple(binders)
        case.body.statements[:0] = lets

    def operation(self, o, result_t: QType, before: list) -> Optional[QType]:
        """Converts an operation's operands to the types it stores them at,
        returning the type of its result as the operation gives it (None when
        that is the let's own)."""
        match o:
            case ir.MakeTuple(args=args):
                t = written_structure(result_t, "tuple")
                if t is not None:
                    o.args = tuple(self.convert(a, f.type_val, before) for a, f in zip(args, t.value_fields))
            case ir.MakeVariant(tag=tag, payload=payload) if payload is not None:
                t = written_structure(result_t, "variant")
                case = t.get_variant(tag) if t is not None else None
                if case is not None and case.type_val is not None:
                    o.payload = self.convert(payload, case.type_val, before)
            case ir.MakeOption(tag=tag, payload=payload) if payload is not None and tag is not None:
                t = written_structure(result_t, "option")
                case = t.get_option(tag) if t is not None else None
                if case is not None and case.payload_type is not None:
                    o.payload = self.convert(payload, case.payload_type, before)
            case ir.MakeArray(args=args):
                elem = array_element(result_t)
                o.args = tuple(self.convert(a, elem, before) for a in args)
            case ir.ArrayRep(init=init):
                o.init = self.convert(init, array_element(result_t), before)
            case ir.MakeAuto(witness=witness, auto_type=auto_t, payload=payload):
                stored_t = auto_payload_type(auto_t)
                p = auto_payload_plan(_type_of(payload), stored_t, auto_t)
                if p is not None:
                    stored = ir.Var("payload", stored_t)
                    before.append(ir.Let(stored, ir.Convert(payload, p)))
                    o.payload = stored
            case ir.TupleField(tuple=t, index=index):
                tt = written_structure(_type_of(t), "tuple")
                return tt.value_fields[index].type_val if tt is not None else None
            case ir.RecordField(record=r, name=name):
                rt = written_structure(_type_of(r), "record")
                field = next((f for f in rt.fields if f.name == name), None) if rt is not None else None
                return field.type_val if field is not None else None
            case ir.Index(array=a):
                return array_element(_type_of(a))
            case ir.ModuleMember(module=ir.Module() as m, member=member) if member is not None:
                return m.members[member].type
            case ir.TypeApp(type_args=type_args):
                if o.callee is not None:
                    orig_t = o.callee.type
                elif isinstance(o.module, ir.Module):
                    orig_t = o.module.members[o.member].type
                else:
                    orig_t = o.callee_type
                o.plans, o.thunk_symbols = type_app_plans(orig_t, type_args, result_t)
            case ir.Payload(value=v, tag=tag):
                vt = written_structure(_type_of(v), "variant")
                if vt is not None:
                    case = vt.get_variant(tag)
                    return case.type_val if case is not None and case.type_val is not None else None
        return None

    def stored_type(self, s) -> Optional[QType]:
        """The type of the location a store stores into (None for one through an
        address)."""
        match s:
            case ir.StoreField(base=base, name=name):
                rt = written_structure(_type_of(base), "record")
                field = next((f for f in rt.fields if f.name == name), None) if rt is not None else None
                return field.type_val if field is not None else None
            case ir.StoreComponent(base=base, index=index):
                tt = written_structure(_type_of(base), "tuple")
                return tt.value_fields[index].type_val if tt is not None else None
            case ir.StoreElement(base=base):
                return array_element(_type_of(base))
        return None

    def call(self, call: ir.Call, before: list, after: list) -> QType:
        """Converts a call's arguments to its callee's parameter types,
        returning its callee's result type. A var or out argument whose location
        is laid out differently from the parameter is a temporary of the
        parameter's type, converted into the location after the call (added to
        after)."""
        self.generic_results = []
        if call.callee is not None:
            callee_t = call.callee.type
        elif isinstance(call.module, ir.Module):
            # A member of one of the unit's modules, called from outside it at
            # its interface's types (abstract types among them), works at the
            # module's own: its arguments and result convert at the boundary
            callee_t = call.module.members[call.member].type
        else:
            callee_t = call.callee_type
        if callee_t is None:
            raise UnsupportedConversion(f"a call of {call.member} whose type is unknown")
        params, result_t = fun_signature(callee_t)
        # A polymorphic callee's parameters at the call's type arguments: an
        # argument is converted to its parameter's type there (a record viewed
        # at the type argument), then to the parameter's generic representation
        quants, _ = quantified(callee_t)
        instantiation = {q.symbol_id: t for q, t in zip(quants, call.type_args)}
        args = []
        for i, a in enumerate(call.args):
            if i < len(params) and (params[i].is_out or params[i].is_var):
                a = self.ref_argument(a, params[i], instantiation, before, after)
            elif i < len(params):
                if instantiation:
                    a = self.convert(a, params[i].type_val.substitute(instantiation), before)
                a = self.convert(a, params[i].type_val, before, (instantiation, True))
            args.append(a)
        call.args = tuple(args)
        if instantiation:
            self.generic_results.append((result_t, result_t.substitute(instantiation), instantiation))
        return result_t

    def ref_argument(self, address: ir.Atom, param, instantiation: dict, before: list, after: list) -> ir.Atom:
        """The address passed for a var or out argument: the location's own, or
        that of a temporary of the parameter's representation (a shadow cell of
        a generic parameter's QVal, or a cell of an out parameter's type where
        the location's is a supertype laid out differently), copied in from the
        location (for var) and out to it after the call. A location holds a
        record or variant boxed (location_representation), as a generic
        parameter's QVal does, so its address is passed to a generic parameter
        as it is."""
        location_t = _type_of(address)
        if isinstance(location_t, (QVarType, QOutType)):
            location_t = location_t.element_type
        param_t = param.type_val
        layout_out = (instantiation, False) if instantiation else None
        p_out = plan(param_t, location_t, layout_out)
        p_in = None if param.is_out else plan(location_t, param_t, (instantiation, True) if instantiation else None)
        if p_out is None and p_in is None:
            return address
        ref_t = QOutType(element_type=param_t) if param.is_out else QVarType(element_type=param_t)
        if is_boxed_in_slots(shape(location_t)) and shape_representation(shape(param_t)) == "QVal" and all(
            p is None or p.kind in ("box", "unbox") for p in (p_in, p_out)
        ):
            # The location holds the record or variant boxed, as the generic
            # parameter's QVal does
            cast = ir.Var("", ref_t)
            before.append(ir.Let(cast, ir.Convert(address, ir.Plan("cast", _type_of(address), ref_t))))
            return cast
        temp = ir.Var("cell", param_t, mutable=True)
        temp_address = ir.Var("", ref_t)
        init = None
        if not param.is_out:
            current = ir.Var("", location_t)
            before.append(ir.Let(current, ir.Load(address)))
            init = current
            if p_in is not None:
                init = ir.Var("", param_t)
                before.append(ir.Let(init, ir.Convert(current, p_in)))
        before.append(ir.VarDecl(temp, init))
        before.append(ir.Let(temp_address, ir.AddrVar(temp)))
        written = ir.Var("", param_t)
        after.append(ir.Let(written, temp))
        if p_out is not None:
            converted = ir.Var("", location_t)
            after.append(ir.Let(converted, ir.Convert(written, p_out)))
            written = converted
        after.append(ir.StoreAt(written, address))
        return temp_address

    def run(self) -> None:
        for m in self.unit.modules:
            self.body(m.init, None)
        self.body(self.unit.main, None)
        for f in self.unit.functions:
            self.body(f.body, f)


def represent_unit(unit: ir.Unit) -> ir.Unit:
    """Inserts the unit's conversions, in place, returning it."""
    _Representer(unit).run()
    decide_slots(unit)
    unit.stage = "represented"
    return unit
