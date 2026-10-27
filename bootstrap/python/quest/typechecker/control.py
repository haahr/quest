"""Elaboration of control flow: case, the built-in infix operators (including
assignment), conditionals, for loops, and blocks. Desugaring
(quest/syntax/desugar.py) has made conditionals of short-circuit operators and
elsif chains, calls of other infix operators, and ExprIndexAssign of assignments
to array elements."""

from __future__ import annotations

from typing import Optional

import quest.syntax.ast as ast
from quest.typechecker.checker import Checker
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
    is_type_equal,
    resolve_record_bound,
    resolve_sum_bound,
    resolve_tuple_bound,
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
from quest.typechecker.checks import join_types, not_desugared
from quest.typechecker.escape import check_no_escaping_path_types

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


class ControlMixin(Checker):
    """Case, infix operators, assignment, conditionals, for loops, and blocks.

    A construct family of the checker (`checker.Checker`): its methods use the
    checker's state and helpers, reach the dispatch (`check_expr`, `synth_expr`)
    through it, and call the families below this one (checker.py) through
    `self`.
    """

    def _elaborate_case_expr(
        self,
        expr: ast.ExprCase,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedCase:
        """Elaborates a case expression over an option or variant target: its
        branches are checked against the expected type if there is one;
        otherwise its type is the join of their synthesized types (Ok if it has
        none)."""
        target_typed = self.synth_expr(expr.target, env, loop_depth)
        target_type = target_typed.type_val.evaluate_lazily(env)

        typed_branches = self._elaborate_case_branches(
            expr, target_type, expected_type=expected_type, env=env, loop_depth=loop_depth
        )

        else_typed = self._elaborate_optional_branch(expr.else_branch, expected_type, env, loop_depth)

        if expected_type is not None:
            result_type = expected_type
        elif branch_types := self._collect_branch_types(typed_branches, else_typed):
            result_type = join_types(
                branch_types,
                env,
                expr.offset,
                error_msg="Cannot find common supertype join for case branch types '{t1}' and '{t2}'",
            )
        else:
            result_type = OK_TYPE

        return TypedCase(
            target=target_typed,
            branches=tuple(typed_branches),
            else_branch=else_typed,
            type_val=result_type,
            offset=expr.offset,
        )

    def _elaborate_case_branches(
        self,
        expr: ast.ExprCase,
        target_type: QType,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> list[TypedCaseBranch]:
        """Checks a case expression's branches against the cases of its target's
        type, and elaborates each branch's body.

        A case expression chooses a branch by the tag of an option or variant
        value, and a branch may bind the tag's payload to a name, its binder:

            Let Shape = Option
                circle with r: Int end
                rect with w: Int h: Int end
                point
            end;
            let area(s: Shape): Int =
                case s
                    when circle with c then 3 * c.r * c.r
                    when rect with b: Tuple w: Int end then b.w * b.w
                    else 0
                end;

        The target's type must be an option or variant type, or have one as its
        bound (resolve_sum_bound: an abstract type A <: Shape, say). Then:

        - Every tag a branch names must be one of the type's cases; a branch
          may name several (when circle, rect then ...).
        - A binder is typed by its tag's payload, the tuple circle carries, or
          by the type it is declared with, which must be a supertype of the
          payload: b sees only rect's w. The paper reads a branch naming
          several tags as one branch per tag, its binder getting the same type
          in each (docs/TypefulProgramming.md §4.5). So a declared type must
          be a supertype of every tag's payload, and without one the payloads
          must all be equal types.
        - Each body is checked against the expected type if there is one, and
          otherwise synthesized, its caller joining the branches' types. A
          synthesized type must not mention a type component of the binder (as
          c.T for a payload Tuple T::TYPE x: T end), which means nothing outside
          the branch.
        - Without an else branch, every case must be covered: here, point's
          branch could be left out only because of the else."""
        if isinstance(target_type, QOptionType):
            available_tags = {opt.name: opt.payload_type for opt in target_type.options}
        elif isinstance(target_type, QVariantType):
            available_tags = {var.name: var.type_val for var in target_type.variants}
        elif isinstance(sum_bound := resolve_sum_bound(target_type, env), QVariantType):
            available_tags = {var.name: var.type_val for var in sum_bound.variants}
        elif isinstance(sum_bound, QOptionType):
            available_tags = {opt.name: opt.payload_type for opt in sum_bound.options}
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
                payloads: list[QType] = []
                for tag in branch.tags:
                    payload = available_tags[tag]
                    if payload is None:
                        raise TypeError(
                            f"Tag '{tag}' has no payload to bind to '{branch.binder}'",
                            offset=branch.offset,
                        )
                    payloads.append(payload)

                if branch.binder_type is not None:
                    binder_t = elaborate_type(branch.binder_type, env)
                    for payload in payloads:
                        if not is_subtype(payload, binder_t, env):
                            raise TypeError(
                                f"Binder '{branch.binder}' type '{binder_t}' is not "
                                f"compatible with payload '{payload}'",
                                offset=branch.offset,
                            )
                else:
                    binder_t = payloads[0]
                    for tag, payload in zip(branch.tags[1:], payloads[1:]):
                        if not is_type_equal(binder_t, payload, env):
                            raise TypeError(
                                f"Binder '{branch.binder}' would have payload type '{binder_t}' for tag "
                                f"'{branch.tags[0]}' but '{payload}' for tag '{tag}'; declare a type for it",
                                offset=branch.offset,
                            )

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

        return typed_branches

    def _synth_infix_expr(self, expr: ast.ExprInfix, env: Environment, loop_depth: int) -> TypedExpr:
        """Synthesizes an infix expression with a built-in operator: assignment,
        arithmetic, comparison, eager logic, and identity. Desugaring has made
        the short-circuit operators conditionals and the others calls."""
        # 1. Assignment (lhs := rhs)
        if expr.op == ":=":
            return self._synth_assignment(expr, env, loop_depth)

        # 2. Short-circuit logic (andif, orif) is desugared into conditionals
        if expr.op in ("andif", "orif"):
            raise not_desugared(expr)

        # 3. Non-overloaded operators (Arithmetic, Relational, String
        #    concatenation, Eager boolean)
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

        # 5. Other infix operators are desugared into calls: a op b is op(a, b)
        raise not_desugared(expr)

    def _synth_assignment(self, expr: ast.ExprInfix, env: Environment, loop_depth: int) -> TypedAssign:
        """Synthesizes an assignment, target := value, whose type is Ok.

        Only a mutable location can be assigned, and there are two kinds of
        target:

            let var n = 0;
            let p = tuple let var x = 1 let y = 2 end;
            n := 1;          (* a variable declared var, or an out parameter *)
            p.x := n + 1;    (* a component of a tuple or record declared var *)

        In each case the value is checked against the location's type, which
        is the variable's type, not the type Var(Int) the target has as a
        location (the TypedVar built below). A component is found in the
        target's type: a tuple type, a record type, or a type bounded by one,
        so that a function over A <: Record var count: Int end can assign
        a.count.

        A closure may not assign a var variable or parameter of an enclosing
        function (_check_capturable), since the location lives in that
        function's frame:

            let h(): Ok = begin let var m = 0 let g(): Ok = m := 2 g() end;

        is rejected, while module-level variables may be assigned anywhere.
        Assignments to array elements, a[i] := v, never reach here: desugaring
        made them ExprIndexAssign nodes."""
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

            # Target 2: Record or Tuple field selection (r.field := rhs, t.field
            # := rhs)
            case ast.ExprSelect(target=target, field=field, offset=sel_off):
                target_typed = self.synth_expr(target, env, loop_depth)
                target_type = target_typed.type_val.evaluate_lazily(env)
                if not isinstance(target_type, QTupleType) and resolve_record_bound(target_type, env) is None:
                    # A type parameter bounded by a tuple type: assigned through
                    # as its bound
                    target_type = resolve_tuple_bound(target_type, env) or target_type
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

            # Desugaring has made an assignment to an array element (a[idx] :=
            # rhs) an ExprIndexAssign
            case ast.ExprIndex():
                raise not_desugared(expr)

            case _:
                raise TypeError("Assignment target must be a mutable variable or field", offset=expr.left.offset)

    def _elaborate_if_expr(
        self,
        expr: ast.ExprIf,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedIf:
        """Elaborates a conditional, whose elsif branches desugaring has nested
        in its else branch.

        Against an expected type, both branches are checked against it
        (check_expr does so only for a conditional with an else branch, and
        checks the others by synthesis and subsumption). Synthesized, its type
        is the join of its branches' types, except that a conditional without an
        else branch is a statement: its then branch is evaluated for its effect,
        and its type is Ok. A short-circuit operator (andif, orif) has Bool
        branches: its operands are checked against Bool, and its type is Bool
        (check_expr checks it by subsumption).
        """
        if expr.elsifs:
            raise not_desugared(expr)
        if expr.short_circuit:
            expected_type = BOOL_TYPE
        cond_typed = self.check_expr(expr.cond, BOOL_TYPE, env, loop_depth)

        if expected_type is None and expr.else_branch is None:
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

        assert expr.else_branch is not None
        then_typed = self._elaborate_subexpr(expr.then_branch, expected_type, env, loop_depth)
        else_typed = self._elaborate_subexpr(expr.else_branch, expected_type, env, loop_depth)

        if expected_type is not None:
            result_type = expected_type
        else:
            result_type = join_types(
                [then_typed.type_val, else_typed.type_val],
                env,
                expr.offset,
                error_msg="Cannot find common supertype for conditional branches '{t1}' and '{t2}'",
            )
        return TypedIf(
            cond=cond_typed,
            then_branch=then_typed,
            else_branch=else_typed,
            type_val=result_type,
            offset=expr.offset,
        )

    def _synth_for_expr(self, expr: ast.ExprFor, env: Environment, loop_depth: int) -> TypedFor:
        """Synthesizes a for loop expression: for i = start upto/downto stop do
        body end."""
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

    def _elaborate_block_expr(
        self,
        expr: ast.ExprBlock,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedBlock:
        """Elaborates a scoped block expression: begin bindings... result end.

        A block ending with an expression statement has that expression's value,
        which is checked against the expected type if there is one; otherwise
        the block's type is Ok, which must then be a subtype of the expected
        type. A synthesized type may not mention the block's own bindings.
        """
        with env.scoped("block") as block_scope:
            typed_bindings: list[TypedBinding] = [
                self._elaborate_binding(binding, env, loop_depth) for binding in expr.bindings[:-1]
            ]

            result_expr: Optional[TypedExpr] = None
            if expr.bindings:
                last_binding = expr.bindings[-1]
                if isinstance(last_binding, ast.ExprStmt):
                    result_expr = self._elaborate_subexpr(last_binding.expr, expected_type, env, loop_depth)
                else:
                    typed_bindings.append(self._elaborate_binding(last_binding, env, loop_depth))
                    # Synthesized, a block also has the value of an exception
                    # declaration it ends with
                    if expected_type is None and isinstance(typed_bindings[-1], TypedExprStmt):
                        result_expr = typed_bindings.pop().expr
            if result_expr is None:
                if expected_type is not None and not is_subtype(OK_TYPE, expected_type, env):
                    what = "Block ending with declaration" if expr.bindings else "Empty block"
                    raise TypeError(
                        f"{what} has type Ok, not expected type '{expected_type}'",
                        offset=expr.offset,
                    )
                result_expr = TypedOk(offset=expr.offset)

            if expected_type is not None:
                result_type = expected_type
            else:
                result_type = result_expr.type_val
                local_symbol_ids = {sym.symbol_id for sym in block_scope.values.values()}
                check_no_escaping_path_types(result_type, local_symbol_ids, "its scope", result_expr.offset)

            return TypedBlock(
                bindings=tuple(typed_bindings),
                result=result_expr,
                type_val=result_type,
                offset=expr.offset,
            )
