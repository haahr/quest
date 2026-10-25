"""Quest Term Elaboration and Bidirectional Typechecker (Phases 2, 3, 4 & 5).

`TypeElaborator` checks (`check_expr`) and synthesizes (`synth_expr`) the types of expressions and elaborates
bindings, phrases, and programs into the typed AST. This module holds its state, the dispatch on expression
forms (with the literals, variables, dereference, and while and loop inline), the helpers shared by the
construct families, phrase and program elaboration, and the module-level entry points. The constructs are
elaborated by mixins, one module each: `bindings` (functions and bindings), `application`, `aggregates`,
`control`, `exceptions`, and `auto_values` (auto values and inspect)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any, Optional

import quest.syntax.ast as ast
from quest.types import (
    BOOL_TYPE,
    QQuantifier,
    QType,
    QTypeMeta,
    QVarType,
)
from quest.modules.stdlib import BuiltinModuleRegistry
from quest.types.env import (
    Environment,
    Scope,
    ValueSymbol,
)
from quest.diagnostics import (
    QuestCompilerError,
    QuestTypeError,
)
from quest.modules.elaboration import (
    elaborate_import,
    elaborate_interface,
    elaborate_module,
)
from quest.typechecker.typed_ast import (
    TypedBinding,
    TypedBool,
    TypedChar,
    TypedDerefCell,
    TypedExit,
    TypedExpr,
    TypedExternal,
    TypedInt,
    TypedLoop,
    TypedOk,
    TypedProgram,
    TypedReal,
    TypedString,
    TypedVar,
    TypedVarCell,
    TypedWhile,
)
from quest.typechecker.checks import require_subtype
from quest.typechecker.scoping import (
    check_well_scoped,
    scope_checks_enabled,
)
from quest.typechecker.bindings import BindingMixin
from quest.typechecker.application import ApplicationMixin
from quest.typechecker.aggregates import AggregateMixin
from quest.typechecker.control import ControlMixin
from quest.typechecker.exceptions import ExceptionMixin
from quest.typechecker.auto_values import AutoValueMixin

# Internal convenience alias for typechecking error raises
TypeError = QuestTypeError


class TypeElaborator(BindingMixin, ApplicationMixin, AggregateMixin, ControlMixin, ExceptionMixin, AutoValueMixin):
    """Stateful term elaboration and bidirectional typechecker for Quest AST expressions and bindings."""

    def __init__(self, env: Optional[Environment] = None, loop_depth: int = 0) -> None:
        self.env: Environment = env if env is not None else Environment(builtin_registry=BuiltinModuleRegistry)
        self.loop_depth: int = loop_depth
        self.function_depth: int = 0
        # Implicit type arguments of the polymorphic call whose arguments are being checked, as
        # (metavariable, quantifier, call offset); nested calls may defer theirs to it.
        self._pending_type_args: Optional[list[tuple[QTypeMeta, QQuantifier, int]]] = None
        # Symbol ids of the type parameters of polymorphic functions: the free type variables that the
        # type component of an auto value and the types of inspect branches must not mention.
        self._type_param_ids: set[int] = set()

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
            types.append(b.body.type_val if hasattr(b, "body") else b.type_val)
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
        sym_depth = getattr(sym, "function_depth", 0)
        if (sym.is_out or sym.is_var) and sym_depth > 0 and self.function_depth > sym_depth:
            kind_str = (
                "'out' parameter"
                if sym.is_out
                else ("'var' parameter" if getattr(sym, "is_param", False) else "'var' variable")
            )
            raise TypeError(f"Cannot capture {kind_str} '{sym.name}' in closure", offset=offset)

    def check(
        self,
        expr: ast.Expr,
        expected_type: QType,
        env: Optional[Environment] = None,
        loop_depth: Optional[int] = None,
    ) -> TypedExpr:
        """Checks an AST expression against an expected QType (Gamma |- e <= T)."""
        return self.check_expr(
            expr,
            expected_type,
            env=env or self.env,
            loop_depth=self.loop_depth if loop_depth is None else loop_depth,
        )

    def synth(
        self,
        expr: ast.Expr,
        env: Optional[Environment] = None,
        loop_depth: Optional[int] = None,
    ) -> TypedExpr:
        """Synthesizes the minimal QType and elaborated TypedExpr (Gamma |- e => T)."""
        return self.synth_expr(
            expr,
            env=env or self.env,
            loop_depth=self.loop_depth if loop_depth is None else loop_depth,
        )

    def elaborate_binding(
        self,
        binding: ast.BindingNode,
        env: Optional[Environment] = None,
        loop_depth: Optional[int] = None,
    ) -> TypedBinding:
        """Elaborates a single binding or statement inside a block or module."""
        return self._elaborate_binding(
            binding,
            env=env or self.env,
            loop_depth=self.loop_depth if loop_depth is None else loop_depth,
        )

    def check_expr(
        self,
        expr: ast.Expr,
        expected_type: QType,
        env: Optional[Environment] = None,
        loop_depth: int = 0,
    ) -> TypedExpr:
        """Checks an AST expression against an expected QType (Gamma |- e <= T).

        The constructs the expected type propagates into have one elaboration method each, `_elaborate_X_expr`,
        taking an optional expected type, which synth_expr calls with None; every other expression is synthesized
        and must be a subtype of the expected type.
        """
        if env is None:
            env = self.env

        match expr:
            # 1. Conditionals with else branch: check both branches against expected_type (a short-circuit operator
            #    is Bool, and is checked by subsumption)
            case ast.ExprIf(else_branch=else_br, short_circuit=False) if else_br is not None:
                return self._elaborate_if_expr(expr, expected_type, env, loop_depth)

            # 2. Block expression: check final result against expected_type
            case ast.ExprBlock():
                return self._elaborate_block_expr(expr, expected_type, env, loop_depth)

            # 3. Function abstraction: check against expected function type
            case ast.ExprFun():
                return self._elaborate_fun_expr(expr, expected_type, env, loop_depth)

            # 4. Record expression: check fields against expected record type
            case ast.ExprRecord():
                return self._elaborate_record_expr(expr, expected_type, env, loop_depth)

            # 5. Tuple expression: check elements against expected tuple type
            case ast.ExprTuple():
                return self._elaborate_tuple_expr(expr, expected_type, env, loop_depth)

            # 6. Case expression: check all branches against expected_type
            case ast.ExprCase():
                return self._elaborate_case_expr(expr, expected_type, env, loop_depth)

            # 7. Array expressions: check elements against expected array element type
            case ast.ExprArray():
                return self._elaborate_array_expr(expr, expected_type, env, loop_depth)

            case ast.ExprArrayRep():
                return self._elaborate_array_rep_expr(expr, expected_type, env, loop_depth)

            # 8. Phase 5: Raise expression (divergent control flow checks against any expected type)
            case ast.ExprRaise():
                return self._elaborate_raise_expr(expr, expected_type, env, loop_depth)

            # 9. Phase 5: Try expression
            case ast.ExprTry():
                return self._elaborate_try_expr(expr, expected_type, env, loop_depth)

            # 10. Phase 5: Inspect expression
            case ast.ExprInspect():
                return self._elaborate_inspect_expr(expr, expected_type, env, loop_depth)

            # 10b. Auto value: checked against the expected auto type
            case ast.ExprAuto():
                return self._elaborate_auto_expr(expr, expected_type, env, loop_depth)

            # 12. External C symbol binding
            case ast.ExprExternal(symbol=symbol, offset=off):
                return TypedExternal(symbol=symbol, type_val=expected_type, offset=off)

            # 13. Application: the type required by the context can determine implicit type arguments
            #     (Cardelli, The Quest Language and System §4: cons(3 nil()))
            case ast.ExprApp():
                typed = self._elaborate_app_expr(expr, expected_type, env, loop_depth)
                return require_subtype(expr, typed, expected_type, env)

            # 14. Subsumption: synthesize minimal type and check subtyping (S <= T)
            case _:
                return self._check_subsumption(expr, expected_type, env, loop_depth)

    def synth_expr(
        self,
        expr: ast.Expr,
        env: Optional[Environment] = None,
        loop_depth: int = 0,
        is_callee: bool = False,
    ) -> TypedExpr:
        """Synthesizes the minimal QType and elaborated TypedExpr (Gamma |- e => T)."""
        if env is None:
            env = self.env

        match expr:
            # --- Literals ---
            case ast.ExprInt(value=val, offset=off):
                return TypedInt(value=val, offset=off)

            case ast.ExprReal(value=val, offset=off):
                return TypedReal(value=val, offset=off)

            case ast.ExprBool(value=val, offset=off):
                return TypedBool(value=val, offset=off)

            case ast.ExprChar(value=val, offset=off):
                return TypedChar(value=val, offset=off)

            case ast.ExprString(value=val, offset=off):
                return TypedString(value=val, offset=off)

            case ast.ExprOk(offset=off):
                return TypedOk(offset=off)

            case ast.ExprExit(offset=off):
                if loop_depth <= 0:
                    raise TypeError("Exit statement outside of any loop", offset=off)
                return TypedExit(offset=off)

            case ast.ExprExternal(symbol=symbol, offset=off):
                raise TypeError(
                    f"External binding '{symbol}' requires an explicit type annotation",
                    offset=off,
                )

            # --- Variables & Identifiers ---
            case ast.ExprId(name=name, offset=off):
                if not is_callee and name in ("not", "extent", "ordinal"):
                    raise TypeError(
                        f"Monadic operator '{name}' cannot be used as a value without an operand",
                        offset=off,
                    )

                sym = env.lookup_value(name)
                if sym is None:
                    raise TypeError(f"Undefined variable '{name}'", offset=off)

                # Disallow capturing out or var parameters / local mutable variables in nested closures
                self._check_capturable(sym, off)

                # Strict write-only enforcement for out parameters
                if sym.is_out:
                    raise TypeError(f"Cannot read from write-only 'out' parameter '{sym.name}'", offset=off)

                # Implicit dereferencing: mutable variables in value positions yield element type
                if sym.is_var:
                    var_node = TypedVar(
                        name=sym.name,
                        symbol=sym,
                        type_val=QVarType(sym.type_val),
                        offset=off,
                    )
                    return TypedDerefCell(target=var_node, type_val=sym.type_val, offset=off)

                return TypedVar(name=sym.name, symbol=sym, type_val=sym.type_val, offset=off)

            # --- Explicit Dereference (@e or !e) ---
            case ast.ExprDerefCell(target=target, offset=off):
                if isinstance(target, ast.ExprId):
                    sym = env.lookup_value(target.name)
                    if sym is None:
                        raise TypeError(f"Undefined variable '{target.name}'", offset=target.offset)
                    if not sym.is_var and not isinstance(sym.type_val, QVarType):
                        raise TypeError(
                            f"Cannot dereference non-variable symbol '{target.name}'",
                            offset=target.offset,
                        )
                    var_type = QVarType(sym.type_val) if sym.is_var else sym.type_val
                    elem_type = sym.type_val if sym.is_var else sym.type_val.element_type
                    var_node = TypedVar(
                        name=sym.name,
                        symbol=sym,
                        type_val=var_type,
                        offset=target.offset,
                    )
                    return TypedDerefCell(target=var_node, type_val=elem_type, offset=off)

                target_typed = self.synth_expr(target, env, loop_depth)
                if not isinstance(target_typed.type_val, QVarType):
                    raise TypeError(
                        f"Cannot dereference non-variable type '{target_typed.type_val}'",
                        offset=off,
                    )
                return TypedDerefCell(
                    target=target_typed,
                    type_val=target_typed.type_val.element_type,
                    offset=off,
                )

            # --- Reference Cell Allocation (var e) ---
            case ast.ExprVarCell(value=val, offset=off):
                val_typed = self.synth_expr(val, env, loop_depth)
                return TypedVarCell(
                    value=val_typed,
                    type_val=QVarType(val_typed.type_val),
                    offset=off,
                )

            # --- Infix Operators ---
            case ast.ExprInfix():
                return self._synth_infix_expr(expr, env, loop_depth)

            # --- Conditionals ---
            case ast.ExprIf():
                return self._elaborate_if_expr(expr, None, env, loop_depth)

            # --- Loops & Control Flow ---
            case ast.ExprWhile(cond=cond, body=body, offset=off):
                cond_typed = self.check_expr(cond, BOOL_TYPE, env, loop_depth)
                self.loop_depth = loop_depth
                with self.in_loop():
                    body_typed = self.synth_expr(body, env, self.loop_depth)
                return TypedWhile(cond=cond_typed, body=body_typed, offset=off)

            case ast.ExprLoop(body=body, offset=off):
                self.loop_depth = loop_depth
                with self.in_loop():
                    body_typed = self.synth_expr(body, env, self.loop_depth)
                return TypedLoop(body=body_typed, offset=off)

            case ast.ExprFor():
                return self._synth_for_expr(expr, env, loop_depth)

            # --- Block Expressions ---
            case ast.ExprBlock():
                return self._elaborate_block_expr(expr, None, env, loop_depth)

            # --- Functions and Applications ---
            case ast.ExprFun():
                return self._elaborate_fun_expr(expr, None, env, loop_depth)

            case ast.ExprApp():
                return self._elaborate_app_expr(expr, None, env, loop_depth)

            # --- Aggregates (Records, Tuples, Options, Variants, Arrays) ---
            case ast.ExprRecord():
                return self._elaborate_record_expr(expr, None, env, loop_depth)

            case ast.ExprTuple():
                return self._elaborate_tuple_expr(expr, None, env, loop_depth)

            case ast.ExprSelect():
                return self._synth_select_expr(expr, env, loop_depth)

            case ast.ExprOption():
                return self._synth_option_expr(expr, env, loop_depth)

            case ast.ExprVariant():
                return self._synth_variant_expr(expr, env, loop_depth)

            case ast.ExprVariantCheck():
                return self._synth_variant_check_expr(expr, env, loop_depth)

            case ast.ExprVariantAssert():
                return self._synth_variant_assert_expr(expr, env, loop_depth)

            case ast.ExprCase():
                return self._elaborate_case_expr(expr, None, env, loop_depth)

            case ast.ExprArray():
                return self._elaborate_array_expr(expr, None, env, loop_depth)

            case ast.ExprArrayRep():
                return self._elaborate_array_rep_expr(expr, None, env, loop_depth)

            case ast.ExprIndex():
                return self._synth_index_expr(expr, env, loop_depth)

            case ast.ExprIndexAssign():
                return self._synth_index_assign_expr(expr, env, loop_depth)

            # --- Exceptions & Dynamic (Phase 5) ---
            case ast.ExprException():
                return self._synth_exception_expr(expr, env, loop_depth)

            case ast.ExprRaise():
                return self._elaborate_raise_expr(expr, None, env, loop_depth)

            case ast.ExprTry():
                return self._elaborate_try_expr(expr, None, env, loop_depth)

            case ast.ExprInspect():
                return self._elaborate_inspect_expr(expr, None, env, loop_depth)

            case ast.ExprAuto():
                return self._elaborate_auto_expr(expr, None, env, loop_depth)

            case _:
                raise TypeError(f"Unsupported AST expression '{expr}'", offset=getattr(expr, "offset", 0))

    def elaborate_phrase(
        self,
        phrase: ast.ASTNode,
        env: Optional[Environment] = None,
    ) -> TypedBinding | TypedExpr:
        """Elaborates a single top-level phrase (interface, module, import, binding, or expr)."""
        if env is None:
            env = self.env
        match phrase:
            case ast.InterfaceDecl():
                return elaborate_interface(phrase, env)
            case ast.ModuleDecl():
                return elaborate_module(phrase, env, self._elaborate_binding)
            case ast.ImportPhrase():
                return elaborate_import(phrase, env)
            case ast.BindingNode():
                return self._elaborate_binding(phrase, env, loop_depth=0)
            case ast.Expr():
                return self.synth_expr(phrase, env, loop_depth=0)
            case _:
                raise TypeError(
                    f"Unsupported top-level phrase '{phrase}'",
                    offset=getattr(phrase, "offset", 0),
                )

    def elaborate_program(
        self,
        program: ast.Program,
        env: Optional[Environment] = None,
    ) -> TypedProgram:
        """Elaborates a top-level Quest program unit (interfaces, modules, declarations, statements)."""
        if env is None:
            env = self.env

        typed_phrases = tuple(self.elaborate_phrase(phrase, env) for phrase in program.phrases)
        typed = TypedProgram(phrases=typed_phrases, offset=program.offset)
        if scope_checks_enabled():
            problems = check_well_scoped(typed)
            if problems:
                raise QuestCompilerError(
                    "internal: the typed program is not well scoped:\n  " + "\n  ".join(problems[:20])
                )
        return typed




# ============================================================================
# Public Module-Level Facade Functions
# ============================================================================

def check_expr(
    expr: ast.Expr,
    expected_type: QType,
    env: Optional[Environment] = None,
    loop_depth: int = 0,
) -> TypedExpr:
    """Checks an AST expression against an expected QType (Gamma |- e <= T)."""
    return TypeElaborator(env=env, loop_depth=loop_depth).check_expr(
        expr, expected_type, env=env, loop_depth=loop_depth
    )


def synth_expr(
    expr: ast.Expr,
    env: Optional[Environment] = None,
    loop_depth: int = 0,
    is_callee: bool = False,
) -> TypedExpr:
    """Synthesizes the minimal QType and elaborated TypedExpr (Gamma |- e => T)."""
    return TypeElaborator(env=env, loop_depth=loop_depth).synth_expr(
        expr, env=env, loop_depth=loop_depth, is_callee=is_callee
    )


def elaborate_phrase(
    phrase: ast.ASTNode,
    env: Optional[Environment] = None,
) -> TypedBinding | TypedExpr:
    """Elaborates a single top-level phrase (interface, module, import, binding, or expr)."""
    return TypeElaborator(env=env).elaborate_phrase(phrase, env=env)


def elaborate_program(
    program: ast.Program,
    env: Optional[Environment] = None,
) -> TypedProgram:
    """Elaborates a top-level Quest program unit (interfaces, modules, declarations, statements)."""
    return TypeElaborator(env=env).elaborate_program(program, env=env)


def elaborate_binding(
    binding: ast.BindingNode,
    env: Optional[Environment] = None,
    loop_depth: int = 0,
) -> TypedBinding:
    """Elaborates a single binding or statement inside a block or module."""
    return TypeElaborator(env=env, loop_depth=loop_depth)._elaborate_binding(
        binding, env=env, loop_depth=loop_depth
    )
