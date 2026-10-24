"""Elaboration of exceptions: exception declarations, raise, and try."""

from __future__ import annotations

from typing import Optional

import quest.syntax.ast as ast
from quest.types import (
    OK_TYPE,
    QExceptionType,
    QType,
)
from quest.types.env import (
    Environment,
    ValueSymbol,
)
from quest.diagnostics import QuestTypeError
from quest.typechecker.elaborate_types import elaborate_type
from quest.typechecker.typed_ast import (
    TypedException,
    TypedExpr,
    TypedRaise,
    TypedTry,
    TypedTryBranch,
)
from quest.typechecker.checks import join_types

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


class ExceptionMixin:
    """Exception declarations, raise, and try.

    A mixin of `TypeElaborator` (in `typecheck.py`): its methods use the elaborator's state and its dispatch
    (`check_expr`, `synth_expr`), and call the other families' methods through `self`.
    """

    def _synth_exception_expr(self, expr: ast.ExprException, env: Environment, loop_depth: int) -> TypedException:
        """Synthesizes an exception constructor: exception Name [: PayloadType] end."""
        payload_type = elaborate_type(expr.type_annot, env) if expr.type_annot else OK_TYPE
        exc_type = QExceptionType(payload_type=payload_type)
        sym = ValueSymbol(
            name=expr.name,
            type_val=exc_type,
            is_var=False,
            function_depth=self.function_depth,
        )
        env.current_scope.declare_value(sym)
        return TypedException(
            name=expr.name,
            payload_type=payload_type,
            type_val=exc_type,
            symbol=sym,
            offset=expr.offset,
        )

    def _elaborate_raise(
        self,
        expr: ast.ExprRaise,
        res_type: QType,
        env: Environment,
        loop_depth: int,
    ) -> TypedRaise:
        """Shared elaboration core for raise expressions."""
        exc_typed = self.synth_expr(expr.exc, env, loop_depth)
        exc_type = exc_typed.type_val.evaluate_lazily(env)
        if not isinstance(exc_type, QExceptionType):
            raise TypeError(f"Cannot raise non-exception type '{exc_type}'", offset=expr.exc.offset)

        if expr.payload is not None:
            payload_typed = self.check_expr(expr.payload, exc_type.payload_type, env, loop_depth)
        else:
            if exc_type.payload_type is not OK_TYPE:
                raise TypeError(
                    f"Exception '{exc_type}' requires a payload of type '{exc_type.payload_type}'",
                    offset=expr.offset,
                )
            payload_typed = None

        return TypedRaise(
            exc=exc_typed,
            payload=payload_typed,
            type_val=res_type,
            offset=expr.offset,
        )

    def _check_raise_expr(
        self,
        expr: ast.ExprRaise,
        expected_type: QType,
        env: Environment,
        loop_depth: int,
    ) -> TypedRaise:
        """Checks a raise expression against any expected type (divergent control flow)."""
        return self._elaborate_raise(expr, expected_type, env, loop_depth)

    def _synth_raise_expr(self, expr: ast.ExprRaise, env: Environment, loop_depth: int) -> TypedRaise:
        """Synthesizes a raise expression. Defaults to Ok if no declared type is present."""
        res_type = elaborate_type(expr.as_type, env) if expr.as_type is not None else OK_TYPE
        return self._elaborate_raise(expr, res_type, env, loop_depth)

    def _elaborate_try_branches(
        self,
        expr: ast.ExprTry,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> tuple[TypedExpr, list[TypedTryBranch], Optional[TypedExpr]]:
        """Elaborates body, handler branches, and optional else branch for a try expression."""
        body_typed = self._elaborate_subexpr(expr.body, expected_type, env, loop_depth)

        typed_branches: list[TypedTryBranch] = []
        for branch in expr.branches:
            exc_typed = self.synth_expr(branch.exc_pattern, env, loop_depth)
            exc_type = exc_typed.type_val.evaluate_lazily(env)
            if not isinstance(exc_type, QExceptionType):
                raise TypeError(
                    f"Pattern in when branch must be an exception, got '{exc_type}'",
                    offset=branch.offset,
                )

            if branch.binder is not None:
                with env.scoped(f"try_{branch.binder}"):
                    binder_sym = ValueSymbol(
                        name=branch.binder,
                        type_val=exc_type.payload_type,
                        is_var=False,
                        function_depth=self.function_depth,
                    )
                    env.current_scope.declare_value(binder_sym)
                    h_body = self._elaborate_subexpr(branch.body, expected_type, env, loop_depth)
            else:
                binder_sym = None
                h_body = self._elaborate_subexpr(branch.body, expected_type, env, loop_depth)

            typed_branches.append(
                TypedTryBranch(
                    exc_pattern=exc_typed,
                    body=h_body,
                    binder=binder_sym,
                    offset=branch.offset,
                )
            )

        else_typed = self._elaborate_optional_branch(expr.else_branch, expected_type, env, loop_depth)
        return body_typed, typed_branches, else_typed

    def _check_try_expr(
        self,
        expr: ast.ExprTry,
        expected_type: QType,
        env: Environment,
        loop_depth: int,
    ) -> TypedTry:
        """Checks a try expression against an expected QType."""
        body_typed, typed_branches, else_typed = self._elaborate_try_branches(
            expr, expected_type, env, loop_depth
        )
        return TypedTry(
            body=body_typed,
            branches=tuple(typed_branches),
            else_branch=else_typed,
            type_val=expected_type,
            offset=expr.offset,
        )

    def _synth_try_expr(self, expr: ast.ExprTry, env: Environment, loop_depth: int) -> TypedTry:
        """Synthesizes a try expression by joining body and branch result types."""
        body_typed, typed_branches, else_typed = self._elaborate_try_branches(
            expr, None, env, loop_depth
        )
        all_types = self._collect_branch_types(
            typed_branches, else_typed, initial_type=body_typed.type_val
        )

        join_type = join_types(
            all_types,
            env,
            expr.offset,
            error_msg="Cannot find common supertype join for try expression branch types '{t1}' and '{t2}'",
        )
        return TypedTry(
            body=body_typed,
            branches=tuple(typed_branches),
            else_branch=else_typed,
            type_val=join_type,
            offset=expr.offset,
        )
