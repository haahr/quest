"""Elaboration of function application: monomorphic calls, polymorphic calls with explicit or inferred type
arguments, and the lvalue arguments of var and out parameters."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Optional

import quest.syntax.ast as ast
from quest.typechecker.checker import Checker
from quest.types import (
    INT_TYPE,
    QAllType,
    QArrayType,
    QFunType,
    QOptionType,
    QOutType,
    QParam,
    QQuantifier,
    QTupleType,
    QType,
    QTypeMeta,
    resolve_metas,
    unsolved_metas,
    QVarType,
    is_subtype,
    resolve_record_bound,
    resolve_option_bound,
    resolve_tuple_bound,
)
from quest.types.env import Environment
from quest.diagnostics import QuestTypeError
from quest.typechecker.elaborate_types import elaborate_type
from quest.typechecker.typed_ast import (
    TypedApp,
    TypedExpr,
    TypedIndexRef,
    TypedSelectRef,
    TypedTupleSelectRef,
    TypedTypeApp,
    TypedVar,
    TypedVarCell,
)
from quest.typechecker.checks import check_type_arg_kind
from quest.typechecker.escape import check_dynamic_type_args
from quest.typechecker.lvalues import check_lvalue_mode_type
from quest.typechecker.metas import resolve_typed_metas

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


class ApplicationMixin(Checker):
    """Function application.

    A construct family of the checker (`checker.Checker`): its methods use the checker's state and helpers, reach
    the dispatch (`check_expr`, `synth_expr`) through it, and call the families below this one (checker.py) through
    `self`.
    """

    def _check_call_args(
        self,
        args: Sequence[ast.Expr],
        params: Sequence[QParam],
        env: Environment,
        loop_depth: int,
        offset: int,
    ) -> list[TypedExpr]:
        """Validates arity and elaborates call arguments against formal parameter modes."""
        if len(args) != len(params):
            raise TypeError(
                f"Function expects {len(params)} arguments, but got {len(args)}",
                offset=offset,
            )
        typed_args: list[TypedExpr] = []
        for arg, param in zip(args, params):
            if param.is_var or param.is_out:
                typed_args.append(
                    self._check_lvalue_arg(arg, param.type_val, env, loop_depth, is_out=param.is_out)
                )
            else:
                typed_args.append(self.check_expr(arg, param.type_val, env, loop_depth))
        return typed_args

    def _elaborate_app_expr(
        self,
        expr: ast.ExprApp,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedExpr:
        """Elaborates a function application, handling polymorphic type inference, var, and out params.

        The expected type, if there is one, can determine the implicit type arguments of a polymorphic call; the
        application's type is still synthesized, and check_expr requires it to be a subtype of the expected type.
        """
        # Special built-in monadic operator: ordinal (Cardelli §4.5)
        if isinstance(expr.func, ast.ExprId) and expr.func.name == "ordinal":
            if len(expr.args) != 1:
                raise TypeError("ordinal expects 1 argument", offset=expr.offset)
            arg_typed = self.synth_expr(expr.args[0], env, loop_depth)
            arg_type_lazy = arg_typed.type_val.evaluate_lazily(env)
            if not isinstance(arg_type_lazy, QOptionType) and resolve_option_bound(arg_type_lazy) is None:
                raise TypeError(
                    f"ordinal requires an Option type, got '{arg_typed.type_val}'",
                    offset=expr.args[0].offset,
                )
            func_typed = self.synth_expr(expr.func, env, loop_depth, is_callee=True)
            return TypedApp(
                func=func_typed,
                args=(arg_typed,),
                type_val=INT_TYPE,
                offset=expr.offset,
            )

        func_typed = self.synth_expr(expr.func, env, loop_depth, is_callee=True)
        fn_type = func_typed.type_val.evaluate_lazily(env)

        # 1. Polymorphic function call (QAllType)
        if isinstance(fn_type, QAllType):
            return self._synth_polymorphic_app(expr, func_typed, fn_type, env, loop_depth, expected_type)

        # 2. Monomorphic function call (QFunType)
        if isinstance(fn_type, QFunType):
            return self._synth_monomorphic_app(expr, func_typed, fn_type, env, loop_depth)

        raise TypeError(f"Cannot invoke non-function type '{fn_type}'", offset=expr.func.offset)

    def _synth_monomorphic_app(
        self,
        expr: ast.ExprApp,
        func_typed: TypedExpr,
        fn_type: QFunType,
        env: Environment,
        loop_depth: int,
    ) -> TypedApp:
        """Synthesizes a monomorphic function application."""
        typed_args = self._check_call_args(expr.args, fn_type.params, env, loop_depth, expr.offset)

        return TypedApp(
            func=func_typed,
            args=tuple(typed_args),
            type_val=fn_type.result_type,
            offset=expr.offset,
        )

    def _check_lvalue_arg(
        self,
        arg: ast.Expr,
        param_type: QType,
        env: Environment,
        loop_depth: int,
        is_out: bool,
    ) -> TypedExpr:
        """Validates that arg is a mutable lvalue location for var or out parameters."""
        # Case 1: @target (Explicit reference passing, Cardelli §4.8)
        if isinstance(arg, ast.ExprDerefCell):
            return self._check_lvalue_target(
                arg.target, param_type, env, loop_depth, is_out, arg.offset
            )

        # Case 2: var(initial_value) (Fresh on-the-fly mutable variable, Cardelli §4.8)
        if isinstance(arg, ast.ExprVarCell):
            val_typed = self.check_expr(arg.value, param_type, env, loop_depth)
            return TypedVarCell(value=val_typed, type_val=QVarType(param_type), offset=arg.offset)

        # Case 3: Bare identifier or expression without @ or var(...) -> REJECT
        mode_name = "out" if is_out else "var"
        raise TypeError(
            f"Argument to '{mode_name}' parameter must be passed with '@' or 'var(...)'",
            offset=arg.offset,
        )

    def _check_lvalue_target(
        self,
        target: ast.Expr,
        param_type: QType,
        env: Environment,
        loop_depth: int,
        is_out: bool,
        offset: int,
    ) -> TypedExpr:
        mode_name = "out" if is_out else "var"
        match target:
            case ast.ExprId():
                sym = env.lookup_value(target.name)
                if sym is None:
                    raise TypeError(f"Undefined variable '{target.name}'", offset=offset)
                self._check_capturable(sym, offset)
                if is_out:
                    if not sym.is_var and not sym.is_out and not isinstance(sym.type_val, (QVarType, QOutType)):
                        raise TypeError(
                            f"Argument to 'out' parameter '{target.name}' must be a mutable variable or out parameter",
                            offset=offset,
                        )
                else:
                    if not sym.is_var and not isinstance(sym.type_val, QVarType):
                        raise TypeError(
                            f"Argument to 'var' parameter '{target.name}' must be a mutable variable",
                            offset=offset,
                        )
                dest_type = check_lvalue_mode_type(
                    param_type, sym.type_val, is_out, "variable", offset, env
                )
                return TypedVar(
                    name=sym.name,
                    symbol=sym,
                    type_val=QVarType(dest_type),
                    offset=offset,
                )
            case ast.ExprSelect():
                rec_typed = self.synth_expr(target.target, env, loop_depth)
                rec_type = rec_typed.type_val.evaluate_lazily(env)
                if not isinstance(rec_type, QTupleType) and resolve_record_bound(rec_type, env) is None:
                    # A type parameter bounded by a tuple type: its components are its bound's
                    rec_type = resolve_tuple_bound(rec_type, env) or rec_type

                # Check for mutable tuple component: @t.f or @t.1
                if isinstance(rec_type, QTupleType):
                    val_idx = -1
                    field_type = None
                    is_field_var = False
                    for i, f in enumerate(rec_type.value_fields):
                        if f.name == target.field or str(i) == target.field:
                            val_idx = i
                            field_type = f.type_val
                            is_field_var = f.is_var or isinstance(f.type_val, (QVarType, QOutType))
                            break
                    if val_idx == -1 or field_type is None:
                        raise TypeError(
                            f"Tuple type '{rec_type}' has no component matching '{target.field}'",
                            offset=offset,
                        )
                    if not is_field_var:
                        raise TypeError(
                            f"Tuple component '{target.field}' is not mutable",
                            offset=offset,
                        )
                    dest_type = check_lvalue_mode_type(
                        param_type, field_type, is_out, "tuple component", offset, env
                    )
                    fld_name = target.field if not target.field.isdigit() else None
                    return TypedTupleSelectRef(
                        target=rec_typed,
                        index=val_idx,
                        field=fld_name,
                        type_val=QVarType(dest_type),
                        offset=offset,
                    )

                rec_bound = resolve_record_bound(rec_type, env)
                if rec_bound is None:
                    raise TypeError(
                        f"Target of field selection in '{mode_name}' argument must be a Record or Tuple, "
                        f"got '{rec_type}'",
                        offset=offset,
                    )
                field = rec_bound.get_field(target.field)
                if field is None:
                    raise TypeError(
                        f"Record type '{rec_type}' has no field '{target.field}'",
                        offset=offset,
                    )
                if not field.is_var and not isinstance(field.type_val, (QVarType, QOutType)):
                    raise TypeError(
                        f"Record field '{target.field}' is not mutable",
                        offset=offset,
                    )
                field_type = check_lvalue_mode_type(
                    param_type, field.type_val, is_out, "field", offset, env
                )
                return TypedSelectRef(
                    target=rec_typed,
                    field=target.field,
                    type_val=QVarType(field_type),
                    offset=offset,
                )
            case ast.ExprIndex():
                arr_typed = self.synth_expr(target.target, env, loop_depth)
                arr_type = arr_typed.type_val.evaluate_lazily(env)
                if not isinstance(arr_type, QArrayType):
                    raise TypeError(
                        f"Target of array indexing in '{mode_name}' argument must be an Array, "
                        f"got '{arr_type}'",
                        offset=offset,
                    )
                idx_typed = self.check_expr(target.index, INT_TYPE, env, loop_depth)
                dest_type = check_lvalue_mode_type(
                    param_type, arr_type.element_type, is_out, "array element", offset, env
                )
                return TypedIndexRef(
                    target=arr_typed,
                    index=idx_typed,
                    type_val=QVarType(dest_type),
                    offset=offset,
                )
            case _:
                raise TypeError(
                    f"Argument to '{mode_name}' parameter must be a mutable variable, field, or array element",
                    offset=offset,
                )

    def _synth_polymorphic_app(
        self,
        expr: ast.ExprApp,
        func_typed: TypedExpr,
        all_type: QAllType,
        env: Environment,
        loop_depth: int,
        expected_type: Optional[QType] = None,
    ) -> TypedExpr:
        """Instantiates a polymorphic function using explicit type arguments or metavariable inference.

        Following Cardelli (The Quest Language and System §4), omitted type arguments are inferred from
        the types of the arguments and, failing that, from the type required by the context
        (expected_type). A type argument that cannot be inferred is an error, except that a call whose
        expected type still depends on the enclosing call's unsolved type arguments defers its own to
        that call (e.g. nil() in cons(nil() tail)).
        """
        # 1. Check for explicit type / kind arguments (e.g. f(:Int 42), id(:Int))
        num_targs = 0
        while num_targs < len(expr.args) and isinstance(
            expr.args[num_targs], (ast.TypeArgument, ast.KindArgument)
        ):
            num_targs += 1

        if num_targs > 0:
            if num_targs > len(all_type.quantifiers):
                raise TypeError(
                    f"Too many type arguments: expected at most {len(all_type.quantifiers)}, "
                    f"got {num_targs}",
                    offset=expr.offset,
                )

            subst: dict[int, QType] = {}
            resolved_targs: list[QType] = []
            for i in range(num_targs):
                q = all_type.quantifiers[i]
                targ_ast = expr.args[i]
                if isinstance(targ_ast, ast.TypeArgument):
                    targ_val = elaborate_type(targ_ast.type_val, env)
                    check_type_arg_kind(
                        "Type argument", targ_val, q.bound.substitute(subst), env, targ_ast.offset
                    )
                    subst[q.symbol_id] = targ_val
                    resolved_targs.append(targ_val)
                elif isinstance(targ_ast, ast.KindArgument):
                    raise TypeError(
                        "Explicit kind arguments are not supported in runtime calls",
                        offset=targ_ast.offset,
                    )

            if num_targs < len(all_type.quantifiers):
                remaining_quants = tuple(
                    q.substitute(subst) for q in all_type.quantifiers[num_targs:]
                )
                instantiated_type: QType = QAllType(
                    quantifiers=remaining_quants,
                    body=all_type.body.substitute(subst),
                )
            else:
                instantiated_type = all_type.body.substitute(subst)

            check_dynamic_type_args(all_type, resolved_targs, expr.offset, self._check_closed_type)
            typed_type_app = TypedTypeApp(
                func=func_typed,
                type_args=tuple(resolved_targs),
                type_val=instantiated_type,
                offset=expr.offset,
            )

            remaining_args = expr.args[num_targs:]
            if not remaining_args:
                return typed_type_app

            inst_lazy = instantiated_type.evaluate_lazily(env)
            remaining_call = ast.ExprApp(
                func=typed_type_app,
                args=remaining_args,
                offset=expr.offset,
            )
            if isinstance(inst_lazy, QAllType):
                return self._synth_polymorphic_app(
                    remaining_call, typed_type_app, inst_lazy, env, loop_depth, expected_type
                )
            if isinstance(inst_lazy, QFunType):
                return self._synth_monomorphic_app(
                    remaining_call, typed_type_app, inst_lazy, env, loop_depth
                )
            raise TypeError(
                f"Cannot invoke non-function type '{inst_lazy}'",
                offset=expr.offset,
            )

        # 2. Metavariable inference for implicit type arguments. Each quantifier is replaced by a metavariable
        #    (QTypeMeta, printed ?A), a placeholder that is_subtype solves as a side effect: comparing ?A with a type
        #    makes that type ?A's solution, the first one found. Metavariables exist only during this call: they are
        #    replaced by their solutions before its node is returned, and an assertion below fails if any remain.
        fn_body = all_type.body.evaluate_lazily(env)
        # An empty application of a polymorphic constant instantiates it (Cardelli: nil()).
        is_instantiation = not isinstance(fn_body, QFunType)
        if is_instantiation and expr.args:
            raise TypeError(
                f"Polymorphic body is '{fn_body}', not a function type",
                offset=expr.offset,
            )

        meta_map: dict[int, QTypeMeta] = {}
        for q in all_type.quantifiers:
            meta_map[q.symbol_id] = QTypeMeta(name=f"?{q.name}")

        instantiated_fn = fn_body.substitute(meta_map)
        result_type = instantiated_fn if is_instantiation else instantiated_fn.result_type

        # This call's type arguments, plus any that calls nested in its arguments defer to it.
        type_args: list[tuple[QTypeMeta, QQuantifier, int]] = [
            (meta_map[q.symbol_id], q, expr.offset) for q in all_type.quantifiers
        ]
        enclosing_type_args = self._pending_type_args
        self._pending_type_args = type_args
        try:
            typed_args = [] if is_instantiation else self._check_call_args(
                expr.args, instantiated_fn.params, env, loop_depth, expr.offset
            )
        finally:
            self._pending_type_args = enclosing_type_args

        if expected_type is not None and any(m.prune() is m for m, _, _ in type_args):
            # Inference from the type required by this instance (a failed match is reported by the caller).
            is_subtype(result_type, expected_type, env)

        unsolved = [entry for entry in type_args if entry[0].prune() is entry[0]]
        if unsolved:
            if enclosing_type_args is not None and expected_type is not None and unsolved_metas(expected_type):
                enclosing_type_args.extend(unsolved)
            else:
                names = ", ".join(f"'{q.name}'" for _, q, _ in unsolved)
                plural = "s" if len(unsolved) > 1 else ""
                raise TypeError(
                    f"Cannot infer type argument{plural} {names} from the arguments or the expected type; "
                    f"supply {'them' if plural else 'it'} explicitly",
                    offset=unsolved[0][2],
                )

        for meta, q, offset in type_args:
            solved = meta.prune()
            if solved is not meta:
                bound = q.bound.substitute(meta_map).substitute({})  # prunes the solved metavariables
                check_type_arg_kind("Inferred type argument", resolve_metas(solved), bound, env, offset)

        resolved_targs = [resolve_metas(meta_map[q.symbol_id]) for q in all_type.quantifiers]
        final_fn = resolve_metas(instantiated_fn)
        if self._pending_type_args is None:
            # Arguments elaborated in check mode (e.g. an array literal checked against Array(?A)) and
            # nested calls that deferred to this one still refer to the now-solved metavariables.
            memo: dict[int, Any] = {}
            typed_args = [resolve_typed_metas(a, memo) for a in typed_args]
            leaked = unsolved_metas(final_fn) + [m for t in resolved_targs for m in unsolved_metas(t)]
            assert not leaked, f"Metavariables escaped polymorphic call inference: {leaked}"

        check_dynamic_type_args(all_type, resolved_targs, expr.offset, self._check_closed_type)
        typed_type_app = TypedTypeApp(
            func=func_typed,
            type_args=tuple(resolved_targs),
            type_val=final_fn,
            offset=expr.offset,
        )
        if is_instantiation:
            return typed_type_app

        assert isinstance(final_fn, QFunType)
        return TypedApp(
            func=typed_type_app,
            args=tuple(typed_args),
            type_val=final_fn.result_type,
            offset=expr.offset,
        )
