# questlang/types: the type model, subtyping, and kinds

This directory defines what a type *is* inside the compiler, and answers the questions asked of types: is this type a
subtype of that one, what kind does this type have, what does this recursive type unfold to, how is it printed. It
does not look at programs. The type checker ([`../typechecker`](../typechecker/README.md)) reads source syntax,
translates written types into the values defined here, and asks this directory to compare them; the IR passes and
backends ([`../ir`](../ir), [`../repr`](../repr)) later ask it for reduced and canonical forms of the same values so
they can choose memory layouts. The division is roughly that of a logic and its proof checker: `types/` is the
logic (the terms, the judgments `S <: T` and `T :: K`, substitution), and `typechecker/` is the procedure that walks a
program and decides which judgments to ask for.

Nothing in `types/` reads the syntax tree. Its input is types already built, and its outputs are booleans (subtyping),
kinds, other types (substitution, unfolding, reduction), and strings (printing).

## Semantic types

A written type such as `Record x: Int y: Int end` is syntax (`ast.TypeExpr`, from [`../syntax`](../syntax)). The
checker's `elaborateTypes` resolves every name in it to a symbol and produces a *semantic* type, a `model.Type`,
defined in [`model.int.quest`](model.int.quest). A `Type` is a node with a `form`, one per type constructor: the
primitives (`typeInt`, `typeString`, ...), aggregates (`typeTuple`, `typeRecord`, `typeVariant`, `typeOption`),
`typeFun`, the reference types `typeVar`, `typeArray`, `typeOut`, the polymorphic forms (`typeAll` for `All(A::K) T`,
`typeOperator` for a type function `Fun(A::K) T`, `typeApp` for its application), `typeAuto` for Cardelli's dynamic
types, and recursive types (`typeRec`, and `typeRecGroup` for one member of a `Let Rec A = ... and B = ...` group).
Five more forms stand for a type by name rather than by structure: a type variable, an abstract type known only by
its bound, a path type `x.A` (the hidden type component of a package value `x`), a reference to an alias (kept so
that messages print the name the programmer wrote), and an inference metavariable `?A`.

Several properties of this representation shape everything that uses it:

- **Hash-consing.** Constructing a node returns the one canonical node for that structure, so two structurally
  identical types are the same node, and `model.same` (an id comparison) is structural identity. Nodes containing a
  metavariable are excluded, since a metavariable is the one mutable type and is solved in place.
- **Named binders.** Binders (`Rec`, `All`, type operators, tuple type components) carry globally unique symbol ids
  from [`symbols`](symbols.int.quest), not de Bruijn indices. Substitution (`model.substitute`) can then avoid capture
  without renaming. Each node records its free symbol ids and whether it contains a metavariable, so substituting into
  a type that cannot change returns it without a walk.
- **Types are kept as written.** Two alpha-equivalent types elaborated separately are different nodes, and an alias
  stays an alias node. This keeps diagnostics, interface files (`.qi`), and the typecheck dump faithful to the source.
  It also means `model.same` is not type equality: code compares types with `subtyping.isTypeEqual` or
  `subtyping.isSubtype`.
- **Lazy evaluation.** Because a type may be an alias, an application of a type operator, or a recursive type, code
  that cases on a type's form first calls `model.evaluateLazily`, which exposes the outermost constructor and leaves
  the parts as written. A recursive type `Rec(X) T` stands for an infinite tree but stays finite: unfolding it
  substitutes the `Rec` node itself for `X`, and the unfolding is cached on the node.

Kinds, the "types of types", are nodes of the same design (`model.Kind`): `TYPE` for ordinary types, `POWER(B)` for
the subtypes of `B` (how a bounded type parameter `A <: B` is expressed), `ALL(X::K1) K2` for type operators, and kind
variables.

## Subtyping

[`subtyping.mod.quest`](subtyping.mod.quest) decides `S <: T` (`isSubtype`), type equality (`isTypeEqual`, both
directions as one proof), and subkinding. Subtyping is structural: a record with more fields is a subtype of one with
fewer, so

```
Let Point = Record x: Int y: Int end
Let Point3 = Record x: Int y: Int z: Int end
```

gives `Point3 <: Point` with no declaration relating them. Function types are contravariant in their parameters,
`Var` and `Out` types are invariant and contravariant respectively, and tuples match by prefix.

Recursive types are *equi-recursive*: `Rec(X) T` equals its unfolding, with no explicit fold or unfold in programs.
A proof about two recursive types can therefore meet its own goal again after unfolding both sides. The prover keeps a
trail of the pairs it is proving and treats a pair that recurs on the trail as proved, a *coinductive* proof (the
assumption is justified because every path through the infinite trees is checked). Bounded quantification
(`All(A <: B) T`) makes subtyping undecidable in general, so each step spends fuel, and a proof that exhausts it is
reported as an error rather than looping.

Results are cached across the whole compilation, with a subtlety: a `True` decided under a coinductive assumption
that later fails is not a fact, so a proof commits its intermediate results only when it finishes, and keeps only the
`False` ones if it fails. [type-system.md](../../docs/type-system.md) §3.2 explains why this is sound.

Subtyping also performs the checker's type-argument inference. When one side of a goal is an unsolved metavariable,
`isSubtype` solves it with the other side and succeeds. The checker's application rule
([`../typechecker/application.mod.quest`](../typechecker/application.mod.quest)) creates the metavariables and calls
subtyping to fill them in; nothing here backtracks, so inference is local and greedy.

## Kinds and contractiveness

[`kinds.mod.quest`](kinds.mod.quest) synthesizes and checks kinds, so that `Int(Bool)` (applying a non-operator) or a
type argument outside its parameter's bound is rejected. It also provides the `resolve*Bound` functions, which find
the record, variant, option, or tuple type that a type variable is bounded by; the checker uses them so that, for
example, selecting `p.x` works when `p` has type `A` with `A <: Point`.

[`contractiveness.mod.quest`](contractiveness.mod.quest) checks that each recursive variable is guarded by a type
constructor. `Rec(L) Tuple head: Int tail: L end` is contractive; `Rec(X) X` and `Let Rec A = B and B = A` are not,
since they have no unique meaning and unfolding them never reaches a constructor, which lazy evaluation and the
subtyping prover rely on. The checker's elaboration of recursive type declarations calls it.

## Symbols and environments

[`symbols.int.quest`](symbols.int.quest) defines the symbols that name values, types, and kinds, and the scopes that
hold them. A type or kind symbol's id is unique for the life of the process and is also found globally by id, so a
type variable means the same thing in every scope; a type symbol's definition may be supplied once, after
declaration, but never replaced. [`env.int.quest`](env.int.quest) is the type-checking environment, `env.T`: the
scope stack (a base scope of builtins, a global scope above it), the interfaces and modules in scope, the standard
library registry that loads library units on demand, and the infix operator table. It also takes and restores
snapshots, which the REPL uses to roll back an input that failed. The environment lives here rather than in the
checker because the module system ([`../modules`](../modules)) and the kind checker need it as well.

## Printing

[`dump.int.quest`](dump.int.quest) prints types in two styles: a compact one for error messages and the typed AST dump,
which keeps alias names, shows a module's record type as `Module 'name'`, and bounds recursion; and a canonical
S-expression dump for golden tests. `model.show` is the plain printer the others build on.

## Reduced and canonical forms, for the backends

Two modules serve the IR and backends rather than the checker. [`reduce.mod.quest`](reduce.mod.quest) normalizes a
type's head with no environment: aliases removed, applications beta-reduced, recursion unfolded, bounds followed
(`normalizeType`, `resolveTypeBound`), and answers questions about option types that code generation needs, such as
the order of an option's cases. Its interface lists the several "expose the head" functions in the tree and how they
differ. [`canonical.mod.quest`](canonical.mod.quest) computes the canonical form of a type containing recursion: it
builds the type as a graph, minimizes it (partition refinement, as in DFA minimization), and writes it back as a type,
so that equal recursive types written differently get one C struct and one run-time descriptor.

The checker does not canonicalize. Canonicalizing every type at construction would make equality an id comparison,
but would lose the written names that messages and interface files show, and would cost time on code with no
recursion; the coinductive prover handles recursive types directly. Canonical forms are computed on demand, and cached,
by [`../repr/shapes.mod.quest`](../repr/shapes.mod.quest) and the dynamic-value serializer
([`../values`](../values)).

## Where it sits

In the module layering ([compiler-organization.md](../../docs/compiler-organization.md) §5), `model`, `symbols`,
`dump`, and `subtyping` are low: above `common` and `syntax`, below the module system's unit graph. `env`, `kinds`,
and `contractiveness` sit above the unit graph, since the environment holds loaded units. `reduce` and `canonical` sit
far above the checker, next to the IR. The bootstrap compiler's counterpart, module for module, is
[`bootstrap/python/quest/types`](../../bootstrap/python/quest/types/README.md).

## Further reading

- [type-system.md](../../docs/type-system.md): §2 the type forms and representation (§2.2 on sharing, aliases, and why
  only the backends canonicalize), §3 subkinding, subtyping, contractiveness and recursive groups, §4 existential tuples
  and path types, §5 environments and scoping.
- [c-representation.md](../../docs/c-representation.md) §5.7: what canonical forms become in C.
- [compiler-organization.md](../../docs/compiler-organization.md) §2 and §5: the directory's place in the tree and in
  the import layers.
- The papers in [docs/](../../docs): Cardelli's TheQuestLanguageAndSystem.md and TypefulProgramming.md for the source
  of the type system.
