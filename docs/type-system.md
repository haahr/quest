# Quest Type System: Semantics, Subtyping, and Term Elaboration

This document specifies the higher-order type system (System $F_{<:}^\omega$), semantic type representations,
subtyping algorithms, recursive contractiveness rules, iterated existential tuples (weak sums / packages),
path-dependent types, and bidirectional term typechecking for the Quest compiler.

---

## 1. Overview and Design Philosophy

Quest implements a higher-order type system with bounded quantification, structural subtyping, and iterated weak sums:
- **Level 2 (Kinds):** Classify types. `TYPE` classifies proper types; `POWER(B)` classifies subtypes of $B$;
  `ALL(X::K1) K2` classifies type operators.
- **Level 1 (Types and Type Operators):** Semantic types (`QType`) representing values, tuples, records, variants,
  options, functions, and path-dependent types (`QPathType`). Compile-time type functions (`Fun(X::K) T`) evaluate
  via typed $\lambda$-calculus reduction.
- **Level 0 (Values):** Runtime expressions evaluated against typing contexts.

The compiler avoids global ML-style constraint unification. Instead, it uses **local bidirectional typing**
(Dunfield & Krishnaswami) where types propagate from annotations downward (checking mode) or are computed from
constructs upward (synthesis mode).

---

## 2. Semantic Hierarchy (`bootstrap/python/quest/types.py`)

Semantic entities use a `Q` prefix to avoid name collisions with Python host primitives:

```
QKind (Level 2)
  ├── QTypeKind               TYPE (proper types)
  ├── QPowerKind              POWER(B) (subtypes of B)
  ├── QAllKind                ALL(X::K1) K2 (operator kinds)
  └── QKindVar                Named kind variable

QType (Level 1)
  ├── Base Types              QIntType, QRealType, QBoolType, QCharType, QStringType, QOkType
  ├── Dynamic & Exceptions    QDynamicType, QExceptionType
  ├── Aggregates              QTupleType, QRecordType, QVariantType, QOptionType
  ├── Functions & References  QFunType, QVarType, QArrayType, QOutType
  ├── Polymorphic & Operators QAllType, QAutoType, QTypeFun, QTypeApp
  ├── Recursive Types         QRecType, QRecGroupType
  ├── Variables & Paths       QTypeVar, QPathType, QAbstractType
  ├── Alias References        QAliasType (transparent; prints the alias name as written)
  └── Metavariables           QTypeMeta (local bidirectional inference)

QTupleComponent (Tuple Components)
  ├── QTupleField             Value field: name (optional), type_val, is_var
  ├── QTupleTypeFormal        Existential type formal: name, symbol_id, bound
  └── QTupleTypeBinding       Manifest type binding: name, type_val, bound
```

### 2.1. Module Record Provenance and Type Compaction
During typechecking and AST serialization, module records track their originating module name or interface identity
via the `provenance: Optional[str]` field on `QRecordType`. When formatting types for diagnostics or typed AST dumps:
- Record types with `provenance` format compactly as `Module '<name>'` rather than listing every exported value,
  function, and type signature.
- Recursive types (`QRecType`, `QRecGroupType`) bound their unfolding depth, and references to type aliases print
  under the alias's name as written (§2.2), which keeps typed AST serializations from exploding in size.
- `format_type_compact(t, env=None)` and `QType.format(env=None)` provide context-sensitive alias compaction.

### 2.2. Type Representation: Immutability, Identity, and Sharing
Semantic types are immutable values (frozen dataclasses), except for metavariables (`QTypeMeta`), which are solved in
place during inference. Several parts of the type checker depend on how type objects are built and shared:

- **No Python equality.** `==` on a `QType` raises. Use `is_type_equal(t1, t2, env)` for semantic (equi-recursive)
  equivalence, or `is` for identity. `structurally_equal(a, b)` compares field by field, for cross-checking
  optimizations; it is not type equivalence.
- **Hash-consing.** Types, kinds, and their components (fields, parameters, quantifiers, type formals) are interned:
  constructing a node returns the canonical object for its structure (a metaclass on `QType`, `QKind`, and the
  component classes looks it up in a weak table), so for interned nodes `is` decides structural identity. The key is
  the class plus every field, including display-only ones (record `provenance`, binder and path names), so two nodes
  that would print differently are never merged. Child nodes enter keys by identity, since they are canonical already.
  Nodes containing a metavariable are not interned: a shared node must not change meaning when a metavariable inside
  it is solved.
- **Named binders.** Binders (`Rec`, `All`, `Fun`, `Auto`, tuple type formals, recursive groups) and type variables
  carry globally unique symbol ids (`allocate_symbol_id`), not de Bruijn indices. Substitution relies on that
  uniqueness rather than renaming, and alpha-equivalent types elaborated separately (two `All(X) X->X`) are distinct
  objects, so each prints with the names written in its source.
- **Alias references.** A reference to a type alias elaborates to a `QAliasType` node carrying the name as written at
  the reference (`Span` inside the interface that declares it, `location.Span` or `ast.Expr` from an importing
  module), the alias's symbol, and its target (the definition). The node is transparent: evaluation
  (`evaluate_lazily`), and so subtyping and kinding, looks straight through it, and an alias of a recursive type
  unfolds through the alias so that recursive occurrences keep the name. The printer and the `.qi` writer print the
  name, so alias names survive `.qi` round trips and copies; hash-consing keeps references to different aliases (or
  one alias spelled differently) apart, since the name is part of the key. A type that is merely structurally equal
  to an alias, without coming from a reference to it, prints structurally. References to the builtin primitive names
  (`Int`, `Ok`, ...) elaborate to the primitives themselves (`alias_reference`). A substitution that changes an
  alias's target drops the alias node.
- **Alias nodes never reach C code generation.** `CEmitter.emit_program` and `emit_module` rebuild the typed AST,
  and the value symbols it references, without alias nodes (`strip_aliases`); the codegen type functions also strip
  defensively. The stripped copies remember their original types, so printed results (`let x:T = ...`) show alias
  names exactly as the interpreter does. Types serialized by `dynamic.extern` are written without alias names, so
  that they read back on their own.
- **Substitution preserves sharing.** Every type node, component (fields, parameters, quantifiers), and kind records at
  construction (`__post_init__`) its free variables, `_fv`: the symbol ids a substitution could replace inside it,
  following exactly the binder rules of its `_substitute_full` method. It also records `_has_meta`, whether it contains
  a metavariable. `QType.substitute` returns the node itself, without traversal, when no free variable is substituted
  and it contains no metavariable (a metavariable could later be solved to anything). When it does traverse, a node
  whose parts all come back unchanged is still returned as itself. Free variables are purely syntactic: aliases are
  not expanded.
- **Recursive types unfold once.** `QRecType.unfold_lazily` and `QRecGroupType.unfold_lazily` cache their result on
  the node. The unfolding refers back to the node, and the members of a recursive group share one tuple of sibling
  nodes (`QRecGroupType.siblings`), so repeated unfolding stays within one finite object graph.
- **Kinds are synthesized once per check.** `synth_kind` memoizes results by node identity for the duration of the
  outermost kind check, since elaborated types are DAGs and a node's kind depends only on the node and the binders in
  scope.
- **Symbols resolve globally.** `Environment.lookup_type_by_id` and `Environment.lookup_kind_by_id` use process-wide
  indexes from symbol id to `TypeSymbol` and `KindSymbol`, so type and kind variables mean the same thing in every
  scope; like types, kinds are fully resolvable at compile time. A `TypeSymbol`'s `definition` may be supplied once
  after declaration (`None` to a type) but never replaced.
- **Metavariables stay inside one call.** They are created for a polymorphic call's implicit type arguments and are
  all resolved, in the result type and the elaborated arguments, before the outermost call returns (§6.9).

---

## 3. Subtyping and Kind Theory

### 3.1. Subkinding ($K_1 \le K_2$)
Subkinding allows type operators and power kinds to be used wherever broader kind bounds are expected:
- *Reflexivity:* $K \le K$.
- *Power to Type:* $\text{POWER}(T) \le \text{TYPE}$ for any valid type $T$.
- *Power to Power:* $\text{POWER}(S) \le \text{POWER}(T) \iff S \le T$ (delegates to equi-recursive `is_subtype`).
- *Operator Kinds:* $\text{ALL}(X::K_1) K_2 \le \text{ALL}(Y::K_1') K_2'$
  $\iff K_1' \le K_1 \land K_2 \le K_2'[Y \mapsto X]$
  (contravariant in parameter kind, covariant in result kind).

### 3.2. Equi-Recursive Subtyping and the Coinductive Trail ($\Sigma$)
In Quest, recursive types are equi-recursive: $\text{Rec}(X::K) T \equiv T[\text{Rec}(X::K) T / X]$.
No explicit user `fold` or `unfold` operations are required.

To guarantee that subtyping checks are both terminating and fast ($\le O(N)$ for repeated references) when checking
recursive and structural types ($S \le T$):
1. **Identity & Reflexivity Fast Path:** If $S$ and $T$ are identical object references ($S \text{ is } T$),
   `is_subtype` immediately returns `True`. Similar identity fast paths are applied elementwise in `QTypeApp`,
   `QVarType`, `QArrayType`, `QOutType`, and `QExceptionType` to bypass exponential pairwise re-evaluations across
   invariant types.
2. **Lazy Evaluation:** Evaluates types lazily only as needed to expose outermost constructors.
3. **Active Assumption Trail ($\Sigma \vdash (S, T)$):** Pairs under proof are recorded in a coinductive trail
   (`SubtypeTrail`). If $(S, T)$ is encountered again under recursive unfolding, it is assumed valid by coinduction.
   Named type variables are keyed by symbol id, path types by root and field, and all other types by object identity;
   the trail keeps every keyed object alive for the duration of the proof, so a freed temporary's id can never be
   reused by an unrelated type and match its assumption.
4. Correctly handles polarity flips during function parameter contravariance.
5. **Subtype Cache:** Results are cached process-wide, keyed by the identities of hash-consed types and by whether an
   environment was given (without one, aliases are not expanded). `is_type_equal` proves both directions as one proof
   with one trail.

#### Why a proof's results are committed only when it finishes
During a top-level check, `is_subtype` records each pair it decides; at the end it commits them all if the answer is
`True`, or only the `False` ones if not.

After a check finishes, nothing about its result can change: types are immutable and hash-consed, symbols resolve
globally, and pairs involving a metavariable are never cached (`is_subtype` solves metavariables as a side effect). The
hazard lies inside a proof. Recursive types are compared coinductively: to prove $A \le B$, the pair is assumed while
the unfolding is checked, and a recurrence of the pair counts as proved. A nested goal decided while such an assumption
is open may hold only because of it:

```
A = Rec(X) Record f: X  g: Int    end
B = Rec(Y) Record f: Y  g: String end
```

Proving $A \le B$ assumes the pair, checks field `f` (the assumption gives `True`), then checks field `g`
(`Int <: String` is `False`); the result is `False`, and the `True` for `f` was conditional on a refuted assumption.
Caching it would be wrong. Hence:
- **A proof that returns `True`** leaves only true facts behind. A proof succeeds only if every nested goal succeeds
  (goals are combined with *and*; the one check that may fail and fall through, a type variable's bound, falls through
  only to `False`), so the pairs it decided or assumed form a consistent set of facts, and all are cached as `True`.
- **`False` results are always cached**, even when decided mid-proof: extra coinductive assumptions can only make more
  goals provable, so a goal that fails with them also fails without them.
- **The conditional `True` results of a proof that returns `False`** are discarded.

Symbol meanings only become more defined (a definition may arrive once, possibly after the symbol was first referenced),
so the environment remembers symbol ids that a lookup found undeclared or undefined and clears the cache when one of
them gains a meaning. The cache is also cleared when it exceeds its size limit.

### 3.3. Recursive Contractiveness ($C \succ X$)
To guarantee that recursive type definitions have unique solutions and do not produce infinite loops or degenerate
empty types, definitions must be **contractive** in their recursive variables (Cardelli & Longo 1991, Section 2.4/2.9,
rule `[T µ]`).

A type $C$ is contractive in $X$ ($C \succ X$) iff the recursive variable $X$ occurs exclusively behind a guarding
type constructor (`Record`, `Tuple`, `Option`, `Variant`, `Fun`, `Array`, `Var`, `Out`).
- **Bare occurrences are rejected:**
  ```quest
  Let Rec Bad::TYPE = Bad;              (* REJECTED: bare self-recursion *)
  Let Rec A = B and B = A;              (* REJECTED: mutual bare cycle *)
  Rec(X)X                               (* REJECTED: inline bare recursion *)
  ```
- **Guarded occurrences are accepted:**
  ```quest
  Let Rec List = Tuple head:Int tail:List end;   (* ACCEPTED: guarded by Tuple *)
  Let Rec Tree = Option empty, node with t:Tree end; (* ACCEPTED: guarded by Option *)
  ```

---

## 4. Iterated Existential Tuples and Weak Sums

Quest represents abstract data types, packages, and modules through **iterated weak sums** (existential tuples),
following Cardelli (*The Quest Language and System* §4.4, §5.3, §7.1, §10, and *A Semantic Basis for Quest* §1.2, §2).

### 4.1. Dependent Signatures and Type Formals
Tuples in Quest can interleave type formals (`X::K`), value fields (`x: T`), and manifest type bindings (`Let X = T`):
```quest
Let PointPackage = Tuple
  Point::TYPE
  origin: Point
  distance(p1: Point, p2: Point): Real
end;
```
Signature elaboration (`bootstrap/python/quest/elaborate_types.py`) proceeds sequentially in an ordered dependent
scope. Each type formal `X::K` introduces a `TypeSymbol` into the local scope so subsequent fields can refer to `X`.
Anonymous type formals (`::TYPE`) are prohibited; type formals must specify an identifier.

### 4.2. Extended Subsignatures (`is_subtype`)
Subtyping between tuple types implements Cardelli's extended subsignature rules (§7.1, §10.2):
1. **Prefix Subtyping:** A tuple type with extra trailing fields is a subtype of any prefix signature:
   $$\text{len}(S.\text{fields}) \ge \text{len}(T.\text{fields})$$
   For example, `Tuple age:Int speed:Int end <: Tuple age:Int end`.
2. **Exact Component Name Matching (No $\alpha$-Conversion):**
   Components must match identically in name and position:
   - `Tuple A::TYPE a:A end` is **not** a subtype of `Tuple B::TYPE a:B end`.
   - Matching names keeps path-dependent dot notation unambiguous and avoids accidental structural matches
     across distinct interfaces.
3. **Type Formal Subkinding & Variable Remapping:**
   For matching type formals (`A::K` in $S$ vs `A::L` in $T$), subtyping requires $K <:: L$. The formal's internal
   symbol ID in $T$ is remapped to the corresponding symbol ID in $S$ for checking subsequent components in $T$.
4. **Manifest Type Binding Subsumption:**
   A tuple with a concrete manifest binding is a subtype of a tuple with an abstract type formal:
   `Tuple Def A::TYPE = Int a:A end <: Tuple A::TYPE a:A end`.
   The manifest type definition is substituted into remaining components of the supertype signature.
5. **Mutable Component Invariance and Covariance (Cardelli §4.8):**
   - If supertype component is mutable (`var`), subtype component must also be mutable and types must match
     invariantly ($S.f \le: T.f \land T.f \le: S.f$).
   - If supertype component is immutable, a mutable subtype component is allowed by forgetting mutability
     (`Tuple var a:A end <: Tuple a:A end`).

### 4.3. Existential Packing and Witness Checking
Existential packages are constructed using tuple expressions with type witness bindings:
```quest
let p: PointPackage = tuple
  Let Point::TYPE = Tuple x: Real y: Real end
  let origin: Point = tuple 0.0 0.0 end
  let distance(p1: Point, p2: Point): Real = ...
end;
```
- **Explicit Ascription Required:**
  Existential packages require explicit type ascription (e.g. `let p: PointPackage = tuple ... end`).
  Unannotated tuple constructors synthesize transparent tuples containing `QTupleTypeBinding`, which coerce
  to existential signatures via subtyping.
- **Witness Checking (`_check_tuple_expr`):**
  When checking a tuple against an existential tuple type:
  1. Witness type bindings (`Let X::K = W`) are matched against expected type formals (`X::K`).
  2. Witness kinds are validated: $\Gamma \vdash W :: K$.
  3. Witnesses are substituted into subsequent component signatures before checking value fields.
  4. Mismatched witness bounds, names, or arities produce informative compile-time diagnostics.

### 4.4. Path-Dependent Types (`QPathType`)
When an existential tuple is bound to an immutable identifier $x$, its type components can be accessed via
**path-dependent types** ($x.A$):
```quest
let origin: p.Point = p.origin;
```
- **Representation:** `QPathType(root_name, root_symbol_id, field_name, bound)`.
- **Immutable Path Roots Only:**
  Path-dependent types can only be rooted at **immutable value bindings** (`let` bindings or immutable function
  parameters). Projecting type components from mutable variables (`let var x: T`) is rejected with a compile-time
  error to prevent unsoundness under variable reassignment.
- **Path Subtyping Rules:**
  1. *Reflexivity:* $x.A \le x.A$ holds when both path types share the same `root_symbol_id` and `field_name`.
     Distinct packages $t_1$ and $t_2$ have incompatible abstract types ($t_1.A \not\le t_2.A$).
  2. *Bounded Subtyping:* When a type formal is bounded by a power kind ($A :: \text{POWER}(B)$), its path type
     inherits that bound: $x.A \le B$. This allows abstract types with bounds to participate in operations of their
     supertype (e.g., arithmetic on bounded integers).
- **Member Selection Restrictions (`_synth_select_expr`):**
  - Type components cannot be evaluated as values: `p.Point` in a value expression produces a type error.
  - Type-dependent value members (`x.a`) cannot be selected from anonymous or compound tuple expressions;
    the package must be bound to an immutable variable first.

### 4.5. Scope Escape Prevention (Scope Extrusion)
Abstract path types cannot escape the lexical scope of their root variable:
```quest
let getOrigin(pkg: PointPackage) = pkg.origin;       (* REJECTED: pkg.Point escapes *)
let getOrigin(pkg: PointPackage): pkg.Point = ...;   (* REJECTED: dependent return type *)
```
- **Checking Rule (`check_no_escaping_path_types`):**
  The typechecker inspects types exiting local scopes (function return types, block results, pattern-matching branches,
  and inspect expressions). If a synthesized type contains a `QPathType` rooted at a locally bound `symbol_id`,
  typechecking aborts with:
  `TypeError: Abstract type 'pkg.Point' cannot escape the scope of 'pkg'`.
- Function return types in Quest cannot depend on value parameters (no value-dependent $\Pi$-types).

### 4.6. REPL Presentation
Following Cardelli §5.3:
- Existential packages print in the REPL with hidden representations:
  `p = tuple <Hidden>::TYPE origin=<hidden> distance=<fun> end : PointPackage`.
- Values whose static type is an abstract path type print as `<hidden>`:
  `origin = <hidden> : p.Point`.

---

## 5. Environment and Scoping (`bootstrap/python/quest/env.py`)

Compilation state is maintained across lexical scopes:
- **`Scope`:** An ordered mapping of identifiers to `Symbol` instances. Ordered scope resolution ensures that
  dependent components (e.g. `Tuple X::TYPE init:X end`) are evaluated left-to-right.
- **`Symbol`:**
  - `ValueSymbol(name, symbol_id, type_val, is_var, is_out)`: Every value symbol has a unique auto-incrementing
    integer `symbol_id` used for path-dependent root identity and scope escape tracking.
  - `TypeSymbol(name, symbol_id, kind, definition)`: resolved by `symbol_id` through a process-wide index,
    independent of the current scope (§2.2).
  - `KindSymbol(name, symbol_id, kind)`
- **Stateless Manifest vs. Abstract Types:**
  Type transparency is controlled structurally without ambient mode flags:
  - Inside an implementing module, `definition` points to concrete `QType` (transparent).
  - Outside in client scopes, `definition` is `None` (abstract, bounded by `kind`).

### 5.1. Two-Tier Root Environment & Module Isolation (Cardelli §11.3)
The typechecking environment employs a two-tier root architecture:
- **`base_scope`:** Declares primitive language types (`Int`, `Real`, `Bool`, `Char`, `String`, `Array`), kinds
  (`TYPE`, `POWER`), built-in operators, and exception constants.
- **`global_scope`:** Inherits from `base_scope` and binds the pre-linked standard library module records
  (`arrayOp`, `ascii`, `conv`, `dynamic`, `int`, `list`, `reader`, `real`, `string`, `word`, `writer`) and their
  interfaces (`ArrayOp`, `Ascii`, `Conv`, `Dynamic`, `IntOp`, `List`, `Reader`, `RealOp`, `StringOp`, `Word`, `Writer`).
- **Module Isolation:** Top-level expressions and REPL sessions execute in `global_scope`, allowing direct access to
  standard library modules without `import`. However, standalone module declarations (`module ... end`) have their
  internal elaboration scopes parented directly to `base_scope`. Consequently, modules cannot access pre-linked
  standard library modules without an explicit `import` statement (Cardelli §11.3).

---

## 6. Term Elaboration and Typechecking (`elaborate_types.py` and `typechecker.py`)

Term typechecking translates syntactic AST expressions into decorated `TypedExpr` nodes:

### 6.1. Bidirectional Discipline
- **Checking Mode ($\Gamma \vdash e \Leftarrow T$):** Pushes expected type $T$ down into expression $e$. Enables
  local inference for numeric constants, record upcasts, existential tuple packing, and function bodies.
- **Synthesis Mode ($\Gamma \vdash e \Rightarrow T$):** Infers minimal type $T$ from $e$ upward.

### 6.2. Mutability, Assignment, and Reference Parameters
Mutable locations are declared with `var`:
```quest
let var x: Int = 10;
x := x + 1;
```
- In value positions, mutable locations automatically coerce to their underlying value type (`TypedDerefCell`).
- In assignment positions (`x := e`), the target must be an explicit mutable location (`is_var=True` or `QVarType`).
- Path-dependent types cannot be rooted at mutable locations.

#### 6.2.1. Parameter Modes: `var` and `out`
Following Cardelli (*Typeful Programming* §4.8), function signatures support reference parameters:
- `var p: T`: Read-write reference parameter. Within the callee body, `p` can be both read and assigned (`p := e`).
- `out p: T`: Strict write-only parameter. Within the callee body, `p` can only be assigned to (`p := e`).
  Attempting to read from an `out` parameter triggers a compile-time `TypeError`.

#### 6.2.2. Callsite Reference Syntax (`@` and `var(...)`)
- Callsites for `var` and `out` parameters strictly require explicit `@` lvalue references or temporary cells `var(e)`.
  Bare identifiers are rejected with a `TypeError`.
- Supported `@` targets: mutable variables (`@x`), mutable record fields (`@r.f`), array elements (`@a[i]`),
  tuple elements (`@t.1`), and arbitrary chained paths ending in a mutable location (`@r.a.b`, `@a[i].f`).
- Forwarding an existing reference parameter `y` to another callee is written `g(@y)` and forwards the underlying
  pointer without re-referencing.

#### 6.2.3. Closure Capture Restrictions
To ensure stack safety and prevent escaping pointer references without requiring boxing every local variable:
- Capturing `var` or `out` parameters inside closures is prohibited.
- Capturing local stack-allocated mutable variables (`let var x = ...` inside a function body) inside closures is
  prohibited.
- Top-level module-level `var` variables are global module state and may be referenced freely by closures.

### 6.3. Strict Non-Overloaded Operators and Numeric Non-Coercion
Quest disallows implicit numeric coercions: `Int` and `Real` are disjoint types. Arithmetic between differing numeric
types requires explicit conversion operations (`conv.real(n)`).

Quest does not overload operators across types; distinct operators exist for each primitive type (Cardelli §4.2):
- **Integer arithmetic:** `+`, `-`, `*`, `/`, `%`, `mod` : `Int, Int -> Int`
- **Integer relations:** `<`, `<=`, `>`, `>=` : `Int, Int -> Bool`
- **Real arithmetic:** `++`, `--`, `**`, `//`, `^^` : `Real, Real -> Real`
- **Real relations:** `<<`, `<<=`, `>>`, `>>=` : `Real, Real -> Bool`
- **String concatenation:** `<>` : `String, String -> String`
- **Boolean logic:** `/\`, `\/` : `Bool, Bool -> Bool`
- **Identity & Equality:** `is`, `isnot` : `All(A) A, A -> Bool`

### 6.4. Explicit Polymorphic Instantiation (`TypedTypeApp`)
Polymorphic functions can be explicitly instantiated at call sites using type arguments:
```quest
let id = fun(A::TYPE)(x: A): A x;
let n = id(:Int)(42);
```
Type arguments prefixed with `:` (`:Type`) match leading type quantifiers in `QAllType`. The typechecker
validates that actual type arguments satisfy their corresponding kind bounds and emits `TypedTypeApp` nodes.

### 6.5. Parameter Passing Modes, Out Types, and Lvalues
Quest supports three parameter passing modes in signatures:
- **Value (`val`, default):** Pass-by-value.
- **Reference (`var`):** Pass-by-reference (`Var(T)`). The type constructor `Var` is invariant.
- **Output (`out`):** Write-only parameter passing (`Out(T)`):
  - **Contravariance:** If $A <: B$, then $\text{Out}(B) <: \text{Out}(A)$ (Cardelli §7.7).
  - **Relation to Var:** If $B <: A$, then $\text{Var}(A) <: \text{Out}(B)$.
  - **Callee Semantics:** Inside the function body, `out` parameters (`sym.is_out=True`) can only be assigned to
    (`y := expr`); evaluating an `out` parameter in a value expression is rejected.
  - **Caller Coercion:** At call sites, arguments bound to `out` parameters must explicitly supply an lvalue reference
    via `@loc` (e.g. `@x` or `@r.field`, translated to `TypedSelectRef`) or an on-the-fly cell via `var(expr)`.

### 6.6. Monadic Operator Typing Rules
Monadic operators are typed with high precedence:
- `not e`: Requires $e \Leftarrow \text{Bool}$, synthesizes $\text{Bool}$.
- `extent e`: Requires $e \Leftarrow \text{Array}(T)$, synthesizes $\text{Int}$.
- `ordinal e`: Requires $e \Leftarrow \text{Option} \dots \text{end}$, synthesizes $\text{Int}$ representing the
  zero-based declaration index of the injected option tag.

### 6.7. Array Typing and Explicit Element Types
Array constructors synthesize `QArrayType`:
- `array of a1 ... an end`: If all elements are homogeneous, synthesizes `Array(T)`.
- `array of :T a1 ... an end`: Explicitly checks each element against $T$ and synthesizes `Array(T)`.
- `array of(cnt init)`: Checks $cnt \Leftarrow \text{Int}$, synthesizes `Array(T)` where $\text{init} \Rightarrow T$.
- **Variant Subtyping in Aggregates:**
  When array elements or tuple components are checked against an expected variant supertype, subtyped variants
  are accepted and coerced via static tag remapping at the aggregate boundary.

### 6.8. Option Typing and Extraction Semantics
Option types provide ordered sum types with ordinal reflection and extraction (Cardelli §4.5):
- **Option Extraction (`!`):** When applied to an option `opt!tag`, the synthesized type is
  `Tuple :Int <fields> end`, where `:Int` is the anonymous ordinal component followed by the components of the
  branch's payload signature (e.g. `bOption!b` produces `Tuple :Int x:Bool end`). In contrast, variant extraction
  (`v!tag`) synthesizes the bare payload type directly.
- **Option Construction by Ordinal:** `option ordinal(e) of OptionType [with Binding] end`:
  - Checks $e \Leftarrow \text{Int}$.
  - Requires that all branches of `OptionType` share identical signatures (component names and types). Mismatched
    branch signatures trigger a compile-time `TypeError`.
  - Checks the payload binding against the common branch signature.

### 6.9. Bounded Quantifiers and Type Variables
Universal quantifiers can be bounded by power kinds (`A <: Bound`, represented semantically as `QPowerKind(Bound)`):
- **Bounded Record Type Variables:** When $A <: \text{Record}$, selecting a field `p.x` where $p: A$ succeeds if the
  bound record type declares $x$, synthesizing $x$'s field type. Assigning to a mutable field `p.x := v` is permitted
  when $x$ is declared `var`.
- **Bounded Variant Type Variables:** When $V <: \text{Variant}$, checking `v?tag`, extracting `v!tag`, and pattern
  matching `case v ... end` inspect the bound variant type to validate variant tags and payload types.
- **Subkinding and Type Argument Inference:** When instantiating a bounded quantifier implicitly or explicitly, type
  arguments are validated against the upper bound via `is_subkind(POWER(Actual), POWER(Bound)) <=> Actual <: Bound`.
- **Implicit Type Arguments (Cardelli, *The Quest Language and System* §4):** Type applications may be omitted when
  the context is sufficiently informative. A polymorphic call instantiates its quantifiers with metavariables, which
  are solved first from the types of the arguments (`cons(3 tail)`) and then from the type required of the call by
  its context (`cons(3 nil())`, where the argument position requires `List(Int)`). An empty application `nil()` of a
  polymorphic constant instantiates it the same way. A type argument that is still unknown is an error ("in
  isolation, `nil()` does not express enough information"), so `let x = nil()` is rejected; there is no defaulting.
  The one exception is a call whose expected type still depends on the enclosing call's unknown type arguments
  (`nil()` in `cons(nil() tail)`): it defers its own to the enclosing call, which reports any that remain unknown.
  Metavariables never escape the outermost call.

### 6.10. Function Signatures and Recursive Bindings (`let rec`)
- **Explicit Parameter Types:** Function parameters are syntactically signatures ($S$). In Quest, every value
  parameter in a signature must provide an explicit type annotation (`x: Int` or `: Int`); parameter types are
  not inferred from usage (Cardelli, *The Quest Language and System* §4).
- **Explicit Return Types on Recursive Functions:**
  While non-recursive functions allow omitting return types (`let f(S) = b` or `fun(S) b`) by synthesizing the
  return type from the body, **recursive functions (`let rec`) require an explicit return type annotation**
  (`let rec f(S): Ret = ...`).
- **Typing Discipline & Context:**
  Quest uses local bidirectional typechecking rather than global Hindley-Milner type inference. In a recursive
  binding, the function identifier $f$ must be introduced into the typing context $\Gamma$ before typechecking
  recursive calls within the function body:
  $$\frac{\Gamma, f: \text{All}(S) \text{Ret} \vdash \text{fun}(S): \text{Ret } b \Leftarrow \text{All}(S) \text{Ret}}
  {\Gamma \vdash \text{let rec } f(S): \text{Ret} = b}$$
  Without an explicit return type annotation, $f$'s signature cannot be formed prior to checking the body.
  Omitting return types or parameter types on recursive definitions triggers a compilation error.
- **Recursive Value Bindings:**
  Any recursive value binding without parameters (`let rec x: T = e`) similarly requires an explicit type
  annotation, and its right-hand side entity must syntactically be a constructor or abstraction (Cardelli,
  *Typeful Programming* §4.3).

### 6.10. Dynamic Typing and Narrowing (`dynamic: Dynamic`)
Dynamic values package a runtime value together with its static type:
- **Creation (`dynamic.new`):**
  - Explicit: `dynamic.new(:Type val)` packages `val` into `Dynamic.T` (erased `QDynamicType`) paired with `Type`.
  - Inferred: `dynamic.new(val)` infers the static type of `val` and packages it into `Dynamic.T`.
  - Legacy bare `dynamic(x)` function syntax is not supported.
- **Narrowing (`dynamic.be`):**
  - `dynamic.be(:TargetType d)` dynamically validates that the dynamic value `d`'s stored type is a subtype of
    `TargetType`. On success, it returns the unwrapped value statically typed as `TargetType`. On mismatch, it
    raises the language exception `dynamic.error`.
- **Dynamic Inspection:**
  - `inspect d when T1 with v then e1 else e2 end` tests membership against branches dynamically.

#### 6.10.1. Intensional Type Analysis vs. Pure Type Erasure
In a pure type erasure model (such as standard System $F_{<:}$ or ML), type parameters are discarded at compile time, leaving runtime code to operate exclusively on untyped representations. However, `Dynamic` requires **Intensional Type Analysis (ITA)** (Harper & Morrisett 1995), because `dynamic.new` and `dynamic.be` inspect types at runtime:
- **Why Erasure Breaks Generic Wrappers:**
  Consider a polymorphic wrapper:
  ```quest
  let dynamicWrapper(A::TYPE a:A): dynamic.T = dynamic.new(:A a);
  ```
  If `A` were erased, `dynamicWrapper` would have no runtime knowledge of `A` and could not package `a` with its type descriptor.
- **Comparison with Java RTTI vs. Erasure:**
  In Java, generic methods are implemented via erasure (`<T> void foo(T x)` erases `T` to `Object`). Java's dynamic operations (`instanceof`, reflection, `getClass()`) do not inspect erased generic parameters; they rely on reified class metadata (`java.lang.Class<T>`) stored in every object's heap header. When Java code needs dynamic operations on an abstract type parameter, it cannot write `new T()` or `x instanceof T`; it forces the programmer to pass an explicit runtime type token (`Class<T> typeToken`). In Quest, `dynamic.new(A::TYPE a:A)` specifies `A` as a formal type parameter, so the compiler automatically passes runtime type descriptors (`const QTypeDescriptor *descriptor_A`) to all quantified functions.

### 6.11. Auto Types and Inspect (Cardelli §4.6, §6.7)
An auto type `Auto A::K with S end` (`QAutoType`) is the union of the signatures `S[T/A]` over all closed types `T` of
kind `K`. An auto value pairs such a type `T`, its *type component*, with components matching `S[T/A]`, so that the
value describes its own shape; `inspect` recovers the type at run time.

```quest
Let UniformPair = Auto A::TYPE with fst,snd:A end;
let p: UniformPair = auto :Bool with false true end;
inspect p
when Bool with arm then arm.fst \/ arm.snd
when Int with arm then {arm.fst * arm.snd} isnot 0
end
```

- **Construction (`_check_auto_expr`):** `auto [let A [HasKind] =] :T with Binding end` is checked against an
  expected auto type; its type is never synthesized, since nothing in the value says which components vary with
  `T`. `T` must be closed and have the auto type's kind (`T <: Object` for `Auto A<:Object ...`), and the binding is
  checked as a tuple against `Tuple S[T/A] end`. A named type component (`auto let A<:Car = :Car with ... end`) is a
  transparent alias for `T` inside the binding, and `T` must also have its declared kind. The result is a
  `TypedAuto`.
- **Closed types:** the type component of an auto value and the type of every `when` clause of an `inspect` on an
  auto value must be *closed*: they may not mention a type parameter of an enclosing polymorphic function (the
  typechecker records these in `_type_param_ids`) or an abstract type projected from a package value (`t.A`, a
  `QPathType`). Types exported abstractly by modules, such as `writer.T`, are closed: they denote the same type
  throughout a program. *Possible extension:* the C backend already passes runtime descriptors for type parameters
  (§6.10.1), so `auto :A with ... end` inside `fun(A::TYPE ...)` could be supported there; the interpreter would
  need run-time type arguments to match.
- **Subtyping (§6.7, `_prove_subtype_step`):** `Auto A::K1 with S1 end <: Auto B::K2 with S2 end` when `K1` is a
  subkind of `K2` and `S1` matches `S2[A/B]` as tuple signatures do (§4.2): a prefix, with the same component names
  in the same order, covariant immutable components, and invariant `var` components. Thus
  `Auto A<:Car with a:A end <: Auto A<:Object with a:A end`.
- **Inspect (`_elaborate_auto_inspect_branches`):** each branch `when T with x then e` binds `x` to the auto value's
  components with type `Tuple S[T/A] end`, so `x.fst` has type `T`. A binder may be declared with a supertype
  (`with x: Tuple fst:T end`). The first matching branch is taken; if none matches and there is no `else` branch,
  `inspect` raises `dynamic.error`. Branch results are joined, or checked against the expected type, as for `case`.
- **Matching rule (`auto_matches_subtypes`):** Cardelli selects the first branch whose type is a supertype of the
  type component. Viewing the components at a supertype is sound only when `A` occurs in `S` solely as the whole
  type of immutable components (`fst,snd:A`, `a:A`), and those are the auto types whose inspect matches by
  subtyping. For any other signature (such as `x:A show(:A):String`, `l:List(A)`, or one with `var` components) a
  branch matches only when its type *equals* the type component: if `S` is `f(x:A):Int` and the type component is
  `Car`, a branch `when Object` would let `f` be applied to an `Object` that is not a `Car`. A typed branch is
  marked `exact` in the typed AST when it matches by equality.

**Relationship with `Dynamic`.** Cardelli defines `Dynamic_T` as `Auto A::TYPE with a:A end`, and both
representations are alike in this implementation (a `QDynamic`, see [c-representation.md](c-representation.md) §8.1), but
`Dynamic` remains a separate built-in: `inspect` on a `Dynamic` binds the contained value itself rather than a
one-component tuple, and `dynamic.new(A::TYPE a:A)` packages a type *parameter*, which the closedness restriction
forbids for auto values. `Dynamic.T` could become a library alias for `Auto A::TYPE with a:A end` once auto values
may have type parameters as their type component (the extension above); `new`, `be`, and the `inspect` binder would
then be written in terms of auto values (`be(:A d)` is `inspect d when A with x then x.a end`).

### 6.12. List Module and Type Operator (`list: List`)
The `list` module provides functional, immutable linked lists conforming to interface `List`:
- **Higher-Kinded Abstract Type:** `List.T :: ALL(A::TYPE)::TYPE`.
- **Operations:**
  - `list.nil(:A) : list.T(A)`: Empty list.
  - `list.cons(:A)(x: A l: list.T(A)) : list.T(A)`: Prepends element `x`.
  - `list.null(:A)(l: list.T(A)) : Bool`: Emptiness test.
  - `list.head(:A)(l: list.T(A)) : A`: First element; raises `list.error` if empty.
  - `list.tail(:A)(l: list.T(A)) : list.T(A)`: Tail sublist; raises `list.error` if empty.
  - `list.length(:A)(l: list.T(A)) : Int`: Element count.
  - `list.enum(:A)(l: list.T(A)) : Array(A)`: Converts list to an array.
  - `list.error : Exception`: Raised on invalid operations (e.g. `head` or `tail` on an empty list).

### 6.13. String Substring Precedence (`StringOp.precedesSub`)
The `StringOp` interface and `string` module provide substring comparison:
- `string.precedesSub(s1: String, start1: Int, size1: Int, s2: String, start2: Int, size2: Int) : Bool`
- Compares slices `s1[start1 : start1 + size1]` and `s2[start2 : start2 + size2]` lexicographically. Raises
  `string.error` if any bounds are invalid.

---

## 7. Summary Complexity Matrix

| Complexity Area | Key Difficulty | Architectural Solution |
| :--- | :--- | :--- |
| **Recursive Subtyping** | Infinite expansion loops & polarity flips | Lazy eval + coinductive trail $\Sigma$ |
| **Dependent Signatures** | Fields depend on earlier type parameters | Ordered `Scope` incremental elaboration |
| **Extended Subsignatures** | Prefix & name matching, manifest types | Subsignature rule in `is_subtype` |
| **Existential Packing** | Witness kind checking & field substitution | Bidirectional `_check_tuple_expr` |
| **Auto Types** | Run-time type discrimination stays sound | Closed types; subtype matching only for covariant signatures |
| **Path-Dependent Types** | Abstract identity tied to bindings | `QPathType` with `root_symbol_id` |
| **Scope Extrusion** | Local package types escaping scope | Escape checker in `typechecker.py` |
| **Type $\lambda$-Calculus** | $\beta$-reduction & variable capture | Lazy eval + `QTypeVar` symbol IDs |
| **Module Manifest Types** | Concrete inside, abstract outside | Structural `TypeSymbol(kind, definition)` |
| **Diamond Imports** | Disparate paths for same interface | Canonical symbol interning in `Environment` |
| **Contractiveness** | Non-terminating or degenerate recursion | Contractiveness validator ($C \succ X$) |

---

## See Also
- [README.md](../README.md): Project overview and quickstart.
- [syntax.md](syntax.md): Lexer, parser, and untyped AST.
- [pipeline.md](pipeline.md): Compiler pipeline framework and CLI driver.
- [testing.md](testing.md): Testing framework and golden outputs.
- [TheQuestLanguageAndSystem.md](TheQuestLanguageAndSystem.md): Cardelli (1990) language manual.
- [ASemanticBasisForQuest.md](ASemanticBasisForQuest.md): Cardelli & Longo (1991) formal semantics.
- [TypefulProgramming.md](TypefulProgramming.md): Cardelli (1989/1993) language specification.
