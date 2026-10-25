"""The C printer (docs/ir.md §8.5): prints a described IR unit as C, the IR's backend.

It prints what the passes decided: each IR function is a C function taking its closure's environment first (and its
own type parameters' descriptors, then its parameters), each closure a QClosure of one (a static one when it captures
nothing), each variable a C variable of its type's representation (globals for the variables the top levels bind
outside loops, declared at file scope), and each structured statement a C statement: join points and loop exits are
labels, and try regions setjmp handlers, popped on every way out. Conversions are `convert` operations, printed as
their plans say, and every other representation decision is the represent pass's, recorded in the IR (docs/ir.md
§8.3, §8.5): aggregate slots hold records and variants boxed (slot_representation), as the locations var and out
parameters point to do, and the IR's boxed variables, slot_box and slot_unbox conversions, and embedded components say
where boxes are made, reused, and read; a tuple or option whose type may be proxied (docs/c-representation.md §5.8)
may be a view of an object of a subtype, and each read of a component records whether it goes through a proxy check,
the original, or neither; inspect cases record their arms, and type applications their thunks' plans. Descriptors are
the describe pass's (ir/describe.py, docs/ir.md §8.4): every run-time use of a type carries its descriptor operand
(a descriptor variable, which the printer names: a function's descriptor parameter, a thunk's, or an inspected auto
value's type component; a static descriptor, which it declares; or a template instantiated at run time), and the
unit's static data lists the static descriptors, offset tables, and tag maps the printer declares. The declarations
of the types it uses (structs, descriptors, offset tables, function type adapters) are c/declarations.py's, and the
representations codegen/layout.py's, spelled in C by c/types.py (docs/c-representation.md). A module file's unit
exports its interface's members: its record (`qm_<module>`), initializer (`qv_mod_<module>_init`), and a function
for each function or polymorphic value (`qv_<module>_<member>`), the ABI other units link against.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any, Optional

from quest.codegen.c.declarations import (
    CDeclarationEmitter,
    collect_aggregate_types,
    fun_shape_signature,
    module_function_arguments,
    module_function_signature,
)
from quest.codegen.c.types import (
    c_char_literal,
    c_string_literal,
    closure_fn_ptr_type,
    descriptor_form,
    echo_descriptor_form,
    MissingDescriptorError,
    qtype_to_c_type,
    qval_unwrap,
    qval_wrap,
    record_struct_name,
    RecordNamingContext,
    shape_qval_to_slot,
    shape_qval_unwrap,
    shape_qval_wrap,
    shape_slot_load,
    shape_slot_store,
    shape_slot_to_qval,
)
from quest.codegen.layout import (
    qtype_to_name_str,
    shape_location_representation,
    shape_representation,
    shape_slot_representation,
    shape_tag,
    tuple_struct_name,
    type_identity_key,
    type_tag,
)
from quest.codegen.symbols import mangle_ident, mangle_module_ident, mangle_module_name, module_record_ident
from quest.diagnostics import MAIN_FRAME, init_frame
from quest.ir import nodes as ir
from quest.ir.describe import echo_value_kind
from quest.ir.represent import held_shape
from quest.ir.shapes import Shape, shape
from quest.ir.walk import global_variables, statement_binders, walk_statements
from quest.types import (
    QAutoType,
    auto_payload_type,
    QParam,
    QRecordField,
    QRecordType,
    QType,
)

_INT_OPS = {"+": "+", "-": "-", "*": "*", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
_REAL_OPS = {"++": "quest_real_add", "--": "quest_real_sub", "**": "quest_real_mul", "//": "quest_real_divide"}
_REAL_RELATIONS = {"<<": "<", "<<=": "<=", ">>": ">", ">>=": ">="}


def _type_parameter_count(t: QType) -> int:
    """The number of type parameters a (possibly polymorphic) function type takes."""
    s = shape(t)
    count = 0
    while s.kind == "all":
        count += len(s.type_params)
        s = s.body
    return count


def _index_table(entries: list[int]) -> str:
    """A C array of indices, to be indexed by a tag or an ordinal."""
    return f"((const int64_t[]){{ {', '.join(f'{e}LL' for e in entries)} }})"


@dataclasses.dataclass
class _FreshBox:
    """A record or variant (an unboxed value) to be stored into a slot of an aggregate being made, in a box sharing
    the aggregate's allocation."""
    value: str
    shape: Shape


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
        self, unit: ir.Unit, env: Any, interface_header: Optional[str] = None
    ) -> None:
        self.unit = unit
        self.interface_header = interface_header
        self.env = env
        self.ctx = RecordNamingContext()
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
        # The pairs of tuple types converted by casts (whose layouts agree, which the C asserts)
        self.tuple_casts: dict[tuple[str, str], tuple[QType, QType]] = {}
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
        if key not in self.names and var.type is ir.DESCRIPTOR_TYPE:
            # A descriptor variable (a function's descriptor parameter)
            self.names[key] = self.fresh_name(var.hint)
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

    def shape_c_type(self, s: Shape) -> str:
        self.types.append(s.structure)
        return shape_representation(s)

    def slot_c_type(self, s: Shape) -> str:
        """The C type of a slot holding values of shape s (slot_representation)."""
        self.types.append(s.structure)
        return shape_slot_representation(s)

    # Proxies (docs/c-representation.md §5.8): a value of a tuple or option type that may be proxied may be a view of
    # an object of a subtype, whose components are read (and var components written) through the runtime, as the
    # represent pass decided (ir.DIRECT, ir.ORIGINAL, ir.PROXY)

    def tuple_component(self, t: str, ts: Shape, i: int, access: str) -> str:
        """The slot form of component i of the tuple t (an atom's C expression) of shape ts, read as access says."""
        if access == ir.DIRECT:
            return f"({t})->_{i}"
        if access == ir.ORIGINAL:
            # Read from the original as it is (its slot at the same offset)
            return f"(({self.c_type(ts.type)})quest_unproxy({t}))->_{i}"
        comp = ts.components[i].shape
        tmp = self.temp(self.slot_c_type(comp))
        through = shape_qval_to_slot(f"quest_proxy_element({t}, {i})", comp)
        self.emit(f"{tmp} = quest_is_proxy({t}) ? {through} : ({t})->_{i};")
        return tmp

    @staticmethod
    def option_tag(v: str, access: str) -> str:
        """The tag of the option v, in its type's numbering, read as access says (through a proxy if it may be one)."""
        if access == ir.DIRECT:
            return f"(({v})->tag)"
        return f"(quest_is_proxy({v}) ? quest_proxy_tag({v}) : ({v})->tag)"

    def option_component(self, v: str, os: Shape, tag: str, i: Optional[int], access: str) -> str:
        """The slot form of component i (None: the payload, when it is not a tuple) of the payload of case tag of
        the option v of shape os, read as access says."""
        raw = f"{v}->u.{tag}.val" if i is None else f"{v}->u.{tag}._{i}"
        if access == ir.DIRECT:
            return raw
        if access == ir.ORIGINAL:
            unproxied = f"(({shape_representation(os)})quest_unproxy({v}))"
            return f"{unproxied}->u.{tag}.val" if i is None else f"{unproxied}->u.{tag}._{i}"
        case = os.case(tag)
        comp = case.shape if i is None else case.shape.components[i].shape
        tmp = self.temp(self.slot_c_type(comp))
        through = shape_qval_to_slot(f"quest_proxy_option_element({v}, {i or 0})", comp)
        self.emit(f"{tmp} = quest_is_proxy({v}) ? {through} : {raw};")
        return tmp

    def slot_fields(self, args, shapes: list[Shape], embedded: tuple[int, ...]) -> list:
        """The fields of an aggregate being made: the atoms' C expressions (their slot forms), or for those the
        represent pass embedded, _FreshBoxes, which the aggregate's allocation makes room for (embedded_boxes)."""
        return [_FreshBox(self.atom(a), s) if i in embedded else self.atom(a)
                for i, (a, s) in enumerate(zip(args, shapes))]

    def embedded_boxes(self, block: str, size: str, fields: list) -> tuple[str, list[str]]:
        """The size of an aggregate's allocation with room after it (size, at block) for the boxes of its fields that
        are _FreshBoxes, and the fields' slot forms, filling in those boxes: a field's box is immutable, so it may
        share the aggregate's allocation (one allocation rather than one per box)."""
        fresh = [f for f in fields if isinstance(f, _FreshBox)]
        if not fresh:
            return size, fields
        boxes = self.temp("QRecordVal *")
        values = []
        for f in fields:
            if isinstance(f, _FreshBox):
                k = len([v for v in values if isinstance(v, tuple)])
                values.append((k, f))
            else:
                values.append(f)
        out = []
        self.pending_embedded = (boxes, block)
        for v in values:
            if isinstance(v, tuple):
                k, f = v
                box_c = self.slot_c_type(f.shape)
                out.append((k, f"(({box_c})&{boxes}[{k}])", f))
            else:
                out.append(v)
        return f"{size} + {len(fresh)} * sizeof(QRecordVal)", out

    def fill_embedded(self, fields: list) -> list[str]:
        """Fills in the embedded boxes of fields (from embedded_boxes), returning the fields' slot forms."""
        if self.pending_embedded is None:
            return fields
        boxes, block = self.pending_embedded
        self.pending_embedded = None
        self.emit(f"{boxes} = (QRecordVal *)({block} + 1);")
        out = []
        for f in fields:
            if isinstance(f, tuple):
                _, box, fresh = f
                self.emit(f"*{box} = {fresh.value};")
                out.append(box)
            else:
                out.append(f)
        return out

    pending_embedded: Optional[tuple[str, str]] = None

    def slot_address(self, ptr: str, s: Shape) -> str:
        """The address of a slot holding values of shape s, as the address of a location of the value
        (location_representation): a record's or variant's box, a Bool's or Char's word through its first byte (the
        slot holds 0 or 1, or the character, in its low byte)."""
        slot_c, c = self.slot_c_type(s), shape_location_representation(s)
        return ptr if slot_c == c else f"(({c} *){ptr})"

    def located_shape(self, address: ir.Atom) -> Shape:
        """The shape of the values at an address (of a var or out location)."""
        s = shape(self.atom_type(address))
        return s.element if s.kind in ("cell", "out") else s

    def var_c_type(self, var: ir.Var) -> str:
        if id(var) in self.handler_vars:
            return "QExceptionState"
        if var.boxed:
            return self.slot_c_type(shape(var.type))
        return self.c_type(var.type)

    @staticmethod
    def is_ok(t: QType) -> bool:
        return shape(t).kind == "ok"

    def held(self, t: QType, kind: str) -> Shape:
        """The shape of t's values as held (see held_shape), which the IR guarantees is of the kind."""
        s = held_shape(t, kind)
        if s is None:
            raise NotImplementedError(f"C printing of a {kind} operation on a value of type {t}")
        return s

    def tag_shape(self, t: QType) -> Shape:
        """The variant or option shape of a value of type t that is switched on or tested."""
        s = held_shape(t, "variant") or held_shape(t, "option")
        if s is None:
            raise NotImplementedError(f"C printing of a tag test on a value of type {t}")
        return s

    def element_shape(self, a: ir.Atom) -> Shape:
        """The shape of the elements of an array atom."""
        s = shape(self.atom_type(a))
        if s.kind != "array":
            raise NotImplementedError(f"C printing of an array operation on a value of type {self.atom_type(a)}")
        return s.element

    def descriptor(self, d: ir.Descriptor) -> str:
        """A descriptor operand (ir/describe.py): a descriptor variable, a static descriptor, or a template instantiated
        at run time with its holes' descriptors."""
        if isinstance(d, ir.Var):
            return self.name(d)
        if isinstance(d, ir.StaticDescriptor):
            form = echo_descriptor_form(d.type, self.ctx) if d.echo else None
            return (form or self.static_form(d.type)).c_expr
        if isinstance(d, ir.Instantiate):
            form = self.static_form(d.template)
            if form.kind in ("base", "bound_var"):
                return form.c_expr
            args = ", ".join(self.descriptor(a) for a in d.args)
            return f"quest_instantiate_descriptor({form.c_expr}, {len(d.args)}, (const QTypeDescriptor *const[]){{ {args} }})"
        raise NotImplementedError("C code generation: a run-time use of a type without its descriptor")

    def static_form(self, t: QType):
        try:
            return descriptor_form(t, self.ctx)
        except MissingDescriptorError as e:
            raise NotImplementedError(f"C code generation: {e}") from None

    def static_descriptor(self, t: QType) -> str:
        """The static descriptor of a closed type (a part of another's, as the declarations name it)."""
        return self.static_form(t).c_expr

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
            return f"(*(*{name}))" if a.boxed else f"(*{name})"
        if a.boxed and a.mutable:
            # A boxed mutable variable holds its location's box (a boxed value is the box itself)
            return f"(*{name})"
        return name

    def is_pointer_param(self, var: ir.Var) -> bool:
        f = self.fs.function
        return f is not None and any(v is var and mode != "value" for v, mode in f.params)

    def location_c_type(self, t: QType) -> str:
        """The C type of a location of a value of t (location_representation): a record or variant boxed."""
        self.types.append(t)
        return shape_location_representation(shape(t))

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
            case ir.Prim(op=op, args=args, offset=offset, access=access):
                return self.prim(op, args, offset, access, o.descriptor)
            case ir.Ordinal(value=v, cases=cases, access=access):
                # The tag numbers the shape's cases, ordered by name; the ordinal counts in the static type's order
                tag = self.option_tag(self.atom(v), access)
                names = tuple(c.name for c in self.tag_shape(self.atom_type(v)).cases)
                return tag if names == cases else f"{_index_table([cases.index(n) for n in names])}[{tag}]"
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
            case ir.CallExternal(args=args):
                return self.external_call(o, [self.descriptor(d) for d in o.descriptors], [self.atom(a) for a in args])
            case ir.MakeClosure():
                return self.make_closure(o, result)
            case ir.EnvField(env=env, index=index):
                return f"{self.name(env)}->c{index}"
            case ir.Convert(value=v, plan=plan):
                if plan.kind == "unbox" and result is not None and result.boxed:
                    # A QVal word holds a record or variant as its box
                    return shape_qval_to_slot(self.atom(v), shape(plan.target))
                if plan.kind == "box" and isinstance(v, ir.Var) and v.boxed and not v.mutable:
                    # A box is a record's or variant's QVal word
                    return shape_slot_to_qval(self.atom(v), shape(plan.source))
                return self.convert(self.atom(v), plan)
            case ir.MakeException(name=name):
                return f"quest_alloc_exception({c_string_literal(name)})"
            case ir.ExceptionPayload(exception=e):
                return qval_unwrap(f"{self.name(e)}.payload", result.type, self.ctx)
            case ir.Addr(var=var) if var is not None:
                if self.is_pointer_param(var):
                    return self.name(var)
                if id(var) in self.fs.volatile:
                    return f"(({self.location_c_type(var.type)} *)&{self.name(var)})"
                return f"(&{self.name(var)})"
            case ir.Addr(cell=cell) if cell is not None:
                cell_c = self.temp(self.location_c_type(self.atom_type(cell)))
                self.emit(f"{cell_c} = {self.atom(cell)};")
                return f"(&{cell_c})"
            case ir.Load(address=a):
                return f"(*{self.atom(a)})"
            case ir.Addr(base=base, name=name) if name is not None:
                ptr, field = self.record_slot(self.atom(base), self.held(self.atom_type(base), "record"), name)
                return self.slot_address(ptr, field)
            case ir.Addr(base=base, index=index, access=access) if isinstance(index, int):
                ts = shape(self.atom_type(base))
                component = ts.components[index].shape
                b = self.atom(base)
                address = self.slot_address(f"(&({b}->_{index}))", component)
                if access == ir.DIRECT:
                    return address
                if access == ir.ORIGINAL:
                    return self.slot_address(f"(&((({self.c_type(ts.type)})quest_unproxy({b}))->_{index}))", component)
                through = f"(({shape_location_representation(component)} *)quest_proxy_slot({b}, {index}))"
                return f"(quest_is_proxy({b}) ? {through} : {address})"
            case ir.Addr(base=base, index=index, offset=offset):
                return self.array_slot(self.atom(base), self.atom(index), self.element_shape(base), offset)
            case ir.MakeTuple(args=args, embedded=embedded):
                shapes = [c.shape for c in shape(result.type).components]
                return self.make_tuple(result.type, self.slot_fields(args, shapes, embedded))
            case ir.TupleField(tuple=t, index=index, access=access):
                return self.tuple_component(self.atom(t), shape(self.atom_type(t)), index, access)
            case ir.MakeRecord():
                return self.make_record(o, result)
            case ir.RecordField(record=r, name=name):
                return self.record_field(self.atom(r), self.held(self.atom_type(r), "record"), name, o)
            case ir.MakeVariant(tag=tag, payload=payload):
                vs = self.held(result.type, "variant")
                index = self.tag_index(vs, tag)
                if payload is None:
                    return f"((QVariantVal){{ .tag = {index}LL, .payload = Q_OK_VAL }})"
                case = vs.case(tag)
                case_s = case.shape if case is not None and case.shape is not None else shape(self.atom_type(payload))
                return f"((QVariantVal){{ .tag = {index}LL, .payload = {shape_qval_wrap(self.atom(payload), case_s)} }})"
            case ir.MakeOption():
                return self.make_option(o, result.type)
            case ir.IsTag(value=v, tag=tag, access=access):
                ts = self.tag_shape(self.atom_type(v))
                tag_c = f"{self.atom(v)}.tag" if ts.kind == "variant" else self.option_tag(self.atom(v), access)
                return f"({tag_c} == {self.tag_index(ts, tag)}LL)"
            case ir.Payload():
                return self.payload(o, result.type)
            case ir.MakeArray(args=args):
                elem = shape(result.type).element
                return self.make_array([self.array_element(a, elem) for a in args], result.type)
            case ir.ArrayRep(count=count, init=init, offset=offset):
                n = f"quest_check_array_count_at({self.atom(count)}, {self.site(offset)})"
                return f"quest_array_new({n}, {self.array_element(init, shape(result.type).element)})"
            case ir.TypeApp():
                return self.type_app(o, result)
            case ir.MakeAuto(auto_type=auto_t, payload=payload):
                return self.make_auto(o.descriptor, auto_t, payload)
            case ir.Index(array=a, index=i, offset=offset):
                arr, idx = self.atom(a), self.atom(i)
                self.emit(f"quest_check_array_bounds_at({arr}, {idx}, {self.site(offset)});")
                elem = self.element_shape(a)
                if result is not None and result.boxed:
                    # A record or variant in its slot form, its box
                    return shape_qval_to_slot(f"({arr}->data[{idx}])", elem)
                return self.array_get(arr, idx, elem)
        raise NotImplementedError(f"C printing of {type(o).__name__}")

    def convert(self, c: str, plan: ir.Plan) -> str:
        match plan.kind:
            case "box":
                return qval_wrap(c, plan.source)
            case "unbox":
                return qval_unwrap(c, plan.target, self.ctx)
            case "record_view":
                return f"quest_record_view({c}, {self.descriptor(plan.descriptors[0])})"
            case "variant_tags":
                table = plan.tag_map
                self.types.extend((table.source, table.target))
                v = self.temp("QVariantVal")
                self.emit(f"{v} = {c};")
                tagmap = f"tagmap_{type_tag(table.target)}_{type_tag(table.source)}"
                return f"((QVariantVal){{ .tag = {tagmap}[{v}.tag], .payload = {v}.payload }})"
            case "cast":
                source_s, target_s = shape(plan.source), shape(plan.target)
                if source_s.kind == target_s.kind == "tuple" and shape_tag(source_s) != shape_tag(target_s):
                    self.tuple_casts[(shape_tag(target_s), shape_tag(source_s))] = (target_s.structure,
                                                                                    source_s.structure)
                return f"(({self.c_type(plan.target)}){c})"
            case "unproxy":
                return f"(({self.c_type(plan.target)})quest_unproxy({c}))"
            case "slot_box":
                return shape_slot_store(c, shape(plan.source))
            case "slot_unbox":
                return f"(*{c})"
            case "view":
                source_d, target_d = (self.descriptor(d) for d in plan.descriptors)
                converted = f"quest_convert({qval_wrap(c, plan.source)}, {source_d}, {target_d})"
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
                from_t, to_t = (native_t, generic_t) if to_generic else (generic_t, native_t)
                from_d, to_d = (self.descriptor(d) for d in plan.descriptors)
                converted = f"quest_convert({qval_wrap(c, from_t)}, {from_d}, {to_d})"
                return qval_unwrap(converted, to_t, self.ctx)
            case "copy":
                src = self.temp(f"{self.c_type(plan.source)}")
                self.emit(f"{src} = {c};")
                fields = []
                source_s, target_s = shape(plan.source), shape(plan.target)
                for i, (tc, fp) in enumerate(zip(target_s.components, plan.fields)):
                    sc = source_s.components[i].shape
                    fc = self.tuple_component(src, source_s, i, plan.access[i])
                    if fp is not None and fp.kind == "view":
                        # Converted by descriptor, from the slot's QVal form to the target slot's
                        source_d, target_d = (self.descriptor(d) for d in fp.descriptors)
                        converted = f"quest_convert({shape_slot_to_qval(fc, sc)}, {source_d}, {target_d})"
                        fields.append(shape_qval_to_slot(converted, tc.shape))
                    elif fp is not None:
                        fields.append(shape_slot_store(self.convert(shape_slot_load(fc, sc), fp), tc.shape))
                    elif self.slot_c_type(sc) == self.slot_c_type(tc.shape):
                        fields.append(fc)
                    else:
                        fields.append(shape_qval_to_slot(shape_slot_to_qval(fc, sc), tc.shape))
                return self.make_tuple(plan.target, fields)
        raise NotImplementedError(f"conversion plan {plan.kind}")

    # Thunks: closures adapted to other signatures, and polymorphic closures applied to types

    def auxiliary(self):
        """Prints an auxiliary function (a thunk) while printing another: the printing state is saved, and restored
        on leaving the with block."""
        printer = self

        class _Saved:
            def __enter__(self_inner):
                self_inner.saved = (printer.fs, printer.lines, printer.indent)
                printer.fs = _FunctionState(None)
                printer.lines = []
                printer.indent = 1
                return self_inner

            def __exit__(self_inner, *exc):
                printer.fs, printer.lines, printer.indent = self_inner.saved
                return False

        return _Saved()

    def thunk_params(self, descriptor_params, params) -> tuple[list[str], list[str], list[str]]:
        """A thunk's parameter declarations (after its environment), and the names of its descriptor parameters (its
        descriptor variables, ir.DescriptorParam, or as many as there are if they are counted) and value parameters."""
        decls, descs, names = [], [], []
        count = descriptor_params if isinstance(descriptor_params, int) else len(descriptor_params)
        for k in range(count):
            descs.append(f"qd_{k}")
            decls.append(f"const QTypeDescriptor *qd_{k}")
            if not isinstance(descriptor_params, int):
                self.names[id(descriptor_params[k].var)] = f"qd_{k}"
        for i, p in enumerate(params):
            names.append(f"qa_{i}")
            if p.is_var or p.is_out:
                decls.append(f"{self.location_c_type(p.type_val)} *qa_{i}")
            else:
                c_t = "QVal" if self.is_ok(p.type_val) else self.c_type(p.type_val)
                decls.append(f"{c_t} qa_{i}")
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
        _, _, s_result = fun_shape_signature(plan.source)
        _, t_params, t_result = fun_shape_signature(plan.target)
        with self.auxiliary():
            # The thunk's descriptor parameters are its descriptor variables, which its plans' descriptors use
            decls, descs, names = self.thunk_params(plan.thunk_params, t_params)
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
        descs = [self.descriptor(d) for d in o.descriptors]
        self.types.extend((orig_t, result.type))
        if o.thunk_params is None:
            if o.callee is None and isinstance(o.module, ir.Import):
                call = f"{mangle_module_ident(mangle_module_name(o.module.canonical_path), o.member)}({', '.join(descs)})"
            else:
                fn_ptr = closure_fn_ptr_type(orig_t, self.ctx)
                call = f"(({fn_ptr})({clos}->fn))({', '.join([f'{clos}->env'] + descs)})"
            p = o.plans[0]
            return call if p is None else self.convert(call, p)
        thunk, env_struct = self.type_app_thunk(orig_t, result.type, o)
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

    def type_app_thunk(self, orig_t: QType, target_t: QType, o: ir.TypeApp) -> tuple[str, str]:
        """The thunk of a type application (and its environment's struct), converting its arguments and result by the
        plans the represent pass made (ir.TypeApp.plans), with the descriptors the describe pass gave them (its own
        descriptor variables, ir.TypeApp.thunk_params, and static ones)."""
        type_args, plans = o.type_args, o.plans
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
        _, _, o_result = fun_shape_signature(orig_t)
        _, t_params, t_result = fun_shape_signature(target_t)
        with self.auxiliary():
            decls, descs, names = self.thunk_params(o.thunk_params, t_params)
            args = [a if p is None else self.convert(a, p) for a, p in zip(names, plans[:-1])]
            env_descs = [f"_env->desc[{i}]" for i in range(n)]
            call_args = ["_env->orig->env"] + env_descs + descs + args
            call = f"(({closure_fn_ptr_type(orig_t, self.ctx)})(_env->orig->fn))({', '.join(call_args)})"
            self.finish_thunk_call(call, o_result, t_result, plans[-1])
            ret = "void" if self.is_ok(t_result) else self.c_type(t_result)
            self.thunk(name, ret, decls, [f"{env_struct} *_env = ({env_struct} *)_raw_env;"]
                       + [f"(void){d};" for d in descs])
        return name, env_struct

    # Aggregates (laid out as docs/c-representation.md §5 says)

    @staticmethod
    def tag_index(s: Shape, tag: Optional[str]) -> int:
        """The index of a case of a variant or option shape."""
        return next((i for i, case in enumerate(s.cases) if case.name == tag), 0)

    def make_tuple(self, t: QType, fields: list) -> str:
        """A new tuple of type t of the fields (slot forms, or _FreshBoxes, which its allocation makes room for)."""
        struct = shape_tag(shape(t))
        self.c_type(t)
        tmp = self.temp(f"{struct} *")
        size, fields = self.embedded_boxes(tmp, f"sizeof({struct})", fields)
        self.emit(f"{tmp} = ({struct} *)quest_alloc({size});")
        for i, c in enumerate(self.fill_embedded(fields)):
            self.emit(f"{tmp}->_{i} = {c};")
        return tmp

    def make_record(self, o: ir.MakeRecord, result: ir.Var) -> str:
        """A new record, made in its box (the payload following it in one allocation): the box, for a boxed variable,
        or the record."""
        fields = o.fields
        concrete = QRecordType(tuple(
            QRecordField(name=n, type_val=self.atom_type(a), is_var=is_var) for n, a, is_var in fields
        ))
        held = held_shape(result.type, "record")
        target = held.structure if held is not None else concrete
        self.types.extend((concrete, target))
        struct = record_struct_name(concrete, self.ctx)
        box = self.temp("QRecordVal *")
        payload = self.temp(f"{struct} *")
        stored = [(i, n, a) for i, (n, a, _) in enumerate(fields) if not self.is_ok(self.atom_type(a))]
        size, values = self.embedded_boxes(
            payload, f"sizeof(QRecordVal) + sizeof({struct})",
            [_FreshBox(self.atom(a), shape(self.atom_type(a))) if i in o.embedded else self.atom(a) for i, _, a in stored],
        )
        self.emit(f"{box} = (QRecordVal *)quest_alloc({size});")
        self.emit(f"{payload} = ({struct} *)({box} + 1);")
        self.emit(f"{payload}->header.descriptor = {self.descriptor(o.descriptor)};")
        for (_, n, _), value in zip(stored, self.fill_embedded(values)):
            self.emit(f"{payload}->qf_{n} = {value};")
        if o.runtime_offsets:
            dict_expr = f"quest_record_dict({self.descriptor(o.view_descriptor)}, {self.descriptor(o.descriptor)})"
        else:
            dict_expr = f"(const void *)&{self.ctx.offset_dict_instance_name(o.offsets.view, o.offsets.layout)}"
        self.emit(f"*{box} = (QRecordVal){{ .val = (void *){payload}, .dict = {dict_expr} }};")
        return box if result.boxed else f"(*{box})"

    def record_slot(self, rec: str, rs: Shape, name: str) -> tuple[str, Shape]:
        """The address of the slot of a field of a record of shape rs, through its offset table, and the field's
        shape."""
        self.types.append(rs.structure)
        fields = rs.sorted_components()
        field = next(f for f in fields if f.name == name).shape
        dict_t = self.ctx.offset_dict_struct_name(rs.structure)
        return f"(({self.slot_c_type(field)} *)((char *){rec}.val + ((const {dict_t} *){rec}.dict)->offset_{name}))", field

    def record_field(self, rec: str, rs: Shape, name: str, o: ir.RecordField) -> str:
        """A field of a record of shape rs, through its offset table: its slot form, or when stored (a field the
        payload may store at another type, as its stored types say) read as stored and converted to the field's
        type, by its descriptor."""
        ptr, field = self.record_slot(rec, rs, name)
        if not o.stored:
            return f"(*{ptr})"
        fields = rs.sorted_components()
        index = next(i for i, f in enumerate(fields) if f.name == name)
        c_fld = self.shape_c_type(field)
        dict_t = self.ctx.offset_dict_struct_name(rs.structure)
        val = self.temp(c_fld)
        stored = f"((const {dict_t} *){rec}.dict)->stored_types"
        converted = shape_qval_unwrap(
            f"quest_convert(quest_slot_read({ptr}), {stored}[{index}], {self.descriptor(o.descriptor)})",
            field,
        )
        self.emit(f"if ({stored} != NULL && {stored}[{index}] != NULL) {val} = {converted};")
        self.emit(f"else {val} = {shape_slot_load(f'*{ptr}', field)};")
        return val

    def make_option(self, o: ir.MakeOption, t: QType) -> str:
        """A new option: its tag, and its payload's components (a tuple's read as the represent pass decided, a
        payload that is not a tuple in its slot form)."""
        tag, payload, ordinal, offset = o.tag, o.payload, o.ordinal, o.offset
        os = self.held(t, "option")
        self.types.append(os.structure)
        struct = shape_tag(os)
        tmp = self.temp(f"{struct} *")
        self.emit(f"{tmp} = ({struct} *)quest_alloc(sizeof({struct}));")
        if ordinal is not None:
            # The ordinal counts in the type's cases as written; the tag numbers the shape's, ordered by name
            checked = f"quest_check_option_ordinal_at({self.atom(ordinal)}, {len(os.cases)}LL, {self.site(offset)})"
            tags = [self.tag_index(os, name) for name in o.cases]
            mapped = checked if tags == list(range(len(tags))) else f"{_index_table(tags)}[{checked}]"
            self.emit(f"{tmp}->tag = {mapped};")
            # The payload is stored as the case of a constant ordinal stores it, and otherwise as the first case
            # does, whose components the union overlays on the other cases' (docs/c-representation.md §5)
            n = ordinal.value if isinstance(ordinal, ir.Const) else -1
            tag = o.cases[n] if 0 <= n < len(o.cases) else os.cases[0].name
        else:
            self.emit(f"{tmp}->tag = {self.tag_index(os, tag)}LL;")
        if payload is not None and tag is not None:
            case = os.case(tag)
            pt = case.shape if case is not None else None
            p = self.atom(payload)
            if pt is not None and pt.kind == "tuple":
                ps = shape(self.atom_type(payload))
                for i, _ in enumerate(pt.components):
                    self.emit(f"{tmp}->u.{tag}._{i} = {self.tuple_component(p, ps, i, o.access[i])};")
            else:
                self.emit(f"{tmp}->u.{tag}.val = {p};")
        return tmp

    def option_field(self, src: str, stored_payload: Optional[Shape], index: int, wanted: Shape) -> str:
        """A component of an option's case, read from the case's struct, in the C type of `wanted`."""
        if stored_payload is None or stored_payload.kind != "tuple" or index >= len(stored_payload.components):
            return src
        stored_c = self.slot_c_type(stored_payload.components[index].shape)
        wanted_c = self.slot_c_type(wanted)
        if stored_c == "QVal" and wanted_c != "QVal":
            return shape_qval_to_slot(src, wanted)
        if stored_c.endswith("*") and wanted_c.endswith("*") and stored_c != wanted_c:
            return f"({wanted_c})({src})"
        return src

    def option_case_tuple(self, opt: str, os: Shape, tag: str, tuple_t: QType, offset: int, tag_access: str,
                          access: tuple[str, ...], ordinal: int = 0) -> str:
        """A new tuple of an option's case components (after `offset` components of tuple_t: the case's ordinal),
        read as access says."""
        ts = shape(tuple_t)
        struct = shape_tag(ts)
        self.c_type(tuple_t)
        tmp = self.temp(f"{struct} *")
        self.emit(f"{tmp} = ({struct} *)quest_alloc(sizeof({struct}));")
        case = os.case(tag)
        pt = case.shape if case is not None else None
        if offset:
            self.emit(f"{tmp}->_0 = {ordinal}LL;")
        if pt is not None and pt.kind == "tuple":
            for i, _ in enumerate(pt.components):
                if i + offset < len(ts.components):
                    src = self.option_field(self.option_component(opt, os, tag, i, access[i]), pt, i,
                                            ts.components[i + offset].shape)
                    self.emit(f"{tmp}->_{i + offset} = {src};")
        elif pt is not None:
            self.emit(f"{tmp}->_{offset} = {self.option_component(opt, os, tag, None, access[0])};")
        return tmp

    def payload(self, o: ir.Payload, t: QType) -> str:
        v, tag, offset = o.value, o.tag, o.offset
        ts = self.tag_shape(self.atom_type(v))
        site = self.site(offset)
        index = self.tag_index(ts, tag)
        if ts.kind == "variant":
            self.emit(f"if ({self.atom(v)}.tag != {index}LL) quest_raise_variant_error_at({site});")
            case = ts.case(tag)
            case_s = case.shape if case is not None and case.shape is not None else shape(t)
            return shape_qval_unwrap(f"{self.atom(v)}.payload", case_s)
        self.emit(f"if ({self.option_tag(self.atom(v), o.access)} != {index}LL) quest_raise_variant_error_at({site});")
        return self.option_case_tuple(self.atom(v), ts, tag, t, 1, o.access, o.components, o.ordinal or 0)

    def array_get(self, arr: str, idx: str, elem: Shape) -> str:
        """An element of an array (its QVal form) as a value of its type (a record or variant read from its box)."""
        if self.shape_c_type(elem) == "QVal":
            return f"({arr}->data[{idx}])"
        return shape_qval_unwrap(f"({arr}->data[{idx}])", elem)

    def array_element(self, a: ir.Atom, elem: Shape) -> str:
        """An atom (in its slot form) as an array element of shape elem holds it: its QVal form."""
        return shape_slot_to_qval(self.atom(a), elem)

    def array_slot(self, arr: str, idx: str, elem: Shape, offset: Optional[int]) -> str:
        self.emit(f"quest_check_array_bounds_at({arr}, {idx}, {self.site(offset)});")
        c_elem = shape_location_representation(elem)
        if c_elem == "QVal":
            return f"(&({arr}->data[{idx}]))"
        if elem.kind == "int":
            return f"(&({arr}->data[{idx}].i))"
        if elem.kind == "real":
            return f"(&({arr}->data[{idx}].r))"
        # A Bool or Char in its word's low byte, a pointer in its word
        return f"(({c_elem} *)(&({arr}->data[{idx}])))"

    def make_array(self, elements: list[str], t: QType) -> str:
        n = len(elements)
        arr = self.temp(self.c_type(t))
        self.emit(f"{arr} = (QArray *)quest_alloc(sizeof(QArray) + (size_t)({n}LL) * sizeof(QVal));")
        self.emit(f"{arr}->length = {n}LL;")
        for i, c in enumerate(elements):
            self.emit(f"{arr}->data[{i}LL] = {c};")
        return arr

    def site(self, offset: Optional[int]) -> str:
        """The site of a raise at offset in the unit's file, as a C string ("file:line:col"), or NULL if it is not
        known (docs/exceptions.md §3.3)."""
        source_map = self.unit.source_map
        if offset is None or source_map is None:
            return "NULL"
        loc = source_map.locate(offset)
        return c_string_literal(f"{loc.file_name}:{loc.line}:{loc.column}")

    def prim(self, op: str, args: tuple[ir.Atom, ...], offset: Optional[int] = None, access: str = ir.DIRECT,
             descriptor: Optional[ir.Descriptor] = None) -> str:
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
                return f"({negate}quest_val_is({self.descriptor(descriptor)}, {left}, {right}))"
            t2 = self.atom_type(args[1]) if t is not None else None
            if access == ir.ORIGINAL:
                # A proxy is the object it views
                left, right = f"quest_unproxy({left})", f"quest_unproxy({right})"
            elif t2 is not None and self.c_type(t) != self.c_type(t2) and self.c_type(t).endswith("*"):
                # Pointers to aggregates of different (subtype-related) types: compared as addresses
                left, right = f"(const void *)({left})", f"(const void *)({right})"
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
        descs = [self.descriptor(d) for d in call.descriptors]
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
        s = shape(t)
        while s.kind == "all":
            s = s.body
        return s.kind == "fun"

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
        quants, params, result_t = fun_shape_signature(t)
        with self.auxiliary():
            decls, descs, names = self.thunk_params(len(quants), params)
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
        rec_t = module.record_type
        if rec_t is None:
            raise NotImplementedError(f"module {module.name}: its interface is unknown")
        self.types.append(rec_t)
        field = next(f for f in rec_t.fields if f.name == member)
        field_s = shape(field.type_val)
        c_fld = self.slot_c_type(field_s)
        dict_t = self.ctx.offset_dict_struct_name(rec_t)
        # In its slot form (a record or variant, for a boxed variable)
        return f"(*(({c_fld} *)((char *){record}.val + ((const {dict_t} *){record}.dict)->offset_{member})))"

    def make_closure(self, o: ir.MakeClosure, result: Optional[ir.Var]) -> str:
        code = self.code_name(o.code)
        if not o.captures and not o.type_args:
            return f"(&{code}_closure)"
        env = self.temp(f"struct QEnv_{code} *")
        self.emit(f"{env} = (struct QEnv_{code} *)quest_alloc(sizeof(struct QEnv_{code}));")
        for i, d in enumerate(o.descriptors):
            self.emit(f"{env}->d{i} = {self.descriptor(d)};")
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
        """Assigns a variable (a boxed one, its box: a var or out parameter's location, or a boxed mutable variable's
        own)."""
        if self.is_ok(var.type):
            if value != "Q_OK_VAL":
                self.emit(f"(void)({value});")
            return
        pointer = var.mutable and self.is_pointer_param(var)
        target = f"(*{self.name(var)})" if pointer else self.name(var)
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
            case ir.Assign(var=var, value=value):
                self.assign(var, self.atom(value))
            case ir.Store(value=value, address=address) if address is not None:
                self.emit(f"*{self.atom(address)} = {self.atom(value)};")
            case ir.Store(value=value, base=base, name=name) if name is not None:
                ptr, field = self.record_slot(self.atom(base), self.held(self.atom_type(base), "record"), name)
                self.emit(f"*{ptr} = {self.atom(value)};")
            case ir.Store(value=value, base=base, index=index, access=access) if isinstance(index, int):
                ts = shape(self.atom_type(base))
                component = ts.components[index].shape
                b, v = self.atom(base), self.atom(value)
                if access == ir.ORIGINAL:
                    # Stored into the original as it is
                    self.emit(f"(({self.c_type(ts.type)})quest_unproxy({b}))->_{index} = {v};")
                elif access == ir.PROXY:
                    # A var component of a proxy is the original's
                    self.emit(f"if (quest_is_proxy({b})) quest_proxy_store({b}, {index}, "
                              f"{shape_slot_to_qval(v, component)});")
                    self.emit(f"else {b}->_{index} = {v};")
                else:
                    self.emit(f"{b}->_{index} = {v};")
            case ir.Store(value=value, base=base, index=index, offset=offset):
                arr, idx = self.atom(base), self.atom(index)
                elem = self.element_shape(base)
                self.emit(f"quest_check_array_bounds_at({arr}, {idx}, {self.site(offset)});")
                self.emit(f"{arr}->data[{idx}] = {self.array_element(value, elem)};")
            case ir.Switch(value=value, cases=cases, else_body=else_body, access=access):
                self.switch(value, cases, else_body, access)
            case ir.Inspect(value=value, cases=cases, else_body=else_body, auto_type=auto_t, offset=offset):
                self.inspect(value, cases, else_body, auto_t, offset, s.witness)
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
            case ir.Echo(value=value, type=t, prefix=prefix, descriptor=d):
                self.echo(prefix, self.atom(value), t, d, "" if prefix else f" : {qtype_to_name_str(t)}")
            case ir.EchoText(text=text):
                self.emit(f"puts({c_string_literal(text)});")
            case _:
                raise NotImplementedError(f"C printing of {type(s).__name__}")

    def switch(self, value: ir.Atom, cases, else_body: Optional[ir.Body], access: str) -> None:
        v = self.atom(value)
        t = self.tag_shape(self.atom_type(value))
        is_variant = t.kind == "variant"
        self.types.append(t.structure)
        self.emit(f"switch ({f'{v}.tag' if is_variant else self.option_tag(v, access)}) {{")
        self.indent += 1
        for c in cases:
            for tag in c.tags:
                self.emit(f"case {self.tag_index(t, tag)}LL:")
            self.emit("{")
            self.indent += 1
            if c.binder is not None and not self.is_ok(c.binder.type):
                if is_variant:
                    self.assign(c.binder, qval_unwrap(f"{v}.payload", c.binder.type, self.ctx))
                elif shape(c.binder.type).kind == "tuple":
                    self.assign(c.binder, self.option_case_tuple(v, t, c.tags[0], c.binder.type, 0, access,
                                                                 c.components))
                else:
                    # In its slot form (a record or variant, for a boxed variable)
                    self.assign(c.binder, self.option_component(v, t, c.tags[0], None, c.components[0]))
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
    # witness-independent layout (docs/c-representation.md §8), as the represent pass converted it

    def make_auto(self, witness: ir.Descriptor, auto_t: QAutoType, payload: ir.Atom) -> str:
        stored_t = auto_payload_type(auto_t)
        self.types.extend((auto_t, stored_t))
        return f"quest_auto_new({self.descriptor(witness)}, {qval_wrap(self.atom(payload), stored_t)})"

    def auto_arm_converted(self, arm_plan: ir.InspectArm, stored: str, stored_t, arm_t) -> str:
        """The components S[T] of an auto value, converted by descriptor from the stored ones as the case's arm says
        (the type component's own value to the case's type, or to the bound it is viewed at; a component mentioning
        it from its stored type at the value's type component; the others copied), by the descriptors the describe
        pass gave the arm."""
        arm_struct = tuple_struct_name(arm_t)
        self.types.append(arm_t)
        arm = self.temp(f"{arm_struct} *")
        self.emit(f"{arm} = ({arm_struct} *)quest_alloc(sizeof({arm_struct}));")
        for i, (pair, stored_f, arm_f) in enumerate(zip(arm_plan.descriptors, stored_t.value_fields,
                                                        arm_t.value_fields)):
            src = f"{stored}->_{i}"
            if pair is None:
                self.emit(f"{arm}->_{i} = {src};")
                continue
            from_desc, to_desc = (self.descriptor(d) for d in pair)
            viewed = f"quest_convert({shape_slot_to_qval(src, shape(stored_f.type_val))}, {from_desc}, {to_desc})"
            self.emit(f"{arm}->_{i} = {shape_qval_to_slot(viewed, shape(arm_f.type_val))};")
        return arm

    def inspect(self, value: ir.Atom, cases, else_body: Optional[ir.Body], auto_t: QAutoType,
                offset: Optional[int], witness: Optional[ir.DescriptorParam]) -> None:
        stored_t = auto_payload_type(auto_t)
        stored_struct = tuple_struct_name(stored_t)
        self.types.extend((auto_t, stored_t))
        tgt = self.temp("const QAuto *")
        self.emit(f"{tgt} = {self.atom(value)};")
        if witness is not None:
            # The value's type component, the descriptor variable the arms' descriptors use
            self.names[id(witness.var)] = f"{tgt}->type_desc"
        stored = self.temp(f"{stored_struct} *")
        self.emit(f"{stored} = ({stored_struct} *){tgt}->payload.p;")
        for i, case in enumerate(cases):
            match_desc = self.descriptor(case.descriptor)
            cond = f"quest_is_subtype({tgt}->type_desc, {match_desc})"
            if case.exact:
                cond = f"{cond} && quest_is_subtype({match_desc}, {tgt}->type_desc)"
            self.emit(f"{'if' if i == 0 else '} else if'} ({cond}) {{")
            self.indent += 1
            if case.binders:
                arm_plan = case.arm
                arm_t = auto_payload_type(auto_t, case.match_type)
                if arm_plan.exact:
                    arm_struct = tuple_struct_name(arm_t)
                    self.types.append(arm_t)
                    arm = self.temp(f"{arm_struct} *")
                    self.emit(f"if (quest_layout_equivalent({tgt}->type_desc, {match_desc})) {{")
                    if arm_plan.shared:
                        # The binders share the stored components (and so see updates of var components)
                        self.emit(f"    {arm} = ({arm_struct} *){stored};")
                    else:
                        self.indent += 1
                        p = arm_plan.plan
                        self.emit(f"{arm} = {stored if p is None else self.convert(stored, p)};")
                        self.indent -= 1
                    self.emit("} else {")
                    self.indent += 1
                    if arm_plan.layout_error:
                        self.emit(f"quest_layout_conversion_error({tgt}->type_desc, {match_desc});")
                    converted = self.auto_arm_converted(arm_plan, stored, stored_t, arm_t)
                    self.emit(f"{arm} = {converted};")
                    self.indent -= 1
                    self.emit("}")
                else:
                    arm = self.auto_arm_converted(arm_plan, stored, stored_t, arm_t)
                for b in case.binders:
                    self.assign(b, arm)
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

    def echo(self, prefix: str, value: str, t: QType, descriptor: Optional[ir.Descriptor], suffix: str) -> None:
        """Prints a top-level phrase's value as the interpreter does: by its type's kind, or by the descriptor the
        describe pass gave it (an echo-only one for a closed type with type components, which writes them with their
        alias names)."""
        wrapped = qval_wrap(value, t)
        if kind := echo_value_kind(t):
            self.emit(f"quest_print_value({c_string_literal(prefix)}, {wrapped}, {c_string_literal(kind)}, "
                      f"{c_string_literal(suffix)});")
        else:
            self.emit(f"quest_print_typed({c_string_literal(prefix)}, {wrapped}, {self.descriptor(descriptor)}, "
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
                # A let rec's variable is bound by the let rec and by the let in it that computes its value
                if id(v) in seen or self.is_ok(v.type):
                    continue
                seen.add(id(v))
                c_t = self.var_c_type(v)
                if id(v) in self.fs.volatile:
                    c_t += " volatile"
                decls.append((c_t, self.name(v)))
        return decls

    def volatile_vars(self, body: ir.Body) -> set[int]:
        """The variables a try body assigns, which C must declare volatile for the handler to read them after
        longjmp."""
        found: set[int] = set()
        for s in walk_statements(body, into_functions=False):
            if isinstance(s, ir.Try):
                for t in walk_statements(s.body, into_functions=False):
                    if isinstance(t, ir.Assign):
                        found.add(id(t.var))
        return found

    def function_signature(self, f: ir.Function) -> str:
        count = _type_parameter_count(f.var.type)
        own = f.descriptor_params[len(f.descriptor_params) - count:] if count else ()
        params = ["void *_raw_env"]
        for p in own:
            params.append(f"const QTypeDescriptor *{self.name(p.var)}")
        for v, mode in f.params:
            if mode != "value":
                params.append(f"{self.location_c_type(v.type)} *{self.name(v)}")
            else:
                params.append(f"{'QVal' if self.is_ok(v.type) else self.c_type(v.type)} {self.name(v)}")
        ret = "void" if self.is_ok(f.result_type) else self.c_type(f.result_type)
        return f"static Q_UNUSED {ret} {self.code_name(f)}({', '.join(params)})"

    def function(self, f: ir.Function) -> list[str]:
        self.fs = _FunctionState(f)
        self.fs.volatile = self.volatile_vars(f.body)
        n_captured = len(f.type_params) - _type_parameter_count(f.var.type)
        signature = self.function_signature(f)
        prologue: list[str] = []
        for p in f.descriptor_params[n_captured:]:
            prologue.append(f"(void){self.name(p.var)};")
        if f.env is not None:
            env_struct = f"struct QEnv_{self.code_name(f)}"
            prologue.append(f"{env_struct} *{self.name(f.env)} = ({env_struct} *)_raw_env;")
            # The descriptors of the type parameters its closure supplies
            for i, p in enumerate(f.descriptor_params[:n_captured]):
                d = self.name(p.var)
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
        registered: set[str] = set()
        for table in self.unit.static_data.offset_tables:
            dict_name = self.ctx.offset_dict_instance_name(table.view, table.layout)
            if table.registered is not None and dict_name not in registered:
                registered.add(dict_name)
                view_d, layout_d = (self.descriptor(d) for d in table.registered)
                out.append(f"    quest_register_record_dict({view_d}, {layout_d}, &{dict_name});")
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
        """A module's initializer, whose body makes its record (ir.Module.record), stored in the module's global. A
        module file's is extern, as are its record and its exported functions, and initializes the modules it imports
        first, as a program's main does."""
        clean = mangle_module_name(m.name)
        decls, lines = self.top_level(m.init)
        linkage = "" if m.exports is not None else "static "
        out = [f"{linkage}void qv_mod_{clean}_init(void) {{",
               f"    if (qv_mod_{clean}_initialized) return;",
               f"    qv_mod_{clean}_initialized = true;"]
        out.extend(f"    {c_t} {name};" for c_t, name in decls)
        out.extend(self.abstract_type_registrations(m))
        if m.exports is not None:
            out.append("    qr_register_dicts();")
            out.extend(f"    qv_mod_{mangle_module_name(imp.canonical_path)}_init();" for imp in self.unit.imports)
        out.extend(lines)
        # The record the initializer made last
        out.append(f"    {module_record_ident(clean)} = {self.atom(m.record)};")
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
            args = module_function_arguments(export.type)
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

    def abstract_type_registrations(self, m: ir.Module) -> list[str]:
        """Registers a module's abstract types with their representations, for dynamic values (docs/dynamic.md
        §2.3), as the describe pass listed them (an operator's representation as a template whose holes are its
        parameters); a representation without a descriptor is not registered."""
        lines: list[str] = []
        for global_name, arity, d in m.abstract_types:
            try:
                form = descriptor_form(d.type, self.ctx)
            except MissingDescriptorError:
                continue
            lines.append(f'    quest_register_abstract_type("{global_name}", {arity}, {form.c_expr});')
        return lines

    def import_declarations(self) -> list[str]:
        imports: list[ir.Import] = []
        seen: set[str] = set()
        for imp in self.unit.imports:
            if imp.canonical_path not in seen:
                seen.add(imp.canonical_path)
                imports.append(imp)
        lines = []
        for imp in imports:
            clean = mangle_module_name(imp.canonical_path)
            lines.append(f"extern QRecordVal {module_record_ident(clean)};")
            lines.append(f"extern void qv_mod_{clean}_init(void);")
        lines.extend(self.decl_emitter.emit_precompiled_module_declarations(
            [(imp.canonical_path, imp.record_type) for imp in imports]
        ))
        return lines

    def declarations(self) -> list[str]:
        """The declarations of the types the unit uses: structs, offset tables, descriptors, and adapters."""
        data = self.unit.static_data
        self.types.extend(imp.record_type for imp in self.unit.imports if imp.record_type is not None)
        for table in data.offset_tables:
            self.types.extend((table.view, table.layout))
        decl = CDeclarationEmitter(self.ctx, lambda t: qtype_to_c_type(t, self.ctx))
        self.decl_emitter = decl
        agg_types, _, _ = collect_aggregate_types(list(self.types), self.ctx)
        # The static tables the unit's operations refer to (ir.StaticData), by their C names
        offset_tables = {
            (record_struct_name(t.view, self.ctx), record_struct_name(t.layout, self.ctx)): (t.view, t.layout)
            for t in data.offset_tables
        }
        tag_maps = {(type_tag(t.target), type_tag(t.source)): (t.target, t.source) for t in data.tag_maps}
        lines = []
        lines.extend(decl.emit_forward_typedefs(agg_types))
        lines.extend(decl.emit_aggregate_structs(agg_types))
        lines.extend(decl.emit_evidence_dictionaries(agg_types, list(offset_tables.values())))
        lines.extend(decl.emit_coercion_tables(list(self.tuple_casts.values()), list(tag_maps.values())))
        lines.extend(decl.emit_type_descriptors([d.type for d in data.descriptors if not d.echo],
                                                self.static_descriptor,
                                                [d.type for d in data.descriptors if d.echo],
                                                [name for name, _ in agg_types]))
        lines.extend(decl.emit_fun_type_adapters(decl.emitted_fun_types))
        return lines


def print_c(unit: ir.Unit, env: Any, interface_header: Optional[str] = None) -> str:
    """The C translation of a described unit: a program, or a module file (including its interface's C header,
    if it has one)."""
    return CPrinter(unit, env, interface_header).print_unit()
