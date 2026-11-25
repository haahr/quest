"""Help for a name that failed to resolve: what the name is instead
(docs/diagnostics.md §4.2).

A lookup that fails says only that it failed (Undefined type 'vector'), and the
commonest causes are a module, its interface, and its type standing in for one
another: vector for vector.T, Vector for vector.T, Iter for the module iter.
Each function here returns the help line for one kind of failed lookup, or None,
by looking for the name in the namespaces the lookup did not search, and for an
interface, for the module of the same name with its first letter lowercased.
Only modules and interfaces already registered are consulted, so asking loads
nothing. mismatch_help does the same for a subtype failure whose types differ
in one of two ways that a declaration, accepted, leads to. The self-hosted
counterpart is questlang/typechecker/nearMiss."""

from __future__ import annotations

from typing import Optional

from quest.types.env import Environment
from quest.types.model import QAllKind, QArrayType, QOutType, QType, QTypeApp, QTypeVar, QVarType
from quest.types.symbols import Scope


def _registered_module(env: Environment, name: str) -> Optional[Scope]:
    """The module registered under name, without loading a builtin one."""
    return env.lookup_module(name) if env.has_module(name) else None


def _lowered(name: str) -> str:
    """name with its first letter, if an ASCII capital, lowercased: an
    interface's module's name."""
    return name[0].lower() + name[1:] if "A" <= name[:1] <= "Z" else name


def type_help(env: Environment, name: str) -> Optional[str]:
    """Help for a type name that is not a type: a module's name, whose type is
    name.T, or an interface's, whose module has the type."""
    scope = _registered_module(env, name)
    if scope is not None and scope.lookup_type_local("T") is not None:
        return f"'{name}' is a module; its type is {name}.T"
    module = _lowered(name)
    if module != name and env.has_interface(name):
        scope = _registered_module(env, module)
        if scope is not None and scope.lookup_type_local("T") is not None:
            return f"'{name}' is an interface; the module imported as '{module}' has the type {module}.T"
    return None


def value_help(env: Environment, name: str) -> Optional[str]:
    """Help for a value name that is not a value: an interface's name, whose
    module is imported under the name lowercased."""
    module = _lowered(name)
    if module != name and env.has_interface(name) and env.has_module(module):
        return f"'{name}' is an interface; the module is imported as '{module}'"
    return None


def member_help(module: str, scope: Scope, member: str) -> Optional[str]:
    """Help for a member a module does not export as a value: a type of the
    module's."""
    if scope.lookup_type_local(member) is not None:
        return f"{module}.{member} is a type, not a value"
    return None


def call_help(env: Environment, name: str) -> Optional[str]:
    """Help for a call of a module's name: one of its functions, new, when it
    has one."""
    scope = _registered_module(env, name)
    if scope is not None and scope.lookup_value_local("new") is not None:
        return f"'{name}' is a module; call one of its functions, such as {name}.new"
    return None


def _interface_type_help(t: QType, other: QType) -> Optional[str]:
    """Help when t is a type reached through an interface's name (Iter.T) and
    other, in its place, the type of that name in the module of the interface's
    name lowercased (iter.T)."""
    if not isinstance(t, QTypeVar) or not isinstance(other, QTypeVar):
        return None
    interface, dot, member = t.name.partition(".")
    module = _lowered(interface)
    if not dot or "." in member or module == interface or other.name != f"{module}.{member}":
        return None
    return (
        f"'{t.name}' is the interface {interface}'s own type, which no value has; "
        f"where it is declared, write {other.name}"
    )


def _unapplied_help(t: QType, other: QType) -> Optional[str]:
    """Help when t is a type operator (vector.T) and other, in its place, the
    same operator applied (vector.T(?A))."""
    if not isinstance(t, QTypeVar) or not isinstance(t.bound, QAllKind):
        return None
    if not isinstance(other, QTypeApp) or not isinstance(other.constructor, QTypeVar):
        return None
    if other.constructor.symbol_id != t.symbol_id:
        return None
    arguments = "argument" if len(other.arguments) == 1 else "arguments"
    return f"'{t.name}' is missing its type {arguments}; where it is declared, write {t.name}(...)"


def mismatch_help(synthesized: QType, expected: QType) -> Optional[str]:
    """Help for a subtype failure between synthesized and expected: the first
    place, in the two types walked together through type applications and
    array, var, and out types, where one is a type through an interface's name
    and the other its module's, or one is a type operator and the other the
    operator applied. Both are declarations the checker accepts, which fail
    only where a value meets them (docs/diagnostics.md §4.2)."""
    for t, other in ((synthesized, expected), (expected, synthesized)):
        found = _interface_type_help(t, other) or _unapplied_help(t, other)
        if found is not None:
            return found
    if isinstance(synthesized, QTypeApp) and isinstance(expected, QTypeApp):
        if len(synthesized.arguments) == len(expected.arguments):
            pairs = zip(
                (synthesized.constructor, *synthesized.arguments), (expected.constructor, *expected.arguments)
            )
            for s, e in pairs:
                found = mismatch_help(s, e)
                if found is not None:
                    return found
        return None
    for cls in (QArrayType, QVarType, QOutType):
        if isinstance(synthesized, cls) and isinstance(expected, cls):
            return mismatch_help(synthesized.element_type, expected.element_type)
    return None
