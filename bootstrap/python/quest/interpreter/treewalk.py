"""The tree-walking interpreter of the typed AST: the `interpret` phase and the REPL.

Evaluates typed expressions, bindings, and programs in lexically scoped runtime environments (RuntimeEnvironment),
loading and evaluating the modules a program imports (load_module_for_interpreter). Primitive operations and the
standard library's runtime errors are quest.interpreter.primitives', and printing values by their types
quest.interpreter.formatting's; the IR interpreter (quest.interpreter.ir_interp) shares them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from quest.diagnostics import (
    MAIN_FRAME,
    QuestCompilerError,
    frame_name,
    init_frame,
)
from quest.interpreter.primitives import (
    ARRAY_OP_ERROR_EXC,
    QuestRuntimeError,
    VARIANT_ERROR_EXC,
    int_arithmetic,
    int_relational,
    real_arithmetic,
    real_relational,
)
from quest.modules.graph import Roots, UnitGraph, UnitKind
from quest.syntax.sources import SourceMap, display_file_name
from quest.values.model import (
    DYNAMIC_ERROR_EXC,
    QuestException,
    FALSE_VALUE,
    OK_VALUE,
    TRUE_VALUE,
    QArray,
    QBool,
    QBuiltinFun,
    QChar,
    QAutoVal,
    QClosure,
    QExceptionVal,
    QInt,
    QList,
    QOk,
    QOption,
    QReal,
    QRecord,
    QRef,
    QArrayElementRef,
    QTupleElementRef,
    QString,
    QTuple,
    QTypeValue,
    QValue,
    QVariant,
    qvalue_is,
)
from quest.types import (
    QOptionType,
    QTupleType,
    QType,
    is_subtype,
    is_type_equal,
)
from quest.typechecker.typed_ast import (
    TypedApp,
    TypedArray,
    TypedArrayRep,
    TypedAssign,
    TypedBinding,
    TypedBlock,
    TypedBool,
    TypedCase,
    TypedChar,
    TypedDefKind,
    TypedDerefCell,
    TypedException,
    TypedExit,
    TypedNode,
    scope_exceptions,
    TypedExpr,
    TypedExprStmt,
    TypedExternal,
    TypedFor,
    TypedFun,
    TypedIf,
    TypedIndex,
    TypedIndexAssign,
    TypedIndexRef,
    TypedInfix,
    TypedImport,
    TypedAuto,
    TypedInspect,
    TypedInterface,
    TypedInt,
    TypedLetType,
    TypedLetTypeGroup,
    TypedLetValueGroup,
    TypedLetValue,
    TypedLoop,
    TypedModule,
    TypedOk,
    TypedOption,
    TypedProgram,
    TypedRaise,
    TypedReal,
    TypedRecord,
    TypedSelect,
    TypedSelectRef,
    TypedTupleSelectRef,
    TypedString,
    TypedTry,
    TypedTuple,
    TypedTypeApp,
    TypedTypeWitness,
    TypedVar,
    TypedVarCell,
    TypedVariant,
    TypedVariantAssert,
    TypedVariantCheck,
    TypedWhile,
    binding_members,
)


# ============================================================================
# 1. Control Signals
# ============================================================================

class _LoopExit(Exception):
    """Internal control-flow signal raised by TypedExit to break out of loops."""
    pass


# ============================================================================
# 2. Scoped Runtime Environment
# ============================================================================

class RuntimeEnvironment:
    """Lexically scoped symbol table mapping variable names to QValue instances."""

    def __init__(self, parent: Optional[RuntimeEnvironment] = None):
        self.parent = parent
        self.bindings: dict[str, QValue] = {}
        # Run-time type arguments: the types bound to the type parameters (by symbol id) of the polymorphic
        # functions being executed, for the operations that use types at run time
        self.type_bindings: dict[int, QType] = {}
        # The named exceptions this scope made before the binding that makes them (by symbol id), which that
        # binding's exception expressions return (make_scope_exceptions)
        self.made_exceptions: dict[int, QExceptionVal] = {}
        if parent is not None:
            self.include_paths: list[Path] = parent.include_paths
            self.current_dir: Optional[Path] = parent.current_dir
            self.program_dir: Optional[Path] = parent.program_dir
            self.units: UnitGraph = parent.units
            self.source_map: Optional[Any] = parent.source_map
            self.call_stack: list[str] = parent.call_stack
        else:
            self.include_paths: list[Path] = []
            self.current_dir: Optional[Path] = None
            self.program_dir: Optional[Path] = None
            # The program's units (docs/build-process.md §2.1), whose typed modules the interpreter evaluates, and
            # which hold the values of the modules it has run; the type checker's graph itself, when the program was
            # type checked by a pipeline (CompilerContext.runtime_env)
            self.units: UnitGraph = UnitGraph()
            # The source map of the file whose code runs in this scope (the program's, or a module file's), where
            # the offsets of the errors that code raises are (docs/exceptions.md §3.2)
            self.source_map: Optional[Any] = None
            # The frames running, outermost first, shared by every scope (docs/exceptions.md §4)
            self.call_stack: list[str] = []

    def push_scope(self) -> RuntimeEnvironment:
        """Pushes a new child scope inheriting from this environment."""
        return RuntimeEnvironment(parent=self)

    def pop_scope(self) -> RuntimeEnvironment:
        """Pops the current child scope, returning its parent."""
        if self.parent is None:
            raise QuestRuntimeError("Cannot pop root runtime scope")
        return self.parent

    def define(self, name: str, value: QValue) -> None:
        """Binds a variable in the current innermost scope frame."""
        self.bindings[name] = value

    def made_exception(self, symbol_id: int) -> Optional[QExceptionVal]:
        """The named exception of the symbol that an enclosing scope made in advance, if one did."""
        env: Optional[RuntimeEnvironment] = self
        while env is not None:
            if symbol_id in env.made_exceptions:
                return env.made_exceptions[symbol_id]
            env = env.parent
        return None

    def bind_types(self, bindings: dict[int, QType]) -> None:
        """Binds type parameters (by symbol id) to their run-time type arguments in the current scope frame."""
        self.type_bindings.update(bindings)

    def lookup_type(self, symbol_id: int) -> Optional[QType]:
        """The run-time type argument bound to a type parameter, if any."""
        env: Optional[RuntimeEnvironment] = self
        while env is not None:
            if symbol_id in env.type_bindings:
                return env.type_bindings[symbol_id]
            env = env.parent
        return None

    def resolve_type(self, t: QType) -> QType:
        """t with the run-time type arguments of the type parameters it mentions substituted."""
        subst = {}
        for symbol_id in t._fv:
            bound = self.lookup_type(symbol_id)
            if bound is not None:
                subst[symbol_id] = bound
        return t.substitute(subst) if subst else t

    def lookup(self, name: str, offset: Optional[int] = None) -> QValue:
        """Resolves a variable recursively outward from innermost to outermost scope."""
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name, offset)
        from quest.modules.stdlib import STANDARD_LIBRARY_MODULES
        norm_mod = name if name in STANDARD_LIBRARY_MODULES else next(
            (m for m in STANDARD_LIBRARY_MODULES if m.lower() == name.lower()),
            None,
        )
        if norm_mod is not None:
            mod_val = load_module_for_interpreter(norm_mod, STANDARD_LIBRARY_MODULES[norm_mod], self)
            if mod_val is not None:
                self.define(norm_mod, mod_val)
                if name != norm_mod:
                    self.define(name, mod_val)
                return mod_val
        raise QuestRuntimeError(f"Undefined runtime symbol '{name}'", offset=offset)

    def assign(self, name: str, new_value: QValue, offset: Optional[int] = None) -> None:
        """Mutates an existing binding or updates its mutable QRef cell in place."""
        if name in self.bindings:
            curr = self.bindings[name]
            if isinstance(curr, QRef):
                curr.assign(new_value)
            else:
                self.bindings[name] = new_value
            return
        if self.parent is not None:
            self.parent.assign(name, new_value, offset)
            return
        raise QuestRuntimeError(f"Cannot assign to undefined symbol '{name}'", offset=offset)

    def snapshot(self) -> dict[str, Any]:
        """Captures a shallow copy of the current bindings and parent pointer."""
        return {
            "bindings": dict(self.bindings),
            "parent": self.parent,
        }

    def restore(self, snap: dict[str, Any]) -> None:
        """Restores bindings and parent from a previous snapshot."""
        self.bindings = dict(snap["bindings"])
        self.parent = snap["parent"]

    _cached_base_bindings: Optional[dict[str, QValue]] = None

    @classmethod
    def create_root_env(cls) -> RuntimeEnvironment:
        """Creates the global root environment with standard constants pre-populated."""
        env = cls()
        if cls._cached_base_bindings is not None:
            env.bindings = dict(cls._cached_base_bindings)
            return env

        env.define("true", TRUE_VALUE)
        env.define("false", FALSE_VALUE)
        env.define("ok", OK_VALUE)

        # Built-in operators as callable functions (Cardelli §4.2)
        for op in ("+", "-", "*", "/", "mod", "%"):
            env.define(
                op,
                QBuiltinFun(
                    op,
                    lambda a, b, op=op: QInt(
                        int_arithmetic(op, a.value, b.value, offset=0)
                    ),
                ),
            )
        for op in ("<", "<=", ">", ">="):
            env.define(
                op,
                QBuiltinFun(
                    op,
                    lambda a, b, op=op: (
                        TRUE_VALUE
                        if int_relational(op, a.value, b.value, offset=0)
                        else FALSE_VALUE
                    ),
                ),
            )
        for op in ("++", "--", "**", "//", "^^"):
            env.define(
                op,
                QBuiltinFun(
                    op,
                    lambda a, b, op=op: QReal(
                        real_arithmetic(op, a.value, b.value, offset=0)
                    ),
                ),
            )
        for op in ("<<", "<<=", ">>", ">>="):
            env.define(
                op,
                QBuiltinFun(
                    op,
                    lambda a, b, op=op: (
                        TRUE_VALUE
                        if real_relational(op, a.value, b.value, offset=0)
                        else FALSE_VALUE
                    ),
                ),
            )
        env.define("<>", QBuiltinFun("<>", lambda a, b: QString(a.value + b.value)))
        env.define(
            "/\\",
            QBuiltinFun("/\\", lambda a, b: TRUE_VALUE if (a.value and b.value) else FALSE_VALUE),
        )
        env.define(
            "\\/",
            QBuiltinFun("\\/", lambda a, b: TRUE_VALUE if (a.value or b.value) else FALSE_VALUE),
        )

        # Monadic Operators: not, extent, ordinal (Cardelli §4.2, §4.3, §4.5)
        env.define(
            "not",
            QBuiltinFun("not", lambda b: FALSE_VALUE if b.value else TRUE_VALUE),
        )
        env.define(
            "extent",
            QBuiltinFun("extent", lambda a: QInt(len(a.elements))),
        )
        env.define(
            "ordinal",
            QBuiltinFun(
                "ordinal",
                lambda o: (
                    QInt(o.ordinal)
                    if isinstance(o, QOption)
                    else (_ for _ in ()).throw(
                        QuestRuntimeError(f"ordinal expects Option, got {o.type_name}")
                    )
                ),
            ),
        )

        cls._cached_base_bindings = dict(env.bindings)
        return env


# ============================================================================
# 3. Expression Evaluator
# ============================================================================

def eval_expr(expr: TypedExpr, env: RuntimeEnvironment) -> QValue:
    """Evaluates a typed expression within the given runtime environment."""
    match expr:
        # 1. Literals
        case TypedInt(value=val):
            return QInt(val)
        case TypedReal(value=val):
            return QReal(val)
        case TypedBool(value=val):
            return TRUE_VALUE if val else FALSE_VALUE
        case TypedChar(value=val):
            return QChar(val)
        case TypedString(value=val):
            return QString(val)
        case TypedOk():
            return OK_VALUE
        case TypedExternal(symbol=symbol):
            from quest.interpreter.builtins import resolve_external_symbol
            return resolve_external_symbol(symbol)

        # 2. Variables & Mutable References
        case TypedVar(name=name, offset=offset):
            return env.lookup(name, offset=offset)

        case TypedVarCell(value=val):
            return QRef(eval_expr(val, env))

        case TypedDerefCell(target=tgt):
            target_val = eval_expr(tgt, env)
            return target_val.deref() if isinstance(target_val, QRef) else target_val

        case TypedSelectRef(target=tgt, field=fld, offset=offset):
            rec_val = eval_expr(tgt, env)
            while isinstance(rec_val, QRef):
                rec_val = rec_val.deref()
            if not isinstance(rec_val, QRecord):
                raise QuestRuntimeError("Field selection target must be Record", offset=offset)
            field_cell = rec_val.get(fld)
            if isinstance(field_cell, QRef):
                return field_cell
            raise QuestRuntimeError(f"Field '{fld}' is not mutable", offset=offset)

        case TypedIndexRef(target=tgt, index=idx, offset=offset):
            arr_val = eval_expr(tgt, env)
            while isinstance(arr_val, QRef):
                arr_val = arr_val.deref()
            if not isinstance(arr_val, QArray):
                raise QuestRuntimeError(f"Index target must be Array, got {arr_val.type_name}", offset=offset)
            idx_val = eval_expr(idx, env)
            if not isinstance(idx_val, QInt):
                raise QuestRuntimeError(f"Array index must be Int, got {idx_val.type_name}", offset=offset)
            i = idx_val.value
            if i < 0 or i >= arr_val.size():
                raise QuestException(ARRAY_OP_ERROR_EXC, offset=offset)
            return QArrayElementRef(arr_val, i)

        case TypedTupleSelectRef(target=tgt, index=idx, field=fld, offset=offset):
            tup_val = eval_expr(tgt, env)
            while isinstance(tup_val, QRef):
                tup_val = tup_val.deref()
            if not isinstance(tup_val, QTuple):
                raise QuestRuntimeError(f"Tuple select target must be Tuple, got {tup_val.type_name}", offset=offset)
            val_idx = idx
            if val_idx < 0 and fld is not None:
                val_idx = tup_val._name_to_index.get(fld, -1)
            if val_idx < 0 or val_idx >= len(tup_val.elements):
                raise QuestRuntimeError("Tuple component out of bounds", offset=offset)
            elem = tup_val.get_by_index(val_idx)
            if isinstance(elem, QRef):
                return elem
            return QTupleElementRef(tup_val, val_idx)

        case TypedAssign(target=tgt, value=val, offset=offset):
            rhs_val = eval_expr(val, env)
            match tgt:
                case TypedVar(name=name):
                    cell = env.lookup(name, offset=offset)
                    if isinstance(cell, QRef):
                        cell.assign(rhs_val)
                    else:
                        env.assign(name, rhs_val, offset=offset)
                    return OK_VALUE
                case TypedSelect(target=rec_expr, field=field):
                    rec_val = eval_expr(rec_expr, env)
                    while isinstance(rec_val, QRef):
                        rec_val = rec_val.deref()
                    if isinstance(rec_val, QRecord):
                        field_cell = rec_val.get(field)
                        if isinstance(field_cell, QRef):
                            field_cell.assign(rhs_val)
                        else:
                            rec_val.fields[field] = rhs_val
                        return OK_VALUE
                    elif isinstance(rec_val, QTuple):
                        rec_val.set_by_name(field, rhs_val)
                        return OK_VALUE
                    else:
                        raise QuestRuntimeError(
                            "Field assignment target must be Record or Tuple", offset=offset
                        )
                case _:
                    raise QuestRuntimeError("Unsupported assignment target in interpreter", offset=offset)

        # 3. Functions & Application
        case TypedFun():
            return make_closure(expr, env)

        case TypedTypeApp(func=func, type_args=type_args):
            callee = eval_expr(func, env)
            type_args = tuple(env.resolve_type(t) for t in type_args)
            if isinstance(callee, QClosure) and callee.type_param_ids:
                callee = callee.instantiate(type_args)
            if isinstance(callee, QBuiltinFun):
                if callee.name == "list.nil":
                    return QList(())
            if isinstance(callee, QClosure) and len(callee.params) == 0:
                return run_closure(callee, [])
            return callee

        case TypedApp(func=func, args=args, offset=offset):
            callee_val = eval_expr(func, env)
            arg_vals = [eval_expr(arg, env) for arg in args]

            match callee_val:
                case QBuiltinFun(fn=fn):
                    return fn(*arg_vals)
                case QClosure():
                    return run_closure(callee_val, arg_vals)
                case _:
                    raise QuestRuntimeError(
                        f"Cannot call non-function of type {callee_val.type_name}",
                        offset=offset,
                    )

        # 4. Infix Operations
        case TypedInfix(left=left, op=op, right=right, offset=offset):
            left_val = eval_expr(left, env)
            right_val = eval_expr(right, env)

            # Integer Arithmetic
            if op in ("+", "-", "*", "/", "mod", "%"):
                if isinstance(left_val, QInt) and isinstance(right_val, QInt):
                    return QInt(int_arithmetic(op, left_val.value, right_val.value, offset=offset))
                raise QuestRuntimeError(
                    f"Operator '{op}' requires Int operands, got {left_val.type_name} and {right_val.type_name}",
                    offset=offset,
                )

            # Integer Relational
            if op in ("<", "<=", ">", ">="):
                if isinstance(left_val, QInt) and isinstance(right_val, QInt):
                    res = int_relational(op, left_val.value, right_val.value, offset=offset)
                    return TRUE_VALUE if res else FALSE_VALUE
                raise QuestRuntimeError(
                    f"Operator '{op}' requires Int operands, got {left_val.type_name} and {right_val.type_name}",
                    offset=offset,
                )

            # Real Arithmetic
            if op in ("++", "--", "**", "//", "^^"):
                if isinstance(left_val, QReal) and isinstance(right_val, QReal):
                    return QReal(real_arithmetic(op, left_val.value, right_val.value, offset=offset))
                raise QuestRuntimeError(
                    f"Operator '{op}' requires Real operands, got {left_val.type_name} and {right_val.type_name}",
                    offset=offset,
                )

            # Real Relational
            if op in ("<<", "<<=", ">>", ">>="):
                if isinstance(left_val, QReal) and isinstance(right_val, QReal):
                    res = real_relational(op, left_val.value, right_val.value, offset=offset)
                    return TRUE_VALUE if res else FALSE_VALUE
                raise QuestRuntimeError(
                    f"Operator '{op}' requires Real operands, got {left_val.type_name} and {right_val.type_name}",
                    offset=offset,
                )

            # String Concatenation
            if op == "<>":
                if isinstance(left_val, QString) and isinstance(right_val, QString):
                    return QString(left_val.value + right_val.value)
                raise QuestRuntimeError(
                    f"Operator '<>' requires String operands, got {left_val.type_name} and {right_val.type_name}",
                    offset=offset,
                )

            # Boolean Eager Operations
            if op == "/\\":
                if isinstance(left_val, QBool) and isinstance(right_val, QBool):
                    return TRUE_VALUE if (left_val.value and right_val.value) else FALSE_VALUE
                raise QuestRuntimeError(
                    f"Operator '/\\' requires Bool operands, got {left_val.type_name} and {right_val.type_name}",
                    offset=offset,
                )
            if op == "\\/":
                if isinstance(left_val, QBool) and isinstance(right_val, QBool):
                    return TRUE_VALUE if (left_val.value or right_val.value) else FALSE_VALUE
                raise QuestRuntimeError(
                    f"Operator '\\/' requires Bool operands, got {left_val.type_name} and {right_val.type_name}",
                    offset=offset,
                )

            # Equality & Identity
            if op == "is":
                res = qvalue_is(left_val, right_val)
                return TRUE_VALUE if res else FALSE_VALUE
            if op == "isnot":
                res = not qvalue_is(left_val, right_val)
                return TRUE_VALUE if res else FALSE_VALUE

            raise QuestRuntimeError(f"Unsupported infix operator '{op}'", offset=offset)

        # 5. Conditionals
        case TypedIf(cond=cond, then_branch=then_b, else_branch=else_b, offset=offset):
            cond_val = eval_expr(cond, env)
            match cond_val:
                case QBool(value=True):
                    return eval_expr(then_b, env)
                case QBool(value=False):
                    return eval_expr(else_b, env)
                case _:
                    raise QuestRuntimeError("Conditional expression must evaluate to Bool", offset=offset)

        # 6. Scoped Blocks
        case TypedBlock(bindings=bindings, result=result):
            block_env = env.push_scope()
            for b in bindings:
                _, block_env = eval_scoped_binding(b, block_env)
            return eval_expr(result, block_env)

        # 7. Loops & Control Flow
        case TypedLoop(body=body):
            while True:
                try:
                    eval_expr(body, env)
                except _LoopExit:
                    break
            return OK_VALUE

        case TypedWhile(cond=cond, body=body, offset=offset):
            while True:
                cond_val = eval_expr(cond, env)
                match cond_val:
                    case QBool(value=True):
                        try:
                            eval_expr(body, env)
                        except _LoopExit:
                            break
                    case QBool(value=False):
                        break
                    case _:
                        raise QuestRuntimeError("While loop condition must evaluate to Bool", offset=offset)
            return OK_VALUE

        case TypedFor(start=start, stop=stop, body=body, is_downto=is_downto, var_name=var_name, offset=offset):
            start_val = eval_expr(start, env)
            stop_val = eval_expr(stop, env)
            match (start_val, stop_val):
                case (QInt(value=start_i), QInt(value=stop_i)):
                    loop_env = env.push_scope()
                    try:
                        step = -1 if is_downto else 1
                        cur = start_i
                        while (cur <= stop_i) if not is_downto else (cur >= stop_i):
                            loop_env.define(var_name, QInt(cur))
                            try:
                                eval_expr(body, loop_env)
                            except _LoopExit:
                                break
                            cur += step
                    finally:
                        env = loop_env.pop_scope()
                    return OK_VALUE
                case _:
                    raise QuestRuntimeError("For loop bounds must evaluate to Int", offset=offset)

        case TypedExit():
            raise _LoopExit()

        # 8. Aggregates: Records & Tuples
        case TypedRecord(fields=fields):
            rec_fields: dict[str, QValue] = {}
            for f in fields:
                val = eval_expr(f.value, env)
                rec_fields[f.name] = QRef(val) if f.is_var else val
            return QRecord(rec_fields)

        case TypedTypeWitness(name=name, witness_type=witness_type, bound=bound):
            return QTypeValue(type_val=witness_type, bound=bound, name=name)

        case TypedTuple(elements=elements, type_val=type_val, simultaneous_groups=simultaneous_groups):
            labels: Optional[tuple[Optional[str], ...]] = None
            if isinstance(type_val, QTupleType):
                labels = tuple(f.name for f in type_val.fields)
            # Each component's label is bound for the components after it. A simultaneous declaration's labels are
            # bound, in a frame of their own, once all of its members' values are computed; the closures of a let rec
            # find their labels in the frame they capture, bound before they are called.
            group_of = {group[0]: group for group in simultaneous_groups}
            tup_env = env.push_scope()
            elems: list[QValue] = []
            idx = 0
            while idx < len(elements):
                group = group_of.get(idx, (idx,))
                values = [eval_expr(elements[i], tup_env) for i in group]
                if len(group) > 1 or idx in group_of:
                    tup_env = tup_env.push_scope()
                for i, val in zip(group, values):
                    elems.append(val)
                    lbl = labels[i] if labels and i < len(labels) else None
                    if lbl is not None:
                        tup_env.define(lbl, val)
                idx += len(group)
            return QTuple(elements=tuple(elems), labels=labels)

        case TypedSelect(target=target, field=field, offset=offset):
            target_val = eval_expr(target, env)
            while isinstance(target_val, QRef):
                target_val = target_val.deref()
            match target_val:
                case QRecord():
                    field_val = target_val.get(field)
                    return field_val.deref() if isinstance(field_val, QRef) else field_val
                case QTuple():
                    return target_val.get_by_name(field)
                case _:
                    raise QuestRuntimeError(
                        f"Cannot select field '{field}' from {target_val.type_name}",
                        offset=offset,
                    )

        # 9. Arrays: Creation, Repetition, Indexing, and Assignment
        case TypedArray(elements=elements):
            return QArray(elements=[eval_expr(e, env) for e in elements])

        case TypedArrayRep(count=count, init_val=init_val, offset=offset):
            count_val = eval_expr(count, env)
            match count_val:
                case QInt(value=c) if c >= 0:
                    init_v = eval_expr(init_val, env)
                    return QArray(elements=[init_v for _ in range(c)])
                case QInt():
                    raise QuestException(ARRAY_OP_ERROR_EXC, offset=offset)
                case _:
                    raise QuestRuntimeError("Array count must evaluate to Int", offset=offset)

        case TypedIndex(target=target, index=index, offset=offset):
            target_val = eval_expr(target, env)
            idx_val = eval_expr(index, env)
            match (target_val, idx_val):
                case (QArray(), QInt(value=idx)):
                    if idx < 0 or idx >= target_val.size():
                        raise QuestException(ARRAY_OP_ERROR_EXC, offset=offset)
                    return target_val.get(idx)
                case (QArray(), _):
                    raise QuestRuntimeError(f"Array index must be Int, got {idx_val.type_name}", offset=offset)
                case _:
                    raise QuestRuntimeError(f"Index target must be Array, got {target_val.type_name}", offset=offset)

        case TypedIndexAssign(target=target, index=index, value=value, offset=offset):
            target_val = eval_expr(target, env)
            idx_val = eval_expr(index, env)
            rhs_val = eval_expr(value, env)
            match (target_val, idx_val):
                case (QArray(), QInt(value=idx)):
                    if idx < 0 or idx >= target_val.size():
                        raise QuestException(ARRAY_OP_ERROR_EXC, offset=offset)
                    target_val.set(idx, rhs_val)
                    return OK_VALUE
                case (QArray(), _):
                    raise QuestRuntimeError(f"Array index must be Int, got {idx_val.type_name}", offset=offset)
                case _:
                    raise QuestRuntimeError(f"Index target must be Array, got {target_val.type_name}", offset=offset)

        # 10. Variants, Options, and Pattern Matching
        case TypedVariant(tag=tag, payload=payload):
            p_val = eval_expr(payload, env) if payload is not None else None
            return QVariant(tag=tag, payload=p_val)

        case TypedAuto(witness_type=witness_type, payload=payload):
            return QAutoVal(eval_expr(payload, env), env.resolve_type(witness_type))

        case TypedOption(
            tag=tag, payload=payload, ordinal=ordinal, ordinal_expr=ordinal_expr, type_val=type_val, offset=offset
        ):
            p_val = eval_expr(payload, env) if payload is not None else None
            if ordinal_expr is not None:
                ord_val = eval_expr(ordinal_expr, env)
                if not isinstance(ord_val, QInt):
                    raise QuestRuntimeError(
                        f"Option ordinal must evaluate to Int, got {ord_val.type_name}",
                        offset=offset,
                    )
                n = ord_val.value
                opt_type = type_val.evaluate_lazily(env)
                if not isinstance(opt_type, QOptionType):
                    raise QuestRuntimeError(f"Expected Option type, got {opt_type}", offset=offset)
                if n < 0 or n >= len(opt_type.options):
                    raise QuestRuntimeError(
                        f"Option ordinal {n} out of bounds (0 <= ordinal < {len(opt_type.options)})",
                        offset=offset,
                    )
                branch_tag = opt_type.options[n].name
                return QOption(tag=branch_tag, payload=p_val, ordinal=n)
            return QOption(tag=tag, payload=p_val, ordinal=ordinal)

        case TypedVariantCheck(target=target, tag=tag, offset=offset):
            target_val = eval_expr(target, env)
            if not isinstance(target_val, (QVariant, QOption)):
                raise QuestRuntimeError(
                    f"Variant query target must be Variant or Option, got {target_val.type_name}",
                    offset=offset,
                )
            return QBool(target_val.tag == tag)

        case TypedVariantAssert(target=target, tag=tag, offset=offset):
            target_val = eval_expr(target, env)
            if not isinstance(target_val, (QVariant, QOption)):
                raise QuestRuntimeError(
                    f"Variant assert target must be Variant or Option, got {target_val.type_name}",
                    offset=offset,
                )
            if target_val.tag != tag:
                raise QuestException(
                    VARIANT_ERROR_EXC,
                    offset=offset,
                )
            if isinstance(target_val, QOption):
                ord_val = QInt(target_val.ordinal)
                if target_val.payload is None:
                    return QTuple(elements=(ord_val,), labels=(None,))
                if isinstance(target_val.payload, QTuple):
                    return QTuple(
                        elements=(ord_val, *target_val.payload.elements),
                        labels=(None, *target_val.payload.labels),
                    )
                return QTuple(elements=(ord_val, target_val.payload), labels=(None, None))
            if target_val.payload is not None:
                return target_val.payload
            return QOk()

        case TypedCase(target=target, branches=branches, else_branch=else_branch, offset=offset):
            target_val = eval_expr(target, env)
            if not isinstance(target_val, (QVariant, QOption)):
                raise QuestRuntimeError(
                    f"Case target must be Variant or Option, got {target_val.type_name}",
                    offset=offset,
                )
            for branch in branches:
                if target_val.tag in branch.tags:
                    if branch.binder is not None:
                        child_env = env.push_scope()
                        child_env.define(
                            branch.binder.name,
                            target_val.payload if target_val.payload is not None else OK_VALUE,
                        )
                        try:
                            return eval_expr(branch.body, child_env)
                        finally:
                            env = child_env.pop_scope()
                    else:
                        return eval_expr(branch.body, env)
            if else_branch is not None:
                return eval_expr(else_branch, env)
            raise QuestRuntimeError(f"Unhandled case tag '{target_val.tag}'", offset=offset)

        # 11. Exceptions
        case TypedException(name=name, symbol=symbol):
            exc_val = env.made_exception(symbol.symbol_id) if symbol is not None else None
            if exc_val is None:
                exc_val = QExceptionVal(name=name)
            if name:
                env.define(name, exc_val)
            return exc_val

        case TypedRaise(exc=exc, payload=payload, offset=offset):
            tag_val = eval_expr(exc, env)
            if not isinstance(tag_val, QExceptionVal):
                raise QuestRuntimeError(
                    f"Target of raise must be Exception, got {tag_val.type_name}",
                    offset=offset,
                )
            payload_val = eval_expr(payload, env) if payload is not None else None
            payload_type = payload.type_val if payload is not None else None
            raise QuestException(
                exc_val=tag_val,
                payload=payload_val,
                payload_type=payload_type,
                offset=offset,
            )

        case TypedTry(body=body, branches=branches, else_branch=else_branch, offset=offset):
            try:
                return eval_expr(body, env)
            except QuestException as raised_exc:
                for branch in branches:
                    pattern_val = eval_expr(branch.exc_pattern, env)
                    if raised_exc.exc_val is pattern_val:
                        if branch.binder is not None:
                            child_env = env.push_scope()
                            actual_payload = (
                                raised_exc.payload
                                if raised_exc.payload is not None
                                else OK_VALUE
                            )
                            child_env.define(branch.binder.name, actual_payload)
                            try:
                                return eval_expr(branch.body, child_env)
                            finally:
                                env = child_env.pop_scope()
                        else:
                            return eval_expr(branch.body, env)
                if else_branch is not None:
                    return eval_expr(else_branch, env)
                raise

        # 12. Dynamic Types & Type Inspection
        case TypedInspect(target=target, branches=branches, else_branch=else_branch, offset=offset):
            target_dyn = eval_expr(target, env)
            if not isinstance(target_dyn, QAutoVal):
                raise QuestRuntimeError(
                    f"Inspect target must be an auto value, got {target_dyn.type_name}",
                    offset=offset,
                )
            for branch in branches:
                match_type = env.resolve_type(branch.match_type)
                if (
                    is_type_equal(target_dyn.type_val, match_type)
                    if branch.exact
                    else is_subtype(target_dyn.type_val, match_type)
                ):
                    if branch.binders:
                        child_env = env.push_scope()
                        for b_sym in branch.binders:
                            child_env.define(b_sym.name, target_dyn.value)
                        try:
                            return eval_expr(branch.body, child_env)
                        finally:
                            env = child_env.pop_scope()
                    else:
                        return eval_expr(branch.body, env)
            if else_branch is not None:
                return eval_expr(else_branch, env)
            raise QuestException(DYNAMIC_ERROR_EXC, offset=offset)

        case _:
            raise QuestRuntimeError(
                f"Unhandled expression node: {expr.__class__.__name__}",
                offset=getattr(expr, "offset", 0),
            )


# ============================================================================
# 4. Binding & Program Evaluator
# ============================================================================

def _define_members(members: tuple[TypedLetValue, ...], values: tuple[QValue, ...], env: RuntimeEnvironment) -> None:
    """Binds the members of a simultaneous value declaration to their values, computed beforehand."""
    for member, val in zip(members, values):
        env.define(member.name, QRef(val) if member.symbol.is_var else val)


def make_closure(fun: TypedFun, env: RuntimeEnvironment, binder: Optional[str] = None,
                 name: Optional[str] = None) -> QClosure:
    """The closure of fun in env, bound to binder if it is let-bound, named in tracebacks by the frame making it
    (docs/exceptions.md §2.3). A recursive function's closure also has its name (name), which printing shows."""
    enclosing = env.call_stack[-1] if env.call_stack else MAIN_FRAME
    return QClosure(
        params=tuple(p.name for p in fun.params),
        body=fun.body,
        env=env,
        name=name,
        type_param_ids=fun.type_param_ids,
        trace_name=frame_name(enclosing, binder),
    )


def note_frames(error: QuestCompilerError, env: RuntimeEnvironment) -> None:
    """Records on an error the frames running where it was raised, the first time it leaves a frame."""
    if error.frames is None:
        error.frames = tuple(reversed(env.call_stack))


def run_closure(closure: QClosure, args: list[QValue]) -> QValue:
    """Applies a closure to its arguments, in its frame: an external's built-in implementation, or the closure's body.
    An error raised inside is located in the file the closure was made in, unless code it called located it already,
    and records the frames running (docs/exceptions.md §3.2, §4)."""
    env = closure.env
    env.call_stack.append(closure.trace_name)
    try:
        if isinstance(closure.body, TypedExternal):
            from quest.interpreter.builtins import resolve_external_symbol

            ext_val = resolve_external_symbol(closure.body.symbol)
            if isinstance(ext_val, QBuiltinFun):
                return ext_val.fn(*args)
            if callable(ext_val):
                return ext_val(*args)
            return ext_val
        call_env = env.push_scope()
        call_env.bind_types(closure.type_bindings)
        for param_name, arg_val in zip(closure.params, args):
            call_env.define(param_name, arg_val)
        # The body is a scope of its own: exceptions made inside it exist throughout it
        call_env = make_scope_exceptions(closure.body, call_env)
        return eval_expr(closure.body, call_env)
    except QuestCompilerError as error:
        if error.source_map is None:
            error.source_map = env.source_map
        note_frames(error, env)
        raise
    finally:
        env.call_stack.pop()


def run_module_init(name: str, bindings, mod_env: RuntimeEnvironment) -> RuntimeEnvironment:
    """Runs a module's bindings in its frame, locating the errors they raise in the module's file (mod_env's), and
    returns the frame its last binding was evaluated in, where its exports are found (eval_scoped_binding)."""
    mod_env.call_stack.append(init_frame(name))
    try:
        for b in bindings:
            _, mod_env = eval_scoped_binding(b, mod_env)
        return mod_env
    except QuestCompilerError as error:
        if error.source_map is None:
            error.source_map = mod_env.source_map
        note_frames(error, mod_env)
        raise
    finally:
        mod_env.call_stack.pop()


def eval_bound_value(name: str, value: TypedExpr, env: RuntimeEnvironment) -> QValue:
    """The value of a let binding of name: a function's closure is bound to the name."""
    if isinstance(value, TypedFun):
        return make_closure(value, env, name)
    return eval_expr(value, env)


def eval_binding(binding: TypedBinding, env: RuntimeEnvironment) -> QValue:
    """Evaluates a declaration or binding inside a block or top-level program."""
    match binding:
        case TypedLetValue(name=name, value=value, is_rec=is_rec, symbol=symbol):
            if is_rec and isinstance(value, TypedFun):
                closure = make_closure(value, env, name, name=name)
                env.define(name, closure)
                return closure
            val = eval_bound_value(name, value, env)
            if symbol.is_var:
                env.define(name, QRef(val))
            else:
                env.define(name, val)
            return val

        case TypedLetValueGroup(members=members, is_rec=True):
            # Each member's closure captures env, where the others are defined before any is called; the result
            # holds the members' values, for echo
            values = tuple(eval_binding(member, env) for member in members)
            return QTuple(values, tuple(member.name for member in members))

        case TypedLetValueGroup(members=members):
            # Simultaneous: every value is computed before any member is bound
            values = tuple(eval_bound_value(member.name, member.value, env) for member in members)
            _define_members(members, values, env)
            return QTuple(values, tuple(member.name for member in members))

        case TypedLetType() | TypedLetTypeGroup() | TypedDefKind() | TypedInterface():
            # Types, kinds, and interface declarations are erased at runtime
            return OK_VALUE

        case TypedModule(name=mod_name, bindings=mod_bindings, scope=mod_scope):
            # A module declared in the program is run where it is declared, each time (a REPL input that declares a
            # module again gets the new one); modules in files are run once (load_module_for_interpreter)
            mod_env = run_module_init(mod_name, mod_bindings, env.push_scope())
            exported_fields: dict[str, QValue] = {}
            for val_name in mod_scope.values:
                exported_fields[val_name] = mod_env.lookup(val_name)
            rec = QRecord(exported_fields)
            env.define(mod_name, rec)
            return rec

        case TypedImport(items=items):
            for item in items:
                # Evaluated modules are shared by canonical name, which distinguishes modules imported by the same
                # name from different directories (docs/modules.md §2.3).
                for local_name, mod_path, canon in zip(
                    item.names, item.effective_module_paths, item.effective_canonical_module_paths
                ):
                    mod_val = load_module_for_interpreter(mod_path, item.effective_interface_path, env, canon)
                    if mod_val is not None:
                        env.define(local_name, mod_val)
            return OK_VALUE

        case TypedExprStmt(expr=inner_expr):
            return eval_expr(inner_expr, env)

        case _:
            raise QuestRuntimeError(f"Unhandled binding node: {binding.__class__.__name__}")


def make_scope_exceptions(node: TypedNode, env: RuntimeEnvironment) -> RuntimeEnvironment:
    """Makes, before node runs, the named exceptions it makes for its scope (scope_exceptions), defining their names,
    and returns the frame it runs in: a frame of its own if a name rebinds one of env's frame, as eval_scoped_binding
    gives a binding that rebinds one."""
    exceptions = scope_exceptions(node)
    if any(exc.name in env.bindings for exc in exceptions):
        env = env.push_scope()
    for exc in exceptions:
        exc_val = QExceptionVal(name=exc.name)
        env.define(exc.name, exc_val)
        env.made_exceptions[exc.symbol.symbol_id] = exc_val
    return env


def eval_scoped_binding(binding: TypedBinding, env: RuntimeEnvironment) -> tuple[QValue, RuntimeEnvironment]:
    """Evaluates a binding of a block, a program, or a module in env's frame, returning its value and the frame the
    bindings after it are evaluated in. A binding that rebinds a name of env's frame gets a frame of its own, so that
    closures built earlier keep the binding they captured (scoping is lexical), and so do the members of a
    simultaneous declaration, so that closures built by their values keep the bindings the members shadow."""
    env = make_scope_exceptions(binding, env)
    if isinstance(binding, TypedLetValueGroup) and not binding.is_rec:
        values = tuple(eval_bound_value(member.name, member.value, env) for member in binding.members)
        env = env.push_scope()
        _define_members(binding.members, values, env)
        return QTuple(values, tuple(member.name for member in binding.members)), env
    if any(getattr(member, "name", None) in env.bindings for member in binding_members(binding)):
        env = env.push_scope()
    return eval_binding(binding, env), env


def eval_program_phrases(
    program: TypedProgram,
    env: Optional[RuntimeEnvironment] = None,
    on_result: Optional[Callable[[TypedBinding | TypedExpr, QValue], None]] = None,
) -> tuple[list[tuple[TypedBinding | TypedExpr, QValue]], RuntimeEnvironment]:
    """Evaluates an entire typed program sequentially, returning (phrase, value) pairs, and the frame its last phrase
    was evaluated in, which phrases evaluated after the program (in the REPL) continue in (eval_scoped_binding).

    on_result, if given, is called with each pair as soon as its phrase is evaluated, before later phrases can
    change the value (by assigning to a component of it) or write output of their own.
    """
    if env is None:
        env = RuntimeEnvironment.create_root_env()

    results: list[tuple[TypedBinding | TypedExpr, QValue]] = []
    for phrase in program.phrases:
        match phrase:
            case TypedBinding():
                val, env = eval_scoped_binding(phrase, env)
                results.append((phrase, val))
            case TypedExpr():
                env = make_scope_exceptions(phrase, env)
                val = eval_expr(phrase, env)
                results.append((phrase, val))
            case _:
                raise QuestRuntimeError(f"Unknown top-level phrase: {phrase.__class__.__name__}")
        if on_result is not None:
            on_result(*results[-1])

    return results, env


def eval_program(program: TypedProgram, env: Optional[RuntimeEnvironment] = None) -> QValue:
    """Evaluates an entire typed program sequentially, returning the final phrase value."""
    results, _ = eval_program_phrases(program, env)
    return results[-1][1] if results else OK_VALUE


def load_module_for_interpreter(
    name: str,
    expected_interface: str,
    r_env: RuntimeEnvironment,
    canonical_name: Optional[str] = None,
) -> Optional[QValue]:
    """Loads and evaluates module `name`, as imported from r_env.current_dir, for the interpreter.

    The module is the unit r_env.units resolves the import to; it is evaluated from that unit's typed module, which
    the type checker elaborated, or which is elaborated here in an environment of its own (a module the program
    uses without importing it, such as a standard library module named in an expression). Its value is kept in the
    unit, so each module is evaluated once, whatever path imports it (docs/modules.md §2.3), until a REPL input
    that loaded it is rolled back (UnitGraph.restore). An import that knows the module's canonical name (from the
    type checker) passes it, and a module already run is found by it without resolving the import again.
    """
    from quest.types.env import Environment
    from quest.modules.loader import load_module

    graph = r_env.units
    if canonical_name is not None:
        known = graph.find(UnitKind.MODULE, canonical_name)
        if known is not None and known.value is not None:
            return known.value
    resolved = graph.resolver.module(name, r_env.current_dir, Roots.of(r_env.include_paths, r_env.program_dir))
    file_path = resolved.source
    canon_name = resolved.canonical_name
    loaded = graph.find(UnitKind.MODULE, canon_name)
    if loaded is not None and loaded.value is not None:
        return loaded.value

    typed_mod = graph.typed_module(canon_name)
    if typed_mod is None:
        type_env = Environment()
        type_env.units = UnitGraph(resolver=graph.resolver)
        type_env.include_paths = list(r_env.include_paths)
        type_env.current_dir = r_env.current_dir
        type_env.program_dir = r_env.program_dir
        typed_mod = load_module(name, expected_interface, type_env)
        graph.unit(UnitKind.MODULE, canon_name).typed_module = typed_mod

    # The module's own imports are resolved from its directory.
    mod_env = r_env.push_scope()
    if file_path is not None:
        mod_env.current_dir = file_path.parent
        mod_env.source_map = SourceMap(file_path.read_text(encoding="utf-8"), display_file_name(file_path))
    mod_env = run_module_init(typed_mod.name, typed_mod.bindings, mod_env)

    exported_fields = {}
    for val_name in typed_mod.scope.values:
        exported_fields[val_name] = mod_env.lookup(val_name)

    rec = QRecord(exported_fields)
    graph.unit(UnitKind.MODULE, canon_name).value = rec
    return rec
