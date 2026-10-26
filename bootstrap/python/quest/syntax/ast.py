"""Quest Abstract Syntax Tree (AST) definitions and S-Expression
Pretty-Printer."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, KW_ONLY
from enum import Enum, auto
from typing import Any, Callable, Optional, Union


# ============================================================================
# 1. Base Node and Parameter Modes
# ============================================================================

@dataclass(frozen=True)
class ASTNode:
    """Root base class for all Quest AST nodes."""
    _: KW_ONLY
    offset: int = 0


class ParamMode(Enum):
    VALUE = auto()
    VAR = auto()
    OUT = auto()


@dataclass(frozen=True)
class FormalParam(ASTNode):
    """Value-level function parameter: [var | out] x : T"""
    name: str
    type_annot: Optional[Type] = None
    mode: ParamMode = ParamMode.VALUE


@dataclass(frozen=True)
class TypeFormal(ASTNode):
    """Type-level parameter: X <: B or X :: K"""
    name: str
    bound: Kind


@dataclass(frozen=True)
class Quantifier(ASTNode):
    """Universal/existential quantifier: X <: B or X :: K or [var/out] x: T"""
    name: str
    bound: Kind
    mode: ParamMode = ParamMode.VALUE
    is_type: bool = False


# ============================================================================
# 2. Level 2: Kinds
# ============================================================================

@dataclass(frozen=True)
class Kind(ASTNode):
    """Base class for Level 2 kind terms."""
    pass


@dataclass(frozen=True)
class KindType(Kind):
    """TYPE — the base kind of all ground types."""
    pass


@dataclass(frozen=True)
class KindPower(Kind):
    """POWER(T) — the kind of all subtypes of type T."""
    bound: Type


@dataclass(frozen=True)
class KindAll(Kind):
    """ALL(X::K) K' — operator kind universal quantifier."""
    param_name: str
    param_kind: Kind
    body_kind: Kind


@dataclass(frozen=True)
class KindId(Kind):
    """User-defined or aliased kind identifier."""
    name: str


@dataclass(frozen=True)
class KindManifest(Kind):
    """Interface manifest kind path, e.g. I_K."""
    interface_name: str
    kind_name: str


# ============================================================================
# 3. Level 1: Types and Type Operators
# ============================================================================

@dataclass(frozen=True)
class Type(ASTNode):
    """Base class for Level 1 type terms and type operators."""
    pass


@dataclass(frozen=True)
class TypePath(Type):
    """Named type or dot-projection path: e.g. 'Int', 'Point', 'Mod.T'."""
    path: tuple[str, ...]


@dataclass(frozen=True)
class TypeAll(Type):
    """All(X <: B, Y :: K) T — universal type quantifier."""
    quantifiers: tuple[Quantifier, ...]
    result_type: Type


@dataclass(frozen=True)
class FieldSig(ASTNode):
    """Field in a tuple or auto signature: [var | out] x : T"""
    name: Optional[str] = None
    type_sig: Optional[Type] = None
    mode: ParamMode = ParamMode.VALUE


@dataclass(frozen=True)
class TypeTuple(Type):
    """Tuple x:Int, y:Real end — ordered dependent tuple signature."""
    fields: tuple[FieldSig, ...]


@dataclass(frozen=True)
class RecordFieldSig(ASTNode):
    """Field in a record signature: [var] x : T"""
    name: str
    type_sig: Type
    is_var: bool = False


@dataclass(frozen=True)
class TypeRecord(Type):
    """Record x:Int, y:Real end — unordered record type."""
    fields: tuple[RecordFieldSig, ...]


@dataclass(frozen=True)
class OptionFieldSig(ASTNode):
    """Variant in an option signature: tag [with fields...]"""
    tag: str
    payload_sig: tuple[FieldSig, ...] = ()


@dataclass(frozen=True)
class TypeOption(Type):
    """Option red, green, blue with val:Int end — tagged union / option type."""
    variants: tuple[OptionFieldSig, ...]


@dataclass(frozen=True)
class VariantFieldSig(ASTNode):
    """Field in a variant signature: [var] tag : T"""
    tag: str
    type_sig: Type
    is_var: bool = False

    @property
    def name(self) -> str:
        return self.tag


@dataclass(frozen=True)
class TypeVariant(Type):
    """Variant ok:Int, err:String end — unordered variant type."""
    fields: tuple[VariantFieldSig, ...]


@dataclass(frozen=True)
class TypeAuto(Type):
    """Auto X::K with x:T end — existential / automorphic dynamic type."""
    type_param: Optional[str]
    kind_bound: Kind
    signature: tuple[FieldSig, ...]


@dataclass(frozen=True)
class TypeFun(Type):
    """Fun(X::K, Y<:B) T — higher-order compile-time type operator."""
    params: tuple[TypeFormal, ...]
    result_kind: Optional[Kind]
    body: Type


@dataclass(frozen=True)
class TypeRec(Type):
    """Rec(X <: B) T — recursive type constructor."""
    var_name: str
    bound: Kind
    body: Type


@dataclass(frozen=True)
class TypeApp(Type):
    """T(A, B) — type operator application."""
    constructor: Type
    arguments: tuple[Type, ...]


@dataclass(frozen=True)
class TypeInfix(Type):
    """T -> U, T /\ U — infix type operator."""
    left: Type
    op: str
    right: Type


@dataclass(frozen=True)
class TypeArray(Type):
    """Array(T) — built-in array type."""
    element_type: Type


@dataclass(frozen=True)
class TypeVar(Type):
    """Var(T) — mutable reference cell type."""
    element_type: Type


@dataclass(frozen=True)
class TypeOut(Type):
    """Out(T) — contravariant output parameter mode."""
    element_type: Type


@dataclass(frozen=True)
class TypeManifest(Type):
    """M_T — manifest type extraction across interfaces."""
    module_name: str
    type_name: str


@dataclass(frozen=True)
class TypeExternal(Type):
    """external "c_type" — opaque C data structure type."""
    c_type: str


# ============================================================================
# 4. Level 0: Values and Expressions
# ============================================================================

@dataclass(frozen=True)
class Expr(ASTNode):
    """Base class for Level 0 value expressions."""
    pass


@dataclass(frozen=True)
class TypeArgument(Expr):
    """Explicit type argument in call binding: :Type"""
    type_val: Type


@dataclass(frozen=True)
class KindArgument(Expr):
    """Explicit kind argument in call binding: ::Kind"""
    kind_val: Kind



# --- Literals ---

@dataclass(frozen=True)
class ExprInt(Expr):
    value: int
    lexeme: str


@dataclass(frozen=True)
class ExprReal(Expr):
    value: float
    lexeme: str


@dataclass(frozen=True)
class ExprChar(Expr):
    value: str
    lexeme: str


@dataclass(frozen=True)
class ExprString(Expr):
    value: str
    lexeme: str


@dataclass(frozen=True)
class ExprBool(Expr):
    value: bool


@dataclass(frozen=True)
class ExprOk(Expr):
    pass


@dataclass(frozen=True)
class ExprId(Expr):
    name: str


@dataclass(frozen=True)
class ExprExternal(Expr):
    """external "c_symbol" — native external C symbol binding."""
    symbol: str


# --- Blocks & Control Flow ---

@dataclass(frozen=True)
class ExprBlock(Expr):
    """begin ... end — sequence of bindings and statements."""
    bindings: tuple[BindingNode, ...]


@dataclass(frozen=True)
class ExprIf(Expr):
    """if cond then e1 elsif cond2 then e2 else e3 end

    short_circuit marks a conditional desugared from andif or orif
    (quest/syntax/desugar.py), whose operands are checked against Bool, so that
    errors name the operand rather than the conditional's branches.
    """
    cond: Expr
    then_branch: Expr
    elsifs: tuple[tuple[Expr, Expr], ...] = ()
    else_branch: Optional[Expr] = None
    short_circuit: bool = False


@dataclass(frozen=True)
class ExprWhile(Expr):
    cond: Expr
    body: Expr


@dataclass(frozen=True)
class ExprLoop(Expr):
    body: Expr


@dataclass(frozen=True)
class ExprExit(Expr):
    pass


@dataclass(frozen=True)
class ExprFor(Expr):
    var_name: str
    start: Expr
    is_downto: bool
    stop: Expr
    body: Expr


# --- Functions & Applications ---

@dataclass(frozen=True)
class ExprFun(Expr):
    """fun(x: Int): Int x + 1"""
    params: tuple[FormalParam, ...]
    return_type: Optional[Type]
    body: Expr
    type_params: tuple[TypeFormal, ...] = ()


@dataclass(frozen=True)
class ExprApp(Expr):
    """f(a, b)"""
    func: Expr
    args: tuple[Expr, ...]


@dataclass(frozen=True)
class ExprInfix(Expr):
    """a + b, a := b, a andif b, a orif b, a is b"""
    left: Expr
    op: str
    right: Expr


# --- Aggregates & Constructors ---

@dataclass(frozen=True)
class TupleBinding(ASTNode):
    name: Optional[str]
    value: Expr
    type_annot: Optional[Type] = None
    is_var: bool = False


@dataclass(frozen=True)
class TupleBindingGroup(ASTNode):
    """Simultaneous value components of a tuple: let x = ... and y = ...
    (without rec)."""
    bindings: tuple[TupleBinding, ...]


@dataclass(frozen=True)
class ExprTuple(Expr):
    """A tuple constructor. Recursive value declarations (let rec ..., alone or
    joined by and) are components as LetValueBinding and LetValueBindingGroup,
    which keep the annotations that type them."""
    fields: tuple[
        Union[
            TupleBinding, TupleBindingGroup, LetValueBinding, LetValueBindingGroup, TypeBinding, TypeBindingGroup,
            DefKindBinding,
        ],
        ...,
    ]


@dataclass(frozen=True)
class RecordBinding(ASTNode):
    name: str
    value: Expr
    is_var: bool = False


@dataclass(frozen=True)
class ExprRecord(Expr):
    fields: tuple[RecordBinding, ...]


@dataclass(frozen=True)
class ExprOption(Expr):
    tag: Optional[str] = None
    option_type: Type = None  # type: ignore[assignment]
    payload: Optional[Expr] = None
    ordinal_expr: Optional[Expr] = None


@dataclass(frozen=True)
class ExprVariant(Expr):
    tag: str
    variant_type: Type
    is_var: bool = False
    payload: Optional[Expr] = None


@dataclass(frozen=True)
class ExprArray(Expr):
    elements: tuple[Expr, ...]
    element_type: Optional[Type] = None


@dataclass(frozen=True)
class ExprArrayRep(Expr):
    count: Expr
    init_val: Expr


@dataclass(frozen=True)
class ExprAuto(Expr):
    """auto [let A [HasKind] =] :W with Binding end — an auto value with type
    component W."""
    witness_type: Type
    payload: Expr
    witness_name: Optional[str] = None
    witness_bound: Optional[Kind] = None


# --- Selection, Indexing, and References ---

@dataclass(frozen=True)
class ExprSelect(Expr):
    target: Expr
    field: str


@dataclass(frozen=True)
class ExprIndex(Expr):
    target: Expr
    index: Expr


@dataclass(frozen=True)
class ExprIndexAssign(Expr):
    target: Expr
    index: Expr
    value: Expr


@dataclass(frozen=True)
class ExprVarCell(Expr):
    value: Expr


@dataclass(frozen=True)
class ExprDerefCell(Expr):
    target: Expr


@dataclass(frozen=True)
class ExprVariantCheck(Expr):
    target: Expr
    tag: str


@dataclass(frozen=True)
class ExprVariantAssert(Expr):
    target: Expr
    tag: str


# --- Pattern Matching & Discrimination ---

@dataclass(frozen=True)
class CaseBranch(ASTNode):
    tags: tuple[str, ...]
    binder: Optional[str] = None
    binder_type: Optional[Type] = None
    body: Expr = None  # type: ignore


@dataclass(frozen=True)
class ExprCase(Expr):
    target: Expr
    branches: tuple[CaseBranch, ...]
    else_branch: Optional[Expr] = None


@dataclass(frozen=True)
class InspectBranch(ASTNode):
    match_type: Type
    binders: tuple[tuple[str, Optional[Type]], ...]
    body: Expr


@dataclass(frozen=True)
class ExprInspect(Expr):
    target: Expr
    branches: tuple[InspectBranch, ...]
    else_branch: Optional[Expr] = None


# --- Exceptions ---

@dataclass(frozen=True)
class ExprException(Expr):
    name: str
    type_annot: Optional[Type] = None


@dataclass(frozen=True)
class ExprRaise(Expr):
    exc: Expr
    payload: Optional[Expr] = None
    as_type: Optional[Type] = None


@dataclass(frozen=True)
class TryBranch(ASTNode):
    exc_pattern: Expr
    binder: Optional[str] = None
    binder_type: Optional[Type] = None
    body: Expr = None  # type: ignore


@dataclass(frozen=True)
class ExprTry(Expr):
    body: Expr
    branches: tuple[TryBranch, ...]
    else_branch: Optional[Expr] = None


# ============================================================================
# 5. Bindings, Declarations, and Program Structure
# ============================================================================

@dataclass(frozen=True)
class BindingNode(ASTNode):
    """Base class for declarations and statements inside blocks/phrases."""
    pass


@dataclass(frozen=True)
class LetValueBinding(BindingNode):
    """let [rec] [var] x (params...) : T = expr and y = ..."""
    name: str
    value: Expr
    params: tuple[FormalParam, ...] = ()
    type_annot: Optional[Type] = None
    is_rec: bool = False
    is_var: bool = False


@dataclass(frozen=True)
class LetValueBindingGroup(BindingNode):
    """let [rec] x = ... and y = ...: two or more simultaneous value bindings.

    The members share the keyword's rec (their is_rec); the group is positioned
    at the keyword and each member at its name.
    """
    bindings: tuple[LetValueBinding, ...]


@dataclass(frozen=True)
class TypeBinding(BindingNode):
    """Let [Rec] T(X::K)::K' = Type, or Def [Rec] T = Type (is_def, e.g. in an
    interface signature)."""
    name: str
    type_val: Type
    params: tuple[TypeFormal, ...] = ()
    bound: Optional[Kind] = None
    is_rec: bool = False
    is_def: bool = False


@dataclass(frozen=True)
class TypeBindingGroup(BindingNode):
    """Let [Rec] T = Type and U = Type ..., or the same with Def: two or more
    simultaneous type bindings.

    The members share the keyword's Rec and Def (their is_rec and is_def); the
    group is positioned at the keyword and each member at its name.
    """
    bindings: tuple[TypeBinding, ...]


@dataclass(frozen=True)
class DefKindBinding(BindingNode):
    """DEF K = Kind"""
    name: str
    kind_val: Kind


@dataclass(frozen=True)
class ExprStmt(BindingNode):
    """Standalone expression statement."""
    expr: Expr


@dataclass(frozen=True)
class ImportItem(ASTNode):
    names: tuple[str, ...]
    interface_name: str
    module_paths: Optional[tuple[str, ...]] = None
    interface_path: Optional[str] = None

    @property
    def effective_module_paths(self) -> tuple[str, ...]:
        return self.module_paths if self.module_paths is not None else self.names

    @property
    def effective_interface_path(self) -> str:
        return self.interface_path if self.interface_path is not None else self.interface_name


@dataclass(frozen=True)
class ImportPhrase(ASTNode):
    items: tuple[ImportItem, ...]


@dataclass(frozen=True)
class InterfaceDecl(ASTNode):
    name: str
    signatures: tuple[BindingNode, ...]
    imports: tuple[ImportItem, ...] = ()
    is_unsound: bool = False


@dataclass(frozen=True)
class ModuleDecl(ASTNode):
    name: str
    interface_name: str
    bindings: tuple[BindingNode, ...]
    imports: tuple[ImportItem, ...] = ()
    is_unsound: bool = False


@dataclass(frozen=True)
class Program(ASTNode):
    """A complete .quest compilation unit: top-level declarations, expressions,
    interfaces, modules."""
    phrases: tuple[ASTNode, ...]


# ============================================================================
# 6. Canonical S-Expression Pretty-Printer
# ============================================================================

def _is_simple_leaf(value: Any) -> bool:
    """Checks if an AST value is a simple leaf that can be printed inline."""
    match value:
        case None | int() | float() | bool() | str() | Enum():
            return True
        case tuple() if all(isinstance(item, str) for item in value):
            return True
        case ASTNode() if len(fields(value)) == 0:
            return True
        case _:
            return False


def ast_dump(node: Any, indent: int = 0, show_offsets: bool = False) -> str:
    """Recursively formats an AST node into a canonical 2-space indented
    S-expression string."""
    padding = "  " * indent
    child_padding = "  " * (indent + 1)

    if not isinstance(node, ASTNode):
        match node:
            case tuple():
                if not node:
                    return "()"
                if all(_is_simple_leaf(item) for item in node):
                    return "(" + " ".join(repr(item) if isinstance(item, str) else str(item) for item in node) + ")"
                lines = ["("]
                for element in node:
                    lines.append(f"{child_padding}{ast_dump(element, indent + 1, show_offsets)}")
                lines.append(f"{padding})")
                return "\n".join(lines)
            case Enum(name=enum_name):
                return enum_name
            case str():
                return repr(node)
            case None:
                return "nil"
            case _:
                return str(node)

    class_name = node.__class__.__name__
    node_fields = fields(node)

    # Filter out offset field unless show_offsets is True
    active_fields = [field for field in node_fields if show_offsets or field.name != "offset"]

    if not active_fields:
        if show_offsets:
            return f"({class_name} :offset {node.offset})"
        return f"({class_name})"

    # Check if all fields are simple leaves
    all_simple = True
    field_values = []
    for field in active_fields:
        field_value = getattr(node, field.name)
        field_values.append((field.name, field_value))
        if not _is_simple_leaf(field_value):
            all_simple = False

    if all_simple:
        parts = [class_name]
        for name, field_value in field_values:
            match field_value:
                case Enum(name=enum_name):
                    parts.append(enum_name)
                case str():
                    parts.append(repr(field_value))
                case tuple():
                    parts.append("(" + " ".join(repr(item) for item in field_value) + ")")
                case None:
                    continue  # omit None in simple leaf inline
                case _:
                    parts.append(str(field_value))
        return f"({ ' '.join(parts) })"

    # Multi-line indented S-expression
    lines = [f"({class_name}"]
    for name, field_value in field_values:
        if field_value is None or field_value == () or field_value is False:
            # Skip empty optional values to keep trees compact
            continue
        if _is_simple_leaf(field_value):
            match field_value:
                case Enum(name=enum_name):
                    lines.append(f"{child_padding}:{name} {enum_name}")
                case str():
                    lines.append(f"{child_padding}:{name} {field_value!r}")
                case tuple():
                    lines.append(f"{child_padding}:{name} ({ ' '.join(repr(item) for item in field_value) })")
                case _:
                    lines.append(f"{child_padding}:{name} {field_value}")
        else:
            if isinstance(field_value, tuple):
                lines.append(f"{child_padding}:{name} (")
                for item in field_value:
                    lines.append(f"{child_padding}  {ast_dump(item, indent + 2, show_offsets)}")
                lines.append(f"{child_padding})")
            else:
                lines.append(f"{child_padding}:{name} {ast_dump(field_value, indent + 1, show_offsets)}")

    lines.append(f"{padding})")
    return "\n".join(lines)


# The explicit traversal: a case for each class of syntax node

def ast_fields(node) -> Optional[tuple]:
    """The values of a syntax node's fields (but its offset), in order; None for
    a value that is not a syntax node. The syntax tree's one traversal: walkers
    of nodes' fields read them through it."""
    accessor = _AST_FIELDS.get(type(node))
    return accessor(node) if accessor is not None else None


def rebuild_ast(node, values: tuple):
    """A syntax node of node's class, at its offset, whose fields are values (as
    ast_fields gives them)."""
    return _REBUILD_AST[type(node)](node, values)


# The entries of the traversal, a case for each class

_AST_FIELDS: dict[type, Callable[[Any], tuple]] = {
    FormalParam: lambda node: (node.name, node.type_annot, node.mode),
    TypeFormal: lambda node: (node.name, node.bound),
    Quantifier: lambda node: (node.name, node.bound, node.mode, node.is_type),
    KindType: lambda node: (),
    KindPower: lambda node: (node.bound,),
    KindAll: lambda node: (node.param_name, node.param_kind, node.body_kind),
    KindId: lambda node: (node.name,),
    KindManifest: lambda node: (node.interface_name, node.kind_name),
    TypePath: lambda node: (node.path,),
    TypeAll: lambda node: (node.quantifiers, node.result_type),
    FieldSig: lambda node: (node.name, node.type_sig, node.mode),
    TypeTuple: lambda node: (node.fields,),
    RecordFieldSig: lambda node: (node.name, node.type_sig, node.is_var),
    TypeRecord: lambda node: (node.fields,),
    OptionFieldSig: lambda node: (node.tag, node.payload_sig),
    TypeOption: lambda node: (node.variants,),
    VariantFieldSig: lambda node: (node.tag, node.type_sig, node.is_var),
    TypeVariant: lambda node: (node.fields,),
    TypeAuto: lambda node: (node.type_param, node.kind_bound, node.signature),
    TypeFun: lambda node: (node.params, node.result_kind, node.body),
    TypeRec: lambda node: (node.var_name, node.bound, node.body),
    TypeApp: lambda node: (node.constructor, node.arguments),
    TypeInfix: lambda node: (node.left, node.op, node.right),
    TypeArray: lambda node: (node.element_type,),
    TypeVar: lambda node: (node.element_type,),
    TypeOut: lambda node: (node.element_type,),
    TypeManifest: lambda node: (node.module_name, node.type_name),
    TypeExternal: lambda node: (node.c_type,),
    TypeArgument: lambda node: (node.type_val,),
    KindArgument: lambda node: (node.kind_val,),
    ExprInt: lambda node: (node.value, node.lexeme),
    ExprReal: lambda node: (node.value, node.lexeme),
    ExprChar: lambda node: (node.value, node.lexeme),
    ExprString: lambda node: (node.value, node.lexeme),
    ExprBool: lambda node: (node.value,),
    ExprOk: lambda node: (),
    ExprId: lambda node: (node.name,),
    ExprExternal: lambda node: (node.symbol,),
    ExprBlock: lambda node: (node.bindings,),
    ExprIf: lambda node: (node.cond, node.then_branch, node.elsifs, node.else_branch, node.short_circuit),
    ExprWhile: lambda node: (node.cond, node.body),
    ExprLoop: lambda node: (node.body,),
    ExprExit: lambda node: (),
    ExprFor: lambda node: (node.var_name, node.start, node.is_downto, node.stop, node.body),
    ExprFun: lambda node: (node.params, node.return_type, node.body, node.type_params),
    ExprApp: lambda node: (node.func, node.args),
    ExprInfix: lambda node: (node.left, node.op, node.right),
    TupleBinding: lambda node: (node.name, node.value, node.type_annot, node.is_var),
    TupleBindingGroup: lambda node: (node.bindings,),
    ExprTuple: lambda node: (node.fields,),
    RecordBinding: lambda node: (node.name, node.value, node.is_var),
    ExprRecord: lambda node: (node.fields,),
    ExprOption: lambda node: (node.tag, node.option_type, node.payload, node.ordinal_expr),
    ExprVariant: lambda node: (node.tag, node.variant_type, node.is_var, node.payload),
    ExprArray: lambda node: (node.elements, node.element_type),
    ExprArrayRep: lambda node: (node.count, node.init_val),
    ExprAuto: lambda node: (node.witness_type, node.payload, node.witness_name, node.witness_bound),
    ExprSelect: lambda node: (node.target, node.field),
    ExprIndex: lambda node: (node.target, node.index),
    ExprIndexAssign: lambda node: (node.target, node.index, node.value),
    ExprVarCell: lambda node: (node.value,),
    ExprDerefCell: lambda node: (node.target,),
    ExprVariantCheck: lambda node: (node.target, node.tag),
    ExprVariantAssert: lambda node: (node.target, node.tag),
    CaseBranch: lambda node: (node.tags, node.binder, node.binder_type, node.body),
    ExprCase: lambda node: (node.target, node.branches, node.else_branch),
    InspectBranch: lambda node: (node.match_type, node.binders, node.body),
    ExprInspect: lambda node: (node.target, node.branches, node.else_branch),
    ExprException: lambda node: (node.name, node.type_annot),
    ExprRaise: lambda node: (node.exc, node.payload, node.as_type),
    TryBranch: lambda node: (node.exc_pattern, node.binder, node.binder_type, node.body),
    ExprTry: lambda node: (node.body, node.branches, node.else_branch),
    LetValueBinding: lambda node: (node.name, node.value, node.params, node.type_annot, node.is_rec, node.is_var),
    LetValueBindingGroup: lambda node: (node.bindings,),
    TypeBinding: lambda node: (node.name, node.type_val, node.params, node.bound, node.is_rec, node.is_def),
    TypeBindingGroup: lambda node: (node.bindings,),
    DefKindBinding: lambda node: (node.name, node.kind_val),
    ExprStmt: lambda node: (node.expr,),
    ImportItem: lambda node: (node.names, node.interface_name, node.module_paths, node.interface_path),
    ImportPhrase: lambda node: (node.items,),
    InterfaceDecl: lambda node: (node.name, node.signatures, node.imports, node.is_unsound),
    ModuleDecl: lambda node: (node.name, node.interface_name, node.bindings, node.imports, node.is_unsound),
    Program: lambda node: (node.phrases,),
}

_REBUILD_AST: dict[type, Callable[[Any, tuple], Any]] = {
    FormalParam: lambda node, values: FormalParam(
        offset=node.offset, name=values[0], type_annot=values[1], mode=values[2],
    ),
    TypeFormal: lambda node, values: TypeFormal(offset=node.offset, name=values[0], bound=values[1]),
    Quantifier: lambda node, values: Quantifier(
        offset=node.offset, name=values[0], bound=values[1], mode=values[2], is_type=values[3],
    ),
    KindType: lambda node, values: KindType(offset=node.offset),
    KindPower: lambda node, values: KindPower(offset=node.offset, bound=values[0]),
    KindAll: lambda node, values: KindAll(
        offset=node.offset, param_name=values[0], param_kind=values[1], body_kind=values[2],
    ),
    KindId: lambda node, values: KindId(offset=node.offset, name=values[0]),
    KindManifest: lambda node, values: KindManifest(offset=node.offset, interface_name=values[0], kind_name=values[1]),
    TypePath: lambda node, values: TypePath(offset=node.offset, path=values[0]),
    TypeAll: lambda node, values: TypeAll(offset=node.offset, quantifiers=values[0], result_type=values[1]),
    FieldSig: lambda node, values: FieldSig(offset=node.offset, name=values[0], type_sig=values[1], mode=values[2]),
    TypeTuple: lambda node, values: TypeTuple(offset=node.offset, fields=values[0]),
    RecordFieldSig: lambda node, values: RecordFieldSig(
        offset=node.offset, name=values[0], type_sig=values[1], is_var=values[2],
    ),
    TypeRecord: lambda node, values: TypeRecord(offset=node.offset, fields=values[0]),
    OptionFieldSig: lambda node, values: OptionFieldSig(offset=node.offset, tag=values[0], payload_sig=values[1]),
    TypeOption: lambda node, values: TypeOption(offset=node.offset, variants=values[0]),
    VariantFieldSig: lambda node, values: VariantFieldSig(
        offset=node.offset, tag=values[0], type_sig=values[1], is_var=values[2],
    ),
    TypeVariant: lambda node, values: TypeVariant(offset=node.offset, fields=values[0]),
    TypeAuto: lambda node, values: TypeAuto(
        offset=node.offset, type_param=values[0], kind_bound=values[1], signature=values[2],
    ),
    TypeFun: lambda node, values: TypeFun(offset=node.offset, params=values[0], result_kind=values[1], body=values[2]),
    TypeRec: lambda node, values: TypeRec(offset=node.offset, var_name=values[0], bound=values[1], body=values[2]),
    TypeApp: lambda node, values: TypeApp(offset=node.offset, constructor=values[0], arguments=values[1]),
    TypeInfix: lambda node, values: TypeInfix(offset=node.offset, left=values[0], op=values[1], right=values[2]),
    TypeArray: lambda node, values: TypeArray(offset=node.offset, element_type=values[0]),
    TypeVar: lambda node, values: TypeVar(offset=node.offset, element_type=values[0]),
    TypeOut: lambda node, values: TypeOut(offset=node.offset, element_type=values[0]),
    TypeManifest: lambda node, values: TypeManifest(offset=node.offset, module_name=values[0], type_name=values[1]),
    TypeExternal: lambda node, values: TypeExternal(offset=node.offset, c_type=values[0]),
    TypeArgument: lambda node, values: TypeArgument(offset=node.offset, type_val=values[0]),
    KindArgument: lambda node, values: KindArgument(offset=node.offset, kind_val=values[0]),
    ExprInt: lambda node, values: ExprInt(offset=node.offset, value=values[0], lexeme=values[1]),
    ExprReal: lambda node, values: ExprReal(offset=node.offset, value=values[0], lexeme=values[1]),
    ExprChar: lambda node, values: ExprChar(offset=node.offset, value=values[0], lexeme=values[1]),
    ExprString: lambda node, values: ExprString(offset=node.offset, value=values[0], lexeme=values[1]),
    ExprBool: lambda node, values: ExprBool(offset=node.offset, value=values[0]),
    ExprOk: lambda node, values: ExprOk(offset=node.offset),
    ExprId: lambda node, values: ExprId(offset=node.offset, name=values[0]),
    ExprExternal: lambda node, values: ExprExternal(offset=node.offset, symbol=values[0]),
    ExprBlock: lambda node, values: ExprBlock(offset=node.offset, bindings=values[0]),
    ExprIf: lambda node, values: ExprIf(
        offset=node.offset, cond=values[0], then_branch=values[1], elsifs=values[2], else_branch=values[3],
        short_circuit=values[4],
    ),
    ExprWhile: lambda node, values: ExprWhile(offset=node.offset, cond=values[0], body=values[1]),
    ExprLoop: lambda node, values: ExprLoop(offset=node.offset, body=values[0]),
    ExprExit: lambda node, values: ExprExit(offset=node.offset),
    ExprFor: lambda node, values: ExprFor(
        offset=node.offset, var_name=values[0], start=values[1], is_downto=values[2], stop=values[3], body=values[4],
    ),
    ExprFun: lambda node, values: ExprFun(
        offset=node.offset, params=values[0], return_type=values[1], body=values[2], type_params=values[3],
    ),
    ExprApp: lambda node, values: ExprApp(offset=node.offset, func=values[0], args=values[1]),
    ExprInfix: lambda node, values: ExprInfix(offset=node.offset, left=values[0], op=values[1], right=values[2]),
    TupleBinding: lambda node, values: TupleBinding(
        offset=node.offset, name=values[0], value=values[1], type_annot=values[2], is_var=values[3],
    ),
    TupleBindingGroup: lambda node, values: TupleBindingGroup(offset=node.offset, bindings=values[0]),
    ExprTuple: lambda node, values: ExprTuple(offset=node.offset, fields=values[0]),
    RecordBinding: lambda node, values: RecordBinding(
        offset=node.offset, name=values[0], value=values[1], is_var=values[2],
    ),
    ExprRecord: lambda node, values: ExprRecord(offset=node.offset, fields=values[0]),
    ExprOption: lambda node, values: ExprOption(
        offset=node.offset, tag=values[0], option_type=values[1], payload=values[2], ordinal_expr=values[3],
    ),
    ExprVariant: lambda node, values: ExprVariant(
        offset=node.offset, tag=values[0], variant_type=values[1], is_var=values[2], payload=values[3],
    ),
    ExprArray: lambda node, values: ExprArray(offset=node.offset, elements=values[0], element_type=values[1]),
    ExprArrayRep: lambda node, values: ExprArrayRep(offset=node.offset, count=values[0], init_val=values[1]),
    ExprAuto: lambda node, values: ExprAuto(
        offset=node.offset, witness_type=values[0], payload=values[1], witness_name=values[2], witness_bound=values[3],
    ),
    ExprSelect: lambda node, values: ExprSelect(offset=node.offset, target=values[0], field=values[1]),
    ExprIndex: lambda node, values: ExprIndex(offset=node.offset, target=values[0], index=values[1]),
    ExprIndexAssign: lambda node, values: ExprIndexAssign(
        offset=node.offset, target=values[0], index=values[1], value=values[2],
    ),
    ExprVarCell: lambda node, values: ExprVarCell(offset=node.offset, value=values[0]),
    ExprDerefCell: lambda node, values: ExprDerefCell(offset=node.offset, target=values[0]),
    ExprVariantCheck: lambda node, values: ExprVariantCheck(offset=node.offset, target=values[0], tag=values[1]),
    ExprVariantAssert: lambda node, values: ExprVariantAssert(offset=node.offset, target=values[0], tag=values[1]),
    CaseBranch: lambda node, values: CaseBranch(
        offset=node.offset, tags=values[0], binder=values[1], binder_type=values[2], body=values[3],
    ),
    ExprCase: lambda node, values: ExprCase(
        offset=node.offset, target=values[0], branches=values[1], else_branch=values[2],
    ),
    InspectBranch: lambda node, values: InspectBranch(
        offset=node.offset, match_type=values[0], binders=values[1], body=values[2],
    ),
    ExprInspect: lambda node, values: ExprInspect(
        offset=node.offset, target=values[0], branches=values[1], else_branch=values[2],
    ),
    ExprException: lambda node, values: ExprException(offset=node.offset, name=values[0], type_annot=values[1]),
    ExprRaise: lambda node, values: ExprRaise(offset=node.offset, exc=values[0], payload=values[1], as_type=values[2]),
    TryBranch: lambda node, values: TryBranch(
        offset=node.offset, exc_pattern=values[0], binder=values[1], binder_type=values[2], body=values[3],
    ),
    ExprTry: lambda node, values: ExprTry(
        offset=node.offset, body=values[0], branches=values[1], else_branch=values[2],
    ),
    LetValueBinding: lambda node, values: LetValueBinding(
        offset=node.offset, name=values[0], value=values[1], params=values[2], type_annot=values[3], is_rec=values[4],
        is_var=values[5],
    ),
    LetValueBindingGroup: lambda node, values: LetValueBindingGroup(offset=node.offset, bindings=values[0]),
    TypeBinding: lambda node, values: TypeBinding(
        offset=node.offset, name=values[0], type_val=values[1], params=values[2], bound=values[3], is_rec=values[4],
        is_def=values[5],
    ),
    TypeBindingGroup: lambda node, values: TypeBindingGroup(offset=node.offset, bindings=values[0]),
    DefKindBinding: lambda node, values: DefKindBinding(offset=node.offset, name=values[0], kind_val=values[1]),
    ExprStmt: lambda node, values: ExprStmt(offset=node.offset, expr=values[0]),
    ImportItem: lambda node, values: ImportItem(
        offset=node.offset, names=values[0], interface_name=values[1], module_paths=values[2], interface_path=values[3],
    ),
    ImportPhrase: lambda node, values: ImportPhrase(offset=node.offset, items=values[0]),
    InterfaceDecl: lambda node, values: InterfaceDecl(
        offset=node.offset, name=values[0], signatures=values[1], imports=values[2], is_unsound=values[3],
    ),
    ModuleDecl: lambda node, values: ModuleDecl(
        offset=node.offset, name=values[0], interface_name=values[1], bindings=values[2], imports=values[3],
        is_unsound=values[4],
    ),
    Program: lambda node, values: Program(offset=node.offset, phrases=values[0]),
}
