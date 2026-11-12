"""The check that a recursive type is contractive in its variables (C succ X,
after Cardelli and Longo): each use of a recursive variable is guarded by a
type constructor. Rec(L) Tuple head: Int tail: L end is contractive, Rec(X) X
and Let Rec A = B and B = A are not. A type that is not has no unique meaning,
and unfolding it never reaches a constructor, which evaluate_lazily relies on.
Elaborating a recursive type declaration calls check_type_contractive, which
raises KindError.

The self-hosted counterpart is questlang/types/contractiveness;
docs/type-system.md §3.3 gives the rule."""

from __future__ import annotations

from typing import Any, Optional

from quest.diagnostics import TypeRecursionLimitExceeded
from quest.types.kinds import KindError
from quest.types.model import (
    MAX_TYPE_EXPANSION_DEPTH,
    QAllType,
    QArrayType,
    QAutoType,
    QBoolType,
    QBottomType,
    QCharType,
    QExceptionType,
    QFunType,
    QIntType,
    QOkType,
    QOptionType,
    QOutType,
    QPathType,
    QRealType,
    QRecGroupType,
    QRecType,
    QRecordType,
    QStringType,
    QTupleType,
    QType,
    QTypeApp,
    QTypeFun,
    QTypeMeta,
    QTypeVar,
    QVariantType,
    QVarType,
    unalias,
)


# ============================================================================
# 11. Recursive Type Contractiveness Verification (C \succ X)
# ============================================================================

def is_type_contractive(
    qtype: QType,
    recursive_var_ids: set[int],
    env: Optional[Any] = None,
    seen_aliases: Optional[set[int]] = None,
    depth: int = 0,
) -> bool:
    """Verifies that `qtype` is contractive in all variable IDs in
    `recursive_var_ids` (C \\succ X).

    According to Cardelli & Longo (1991, Section 2.4/2.9) and MacQueen, Plotkin
    & Sethi (1986):
    - Primitive types (Int, Bool, Top, etc.) are contractive in all X.
    - Type variable Y is contractive in X iff Y != X.
    - Type constructors (Record, Tuple, Option, Variant, Fun, Array, Var, Out)
      are contractive in X.
    - Universal quantifier All(X':K)B is contractive in X iff X not free in K
      and B \\succ X.
    - Type application (λ(X':K)B)(A) is contractive in X iff the beta-reduced
      body \\succ X.
    - Recursive type Rec(X')B is contractive in X iff B \\succ X' and B \\succ
      X.
    """
    if depth > MAX_TYPE_EXPANSION_DEPTH:
        raise TypeRecursionLimitExceeded(
            f"Type contractiveness check exceeded recursion depth of {MAX_TYPE_EXPANSION_DEPTH}"
        )
    seen = seen_aliases or set()
    qtype_lazy = qtype.evaluate_lazily(env)

    match qtype_lazy:
        case QTypeVar(symbol_id=sym_id):
            if sym_id in recursive_var_ids:
                return False
            if env is not None:
                sym = env.lookup_type_by_id(sym_id)
                if sym is not None and sym.definition is not None and sym_id not in seen:
                    return is_type_contractive(sym.definition, recursive_var_ids, env, seen | {sym_id}, depth + 1)
            return True

        # An unsolved metavariable (evaluate_lazily looks through a solved
        # one) is not a recursive variable, so it is contractive
        case QTypeMeta():
            return True

        case QRecType(symbol_id=inner_id, body=inner_body):
            return (
                is_type_contractive(inner_body, {inner_id}, env, seen, depth + 1)
                and is_type_contractive(inner_body, recursive_var_ids, env, seen, depth + 1)
            )

        case QRecGroupType(bindings=bindings, active_index=active_idx):
            all_group_ids = {b[1] for b in bindings}
            active_body = bindings[active_idx][3]
            return is_type_contractive(active_body, recursive_var_ids | all_group_ids, env, seen, depth + 1)

        case QAllType(quantifiers=quants, body=body):
            return is_type_contractive(body, recursive_var_ids, env, seen, depth + 1)

        case QTypeApp(constructor=ctor):
            # evaluate_lazily has already beta-reduced applications of type
            # functions, so the constructor here is opaque; the application is
            # contractive if the constructor is.
            return is_type_contractive(ctor.evaluate_lazily(env), recursive_var_ids, env, seen, depth + 1)

        case (
            QRecordType()
            | QTupleType()
            | QOptionType()
            | QVariantType()
            | QFunType()
            | QArrayType()
            | QVarType()
            | QOutType()
        ):
            # Guarded by constructor
            return True

        case (
            QOkType()
            | QBoolType()
            | QCharType()
            | QStringType()
            | QIntType()
            | QRealType()
            | QExceptionType()
            | QBottomType()
        ):
            return True

        case _:
            return True


def check_type_contractive(
    qtype: QType,
    recursive_var_ids: set[int],
    var_name: str,
    offset: int = 0,
    env: Optional[Any] = None,
) -> None:
    """Validates that `qtype` is contractive in `recursive_var_ids`, raising
    KindError if not."""
    if not is_type_contractive(qtype, recursive_var_ids, env):
        raise KindError(
            f"Recursive type '{var_name}' is not contractive; "
            "recursive type variable must be guarded by a constructor",
            offset=offset,
            help_text=(
                "ensure recursive variable appears inside a record, tuple, function, "
                "option, variant, or array type"
            ),
            notes=[
                f"definition of '{var_name}' refers directly to itself as a bare alias without a guarding constructor"
            ],
        )


