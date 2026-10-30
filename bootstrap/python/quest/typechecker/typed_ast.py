"""Quest Typed Core Abstract Syntax Tree (Typed AST) Definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

from quest.types import (
    BOOL_TYPE,
    CHAR_TYPE,
    EXCEPTION_TYPE,
    INT_TYPE,
    OK_TYPE,
    QArrayType,
    QAutoType,
    QFunType,
    QKind,
    QOptionType,
    QRecordType,
    QTupleType,
    QType,
    QVarType,
    QVariantType,
    REAL_TYPE,
    STRING_TYPE,
    TYPE_KIND,
    format_type_compact,
    qtype_dump,
)
from quest.types.env import (
    KindSymbol,
    Scope,
    Symbol,
    TypeSymbol,
    ValueSymbol,
)


# ============================================================================
# 1. Base Typed Nodes
# ============================================================================

@dataclass(frozen=True)
class TypedNode:
    """Base class for all typed Quest AST nodes with unified S-expression
    formatting."""
    offset: int = field(default=0, kw_only=True)

    def dump_header(self, env: Optional[Any] = None) -> str:
        """Returns inline summary tokens (e.g. literal values, names)."""
        return ""

    def dump_children(self) -> list[tuple[str, Any]]:
        """Returns structured children as [(':label', child_or_sequence),
        ...]."""
        return []

    def dump_type(self) -> Optional[QType]:
        """The type appended to the header as :type, if any."""
        return None

    def dump(self, indent: int = 0, env: Optional[Any] = None) -> str:
        """Recursively formats this node into a canonical 2-space indented
        S-expression."""
        child_pad = "  " * (indent + 1)

        # 1. Construct header parts
        parts = [self.__class__.__name__]
        extra = self.dump_header(env=env)
        if extra:
            parts.append(extra)

        t_val = self.dump_type()
        if t_val is not None:
            parts.append(f":type {format_type_compact(t_val, env=env)}")

        header_str = " ".join(parts)
        children = self.dump_children()

        # 2. Leaf node: render compact single-line
        if not children:
            return f"({header_str})"

        # 3. Non-leaf node: format labeled children consistently
        lines = [f"({header_str}"]
        for label, child in children:
            match child:
                case TypedNode():
                    lines.append(f"{child_pad}{label} {child.dump(indent + 1, env=env)}")
                case tuple() | list():
                    if not child:
                        lines.append(f"{child_pad}{label} ()")
                    else:
                        lines.append(f"{child_pad}{label} (")
                        for elem in child:
                            if isinstance(elem, TypedNode):
                                lines.append(f"{child_pad}  {elem.dump(indent + 2, env=env)}")
                            else:
                                lines.append(f"{child_pad}  {elem}")
                        lines.append(f"{child_pad})")
                case None:
                    pass
                case _:
                    lines.append(f"{child_pad}{label} {child}")

        lines[-1] = lines[-1] + ")"
        return "\n".join(lines)


@dataclass(frozen=True)
class TypedExpr(TypedNode):
    """Base class for all typed value expressions."""

    def dump_type(self) -> Optional[QType]:
        # Every expression has its type (type_val)
        return self.type_val


@dataclass(frozen=True)
class TypedBinding(TypedNode):
    """Base class for declarations and statements inside blocks and programs."""
    def dump_type(self) -> Optional[QType]:
        return None


# ============================================================================
# 2. Literals and Variables
# ============================================================================

@dataclass(frozen=True)
class TypedInt(TypedExpr):
    value: int
    type_val: QType = INT_TYPE

    def dump_header(self, env: Optional[Any] = None) -> str:
        return repr(self.value)


@dataclass(frozen=True)
class TypedReal(TypedExpr):
    value: float
    type_val: QType = REAL_TYPE

    def dump_header(self, env: Optional[Any] = None) -> str:
        return repr(self.value)


@dataclass(frozen=True)
class TypedBool(TypedExpr):
    value: bool
    type_val: QType = BOOL_TYPE

    def dump_header(self, env: Optional[Any] = None) -> str:
        return "true" if self.value else "false"

    def dump_type(self) -> Optional[QType]:
        return None


@dataclass(frozen=True)
class TypedChar(TypedExpr):
    value: str
    type_val: QType = CHAR_TYPE

    def dump_header(self, env: Optional[Any] = None) -> str:
        return repr(self.value)


@dataclass(frozen=True)
class TypedString(TypedExpr):
    value: str
    type_val: QType = STRING_TYPE

    def dump_header(self, env: Optional[Any] = None) -> str:
        return repr(self.value)


@dataclass(frozen=True)
class TypedOk(TypedExpr):
    type_val: QType = OK_TYPE

    def dump_type(self) -> Optional[QType]:
        return None


@dataclass(frozen=True)
class TypedExternal(TypedExpr):
    """External C symbol reference: external "c_symbol"."""
    symbol: str
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.symbol}'"


@dataclass(frozen=True)
class TypedVar(TypedExpr):
    """Reference to a resolved value symbol."""
    name: str
    symbol: ValueSymbol
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.name}'"


# ============================================================================
# 3. Functions, Parameters, and Applications
# ============================================================================

@dataclass(frozen=True)
class TypedParam(TypedNode):
    """Resolved formal parameter to a function."""
    name: str
    symbol: ValueSymbol
    type_val: QType
    is_var: bool = False
    is_out: bool = False

    def dump_type(self) -> Optional[QType]:
        return self.type_val

    def dump_header(self, env: Optional[Any] = None) -> str:
        var_tag = " :var" if self.is_var else (" :out" if self.is_out else "")
        return f"'{self.name}'{var_tag}"


@dataclass(frozen=True)
class TypedFun(TypedExpr):
    """Function abstraction: fun(params): RetType Body."""
    params: tuple[TypedParam, ...]
    body: TypedExpr
    type_val: QFunType
    # Symbol ids of the function's type parameters as its body refers to them
    # (for a polymorphic function checked against an expected type, these differ
    # from the expected type's quantifiers), bound at run time by type
    # applications
    type_param_ids: tuple[int, ...] = ()
    # Whether its type parameters are its only parameters, as in fun(A::TYPE)
    # e, whose application to types computes e. A function of type parameters
    # then value parameters, even none, as in fun(A::TYPE)() e, can have the
    # same type, but its application to types is a function.
    type_only: bool = False

    def dump_header(self, env: Optional[Any] = None) -> str:
        params_str = " ".join(
            f"('{p.name}' : {format_type_compact(p.type_val, env=env)})"
            for p in self.params
        )
        return f":params ({params_str})"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":body", self.body)]


@dataclass(frozen=True)
class TypedApp(TypedExpr):
    """Function application: func(arg1, ..., argN)."""
    func: TypedExpr
    args: tuple[TypedExpr, ...]
    type_val: QType

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":func", self.func), (":args", self.args)]


@dataclass(frozen=True)
class TypedTypeApp(TypedExpr):
    """Explicit polymorphic type instantiation: func[T1, ..., Tn]."""
    func: TypedExpr
    type_args: tuple[QType, ...]
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        targs_str = " ".join(format_type_compact(t, env=env) for t in self.type_args)
        return f"[{targs_str}]"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":func", self.func)]


@dataclass(frozen=True)
class TypedInfix(TypedExpr):
    """Binary infix operation: left op right."""
    left: TypedExpr
    op: str
    right: TypedExpr
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        return repr(self.op)

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":left", self.left), (":right", self.right)]


# ============================================================================
# 4. Aggregates and Projections
# ============================================================================

@dataclass(frozen=True)
class TypedRecordField(TypedNode):
    """A single evaluated field in a record value."""
    name: str
    value: TypedExpr
    is_var: bool = False

    def dump_header(self, env: Optional[Any] = None) -> str:
        var_tag = " :var" if self.is_var else ""
        return f"'{self.name}'{var_tag}"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":value", self.value)]


@dataclass(frozen=True)
class TypedRecord(TypedExpr):
    """Record value construction: record x = e1, y = e2 end."""
    fields: tuple[TypedRecordField, ...]
    type_val: QRecordType

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":fields", self.fields)]


@dataclass(frozen=True)
class TypedTypeWitness(TypedExpr):
    """Witness type element in an existential tuple: Let A::K = T."""
    name: str
    witness_type: QType
    bound: Optional[Any] = None
    type_val: QType = field(default_factory=lambda: TYPE_KIND)

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.name}' = {self.witness_type}"

    def dump_type(self) -> Optional[QType]:
        return None


@dataclass(frozen=True)
class TypedTuple(TypedExpr):
    """Tuple value construction: tuple e1, e2 end.

    Components declared together are listed as groups of indices into elements:
    mutually recursive ones (let rec, alone or joined by and), whose closures
    may refer to one another, and simultaneous ones (let ... and ...), whose
    values are all computed before any of their labels is bound. A labeled
    component's label is a variable of the components after it (and, in a
    recursive group, of the group's members), bound by its symbol in labels.
    """
    elements: tuple[TypedExpr, ...]
    type_val: QTupleType
    rec_groups: tuple[tuple[int, ...], ...] = ()
    simultaneous_groups: tuple[tuple[int, ...], ...] = ()
    # The symbol each element's label binds for the later elements (None for an
    # unlabeled one, or a type component)
    labels: tuple[Optional[ValueSymbol], ...] = ()

    def dump_header(self, env: Optional[Any] = None) -> str:
        parts = [f":rec {list(group)}" for group in self.rec_groups]
        parts += [f":and {list(group)}" for group in self.simultaneous_groups]
        return " ".join(parts)

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":elements", self.elements)]


@dataclass(frozen=True)
class TypedSelect(TypedExpr):
    """Field selection: target.field."""
    target: TypedExpr
    field: str
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.field}'"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":target", self.target)]


@dataclass(frozen=True)
class TypedIndex(TypedExpr):
    """Array indexing: target[index]."""
    target: TypedExpr
    index: TypedExpr
    type_val: QType

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":target", self.target), (":index", self.index)]


@dataclass(frozen=True)
class TypedIndexAssign(TypedExpr):
    """Array element assignment: target[index] := value."""
    target: TypedExpr
    index: TypedExpr
    value: TypedExpr
    type_val: QType = OK_TYPE

    def dump_type(self) -> Optional[QType]:
        return None

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":target", self.target), (":index", self.index), (":value", self.value)]


@dataclass(frozen=True)
class TypedArray(TypedExpr):
    """Explicit array construction: array [e1, e2, ...]."""
    elements: tuple[TypedExpr, ...]
    type_val: QArrayType

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":elements", self.elements)]


@dataclass(frozen=True)
class TypedArrayRep(TypedExpr):
    """Array repetition: array of count elements init_val."""
    count: TypedExpr
    init_val: TypedExpr
    type_val: QArrayType

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":count", self.count), (":init", self.init_val)]


# ============================================================================
# 5. Mutable References and Assignment
# ============================================================================

@dataclass(frozen=True)
class TypedVarCell(TypedExpr):
    """Reference cell allocation: var(initial_value)."""
    value: TypedExpr
    type_val: QVarType

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":value", self.value)]


@dataclass(frozen=True)
class TypedDerefCell(TypedExpr):
    """Explicit or implicit reference dereference."""
    target: TypedExpr
    type_val: QType

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":target", self.target)]


@dataclass(frozen=True)
class TypedSelectRef(TypedExpr):
    """Reference to a mutable record field (for var/out arguments): @r.f."""
    target: TypedExpr
    field: str
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f".{self.field} (ref)"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":target", self.target)]


@dataclass(frozen=True)
class TypedIndexRef(TypedExpr):
    """Reference to an array element location (for var/out arguments): @a[i]."""
    target: TypedExpr
    index: TypedExpr
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        return "[] (ref)"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":target", self.target), (":index", self.index)]


@dataclass(frozen=True)
class TypedTupleSelectRef(TypedExpr):
    """Reference to a mutable tuple field/element (for var/out arguments): @t.f
    or @t.1."""
    target: TypedExpr
    index: int
    field: Optional[str]
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        fld_desc = f".{self.field}" if self.field else f"._{self.index}"
        return f"{fld_desc} (ref)"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":target", self.target)]


@dataclass(frozen=True)
class TypedAssign(TypedExpr):
    """Assignment to mutable reference or record field: target := value."""
    target: TypedExpr
    value: TypedExpr
    type_val: QType = OK_TYPE

    def dump_type(self) -> Optional[QType]:
        return None

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":target", self.target), (":value", self.value)]


# ============================================================================
# 6. Variants, Options, and Pattern Matching
# ============================================================================

@dataclass(frozen=True)
class TypedVariant(TypedExpr):
    """Variant injection: variant tag = value end."""
    tag: str
    type_val: QVariantType
    payload: Optional[TypedExpr] = None

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.tag}'"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":payload", self.payload)] if self.payload else []


@dataclass(frozen=True)
class TypedOption(TypedExpr):
    """Option injection: option tag or ordinal with value end."""
    tag: Optional[str]
    type_val: QOptionType
    payload: Optional[TypedExpr] = None
    ordinal_expr: Optional[TypedExpr] = None

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.tag}'" if self.tag is not None else "ordinal"

    def dump_children(self) -> list[tuple[str, Any]]:
        res: list[tuple[str, Any]] = []
        if self.ordinal_expr is not None:
            res.append((":ordinal", self.ordinal_expr))
        if self.payload is not None:
            res.append((":payload", self.payload))
        return res


@dataclass(frozen=True)
class TypedAuto(TypedExpr):
    """Auto value: auto :W with Binding end, packaging the payload with its type
    component W."""
    witness_type: QType
    auto_type: QAutoType
    payload: TypedExpr
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f":{self.witness_type}"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":payload", self.payload)]


@dataclass(frozen=True)
class TypedVariantCheck(TypedExpr):
    """Variant/Option tag check: target?tag."""
    target: TypedExpr
    tag: str
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.tag}'"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":target", self.target)]


@dataclass(frozen=True)
class TypedVariantAssert(TypedExpr):
    """Variant/Option tag assertion/extraction: target!tag."""
    target: TypedExpr
    tag: str
    type_val: QType

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.tag}'"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":target", self.target)]


@dataclass(frozen=True)
class TypedCaseBranch(TypedNode):
    """A branch in a case discrimination: when tag1, tag2 => body."""
    tags: tuple[str, ...]
    body: TypedExpr
    binder: Optional[ValueSymbol] = None

    def dump_header(self, env: Optional[Any] = None) -> str:
        binder_str = f" :binder '{self.binder.name}'" if self.binder else ""
        return f"tags=({', '.join(self.tags)}){binder_str}"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":body", self.body)]


@dataclass(frozen=True)
class TypedCase(TypedExpr):
    """Case discrimination on variants or options."""
    target: TypedExpr
    branches: tuple[TypedCaseBranch, ...]
    type_val: QType
    else_branch: Optional[TypedExpr] = None

    def dump_children(self) -> list[tuple[str, Any]]:
        children: list[tuple[str, Any]] = [(":target", self.target), (":branches", self.branches)]
        if self.else_branch:
            children.append((":else", self.else_branch))
        return children


@dataclass(frozen=True)
class TypedInspectBranch(TypedNode):
    """A branch in a dynamic type inspection: when Type => body.

    The branch is selected when the inspected type is a subtype of match_type,
    or, if exact, equal to it.
    """
    match_type: QType
    binders: tuple[ValueSymbol, ...]
    body: TypedExpr
    exact: bool = False

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"match={self.match_type}" + (" exact" if self.exact else "")

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":body", self.body)]


@dataclass(frozen=True)
class TypedInspect(TypedExpr):
    """Type inspection (inspect target ...) of a Dynamic or, when auto_type is
    set, an auto value."""
    target: TypedExpr
    branches: tuple[TypedInspectBranch, ...]
    type_val: QType
    else_branch: Optional[TypedExpr] = None
    auto_type: Optional[QAutoType] = None

    def dump_children(self) -> list[tuple[str, Any]]:
        children: list[tuple[str, Any]] = [(":target", self.target), (":branches", self.branches)]
        if self.else_branch:
            children.append((":else", self.else_branch))
        return children


# ============================================================================
# 7. Control Flow and Blocks
# ============================================================================

@dataclass(frozen=True)
class TypedBlock(TypedExpr):
    """Block expression: begin bindings... result end."""
    bindings: tuple[TypedBinding, ...]
    result: TypedExpr
    type_val: QType

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":bindings", self.bindings), (":result", self.result)]


@dataclass(frozen=True)
class TypedIf(TypedExpr):
    """Conditional expression: if cond then e1 else e2 end."""
    cond: TypedExpr
    then_branch: TypedExpr
    else_branch: TypedExpr
    type_val: QType

    def dump_children(self) -> list[tuple[str, Any]]:
        return [
            (":cond", self.cond),
            (":then", self.then_branch),
            (":else", self.else_branch),
        ]


@dataclass(frozen=True)
class TypedWhile(TypedExpr):
    """While loop: while cond do body end."""
    cond: TypedExpr
    body: TypedExpr
    type_val: QType = OK_TYPE

    def dump_type(self) -> Optional[QType]:
        return None

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":cond", self.cond), (":body", self.body)]


@dataclass(frozen=True)
class TypedLoop(TypedExpr):
    """Infinite loop: loop body end."""
    body: TypedExpr
    type_val: QType = OK_TYPE

    def dump_type(self) -> Optional[QType]:
        return None

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":body", self.body)]


@dataclass(frozen=True)
class TypedFor(TypedExpr):
    """For loop: for var_name = start [downto] stop do body end."""
    var_name: str
    symbol: ValueSymbol
    start: TypedExpr
    is_downto: bool
    stop: TypedExpr
    body: TypedExpr
    type_val: QType = OK_TYPE

    def dump_type(self) -> Optional[QType]:
        return None

    def dump_header(self, env: Optional[Any] = None) -> str:
        dir_tag = " :downto" if self.is_downto else " :upto"
        return f"'{self.var_name}'{dir_tag}"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":start", self.start), (":stop", self.stop), (":body", self.body)]


@dataclass(frozen=True)
class TypedExit(TypedExpr):
    """Exit statement exiting the innermost loop."""
    type_val: QType = OK_TYPE

    def dump_type(self) -> Optional[QType]:
        return None


# ============================================================================
# 8. Exceptions
# ============================================================================

@dataclass(frozen=True)
class TypedException(TypedExpr):
    """Exception value constructor: exception name [: Type] end. It also binds
    the name (symbol) to the exception, in the scope where it appears."""
    name: str
    payload_type: Optional[QType] = None
    type_val: QType = EXCEPTION_TYPE
    symbol: Optional[ValueSymbol] = None

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.name}'"


@dataclass(frozen=True)
class TypedRaise(TypedExpr):
    """Raise statement: raise exc [with payload]."""
    exc: TypedExpr
    type_val: QType
    payload: Optional[TypedExpr] = None

    def dump_children(self) -> list[tuple[str, Any]]:
        children: list[tuple[str, Any]] = [(":exc", self.exc)]
        if self.payload:
            children.append((":payload", self.payload))
        return children


@dataclass(frozen=True)
class TypedTryBranch(TypedNode):
    """Catch branch in a try block."""
    exc_pattern: TypedExpr
    body: TypedExpr
    binder: Optional[ValueSymbol] = None

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":exc_pattern", self.exc_pattern), (":body", self.body)]


@dataclass(frozen=True)
class TypedTry(TypedExpr):
    """Try-with exception handler."""
    body: TypedExpr
    branches: tuple[TypedTryBranch, ...]
    type_val: QType
    else_branch: Optional[TypedExpr] = None
    # The else branch's binder, of type raised.T (docs/raised.md)
    else_binder: Optional[ValueSymbol] = None

    def dump_children(self) -> list[tuple[str, Any]]:
        children: list[tuple[str, Any]] = [(":body", self.body), (":branches", self.branches)]
        if self.else_branch:
            children.append((":else", self.else_branch))
        return children


# ============================================================================
# 9. Declarations and Program Structure
# ============================================================================

@dataclass(frozen=True)
class TypedLetValue(TypedBinding):
    """Value let declaration: let [rec] [var] x = expr."""
    name: str
    value: TypedExpr
    symbol: ValueSymbol
    is_rec: bool = False

    def dump_header(self, env: Optional[Any] = None) -> str:
        rec_tag = " :rec" if self.is_rec else ""
        return f"'{self.name}'{rec_tag} :type {format_type_compact(self.symbol.type_val, env=env)}"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":value", self.value)]


@dataclass(frozen=True)
class TypedLetValueGroup(TypedBinding):
    """Simultaneous value declarations: let [rec] x = expr and y = expr ...

    With rec (each member's is_rec), the members are mutually recursive; without
    it, every member's value is computed before any member is bound.
    """
    members: tuple[TypedLetValue, ...]

    @property
    def is_rec(self) -> bool:
        return self.members[0].is_rec

    def dump_header(self, env: Optional[Any] = None) -> str:
        return " ".join(f"'{member.name}'" for member in self.members)

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":members", self.members)]


def binding_members(binding: Any) -> tuple[Any, ...]:
    """The bindings a binding declares: the members of a group of value
    declarations, or the binding itself."""
    return binding.members if isinstance(binding, TypedLetValueGroup) else (binding,)


def declared_name(binding: Any) -> Optional[str]:
    """The name a binding declares by itself, if it declares one (not a group's,
    a statement's, or an import's)."""
    match binding:
        case TypedLetValue(name=name) | TypedLetType(name=name) | TypedDefKind(name=name) | TypedInterface(name=name) | \
                TypedModule(name=name):
            return name
    return None


@dataclass(frozen=True)
class TypedLetType(TypedBinding):
    """Type let declaration: Let T = Type."""
    name: str
    symbol: TypeSymbol

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.name}' :kind {self.symbol.kind}"


@dataclass(frozen=True)
class TypedLetTypeGroup(TypedBinding):
    """Simultaneous type declarations: Let [Rec] T1 = Type and T2 = Type ..."""
    members: tuple[TypedLetType, ...]

    def dump_header(self, env: Optional[Any] = None) -> str:
        return " ".join(f"'{member.name}'" for member in self.members)

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":members", self.members)]


@dataclass(frozen=True)
class TypedDefKind(TypedBinding):
    """Kind definition: DEF K = Kind."""
    name: str
    symbol: KindSymbol

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.name}' :kind {self.symbol.kind}"


@dataclass(frozen=True)
class TypedExprStmt(TypedBinding):
    """Standalone expression statement."""
    expr: TypedExpr

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":expr", self.expr)]


@dataclass(frozen=True)
class TypedInterface(TypedBinding):
    """Interface declaration."""
    name: str
    signatures: tuple[TypedBinding, ...]
    scope: Scope

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.name}'"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":signatures", self.signatures)]


@dataclass(frozen=True)
class TypedModule(TypedBinding):
    """Module implementation conforming to an interface. `symbol_id` identifies
    the value symbol its name binds, which uses of the module refer to (an id
    rather than the symbol, whose record type the C backend's walkers of the
    typed AST would otherwise visit)."""
    name: str
    interface_name: str
    bindings: tuple[TypedBinding, ...]
    scope: Scope
    c_init: Optional[str] = None
    is_precompiled: bool = False
    symbol_id: Optional[int] = field(default=None, compare=False)

    def dump_header(self, env: Optional[Any] = None) -> str:
        return f"'{self.name}' implements '{self.interface_name}'"

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":bindings", self.bindings)]


@dataclass(frozen=True)
class TypedImportItem(TypedNode):
    names: tuple[str, ...]
    interface_name: str
    module_paths: Optional[tuple[str, ...]] = None
    interface_path: Optional[str] = None
    # The canonical names of the imported modules (docs/modules.md §2.3), which
    # name them in C symbols; None where they are the module paths as written.
    canonical_module_paths: Optional[tuple[str, ...]] = None
    # The ids of the value symbols the names bind to the modules, which uses of
    # the modules refer to (None for a name that imports a type, value, or kind
    # of the interface rather than a module). Not compared: the same import
    # elaborated twice is the same import
    symbol_ids: Optional[tuple[Optional[int], ...]] = field(default=None, compare=False)

    @property
    def effective_module_paths(self) -> tuple[str, ...]:
        return self.module_paths if self.module_paths is not None else self.names

    @property
    def effective_interface_path(self) -> str:
        return self.interface_path if self.interface_path is not None else self.interface_name

    @property
    def effective_canonical_module_paths(self) -> tuple[str, ...]:
        if self.canonical_module_paths is not None:
            return self.canonical_module_paths
        return self.effective_module_paths

    def dump_header(self, env: Optional[Any] = None) -> str:
        if self.names:
            return f"({' '.join(repr(n) for n in self.names)}) : '{self.interface_name}'"
        return f": '{self.interface_name}'"



@dataclass(frozen=True)
class TypedImport(TypedBinding):
    """Import statement importing interfaces and modules."""
    items: tuple[TypedImportItem, ...]

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":items", self.items)]


@dataclass(frozen=True)
class TypedProgram(TypedNode):
    """Top-level typed program AST."""
    phrases: tuple[Union[TypedBinding, TypedExpr], ...]

    def dump_children(self) -> list[tuple[str, Any]]:
        return [(":phrases", self.phrases)]


# ============================================================================
# 10. Canonical S-Expression Pretty Printer (typed_ast_dump)
# ============================================================================

def named_exceptions_in(node: Any) -> list[TypedException]:
    """The named exceptions made in node whose names bind in node's scope: not
    inside functions or blocks, which are scopes of their own."""
    found: list[TypedException] = []

    def scan(n: Any) -> None:
        if n is None or isinstance(n, (QType, str, int, float, bool, TypedFun, TypedBlock, Symbol)):
            return
        if isinstance(n, TypedException):
            if n.name:
                found.append(n)
            return
        if isinstance(n, (list, tuple)):
            for item in n:
                scan(item)
        else:
            for part in typed_fields(n) or ():
                scan(part)

    scan(node)
    return found


def scope_exceptions(node: Any) -> list[TypedException]:
    """The named exceptions that a binding, a phrase, or a function's body makes
    for its scope before it runs, so that each one exists throughout the scope
    whether or not the expression that makes it runs (docs/type-system.md
    §6.14): those named_exceptions_in finds, except the exception node is itself
    or binds directly, which it makes as it runs."""
    direct = node.expr if isinstance(node, TypedExprStmt) else node.value if isinstance(node, TypedLetValue) else node
    return [exc for exc in named_exceptions_in(node) if exc is not direct and exc.symbol is not None]


def typed_ast_dump(node: TypedNode, indent: int = 0, env: Optional[Any] = None) -> str:
    """Formats a TypedNode into a canonical 2-space indented S-expression
    string."""
    return node.dump(indent, env=env)


# The explicit traversal: a case for each class of typed node

def typed_fields(node) -> Optional[tuple]:
    """The values of a typed node's fields (but its offset), in order; None for
    a value that is not a typed node. The typed AST's one traversal: every
    walker of nodes' fields reads them through it."""
    accessor = _TYPED_FIELDS.get(type(node))
    return accessor(node) if accessor is not None else None


def rebuild_typed(node, values: tuple):
    """A typed node of node's class, at its offset, whose fields are values (as
    typed_fields gives them)."""
    return _REBUILD_TYPED[type(node)](node, values)


# The entries of the traversal, a case for each class

_TYPED_FIELDS: dict[type, Callable[[Any], tuple]] = {
    TypedInt: lambda node: (node.value, node.type_val),
    TypedReal: lambda node: (node.value, node.type_val),
    TypedBool: lambda node: (node.value, node.type_val),
    TypedChar: lambda node: (node.value, node.type_val),
    TypedString: lambda node: (node.value, node.type_val),
    TypedOk: lambda node: (node.type_val,),
    TypedExternal: lambda node: (node.symbol, node.type_val),
    TypedVar: lambda node: (node.name, node.symbol, node.type_val),
    TypedParam: lambda node: (node.name, node.symbol, node.type_val, node.is_var, node.is_out),
    TypedFun: lambda node: (node.params, node.body, node.type_val, node.type_param_ids, node.type_only),
    TypedApp: lambda node: (node.func, node.args, node.type_val),
    TypedTypeApp: lambda node: (node.func, node.type_args, node.type_val),
    TypedInfix: lambda node: (node.left, node.op, node.right, node.type_val),
    TypedRecordField: lambda node: (node.name, node.value, node.is_var),
    TypedRecord: lambda node: (node.fields, node.type_val),
    TypedTypeWitness: lambda node: (node.name, node.witness_type, node.bound, node.type_val),
    TypedTuple: lambda node: (node.elements, node.type_val, node.rec_groups, node.simultaneous_groups, node.labels),
    TypedSelect: lambda node: (node.target, node.field, node.type_val),
    TypedIndex: lambda node: (node.target, node.index, node.type_val),
    TypedIndexAssign: lambda node: (node.target, node.index, node.value, node.type_val),
    TypedArray: lambda node: (node.elements, node.type_val),
    TypedArrayRep: lambda node: (node.count, node.init_val, node.type_val),
    TypedVarCell: lambda node: (node.value, node.type_val),
    TypedDerefCell: lambda node: (node.target, node.type_val),
    TypedSelectRef: lambda node: (node.target, node.field, node.type_val),
    TypedIndexRef: lambda node: (node.target, node.index, node.type_val),
    TypedTupleSelectRef: lambda node: (node.target, node.index, node.field, node.type_val),
    TypedAssign: lambda node: (node.target, node.value, node.type_val),
    TypedVariant: lambda node: (node.tag, node.type_val, node.payload),
    TypedOption: lambda node: (node.tag, node.type_val, node.payload, node.ordinal_expr),
    TypedAuto: lambda node: (node.witness_type, node.auto_type, node.payload, node.type_val),
    TypedVariantCheck: lambda node: (node.target, node.tag, node.type_val),
    TypedVariantAssert: lambda node: (node.target, node.tag, node.type_val),
    TypedCaseBranch: lambda node: (node.tags, node.body, node.binder),
    TypedCase: lambda node: (node.target, node.branches, node.type_val, node.else_branch),
    TypedInspectBranch: lambda node: (node.match_type, node.binders, node.body, node.exact),
    TypedInspect: lambda node: (node.target, node.branches, node.type_val, node.else_branch, node.auto_type),
    TypedBlock: lambda node: (node.bindings, node.result, node.type_val),
    TypedIf: lambda node: (node.cond, node.then_branch, node.else_branch, node.type_val),
    TypedWhile: lambda node: (node.cond, node.body, node.type_val),
    TypedLoop: lambda node: (node.body, node.type_val),
    TypedFor: lambda node: (
        node.var_name, node.symbol, node.start, node.is_downto, node.stop, node.body, node.type_val,
    ),
    TypedExit: lambda node: (node.type_val,),
    TypedException: lambda node: (node.name, node.payload_type, node.type_val, node.symbol),
    TypedRaise: lambda node: (node.exc, node.type_val, node.payload),
    TypedTryBranch: lambda node: (node.exc_pattern, node.body, node.binder),
    TypedTry: lambda node: (node.body, node.branches, node.type_val, node.else_branch, node.else_binder),
    TypedLetValue: lambda node: (node.name, node.value, node.symbol, node.is_rec),
    TypedLetValueGroup: lambda node: (node.members,),
    TypedLetType: lambda node: (node.name, node.symbol),
    TypedLetTypeGroup: lambda node: (node.members,),
    TypedDefKind: lambda node: (node.name, node.symbol),
    TypedExprStmt: lambda node: (node.expr,),
    TypedInterface: lambda node: (node.name, node.signatures, node.scope),
    TypedModule: lambda node: (
        node.name, node.interface_name, node.bindings, node.scope, node.c_init, node.is_precompiled, node.symbol_id,
    ),
    TypedImportItem: lambda node: (
        node.names, node.interface_name, node.module_paths, node.interface_path, node.canonical_module_paths,
        node.symbol_ids,
    ),
    TypedImport: lambda node: (node.items,),
    TypedProgram: lambda node: (node.phrases,),
}

_REBUILD_TYPED: dict[type, Callable[[Any, tuple], Any]] = {
    TypedInt: lambda node, values: TypedInt(offset=node.offset, value=values[0], type_val=values[1]),
    TypedReal: lambda node, values: TypedReal(offset=node.offset, value=values[0], type_val=values[1]),
    TypedBool: lambda node, values: TypedBool(offset=node.offset, value=values[0], type_val=values[1]),
    TypedChar: lambda node, values: TypedChar(offset=node.offset, value=values[0], type_val=values[1]),
    TypedString: lambda node, values: TypedString(offset=node.offset, value=values[0], type_val=values[1]),
    TypedOk: lambda node, values: TypedOk(offset=node.offset, type_val=values[0]),
    TypedExternal: lambda node, values: TypedExternal(offset=node.offset, symbol=values[0], type_val=values[1]),
    TypedVar: lambda node, values: TypedVar(offset=node.offset, name=values[0], symbol=values[1], type_val=values[2]),
    TypedParam: lambda node, values: TypedParam(
        offset=node.offset, name=values[0], symbol=values[1], type_val=values[2], is_var=values[3], is_out=values[4],
    ),
    TypedFun: lambda node, values: TypedFun(
        offset=node.offset, params=values[0], body=values[1], type_val=values[2], type_param_ids=values[3],
        type_only=values[4],
    ),
    TypedApp: lambda node, values: TypedApp(offset=node.offset, func=values[0], args=values[1], type_val=values[2]),
    TypedTypeApp: lambda node, values: TypedTypeApp(
        offset=node.offset, func=values[0], type_args=values[1], type_val=values[2],
    ),
    TypedInfix: lambda node, values: TypedInfix(
        offset=node.offset, left=values[0], op=values[1], right=values[2], type_val=values[3],
    ),
    TypedRecordField: lambda node, values: TypedRecordField(
        offset=node.offset, name=values[0], value=values[1], is_var=values[2],
    ),
    TypedRecord: lambda node, values: TypedRecord(offset=node.offset, fields=values[0], type_val=values[1]),
    TypedTypeWitness: lambda node, values: TypedTypeWitness(
        offset=node.offset, name=values[0], witness_type=values[1], bound=values[2], type_val=values[3],
    ),
    TypedTuple: lambda node, values: TypedTuple(
        offset=node.offset, elements=values[0], type_val=values[1], rec_groups=values[2], simultaneous_groups=values[3],
        labels=values[4],
    ),
    TypedSelect: lambda node, values: TypedSelect(
        offset=node.offset, target=values[0], field=values[1], type_val=values[2],
    ),
    TypedIndex: lambda node, values: TypedIndex(
        offset=node.offset, target=values[0], index=values[1], type_val=values[2],
    ),
    TypedIndexAssign: lambda node, values: TypedIndexAssign(
        offset=node.offset, target=values[0], index=values[1], value=values[2], type_val=values[3],
    ),
    TypedArray: lambda node, values: TypedArray(offset=node.offset, elements=values[0], type_val=values[1]),
    TypedArrayRep: lambda node, values: TypedArrayRep(
        offset=node.offset, count=values[0], init_val=values[1], type_val=values[2],
    ),
    TypedVarCell: lambda node, values: TypedVarCell(offset=node.offset, value=values[0], type_val=values[1]),
    TypedDerefCell: lambda node, values: TypedDerefCell(offset=node.offset, target=values[0], type_val=values[1]),
    TypedSelectRef: lambda node, values: TypedSelectRef(
        offset=node.offset, target=values[0], field=values[1], type_val=values[2],
    ),
    TypedIndexRef: lambda node, values: TypedIndexRef(
        offset=node.offset, target=values[0], index=values[1], type_val=values[2],
    ),
    TypedTupleSelectRef: lambda node, values: TypedTupleSelectRef(
        offset=node.offset, target=values[0], index=values[1], field=values[2], type_val=values[3],
    ),
    TypedAssign: lambda node, values: TypedAssign(
        offset=node.offset, target=values[0], value=values[1], type_val=values[2],
    ),
    TypedVariant: lambda node, values: TypedVariant(
        offset=node.offset, tag=values[0], type_val=values[1], payload=values[2],
    ),
    TypedOption: lambda node, values: TypedOption(
        offset=node.offset, tag=values[0], type_val=values[1], payload=values[2], ordinal_expr=values[3],
    ),
    TypedAuto: lambda node, values: TypedAuto(
        offset=node.offset, witness_type=values[0], auto_type=values[1], payload=values[2], type_val=values[3],
    ),
    TypedVariantCheck: lambda node, values: TypedVariantCheck(
        offset=node.offset, target=values[0], tag=values[1], type_val=values[2],
    ),
    TypedVariantAssert: lambda node, values: TypedVariantAssert(
        offset=node.offset, target=values[0], tag=values[1], type_val=values[2],
    ),
    TypedCaseBranch: lambda node, values: TypedCaseBranch(
        offset=node.offset, tags=values[0], body=values[1], binder=values[2],
    ),
    TypedCase: lambda node, values: TypedCase(
        offset=node.offset, target=values[0], branches=values[1], type_val=values[2], else_branch=values[3],
    ),
    TypedInspectBranch: lambda node, values: TypedInspectBranch(
        offset=node.offset, match_type=values[0], binders=values[1], body=values[2], exact=values[3],
    ),
    TypedInspect: lambda node, values: TypedInspect(
        offset=node.offset, target=values[0], branches=values[1], type_val=values[2], else_branch=values[3],
        auto_type=values[4],
    ),
    TypedBlock: lambda node, values: TypedBlock(
        offset=node.offset, bindings=values[0], result=values[1], type_val=values[2],
    ),
    TypedIf: lambda node, values: TypedIf(
        offset=node.offset, cond=values[0], then_branch=values[1], else_branch=values[2], type_val=values[3],
    ),
    TypedWhile: lambda node, values: TypedWhile(offset=node.offset, cond=values[0], body=values[1], type_val=values[2]),
    TypedLoop: lambda node, values: TypedLoop(offset=node.offset, body=values[0], type_val=values[1]),
    TypedFor: lambda node, values: TypedFor(
        offset=node.offset, var_name=values[0], symbol=values[1], start=values[2], is_downto=values[3], stop=values[4],
        body=values[5], type_val=values[6],
    ),
    TypedExit: lambda node, values: TypedExit(offset=node.offset, type_val=values[0]),
    TypedException: lambda node, values: TypedException(
        offset=node.offset, name=values[0], payload_type=values[1], type_val=values[2], symbol=values[3],
    ),
    TypedRaise: lambda node, values: TypedRaise(
        offset=node.offset, exc=values[0], type_val=values[1], payload=values[2],
    ),
    TypedTryBranch: lambda node, values: TypedTryBranch(
        offset=node.offset, exc_pattern=values[0], body=values[1], binder=values[2],
    ),
    TypedTry: lambda node, values: TypedTry(
        offset=node.offset, body=values[0], branches=values[1], type_val=values[2], else_branch=values[3],
        else_binder=values[4],
    ),
    TypedLetValue: lambda node, values: TypedLetValue(
        offset=node.offset, name=values[0], value=values[1], symbol=values[2], is_rec=values[3],
    ),
    TypedLetValueGroup: lambda node, values: TypedLetValueGroup(offset=node.offset, members=values[0]),
    TypedLetType: lambda node, values: TypedLetType(offset=node.offset, name=values[0], symbol=values[1]),
    TypedLetTypeGroup: lambda node, values: TypedLetTypeGroup(offset=node.offset, members=values[0]),
    TypedDefKind: lambda node, values: TypedDefKind(offset=node.offset, name=values[0], symbol=values[1]),
    TypedExprStmt: lambda node, values: TypedExprStmt(offset=node.offset, expr=values[0]),
    TypedInterface: lambda node, values: TypedInterface(
        offset=node.offset, name=values[0], signatures=values[1], scope=values[2],
    ),
    TypedModule: lambda node, values: TypedModule(
        offset=node.offset, name=values[0], interface_name=values[1], bindings=values[2], scope=values[3],
        c_init=values[4], is_precompiled=values[5], symbol_id=values[6],
    ),
    TypedImportItem: lambda node, values: TypedImportItem(
        offset=node.offset, names=values[0], interface_name=values[1], module_paths=values[2], interface_path=values[3],
        canonical_module_paths=values[4], symbol_ids=values[5],
    ),
    TypedImport: lambda node, values: TypedImport(offset=node.offset, items=values[0]),
    TypedProgram: lambda node, values: TypedProgram(offset=node.offset, phrases=values[0]),
}
