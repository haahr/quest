"""Lowering from the typed AST to Core IR (docs/ir.md §12, step 3).

value(e) lowers an expression, emitting statements into the current body, and
returns the atom holding its value; effect(e) lowers one for its effect alone.
An expression producing a value on several paths (if, case, inspect, try) joins
them through a join point, after which lowering continues in the join point's
continuation. After a terminator (raise, exit), lowering continues in a
discarded body, so that no statement follows a terminator.

Every typed-AST symbol is mapped to one IR variable when its binder is lowered;
uses look the variable up by symbol. A use of a variable whose binder is not in
the unit (an imported module, a module's member) is a module reference or a
module member, and a use of a built-in value is a constant or a built-in
function.
"""

from __future__ import annotations

from typing import Optional

from quest.diagnostics import MAIN_FRAME, frame_name, init_frame
from quest.modules.elaboration import build_record_type_from_scope
from quest.modules.stdlib import STANDARD_LIBRARY_MODULE_NAMES, STANDARD_LIBRARY_MODULES
from quest.config import CompilerOptions
from quest.types.env import Environment, ValueSymbol
from quest.ir import nodes as ir
from quest.codegen.layout import resolved_shape
from quest.ir.shapes import shape
from quest.types.canonical import collect_fun_quantifiers, option_case_names
from quest.typechecker.typed_ast import (
    typed_fields,
    TypedApp,
    TypedArray,
    TypedArrayRep,
    TypedAssign,
    TypedAuto,
    TypedBlock,
    TypedBool,
    TypedCase,
    TypedChar,
    TypedDefKind,
    TypedDerefCell,
    TypedException,
    named_exceptions_in,
    scope_exceptions,
    TypedExit,
    TypedExpr,
    TypedExprStmt,
    TypedExternal,
    TypedFor,
    TypedFun,
    TypedIf,
    TypedImport,
    TypedIndex,
    TypedIndexAssign,
    TypedIndexRef,
    TypedInfix,
    TypedInspect,
    TypedInt,
    TypedInterface,
    TypedLetType,
    TypedLetTypeGroup,
    TypedLetValue,
    TypedLetValueGroup,
    TypedLoop,
    TypedModule,
    TypedNode,
    TypedOk,
    TypedOption,
    TypedProgram,
    TypedRaise,
    TypedReal,
    TypedRecord,
    TypedSelect,
    TypedSelectRef,
    TypedString,
    TypedTry,
    TypedTuple,
    TypedTupleSelectRef,
    TypedTypeApp,
    TypedTypeWitness,
    TypedVar,
    TypedVarCell,
    TypedVariant,
    TypedVariantAssert,
    TypedVariantCheck,
    TypedWhile,
)
from quest.types import (
    is_type_equal,
    QPowerKind,
    BOOL_TYPE,
    CHAR_TYPE,
    EXCEPTION_TYPE,
    INFIX_OPERATORS,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    QAllType,
    QFunType,
    QRecordField,
    QTupleField,
    QTupleType,
    QRecordType,
    QType,
    QTypeVar,
    QVarType,
    QOutType,
    binds_module,
)

def _expected_params(var_t: QType, fun_t: QType, count: int) -> Optional[list[QType]]:
    """The parameter types of a function's variable's type (var_t), as written,
    for a function of count parameters and type fun_t, in the function's own
    type parameters; None when they are not known."""
    fun_quants = fun_t.quantifiers if isinstance(fun_t, QAllType) else ()
    quants, inner = collect_fun_quantifiers(var_t)
    if len(quants) != len(fun_quants) or not isinstance(inner, QFunType) or len(inner.params) != count:
        return None
    subst = {vq.symbol_id: QTypeVar(fq.name, fq.symbol_id, fq.bound) for vq, fq in zip(quants, fun_quants)}
    return [param.type_val.substitute(subst) if subst else param.type_val for param in inner.params]


def _option_cases(t: QType) -> Optional[tuple[str, ...]]:
    """The names of the cases of t as written, if it is an option type (or a
    type parameter bounded by one)."""
    try:
        return option_case_names(t)
    except ValueError:
        return None


_BUILTIN_FUNCTIONS = frozenset(INFIX_OPERATORS) | {"is", "isnot", "not", "extent", "ordinal"}
# The standard library's array operations, which are lowered to the IR's
# (array_op)
_ARRAY_OPS = frozenset({"new", "size", "get", "set"})


def _captured_mutables(prog: TypedProgram) -> set[int]:
    """The symbols of the local var variables that functions nested in their
    scope use: a let var anywhere but directly at a unit's or a module's top
    level (where it is global), used inside a function within its scope."""
    declared: dict[int, int] = {}
    captured: set[int] = set()
    seen: set[int] = set()

    def walk(n, depth: int, top: bool) -> None:
        if isinstance(n, (list, tuple)):
            for item in n:
                walk(item, depth, top)
            return
        if id(n) in seen:
            return
        fields = typed_fields(n)
        if fields is None:
            return
        seen.add(id(n))
        if isinstance(n, TypedLetValue) and n.symbol.is_var and not top:
            declared[n.symbol.symbol_id] = depth
        elif isinstance(n, TypedVar) and declared.get(n.symbol.symbol_id, depth) < depth:
            captured.add(n.symbol.symbol_id)
        inner = depth + 1 if isinstance(n, TypedFun) else depth
        # A unit's phrases, a module's bindings, and a group's members are at
        # the top level their parent is at
        inner_top = top and isinstance(n, (TypedProgram, TypedModule, TypedLetValueGroup))
        for part in fields:
            walk(part, inner, inner_top)

    walk(prog, 0, True)
    return captured


class LoweringError(Exception):
    """A typed program the lowering does not handle (a gap in the lowering, not
    an error in the program)."""


class _Lowerer:
    """Lowers a unit's typed program (or module) to Core IR, holding what the
    lowering needs as it goes.

    Core IR (docs/ir.md) is flat: an operation's operands are atoms, variables
    and constants, never nested expressions, so every intermediate value is
    named by a let. Where control paths meet again, as after an if
    expression's branches, the IR has a join point, a local block that the
    paths jump to with their values. So

        let abs(n: Int): Int = if n < 0 then 0 - n else n end;

    is lowered to (as --stop-after ir_core prints it)

        fun abs(n: Int): Int {
          join k1(r: Int) {
            return r
          } in {
            let %1: Bool = prim <(n, 0)
            if %1 {
              let %2: Int = prim -(0, n)
              jump k1(%2)
            } else {
              jump k1(n)
            }
          }
        }

    Statements are appended to the current body, self.body, which a construct
    with bodies of its own (the if's branches, a function, a join point)
    replaces while it lowers them (in_body). The rest of the state:

    - vars, the IR variable of each typed-AST symbol whose binder has been
      lowered, and builtins, the builtin values' names by symbol;
    - loops, the labels of the enclosing loops, innermost last: an exit
      expression leaves the innermost;
    - imports and module_refs, the modules the unit imports and defines;
    - frame, the name of the code being lowered as exception tracebacks show
      it, and made, the exceptions created ahead of the bindings that declare
      them (make_scope_exceptions).

    value and effect, the entry points for expressions, are described in the
    module's docstring."""

    def __init__(self, env: Environment, echo: bool, print_result: bool) -> None:
        self.vars: dict[int, ir.Var] = {}
        self.builtins: dict[int, str] = {
            sym.symbol_id: name for name, sym in env.base_scope.values.items() if isinstance(sym, ValueSymbol)
        }
        self.env = env
        self.echo = echo
        self.print_result = print_result
        # The source file's map, in which the offsets of the nodes that can
        # raise are (docs/exceptions.md §3.1)
        self.source_map = env.source_map
        # The frame of the code being lowered, which names the functions it
        # makes (docs/exceptions.md §2.3)
        self.frame = MAIN_FRAME
        self.body = ir.Body()
        self.loops: list[str] = []
        self.label_counts: dict[str, int] = {}
        self.imports: list[ir.Import] = []
        # The modules the unit defines and imports, by the symbols their names
        # bind
        self.module_refs: dict[int, ir.ModuleRef] = {}
        # Exceptions made inside an expression, whose names the enclosing scope
        # sees: made before the binding containing them (make_scope_exceptions),
        # and not yet reached where they are written
        self.made: set[int] = set()
        # The local var variables that closures capture (_captured_mutables),
        # and the boxes that hold those bound so far: a tuple of one var
        # component, which the frame and the closures share
        self.captured: set[int] = set()
        self.boxes: dict[int, ir.Var] = {}

    # Building

    def emit(self, statement) -> None:
        self.body.statements.append(statement)

    def terminate(self, terminator) -> None:
        """Emits a terminator; what follows it is unreachable, and goes into a
        body that is discarded."""
        self.emit(terminator)
        self.body = ir.Body()

    def fresh(self, hint: str, t: QType, mutable: bool = False) -> ir.Var:
        return ir.Var(hint, t, mutable)

    def label(self, prefix: str) -> str:
        n = self.label_counts.get(prefix, 0) + 1
        self.label_counts[prefix] = n
        return f"{prefix}{n}"

    def let(self, op, t: QType, into: Optional[ir.Var] = None, hint: str = "") -> ir.Var:
        var = into if into is not None else self.fresh(hint, t)
        self.emit(ir.Let(var, op))
        return var

    def bind_symbol(self, symbol: ValueSymbol, t: Optional[QType] = None, mutable: bool = False) -> ir.Var:
        if symbol.symbol_id in self.vars:
            raise LoweringError(f"symbol '{symbol.name}' (#{symbol.symbol_id}) is bound twice")
        var = self.fresh(symbol.name, t if t is not None else symbol.type_val, mutable)
        self.vars[symbol.symbol_id] = var
        return var

    def in_body(self, body: ir.Body):
        """Lowers into another body for the duration of a with block."""
        lowerer = self

        class _Into:
            def __enter__(self_inner):
                self_inner.saved = lowerer.body
                lowerer.body = body
                return body

            def __exit__(self_inner, *exc):
                lowerer.body = self_inner.saved
                return False

        return _Into()

    def const(self, value, t: QType) -> ir.Const:
        return ir.Const(value, shape(t))

    def copy_into(self, atom: ir.Atom, into: Optional[ir.Var]) -> ir.Atom:
        if into is None:
            return atom
        self.emit(ir.Let(into, atom))
        return into

    # Values

    def value(self, e: TypedExpr, into: Optional[ir.Var] = None) -> ir.Atom:
        """Lowers e, returning the atom that holds its value (into, if
        given)."""
        match e:
            case TypedInt(value=v):
                return self.copy_into(self.const(v, INT_TYPE), into)
            case TypedReal(value=v):
                return self.copy_into(self.const(v, REAL_TYPE), into)
            case TypedBool(value=v):
                return self.copy_into(self.const(v, BOOL_TYPE), into)
            case TypedChar(value=v):
                return self.copy_into(self.const(v, CHAR_TYPE), into)
            case TypedString(value=v):
                return self.copy_into(self.const(v, STRING_TYPE), into)
            case TypedOk():
                return self.copy_into(self.const(None, OK_TYPE), into)
            case TypedVar():
                return self.var_value(e, into)
            case TypedDerefCell(target=target):
                if isinstance(target, TypedVar) and (box := self.boxes.get(target.symbol.symbol_id)) is not None:
                    return self.let(ir.TupleField(box, 0), e.type_val, into)
                if isinstance(target, TypedVar) and (var := self.vars.get(target.symbol.symbol_id)) and var.mutable:
                    # Reading a mutable variable
                    return self.copy_into(var, into)
                return self.let(ir.Load(self.value(target)), e.type_val, into)
            case TypedExternal(symbol=symbol):
                return self.let(ir.External(symbol), e.type_val, into)
            case TypedFun():
                var = into if into is not None else self.fresh("f", e.type_val)
                self.emit(ir.Funs((self.function(e, var),)))
                return var
            case TypedApp():
                return self.call(e, into)
            case TypedTypeApp():
                return self.type_app(e, into)
            case TypedInfix(left=left, op=op, right=right):
                l = self.value(left)
                r = self.value(right)
                return self.let(ir.Prim(op, (l, r), e.offset), e.type_val, into)
            case TypedRecord(fields=fields):
                atoms = tuple((f.name, self.value(f.value), f.is_var) for f in fields)
                return self.let(ir.MakeRecord(atoms), e.type_val, into)
            case TypedTuple():
                return self.tuple(e, into)
            case TypedSelect(target=target, field=fld):
                return self.select(e, target, fld, into)
            case TypedIndex(target=target, index=index):
                a = self.value(target)
                i = self.value(index)
                return self.let(ir.Index(a, i, e.offset), e.type_val, into)
            case TypedArray(elements=elements):
                return self.let(ir.MakeArray(tuple(self.value(x) for x in elements)), e.type_val, into)
            case TypedArrayRep(count=count, init_val=init):
                n = self.value(count)
                v = self.value(init)
                return self.let(ir.ArrayRep(n, v, e.offset), e.type_val, into)
            case TypedVarCell(value=v):
                return self.let(ir.AddrCell(self.value(v)), e.type_val, into)
            case TypedSelectRef(target=target, field=fld):
                return self.let(ir.AddrField(self.value(target), fld), e.type_val, into)
            case TypedIndexRef(target=target, index=index):
                a = self.value(target)
                i = self.value(index)
                return self.let(ir.AddrElement(a, i, e.offset), e.type_val, into)
            case TypedTupleSelectRef(target=target, index=index, field=fld):
                t = self.value(target)
                return self.let(ir.AddrComponent(t, self.tuple_index(target.type_val, index, fld)), e.type_val, into)
            case TypedVariant(tag=tag, payload=payload):
                p = self.value(payload) if payload is not None else None
                return self.let(ir.MakeVariant(tag, p), e.type_val, into)
            case TypedOption(tag=tag, payload=payload, ordinal_expr=ordinal_expr):
                ordinal = self.value(ordinal_expr) if ordinal_expr is not None else None
                p = self.value(payload) if payload is not None else None
                cases = option_case_names(e.type_val) if ordinal is not None else ()
                return self.let(ir.MakeOption(tag, p, ordinal, e.offset, cases), e.type_val, into)
            case TypedVariantCheck(target=target, tag=tag):
                return self.let(ir.IsTag(self.value(target), tag), e.type_val, into)
            case TypedVariantAssert(target=target, tag=tag):
                cases = _option_cases(target.type_val)
                ordinal = cases.index(tag) if cases is not None else None
                return self.let(ir.Payload(self.value(target), tag, e.offset, ordinal=ordinal), e.type_val, into)
            case TypedAuto(witness_type=witness, auto_type=auto_type, payload=payload):
                return self.let(ir.MakeAuto(witness, auto_type, self.value(payload)), e.type_val, into)
            case TypedException(name=name, payload_type=payload_type, symbol=symbol):
                if symbol is not None and (made := self.vars.get(symbol.symbol_id)) is not None:
                    if id(made) not in self.made:
                        raise LoweringError(f"exception '{name}' is bound twice")
                    self.made.discard(id(made))
                    return self.copy_into(made, into)
                if symbol is not None:
                    bound = self.bind_symbol(symbol, e.type_val)
                    self.emit(ir.Let(bound, ir.MakeException(name, payload_type)))
                    return self.copy_into(bound, into)
                return self.let(ir.MakeException(name, payload_type), e.type_val, into)
            case TypedBlock(bindings=bindings, result=result):
                for b in bindings:
                    self.binding(b)
                return self.value(result, into)
            case TypedIf() | TypedCase() | TypedInspect() | TypedTry():
                if e.type_val is OK_TYPE:
                    self.effect(e)
                    return self.copy_into(self.const(None, OK_TYPE), into)
                return self.joined(e, into)
            case TypedWhile() | TypedLoop() | TypedFor() | TypedAssign() | TypedIndexAssign():
                self.effect(e)
                return self.copy_into(self.const(None, OK_TYPE), into)
            case TypedRaise() | TypedExit():
                self.effect(e)
                # Unreachable: the value is never used
                return self.let(ir.Load(self.const(None, OK_TYPE)), e.type_val, into)
            case _:
                raise LoweringError(f"lowering {type(e).__name__} is not implemented")

    def var_value(self, e: TypedVar, into: Optional[ir.Var]) -> ir.Atom:
        sym_id = e.symbol.symbol_id
        if (box := self.boxes.get(sym_id)) is not None:
            # A boxed variable's address is its box's component's
            return self.let(ir.AddrComponent(box, 0), e.type_val, into)
        var = self.vars.get(sym_id)
        if var is not None:
            if var.mutable:
                # A mutable variable not read through a dereference is passed by
                # address (@x)
                return self.let(ir.AddrVar(var), e.type_val, into)
            return self.copy_into(var, into)
        if sym_id in self.builtins:
            name = self.builtins[sym_id]
            if name in ("true", "false"):
                return self.copy_into(self.const(name == "true", BOOL_TYPE), into)
            if name == "ok":
                return self.copy_into(self.const(None, OK_TYPE), into)
            return self.let(ir.Builtin(name), e.type_val, into)
        if (module := self.module_ref(e)) is not None:
            return self.let(ir.ModuleMember(module), e.type_val, into)
        raise LoweringError(f"variable '{e.name}' (#{sym_id}) has no binder in the unit")

    def module_ref(self, e: TypedExpr) -> Optional[ir.ModuleRef]:
        """The module e refers to, if it is a reference to a module rather than
        a value."""
        if not isinstance(e, TypedVar) or e.symbol.symbol_id in self.vars:
            return None
        module = self.module_refs.get(e.symbol.symbol_id)
        if module is None and binds_module(e.name, e.type_val):
            # A standard library module, which a unit uses without importing it
            name = STANDARD_LIBRARY_MODULE_NAMES.get(e.name, STANDARD_LIBRARY_MODULE_NAMES.get(e.name.lower()))
            if name is None:
                raise LoweringError(f"module '{e.name}' (#{e.symbol.symbol_id}) is neither defined nor imported")
            module = self.make_import(e.name, name, name, STANDARD_LIBRARY_MODULES[name])
            self.imports.append(module)
            self.module_refs[e.symbol.symbol_id] = module
        return module

    def callee(self, func: TypedExpr) -> tuple[Optional[ir.Var], Optional[ir.ModuleRef], Optional[str]]:
        """What a call or type application applies: a variable, or a module's
        member."""
        if isinstance(func, TypedSelect) and (module := self.module_ref(func.target)) is not None:
            return None, module, func.field
        atom = self.value(func)
        if not isinstance(atom, ir.Var):
            raise LoweringError(f"calling a constant: {func}")
        return atom, None, None

    def type_app(self, e: TypedTypeApp, into: Optional[ir.Var]) -> ir.Atom:
        """A type application, f(:A)(:B) as one. Applied to fewer types than
        it takes, a polymorphic function is a closure over the rest (and its
        value parameters, if it has any), which applies it to all of them, since
        the backend calls a polymorphic function with all its type arguments
        at once."""
        func: TypedExpr = e
        type_args: tuple[QType, ...] = ()
        while isinstance(func, TypedTypeApp):
            type_args = tuple(func.type_args) + type_args
            func = func.func
        callee, module, member = self.callee(func)
        callee_type = func.type_val if module is not None else None
        quants, _ = collect_fun_quantifiers(func.type_val)
        if len(type_args) >= len(quants):
            return self.let(ir.TypeApp(callee, type_args, module, member, callee_type), e.type_val, into)
        rest, inner = collect_fun_quantifiers(e.type_val)
        var = into if into is not None else self.fresh("f", e.type_val)
        type_params = tuple(
            ir.TypeParam(q.name, q.symbol_id, q.bound, shape(q.bound.bound) if isinstance(q.bound, QPowerKind) else None)
            for q in rest
        )
        all_type_args = type_args + tuple(QTypeVar(q.name, q.symbol_id, q.bound) for q in rest)
        params = []
        body = ir.Body()
        with self.in_body(body):
            if isinstance(inner, QFunType):
                args = []
                for p in inner.params:
                    param_t = p.type_val.element_type if isinstance(p.type_val, (QVarType, QOutType)) else p.type_val
                    mode = "var" if p.is_var or isinstance(p.type_val, QVarType) else (
                        "out" if p.is_out or isinstance(p.type_val, QOutType) else "value")
                    param = self.fresh(p.name, param_t, mutable=mode != "value")
                    params.append((param, mode))
                    if mode == "value":
                        args.append(param)
                    else:
                        ref_t = QVarType(element_type=param_t) if mode == "var" else QOutType(element_type=param_t)
                        args.append(self.let(ir.AddrVar(param), ref_t))
                result_t = inner.result_type
                result = self.let(ir.Call(callee, all_type_args, tuple(args), module, member, callee_type), result_t)
            else:
                result_t = inner
                result = self.let(ir.TypeApp(callee, all_type_args, module, member, callee_type), result_t)
            self.terminate(ir.Return(result))
        self.emit(ir.Funs((ir.Function(var, type_params, tuple(params), result_t, body, trace_name=self.frame),)))
        return var

    def call(self, e: TypedApp, into: Optional[ir.Var]) -> ir.Atom:
        func, type_args = e.func, ()
        while isinstance(func, TypedTypeApp):
            type_args = tuple(func.type_args) + type_args
            func = func.func
        if isinstance(func, TypedVar) and func.symbol.symbol_id in self.builtins:
            name = self.builtins[func.symbol.symbol_id]
            if name in _BUILTIN_FUNCTIONS:
                args = tuple(self.value(a) for a in e.args)
                if name == "ordinal":
                    op = ir.Ordinal(args[0], option_case_names(e.args[0].type_val))
                else:
                    op = ir.Prim(name, args, e.offset)
                return self.let(op, e.type_val, into)
        callee, module, member = self.callee(func)
        args = tuple(self.argument(a) for a in e.args)
        if isinstance(module, ir.Import) and module.canonical_path.lower() == "arrayop" and member in _ARRAY_OPS:
            return self.array_op(member, args, e.type_val, into, e.offset)
        call = ir.Call(callee, type_args, args, module, member, func.type_val if module is not None else None)
        return self.let(call, e.type_val, into)

    def array_op(self, member: str, args: tuple[ir.Atom, ...], t: QType, into: Optional[ir.Var],
                 offset: Optional[int]) -> ir.Atom:
        """A call of the standard library's arrayOp, as the array operation it
        is (arrays of records and variants, stored wide, could not be passed to
        the generic functions without copying). Its errors are located at the
        call (offset)."""
        match member:
            case "new":
                return self.let(ir.ArrayRep(args[0], args[1], offset), t, into)
            case "size":
                return self.let(ir.Prim("extent", (args[0],)), t, into)
            case "get":
                return self.let(ir.Index(args[0], args[1], offset), t, into)
            case "set":
                self.emit(ir.StoreElement(args[2], args[0], args[1], offset))
                return self.copy_into(self.const(None, OK_TYPE), into)
        raise LoweringError(f"arrayOp.{member}")

    def argument(self, a: TypedExpr) -> ir.Atom:
        # A var or out argument is an address: a mutable variable (TypedVar) or
        # a reference node, which value() lowers to addresses; a value argument
        # is a value
        return self.value(a)

    def tuple_index(self, tuple_type: QType, index: int, fld: Optional[str]) -> int:
        # A type parameter bounded by a tuple type is indexed as its bound
        s = resolved_shape(shape(tuple_type))
        if s.kind != "tuple":
            raise LoweringError(f"tuple component of a {s.kind}")
        if fld is not None:
            for i, c in enumerate(s.components):
                if c.name == fld:
                    return i
        if 0 <= index < len(s.components):
            return index
        raise LoweringError(f"tuple {tuple_type} has no component {fld or index}")

    def select(self, e: TypedSelect, target: TypedExpr, fld: str, into: Optional[ir.Var]) -> ir.Atom:
        if (module := self.module_ref(target)) is not None:
            return self.let(ir.ModuleMember(module, fld), e.type_val, into)
        base = self.value(target)
        s = resolved_shape(shape(target.type_val))
        if s.kind == "tuple":
            return self.let(ir.TupleField(base, self.tuple_index(target.type_val, -1, fld)), e.type_val, into)
        return self.let(ir.RecordField(base, fld), e.type_val, into)

    def tuple(self, e: TypedTuple, into: Optional[ir.Var]) -> ir.Atom:
        """Lowers a tuple expression: each component is computed, in order,
        then a make-tuple operation collects them (into, if given).

            tuple let a = 1 let b = a + 1 end    let a: Int = 1
                                                 let b: Int = prim +(a, 1)
                                                 let t: ... = tuple(a, b)

        A label (let a = ...) names its component for the components after it,
        so a labelled component is computed into a variable bound to the label.
        Components declared with let rec ... and ... are functions that see one
        another: they become one funs rec statement, whose closures are the
        components. A type component (Let T = Int) is a witness, the type it
        stands for, not a value: it computes nothing, and becomes one of the
        make-tuple's type components,

            tuple Let T = Int let x: T = 3 end  ->  tuple(Let T = Int x)

        Binding each label as soon as its value is computed is right even for
        a simultaneous group (let a = ... and b = ...), whose members do not
        see one another: a member refers to a binding that a label shadows by
        that binding's own symbol, never the label's."""
        labels =e.labels if e.labels else (None,) * len(e.elements)
        values: dict[int, ir.Atom] = {}
        type_components: list[tuple[str, QType]] = []
        rec_first = {group[0]: group for group in e.rec_groups}
        rec_members = {i for group in e.rec_groups for i in group}
        for i, (element, label) in enumerate(zip(e.elements, labels)):
            if isinstance(element, TypedTypeWitness):
                type_components.append((element.name, element.witness_type))
                continue
            if i in rec_first:
                # Recursive components: functions that see one another, through
                # their labels
                group = rec_first[i]
                functions = []
                for k in group:
                    sym = labels[k]
                    var = self.bind_symbol(sym) if sym is not None else self.fresh("f", e.elements[k].type_val)
                    values[k] = var
                    functions.append((e.elements[k], var))
                funs = []
                for fun_e, var in functions:
                    if not isinstance(fun_e, TypedFun):
                        raise LoweringError("recursive tuple components other than functions")
                    funs.append(self.function(fun_e, var))
                self.emit(ir.Funs(tuple(funs), recursive=True))
                continue
            if i in rec_members:
                continue
            if label is None:
                values[i] = self.value(element)
                continue
            # A label names its component's value for the later components. The
            # members of a simultaneous group refer to the bindings their labels
            # shadow by other symbols, so binding each label as its value is
            # computed is the same as binding them all after the group
            var = self.bind_symbol(label, element.type_val)
            values[i] = self.value(element, var)
        atoms = []
        for i, element in enumerate(e.elements):
            if isinstance(element, TypedTypeWitness):
                continue
            atoms.append(values[i])
        return self.let(ir.MakeTuple(tuple(atoms), tuple(type_components)), e.type_val, into)

    def joined(self, e: TypedExpr, into: Optional[ir.Var]) -> ir.Atom:
        """A value produced on several paths: each path jumps to a join point
        with its value."""
        result = into if into is not None else self.fresh("r", e.type_val)
        label = self.label("k")
        join = ir.Join(label, (result,), ir.Body(), ir.Body())
        self.emit(join)
        with self.in_body(join.body):
            self.branches(e, lambda branch: self.jump_with(label, branch))
        self.body = join.continuation
        return result

    def jump_with(self, label: str, branch: TypedExpr) -> None:
        atom = self.value(branch)
        if not self.body.terminated:
            self.terminate(ir.Jump(label, (atom,)))

    # Effects

    def effect(self, e: TypedExpr) -> None:
        """Lowers e for its effect alone."""
        match e:
            case TypedIf() | TypedCase() | TypedInspect() | TypedTry():
                self.branches(e, self.effect)
            case TypedBlock(bindings=bindings, result=result):
                for b in bindings:
                    self.binding(b)
                self.effect(result)
            case TypedWhile(cond=cond, body=body):
                label = self.label("L")
                loop = ir.Loop(label, ir.Body())
                self.emit(loop)
                self.loops.append(label)
                with self.in_body(loop.body):
                    c = self.value(cond)
                    then_body = ir.Body()
                    self.emit(ir.If(c, then_body, ir.Body([ir.Break(label)])))
                    with self.in_body(then_body):
                        self.effect(body)
                self.loops.pop()
            case TypedLoop(body=body):
                label = self.label("L")
                loop = ir.Loop(label, ir.Body())
                self.emit(loop)
                self.loops.append(label)
                with self.in_body(loop.body):
                    self.effect(body)
                self.loops.pop()
            case TypedFor():
                self.for_loop(e)
            case TypedExit():
                if not self.loops:
                    raise LoweringError("exit outside a loop")
                self.terminate(ir.Break(self.loops[-1]))
            case TypedAssign(target=target, value=value):
                self.assign(target, value)
            case TypedIndexAssign(target=target, index=index, value=value):
                a = self.value(target)
                i = self.value(index)
                v = self.value(value)
                self.emit(ir.StoreElement(v, a, i, e.offset))
            case TypedRaise(exc=exc, payload=payload):
                x = self.value(exc)
                p = self.value(payload) if payload is not None else None
                self.terminate(ir.Raise(x, p, e.offset))
            case TypedApp() if e.type_val is OK_TYPE:
                atom = self.call(e, None)
                # A call for its effect: its result is not used (Ok)
                last = self.body.statements[-1] if self.body.statements else None
                if isinstance(last, ir.Let) and last.var is atom and isinstance(last.value, ir.Call):
                    self.body.statements[-1] = ir.Do(last.value)
            case _:
                self.value(e)

    def assign(self, target: TypedExpr, value: TypedExpr) -> None:
        match target:
            case TypedVar() if (box := self.boxes.get(target.symbol.symbol_id)) is not None:
                self.emit(ir.StoreComponent(self.value(value), box, 0))
            case TypedVar() if (var := self.vars.get(target.symbol.symbol_id)) is not None and var.mutable:
                v = self.value(value)
                self.emit(ir.Assign(var, v))
            case TypedSelect(target=base_e, field=fld):
                base = self.value(base_e)
                v = self.value(value)
                s = resolved_shape(shape(base_e.type_val))
                if s.kind == "tuple":
                    self.emit(ir.StoreComponent(v, base, self.tuple_index(base_e.type_val, -1, fld)))
                else:
                    self.emit(ir.StoreField(v, base, fld))
            case _:
                address = self.value(target)
                v = self.value(value)
                self.emit(ir.StoreAt(v, address))

    def for_loop(self, e: TypedFor) -> None:
        start = self.value(e.start)
        stop = self.value(e.stop)
        counter = self.fresh(e.var_name, INT_TYPE, mutable=True)
        self.emit(ir.VarDecl(counter, start))
        label = self.label("L")
        loop = ir.Loop(label, ir.Body())
        self.emit(loop)
        self.loops.append(label)
        with self.in_body(loop.body):
            more = self.let(ir.Prim(">=" if e.is_downto else "<=", (counter, stop)), BOOL_TYPE)
            then_body = ir.Body()
            self.emit(ir.If(more, then_body, ir.Body([ir.Break(label)])))
            with self.in_body(then_body):
                i = self.bind_symbol(e.symbol, INT_TYPE)
                self.emit(ir.Let(i, counter))
                self.effect(e.body)
                if not self.body.terminated:
                    step = self.let(ir.Prim("-" if e.is_downto else "+", (counter, self.const(1, INT_TYPE))), INT_TYPE)
                    self.emit(ir.Assign(counter, step))
        self.loops.pop()

    def branches(self, e: TypedExpr, lower_branch) -> None:
        """Lowers the branches of an if, case, inspect, or try, each with
        lower_branch (into the branch's body)."""
        match e:
            case TypedIf(cond=cond, then_branch=then_e, else_branch=else_e):
                c = self.value(cond)
                stmt = ir.If(c, ir.Body(), ir.Body())
                self.emit(stmt)
                with self.in_body(stmt.then_body):
                    lower_branch(then_e)
                with self.in_body(stmt.else_body):
                    lower_branch(else_e)
            case TypedCase(target=target, branches=branches, else_branch=else_e):
                v = self.value(target)
                cases = []
                for br in branches:
                    binder = None
                    if br.binder is not None:
                        binder = self.bind_symbol(br.binder)
                    case = ir.Case(tuple(br.tags), ir.Body(), binder)
                    with self.in_body(case.body):
                        lower_branch(br.body)
                    cases.append(case)
                else_body = None
                if else_e is not None:
                    else_body = ir.Body()
                    with self.in_body(else_body):
                        lower_branch(else_e)
                self.emit(ir.Switch(v, tuple(cases), else_body))
            case TypedInspect(target=target, branches=branches, else_branch=else_e, auto_type=auto_type):
                v = self.value(target)
                cases = []
                for br in branches:
                    binders = tuple(self.bind_symbol(b) for b in br.binders)
                    case = ir.InspectCase(br.match_type, binders, ir.Body(), br.exact)
                    with self.in_body(case.body):
                        lower_branch(br.body)
                    cases.append(case)
                else_body = None
                if else_e is not None:
                    else_body = ir.Body()
                    with self.in_body(else_body):
                        lower_branch(else_e)
                self.emit(ir.Inspect(v, tuple(cases), else_body, auto_type, e.offset))
            case TypedTry(body=body_e, branches=branches, else_branch=else_e, else_binder=else_binder):
                exception = self.fresh("e", EXCEPTION_TYPE)
                # What the handler catches, when that is known before the try
                # (docs/exceptions.md §5.1): its patterns' values, computed
                # before the try when computing them there gives the same values
                patterns: Optional[list[ir.Atom]] = None
                catching = ir.CATCH_UNKNOWN
                if else_binder is not None:
                    catching = ir.CATCH_ALL_TRACED
                elif else_e is not None:
                    catching = ir.CATCH_ALL
                elif all(self.pure_pattern(br.exc_pattern) for br in branches):
                    patterns = [self.value(br.exc_pattern) for br in branches]
                    catching = ir.CATCH_LISTED
                stmt = ir.Try(ir.Body(), exception, ir.Body(), catching, tuple(patterns or ()))
                self.emit(stmt)
                with self.in_body(stmt.body):
                    lower_branch(body_e)
                with self.in_body(stmt.handler):
                    self.handler(exception, branches, else_e, lower_branch, patterns, else_binder)
            case _:
                raise LoweringError(f"branches of {type(e).__name__}")

    def pure_pattern(self, e: TypedExpr) -> bool:
        """Whether a try's pattern has the same value computed before the try as
        in its handler: an immutable variable already bound, or a module's
        member."""
        match e:
            case TypedVar(symbol=symbol):
                var = self.vars.get(symbol.symbol_id)
                return var is not None and not var.mutable
            case TypedSelect(target=target):
                return self.module_ref(target) is not None
        return False

    def handler(self, exception: ir.Var, branches, else_e, lower_branch,
                patterns: Optional[list[ir.Atom]] = None, else_binder: Optional[ValueSymbol] = None) -> None:
        """A try's handler: the branches' patterns (or their values, computed
        before the try) tested in order against the exception, else the else
        branch (with its binder, if it names the exception), or the exception
        raised again."""
        if not branches:
            if else_e is not None:
                if else_binder is not None:
                    self.emit(ir.Let(self.bind_symbol(else_binder), ir.CaughtException(exception)))
                lower_branch(else_e)
            else:
                self.terminate(ir.Reraise(exception))
            return
        br, rest = branches[0], branches[1:]
        pattern = patterns[0] if patterns is not None else self.value(br.exc_pattern)
        matches = self.let(ir.Prim("is", (exception, pattern)), BOOL_TYPE)
        stmt = ir.If(matches, ir.Body(), ir.Body())
        self.emit(stmt)
        with self.in_body(stmt.then_body):
            if br.binder is not None:
                self.emit(ir.Let(self.bind_symbol(br.binder), ir.ExceptionPayload(exception)))
            lower_branch(br.body)
        with self.in_body(stmt.else_body):
            self.handler(exception, rest, else_e, lower_branch, patterns[1:] if patterns is not None else None,
                         else_binder)

    # Functions

    def function(self, e: TypedFun, var: ir.Var, binder: Optional[str] = None) -> ir.Function:
        """The function e, bound to binder if it is let-bound. A function
        checked against its variable's type may annotate a value parameter with
        a supertype of the type's (contravariance): its parameter has the
        variable's type's, which callers pass, and a let at its entry binds the
        annotation's (which the represent pass converts)."""
        trace_name = frame_name(self.frame, binder)
        t = e.type_val
        type_params: tuple[ir.TypeParam, ...] = ()
        inner = t
        if isinstance(t, QAllType):
            type_params = tuple(
                ir.TypeParam(q.name, q.symbol_id, q.bound, shape(q.bound.bound) if isinstance(q.bound, QPowerKind) else None)
                for q in t.quantifiers
            )
            inner = t.body
        result_t = inner.result_type if isinstance(inner, QFunType) else inner
        expected = _expected_params(var.type, t, len(e.params))
        params = []
        entry = []
        for i, p in enumerate(e.params):
            mode = "var" if p.is_var else "out" if p.is_out else "value"
            param_t = p.type_val
            if isinstance(param_t, (QVarType, QOutType)):
                param_t = param_t.element_type
            expected_t = expected[i] if expected is not None else None
            if isinstance(expected_t, (QVarType, QOutType)):
                expected_t = expected_t.element_type
            if mode == "value" and expected_t is not None and not is_type_equal(expected_t, param_t):
                param = self.fresh(p.symbol.name, expected_t)
                entry.append(ir.Let(self.bind_symbol(p.symbol, param_t), param))
                params.append((param, mode))
                continue
            params.append((self.bind_symbol(p.symbol, param_t, mutable=mode != "value"), mode))
        body = ir.Body(entry)
        saved_loops, self.loops = self.loops, []
        saved_frame, self.frame = self.frame, trace_name
        with self.in_body(body):
            if isinstance(e.body, TypedExternal):
                result = self.external_call(e.body, t, params, result_t)
            else:
                # The body is a scope of its own: exceptions made inside it are
                # visible throughout it
                self.make_scope_exceptions(e.body)
                result = self.value(e.body)
            if not self.body.terminated:
                self.terminate(ir.Return(result))
        self.loops = saved_loops
        self.frame = saved_frame
        return ir.Function(var, type_params, tuple(params), result_t, body, trace_name=trace_name)

    def external_call(self, ext: TypedExternal, t: QType, params, result_t: QType) -> ir.Atom:
        """The body of a function defined as an external C function: a call of
        it."""
        quants = t.quantifiers if isinstance(t, QAllType) else ()
        type_args = tuple(QTypeVar(q.name, q.symbol_id, q.bound) for q in quants)
        args = []
        for var, mode in params:
            if mode == "value":
                args.append(var)
            else:
                ref_t = QVarType(element_type=var.type) if mode == "var" else QOutType(element_type=var.type)
                args.append(self.let(ir.AddrVar(var), ref_t))
        return self.let(ir.CallExternal(ext.symbol, type_args, tuple(args)), result_t)

    # Bindings

    def make_scope_exceptions(self, b: TypedNode) -> None:
        """Makes, before b, the named exceptions b makes for its scope
        (scope_exceptions), which the expressions that make them then refer
        to."""
        for exc in scope_exceptions(b):
            if exc.symbol.symbol_id in self.vars:
                continue
            var = self.bind_symbol(exc.symbol, exc.type_val)
            self.made.add(id(var))
            self.emit(ir.Let(var, ir.MakeException(exc.name, exc.payload_type)))

    def binding(self, b: TypedNode, show: bool = False) -> None:
        """Lowers one declaration of a block or a unit's top level, emitting
        its statements into the current body. With show, as for a top-level
        phrase run with --echo, it also emits what the interactive system
        prints for it.

            let x = 1;                  let x: Int = 1
            let var y = x + 1;          let %1: Int = prim +(x, 1)
                                        var y: Int = %1
            let x = x + 2;              let x.1: Int = prim +(x, 2)
            let f(n: Int): Int = n + x; funs { fun f(n: Int): Int {...} }
            Let T = Int;                (nothing)

        - A value is computed straight into the variable that binds it (value's
          into). The variable is entered in vars, where uses look it up, only
          after its value is lowered, so that the value sees the binding it
          shadows: the second x reads the first, and is printed x.1.
        - A var is a mutable variable (VarDecl), initialized from its value.
        - A function becomes a funs statement, which makes closures. Functions
          declared together with let rec ... and ... are one funs rec, whose
          functions see one another. A let rec of values that are not all
          functions (a record of functions, say) goes to rec_values.
        - A simultaneous let ... and ... (without rec) is lowered member by
          member: its members' values refer to the bindings the members
          shadow, which are other symbols, so binding each as it is computed
          means the same.
        - Type and kind declarations exist only for the type checker; they
          lower to nothing, but for their echoed text.
        - An expression statement goes to phrase_expr: lowered for its effect
          alone if its type is Ok, and otherwise for its value, which --echo
          prints. An import adds the imported modules to the unit.

        The named exceptions b makes for its scope are made before it
        (make_scope_exceptions)."""
        self.make_scope_exceptions(b)
        match b:
            case TypedLetValue(value=value, is_rec=True) if not isinstance(value, TypedFun):
                self.rec_values((b,), show)
            case TypedLetValue(name=name, value=value, symbol=symbol):
                if isinstance(value, TypedFun):
                    var = self.bind_symbol(symbol)
                    self.emit(ir.Funs((self.function(value, var, name),), recursive=b.is_rec))
                    if show:
                        self.emit(ir.EchoText(f"let {name}:{_display(symbol.type_val)} = <fun>"))
                    return
                if symbol.is_var and symbol.symbol_id in self.captured:
                    # Held in a box that closures capture (_captured_mutables)
                    init = self.value(value)
                    box_t = QTupleType((QTupleField(name=name, type_val=symbol.type_val, is_var=True),))
                    box = self.let(ir.MakeTuple((init,)), box_t, hint=name)
                    self.boxes[symbol.symbol_id] = box
                elif symbol.is_var:
                    init = self.value(value)
                    var = self.bind_symbol(symbol, mutable=True)
                    self.emit(ir.VarDecl(var, init))
                else:
                    if b.is_rec:
                        raise LoweringError("recursive values other than functions")
                    # The value is lowered before the variable is bound, so that
                    # it refers to any binding it shadows
                    var = ir.Var(symbol.name, symbol.type_val)
                    self.value(value, var)
                    if symbol.symbol_id in self.vars:
                        raise LoweringError(f"symbol '{name}' is bound twice")
                    self.vars[symbol.symbol_id] = var
                if show:
                    self.echo_binding(name, symbol, var)
            case TypedLetValueGroup(members=members, is_rec=True) if not all(
                isinstance(m.value, TypedFun) for m in members
            ):
                self.rec_values(members, show)
            case TypedLetValueGroup(members=members, is_rec=True):
                vars_ = [self.bind_symbol(m.symbol) for m in members]
                functions = tuple(self.function(m.value, v, m.name) for m, v in zip(members, vars_))
                self.emit(ir.Funs(functions, recursive=True))
                if show:
                    for m in members:
                        self.emit(ir.EchoText(f"let {m.name}:{_display(m.symbol.type_val)} = <fun>"))
            case TypedLetValueGroup(members=members):
                # Simultaneous: every member's value refers to the bindings the
                # members shadow, which their symbols keep apart, so lowering
                # them in order and binding each as it is computed is the same
                for m in members:
                    self.binding(m, show)
            case TypedExprStmt(expr=expr):
                self.phrase_expr(expr, show)
            case TypedLetType(name=name, symbol=symbol):
                if show:
                    kind_str = str(symbol.kind)
                    if symbol.definition is not None:
                        self.emit(ir.EchoText(f"Let {name}::{kind_str} = {symbol.definition}"))
                    else:
                        self.emit(ir.EchoText(f"Let {name}::{kind_str}"))
            case TypedLetTypeGroup(members=members):
                for m in members:
                    self.binding(m, show)
            case TypedDefKind(name=name, symbol=symbol):
                if show:
                    self.emit(ir.EchoText(f"DEF {name} = {symbol.kind}"))
            case TypedException():
                self.phrase_expr(b, show)
            case TypedImport(items=items):
                self.add_imports(items)
            case TypedInterface() | TypedModule():
                raise LoweringError(f"{type(b).__name__} inside a block")
            case TypedExpr():
                self.phrase_expr(b, show)
            case _:
                raise LoweringError(f"lowering binding {type(b).__name__} is not implemented")

    def rec_values(self, members, show: bool) -> None:
        """Recursive values (and functions) declared together: each member's
        value is computed into its variable in a let rec, where closures may
        refer to all of them."""
        vars_ = tuple(self.bind_symbol(m.symbol) for m in members)
        group = ir.LetRec(vars_, ir.Body())
        self.emit(group)
        with self.in_body(group.body):
            for m, var in zip(members, vars_):
                if isinstance(m.value, TypedFun):
                    self.emit(ir.Funs((self.function(m.value, var, m.name),)))
                else:
                    self.value(m.value, var)
        if show:
            for m, var in zip(members, vars_):
                if isinstance(m.value, TypedFun):
                    self.emit(ir.EchoText(f"let {m.name}:{_display(m.symbol.type_val)} = <fun>"))
                else:
                    self.echo_binding(m.name, m.symbol, var)

    def phrase_expr(self, e: TypedExpr, show: bool) -> None:
        if isinstance(e, TypedException) and e.name:
            self.value(e)
            if show:
                self.emit(ir.EchoText(f"exception {e.name}"))
            return
        if e.type_val is OK_TYPE:
            self.effect(e)
            return
        atom = self.value(e)
        if show:
            self.emit(ir.Echo(atom, e.type_val, ""))

    def echo_binding(self, name: str, symbol: ValueSymbol, var: ir.Var) -> None:
        prefix = f"let {'var ' if symbol.is_var else ''}{name}:{_display(symbol.type_val)} = "
        if symbol.type_val is OK_TYPE:
            self.emit(ir.EchoText(prefix + "ok"))
        else:
            self.emit(ir.Echo(var, symbol.type_val, prefix))

    # Units

    def make_import(self, name: str, module_path: str, canonical_path: str, interface_path: str) -> ir.Import:
        """An imported module, with the record type of the interface it is
        imported through."""
        scope = (
            self.env.lookup_module(canonical_path)
            or self.env.lookup_module(module_path)
            or self.env.lookup_module(name)
            or self.env.lookup_interface(interface_path)
        )
        record_t = build_record_type_from_scope(scope) if scope is not None else None
        return ir.Import(name, module_path, canonical_path, interface_path, record_t)

    def add_imports(self, items) -> None:
        for item in items:
            symbol_ids = item.symbol_ids if item.symbol_ids is not None else (None,) * len(item.names)
            for name, path, canonical, symbol_id in zip(
                item.names, item.effective_module_paths, item.effective_canonical_module_paths, symbol_ids
            ):
                imp = self.make_import(name, path, canonical, item.effective_interface_path)
                self.imports.append(imp)
                if symbol_id is not None:
                    self.module_refs[symbol_id] = imp

    def module(self, m: TypedModule) -> ir.Module:
        init = ir.Body()
        members: dict[str, ir.Var] = {}
        saved_frame, self.frame = self.frame, init_frame(m.name)
        with self.in_body(init):
            for b in m.bindings:
                match b:
                    case TypedImport(items=items):
                        self.add_imports(items)
                    case _:
                        self.binding(b)
                        for exc in named_exceptions_in(b):
                            if exc.symbol is not None:
                                members[exc.name] = self.vars[exc.symbol.symbol_id]
                        for member in (b.members if isinstance(b, (TypedLetValueGroup, TypedLetTypeGroup)) else (b,)):
                            if isinstance(member, TypedLetValue):
                                members[member.name] = self.vars[member.symbol.symbol_id]
        self.frame = saved_frame
        module = ir.Module(m.name, m.interface_name, init, members)
        if m.symbol_id is not None:
            self.module_refs[m.symbol_id] = module
        return module

    def program(self, prog: TypedProgram) -> ir.Unit:
        self.captured = _captured_mutables(prog)
        main = ir.Body()
        modules: list[ir.Module] = []
        phrases = prog.phrases
        with self.in_body(main):
            for i, phrase in enumerate(phrases):
                show = self.echo or (self.print_result and i == len(phrases) - 1)
                match phrase:
                    case TypedModule():
                        if not phrase.is_precompiled:
                            modules.append(self.module(phrase))
                    case TypedInterface():
                        pass
                    case _:
                        self.binding(phrase, show)
        return ir.Unit(main, modules, tuple(self.imports), source_map=self.source_map)


def _display(t: QType) -> str:
    # As the interpreter prints a phrase's type
    return str(t)


def lower_module_file(mod: TypedModule, env: Environment) -> ir.Unit:
    """Lowers a module file's typed module to a Core IR unit of the module
    alone, with its exports."""
    unit = _Lowerer(env, False, False).program(TypedProgram(phrases=(mod,)))
    module = unit.modules[0]
    exports: dict[str, ir.Var] = {}
    for name, symbol in mod.scope.values.items():
        member = module.members.get(name)
        if member is None:
            raise LoweringError(f"module {mod.name} does not define its interface's member '{name}'")
        if is_type_equal(member.type, symbol.type_val):
            exports[name] = member
        else:
            export = ir.Var(name, symbol.type_val)
            module.init.statements.append(ir.Let(export, member))
            exports[name] = export
    module.exports = exports
    _add_module_record(module)
    return unit


def _add_module_record(module: ir.Module) -> None:
    """Ends a module's initializer by making its record: of its members, or of
    its exports (docs/ir.md §3)."""
    fields = module.members if module.exports is None else module.exports
    rec_t = QRecordType(tuple(QRecordField(name=n, type_val=v.type) for n, v in fields.items()))
    module.record = ir.Var(f"{module.name}_record", rec_t)
    module.init.statements.append(
        ir.Let(module.record, ir.MakeRecord(tuple((n, v, False) for n, v in fields.items())))
    )


def lower_program(
    prog: TypedProgram,
    env: Environment,
    options: Optional[CompilerOptions] = None,
    echo: bool = False,
    print_result: bool = True,
) -> ir.Unit:
    """Lowers a typed program to a Core IR unit."""
    if options is not None:
        echo = options.echo
    unit = _Lowerer(env, echo, print_result).program(prog)
    for module in unit.modules:
        _add_module_record(module)
    return unit
