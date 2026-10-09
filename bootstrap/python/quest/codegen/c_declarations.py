"""Declaration and header generation for Quest C Transpiler."""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from quest.typed_ast import TypedExpr, TypedFun, TypedRecord
from quest.codegen.c_analysis import CLambdaInfo, CProgramAnalysis
from quest.codegen.c_types import (
    DescriptorForm,
    MissingDescriptorError,
    descriptor_display_name,
    descriptor_form,
    fun_descriptor_tag,
    RecordNamingContext,
    collect_fun_quantifiers,
    mangle_ident,
    mangle_module_ident,
    mangle_module_name,
    normalize_type,
    module_record_ident,
    option_struct_name,
    record_struct_name,
    tuple_struct_name,
    type_to_c_tag,
)
from quest.types import (
    auto_payload_type,
    QPowerKind,
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


def emit_trampoline(
    tramp_name: str,
    ret_c: str,
    param_decls: Sequence[str],
    call_expr: str,
    is_void: bool,
    unused: bool = False,
    unused_vars: Sequence[str] = (),
) -> list[str]:
    """Generates C definition for a trampoline function forwarding to a target implementation."""
    attr = "Q_UNUSED " if unused else ""
    param_sigs = ["void *env"] + list(param_decls)
    sig = ", ".join(param_sigs)
    lines = [
        f"static {attr}{ret_c} {tramp_name}({sig}) {{",
        "    (void)env;",
    ]
    for uv in unused_vars:
        lines.append(f"    (void){uv};")
    if is_void:
        lines.append(f"    {call_expr};")
        if unused:
            lines.append("    return;")
    else:
        lines.append(f"    return {call_expr};")
    lines.append("}")
    return lines


class CDeclarationEmitter:
    """Emits forward declarations, structs, typedefs, evidence dictionaries, and trampolines."""

    def __init__(
        self,
        record_ctx: RecordNamingContext,
        c_type_fn: Callable[[QType], str],
        param_sigs_fn: Callable[[list[Any], tuple[QQuantifier, ...]], tuple[list[str], list[str]]],
        collect_quants_fn: Optional[
            Callable[[QType], tuple[tuple[QQuantifier, ...], QType]]
        ] = None,
        is_exact_record_literal_fn: Optional[Callable[[QType, TypedExpr], bool]] = None,
    ):
        self.record_ctx = record_ctx
        self.c_type = c_type_fn
        self.param_signatures = param_sigs_fn
        self.collect_fun_quantifiers = collect_quants_fn or collect_fun_quantifiers
        self.is_exact_record_literal = is_exact_record_literal_fn or (lambda _t, _e: False)
        self.emitted_descriptor_tags: list[str] = []
        # Function types with descriptors, whose adapters (quest_adapt_<tag>) the emitter must define
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

    def emit_module_declarations(self, analysis: CProgramAnalysis) -> list[str]:
        lines: list[str] = []
        if analysis.sorted_modules:
            has_precompiled = any(getattr(m, "is_precompiled", False) for m in analysis.sorted_modules)
            lines.append("/* Forward declarations and state for compiled modules */")
            for mod in analysis.sorted_modules:
                clean_mod = mangle_module_name(mod.name)
                if getattr(mod, "is_precompiled", False):
                    lines.append(f"extern QRecordVal {module_record_ident(clean_mod)};")
                    lines.append(f"extern void qv_mod_{clean_mod}_init(void);")
                elif has_precompiled:
                    lines.append(f"QRecordVal {module_record_ident(clean_mod)};")
                    lines.append(f"static bool qv_mod_{clean_mod}_initialized = false;")
                    lines.append(f"void qv_mod_{clean_mod}_init(void);")
                else:
                    lines.append(f"static QRecordVal {module_record_ident(clean_mod)};")
                    lines.append(f"static bool qv_mod_{clean_mod}_initialized = false;")
                    lines.append(f"static void qv_mod_{clean_mod}_init(void);")
            lines.append("")
        return lines

    def emit_precompiled_module_declarations(self, analysis: CProgramAnalysis) -> list[str]:
        lines: list[str] = []
        precompiled_mods = [m for m in analysis.sorted_modules if getattr(m, "is_precompiled", False)]
        if precompiled_mods:
            lines.append("/* External declarations for precompiled module functions */")
            for mod in precompiled_mods:
                clean_mod = mangle_module_name(mod.name)
                if getattr(mod, "scope", None) and hasattr(mod.scope, "values"):
                    for val_name, val_sym in mod.scope.values.items():
                        type_val = val_sym.type_val
                        if isinstance(type_val, QAllType):
                            quants = type_val.quantifiers
                            fun_t = type_val.body
                        else:
                            quants = ()
                            fun_t = type_val
                        if isinstance(fun_t, QFunType):
                            m_ident = mangle_module_ident(clean_mod, val_name)
                            ret_type = fun_t.result_type
                            ret_c = "void" if ret_type is OK_TYPE else (
                                "QRecordVal"
                                if isinstance(ret_type, QRecordType)
                                else self.c_type(ret_type)
                            )
                            quant_decls = [f"const QTypeDescriptor *descriptor_{q.name}" for q in quants]
                            param_decls = quant_decls + [
                                f"{self.c_type(p.type_val)}{' *' if p.is_out or p.is_var else ' '}qv_p_{p.name}"
                                for p in fun_t.params
                            ]
                            sig = "void" if not param_decls else ", ".join(param_decls)
                            lines.append(f"extern {ret_c} {m_ident}({sig});")
                        elif quants:
                            m_ident = mangle_module_ident(clean_mod, val_name)
                            ret_type = fun_t
                            ret_c = "void" if ret_type is OK_TYPE else (
                                "QRecordVal"
                                if isinstance(ret_type, QRecordType)
                                else self.c_type(ret_type)
                            )
                            quant_decls = [f"const QTypeDescriptor *descriptor_{q.name}" for q in quants]
                            sig = ", ".join(quant_decls)
                            lines.append(f"extern {ret_c} {m_ident}({sig});")
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
            if isinstance(t, QTupleType):
                if not t.value_fields:
                    lines.append("    char _unused;")
                else:
                    for i, f in enumerate(t.value_fields):
                        c_type = self.c_type(f.type_val)
                        lines.append(f"    {c_type} _{i};")
            elif isinstance(t, QRecordType):
                lines.append("    QRecordHeader header;")
                if not t.fields:
                    lines.append("    char _unused;")
                else:
                    for f in sorted(t.fields, key=lambda fld: fld.name):
                        c_type = self.c_type(f.type_val)
                        lines.append(f"    {c_type} qf_{f.name};")
            elif isinstance(t, QOptionType):
                lines.append("    int64_t tag;")
                payload_branches = [o for o in t.options if o.payload_type is not None]
                if payload_branches:
                    lines.append("    union {")
                    for o in payload_branches:
                        pt = o.payload_type
                        if isinstance(pt, QTupleType):
                            lines.append(f"        struct {tag_name}_{o.name}_payload {{")
                            for i, f in enumerate(pt.value_fields):
                                c_f_type = self.c_type(f.type_val)
                                f_ident = f"_{i}" if not f.name else f"_{i}"
                                lines.append(f"            {c_f_type} {f_ident};")
                            lines.append(f"        }} {o.name};")
                        elif isinstance(pt, QRecordType):
                            lines.append(f"        struct {tag_name}_{o.name}_payload {{")
                            for f in sorted(pt.fields, key=lambda fld: fld.name):
                                c_f_type = self.c_type(f.type_val)
                                lines.append(f"            {c_f_type} qf_{f.name};")
                            lines.append(f"        }} {o.name};")
                        else:
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
                key=lambda p: (type_to_c_tag(p[0]), type_to_c_tag(p[1])),
            ):
                tgt_tag = type_to_c_tag(tgt)
                src_tag = type_to_c_tag(src)
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

        desc_fn gives the descriptor expression of a component type, as c_type_descriptor does.
        """
        lines: list[str] = []
        forms: dict[str, list[DescriptorForm]] = {}
        seen_tags: set[str] = set()

        def visit(t: Optional[QType]) -> None:
            if t is None:
                return
            try:
                form = descriptor_form(t, self.record_ctx)
            except MissingDescriptorError:
                return
            if form.kind in ("base", "bound_var") or form.tag in seen_tags:
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

        # Descriptors of unfolded recursive types may name tuple and record structs that the program's own types
        # do not (a recursive occurrence is named by its unfolding rather than as QVal); their layouts are the same,
        # but the structs must be defined for offsetof and sizeof
        defined = {name for name, _ in agg_types}
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
            lines.append("")

        lines.append("/* Static runtime type descriptors for compound and opaque types */")
        for form in forms.get("opaque", []):
            lines.extend(type_descriptor(form.tag, "QTYPE_KIND_OPAQUE", form.name, "sizeof(QVal)", "NULL"))
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
                f"    .quantifier_count = {len(quants)},",
                f"    .quantifier_bounds = {bounds},",
            ]
            if params:
                lines.append("static const struct {")
                lines.append("    size_t param_count;")
                lines.append("    const QTypeDescriptor *result_type;")
                lines.append("    QFunAdapter adapt;")
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
            lines.extend(type_descriptor(tag, "QTYPE_KIND_FUN", descriptor_display_name(form.type), "sizeof(QClosure *)", f"&qfun_desc_{tag}"))
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
            lines.extend(type_descriptor(tag, "QTYPE_KIND_AUTO", descriptor_display_name(auto_t), "sizeof(QAuto *)", f"&qauto_desc_{tag}"))
            lines.append("")

        for form in forms.get("exception", []):
            tag = form.tag
            lines.append(f"static const QExceptionTypeDescriptor qexc_desc_{tag} Q_UNUSED = {{")
            lines.append(f"    .payload_type = {desc_fn(form.type.payload_type)},")
            lines.append("};")
            lines.extend(type_descriptor(tag, "QTYPE_KIND_EXCEPTION", descriptor_display_name(form.type), "sizeof(void *)", f"&qexc_desc_{tag}"))
            lines.append("")

        for form in forms.get("array", []):
            tag = form.tag
            lines.append(f"static const QArrayTypeDescriptor qarr_desc_{tag} Q_UNUSED = {{")
            lines.append(f"    .element_type = {desc_fn(form.type.element_type)},")
            lines.append("};")
            lines.extend(type_descriptor(tag, "QTYPE_KIND_ARRAY", descriptor_display_name(form.type), "sizeof(void *)", f"&qarr_desc_{tag}"))
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
                lines.extend(type_descriptor(tag, "QTYPE_KIND_RECORD", descriptor_display_name(qtype), f"sizeof(struct {tag})", f"&qrec_desc_{tag}"))
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
            lines.extend(type_descriptor(tag, "QTYPE_KIND_TUPLE", descriptor_display_name(qtype), f"sizeof(struct {struct_name})", f"&qtup_desc_{tag}"))
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
            lines.extend(type_descriptor(tag, kind_str, descriptor_display_name(qtype), size_str, f"&qvar_desc_{tag}"))
            lines.append("")
        return lines

    def emit_environment_structs(self, lifted_lambdas: list[CLambdaInfo]) -> list[str]:
        lines: list[str] = []
        capturing_lambdas = [l for l in lifted_lambdas if l.free_vars]
        if capturing_lambdas:
            lines.append("/* Environment structs for capturing closures */")
            for l in capturing_lambdas:
                lines.append(f"{l.env_struct_name} {{")
                for vname, vtype in l.free_vars:
                    c_type = self.c_type(vtype)
                    lines.append(f"    {c_type} {mangle_ident(vname)};")
                lines.append("};")
                lines.append("")
        return lines

    def emit_top_vars_declarations(
        self,
        top_vars: list[tuple[str, TypedExpr, Any]],
        var_dict_names: Optional[dict[str, str]] = None,
    ) -> list[str]:
        lines: list[str] = []
        if top_vars:
            for name, val, symbol in top_vars:
                if symbol.type_val is not OK_TYPE:
                    c_ident = mangle_ident(name)
                    if isinstance(symbol.type_val, QRecordType):
                        lines.append(f"static QRecordVal {c_ident};")
                    else:
                        c_type = self.c_type(symbol.type_val)
                        lines.append(f"static {c_type} {c_ident};")
            lines.append("")
        return lines

    def emit_forward_declarations_and_trampolines(
        self,
        top_funs: list[tuple[str, TypedFun, Any]],
        lifted_lambdas: list[CLambdaInfo],
        val_referenced_top_funs: set[str],
        top_funs_dict: dict[str, tuple[TypedFun, Any]],
    ) -> list[str]:
        lines: list[str] = []

        if top_funs:
            lines.append("/* Forward declarations for top-level functions */")
            for name, fun, _sym in top_funs:
                quants, inner = self.collect_fun_quantifiers(fun.type_val)
                ret_type = inner.result_type if isinstance(inner, QFunType) else inner
                c_name = mangle_ident(name)
                ret_c = "void" if ret_type is OK_TYPE else (
                    "QRecordVal"
                    if isinstance(ret_type, QRecordType)
                    else self.c_type(ret_type)
                )
                decls, _ = self.param_signatures(fun.params, quants)
                param_sig = "void" if not decls else ", ".join(decls)
                lines.append(f"static Q_UNUSED {ret_c} {c_name}({param_sig});")
            lines.append("")

        if lifted_lambdas:
            lines.append("/* Forward declarations for lifted lambdas */")
            for l in lifted_lambdas:
                quants, _ = self.collect_fun_quantifiers(l.fun.type_val)
                ret_type = l.fun.type_val.result_type if isinstance(l.fun.type_val, QFunType) else l.fun.type_val
                if isinstance(ret_type, QAllType):
                    _, inner = self.collect_fun_quantifiers(ret_type)
                    ret_type = inner.result_type if isinstance(inner, QFunType) else inner
                ret_c = "void" if ret_type is OK_TYPE else (
                    "QRecordVal"
                    if isinstance(ret_type, QRecordType)
                    else self.c_type(ret_type)
                )
                decls, _ = self.param_signatures(l.fun.params, quants)
                param_sigs = ["void *_raw_env"] + decls
                sig = ", ".join(param_sigs)
                lines.append(f"static Q_UNUSED {ret_c} {l.c_fn_name}({sig});")
            lines.append("")

        non_capturing = [l for l in lifted_lambdas if not l.free_vars]
        if non_capturing:
            lines.append("/* Static closures for non-capturing lambdas */")
            for l in non_capturing:
                lines.append(f"static Q_UNUSED QClosure {l.closure_var_name} = {{ (void *){l.c_fn_name}, NULL }};")
            lines.append("")

        if val_referenced_top_funs:
            lines.append("/* Trampoline functions and static closures for first-class top-level functions */")
            for name in sorted(val_referenced_top_funs):
                fun, _ = top_funs_dict[name]
                c_name = mangle_ident(name)
                tramp_name = f"{c_name}_trampoline"
                quants, inner = self.collect_fun_quantifiers(fun.type_val)
                ret_type = inner.result_type if isinstance(inner, QFunType) else inner
                ret_c = "void" if ret_type is OK_TYPE else (
                    "QRecordVal"
                    if isinstance(ret_type, QRecordType)
                    else self.c_type(ret_type)
                )
                decls, forward_args = self.param_signatures(fun.params, quants)
                lines.extend(
                    emit_trampoline(
                        tramp_name,
                        ret_c,
                        decls,
                        f"{c_name}({', '.join(forward_args)})",
                        ret_type is OK_TYPE,
                        unused=True,
                    )
                )
                lines.append(f"static Q_UNUSED QClosure {c_name}_closure = {{ (void *){tramp_name}, NULL }};")
                lines.append("")
        return lines
