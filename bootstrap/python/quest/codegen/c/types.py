"""C spellings for the C backend: the C types of representations (codegen/layout.py), function pointer types, QVal
wrapping and unwrapping, literals, record struct and offset table names, and descriptor expressions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from quest.codegen.descriptors import (
    bound_var_index,
    canonical_auto_type,
    canonical_fun_type,
    hole_index,
    module_abstract_type_name,
)
from quest.codegen.layout import (
    PRINTED_TEXT_LIMIT,
    is_boxed_in_slots,
    shape_location_representation,
    shape_slot_representation,
    option_struct_name,
    printed,
    representation,
    resolved_shape,
    shape_representation,
    text_digest,
    tuple_struct_name,
    type_digest,
    type_tag,
)
from quest.ir.shapes import Shape, shape
from quest.codegen.symbols import mangle_ident
from quest.types import (
    short_type_name,
    QAbstractType,
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
    QExternalType,
    QFunType,
    QOptionType,
    QPathType,
    QPowerKind,
    QRecordType,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QType,
    QTypeApp,
    QTypeFun,
    QTypeVar,
    QVarType,
    QOutType,
    QVariantType,
    unalias,
)


def _opaque_name(t: QType) -> str:
    """The name of an opaque descriptor, by which descriptors are compared: a module abstract type's global name, or
    the type as printed, or for a type that prints longer than PRINTED_TEXT_LIMIT, the start of it followed by the
    digest of the whole."""
    if (global_name := module_abstract_type_name(t)) is not None:
        return global_name
    length, digest = printed(t)
    if length <= PRINTED_TEXT_LIMIT:
        return str(t)
    return f"{short_type_name(t)}#{digest[:16]}"


class MissingDescriptorError(Exception):
    """A type has no runtime type descriptor (such as Var(T) or a type operator)."""


@dataclass(frozen=True)
class DescriptorForm:
    """How a type is described at run time.

    kind is one of base and bound_var (expr is the descriptor expression), or record, tuple, variant, option,
    array, exception, fun, auto, opaque, and hole (the descriptor is quest_type_<tag>, describing `type`; an opaque
    descriptor is compared by `name` and, for an application of an abstract type operator (`type` is a QTypeApp),
    its arguments; a hole's `name` is its index).
    """
    kind: str
    tag: str = ""
    type: Optional[QType] = None
    name: str = ""
    expr: str = ""
    struct: str = ""  # the C struct laid out as `type`, when its name is not derived from `type` itself
    # For a descriptor that only echo uses (echo_descriptor_form): the type as written, with alias names, whose type
    # components the descriptor writes
    display: Optional[QType] = None

    @property
    def c_expr(self) -> str:
        return self.expr if self.expr else f"(&quest_type_{self.tag})"


_BASE_DESCRIPTORS = {
    "int": "&quest_type_Int", "real": "&quest_type_Real", "bool": "&quest_type_Bool", "char": "&quest_type_Char",
    "string": "&quest_type_String", "ok": "&quest_type_Ok",
}


def descriptor_form(t: QType, ctx: Optional["RecordNamingContext"] = None) -> DescriptorForm:
    """Decides the runtime descriptor of a closed type (type parameters in scope are the printer's business).

    Each distinct type gets its own tag: tags of compound types include a digest of the type, because C tags
    conflate types with the same representation (every closure is a QClosure, every type variable a QVal).
    Recursive types are described by their unfoldings, which refer back to them by tag, so their descriptors are
    cyclic. Raises MissingDescriptorError for types that have none.
    """
    s = shape(t)
    if (index := hole_index(s.type)) is not None:
        # A template's hole (described as such, not by the bound a bounded type variable resolves to)
        bound = s.type.bound
        tag = f"hole_{index}_{type_digest(bound.bound)}" if isinstance(bound, QPowerKind) else f"hole_{index}"
        return DescriptorForm("hole", tag=tag, type=s.type, name=str(index))
    # Equal types share a descriptor: a type is described by its shape's structure, the unfolding of its canonical
    # form (in which equal types containing recursion are one type)
    t = s.structure
    if s.kind in _BASE_DESCRIPTORS:
        return DescriptorForm("base", expr=_BASE_DESCRIPTORS[s.kind])
    if s.kind == "word":
        return DescriptorForm("base", expr="&quest_type_Word")
    if (index := bound_var_index(t)) is not None:
        return DescriptorForm("bound_var", expr=f"(&quest_type_bound_vars[{index}])")
    if isinstance(t, QTupleType) and not t.fields:
        return DescriptorForm("base", expr="&quest_type_EmptyTuple")
    if (
        isinstance(t, QTypeVar)
        and isinstance(t.bound, QPowerKind)
        and (global_name := module_abstract_type_name(t)) is not None
    ):
        # A module's abstract type with a bound: opaque, and held outside the module in the representation of its
        # bound, viewed at the bound (a stored descriptor, as for a bounded type parameter)
        return DescriptorForm("stored", tag=f"stored_{text_digest(global_name)}", name=global_name, type=t)
    # A type variable bounded by a record, variant, or option type is described by its bound
    held = resolved_shape(s)
    if held.kind == "record":
        rec_t = held.structure
        return DescriptorForm("record", tag=record_struct_name(rec_t, ctx), type=rec_t)
    if s.kind == "tuple":
        return DescriptorForm("tuple", tag=f"{tuple_struct_name(t)}_{type_digest(t)}", type=t)
    if held.kind == "variant":
        var_t = held.structure
        return DescriptorForm("variant", tag=f"{type_tag(var_t)}_{type_digest(var_t)}", type=var_t)
    if held.kind == "option":
        opt_t = held.structure
        return DescriptorForm(
            "option",
            tag=f"{option_struct_name(opt_t)}_{type_digest(opt_t)}",
            type=opt_t,
            struct=option_struct_name(opt_t),
        )
    if isinstance(t, QTypeApp):
        # An application of an abstract type operator (list.T(Int)): opaque, compared by the operator's name and the
        # arguments
        name = _opaque_name(t.constructor)
        return DescriptorForm("opaque", tag=f"opaque_{type_digest(t)}", name=name, type=t)
    if isinstance(t, QArrayType):
        return DescriptorForm("array", tag=f"array_{type_digest(t)}", type=t)
    if isinstance(t, QExceptionType):
        return DescriptorForm("exception", tag=f"exception_{type_digest(t)}", type=t)
    if isinstance(t, (QFunType, QAllType)):
        canonical = canonical_fun_type(t)
        return DescriptorForm("fun", tag=f"fun_{type_digest(canonical)}", type=canonical)
    if isinstance(t, QExternalType):
        name = t.name or t.c_type
        return DescriptorForm("opaque", tag=f"opaque_{mangle_ident(name)}", name=name)
    if (global_name := module_abstract_type_name(t)) is not None:
        return DescriptorForm("opaque", tag=f"opaque_{text_digest(global_name)}", name=global_name)
    if isinstance(t, (QTypeVar, QAbstractType)):
        return DescriptorForm("opaque", tag=f"opaque_{mangle_ident(t.name)}", name=t.name)
    if isinstance(t, QPathType):
        # An abstract type of a package value (t.A): opaque, and distinct for each binding of t
        name = f"{t.root_name}.{t.field_name}#{t.root_symbol_id}"
        return DescriptorForm("opaque", tag=f"opaque_{text_digest(name)}", name=name)
    if isinstance(t, QAutoType):
        canonical = canonical_auto_type(t)
        return DescriptorForm("auto", tag=f"auto_{type_digest(canonical)}", type=canonical)
    if isinstance(t, (QVarType, QOutType)):
        # The type of a var or out parameter: described by its element type
        return descriptor_form(t.element_type, ctx)
    if isinstance(t, QTypeFun):
        # A type operator, passed for a higher-kinded type parameter: opaque, compared by name
        name = _opaque_name(t)
        return DescriptorForm("opaque", tag=f"opaque_{text_digest(name)}", name=name)
    raise MissingDescriptorError(f"no runtime type descriptor for type '{t}'")


def record_struct_name(t: QRecordType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Returns the C struct tag name for a given QRecordType."""
    if ctx is not None:
        name = ctx.get_or_create_name(t)
        return f"QT_{name}"
    return type_tag(t)


class RecordNamingContext:
    """Names record types and evidence dictionaries in C, after a type alias for the record where there is one.

    Every name ends with a digest of the record's shape, so a name stands for one layout in every C unit: the generated
    headers of interfaces define record structs under include guards named after them, and a unit includes headers
    whose records were named in other compilations.
    """

    def __init__(self) -> None:
        self.alias_by_shape: dict[tuple[tuple[str, str, str], ...], str] = {}
        self.shape_to_canonical_name: dict[tuple[tuple[str, str, str], ...], str] = {}

    def _shape_key(self, t: QRecordType) -> tuple[tuple[str, str, str], ...]:
        # Records share a struct (and so a descriptor) only if their fields have the same types, not merely the same
        # C representations: type_tag is QClosure for every function type and QVal for every type variable. The
        # fields are those of the record's shape (the structure of its canonical form), so that a record type is
        # named alike however it is written.
        s = shape(t)
        fields = s.structure.fields if s.kind == "record" else t.fields
        sorted_fields = sorted(fields, key=lambda f: f.name)
        return tuple((f.name, type_tag(f.type_val), type_digest(f.type_val)) for f in sorted_fields)

    @staticmethod
    def _shape_digest(key: tuple[tuple[str, str, str], ...]) -> str:
        return text_digest(repr(key))

    def register_alias(self, alias_name: str, t: QRecordType) -> None:
        key = self._shape_key(t)
        if key not in self.alias_by_shape:
            name = f"{alias_name}_{self._shape_digest(key)}"
            self.alias_by_shape[key] = name
            self.shape_to_canonical_name[key] = name

    def get_or_create_name(self, t: QRecordType) -> str:
        key = self._shape_key(t)
        if key not in self.shape_to_canonical_name:
            self.shape_to_canonical_name[key] = f"record_{self._shape_digest(key)}"
        return self.shape_to_canonical_name[key]

    def record_struct_name(self, t: QRecordType) -> str:
        name = self.get_or_create_name(t)
        return f"QT_{name}"

    def offset_dict_struct_name(self, t: QRecordType) -> str:
        name = self.get_or_create_name(t)
        return f"OffsetDict_{name}"

    def offset_dict_instance_name(self, target: QRecordType, source: QRecordType) -> str:
        tgt_name = self.get_or_create_name(target)
        src_name = self.get_or_create_name(source)
        return f"offsetdict_{tgt_name}_{src_name}"


def qtype_to_c_type(t: QType, ctx: Optional[RecordNamingContext] = None) -> str:
    """The C type of a value of t: its representation (codegen/layout.py), which is named by the runtime's C type."""
    return representation(t)


def c_string_literal(s: str) -> str:
    """Escapes a Python string into a safe C string literal."""
    parts = []
    for ch in s:
        if ch == "\"":
            parts.append("\\\"")
        elif ch == "\\":
            parts.append("\\\\")
        elif ch == "\n":
            parts.append("\\n")
        elif ch == "\t":
            parts.append("\\t")
        elif ch == "\r":
            parts.append("\\r")
        elif 32 <= ord(ch) < 127:
            parts.append(ch)
        else:
            parts.append(f"\\x{ord(ch):02x}")
    return "\"" + "".join(parts) + "\""


def c_char_literal(ch: str) -> str:
    """Escapes a single Python character into a C char literal."""
    if ch == "\'":
        return "'\\''"
    if ch == "\\":
        return "'\\\\'"
    if ch == "\n":
        return "'\\n'"
    if ch == "\t":
        return "'\\t'"
    if ch == "\r":
        return "'\\r'"
    if 32 <= ord(ch) < 127:
        return f"'{ch}'"
    return f"'\\x{ord(ch):02x}'"


def qval_wrap(expr_str: str, t: QType) -> str:
    """Wraps a scalar or pointer expression into a QVal union initializer."""
    return shape_qval_wrap(expr_str, shape(t))


def shape_qval_wrap(expr_str: str, s: Shape) -> str:
    """Wraps a scalar or pointer expression of shape s into a QVal union initializer (a value of a bounded type
    parameter is a value of its bound)."""
    s = resolved_shape(s)
    kind = s.kind
    if shape_representation(s) == "QVal":
        return expr_str
    if kind == "ok":
        return "Q_OK_VAL"
    if kind == "record":
        return f"((QVal){{ .p = (void *)quest_record_box({expr_str}) }})"
    if kind == "variant":
        return f"((QVal){{ .p = (void *)quest_variant_box({expr_str}) }})"
    if kind == "word":
        return f"((QVal){{ .u = (uint64_t)({expr_str}) }})"
    if kind in ("int", "bool", "char"):
        return f"((QVal){{ .i = (int64_t)({expr_str}) }})"
    if kind == "real":
        return f"((QVal){{ .r = (double)({expr_str}) }})"
    return f"((QVal){{ .p = (void *)({expr_str}) }})"


def qval_unwrap(qval_expr: str, t: QType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Extracts the underlying concrete scalar or pointer from a QVal expression."""
    return shape_qval_unwrap(qval_expr, shape(t))


def shape_qval_unwrap(qval_expr: str, s: Shape) -> str:
    """Extracts the underlying concrete scalar or pointer of shape s from a QVal expression (a value of a bounded
    type parameter is a value of its bound)."""
    s = resolved_shape(s)
    kind = s.kind
    c_t = shape_representation(s)
    if c_t == "QVal":
        return qval_expr
    if kind == "record":
        return f"(*((QRecordVal *)({qval_expr}.p)))"
    if kind == "variant":
        return f"(*((QVariantVal *)({qval_expr}.p)))"
    if kind == "word":
        return f"({qval_expr}.u)"
    if kind in ("int", "bool", "char"):
        return f"({qval_expr}.i)"
    if kind == "real":
        return f"({qval_expr}.r)"
    if kind == "ok":
        return "((void)0)"
    return f"(({c_t})({qval_expr}.p))"


def shape_slot_load(slot_expr: str, s: Shape) -> str:
    """The value of shape s held in a slot (slot_representation): a record or variant read from its box, a Bool or
    Char narrowed from its word (implicitly), anything else as it is."""
    if is_boxed_in_slots(s):
        return f"(*({slot_expr}))"
    return slot_expr


def shape_slot_store(expr: str, s: Shape) -> str:
    """A value of shape s in the form a slot holds it: a record or variant in a new box."""
    if is_boxed_in_slots(s):
        box = "quest_record_box" if shape_representation(s) == "QRecordVal" else "quest_variant_box"
        return f"{box}({expr})"
    return expr


def shape_slot_to_qval(slot_expr: str, s: Shape) -> str:
    """The QVal form of the slot contents of a value of shape s (a box is its QVal form)."""
    slot_c = shape_slot_representation(s)
    if slot_c == "QVal":
        return slot_expr
    if is_boxed_in_slots(s):
        return f"((QVal){{ .p = (void *)({slot_expr}) }})"
    return shape_qval_wrap(slot_expr, s)


def shape_qval_to_slot(qval_expr: str, s: Shape) -> str:
    """The slot contents of a value of shape s from its QVal form (a box is its QVal form)."""
    slot_c = shape_slot_representation(s)
    if slot_c == "QVal":
        return qval_expr
    if is_boxed_in_slots(s):
        return f"(({slot_c})({qval_expr}.p))"
    return shape_qval_unwrap(qval_expr, s)


def closure_fn_ptr_type(fun_type: QType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Constructs the C function pointer cast type for invoking a closure: its environment, its type parameters'
    descriptors, and its parameters (a recursive function type is called as its unfolding is)."""
    s = shape(fun_type)
    param_types = ["void *"]
    while s.kind == "all":
        # Quantifier descriptors appear immediately after env
        param_types.extend("const QTypeDescriptor *" for _ in s.type_params)
        s = s.body
    if s.kind != "fun":
        return f"{shape_representation(s)} (*)({', '.join(param_types)})"
    for p in s.params:
        if p.mode != "value":
            param_types.append(f"{shape_location_representation(p.shape)} *")
        elif p.shape.kind == "ok":
            param_types.append("QVal")
        else:
            param_types.append(shape_representation(p.shape))
    return f"{shape_representation(s.result)} (*)({', '.join(param_types)})"


def tuple_type_components(t: QTupleType) -> list[tuple[int, str]]:
    """A tuple type's type components as echo writes them, as the interpreter does (_format_aggregate), each with
    the number of value elements before it."""
    components: list[tuple[int, str]] = []
    position = 0
    for comp in t.components:
        if isinstance(comp, QTupleTypeFormal):
            components.append((position, f"<Hidden>::{comp.bound}"))
        elif isinstance(comp, QTupleTypeBinding):
            components.append((position, f"Let {comp.name} = {comp.type_val}"))
        else:
            position += 1
    return components


def _echo_head(t: QType) -> QType:
    return unalias(t.prune() if hasattr(t, "prune") else t)


def echo_children(t: QType) -> dict[str, QType]:
    """The types of the parts of a value of type t that echo writes through descriptors of their own, keyed as the
    emitted descriptor of t refers to them: a tuple's value elements by index, a record's fields, options', and
    variants' cases by name, and an array's elements by "". A recursive type or a type application has none here:
    its unfolding is described by its shared descriptor."""
    t = _echo_head(t)
    if isinstance(t, QTupleType):
        return {str(i): f.type_val for i, f in enumerate(t.value_fields)}
    if isinstance(t, QRecordType):
        return {f.name: f.type_val for f in t.fields}
    if isinstance(t, QArrayType):
        return {"": t.element_type}
    if isinstance(t, QOptionType):
        return {o.name: o.payload_type for o in t.options if o.payload_type is not None}
    if isinstance(t, QVariantType):
        return {v.name: v.type_val for v in t.variants if v.type_val is not None}
    return {}


def _echo_key(t: QType) -> Optional[str]:
    """What tells apart the echo-only descriptors of t: the type components that echo writes for it and its parts,
    with their alias names, or None if it writes none (and t's shared descriptor will do)."""
    head = _echo_head(t)
    own = tuple_type_components(head) if isinstance(head, QTupleType) else []
    parts = [(name, _echo_key(child)) for name, child in echo_children(head).items()]
    if not own and all(key is None for _, key in parts):
        return None
    return repr((type(head).__name__, own, parts))


def echo_descriptor_form(t: QType, ctx: Optional["RecordNamingContext"] = None) -> Optional[DescriptorForm]:
    """The descriptor echo writes a value of the closed type t by, when t's shared descriptor would leave out type
    components (which only echo writes) or write them without their alias names, or None.

    Descriptors are shared by types equal but for alias names (descriptor_form), but echo writes type components as
    the interpreter does, with alias names (Let N = P, not Let N = Tuple a: Int end), so it uses descriptors of its
    own: copies of the shared ones, laid out the same, told apart by the components' text."""
    key = _echo_key(t)
    if key is None:
        return None
    form = descriptor_form(t, ctx)
    if form.kind not in ("tuple", "record", "array", "option", "variant"):
        return None
    # A record's tag names its struct too, which the copy keeps
    struct = form.struct or (form.tag if form.kind == "record" else "")
    return replace(form, tag=f"{form.tag}_echo_{text_digest(key)}", struct=struct, display=_echo_head(t))
