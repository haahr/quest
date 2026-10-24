"""Elaboration of auto values (Cardelli's dynamic types, The Quest Language and System §4.6): their
construction, inspect, and the closedness check on types used at run time."""

from __future__ import annotations

from typing import Optional

import quest.syntax.ast as ast
from quest.types import (
    OK_TYPE,
    QAbstractType,
    QAutoType,
    QType,
    QTypeVar,
    TYPE_KIND,
    KindError,
    check_kind,
    is_subtype,
    auto_matches_subtypes,
    auto_payload_type,
    strip_aliases,
    unalias,
)
from quest.types.env import (
    Environment,
    TypeSymbol,
    ValueSymbol,
)
from quest.diagnostics import QuestTypeError
from quest.typechecker.elaborate_types import (
    elaborate_kind,
    elaborate_type,
)
from quest.typechecker.typed_ast import (
    TypedExpr,
    TypedAuto,
    TypedInspect,
    TypedInspectBranch,
)
from quest.typechecker.checks import (
    describe_kind,
    join_types,
)
from quest.typechecker.escape import (
    check_no_package_types,
    inspected_auto_type,
    mutable_type_vars_with_ids,
    type_vars_with_ids,
)

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


class AutoValueMixin:
    """Auto values and inspect.

    A mixin of `TypeElaborator` (in `typecheck.py`): its methods use the elaborator's state and its dispatch
    (`check_expr`, `synth_expr`), and call the other families' methods through `self`.
    """

    def _elaborate_inspect_branches(
        self,
        expr: ast.ExprInspect,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> tuple[TypedExpr, list[TypedInspectBranch], Optional[TypedExpr]]:
        """Elaborates target, inspect branches, and optional else branch for an inspect expression."""
        target_typed = self.synth_expr(expr.target, env, loop_depth)
        target_type = target_typed.type_val.evaluate_lazily(env)
        if isinstance(target_type, QAutoType):
            return self._elaborate_auto_inspect_branches(
                expr, target_typed, target_type, expected_type, env, loop_depth
            )
        raise TypeError(
            f"Target of inspect must have an Auto type (such as Dynamic), got '{target_type}'",
            offset=expr.target.offset,
        )

    def _elaborate_auto_inspect_branches(
        self,
        expr: ast.ExprInspect,
        target_typed: TypedExpr,
        auto_type: QAutoType,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> tuple[TypedExpr, list[TypedInspectBranch], Optional[TypedExpr]]:
        """Elaborates the branches of an inspect on an auto value (Cardelli §4.6).

        In the branch for type T, the binders denote the auto value's components, with signature S[T].
        """
        exact = not auto_matches_subtypes(auto_type)
        typed_branches: list[TypedInspectBranch] = []
        for branch in expr.branches:
            match_t = elaborate_type(branch.match_type, env)
            self._check_closed_type(
                match_t, "The type in an inspect when clause", branch.match_type.offset, auto_type
            )
            arm_type: QType = auto_payload_type(auto_type, match_t)
            with env.scoped("inspect_branch"):
                b_syms: list[ValueSymbol] = []
                for name, annot in branch.binders:
                    b_type = arm_type
                    if annot is not None:
                        b_type = elaborate_type(annot, env)
                        if not is_subtype(arm_type, b_type, env):
                            raise TypeError(
                                f"Inspect binder '{name}' has components of type '{arm_type}', "
                                f"which is not a subtype of the declared type '{b_type}'",
                                offset=annot.offset,
                            )
                    b_sym = ValueSymbol(
                        name=name,
                        type_val=b_type,
                        is_var=False,
                        function_depth=self.function_depth,
                    )
                    env.current_scope.declare_value(b_sym)
                    b_syms.append(b_sym)
                h_body = self._elaborate_subexpr(branch.body, expected_type, env, loop_depth)
            typed_branches.append(
                TypedInspectBranch(
                    match_type=match_t,
                    binders=tuple(b_syms),
                    body=h_body,
                    exact=exact,
                    offset=branch.offset,
                )
            )

        else_typed = self._elaborate_optional_branch(expr.else_branch, expected_type, env, loop_depth)
        return target_typed, typed_branches, else_typed

    def _check_closed_type(
        self, t: QType, what: str, offset: int, auto_type: Optional[QAutoType] = None
    ) -> None:
        """Checks a type that is used at run time (Cardelli §4.6 requires it to be closed).

        A type that mentions type parameters of enclosing polymorphic functions is allowed: their run-time type
        arguments are known when the function runs. But inside generic code such a type's values are laid out
        generically, so using them at a particular type argument may convert them, and for now the parameters
        may not occur inside mutable data (arrays, var components and fields, var and out parameters), whose
        conversion would be a copy that loses updates, nor may an auto type with var components (`auto_type`)
        have such a type component, since its binders must share those components. An abstract type projected
        from a package value (t.A) has no run-time identity.
        """
        check_no_package_types(t, what, offset)
        free = set(t._fv) & self._type_param_ids
        if not free:
            return
        bare = unalias(t)
        if isinstance(bare, (QTypeVar, QAbstractType)) and bare.symbol_id in self._type_param_ids:
            return
        mutable = sorted({v.name for v in mutable_type_vars_with_ids(strip_aliases(t), free)})
        if mutable:
            raise TypeError(
                f"{what} cannot yet mention a type parameter of an enclosing function inside mutable data (an "
                f"array, a var component or field, or a var or out parameter): '{t}' mentions {', '.join(mutable)}",
                offset=offset,
            )
        if auto_type is not None and any(f.is_var for f in auto_type.signature):
            names = sorted({v.name for v in type_vars_with_ids(strip_aliases(t), free)})
            raise TypeError(
                f"{what} cannot yet mention a type parameter of an enclosing function inside a larger type when "
                f"the auto type has var components: '{t}' mentions {', '.join(names)}",
                offset=offset,
            )

    def _check_auto_expr(
        self,
        expr: ast.ExprAuto,
        expected_type: QType,
        env: Environment,
        loop_depth: int,
    ) -> TypedAuto:
        """Checks an auto value auto [let A [HasKind] =] :W with Binding end against an Auto type."""
        auto_type = expected_type.evaluate_lazily(env)
        if not isinstance(auto_type, QAutoType):
            raise TypeError(
                f"Auto value used where a value of type '{expected_type}' is expected; "
                f"auto values have Auto types",
                offset=expr.offset,
            )
        witness = elaborate_type(expr.witness_type, env)
        self._check_closed_type(
            witness, "The type component of an auto value", expr.witness_type.offset, auto_type
        )
        try:
            check_kind(witness, auto_type.kind_bound, env)
        except KindError:
            raise TypeError(
                f"Type component '{witness}' of the auto value does not have kind "
                f"'{describe_kind(auto_type.kind_bound)}' required by '{expected_type}'",
                offset=expr.witness_type.offset,
            ) from None
        payload_type = auto_payload_type(auto_type, witness)
        with env.scoped("auto_value"):
            if expr.witness_name is not None:
                local_bound = (
                    elaborate_kind(expr.witness_bound, env) if expr.witness_bound is not None else TYPE_KIND
                )
                try:
                    check_kind(witness, local_bound, env)
                except KindError:
                    raise TypeError(
                        f"Type component '{witness}' of the auto value does not have the declared kind "
                        f"'{describe_kind(local_bound)}' of '{expr.witness_name}'",
                        offset=expr.witness_type.offset,
                    ) from None
                env.current_scope.declare_type(
                    TypeSymbol(
                        name=expr.witness_name,
                        symbol_id=env.fresh_symbol_id(),
                        kind=local_bound,
                        definition=witness,
                    )
                )
            payload_typed = self.check_expr(expr.payload, payload_type, env, loop_depth)
        return TypedAuto(
            witness_type=witness,
            auto_type=auto_type,
            payload=payload_typed,
            type_val=expected_type,
            offset=expr.offset,
        )

    def _check_inspect_expr(
        self,
        expr: ast.ExprInspect,
        expected_type: QType,
        env: Environment,
        loop_depth: int,
    ) -> TypedInspect:
        """Checks an inspect expression against an expected QType."""
        target_typed, typed_branches, else_typed = self._elaborate_inspect_branches(
            expr, expected_type, env, loop_depth
        )
        return TypedInspect(
            target=target_typed,
            branches=tuple(typed_branches),
            else_branch=else_typed,
            auto_type=inspected_auto_type(target_typed, env),
            type_val=expected_type,
            offset=expr.offset,
        )

    def _synth_inspect_expr(self, expr: ast.ExprInspect, env: Environment, loop_depth: int) -> TypedInspect:
        """Synthesizes an inspect expression by joining branch result types."""
        target_typed, typed_branches, else_typed = self._elaborate_inspect_branches(
            expr, None, env, loop_depth
        )
        branch_types = self._collect_branch_types(typed_branches, else_typed)

        if not branch_types:
            return TypedInspect(
                target=target_typed,
                branches=tuple(typed_branches),
                else_branch=else_typed,
                auto_type=inspected_auto_type(target_typed, env),
                type_val=OK_TYPE,
                offset=expr.offset,
            )

        join_type = join_types(
            branch_types,
            env,
            expr.offset,
            error_msg="Cannot find common supertype join for inspect branch types '{t1}' and '{t2}'",
        )
        return TypedInspect(
            target=target_typed,
            branches=tuple(typed_branches),
            else_branch=else_typed,
            auto_type=inspected_auto_type(target_typed, env),
            type_val=join_type,
            offset=expr.offset,
        )
