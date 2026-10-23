"""The IR's nodes (docs/ir.md §3, §5, §6).

A unit is a body of statements (its main) together with the modules it defines. Bodies are sequences of statements.
Operations take atoms (variables and constants) and are named by `let`; structured statements (if, switch, loop,
try) contain bodies, and continue with the next statement when a branch ends without a terminator; values produced on
several paths join through join points.

Binders are objects: a Var is bound by exactly one binder (a let, a mutable variable's declaration, a function's
parameter, a funs statement, a join point's parameter, a case's or handler's binder), and every use refers to that
same object. Printing gives variables distinct names (ir/printer.py); the verifier checks that every use is in scope
(ir/verify.py).

Nodes are plain mutable dataclasses with identity equality, built once by lowering and then rewritten by passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from quest.ir.shapes import Shape
from quest.types import QKind, QType


# ============================================================================
# Variables and atoms
# ============================================================================

@dataclass(eq=False)
class Var:
    """A variable: a value (bound once), a mutable variable (a `let var` local, or a `var`/`out` parameter), or a
    function bound by a funs statement. `type` is the Quest type, kept for printing (with alias names)."""
    hint: str
    shape: Shape
    type: QType
    mutable: bool = False

    def __repr__(self) -> str:
        return f"<Var {self.hint}>"


@dataclass(eq=False)
class Const:
    """A constant: an Int, Real, Bool, Char, or String, or ok (value None)."""
    value: Union[int, float, bool, str, None]
    shape: Shape


Atom = Union[Var, Const]


@dataclass(eq=False)
class TypeParam:
    """A type parameter of a function, identified by the symbol that types (and so shapes) refer to it by."""
    name: str
    symbol_id: int
    kind: QKind
    bound: Optional[Shape] = None


# ============================================================================
# Operations (the right-hand sides of let)
# ============================================================================

@dataclass(eq=False)
class Prim:
    """A primitive operation on scalars and strings: arithmetic, comparison, logic, concatenation, identity (`is`)."""
    op: str
    args: tuple[Atom, ...]


@dataclass(eq=False)
class Call:
    """A call: of a function bound by a funs statement or held in a variable (`callee`), or of a module's member
    (`module` and `member`), with type arguments and arguments."""
    callee: Optional[Var]
    type_args: tuple[QType, ...]
    args: tuple[Atom, ...]
    module: Optional[str] = None
    member: Optional[str] = None


@dataclass(eq=False)
class TypeApp:
    """A polymorphic value applied to types only: the instance, a value of the instantiated type."""
    callee: Optional[Var]
    type_args: tuple[QType, ...]
    module: Optional[str] = None
    member: Optional[str] = None


@dataclass(eq=False)
class ModuleMember:
    """A member of a module, as a value (`conv.int` passed as an argument)."""
    module: str
    member: str


@dataclass(eq=False)
class External:
    """An external C value or function (`external "symbol"`), and its inline C template if any."""
    symbol: str
    inline_template: Optional[str] = None


@dataclass(eq=False)
class MakeTuple:
    """A tuple of the atoms, its value components in order. `type_components` keeps the names and types of its type
    components (erased from the layout), for printing."""
    args: tuple[Atom, ...]
    type_components: tuple[tuple[str, QType], ...] = ()


@dataclass(eq=False)
class TupleField:
    tuple: Atom
    index: int


@dataclass(eq=False)
class MakeRecord:
    """A record of named fields (`var` fields marked)."""
    fields: tuple[tuple[str, Atom, bool], ...]


@dataclass(eq=False)
class RecordField:
    record: Atom
    name: str


@dataclass(eq=False)
class MakeVariant:
    tag: str
    payload: Optional[Atom]


@dataclass(eq=False)
class MakeOption:
    """An option of the given case, by tag or, when `ordinal` is an atom, by computed ordinal, with its payload's
    components."""
    tag: Optional[str]
    args: tuple[Atom, ...]
    ordinal: Optional[Atom] = None


@dataclass(eq=False)
class IsTag:
    """Whether a variant or option is of the case (`v?tag`)."""
    value: Atom
    tag: str


@dataclass(eq=False)
class Payload:
    """A variant's payload, or an option's payload as a tuple, for the case (`v!tag`, raising if it is another)."""
    value: Atom
    tag: str


@dataclass(eq=False)
class Ordinal:
    """An option's ordinal."""
    value: Atom


@dataclass(eq=False)
class MakeArray:
    args: tuple[Atom, ...]


@dataclass(eq=False)
class ArrayRep:
    """An array of `count` copies of `init`."""
    count: Atom
    init: Atom


@dataclass(eq=False)
class Index:
    """An array's element (raising if the index is out of bounds)."""
    array: Atom
    index: Atom


@dataclass(eq=False)
class MakeAuto:
    """An auto value of `auto_type`, with type component `witness` and payload components `args`."""
    witness: QType
    auto_type: QType
    payload: Atom


@dataclass(eq=False)
class MakeException:
    """A new exception (exceptions are generative), with the payload type it carries, if any."""
    name: str
    payload_type: Optional[QType] = None


@dataclass(eq=False)
class ExceptionPayload:
    """The payload of a raised exception (in a handler)."""
    exception: Atom


@dataclass(eq=False)
class Addr:
    """The address of a location, for a var or out argument (`@x`, `@r.f`, `@t.f`, `@a[i]`): a mutable variable
    (`var`), a record's or tuple's var component (`base` and `name` or `index`), or an array element (`base`, `index`).
    A fresh cell holding `init` when `cell` is set (`var(e)`)."""
    var: Optional[Var] = None
    base: Optional[Atom] = None
    name: Optional[str] = None
    index: Optional[Union[int, Atom]] = None
    cell: Optional[Atom] = None


@dataclass(eq=False)
class Load:
    """The value at an address."""
    address: Atom


Operation = Union[
    Prim, Call, TypeApp, ModuleMember, External, MakeTuple, TupleField, MakeRecord, RecordField, MakeVariant,
    MakeOption, IsTag, Payload, Ordinal, MakeArray, ArrayRep, Index, MakeAuto, MakeException, ExceptionPayload, Addr,
    Load,
]


# ============================================================================
# Statements
# ============================================================================

@dataclass(eq=False)
class Let:
    """let var: shape = operation, or = atom (a copy)."""
    var: Var
    value: Union[Operation, Atom]


@dataclass(eq=False)
class VarDecl:
    """A mutable variable and its initial value."""
    var: Var
    init: Atom


@dataclass(eq=False)
class Assign:
    """var := atom, for a mutable variable."""
    var: Var
    value: Atom


@dataclass(eq=False)
class Store:
    """A store into a record's or tuple's var component, an array element, or the location at an address."""
    value: Atom
    base: Optional[Atom] = None
    name: Optional[str] = None
    index: Optional[Union[int, Atom]] = None
    address: Optional[Atom] = None


@dataclass(eq=False)
class Do:
    """An operation evaluated for its effect (a call whose result is Ok or unused)."""
    value: Operation


@dataclass(eq=False)
class Function:
    """A function: `var` names it; its type parameters, parameters (with modes), result shape, and body."""
    var: Var
    type_params: tuple[TypeParam, ...]
    params: tuple[tuple[Var, str], ...]
    result: Shape
    body: Body


@dataclass(eq=False)
class Funs:
    """Functions bound together: each is in scope in the bodies of all when `recursive` (let rec), in none
    otherwise."""
    functions: tuple[Function, ...]
    recursive: bool = False


@dataclass(eq=False)
class If:
    cond: Atom
    then_body: Body
    else_body: Body


@dataclass(eq=False)
class Case:
    """A case of a switch: the tags it matches, the variable bound to the payload (if any), and its body."""
    tags: tuple[str, ...]
    body: Body
    binder: Optional[Var] = None


@dataclass(eq=False)
class Switch:
    """A switch on a variant's or option's tag."""
    value: Atom
    cases: tuple[Case, ...]
    else_body: Optional[Body] = None


@dataclass(eq=False)
class InspectCase:
    """A case of an inspect: the type it matches (a subtype of it, or exactly it), the variables bound to the value's
    components as of that type, and its body."""
    match_type: QType
    binders: tuple[Var, ...]
    body: Body
    exact: bool = False


@dataclass(eq=False)
class Inspect:
    """An inspect of a dynamic or auto value by its run-time type."""
    value: Atom
    cases: tuple[InspectCase, ...]
    else_body: Optional[Body] = None
    auto_type: Optional[QType] = None


@dataclass(eq=False)
class Loop:
    """A loop: its body repeats, until a break of its label."""
    label: str
    body: Body


@dataclass(eq=False)
class Try:
    """A try region: a raise in `body`, or in what it calls, transfers to `handler`, with `exception` bound to the
    exception raised."""
    body: Body
    exception: Var
    handler: Body


@dataclass(eq=False)
class Join:
    """A join point: `jump label(args)` in `body` continues with `continuation`, its parameters bound to the args."""
    label: str
    params: tuple[Var, ...]
    continuation: Body
    body: Body


@dataclass(eq=False)
class Echo:
    """Prints a value with its Quest type: a top-level phrase's value (echo), or the program's result."""
    value: Atom
    type: QType
    name: Optional[str] = None
    is_result: bool = False


# Terminators

@dataclass(eq=False)
class Return:
    value: Atom


@dataclass(eq=False)
class Jump:
    label: str
    args: tuple[Atom, ...]


@dataclass(eq=False)
class Break:
    label: str


@dataclass(eq=False)
class Continue:
    label: str


@dataclass(eq=False)
class Raise:
    exception: Atom
    payload: Optional[Atom] = None


@dataclass(eq=False)
class Unreachable:
    """After a call that does not return (exit), or where no path can reach."""


Terminator = Union[Return, Jump, Break, Continue, Raise, Unreachable]
Statement = Union[
    Let, VarDecl, Assign, Store, Do, Funs, If, Switch, Inspect, Loop, Try, Join, Echo, Return, Jump, Break, Continue,
    Raise, Unreachable,
]
TERMINATORS = (Return, Jump, Break, Continue, Raise, Unreachable)


@dataclass(eq=False)
class Body:
    """A sequence of statements; a terminator, if any, is last."""
    statements: list[Statement] = field(default_factory=list)

    @property
    def terminated(self) -> bool:
        return bool(self.statements) and isinstance(self.statements[-1], TERMINATORS)


# ============================================================================
# Units and modules
# ============================================================================

@dataclass(eq=False)
class Module:
    """A module defined by the unit: its members, bound in its initializer body, by name."""
    name: str
    interface_name: str
    init: Body
    members: dict[str, Var]


@dataclass(eq=False)
class Unit:
    """A compilation unit: the modules it defines, its main body (the program's phrases, in order), and the modules
    it uses from elsewhere."""
    main: Body
    modules: list[Module] = field(default_factory=list)
    imports: tuple[str, ...] = ()
