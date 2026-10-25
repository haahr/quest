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

The nodes that can raise an exception (checked operations, raise) keep the source offset of the expression they were
lowered from, in the unit's source file, so that every backend reports where an uncaught exception was raised
(docs/exceptions.md §3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Union

from quest.ir.shapes import Shape, shape
from quest.types import QExternalType, QKind, QType


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
    # Set by the represent pass for a variable of a record or variant type held boxed, in its slot representation
    # (docs/ir.md §4.2): a value bound by a let is the box itself (read from a slot, or made to be stored into one),
    # which slots take as it is; a mutable variable whose address is taken, or a var or out parameter, holds its
    # location's box, and a use of it reads the value from the box
    boxed: bool = False

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


# ============================================================================
# Descriptors (docs/ir.md §7, §8.4)
# ============================================================================

# The type of a descriptor variable: a run-time type, the descriptor of a type parameter
DESCRIPTOR_TYPE = QExternalType(name="descriptor", c_type="const QTypeDescriptor *")


@dataclass(eq=False)
class StaticDescriptor:
    """The static descriptor of a type that mentions no type parameter in scope, or of a template, a type whose holes
    (codegen/descriptors.py, hole_var) stand for type parameters. `echo`: the descriptor echo writes a value of the
    closed type by, which writes its type components with their alias names (a copy of the shared descriptor, where
    the type has type components)."""
    type: QType
    echo: bool = False


@dataclass(eq=False)
class Instantiate:
    """A template's descriptor instantiated with the descriptors of its holes, in order (at run time)."""
    template: QType
    args: tuple[Descriptor, ...]


# A descriptor operand (after the describe pass): a descriptor variable (a Var of DESCRIPTOR_TYPE, bound by a
# DescriptorParam), a static descriptor, or an instantiated template. Descriptors are pure, so operands are these small
# expressions rather than values named by lets
Descriptor = Union[Var, StaticDescriptor, Instantiate]


@dataclass(eq=False)
class DescriptorParam:
    """A descriptor variable bound for a type parameter: a function's (its own, passed before its parameters, or one
    its closure supplies, read from its environment), a thunk's, or an inspected auto value's type component. `symbols`
    are the symbols the type parameter is named by in the types it describes (a thunk's type parameters are named by
    both the closure's type and the type it is adapted to)."""
    var: Var
    symbols: tuple[int, ...]


@dataclass(eq=False)
class OffsetTable:
    """A static offset table: the record type `layout`'s payload viewed at `view` (docs/c-representation.md §5.2).
    `registered`: the two types' static descriptors, by which the runtime finds the table for dynamic values, when
    both are closed."""
    view: QType
    layout: QType
    registered: Optional[tuple[StaticDescriptor, StaticDescriptor]] = None


@dataclass(eq=False)
class TagMap:
    """A static table remapping a variant's tags from `source`'s numbering to its supertype `target`'s."""
    target: QType
    source: QType


@dataclass(eq=False)
class StaticData:
    """The static descriptors and tables a unit's operations refer to (after the describe pass), which a backend
    emits: descriptors (each with those of its parts), offset tables, and tag maps."""
    descriptors: list[StaticDescriptor] = field(default_factory=list)
    offset_tables: list[OffsetTable] = field(default_factory=list)
    tag_maps: list[TagMap] = field(default_factory=list)


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

# How an operation reads (or writes) a component of a tuple or option, as the represent pass decides
# (docs/c-representation.md §5.8): DIRECT, the value is not a proxy (its type cannot be one, or the function made it);
# ORIGINAL, it may be a proxy, but the component reads the same from the proxy's original (its slot, or for `is`, the
# object compared); PROXY, it may be a proxy at which the component changes view, so the read checks, and converts
# through the proxy
DIRECT, ORIGINAL, PROXY = "direct", "original", "proxy"

@dataclass(eq=False)
class Prim:
    """A primitive operation on scalars and strings: arithmetic, comparison, logic, concatenation, identity (`is`)."""
    op: str
    args: tuple[Atom, ...]
    offset: Optional[int] = None
    # For `is` of tuples or options that may be proxies, ORIGINAL: their originals are compared
    access: str = DIRECT
    # For `is` of values held as QVal words (after the describe pass), their type's descriptor
    descriptor: Optional[Descriptor] = None


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
    # The type arguments' descriptors (after the describe pass)
    descriptors: tuple[Descriptor, ...] = ()


@dataclass(eq=False)
class TypeApp:
    """A polymorphic value applied to types only: the instance, a value of the instantiated type."""
    callee: Optional[Var]
    type_args: tuple[QType, ...]
    module: Optional[ModuleRef] = None
    member: Optional[str] = None
    callee_type: Optional[QType] = None
    # Set by the represent pass: for a polymorphic value of no parameters, the plan of its value at the type
    # arguments to the let's type; for a function, the instance is a closure converting its arguments from the let's
    # parameter types to the function's generic ones at the type arguments, and its result back: the parameters'
    # plans (None for var and out parameters), then the result's
    plans: tuple[Optional[Plan], ...] = ()
    # Set by the represent pass for a function: the symbols the instance's own type parameters (the thunk's) are named
    # by in the plans, the let's type's as written
    thunk_symbols: tuple[tuple[int, ...], ...] = ()
    # Set by the describe pass: the type arguments' descriptors, and for a function, the thunk's own type parameters'
    # descriptor variables (which its plans' descriptors use); None for a value of no parameters, whose plan converts
    # it where it is applied
    descriptors: tuple[Descriptor, ...] = ()
    thunk_params: Optional[tuple[DescriptorParam, ...]] = None


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
    # The type arguments' descriptors (after the describe pass)
    descriptors: tuple[Descriptor, ...] = ()


@dataclass(eq=False)
class MakeClosure:
    """A closure (after closure conversion): the lifted function `code` (one of the unit's functions), with the
    values it captures, which its body reads from its environment, and the types of the enclosing functions' type
    parameters it takes first (its leading type parameters)."""
    code: Function
    captures: tuple[Atom, ...]
    type_args: tuple[QType, ...] = ()
    # The type arguments' descriptors (after the describe pass)
    descriptors: tuple[Descriptor, ...] = ()


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
    pointer viewed through another struct, whose layout agrees); `unproxy` (a cast to a tuple or option type that
    cannot be a proxy, from one that may be: the original serves, as no component changes view); `slot_box` (a record
    or variant put in a new box, to be stored into a slot) and `slot_unbox` (read from its box, a boxed variable);
    `copy` (a new tuple, each component converted by its plan in `fields`, None where it is used as it is, and read as
    `access` says: an auto value's payload, stored in its witness-independent layout; a `view` field converts the
    slot's QVal form); `runtime` (converted by the runtime, between the descriptors of
    the two layouts, for a value passed to or returned from a polymorphic callee that lays it out generically: the
    callee's type parameters' instantiation, and whether the value goes to the generic layout, are `layout`); `adapt`
    (a closure wrapped in a thunk of the target's C signature converting arguments and result: `fields` are the
    parameters' plans, then the result's); `view` (converted by the runtime between two views' descriptors: a tuple or
    option upcast to a supertype at which components change view, as a proxy of the original; a variant or option
    from a bounded type parameter's view at its bound to another)."""
    kind: str
    source: QType
    target: QType
    fields: tuple[Optional[Plan], ...] = ()
    layout: Optional[tuple[dict[int, QType], bool]] = None
    # A copy's reads of the source tuple's components (DIRECT, ORIGINAL, PROXY)
    access: tuple[str, ...] = ()
    # An adapt plan's thunk's type parameters: the symbols each is named by in the plans of `fields` (the target's
    # and the source's, as written), set by the represent pass
    thunk_symbols: tuple[tuple[int, ...], ...] = ()
    # Set by the describe pass: the descriptors a plan converts by (record_view: the target record's; view: the
    # source's and the target's; runtime: those of the layouts it converts from and to), an adapt plan's thunk's
    # descriptor variables (which its fields' descriptors use), and a variant_tags plan's tag map
    descriptors: tuple[Descriptor, ...] = ()
    thunk_params: tuple[DescriptorParam, ...] = ()
    tag_map: Optional[TagMap] = None


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
    # The positions of the records and variants (unboxed) that the represent pass boxes in the tuple's own allocation
    # (a box is immutable, so it may share it); the other components are atoms in their slot forms
    embedded: tuple[int, ...] = ()


@dataclass(eq=False)
class TupleField:
    """A tuple's component, in its slot form (a record or variant read into a boxed variable), read as `access` says."""
    tuple: Atom
    index: int
    access: str = DIRECT


@dataclass(eq=False)
class MakeRecord:
    """A record of named fields (`var` fields marked), made in its box (so bound to a boxed variable after the represent
    pass). `embedded` (positions in `fields`) and the fields' atoms are as a tuple's; `runtime_offsets` is set when the
    offset table of the let's view of it is not known statically (the view is not a supertype by width alone), and is
    found at run time."""
    fields: tuple[tuple[str, Atom, bool], ...]
    embedded: tuple[int, ...] = ()
    runtime_offsets: bool = False
    # Set by the describe pass: the descriptor of the record's own type (its fields' atoms' types), which its payload
    # carries; the static offset table of its view, or with runtime offsets, the view's descriptor
    descriptor: Optional[Descriptor] = None
    offsets: Optional[OffsetTable] = None
    view_descriptor: Optional[Descriptor] = None


@dataclass(eq=False)
class RecordField:
    """A record's field: in its slot form, or when `stored` (an immutable field of a type a subtype's payload may store
    it at, docs/c-representation.md §5.2) read through the offset table's stored types and converted."""
    record: Atom
    name: str
    stored: bool = False
    # For a stored field (after the describe pass), the descriptor of the field's type, converted to
    descriptor: Optional[Descriptor] = None


@dataclass(eq=False)
class MakeVariant:
    tag: str
    payload: Optional[Atom]


@dataclass(eq=False)
class MakeOption:
    """An option of the given case, by tag or, when `ordinal` is an atom, by computed ordinal, with its payload (a
    tuple of the case's components), if it has one. An ordinal counts in `cases`, the names of the cases of the
    option's type as written (types.canonical.option_case_names), not its shape's order."""
    tag: Optional[str]
    payload: Optional[Atom] = None
    ordinal: Optional[Atom] = None
    offset: Optional[int] = None
    cases: tuple[str, ...] = ()
    # How the components of a tuple payload are read (DIRECT, ORIGINAL, PROXY); a payload that is not a tuple is in
    # its slot form
    access: tuple[str, ...] = ()


@dataclass(eq=False)
class IsTag:
    """Whether a variant or option is of the case (`v?tag`); an option's tag is read as `access` says (DIRECT or
    PROXY)."""
    value: Atom
    tag: str
    access: str = DIRECT


@dataclass(eq=False)
class Payload:
    """A variant's payload, or an option's payload as a tuple, for the case (`v!tag`, raising if it is another): an
    option's tag is read as `access` says, and its components as `components` do. The tuple of an option's payload
    starts with `ordinal`, the case's index in the option's static type as written."""
    value: Atom
    tag: str
    offset: Optional[int] = None
    access: str = DIRECT
    components: tuple[str, ...] = ()
    ordinal: Optional[int] = None


@dataclass(eq=False)
class Ordinal:
    """An option's ordinal: its case's index in `cases`, the names of the cases of its static type as written
    (types.canonical.option_case_names), not its shape's order. The tag is read as `access` says."""
    value: Atom
    cases: tuple[str, ...] = ()
    access: str = DIRECT


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
    # The witness's descriptor (after the describe pass)
    descriptor: Optional[Descriptor] = None


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
    A fresh cell holding `init` when `cell` is set (`var(e)`, in its slot form). A tuple's component is reached as
    `access` says (through a proxy, the original's slot)."""
    var: Optional[Var] = None
    base: Optional[Atom] = None
    name: Optional[str] = None
    index: Optional[Union[int, Atom]] = None
    cell: Optional[Atom] = None
    offset: Optional[int] = None
    access: str = DIRECT


@dataclass(eq=False)
class Load:
    """The value at an address, in its slot form (a location holds a record or variant boxed)."""
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
class Assign:
    """var := atom, for a mutable variable."""
    var: Var
    value: Atom


@dataclass(eq=False)
class Store:
    """A store into a record's or tuple's var component, an array element, or the location at an address, of a value
    in its slot form; a tuple's component is written as `access` says (through a proxy, into the original)."""
    value: Atom
    base: Optional[Atom] = None
    name: Optional[str] = None
    index: Optional[Union[int, Atom]] = None
    address: Optional[Atom] = None
    offset: Optional[int] = None
    access: str = DIRECT


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
    # The function's frame in tracebacks (docs/exceptions.md §2.3); None for the functions the passes make
    trace_name: Optional[str] = None
    # Set by the describe pass: the descriptor variables of its type parameters, in order (those its closure supplies
    # first, read from its environment, then its own, passed before its parameters)
    descriptor_params: tuple[DescriptorParam, ...] = ()

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
    """A case of a switch: the tags it matches, the variable bound to the payload (if any), and its body. An option's
    payload is read as `components` say (a payload that is not a tuple, in its slot form)."""
    tags: tuple[str, ...]
    body: Body
    binder: Optional[Var] = None
    components: tuple[str, ...] = ()


@dataclass(eq=False)
class Switch:
    """A switch on a variant's or option's tag (an option's read as `access` says)."""
    value: Atom
    cases: tuple[Case, ...]
    else_body: Optional[Body] = None
    access: str = DIRECT


@dataclass(eq=False)
class InspectCase:
    """A case of an inspect: the type it matches (a subtype of it, or exactly it), the variables bound to the value's
    components as of that type, and its body."""
    match_type: QType
    binders: tuple[Var, ...]
    body: Body
    exact: bool = False
    # How the binders' components are obtained from the auto value's stored payload, decided by the represent pass
    arm: Optional[InspectArm] = None
    # The matched type's descriptor (after the describe pass)
    descriptor: Optional[Descriptor] = None


@dataclass(eq=False)
class InspectArm:
    """How an inspect case of an auto value obtains its components from the payload, stored in the auto type's
    witness-independent layout (docs/c-representation.md §8), decided by the represent pass. `converted` says, per
    component, how a new tuple of the case's components gets it: None, copied; "component", the type component's
    value itself, converted by descriptor from the value's type component to the case's type (or to `bound`); or
    "mentions", a component whose type mentions the type component, converted by descriptor from its stored type at
    the value's type component. For an exact case (`exact`), the runtime checks whether the stored layout is the
    case's (quest_layout_equivalent): if so the stored payload serves, shared (`shared`, the layouts agree statically,
    so var components are shared too) or converted by `plan`; if not, the components are converted as for any case,
    after raising a layout error when the auto type has var components (`layout_error`). `bound` is set when the
    case's type is a type parameter in scope bounded by a record, variant, or option type, whose values generic code
    holds viewed at the bound."""
    converted: tuple[Optional[str], ...]
    exact: bool = False
    shared: bool = False
    plan: Optional[Plan] = None
    layout_error: bool = False
    bound: Optional[QType] = None
    # Set by the describe pass: per component converted, the descriptors it converts from and to (None for the
    # others); a component mentioning the type component is converted from its stored type at the value's type
    # component (the inspect's witness)
    descriptors: tuple[Optional[tuple[Descriptor, Descriptor]], ...] = ()


@dataclass(eq=False)
class Inspect:
    """An inspect of a dynamic or auto value by its run-time type."""
    value: Atom
    cases: tuple[InspectCase, ...]
    else_body: Optional[Body] = None
    auto_type: Optional[QType] = None
    offset: Optional[int] = None
    # Set by the describe pass: the descriptor variable of the value's type component (its run-time type), bound for
    # the cases' arms, under the auto type's own symbol
    witness: Optional[DescriptorParam] = None


@dataclass(eq=False)
class Loop:
    """A loop: its body repeats, until a break of its label."""
    label: str
    body: Body


@dataclass(eq=False)
class Try:
    """A try region: a raise in `body`, or in what it calls, transfers to `handler`, with `exception` bound to the
    exception raised. `catches` says what the handler catches (docs/exceptions.md §5.1): the exceptions its patterns
    are (atoms bound before the try), or CATCH_ALL (it has an else branch), or None, if its patterns are computed in
    the handler."""
    body: Body
    exception: Var
    handler: Body
    catches: Union[None, str, tuple[Atom, ...]] = None


# A try whose handler catches every exception
CATCH_ALL = "all"


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
    # The descriptor the value is written by, when its type does not say how (after the describe pass)
    descriptor: Optional[Descriptor] = None


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
    Let, VarDecl, Assign, Store, Do, Funs, LetRec, If, Switch, Inspect, Loop, Try, Join, Echo, EchoText, Return,
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
    bound in its initializer after its members (a member itself where the types are the same). The initializer ends by
    making the module's record of them (`record`)."""
    name: str
    interface_name: str
    init: Body
    members: dict[str, Var]
    exports: Optional[dict[str, Var]] = None
    # The module's record (a record of its members, or of its exports), which its initializer makes last
    record: Optional[Var] = None
    # Set by the describe pass: its abstract types' registrations for dynamic values (docs/dynamic.md §2.3): each
    # one's global name, its arity, and the descriptor of its representation (a template whose holes are its
    # parameters, for an operator)
    abstract_types: tuple[tuple[str, int, StaticDescriptor], ...] = ()


@dataclass(eq=False)
class Import:
    """A module the unit uses from elsewhere: the name it is imported as, the module's path as imported and its
    canonical name (docs/modules.md §2.3), the path of the interface it is imported through, and the record type of
    that interface (its members, with their types as written; None if lowering did not know the interface), which
    the module's record value has."""
    name: str
    module_path: str
    canonical_path: str
    interface_path: str
    record_type: Optional[QType] = None


# The IR's stages (docs/ir.md §9), in order: each pass produces the next
STAGES = ("core", "specialized", "closed", "represented", "described")

# The fields of operations that hold descriptor operands (or tables), not atoms: traversals of atoms skip them, and the
# verifier checks them on their own
DESCRIPTOR_FIELDS = frozenset({"descriptor", "descriptors", "view_descriptor", "thunk_params", "offsets", "tag_map"})

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
    # After the describe pass, the static descriptors and tables its operations refer to
    static_data: Optional[StaticData] = None

    def at_least(self, stage: str) -> bool:
        """Whether the unit is at the given stage or a later one."""
        return STAGES.index(self.stage) >= STAGES.index(stage)
