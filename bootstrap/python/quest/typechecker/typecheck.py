"""Quest Term Elaboration and Bidirectional Typechecker (Phases 2, 3, 4 & 5).

`TypeElaborator` checks (`check_expr`) and synthesizes (`synth_expr`) the types of expressions and elaborates
bindings, phrases, and programs into the typed AST. This module holds the dispatch on expression forms (with the
literals, variables, dereference, and while and loop inline), phrase and program elaboration, and the module-level
entry points. The checker's state and shared helpers are `checker.Checker`'s; the constructs are elaborated by
construct families, one module each, built on it: `bindings` (functions and bindings), `application`,
`aggregates`, `control`, `exceptions`, and `auto_values` (auto values and inspect)."""

from __future__ import annotations

from typing import Optional

import quest.syntax.ast as ast
from quest.types import (
    BOOL_TYPE,
    QType,
    QVarType,
)
from quest.types.env import Environment
from quest.diagnostics import (
    QuestCompilerError,
    QuestTypeError,
)
from quest.modules.elaboration import (
    elaborate_import,
    elaborate_interface,
    elaborate_module,
    register_binding_elaborator,
)
import quest.modules.loader  # noqa: F401  (registers the loader with quest.modules.elaboration)
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
    """The type checker, which elaborates a parsed syntax tree into a typed AST or reports the first type error.

    Elaborating means more than checking: the checker builds a new tree in which what the source leaves implicit is
    explicit. Every expression carries its type. Every variable carries its symbol, the record of the declaration it
    refers to: names can be shadowed, so two variables with one name may be different variables, and later phases
    identify them by symbol. Reading a mutable variable becomes an explicit dereference, and a call of a polymorphic
    function gets its type arguments, written or inferred. Given

        let var n = 1
        let id(A::TYPE x: A): A = x
        id(n + 1)

    the call elaborates to (as `./quest --stop-after typecheck` prints it)

        (TypedApp :type Int
          :func (TypedTypeApp [Int] :type Fun(x: Int): Int
            :func (TypedVar 'id' :type All(A :: TYPE) Fun(x: A): A))
          :args ((TypedInfix '+' :type Int
                   :left (TypedDerefCell :type Int :target (TypedVar 'n' :type Var(Int)))
                   :right (TypedInt 1 :type Int))))

    The tree has two readers: the interpreter, which evaluates it, and lowering, which translates it into the
    compiler's intermediate representation, from which C is printed. Neither looks at the syntax again or checks
    types, so whatever they need to know about types, the checker must write into the tree. docs/walkthrough.md §6
    follows one program through this phase.

    Checking is bidirectional (docs/type-system.md §6.1). check_expr(e, T) requires e to have type T and pushes T down
    into e, so that context can supply what e leaves unwritten, such as the type argument of list.nil() when it is
    checked against list.T(Int). synth_expr(e) works out e's type from e alone, bottom up. Most forms are synthesized
    even when checked, and then accepted by subsumption: a value of a subtype of T is accepted where T is expected
    (_check_subsumption). The forms that an expected type can inform each have one method, _elaborate_X_expr, which
    check_expr calls with the expected type and synth_expr with None. The methods are spread over mixins, one per family
    of constructs, purely to divide the code into files (checker.py describes them); at run time a check is one
    TypeElaborator object.

    The checker's state is env, a mutable Environment holding a stack of scopes, each holding the symbols declared in
    it. Bindings are declared into the current scope as they are elaborated, so elaboration order is scoping order. The
    elaborator itself is short-lived, but the Environment persists across a program's phrases (and, in the REPL,
    across the phrases typed). Alongside it, two counters track how many loops and functions enclose the code being
    checked, so that exit and closures that capture mutable variables can be checked.

    Things to know when changing or debugging it:

    - Types are immutable and shared (types/model.py), and == on a type raises. Compare types with is_subtype and
      is_type_equal, not `is`: equal types may be distinct objects (an alias and its target, a recursive type and its
      unfolding). A type may be an alias or a recursive type, so call t.evaluate_lazily(env) to expose its outermost
      constructor before testing it with isinstance or match; that holds for readers of the typed AST too.
    - Subsumption leaves no trace in the tree. An expression accepted where T is expected keeps its own type, so a
      node's type may be more specific than its context requires; only a construct that propagated T into its parts
      has type T. Changes of representation that subsumption implies are inserted much later, in the IR.
    - Errors are QuestTypeError (TypeError in these modules), raised at the offending syntax's offset, and the first
      one ends the check. A broken internal invariant raises QuestCompilerError with a message starting "internal:".
    """

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
        """Synthesizes the type of expr from expr alone, bottom up, and returns its elaborated node (Gamma |- e => T).

        The type synthesized is the most specific one the checker can determine, which subsumption may then widen. The
        cases fall into two groups. A form that check_expr also handles delegates to its _elaborate_X_expr method with
        no expected type, so that each construct has one elaboration whichever mode reaches it. Every other form is
        synthesized only: the simplest inline here, the rest by _synth_X methods in the mixins. Variables show what
        inline elaboration involves: the name is looked up in env to find its symbol, and a mutable variable, which in
        a value position stands for its contents, is wrapped in an explicit dereference.

        is_callee is true only for the function of a call. The monadic operators not, extent, and ordinal are names
        that may be called but are not values, so anywhere else they are rejected.

        A form with no case here falls to the last one, which reports it as unsupported. A new expression form needs a
        case here, and one in check_expr too if an expected type should flow into it; a
        typed node in typed_ast.py, with its dump; and its evaluation (interpreter/treewalk.py) and lowering
        (ir/lower.py), since those read only the typed AST.
        """
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
                raise TypeError(f"Unsupported AST expression '{expr}'", offset=expr.offset)

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
                    offset=phrase.offset,
                )

    def elaborate_program(
        self,
        program: ast.Program,
        env: Optional[Environment] = None,
    ) -> TypedProgram:
        """Elaborates a top-level Quest program unit (interfaces, modules, declarations, statements).

        Each elaboration declares fresh symbols, so elaborating the same syntax twice gives trees whose references do
        not resolve in each other. Under QUEST_CHECK_SCOPES=1, which the test runners set, the result is checked to be
        well scoped (every variable refers to a binder in scope; see scoping.py), which catches such a mix.
        """
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


register_binding_elaborator(elaborate_binding)
