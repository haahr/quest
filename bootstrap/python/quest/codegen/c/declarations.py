"""The declarations of the C the IR's printer writes (c/printer.py) and of interfaces' C headers (c/headers.py):
aggregate structs, offset tables, coercion tables, type descriptors, function type adapters, and modules' exported
functions."""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from quest.typechecker.typed_ast import TypedLetType, TypedRecord
from quest.ir.represent import _may_be_stored_as_subtype
from quest.codegen.c.types import (
    closure_fn_ptr_type,
    descriptor_form,
    DescriptorForm,
    MissingDescriptorError,
    qval_unwrap,
    qval_wrap,
    record_struct_name,
    RecordNamingContext,
)
from quest.codegen.descriptors import fun_descriptor_tag
from quest.codegen.layout import (
    collect_fun_quantifiers,
    normalize_type,
    option_struct_name,
    tuple_struct_name,
    type_tag,
)
from quest.codegen.symbols import mangle_ident, mangle_module_ident, mangle_module_name, module_record_ident
from quest.types import (
    auto_payload_type,
    is_type_equal,
    QRecordField,
    QRecGroupType,
    QRecType,
    short_type_name,
    QPowerKind,
    QTypeApp,
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
    QQuantifier,
    QRecordType,
    QTupleType,
    QType,
    QTypeVar,
    QVariantType,
    REAL_TYPE,
    STRING_TYPE,
    resolve_option_bound,
    resolve_record_bound,
    resolve_variant_bound,
)


def module_function_signature(
    clean_mod: str, name: str, type_val: QType, c_type: Callable[[QType], str]
) -> Optional[tuple[str, str, list[str]]]:
    """The C function a module file exports for a member of its interface that is a function or a polymorphic value
    (`qv_<module>_<member>`, taking its type parameters' descriptors and then its parameters, at the interface's
    types): its result's C type, its name, and its parameters' declarations; None for other members."""
    if isinstance(type_val, QAllType):
        quants, fun_t = type_val.quantifiers, type_val.body
    else:
        quants, fun_t = (), type_val
    if not isinstance(fun_t, QFunType) and not quants:
        return None
    ret_type = fun_t.result_type if isinstance(fun_t, QFunType) else fun_t
    ret_c = "void" if ret_type is OK_TYPE else ("QRecordVal" if isinstance(ret_type, QRecordType) else c_type(ret_type))
    param_decls = [f"const QTypeDescriptor *descriptor_{q.name}" for q in quants]
    if isinstance(fun_t, QFunType):
        param_decls += [
            f"{c_type(p.type_val)}{' *' if p.is_out or p.is_var else ' '}qv_p_{p.name}" for p in fun_t.params
        ]
    return ret_c, mangle_module_ident(clean_mod, name), param_decls


def collect_aggregate_types(
    node: Any,
    ctx: RecordNamingContext,
    visited_names: Optional[set[str]] = None,
    visited_type_ids: Optional[set[int]] = None,
    visited_node_ids: Optional[set[int]] = None,
) -> tuple[list[tuple[str, QType]], list[QVariantType], list[QType]]:
    """Traverses an AST to find all unique aggregate types (tuples, records, options, variants)."""
    if visited_names is None:
        visited_names = set()
    if visited_type_ids is None:
        visited_type_ids = set()
    if visited_node_ids is None:
        visited_node_ids = set()
    result: list[tuple[str, QType]] = []
    variant_types: list[QVariantType] = []
    all_types: list[QType] = []

    def visit_type(t: Optional[QType]) -> None:
        if t is None:
            return
        t_id = id(t)
        if t_id in visited_type_ids:
            return
        visited_type_ids.add(t_id)
        t = normalize_type(t)
        all_types.append(t)
        if isinstance(t, QTupleType):
            for f in t.value_fields:
                visit_type(f.type_val)
            name = tuple_struct_name(t)
            if name not in visited_names:
                visited_names.add(name)
                result.append((name, t))
        elif isinstance(t, QRecordType):
            for f in t.fields:
                visit_type(f.type_val)
            name = record_struct_name(t, ctx)
            if name not in visited_names:
                visited_names.add(name)
                result.append((name, t))
        elif isinstance(t, QOptionType) or (opt_bound := resolve_option_bound(t)) is not None:
            opt_t = t if isinstance(t, QOptionType) else opt_bound
            for o in opt_t.options:
                if o.payload_type:
                    visit_type(o.payload_type)
            name = option_struct_name(opt_t)
            if name not in visited_names:
                visited_names.add(name)
                result.append((name, opt_t))
        elif isinstance(t, QAutoType):
            # Auto payloads are stored in the witness-independent layout
            visit_type(auto_payload_type(t))
        elif isinstance(t, QVariantType):
            if not any(v is t or is_type_equal(v, t) for v in variant_types):
                variant_types.append(t)
            for v in t.variants:
                if getattr(v, "type_val", None):
                    visit_type(v.type_val)
        elif hasattr(t, "params") and hasattr(t, "result_type"):
            for p in getattr(t, "params", ()):
                visit_type(getattr(p, "type_val", None))
            visit_type(getattr(t, "result_type", None))
        elif hasattr(t, "element_type"):
            visit_type(getattr(t, "element_type", None))
        elif hasattr(t, "inner_type"):
            visit_type(getattr(t, "inner_type", None))
        if hasattr(t, "bound"):
            bound = getattr(t, "bound")
            if hasattr(bound, "bound"):
                visit_type(getattr(bound, "bound"))
        if hasattr(t, "quantifiers") and hasattr(t, "body"):
            for q in getattr(t, "quantifiers", ()):
                if hasattr(q, "bound") and hasattr(q.bound, "bound"):
                    visit_type(getattr(q.bound, "bound"))
            visit_type(getattr(t, "body", None))

    def visit_node(n: Any) -> None:
        if n is None:
            return
        n_id = id(n)
        if n_id in visited_node_ids:
            return
        visited_node_ids.add(n_id)
        if isinstance(n, QType):
            visit_type(n)
        if isinstance(n, TypedLetType) and n.symbol.definition is not None:
            if isinstance(n.symbol.definition, QRecordType):
                ctx.register_alias(n.name, n.symbol.definition)
        if isinstance(n, TypedRecord):
            concrete_t = QRecordType(
                fields=tuple(
                    QRecordField(name=fld.name, type_val=fld.value.type_val, is_var=fld.is_var)
                    for fld in n.fields
                )
            )
            visit_type(concrete_t)
        if hasattr(n, "type_val") and isinstance(getattr(n, "type_val"), QType):
            visit_type(getattr(n, "type_val"))
        if hasattr(n, "symbol"):
            sym = getattr(n, "symbol")
            if hasattr(sym, "type_val") and isinstance(getattr(sym, "type_val"), QType):
                visit_type(getattr(sym, "type_val"))
            if hasattr(sym, "definition") and isinstance(getattr(sym, "definition"), QType):
                visit_type(getattr(sym, "definition"))
        if hasattr(n, "definition") and isinstance(getattr(n, "definition"), QType):
            visit_type(getattr(n, "definition"))

        if isinstance(n, (list, tuple)):
            for item in n:
                visit_node(item)
            return

        # A recursive type's bodies mention its variables free; visit_type has visited its unfolding
        if isinstance(n, (QRecType, QRecGroupType)):
            return

        if hasattr(n, "__dataclass_fields__"):
            for field_name in n.__dataclass_fields__:
                visit_node(getattr(n, field_name))

    visit_node(node)
    return result, variant_types, all_types


class CDeclarationEmitter:
    """Emits forward declarations, structs, typedefs, evidence dictionaries, and trampolines."""

    def __init__(self, record_ctx: RecordNamingContext, c_type_fn: Callable[[QType], str]):
        self.record_ctx = record_ctx
        self.c_type = c_type_fn
        self.emitted_descriptor_tags: list[str] = []
        # Function types with descriptors, whose adapters (quest_adapt_<tag>) emit_fun_type_adapters defines
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

    def emit_precompiled_module_declarations(self, modules: list) -> list[str]:
        """The extern declarations of the functions modules compiled on their own export (each a TypedModule whose
        scope is its interface's)."""
        lines: list[str] = []
        precompiled_mods = [m for m in modules if getattr(m, "is_precompiled", False)]
        if precompiled_mods:
            lines.append("/* External declarations for precompiled module functions */")
            for mod in precompiled_mods:
                clean_mod = mangle_module_name(mod.name)
                if getattr(mod, "scope", None) and hasattr(mod.scope, "values"):
                    for val_name, val_sym in mod.scope.values.items():
                        sig = module_function_signature(clean_mod, val_name, val_sym.type_val, self.c_type)
                        if sig is not None:
                            ret_c, m_ident, param_decls = sig
                            lines.append(f"extern {ret_c} {m_ident}({', '.join(param_decls) or 'void'});")
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
                            c_type = self.c_type(f.type_val)
                            lines.append(f"    {c_type} _{i};")
                case QRecordType(fields=fields):
                    lines.append("    QRecordHeader header;")
                    if not fields:
                        lines.append("    char _unused;")
                    else:
                        for f in sorted(fields, key=lambda fld: fld.name):
                            c_type = self.c_type(f.type_val)
                            lines.append(f"    {c_type} qf_{f.name};")
                case QOptionType(options=options):
                    lines.append("    int64_t tag;")
                    payload_branches = [o for o in options if o.payload_type is not None]
                    if payload_branches:
                        lines.append("    union {")
                        for o in payload_branches:
                            match o.payload_type:
                                case QTupleType(value_fields=pt_fields):
                                    lines.append(f"        struct {tag_name}_{o.name}_payload {{")
                                    for i, f in enumerate(pt_fields):
                                        c_f_type = self.c_type(f.type_val)
                                        f_ident = f"_{i}" if not f.name else f"_{i}"
                                        lines.append(f"            {c_f_type} {f_ident};")
                                    lines.append(f"        }} {o.name};")
                                case QRecordType(fields=pt_fields):
                                    lines.append(f"        struct {tag_name}_{o.name}_payload {{")
                                    for f in sorted(pt_fields, key=lambda fld: fld.name):
                                        c_f_type = self.c_type(f.type_val)
                                        lines.append(f"            {c_f_type} qf_{f.name};")
                                    lines.append(f"        }} {o.name};")
                                case pt:
                                    c_pt = self.c_type(pt)
                                    lines.append(f"        struct {{ {c_pt} val; }} {o.name};")
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
                # Static tables only relate records whose shared fields have equal types, so no field is stored
                # at a different type (stored_types is NULL)
                if not tgt.fields:
                    lines.append(f"static const {dict_t} {inst_name} = {{ 0, NULL }};")
                else:
                    entries = [
                        f"offsetof({src_sname}, qf_{f.name})"
                        for f in sorted(tgt.fields, key=lambda fld: fld.name)
                    ]
                    lines.append(f"static const {dict_t} {inst_name} = {{ {', '.join(entries)}, NULL }};")
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
                        f"static_assert(offsetof({src_name}, _{i}) == offsetof({tgt_name}, _{i}), "
                        f"tuple_coercion_{tgt_name}_{src_name}_{i});"
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
                    str(next(j for j, tv in enumerate(tgt.variants) if tv.name == sv.name))
                    for sv in src.variants
                ]
                lines.append(
                    f"static const int64_t tagmap_{tgt_tag}_{src_tag}[{len(src.variants)}] = "
                    f"{{ {', '.join(entries)} }};"
                )
            lines.append("")
        return lines

    def emit_type_descriptors(
        self,
        agg_types: list[tuple[str, QType]],
        variant_types: list[QVariantType],
        desc_fn: Callable[[QType], str],
        all_program_types: Optional[list[QType]] = None,
    ) -> list[str]:
        """Emits a static descriptor for every type of the program that has one (see descriptor_form).

        desc_fn gives the descriptor expression of a component type, as c_type_descriptor does. A later call emits
        only descriptors (and structs) that earlier calls did not, as for the templates that function bodies need.
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
                    visit(getattr(v, "type_val", None))
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
                quants, inner = collect_fun_quantifiers(dt)
                for q in quants:
                    if isinstance(q.bound, QPowerKind):
                        visit(q.bound.bound)
                if isinstance(inner, QFunType):
                    for prm in inner.params:
                        visit(prm.type_val)
                    visit(inner.result_type)
                else:
                    visit(inner)

        for _, t in agg_types:
            visit(t)
        for v in variant_types:
            visit(v)
        if all_program_types:
            for t in all_program_types:
                visit(t)

        funs = [(f.tag, f.type) for f in forms.get("fun", [])]
        self.emitted_fun_types = funs
        if not seen_tags:
            return lines
        emitted_before.update(seen_tags)

        # Descriptors of unfolded recursive types may name tuple, record, and option structs that the program's own
        # types do not (a recursive occurrence is named by its unfolding rather than as QVal, and a type reached only
        # as the argument of an opaque type has no values in the program); their layouts are the same, but the
        # structs must be defined for offsetof and sizeof
        defined: set[str] = self.__dict__.setdefault("_defined_struct_names", set())
        defined.update(name for name, _ in agg_types)
        missing: list[tuple[str, QType]] = []
        for form in forms.get("tuple", []):
            struct_name = tuple_struct_name(form.type)
            if struct_name not in defined:
                defined.add(struct_name)
                missing.append((struct_name, form.type))
        for form in forms.get("record", []):
            if form.tag not in defined:
                defined.add(form.tag)
                missing.append((form.tag, form.type))
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

        def c_string(text: str) -> str:
            return text.replace("\\", "\\\\").replace('"', '\\"')

        def type_descriptor(tag: str, kind: str, name: str, size: str, extra: str) -> list[str]:
            return [
                f"static const QTypeDescriptor quest_type_{tag} Q_UNUSED = {{",
                f"    .kind = {kind},",
                f"    .name = \"{c_string(name)}\",",
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
                # An application of an abstract type operator: its arguments are part of its identity
                args = [desc_fn(a) for a in form.type.arguments]
                lines.append(
                    f"static const QTypeDescriptor *const qopaque_args_{form.tag}[{max(1, len(args))}] Q_UNUSED = "
                    f"{{ {', '.join(args) if args else 'NULL'} }};"
                )
                lines.append(
                    f"static const QOpaqueTypeDescriptor qopaque_desc_{form.tag} Q_UNUSED = "
                    f"{{ .arg_count = {len(args)}, .args = qopaque_args_{form.tag} }};"
                )
                extra = f"&qopaque_desc_{form.tag}"
            lines.extend(type_descriptor(form.tag, "QTYPE_KIND_OPAQUE", form.name, "sizeof(QVal)", extra))
            lines.append("")

        for form in forms.get("stored", []):
            # A module's bounded abstract type: its opaque type, held as a value of its bound
            lines.extend(type_descriptor(f"{form.tag}_abstract", "QTYPE_KIND_OPAQUE", form.name, "sizeof(QVal)", "NULL"))
            lines.append(
                f"static const QStoredDescriptor qstored_desc_{form.tag} Q_UNUSED = "
                f"{{ .type = &quest_type_{form.tag}_abstract, .storage = {desc_fn(form.type.bound.bound)} }};"
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
            quants, inner = collect_fun_quantifiers(form.type)
            params = inner.params if isinstance(inner, QFunType) else ()
            result_t = inner.result_type if isinstance(inner, QFunType) else inner
            bounds = "NULL"
            if quants:
                bound_descs = [
                    desc_fn(q.bound.bound) if isinstance(q.bound, QPowerKind) else "NULL" for q in quants
                ]
                lines.append(
                    f"static const QTypeDescriptor *const qfun_bounds_{tag}[{len(quants)}] Q_UNUSED = "
                    f"{{ {', '.join(bound_descs)} }};"
                )
                bounds = f"qfun_bounds_{tag}"
            header = [
                f"    .param_count = {len(params)},",
                f"    .result_type = {desc_fn(result_t)},",
                f"    .adapt = quest_adapt_{tag},",
                f"    .invoke = quest_invoke_{tag},",
                f"    .quantifier_count = {len(quants)},",
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
                lines.append(f"    const QFunParamDescriptor params[{len(params)}];")
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
            lines.append(f"    const QAutoComponentDescriptor components[{max(n, 1)}];")
            lines.append(f"}} qauto_desc_{tag} Q_UNUSED = {{")
            lines.append(f"    .bound = {bound},")
            lines.append(f"    .payload_size = {payload_size},")
            lines.append(f"    .component_count = {n},")
            lines.append("    .components = {")
            for i, (sig_f, stored_f) in enumerate(zip(auto_t.signature, payload_t.value_fields)):
                # Records and variants are stored inline (16 bytes); any other component's 8 bytes are its QVal form
                inline = self.c_type(stored_f.type_val) in ("QRecordVal", "QVariantVal")
                storage = desc_fn(stored_f.type_val) if inline else "NULL"
                is_var = "true" if sig_f.is_var else "false"
                lines.append(
                    f"        {{ .name = \"{sig_f.name}\", .type = {desc_fn(sig_f.type_val)}, .storage = {storage}, "
                    f".offset = offsetof(struct {struct_name}, _{i}), .is_var = {is_var} }},"
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
            lines.append(f"    .element_type = {desc_fn(form.type.element_type)},")
            lines.append("};")
            lines.extend(type_descriptor(tag, "QTYPE_KIND_ARRAY", short_type_name(form.type), "sizeof(void *)", f"&qarr_desc_{tag}"))
            lines.append("")

        for form in forms.get("record", []):
            tag, qtype = form.tag, form.type
            sorted_fields = sorted(qtype.fields, key=lambda f: f.name)
            n = len(sorted_fields)
            if n > 0:
                lines.append("static const struct {")
                lines.append("    size_t field_count;")
                lines.append(f"    const QRecordFieldDescriptor fields[{n}];")
                lines.append(f"}} qrec_desc_{tag} Q_UNUSED = {{")
                lines.append(f"    .field_count = {n},")
                lines.append("    .fields = {")
                for f in sorted_fields:
                    is_var_str = "true" if f.is_var else "false"
                    lines.append(
                        f"        {{ .name = \"{f.name}\", .type = {desc_fn(f.type_val)}, "
                        f".offset = offsetof(struct {tag}, qf_{f.name}), .is_var = {is_var_str} }},"
                    )
                lines.append("    }")
                lines.append("};")
                lines.extend(type_descriptor(tag, "QTYPE_KIND_RECORD", short_type_name(qtype), f"sizeof(struct {tag})", f"&qrec_desc_{tag}"))
            else:
                lines.append(f"static const QRecordTypeDescriptor qrec_desc_{tag} Q_UNUSED = {{ .field_count = 0 }};")
                lines.extend(type_descriptor(tag, "QTYPE_KIND_RECORD", "Record end", "sizeof(void *)", f"&qrec_desc_{tag}"))
            lines.append("")

        for form in forms.get("tuple", []):
            tag, qtype = form.tag, form.type
            struct_name = tuple_struct_name(qtype)
            val_fields = qtype.value_fields
            n = len(val_fields)
            lines.append("static const struct {")
            lines.append("    size_t element_count;")
            lines.append(f"    const QTupleElementDescriptor elements[{n}];")
            lines.append(f"}} qtup_desc_{tag} Q_UNUSED = {{")
            lines.append(f"    .element_count = {n},")
            lines.append("    .elements = {")
            for i, f in enumerate(val_fields):
                name_str = f'"{f.name}"' if getattr(f, "name", None) is not None else "NULL"
                is_var_str = "true" if f.is_var else "false"
                lines.append(
                    f"        {{ .name = {name_str}, .type = {desc_fn(f.type_val)}, "
                    f".offset = offsetof(struct {struct_name}, _{i}), .is_var = {is_var_str} }},"
                )
            lines.append("    }")
            lines.append("};")
            lines.extend(type_descriptor(tag, "QTYPE_KIND_TUPLE", short_type_name(qtype), f"sizeof(struct {struct_name})", f"&qtup_desc_{tag}"))
            lines.append("")

        for form in forms.get("variant", []) + forms.get("option", []):
            tag, qtype = form.tag, form.type
            cases = (
                [(v.name, getattr(v, "type_val", None), getattr(v, "is_var", False)) for v in qtype.variants]
                if isinstance(qtype, QVariantType)
                else [(o.name, o.payload_type, False) for o in qtype.options]
            )
            n = len(cases)
            lines.append("static const struct {")
            lines.append("    size_t case_count;")
            lines.append(f"    const QVariantCaseDescriptor cases[{max(n, 1)}];")
            lines.append(f"}} qvar_desc_{tag} Q_UNUSED = {{")
            lines.append(f"    .case_count = {n},")
            lines.append("    .cases = {")
            for i, (c_tag_name, p_type, is_var) in enumerate(cases):
                p_desc = desc_fn(p_type) if p_type is not None else "NULL"
                is_var_str = "true" if is_var else "false"
                lines.append(
                    f"        {{ .name = \"{c_tag_name}\", .payload_type = {p_desc}, "
                    f".tag_index = {i}LL, .is_var = {is_var_str} }},"
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
        """Defines the adapter and the invoker of each function type that has a runtime descriptor (QFunAdapter,
        quest_adapt_<tag>, and QFunInvoker, quest_invoke_<tag>).

        Run-time conversions of a closure to a function type T, by dynamic.be, inspect, or the read of a record field
        stored at a subtype, are known only to be from some subtype of T. The adapter for T wraps the closure in a
        thunk with T's C signature, which converts arguments and result as described by the two descriptors. The
        closure is called through T's signature when it has the same C signature (as types related by subtyping
        do), and otherwise, when one of the two types is laid out generically (a template's instance), through the
        invoker of the closure's own type, which takes and returns QVal forms.
        """
        lines: list[str] = []
        if not fun_types:
            return lines
        lines.append("/* Adapters for function types: thunks converting arguments and results by descriptor */")
        for tag, fun_t in fun_types:
            # A polymorphic function type takes its type parameters' descriptors first; they are passed through
            quants, inner = collect_fun_quantifiers(fun_t)
            params = inner.params if isinstance(inner, QFunType) else ()
            ret_t = inner.result_type if isinstance(inner, QFunType) else inner
            ret_c = "void" if ret_t is OK_TYPE else self.c_type(ret_t)
            fn_ptr = closure_fn_ptr_type(fun_t, self.record_ctx)
            nq = len(quants)
            param_decls = ["void *_raw_env"]
            param_decls.extend(f"const QTypeDescriptor *qv_desc_{k}" for k in range(nq))
            direct: list[str] = []
            uniform: list[str] = [f"QVal qv_args[{max(1, nq + len(params))}];"]
            uniform.extend(f"qv_args[{k}].p = (void *)qv_desc_{k};" for k in range(nq))
            call_args = ["e->orig->env"] + [f"qv_desc_{k}" for k in range(nq)]
            for i, p in enumerate(params):
                name = f"qv_arg_{i}"
                slot = f"qv_args[{nq + i}]"
                if p.is_var or p.is_out:
                    param_decls.append(f"{self.c_type(p.type_val)} *{name}")
                    uniform.append(f"{slot}.p = (void *){name};")
                elif p.type_val is OK_TYPE:
                    param_decls.append(f"QVal {name}")
                    uniform.append(f"{slot} = {name};")
                else:
                    param_decls.append(f"{self.c_type(p.type_val)} {name}")
                    to_from = f"to->params[{i}].type, from->params[{i}].type"
                    uniform.append(f"{slot} = quest_convert({qval_wrap(name, p.type_val)}, {to_from});")
                    if _may_be_stored_as_subtype(p.type_val):
                        converted = qval_unwrap(
                            f"quest_convert({qval_wrap(name, p.type_val)}, {to_from})", p.type_val, self
                        )
                        direct.append(f"{name} = {converted};")
                call_args.append(name)
            call_expr = f"(({fn_ptr})(e->orig->fn))({', '.join(call_args)})"
            invoke_expr = "from->invoke(e->orig, qv_args)"
            if ret_t is OK_TYPE:
                direct.append(f"{call_expr};")
                direct.append("return;")
                uniform.append(f"(void){invoke_expr};")
            else:
                if _may_be_stored_as_subtype(ret_t):
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
            lines.append(f"static {ret_c} {thunk}({', '.join(param_decls)}) {{")
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
            # The invoker: a call with QVal forms, for adapters whose closure has this type's C signature
            inv_args = ["c->env"] + [f"(const QTypeDescriptor *)args[{k}].p" for k in range(nq)]
            for i, p in enumerate(params):
                arg = f"args[{nq + i}]"
                if p.is_var or p.is_out:
                    inv_args.append(f"({self.c_type(p.type_val)} *){arg}.p")
                elif p.type_val is OK_TYPE:
                    inv_args.append(arg)
                else:
                    inv_args.append(qval_unwrap(arg, p.type_val, self.record_ctx))
            inv_call = f"(({fn_ptr})(c->fn))({', '.join(inv_args)})"
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
