"""Quest Canonical S-Expression Pretty Printer and Compact Type Formatter."""

from __future__ import annotations

from typing import Any, Optional, Union

from quest.types.model import (
    BOOL_TYPE,
    BOTTOM_TYPE,
    CHAR_TYPE,
    DYNAMIC_TYPE,
    EXCEPTION_TYPE,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    TYPE_KIND,
    QAbstractType,
    QAliasType,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QBoolType,
    QCharType,
    QExceptionType,
    QExternalType,
    QFunType,
    QIntType,
    QKind,
    QKindVar,
    QOkType,
    QOptionField,
    QOptionType,
    QOutType,
    QPathType,
    QPowerKind,
    QRealType,
    QRecGroupType,
    QRecType,
    QRecordField,
    QRecordType,
    QStringType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QType,
    QTypeApp,
    QTypeFun,
    QTypeKind,
    QTypeVar,
    QVariantField,
    QVariantType,
    QVarType,
    register_type_formatter,
    unalias,
)

# ============================================================================
# 11. Canonical S-Expression Pretty Printer (qtype_dump)
# ============================================================================

def qtype_dump(item: Union[QType, QKind], indent: int = 0) -> str:
    """Formats a QType or QKind into a canonical 2-space indented S-expression string."""
    pad = "  " * indent
    match item:
        case (QIntType() | QRealType() | QBoolType() | QCharType() | QStringType()
              | QOkType() | QExceptionType() | QTypeKind()):
            return f"({item.__class__.__name__})"

        case QPowerKind(bound=bound):
            return f"({item.__class__.__name__}\n{pad}  :bound {qtype_dump(bound, indent + 1)})"

        case QAllKind(param_name=pname, param_kind=pkind, result_kind=rkind):
            return (
                f"({item.__class__.__name__}\n"
                f"{pad}  :param '{pname}'\n"
                f"{pad}  :param_kind {qtype_dump(pkind, indent + 1)}\n"
                f"{pad}  :result_kind {qtype_dump(rkind, indent + 1)})"
            )

        case QTypeVar(name=name, symbol_id=sym_id) | QAbstractType(name=name, symbol_id=sym_id) \
             | QKindVar(name=name, symbol_id=sym_id):
            return f"({item.__class__.__name__} '{name}' #{sym_id})"

        case QPathType(root_name=rname, root_symbol_id=rsym_id, field_name=fname):
            return f"(QPathType '{rname}.{fname}' #{rsym_id})"

        case QTupleType(fields=fields):
            if not fields:
                return "(QTupleType)"
            field_strs = []
            for f in fields:
                match f:
                    case QTupleTypeFormal():
                        field_strs.append(
                            f"{pad}    (QTupleTypeFormal '{f.name}' #{f.symbol_id} :: {f.bound})"
                        )
                    case QTupleField():
                        field_strs.append(
                            f"{pad}    (QTupleField {f.name or ''}{' :var' if f.is_var else ''} "
                            f"{qtype_dump(f.type_val, indent + 2)})"
                        )
                    case QTupleTypeBinding():
                        field_strs.append(
                            f"{pad}    (QTupleTypeBinding '{f.name}' = {qtype_dump(f.type_val, indent + 2)})"
                        )
            f_joined = "\n".join(field_strs)
            return f"(QTupleType\n{pad}  :fields (\n{f_joined}\n{pad}  ))"

        case QRecordType(fields=fields):
            if not fields:
                return "(QRecordType)"
            field_strs = "\n".join(
                f"{pad}    (QRecordField '{f.name}'{ ' :var' if f.is_var else '' } "
                f"{qtype_dump(f.type_val, indent + 2)})"
                for f in fields
            )
            return f"(QRecordType\n{pad}  :fields (\n{field_strs}\n{pad}  ))"

        case QVariantType(variants=variants):
            if not variants:
                return "(QVariantType)"
            var_strs = "\n".join(
                f"{pad}    (QVariantField '{v.name}'"
                + (f" {qtype_dump(v.type_val, indent + 2)}" if v.type_val else "")
                + ")"
                for v in variants
            )
            return f"(QVariantType\n{pad}  :variants (\n{var_strs}\n{pad}  ))"

        case QOptionType(options=options):
            if not options:
                return "(QOptionType)"
            opt_strs = "\n".join(
                f"{pad}    (QOptionField '{o.name}'"
                + (f" {qtype_dump(o.payload_type, indent + 2)}" if o.payload_type else "")
                + ")"
                for o in options
            )
            return f"(QOptionType\n{pad}  :options (\n{opt_strs}\n{pad}  ))"

        case QFunType(params=params, result_type=res_type):
            param_strs = "\n".join(
                f"{pad}    (QParam '{p.name}'{ ' :var' if p.is_var else '' }{ ' :out' if p.is_out else '' } "
                f"{qtype_dump(p.type_val, indent + 2)})"
                for p in params
            )
            return (
                f"(QFunType\n"
                f"{pad}  :params (\n{param_strs}\n{pad}  )\n"
                f"{pad}  :result {qtype_dump(res_type, indent + 1)})"
            )

        case QVarType(element_type=elem) | QArrayType(element_type=elem) | QOutType(element_type=elem):
            return f"({item.__class__.__name__}\n{pad}  :element {qtype_dump(elem, indent + 1)})"

        case QAllType(quantifiers=quants, body=body):
            quant_strs = "\n".join(
                f"{pad}    (QQuantifier '{q.name}' #{q.symbol_id} {qtype_dump(q.bound, indent + 2)})"
                for q in quants
            )
            return (
                f"(QAllType\n"
                f"{pad}  :quantifiers (\n{quant_strs}\n{pad}  )\n"
                f"{pad}  :body {qtype_dump(body, indent + 1)})"
            )

        case QTypeApp(constructor=ctor, arguments=args):
            arg_strs = "\n".join(f"{pad}    {qtype_dump(arg, indent + 2)}" for arg in args)
            return (
                f"(QTypeApp\n"
                f"{pad}  :constructor {qtype_dump(ctor, indent + 1)}\n"
                f"{pad}  :arguments (\n{arg_strs}\n{pad}  ))"
            )

        case QRecType(var_name=vname, symbol_id=sym_id, bound=bound, body=body):
            return (
                f"(QRecType '{vname}' #{sym_id}\n"
                f"{pad}  :bound {qtype_dump(bound, indent + 1)}\n"
                f"{pad}  :body {qtype_dump(body, indent + 1)})"
            )

        case QRecGroupType(bindings=bindings):
            b_strs = "\n".join(
                f"{pad}    (Binding '{b[0]}' #{b[1]} {qtype_dump(b[2], indent + 2)} {qtype_dump(b[3], indent + 2)})"
                for b in bindings
            )
            return f"(QRecGroupType\n{pad}  :bindings (\n{b_strs}\n{pad}  ))"

        case _:
            return f"({item.__class__.__name__})"



_DISPLAY_NAME_LIMIT = 80


class _DisplayNameFull(Exception):
    """The display name being printed has reached its limit."""


def short_type_name(t: QType) -> str:
    """A short name for a type: the type as printed, cut off at 80 characters. A recursive type prints as its variable.

    It names runtime type descriptors in compiled code, which compare them structurally, so the name need not
    identify the type (printing a large recursive type in full can take megabytes). Echoed auto values show their
    type components by this name, as compiled code can.
    """
    parts: list[str] = []
    size = 0

    def emit(text: str) -> None:
        nonlocal size
        parts.append(text)
        size += len(text)
        if size > _DISPLAY_NAME_LIMIT:
            raise _DisplayNameFull()

    def walk(t: Optional[QType]) -> None:
        if t is None:
            return
        t = unalias(t.prune() if hasattr(t, "prune") else t)
        match t:
            case QRecordType():
                emit("Record")
                for f in t.fields:
                    emit(f" {'var ' if f.is_var else ''}{f.name}: ")
                    walk(f.type_val)
                emit(" end")
            case QTupleType():
                emit("Tuple")
                for f in t.value_fields:
                    emit(f" {'var ' if f.is_var else ''}{f.name}: " if f.name else " :")
                    walk(f.type_val)
                emit(" end")
            case QVariantType() | QOptionType():
                emit("Variant" if isinstance(t, QVariantType) else "Option")
                cases = (
                    [(v.name, v.type_val) for v in t.variants] if isinstance(t, QVariantType)
                    else [(o.name, o.payload_type) for o in t.options]
                )
                for name, payload in cases:
                    emit(f" {name}")
                    if payload is not None:
                        emit(": ")
                        walk(payload)
                emit(" end")
            case QArrayType():
                emit("Array(")
                walk(t.element_type)
                emit(")")
            case QExceptionType():
                emit("Exception(")
                walk(t.payload_type)
                emit(")")
            case QFunType():
                emit("Fun(")
                for i, p in enumerate(t.params):
                    emit(f"{' ' if i else ''}{'var ' if p.is_var else 'out ' if p.is_out else ''}{p.name}: ")
                    walk(p.type_val)
                emit(") ")
                walk(t.result_type)
            case QAllType():
                emit("All(" + " ".join(q.name for q in t.quantifiers) + ") ")
                walk(t.body)
            case QAutoType():
                emit(f"Auto {t.type_param} with")
                for f in t.signature:
                    emit(f" {'var ' if f.is_var else ''}{f.name}: ")
                    walk(f.type_val)
                emit(" end")
            case QRecType():
                emit(t.var_name)
            case QTypeApp():
                walk(t.constructor)
                emit("(")
                for i, a in enumerate(t.arguments):
                    if i:
                        emit(" ")
                    walk(a)
                emit(")")
            case QRecGroupType() | QTypeFun():
                emit(type(t).__name__)
            case _:
                emit(str(t))

    try:
        walk(t)
    except _DisplayNameFull:
        return "".join(parts)[:_DISPLAY_NAME_LIMIT] + "..."
    return "".join(parts)


def format_type_compact(
    t: Union[QType, QKind, None],
    env: Optional[Any] = None,
    visited_ids: Optional[set[int]] = None,
    depth: int = 0,
) -> str:
    """Formats a QType or QKind into a compact, human-readable string with alias awareness and bounded recursion."""
    if t is None:
        return ""
    if visited_ids is None:
        visited_ids = set()

    # 1. Alias references print as written
    if isinstance(t, QAliasType):
        return t.name

    # 2. Primitives and Singletons
    if t is INT_TYPE:
        return "Int"
    if t is REAL_TYPE:
        return "Real"
    if t is BOOL_TYPE:
        return "Bool"
    if t is CHAR_TYPE:
        return "Char"
    if t is STRING_TYPE:
        return "String"
    if t is OK_TYPE:
        return "Ok"
    if t is DYNAMIC_TYPE:
        return "Dynamic"
    if t is BOTTOM_TYPE:
        return "Bottom"
    if t is EXCEPTION_TYPE:
        return "Exception"
    if t is TYPE_KIND:
        return "TYPE"

    # 3. Kinds
    match t:
        case QPowerKind():
            return f"POWER({format_type_compact(t.bound, env, visited_ids, depth)})"
        case QAllKind():
            p_str = format_type_compact(t.param_kind, env, visited_ids, depth)
            r_str = format_type_compact(t.result_kind, env, visited_ids, depth)
            return f"All({t.param_name} :: {p_str}) {r_str}"

        # 4. Symbol identifiers and paths
        case QTypeVar() | QAbstractType():
            return t.name
        case QPathType():
            return f"{t.root_name}.{t.field_name}"
        case QExternalType():
            return t.name if t.name else f'external "{t.c_type}"'

        # 5. Type constructor containers
        case QArrayType():
            return f"Array({format_type_compact(t.element_type, env, visited_ids, depth)})"
        case QVarType():
            return f"Var({format_type_compact(t.element_type, env, visited_ids, depth)})"
        case QOutType():
            return f"Out({format_type_compact(t.element_type, env, visited_ids, depth)})"

        # 6. Type Application
        case QTypeApp():
            ctor_str = format_type_compact(t.constructor, env, visited_ids, depth)
            args_str = " ".join(format_type_compact(arg, env, visited_ids, depth) for arg in t.arguments)
            return f"{ctor_str}({args_str})" if args_str else f"{ctor_str}()"

        # 7. Type-level Functions
        case QTypeFun():
            if depth > 2:
                return "Fun(...)"
            params_str = " ".join(
                f"{p.name} :: {format_type_compact(p.bound, env, visited_ids, depth + 1)}"
                for p in t.params
            )
            body_str = format_type_compact(t.body, env, visited_ids, depth + 1)
            return f"Fun({params_str}) {body_str}"

        # 8. Function Type
        case QFunType():
            if depth > 3:
                return "Fun(...)"
            p_items = []
            for p in t.params:
                prefix = "var " if p.is_var else ("out " if p.is_out else "")
                t_s = format_type_compact(p.type_val, env, visited_ids, depth + 1)
                p_items.append(f"{prefix}{p.name}: {t_s}" if p.name else t_s)
            params_str = " ".join(p_items)
            res_str = format_type_compact(t.result_type, env, visited_ids, depth + 1)
            return f"Fun({params_str}): {res_str}"

        # 9. All Quantifier Type
        case QAllType():
            if depth > 3:
                return "All(...) ..."
            quants_str = " ".join(str(q) for q in t.quantifiers)
            body_str = format_type_compact(t.body, env, visited_ids, depth + 1)
            return f"All({quants_str}) {body_str}"

        # 10. Records (Module check first)
        case QRecordType():
            if t.provenance:
                return f"Module '{t.provenance}'"
            if depth > 3:
                return "Record ... end"
            f_strs = " ".join(
                f"{'var ' if f.is_var else ''}{f.name}: {format_type_compact(f.type_val, env, visited_ids, depth + 1)}"
                for f in t.fields
            )
            return f"Record {f_strs} end" if f_strs else "Record end"

        # 11. Tuples
        case QTupleType():
            if depth > 3:
                return "Tuple ... end"
            f_parts: list[str] = []
            for f in t.fields:
                match f:
                    case QTupleField():
                        var_p = "var " if f.is_var else ""
                        t_str = format_type_compact(f.type_val, env, visited_ids, depth + 1)
                        f_parts.append(f"{var_p}{f.name}: {t_str}" if f.name else f"{var_p}{t_str}")
                    case QTupleTypeBinding():
                        t_str = format_type_compact(f.type_val, env, visited_ids, depth + 1)
                        f_parts.append(f"Let {f.name} = {t_str}")
                    case QTupleTypeFormal():
                        k_str = format_type_compact(f.bound, env, visited_ids, depth + 1)
                        f_parts.append(f"Type {f.name} :: {k_str}")
                    case _:
                        f_parts.append(str(f))
            elems_str = " ".join(f_parts)
            return f"Tuple {elems_str} end" if elems_str else "Tuple end"

        # 12. Variants and Options
        case QVariantType():
            if depth > 3:
                return "Variant ... end"
            v_strs = " ".join(
                f"{'var ' if v.is_var else ''}{v.name}: {format_type_compact(v.type_val, env, visited_ids, depth + 1)}"
                if v.type_val is not OK_TYPE and v.type_val is not None else v.name
                for v in t.variants
            )
            return f"Variant {v_strs} end" if v_strs else "Variant end"
        case QOptionType():
            if depth > 3:
                return "Option ... end"
            o_strs = " ".join(
                f"{o.name} with {format_type_compact(o.payload_type, env, visited_ids, depth + 1)}"
                if o.payload_type is not None else o.name
                for o in t.options
            )
            return f"Option {o_strs} end" if o_strs else "Option end"

        # 13. Recursive Types (Bounded unfold / self-reference handling)
        case QRecType():
            if t.symbol_id in visited_ids or depth > 1:
                return t.var_name
            visited_ids = visited_ids | {t.symbol_id}
            b_str = format_type_compact(t.bound, env, visited_ids, depth + 1)
            body_str = format_type_compact(t.body, env, visited_ids, depth + 1)
            return f"Rec({t.var_name} :: {b_str}) {body_str}"
        case QRecGroupType():
            if t.current_symbol_id in visited_ids or depth > 1:
                return t.current_name
            visited_ids = visited_ids | {b[1] for b in t.bindings}
            name, _, bound, body = t.bindings[t.active_index]
            b_str = format_type_compact(bound, env, visited_ids, depth + 1)
            body_str = format_type_compact(body, env, visited_ids, depth + 1)
            return f"Rec({name} :: {b_str}) {body_str}"
        case _:
            return str(t)


# Register compact formatter for QType.format()
register_type_formatter(format_type_compact)

