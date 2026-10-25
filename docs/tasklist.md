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
