"""Closure conversion (docs/ir.md §8.2): lifts every function to the unit's functions, making closures of them.

Each funs statement becomes lets of `closure code {captures...}`: `code` is the lifted function, and its captures
are the function's free variables other than globals (global_variables), in the order of their first use. The lifted
function reads them from its environment at its start (`let x = env_field(env, i)`) and uses those variables in
their place. Closures do not capture mutable variables (Core does not allow it), so captures are values, copied
into the closure. A function nested in a polymorphic one takes the enclosing functions' type parameters as its
leading type parameters, which its closure supplies (its types mention them).

Nested functions are converted first, so a function's free variables include what the closures it makes capture. A
closure that captures another of its own recursive group (or itself) is made in a let rec, whose closures refer to
the variables being bound, so that the C printer fills in such captures once all the group's closures exist.
"""

from __future__ import annotations

from dataclasses import fields

from quest.ir import nodes as ir
from quest.ir.walk import global_variables, statement_binders, statement_bodies, statement_uses, walk_statements
from quest.types import OK_TYPE, QTypeVar


class _Converter:
    def __init__(self, unit: ir.Unit) -> None:
        self.unit = unit
        self.globals = global_variables(unit)

    def body(self, body: ir.Body, type_params: tuple[ir.TypeParam, ...]) -> None:
        statements = []
        for s in body.statements:
            if isinstance(s, ir.Funs):
                statements.extend(self.funs(s, type_params))
                continue
            for b in statement_bodies(s):
                self.body(b, type_params)
            statements.append(s)
        body.statements = statements

    def funs(self, s: ir.Funs, type_params: tuple[ir.TypeParam, ...]) -> list:
        type_args = tuple(QTypeVar(name=tp.name, symbol_id=tp.symbol_id, bound=tp.kind) for tp in type_params)
        lets = []
        captures_group = False
        group = {id(f.var) for f in s.functions}
        for f in s.functions:
            code, captures = self.lift(f, type_params)
            captures_group = captures_group or any(id(c) in group for c in captures)
            lets.append(ir.Let(f.var, ir.MakeClosure(code, tuple(captures), type_args)))
        if s.recursive and captures_group:
            return [ir.LetRec(tuple(f.var for f in s.functions), ir.Body(lets))]
        return lets

    def lift(self, f: ir.Function, type_params: tuple[ir.TypeParam, ...]) -> tuple[ir.Function, list[ir.Var]]:
        """The lifted function, added to the unit's, and the variables its closures capture."""
        self.body(f.body, type_params + f.type_params)
        bound = {id(v) for v, _ in f.params}
        used: dict[int, ir.Var] = {}
        for s in walk_statements(f.body, into_functions=False):
            bound.update(id(v) for v in statement_binders(s))
            for a in statement_uses(s):
                if isinstance(a, ir.Var):
                    used.setdefault(id(a), a)
        captures = [v for key, v in used.items() if key not in bound and key not in self.globals]
        env = None
        if captures or type_params:
            # The environment (of the captured values, and of the descriptors of the enclosing functions' type
            # parameters) is not a value of a Quest type; its type is a placeholder (it prints without one)
            env = ir.Var("env", OK_TYPE)
            renamed: dict[int, ir.Var] = {}
            prologue = []
            for i, c in enumerate(captures):
                if c.mutable:
                    raise ValueError(f"function '{f.var.hint}' captures mutable variable '{c.hint}'")
                local = ir.Var(c.hint, c.type)
                renamed[id(c)] = local
                prologue.append(ir.Let(local, ir.EnvField(env, i)))
            _rename(f.body, renamed)
            f.body.statements = prologue + f.body.statements
        code = ir.Function(ir.Var(f.var.hint, f.var.type), type_params + f.type_params, f.params, f.result_type,
                           f.body, env, f.trace_name)
        self.unit.functions.append(code)
        return code, captures

    def run(self) -> None:
        for m in self.unit.modules:
            self.body(m.init, ())
        self.body(self.unit.main, ())


def _rename(body: ir.Body, renamed: dict[int, ir.Var]) -> None:
    """Replaces, in place, the uses in body of the variables renamed maps (none of which body binds)."""
    for s in walk_statements(body, into_functions=False):
        _rename_fields(s, renamed)


def _rename_fields(node, renamed: dict[int, ir.Var]) -> None:
    for f in fields(node):
        if f.name == "code":
            continue
        v = getattr(node, f.name)
        new = _renamed(v, renamed)
        if new is not v:
            setattr(node, f.name, new)
        elif f.name in ("value",) and not isinstance(v, (ir.Var, ir.Const)) and hasattr(v, "__dataclass_fields__"):
            # A let's or do's operation
            _rename_fields(v, renamed)


def _renamed(v, renamed: dict[int, ir.Var]):
    if isinstance(v, ir.Var):
        return renamed.get(id(v), v)
    if isinstance(v, tuple):
        items = tuple(_renamed(x, renamed) for x in v)
        return v if all(a is b for a, b in zip(items, v)) else items
    return v


def closure_convert_unit(unit: ir.Unit) -> ir.Unit:
    """Converts the unit's functions to closures of lifted functions, in place, returning it."""
    _Converter(unit).run()
    unit.stage = "closed"
    return unit
