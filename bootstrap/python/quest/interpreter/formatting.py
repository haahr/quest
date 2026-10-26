"""Printing values by their types, for the interpreters: a value as its static type shows it (Cardelli §5.3), as
compiled code prints it from the type's descriptor, and a top-level phrase's result in interactive style.
"""

from __future__ import annotations

from typing import Optional

from quest.types import (
    OK_TYPE,
    QAbstractType,
    QAllType,
    QArrayType,
    QAutoType,
    QFunType,
    QOptionType,
    QPathType,
    QRecordType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QType,
    QTypeApp,
    QTypeVar,
    QVariantType,
    auto_payload_type,
    short_type_name,
    unalias,
    unfold_head,
)
from quest.typechecker.typed_ast import (
    TypedDefKind,
    TypedException,
    TypedExpr,
    TypedExprStmt,
    TypedImport,
    TypedInterface,
    TypedLetType,
    TypedLetTypeGroup,
    TypedLetValue,
    TypedLetValueGroup,
    TypedModule,
    TypedNode,
)
from quest.values.model import (
    QArray,
    QAutoVal,
    QOk,
    QOption,
    QRecord,
    QRef,
    QTuple,
    QTypeValue,
    QValue,
    QVariant,
    QWord,
    qvalue_to_str,
)


def format_value_with_type(val: QValue, typ: Optional[QType] = None) -> str:
    """Formats a runtime value with respect to its static type (Cardelli §5.3).

    The type decides what is shown, all the way down, so that compiled code (quest_print_typed) can print the same
    from the value's type descriptor: a record shows its type's fields, a function is <fun>, and a value of an
    abstract type is <hidden>.
    """
    if typ is None:
        return qvalue_to_str(val)
    return _format_typed(val, typ, set())


def exposed_type(typ: QType) -> QType:
    """typ with aliases removed, recursive types unfolded, and type operator applications reduced."""
    typ = unalias(typ)
    while (unfolded := unfold_head(typ)) is not None:
        typ = unalias(unfolded)
    return typ


def _format_typed(val: QValue, typ: QType, visited: set[int]) -> str:
    if isinstance(val, QRef):
        val = val.deref()
    typ = exposed_type(typ)

    # A value of an abstract type, such as a module's T, is hidden, so that the interpreter and compiled code (which
    # cannot see a separately compiled module's representation) agree. Word.T is a library type with literals of
    # its own.
    match typ:
        case QPathType() | QAbstractType() | QTypeApp():
            return "<hidden>"
        case QTypeVar() if not isinstance(val, QWord):
            return "<hidden>"
        case QFunType() | QAllType():
            return "<fun>"

    match val, typ:
        case QTypeValue(), _:
            if val.bound:
                return f"<Hidden>::{val.bound}"
            return "<Hidden>::TYPE"
        case QAutoVal(), QAutoType():
            components = _format_typed(val.value, auto_payload_type(typ, val.type_val), visited)
            components = components.removeprefix("tuple").removesuffix("end").strip()
            # The type component is shown as compiled code shows it, by its runtime descriptor's name
            type_name = short_type_name(val.type_val)
            return f"auto :{type_name} with {components} end" if components else f"auto :{type_name} with end"
        case QTuple() | QRecord() | QArray(), _:
            if id(val) in visited:
                opening = {QTuple: "tuple", QRecord: "record", QArray: "array of"}[type(val)]
                return f"{opening} ... end"
            visited.add(id(val))
            try:
                return _format_aggregate(val, typ, visited)
            finally:
                visited.remove(id(val))
        case QOption(), QOptionType():
            found = typ.get_option(val.tag)
            if found is None or found.payload_type is None or val.payload is None:
                return f"option {val.tag} end"
            return f"option {val.tag} with {_format_typed(val.payload, found.payload_type, visited)} end"
        case QVariant(), QVariantType():
            found = typ.get_variant(val.tag)
            if found is None or found.type_val is None or unalias(found.type_val) is OK_TYPE or val.payload is None:
                return f"variant {val.tag} end"
            return f"variant {val.tag} with {_format_typed(val.payload, found.type_val, visited)} end"
        case _:
            return qvalue_to_str(val)


def _format_aggregate(val: QTuple | QRecord | QArray, typ: QType, visited: set[int]) -> str:
    match val, typ:
        case QTuple(), QTupleType():
            parts: list[str] = []
            elem_idx = 0
            for comp in typ.components:
                match comp:
                    case QTupleTypeFormal():
                        parts.append(f"<Hidden>::{comp.bound}")
                        elem_idx += 1
                    case QTupleTypeBinding():
                        parts.append(f"Let {comp.name} = {comp.type_val}")
                        elem_idx += 1
                    case QTupleField():
                        if elem_idx < len(val.elements):
                            elem_str = _format_typed(val.elements[elem_idx], comp.type_val, visited)
                            parts.append(f"{comp.name}={elem_str}" if comp.name else elem_str)
                            elem_idx += 1
            return f"tuple {' '.join(parts)} end" if parts else "tuple end"
        case QRecord(), QRecordType():
            fields = [
                f"{f.name}={_format_typed(val.fields[f.name], f.type_val, visited)}"
                for f in sorted(typ.fields, key=lambda f: f.name)
                if f.name in val.fields
            ]
            return f"record {' '.join(fields)} end" if fields else "record end"
        case QArray(), QArrayType():
            elems = [_format_typed(e, typ.element_type, visited) for e in val.elements]
            return f"array of {' '.join(elems)} end" if elems else "array of end"
        case _:
            return val.to_str(visited)


def format_interactive_result(
    phrase: Optional[TypedNode],
    val: Optional[QValue],
) -> str:
    """Formats the result of evaluating a top-level phrase in Cardelli interactive style."""
    if phrase is None or val is None:
        return ""

    match phrase:
        case TypedLetValue(name=name, symbol=symbol):
            var_str = "var " if symbol.is_var else ""
            type_str = str(symbol.type_val)
            val_str = format_value_with_type(val, symbol.type_val)
            return f"let {var_str}{name}:{type_str} = {val_str}"

        case TypedLetType(name=name, symbol=symbol):
            kind_str = str(symbol.kind)
            if symbol.definition is not None:
                return f"Let {name}::{kind_str} = {symbol.definition}"
            return f"Let {name}::{kind_str}"

        case TypedLetTypeGroup(members=members):
            return "\n".join(format_interactive_result(member, val) for member in members)

        case TypedLetValueGroup(members=members):
            assert isinstance(val, QTuple)
            return "\n".join(
                format_interactive_result(member, member_val) for member, member_val in zip(members, val.elements)
            )

        case TypedDefKind(name=name, symbol=symbol):
            kind_str = str(symbol.kind)
            return f"DEF {name} = {kind_str}"

        case TypedImport() | TypedInterface() | TypedModule():
            return ""

        case TypedExprStmt(expr=TypedException(name=name)):
            return f"exception {name}"

        case TypedExprStmt(expr=inner_expr):
            if isinstance(val, QOk):
                return ""
            val_str = format_value_with_type(val, inner_expr.type_val)
            return f"{val_str} : {inner_expr.type_val}"

        case TypedException(name=name):
            return f"exception {name}"

        case TypedExpr():
            if isinstance(val, QOk):
                return ""
            val_str = format_value_with_type(val, phrase.type_val)
            return f"{val_str} : {phrase.type_val}"

        case _:
            return ""
