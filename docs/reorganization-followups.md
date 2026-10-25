# Reorganization Follow-ups

This plan finishes what the compiler reorganization ([reorganization.md](reorganization.md)) left undone, and fixes
the [tasklist.md](tasklist.md) problems that the reorganization's representation change bears on. The constraints are
the reorganization's: golden output and errors change only where a step says so, every benchmark stays within 10% of
main (`tests/perf/measure.py`, compared by CPU time or interleaved runs on this machine), and a change to the runtime's
headers or to the C that interfaces pin bumps `ABI_VERSION`.

The goal of phases 2 and 3 is the one stated in [reorganization.md](reorganization.md) §1: below lowering, code reads
shapes and what lowering recorded, never types as written; and the C printer only spells the IR in C, deciding
nothing.

**Not in this plan:** unifying types as written with canonical types. B4 showed that type equality cannot become
identity in the type checker ([reorganization.md](reorganization.md) §4), so that would be a change to how types are
represented, not a cleanup.

---

## 1. Phase 1: Bugs and Restrictions

The three steps are independent of one another and of phases 2 and 3.

**1a. Narrow the restrictions on type parameters inside mutable data to bounded ones.** The type checker rejects a
type parameter of an enclosing function inside mutable data (arrays, var components and fields, var and out
parameters) in a type used at run time, and any compound witness mentioning one for an auto type with var components
(`_check_closed_type` in `typechecker/auto_values.py`, [type-system.md](type-system.md) §6.11; the first two
[tasklist.md](tasklist.md) tasks). It does so because converting generic layouts to native ones used to copy. Since
A2, every slot holds one word, so generic and native layouts differ only where generic code holds a value of a
*bounded* type parameter viewed at its bound (`_stored_value_agrees` in `codegen/layout.py`). With the check lifted,
programs that use each rejected form with an unbounded parameter (an array of `A` given to `dynamic.new`, an auto
witness `Tuple var y: A end` updated through inspect, and a compound witness of an auto type with a var component)
give the same results, with updates shared, interpreted, in the IR interpreter, and compiled.

The step limits each check to bounded type parameters, and keeps the run-time check (`quest_layout_conversion_error`)
for those that reach `dynamic.new` as ordinary type arguments. Done when the four error tests named in the tasks
become golden tests (or are replaced by golden tests of the same forms with unbounded parameters), new error tests
show the restriction on bounded ones, §6.11 states the narrower rule, and the two tasks are rewritten to cover only
bounded parameters (phase 4).

**Done:** the type checker tracks the type parameters declared with a bound (`_bounded_type_param_ids`), and both
checks apply only to them. `language/auto_type_parameters_in_mutable_data` uses all three forms with unbounded
parameters (an array in a dynamic value, a var witness component updated through inspect by generic code, and a
compound witness of an auto type with a var component), with updates shared in every backend. The four error tests
are now about bounded parameters (`*_bounded_type_parameter_*`), and the two tasks are one, for phase 4.

**1b. Options whose cases are listed in different orders** (the third [tasklist.md](tasklist.md) task). Option types
are equal regardless of case order, but C lays them out and numbers their tags in the order written, so a variable of
`Option b a end` holding an `Option a b end` fails to compile, and `ordinal` after an upcast to a reordered supertype
differs between the backends.

*Decided:* an ordinal is the case's index in the static type of the argument, the only reading under which equal
types give equal results. Then shapes (`ir/shapes.py`, with canonical forms in
`types/canonical.py`) order an option's cases canonically, so equal option types have one layout, one struct, and one
tag numbering; `ordinal`, the ordinal component of an extraction (`opt!tag`), and construction by ordinal
(`option ordinal(e) of T end`) map indices through the static type (a table per type, made at compile time). Option
struct names and tag numbers change, so `ABI_VERSION` is bumped. Done when both programs in the task compile and
print the same in every backend, golden tests cover them and the extraction and construction cases, and
[type-system.md](type-system.md) §6.6 and §6.8 say which type's declaration order an ordinal counts in.

**Done,** under `ABI_VERSION` 34.

- **Variants too.** Variant types are also compared by case name, and C miscompiled a variant upcast to an equal type
  listing its cases in another order: a `case` on it took the wrong arm, silently (`variant b` of `Variant a: Int b:
  Bool end` viewed as `Variant b: Bool a: Int end` matched `a`). The fix covers both.
- **Shapes and canonical forms order cases by name** (`cases_by_name` in `ir/shapes.py`, and `_canonical_node` in
  `types/canonical.py` for recursive types), so equal types share one shape, struct, descriptor, and tag numbering.
- **Ordinals count in the static type as written.** Lowering records its cases on `ordinal` and on construction by
  ordinal (`cases`, from `option_case_names` in `types/canonical.py`), and an option payload's ordinal on `payload`;
  the C printer maps tags through a constant table where the orders differ, and both interpreters count in the
  recorded order (option values no longer carry an ordinal). The verifier checks the recorded cases.
- **Serialization** lists cases by name in both writers, and the C reader sorts the cases of a type it reads, so
  files listing them in declaration order (all files written before) still read (`stdlib/dynamic_case_order`).
- Tests: `language/option_case_order` (the task's programs, variants, construction, extraction, and a type
  parameter bounded by an option type). IR dumps show the recorded cases, and descriptors their cases by name.

**1c. Check for a proxy once per value.** A read of a tuple component whose type may be proxied checks the tuple for a
proxy each time (`tuple_access` in `ir/slots.py`), about 1.6x in a microbenchmark of such reads (no benchmark is
affected). The slots pass can instead resolve a value that may be a proxy once, where it is bound, into either its
original and an access note `original`, or a known proxy, and read components through that. Done when the
microbenchmark is within 10% of reads of a tuple that cannot be proxied, and the conversion matrix and proxy tests
pass.

**Done (no change needed).** Measured by compiling a program's C as printed and with every proxy check replaced by
a direct read (user CPU, interleaved, `-O2`): reading `t.p.a + t.q.b` from tuples of tuples taken from an array
in a loop costs 1.03 to 1.06 times the direct reads, within the bar. The check is one bit test, the same on every
iteration of a loop. The large ratios come only from loop-invariant reads: with direct reads clang hoists them, or
folds a loop that sums them into a closed form (over 100 times faster here), while the call on the check's proxy
branch keeps it from doing either. Resolving a value once where it is bound cannot avoid a check per read without
duplicating loops (which clang does not do at `-O2`), and declaring the runtime's proxy readers `pure`, which lets
clang treat them as loads, gained nothing measurable (1.06 to 1.04), so neither is done.

---

## 2. Phase 2: Types as Written, Recorded at Lowering

Lowering is the last phase that sees the typed AST, so it records what later passes need from types as written; the
passes below it read those records and shapes. Each step removes one of the remaining readers
([reorganization.md](reorganization.md), "Left undone").

**2a. Component types and quantifiers.** The represent pass finds the types, with their alias names, of the variables
it makes for components (`written_structure`, `array_element`), and the symbols of function types' own type
parameters (`collect_fun_quantifiers`, recorded on thunks as `thunk_symbols`). Lowering records both on the IR
operations that need them: the written component types of aggregate constructions, reads, and stores, and the
quantifier symbols of function types at type applications, adapters, and calls. Done when `ir/represent.py` no longer
imports `normalize_type`, `resolve_type_bound`, or `collect_fun_quantifiers`, and IR dumps are unchanged.

**2b. Echo.** The describe pass turns an echo of a package into an echo of its text from the type as written, and
echo-only descriptors take alias names from types as written (`echo_descriptor_form` and `descriptor_form` in
`codegen/c/types.py`). Lowering records each echo's written form: the text, for a package, and otherwise the written
type tree whose alias names the descriptor shows (a structure of shapes and names, not a `QType`). Done when the
describe pass and `codegen/c/types.py` read no type as written for echo, and echo goldens are unchanged.

**2c. Imported modules' interfaces.** The printer builds the record types of imported modules from their scopes
(`build_record_type_from_scope`), and exported functions' C signatures from the interface's types as written
(`module_function_signature` in `codegen/c/declarations.py`). The unit graph (`modules/graph.py`) makes each unit's
interface record type once, and the IR module records the shapes of its imports' records and its exports'
signatures, which the printer spells. If a signature's C changes (parameter names, for instance), it is an
`ABI_VERSION` bump, since interfaces' headers pin it (`tests/abi`). Done when `codegen/c/` imports nothing from
`quest.modules.elaboration` and neither function reads a scope or a type as written.

---

## 3. Phase 3: The Printer Only Spells the IR

**3a. Payload wrapping as conversions.** The printer wraps and unwraps variant payloads, exception payloads, auto
payloads, and echoed values as QVal words by their representations (`qval_wrap`, `shape_qval_wrap`,
`shape_slot_to_qval` in `codegen/c/printer.py`). The represent and slots passes make these explicit, as `slot_box`
and `slot_unbox` already are for slots, so each payload operand arrives in the representation its operation takes.
Done when the printer calls none of these wrapping functions except to spell a conversion the IR records, the
verifier checks payload representations, and the C is unchanged but for names and separate statements.

**3b. Declarations from the IR.** The printer collects the types whose structs it declares as it prints
(`self.types`). A pass lists the aggregate shapes a unit uses, as `Unit.static_data` lists its static descriptors and
tables, and the printer declares exactly those. The order of declarations in interfaces' headers must stay fixed, or
`ABI_VERSION` is bumped (with 1b's bump if they land together). Done when the printer appends to no list of types,
and the verifier checks that every aggregate shape used is declared.

**3c. Let-bound descriptor operands** ([ir.md](ir.md) §8.4). Descriptor operands are small pure expressions, a
departure from strict ANF. The describe pass binds each instantiated template to a variable, once per function where
its descriptors are in scope, and static descriptors and descriptor parameters stay atoms. This shares
instantiations that are now repeated at each use. Done when the IR is in strict ANF, [ir.md](ir.md) says so, the
verifier checks that descriptor operands are atoms, and the benchmarks are within the bar (expected equal or
faster).

3a and 3b come after 2c, so that imported modules' records are spelled from the IR. 3b comes after 1b, so that
option structs are declared under their canonical names once.

---

## 4. Phase 4: Bounded Type Parameters inside Mutable Data

After 1a, the remaining restriction is a value of a bounded type parameter, held viewed at its bound, inside mutable
data: an `Array(Tuple v: A end)` with `A <: Record age: Int end`, whose elements a `Car` array holds at the `Car`
view. Converting it would copy, losing updates (`tests/errors/run/layout_conversion_mutable_data.quest`).

*Decided:* (B). The alternative was (A):

- **(A) Proxies for arrays and cells.** Extend proxies to arrays and `Var` cells, reading and writing the original's
  elements and converting each between the two views. This reuses the V1 machinery (descriptors, tag maps, caches),
  but adds a proxy check to array reads and writes that may be proxied, on hot paths.
- **(B) Hold bounded type parameters' values at their own view.** Generic code would hold a record of type `A <: P`
  at the view it has, not at `P`'s, and find `P`'s fields through `A`'s descriptor (an offset table from `A` to `P`,
  passed with the type argument), so layouts agree everywhere and nothing converts. This removes conversions at
  polymorphic calls with bounded parameters, but changes field access in generic code and every bounded call
  ([c-representation.md](c-representation.md) §5.1), and needs an `ABI_VERSION` bump.

(B) is a representation change on the scale of A2, so it is prototyped and measured against the bar before it lands.
Done when the error test above becomes a golden test with the same results in every backend, the remaining
restrictions in §6.11 and both tasks in [tasklist.md](tasklist.md) are gone, and the benchmarks are within the bar.

---

## 5. Order

Phase 1's steps can start at once, in parallel with phase 2. Phase 3 follows 2c (and 3b follows 1b). Phase 4 follows
1a. Each step updates the documents it changes
([ir.md](ir.md), [c-representation.md](c-representation.md), [type-system.md](type-system.md),
[tasklist.md](tasklist.md)) and records its outcome here as the reorganization did, with a **Done** note.
