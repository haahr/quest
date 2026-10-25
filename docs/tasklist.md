# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

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
