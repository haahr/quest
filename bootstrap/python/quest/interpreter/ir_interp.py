"""An interpreter for the IR (docs/ir.md §12, step 4), a test oracle for the
lowering and the passes.

The test runner runs every golden test program's IR through it and compares the
output with the source interpreter's (tests/golden/run), so that a lowering or a
pass that changes a program's meaning fails at that stage, before any C is
printed. Values are the tree-walking interpreter's (quest/values/model.py), and
the modules a unit imports, the standard library included, are loaded and run by
the source interpreter; functions of either kind may call the other's.

Variables are looked up by identity in frames: a frame per function activation,
its parent the frame its closure was made in, and a frame per loop iteration, so
that a closure made in one iteration keeps that iteration's values. A mutable
variable holds a cell (QRef), which `addr x` yields and a var or out parameter
receives. Statements return None when they fall through, or the terminator's
signal (return, jump, break, continue); a raise is a Python exception
(QuestException), as in the source interpreter.

From the described stage on, operations carry descriptor operands
(ir/describe.py), which a run evaluates to the types they describe and checks
against the types they stand for (type arguments, auto values' witnesses, and
inspect cases' types), so that a descriptor made wrong fails here too: a
descriptor variable is its type parameter's type argument, a static descriptor
its type, and an instantiated template its type with the holes replaced by the
arguments'.
"""

from __future__ import annotations

import sys
from typing import Any, Optional

from quest.diagnostics import MAIN_FRAME, QuestCompilerError, init_frame
from quest.interpreter.formatting import exposed_type, format_value_with_type
from quest.interpreter.primitives import (
    ARRAY_OP_ERROR_EXC,
    MAX_CALL_DEPTH,
    QuestRuntimeError,
    STACK_OVERFLOW_EXC,
    VARIANT_ERROR_EXC,
    int_arithmetic,
    int_relational,
    real_arithmetic,
    real_relational,
)
from quest.interpreter.treewalk import RuntimeEnvironment, load_module_for_interpreter, note_frames, run_closure
from quest.values.model import (
    DYNAMIC_ERROR_EXC,
    QuestException,
    FALSE_VALUE,
    OK_VALUE,
    TRUE_VALUE,
    QArray,
    QArrayElementRef,
    QAutoVal,
    QBool,
    QBuiltinFun,
    QChar,
    QClosure,
    QExceptionVal,
    QInt,
    QOk,
    QOption,
    QReal,
    QRecord,
    QRef,
    QString,
    QTuple,
    QTupleElementRef,
    QTypeValue,
    QValue,
    QVariant,
    qvalue_is,
)
from quest.ir import nodes as ir
from quest.types import (
    QAllType,
    QFunType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QType,
    is_subtype,
    is_type_equal,
)
from quest.codegen.descriptors import hole_var
from quest.interpreter.builtins import resolve_external_symbol

_INT_ARITHMETIC = ("+", "-", "*", "/", "mod", "%")
_INT_RELATIONAL = ("<", "<=", ">", ">=")
_REAL_ARITHMETIC = ("++", "--", "**", "//", "^^")
_REAL_RELATIONAL = ("<<", "<<=", ">>", ">>=")

# The value of a let rec's variable before its value is computed
_UNBOUND = object()


class IRInterpreterError(Exception):
    """IR the interpreter cannot run (a malformed unit, not an error in the
    program)."""


class _Frame:
    __slots__ = ("parent", "values", "types", "top")

    def __init__(self, parent: Optional[_Frame], types: Optional[dict[int, QType]] = None) -> None:
        self.parent = parent
        self.values: dict[int, Any] = {}
        # The type arguments of the type parameters (by symbol id) of the
        # functions being run
        self.types: dict[int, QType] = types if types is not None else {}
        # The frame of the top level (the main body, or a module's initializer)
        # this frame runs in: the parent of lifted functions' frames, which see
        # only its globals
        self.top: _Frame = parent.top if parent is not None else self

    def peek(self, var: ir.Var) -> Any:
        """The value a variable holds, _UNBOUND if it is declared and not yet
        bound."""
        key = id(var)
        frame: Optional[_Frame] = self
        while frame is not None:
            if key in frame.values:
                return frame.values[key]
            frame = frame.parent
        raise IRInterpreterError(f"variable '{var.hint}' is not bound")

    def lookup(self, var: ir.Var) -> Any:
        key = id(var)
        frame: Optional[_Frame] = self
        while frame is not None:
            if key in frame.values:
                value = frame.values[key]
                if value is _UNBOUND:
                    raise QuestRuntimeError(f"Undefined runtime symbol '{var.hint}'")
                return value
            frame = frame.parent
        raise IRInterpreterError(f"variable '{var.hint}' is not bound")

    def bind_declared(self, var: ir.Var, value: QValue) -> None:
        """Binds a declared variable in the frame that declared it."""
        key = id(var)
        frame: Optional[_Frame] = self
        while frame is not None:
            if frame.values.get(key, None) is _UNBOUND:
                frame.values[key] = value
                return
            frame = frame.parent
        raise IRInterpreterError(f"declared variable '{var.hint}' is bound outside its scope")

    def lookup_type(self, symbol_id: int) -> Optional[QType]:
        frame: Optional[_Frame] = self
        while frame is not None:
            if symbol_id in frame.types:
                return frame.types[symbol_id]
            frame = frame.parent
        return None

    def resolve(self, t: QType) -> QType:
        """t with the type arguments of the type parameters it mentions
        substituted."""
        subst = {}
        for symbol_id in t._fv:
            bound = self.lookup_type(symbol_id)
            if bound is not None:
                subst[symbol_id] = bound
        return t.substitute(subst) if subst else t


class _Raised(QValue):
    """A handler's exception variable: the exception raised, with its payload,
    which `exception_payload` reads and a raise of the variable raises again."""

    def __init__(self, raised: QuestException) -> None:
        self.raised = raised

    @property
    def type_name(self) -> str:
        return "Exception"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        return self.raised.exc_val.to_str(visited)


class _Closure(QBuiltinFun):
    """An IR function value: its function, the frame it was made in, and the
    types bound to its type parameters. It is a built-in function to the source
    interpreter, so that library functions written in Quest can call it."""

    def __init__(self, interp: Interpreter, function: ir.Function, frame: _Frame,
                 type_bindings: Optional[dict[int, QType]] = None, env: Optional[list[QValue]] = None) -> None:
        super().__init__(function.var.hint, lambda *args: interp.apply(self, list(args)))
        self.function = function
        self.frame = frame
        self.type_bindings: dict[int, QType] = dict(type_bindings or {})
        # After closure conversion, the values the closure captured
        self.env = env

    def instantiate(self, interp: Interpreter, type_args: tuple[QType, ...]) -> _Closure:
        unbound = [tp.symbol_id for tp in self.function.type_params if tp.symbol_id not in self.type_bindings]
        bindings = dict(self.type_bindings)
        bindings.update(zip(unbound, type_args))
        return _Closure(interp, self.function, self.frame, bindings, self.env)

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        return f"<fun:{self.function.var.hint}>"


class Interpreter:
    """Runs one IR unit, at any stage, sharing the source interpreter's runtime
    environment (renv): its values, its call stack, and the modules it has
    loaded.

    run runs the unit's imports (by the source interpreter), then each of its
    modules' initializers, in a frame of its own whose variables become the
    module's members, and then its main body.

    Control flow inside a function is by signals, not Python exceptions: a
    statement returns None to fall through, or the terminator it reached as a
    tuple, ("return", value), ("jump", label, values), ("break", label), or
    ("continue", label), which each enclosing statement passes up until one
    that handles it. The abs function in _Lowerer's docstring (ir/lower.py),

        join k1(r: Int) { return r }
        in { ... if %1 { ... jump k1(%2) } else { jump k1(n) } }

    runs the join's body (after in), whose jump signal reaches the join; the
    join binds r and runs its continuation, whose return signal ends the call.
    A raise is a Python exception (QuestException), which a try catches.

    After closure conversion (the pass that makes each local function code of
    its own, with the values it uses from around it passed in as captures), a
    closure is made by MakeClosure, which copies the values it captures. A let
    rec's closures may capture variables it has yet to bind, so make_closure
    records each such capture in fixups, and the let rec fills them in once its
    body has bound the variables."""

    def __init__(self, runtime_env: RuntimeEnvironment) -> None:
        self.renv = runtime_env
        self.root = RuntimeEnvironment.create_root_env()
        # The unit's modules and those it imports (by identity), as records of
        # their members
        self.modules: dict[int, QValue] = {}
        self.declared: set[int] = set()
        # For each let rec being run, the captures of closures made in it of
        # variables it has yet to bind: (the closure's captured values, the
        # index, the variable, the let rec's frame)
        self.fixups: list[list[tuple[list[QValue], int, ir.Var, _Frame]]] = []
        # The source map of the unit's file, where its nodes' offsets are
        self.source_map: Optional[Any] = None
        # The symbols of the type parameters the unit's functions' descriptor
        # variables describe (by variable)
        self.descriptor_symbols: dict[int, int] = {}

    # Units

    def run(self, unit: ir.Unit) -> None:
        self.source_map = unit.source_map
        self.descriptor_symbols = {id(p.var): p.symbols[0] for f in unit.functions for p in f.descriptor_params}
        # Everything runs in the program's frame, imported modules' initializers
        # included, as the source interpreter runs them when the program's
        # import runs (docs/exceptions.md §4)
        stack = self.renv.call_stack
        stack.append(MAIN_FRAME)
        try:
            for imp in unit.imports:
                self.import_module(imp)
            for m in unit.modules:
                frame = _Frame(None)
                self.run_top_level(m.init, frame, init_frame(m.name))
                self.modules[id(m)] = QRecord({name: frame.lookup(var) for name, var in m.members.items()})
            self.run_top_level(unit.main, _Frame(None))
        except QuestCompilerError as error:
            note_frames(error, self.renv)
            raise
        finally:
            stack.pop()

    def in_frame(self, name: str, body: ir.Body, frame: _Frame) -> Optional[tuple]:
        """Runs body in the frame name, which errors raised inside record
        (docs/exceptions.md §4)."""
        stack = self.renv.call_stack
        stack.append(name)
        try:
            return self.body(body, frame)
        except QuestCompilerError as error:
            note_frames(error, self.renv)
            raise
        finally:
            stack.pop()

    def run_top_level(self, body: ir.Body, frame: _Frame, frame_name: Optional[str] = None) -> None:
        signal = self.body(body, frame) if frame_name is None else self.in_frame(frame_name, body, frame)
        if signal is not None:
            raise IRInterpreterError(f"a top level ends with {signal[0]}")

    def import_module(self, imp: ir.Import) -> None:
        # Run once per program, and kept in its unit (as the source
        # interpreter's imports are)
        value = load_module_for_interpreter(imp.module_path, imp.interface_path, self.renv, imp.canonical_path)
        if value is None:
            raise IRInterpreterError(f"module '{imp.module_path}' could not be loaded")
        self.modules[id(imp)] = value

    def module(self, ref: ir.ModuleRef) -> QValue:
        return self.modules[id(ref)]

    def member(self, module: ir.ModuleRef, member: str) -> QValue:
        record = self.module(module)
        if not isinstance(record, QRecord):
            raise IRInterpreterError(f"module '{module.name}' is a {record.type_name}")
        value = record.get(member)
        return value.deref() if isinstance(value, QRef) else value

    # Atoms

    def atom(self, a: ir.Atom, frame: _Frame) -> QValue:
        if isinstance(a, ir.Var):
            value = frame.lookup(a)
            # A mutable variable holds a cell; a use reads it
            return value.deref() if a.mutable else value
        v = a.value
        if v is None:
            return OK_VALUE
        if isinstance(v, bool):
            return TRUE_VALUE if v else FALSE_VALUE
        match a.shape.kind:
            case "int":
                return QInt(v)
            case "real":
                return QReal(v)
            case "char":
                return QChar(v)
            case "string":
                # A new string each time, as each evaluation of a string literal
                # is (is compares strings by identity)
                return QString(v)
        raise IRInterpreterError(f"constant {v!r} of shape {a.shape.kind}")

    def atoms(self, atoms: tuple[ir.Atom, ...], frame: _Frame) -> list[QValue]:
        return [self.atom(a, frame) for a in atoms]

    # Calls

    def apply(self, callee: QValue, args: list[QValue]) -> QValue:
        match callee:
            case _Closure(function=f):
                # IR calls have no offsets, so stack.overflow is not located
                if len(self.renv.call_stack) >= MAX_CALL_DEPTH:
                    raise QuestException(STACK_OVERFLOW_EXC)
                frame = _Frame(callee.frame, dict(callee.type_bindings))
                if f.env is not None:
                    frame.values[id(f.env)] = callee.env
                for (param, _mode), arg in zip(f.params, args):
                    frame.values[id(param)] = arg
                if f.trace_name is None:
                    signal = self.body(f.body, frame)
                else:
                    signal = self.in_frame(f.trace_name, f.body, frame)
                if signal is None or signal[0] != "return":
                    raise IRInterpreterError(f"function '{f.var.hint}' ends without returning")
                return signal[1]
            case QBuiltinFun(fn=fn):
                return fn(*args)
            case QClosure():
                return run_closure(callee, args)
        raise QuestRuntimeError(f"Cannot call non-function of type {callee.type_name}")

    def type_apply(self, callee: QValue, type_args: tuple[QType, ...]) -> QValue:
        """A polymorphic value applied to types: its instance (the value, for a
        polymorphic function with no value parameters, as the source interpreter
        computes it)."""
        match callee:
            case _Closure(function=f):
                inst = callee.instantiate(self, type_args)
                if not f.params and len(inst.type_bindings) >= len(f.type_params) and not _is_function_type(f):
                    return self.apply(inst, [])
                return inst
            case QClosure():
                inst = callee.instantiate(type_args) if callee.type_param_ids else callee
                if inst.type_only:
                    return run_closure(inst, [])
                return inst
        return callee

    def callee(self, var: Optional[ir.Var], module: Optional[ir.ModuleRef], member: Optional[str],
               frame: _Frame) -> QValue:
        return self.atom(var, frame) if var is not None else self.member(module, member)

    # Operations

    def located(self, error: QuestCompilerError, offset: Optional[int]) -> QuestCompilerError:
        """error, raised by an operation at offset in the unit, located there
        unless it already is (an exception a library function raised is located
        in its own unit, or nowhere)."""
        if error.offset is None and error.source_map is None and offset is not None:
            error.offset, error.source_map = offset, self.source_map
        return error

    def raising(self, exc: QExceptionVal, offset: Optional[int]) -> QuestException:
        """The exception exc, raised at offset in the unit."""
        return self.located(QuestException(exc), offset)

    def operation(self, o, frame: _Frame, result: ir.Var) -> QValue:
        match o:
            case ir.Var() | ir.Const():
                return self.atom(o, frame)
            case ir.Prim(op=op, args=args, offset=offset):
                try:
                    return self.prim(op, self.atoms(args, frame))
                except QuestCompilerError as error:
                    raise self.located(error, offset)
            case ir.Call(callee=callee, type_args=type_args, args=args, module=module, member=member):
                self.check_descriptors(o.descriptors, type_args, frame)
                f = self.callee(callee, module, member, frame)
                if type_args:
                    f = self.type_apply(f, tuple(frame.resolve(t) for t in type_args))
                return self.apply(f, self.atoms(args, frame))
            case ir.TypeApp(callee=callee, type_args=type_args, module=module, member=member):
                self.check_descriptors(o.descriptors, type_args, frame)
                f = self.callee(callee, module, member, frame)
                return self.type_apply(f, tuple(frame.resolve(t) for t in type_args))
            case ir.ModuleMember(module=module, member=None):
                return self.module(module)
            case ir.ModuleMember(module=module, member=member):
                return self.member(module, member)
            case ir.Builtin(name=name):
                return self.root.lookup(name)
            case ir.MakeClosure(code=code, captures=captures, type_args=type_args):
                self.check_descriptors(o.descriptors, type_args, frame)
                return self.make_closure(code, captures, type_args, frame)
            case ir.EnvField(env=env, index=index):
                return self.atom(env, frame)[index]
            case ir.Convert(value=v):
                # A change of representation, which values here do not have
                return self.atom(v, frame)
            case ir.External(symbol=symbol):
                return resolve_external_symbol(symbol)
            case ir.CallExternal(symbol=symbol, args=args):
                ext = resolve_external_symbol(symbol)
                values = self.atoms(args, frame)
                return ext.fn(*values) if isinstance(ext, QBuiltinFun) else ext
            case ir.MakeTuple(args=args, type_components=type_components):
                return self.make_tuple(self.atoms(args, frame), type_components, result, frame)
            case ir.TupleField(tuple=t, index=index):
                tup = _deref(self.atom(t, frame))
                return tup.elements[_element_index(tup, index)]
            case ir.MakeRecord(fields=fields):
                return QRecord({
                    name: QRef(self.atom(a, frame)) if is_var else self.atom(a, frame) for name, a, is_var in fields
                })
            case ir.RecordField(record=r, name=name):
                rec = _deref(self.atom(r, frame))
                if isinstance(rec, QTuple):
                    return rec.get_by_name(name)
                return _deref(rec.get(name))
            case ir.MakeVariant(tag=tag, payload=payload):
                return QVariant(tag=tag, payload=self.atom(payload, frame) if payload is not None else None)
            case ir.MakeOption(tag=tag, payload=payload, ordinal=ordinal, offset=offset, cases=cases):
                try:
                    return self.make_option(tag, payload, ordinal, cases, frame)
                except QuestCompilerError as error:
                    raise self.located(error, offset)
            case ir.IsTag(value=v, tag=tag):
                return QBool(self.atom(v, frame).tag == tag)
            case ir.Payload(value=v, tag=tag, offset=offset, ordinal=ordinal):
                try:
                    return _payload(self.atom(v, frame), tag, ordinal)
                except QuestCompilerError as error:
                    raise self.located(error, offset)
            case ir.Ordinal(value=v, cases=cases):
                o_val = self.atom(v, frame)
                if not isinstance(o_val, QOption):
                    raise QuestRuntimeError(f"ordinal expects Option, got {o_val.type_name}")
                return QInt(cases.index(o_val.tag))
            case ir.MakeArray(args=args):
                return QArray(elements=self.atoms(args, frame))
            case ir.ArrayRep(count=count, init=init, offset=offset):
                n = self.atom(count, frame).value
                if n < 0:
                    raise self.raising(ARRAY_OP_ERROR_EXC, offset)
                v = self.atom(init, frame)
                return QArray(elements=[v for _ in range(n)])
            case ir.Index(array=a, index=i, offset=offset):
                arr = self.atom(a, frame)
                idx = self.atom(i, frame).value
                if idx < 0 or idx >= arr.size():
                    raise self.raising(ARRAY_OP_ERROR_EXC, offset)
                return arr.get(idx)
            case ir.MakeAuto(witness=witness, payload=p):
                if o.descriptor is not None:
                    self.check_descriptors((o.descriptor,), (witness,), frame)
                return QAutoVal(self.atom(p, frame), frame.resolve(witness))
            case ir.MakeException(name=name):
                return QExceptionVal(name=name)
            case ir.ExceptionPayload(exception=e):
                raised = self.atom(e, frame)
                if not isinstance(raised, _Raised):
                    raise IRInterpreterError("exception_payload of a value other than a handler's exception")
                payload = raised.raised.payload
                return payload if payload is not None else OK_VALUE
            case ir.AddrVar() | ir.AddrCell() | ir.AddrField() | ir.AddrComponent() | ir.AddrElement():
                return self.address(o, frame)
            case ir.Load(address=a):
                return _deref(self.atom(a, frame))
        raise IRInterpreterError(f"not an operation: {type(o).__name__}")

    def prim(self, op: str, args: list[QValue]) -> QValue:
        if op in ("is", "isnot"):
            a, b = (x.raised.exc_val if isinstance(x, _Raised) else x for x in args)
            return TRUE_VALUE if qvalue_is(a, b) == (op == "is") else FALSE_VALUE
        if op == "not":
            return FALSE_VALUE if args[0].value else TRUE_VALUE
        if op == "extent":
            return QInt(len(args[0].elements))
        a, b = args
        if op in _INT_ARITHMETIC:
            return QInt(int_arithmetic(op, a.value, b.value))
        if op in _INT_RELATIONAL:
            return TRUE_VALUE if int_relational(op, a.value, b.value) else FALSE_VALUE
        if op in _REAL_ARITHMETIC:
            return QReal(real_arithmetic(op, a.value, b.value))
        if op in _REAL_RELATIONAL:
            return TRUE_VALUE if real_relational(op, a.value, b.value) else FALSE_VALUE
        if op == "<>":
            return QString(a.value + b.value)
        if op == "/\\":
            return TRUE_VALUE if (a.value and b.value) else FALSE_VALUE
        if op == "\\/":
            return TRUE_VALUE if (a.value or b.value) else FALSE_VALUE
        raise IRInterpreterError(f"primitive '{op}'")

    def described(self, d: ir.Descriptor, frame: _Frame) -> QType:
        """The type a descriptor operand describes in the frame."""
        if isinstance(d, ir.Var):
            t = frame.lookup_type(self.descriptor_symbols.get(id(d), -1))
            if t is None:
                raise IRInterpreterError(f"descriptor variable '{d.hint}' describes no type here")
            return t
        if isinstance(d, ir.StaticDescriptor):
            return frame.resolve(d.type)

        args = {hole_var(i, None).symbol_id: self.described(a, frame) for i, a in enumerate(d.args)}
        return frame.resolve(d.template).substitute(args)

    def check_descriptors(self, descriptors, types, frame: _Frame) -> None:
        """Checks that descriptor operands describe the types they stand for
        (after the describe pass)."""
        for d, t in zip(descriptors, types):
            if not is_type_equal(self.described(d, frame), frame.resolve(t)):
                raise IRInterpreterError(f"a descriptor of {self.described(d, frame)} stands for {frame.resolve(t)}")

    def make_closure(self, code: ir.Function, captures, type_args, frame: _Frame) -> _Closure:
        """A closure of a lifted function, whose frames see only the globals of
        the top level that makes it."""
        values: list[QValue] = []
        for i, a in enumerate(captures):
            if isinstance(a, ir.Var) and frame.peek(a) is _UNBOUND and self.fixups:
                # A variable of an enclosing let rec, bound once its body has
                # run
                self.fixups[-1].append((values, i, a, frame))
                values.append(_UNBOUND)
            else:
                values.append(self.atom(a, frame))
        bindings = {tp.symbol_id: frame.resolve(t) for tp, t in zip(code.type_params, type_args)}
        return _Closure(self, code, frame.top, bindings, values)

    def make_tuple(self, values: list[QValue], type_components, result: ir.Var, frame: _Frame) -> QTuple:
        """A tuple laid out as the source interpreter lays it out: its type
        components are elements too (type values), which printing a tuple
        expects."""
        t = exposed_type(result.type)
        if not isinstance(t, QTupleType) or not type_components:
            labels = tuple(f.name for f in t.fields) if isinstance(t, QTupleType) else None
            if labels is not None and len(labels) != len(values):
                labels = None
            return QTuple(elements=tuple(values), labels=labels)
        witnesses = iter(type_components)
        values_iter = iter(values)
        elements: list[QValue] = []
        for comp in t.fields:
            if isinstance(comp, (QTupleTypeFormal, QTupleTypeBinding)):
                name, witness = next(witnesses)
                elements.append(QTypeValue(type_val=frame.resolve(witness), bound=comp.bound, name=name))
            else:
                elements.append(next(values_iter))
        return QTuple(elements=tuple(elements), labels=tuple(f.name for f in t.fields))

    def make_option(self, tag: Optional[str], payload, ordinal, cases: tuple[str, ...], frame: _Frame) -> QOption:
        p = self.atom(payload, frame) if payload is not None else None
        if ordinal is not None:
            n = self.atom(ordinal, frame).value
            if n < 0 or n >= len(cases):
                raise QuestRuntimeError(f"Option ordinal {n} out of bounds (0 <= ordinal < {len(cases)})")
            return QOption(tag=cases[n], payload=p)
        return QOption(tag=tag, payload=p)

    def address(self, o, frame: _Frame) -> QValue:
        match o:
            case ir.AddrVar(var=var):
                return frame.lookup(var)
            case ir.AddrCell(init=init):
                return QRef(self.atom(init, frame))
            case ir.AddrField(base=b, name=name):
                cell = _deref(self.atom(b, frame)).get(name)
                if not isinstance(cell, QRef):
                    raise QuestRuntimeError(f"Field '{name}' is not mutable")
                return cell
            case ir.AddrComponent(base=b, index=index):
                base = _deref(self.atom(b, frame))
                i = _element_index(base, index)
                element = base.elements[i]
                return element if isinstance(element, QRef) else QTupleElementRef(base, i)
            case ir.AddrElement(base=b, index=index, offset=offset):
                base = _deref(self.atom(b, frame))
                idx = self.atom(index, frame).value
                if idx < 0 or idx >= base.size():
                    raise self.raising(ARRAY_OP_ERROR_EXC, offset)
                return QArrayElementRef(base, idx)
        raise IRInterpreterError(f"not an address: {type(o).__name__}")

    def store(self, s, frame: _Frame) -> None:
        value = self.atom(s.value, frame)
        match s:
            case ir.StoreAt(address=address):
                self.atom(address, frame).assign(value)
            case ir.StoreField(base=b, name=name):
                base = _deref(self.atom(b, frame))
                cell = base.fields.get(name)
                if isinstance(cell, QRef):
                    cell.assign(value)
                else:
                    base.fields[name] = value
            case ir.StoreComponent(base=b, index=index):
                base = _deref(self.atom(b, frame))
                i = _element_index(base, index)
                if isinstance(base.elements[i], QRef):
                    base.elements[i].assign(value)
                else:
                    base.set_by_index(i, value)
            case ir.StoreElement(base=b, index=index, offset=offset):
                base = _deref(self.atom(b, frame))
                idx = self.atom(index, frame).value
                if idx < 0 or idx >= base.size():
                    raise self.raising(ARRAY_OP_ERROR_EXC, offset)
                base.set(idx, value)

    # Statements

    def body(self, body: ir.Body, frame: _Frame) -> Optional[tuple]:
        for s in body.statements:
            signal = self.statement(s, frame)
            if signal is not None:
                return signal
        return None

    def statement(self, s, frame: _Frame) -> Optional[tuple]:
        match s:
            case ir.Let(var=var, value=value):
                v = self.operation(value, frame, var)
                if id(var) in self.declared:
                    frame.bind_declared(var, v)
                else:
                    frame.values[id(var)] = v
            case ir.VarDecl(var=var, init=init):
                frame.values[id(var)] = QRef(self.atom(init, frame) if init is not None else OK_VALUE)
            case ir.Assign(var=var, value=value):
                frame.lookup(var).assign(self.atom(value, frame))
            case ir.StoreAt() | ir.StoreField() | ir.StoreComponent() | ir.StoreElement():
                self.store(s, frame)
            case ir.Do(value=value):
                self.operation(value, frame, None)
            case ir.Funs(functions=functions):
                for f in functions:
                    frame.values[id(f.var)] = _Closure(self, f, frame)
            case ir.LetRec(vars=vars_, body=body):
                for v in vars_:
                    self.declared.add(id(v))
                    frame.values[id(v)] = _UNBOUND
                self.fixups.append([])
                try:
                    signal = self.body(body, frame)
                finally:
                    fixups = self.fixups.pop()
                for values, i, var, var_frame in fixups:
                    if var_frame.peek(var) is _UNBOUND and self.fixups:
                        # A variable of an enclosing let rec
                        self.fixups[-1].append((values, i, var, var_frame))
                    else:
                        values[i] = var_frame.lookup(var)
                return signal
            case ir.If(cond=cond, then_body=then_body, else_body=else_body):
                return self.body(then_body if self.atom(cond, frame).value else else_body, frame)
            case ir.Switch(value=value, cases=cases, else_body=else_body):
                v = self.atom(value, frame)
                for c in cases:
                    if v.tag in c.tags:
                        if c.binder is not None:
                            frame.values[id(c.binder)] = v.payload if v.payload is not None else OK_VALUE
                        return self.body(c.body, frame)
                if else_body is not None:
                    return self.body(else_body, frame)
                raise QuestRuntimeError(f"Unhandled case tag '{v.tag}'")
            case ir.Inspect(value=value, cases=cases, else_body=else_body):
                v = self.atom(value, frame)
                if not isinstance(v, QAutoVal):
                    raise QuestRuntimeError(f"Inspect target must be an auto value, got {v.type_name}")
                for c in cases:
                    if c.descriptor is not None:
                        self.check_descriptors((c.descriptor,), (c.match_type,), frame)
                    match_type = frame.resolve(c.match_type)
                    if is_type_equal(v.type_val, match_type) if c.exact else is_subtype(v.type_val, match_type):
                        for b in c.binders:
                            frame.values[id(b)] = v.value
                        return self.body(c.body, frame)
                if else_body is not None:
                    return self.body(else_body, frame)
                raise self.raising(DYNAMIC_ERROR_EXC, s.offset)
            case ir.Loop(label=label, body=body):
                while True:
                    signal = self.body(body, _Frame(frame))
                    if signal is None or signal == ("continue", label):
                        continue
                    if signal == ("break", label):
                        return None
                    return signal
            case ir.Try(body=body, exception=exception, handler=handler):
                try:
                    return self.body(body, frame)
                except QuestException as raised:
                    frame.values[id(exception)] = _Raised(raised)
                    return self.body(handler, frame)
            case ir.Join(label=label, params=params, continuation=continuation, body=body):
                signal = self.body(body, frame)
                if signal is None or signal[0] != "jump" or signal[1] != label:
                    return signal
                for p, v in zip(params, signal[2]):
                    frame.values[id(p)] = v
                return self.body(continuation, frame)
            case ir.Echo(value=value, type=t, prefix=prefix):
                v = self.atom(value, frame)
                if prefix:
                    sys.stdout.write(f"{prefix}{format_value_with_type(v, t)}\n")
                elif not isinstance(v, QOk):
                    sys.stdout.write(f"{format_value_with_type(v, t)} : {t}\n")
            case ir.EchoText(text=text):
                sys.stdout.write(text + "\n")
            case ir.Return(value=value):
                return ("return", self.atom(value, frame))
            case ir.Jump(label=label, args=args):
                return ("jump", label, self.atoms(args, frame))
            case ir.Break(label=label):
                return ("break", label)
            case ir.Continue(label=label):
                return ("continue", label)
            case ir.Raise(exception=e, payload=p, offset=offset):
                exc = self.atom(e, frame)
                payload = self.atom(p, frame) if p is not None else None
                payload_type = p.type if isinstance(p, ir.Var) else None
                raise self.located(QuestException(exc_val=exc, payload=payload, payload_type=payload_type), offset)
            case ir.Reraise(exception=e):
                raise self.atom(e, frame).raised
            case ir.Unreachable():
                raise IRInterpreterError("reached unreachable code")
            case _:
                raise IRInterpreterError(f"not a statement: {type(s).__name__}")
        return None


def _deref(v: QValue) -> QValue:
    while isinstance(v, QRef):
        v = v.deref()
    return v


def _element_index(tup: QTuple, index: int) -> int:
    """The element of a tuple holding its index'th value component (its type
    components are elements too)."""
    n = -1
    for i, element in enumerate(tup.elements):
        if not isinstance(element, QTypeValue):
            n += 1
            if n == index:
                return i
    raise IRInterpreterError(f"tuple has no value component {index}")


def _payload(v: QValue, tag: str, ordinal_index: Optional[int]) -> QValue:
    """A variant's payload, or an option's components (its ordinal in its static
    type first) as a tuple, as the source interpreter's `v!tag` computes
    them."""
    if v.tag != tag:
        raise QuestException(VARIANT_ERROR_EXC)
    if isinstance(v, QOption):
        if ordinal_index is None:
            raise IRInterpreterError(f"the payload of option case {tag} without its ordinal")
        ordinal = QInt(ordinal_index)
        if v.payload is None:
            return QTuple(elements=(ordinal,), labels=(None,))
        if isinstance(v.payload, QTuple):
            # A new tuple: its var components are copies of the payload's
            # (which a case's binder shares)
            elements = (QRef(e.deref()) if isinstance(e, QRef) else e for e in v.payload.elements)
            return QTuple(elements=(ordinal, *elements), labels=(None, *v.payload.labels))
        return QTuple(elements=(ordinal, v.payload), labels=(None, None))
    return v.payload if v.payload is not None else QOk()


def _is_function_type(f: ir.Function) -> bool:
    """Whether a polymorphic function, applied to all its types, is a function
    (rather than a value computed when it is instantiated)."""
    t = exposed_type(f.var.type)
    while isinstance(t, QAllType):
        t = exposed_type(t.body)
    return isinstance(t, QFunType)


def run_unit(unit: ir.Unit, runtime_env: RuntimeEnvironment) -> None:
    """Runs a unit: its imports, its modules' initializers, then its main
    body."""
    Interpreter(runtime_env).run(unit)
