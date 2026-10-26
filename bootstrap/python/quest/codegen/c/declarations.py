"""The declarations of the C the IR's printer writes (c/printer.py) and of
interfaces' C headers (c/headers.py): aggregate structs, offset tables, coercion
tables, type descriptors, function type adapters, and modules' exported
functions."""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from quest.ir.slots import may_be_stored_as_subtype
from quest.ir.shapes import Shape, shape
from quest.ir.written import echo_children, fun_signature, quantified, tuple_type_components
from quest.codegen.syntax import c_int, c_int_literal, c_string, call, comma
from quest.codegen.c.types import (
    closure_fn_ptr_type,
    descriptor_form,
    DescriptorForm,
    echo_descriptor_form,
    MissingDescriptorError,
    qval_unwrap,
    qval_wrap,
    record_struct_name,
    RecordNamingContext,
)
from quest.codegen.descriptors import fun_descriptor_tag
from quest.codegen.layout import (
    location_representation,
    option_struct_name,
    resolved_shape,
    shape_tag,
    slot_representation,
    tuple_struct_name,
    type_tag,
)
from quest.codegen.symbols import mangle_ident, mangle_module_ident, mangle_module_name, module_record_ident
from quest.types import (
    auto_payload_type,
    BOOL_TYPE,
    CHAR_TYPE,
    INT_TYPE,
    OK_TYPE,
    QAbstractType,
    QAllType,
    QArrayType,
    QAutoType,
    QExternalType,
    QFunType,
    QOptionType,
    QParam,
    QPowerKind,
    QQuantifier,
    QRecGroupType,
    QRecordField,
    QRecordType,
    QRecType,
    QTupleType,
    QType,
    QTypeApp,
    QTypeVar,
    QVariantType,
    REAL_TYPE,
    short_type_name,
    STRING_TYPE,
    type_fields,
)


def module_function_signature(
    clean_mod: str, name: str, type_val: QType, c_type: Callable[[QType], str]
) -> Optional[tuple[str, str, list[str]]]:
    """The C function a module file exports for a member of its interface that
    is a function or a polymorphic value (`qv_<module>_<member>`, taking its
    type parameters' descriptors and then its parameters, at the interface's
    types): its result's C type, its name, and its parameters' declarations;
    None for other members. The type parameters' and parameters' names are the
    interface's, as written."""
    quants, fun_t = quantified(type_val)
    if not isinstance(fun_t, QFunType) and not quants:
        return None
    params, ret_type = fun_signature(type_val)
    ret_kind = shape(ret_type).kind
    ret_c = "void" if ret_kind == "ok" else ("QRecordVal" if ret_kind == "record" else c_type(ret_type))
    param_decls = [f"const QTypeDescriptor *descriptor_{q.name}" for q in quants]
    param_decls += [
        f"{location_representation(p.type_val)} *qv_p_{p.name}" if p.is_out or p.is_var
        else f"{c_type(p.type_val)} qv_p_{p.name}" for p in params
    ]
    return ret_c, mangle_module_ident(clean_mod, name), param_decls


def module_function_arguments(type_val: QType) -> list[str]:
    """The names of the parameters module_function_signature declares, in
    order."""
    quants, _ = quantified(type_val)
    params, _ = fun_signature(type_val)
    return [f"descriptor_{q.name}" for q in quants] + [f"qv_p_{p.name}" for p in params]


def fun_shape_signature(t: QType) -> tuple[tuple[Optional[QType], ...], tuple[QParam, ...], QType]:
    """A (possibly polymorphic) function type's signature, from its shape: the
    POWER bounds of its type parameters (None for a parameter without one), its
    parameters, and its result type (the types of its shape's parts). Their type
    parameters are its canonical form's, which only descriptors (of the de
    Bruijn forms that name type parameters by position, canonical_fun_type) and
    representations, which do not depend on them, read here."""
    s = shape(t)
    bounds: list[Optional[QType]] = []
    while s.kind == "all":
        bounds.extend(tp.bound.type if tp.bound is not None else None for tp in s.type_params)
        s = s.body
    if s.kind != "fun":
        return tuple(bounds), (), s.type
    params = tuple(
        QParam(name=p.name, type_val=p.shape.type, is_var=p.mode == "var", is_out=p.mode == "out") for p in s.params
    )
    return tuple(bounds), params, s.result.type


def collect_aggregate_types(
    node: Any,
    ctx: RecordNamingContext,
    visited_names: Optional[set[str]] = None,
    visited_type_ids: Optional[set[int]] = None,
    visited_node_ids: Optional[set[int]] = None,
) -> tuple[list[tuple[str, QType]], list[QVariantType], list[QType]]:
    """Traverses an AST (or a list of types) to find all unique aggregate types
    (tuples, records, options, variants), from their shapes: each as its shape's
    structure, the unfolding of its canonical form, which its struct and
    descriptor declare, in the order first reached (which interfaces' C headers
    pin, tests/abi)."""
    if visited_names is None:
        visited_names = set()
    if visited_type_ids is None:
        visited_type_ids = set()
    if visited_node_ids is None:
        visited_node_ids = set()
    result: list[tuple[str, QType]] = []
    variant_types: list[QVariantType] = []
    variant_shapes: list[Shape] = []
    all_types: list[QType] = []
    visited_shape_ids: set[int] = set()

    def visit_type(t: Optional[QType]) -> None:
        if t is None:
            return
        if id(t) in visited_type_ids:
            return
        visited_type_ids.add(id(t))
        try:
            s = shape(t)
        except ValueError:
            return
        visit_shape(s)

    def visit_shape(s: Optional[Shape]) -> None:
        # Shapes, not types as written: equal types (however written, with
        # whatever aliases) share one shape, whose structure (the unfolding of
        # its canonical form) declares the struct, and records are named from it
        if s is None or id(s) in visited_shape_ids:
            return
        visited_shape_ids.add(id(s))
        t = s.structure
        all_types.append(t)
        held = resolved_shape(s)
        if s.kind == "tuple":
            for c in s.components:
                visit_shape(c.shape)
            add(shape_tag(s), t)
        elif s.kind == "record":
            for c in s.components:
                visit_shape(c.shape)
            add(record_struct_name(t, ctx), t)
        elif held.kind == "option":
            # An option, or a type parameter bounded by one, whose values are
            # held in the bound's representation
            for c in held.cases:
                visit_shape(c.shape)
            add(shape_tag(held), held.structure)
        elif s.kind == "auto":
            # Auto payloads are stored in the witness-independent layout
            visit_type(auto_payload_type(t))
        elif s.kind == "variant":
            if not any(id(v) == id(s) for v in variant_shapes):
                variant_shapes.append(s)
                variant_types.append(t)
            for c in s.cases:
                visit_shape(c.shape)
        else:
            for child in s.children():
                visit_shape(child)
        if s.kind in ("typevar", "abstract") and s.bound is not None:
            visit_shape(s.bound)

    def add(name: str, t: QType) -> None:
        if name not in visited_names:
            visited_names.add(name)
            result.append((name, t))

    def visit_node(n: Any) -> None:
        if n is None:
            return
        n_id = id(n)
        if n_id in visited_node_ids:
            return
        visited_node_ids.add(n_id)
        if isinstance(n, QType):
            visit_type(n)
        if isinstance(n, (list, tuple)):
            for item in n:
                visit_node(item)
            return

        # A recursive type's bodies mention its variables free; visit_type has
        # visited its unfolding
        if isinstance(n, (QRecType, QRecGroupType)):
            return

        for part in type_fields(n) or ():
            visit_node(part)

    visit_node(node)
    return result, variant_types, all_types


class CDeclarationEmitter:
    """Emits forward declarations, structs, typedefs, evidence dictionaries, and
    trampolines."""

    def __init__(self, record_ctx: RecordNamingContext, c_type_fn: Callable[[QType], str]):
        self.record_ctx = record_ctx
        self.c_type = c_type_fn
        self.emitted_descriptor_tags: list[str] = []
        # Function types with descriptors, whose adapters (quest_adapt_<tag>)
        # emit_fun_type_adapters defines
        self.emitted_fun_types: list[tuple[str, QFunType]] = []

    def emit_forward_typedefs(self, agg_types: list[tuple[str, QType]]) -> list[str]:
        lines: list[str] = []
        if agg_types:
            lines.append("/* Forward declarations for aggregate types */")
            seen: set[str] = set()
            for tag_name, _ in agg_types:
                if tag_name not in seen:
                    seen.add(tag_name)
                    lines.append(f"#ifndef QUEST_TYPE_{tag_name}_TYPEDEF")
                    lines.append(f"#define QUEST_TYPE_{tag_name}_TYPEDEF")
                    lines.append(f"typedef struct {tag_name} {tag_name};")
                    lines.append("#endif")
            lines.append("")
        return lines

    def emit_precompiled_module_declarations(self, modules: list[tuple[str, Optional[QType]]]) -> list[str]:
        """The extern declarations of the functions modules compiled on their
        own export, for each module by its canonical name and the record type of
        its interface (ir.Import.record_type)."""
        lines: list[str] = []
        if modules:
            lines.append("/* External declarations for precompiled module functions */")
            for name, record_t in modules:
                clean_mod = mangle_module_name(name)
                for f in record_t.fields if record_t is not None else ():
                    sig = module_function_signature(clean_mod, f.name, f.type_val, self.c_type)
                    if sig is not None:
                        ret_c, m_ident, param_decls = sig
                        lines.append(f"extern {ret_c} {call(m_ident, param_decls or ['void'])};")
            lines.append("")
        return lines

    def emit_aggregate_structs(self, agg_types: list[tuple[str, QType]]) -> list[str]:
        lines: list[str] = []
        if not agg_types:
            return lines

        lines.append("/* Aggregate struct definitions */")
        seen: set[str] = set()
        for tag_name, t in agg_types:
            if tag_name in seen:
                continue
            seen.add(tag_name)
            lines.append(f"#ifndef QUEST_TYPE_{tag_name}_DEFINED")
            lines.append(f"#define QUEST_TYPE_{tag_name}_DEFINED")
            lines.append(f"struct {tag_name} {{")
            match t:
                case QTupleType(value_fields=value_fields):
                    if not value_fields:
                        lines.append("    char _unused;")
                    else:
                        for i, f in enumerate(value_fields):
                            lines.append(f"    {slot_representation(f.type_val)} _{c_int(i)};")
                case QRecordType(fields=fields):
                    lines.append("    QRecordHeader header;")
                    if not fields:
                        lines.append("    char _unused;")
                    else:
                        for f in sorted(fields, key=lambda fld: fld.name):
                            lines.append(f"    {slot_representation(f.type_val)} qf_{f.name};")
                case QOptionType(options=options):
                    lines.append("    int64_t tag;")
                    payload_branches = [o for o in options if o.payload_type is not None]
                    if payload_branches:
                        lines.append("    union {")
                        for o in payload_branches:
                            # A case's payload is a tuple, whose shape gives its
                            # components (in a canonical form, it may be written
                            # as a recursive type)
                            payload = shape(o.payload_type)
                            if payload.kind in ("tuple", "record"):
                                lines.append(f"        struct {tag_name}_{o.name}_payload {{")
                                if payload.kind == "tuple":
                                    for i, c in enumerate(payload.components):
                                        lines.append(f"            {slot_representation(c.shape.type)} _{c_int(i)};")
                                else:
                                    for c in payload.sorted_components():
                                        lines.append(f"            {slot_representation(c.shape.type)} qf_{c.name};")
                                lines.append(f"        }} {o.name};")
                            else:
                                lines.append(f"        struct {{ {slot_representation(o.payload_type)} val; }} {o.name};")
                        lines.append("    } u;")
            lines.append("};")
            lines.append("#endif")
            lines.append("")
        return lines

    def emit_evidence_dictionaries(
        self,
        agg_types: list[tuple[str, QType]],
        needed_dicts: Sequence[tuple[QRecordType, QRecordType]],
    ) -> list[str]:
        lines: list[str] = []
        all_records = [t for _, t in agg_types if isinstance(t, QRecordType)]
        if all_records:
            lines.append("/* Evidence dictionary struct definitions */")
            for t in all_records:
                dict_t = self.record_ctx.offset_dict_struct_name(t)
                rec_name = self.record_ctx.get_or_create_name(t)
                lines.append(f"typedef struct {dict_t} {dict_t};")
                lines.append(f"struct {dict_t} {{")
                if not t.fields:
                    lines.append("    size_t _unused;")
                else:
                    for f in sorted(t.fields, key=lambda fld: fld.name):
                        lines.append(f"    size_t offset_{f.name};")
                lines.append("    QRecordStoredTypes stored_types;")
                lines.append("};")

            lines.append("")

        if needed_dicts:
            lines.append("/* Static evidence dictionaries for record subtyping */")
            for tgt, src in sorted(
                needed_dicts,
                key=lambda p: (
                    self.record_ctx.get_or_create_name(p[0]),
                    self.record_ctx.get_or_create_name(p[1]),
                ),
            ):
                inst_name = self.record_ctx.offset_dict_instance_name(tgt, src)
                dict_t = self.record_ctx.offset_dict_struct_name(tgt)
                src_sname = record_struct_name(src, self.record_ctx)
                # Static tables only relate records whose shared fields have
                # equal types, so no field is stored at a different type
                # (stored_types is NULL)
                if not tgt.fields:
                    lines.append(f"static const {dict_t} {inst_name} = {{ 0, NULL }};")
                else:
                    entries = [
                        f"offsetof({src_sname}, qf_{f.name})"
                        for f in sorted(tgt.fields, key=lambda fld: fld.name)
                    ]
                    lines.append(f"static const {dict_t} {inst_name} = {{ {comma(entries)}, NULL }};")
            lines.append("")
        return lines

    def emit_coercion_tables(
        self,
        tuple_coercions: Sequence[tuple[QTupleType, QTupleType]],
        variant_coercions: Sequence[tuple[QVariantType, QVariantType]],
    ) -> list[str]:
        lines: list[str] = []
        if tuple_coercions:
            lines.append("/* Compile-time static assertions for tuple subtyping */")
            for tgt, src in sorted(
                tuple_coercions,
                key=lambda p: (tuple_struct_name(p[0]), tuple_struct_name(p[1])),
            ):
                tgt_name = tuple_struct_name(tgt)
                src_name = tuple_struct_name(src)
                for i in range(len(tgt.value_fields)):
                    lines.append(
                        f"static_assert(offsetof({src_name}, _{c_int(i)}) == offsetof({tgt_name}, _{c_int(i)}), "
                        f"tuple_coercion_{tgt_name}_{src_name}_{c_int(i)});"
                    )
            lines.append("")

        if variant_coercions:
            lines.append("/* Static tag remapping tables for variant subtyping */")
            for tgt, src in sorted(
                variant_coercions,
                key=lambda p: (type_tag(p[0]), type_tag(p[1])),
            ):
                tgt_tag = type_tag(tgt)
                src_tag = type_tag(src)
                entries = [
                    c_int(next(j for j, tv in enumerate(tgt.variants) if tv.name == sv.name))
                    for sv in src.variants
                ]
                lines.append(
                    f"static const int64_t tagmap_{tgt_tag}_{src_tag}[{c_int(len(src.variants))}] = "
                    f"{{ {comma(entries)} }};"
                )
            lines.append("")
        return lines

    def emit_type_descriptors(
        self,
        types: Sequence[QType],
        desc_fn: Callable[[QType], str],
        echo_types: Sequence[QType] = (),
        defined_structs: Sequence[str] = (),
    ) -> list[str]:
        """Emits the static descriptors of types (see descriptor_form; templates
        among them) and those that echo uses for echo_types (see
        echo_descriptor_form), each with the descriptors of its parts, for those
        that have one.

        desc_fn gives the static descriptor expression of a part's type. A later
        call emits only descriptors (and structs) that earlier calls did not;
        defined_structs are the structs already defined.
        """
        lines: list[str] = []
        forms: dict[str, list[DescriptorForm]] = {}
        emitted_before: set[str] = self.__dict__.setdefault("_emitted_descriptor_tag_set", set())
        seen_tags: set[str] = set()

        def visit(t: Optional[QType]) -> None:
            if t is None:
                return
            try:
                form = descriptor_form(t, self.record_ctx)
            except MissingDescriptorError:
                return
            if form.kind in ("base", "bound_var") or form.tag in seen_tags or form.tag in emitted_before:
                return
            seen_tags.add(form.tag)
            forms.setdefault(form.kind, []).append(form)
            dt = form.type
            if form.kind == "record":
                for f in dt.fields:
                    visit(f.type_val)
            elif form.kind == "tuple":
                for f in dt.value_fields:
                    visit(f.type_val)
            elif form.kind == "variant":
                for v in dt.variants:
                    visit(v.type_val)
            elif form.kind == "option":
                for o in dt.options:
                    visit(o.payload_type)
            elif form.kind == "array":
                visit(dt.element_type)
            elif form.kind == "exception":
                visit(dt.payload_type)
            elif form.kind == "hole":
                if isinstance(dt.bound, QPowerKind):
                    visit(dt.bound.bound)
            elif form.kind == "stored":
                visit(dt.bound.bound)
            elif form.kind == "opaque" and isinstance(dt, QTypeApp):
                for a in dt.arguments:
                    visit(a)
            elif form.kind == "auto":
                if isinstance(dt.kind_bound, QPowerKind):
                    visit(dt.kind_bound.bound)
                for f in dt.signature:
                    visit(f.type_val)
            elif form.kind == "fun":
                bounds, params, result_t = fun_shape_signature(dt)
                for bound in bounds:
                    visit(bound)
                for prm in params:
                    visit(prm.type_val)
                visit(result_t)

        def visit_echo(t: QType) -> None:
            # An echo-only descriptor, and those of its parts (echo-only too
            # where they write type components)
            visit(t)
            form = echo_descriptor_form(t, self.record_ctx)
            if form is None or form.tag in seen_tags or form.tag in emitted_before:
                return
            seen_tags.add(form.tag)
            forms.setdefault(form.kind, []).append(form)
            for child in echo_children(form.display).values():
                visit_echo(child)

        for t in types:
            visit(t)
        for t in echo_types:
            visit_echo(t)

        funs = [(f.tag, f.type) for f in forms.get("fun", [])]
        self.emitted_fun_types = funs
        if not seen_tags:
            return lines
        emitted_before.update(seen_tags)

        # Descriptors of unfolded recursive types may name tuple, record, and
        # option structs that the program's own types do not (a recursive
        # occurrence is named by its unfolding rather than as QVal, and a type
        # reached only as the argument of an opaque type has no values in the
        # program); their layouts are the same, but the structs must be defined
        # for offsetof and sizeof
        defined: set[str] = self.__dict__.setdefault("_defined_struct_names", set())
        defined.update(defined_structs)
        missing: list[tuple[str, QType]] = []
        for form in forms.get("tuple", []):
            struct_name = tuple_struct_name(form.type)
            if struct_name not in defined:
                defined.add(struct_name)
                missing.append((struct_name, form.type))
        for form in forms.get("record", []):
            struct_name = form.struct or form.tag
            if struct_name not in defined:
                defined.add(struct_name)
                missing.append((struct_name, form.type))
        for form in forms.get("option", []):
            struct_name = form.struct or option_struct_name(form.type)
            if struct_name not in defined:
                defined.add(struct_name)
                missing.append((struct_name, form.type))
        for form in forms.get("auto", []):
            payload_t = auto_payload_type(form.type)
            struct_name = tuple_struct_name(payload_t)
            if payload_t.value_fields and struct_name not in defined:
                defined.add(struct_name)
                missing.append((struct_name, payload_t))
        if missing:
            lines.extend(self.emit_forward_typedefs(missing))
            lines.extend(self.emit_aggregate_structs(missing))

        def part_desc(form: DescriptorForm, key: str, t: Optional[QType]) -> str:
            # The descriptor of a part of form's type (t, keyed as echo_children
            # keys it): for an echo-only descriptor, the part's echo-only
            # descriptor if it has one
            if t is None:
                return "NULL"
            if form.display is not None:
                shown = echo_children(form.display).get(key)
                if shown is not None and (shown_form := echo_descriptor_form(shown, self.record_ctx)) is not None:
                    return shown_form.c_expr
            return desc_fn(t)

        def type_descriptor(tag: str, kind: str, name: str, size: str, extra: str) -> list[str]:
            return [
                f"static const QTypeDescriptor quest_type_{tag} Q_UNUSED = {{",
                f"    .kind = {kind},",
                f"    .name = {c_string(name)},",
                f"    .size = {size},",
                "    .alignment = sizeof(void *),",
                "    .is_subtype = quest_is_subtype,",
                f"    .extra = {extra},",
                "};",
            ]

        self.emitted_descriptor_tags = sorted(seen_tags)
        lines.append("/* Forward declarations for static type descriptors */")
        for tag in self.emitted_descriptor_tags:
            lines.append(f"static const QTypeDescriptor quest_type_{tag} Q_UNUSED;")
        lines.append("")

        if funs:
            lines.append("/* Adapters for function types (defined after the descriptors) */")
            for tag, _ in funs:
                lines.append(
                    f"static QClosure *quest_adapt_{tag}(const QClosure *orig, const QTypeDescriptor *from, "
                    f"const QTypeDescriptor *to);"
                )
                lines.append(f"static QVal quest_invoke_{tag}(const QClosure *c, const QVal *args);")
            lines.append("")

        lines.append("/* Static runtime type descriptors for compound and opaque types */")
        for form in forms.get("opaque", []):
            extra = "NULL"
            if isinstance(form.type, QTypeApp):
                # An application of an abstract type operator: its arguments are
                # part of its identity
                args = [desc_fn(a) for a in form.type.arguments]
                lines.append(
                    f"static const QTypeDescriptor *const qopaque_args_{form.tag}[{c_int(max(1, len(args)))}] "
                    f"Q_UNUSED = "
                    f"{{ {comma(args or ['NULL'])} }};"
                )
                lines.append(
                    f"static const QOpaqueTypeDescriptor qopaque_desc_{form.tag} Q_UNUSED = "
                    f"{{ .arg_count = {c_int(len(args))}, .args = qopaque_args_{form.tag} }};"
                )
                extra = f"&qopaque_desc_{form.tag}"
            lines.extend(type_descriptor(form.tag, "QTYPE_KIND_OPAQUE", form.name, "sizeof(QVal)", extra))
            lines.append("")

        for form in forms.get("stored", []):
            # A module's bounded abstract type: its opaque type, held as a value
            # of its bound
            lines.extend(type_descriptor(f"{form.tag}_abstract", "QTYPE_KIND_OPAQUE", form.name, "sizeof(QVal)", "NULL"))
            lines.append(
                f"static const QStoredDescriptor qstored_desc_{form.tag} Q_UNUSED = "
                f"{{ .type = &quest_type_{form.tag}_abstract, .storage = {desc_fn(form.type.bound.bound)}, "
                f".viewed = true }};"
            )
            lines.extend(type_descriptor(
                form.tag, "QTYPE_KIND_STORED", form.name, f"sizeof({self.c_type(form.type)})", f"&qstored_desc_{form.tag}"
            ))
            lines.append("")

        for form in forms.get("hole", []):
            # A type parameter in a template, stored as a QVal or as its bound
            hole_t = form.type
            bounded = isinstance(hole_t.bound, QPowerKind)
            storage = desc_fn(hole_t.bound.bound) if bounded else "NULL"
            size = f"sizeof({self.c_type(hole_t)})" if bounded else "sizeof(QVal)"
            lines.append(
                f"static const QHoleDescriptor qhole_desc_{form.tag} Q_UNUSED = "
                f"{{ .index = {form.name}, .storage = {storage} }};"
            )
            lines.extend(type_descriptor(form.tag, "QTYPE_KIND_HOLE", f"?{form.name}", size, f"&qhole_desc_{form.tag}"))
            lines.append("")

        for form in forms.get("fun", []):
            tag = form.tag
            quants, params, result_t = fun_shape_signature(form.type)
            bounds = "NULL"
            if quants:
                bound_descs = [desc_fn(bound) if bound is not None else "NULL" for bound in quants]
                lines.append(
                    f"static const QTypeDescriptor *const qfun_bounds_{tag}[{c_int(len(quants))}] Q_UNUSED = "
                    f"{{ {comma(bound_descs)} }};"
                )
                bounds = f"qfun_bounds_{tag}"
            header = [
                f"    .param_count = {c_int(len(params))},",
                f"    .result_type = {desc_fn(result_t)},",
                f"    .adapt = quest_adapt_{tag},",
                f"    .invoke = quest_invoke_{tag},",
                f"    .quantifier_count = {c_int(len(quants))},",
                f"    .quantifier_bounds = {bounds},",
            ]
            if params:
                lines.append("static const struct {")
                lines.append("    size_t param_count;")
                lines.append("    const QTypeDescriptor *result_type;")
                lines.append("    QFunAdapter adapt;")
                lines.append("    QFunInvoker invoke;")
                lines.append("    size_t quantifier_count;")
                lines.append("    const QTypeDescriptor *const *quantifier_bounds;")
                lines.append(f"    const QFunParamDescriptor params[{c_int(len(params))}];")
                lines.append(f"}} qfun_desc_{tag} Q_UNUSED = {{")
                lines.extend(header)
                lines.append("    .params = {")
                for prm in params:
                    is_var = "true" if prm.is_var else "false"
                    is_out = "true" if prm.is_out else "false"
                    lines.append(f"        {{ .type = {desc_fn(prm.type_val)}, .is_var = {is_var}, .is_out = {is_out} }},")
                lines.append("    }")
                lines.append("};")
            else:
                lines.append(f"static const QFunTypeDescriptor qfun_desc_{tag} Q_UNUSED = {{")
                lines.extend(header)
                lines.append("};")
            lines.extend(type_descriptor(tag, "QTYPE_KIND_FUN", short_type_name(form.type), "sizeof(QClosure *)", f"&qfun_desc_{tag}"))
            lines.append("")

        for form in forms.get("auto", []):
            tag, auto_t = form.tag, form.type
            payload_t = auto_payload_type(auto_t)
            struct_name = tuple_struct_name(payload_t)
            n = len(payload_t.value_fields)
            bound = desc_fn(auto_t.kind_bound.bound) if isinstance(auto_t.kind_bound, QPowerKind) else "NULL"
            payload_size = f"sizeof(struct {struct_name})" if n else "0"
            lines.append("static const struct {")
            lines.append("    const QTypeDescriptor *bound;")
            lines.append("    size_t payload_size;")
            lines.append("    size_t component_count;")
            lines.append(f"    const QAutoComponentDescriptor components[{c_int(max(n, 1))}];")
            lines.append(f"}} qauto_desc_{tag} Q_UNUSED = {{")
            lines.append(f"    .bound = {bound},")
            lines.append(f"    .payload_size = {payload_size},")
            lines.append(f"    .component_count = {c_int(n)},")
            lines.append("    .components = {")
            for i, sig_f in enumerate(auto_t.signature):
                is_var = "true" if sig_f.is_var else "false"
                lines.append(
                    f"        {{ .name = {c_string(sig_f.name)}, .type = {desc_fn(sig_f.type_val)}, "
                    f".offset = offsetof(struct {struct_name}, _{c_int(i)}), .is_var = {is_var} }},"
                )
            lines.append("    }")
            lines.append("};")
            lines.extend(type_descriptor(tag, "QTYPE_KIND_AUTO", short_type_name(auto_t), "sizeof(QAuto *)", f"&qauto_desc_{tag}"))
            lines.append("")

        for form in forms.get("exception", []):
            tag = form.tag
            lines.append(f"static const QExceptionTypeDescriptor qexc_desc_{tag} Q_UNUSED = {{")
            lines.append(f"    .payload_type = {desc_fn(form.type.payload_type)},")
            lines.append("};")
            lines.extend(type_descriptor(tag, "QTYPE_KIND_EXCEPTION", short_type_name(form.type), "sizeof(void *)", f"&qexc_desc_{tag}"))
            lines.append("")

        for form in forms.get("array", []):
            tag = form.tag
            lines.append(f"static const QArrayTypeDescriptor qarr_desc_{tag} Q_UNUSED = {{")
            lines.append(f"    .element_type = {part_desc(form, '', form.type.element_type)},")
            lines.append("};")
            lines.extend(type_descriptor(tag, "QTYPE_KIND_ARRAY", short_type_name(form.type), "sizeof(void *)", f"&qarr_desc_{tag}"))
            lines.append("")

        for form in forms.get("record", []):
            tag, qtype = form.tag, form.type
            struct_name = form.struct or tag
            sorted_fields = sorted(qtype.fields, key=lambda f: f.name)
            n = len(sorted_fields)
            if n > 0:
                lines.append("static const struct {")
                lines.append("    size_t field_count;")
                lines.append(f"    const QRecordFieldDescriptor fields[{c_int(n)}];")
                lines.append(f"}} qrec_desc_{tag} Q_UNUSED = {{")
                lines.append(f"    .field_count = {c_int(n)},")
                lines.append("    .fields = {")
                for f in sorted_fields:
                    is_var_str = "true" if f.is_var else "false"
                    lines.append(
                        f"        {{ .name = {c_string(f.name)}, .type = {part_desc(form, f.name, f.type_val)}, "
                        f".offset = offsetof(struct {struct_name}, qf_{f.name}), .is_var = {is_var_str} }},"
                    )
                lines.append("    }")
                lines.append("};")
                size = f"sizeof(struct {struct_name})"
                lines.extend(type_descriptor(tag, "QTYPE_KIND_RECORD", short_type_name(qtype), size, f"&qrec_desc_{tag}"))
            else:
                lines.append(f"static const QRecordTypeDescriptor qrec_desc_{tag} Q_UNUSED = {{ .field_count = 0 }};")
                lines.extend(type_descriptor(tag, "QTYPE_KIND_RECORD", "Record end", "sizeof(void *)", f"&qrec_desc_{tag}"))
            lines.append("")

        for form in forms.get("tuple", []):
            tag, qtype = form.tag, form.type
            struct_name = tuple_struct_name(qtype)
            val_fields = qtype.value_fields
            n = len(val_fields)
            # Its type components, which only echo writes: with alias names in
            # an echo-only descriptor
            components = tuple_type_components(form.display if form.display is not None else qtype)
            if components:
                lines.append(
                    f"static const QTupleTypeComponentDescriptor qtup_components_{tag}[{c_int(len(components))}] "
                    f"Q_UNUSED = {{"
                )
                for position, text in components:
                    lines.append(f"    {{ .position = {c_int(position)}, .text = {c_string(text)} }},")
                lines.append("};")
            lines.append("static const struct {")
            lines.append("    size_t component_count;")
            lines.append("    const QTupleTypeComponentDescriptor *components;")
            lines.append("    size_t element_count;")
            # (C99 has no empty arrays: a tuple of type components alone has one
            # unused element)
            lines.append(f"    const QTupleElementDescriptor elements[{c_int(max(n, 1))}];")
            lines.append(f"}} qtup_desc_{tag} Q_UNUSED = {{")
            lines.append(f"    .component_count = {c_int(len(components))},")
            lines.append(f"    .components = {f'qtup_components_{tag}' if components else 'NULL'},")
            lines.append(f"    .element_count = {c_int(n)},")
            lines.append("    .elements = {")
            for i, f in enumerate(val_fields):
                name_str = c_string(f.name) if f.name is not None else "NULL"
                is_var_str = "true" if f.is_var else "false"
                lines.append(
                    f"        {{ .name = {name_str}, .type = {part_desc(form, c_int(i), f.type_val)}, "
                    f".offset = offsetof(struct {struct_name}, _{c_int(i)}), .is_var = {is_var_str} }},"
                )
            if not val_fields:
                lines.append("        { .name = NULL },")
            lines.append("    }")
            lines.append("};")
            lines.extend(type_descriptor(tag, "QTYPE_KIND_TUPLE", short_type_name(qtype), f"sizeof(struct {struct_name})", f"&qtup_desc_{tag}"))
            lines.append("")

        for form in forms.get("variant", []) + forms.get("option", []):
            tag, qtype = form.tag, form.type
            cases = (
                [(v.name, v.type_val, v.is_var) for v in qtype.variants]
                if isinstance(qtype, QVariantType)
                else [(o.name, o.payload_type, False) for o in qtype.options]
            )
            n = len(cases)
            lines.append("static const struct {")
            lines.append("    size_t case_count;")
            lines.append(f"    const QVariantCaseDescriptor cases[{c_int(max(n, 1))}];")
            lines.append(f"}} qvar_desc_{tag} Q_UNUSED = {{")
            lines.append(f"    .case_count = {c_int(n)},")
            lines.append("    .cases = {")
            for i, (c_tag_name, p_type, is_var) in enumerate(cases):
                p_desc = part_desc(form, c_tag_name, p_type)
                is_var_str = "true" if is_var else "false"
                lines.append(
                    f"        {{ .name = {c_string(c_tag_name)}, .payload_type = {p_desc}, "
                    f".tag_index = {c_int_literal(i)}, .is_var = {is_var_str} }},"
                )
            lines.append("    }")
            lines.append("};")
            if isinstance(qtype, QVariantType):
                kind_str, size_str = "QTYPE_KIND_VARIANT", "sizeof(QVariantVal)"
            else:
                struct_name = form.struct or option_struct_name(qtype)
                kind_str, size_str = "QTYPE_KIND_OPTION", f"sizeof(struct {struct_name})"
            lines.extend(type_descriptor(tag, kind_str, short_type_name(qtype), size_str, f"&qvar_desc_{tag}"))
            lines.append("")
        return lines

    def emit_fun_type_adapters(self, fun_types: Sequence[tuple[str, QFunType]]) -> list[str]:
        """Defines the adapter and the invoker of each function type that has a
        runtime descriptor (QFunAdapter, quest_adapt_<tag>, and QFunInvoker,
        quest_invoke_<tag>).

        Run-time conversions of a closure to a function type T, by dynamic.be,
        inspect, or the read of a record field stored at a subtype, are known
        only to be from some subtype of T. The adapter for T wraps the closure
        in a thunk with T's C signature, which converts arguments and result as
        described by the two descriptors. The closure is called through T's
        signature when it has the same C signature (as types related by
        subtyping do), and otherwise, when one of the two types is laid out
        generically (a template's instance), through the invoker of the
        closure's own type, which takes and returns QVal forms.
        """
        lines: list[str] = []
        if not fun_types:
            return lines
        lines.append("/* Adapters for function types: thunks converting arguments and results by descriptor */")
        for tag, fun_t in fun_types:
            # A polymorphic function type takes its type parameters' descriptors
            # first; they are passed through
            quants, params, ret_t = fun_shape_signature(fun_t)
            ret_c = "void" if ret_t is OK_TYPE else self.c_type(ret_t)
            fn_ptr = closure_fn_ptr_type(fun_t, self.record_ctx)
            nq = len(quants)
            param_decls = ["void *_raw_env"]
            param_decls.extend(f"const QTypeDescriptor *qv_desc_{c_int(k)}" for k in range(nq))
            direct: list[str] = []
            uniform: list[str] = [f"QVal qv_args[{c_int(max(1, nq + len(params)))}];"]
            uniform.extend(f"qv_args[{c_int(k)}].p = (void *)qv_desc_{c_int(k)};" for k in range(nq))
            call_args = ["e->orig->env"] + [f"qv_desc_{c_int(k)}" for k in range(nq)]
            for i, p in enumerate(params):
                name = f"qv_arg_{c_int(i)}"
                slot = f"qv_args[{c_int(nq + i)}]"
                if p.is_var or p.is_out:
                    param_decls.append(f"{location_representation(p.type_val)} *{name}")
                    uniform.append(f"{slot}.p = (void *){name};")
                elif p.type_val is OK_TYPE:
                    param_decls.append(f"QVal {name}")
                    uniform.append(f"{slot} = {name};")
                else:
                    param_decls.append(f"{self.c_type(p.type_val)} {name}")
                    to_from = f"to->params[{c_int(i)}].type, from->params[{c_int(i)}].type"
                    uniform.append(f"{slot} = quest_convert({qval_wrap(name, p.type_val)}, {to_from});")
                    if may_be_stored_as_subtype(shape(p.type_val)):
                        converted = qval_unwrap(
                            f"quest_convert({qval_wrap(name, p.type_val)}, {to_from})", p.type_val, self
                        )
                        direct.append(f"{name} = {converted};")
                call_args.append(name)
            call_expr = call(f"(({fn_ptr})(e->orig->fn))", call_args)
            invoke_expr = "from->invoke(e->orig, qv_args)"
            if ret_t is OK_TYPE:
                direct.append(f"{call_expr};")
                direct.append("return;")
                uniform.append(f"(void){invoke_expr};")
            else:
                if may_be_stored_as_subtype(shape(ret_t)):
                    direct.append(f"{ret_c} qv_result = {call_expr};")
                    converted = qval_unwrap(
                        f"quest_convert({qval_wrap('qv_result', ret_t)}, from->result_type, to->result_type)",
                        ret_t,
                        self.record_ctx,
                    )
                    direct.append(f"return {converted};")
                else:
                    direct.append(f"return {call_expr};")
                uniform.append(
                    "return "
                    + qval_unwrap(f"quest_convert({invoke_expr}, from->result_type, to->result_type)", ret_t, self.record_ctx)
                    + ";"
                )
            thunk = f"quest_thunk_{tag}"
            lines.append(f"static {ret_c} {call(thunk, param_decls)} {{")
            lines.append("    const QFunAdapterEnv *e = (const QFunAdapterEnv *)_raw_env;")
            lines.append("    const QFunTypeDescriptor *from = (const QFunTypeDescriptor *)e->from->extra;")
            lines.append("    const QFunTypeDescriptor *to = (const QFunTypeDescriptor *)e->to->extra;")
            lines.append("    if (e->direct) {")
            lines.extend(f"        {line}" for line in direct)
            lines.append("    }")
            lines.extend(f"    {line}" for line in uniform)
            lines.append("}")
            lines.append(
                f"static QClosure *quest_adapt_{tag}(const QClosure *orig, const QTypeDescriptor *from, "
                f"const QTypeDescriptor *to) {{"
            )
            lines.append("    QFunAdapterEnv *e = (QFunAdapterEnv *)quest_alloc(sizeof(QFunAdapterEnv));")
            lines.append("    e->orig = orig;")
            lines.append("    e->from = from;")
            lines.append("    e->to = to;")
            lines.append("    e->direct = quest_fun_signature_equivalent(from, to);")
            lines.append("    QClosure *adapted = (QClosure *)quest_alloc(sizeof(QClosure));")
            lines.append(f"    adapted->fn = (void *){thunk};")
            lines.append("    adapted->env = e;")
            lines.append("    return adapted;")
            lines.append("}")
            # The invoker: a call with QVal forms, for adapters whose closure
            # has this type's C signature
            inv_args = ["c->env"] + [f"(const QTypeDescriptor *)args[{c_int(k)}].p" for k in range(nq)]
            for i, p in enumerate(params):
                arg = f"args[{c_int(nq + i)}]"
                if p.is_var or p.is_out:
                    inv_args.append(f"({location_representation(p.type_val)} *){arg}.p")
                elif p.type_val is OK_TYPE:
                    inv_args.append(arg)
                else:
                    inv_args.append(qval_unwrap(arg, p.type_val, self.record_ctx))
            inv_call = call(f"(({fn_ptr})(c->fn))", inv_args)
            lines.append(f"static QVal quest_invoke_{tag}(const QClosure *c, const QVal *args) {{")
            lines.append("    (void)args;")
            if ret_t is OK_TYPE:
                lines.append(f"    {inv_call};")
                lines.append("    return Q_OK_VAL;")
            else:
                lines.append(f"    return {qval_wrap(inv_call, ret_t)};")
            lines.append("}")
            lines.append("")
        return lines
