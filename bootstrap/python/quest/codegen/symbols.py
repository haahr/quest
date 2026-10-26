"""The names of what units link against: values, functions, and modules, mangled into identifiers
(docs/name-mangling.md). Every backend's units use them, so that they link with one another and with the C runtime."""

from __future__ import annotations

from quest.codegen.syntax import joined


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
                s = joined("", curr).strip("_")
                if s:
                    parts.append(s)
                curr.clear()
            parts.append(SYMBOL_MANGLE_MAP[ch])
        elif ch == ".":
            if curr:
                s = joined("", curr).strip("_")
                if s:
                    parts.append(s)
                curr.clear()
        else:
            curr.append(ch)
    if curr:
        s = joined("", curr).strip("_")
        if s:
            parts.append(s)
    return "qv_sym_" + joined("_", parts)


def mangle_ident(name: str) -> str:
    """Mangles a Quest identifier into a C-safe identifier prefixed with qv_."""
    if is_symbolic_name(name):
        return mangle_symbolic_ident(name)
    clean = name.replace(".", "_")
    return f"qv_{clean}"


def mangle_module_name(module_name: str) -> str:
    """Mangles a hierarchical module name into a C-safe identifier using __ for slashes."""
    return module_name.lower().replace("/", "__").replace(".", "_")


MODULE_RECORD_PREFIX = "qm_"


def module_record_ident(clean_mod: str) -> str:
    """Returns the C identifier of a module's record value, given its mangled module name.

    Module records use their own qm_ prefix: under qv_, the record of module m would be qv_m, which is
    also the mangling of a user identifier m (for example, a top-level 'let real' and module 'real').
    """
    return f"{MODULE_RECORD_PREFIX}{clean_mod}"


def mangle_module_ident(module_name: str, name: str) -> str:
    """Mangles a module-scoped Quest identifier into a C-safe identifier prefixed with qv_<mod>_."""
    clean_mod = mangle_module_name(module_name)
    if is_symbolic_name(name):
        sym_suffix = mangle_symbolic_ident(name)[3:]  # strip leading 'qv_'
        return f"qv_{clean_mod}_{sym_suffix}"
    clean_name = name.replace(".", "_")
    return f"qv_{clean_mod}_{clean_name}"
