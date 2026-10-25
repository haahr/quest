# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Values of type parameters bounded by option or tuple types can be used only through upcasts

**Problem.** The type checker accepts `case`, `?`, and `!` on a value of a type parameter bounded by a variant type,
and field selection on one bounded by a record type, but rejects `case`, `?`, and `!` on one bounded by an option type
(only `ordinal` is accepted), and selection on one bounded by a tuple type. The backends read such values through the
bound already (a view map for options, `docs/c-representation.md` §5.1; tuples' components would be read as through a
proxy).

**Reproduce.** `let get(A <: Option none some with x: Int end end o: A): Int = case o when some with p then p.x
when none then 0 end;` reports `Case target must have Option or Variant type, got 'A'`; `o!some` reports `Variant
assertion '!' requires Variant or Option target`; and `let f(A <: Tuple x: Int end t: A): Int = t.x;` reports `Cannot
select field 'x' from non-record/tuple type 'A'`.

**Where to start.** The case, query, and extraction elaboration in `bootstrap/python/quest/typechecker/control.py` and
`aggregates.py`, which resolve a variant bound (`resolve_option_bound` exists, and `ordinal` uses it) but not an
option's, and `_synth_select_expr` in `typechecker/aggregates.py` for tuples. The C printer reads an option through a
view map already (`view_payload` in `codegen/c/printer.py`); a tuple bound needs the same (or the value upcast to
its bound, through a proxy).

**Done when.** The programs above type-check and run with the same results in every backend, and
`language/bounded_parameters_own_view` covers them.

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
