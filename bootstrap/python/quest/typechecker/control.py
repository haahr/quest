"""Elaboration of control flow: case, infix operators (including assignment and short-circuit logic),
conditionals, for loops, and blocks."""

from __future__ import annotations

from typing import Optional

import quest.syntax.ast as ast
from quest.types import (
    BOOL_TYPE,
    INFIX_OPERATORS,
    INT_TYPE,
    OK_TYPE,
    QOptionType,
    QTupleType,
    QType,
    QVarType,
    QVariantType,
    is_subtype,
    resolve_record_bound,
    resolve_variant_bound,
)
from quest.types.env import (
    Environment,
    ValueSymbol,
)
from quest.diagnostics import QuestTypeError
from quest.typechecker.elaborate_types import elaborate_type
from quest.typechecker.typed_ast import (
    TypedAssign,
    TypedBinding,
    TypedBlock,
    TypedBool,
    TypedCase,
    TypedCaseBranch,
    TypedExpr,
    TypedExprStmt,
    TypedFor,
    TypedIf,
    TypedInfix,
    TypedOk,
    TypedSelect,
    TypedVar,
)
from quest.typechecker.checks import join_types
from quest.typechecker.escape import check_no_escaping_path_types

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


class ControlMixin:
    """Case, infix operators, assignment, conditionals, for loops, and blocks.

    A mixin of `TypeElaborator` (in `typecheck.py`): its methods use the elaborator's state and its dispatch
    (`check_expr`, `synth_expr`), and call the other families' methods through `self`.
    """

    def _synth_case_expr(self, expr: ast.ExprCase, env: Environment, loop_depth: int) -> TypedCase:
        """Synthesizes a case expression over an option or variant target."""
        target_typed = self.synth_expr(expr.target, env, loop_depth)
        target_type = target_typed.type_val.evaluate_lazily(env)

        available_tags, typed_branches = self._elaborate_case_branches(
            expr, target_type, expected_type=None, env=env, loop_depth=loop_depth
        )

        else_typed = self._elaborate_optional_branch(expr.else_branch, None, env, loop_depth)
        branch_types = self._collect_branch_types(typed_branches, else_typed)

        if not branch_types:
            return TypedCase(
                target=target_typed,
                branches=tuple(typed_branches),
                else_branch=else_typed,
                type_val=OK_TYPE,
                offset=expr.offset,
            )

        join_type = join_types(
            branch_types,
            env,
            expr.offset,
            error_msg="Cannot find common supertype join for case branch types '{t1}' and '{t2}'",
        )

        return TypedCase(
            target=target_typed,
            branches=tuple(typed_branches),
            else_branch=else_typed,
            type_val=join_type,
            offset=expr.offset,
        )

    def _check_case_expr(
        self,
        expr: ast.ExprCase,
        expected_type: QType,
        env: Environment,
        loop_depth: int,
    ) -> TypedCase:
        """Checks a case expression against an expected QType."""
        target_typed = self.synth_expr(expr.target, env, loop_depth)
        target_type = target_typed.type_val.evaluate_lazily(env)

        available_tags, typed_branches = self._elaborate_case_branches(
            expr, target_type, expected_type=expected_type, env=env, loop_depth=loop_depth
        )

        else_typed = self._elaborate_optional_branch(
            expr.else_branch, expected_type, env, loop_depth
        )

        return TypedCase(
            target=target_typed,
            branches=tuple(typed_branches),
            else_branch=else_typed,
            type_val=expected_type,
            offset=expr.offset,
        )

    def _elaborate_case_branches(
        self,
        expr: ast.ExprCase,
        target_type: QType,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> tuple[dict[str, Optional[QType]], list[TypedCaseBranch]]:
        """Validates tags, binders, exhaustiveness, and elaborates typed case branches."""
        if isinstance(target_type, QOptionType):
            available_tags = {opt.name: opt.payload_type for opt in target_type.options}
        elif isinstance(target_type, QVariantType):
            available_tags = {var.name: var.type_val for var in target_type.variants}
        elif (var_bound := resolve_variant_bound(target_type, env)) is not None:
            available_tags = {var.name: var.type_val for var in var_bound.variants}
        else:
            raise TypeError(
                f"Case target must have Option or Variant type, got '{target_type}'",
                offset=expr.target.offset,
            )

        covered_tags: set[str] = set()
        typed_branches: list[TypedCaseBranch] = []

        for branch in expr.branches:
            for tag in branch.tags:
                if tag not in available_tags:
                    raise TypeError(
                        f"Tag '{tag}' is not a valid variant of type '{target_type}'",
                        offset=branch.offset,
                    )
                covered_tags.add(tag)

            if branch.binder is not None:
                first_payload = available_tags[branch.tags[0]]
                if first_payload is None:
                    raise TypeError(
                        f"Tag '{branch.tags[0]}' has no payload to bind to '{branch.binder}'",
                        offset=branch.offset,
                    )

                if branch.binder_type is not None:
                    binder_t = elaborate_type(branch.binder_type, env)
                    if not is_subtype(first_payload, binder_t, env):
                        raise TypeError(
                            f"Binder '{branch.binder}' type '{binder_t}' is not "
                            f"compatible with payload '{first_payload}'",
                            offset=branch.offset,
                        )
                else:
                    binder_t = first_payload

                with env.scoped(f"case_{branch.binder}"):
                    binder_sym = ValueSymbol(
                        name=branch.binder,
                        type_val=binder_t,
                        is_var=False,
                        function_depth=self.function_depth,
                    )
                    env.current_scope.declare_value(binder_sym)
                    body_typed = self._elaborate_subexpr(branch.body, expected_type, env, loop_depth)
                    if expected_type is None:
                        check_no_escaping_path_types(
                            body_typed.type_val,
                            {binder_sym.symbol_id},
                            "case branch scope",
                            branch.body.offset,
                        )
            else:
                binder_sym = None
                body_typed = self._elaborate_subexpr(branch.body, expected_type, env, loop_depth)

            typed_branches.append(
                TypedCaseBranch(
                    tags=branch.tags,
                    body=body_typed,
                    binder=binder_sym,
                    offset=branch.offset,
                )
            )

        if expr.else_branch is None:
            missing = set(available_tags.keys()) - covered_tags
            if missing:
                missing_str = ", ".join(sorted(missing))
                raise TypeError(
                    f"Non-exhaustive case expression missing tags: {missing_str}",
                    offset=expr.offset,
                )

        return available_tags, typed_branches

    def _synth_infix_expr(self, expr: ast.ExprInfix, env: Environment, loop_depth: int) -> TypedExpr:
        """Synthesizes an infix expression (assignment, logic, arithmetic, comparison)."""
        # 1. Assignment (lhs := rhs)
        if expr.op == ":=":
            return self._synth_assignment(expr, env, loop_depth)

        # 2. Short-Circuit Logic (andif, orif) -> desugar to TypedIf
        if expr.op in ("andif", "orif"):
            left_typed = self.check_expr(expr.left, BOOL_TYPE, env, loop_depth)
            right_typed = self.check_expr(expr.right, BOOL_TYPE, env, loop_depth)
            if expr.op == "andif":
                return TypedIf(
                    cond=left_typed,
                    then_branch=right_typed,
                    else_branch=TypedBool(value=False, offset=expr.offset),
                    type_val=BOOL_TYPE,
                    offset=expr.offset,
                )
            else:
                return TypedIf(
                    cond=left_typed,
                    then_branch=TypedBool(value=True, offset=expr.offset),
                    else_branch=right_typed,
                    type_val=BOOL_TYPE,
                    offset=expr.offset,
                )

        # 3. Non-overloaded operators (Arithmetic, Relational, String concatenation, Eager boolean)
        if expr.op in INFIX_OPERATORS:
            exp_l, exp_r, res_type = INFIX_OPERATORS[expr.op]
            left_typed = self.check_expr(expr.left, exp_l, env, loop_depth)
            right_typed = self.check_expr(expr.right, exp_r, env, loop_depth)
            return TypedInfix(
                left=left_typed,
                op=expr.op,
                right=right_typed,
                type_val=res_type,
                offset=expr.offset,
            )

        # 4. Identity and Equality Operators (is, isnot)
        if expr.op in ("is", "isnot"):
            left_typed = self.synth_expr(expr.left, env, loop_depth)
            right_typed = self.synth_expr(expr.right, env, loop_depth)
            if (
                is_subtype(left_typed.type_val, right_typed.type_val, env)
                or is_subtype(right_typed.type_val, left_typed.type_val, env)
            ):
                return TypedInfix(
                    left=left_typed,
                    op=expr.op,
                    right=right_typed,
                    type_val=BOOL_TYPE,
                    offset=expr.offset,
                )

            raise TypeError(
                f"Equality operator '{expr.op}' requires operands of compatible types, got "
                f"'{left_typed.type_val}' and '{right_typed.type_val}'",
                offset=expr.offset,
            )

        if expr.op in ("==", "!="):
            suggest = "is" if expr.op == "==" else "isnot"
            raise TypeError(
                f"Operator '{expr.op}' is not supported; use '{suggest}' instead",
                offset=expr.offset,
            )

        # 5. User-defined infix operators: a op b desugars to op(a, b)
        op_sym = env.lookup_value(expr.op)
        if op_sym is not None:
            call_expr = ast.ExprApp(
                func=ast.ExprId(name=expr.op, offset=expr.offset),
                args=(expr.left, expr.right),
                offset=expr.offset,
            )
            return self.synth_expr(call_expr, env, loop_depth)

        raise TypeError(f"Unsupported infix operator '{expr.op}'", offset=expr.offset)

    def _synth_assignment(self, expr: ast.ExprInfix, env: Environment, loop_depth: int) -> TypedAssign:
        """Synthesizes an assignment expression: lhs := rhs."""
        match expr.left:
            # Target 1: Variable identifier
            case ast.ExprId(name=name, offset=id_off):
                sym = env.lookup_value(name)
                if sym is None:
                    raise TypeError(f"Undefined variable '{name}'", offset=id_off)
                self._check_capturable(sym, id_off)
                if not sym.is_var and not sym.is_out:
                    raise TypeError(f"Cannot assign to immutable variable '{name}'", offset=id_off)

                target_node = TypedVar(
                    name=sym.name,
                    symbol=sym,
                    type_val=QVarType(sym.type_val),
                    offset=id_off,
                )
                rhs_typed = self.check_expr(expr.right, sym.type_val, env, loop_depth)
                return TypedAssign(target=target_node, value=rhs_typed, offset=expr.offset)

            # Target 2: Record or Tuple field selection (r.field := rhs, t.field := rhs)
            case ast.ExprSelect(target=target, field=field, offset=sel_off):
                target_typed = self.synth_expr(target, env, loop_depth)
                target_type = target_typed.type_val.evaluate_lazily(env)
                if isinstance(target_type, QTupleType):
                    tup_f = None
                    for i, f in enumerate(target_type.value_fields):
                        if (
                            f.name == field
                            or str(i) == field
                            or (field.startswith("_") and field[1:] == str(i))
                        ):
                            tup_f = f
                            break
                    if tup_f is None:
                        raise TypeError(
                            f"Tuple type '{target_type}' has no field named '{field}'",
                            offset=sel_off,
                        )
                    if not tup_f.is_var:
                        raise TypeError(
                            f"Cannot assign to immutable tuple field '{field}'",
                            offset=sel_off,
                        )
                    rhs_typed = self.check_expr(expr.right, tup_f.type_val, env, loop_depth)
                    target_select = TypedSelect(
                        target=target_typed,
                        field=field,
                        type_val=tup_f.type_val,
                        offset=sel_off,
                    )
                    return TypedAssign(target=target_select, value=rhs_typed, offset=expr.offset)

                rec_bound = resolve_record_bound(target_type, env)
                if rec_bound is None:
                    raise TypeError(
                        f"Cannot mutate field of non-record type '{target_type}'",
                        offset=sel_off,
                    )
                rec_f = rec_bound.get_field(field)
                if rec_f is None:
                    raise TypeError(
                        f"Record has no field '{field}'",
                        offset=sel_off,
                    )
                if not rec_f.is_var:
                    raise TypeError(
                        f"Cannot assign to immutable record field '{field}'",
                        offset=sel_off,
                    )
                rhs_typed = self.check_expr(expr.right, rec_f.type_val, env, loop_depth)
                target_select = TypedSelect(
                    target=target_typed,
                    field=field,
                    type_val=rec_f.type_val,
                    offset=sel_off,
                )
                return TypedAssign(target=target_select, value=rhs_typed, offset=expr.offset)

            # Target 3: Array indexing (a[idx] := rhs)
            case ast.ExprIndex(target=target, index=index):
                return self._synth_index_assign_expr(
                    ast.ExprIndexAssign(target=target, index=index, value=expr.right, offset=expr.offset),
                    env,
                    loop_depth,
                )

            case _:
                raise TypeError("Assignment target must be a mutable variable or field", offset=expr.left.offset)

    def _desugar_if_else(self, expr: ast.ExprIf) -> ast.Expr:
        """Desugars elsif chains and optional else branch into a nested else AST expression."""
        desugared_else: ast.Expr = expr.else_branch if expr.else_branch else ast.ExprOk(offset=expr.offset)
        for elsif_cond, elsif_then in reversed(expr.elsifs):
            desugared_else = ast.ExprIf(
                cond=elsif_cond,
                then_branch=elsif_then,
                elsifs=(),
                else_branch=desugared_else,
                offset=elsif_cond.offset,
            )
        return desugared_else

    def _synth_if_expr(self, expr: ast.ExprIf, env: Environment, loop_depth: int) -> TypedIf:
        """Synthesizes an if expression."""
        cond_typed = self.check_expr(expr.cond, BOOL_TYPE, env, loop_depth)

        if expr.else_branch is None and not expr.elsifs:
            then_typed = self.synth_expr(expr.then_branch, env, loop_depth)
            then_body = TypedBlock(
                bindings=(TypedExprStmt(expr=then_typed, offset=then_typed.offset),),
                result=TypedOk(offset=then_typed.offset),
                type_val=OK_TYPE,
                offset=then_typed.offset,
            )
            return TypedIf(
                cond=cond_typed,
                then_branch=then_body,
                else_branch=TypedOk(offset=expr.offset),
                type_val=OK_TYPE,
                offset=expr.offset,
            )

        desugared_else = self._desugar_if_else(expr)
        then_typed = self.synth_expr(expr.then_branch, env, loop_depth)
        else_typed = self.synth_expr(desugared_else, env, loop_depth)

        join_type = join_types(
            [then_typed.type_val, else_typed.type_val],
            env,
            expr.offset,
            error_msg="Cannot find common supertype for conditional branches '{t1}' and '{t2}'",
        )
        return TypedIf(
            cond=cond_typed,
            then_branch=then_typed,
            else_branch=else_typed,
            type_val=join_type,
            offset=expr.offset,
        )

    def _check_if_expr(
        self,
        expr: ast.ExprIf,
        expected_type: QType,
        env: Environment,
        loop_depth: int,
    ) -> TypedIf:
        """Checks an if expression against an expected QType."""
        cond_typed = self.check_expr(expr.cond, BOOL_TYPE, env, loop_depth)
        desugared_else = self._desugar_if_else(expr)
        then_typed = self.check_expr(expr.then_branch, expected_type, env, loop_depth)
        else_typed = self.check_expr(desugared_else, expected_type, env, loop_depth)

        return TypedIf(
            cond=cond_typed,
            then_branch=then_typed,
            else_branch=else_typed,
            type_val=expected_type,
            offset=expr.offset,
        )

    def _synth_for_expr(self, expr: ast.ExprFor, env: Environment, loop_depth: int) -> TypedFor:
        """Synthesizes a for loop expression: for i = start upto/downto stop do body end."""
        start_typed = self.check_expr(expr.start, INT_TYPE, env, loop_depth)
        stop_typed = self.check_expr(expr.stop, INT_TYPE, env, loop_depth)

        with env.scoped(f"for_{expr.var_name}"):
            loop_var_sym = ValueSymbol(
                name=expr.var_name,
                type_val=INT_TYPE,
                is_var=False,
                function_depth=self.function_depth,
            )
            env.current_scope.declare_value(loop_var_sym)
            self.loop_depth = loop_depth
            with self.in_loop():
                body_typed = self.synth_expr(expr.body, env, self.loop_depth)

        return TypedFor(
            var_name=expr.var_name,
            symbol=loop_var_sym,
            start=start_typed,
            is_downto=expr.is_downto,
            stop=stop_typed,
            body=body_typed,
            offset=expr.offset,
        )

    def _synth_block_expr(self, expr: ast.ExprBlock, env: Environment, loop_depth: int) -> TypedBlock:
        """Synthesizes a scoped block expression: begin bindings... result end."""
        with env.scoped("block") as block_scope:
            typed_bindings: list[TypedBinding] = []
            for binding in expr.bindings:
                typed_b = self._elaborate_binding(binding, env, loop_depth)
                typed_bindings.append(typed_b)

            if typed_bindings and isinstance(typed_bindings[-1], TypedExprStmt):
                last_stmt = typed_bindings.pop()
                assert isinstance(last_stmt, TypedExprStmt)
                result_expr = last_stmt.expr
                result_type = result_expr.type_val
            else:
                result_expr = TypedOk(offset=expr.offset)
                result_type = OK_TYPE

            local_symbol_ids = {sym.symbol_id for sym in block_scope.values.values()}
            check_no_escaping_path_types(result_type, local_symbol_ids, "its scope", result_expr.offset)

            return TypedBlock(
                bindings=tuple(typed_bindings),
                result=result_expr,
                type_val=result_type,
                offset=expr.offset,
            )

    def _check_block_expr(
        self,
        expr: ast.ExprBlock,
        expected_type: QType,
        env: Environment,
        loop_depth: int,
    ) -> TypedBlock:
        """Checks a scoped block expression against an expected QType."""
        with env.scoped("block"):
            typed_bindings: list[TypedBinding] = []
            for binding in expr.bindings[:-1]:
                typed_b = self._elaborate_binding(binding, env, loop_depth)
                typed_bindings.append(typed_b)

            if expr.bindings:
                last_binding = expr.bindings[-1]
                if isinstance(last_binding, ast.ExprStmt):
                    result_expr = self.check_expr(last_binding.expr, expected_type, env, loop_depth)
                else:
                    typed_b = self._elaborate_binding(last_binding, env, loop_depth)
                    typed_bindings.append(typed_b)
                    if not is_subtype(OK_TYPE, expected_type, env):
                        raise TypeError(
                            f"Block ending with declaration has type Ok, not expected type '{expected_type}'",
                            offset=expr.offset,
                        )
                    result_expr = TypedOk(offset=expr.offset)
            else:
                if not is_subtype(OK_TYPE, expected_type, env):
                    raise TypeError(
                        f"Empty block has type Ok, not expected type '{expected_type}'",
                        offset=expr.offset,
                    )
                result_expr = TypedOk(offset=expr.offset)

            return TypedBlock(
                bindings=tuple(typed_bindings),
                result=result_expr,
                type_val=expected_type,
                offset=expr.offset,
            )
