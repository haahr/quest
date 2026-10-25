"""Elaboration of auto values (Cardelli's dynamic types, The Quest Language and System §4.6): their
construction, inspect, and the closedness check on types used at run time."""

from __future__ import annotations

from typing import Optional

import quest.syntax.ast as ast
from quest.types import (
    OK_TYPE,
    QAutoType,
    QType,
    TYPE_KIND,
    KindError,
    check_kind,
    is_subtype,
    auto_matches_subtypes,
    auto_payload_type,
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
)

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


class AutoValueMixin:
    """Auto values and inspect.

    A mixin of `TypeElaborator` (in `typecheck.py`): its methods use the elaborator's state and its dispatch
    (`check_expr`, `synth_expr`), and call the other families' methods through `self`.
    """

    def _elaborate_inspect_expr(
        self,
        expr: ast.ExprInspect,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedInspect:
        """Elaborates an inspect expression on an auto value: its branches are checked against the expected type if
        there is one; otherwise its type is the join of their synthesized types (Ok if it has none)."""
        target_typed = self.synth_expr(expr.target, env, loop_depth)
        target_type = target_typed.type_val.evaluate_lazily(env)
        if not isinstance(target_type, QAutoType):
            raise TypeError(
                f"Target of inspect must have an Auto type (such as Dynamic), got '{target_type}'",
                offset=expr.target.offset,
            )
        typed_branches, else_typed = self._elaborate_auto_inspect_branches(
            expr, target_type, expected_type, env, loop_depth
        )

        if expected_type is not None:
            result_type = expected_type
        elif branch_types := self._collect_branch_types(typed_branches, else_typed):
            result_type = join_types(
                branch_types,
                env,
                expr.offset,
                error_msg="Cannot find common supertype join for inspect branch types '{t1}' and '{t2}'",
            )
        else:
            result_type = OK_TYPE

        return TypedInspect(
            target=target_typed,
            branches=tuple(typed_branches),
            else_branch=else_typed,
            auto_type=inspected_auto_type(target_typed, env),
            type_val=result_type,
            offset=expr.offset,
        )

    def _elaborate_auto_inspect_branches(
        self,
        expr: ast.ExprInspect,
        auto_type: QAutoType,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> tuple[list[TypedInspectBranch], Optional[TypedExpr]]:
        """Elaborates the branches of an inspect on an auto value (Cardelli §4.6).

        In the branch for type T, the binders denote the auto value's components, with signature S[T].
        """
        exact = not auto_matches_subtypes(auto_type)
        typed_branches: list[TypedInspectBranch] = []
        for branch in expr.branches:
            match_t = elaborate_type(branch.match_type, env)
            self._check_closed_type(match_t, "The type in an inspect when clause", branch.match_type.offset)
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
        return typed_branches, else_typed

    def _check_closed_type(self, t: QType, what: str, offset: int) -> None:
        """Checks a type that is used at run time (Cardelli §4.6 requires it to be closed).

        A type that mentions type parameters of enclosing polymorphic functions is allowed: their run-time type
        arguments are known when the function runs. Inside generic code such a type's values are laid out
        generically, which agrees with the native layout at any type argument (every slot holds one word, and a
        bounded type parameter's value is held at its own view), so they are used at a particular type argument as
        they are, mutable data included. An abstract type projected from a package value (t.A) has no run-time
        identity.
        """
        check_no_package_types(t, what, offset)

    def _elaborate_auto_expr(
        self,
        expr: ast.ExprAuto,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedAuto:
        """Checks an auto value auto [let A [HasKind] =] :W with Binding end against an Auto type. An auto value's
        type cannot be synthesized: it needs an expected type."""
        if expected_type is None:
            raise TypeError(
                "Cannot infer the type of an auto value; give it an expected Auto type "
                "(e.g. let p:Auto A::TYPE with a:A end = auto :Int with 3 end)",
                offset=expr.offset,
            )
        auto_type = expected_type.evaluate_lazily(env)
        if not isinstance(auto_type, QAutoType):
            raise TypeError(
                f"Auto value used where a value of type '{expected_type}' is expected; "
                f"auto values have Auto types",
                offset=expr.offset,
            )
        witness = elaborate_type(expr.witness_type, env)
        self._check_closed_type(witness, "The type component of an auto value", expr.witness_type.offset)
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
