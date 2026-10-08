"""Quest Language Grammar Specification and AST Builders."""

from __future__ import annotations

import dataclasses
from functools import reduce
from typing import Any, Callable

from quest.tokens import SourceMap, Token, TokenKind
from quest.parser import (
    Construct,
    MatchToken,
    Optional,
    Parser,
    Repeated,
    Rule,
    SepBy,
    SyntaxTarget,
)
import quest.ast as ast


# ============================================================================
# 1. Top-Level Quest Syntax Targets (Non-Terminals)
# ============================================================================

PROGRAM = SyntaxTarget("Program")
PHRASE = SyntaxTarget("Phrase")
LINKAGE = SyntaxTarget("Linkage")
IMPORT = SyntaxTarget("Import")
IMPORT_ITEM = SyntaxTarget("ImportItem")
IDE = SyntaxTarget("Ide")
IDE_LIST = SyntaxTarget("IdeList")
PATH = SyntaxTarget("Path")
PATH_LIST = SyntaxTarget("PathList")
MODULE_ENTRY = SyntaxTarget("ModuleEntry")
MODULE_ENTRY_LIST = SyntaxTarget("ModuleEntryList")

KIND = SyntaxTarget("Kind")
PRIMARY_KIND = SyntaxTarget("PrimaryKind")

TYPE = SyntaxTarget("Type")
POSTFIX_TYPE = SyntaxTarget("PostfixType")
POSTFIX_TYPE_OP = SyntaxTarget("PostfixTypeOp")
PRIMARY_TYPE = SyntaxTarget("PrimaryType")
TYPE_SIGNATURE = SyntaxTarget("TypeSignature")
VALUE_SIGNATURE = SyntaxTarget("ValueSignature")
OPTION_SIGNATURE = SyntaxTarget("OptionSignature")
SIGNATURE = SyntaxTarget("Signature")

VALUE = SyntaxTarget("Value")
POSTFIX_VALUE = SyntaxTarget("PostfixValue")
POSTFIX_OP = SyntaxTarget("PostfixOp")
PRIMARY_VALUE = SyntaxTarget("PrimaryValue")
INFIX_OP = SyntaxTarget("InfixOp")
BINDING = SyntaxTarget("Binding")
TYPE_BINDING = SyntaxTarget("TypeBinding")
VALUE_BINDING = SyntaxTarget("ValueBinding")

KIND_DECL = SyntaxTarget("KindDecl")
TYPE_DECL = SyntaxTarget("TypeDecl")
VALUE_DECL = SyntaxTarget("ValueDecl")
TYPE_FORMAL = SyntaxTarget("TypeFormal")
TYPE_FORMALS = SyntaxTarget("TypeFormals")

CASE_BRANCHES = SyntaxTarget("CaseBranches")
INSPECT_BRANCHES = SyntaxTarget("InspectBranches")
TRY_BRANCHES = SyntaxTarget("TryBranches")

HAS_TYPE = SyntaxTarget("HasType")
HAS_MUT_TYPE = SyntaxTarget("HasMutType")
HAS_KIND = SyntaxTarget("HasKind")

ALL_SYNTAX_TARGETS: tuple[SyntaxTarget, ...] = tuple(
    value for value in globals().values() if isinstance(value, SyntaxTarget)
)


# ============================================================================
# 2. AST Construction Helpers
# ============================================================================

# Postfix operator rules evaluate to functions from the operand to the resulting node;
# a postfix chain applies them left to right.
PostfixOp = Callable[[Any], Any]


def _apply_postfix(primary: Any, operations: tuple[PostfixOp, ...]) -> Any:
    return reduce(lambda operand, operation: operation(operand), operations, primary)


def _select_type(name: str) -> PostfixOp:
    def select(current: ast.Type) -> ast.Type:
        path = current.path if isinstance(current, ast.TypePath) else ()
        return ast.TypePath(path=path + (name,), offset=current.offset)
    return select


def _call_args(bindings: tuple[Any, ...]) -> tuple[ast.Expr, ...]:
    """Converts the phrases of a call's argument list to argument expressions."""
    return tuple(argument.expr if isinstance(argument, ast.ExprStmt) else argument for argument in bindings)


def _body(bindings: tuple[Any, ...], offset: int) -> Any:
    """A single phrase as-is, or several phrases as a block."""
    return bindings[0] if len(bindings) == 1 else ast.ExprBlock(bindings=bindings, offset=offset)


def _optional_body(bindings: Optional[tuple[Any, ...]], offset: int) -> Any:
    """Like _body, but None for an absent clause."""
    return None if bindings is None else _body(bindings, offset)


def _mode(var_token: Optional[Token], out_token: Optional[Token]) -> ast.ParamMode:
    if var_token:
        return ast.ParamMode.VAR
    if out_token:
        return ast.ParamMode.OUT
    return ast.ParamMode.VALUE


def _basename(path: str) -> str:
    return path.split("/")[-1]


def _build_array_expr(offset: int, bindings: tuple[Any, ...]) -> ast.ExprArray:
    """Builds an ExprArray from bindings, extracting leading element type if present."""
    elem_type = None
    if bindings and isinstance(bindings[0], ast.TypeArgument):
        elem_type = bindings[0].type_val
        bindings = bindings[1:]
    return ast.ExprArray(elements=_call_args(bindings), element_type=elem_type, offset=offset)


def _process_tuple_bindings(bindings: tuple[Any, ...]) -> tuple[Any, ...]:
    """Processes phrases inside a tuple constructor into tuple components."""
    result: list[Any] = []
    for item in bindings:
        match item:
            case ast.LetTypeBinding() | ast.DefTypeBinding():
                result.append(item)
            case ast.LetValueBinding(params=params) if params:
                fn_expr = ast.ExprFun(
                    params=params,
                    return_type=item.type_annot,
                    body=item.value,
                    offset=item.offset,
                )
                result.append(
                    ast.TupleBinding(
                        name=item.name,
                        value=fn_expr,
                        is_var=item.is_var,
                        offset=item.offset,
                    )
                )
            case ast.LetValueBinding():
                result.append(
                    ast.TupleBinding(
                        name=item.name,
                        value=item.value,
                        type_annot=item.type_annot,
                        is_var=item.is_var,
                        offset=item.offset,
                    )
                )
            case ast.ExprStmt(expr=expr):
                result.append(ast.TupleBinding(name=None, value=expr, offset=item.offset))
            case ast.TupleBinding():
                result.append(item)
            case ast.Expr():
                result.append(ast.TupleBinding(name=None, value=item, offset=item.offset))
            case _:
                result.append(
                    ast.TupleBinding(
                        name=getattr(item, "name", None),
                        value=getattr(item, "value", getattr(item, "expr", item)),
                        is_var=getattr(item, "is_var", False),
                        offset=getattr(item, "offset", 0),
                    )
                )
    return tuple(result)


def _build_option_payload(with_bindings: Optional[tuple[Any, ...]], offset: int) -> Optional[ast.Expr]:
    """Processes the phrases of an option's with clause (None if absent) into a payload."""
    if not with_bindings:
        return None
    if (
        len(with_bindings) == 1
        and isinstance(with_bindings[0], ast.ExprStmt)
        and isinstance(with_bindings[0].expr, ast.ExprTuple)
    ):
        return with_bindings[0].expr
    return ast.ExprTuple(fields=_process_tuple_bindings(with_bindings), offset=offset)


def _build_kind_all(all_token: Token, left_paren: Token, signatures: tuple[Any, ...], body: ast.Kind) -> ast.Kind:
    """Curries ALL(A,B::K1 C::K2) K into ALL(A::K1) ALL(B::K1) ALL(C::K2) K (Cardelli's ALL(TypeSignature)Kind)."""
    kind = body
    for i in reversed(range(len(signatures))):
        sig = signatures[i]
        kind = ast.KindAll(
            param_name=getattr(sig, "name", "_"),
            param_kind=getattr(sig, "bound", ast.KindType(offset=left_paren.offset)),
            body_kind=kind,
            offset=all_token.offset if i == 0 else getattr(sig, "offset", left_paren.offset),
        )
    return kind


def _curried_type(param_groups: tuple[tuple[Any, ...], ...], result_type: ast.Type, offset: int) -> ast.Type:
    """The type All(group1) ... All(groupN) result_type of a curried function signature."""
    current_type = result_type
    for group in reversed(param_groups):
        current_type = ast.TypeAll(
            quantifiers=tuple(
                ast.Quantifier(
                    name=getattr(sig, "name", "_") or "_",
                    bound=(
                        ast.KindPower(bound=sig.type_sig)
                        if hasattr(sig, "type_sig") and sig.type_sig is not None
                        else getattr(sig, "bound", ast.KindType(offset=offset))
                    ),
                    mode=getattr(sig, "mode", ast.ParamMode.VALUE),
                    is_type=isinstance(sig, ast.TypeFormal),
                    offset=getattr(sig, "offset", offset),
                )
                for sig in group
            ),
            result_type=current_type,
            offset=offset,
        )
    return current_type


def _split_params(group: tuple[Any, ...]) -> tuple[tuple[ast.TypeFormal, ...], tuple[ast.FormalParam, ...]]:
    """Splits one parenthesized parameter group into its type and value parameters."""
    type_params = tuple(sig for sig in group if isinstance(sig, ast.TypeFormal))
    value_params = tuple(
        ast.FormalParam(name=sig.name, type_annot=sig.type_sig, mode=sig.mode, offset=sig.offset)
        for sig in group
        if isinstance(sig, ast.FieldSig) and sig.name is not None
    )
    return type_params, value_params


def _curried_fun(
    param_groups: tuple[tuple[Any, ...], ...],
    return_type: Optional[ast.Type],
    body: ast.Expr,
    offset: int,
) -> ast.Expr:
    """Nests one ExprFun per parameter group; the return type annotates the innermost one."""
    if not param_groups:
        return ast.ExprFun(params=(), return_type=return_type, body=body, type_params=(), offset=offset)
    current_body = body
    for i in reversed(range(len(param_groups))):
        type_params, value_params = _split_params(param_groups[i])
        current_body = ast.ExprFun(
            params=value_params,
            return_type=return_type if i == len(param_groups) - 1 else None,
            body=current_body,
            type_params=type_params,
            offset=offset,
        )
    return current_body


def _build_curried_field_sig(
    var_token: Optional[Token],
    out_token: Optional[Token],
    identifiers: tuple[str, ...],
    param_groups: tuple[tuple[Any, ...], ...],
    colon_token: Token,
    return_type: ast.Type,
) -> tuple[ast.FieldSig, ...]:
    field_type = _curried_type(param_groups, return_type, colon_token.offset)
    mode = _mode(var_token, out_token)
    return tuple(
        ast.FieldSig(name=name, type_sig=field_type, mode=mode, offset=colon_token.offset)
        for name in identifiers
    )


def _build_curried_value_decl(
    var_token: Optional[Token],
    ident_token: Token,
    param_groups: tuple[tuple[Any, ...], ...],
    return_type: Optional[ast.Type],
    val_expr: ast.Expr,
) -> ast.LetValueBinding:
    def binding(value: ast.Expr, params: tuple[ast.FormalParam, ...], type_annot: Optional[ast.Type]):
        return ast.LetValueBinding(
            name=ident_token.lexeme,
            value=value,
            params=params,
            type_annot=type_annot,
            is_var=bool(var_token),
            offset=ident_token.offset,
        )

    if not param_groups:
        return binding(val_expr, (), return_type)
    if len(param_groups) == 1:
        type_params, value_params = _split_params(param_groups[0])
        if not type_params and value_params:
            # let f(x: Int): Int = ... keeps its parameters on the binding.
            return binding(val_expr, value_params, return_type)
    full_type_annot = (
        _curried_type(param_groups, return_type, ident_token.offset) if return_type is not None else None
    )
    return binding(_curried_fun(param_groups, return_type, val_expr, ident_token.offset), (), full_type_annot)


def _build_type_decl(
    ident_token: Token,
    param_groups: tuple[tuple[ast.TypeFormal, ...], ...],
    kind_bound: Optional[ast.Kind],
    type_node: ast.Type,
) -> ast.LetTypeBinding:
    if not param_groups:
        return ast.LetTypeBinding(
            name=ident_token.lexeme, type_val=type_node, bound=kind_bound, offset=ident_token.offset
        )
    type_fun = ast.TypeFun(
        params=tuple(formal for group in param_groups for formal in group),
        result_kind=kind_bound,
        body=type_node,
        offset=ident_token.offset,
    )
    return ast.LetTypeBinding(name=ident_token.lexeme, type_val=type_fun, bound=None, offset=ident_token.offset)


def _build_def_type(def_token: Token, rec_token: Optional[Token], decl: ast.LetTypeBinding) -> ast.DefTypeBinding:
    return ast.DefTypeBinding(
        name=decl.name,
        type_val=decl.type_val,
        params=decl.params,
        bound=decl.bound,
        is_rec=bool(rec_token),
        offset=def_token.offset,
    )


# --- case / inspect / try branches ---
# Each `when` clause matches as a tuple that is unpacked into one of these builders.

def _case_branch(when_token: Token, tags: tuple[str, ...], binder: Any, body: tuple[Any, ...]) -> ast.CaseBranch:
    binder_token, binder_type = binder or (None, None)
    return ast.CaseBranch(
        tags=tags,
        binder=binder_token.lexeme if binder_token else None,
        binder_type=binder_type,
        body=_body(body, when_token.offset),
        offset=when_token.offset,
    )


def _inspect_branch(when_token: Token, match_type: ast.Type, binder: Any, body: tuple[Any, ...]) -> ast.InspectBranch:
    names, binder_type = binder or ((), None)
    return ast.InspectBranch(
        match_type=match_type,
        binders=tuple((name, binder_type) for name in names),
        body=_body(body, when_token.offset),
        offset=when_token.offset,
    )


def _try_branch(when_token: Token, exc_pattern: ast.Expr, binder: Any, body: tuple[Any, ...]) -> ast.TryBranch:
    binder_token, binder_type = binder or (None, None)
    return ast.TryBranch(
        exc_pattern=exc_pattern,
        binder=binder_token.lexeme if binder_token else None,
        binder_type=binder_type,
        body=_body(body, when_token.offset),
        offset=when_token.offset,
    )


# --- imports ---

def _module_import(entries: tuple[tuple[str, str], ...], colon_token: Token, iface_path: str) -> ast.ImportItem:
    """m1 = p1, m2 = p2 : IfacePath  or  p1, p2 : IfacePath"""
    names = tuple(name for name, _ in entries)
    paths = tuple(path for _, path in entries)
    return ast.ImportItem(
        names=names,
        interface_name=_basename(iface_path),
        module_paths=paths if any("/" in p for p in paths) or paths != names else None,
        interface_path=iface_path if "/" in iface_path else None,
        offset=colon_token.offset,
    )


# ============================================================================
# 3. Quest Grammar Definition Builder
# ============================================================================

def build_quest_grammar() -> None:
    for target in ALL_SYNTAX_TARGETS:
        target.rules.clear()

    T = MatchToken
    TK = TokenKind
    Opt = Optional
    Rep = Repeated

    def P(kind: TokenKind, lexeme: str | None = None) -> MatchToken:
        """A token that must match but is not passed to the rule's action (punctuation, etc.)."""
        return MatchToken(kind, lexeme, silent=True)

    # ------------------------------------------------------------------------
    # Helper: Identifiers & Lists
    # ------------------------------------------------------------------------
    IDE.add_rule((T(TK.IDENT),), lambda ident_token: ident_token)
    IDE.add_rule((T(TK.SYMBOLIC_INFIX),), lambda token: token)

    # IdeList: ide {, ide}
    IDE_LIST.add_rule(
        (SepBy(IDE, P(TK.COMMA)),),
        lambda ident_tokens: tuple(token.lexeme for token in ident_tokens),
    )

    # Path: ident {/ ident}
    PATH.add_rule(
        (SepBy(T(TK.IDENT), P(TK.SYMBOLIC_INFIX, "/")),),
        lambda ident_tokens: "/".join(token.lexeme for token in ident_tokens),
    )

    # PathList: Path {, Path}
    PATH_LIST.add_rule((SepBy(PATH, P(TK.COMMA)),), lambda paths: paths)

    # ModuleEntry: ident = Path | Path
    MODULE_ENTRY.add_rule(
        (T(TK.IDENT), P(TK.EQUAL), PATH),
        lambda ident, path: (ident.lexeme, path),
    )
    MODULE_ENTRY.add_rule((PATH,), lambda path: (_basename(path), path))

    # ModuleEntryList: ModuleEntry {, ModuleEntry}
    MODULE_ENTRY_LIST.add_rule((SepBy(MODULE_ENTRY, P(TK.COMMA)),), lambda entries: entries)

    # ------------------------------------------------------------------------
    # Kinds (Level 2)
    # ------------------------------------------------------------------------
    # ALL ( TypeSignature ) Kind
    KIND.add_rule((T(TK.KW_ALL_KIND), T(TK.LPAREN), SIGNATURE, P(TK.RPAREN), KIND), _build_kind_all)
    # PRIMARY_KIND
    KIND.add_rule((PRIMARY_KIND,), lambda primary_kind: primary_kind)

    # TYPE
    PRIMARY_KIND.add_rule((T(TK.KW_TYPE),), lambda type_token: ast.KindType(offset=type_token.offset))
    # POWER ( Type )
    PRIMARY_KIND.add_rule(
        (T(TK.KW_POWER), P(TK.LPAREN), TYPE, P(TK.RPAREN)),
        lambda power_token, bound_type: ast.KindPower(bound=bound_type, offset=power_token.offset),
    )
    # ide _ ide (Manifest kind)
    PRIMARY_KIND.add_rule(
        (T(TK.IDENT), P(TK.UNDERSCORE), T(TK.IDENT)),
        lambda interface_ident, kind_ident: ast.KindManifest(
            interface_name=interface_ident.lexeme,
            kind_name=kind_ident.lexeme,
            offset=interface_ident.offset,
        ),
    )
    # ide (Kind identifier)
    PRIMARY_KIND.add_rule(
        (T(TK.IDENT),),
        lambda ident_token: ast.KindId(name=ident_token.lexeme, offset=ident_token.offset),
    )
    # { Kind }
    PRIMARY_KIND.add_rule((P(TK.LBRACE), KIND, P(TK.RBRACE)), lambda inner_kind: inner_kind)

    # ------------------------------------------------------------------------
    # Types (Level 1)
    # ------------------------------------------------------------------------
    # POSTFIX_TYPE [ InfixTail ]
    TYPE.add_rule(
        (POSTFIX_TYPE, Opt(T(TK.SYMBOLIC_INFIX), TYPE)),
        lambda left, tail: (
            ast.TypeInfix(left=left, op=tail[0].lexeme, right=tail[1], offset=left.offset)
            if tail
            else left
        ),
    )

    POSTFIX_TYPE.add_rule((PRIMARY_TYPE, Rep(POSTFIX_TYPE_OP)), _apply_postfix)

    # . ide
    POSTFIX_TYPE_OP.add_rule((P(TK.DOT), T(TK.IDENT)), lambda ident_token: _select_type(ident_token.lexeme))
    # ( TypeBinding )
    POSTFIX_TYPE_OP.add_rule(
        (P(TK.LPAREN), Opt(TYPE_BINDING), P(TK.RPAREN)),
        lambda arguments: lambda current: ast.TypeApp(
            constructor=current, arguments=arguments, offset=current.offset
        ),
    )
    # _ ide
    POSTFIX_TYPE_OP.add_rule(
        (P(TK.UNDERSCORE), T(TK.IDENT)),
        lambda ident_token: lambda current: ast.TypeManifest(
            module_name=getattr(current, "path", ("_",))[-1],
            type_name=ident_token.lexeme,
            offset=current.offset,
        ),
    )

    # All ( Signature ) Type
    PRIMARY_TYPE.add_rule(
        (T(TK.KW_ALL), T(TK.LPAREN), SIGNATURE, P(TK.RPAREN), TYPE),
        lambda all_token, left_paren, signatures, result_type: ast.TypeAll(
            quantifiers=tuple(
                ast.Quantifier(
                    name=getattr(sig, "name", "_") or "_",
                    bound=(
                        getattr(sig, "bound", None)
                        or (
                            ast.KindPower(bound=sig.type_sig, offset=sig.offset)
                            if hasattr(sig, "type_sig")
                            else ast.KindType(offset=left_paren.offset)
                        )
                    ),
                    mode=getattr(sig, "mode", ast.ParamMode.VALUE),
                    is_type=isinstance(sig, ast.TypeFormal),
                    offset=getattr(sig, "offset", left_paren.offset),
                )
                for sig in signatures
            ),
            result_type=result_type,
            offset=all_token.offset,
        ),
    )
    # Tuple Signature end
    PRIMARY_TYPE.add_rule(
        (T(TK.KW_TUPLE_TYPE), SIGNATURE, P(TK.KW_END)),
        lambda tuple_token, signatures: ast.TypeTuple(fields=signatures, offset=tuple_token.offset),
    )
    # Option OptionSignature end
    PRIMARY_TYPE.add_rule(
        (T(TK.KW_OPTION_TYPE), OPTION_SIGNATURE, P(TK.KW_END)),
        lambda option_token, option_signatures: ast.TypeOption(
            variants=option_signatures, offset=option_token.offset
        ),
    )
    # Record ValueSignature end
    PRIMARY_TYPE.add_rule(
        (T(TK.KW_RECORD_TYPE), VALUE_SIGNATURE, P(TK.KW_END)),
        lambda record_token, signatures: ast.TypeRecord(fields=signatures, offset=record_token.offset),
    )
    # Variant ValueSignature end
    PRIMARY_TYPE.add_rule(
        (T(TK.KW_VARIANT_TYPE), VALUE_SIGNATURE, P(TK.KW_END)),
        lambda variant_token, signatures: ast.TypeVariant(
            fields=tuple(
                ast.VariantFieldSig(tag=sig.name, type_sig=sig.type_sig, is_var=sig.is_var, offset=sig.offset)
                for sig in signatures
            ),
            offset=variant_token.offset,
        ),
    )
    # Auto [ide] HasKind with Signature end
    PRIMARY_TYPE.add_rule(
        (T(TK.KW_AUTO_TYPE), Opt(T(TK.IDENT)), HAS_KIND, P(TK.KW_WITH), SIGNATURE, P(TK.KW_END)),
        lambda auto_token, ident_token, kind_bound, signatures: ast.TypeAuto(
            type_param=ident_token.lexeme if ident_token else None,
            kind_bound=kind_bound,
            signature=signatures,
            offset=auto_token.offset,
        ),
    )
    # Fun ( TypeFormals ) [HasKind] Type
    PRIMARY_TYPE.add_rule(
        (T(TK.KW_FUN_TYPE), P(TK.LPAREN), TYPE_FORMALS, P(TK.RPAREN), Opt(HAS_KIND), TYPE),
        lambda fun_token, formals, kind_bound, body_type: ast.TypeFun(
            params=formals, result_kind=kind_bound, body=body_type, offset=fun_token.offset
        ),
    )
    # Rec ( ide HasKind ) Type
    PRIMARY_TYPE.add_rule(
        (T(TK.KW_REC_TYPE), P(TK.LPAREN), T(TK.IDENT), HAS_KIND, P(TK.RPAREN), TYPE),
        lambda rec_token, ident_token, kind_bound, body_type: ast.TypeRec(
            var_name=ident_token.lexeme, bound=kind_bound, body=body_type, offset=rec_token.offset
        ),
    )
    # Array ( Type ), Var ( Type ), Out ( Type )
    for keyword, node_class in (
        (TK.KW_ARRAY_TYPE, ast.TypeArray),
        (TK.KW_VAR_TYPE, ast.TypeVar),
        (TK.KW_OUT_TYPE, ast.TypeOut),
    ):
        PRIMARY_TYPE.add_rule(
            (T(keyword), P(TK.LPAREN), TYPE, P(TK.RPAREN)),
            lambda keyword_token, element_type, node_class=node_class: node_class(
                element_type=element_type, offset=keyword_token.offset
            ),
        )
    # ide _ ide (Manifest type)
    PRIMARY_TYPE.add_rule(
        (T(TK.IDENT), P(TK.UNDERSCORE), T(TK.IDENT)),
        lambda module_ident, type_ident: ast.TypeManifest(
            module_name=module_ident.lexeme,
            type_name=type_ident.lexeme,
            offset=module_ident.offset,
        ),
    )
    # ide (Named type: Int, Real, Bool, String, Char, Ok, Exception, or User Type)
    PRIMARY_TYPE.add_rule(
        (T(TK.IDENT),),
        lambda ident_token: ast.TypePath(path=(ident_token.lexeme,), offset=ident_token.offset),
    )
    PRIMARY_TYPE.add_rule(
        (T(TK.KW_EXCEPTION_TYPE),),
        lambda exc_token: ast.TypePath(path=("Exception",), offset=exc_token.offset),
    )
    # { infix }
    PRIMARY_TYPE.add_rule(
        (P(TK.LBRACE), T(TK.SYMBOLIC_INFIX), P(TK.RBRACE)),
        lambda token: ast.TypePath(path=(token.lexeme,), offset=token.offset),
    )
    # infix ( TypeBinding )
    PRIMARY_TYPE.add_rule(
        (T(TK.SYMBOLIC_INFIX), P(TK.LPAREN), Opt(TYPE_BINDING), P(TK.RPAREN)),
        lambda token, arguments: ast.TypeApp(
            constructor=ast.TypePath(path=(token.lexeme,), offset=token.offset),
            arguments=arguments,
            offset=token.offset,
        ),
    )
    # { Type }
    PRIMARY_TYPE.add_rule((P(TK.LBRACE), TYPE, P(TK.RBRACE)), lambda inner_type: inner_type)
    # external "c_type"
    PRIMARY_TYPE.add_rule(
        (T(TK.KW_EXTERNAL), T(TK.STRING_LIT)),
        lambda ext_token, str_token: ast.TypeExternal(c_type=str_token.value, offset=ext_token.offset),
    )

    # ------------------------------------------------------------------------
    # Signatures
    # ------------------------------------------------------------------------
    # Every TypeSignature rule yields a tuple of signature items.
    SIGNATURE.add_rule(
        (Rep(TYPE_SIGNATURE),),
        lambda groups: tuple(item for group in groups for item in group),
    )

    # DEF KindDecl
    TYPE_SIGNATURE.add_rule((P(TK.KW_DEF_KIND), KIND_DECL), lambda kind_declaration: (kind_declaration,))
    # Def [Rec] TypeDecl
    TYPE_SIGNATURE.add_rule(
        (T(TK.KW_DEF), Opt(T(TK.KW_REC_TYPE)), TYPE_DECL),
        lambda def_token, rec_token, type_declaration: (
            _build_def_type(def_token, rec_token, type_declaration) if rec_token else type_declaration,
        ),
    )
    # [var | out] IdeList {"(" Signature ")"} : Type (ValueFormals; plain fields have no groups)
    TYPE_SIGNATURE.add_rule(
        (
            Opt(T(TK.KW_VAR)),
            Opt(T(TK.KW_OUT)),
            IDE_LIST,
            Rep(P(TK.LPAREN), SIGNATURE, P(TK.RPAREN)),
            T(TK.COLON),
            TYPE,
        ),
        _build_curried_field_sig,
    )
    # [IdeList] HasKind
    TYPE_SIGNATURE.add_rule((TYPE_FORMAL,), lambda formals: formals)
    TYPE_FORMAL.add_rule(
        (Opt(IDE_LIST), HAS_KIND),
        lambda identifiers, kind_bound: tuple(
            ast.TypeFormal(name=name, bound=kind_bound, offset=kind_bound.offset)
            for name in (identifiers or ("_",))
        ),
    )
    # Operator parameters (Fun and Let X(...)) are type formals only: X::K or X <: T
    TYPE_FORMALS.add_rule(
        (Rep(TYPE_FORMAL),),
        lambda formal_groups: tuple(formal for group in formal_groups for formal in group),
    )
    # HasMutType (Anonymous tuple/signature field :Int or :Var(Int) or :Out(Int))
    TYPE_SIGNATURE.add_rule((HAS_MUT_TYPE,), lambda mut_field: (mut_field,))

    # [var] IdeList HasType (Record/Variant type signatures)
    VALUE_SIGNATURE.add_rule(
        (Rep(Opt(T(TK.KW_VAR)), IDE_LIST, HAS_TYPE, Opt(P(TK.SEMICOLON))),),
        lambda fields: tuple(
            ast.RecordFieldSig(name=name, type_sig=field_type, is_var=bool(var_token), offset=field_type.offset)
            for var_token, names, field_type in fields
            for name in names
        ),
    )

    # IdeList [with Signature end]
    OPTION_SIGNATURE.add_rule(
        (Rep(IDE_LIST, Opt(P(TK.KW_WITH), SIGNATURE, P(TK.KW_END))),),
        lambda options: tuple(
            ast.OptionFieldSig(tag=tag, payload_sig=payload or (), offset=0)
            for tags, payload in options
            for tag in tags
        ),
    )

    # ------------------------------------------------------------------------
    # Values and Expressions (Level 0)
    # ------------------------------------------------------------------------
    for infix_kind in (TK.SYMBOLIC_INFIX, TK.KW_IS, TK.KW_ISNOT, TK.KW_ANDIF, TK.KW_ORIF, TK.ASSIGN):
        INFIX_OP.add_rule((T(infix_kind),), lambda token: token.lexeme)

    # POSTFIX_VALUE [ InfixOp Value ]
    VALUE.add_rule(
        (POSTFIX_VALUE, Opt(INFIX_OP, VALUE)),
        lambda left, tail: (
            ast.ExprInfix(left=left, op=tail[0], right=tail[1], offset=left.offset)
            if tail
            else left
        ),
    )

    POSTFIX_VALUE.add_rule((PRIMARY_VALUE, Rep(POSTFIX_OP)), _apply_postfix)

    # . ide, ? ide, ! ide
    for punctuation, node_class in (
        (TK.DOT, ast.ExprSelect),
        (TK.QUESTION, ast.ExprVariantCheck),
        (TK.BANG, ast.ExprVariantAssert),
    ):
        field = "field" if node_class is ast.ExprSelect else "tag"
        POSTFIX_OP.add_rule(
            (P(punctuation), T(TK.IDENT)),
            lambda ident_token, node_class=node_class, field=field: lambda target: node_class(
                target=target, **{field: ident_token.lexeme}, offset=target.offset
            ),
        )
    # ( Binding )
    POSTFIX_OP.add_rule(
        (P(TK.LPAREN), Opt(BINDING), P(TK.RPAREN)),
        lambda arguments: lambda func: ast.ExprApp(func=func, args=_call_args(arguments), offset=func.offset),
    )
    # [ Value ]
    POSTFIX_OP.add_rule(
        (P(TK.LBRACKET), VALUE, P(TK.RBRACKET)),
        lambda index_expr: lambda target: ast.ExprIndex(target=target, index=index_expr, offset=target.offset),
    )
    # Listfix application: f of(count init) and f of ... end
    POSTFIX_OP.add_rule(
        (T(TK.KW_OF), P(TK.LPAREN), VALUE, VALUE, P(TK.RPAREN)),
        lambda of_token, count_expr, init_expr: lambda func: ast.ExprApp(
            func=func,
            args=(ast.ExprArrayRep(count=count_expr, init_val=init_expr, offset=of_token.offset),),
            offset=func.offset,
        ),
    )
    POSTFIX_OP.add_rule(
        (T(TK.KW_OF), Opt(BINDING), P(TK.KW_END)),
        lambda of_token, bindings: lambda func: ast.ExprApp(
            func=func,
            args=(_build_array_expr(of_token.offset, bindings),),
            offset=func.offset,
        ),
    )

    # Literals
    for literal_kind, node_class in (
        (TK.INT_LIT, ast.ExprInt),
        (TK.REAL_LIT, ast.ExprReal),
        (TK.CHAR_LIT, ast.ExprChar),
        (TK.STRING_LIT, ast.ExprString),
    ):
        PRIMARY_VALUE.add_rule(
            (T(literal_kind),),
            lambda token, node_class=node_class: node_class(
                value=token.value, lexeme=token.lexeme, offset=token.offset
            ),
        )
    PRIMARY_VALUE.add_rule((T(TK.KW_TRUE),), lambda token: ast.ExprBool(value=True, offset=token.offset))
    PRIMARY_VALUE.add_rule((T(TK.KW_FALSE),), lambda token: ast.ExprBool(value=False, offset=token.offset))
    PRIMARY_VALUE.add_rule((T(TK.KW_OK),), lambda token: ast.ExprOk(offset=token.offset))
    PRIMARY_VALUE.add_rule((T(TK.KW_EXIT),), lambda token: ast.ExprExit(offset=token.offset))
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_EXTERNAL), T(TK.STRING_LIT)),
        lambda ext_token, str_token: ast.ExprExternal(symbol=str_token.value, offset=ext_token.offset),
    )

    # if Binding [then Binding] {elsif Binding [then Binding]} [else Binding] end
    PRIMARY_VALUE.add_rule(
        (
            T(TK.KW_IF),
            VALUE,
            Opt(P(TK.KW_THEN)),
            BINDING,
            Rep(T(TK.KW_ELSIF), VALUE, Opt(P(TK.KW_THEN)), BINDING),
            Opt(P(TK.KW_ELSE), BINDING),
            P(TK.KW_END),
        ),
        lambda if_token, condition, then_bindings, elsifs, else_bindings: ast.ExprIf(
            cond=condition,
            then_branch=_body(then_bindings, if_token.offset),
            elsifs=tuple(
                (elsif_condition, _body(elsif_bindings, elsif_token.offset))
                for elsif_token, elsif_condition, elsif_bindings in elsifs
            ),
            else_branch=_optional_body(else_bindings, if_token.offset),
            offset=if_token.offset,
        ),
    )

    # begin Binding end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_BEGIN), BINDING, P(TK.KW_END)),
        lambda begin_token, bindings: ast.ExprBlock(bindings=bindings, offset=begin_token.offset),
    )

    # loop Binding end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_LOOP), BINDING, P(TK.KW_END)),
        lambda loop_token, bindings: ast.ExprLoop(body=_body(bindings, loop_token.offset), offset=loop_token.offset),
    )

    # while Binding do Binding end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_WHILE), VALUE, P(TK.KW_DO), BINDING, P(TK.KW_END)),
        lambda while_token, condition, body_bindings: ast.ExprWhile(
            cond=condition, body=_body(body_bindings, while_token.offset), offset=while_token.offset
        ),
    )

    # for ide = Binding (upto | downto) Binding do Binding end
    PRIMARY_VALUE.add_rule(
        (
            T(TK.KW_FOR),
            T(TK.IDENT),
            P(TK.EQUAL),
            VALUE,
            Opt(P(TK.KW_UPTO)),
            Opt(T(TK.KW_DOWNTO)),
            VALUE,
            P(TK.KW_DO),
            BINDING,
            P(TK.KW_END),
        ),
        lambda for_token, ident_token, start_val, downto_token, stop_val, body_bindings: ast.ExprFor(
            var_name=ident_token.lexeme,
            start=start_val,
            is_downto=bool(downto_token),
            stop=stop_val,
            body=_body(body_bindings, for_token.offset),
            offset=for_token.offset,
        ),
    )

    # fun { ( Signature ) } [: Type] Value
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_FUN), Rep(P(TK.LPAREN), SIGNATURE, P(TK.RPAREN)), Opt(P(TK.COLON), TYPE), VALUE),
        lambda fun_token, param_groups, return_type, body_expr: _curried_fun(
            param_groups, return_type, body_expr, fun_token.offset
        ),
    )

    # tuple Binding end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_TUPLE), BINDING, P(TK.KW_END)),
        lambda tuple_token, bindings: ast.ExprTuple(
            fields=_process_tuple_bindings(bindings), offset=tuple_token.offset
        ),
    )

    # record ValueBinding end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_RECORD), VALUE_BINDING, P(TK.KW_END)),
        lambda record_token, bindings: ast.ExprRecord(fields=bindings, offset=record_token.offset),
    )

    # array of ( Binding end | ( Value Value ) )
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_ARRAY), P(TK.KW_OF), P(TK.LPAREN), VALUE, VALUE, P(TK.RPAREN)),
        lambda array_token, count_expr, init_expr: ast.ExprArrayRep(
            count=count_expr, init_val=init_expr, offset=array_token.offset
        ),
    )
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_ARRAY), P(TK.KW_OF), Opt(BINDING), P(TK.KW_END)),
        lambda array_token, bindings: _build_array_expr(array_token.offset, bindings),
    )

    # option (ide | ordinal(Value)) of Type [with Binding] end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_OPTION), IDE, P(TK.KW_OF), TYPE, Opt(P(TK.KW_WITH), BINDING), P(TK.KW_END)),
        lambda option_token, ide, option_type, with_bindings: ast.ExprOption(
            tag=ide.lexeme,
            option_type=option_type,
            payload=_build_option_payload(with_bindings, option_token.offset),
            offset=option_token.offset,
        ),
    )
    PRIMARY_VALUE.add_rule(
        (
            T(TK.KW_OPTION),
            P(TK.KW_ORDINAL),
            P(TK.LPAREN),
            VALUE,
            P(TK.RPAREN),
            P(TK.KW_OF),
            TYPE,
            Opt(P(TK.KW_WITH), BINDING),
            P(TK.KW_END),
        ),
        lambda option_token, ord_val, option_type, with_bindings: ast.ExprOption(
            tag=None,
            option_type=option_type,
            payload=_build_option_payload(with_bindings, option_token.offset),
            ordinal_expr=ord_val,
            offset=option_token.offset,
        ),
    )

    # variant [var] ide of Type [with Value] end
    PRIMARY_VALUE.add_rule(
        (
            T(TK.KW_VARIANT),
            Opt(T(TK.KW_VAR)),
            T(TK.IDENT),
            P(TK.KW_OF),
            TYPE,
            Opt(P(TK.KW_WITH), VALUE),
            P(TK.KW_END),
        ),
        lambda variant_token, var_token, ident_token, variant_type, payload: ast.ExprVariant(
            tag=ident_token.lexeme,
            variant_type=variant_type,
            is_var=bool(var_token),
            payload=payload,
            offset=variant_token.offset,
        ),
    )

    # auto [let ide [HasKind] =] : Type with Binding end
    PRIMARY_VALUE.add_rule(
        (
            T(TK.KW_AUTO),
            Opt(P(TK.KW_LET), T(TK.IDENT), Opt(HAS_KIND), P(TK.EQUAL)),
            P(TK.COLON),
            TYPE,
            T(TK.KW_WITH),
            Opt(BINDING),
            P(TK.KW_END),
        ),
        lambda auto_token, witness_decl, witness_type, with_token, bindings: ast.ExprAuto(
            witness_type=witness_type,
            payload=ast.ExprTuple(fields=_process_tuple_bindings(bindings), offset=with_token.offset),
            witness_name=witness_decl[0].lexeme if witness_decl else None,
            witness_bound=witness_decl[1] if witness_decl else None,
            offset=auto_token.offset,
        ),
    )

    # case Value CaseBranches end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_CASE), VALUE, CASE_BRANCHES, P(TK.KW_END)),
        lambda case_token, target_expr, branches: ast.ExprCase(
            target=target_expr, branches=branches[0], else_branch=branches[1], offset=case_token.offset
        ),
    )

    # inspect Value InspectBranches end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_INSPECT), VALUE, INSPECT_BRANCHES, P(TK.KW_END)),
        lambda inspect_token, target_expr, branches: ast.ExprInspect(
            target=target_expr, branches=branches[0], else_branch=branches[1], offset=inspect_token.offset
        ),
    )

    # exception ide [: Type] end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_EXCEPTION), T(TK.IDENT), Opt(P(TK.COLON), TYPE), P(TK.KW_END)),
        lambda exc_token, ident_token, type_annot: ast.ExprException(
            name=ident_token.lexeme, type_annot=type_annot, offset=exc_token.offset
        ),
    )

    # raise Value [with Value] [as Type] end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_RAISE), VALUE, Opt(P(TK.KW_WITH), VALUE), Opt(P(TK.KW_AS), TYPE), P(TK.KW_END)),
        lambda raise_token, exc_expr, payload, as_type: ast.ExprRaise(
            exc=exc_expr, payload=payload, as_type=as_type, offset=raise_token.offset
        ),
    )

    # try Binding TryBranches end
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_TRY), BINDING, TRY_BRANCHES, P(TK.KW_END)),
        lambda try_token, body_bindings, branches: ast.ExprTry(
            body=_body(body_bindings, try_token.offset),
            branches=branches[0],
            else_branch=branches[1],
            offset=try_token.offset,
        ),
    )

    # var ( Value )
    PRIMARY_VALUE.add_rule(
        (T(TK.KW_VAR), P(TK.LPAREN), VALUE, P(TK.RPAREN)),
        lambda var_token, cell_value: ast.ExprVarCell(value=cell_value, offset=var_token.offset),
    )

    # @ Value
    PRIMARY_VALUE.add_rule(
        (T(TK.AT), VALUE),
        lambda at_token, target_expr: ast.ExprDerefCell(target=target_expr, offset=at_token.offset),
    )

    # ide (Identifier)
    PRIMARY_VALUE.add_rule(
        (T(TK.IDENT),),
        lambda ident_token: ast.ExprId(name=ident_token.lexeme, offset=ident_token.offset),
    )
    # { infix } (Stand-alone infix identifier, e.g. {+})
    PRIMARY_VALUE.add_rule(
        (P(TK.LBRACE), T(TK.SYMBOLIC_INFIX), P(TK.RBRACE)),
        lambda token: ast.ExprId(name=token.lexeme, offset=token.offset),
    )
    # prefix infix application: +(x y)
    PRIMARY_VALUE.add_rule(
        (T(TK.SYMBOLIC_INFIX), P(TK.LPAREN), Opt(BINDING), P(TK.RPAREN)),
        lambda token, arguments: ast.ExprApp(
            func=ast.ExprId(name=token.lexeme, offset=token.offset),
            args=_call_args(arguments),
            offset=token.offset,
        ),
    )

    # { Value }
    PRIMARY_VALUE.add_rule((P(TK.LBRACE), VALUE, P(TK.RBRACE)), lambda inner_expr: inner_expr)

    # Monadic Operators: not, extent, ordinal (Cardelli §4.2, §4.3, §4.5), applied or stand-alone
    for keyword in (TK.KW_NOT, TK.KW_EXTENT, TK.KW_ORDINAL):
        PRIMARY_VALUE.add_rule(
            (T(keyword), POSTFIX_VALUE),
            lambda token, operand: ast.ExprApp(
                func=ast.ExprId(name=token.lexeme, offset=token.offset),
                args=(operand,),
                offset=token.offset,
            ),
        )
        PRIMARY_VALUE.add_rule((T(keyword),), lambda token: ast.ExprId(name=token.lexeme, offset=token.offset))

    # ------------------------------------------------------------------------
    # Bindings (Inside Blocks, Tuples, Phrases)
    # ------------------------------------------------------------------------
    BINDING.add_rule((Rep(PHRASE, Opt(P(TK.SEMICOLON))),), lambda phrases: phrases)

    TYPE_BINDING.add_rule((Rep(TYPE),), lambda types: types)

    VALUE_BINDING.add_rule(
        (Rep(Opt(T(TK.KW_VAR)), T(TK.IDENT), P(TK.EQUAL), VALUE, Opt(P(TK.SEMICOLON))),),
        lambda items: tuple(
            ast.RecordBinding(
                name=ident_token.lexeme, value=value, is_var=bool(var_token), offset=ident_token.offset
            )
            for var_token, ident_token, value in items
        ),
    )

    # ------------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------------
    KIND_DECL.add_rule(
        (IDE, P(TK.EQUAL), KIND),
        lambda ident_token, kind_node: ast.DefKindBinding(
            name=ident_token.lexeme, kind_val=kind_node, offset=ident_token.offset
        ),
    )

    TYPE_DECL.add_rule(
        (IDE, Rep(P(TK.LPAREN), TYPE_FORMALS, P(TK.RPAREN)), Opt(HAS_KIND), P(TK.EQUAL), TYPE),
        _build_type_decl,
    )

    VALUE_DECL.add_rule(
        (
            Opt(T(TK.KW_VAR)),
            IDE,
            Rep(P(TK.LPAREN), SIGNATURE, P(TK.RPAREN)),
            Opt(P(TK.COLON), TYPE),
            P(TK.EQUAL),
            VALUE,
        ),
        _build_curried_value_decl,
    )

    # ------------------------------------------------------------------------
    # Case, Inspect, Try Branches: {when Pattern [with Binder] then Binding} [else Binding]
    # Each yields (branches, else_body).
    # ------------------------------------------------------------------------
    for branches_target, pattern, binder, build_branch in (
        (CASE_BRANCHES, IDE_LIST, T(TK.IDENT), _case_branch),
        (INSPECT_BRANCHES, TYPE, IDE_LIST, _inspect_branch),
        (TRY_BRANCHES, VALUE, T(TK.IDENT), _try_branch),
    ):
        branches_target.add_rule(
            (
                Rep(T(TK.KW_WHEN), pattern, Opt(P(TK.KW_WITH), binder, Opt(P(TK.COLON), TYPE)), P(TK.KW_THEN), BINDING),
                Opt(P(TK.KW_ELSE), BINDING),
            ),
            lambda branches, else_bindings, build_branch=build_branch: (
                tuple(build_branch(*branch) for branch in branches),
                _optional_body(else_bindings, 0),
            ),
        )

    # ------------------------------------------------------------------------
    # HasType / HasMutType / HasKind
    # ------------------------------------------------------------------------
    HAS_TYPE.add_rule((P(TK.COLON), TYPE), lambda type_node: type_node)

    # : Var(Type), : Out(Type), var : Type, out : Type, : Type
    # (an anonymous field; its offset is that of the first token)
    for constructs, mode in (
        ((T(TK.COLON), P(TK.KW_VAR_TYPE), P(TK.LPAREN), TYPE, P(TK.RPAREN)), ast.ParamMode.VAR),
        ((T(TK.COLON), P(TK.KW_OUT_TYPE), P(TK.LPAREN), TYPE, P(TK.RPAREN)), ast.ParamMode.OUT),
        ((T(TK.KW_VAR), P(TK.COLON), TYPE), ast.ParamMode.VAR),
        ((T(TK.KW_OUT), P(TK.COLON), TYPE), ast.ParamMode.OUT),
        ((T(TK.COLON), TYPE), ast.ParamMode.VALUE),
    ):
        HAS_MUT_TYPE.add_rule(
            constructs,
            lambda first_token, type_node, mode=mode: ast.FieldSig(
                name=None, type_sig=type_node, mode=mode, offset=first_token.offset
            ),
        )

    HAS_KIND.add_rule(
        (T(TK.SUBTYPE), TYPE),
        lambda subtype_token, bound_type: ast.KindPower(bound=bound_type, offset=subtype_token.offset),
    )
    HAS_KIND.add_rule((P(TK.COLON_COLON), KIND), lambda kind_node: kind_node)

    # ------------------------------------------------------------------------
    # Phrases & Program (Top Level)
    # ------------------------------------------------------------------------
    # Interface
    PHRASE.add_rule(
        (
            Opt(T(TK.KW_UNSOUND)),
            T(TK.KW_INTERFACE),
            T(TK.IDENT),
            Opt(P(TK.KW_IMPORT), IMPORT),
            P(TK.KW_EXPORT),
            SIGNATURE,
            P(TK.KW_END),
        ),
        lambda unsound, interface_token, ident_token, imports, signatures: ast.InterfaceDecl(
            name=ident_token.lexeme,
            signatures=signatures,
            imports=imports or (),
            is_unsound=bool(unsound),
            offset=interface_token.offset,
        ),
    )
    # Module
    PHRASE.add_rule(
        (
            Opt(T(TK.KW_UNSOUND)),
            T(TK.KW_MODULE),
            T(TK.IDENT),
            P(TK.COLON),
            PATH,
            Opt(P(TK.KW_IMPORT), IMPORT),
            P(TK.KW_EXPORT),
            BINDING,
            P(TK.KW_END),
        ),
        lambda unsound, module_token, ident_token, interface_path, imports, bindings: ast.ModuleDecl(
            name=ident_token.lexeme,
            interface_name=interface_path,
            bindings=bindings,
            imports=imports or (),
            is_unsound=bool(unsound),
            offset=module_token.offset,
        ),
    )
    # Let [Rec] TypeDecl
    PHRASE.add_rule(
        (T(TK.KW_LET_TYPE), Opt(T(TK.KW_REC_TYPE)), TYPE_DECL),
        lambda let_token, rec_token, type_declaration: dataclasses.replace(
            type_declaration, is_rec=bool(rec_token), offset=let_token.offset
        ),
    )
    # let [rec] ValueDecl
    PHRASE.add_rule(
        (T(TK.KW_LET), Opt(T(TK.KW_REC)), VALUE_DECL),
        lambda let_token, rec_token, val_declaration: dataclasses.replace(
            val_declaration, is_rec=bool(rec_token), offset=let_token.offset
        ),
    )
    # var ValueDecl (allows 'var x = 0' inside tuples, blocks, or module phrases)
    PHRASE.add_rule(
        (T(TK.KW_VAR), VALUE_DECL),
        lambda var_token, val_declaration: dataclasses.replace(
            val_declaration, is_rec=False, is_var=True, offset=var_token.offset
        ),
    )
    # DEF KindDecl
    PHRASE.add_rule((P(TK.KW_DEF_KIND), KIND_DECL), lambda kind_declaration: kind_declaration)
    # Def [Rec] TypeDecl
    PHRASE.add_rule((T(TK.KW_DEF), Opt(T(TK.KW_REC_TYPE)), TYPE_DECL), _build_def_type)
    # : Type (TypeArgument in call bindings / phrases)
    PHRASE.add_rule(
        (T(TK.COLON), TYPE),
        lambda colon_token, type_node: ast.TypeArgument(type_val=type_node, offset=colon_token.offset),
    )
    # :: Kind (KindArgument in call bindings / phrases)
    PHRASE.add_rule(
        (T(TK.COLON_COLON), KIND),
        lambda colon_token, kind_node: ast.KindArgument(kind_val=kind_node, offset=colon_token.offset),
    )
    # Top-level Value Expression
    PHRASE.add_rule(
        (VALUE,),
        lambda value_expr: (
            ast.ExprStmt(expr=value_expr, offset=value_expr.offset)
            if isinstance(value_expr, ast.Expr)
            else value_expr
        ),
    )

    # import ImportList
    LINKAGE.add_rule(
        (T(TK.KW_IMPORT), IMPORT),
        lambda import_token, items: ast.ImportPhrase(items=items, offset=import_token.offset),
    )
    PHRASE.add_rule((LINKAGE,), lambda linkage: linkage)

    # 1. Dual alias with =: r1, r2 : Rnd = p1, p2 : IfacePath
    IMPORT_ITEM.add_rule(
        (IDE_LIST, T(TK.COLON), T(TK.IDENT), P(TK.EQUAL), PATH_LIST, P(TK.COLON), PATH),
        lambda names, colon_token, iface_ident, paths, iface_path: ast.ImportItem(
            names=names,
            interface_name=iface_ident.lexeme,
            module_paths=paths,
            interface_path=iface_path,
            offset=colon_token.offset,
        ),
    )

    # 2. Interface alias with module path: :Rnd = p1, p2 : IfacePath
    IMPORT_ITEM.add_rule(
        (T(TK.COLON), T(TK.IDENT), P(TK.EQUAL), PATH_LIST, P(TK.COLON), PATH),
        lambda colon_token, iface_ident, paths, iface_path: ast.ImportItem(
            names=tuple(_basename(p) for p in paths),
            interface_name=iface_ident.lexeme,
            module_paths=paths,
            interface_path=iface_path,
            offset=colon_token.offset,
        ),
    )

    # 3. Interface alias, interface-only: :Rnd = :IfacePath
    IMPORT_ITEM.add_rule(
        (T(TK.COLON), T(TK.IDENT), P(TK.EQUAL), P(TK.COLON), PATH),
        lambda colon_token, iface_ident, iface_path: ast.ImportItem(
            names=(),
            interface_name=iface_ident.lexeme,
            module_paths=None,
            interface_path=iface_path,
            offset=colon_token.offset,
        ),
    )

    # 4. Interface-only, unaliased: :IfacePath
    IMPORT_ITEM.add_rule(
        (T(TK.COLON), PATH),
        lambda colon_token, iface_path: ast.ImportItem(
            names=(),
            interface_name=_basename(iface_path),
            module_paths=None,
            interface_path=iface_path if "/" in iface_path else None,
            offset=colon_token.offset,
        ),
    )

    # 5. Module & interface (including module aliases and unaliased paths):
    #    m1 = p1, m2 = p2 : IfacePath  OR  p1, p2 : IfacePath
    IMPORT_ITEM.add_rule((MODULE_ENTRY_LIST, T(TK.COLON), PATH), _module_import)

    IMPORT.add_rule((Rep(IMPORT_ITEM, Opt(P(TK.SEMICOLON))),), lambda items: items)

    PROGRAM.add_rule(
        (Rep(PHRASE, Opt(P(TK.SEMICOLON))),),
        lambda phrases: ast.Program(phrases=phrases, offset=phrases[0].offset if phrases else 0),
    )


# Initialize the Quest grammar rules at module load time
build_quest_grammar()


def resolve_syntax_target(target: SyntaxTarget | str | None) -> SyntaxTarget:
    """Resolves a start symbol string or SyntaxTarget to a grammar SyntaxTarget."""
    if target is None:
        return PROGRAM
    if isinstance(target, SyntaxTarget):
        return target
    if isinstance(target, str):
        mapping = {
            "program": PROGRAM,
            "phrase": PHRASE,
            "type": TYPE,
            "kind": KIND,
            "expr": VALUE,
            "value": VALUE,
            "signature": SIGNATURE,
        }
        resolved = mapping.get(target.lower())
        if resolved is not None:
            return resolved
        available = sorted(mapping.keys())
        raise ValueError(f"Unknown start target '{target}'. Available: {available}")
    raise TypeError(f"Expected str or SyntaxTarget, got {type(target).__name__}")


def parse_quest_program(
    tokens: list[Token],
    source_map: SourceMap,
    target: SyntaxTarget | str | None = None,
) -> Any:
    """Convenience helper to parse tokens using the standard Quest grammar starting at target."""
    syntax_target = resolve_syntax_target(target)
    parser = Parser(tokens, source_map)
    return parser.parse(syntax_target)
