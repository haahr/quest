"""Quest Kind Synthesis, Checking, Well-Kindedness, and Operator Signatures."""

from __future__ import annotations

from typing import Any, Optional, Union

from quest.diagnostics import Diagnostic, DiagnosticRenderer, QuestCompilerError
from quest.types.model import (
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
    QTypeMeta,
    QTypeVar,
    QVariantField,
    QVariantType,
    QVarType,
    unalias,
)
from quest.types.subtyping import is_subkind, is_subtype

# ============================================================================
# 10. Kind Synthesis, Checking, and Well-Kindedness
# ============================================================================

class KindError(QuestCompilerError):
    """Raised when kind synthesis, kind checking, or well-kindedness
    verification fails."""

    def __init__(
        self,
        message: str,
        offset: int = 0,
        help_text: Optional[str] = None,
        notes: Optional[list[str]] = None,
        length: int = 1,
    ) -> None:
        super().__init__(message=message, offset=offset, length=length)
        self.help_text = help_text
        self.notes = notes or []

    def to_diagnostic(self, length: int = 1) -> Diagnostic:
        """Converts this error into a structured Diagnostic object."""
        return Diagnostic.make_error(
            message=self.message,
            offset=self.offset,
            length=length,
            help_text=self.help_text,
            notes=self.notes,
        )

    def format_with_source(self, source_map: Any, length: int = 1) -> str:
        """Renders a diagnostic message with underlined source context."""
        return DiagnosticRenderer.render_diagnostic(self.to_diagnostic(length), source_map)


def check_kind_well_formed(kind: QKind, env: Optional[Any] = None) -> None:
    """Verifies that a kind is well-formed according to Quest kind formation
    rules."""
    kind_lazy = kind.evaluate_lazily(env)
    match kind_lazy:
        case QTypeKind():
            return

        case QPowerKind(bound=bound):
            # Bound of a power kind MUST be a proper type of kind TYPE
            check_kind(bound, TYPE_KIND, env)
            return

        case QAllKind(
            param_name=param_name,
            param_id=param_id,
            param_kind=param_kind,
            result_kind=result_kind,
        ):
            check_kind_well_formed(param_kind, env)
            if env is not None:
                env.push_scope(f"kind_param_{param_name}")
                try:
                    env.current_scope.declare_type_variable(
                        name=param_name,
                        symbol_id=param_id,
                        kind=param_kind,
                    )
                    check_kind_well_formed(result_kind, env)
                finally:
                    env.pop_scope()
            else:
                check_kind_well_formed(result_kind, env)
            return

        case QKindVar(name=name, symbol_id=symbol_id):
            if env is not None:
                sym = env.lookup_kind_by_id(symbol_id)
                if sym is None:
                    sym = env.lookup_kind(name)
                if sym is None:
                    raise KindError(f"Unbound kind variable '{name}' (#{symbol_id})")
            return

        case _:
            raise KindError(f"Malformed or unsupported kind '{kind_lazy}'")



def check_kind(type_val: QType, expected_kind: QKind, env: Optional[Any] = None) -> None:
    """Checks that type_val has a kind that is a subkind of expected_kind.

    Against POWER(B) the check is subtyping, type_val <: B, rather than a
    comparison of kinds: a type's synthesized kind is TYPE (or its bound, for a
    type variable), not the POWER of each of its supertypes.
    """
    expected_lazy = expected_kind.evaluate_lazily(env)
    if isinstance(expected_lazy, QPowerKind):
        if is_subtype(type_val, expected_lazy.bound, env):
            return
        raise KindError(
            f"Kind mismatch: type '{type_val}' is not a subtype of bound '{expected_lazy.bound}'"
        )
    synthesized = synth_kind(type_val, env)
    if not is_subkind(synthesized, expected_lazy, env):
        raise KindError(
            f"Kind mismatch: type '{type_val}' has kind '{synthesized}', "
            f"which is not a subkind of expected kind '{expected_kind}'"
        )


# Kinds synthesized during the current top-level kind check, keyed by node
# identity. Elaborated types are DAGs (aliases are shared), so without this
# every shared subterm is re-checked on every path to it.
_kind_memo: Optional[dict[int, tuple[QType, QKind]]] = None
_kind_memo_env: Optional[Any] = None


def synth_kind(type_val: QType, env: Optional[Any] = None) -> QKind:
    """Synthesizes the most specific minimal kind K for type_val in the given
    environment.

    Results are memoized for the duration of the outermost call. That is sound
    because a node's kind depends only on the node and the binders in scope,
    which have unique symbol ids, so a shared node has the same kind wherever it
    occurs. Metavariables are not memoized (their kind follows their solution),
    and a nested call with a different environment bypasses the memo.
    """
    global _kind_memo, _kind_memo_env
    if isinstance(type_val, QTypeMeta):
        return _synth_kind_uncached(type_val, env)
    if _kind_memo is not None:
        if env is not _kind_memo_env:
            return _synth_kind_uncached(type_val, env)
        hit = _kind_memo.get(id(type_val))
        if hit is not None and hit[0] is type_val:
            return hit[1]
        kind = _synth_kind_uncached(type_val, env)
        _kind_memo[id(type_val)] = (type_val, kind)
        return kind

    _kind_memo, _kind_memo_env = {}, env
    try:
        kind = _synth_kind_uncached(type_val, env)
    finally:
        _kind_memo, _kind_memo_env = None, None
    return kind


def _synth_kind_uncached(type_val: QType, env: Optional[Any] = None) -> QKind:
    """Synthesizes the kind of type_val; recursive checks go through the
    memoizing synth_kind.

    Kinds classify types as types classify values. TYPE is the kind of the types
    of values. POWER(B) is the kind of B's subtypes, which is how a bounded type
    parameter is expressed: A <: Record x: Int end declares A with kind
    POWER(Record x: Int end). ALL(A::K) K' is the kind of a type operator, which
    applied to a type of kind K gives one of kind K'. Subkinding follows:
    POWER(B) is included in TYPE, and in POWER(B') when B <: B'.

    The kind synthesized is the most specific one: TYPE for a type built by a
    constructor (a record type is a type of values), a type variable's bound,
    ALL for a type operator, and for an application, the operator's result kind
    with the arguments substituted. Synthesis also checks that the type's parts
    are well kinded: that a field's type is a type of values, that each binder's
    bound is a well-formed kind, and that an operator's arguments have its
    parameter kinds. A binder's variables are declared in a scope pushed on env
    while its body is checked; without an environment, a variable is known by
    the bound it carries.
    """
    match type_val:
        case (QIntType() | QRealType() | QBoolType() | QCharType() | QStringType()
              | QOkType() | QExceptionType() | QExternalType()):
            return TYPE_KIND

        case QTupleType(fields=fields):
            if env is not None:
                env.push_scope("tuple_kind_check")
                try:
                    for f in fields:
                        match f:
                            case QTupleTypeFormal():
                                check_kind_well_formed(f.bound, env)
                                env.current_scope.declare_type_variable(
                                    name=f.name, symbol_id=f.symbol_id, kind=f.bound
                                )
                            case QTupleField():
                                check_kind(f.type_val, TYPE_KIND, env)
                            case QTupleTypeBinding():
                                check_kind(f.type_val, TYPE_KIND, env)
                                env.current_scope.declare_type_variable(
                                    name=f.name,
                                    symbol_id=env.fresh_symbol_id(),
                                    kind=f.bound or TYPE_KIND,
                                    definition=f.type_val,
                                )
                finally:
                    env.pop_scope()
            else:
                for f in fields:
                    if isinstance(f, QTupleTypeFormal):
                        check_kind_well_formed(f.bound, env)
                    elif isinstance(f, (QTupleField, QTupleTypeBinding)):
                        check_kind(f.type_val, TYPE_KIND, env)
            return TYPE_KIND

        case QRecordType(fields=fields):
            for f in fields:
                check_kind(f.type_val, TYPE_KIND, env)
            return TYPE_KIND

        case QVariantType(variants=variants):
            for v in variants:
                if v.type_val is not None:
                    check_kind(v.type_val, TYPE_KIND, env)
            return TYPE_KIND

        case QOptionType(options=options):
            for opt in options:
                if opt.payload_type is not None:
                    check_kind(opt.payload_type, TYPE_KIND, env)
            return TYPE_KIND

        case QFunType(params=params, result_type=res_type):
            for param in params:
                check_kind(param.type_val, TYPE_KIND, env)
            check_kind(res_type, TYPE_KIND, env)
            return TYPE_KIND

        case QVarType(element_type=elem) | QArrayType(element_type=elem) | QOutType(element_type=elem):
            check_kind(elem, TYPE_KIND, env)
            return TYPE_KIND

        case QTypeVar(name=name, symbol_id=sym_id, bound=bound):
            if bound is not None:
                return bound
            if env is not None:
                sym = env.lookup_type_by_id(sym_id)
                if sym is None:
                    sym = env.lookup_type(name)
                if sym is not None:
                    return sym.kind
            raise KindError(f"Unbound type variable '{name}' (#{sym_id})")

        case QAbstractType(bound=bound) | QPathType(bound=bound):
            check_kind_well_formed(bound, env)
            return bound

        case QAliasType(target=target):
            return synth_kind(target, env)

        case QTypeMeta():
            pruned = type_val.prune()
            if pruned is not type_val:
                return synth_kind(pruned, env)
            return type_val.bound

        case QAllType(quantifiers=quants, body=body):
            if env is not None:
                env.push_scope("all_type")
                try:
                    for q in quants:
                        check_kind_well_formed(q.bound, env)
                        env.current_scope.declare_type_variable(
                            name=q.name, symbol_id=q.symbol_id, kind=q.bound
                        )
                    check_kind(body, TYPE_KIND, env)
                finally:
                    env.pop_scope()
            else:
                for q in quants:
                    check_kind_well_formed(q.bound, env)
                check_kind(body, TYPE_KIND, env)
            return TYPE_KIND

        case QAutoType(type_param=param_name, symbol_id=sym_id, kind_bound=kbound, signature=sig):
            if env is not None:
                env.push_scope("auto_type")
                try:
                    check_kind_well_formed(kbound, env)
                    env.current_scope.declare_type_variable(
                        name=param_name, symbol_id=sym_id, kind=kbound
                    )
                    for f in sig:
                        check_kind(f.type_val, TYPE_KIND, env)
                finally:
                    env.pop_scope()
            else:
                check_kind_well_formed(kbound, env)
                for f in sig:
                    check_kind(f.type_val, TYPE_KIND, env)
            return TYPE_KIND

        case QRecType(var_name=vname, symbol_id=sym_id, bound=bound, body=body):
            check_kind_well_formed(bound, env)
            if env is not None:
                env.push_scope(f"rec_{vname}")
                try:
                    env.current_scope.declare_type_variable(
                        name=vname, symbol_id=sym_id, kind=bound
                    )
                    check_kind(body, bound, env)
                finally:
                    env.pop_scope()
            else:
                check_kind(body, bound, env)
            return bound

        case QRecGroupType(bindings=bindings, active_index=idx):
            if env is not None:
                env.push_scope("rec_group")
                try:
                    for b_name, b_id, b_kind, _ in bindings:
                        check_kind_well_formed(b_kind, env)
                        env.current_scope.declare_type_variable(
                            name=b_name, symbol_id=b_id, kind=b_kind
                        )
                    for _, _, b_kind, b_body in bindings:
                        check_kind(b_body, b_kind, env)
                finally:
                    env.pop_scope()
            return bindings[idx][2]

        case QTypeFun(params=formals, body=body):
            if env is not None:
                env.push_scope("type_fun")
                try:
                    for formal in formals:
                        check_kind_well_formed(formal.bound, env)
                        env.current_scope.declare_type_variable(
                            name=formal.name, symbol_id=formal.symbol_id, kind=formal.bound
                        )
                    body_kind = synth_kind(body, env)
                finally:
                    env.pop_scope()
            else:
                for formal in formals:
                    check_kind_well_formed(formal.bound, env)
                body_kind = synth_kind(body, env)

            result_kind = body_kind
            for formal in reversed(formals):
                result_kind = QAllKind(
                    param_name=formal.name,
                    param_id=formal.symbol_id,
                    param_kind=formal.bound,
                    result_kind=result_kind,
                )
            return result_kind

        case QTypeApp(constructor=ctor, arguments=args):
            ctor_kind = synth_kind(ctor, env).evaluate_lazily(env)
            for arg in args:
                if not isinstance(ctor_kind, QAllKind):
                    raise KindError(
                        f"Type application error: constructor '{ctor}' "
                        f"has non-operator kind '{ctor_kind}'"
                    )
                check_kind(arg, ctor_kind.param_kind, env)
                ctor_kind = ctor_kind.result_kind.substitute_types({
                    ctor_kind.param_id: arg
                }).evaluate_lazily(env)
            return ctor_kind

        case _:
            raise KindError(f"Cannot synthesize kind for unknown type node '{type_val}'")



def unfold_head(t: QType) -> Optional[QType]:
    """One step of exposing the structure of t: unfolds a recursive type or
    reduces an application of a type operator, or returns None when t is an
    application of anything else (such as an abstract type operator)."""
    if isinstance(t, (QRecType, QRecGroupType)):
        return t.unfold_lazily()
    if isinstance(t, QTypeApp):
        ctor = unalias(t.constructor)
        if isinstance(ctor, QTypeFun) and len(ctor.params) == len(t.arguments):
            return ctor.body.substitute({p.symbol_id: arg for p, arg in zip(ctor.params, t.arguments)})
    return None


_unfold_head = unfold_head


def _resolve_bound(t: QType, env: Optional[Any], wanted: tuple[type, ...]) -> Optional[QType]:
    """t, or the upper bound of a type variable or path type (through bounds
    that are themselves bounded type variables), if it is a type of one of the
    wanted classes; unfolds recursive types."""
    curr = t
    visited = set()
    unfolded: list[QType] = []
    while True:
        curr_lazy = curr.evaluate_lazily(env) if env is not None else unalias(curr)
        if isinstance(curr_lazy, wanted):
            return curr_lazy
        if isinstance(curr_lazy, (QRecType, QRecGroupType, QTypeApp)):
            if any(curr_lazy is seen for seen in unfolded):
                return None
            unfolded.append(curr_lazy)
            step = unfold_head(curr_lazy)
            if step is None:
                return None
            curr = step
            continue
        if (
            isinstance(curr_lazy, (QTypeVar, QAbstractType, QPathType))
            and isinstance(curr_lazy.bound, QPowerKind)
        ):
            sym_id = id(curr_lazy) if isinstance(curr_lazy, QPathType) else curr_lazy.symbol_id
            if sym_id in visited:
                return None
            visited.add(sym_id)
            curr = curr_lazy.bound.bound
        else:
            return None


def resolve_record_bound(t: QType, env: Optional[Any] = None) -> Optional[QRecordType]:
    """Resolves upper bound for a type variable or path type if bounded by a
    record type; unfolds recursive types."""
    return _resolve_bound(t, env, (QRecordType,))


def resolve_variant_bound(t: QType, env: Optional[Any] = None) -> Optional[QVariantType]:
    """Resolves upper bound for a type variable or path type if bounded by a
    variant type; unfolds recursive types."""
    return _resolve_bound(t, env, (QVariantType,))


def resolve_sum_bound(t: QType, env: Optional[Any] = None) -> Optional[Union[QVariantType, QOptionType]]:
    """Resolves upper bound for a type variable or path type if bounded by a
    variant or option type; unfolds recursive types."""
    return _resolve_bound(t, env, (QVariantType, QOptionType))


def resolve_tuple_bound(t: QType, env: Optional[Any] = None) -> Optional[QTupleType]:
    """Resolves upper bound for a type variable or path type if bounded by a
    tuple type; unfolds recursive types."""
    return _resolve_bound(t, env, (QTupleType,))


def resolve_option_bound(t: QType, env: Optional[Any] = None) -> Optional[QOptionType]:
    """Resolves an option type, unwrapping type applications, recursive types,
    or bounds."""
    curr = t
    visited = set()
    while True:
        curr = unalias(curr)
        if isinstance(curr, QOptionType):
            return curr
        if isinstance(curr, QRecType):
            curr = curr.body
            continue
        if isinstance(curr, QTypeApp):
            ctor = curr.constructor
            if env is not None and isinstance(ctor, (QTypeVar, QAbstractType, QPathType)):
                ctor = ctor.evaluate_lazily(env)
            if isinstance(ctor, QTypeFun):
                subst = {p.symbol_id: arg for p, arg in zip(ctor.params, curr.arguments)}
                curr = ctor.body.substitute(subst)
                continue
            elif env is not None:
                curr_lazy = curr.evaluate_lazily(env)
                if not isinstance(curr_lazy, QTypeApp):
                    curr = curr_lazy
                    continue
        if (
            isinstance(curr, (QTypeVar, QAbstractType, QPathType))
            and isinstance(curr.bound, QPowerKind)
        ):
            sym_id = id(curr) if isinstance(curr, QPathType) else curr.symbol_id
            if sym_id in visited:
                return None
            visited.add(sym_id)
            curr = curr.bound.bound
            continue
        if env is not None:
            curr_lazy = curr.evaluate_lazily(env)
            if curr_lazy is not curr and type(curr_lazy) is not type(curr):
                curr = curr_lazy
                continue
        return None


