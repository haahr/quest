"""Quest Equi-Recursive Subtyping and Type Equivalence."""

from __future__ import annotations

from typing import Any, Optional

from quest.diagnostics import TypeRecursionLimitExceeded
from collections.abc import Iterator
from quest.types.model import (
    BOTTOM_TYPE,
    MAX_SUBTYPE_FUEL,
    OK_TYPE,
    QAbstractType,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QBoolType,
    QBottomType,
    QCharType,
    QExceptionType,
    QExternalType,
    QFunType,
    QIntType,
    QKind,
    QKindVar,
    QOkType,
    QOptionType,
    QOutType,
    QPathType,
    QPowerKind,
    QRealType,
    QRecGroupType,
    QRecType,
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
    QVariantType,
    QVarType,
    auto_matches_subtypes,
    structurally_equal,
    unalias,
)

# ============================================================================
# 9. Equi-Recursive Subtyping and Type Equivalence
# ============================================================================

# ----------------------------------------------------------------------------
# Subtype cache
# ----------------------------------------------------------------------------
#
# Results of subtyping proofs, keyed by the identities of hash-consed types and whether an environment
# was given (without one, aliases are not expanded). Entries hold the types they key on, so an id is
# never reused while its entry exists; pairs involving a metavariable are never cached, because
# is_subtype solves metavariables as a side effect.
#
# Why results are committed only when a top-level proof finishes: is_subtype proves goals about
# recursive types coinductively. To prove A <: B it assumes A <: B while checking the unfolding, and a
# recurrence of the pair counts as proved. A nested goal decided while such an assumption is still open
# may be True only because of it: for A = Rec(X) Record f: X g: Int end and
# B = Rec(Y) Record f: Y g: String end, field f gives A <: B (assumed) and field g gives
# Int <: String false, so the conditional True for f is wrong. Nothing about a result can change after
# a proof finishes (types are immutable, symbols resolve globally, metavariables are excluded); the only
# hazard is caching a result that depended on an assumption which the proof later refutes. Hence:
#
# - When a top-level proof returns True, every pair it decided or assumed is a true fact. In this
#   implementation a proof succeeds only if every nested goal succeeds (all nested goals are combined
#   with and; the type-variable bound check that may fail falls through only to False), so the pairs
#   on the trail form a consistent set of facts (a simulation). All of them are cached as True.
# - False results are always cached, even when decided mid-proof: extra coinductive assumptions can
#   only make more goals provable, so a goal that fails with them also fails without them.
# - Conditional True results of a proof that returns False are discarded.
#
# Symbol meanings only become more defined (a definition may arrive once, later than a reference), so
# the environment clears the cache when an id that some lookup saw as undefined gains a meaning.

SUBTYPE_CACHE: dict[tuple[int, int, bool], tuple[QType, QType, bool]] = {}
SUBTYPE_CACHE_LIMIT = 250_000
_SUBTYPE_CACHE = SUBTYPE_CACHE
_SUBTYPE_CACHE_LIMIT = SUBTYPE_CACHE_LIMIT


def clear_subtype_cache() -> None:
    _SUBTYPE_CACHE.clear()


def _subtype_cache_lookup(sub: QType, sup: QType, env: Optional[Any]) -> Optional[bool]:
    entry = _SUBTYPE_CACHE.get((id(sub), id(sup), env is None))
    if entry is None or entry[0] is not sub or entry[1] is not sup:
        return None
    return entry[2]


def _subtype_cache_store(sub: QType, sup: QType, env: Optional[Any], result: bool) -> None:
    if sub._has_meta or sup._has_meta:
        return
    if len(_SUBTYPE_CACHE) >= _SUBTYPE_CACHE_LIMIT:
        _SUBTYPE_CACHE.clear()
    _SUBTYPE_CACHE[(id(sub), id(sup), env is None)] = (sub, sup, result)


def _commit_proof(trail: SubtypeTrail, result: bool, env: Optional[Any]) -> None:
    """Enters a finished top-level proof's results in the cache (see the comment above)."""
    if result:
        for sub, sup, r in trail.results:
            _subtype_cache_store(sub, sup, env, r)
        for sub, sup in trail.assumed_pairs():
            _subtype_cache_store(sub, sup, env, True)
    else:
        for sub, sup, r in trail.results:
            if not r:
                _subtype_cache_store(sub, sup, env, False)


def is_type_equal(t1: QType, t2: QType, env: Optional[Any] = None) -> bool:
    """Checks equi-recursive type equivalence (t1 <: t2 and t2 <: t1).

    Both directions form one proof with one trail: once t1 <: t2 succeeds, every pair it assumed holds,
    so the reverse direction may rely on those assumptions too.
    """
    if t1 is t2:
        return True
    trail = SubtypeTrail()
    result = (_prove_subtype(t1, t2, env, trail, MAX_SUBTYPE_FUEL)
              and _prove_subtype(t2, t1, env, trail, MAX_SUBTYPE_FUEL))
    _commit_proof(trail, result, env)
    return result


class SubtypeTrail:
    """Coinductive assumptions of one subtyping proof: pairs (sub, sup) currently assumed to hold.

    Named type variables are keyed by symbol and everything else by object identity. The trail keeps
    every keyed object alive for the duration of the proof, so that an id can never be reused by a
    different (temporary) type and match an assumption it was not part of.
    """

    __slots__ = ("_assumed", "_keep_alive", "results")

    def __init__(self) -> None:
        self._assumed: set[tuple[Any, Any]] = set()
        self._keep_alive: list[QType] = []
        # (sub, sup, result) for every metavariable-free pair decided during the proof
        self.results: list[tuple[QType, QType, bool]] = []

    @staticmethod
    def key(t: QType) -> tuple[Any, ...]:
        if isinstance(t, (QTypeVar, QAbstractType)):
            return ("var", t.symbol_id)
        if isinstance(t, QPathType):
            return ("path", t.root_symbol_id, t.field_name)
        return ("obj", id(t))

    def pair(self, sub: QType, sup: QType) -> tuple[Any, Any]:
        return (self.key(sub), self.key(sup))

    def __contains__(self, pair: tuple[Any, Any]) -> bool:
        return pair in self._assumed

    def assume(self, pair: tuple[Any, Any], sub: QType, sup: QType) -> None:
        self._assumed.add(pair)
        self._keep_alive.append(sub)
        self._keep_alive.append(sup)

    def assumed_pairs(self) -> Iterator[tuple[QType, QType]]:
        """The (sub, sup) pairs assumed during the proof, in order."""
        it = iter(self._keep_alive)
        return zip(it, it)


# The fuel a comparison of quantified types costs (see the QAllType case of _prove_subtype_step)
_QUANTIFIER_FUEL = 500


def is_subtype(
    sub: QType,
    sup: QType,
    env: Optional[Any] = None,
    trail: Optional[SubtypeTrail] = None,
    fuel: int = MAX_SUBTYPE_FUEL,
) -> bool:
    """Checks if sub is a subtype of sup (sub <: sup) with coinductive cycle detection and fuel limit.

    A call without a trail is a top-level proof: its results are entered in the subtype cache when it
    finishes (see _commit_proof).
    """
    if trail is not None:
        return _prove_subtype(sub, sup, env, trail, fuel)
    if sub is sup:
        return True
    trail = SubtypeTrail()
    result = _prove_subtype(sub, sup, env, trail, fuel)
    _commit_proof(trail, result, env)
    return result


def _prove_subtype(sub: QType, sup: QType, env: Optional[Any], trail: SubtypeTrail, fuel: int) -> bool:
    """One subtyping goal within a proof: consults the cache, then records the result on the trail."""
    if sub is sup:
        return True
    cacheable = not (sub._has_meta or sup._has_meta)
    if cacheable:
        cached = _subtype_cache_lookup(sub, sup, env)
        if cached is not None:
            return cached
    result = _prove_subtype_step(sub, sup, env, trail, fuel)
    if cacheable:
        trail.results.append((sub, sup, result))
    return result


def _prove_subtype_step(sub: QType, sup: QType, env: Optional[Any], trail: SubtypeTrail, fuel: int) -> bool:
    """Decides sub <: sup structurally; nested goals go through _prove_subtype."""
    if fuel <= 0:
        raise TypeRecursionLimitExceeded(
            f"Subtyping proof exceeded step limit of {MAX_SUBTYPE_FUEL} steps "
            f"while checking ({sub} <: {sup})"
        )
    fuel -= 1

    # 0. Coinductive cycle detection for recursive types before lazy unfolding
    type_pair = trail.pair(sub, sup)
    if type_pair in trail:
        return True
    if isinstance(sub, (QRecType, QRecGroupType)) or isinstance(sup, (QRecType, QRecGroupType)):
        trail.assume(type_pair, sub, sup)

    # 1. Evaluate both types lazily to expose outermost constructors
    sub_lazy = sub.evaluate_lazily(env)
    sup_lazy = sup.evaluate_lazily(env)

    # 2. Reflexivity & identical instances (no Python structural == on QType)
    if sub_lazy is sup_lazy:
        return True
    if (
        isinstance(sub_lazy, (QTypeVar, QAbstractType, QPathType))
        and isinstance(sup_lazy, (QTypeVar, QAbstractType, QPathType))
        and SubtypeTrail.key(sub_lazy) == SubtypeTrail.key(sup_lazy)
    ):
        return True
    if (
        isinstance(sub_lazy, (QIntType, QRealType, QBoolType, QCharType, QStringType, QOkType))
        and type(sub_lazy) is type(sup_lazy)
    ):
        return True

    # 2b. Bottom type: subtype of all types
    if isinstance(sub_lazy, QBottomType):
        return True

    # 3. Metavariable resolution & unification
    if isinstance(sub_lazy, QTypeMeta):
        pruned = sub_lazy.prune()
        if pruned is not sub_lazy:
            return _prove_subtype(pruned, sup_lazy, env, trail, fuel)
        sub_lazy.instance = sup_lazy
        return True
    if isinstance(sup_lazy, QTypeMeta):
        pruned = sup_lazy.prune()
        if pruned is not sup_lazy:
            return _prove_subtype(sub_lazy, pruned, env, trail, fuel)
        sup_lazy.instance = sub_lazy
        return True

    # 4. Top types: in Quest, any proper type is a subtype of itself or upper bounds
    # 5. Coinductive trail check
    pair = trail.pair(sub_lazy, sup_lazy)
    if pair in trail:
        return True
    trail.assume(pair, sub_lazy, sup_lazy)

    # 6. Type Variable bound checking
    if isinstance(sub_lazy, (QTypeVar, QAbstractType, QPathType)):
        if sub_lazy.bound and isinstance(sub_lazy.bound, QPowerKind):
            if _prove_subtype(sub_lazy.bound.bound, sup_lazy, env, trail, fuel):
                return True

    # 7. Pattern matching across type pairs
    match (sub_lazy, sup_lazy):
        # Tuples: prefix match (Cardelli §7.1, §10.2), matching names, covariant elements / subkinds
        case (QTupleType(fields=sub_fields), QTupleType(fields=sup_fields)):
            if len(sub_fields) < len(sup_fields):
                return False
            curr_sup_fields = list(sup_fields)
            for idx in range(len(curr_sup_fields)):
                s_f = sub_fields[idx]
                t_f = curr_sup_fields[idx]
                match s_f, t_f:
                    case QTupleTypeFormal(), QTupleTypeFormal():
                        if s_f.name != t_f.name or not is_subkind(s_f.bound, t_f.bound, env):
                            return False
                        if t_f.symbol_id != s_f.symbol_id:
                            subst = {t_f.symbol_id: QTypeVar(s_f.name, s_f.symbol_id, s_f.bound)}
                            for rem_idx in range(idx + 1, len(curr_sup_fields)):
                                curr_sup_fields[rem_idx] = curr_sup_fields[rem_idx].substitute(subst)
                    case QTupleTypeBinding(), QTupleTypeFormal():
                        if s_f.name != t_f.name:
                            return False
                        if isinstance(t_f.bound, QPowerKind):
                            if not _prove_subtype(s_f.type_val, t_f.bound.bound, env, trail, fuel):
                                return False
                        subst = {t_f.symbol_id: s_f.type_val}
                        for rem_idx in range(idx + 1, len(curr_sup_fields)):
                            curr_sup_fields[rem_idx] = curr_sup_fields[rem_idx].substitute(subst)
                    case QTupleField(), QTupleField():
                        if t_f.name is not None and s_f.name != t_f.name:
                            return False
                        if t_f.is_var:
                            if not s_f.is_var:
                                return False
                            if not (_prove_subtype(s_f.type_val, t_f.type_val, env, trail, fuel)
                                    and _prove_subtype(t_f.type_val, s_f.type_val, env, trail, fuel)):
                                return False
                        else:
                            if not _prove_subtype(s_f.type_val, t_f.type_val, env, trail, fuel):
                                return False
                    case QTupleTypeBinding(), QTupleTypeBinding():
                        if s_f.name != t_f.name or not _prove_subtype(s_f.type_val, t_f.type_val, env, trail, fuel):
                            return False
                    case _:
                        return False
            return True

        # Records: width, depth, and mutable invariance
        case (QRecordType(), QRecordType()):
            for sup_field in sup_lazy.fields:
                sub_field = sub_lazy.get_field(sup_field.name)
                if sub_field is None:
                    return False
                if sup_field.is_var:
                    if not sub_field.is_var:
                        return False
                    if not (_prove_subtype(sub_field.type_val, sup_field.type_val, env, trail, fuel)
                            and _prove_subtype(sup_field.type_val, sub_field.type_val, env, trail, fuel)):
                        return False
                else:
                    if not _prove_subtype(sub_field.type_val, sup_field.type_val, env, trail, fuel):
                        return False
            return True

        # Variants: width and payload covariance
        case (QVariantType(), QVariantType()):
            for sub_var in sub_lazy.variants:
                sup_var = sup_lazy.get_variant(sub_var.name)
                if sup_var is None:
                    return False
                if sub_var.type_val is not None:
                    if sup_var.type_val is None:
                        return False
                    if sub_var.is_var or sup_var.is_var:
                        if not (_prove_subtype(sub_var.type_val, sup_var.type_val, env, trail, fuel)
                                and _prove_subtype(sup_var.type_val, sub_var.type_val, env, trail, fuel)):
                            return False
                    else:
                        if not _prove_subtype(sub_var.type_val, sup_var.type_val, env, trail, fuel):
                            return False
                elif sup_var.type_val is not None:
                    return False
            return True

        # Options: width and payload covariance
        case (QOptionType(), QOptionType()):
            for sub_opt in sub_lazy.options:
                sup_opt = sup_lazy.get_option(sub_opt.name)
                if sup_opt is None:
                    return False
                if sub_opt.payload_type is not None:
                    if sup_opt.payload_type is None:
                        return False
                    if not _prove_subtype(sub_opt.payload_type, sup_opt.payload_type, env, trail, fuel):
                        return False
                elif sup_opt.payload_type is not None:
                    return False
            return True

        # Functions: contravariant value params, invariant var params, covariant out params and result
        case (QFunType(), QFunType()):
            if len(sub_lazy.params) != len(sup_lazy.params):
                return False
            for s_param, t_param in zip(sub_lazy.params, sup_lazy.params):
                if s_param.is_var or t_param.is_var:
                    if s_param.is_var != t_param.is_var:
                        return False
                    if not (_prove_subtype(t_param.type_val, s_param.type_val, env, trail, fuel)
                            and _prove_subtype(s_param.type_val, t_param.type_val, env, trail, fuel)):
                        return False
                elif s_param.is_out or t_param.is_out:
                    if s_param.is_out != t_param.is_out:
                        return False
                    if not _prove_subtype(s_param.type_val, t_param.type_val, env, trail, fuel):
                        return False
                else:
                    if not _prove_subtype(t_param.type_val, s_param.type_val, env, trail, fuel):
                        return False
            return _prove_subtype(sub_lazy.result_type, sup_lazy.result_type, env, trail, fuel)

        # References (Var) & Arrays: invariant element type
        case (QVarType(element_type=s_elem), QVarType(element_type=t_elem)) | \
             (QArrayType(element_type=s_elem), QArrayType(element_type=t_elem)):
            if s_elem is t_elem:
                return True
            return (_prove_subtype(s_elem, t_elem, env, trail, fuel)
                    and _prove_subtype(t_elem, s_elem, env, trail, fuel))

        # Out parameters: contravariant
        case (QOutType(element_type=s_elem), QOutType(element_type=t_elem)):
            if s_elem is t_elem:
                return True
            return _prove_subtype(t_elem, s_elem, env, trail, fuel)

        # Exceptions: invariant payload type
        case (QExceptionType(payload_type=s_pay), QExceptionType(payload_type=t_pay)):
            if s_pay is t_pay:
                return True
            return (_prove_subtype(s_pay, t_pay, env, trail, fuel)
                    and _prove_subtype(t_pay, s_pay, env, trail, fuel))

        # Universal Quantifiers ([TIncl Π], A Semantic Basis for Quest §2): bounds contravariant, body covariant,
        # compared under the supertype's bounds. As in full F<: this is undecidable; fuel keeps it terminating
        case (QAllType(), QAllType()):
            if len(sub_lazy.quantifiers) != len(sup_lazy.quantifiers):
                return False
            # Both sides' quantifiers become fresh variables, with sup's bounds: either type may contain the other's
            # binders (a type compared with its own bound), which renaming one to the other's would capture
            from quest.types.env import allocate_symbol_id  # env imports this module

            # The bounds are compared within this proof, so that they share its fuel, and each comparison of
            # quantifiers costs much of it: a search that diverges through bounds (Pierce, Bounded quantification is
            # undecidable) runs out after a few levels, well within Python's stack, and fails as not a subtype
            if fuel <= _QUANTIFIER_FUEL:
                return False
            fuel -= _QUANTIFIER_FUEL
            sub_subst: dict[int, QType] = {}
            sup_subst: dict[int, QType] = {}
            for s_q, t_q in zip(sub_lazy.quantifiers, sup_lazy.quantifiers):
                fresh = QTypeVar(t_q.name, allocate_symbol_id(), t_q.bound.substitute_types(sup_subst))
                s_bound = s_q.bound.substitute_types(sub_subst)
                if isinstance(fresh.bound, QPowerKind) and isinstance(s_bound, QPowerKind):
                    if not _prove_subtype(fresh.bound.bound, s_bound.bound, env, trail, fuel):
                        return False
                elif not is_subkind(fresh.bound, s_bound, env):
                    return False
                sub_subst[s_q.symbol_id] = fresh
                sup_subst[t_q.symbol_id] = fresh
            return _prove_subtype(
                sub_lazy.body.substitute(sub_subst), sup_lazy.body.substitute(sup_subst), env, trail, fuel
            )

        # Auto types (Cardelli §6.7): subkind for the type component; for the signature, as for tuples, a
        # prefix match with matching names, covariant immutable and invariant mutable components
        case (QAutoType(), QAutoType()):
            if len(sub_lazy.signature) < len(sup_lazy.signature):
                return False
            if not is_subkind(sub_lazy.kind_bound, sup_lazy.kind_bound, env):
                return False
            subst = {
                sup_lazy.symbol_id: QTypeVar(sub_lazy.type_param, sub_lazy.symbol_id, sub_lazy.kind_bound)
            }
            for s_f, t_f in zip(sub_lazy.signature, sup_lazy.signature):
                if s_f.name != t_f.name or s_f.is_var != t_f.is_var:
                    return False
                t_type = t_f.type_val.substitute(subst)
                if not _prove_subtype(s_f.type_val, t_type, env, trail, fuel):
                    return False
                if t_f.is_var and not _prove_subtype(t_type, s_f.type_val, env, trail, fuel):
                    return False
            return True

        # Type Functions (Type Operators): parameter kinds match, bodies subtype under substitution
        case (QTypeFun(), QTypeFun()):
            if len(sub_lazy.params) != len(sup_lazy.params):
                return False
            subst = {
                t_p.symbol_id: QTypeVar(s_p.name, s_p.symbol_id, s_p.bound)
                for s_p, t_p in zip(sub_lazy.params, sup_lazy.params)
            }
            for s_p, t_p in zip(sub_lazy.params, sup_lazy.params):
                t_bound_renamed = t_p.bound.substitute_types(subst)
                if not is_kind_equal(s_p.bound, t_bound_renamed, env):
                    return False
            return _prove_subtype(sub_lazy.body, sup_lazy.body.substitute(subst), env, trail, fuel)

        # Type operator application (e.g. List.T(A))
        case (
            QTypeApp(constructor=s_c, arguments=s_args),
            QTypeApp(constructor=t_c, arguments=t_args),
        ):
            if len(s_args) != len(t_args) or not is_type_equal(s_c, t_c, env):
                return False
            for sa, ta in zip(s_args, t_args):
                if sa is ta:
                    continue
                if not (_prove_subtype(sa, ta, env, trail, fuel) and _prove_subtype(ta, sa, env, trail, fuel)):
                    return False
            return True

        # External Types: structural equality on underlying C type
        case (QExternalType(c_type=sub_c), QExternalType(c_type=sup_c)):
            return sub_c.strip() == sup_c.strip()

        case _:
            return False


def is_kind_equal(k1: QKind, k2: QKind, env: Optional[Any] = None) -> bool:
    """Checks if two kinds are equivalent (k1 <= k2 and k2 <= k1)."""
    return is_subkind(k1, k2, env) and is_subkind(k2, k1, env)


def is_subkind(sub: QKind, sup: QKind, env: Optional[Any] = None) -> bool:
    """Checks if sub is a subkind of sup (sub <= sup) with Full Subkinding on Kinds."""
    sub_lazy = sub.evaluate_lazily(env)
    sup_lazy = sup.evaluate_lazily(env)

    # 1. Reflexivity
    if sub_lazy is sup_lazy:
        return True

    # 2. Binary pattern matching
    match (sub_lazy, sup_lazy):
        # Power Kind to TYPE: POWER(T) <= TYPE
        case (QPowerKind(), QTypeKind()):
            return True

        # Power to Power: POWER(S) <= POWER(T) iff S <: T
        case (QPowerKind(bound=s_bound), QPowerKind(bound=t_bound)):
            return is_subtype(s_bound, t_bound, env)

        # Higher-Order Operator Kinds (Full Subkinding on Kinds):
        # ALL(X :: K1) K2 <= ALL(Y :: K1') K2' iff K1' <= K1 and K2 <= K2'[Y -> X]
        case (QAllKind(), QAllKind()):
            if not is_subkind(sup_lazy.param_kind, sub_lazy.param_kind, env):
                return False
            renamed_sup_res = sup_lazy.result_kind.substitute_types({
                sup_lazy.param_id: QTypeVar(sub_lazy.param_name, sup_lazy.param_id)
            }).substitute_kinds({
                sup_lazy.param_id: QKindVar(sub_lazy.param_name, sub_lazy.param_id)
            })
            return is_subkind(sub_lazy.result_kind, renamed_sup_res, env)

        case _:
            return False


