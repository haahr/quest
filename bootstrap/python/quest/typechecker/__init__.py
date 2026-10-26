"""Quest Typechecker Package.

Type and kind elaboration (`elaborate_types`), and the bidirectional type
checker that elaborates terms into the typed AST (`typed_ast`). The checker is
`TypeElaborator` in `typecheck`, which holds its state, the dispatch on
expression forms, and the entry points (`check_expr`, `synth_expr`,
`elaborate_binding`, `elaborate_phrase`, `elaborate_program`); it combines one
mixin per construct family:

- `bindings`: function abstractions and value, type, and kind bindings.
- `application`: monomorphic and polymorphic calls, and lvalue arguments of var
  and out parameters.
- `aggregates`: records, tuples, selection, options, variants, arrays, and
  indexing.
- `control`: case, infix operators and assignment, conditionals, for loops, and
  blocks.
- `exceptions`: exception declarations, raise, and try.
- `auto_values`: auto values, inspect, and the closedness of types used at run
  time.

Helpers shared by them: `checks` (subtype assertions, joins, kind bounds),
`escape` (escaping path types and closedness), `lvalues`, `metas` (resolving
inferred type arguments), and `scoping` (the well-scopedness check).
"""

__all__ = [
    "aggregates",
    "application",
    "auto_values",
    "bindings",
    "checks",
    "control",
    "elaborate_types",
    "escape",
    "exceptions",
    "lvalues",
    "metas",
    "scoping",
    "typecheck",
    "typed_ast",
]
