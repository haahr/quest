# bootstrap/python/quest/typechecker: bidirectional checking and elaboration

This package is the bootstrap compiler's type checker. It takes the desugared syntax tree from
[`../syntax`](../syntax) and elaborates it into a typed AST, in which every expression carries its type, every name
refers to its symbol, reads of mutable variables are explicit dereferences, and polymorphic calls carry their type
arguments, written or inferred. The interpreter ([`../interpreter`](../interpreter)) and the IR's lowering
([`../ir`](../ir)) read only that tree. It mirrors
[`questlang/typechecker`](../../../../questlang/typechecker/README.md), whose README is the full introduction;
this one says what is particular to the Python version.

The split with [`../types`](../types/README.md) is the same as in questlang: `types/` defines types and kinds and
decides subtyping, kinding, and contractiveness, and never sees a term; this package walks the program, turns written
types into semantic ones ([`elaborate_types.py`](elaborate_types.py)), declares symbols as bindings are checked, and
asks `types/` the questions each construct needs.

## The concepts, briefly

- **The typed AST** ([`typed_ast.py`](typed_ast.py)): frozen dataclasses, `TypedExpr` (with its type, `type_val`) and
  `TypedBinding`, each with the offset of the syntax it came from. Each node class says how it prints;
  [`typedastprint.py`](typedastprint.py) lays out the `--stop-after typecheck` dump that the golden tests share with
  questlang.
- **Bidirectional checking** ([`typecheck.py`](typecheck.py)): `check_expr` pushes an expected type into an expression,
  `synth_expr` computes its type bottom up, and checking a form that the expected type cannot inform is synthesis
  followed by subsumption (`_check_subsumption`). The forms that can be informed each have one `_elaborate_X_expr`
  method taking an optional expected type.
- **Construct families**: [`bindings.py`](bindings.py), [`application.py`](application.py) (including type-argument
  inference through metavariables that `is_subtype` solves), [`aggregates.py`](aggregates.py),
  [`tuples.py`](tuples.py), [`control.py`](control.py), [`exceptions.py`](exceptions.py), and
  [`auto_values.py`](auto_values.py), with shared helpers in [`checks.py`](checks.py) and
  [`escape.py`](escape.py) (path types must not escape their root's scope or be used at run time).
- **Well-scopedness** ([`scoping.py`](scoping.py)): with `QUEST_CHECK_SCOPES=1`, a check after elaboration that every
  variable is used within its binder's scope.

## What differs from questlang/typechecker

- **Mixins, not hooks.** Each family is a mixin class (`BindingMixin`, `ApplicationMixin`, ...) deriving from
  [`checker.py`](checker.py)'s `Checker`, which holds the state and declares `check_expr` and `synth_expr`;
  `TypeElaborator` in `typecheck.py` combines them and defines the dispatch. questlang cannot use inheritance, so its
  `checker.T` is a tuple with function-valued fields that `typecheck.newChecker` fills.
- **The first error stops the check.** Errors are exceptions (`QuestTypeError`, `KindError`) that propagate out of the
  program; questlang records errors, poisons the failed binding's names, and continues, reporting up to 20.
- **Callbacks into the module system** are registered with `register_binding_elaborator` and `register_unit_loader`
  in [`../modules/elaboration.py`](../modules/elaboration.py); questlang sets the fields of `elaboration.hooks`.

The pipeline ([`../pipeline.py`](../pipeline.py)) and the build engine ([`../build`](../build)) call the module-level
`elaborate_program`.

## Further reading

- [type-system.md](../../../../docs/type-system.md) §6: the elaboration rules (§6.1 the bidirectional discipline), and
  §4 for tuples, packages, and path types.
- [walkthrough.md](../../../../docs/walkthrough.md) §6: one program through the typecheck phase.
- [compiler-organization.md](../../../../docs/compiler-organization.md) §6: how the two compilers differ.
