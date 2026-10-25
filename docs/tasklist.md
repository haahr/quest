# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Bounded type parameters inside mutable data in types used at run time

**Problem.** Generic code holds a value of a bounded type parameter (`A <: T`) viewed at its bound, so a value
mentioning one is converted when used at a particular type argument (`quest_convert`, `docs/c-representation.md`
§6.4.5), and a conversion of mutable data would be a copy that does not share updates. The type checker rejects a
bounded type parameter inside mutable data (arrays, var components and fields, var and out parameters) in an auto
value's witness, in the types of inspect's when clauses, and in the type arguments of `dynamic.new` and
`dynamic.be`, and a larger type mentioning one as the witness or when type of an auto type with var components
(`docs/type-system.md` §6.11). Where it cannot see the type, as when one reaches `dynamic.new` as an ordinary type
argument, compiled code stops with a run-time error. The interpreter has no layouts and runs such programs.
Unbounded type parameters are not restricted: generic and native layouts agree for them.

**Reproduce.** `tests/errors/typecheck/auto/*_bounded_type_parameter_*.quest` are rejected, and
`tests/errors/run/layout_conversion_mutable_data.quest` runs interpreted but fails compiled with `a value used at type
Array(Tuple v: Record age: Int fuel: String end end) was laid out by generic code, and converting it would copy
mutable data`.

**Where to start.** Phase 4 of [reorganization-followups.md](reorganization-followups.md), decided as (B): generic
code holds bounded type parameters' values at their own view, so layouts agree and nothing converts.

**Done when.** The five tests above run (the error tests becoming golden tests) with the same results interpreted
and compiled.

---

## Specialization's tuple trigger depends on how a tuple type is written

**Problem.** A polymorphic function is specialized when a parameter or its result is a tuple type over its type
parameters (`should_specialize` in `bootstrap/python/quest/ir/specialize.py`, docs/c-representation.md §6.4.3), but
the test is on the type as written (`isinstance(t, QTupleType)`), so the same tuple type reached through an alias or a
type operator's application (`Box(A)` for `Let Box = Fun(A::TYPE) Tuple x: A end`) does not trigger it. Since every
slot holds one word (A2 of docs/reorganization.md), a tuple's generic layout agrees with the native one up to casts,
so the trigger may no longer be needed at all.

**Reproduce.** With the test changed to the shape's kind (`shape(t).kind == "tuple"`), `mkBox` and `getBox` of
`tests/python/test_generic_layouts.py` (`TestPolymorphicCallsInC`) are specialized at `Bool`, and
`language/type_parameters_in_aggregates` specializes differently.

**Where to start.** Measure the benchmarks with the tuple trigger removed, and with it made shape-based; keep
whichever is within the bar and simpler, and update §6.4.3.

**Done when.** The trigger does not depend on aliases or type applications (or is gone), §6.4.3 says why, and the
benchmarks are within the bar.
