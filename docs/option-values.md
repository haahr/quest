# Plan: Options as Values

A change to the language and to the self-hosted compiler's representation of options: an option of a case without
components is a value, compared by its case, and made without allocating; and an option of a type shaped like
`maybe.T` holds its one component directly, compared by it. It removes most of the allocation
[benchmarks.md](benchmarks.md) §3.6 describes (`lists.nil` is 6.8 million of ratio-regions' 29 million allocations;
`maybe.none` and `maybe.some` are much of peek's and zebra's).

**Status (2026-11-01):** steps 1 and 2 are done, with two C printer fixes for options made from or read through
their payloads (§5); benchmarks.md §8 measures them. The language change is adopted. Step 3, single-word options as
nullable pointers, is deferred. If it is not done, the single-word rule of §2.2 is to be undone (its `is` by
component in both compilers, the runtime, the interpreters, and the tests, and its paragraph in extensions.md),
since without the representation it costs a comparison of components and buys nothing.

---

## 1. Decisions

- **The language changes** (decided 2026-10-31), and [extensions.md](extensions.md) records it as an extension to
  the original language. *Typeful Programming* defines `is` as ordinary equality for `Ok`, `Bool`, `Char`, `Int`, and
  `Real`, and as "same memory location" for every other type (§3.1 there;
  [TypefulProgramming.md](TypefulProgramming.md) line 509), options included, so that two evaluations of
  `option red of Color end` are not `is` each other. After the change they are.
- **Single-word options are nullable pointers** (decided 2026-10-31): an option type of the shape of §2.2 holds its
  one component itself, when the component is a pointer, rather than a box holding it.
- **The rule is by shape, not by name:** `maybe.T` and every option type of its shape (§2.2), the user's included.
- **Generic code sees boxed options** (decided 2026-10-31): an option over a type parameter has today's layout, and
  polymorphic calls convert between it and the nullable one, as they convert tuples
  ([c-representation.md](c-representation.md) §5.1).
- **`is` depends on the static type it is applied at** (decided 2026-10-31), documented in extensions.md: a
  single-word option viewed at a supertype not of the shape (one with another case with components) is boxed there,
  and two `some`s made apart are then not `is` each other.
- **The bootstrap changes its semantics only** (decided 2026-10-31): its interpreters and C backend implement the new
  `is` and identity hash, so that the behavior goldens stay shared ([testing.md](testing.md) §2.8), and keep their
  representation. The representation is the self-hosted compiler's, in both of its backends' paths (the C printer,
  and the SSA for `ssac` and `arm64`).

## 2. The Language

### 2.1. Cases without components

Two options are `is` each other if they are the same object, or if they are of the same case and the case has no
components at the type `is` is applied at. A case is its name: `option thu of WeekDay end`, viewed as a `Day`, is
`option thu of Day end`. `isnot` is its negation, and `hash.identityHash` hashes such an option by its case, so that
an identity map's keys agree with `is`.

### 2.2. Single-word options

An option type is *single-word* if exactly one of its cases has components, exactly one, not `var`, and every other
case has none (`maybe.T(A)`: `none`, and `some with val: A end`). Two options of a single-word type are `is` each
other if they are of the same case and, for the case with a component, its components are `is` each other at its
type. So `maybe.some(:String)(s) is maybe.some(:String)(s)` is true, as `s is s` is.

A `var` component is excluded because its identity is the location, which a copy would not share.

### 2.3. The static type decides

`is` applies the rules of the type it is applied at. Options of a case with components at a type that is not
single-word keep the original rule, the same object. So two `some`s of one string are `is` each other as
`maybe.T(String)`s, and not after an upcast to `Option none some with val: String end other with x: Int end end`, at
which each is a distinct object. extensions.md gives this example.

## 3. Representation (the self-hosted compiler)

### 3.1. Cases without components are constants

- **One static object per case without components, per option type,** `{ .tag = n }`, read-only, in the unit's
  static data ([arm64.md](arm64.md) §7.5's description, which the C printer and the SSA's backends share). Each unit
  emits the ones it uses; they need not be shared across units, since `is` compares cases (§2.1), not addresses.
- **Making one is the constant:** `option red of T end`, `maybe.none`, `lists.nil`; `option ordinal(n) of T end`,
  when every case has none, indexes a table of them.
- **Converting one gives the target type's constant:** an upcast that would make a proxy, and the conversions between
  native and generic layouts, never allocate for such a case.
- **`is` at a type with such cases** is `a == b`, or the same case (through a proxy's tag map) with no components: a
  runtime helper the printers call. Types without such cases compare as now.
- **The runtime's generic `is` and identity hash** (`quest_val_is`, `quest_identity_hash`) do the same from the
  descriptor; an ABI bump.

### 3.2. Single-word options hold their component

- **Which types:** a single-word type whose component's slot representation is a pointer that is never null and
  never one of this type's constants: a string, array, tuple, closure, a record's or variant's box, or a boxed
  option. Not an `Int`, `Bool`, `Char`, `Real`, `Word`, or `Ok`, which have no spare value, nor a single-word option
  itself (whose constants could be its own component's), nor a type parameter (§3.3). The others of the shape keep
  the boxed layout with §2.2's `is`.
- **A value is the component, or one of the type's constants** (§3.1) for a case without components; the case is
  found by comparing with the constants (one compare for `maybe`). A constant is a valid boxed option of its case,
  so converting one to the boxed layout is free.
- **`case`, `?`, `!`, `ordinal`, and `opt!tag`** read the case by that comparison and the component as the value
  itself; a case binder is the component (no tuple to share).
- **`is`** is pointer equality (unproxied, as now), which is §2.2's rule here.
- **The descriptor records the representation** (an option descriptor's flag), so that the runtime's generic paths
  (`is`, identity hash, conversion, proxies, echo, serialization) read such values.
- **Upcasts:** to a single-word supertype (more cases without components, or the component at a supertype) the value
  stays a pointer, the component converted or proxied as its type needs and a constant mapped to the supertype's; to
  any other supertype it is boxed, allocating for the case with the component.

### 3.3. Generic code

An option over a type parameter keeps the boxed layout, whatever the type argument. A polymorphic call converts a
single-word option (§3.2) to it, boxing the component (a constant needs no box), and converts its result back,
reading the component. Specialization and inlining remove most of these conversions where the type is known; in
separate builds, `maybe`'s own functions are polymorphic calls into another unit, so `maybe.some` still allocates
there until whole-program inlining (inlining.md step 6) or specialization reaches it.

## 4. Testing

- **Behavior goldens, shared by both compilers:** `language/option_identity`, covering `is`, `isnot`, and
  `hash.identityHash` on cases without components (at one type, through an upcast that changes the tags, through a
  polymorphic function, as identity-map keys, made by `option ordinal(n) of T end`), on single-word options (equal
  components, distinct ones, `maybe.T(Int)` boxed, after an upcast to a supertype not of the shape), and that other
  cases with components keep the same-object rule.
- **The self-hosted compiler's IR and C goldens** showing the constants, the nullable layout, and the conversions;
  and per-pass tests of the conversions as backend-improvements.md §3.4 allows.
- **Every backend's runner mode** (`ssac`, `arm64`, `arm64-program`, `c-whole`, `arm64-whole`), the fixed points, and
  `tools/check --all` (the runtime and the bootstrap change).
- **Measurements** in benchmarks.md, dated: the suite through C and arm64, and the allocation counts of ratio-regions,
  peek, and zebra, before and after steps 2 and 3.

## 5. Steps

1. **The language** (§2), with no change of representation: the bootstrap's tree-walker and IR interpreter, the
   self-hosted interpreter, the runtime's `quest_val_is` and `quest_identity_hash`, and compiled `is` in both
   compilers' printers and the SSA. *Done when* the behavior golden (§4) passes in every implementation and backend,
   and [extensions.md](extensions.md) has its section (§6). *Done* (`63746a81`, ABI 58).
2. **Constants for cases without components** (§3.1), with the simplifier folding `?`, `ordinal`, `case`, and `is` of
   a known one. *Done when* making one allocates nothing in either backend path, and benchmarks.md records the
   allocation counts.
   *Done* (`83dbd27a`), with, in the C printer, an option made from its payload tuple's components rather than the
   tuple, and `o!tag.field` read from the option in place (`193a3f11`, [escape-analysis.md](escape-analysis.md) §6).
3. **Single-word options as pointers** (§3.2, §3.3), **deferred** (2026-11-01; if dropped, §2.2's rule is undone, as
   the status above says), after [escape-analysis.md](escape-analysis.md), and only if the allocations that still
   escape after it justify the change: layout, represent's plans and conversions, the descriptor
   flag and the runtime's generic paths, both backend paths. *Done when* `maybe.some(:String)` allocates nothing in a
   whole-program build, the suite passes in every mode, and benchmarks.md records the suite's times.
4. **Docs:** c-representation.md's options section (the constants and the nullable layout), runtime-design.md's
   identity bullets (§3 and §4 there), and benchmarks.md §3.6 marked done.

## 6. The Extension

[extensions.md](extensions.md) gets a section, "Options as Values", after "Semicolons": the paper's rule, quoted;
§2.1's and §2.2's rules and §2.3's dependence on the static type, with the upcast example; that
`{option red of Color end} is {option red of Color end}` is now true, as is `maybe.some(:String)(s) is
maybe.some(:String)(s)`; and why: these options are what the paper's programs and the suite use as enumerations and
optional values, and making a new object for each, so that `is` can tell them apart, is the cost §3.6 measures.
