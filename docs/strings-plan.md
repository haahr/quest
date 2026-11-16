# Strings: `stringBuilder` as Functions, Static Literals, and Cheaper `<>`

Six changes to how Quest builds strings, in the order of §9: `util/stringBuilder` becomes functions over a native
type (§1–3), `QString` loses its unused `capacity` (§4), string literals become static, read-only strings (§5), a
chain of `<>` allocates once (§6), and the compiler's code then uses `<>` for a string that is one expression and the
builder only for accumulation (§7), after which the builder's untuned constants and policies are tuned by timing the
compiler (§8). Decisions recorded 2026-11-15: separate builder calls with an `sb` alias, appends return `Ok`,
`toString` empties the builder, `strShared` appends without a copy, the builder switch in one commit; literals static,
marked read-only by a header bit.

## The builder today

`util/stringBuilder` builds strings through an object: `stringBuilder.new()` returns a recursive tuple of eleven
closures (`str`, `char`, `int`, …), each of which appends to a native buffer (`quest_sb_*` in the runtime) and returns
the tuple, so calls chain (`b.str("x = ").int(x).char('\n')`). Every builder therefore costs a tuple and eleven
closures before it holds a character, and every append is an unknown call through a closure into a Quest wrapper that
then calls the runtime. Most of our builders are small and short-lived (quoting one string, formatting one line),
where that overhead dominates.

The module is used heavily (about 350 calls in 38 files), so this plan keeps it and its native buffer, and changes
only its shape: the builder becomes an abstract native type, as `writer.T` is, and each method becomes a function of
the module that is the runtime function itself (an external), so an append is one known call and a new builder is
one allocation. The closure-per-method object moves to a test, wrapped around the new module, since that
style should keep working and is a demanding test of the compiler (a recursive tuple type, a `let rec` tuple whose
components close over it, chained calls through components).

## 1. The new interface

```
interface StringBuilder
    import wordLib = word: Word
export
    (* A string accumulated in a native buffer ... (the current header comment,
     * with the example rewritten) *)
    T::TYPE

    new(): T
    str(b: T s: String): Ok
    strShared(b: T s: String): Ok
    char(b: T c: Char): Ok
    int(b: T n: Int): Ok
    real(b: T r: Real): Ok
    bool(b: T v: Bool): Ok
    word(b: T w: wordLib.T): Ok
    sub(b: T s: String start: Int size: Int): Ok
    repeat(b: T c: Char n: Int): Ok
    clear(b: T): Ok
    length(b: T): Int
    toString(b: T): String
end
```

The module stays `unsound`, now with `Let T = external "QStringBuilder *"` and every function `= external
"quest_sb_…"`, the way `lib/writer.mod.quest` is written. The names and semantics are the methods' (copying appends,
`sub` and `repeat` raising `string.error`), but for `toString`, below; the receiver moves into the argument list and the
appends return `Ok`. The externals table entry renames the type from `stringBuilder.Buffer` to `stringBuilder.T`,
which `tools/externals` regenerates, with an `ABI_VERSION` bump.

**`toString` empties the builder** (decided 2026-11-15). It returns the contents and leaves the builder as `clear`
does: empty, and still usable. Today it leaves the contents in place. Reading every caller on d3b7502b found none that
uses a builder after its `toString` except to `clear` it at once (`mangleSymbolicIdent` in `repr/symbols.mod.quest` and
`quest_readline_read_history` in `runtime/quest_readline.c`, whose `clear` calls become redundant and go); the one
builder kept in a record (`types/dump`'s `name.b`) reads `length` only before. Unlike the rest of this step, the
compiler cannot find a caller that depends on the old behavior, which is why the callers were read, and why the
interface comment states the rule. It lets §8 hand the buffer over instead of copying. What changes:
`quest_sb_to_string` (no longer `const`) resets the builder after copying out, with the comment in `quest_runtime.h`;
the bootstrap's `_sb_to_string` in `bootstrap/python/quest/interpreter/builtins.py` does the same; the self-hosted
interpreter calls the host builder's `toString`, so it follows.

**`strShared` appends without a copy** (decided 2026-11-15). `str` copies its argument, so that changing the string
afterward cannot change the result. `strShared(b s)` instead may keep `s` itself until the builder's next `toString`
or `clear`, and its caller promises not to change `s` until then. In the runtime (`quest_sb_append_string_shared`), a
short string is copied into the working buffer as `str` does, since that is cheaper than recording a reference; a
string longer than `QUEST_SB_LONG_APPEND` flushes the buffer and becomes a chunk itself, since a chunk is already a
`QString *`, saving the copy's allocation, header, and `memcpy`. The bytes are still copied once, by `toString`. A
caller that breaks the promise gets the changed text or the old one, unspecified which (the interpreters may copy), and
never a memory error, since `setChar` and `setSub` cannot change a string's length. The self-hosted interpreter's
table maps it to the host's `strShared`, and the bootstrap's to the same function as `str` (its strings hold a Python
`str`, so its appends are snapshots anyway). The name says what the caller grants, and `sb.strShared(b x)` is short
enough with the alias.

**Not direct calls yet** (found 2026-11-15, building step 1). An importer calls a library module's external function
as the C function itself only when no parameter or result is held as a `QVal` (c-representation.md §6.2), and it
holds every library external type but `reader.T` and `writer.T`, which the compiler has built in, as an abstract
`QVal`: `os/process`'s `process.T` already had this. So `sb.str(b s)` is a call of the module's wrapper,
`qv_util__stringbuilder_str`, which calls `quest_sb_append_string`: a known call in place of a closure's, but not the
runtime's function itself. `tools/externals` also leaves out `new`, which has no parameters, and `word`, whose
`wordLib.T` is not a simple type. Making importers see a library external type as its C type, as the compiler's
table already records (`questlang/repr/externals`' types), would make these calls direct for every such module; it is
a change to the self-hosted compiler alone, proposed as a step of its own rather than folded into this one.

Call sites read `sb.str(b "x = ")`, then `sb.int(b x)`, then `sb.char(b '\n')`, as separate statements, with the
module imported under the short alias `sb` (`sb = util/stringBuilder : util/StringBuilder`, as the tokenizer already
renames its import) wherever a module appends more than a few times. A chain is not folded into one `str` of a `<>`
expression, which would allocate the intermediate strings. (Decided 2026-11-15: separate calls with the alias;
appends return `Ok`, so each function can be the runtime's.)

## 2. What changes at the call sites

Counted on 20d7316a: about 346 method calls in 38 files, 57 lines of them chained. The users:

- **`lib/`** (shared by both compilers): `util/strutil`, `io/display`, `os/path`, `util/path`, `util/argparse`.
- **`questlang/`**, 31 modules: `codegen/{c/ssac,c/headers,arm64/asm,machine}`, `ssa/{printer,parser}`,
  `syntax/{astprint,tokenizer}`, `typechecker/typedastprint`, `types/dump`,
  `common/{json,pyrepr,diagnostics,files,sha256}`, `repr/{symbols,syntax,digests,genericlayout,staticdata}`,
  `modules/paths`, `driver/{main,kernel,binaryerrors}`, `jit/{session,debugobject}`, `interpreter/builtins`,
  `values/{model,dynamicjson}`.
- **Tests and benchmarks:** `tests/source/stdlib/stringbuilder_operations.quest`,
  `tests/source/questlang/syntax_parser_engine.quest`, `tests/perf/questlang_tokenizer.quest`, the Quest source in
  `tests/self-hosted/fingerprints.py`, `benchmarks/mlton/support/reals.mod.quest`.

The rewrite is mechanical: `b.m(args)` becomes `stringBuilder.m(b args)`, a chain becomes a sequence, and a builder
passed to a helper is passed as before (its type is still `stringBuilder.T`). Helpers that return the builder to
continue a chain (`astprint.pad`, `quoted`, `simpleField`, `simpleItem`, `render`, `renderNode`) return `Ok` instead.
`pad` in `typedastprint` and `types/dump`, which build a throwaway builder for spaces, become `stringOp.new(n ' ')`.

Once `T` is abstract, every missed site is a type error (`T` has no components), so the compiler finds them all.

**`str` or `strShared`.** In `lib/` and `questlang/`, the only code that changes a string is `lib/util/strutil` and
`lib/util/bignum`, each filling a string it has just made before returning it (found on d3b7502b); the compiler never
changes a string once made. So in `questlang/` every append of a string-valued argument can be `strShared`, and is,
where the string may be long (a call's result, such as `formatFunction(…)` in `ssa/printer`, a joined list, a file's
text); a literal or a short piece stays `str`, where the two behave alike. In `lib/`, which serves programs that may
change their strings, `strShared` is used only where the argument is the caller's own fresh string. Unlike the type
errors, this choice is not checked, so the rule is written in the interface comment and each use is one the reader
can see is safe from the line itself.

## 3. The test that keeps the chained style

`tests/source/modules/chainbuilder.{int,mod}.quest` holds today's interface (the recursive tuple `T` and `new()`), and
its module builds each object over a `util/stringBuilder.T`, every method a closure that calls the matching function
and returns the object. It is an ordinary module, not `unsound`, and needs nothing from the interpreters.

`tests/source/stdlib/stringbuilder_operations.quest` keeps its cases, rewritten for the function interface, and
`tests/source/modules/chainbuilder_operations.quest` is today's test with its import changed and the same new case
(below) added. Their run
outputs must be byte-for-byte the same as each other, under both compilers, the interpreter, and every backend, and
the same as what `tests/golden/run/stdlib/stringbuilder_operations.out` holds today except for the three lines that
read `length` after `toString` (in cases 1, 2 and 4), which now print 0. Case 2's comment ("toString returns a copy
…") is rewritten to say that `toString` empties the builder and that it can be reused after it, and a case is added
for a second `toString` in a row returning the empty string. Both tests also get a `strShared` case: short and long
strings (either side of `QUEST_SB_LONG_APPEND`), mixed with `str`, in order, and a builder reused after `toString`
whose earlier shared string is no longer in it. The chained wrapper gains a `strShared` method for it. No test changes
a string after sharing it, since the result of that is unspecified.

## 4. Dropping `QString.capacity`

Strings never change length, so `capacity` is always equal to `length` and nothing reads it (the comment on `QString`
in `runtime/quest_runtime.h` says so). Removing it makes a string's header 16 bytes rather than 24 (24 rather than 32
with the collector's header word), for every string a program makes. It touches:

- the struct, its `static_assert`, and the layout `Q_FIXED(quest_layout_string, "QString", 24, S, S, P)` in
  `runtime/quest_gc.c`;
- the six stores of `capacity` (`quest_runtime.c`, `quest_stdlib.c`);
- the self-hosted compiler's table (`questlang/repr/runtimelayout`: `data` moves from offset 16 to 8), which the SSA
  builder's inlined `length`, `getChar`, and `setChar` read;
- `questlang/jit/session.bytesOf`, which hard-codes the data's offset as 16 rather than asking the table (change it to
  ask);
- `c-representation.md` §3.2 and §5.5, and the `QString` comment.

The bootstrap's C refers to the fields by name and needs nothing.

## 5. Static, read-only literals

**Today.** A literal is `quest_string_new(literal, length)` at each evaluation (`ssa/build/values`, the C printer
`codegen/c/printer`, and the bootstrap's `codegen/c/printer.py`), an allocation and a copy every time. That was our
compilers' choice, not the language's: Cardelli's `StringOp` makes strings mutable (`setChar`, `setSub`), but neither
the paper nor our docs say what a literal denotes when it is mutated. The implementations also disagree (checked
2026-11-15, `let f(): String = "ab"`): compiled code and both of the bootstrap's paths give each evaluation a fresh
string, so `f() is f()` is false and `setChar(f() 0 'X')` leaves the next `f()` as `"ab"`; the self-hosted
interpreter (`irinterp`, which returns the IR constant's own string) shares one string per literal, so `f() is f()` is
true and the next `f()` is `"Xb"`.

**The rule (decided).** A string literal denotes one static string, the same object at every evaluation, which is
read-only: `setChar` or `setSub` on it raises `string.error`. Every other string is mutable as before. This is an
extension of Cardelli's semantics and is recorded in `extensions.md`.

**The read-only mark.** A bit in the object's header word, not in the string: the mutator's byte (bits 48 to 55,
`runtime/quest_gc.h`) uses one bit of eight (`Q_HEADER_LOGGED`), so `Q_HEADER_READONLY` takes another. `setChar`
(inlined by the SSA builder: on arm64 a load and a `tbnz` beside its existing checks) and `quest_string_set_char` and
`quest_string_set_sub` in the runtime raise `string.error` when it is set. Nothing that reads a string changes. A bit
stolen from `length` would instead cost every reader a mask, and a reader that missed it would pass the unsigned
bounds check (`idx < length`) for any index. `quest_string_freeze(s)` sets the bit on a heap string, for the
self-hosted interpreter.

**Moved to bit 63** (found 2026-11-16, building step 4). Step 3 put the bit at 49, in the mutator's byte. A static
literal's header is then `quest_layout_string`'s address plus 2^49, a relocated pointer with an addend, and arm64
Darwin's chained fixups (the linker's default) keep only a pointer's low 36 bits and its top byte: the addend was
dropped without a warning, so every static literal was writable and a `setChar` on one wrote into `__TEXT` and died
of SIGBUS. Bit 63, the top of the collector's byte, survives the fixups. It breaks collector.md §3.2's rule that each
byte has one writer, since the mutator sets it, but it is set once, before the string is shared, and never cleared,
and the collector's writes (or-ing in `old`, the whole word at birth) keep it. The other way would be linking every
program with `-Wl,-no_fixup_chains`, which keeps full addends, but a link without it would silently lose the check.
Raised with the owner as a decision to confirm. `quest_string_freeze` writes only when the bit is not set yet, so
the mutator writes the collector's byte once per string and never a static literal's read-only header, and the
runtime header asserts that the bit is in the top byte.

**The WASM backend** (on `main` since this plan was written) does not follow the rule yet: its strings are WASM-GC
byte arrays with no header, so its literals stay fresh and writable, and its `quest_string_freeze`, which the
interpreters compiled to WASM call, does nothing (recorded in `extensions.md`).

**Emitting them.** Each distinct literal in a unit becomes static data: a header word (the address of
`quest_layout_string`, with the read-only bit), the `QString` (length and a pointer to its bytes), and the bytes,
NUL-terminated; a use is the object's address (`opSymbol`), not a call. Static closures today have no header word, so
the collector already ignores static objects by address; what must be checked is everything else that reads a
header (`quest_layout_of` has 14 callers: identity hashing, printing, `dynamic`, serialization) and that each works
on a static string. The bytes can live in read-only data; the header and `QString` hold a relocated pointer, so they
go where the unit's other relocated constants do.

**Where it changes.** The self-hosted SSA builder (so `ssac`, arm64, and the JIT), the self-hosted C printer, the
self-hosted interpreter (which freezes each constant's string once), the bootstrap's C printer (a `static` C object
with its header), and the bootstrap's interpreter (a read-only flag on its `QString`). All of them change together,
since the shared goldens include the new behavior.

**What follows from it.** `f() is f()` is true for a literal; code that used a literal as a scratch buffer now raises,
which the suites will find. A `case` whose arms each give a string literal (`when primAdd then "+" ...`) becomes
a table (decided 2026-11-15): each arm's value is now a static string's address (`opSymbol`), which
`ssa/passes/tables` (`ssa.md` §4.1) already accepts, so the switch becomes one load from a table of pointers with no
change to the pass. No interning or string comparison is involved, since the `case` is on an option's tag.

## 6. Concatenation chains

`x <> y <> z` is two calls of `quest_string_concat`, each allocating a result (a header and its bytes) and copying both
operands, so a chain of n parts makes n − 1 strings, of which n − 2 are garbage, and copies its early parts up to
n − 1 times. Gathering the parts and allocating once makes it one string, each byte copied once.

**Where.** The IR is in A-normal form, so a chain arrives as `let t1 = prim <>(x, y)` then `let t2 = prim <>(t1, z)`.
A rewrite in `ir/simplify` (or a small pass beside it) turns a concatenation whose operand is a variable bound by
another concatenation and used only there into one operation over all the atoms, in order: a new IR operation
`concat(a1, ..., an)` (n ≥ 2; the binary `prim <>` becomes its two-atom case). Doing it in the IR serves every
consumer: the SSA builder (so `ssac` and arm64), the C printer, and the IR interpreter, which concatenates the atoms
with `stringOp.conc`. Adjacent literal atoms fold into one literal.

**Runtime.** `quest_string_concat_n(int64_t n, const QString *const *parts)`, the parts in a stack slot the SSA
builder fills (the slot machinery already passes memory to the runtime), with one allocation of the total length.
With static literals (§5), every part, literal or not, is a `QString *`, so no separate form for literal bytes is
needed. The existing `quest_string_conc` takes a heap `QArray`, which would cost an allocation of its own.

**Scope.** Self-hosted compiler only, as other optimizations have been (two-compilers policy): the bootstrap keeps its
pairwise `<>`, and behavior is identical, since the result is a fresh string either way. It does not help
`s := s <> piece` in a loop, which is quadratic in any form and is what `stringBuilder` is for.

## 7. Choosing between `<>` and the builder

Once a chain allocates once (§6), a builder used in straight-line code costs more than the chain it could be: the
builder and its buffer, any regrowth, and a copy in `toString`, against one allocation and one copy. And `<>` in a
loop stays quadratic. So the rule for our code becomes: a string that can be written as one `<>` expression within one
function is written that way; a string accumulated across loop iterations, or by helpers that take the builder, uses
the builder (decided 2026-11-15).

**To `<>`.** A run of `sb.str(b …)` calls ending in `sb.toString(b)`, including ones guarded by an `if` statement,
which becomes an operand `if c then x else "" end` in the chain (as `ssa/printer`'s `formatFunction` already does
within one call). Conditionals are no obstacle; only control flow that is not an expression is.

**Staying a builder.** Loops; a builder passed to helpers that append to it (`syntax/astprint`, `types/dump`,
`values/model`, `common/json`, `ssac`, and the others whose functions take a `stringBuilder.T`), since fusion stops
at a call and helpers returning strings would allocate one per call; and a long formatting function where one chain
would read worse than separate calls, judged case by case.

**To the builder.** `s := s <> piece` in a loop, which is quadratic in any form: in `ssa/printer`, `paramsText`'s
`text`, `instText`'s `lhs`, and `termText`'s `termSwitch` arm, and their like elsewhere, become a builder, or
`strutil.joinArray` where the pieces are a list.

Source only: no ABI change and no golden changes, since every output must stay the same. The bootstrap compiler does
not fuse chains (§6, **Scope**), so its stage-1 build of the converted code is a little slower; nothing else is.

## 8. Tuning the builder

The native builder's constants and policies (`runtime/quest_runtime.h` and `quest_stdlib.c`) were chosen, not
measured:

- **The working buffer.** `quest_sb_new` allocates `QUEST_SB_BUFFER_SIZE` (512) bytes at once, however little the
  builder will hold. Alternatives: a smaller first buffer that doubles until it reaches a cap; allocating it on the
  first append; or one contiguous buffer that grows by doubling, with no chunks at all.
- **Long appends.** A string longer than `QUEST_SB_LONG_APPEND` (256) bytes flushes the working buffer and is copied
  into a chunk of its own, unless appended by `strShared` (§1), which keeps the string. The threshold, which may
  differ for the two; and whether `str` should share a read-only string (a literal, after §5) as `strShared` does.
- **Chunks.** Each finished chunk costs a `QString` header besides its bytes, in an array that starts at 8 and
  doubles. Alternatives: chunk data and lengths in the builder without headers, or a different first size.
- **`clear`.** It zeroes the chunk pointers and keeps the chunk array, at its largest size, and the working buffer.
  Alternatives: also drop the chunk array; drop everything, as if new; or keep the finished chunks' memory to
  reuse as working buffers.
- **`toString`.** It copies into a fresh string. Since it empties the builder (§1), it could instead hand over its
  buffer when the contents are in one piece, if the buffer is exactly full or the extra space is accepted, and the
  builder would start a new buffer on its next append.
- **Formatting.** `int` and `word` go through `snprintf`; a hand-written conversion may be cheaper.

These choices interact (the buffer's growth decides how many chunks exist, which decides what `clear` keeps), so they
are judged as strategies, not one constant at a time. First, a counting build of the runtime records, over a self-hosted
driver build, each builder's final length, number of appends and their sizes (`str` and `strShared` apart), and how many
`clear` and `toString` calls it sees; that distribution names the candidate strategies. Each candidate is then timed the
way step 0 measures (the driver build at `-j 1` and `-j 8`, allocation total and peak, the perf suite's
`stringbuilder_operations`), clearing `.build/quest-stages` between candidates, with a run of the current strategy
alongside to show the noise. The winner is kept only if it beats the noise; otherwise the simpler code wins. The C
runtime's own builders (`quest_conv_char`, `quest_print`, `quest_readline`) change with it, and are part of what is
timed.

## 9. Order

Each step is one commit unless it says otherwise, ends with the full `tools/check` (each touches `lib/`, `runtime/`,
or shared tests) on a quiet machine, and is ready to push when it passes. Each that changes the ABI bumps
`ABI_VERSION`, regenerates both ABI corpora, and clears `.build/quest-stages` before anything is measured. Each
measurement repeats step 0's and goes into `benchmarks.md`.

0. **Measure.** Record the self-hosted driver build (`-j 8` and `-j 1`), its allocation (total and peak), `./quest
   --stop-after codegen_c` and `codegen_arm64` on a large module (`codegen/c/ssac`, `ssa/printer`), the perf suite's
   `stringbuilder_operations` and `questlang_tokenizer`, and a profile's share of `quest_string_concat`,
   `quest_string_new`, and allocation. *Done when* the numbers are in this plan.
1. **`stringBuilder` as functions** (§1–3), done 2026-11-16 ("Make stringBuilder functions over a native type"; tested
   with a stage 1 built by a local self-hosted compiler, since the release cannot compile it), one commit: the interface and module, every call site, the rewritten
   `stringbuilder_operations` test, and the chained test module and its test; `toString` emptying the builder in the
   runtime and the bootstrap, and `strShared` in the runtime, both interpreters, and the callers (§1–2);
   `tools/externals`; ABI bump. *Done when* the full `tools/check` passes, the goldens other than the rewritten test's
   front-end phases are unchanged, both tests' run outputs equal each other and today's `stringbuilder_operations.out`
   but for the lengths after `toString` (§3), and the SSA shows known calls of the module's functions where closure
   calls were. Then a Markdown-only
   commit for the docs (`libraries.md` §1.2, `converting-python-to-quest.md` item 6, `arm64.md` §3), and a measurement.
2. **Drop `capacity`** (§4), done 2026-11-16 ("Drop QString's capacity"); ABI bump. *Done when* the full `tools/check` passes, the JIT's tests included, and the
   allocation is measured.
3. **The read-only bit** (§5), done 2026-11-16 ("Mark read-only strings by a header bit"; the test is
   `tests/python/test_runtime_readonly.py`, since `test_runtime.py` tests the bootstrap's values), with no literal
   changed yet: `Q_HEADER_READONLY`, the checks in
   `quest_string_set_char`, `quest_string_set_sub`, and the SSA builder's inlined `setChar`, and
   `quest_string_freeze`; ABI bump. *Done when* the full `tools/check` passes (nothing is read-only yet, so this
   proves the checks cost no behavior) and a test in `tests/python/test_runtime.py` shows a frozen string raising.
4. **Static literals** (§5), done 2026-11-16 ("Make string literals static, shared, and read-only"; the bit moved
   to 63, §5), in every implementation at once, with a shared test (a literal's identity across
   evaluations, `setChar` and `setSub` on a literal raising `string.error`, a mutable copy made by `getSub` still
   writable, a literal inside a closure and a module member) and `extensions.md`, `c-representation.md`, and the
   `QString` comment updated; ABI bump. Fix, in the same commit, any code the suites show writing into a literal.
   The switch tables for a `case` of string literals come with it (§5): add such a `case` (dense, at least 4 arms) to
   `tests/source/questlang/ssa_tables.quest`, and replace `ssa.md` §4.1's "a case of strings is not converted" with
   what it now does. *Done when* the full `tools/check` passes, the self-hosted interpreter agrees with compiled code
   on the new test, `ssa_tables` shows the string `case` as a table, and the gain is measured.
5. **Concatenation chains** (§6): the IR operation and its simplification, its lowering in the SSA builder, C
   printer, and IR interpreter, and `quest_string_concat_n`; ABI bump; a test of chains with literals, adjacent
   literals, empty strings, a part mutated after the concatenation, and an intermediate used twice (which must stay
   split). *Done when* `--stop-after ir_…` shows chains as one `concat`, the C and arm64 call
   `quest_string_concat_n` once per chain, the full `tools/check` passes, and the gain is measured.
6. **`<>` or the builder** (§7), in the compiler (`questlang/`) and `lib/`: straight-line builders become chains,
   accumulating `<>` becomes a builder. No ABI bump. *Done when* the full `tools/check` passes with no golden
   changed, a search finds no builder used only in straight-line code outside the kept cases, and the gain is
   measured.
7. **Tune the builder** (§8): the counting build and its distribution, recorded in `benchmarks.md`; the candidate
   strategies timed against the current one; the winner committed with its `quest_runtime.h` comment updated, and an
   ABI bump if the struct or header changed. *Done when* the full `tools/check` passes, the timings of every
   candidate are in `benchmarks.md` with the reason for the choice, and `stringbuilder_operations` and the
   chained test still give step 1's output.

**Why this order.** The builder comes first because it is the largest change and depends on nothing else, and
measuring it alone shows what the closures cost. `capacity` goes before static literals so that the emitters lay out
static strings once, at their final size. The read-only check lands before any literal is shared, so the moment
literals become shared, a write into one raises instead of corrupting every later evaluation; and it lands alone so
that a slowdown from the inlined check is visible apart from the gain of static literals. Static literals come before
the chains because they make every part of a chain a `QString *`, which keeps `quest_string_concat_n` to one form.
The source rewrite comes last because before the chains fuse, a converted chain makes n − 1 strings and would slow
every measurement in between; and with it separate, its gain shows apart from the optimization's. Tuning comes
after all of them because each earlier step changes how builders are used (step 1 makes them cheap to create, step
6 removes the short straight-line ones), so a strategy tuned earlier would be tuned for a distribution that no longer
exists.

When step 7 is done, what is still true moves into `libraries.md`, `extensions.md`, `ir.md`, `ssa.md`, and
`c-representation.md`, and this plan is deleted.
