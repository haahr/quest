# questlang/typechecker: bidirectional checking and elaboration

The type checker sits between the front end and everything after it. Its input is the desugared syntax tree from
[`../syntax`](../syntax) (parsed, with sugar such as `elsif` chains and short-circuit operators rewritten into core
forms). Its output is a *typed AST*: a new tree in which every expression carries its type, every name refers to its
symbol, and everything the source leaves implicit is explicit. Two readers consume that tree: the tree-walking
interpreter ([`../interpreter`](../interpreter)) evaluates it, and lowering ([`../ir`](../ir)) translates it into the
IR. Neither looks at the syntax again or checks a type, so whatever they need to know, the checker writes into the
tree.

The checker relies on [`../types`](../types/README.md) for everything about types themselves. The division of labor:

| `types/` | `typechecker/` |
|----------|----------------|
| What a type and a kind are (`model.Type`, `model.Kind`) | Turning written types into those values (`elaboratetypes`) |
| `S <: T`, type equality, `T :: K`, contractiveness | Deciding which of those judgments each construct needs |
| Substitution, unfolding, lazy evaluation | Elaborating expressions and bindings into the typed AST |
| Symbols, scopes, the environment `env.T` | Declaring symbols into the environment as bindings are checked |
| Solving metavariables during a subtype proof | Making metavariables for a polymorphic call, checking solutions |

So `types/` never sees a term, and `typechecker/` never decides a subtyping question itself.

## Elaboration

Checking here means elaborating. Given

```
let var n = 1
let id(A::TYPE x: A): A = x
id(n + 1)
```

the call becomes a typed application whose function is `id` applied to the type argument `Int` (inferred, since the
source writes none), and whose argument reads `n` through an explicit dereference, since `n` is a mutable cell
(`Var(Int)`) and a value position wants its contents. Each node records its type; the variable `n` records its
`symbols.ValueSymbol`, so that a later `n` declared in an inner scope is a different variable even with the same name.
The header comment of [`typecheck.mod.quest`](typecheck.mod.quest) shows the full dump of this example.

The typed AST is defined in [`typedast.int.quest`](typedast.int.quest): `typedAst.Expr` (an offset, a type, and one
of about forty forms such as `exprApp`, `exprTypeApp`, `exprDerefCell`, `exprTuple`, `exprCase`) and
`typedAst.Binding` for declarations, statements, imports, interfaces, and modules. Its printer,
[`typedastprint.mod.quest`](typedastprint.mod.quest), produces the `--stop-after typecheck` output that the golden
tests compare with the bootstrap's.

## Bidirectional checking

The checker uses local bidirectional typing rather than global unification. There are two modes, both in
[`typecheck.mod.quest`](typecheck.mod.quest):

- `synthExpr` (synthesis, Γ ⊢ e ⇒ T) works out an expression's most specific type from the expression alone, bottom up.
- `checkExpr` (checking, Γ ⊢ e ⇐ T) is given the type the context expects and pushes it down into the expression, so
  that the context can supply what the expression leaves unwritten.

Most forms are only synthesized; checking one is synthesis followed by *subsumption* (`checker.checkSubsumption`):
the synthesized type must be a subtype of the expected one. Subsumption leaves no trace in the tree, so a node's type
may be more specific than its context requires; changes of representation that the subtyping implies are inserted
much later, in the IR. The forms an expected type can inform (conditionals, blocks, functions, records, tuples,
arrays, case, raise, try, inspect, auto values, and applications) each have one `elaborateX` function that takes an
optional expected type; `checkExpr` calls it with the type and `synthExpr` with none, so each construct has a single
elaboration whichever mode reaches it. A function checked against `Fun(x: Int): Int`, for example, takes its
parameter types from the expected type when it writes none.

Applications show why checking matters. A polymorphic call with no written type arguments
([`application.mod.quest`](application.mod.quest)) replaces each type parameter with a metavariable, a placeholder
that the subtype prover solves as the arguments are compared with the parameter types. If some remain unsolved, the
expected type of the result is tried, which is how `list.nil()` checked against `list.T(Int)` gets its `Int`. A call
nested in another call's arguments, like `nil()` in `cons(x nil())`, may hand its unsolved metavariables to the outer
call (`checker.T`'s `pendingTypeArgs`), which solves them and rewrites the nested node. Each solution is then
checked against its parameter's bound, which solving ignores. Inference is greedy and never backtracks.

## The construct families

The rules are grouped into construct families, one module each, all taking a `checker.T`, the syntax node, the
optional expected type, the environment, and the loop depth:

- [`bindings`](bindings.mod.quest): function abstractions and their parameters, `let` declarations (recursive,
  simultaneous, external), and type and kind bindings.
- [`application`](application.mod.quest): calls, explicit and inferred type arguments, and the lvalue arguments of
  `var` and `out` parameters.
- [`aggregates`](aggregates.mod.quest): records, selection, options, variants, arrays, and indexing.
- [`tuples`](tuples.mod.quest): tuples, whose components may be values, type components (the witnesses of a package's
  abstract types), and declarations. Checked against an existential tuple type, a type component matching a formal
  `A::K` is hidden behind `A`; this is how packages are made.
- [`control`](control.mod.quest): case, built-in infix operators and assignment, conditionals, `for`, and blocks.
- [`exceptions`](exceptions.mod.quest): exception declarations, `raise`, and `try`.
- [`autovalues`](autovalues.mod.quest): auto values (Cardelli's dynamic types) and `inspect`.

The families need the dispatch (`checkExpr`, `synthExpr`) to check their subexpressions, but the dispatch needs the
families, and Quest modules cannot import each other cyclically. [`checker.int.quest`](checker.int.quest) breaks the
cycle: `checker.T` holds the checker's state and two function-valued fields, `checkHook` and `synthHook`, which
`typecheck` passes to `checker.new`. A family calls the families below it directly and reaches the
dispatch through the hooks. `checker.T` also counts enclosing loops and functions, which the checks of `exit` and of
closure capture (`checkCapturable`: a closure may not capture a `var` parameter of an enclosing function) rely on.

Shared helpers sit beside the families: [`checks`](checks.mod.quest) (joins of branch types, subtype assertions,
kinds of type arguments), [`escape`](escape.mod.quest) (a path type `p.T`, the hidden type of a package `p`, must not
leave `p`'s scope, nor be used as a run-time type), and [`elaboratetypes`](elaboratetypes.mod.quest), which turns
written types and kinds into `model` values, declares type and kind bindings, and handles recursive and mutually
recursive type groups (calling `types/contractiveness` and `types/kinds`).

## Errors and recovery

An error is raised with `diagnostics.fail` at the offending syntax's offset and ends the elaboration of the binding it
is in. Bindings and blocks are recovery points: the failing binding is reported, the names it declares are bound to
*poisoned* symbols (or to symbols of the type it declared, if it declared one), and checking continues with the next
binding. A later use of a poisoned name fails silently, so one mistake does not produce a cascade of errors. The
check stops after 20 errors or a fatal one; `typecheck.elaborateProgram` returns the typed program only if there were
none.

## Connections

`typecheck.elaborateProgram` is the entry point for a program; the driver ([`../driver`](../driver)), the REPL, the
language server ([`../lsp`](../lsp)), and the build engine call it. Module and interface elaboration lives in
[`../modules`](../modules), below the checker in the import order, so the checker installs callbacks into
`modules/elaboration`'s hooks for elaborating a module's bindings, and the loader installs one for loading units.
After checking, when `QUEST_CHECK_SCOPES=1` (as the test runners set it), [`scoping`](scoping.mod.quest) verifies that
every variable in the typed program is used within its binder's scope, which catches transformations that
re-elaborate code with fresh symbols.

The bootstrap compiler's counterpart is
[`bootstrap/python/quest/typechecker`](../../bootstrap/python/quest/typechecker/README.md), which has the same
families and prints the same typed AST, but stops at the first error.

## Further reading

- [type-system.md](../../docs/type-system.md) §6: the elaboration rules, §6.1 the bidirectional discipline in detail,
  §6.2 to §6.15 the individual constructs; §4 existential tuples, packing, path types, and escape.
- [walkthrough.md](../../docs/walkthrough.md) §6: one program followed through this phase.
- [diagnostics.md](../../docs/diagnostics.md) §4.5: error recovery.
- [syntax.md](../../docs/syntax.md) §5: what desugaring hands the checker.
- [compiler-organization.md](../../docs/compiler-organization.md) §5 and §6: the import layers and how the families are
  wired, and how they differ from the bootstrap's.
