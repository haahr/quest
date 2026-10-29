"""Elaboration of functions and of value bindings: function abstractions and
their parameters, let declarations (external, recursive, and simultaneous), type
and kind bindings, and the declarations of interfaces and modules met inside
blocks. Desugaring (quest/syntax/desugar.py) has made function values of the
parameters of let declarations that are neither recursive nor external."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

import quest.syntax.ast as ast
from quest.typechecker.checker import Checker
from quest.types import (
    QAllType,
    QFunType,
    QParam,
    QQuantifier,
    QType,
    QTypeVar,
    is_subkind,
    is_subtype,
    is_type_equal,
)
from quest.types.env import (
    Environment,
    TypeSymbol,
    ValueSymbol,
)
from quest.diagnostics import QuestTypeError
from quest.modules.elaboration import (
    elaborate_interface,
    elaborate_module,
)
from quest.typechecker.elaborate_types import (
    elaborate_kind,
    elaborate_kind_binding,
    elaborate_type,
    elaborate_type_binding,
    elaborate_type_binding_group,
)
from quest.typechecker.typed_ast import (
    TypedBinding,
    TypedDefKind,
    TypedExpr,
    TypedExprStmt,
    TypedExternal,
    TypedFun,
    TypedLetType,
    TypedLetTypeGroup,
    TypedLetValueGroup,
    TypedLetValue,
    TypedParam,
)
from quest.typechecker.checks import check_distinct_names, not_desugared
from quest.typechecker.escape import check_no_escaping_path_types

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


def _param_mode(is_var: bool, is_out: bool) -> str:
    """Describes a parameter mode for error messages."""
    return "var" if is_var else ("out" if is_out else "a value parameter")


def _require_param_type(param: ast.Param, written: QType, expected: QParam, env: Environment) -> None:
    """Requires the type a parameter is written with to fit the expected
    parameter of the same mode, as subtyping of function types does: a value
    parameter's written type must include the expected type (contravariance), a
    var parameter's must equal it, and an out parameter's must be included in
    it."""
    assert param.type_annot is not None
    if expected.is_var:
        ok = is_type_equal(written, expected.type_val, env)
        relation = "equal to"
    elif expected.is_out:
        ok = is_subtype(written, expected.type_val, env)
        relation = "a subtype of"
    else:
        ok = is_subtype(expected.type_val, written, env)
        relation = "a supertype of"
    if not ok:
        raise TypeError(
            f"Parameter '{param.name}' declared type '{written}' is not {relation} expected parameter type "
            f"'{expected.type_val}'",
            offset=param.type_annot.offset,
        )


class BindingMixin(Checker):
    """Function abstractions and the bindings of blocks, modules, and tuples.

    A construct family of the checker (`checker.Checker`): its methods use the
    checker's state and helpers, reach the dispatch (`check_expr`, `synth_expr`)
    through it, and call the families below this one (checker.py) through
    `self`.
    """

    def _declare_fun_params(
        self,
        params: Sequence[ast.Param],
        expected_params: Optional[Sequence[QParam]],
        env: Environment,
    ) -> tuple[tuple[TypedParam, ...], tuple[QParam, ...]]:
        """Declares function parameters in local scope and returns typed params
        and signature formals."""
        formal_params: list[TypedParam] = []
        q_params: list[QParam] = []
        for i, p in enumerate(params):
            is_var = p.mode == ast.ParamMode.VAR
            is_out = p.mode == ast.ParamMode.OUT
            expected_param = expected_params[i] if expected_params is not None else None
            if expected_param is not None and (is_var, is_out) != (expected_param.is_var, expected_param.is_out):
                raise TypeError(
                    f"Parameter '{p.name}' is declared {_param_mode(is_var, is_out)}, but the expected parameter "
                    f"'{expected_param}' is {_param_mode(expected_param.is_var, expected_param.is_out)}",
                    offset=p.offset,
                )
            if p.type_annot is not None:
                p_type = elaborate_type(p.type_annot, env)
                if expected_param is not None:
                    _require_param_type(p, p_type, expected_param, env)
            elif expected_param is not None:
                p_type = expected_param.type_val
            else:
                raise TypeError(
                    f"Parameter '{p.name}' requires a type annotation in synthesis mode",
                    offset=p.offset,
                )
            p_sym = ValueSymbol(
                name=p.name,
                type_val=p_type,
                is_var=is_var,
                is_out=is_out,
                is_param=True,
                function_depth=self.function_depth + 1,
            )
            env.current_scope.declare_value(p_sym)
            formal_params.append(
                TypedParam(
                    name=p.name,
                    symbol=p_sym,
                    type_val=p_type,
                    is_var=is_var,
                    is_out=is_out,
                    offset=p.offset,
                )
            )
            q_params.append(QParam(name=p.name, type_val=p_type, is_var=is_var, is_out=is_out))
        return tuple(formal_params), tuple(q_params)

    def _elaborate_fun_expr(
        self,
        expr: ast.ExprFun,
        expected_type: Optional[QType],
        env: Environment,
        loop_depth: int,
    ) -> TypedExpr:
        """Elaborates a function, fun[(type params)](params)[: R] body, into a
        TypedFun.

        The function opens a scope, declares its type parameters and parameters
        in it, and elaborates its body inside in_function, so that an exit
        cannot leave the function and the body's uses of enclosing mutable
        variables count as captures (see Checker). Its type is assembled from
        what it declares: Fun(params): R, under All(type params) if it has any.
        TypedFun.type_param_ids records which type symbols are the function's
        own, and a type mentioning one of them may occur only inside the
        function (scoping.py checks this). Likewise, the result type may not
        mention a path type rooted at a parameter, the type of one of a
        parameter's hidden type components.

        Checked against an expected function type, the function lets the
        expected type supply what it leaves unwritten: passed where the type
        All(x: Int) Int is expected, fun(x: Int) x + 1 needs no result
        annotation, because its body is checked against Int, and the function
        has the expected result type. What the function does write is held to
        what subsumption would require (docs/type-system.md §6.1): its
        parameters' modes must match, and its annotations must fit the expected
        types (_require_param_type). A parameter without an annotation would
        take its expected type, but the grammar requires one, so only an AST
        built directly (as by the unit tests) omits it. Against an expected
        polymorphic type, see _check_polymorphic_fun_expr. A function with type
        parameters checked against a plain function type, or any function
        checked against a type of another form, is synthesized and must be a
        subtype. Synthesized, the body is checked against the result annotation
        if there is one.
        """
        expected_fun: Optional[QFunType] = None
        if expected_type is not None:
            expected_lazy = expected_type.evaluate_lazily(env)
            if isinstance(expected_lazy, QAllType):
                return self._check_polymorphic_fun_expr(expr, expected_type, expected_lazy, env, loop_depth)
            # A function with type parameters is polymorphic, so it is checked
            # against a function type as it would be against any other type of
            # another form
            if not isinstance(expected_lazy, QFunType) or expr.type_params:
                return self._check_subsumption(expr, expected_type, env, loop_depth, type_desc="Function")
            if len(expr.params) != len(expected_lazy.params):
                raise TypeError(
                    f"Function arity mismatch: expected {len(expected_lazy.params)} parameters, "
                    f"got {len(expr.params)}",
                    offset=expr.offset,
                )
            expected_fun = expected_lazy

        with env.scoped("fun"):
            quants: list[QQuantifier] = []
            for tp in expr.type_params:
                bound_kind = elaborate_kind(tp.bound, env)
                sym_id = env.fresh_symbol_id()
                env.current_scope.declare_type(
                    TypeSymbol(name=tp.name, symbol_id=sym_id, kind=bound_kind)
                )
                quants.append(QQuantifier(name=tp.name, symbol_id=sym_id, bound=bound_kind))

            formal_params, q_params = self._declare_fun_params(
                expr.params, expected_fun.params if expected_fun is not None else None, env
            )

            with self.in_function():
                # The type the body is checked against: the result type
                # annotation, or else the expected result type
                body_expected: Optional[QType]
                if expr.return_type is not None:
                    body_expected = elaborate_type(expr.return_type, env)
                    if expected_fun is not None and not is_subtype(body_expected, expected_fun.result_type, env):
                        raise TypeError(
                            f"Function declared result type '{body_expected}' is not a subtype of expected result "
                            f"type '{expected_fun.result_type}'",
                            offset=expr.return_type.offset,
                        )
                elif expected_fun is not None:
                    body_expected = expected_fun.result_type
                else:
                    body_expected = None
                body_typed = self._elaborate_subexpr(
                    expr.body, body_expected, env, loop_depth=self.loop_depth
                )
                if expected_fun is not None:
                    ret_type = expected_fun.result_type
                elif body_expected is not None:
                    ret_type = body_expected
                else:
                    ret_type = body_typed.type_val

            # The result type may not mention the function's parameters (an
            # expected one cannot, a written one can)
            local_symbol_ids = {sym.symbol_id for sym in env.current_scope.values.values()}
            escape_type = body_expected if body_expected is not None else ret_type
            check_no_escaping_path_types(escape_type, local_symbol_ids, "function scope", expr.offset)

            if quants:
                if q_params:
                    fun_type: QType = QAllType(
                        quantifiers=tuple(quants),
                        body=QFunType(params=tuple(q_params), result_type=ret_type),
                    )
                else:
                    fun_type = QAllType(quantifiers=tuple(quants), body=ret_type)
            else:
                fun_type = QFunType(params=tuple(q_params), result_type=ret_type)

            return TypedFun(
                params=tuple(formal_params),
                body=body_typed,
                type_val=fun_type,
                type_param_ids=tuple(q.symbol_id for q in quants),
                type_only=bool(quants) and not q_params,
                offset=expr.offset,
            )

    def _check_polymorphic_fun_expr(
        self,
        expr: ast.ExprFun,
        expected_type: QType,
        expected_lazy: QAllType,
        env: Environment,
        loop_depth: int,
    ) -> TypedFun:
        """Checks a function against an expected polymorphic type, All(B::K) T.

        The function is made polymorphic in the expected type parameters, under
        its own names. Checking fun(A::TYPE x: A): A x against All(B::TYPE x: B)
        B declares A, with a fresh symbol and B's bound, and checks the rest of
        the function against Fun(x: A): A. A function that writes no type
        parameters, fun(x: B) x, takes the expected ones, names and all. The
        symbols are fresh because the expected type's own may already be in
        scope. A bound the function writes may be weaker than the expected one,
        as subtyping of polymorphic types allows (Cardelli's [TIncl Pi]), and
        the body is checked under the expected, stronger bound. The function's
        type is the renamed one, All(A::TYPE) Fun(x: A): A, so that its
        parameters and body refer to its own type parameters.
        """
        written = tuple(expr.type_params)
        if written and len(written) != len(expected_lazy.quantifiers):
            raise TypeError(
                f"Function has {len(written)} type parameters, but its expected type '{expected_type}' has "
                f"{len(expected_lazy.quantifiers)}",
                offset=expr.offset,
            )
        with env.scoped("poly_fun"):
            meta_map: dict[int, QType] = {}
            quants: list[QQuantifier] = []
            for idx, q in enumerate(expected_lazy.quantifiers):
                bound = q.bound.substitute_types(meta_map)
                name = written[idx].name if written else q.name
                if written:
                    written_bound = elaborate_kind(written[idx].bound, env)
                    if not is_subkind(bound, written_bound, env):
                        raise TypeError(
                            f"Type parameter '{name}' is declared '{QQuantifier(name, 0, written_bound)}', which "
                            f"does not include the expected '{QQuantifier(name, 0, bound)}'",
                            offset=written[idx].offset,
                        )
                sym_id = env.fresh_symbol_id()
                env.current_scope.declare_type(TypeSymbol(name=name, symbol_id=sym_id, kind=bound))
                meta_map[q.symbol_id] = QTypeVar(name=name, symbol_id=sym_id, bound=bound)
                quants.append(QQuantifier(name=name, symbol_id=sym_id, bound=bound))
            inner_exp = expected_lazy.body.substitute(meta_map)
            if written:
                if expr.params:
                    inner_expr = ast.ExprFun(
                        params=expr.params,
                        return_type=expr.return_type,
                        body=expr.body,
                        type_params=(),
                        offset=expr.offset,
                    )
                else:
                    inner_expr = expr.body
            else:
                inner_expr = expr
            body_exp = inner_exp
            if written and not expr.params and expr.return_type is not None:
                # Without value parameters, the body is checked against the
                # result type annotation, which must be a subtype of the
                # expected result type (the function's type keeps the expected
                # one)
                body_exp = elaborate_type(expr.return_type, env)
                if not is_subtype(body_exp, inner_exp, env):
                    raise TypeError(
                        f"Function declared result type '{body_exp}' is not a subtype of expected result "
                        f"type '{inner_exp}'",
                        offset=expr.return_type.offset,
                    )
            inner_typed = self.check_expr(inner_expr, body_exp, env, loop_depth)
            # The function's value parameters: those it writes, or, for a
            # function written with type parameters only, those of a body that
            # is itself a function, fun(A::TYPE) fun() e, as a curried
            # definition f(A::TYPE)() is, unless that function has type
            # parameters of its own. Otherwise its type parameters are its only
            # ones.
            merged = isinstance(inner_typed, TypedFun) and (bool(expr.params) or not inner_typed.type_param_ids)
            return TypedFun(
                params=inner_typed.params if merged else (),
                body=inner_typed.body if merged else inner_typed,
                type_val=QAllType(quantifiers=tuple(quants), body=inner_typed.type_val if merged else inner_exp),
                type_param_ids=tuple(q.symbol_id for q in quants),
                type_only=not merged,
                offset=expr.offset,
            )

    def _declare_rec_value(self, binding: ast.LetValueBinding, env: Environment) -> ValueSymbol:
        """Declares the symbol of a recursive value declaration (let rec) before
        its value is checked, so that the value, and the other members of its
        group, can refer to it:

            let rec even(n: Int): Bool = if n is 0 then true else odd(n - 1) end
            and odd(n: Int): Bool = if n is 0 then false else even(n - 1) end;

        Every member's type must be known before any body is checked, since
        each body may use the others, and a type cannot be taken from a body
        that has not been checked yet. So it is taken from the annotations
        alone:

        - A function, as even, needs a type on each parameter and a result
          type, from which its type is built: Fun(n: Int): Bool.
        - Any other value needs a type for the whole:
          let rec ones: Tuple head: Int tail: All() Int end = tuple ... end.

        So let rec fact(n: Int) = ... is rejected for want of a result type,
        though without rec its result type would be synthesized from its body.
        _check_rec_value then checks each value against its declared type."""
        if binding.params:
            if binding.type_annot is None:
                raise TypeError(
                    f"Recursive function '{binding.name}' requires an explicit return type annotation",
                    offset=binding.offset,
                )
            for p in binding.params:
                if p.type_annot is None:
                    raise TypeError(
                        f"Parameter '{p.name}' in recursive function '{binding.name}' "
                        f"requires an explicit type annotation",
                        offset=p.offset,
                    )
            q_params = tuple(
                QParam(
                    name=p.name,
                    type_val=elaborate_type(p.type_annot, env),
                    is_var=(p.mode == ast.ParamMode.VAR),
                    is_out=(p.mode == ast.ParamMode.OUT),
                )
                for p in binding.params
            )
            rec_fn_type = QFunType(params=q_params, result_type=elaborate_type(binding.type_annot, env))
            sym = ValueSymbol(name=binding.name, type_val=rec_fn_type, function_depth=self.function_depth)
        else:
            if binding.type_annot is None:
                raise TypeError(
                    f"Recursive definition '{binding.name}' requires an explicit type annotation",
                    offset=binding.offset,
                )
            sym = ValueSymbol(
                name=binding.name,
                type_val=elaborate_type(binding.type_annot, env),
                is_var=binding.is_var,
                function_depth=self.function_depth,
            )
        return env.current_scope.declare_value(sym)

    def _check_rec_value(
        self,
        binding: ast.LetValueBinding,
        sym: ValueSymbol,
        env: Environment,
        loop_depth: int,
    ) -> TypedLetValue:
        """Checks the value of a recursive value declaration against the type
        its symbol was declared with."""
        if binding.params:
            fn_expr = ast.ExprFun(
                params=binding.params,
                return_type=binding.type_annot,
                body=binding.value,
                offset=binding.offset,
            )
            typed_val = self.check_expr(fn_expr, sym.type_val, env, loop_depth=0)
        else:
            typed_val = self.check_expr(binding.value, sym.type_val, env, loop_depth)
        return TypedLetValue(
            name=binding.name,
            value=typed_val,
            symbol=sym,
            is_rec=True,
            offset=binding.offset,
        )

    def _elaborate_value_group(
        self,
        group: ast.LetValueBindingGroup,
        env: Environment,
        loop_depth: int,
    ) -> TypedLetValueGroup:
        """Elaborates simultaneous value declarations: let [rec] x = ... and y =
        ....

        With rec, every member is declared before any value is checked, so the
        members are mutually recursive. Without rec, each member is elaborated
        in a scope of its own, so it sees the enclosing scope and not the other
        members, and all are declared once every member has been elaborated.
        """
        check_distinct_names(group.bindings)
        if not group.bindings[0].is_rec:
            members: list[TypedLetValue] = []
            for member in group.bindings:
                with env.scoped("simultaneous"):
                    typed_member = self._elaborate_binding(member, env, loop_depth)
                assert isinstance(typed_member, TypedLetValue)
                members.append(typed_member)
            for typed_member in members:
                env.current_scope.declare_value(typed_member.symbol)
            return TypedLetValueGroup(members=tuple(members), offset=group.offset)
        syms = [self._declare_rec_value(member, env) for member in group.bindings]
        return TypedLetValueGroup(
            members=tuple(
                self._check_rec_value(member, sym, env, loop_depth) for member, sym in zip(group.bindings, syms)
            ),
            offset=group.offset,
        )

    def _elaborate_binding(self, binding: ast.BindingNode, env: Environment, loop_depth: int) -> TypedBinding:
        """Elaborates one binding and declares the names it binds in env's
        current scope, so that the bindings after it can use them.

        A block, a module, and a program are each a sequence of bindings,
        Cardelli's term for both declarations (let x = e) and statements (an
        expression evaluated for its effect, which declares nothing). They are
        elaborated in order, so each binding sees exactly the names declared
        before it.

        For a value declaration, the question is whether its own name is in
        scope in its value. An ordinary let checks the value first and declares
        the name afterward, so a use of the name inside the value refers to an
        earlier binding:

            let x = 1
            let x = x + 1        (the second x is the first one; x is now 2)

        A let rec declares the name first, so that the value can refer to
        itself, as a recursive function must:

            let rec fact(n: Int): Int =
                if n is 0 then 1 else n * fact(n - 1) end

        Since the name is used before its value has been checked, its type must
        come from the annotations alone, so a recursive function annotates every
        parameter and its result.

        Otherwise the name's type is its annotation, if it has one, and the
        value's synthesized type if not. An annotation may be less specific than
        the value, and it is what the name gets, so that here r.q is an error:

            let r: Record p: Int end = record p = 1 q = 2 end

        Declarations joined by and (let x = ... and y = ...) are declared
        together: after all their values, or, with rec, before any, so that they
        can refer to one another (_elaborate_value_group). An external function
        is implemented in C, so its annotations are its type. Type declarations,
        interfaces, and modules are elaborated by elaborate_types.py and
        modules/elaboration.py, to which this method passes them.
        """
        match binding:
            case ast.InterfaceDecl():
                return elaborate_interface(binding, env)

            case ast.ModuleDecl():
                return elaborate_module(binding, env, self._elaborate_binding)

            case ast.ExprException():
                typed_exc = self._synth_exception_expr(binding, env, loop_depth)
                return TypedExprStmt(expr=typed_exc, offset=binding.offset)

            case ast.ExprStmt(expr=ast.ExprException() as exc):
                typed_exc = self._synth_exception_expr(exc, env, loop_depth)
                return TypedExprStmt(expr=typed_exc, offset=binding.offset)

            case ast.ExprStmt(expr=expr):
                typed_e = self.synth_expr(expr, env, loop_depth)
                return TypedExprStmt(expr=typed_e, offset=binding.offset)

            # An external function: its parameters and result annotation declare
            # its type
            case ast.LetValueBinding(params=params, value=ast.ExprExternal()) if params:
                if binding.type_annot is None:
                    raise TypeError(
                        f"External function '{binding.name}' requires an explicit return type annotation",
                        offset=binding.offset,
                    )
                for p in params:
                    if p.type_annot is None:
                        raise TypeError(
                            f"Parameter '{p.name}' in external function '{binding.name}' "
                            f"requires an explicit type annotation",
                            offset=p.offset,
                        )
                param_types = tuple(
                    elaborate_type(p.type_annot, env)
                    for p in params
                )
                ret_type = elaborate_type(binding.type_annot, env)
                q_params = tuple(
                    QParam(
                        name=p.name,
                        type_val=param_types[i],
                        is_var=(p.mode == ast.ParamMode.VAR),
                        is_out=(p.mode == ast.ParamMode.OUT),
                    )
                    for i, p in enumerate(params)
                )
                fn_type = QFunType(params=q_params, result_type=ret_type)
                sym = ValueSymbol(
                    name=binding.name,
                    type_val=fn_type,
                    is_var=binding.is_var,
                    function_depth=self.function_depth,
                )
                env.current_scope.declare_value(sym)
                typed_ext = TypedExternal(
                    symbol=binding.value.symbol,
                    type_val=fn_type,
                    offset=binding.value.offset,
                )
                return TypedLetValue(
                    name=binding.name,
                    value=typed_ext,
                    symbol=sym,
                    is_rec=False,
                    offset=binding.offset,
                )

            # A recursive declaration, with or without parameters (desugaring
            # has made a function value of the parameters of one that is not
            # recursive)
            case ast.LetValueBinding(is_rec=True):
                rec_sym = self._declare_rec_value(binding, env)
                return self._check_rec_value(binding, rec_sym, env, loop_depth)

            case ast.LetValueBinding(params=params) if params:
                raise not_desugared(binding)

            case ast.LetValueBindingGroup():
                return self._elaborate_value_group(binding, env, loop_depth)

            case ast.LetValueBinding():
                if binding.type_annot is not None:
                    expected = elaborate_type(binding.type_annot, env)
                    typed_val = self.check_expr(binding.value, expected, env, loop_depth)
                    val_type = expected
                else:
                    typed_val = self.synth_expr(binding.value, env, loop_depth)
                    val_type = typed_val.type_val

                sym = ValueSymbol(
                    name=binding.name,
                    type_val=val_type,
                    is_var=binding.is_var,
                    function_depth=self.function_depth,
                )
                env.current_scope.declare_value(sym)
                return TypedLetValue(
                    name=binding.name,
                    value=typed_val,
                    symbol=sym,
                    is_rec=binding.is_rec,
                    offset=binding.offset,
                )

            case ast.TypeBinding():
                sym = elaborate_type_binding(binding, env)
                return TypedLetType(name=binding.name, symbol=sym, offset=binding.offset)

            case ast.TypeBindingGroup():
                syms = elaborate_type_binding_group(binding, env)
                return TypedLetTypeGroup(
                    members=tuple(
                        TypedLetType(name=sym.name, symbol=sym, offset=member.offset)
                        for sym, member in zip(syms, binding.bindings)
                    ),
                    offset=binding.offset,
                )

            case ast.DefKindBinding():
                k_sym = elaborate_kind_binding(binding, env)
                return TypedDefKind(name=binding.name, symbol=k_sym, offset=binding.offset)

            case _:
                raise TypeError(f"Unsupported binding '{binding}'", offset=binding.offset)
