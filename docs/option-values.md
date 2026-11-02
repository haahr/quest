# Plan: Single-Word Options as Pointers

The rest of options as values: an option of a type shaped like `maybe.T` held as its one component, or as a constant
for its cases without components, rather than as a box. What is done, the language's rule
([extensions.md](extensions.md), "Options as Values") and constants for cases without components
([c-representation.md](c-representation.md) §5.3), is measured in [benchmarks.md](benchmarks.md) §8.

**Status (2026-11-01): deferred.** Escape analysis ([ssa.md](ssa.md) §4.2) removed most payload tuples; what still
escapes in peek and zebra is mostly `maybe.some`'s box, which this would remove ([benchmarks.md](benchmarks.md) §9).
If this plan is dropped, the single-word rule of extensions.md is to be undone (its `is` by component in both
compilers, the runtime, the interpreters, and the tests, and its paragraph in extensions.md), since without the
representation it costs a comparison of components and buys nothing.

---

## 1. Decisions

- **Single-word options are nullable pointers** (decided 2026-10-31): an option type of the single-word shape holds
  its one component itself, when the component is a pointer, rather than a box holding it.
- **The rule is by shape, not by name:** `maybe.T` and every option type of its shape, the user's included.
- **Generic code sees boxed options** (decided 2026-10-31): an option over a type parameter has the boxed layout, and
  polymorphic calls convert between it and the nullable one, as they convert tuples
  ([c-representation.md](c-representation.md) §5.1).
- **The bootstrap changes nothing:** it already implements the language's `is`; the representation is the
  self-hosted compiler's, in both of its backends' paths (the C printer, and the SSA for `ssac` and `arm64`).

## 2. Representation

- **Which types:** a single-word type whose component's slot representation is a pointer that is never null and
  never one of this type's constants: a string, array, tuple, closure, a record's or variant's box, or a boxed
  option. Not an `Int`, `Bool`, `Char`, `Real`, `Word`, or `Ok`, which have no spare value, nor a single-word option
  itself (whose constants could be its own component's), nor a type parameter (§3). The others of the shape keep
  the boxed layout with the language's `is`.
- **A value is the component, or one of the type's constants** for a case without components; the case is found by
  comparing with the constants (one compare for `maybe`). A constant is a valid boxed option of its case, so
  converting one to the boxed layout is free.
- **`case`, `?`, `!`, `ordinal`, and `opt!tag`** read the case by that comparison and the component as the value
  itself; a case binder is the component (no tuple to share).
- **`is`** is pointer equality (unproxied, as now), which is the language's rule here.
- **The descriptor records the representation** (an option descriptor's flag), so that the runtime's generic paths
  (`is`, identity hash, conversion, proxies, echo, serialization) read such values.
- **Upcasts:** to a single-word supertype (more cases without components, or the component at a supertype) the value
  stays a pointer, the component converted or proxied as its type needs and a constant mapped to the supertype's; to
  any other supertype it is boxed, allocating for the case with the component.
- **Proxies** (c-representation.md §5.8): an option value may be a proxy, its low bit set, and so may a payload, so
  the encoding must still tell a proxied option from a component that is itself a proxy.

## 3. Generic Code

An option over a type parameter keeps the boxed layout, whatever the type argument. A polymorphic call converts a
single-word option to it, boxing the component (a constant needs no box), and converts its result back, reading the
component. Specialization and inlining remove most of these conversions where the type is known; in separate builds,
`maybe`'s own functions are polymorphic calls into another unit, so `maybe.some` still allocates there until
whole-program inlining ([ir.md](ir.md) §8.6) or specialization reaches it.

## 4. Testing

- **The behavior golden** `language/option_identity`, shared by both compilers, already covers the language; it
  gains cases for the nullable layout's conversions if they need them.
- **The self-hosted compiler's IR and SSA goldens** showing the nullable layout and the conversions, and per-pass
  tests of the conversions on SSA written as text ([ssa.md](ssa.md) §6).
- **Every backend's runner mode** (`ssac`, `arm64`, `arm64-program`, `c-whole`, `arm64-whole`), the fixed points, and
  `tools/check --all` (the runtime changes).
- **Measurements** in benchmarks.md, dated: the suite through C and arm64, and the allocation counts of ratio-regions,
  peek, and zebra (`benchmarks/mlton/allocations.py`), before and after.

## 5. Steps

1. **Single-word options as pointers** (§2, §3): layout, represent's plans and conversions, the descriptor flag and
   the runtime's generic paths, both backend paths. *Done when* `maybe.some(:String)` allocates nothing in a
   whole-program build, the suite passes in every mode, and benchmarks.md records the suite's times.
2. **Docs:** c-representation.md's options section and runtime-design.md's identity bullets describe the nullable
   layout, and extensions.md no longer calls the single-word rule provisional.
