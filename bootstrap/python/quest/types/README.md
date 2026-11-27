# bootstrap/python/quest/types: the type model, subtyping, and kinds

This package is the bootstrap compiler's model of Quest types: what a type and a kind are, and the judgments on them
(subtyping, type equality, kinding, contractiveness), with substitution, printing, and the reduced and canonical forms
the C backend needs. It reads no syntax. The type checker ([`../typechecker`](../typechecker/README.md)) builds
types from written syntax and asks this package to compare them; the IR and C backend ([`../ir`](../ir),
[`../repr`](../repr)) ask it for reduced and canonical forms when choosing layouts. It mirrors
[`questlang/types`](../../../../questlang/types/README.md) module for module, and that README is the full
introduction; this one says what is particular to the Python version.

## The concepts, briefly

- **Semantic types** ([`model.py`](model.py)) are a class hierarchy with a `Q` prefix: `QRecordType`, `QFunType`,
  `QAllType`, `QRecType`, `QRecGroupType`, `QTypeVar`, `QPathType`, `QAliasType`, the metavariable `QTypeMeta`, and
  so on, with kinds `QTypeKind` (`TYPE`), `QPowerKind` (`POWER(B)`), and `QAllKind`. They are frozen dataclasses,
  hash-consed by a metaclass that looks each structure up in a weak table, so `is` is structural identity. Binders
  carry globally unique symbol ids, types are kept as written (aliases and binder names survive), and code calls
  `evaluate_lazily` to expose a type's outermost constructor before casing on it.
- **Subtyping** ([`subtyping.py`](subtyping.py)): `is_subtype`, `is_type_equal`, and `is_subkind`. Recursive types are
  equi-recursive, compared coinductively with a trail of assumptions (`SubtypeTrail`); steps cost fuel, since bounded
  quantification makes the problem undecidable; results are cached, and a proof's intermediate results are committed
  only when it finishes. `is_subtype` also solves inference metavariables as a side effect.
- **Kinds** ([`kinds.py`](kinds.py)): kind synthesis and checking, raising `KindError`, and the `resolve_*_bound`
  functions that find the record, variant, option, or tuple type a type variable is bounded by.
- **Contractiveness** ([`contractiveness.py`](contractiveness.py)): a recursive variable must be guarded by a type
  constructor, so `Rec(X) X` is rejected.
- **Symbols and environments** ([`symbols.py`](symbols.py), [`env.py`](env.py)): value, type, and kind symbols,
  scopes, and the `Environment` with its scope stack, units, and the standard library's `BuiltinRegistry`.
- **Printing** ([`dump.py`](dump.py)): the compact formatter for messages and the typed AST dump
  (`format_type_compact`) and the canonical S-expression dump (`qtype_dump`).
- **Echoes** ([`echo.py`](echo.py)): a top-level declaration as the REPL echoes it, for the interpreter's
  formatting and the IR's lowering of echoed phrases alike.
- **Reduced and canonical forms** ([`reduce.py`](reduce.py), [`canonical.py`](canonical.py)): for the backend only.
  `canonical_type` minimizes a recursive type's graph so that equal recursive types get one C struct and descriptor;
  the checker does not canonicalize.

## What differs from questlang/types

- **Classes, not one node type.** Each form is a Python class; questlang has one `model.Type` tuple whose `form` is an
  option with a case per constructor, and an integer `id` standing in for `is`.
- **Equality raises.** Importing the package replaces `__eq__` on every `QType` subclass so that `==` raises
  ([`__init__.py`](__init__.py)): types are compared with `is` or `is_type_equal`, never with Python equality.
- **Keys and caches.** The subtype cache and other tables are keyed by tuples of objects, which Python hashes;
  questlang builds string or integer keys instead.
- **Errors.** Kind errors are `KindError` and subtyping overruns `TypeRecursionLimitExceeded`, subclasses of
  `QuestCompilerError`; questlang raises one exception, `diagnostics.compilerError`, for all of them.

The package's `__init__.py` re-exports the public names of all its modules, so most code imports from `quest.types`
directly.

## Further reading

- [type-system.md](../../../../docs/type-system.md) §2 (the hierarchy and its representation), §3 (subkinding,
  subtyping, contractiveness, recursive groups), §5 (environments).
- [compiler-organization.md](../../../../docs/compiler-organization.md) §6: how the two compilers differ.
