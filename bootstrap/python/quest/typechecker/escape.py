"""Two checks on the abstract types of packages.

A package is a value of an existential tuple type, `Tuple T::TYPE x: T end`,
whose type component is hidden. Bound to an immutable variable p, its
component is the path type p.T (QPathType), distinct from every other
package's (docs/type-system.md §4.4). Two things may not mention one:

- a type that leaves p's scope, such as the result type of a function taking
  p as a parameter (check_no_escaping_path_types, §4.5), since outside the
  scope p.T names nothing;
- a type used at run time, such as a dynamic value's or an inspect branch's
  (check_no_package_types), since p.T has no run-time identity to compare.

The self-hosted counterpart is questlang/typechecker/escape."""

from __future__ import annotations

from quest.common.diagnostics import QuestTypeError
from quest.types import (
    QType,
    find_path_types,
    strip_aliases,
)


def check_no_package_types(t: QType, what: str, offset: int) -> None:
    """Rejects a type that mentions an abstract type projected from a package
    value (t.A): its identity is the package's hidden type, which is not known
    at run time."""
    paths = find_path_types(strip_aliases(t))
    if paths:
        names = ", ".join(sorted({f"{p.root_name}.{p.field_name}" for p in paths}))
        raise QuestTypeError(
            f"{what} cannot mention {names}, an abstract type of a package value, because its identity is not "
            f"known at run time",
            offset=offset,
        )


def check_no_escaping_path_types(
    typ: QType,
    local_symbol_ids: set[int],
    context_desc: str,
    offset: int = 0,
) -> None:
    """Ensures that no abstract path-dependent types rooted at local variables
    escape."""
    for p in find_path_types(typ):
        if p.root_symbol_id in local_symbol_ids:
            raise QuestTypeError(
                f"Abstract type '{p.root_name}.{p.field_name}' cannot escape {context_desc} "
                f"in type '{typ}'",
                offset=offset,
            )
