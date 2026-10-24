"""The IR's nodes (docs/ir.md §3, §5, §6).

A unit is a body of statements (its main) together with the modules it defines. Bodies are sequences of statements.
Operations take atoms (variables and constants) and are named by `let`; structured statements (if, switch, loop,
try) contain bodies, and continue with the next statement when a branch ends without a terminator; values produced on
several paths join through join points.

Binders are objects: a Var is bound by exactly one binder (a let, a mutable variable's declaration, a function's
parameter, a funs statement, a join point's parameter, a case's or handler's binder), and every use refers to that
same object. A declared variable (Declare) is in scope from its declaration, and bound by one later let. Printing gives variables distinct names (ir/printer.py); the verifier checks that every use is in scope
(ir/verify.py).

Nodes are plain mutable dataclasses with identity equality, built once by lowering and then rewritten by passes.

The nodes that can raise an exception (checked operations, raise) keep the source offset of the expression they were
lowered from, in the unit's source file, so that every backend reports where an uncaught exception was raised
(docs/exceptions.md §3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Union

from quest.ir.shapes import Shape, shape
from quest.types import QKind, QType


# ============================================================================
# Variables and atoms
# ============================================================================

@dataclass(eq=False)
class Var:
    """A variable: a value (bound once), a mutable variable (a `let var` local, or a `var`/`out` parameter), or a
    function bound by a funs statement. `type` is its Quest type (with alias names, for printing), which passes
    rewrite (specialization substitutes type arguments in it); its shape is the type's."""
    hint: str
    type: QType
    mutable: bool = False

    @property
    def shape(self) -> Shape:
        return shape(self.type)

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
    offset: Optional[int] = None


@dataclass(eq=False)
class Call:
    """A call: of a function bound by a funs statement or held in a variable (`callee`), or of a module's member
    (`module`, the unit's module or import it refers to, and `member`), with type arguments and arguments."""
    callee: Optional[Var]
    type_args: tuple[QType, ...]
    args: tuple[Atom, ...]
    module: Optional[ModuleRef] = None
    member: Optional[str] = None
    # The type of a module's member called (a variable's is its own)
    callee_type: Optional[QType] = None


@dataclass(eq=False)
class TypeApp:
    """A polymorphic value applied to types only: the instance, a value of the instantiated type."""
    callee: Optional[Var]
    type_args: tuple[QType, ...]
    module: Optional[ModuleRef] = None
    member: Optional[str] = None
    callee_type: Optional[QType] = None


@dataclass(eq=False)
class ModuleMember:
    """A member of a module, as a value (`conv.int` passed as an argument), or the module itself when `member` is
    None (a module used as a value)."""
    module: ModuleRef
    member: Optional[str] = None


@dataclass(eq=False)
class Builtin:
    """A built-in function as a value: an infix operator (`+`), `not`, `extent`, or `ordinal`."""
    name: str


@dataclass(eq=False)
class External:
    """An external C value or function (`external "symbol"`), and its inline C template if any. A function is passed
    its type parameters' descriptors only if pass_type_descriptors (a native binding's choice)."""
    symbol: str
    inline_template: Optional[str] = None
    pass_type_descriptors: bool = False


@dataclass(eq=False)
class CallExternal:
    """A call of an external C function: the body of a function defined as `external "symbol"`, which passes the C
    function its type parameters' descriptors (type_args) and its parameters (args; addresses for var and out)."""
    symbol: str
    inline_template: Optional[str]
    type_args: tuple[QType, ...]
    args: tuple[Atom, ...]


@dataclass(eq=False)
class MakeClosure:
    """A closure (after closure conversion): the lifted function `code` (one of the unit's functions), with the
    values it captures, which its body reads from its environment, and the types of the enclosing functions' type
    parameters it takes first (its leading type parameters)."""
    code: Function
    captures: tuple[Atom, ...]
    type_args: tuple[QType, ...] = ()


@dataclass(eq=False)
class EnvField:
    """A value a closure captured, read from the environment of the function it runs (its index'th capture)."""
    env: Atom
    index: int


@dataclass(eq=False)
class Plan:
    """How `convert` changes a value's representation (docs/ir.md §8.3), from `source`'s to `target`'s: `box` (a
    native value to a QVal word, as generic code holds it) or `unbox` (back); `record_view` (a record viewed at a
    supertype, with that type's offset table); `variant_tags` (a variant's tag remapped to a supertype's); `cast` (a
    pointer viewed through another struct, whose layout agrees); `copy` (a new tuple, each component converted by its
    plan in `fields`, None where it is used as it is); `runtime` (converted by the runtime, between the descriptors of
    the two layouts, for a value passed to or returned from a polymorphic callee that lays it out generically: the
    callee's type parameters' instantiation, and whether the value goes to the generic layout, are `layout`); `adapt`
    (a closure wrapped in a thunk of the target's C signature converting arguments and result: `fields` are the
    parameters' plans, then the result's); `view` (a variant or option converted by the runtime between two views'
    descriptors, from a bounded type parameter's view at its bound to another)."""
    kind: str
    source: QType
    target: QType
    fields: tuple[Optional[Plan], ...] = ()
    layout: Optional[tuple[dict[int, QType], bool]] = None


@dataclass(eq=False)
class Convert:
    """A value converted to another representation (after the represent pass)."""
    value: Atom
    plan: Plan


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
    """An option of the given case, by tag or, when `ordinal` is an atom, by computed ordinal, with its payload (a
    tuple of the case's components), if it has one."""
    tag: Optional[str]
    payload: Optional[Atom] = None
    ordinal: Optional[Atom] = None
    offset: Optional[int] = None


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
    offset: Optional[int] = None


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
    offset: Optional[int] = None


@dataclass(eq=False)
class Index:
    """An array's element (raising if the index is out of bounds)."""
    array: Atom
    index: Atom
    offset: Optional[int] = None


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
    offset: Optional[int] = None


@dataclass(eq=False)
class Load:
    """The value at an address."""
    address: Atom


Operation = Union[
    Prim, Call, TypeApp, ModuleMember, Builtin, External, CallExternal, MakeClosure, EnvField, Convert, MakeTuple, TupleField, MakeRecord, RecordField, MakeVariant,
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
    """A mutable variable and its initial value (none for the temporary of an out argument, which the callee
    writes before it is read)."""
    var: Var
    init: Optional[Atom]


@dataclass(eq=False)
class Declare:
    """Declares a variable, in scope from here to the end of the body, whose value one later let in that scope binds:
    a named exception made inside an expression, whose name the rest of the expression's scope sees. Closures may
    use it, as it is not mutable; reading it before its let has run is undefined (the type checker allows an
    exception made on a branch that does not run to be named later)."""
    var: Var


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
    offset: Optional[int] = None


@dataclass(eq=False)
class Do:
    """An operation evaluated for its effect (a call whose result is Ok or unused)."""
    value: Operation


@dataclass(eq=False)
class Function:
    """A function: `var` names it; its type parameters, parameters (with modes), result type, and body. After closure
    conversion, a function is one of the unit's, and `env`, if any, is the environment of the closure it runs, from
    which its body reads the values it captured."""
    var: Var
    type_params: tuple[TypeParam, ...]
    params: tuple[tuple[Var, str], ...]
    result_type: QType
    body: Body
    env: Optional[Var] = None

    @property
    def result(self) -> Shape:
        return shape(self.result_type)


@dataclass(eq=False)
class Funs:
    """Functions bound together: each is in scope in the bodies of all when `recursive` (let rec), in none
    otherwise."""
    functions: tuple[Function, ...]
    recursive: bool = False


@dataclass(eq=False)
class LetRec:
    """Recursive values (`let rec self: T = tuple let me(): T = self ... end`): `body` computes each variable's value
    (a constructor, or a function), and closures made in `body` may refer to any of the variables, which are bound
    when `body` finishes. (Quest requires such values to be constructors or abstractions.)"""
    vars: tuple[Var, ...]
    body: Body


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
    offset: Optional[int] = None


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
    """Prints a top-level phrase's value as the interpreter does: `prefix` (`let x:T = ` for a binding), the value,
    and, for an expression, ` : T`."""
    value: Atom
    type: QType
    prefix: str = ""


@dataclass(eq=False)
class EchoText:
    """Prints a line of text for a top-level phrase without a value to print (a function, a type or kind
    declaration, an exception)."""
    text: str


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
    """A new raise of an exception, with its payload, if any."""
    exception: Atom
    payload: Optional[Atom] = None
    offset: Optional[int] = None


@dataclass(eq=False)
class Reraise:
    """A try's handler raising the exception it caught again, when none of its branches matches: the exception keeps
    the site it was raised at."""
    exception: Var


@dataclass(eq=False)
class Unreachable:
    """After a call that does not return (exit), or where no path can reach."""


Terminator = Union[Return, Jump, Break, Continue, Raise, Reraise, Unreachable]
Statement = Union[
    Let, VarDecl, Declare, Assign, Store, Do, Funs, LetRec, If, Switch, Inspect, Loop, Try, Join, Echo, EchoText, Return,
    Jump, Break, Continue, Raise, Reraise, Unreachable,
]
TERMINATORS = (Return, Jump, Break, Continue, Raise, Reraise, Unreachable)


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
    """A module defined by the unit: its members, bound in its initializer body, by name. A module file's module (a
    unit of its own, which other units import) also has exports: its interface's members, at the interface's types,
    bound last in its initializer (a member itself where the types are the same)."""
    name: str
    interface_name: str
    init: Body
    members: dict[str, Var]
    exports: Optional[dict[str, Var]] = None


@dataclass(eq=False)
class Import:
    """A module the unit uses from elsewhere: the name it is imported as, the module's path as imported and its
    canonical name (docs/modules.md §2.3), and the path of the interface it is imported through."""
    name: str
    module_path: str
    canonical_path: str
    interface_path: str


# The IR's stages (docs/ir.md §9), in order: each pass produces the next
STAGES = ("core", "specialized", "closed", "represented")

# A reference to a module: one the unit defines, or one it imports (by identity, never by name)
ModuleRef = Union[Module, Import]


@dataclass(eq=False)
class Unit:
    """A compilation unit: the modules it defines, its main body (the program's phrases, in order), and the modules
    it uses from elsewhere."""
    main: Body
    modules: list[Module] = field(default_factory=list)
    imports: tuple[Import, ...] = ()
    # After closure conversion, every function of the unit, lifted out of the bodies that made closures of it
    functions: list[Function] = field(default_factory=list)
    stage: str = "core"
    # The source map of the unit's file, in which the nodes' offsets are
    source_map: Optional[Any] = None

    def at_least(self, stage: str) -> bool:
        """Whether the unit is at the given stage or a later one."""
        return STAGES.index(self.stage) >= STAGES.index(stage)
