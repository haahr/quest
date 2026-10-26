"""The type checker's state and the helpers its construct families share.

`Checker` is the base of `TypeElaborator` (in `typecheck`) and of each construct family's mixin (`bindings`,
`application`, `aggregates`, `control`, `exceptions`, `auto_values`), so that a family uses the state and helpers
through it, calls the families below it directly, and reaches the dispatch on expression forms (`check_expr`,
`synth_expr`), which is `typecheck`'s, through the methods declared here. The families call each other in one
direction: `exceptions` and `auto_values` are used by `bindings` and `application`, and `bindings` by `aggregates` and
`control`.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any, Optional

import quest.syntax.ast as ast
from quest.diagnostics import QuestTypeError
from quest.modules.stdlib import BuiltinModuleRegistry
from quest.typechecker.checks import require_subtype
from quest.typechecker.typed_ast import TypedExpr
from quest.types import QQuantifier, QType, QTypeMeta
from quest.types.env import Environment, Scope, ValueSymbol

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


class Checker:
    """The state of one type check, and the helpers its construct families share."""

    def __init__(self, env: Optional[Environment] = None, loop_depth: int = 0) -> None:
        self.env: Environment = env if env is not None else Environment(builtin_registry=BuiltinModuleRegistry)
        # The number of loops enclosing the code being checked, for checking exit. The loop_depth argument threaded
        # through the elaboration methods is authoritative; this field is only the counter that in_loop and in_function
        # adjust, set from the argument just before (see the while case of synth_expr).
        self.loop_depth: int = loop_depth
        # The number of functions enclosing the code being checked; one more inside each function body (in_function).
        # A symbol records the depth it was declared at, and a use from a deeper function is a capture
        # (_check_capturable).
        self.function_depth: int = 0
        # Implicit type arguments of the polymorphic call whose arguments are being checked, as
        # (metavariable, quantifier, call offset); nested calls may defer theirs to it.
        self._pending_type_args: Optional[list[tuple[QTypeMeta, QQuantifier, int]]] = None

    @contextmanager
    def scope(self, name: str = "local") -> Iterator[Scope]:
        """RAII scope context manager pushing and popping an environment scope."""
        with self.env.scoped(name) as s:
            yield s

    @contextmanager
    def in_loop(self) -> Iterator[None]:
        """RAII loop depth tracking context manager for while/loop/for constructs."""
        self.loop_depth += 1
        try:
            yield
        finally:
            self.loop_depth -= 1

    @contextmanager
    def in_function(self) -> Iterator[None]:
        """RAII scope isolation for function bodies (loops inside cannot exit outer loops)."""
        saved_depth = self.loop_depth
        self.loop_depth = 0
        self.function_depth += 1
        try:
            yield
        finally:
            self.loop_depth = saved_depth
            self.function_depth -= 1

    def _elaborate_subexpr(
        self,
        expr: ast.Expr,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedExpr:
        """Elaborates an expression in checking mode if expected_type is provided, else synthesis mode."""
        if expected_type is not None:
            return self.check_expr(expr, expected_type, env, loop_depth)
        return self.synth_expr(expr, env, loop_depth)

    def _elaborate_optional_branch(
        self,
        expr: Optional[ast.Expr],
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> Optional[TypedExpr]:
        """Elaborates an optional branch (e.g. else branch) if present, returning None otherwise."""
        if expr is None:
            return None
        return self._elaborate_subexpr(expr, expected_type, env, loop_depth)

    def _collect_branch_types(
        self,
        branches: Sequence[Any],
        else_branch: Optional[TypedExpr] = None,
        initial_type: Optional[QType] = None,
    ) -> list[QType]:
        """Collects body/result types from typed branch nodes and an optional else branch."""
        types: list[QType] = [initial_type] if initial_type is not None else []
        for b in branches:
            types.append(b.body.type_val)
        if else_branch is not None:
            types.append(else_branch.type_val)
        return types

    def _check_subsumption(
        self,
        expr: ast.Expr,
        expected_type: QType,
        env: Environment,
        loop_depth: int,
        type_desc: Optional[str] = None,
    ) -> TypedExpr:
        """Synthesizes expr and asserts that the synthesized type is a subtype of expected_type."""
        typed = self.synth_expr(expr, env, loop_depth)
        return require_subtype(expr, typed, expected_type, env, type_desc)

    def _check_capturable(self, sym: ValueSymbol, offset: int) -> None:
        """Rejects a use, from a closure, of a var or out parameter or a mutable local variable of an enclosing
        function: such locations live in that function's frame, so closures may not capture them. Module-level
        variables (function depth 0) may be used anywhere."""
        sym_depth = sym.function_depth
        if (sym.is_out or sym.is_var) and sym_depth > 0 and self.function_depth > sym_depth:
            kind_str = (
                "'out' parameter"
                if sym.is_out
                else ("'var' parameter" if sym.is_param else "'var' variable")
            )
            raise TypeError(f"Cannot capture {kind_str} '{sym.name}' in closure", offset=offset)

    # --- Dispatch, which typecheck.TypeElaborator defines ---

    def check_expr(
        self,
        expr: ast.Expr,
        expected_type: QType,
        env: Optional[Environment] = None,
        loop_depth: int = 0,
    ) -> TypedExpr:
        """Checks expr against expected_type (Gamma |- e <= T)."""
        raise NotImplementedError

    def synth_expr(
        self,
        expr: ast.Expr,
        env: Optional[Environment] = None,
        loop_depth: int = 0,
        is_callee: bool = False,
    ) -> TypedExpr:
        """Synthesizes the type of expr (Gamma |- e => T)."""
        raise NotImplementedError
