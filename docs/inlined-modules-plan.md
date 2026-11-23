# Plan: Library Modules Inlined into Their Importers

A plan for the tasklist entry "A few library modules inlined into their importers, as in a whole program"
([tasklist.md](tasklist.md)). It covers how to choose the modules by profiling (§2), how the compiler gives separately
compiled importers their bodies while each module's state stays single (§3), the steps (§4), and a later
command-line option that gives a program's own modules the same treatment, marked in their `.qi` files (§5).
Self-hosted compiler only. The bootstrap is untouched: behavior goldens stay shared, and its output does not change.

## 1. What is measured already

[benchmarks.md](benchmarks.md) §36 built whole programs with `util/maybe`, `util/iter`, and `collections/vector` kept
apart (an experimental `--apart` flag, since reverted). The flag made `whole.mergeImports` treat each named module as
precompiled, keep one import per kept module, and rewrite merged code's references to it to that import. In
`benchmarks/iter/` they account for all of the whole-program gain (`filter`: 153 instructions per element separately, 45
whole, 153 with the three apart). In the compiler they account for 56% of it: 2.5% of the separate build's instructions
retired, against 4.5% for a whole program. That measures the three inlined into a whole program. Inlined only into
separately compiled units, with everything else still apart, they may gain less, so step 6 measures again.

## 2. Choosing the modules by profiling

The fixed list should be decided by measurement, not by guessing from module sizes. Three tools, from cheap to
decisive. The first two are screens, and the third makes the decision.

### 2.1. Static screen: cross-module calls to small members

A report flag, `--report-cross-module-calls` (named like `--report-inferable`), printed after the simplifier for each
separately compiled unit of a build. For each call it gives:

- the callee's module and member;
- the callee's Core IR size, against the inliner's bounds ([inlining.md](inlining.md) §1);
- whether the callee is polymorphic at a type its caller has closed, which means a conversion between generic and
  native layouts and no specialization.

Summed over a corpus, per callee module, this gives the call sites the list could remove. The corpus is:

- the compiler's driver build;
- `benchmarks/mlton` built separately;
- `benchmarks/iter`;
- the behavior tests' programs.

The report counts call sites, not calls, so it only says which modules to look at. Modules with no small or
polymorphic members called from outside drop out here.

### 2.2. Dynamic screen: where the time goes across the boundary

Two ways to weigh the call sites from §2.1 by how often they run. The second is the one to build if the first leaves
the ranking unclear.

- **Samples by module.** `tools/perf/profile.py` gains `--by-module`. It needs two attributions:
  - an exported function's samples go to the module its symbol names (`qv_collections__vector_get`);
  - a static function's samples go to the object file it came from, from a link map (`-Wl,-map`) that
    `variants.py --separate` writes.

  Samples in a small callee measure its call overhead, more or less. They miss the caller's side: boxing at a
  generic layout, and loops that are not specialized. So samples rank the candidates but do not measure the gain.
- **Exact call counts.** An arm64-only development option, `--count-cross-module-calls`. It gives each call site to
  another module's member a counter, kept per pair of caller unit and callee member, and dumps the counters at exit.
  The counts are deterministic, so they need no quiet machine. They answer "how many calls would the list remove",
  which samples cannot.

### 2.3. Decision: leave-one-out instruction counts

Bring back §36's `--apart` as a development option, which keeps the named modules apart in a whole program. Also
apply the fix the experiment needed: an import made through an alias, like vector's `iterLib`, gets its record type
from the interface's scope. Then, for each candidate M that survived the screens:

- build the corpus whole with every candidate apart except M;
- build it with all of them apart;
- the difference in instructions retired is what M alone gains.

Keep each `/usr/bin/time -l` count, at `-j 1` for the compiler. The counts are deterministic, so the per-module numbers
add up, apart from interactions between modules. Interactions are why §36 measured the three together: vector's
`iter` returns an `iter.T`, so vector's gain partly depends on iter being inlined too.

The candidates beyond the three are the library modules that the compiler or the benchmarks call most across module
boundaries. The screens will name them; `collections/hashMap`, `util/hash`, `util/stringBuilder`, `util/lazy`, and
`util/sort` are likely. The prelinked modules (`string`, `int`, `conv`, ...) are out of scope: they have no source an
importer could inline.

### 2.4. The rule to join the list

Record this rule where the list is defined (§3.1). A module joins when all of these hold:

- **Gain.** Its leave-one-out gain is at least 0.2% of the compiler's instructions retired, or at least 10% on some
  benchmark program.
- **Cost.** Its cost (§2.5) is below its gain.
- **Stable.** Every change to its source rebuilds every importer.
- **Not huge.** The importers elaborate its source (§3.4). `util/iter` at 491 lines is about the limit.

State in a module's members is no reason to leave it out, since state stays single (§3.2).

### 2.5. The costs to measure with each candidate

- **Compile time.** Each importer typechecks and lowers the module's source. Measure the driver build's
  instructions retired at `-j 1`, and its wall time at `-j 8` on a quiet machine.
- **Code size.** Copies of members are made in every importer. Measure with `tools/perf/asmstats.py` and the size of
  the driver binary.
- **Rebuild fan-out.** Count the units a touch of the module rebuilds. It matters for in-tree library work, not
  for a release.

## 3. Design

### 3.1. The list

`questlang/modules/inlined` holds the canonical names of the library's inlined modules, with the rule of §2.4 in its
comment. The list starts as `util/maybe`, `util/iter`, and `collections/vector`, and changes as §2 decides. It is
data for the mark in §3.5, so the later user option (§5) only adds names to the same set.

### 3.2. An opened module: copied code, single state

A separately compiled unit U that imports a listed module M does not merge M. Merging is what `driver/whole` does,
and it would give U its own copy of M's state and its own initializer. Instead, U's Core IR gets an **opened
module**: a `nodes.Module` for M, marked as opened. It holds copies of the members U can reach from its references,
transitively, and every other reference still goes through the import of M's compiled object:

- **Copied:** M's functions, private ones too, and members bound to pure, identity-free values: an `Int`, `Real`,
  `Bool`, or `Char` constant, such as vector's `floorSize`. These are what the inliner, the specializer, and constant
  folding need.
- **Read from M's object:** members with identity or effects. These are:
  - exceptions (`maybe.error`, `vector.error`, `iter.exhausted`, `iter.error`), matched by identity;
  - `String` constants, which `is` compares;
  - `var` members;
  - anything allocated or computed by a call.

  The copies' references to these become reads through the import, so a raise of `vector.error` in U's inlined code
  is caught by a handler in vector's own code, and the reverse.
- **Not run in U:** M's initializer. M is initialized as any import is, before U's body (c-representation.md §5.6).
- **A member used as a value**, rather than called, is M's closure from M's record, the same value however it is
  reached.

This avoids the experiment's closed-set problem (benchmarks.md §36). Nothing is linked twice: M is compiled and
linked once, and the copies in U are static.

**Exports for openers.** A private identity member has no symbol today. When M is compiled and is on the list, its
object exports every identity member under a symbol of its own: a rule that name-mangling.md gains,
`qv_<module>__open_<member>` for example. This changes the objects, so it is an ABI bump.

**Imports gained.** A copy can refer to a module U does not import: vector's `iter` refers to `util/iter`. U then
imports it, to initialize and link it, and records it in its `.qm` as an import made by an opened module (§3.4). If
that module is listed too, it is opened as well.

**After the simplifier**, an unspecialized copy that nothing inlined is dropped. The calls left to it go to M's
exported function, so each importer does not carry a full copy of M. A private helper left called keeps its static
copy, unless measurement shows that exporting helpers is smaller.

### 3.3. Layouts across the boundary

U is not a whole program, so the global switch `shapes.transparentAbstractTypes()` stays off. Six sites read it:

- represent;
- simplify, twice;
- the module compiler;
- staticdata;
- `genericLayout.abstractInstance`.

The switch becomes a predicate on each abstract type's instance. An opened module's unbounded abstract type is
transparent in U at exactly the instances whose native layout agrees with its generic one, where
`genericLayout.genericLayoutAgrees(generic subst)` holds:

- **Transparent:** `vector.T(Int)` and `maybe.T(String)`. Every slot holds a value's `QVal` form, so they agree.
  Through the inlined code, their values are the same bits as M's own code sees.
- **Opaque:** `iter.T(Real)`, whose closures' C signatures change with `Real`. Such an instance stays opaque in U at
  the generic layout, as it is today outside M. Inlined code converts at the boundary with the plans that already
  convert between a module's code at concrete arguments and code outside it (`_abstract_plan`, c-representation.md
  §5.1).

The specializer's rule for calls from outside a module (ir.md §8.1) applies unchanged to calls left to M's
entries. Opaque shapes (`shapes.opaqueShape`) stay opaque, so descriptors, echo, dynamic values, and the names of
records do not change, as in a whole program.

The risk is that the gain for iterators over `Real`, records, or variants is small. Step 6 measures it. If it
matters, the next step is to make the conversion a view, not a copy, rather than to make the instance
transparent.

### 3.4. Where the bodies come from, and staleness

The importer elaborates M's source, `lib/collections/vector.mod.quest`, through the unit graph, as a whole program
does (`graph.typedModule`). The `.qi` stays interface-only. If compile time (§2.5) shows that re-elaborating costs
too much, a later step can have M's compile write its lowered Core IR beside its object. That is still not in the
`.qi`.

U's object now depends on M's body, not only on its interface. U's `.qm` therefore gains `opened_modules`:

- each opened module, with the source it was read from and its mtime;
- transitively, the modules the copies opened in turn;
- the imports those copies added (§3.2).

The build engine treats U as stale when any of those sources is newer than U's `.qm` (build-process.md §7.1, a new
rule beside rule 4). It adds the gained imports to the link closure. A release's library sources ship in
`QUEST_HOME/lib`, so the same rule holds there. Its objects change only with the release.

### 3.5. The mark in the `.qi`

Being inlined is a property of M that every unit must agree on: M's compile has to export its identity members,
and every importer has to open M. One flag, read by both and kept with the artifacts, is the way to get that
agreement. So the interface compiler, compiling M's interface when M is on the list, writes into the `.qi`:

- `inlined_module`: M's canonical name;
- `inlined_source`: the path of M's source.

An importer opens M if and only if M's `.qi` has the mark. This is the same mechanism the later user option (§5)
needs, so the fixed list costs nothing extra there. A `.qi` without the mark means what it means today.

### 3.6. What else follows whole programs

- **Raise sites** in copies name M's file. U's unit numbers M's file offsets apart (`nodes.fileOffset`), as a whole
  program does.
- **Tracebacks** lose inlined frames ([exceptions.md](exceptions.md) §2.4).
- **Every backend** takes the opened module's copies: C, ssac, arm64, and WASM, with WASM in the same step as the
  others.
- **The JIT** compiles inputs that import a listed module the same way. The driver's own objects of the listed
  modules then have to export the identity members (jit.md §3). Module rollback never rolls back a library module,
  but an input's opened copies are the input's own, and roll back with it.
- **Determinism:** copies are made in source order, so the self-hosting fixed point holds.

## 4. Steps

Each step ends with tools/check passing, except where it says otherwise. Each step's measurement goes into
benchmarks.md.

1. **Measurement tools (§2).** Restore `--apart` as a development option, with the alias fix (§2.3). Add
   `--report-cross-module-calls`, and `profile.py --by-module` with the link map. Run the screens and the leave-one-out
   counts, and write the list into benchmarks.md with each module's gain and costs.

   Self-contained tooling with unit tests; the compiler flags need the driver's tests only. Done when the list is
   decided and recorded.
2. **Exports for openers.** The list module (§3.1), the `.qi` mark (§3.5), and the export of identity members by a
   listed module's object (§3.2), with the ABI bump. Nothing opens yet, so behavior and code are unchanged except
   for the new symbols. Done when tools/check passes and the marks appear in the build directory's `.qi` files.
3. **Opened modules, opaque.** Importers open marked modules (§3.2), with every abstract type still opaque in U.
   Inlined bodies meet U's values through the existing abstract-to-representation coercions, which are copies
   wherever the layouts agree (ir.md §8.6, projections through "a module's abstract type for its manifest one").
   This alone may get most of maybe's and vector's gain.

   Add `opened_modules` and its staleness rule (§3.4), and the imports gained. Tests:
   - exception identity both ways: a raise in vector's code caught by inlined code, and a raise in inlined code
     caught by vector's code;
   - a `var` member read and written through both;
   - a build-engine test where touching `vector.mod.quest` rebuilds an importer;
   - an `ir_simplified` golden of a separately compiled unit, with `maybe.isSome` inlined.

   The behavior goldens must not change. Measure.
4. **Transparency where layouts agree (§3.3).** The six uses of `transparentAbstractTypes()` become the per-instance
   predicate. Test `iter.T(Real)` across the boundary, both ways, and an echo or descriptor of an opened module's
   abstract type, to show the opaque shapes are unchanged. Measure.
5. **Every backend and the JIT.** C, ssac, and WASM goldens. The JIT's tests, including an input that imports
   vector, a redefinition, and a rollback. Run the C fixed point with the bootstrap's stage 1, then cut a release
   (the library objects' exports change), and run `--seed` bootstrap.
6. **Measure and use.** Measure the driver build's instructions retired and `benchmarks/iter`, against §36's
   whole-program numbers. Let util/iter's own slots give way to `util/maybe` where the measurement says it no longer
   costs (iter.md rule 5, which then says so). Write the result into benchmarks.md and retire this plan into its
   docs:
   - ir.md §8.6: "Across modules only in whole programs" gains the exception;
   - build-process.md: opened modules and the new staleness rule;
   - modules.md §9: the `.qi` mark.

   Or, if steps 3 and 4 gain much less than §36, stop after measuring, and record why.

## 5. Later: a program's own modules

Once the list works, a command-line option can give a program's own modules the same treatment:

- **The option.** `--inline-module PATH`, repeatable. PATH is a module path as an import writes it, resolved as the
  program's imports are. It is accepted wherever a build compiles interfaces: a program build, and `-c` of an
  interface.
- **It sets the mark.** The option adds PATH's canonical name to the set of §3.1. So the interface compiler writes
  the mark (§3.5) into that module's `.qi`, M's compile exports its identity members, and importers open it, all
  through the same mechanism as the library's list.
- **The `.qi` keeps the decision.** A unit compiled later on its own, with `-c` and without the option, reads the
  mark from the `.qi` and opens M, so the decision cannot differ between units.
- **Staleness.** Whether a module is marked is part of its `.qi`'s key. A build that adds or drops the option for M
  finds M's `.qi` stale, rewrites it, and the transitive interface rule (build-process.md §7.2) rebuilds M and every
  importer. Dropping the option has to be a cascade, not silently ignored. Otherwise M's importers would keep
  copies against an M whose object no longer exports the identity members they read.
- **Restrictions,** each an error naming the module:
  - a module with variants (build-process.md §6.4), which one importer could not choose among;
  - a module whose source the importer cannot find from the mark's recorded path;
  - a prelinked or precompiled module, which has no source.

  Hybrid Quest/C modules are fine: their externals are called directly.
- **Not a pragma.** The option is not written in the module's source. A module does not decide how its importers are
  compiled; the build does. If programs want the setting persistent, a build-directory configuration file can carry
  it later.

The `.qi` file still carries no bodies, so the model stays "an importer depends on interfaces" for every unmarked
module. A marked module's importers depend on its source too, and the mark says so, so a build can tell from the
artifacts alone which objects a source change makes stale.
