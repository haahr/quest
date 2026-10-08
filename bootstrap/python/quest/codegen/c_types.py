"""C Type mapping, identifier mangling, and operator dispatch for Quest C Transpiler."""

from __future__ import annotations

import hashlib

from quest.types import (
    QAliasType,
    strip_aliases,
    BOOL_TYPE,
    CHAR_TYPE,
    DYNAMIC_TYPE,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    QAbstractType,
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
    QExternalType,
    QFunType,
    QOptionField,
    QOptionType,
    QPathType,
    QPowerKind,
    QQuantifier,
    QRecGroupType,
    QRecType,
    QRecordField,
    QRecordType,
    QTupleField,
    QTupleType,
    QType,
    QTypeApp,
    QTypeFun,
    QTypeVar,
    QVarType,
    QOutType,
    QVariantField,
    QVariantType,
    resolve_record_bound,
    resolve_variant_bound,
    resolve_option_bound,
    is_type_equal,
    auto_payload_type,
)

SYMBOL_MANGLE_MAP: dict[str, str] = {
    "+": "plus",
    "-": "minus",
    "*": "star",
    "/": "slash",
    "=": "equals",
    "<": "lt",
    ">": "gt",
    "!": "bang",
    "?": "question",
    ":": "colon",
    "@": "at",
    "#": "hash",
    "$": "dollar",
    "%": "percent",
    "^": "caret",
    "&": "amp",
    "|": "pipe",
    "~": "tilde",
    "\\": "backslash",
    ".": "dot",
    "'": "prime",
}


def is_symbolic_name(name: str) -> bool:
    """Returns True if the identifier contains symbolic operator characters (excluding simple module dots)."""
    return any(ch in SYMBOL_MANGLE_MAP and ch != "." for ch in name)


def mangle_symbolic_ident(name: str) -> str:
    """Mangles an identifier containing symbolic operator characters into a C-safe identifier."""
    parts: list[str] = []
    curr: list[str] = []
    for ch in name:
        if ch in SYMBOL_MANGLE_MAP and ch != ".":
            if curr:
                s = "".join(curr).strip("_")
                if s:
                    parts.append(s)
                curr.clear()
            parts.append(SYMBOL_MANGLE_MAP[ch])
        elif ch == ".":
            if curr:
                s = "".join(curr).strip("_")
                if s:
                    parts.append(s)
                curr.clear()
        else:
            curr.append(ch)
    if curr:
        s = "".join(curr).strip("_")
        if s:
            parts.append(s)
    return "qv_sym_" + "_".join(parts)


def mangle_ident(name: str) -> str:
    """Mangles a Quest identifier into a C-safe identifier prefixed with qv_."""
    if is_symbolic_name(name):
        return mangle_symbolic_ident(name)
    clean = name.replace(".", "_")
    return f"qv_{clean}"


def mangle_module_name(module_name: str) -> str:
    """Mangles a hierarchical module name into a C-safe identifier using __ for slashes."""
    return module_name.lower().replace("/", "__").replace(".", "_")


def module_record_ident(clean_mod: str) -> str:
    """Returns the C identifier of a module's record value, given its mangled module name.

    Module records use their own qm_ prefix: under qv_, the record of module m would be qv_m, which is
    also the mangling of a user identifier m (for example, a top-level 'let real' and module 'real').
    """
    return f"qm_{clean_mod}"


def mangle_module_ident(module_name: str, name: str) -> str:
    """Mangles a module-scoped Quest identifier into a C-safe identifier prefixed with qv_<mod>_."""
    clean_mod = mangle_module_name(module_name)
    if is_symbolic_name(name):
        sym_suffix = mangle_symbolic_ident(name)[3:]  # strip leading 'qv_'
        return f"qv_{clean_mod}_{sym_suffix}"
    clean_name = name.replace(".", "_")
    return f"qv_{clean_mod}_{clean_name}"


_MAX_BETA_STEPS = 1000


def _beta_reduce_head(t: QType) -> QType:
    """Beta-reduces type operator applications at the head of t, without unfolding recursive types."""
    for _ in range(_MAX_BETA_STEPS):
        t = t.prune() if hasattr(t, "prune") else t
        if not isinstance(t, QTypeApp):
            return t
        ctor = _beta_reduce_head(t.constructor)
        if isinstance(ctor, QExceptionType) and len(t.arguments) == 1:
            return QExceptionType(payload_type=t.arguments[0])
        if not isinstance(ctor, QTypeFun) or len(ctor.params) != len(t.arguments):
            return t
        t = ctor.body.substitute({formal.symbol_id: arg for formal, arg in zip(ctor.params, t.arguments)})
    return t


def normalize_type(t: QType) -> QType:
    """Reduces type operator applications so that C representations are chosen from the reduced type.

    Applications whose head reduces to a non-recursive type are replaced by that type; applications that
    reduce to a recursive type are only unfolded when the unfolding is a concrete tuple or record type.
    """
    t = t.prune() if hasattr(t, "prune") else t
    t = strip_aliases(t)
    if isinstance(t, QTypeApp):
        reduced = _beta_reduce_head(t)
        if not isinstance(reduced, (QTypeApp, QRecType, QRecGroupType)):
            return reduced
        evaled = t.evaluate_lazily()
        if evaled is not t and isinstance(evaled, (QTupleType, QRecordType)):
            return evaled
    return t


def resolve_type_bound(t: QType) -> QType:
    """Unwraps upper bounds for path types and type variables bounded by POWER(T)."""
    curr = t.prune() if hasattr(t, "prune") else t
    curr = strip_aliases(curr)
    visited = set()
    while isinstance(curr, (QTypeVar, QAbstractType, QPathType)) and isinstance(curr.bound, QPowerKind):
        sym_id = getattr(curr, "symbol_id", id(curr))
        if sym_id in visited:
            break
        visited.add(sym_id)
        curr = curr.bound.bound
        curr = curr.prune() if hasattr(curr, "prune") else curr
    return curr


def is_word_type(t: QType) -> bool:
    """Returns True if t is the standard library Word.T type."""
    t = t.prune() if hasattr(t, "prune") else t
    t = resolve_type_bound(t)
    t = normalize_type(t)
    if isinstance(t, QTypeVar) and t.name in ("Word.T", "word.T"):
        return True
    if isinstance(t, QPathType) and t.field_name == "T" and t.root_name in ("Word", "word"):
        return True
    if isinstance(t, QExternalType) and (t.name in ("Word.T", "word.T") or t.c_type == "uint64_t"):
        return True
    return False


def type_to_c_tag(t: QType) -> str:
    """Produces a deterministic, valid C identifier component for a QType."""
    raw = _type_to_c_tag_raw(t)
    if len(raw) > 64:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"{raw[:24]}_{digest}"
    return raw


def _type_to_c_tag_raw(t: QType) -> str:
    t = t.prune() if hasattr(t, "prune") else t
    t = strip_aliases(t)
    t = resolve_type_bound(t)
    t = normalize_type(t)
    if is_word_type(t):
        return "Word"
    if t is INT_TYPE:
        return "Int"
    if t is REAL_TYPE:
        return "Real"
    if t is BOOL_TYPE:
        return "Bool"
    if t is CHAR_TYPE:
        return "Char"
    if t is STRING_TYPE:
        return "String"
    if t is OK_TYPE:
        return "Ok"
    if t is DYNAMIC_TYPE or (isinstance(t, QTypeVar) and t.name == "Dynamic.T"):
        return "Dynamic"
    if isinstance(t, QExternalType):
        return t.name.replace(".", "_") if t.name else t.c_type.replace("*", "").strip()
    if isinstance(t, QTypeVar) and t.name == "Writer.T":
        return "QWriter"
    if isinstance(t, QTypeVar) and t.name == "Reader.T":
        return "QReader"
    if isinstance(t, QTupleType):
        tags = [type_to_c_tag(f.type_val) for f in t.value_fields]
        return "QTuple_" + ("_".join(tags) if tags else "empty")
    if isinstance(t, QRecordType):
        sorted_fields = sorted(t.fields, key=lambda f: f.name)
        tags = [f"{f.name}_{type_to_c_tag(f.type_val)}" for f in sorted_fields]
        return "QRecord_" + ("_".join(tags) if tags else "empty")
    if isinstance(t, (QFunType, QAllType)):
        return "QClosure"
    if isinstance(t, (QVarType, QOutType)):
        return f"Ref_{type_to_c_tag(t.element_type)}"
    if isinstance(t, (QTypeVar, QAbstractType, QPathType)):
        return "QVal"
    if isinstance(t, QArrayType):
        return f"QArray_{type_to_c_tag(t.element_type)}"
    if isinstance(t, QVariantType):
        tags = []
        for v in t.variants:
            if v.type_val:
                tags.append(f"{v.name}_{type_to_c_tag(v.type_val)}")
            else:
                tags.append(v.name)
        return "QVariant_" + ("_".join(tags) if tags else "empty")
    if isinstance(t, QExceptionType):
        return "QException"
    if isinstance(t, QAutoType):
        return "Auto_" + type_to_c_tag(auto_payload_type(t))
    if isinstance(t, QOptionType) or (opt_bound := resolve_option_bound(t)) is not None:
        opt_t = t if isinstance(t, QOptionType) else opt_bound
        tags = []
        for o in opt_t.options:
            if o.payload_type:
                tags.append(f"{o.name}_{type_to_c_tag(o.payload_type)}")
            else:
                tags.append(o.name)
        return "QOption_" + ("_".join(tags) if tags else "empty")
    return "QVal"


def _type_digest(t: QType) -> str:
    """A short digest of a type's canonical text, telling apart types that type_to_c_tag conflates."""
    t = normalize_type(strip_aliases(t.prune() if hasattr(t, "prune") else t))
    return hashlib.sha256(str(t).encode("utf-8")).hexdigest()[:16]


def fun_descriptor_tag(t: QType) -> str:
    """The tag of the runtime descriptor of a function type (QFunType or QAllType).

    type_to_c_tag is QClosure for every function type, which suits struct naming (all closures are represented
    alike) but not descriptors, which must tell function types apart.
    """
    return "fun_" + _type_digest(t)


def tuple_struct_name(t: QTupleType) -> str:
    """Returns the C struct tag name for a given QTupleType."""
    return type_to_c_tag(t)


def record_struct_name(t: QRecordType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Returns the C struct tag name for a given QRecordType."""
    if ctx is not None:
        name = ctx.get_or_create_name(t)
        return f"QT_{name}"
    return type_to_c_tag(t)


def option_struct_name(t: QType) -> str:
    """Returns the C struct tag name for a given QOptionType."""
    return type_to_c_tag(t)


class RecordNamingContext:
    """Maintains sequential and alias-based naming for record types and evidence dictionaries."""

    def __init__(self) -> None:
        self.alias_by_shape: dict[tuple[tuple[str, str, str], ...], str] = {}
        self.seq_by_shape: dict[tuple[tuple[str, str, str], ...], str] = {}
        self.shape_to_canonical_name: dict[tuple[tuple[str, str, str], ...], str] = {}
        self._record_counter = 0

    def _shape_key(self, t: QRecordType) -> tuple[tuple[str, str, str], ...]:
        # Records share a struct (and so a descriptor) only if their fields have the same types, not merely the same
        # C representations: type_to_c_tag is QClosure for every function type and QVal for every type variable.
        sorted_fields = sorted(t.fields, key=lambda f: f.name)
        return tuple((f.name, type_to_c_tag(f.type_val), _type_digest(f.type_val)) for f in sorted_fields)

    def register_alias(self, alias_name: str, t: QRecordType) -> None:
        key = self._shape_key(t)
        if key not in self.alias_by_shape:
            self.alias_by_shape[key] = alias_name
            self.shape_to_canonical_name[key] = alias_name

    def get_or_create_name(self, t: QRecordType, module_name: Optional[str] = None) -> str:
        key = self._shape_key(t)
        if key in self.shape_to_canonical_name:
            return self.shape_to_canonical_name[key]
        self._record_counter += 1
        prefix = f"{module_name}_" if module_name else ""
        name = f"{prefix}record{self._record_counter}"
        self.seq_by_shape[key] = name
        self.shape_to_canonical_name[key] = name
        return name

    def record_struct_name(self, t: QRecordType) -> str:
        name = self.get_or_create_name(t)
        return f"QT_{name}"

    def offset_dict_struct_name(self, t: QRecordType) -> str:
        name = self.get_or_create_name(t)
        return f"OffsetDict_{name}"

    def offset_dict_instance_name(self, target: QRecordType, source: QRecordType) -> str:
        tgt_name = self.get_or_create_name(target)
        src_name = self.get_or_create_name(source)
        return f"offsetdict_{tgt_name}_{src_name}"


def qtype_to_c_type(t: QType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Maps a semantic Quest QType to its corresponding C scalar or pointer type representation."""
    t = t.prune() if hasattr(t, "prune") else t
    t = strip_aliases(t)
    t = resolve_type_bound(t)
    t = normalize_type(t)
    if is_word_type(t):
        return "uint64_t"
    if t is INT_TYPE:
        return "QInt"
    if t is REAL_TYPE:
        return "QReal"
    if t is BOOL_TYPE:
        return "QBool"
    if t is CHAR_TYPE:
        return "QChar"
    if t is STRING_TYPE:
        return "QString *"
    if t is OK_TYPE:
        return "void"
    if t is DYNAMIC_TYPE or (isinstance(t, QTypeVar) and t.name == "Dynamic.T"):
        return "QDynamic *"
    if isinstance(t, QAutoType):
        # An auto value is represented like a Dynamic: its type component's descriptor and its payload
        return "QDynamic *"
    if isinstance(t, QExternalType):
        return t.c_type
    if isinstance(t, QTypeVar) and t.name == "Writer.T":
        return "QWriter *"
    if isinstance(t, QTypeVar) and t.name == "Reader.T":
        return "QReader *"
    if isinstance(t, QTupleType):
        return f"{tuple_struct_name(t)} *"
    if isinstance(t, QRecordType) or resolve_record_bound(t) is not None:
        return "QRecordVal"
    if isinstance(t, (QFunType, QAllType)):
        return "QClosure *"
    if isinstance(t, QArrayType):
        elem = t.element_type
        if isinstance(elem, QRecordType) or resolve_record_bound(elem) is not None:
            return "QArrayWideRecord *"
        if isinstance(elem, QVariantType) or resolve_variant_bound(elem) is not None:
            return "QArrayWideVariant *"
        return "QArray *"
    if isinstance(t, QVariantType) or resolve_variant_bound(t) is not None:
        return "QVariantVal"
    if isinstance(t, QExceptionType):
        return "const QException *"
    if isinstance(t, QOptionType) or (opt_bound := resolve_option_bound(t)) is not None:
        opt_t = t if isinstance(t, QOptionType) else opt_bound
        return f"{option_struct_name(opt_t)} *"
    if isinstance(t, (QVarType, QOutType)):
        return f"{qtype_to_c_type(t.element_type, ctx)} *"
    if isinstance(t, (QTypeVar, QAbstractType, QPathType)):
        return "QVal"
    return "QVal"


def qtype_to_name_str(t: QType) -> str:
    """Returns the human-readable Quest type name string for runtime diagnostics and printing."""
    t = t.prune() if hasattr(t, "prune") else t
    if isinstance(t, QAliasType):
        return t.name
    if is_word_type(t):
        return "Word.T"
    if t is INT_TYPE:
        return "Int"
    if t is REAL_TYPE:
        return "Real"
    if t is BOOL_TYPE:
        return "Bool"
    if t is CHAR_TYPE:
        return "Char"
    if t is STRING_TYPE:
        return "String"
    if t is OK_TYPE:
        return "Ok"
    if isinstance(t, QExternalType):
        return t.name or t.c_type
    return str(t)


def c_string_literal(s: str) -> str:
    """Escapes a Python string into a safe C string literal."""
    parts = []
    for ch in s:
        if ch == "\"":
            parts.append("\\\"")
        elif ch == "\\":
            parts.append("\\\\")
        elif ch == "\n":
            parts.append("\\n")
        elif ch == "\t":
            parts.append("\\t")
        elif ch == "\r":
            parts.append("\\r")
        elif 32 <= ord(ch) < 127:
            parts.append(ch)
        else:
            parts.append(f"\\x{ord(ch):02x}")
    return "\"" + "".join(parts) + "\""


def c_char_literal(ch: str) -> str:
    """Escapes a single Python character into a C char literal."""
    if ch == "\'":
        return "'\\''"
    if ch == "\\":
        return "'\\\\'"
    if ch == "\n":
        return "'\\n'"
    if ch == "\t":
        return "'\\t'"
    if ch == "\r":
        return "'\\r'"
    if 32 <= ord(ch) < 127:
        return f"'{ch}'"
    return f"'\\x{ord(ch):02x}'"


def qval_wrap(expr_str: str, t: QType) -> str:
    """Wraps a scalar or pointer expression into a QVal union initializer."""
    t = t.prune() if hasattr(t, "prune") else t
    t = resolve_type_bound(t)
    t = normalize_type(t)
    if qtype_to_c_type(t) == "QVal":
        return expr_str
    if t is OK_TYPE:
        return "Q_OK_VAL"
    if isinstance(t, QRecordType) or resolve_record_bound(t) is not None:
        return f"((QVal){{ .p = (void *)quest_record_box({expr_str}) }})"
    if isinstance(t, QVariantType) or resolve_variant_bound(t) is not None:
        return f"((QVal){{ .p = (void *)quest_variant_box({expr_str}) }})"
    if is_word_type(t):
        return f"((QVal){{ .u = (uint64_t)({expr_str}) }})"
    if t is INT_TYPE or t is BOOL_TYPE or t is CHAR_TYPE:
        return f"((QVal){{ .i = (int64_t)({expr_str}) }})"
    if t is REAL_TYPE:
        return f"((QVal){{ .r = (double)({expr_str}) }})"
    return f"((QVal){{ .p = (void *)({expr_str}) }})"


def qval_unwrap(qval_expr: str, t: QType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Extracts the underlying concrete scalar or pointer from a QVal expression."""
    t = t.prune() if hasattr(t, "prune") else t
    t = resolve_type_bound(t)
    t = normalize_type(t)
    if qtype_to_c_type(t, ctx) == "QVal":
        return qval_expr
    if isinstance(t, QRecordType) or resolve_record_bound(t) is not None:
        return f"(*((QRecordVal *)({qval_expr}.p)))"
    if isinstance(t, QVariantType) or resolve_variant_bound(t) is not None:
        return f"(*((QVariantVal *)({qval_expr}.p)))"
    if is_word_type(t):
        return f"({qval_expr}.u)"
    if t is INT_TYPE or t is BOOL_TYPE or t is CHAR_TYPE:
        return f"({qval_expr}.i)"
    if t is REAL_TYPE:
        return f"({qval_expr}.r)"
    if t is OK_TYPE:
        return "((void)0)"
    c_t = qtype_to_c_type(t, ctx)
    return f"(({c_t})({qval_expr}.p))"


def closure_fn_ptr_type(fun_type: QType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Constructs the C function pointer cast type for invoking a closure."""
    quantifiers: tuple[Any, ...] = ()
    cur_type = fun_type
    while isinstance(cur_type, QAllType):
        quantifiers = quantifiers + cur_type.quantifiers
        cur_type = cur_type.body

    if isinstance(cur_type, QFunType):
        if cur_type.result_type is OK_TYPE:
            ret_c = "void"
        elif isinstance(cur_type.result_type, QRecordType):
            ret_c = "QRecordVal"
        else:
            ret_c = qtype_to_c_type(cur_type.result_type, ctx)
        param_types = ["void *"]
        # Quantifier descriptors appear immediately after env
        for _ in quantifiers:
            param_types.append("const QTypeDescriptor *")
        for p in cur_type.params:
            if getattr(p, "is_out", False) or getattr(p, "is_var", False):
                param_types.append(f"{qtype_to_c_type(p.type_val, ctx)} *")
            elif p.type_val is OK_TYPE:
                param_types.append("QVal")
            else:
                param_types.append(qtype_to_c_type(p.type_val, ctx))
        sig = ", ".join(param_types)
        return f"{ret_c} (*)({sig})"

    ret_c = "void" if cur_type is OK_TYPE else (
        "QRecordVal" if isinstance(cur_type, QRecordType)
        else qtype_to_c_type(cur_type, ctx)
    )
    param_types = ["void *"]
    for _ in quantifiers:
        param_types.append("const QTypeDescriptor *")
    sig = ", ".join(param_types)
    return f"{ret_c} (*)({sig})"


def is_record_subtype(s: QType, t: QType) -> bool:
    if not isinstance(s, QRecordType) or not isinstance(t, QRecordType):
        return False
    s_fields = {f.name: f.type_val for f in s.fields}
    for f in t.fields:
        if f.name not in s_fields:
            return False
        s_f_type = s_fields[f.name]
        if s_f_type is not f.type_val and not is_type_equal(s_f_type, f.type_val):
            return False
    return True


def is_tuple_subtype(s: QType, t: QType) -> bool:
    if not isinstance(s, QTupleType) or not isinstance(t, QTupleType):
        return False
    if len(s.value_fields) < len(t.value_fields):
        return False
    for i in range(len(t.value_fields)):
        s_c = qtype_to_c_type(s.value_fields[i].type_val)
        t_c = qtype_to_c_type(t.value_fields[i].type_val)
        if s_c != t_c:
            return False
    return True


def is_variant_subtype(s: QType, t: QType) -> bool:
    if not isinstance(s, QVariantType) or not isinstance(t, QVariantType):
        return False
    t_map = {v.name: v.type_val for v in t.variants}
    for v in s.variants:
        if v.name not in t_map:
            return False
        t_v_type = t_map[v.name]
        if v.type_val is not t_v_type and not is_type_equal(v.type_val, t_v_type):
            return False
    return True


def collect_fun_quantifiers(fun_type: QType) -> tuple[tuple[QQuantifier, ...], QType]:
    """Extracts any universal quantifiers wrapping a function type."""
    quants: tuple[QQuantifier, ...] = ()
    curr = fun_type
    while isinstance(curr, QAllType):
        quants = quants + curr.quantifiers
        curr = curr.body
    return quants, curr
