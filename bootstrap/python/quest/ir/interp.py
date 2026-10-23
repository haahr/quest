"""An interpreter for the IR (docs/ir.md §12, step 4), a test oracle for the lowering and the passes.

The test runner runs every golden test program's IR through it and compares the output with the source interpreter's
(tests/golden/run), so that a lowering or a pass that changes a program's meaning fails at that stage, before any C is
printed. Values are the source interpreter's (quest/runtime.py), and the modules a unit imports, the standard library
included, are loaded and run by the source interpreter; functions of either kind may call the other's.

Variables are looked up by identity in frames: a frame per function activation, its parent the frame its closure was
made in, and a frame per loop iteration, so that a closure made in one iteration keeps that iteration's values. A
mutable variable holds a cell (QRef), which `addr x` yields and a var or out parameter receives. Statements return
None when they fall through, or the terminator's signal (return, jump, break, continue); a raise is a Python
exception (QuestException), as in the source interpreter.
"""

from __future__ import annotations

import sys
from typing import Any, Optional

from quest.interpreter import (
    ARRAY_OP_ERROR_EXC,
    DYNAMIC_ERROR_EXC,
    VARIANT_ERROR_EXC,
    QuestException,
    QuestRuntimeError,
    RuntimeEnvironment,
    _eval_int_arithmetic,
    _eval_int_relational,
    _eval_real_arithmetic,
    _eval_real_relational,
    _exposed_type,
    format_value_with_type,
)
from quest.ir import nodes as ir
from quest.runtime import (
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
    QList,
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
from quest.types import (
    QAllType,
    QFunType,
    QOptionType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QType,
    is_subtype,
    is_type_equal,
)

_INT_ARITHMETIC = ("+", "-", "*", "/", "mod", "%")
_INT_RELATIONAL = ("<", "<=", ">", ">=")
_REAL_ARITHMETIC = ("++", "--", "**", "//", "^^")
_REAL_RELATIONAL = ("<<", "<<=", ">>", ">>=")

# The value of a declared variable before its let has run
_UNBOUND = object()


class IRInterpreterError(Exception):
    """IR the interpreter cannot run (a malformed unit, not an error in the program)."""


class _Frame:
    __slots__ = ("parent", "values", "types", "top")

    def __init__(self, parent: Optional[_Frame], types: Optional[dict[int, QType]] = None) -> None:
        self.parent = parent
        self.values: dict[int, Any] = {}
        # The type arguments of the type parameters (by symbol id) of the functions being run
        self.types: dict[int, QType] = types if types is not None else {}
        # The frame of the top level (the main body, or a module's initializer) this frame runs in: the parent of
        # lifted functions' frames, which see only its globals
        self.top: _Frame = parent.top if parent is not None else self

    def peek(self, var: ir.Var) -> Any:
        """The value a variable holds, _UNBOUND if it is declared and not yet bound."""
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
        """t with the type arguments of the type parameters it mentions substituted."""
        subst = {}
        for symbol_id in t._fv:
            bound = self.lookup_type(symbol_id)
            if bound is not None:
                subst[symbol_id] = bound
        return t.substitute(subst) if subst else t


class _Raised(QValue):
    """A handler's exception variable: the exception raised, with its payload, which `exception_payload` reads and
    a raise of the variable raises again."""

    def __init__(self, raised: QuestException) -> None:
        self.raised = raised

    @property
    def type_name(self) -> str:
        return "Exception"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        return self.raised.exc_val.to_str(visited)


class _Closure(QBuiltinFun):
    """An IR function value: its function, the frame it was made in, and the types bound to its type parameters.
    It is a built-in function to the source interpreter, so that library functions written in Quest can call it."""

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
    def __init__(self, runtime_env: RuntimeEnvironment) -> None:
        self.renv = runtime_env
        self.root = RuntimeEnvironment.create_root_env()
        # The unit's modules and those it imports (by identity), as records of their members
        self.modules: dict[int, QValue] = {}
        self.declared: set[int] = set()
        # For each let rec being run, the captures of closures made in it of variables it has yet to bind: (the
        # closure's captured values, the index, the variable, the let rec's frame)
        self.fixups: list[list[tuple[list[QValue], int, ir.Var, _Frame]]] = []

    # Units

    def run(self, unit: ir.Unit) -> None:
        for imp in unit.imports:
            self.import_module(imp)
        for m in unit.modules:
            frame = _Frame(None)
            self.run_top_level(m.init, frame)
            self.modules[id(m)] = QRecord({name: frame.lookup(var) for name, var in m.members.items()})
        self.run_top_level(unit.main, _Frame(None))

    def run_top_level(self, body: ir.Body, frame: _Frame) -> None:
        signal = self.body(body, frame)
        if signal is not None:
            raise IRInterpreterError(f"a top level ends with {signal[0]}")

    def import_module(self, imp: ir.Import) -> None:
        from quest.modules.loader import load_module_for_interpreter

        evaluated = self.renv.evaluated_modules
        if imp.canonical_path in evaluated:
            value = evaluated[imp.canonical_path]
        else:
            value = load_module_for_interpreter(imp.module_path, imp.interface_path, self.renv)
            if value is not None:
                evaluated[imp.canonical_path] = value
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
                # A new string each time, as each evaluation of a string literal is (is compares strings by identity)
                return QString(v)
        raise IRInterpreterError(f"constant {v!r} of shape {a.shape.kind}")

    def atoms(self, atoms: tuple[ir.Atom, ...], frame: _Frame) -> list[QValue]:
        return [self.atom(a, frame) for a in atoms]

    # Calls

    def apply(self, callee: QValue, args: list[QValue]) -> QValue:
        match callee:
            case _Closure(function=f):
                frame = _Frame(callee.frame, dict(callee.type_bindings))
                if f.env is not None:
                    frame.values[id(f.env)] = callee.env
                for (param, _mode), arg in zip(f.params, args):
                    frame.values[id(param)] = arg
                signal = self.body(f.body, frame)
                if signal is None or signal[0] != "return":
                    raise IRInterpreterError(f"function '{f.var.hint}' ends without returning")
                return signal[1]
            case QBuiltinFun(fn=fn):
                return fn(*args)
            case QClosure():
                from quest.interpreter import eval_expr
                from quest.typed_ast import TypedExternal

                call_env = callee.env.push_scope()
                call_env.bind_types(callee.type_bindings)
                for name, arg in zip(callee.params, args):
                    call_env.define(name, arg)
                if isinstance(callee.body, TypedExternal):
                    from quest.builtins import BuiltinModuleRegistry

                    ext = BuiltinModuleRegistry.resolve_external_symbol(callee.body.symbol)
                    if isinstance(ext, QBuiltinFun):
                        return ext.fn(*args)
                    return ext(*args) if callable(ext) else ext
                return eval_expr(callee.body, call_env)
        raise QuestRuntimeError(f"Cannot call non-function of type {callee.type_name}")

    def type_apply(self, callee: QValue, type_args: tuple[QType, ...]) -> QValue:
        """A polymorphic value applied to types: its instance (the value, for a polymorphic function with no value
        parameters, as the source interpreter computes it)."""
        match callee:
            case _Closure(function=f):
                inst = callee.instantiate(self, type_args)
                if not f.params and len(inst.type_bindings) >= len(f.type_params) and not _is_function_type(f):
                    return self.apply(inst, [])
                return inst
            case QClosure():
                inst = callee.instantiate(type_args) if callee.type_param_ids else callee
                if len(inst.params) == 0:
                    from quest.interpreter import eval_expr

                    call_env = inst.env.push_scope()
                    call_env.bind_types(inst.type_bindings)
                    return eval_expr(inst.body, call_env)
                return inst
            case QBuiltinFun(name="list.nil"):
                return QList(())
        return callee

    def callee(self, var: Optional[ir.Var], module: Optional[ir.ModuleRef], member: Optional[str],
               frame: _Frame) -> QValue:
        return self.atom(var, frame) if var is not None else self.member(module, member)

    # Operations

    def operation(self, o, frame: _Frame, result: ir.Var) -> QValue:
        match o:
            case ir.Var() | ir.Const():
                return self.atom(o, frame)
            case ir.Prim(op=op, args=args):
                return self.prim(op, self.atoms(args, frame))
            case ir.Call(callee=callee, type_args=type_args, args=args, module=module, member=member):
                f = self.callee(callee, module, member, frame)
                if type_args:
                    f = self.type_apply(f, tuple(frame.resolve(t) for t in type_args))
                return self.apply(f, self.atoms(args, frame))
            case ir.TypeApp(callee=callee, type_args=type_args, module=module, member=member):
                f = self.callee(callee, module, member, frame)
                return self.type_apply(f, tuple(frame.resolve(t) for t in type_args))
            case ir.ModuleMember(module=module, member=None):
                return self.module(module)
            case ir.ModuleMember(module=module, member=member):
                return self.member(module, member)
            case ir.Builtin(name=name):
                return self.root.lookup(name)
            case ir.MakeClosure(code=code, captures=captures, type_args=type_args):
                return self.make_closure(code, captures, type_args, frame)
            case ir.EnvField(env=env, index=index):
                return self.atom(env, frame)[index]
            case ir.External(symbol=symbol):
                from quest.builtins import BuiltinModuleRegistry

                return BuiltinModuleRegistry.resolve_external_symbol(symbol)
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
            case ir.MakeOption(tag=tag, payload=payload, ordinal=ordinal):
                return self.make_option(tag, payload, ordinal, result, frame)
            case ir.IsTag(value=v, tag=tag):
                return QBool(self.atom(v, frame).tag == tag)
            case ir.Payload(value=v, tag=tag):
                return _payload(self.atom(v, frame), tag)
            case ir.Ordinal(value=v):
                o_val = self.atom(v, frame)
                if not isinstance(o_val, QOption):
                    raise QuestRuntimeError(f"ordinal expects Option, got {o_val.type_name}")
                return QInt(o_val.ordinal)
            case ir.MakeArray(args=args):
                return QArray(elements=self.atoms(args, frame))
            case ir.ArrayRep(count=count, init=init):
                n = self.atom(count, frame).value
                if n < 0:
                    raise QuestException(ARRAY_OP_ERROR_EXC)
                v = self.atom(init, frame)
                return QArray(elements=[v for _ in range(n)])
            case ir.Index(array=a, index=i):
                arr = self.atom(a, frame)
                idx = self.atom(i, frame).value
                if idx < 0 or idx >= arr.size():
                    raise QuestException(ARRAY_OP_ERROR_EXC)
                return arr.get(idx)
            case ir.MakeAuto(witness=witness, payload=p):
                return QAutoVal(self.atom(p, frame), frame.resolve(witness))
            case ir.MakeException(name=name):
                return QExceptionVal(name=name)
            case ir.ExceptionPayload(exception=e):
                raised = self.atom(e, frame)
                if not isinstance(raised, _Raised):
                    raise IRInterpreterError("exception_payload of a value other than a handler's exception")
                payload = raised.raised.payload
                return payload if payload is not None else OK_VALUE
            case ir.Addr():
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
            return QInt(_eval_int_arithmetic(op, a.value, b.value))
        if op in _INT_RELATIONAL:
            return TRUE_VALUE if _eval_int_relational(op, a.value, b.value) else FALSE_VALUE
        if op in _REAL_ARITHMETIC:
            return QReal(_eval_real_arithmetic(op, a.value, b.value))
        if op in _REAL_RELATIONAL:
            return TRUE_VALUE if _eval_real_relational(op, a.value, b.value) else FALSE_VALUE
        if op == "<>":
            return QString(a.value + b.value)
        if op == "/\\":
            return TRUE_VALUE if (a.value and b.value) else FALSE_VALUE
        if op == "\\/":
            return TRUE_VALUE if (a.value or b.value) else FALSE_VALUE
        raise IRInterpreterError(f"primitive '{op}'")

    def make_closure(self, code: ir.Function, captures, type_args, frame: _Frame) -> _Closure:
        """A closure of a lifted function, whose frames see only the globals of the top level that makes it."""
        values: list[QValue] = []
        for i, a in enumerate(captures):
            if isinstance(a, ir.Var) and frame.peek(a) is _UNBOUND and self.fixups:
                # A variable of an enclosing let rec, bound once its body has run
                self.fixups[-1].append((values, i, a, frame))
                values.append(_UNBOUND)
            else:
                values.append(self.atom(a, frame))
        bindings = {tp.symbol_id: frame.resolve(t) for tp, t in zip(code.type_params, type_args)}
        return _Closure(self, code, frame.top, bindings, values)

    def make_tuple(self, values: list[QValue], type_components, result: ir.Var, frame: _Frame) -> QTuple:
        """A tuple laid out as the source interpreter lays it out: its type components are elements too (type
        values), which printing a tuple expects."""
        t = _exposed_type(result.type)
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

    def make_option(self, tag: Optional[str], payload, ordinal, result: ir.Var, frame: _Frame) -> QOption:
        p = self.atom(payload, frame) if payload is not None else None
        t = _exposed_type(frame.resolve(result.type))
        if not isinstance(t, QOptionType):
            raise IRInterpreterError(f"option of type {result.type}")
        if ordinal is not None:
            n = self.atom(ordinal, frame).value
            if n < 0 or n >= len(t.options):
                raise QuestRuntimeError(f"Option ordinal {n} out of bounds (0 <= ordinal < {len(t.options)})")
            return QOption(tag=t.options[n].name, payload=p, ordinal=n)
        n = next(i for i, case in enumerate(t.options) if case.name == tag)
        return QOption(tag=tag, payload=p, ordinal=n)

    def address(self, o: ir.Addr, frame: _Frame) -> QValue:
        if o.var is not None:
            return frame.lookup(o.var)
        if o.cell is not None:
            return QRef(self.atom(o.cell, frame))
        base = _deref(self.atom(o.base, frame))
        if o.name is not None:
            cell = base.get(o.name)
            if not isinstance(cell, QRef):
                raise QuestRuntimeError(f"Field '{o.name}' is not mutable")
            return cell
        if isinstance(o.index, int):
            i = _element_index(base, o.index)
            element = base.elements[i]
            return element if isinstance(element, QRef) else QTupleElementRef(base, i)
        idx = self.atom(o.index, frame).value
        if idx < 0 or idx >= base.size():
            raise QuestException(ARRAY_OP_ERROR_EXC)
        return QArrayElementRef(base, idx)

    def store(self, s: ir.Store, frame: _Frame) -> None:
        value = self.atom(s.value, frame)
        if s.address is not None:
            self.atom(s.address, frame).assign(value)
            return
        base = _deref(self.atom(s.base, frame))
        if s.name is not None:
            cell = base.fields.get(s.name)
            if isinstance(cell, QRef):
                cell.assign(value)
            else:
                base.fields[s.name] = value
        elif isinstance(s.index, int):
            i = _element_index(base, s.index)
            if isinstance(base.elements[i], QRef):
                base.elements[i].assign(value)
            else:
                base.set_by_index(i, value)
        else:
            idx = self.atom(s.index, frame).value
            if idx < 0 or idx >= base.size():
                raise QuestException(ARRAY_OP_ERROR_EXC)
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
                frame.values[id(var)] = QRef(self.atom(init, frame))
            case ir.Declare(var=var):
                self.declared.add(id(var))
                frame.values[id(var)] = _UNBOUND
            case ir.Assign(var=var, value=value):
                frame.lookup(var).assign(self.atom(value, frame))
            case ir.Store():
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
                    match_type = frame.resolve(c.match_type)
                    if is_type_equal(v.type_val, match_type) if c.exact else is_subtype(v.type_val, match_type):
                        for b in c.binders:
                            frame.values[id(b)] = v.value
                        return self.body(c.body, frame)
                if else_body is not None:
                    return self.body(else_body, frame)
                raise QuestException(DYNAMIC_ERROR_EXC)
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
            case ir.Raise(exception=e, payload=p):
                exc = self.atom(e, frame)
                if isinstance(exc, _Raised):
                    if p is None:
                        raise exc.raised
                    exc = exc.raised.exc_val
                payload = self.atom(p, frame) if p is not None else None
                payload_type = p.type if isinstance(p, ir.Var) else None
                raise QuestException(exc_val=exc, payload=payload, payload_type=payload_type)
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
    """The element of a tuple holding its index'th value component (its type components are elements too)."""
    n = -1
    for i, element in enumerate(tup.elements):
        if not isinstance(element, QTypeValue):
            n += 1
            if n == index:
                return i
    raise IRInterpreterError(f"tuple has no value component {index}")


def _payload(v: QValue, tag: str) -> QValue:
    """A variant's payload, or an option's components (its ordinal first) as a tuple, as the source interpreter's
    `v!tag` computes them."""
    if v.tag != tag:
        raise QuestException(VARIANT_ERROR_EXC)
    if isinstance(v, QOption):
        ordinal = QInt(v.ordinal)
        if v.payload is None:
            return QTuple(elements=(ordinal,), labels=(None,))
        if isinstance(v.payload, QTuple):
            return QTuple(elements=(ordinal, *v.payload.elements), labels=(None, *v.payload.labels))
        return QTuple(elements=(ordinal, v.payload), labels=(None, None))
    return v.payload if v.payload is not None else QOk()


def _is_function_type(f: ir.Function) -> bool:
    """Whether a polymorphic function, applied to all its types, is a function (rather than a value computed when it
    is instantiated)."""
    t = _exposed_type(f.var.type)
    while isinstance(t, QAllType):
        t = _exposed_type(t.body)
    return isinstance(t, QFunType)


def run_unit(unit: ir.Unit, runtime_env: RuntimeEnvironment) -> None:
    """Runs a unit: its imports, its modules' initializers, then its main body."""
    Interpreter(runtime_env).run(unit)
