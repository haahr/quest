# Review of the WebAssembly Backend, to Step 20

A review of the series that ends at bc0d67bc (steps 2 to 20 of [wasm-plan.md](wasm-plan.md)). It was first made at
4b10791a (milestone 1) on 2026-11-14, and was brought up to bc0d67bc on 2026-11-15: every finding of the first
review was run again, and the work added since (steps 11 to 20) was reviewed. Its first purpose is bugs and mistakes
of design; improvements follow.

**In short.** The compiler's core is still sound, and the JIT's meaning across inputs held up well. Of the first
review's findings, the two faults of `is` and the reuse of locals are fixed; almost everything in the runtime's
output and files, the string sizes, and the driver stands as it was (§1). The new work has three bugs in the code
generator, all where a boxed or proxied value meets code that expects the plain one (§2.1), and its most serious
faults are in recovery: an overflow rolled back with no replay can leave type tests unsound, and a replay loses
bindings without a word (§2.2). The page freezes on a loop that prints (§2.3). The dynamic runtime departs from
the C it ports in six places that give wrong results, traps, or a hang (§2.4).

**How it was made.** First review: the code generator read and probed with nine programs, each run compiled by
arm64, and by this backend in wasmtime and in node, and compared; the encoder, the runtime, and `util/realconv`
each reviewed apart. Update: the same programs and the first review's own cases run again at bc0d67bc with fresh
build directories; then four parts reviewed apart, each by reading and by programs of its own: steps 15 to 17 with
the reuse of locals and self tail calls; step 18's dynamic runtime; step 19's `Real` mathematics; and milestones 2
and 3 (the session, recovery, the JIT, the page), which were driven in node and in headless Chrome. "Confirmed"
means a program showed it; "suspected" means it was read and not run.

**How to run a program on this target** (§1.4): `./quest --backend wasm --stop-after run_c_compiled FILE`, with
`--wasm-engine node` for node. The comparisons are against `./quest --stop-after run_c_compiled FILE`, the arm64
backend's build.

---

## 1. The First Review's Findings, at bc0d67bc

| Finding | Now |
|---|---|
| `is` at a type parameter, for `Real`s and options | Fixed |
| `is` on options with a `Real` component | Fixed |
| `hash.identityHash` of a `Real` | Still there (§1.1) |
| node cuts output to a pipe at 64 KB | Still there (§1.2) |
| A closed writer still writes, into another file | Still there for programs; half fixed in a session (§1.2) |
| Late standard input in node | Still there (§1.2) |
| Paths | Still there for programs; partly fixed in a session (§1.2) |
| `putSubString`'s exception, `getSubString`'s short read | Still there (§1.2) |
| A string's size is not tested | Still there (§1.3) |
| `system.sysexit(200)` in wasmtime | Still there (§1.3) |
| `--backend wasm FILE` runs the native JIT | Still there (§1.4) |
| wasmtime's default stack; overflow as the engine's text | Still there for programs; right in a session (§1.4) |
| A member named `noClosure` | Fixed |
| Locals not reused | Fixed: `wasm/locals` reuses by type, and held up (§5) |
| An accumulating recursion is not a loop | Still there (§3) |
| Boxing an `Int` is a call into another module | Still there (§3) |
| Echo of an aggregate is quadratic | The joins are as they were; not timed again |
| Reading a `Real` is quadratic in its digits | Still there (§4) |
| A NaN's bits print as `inf` | Fixed in step 20: `word.toReal` raises `word.error` |
| A runtime's raise reports a site in `wasm/core` | Still there |

Not run again: the casts at each use, the unused build outputs, the encoder's and printer's edges, the tail calls
across units, and the two suspicions about `wasm/core`'s instantiation.

### 1.1. The Identity Hash of a `Real`

`hash.identityHash(:Real 1.0) is hash.identityHash(:Real 2.0)` is still true, where natively it is false: a boxed
`Real` is none of the kinds the hash tests for, so every `Real` hashes alike. 20,001 insertions into
`hashMap.newIdentityMap(:Real :Int)` take about 50 s against 0.1 s natively. The same holds for an option with a
`Real` component and for an abstract type whose representation is `Real`. `is` now goes by the descriptor
(`valIs`); the hash (`identityHashAt`) wants a case for the boxed `Real`. The first review's suspicion about
options behind opaque descriptors is settled: they hash by value now, through `identityType`.

### 1.2. Output and Files

1. **node cuts output to a pipe at 64 KB.** The base's `write` calls `fd_write` once and drops its result and the
   count written (`wasm/runtime`, `write`). A `putString` of 300,000 bytes piped to `wc -c`: 65,537 bytes in node,
   all of them in wasmtime. It needs a loop on the count, a retry for "try again", and `writer.error` on failure.
   **The session has the same fault one layer up:** `session-node.mjs` writes with `fs.writeSync` and ignores the
   count; with a slow reader 65,536 bytes arrive, and then the process dies of an uncaught `EAGAIN` at the
   prompt's write.
2. **A closed writer still writes, and may write to another file.** Close a writer on `a.txt`, open one on
   `b.txt`, and put a string to the first: natively `writer.error`; here the string is in `b.txt`. `putChar` and
   `flush` on a closed writer are silent, and so is a write after `writer.close(writer.output)`. Under `host.mjs`
   descriptors are not reused, so nothing lands in another file, but the write is still silent.
3. **Reading standard input from a pipe fails in node** when the data comes late:
   `(printf ab; sleep 1; printf cd) | …` gives `reader.error`, where arm64 and wasmtime read four bytes.
4. **Paths** (`wasm/core`, the resolution of a path): `//tmp` is not found, where natively it is; the empty path
   is the current directory (`fileExists("")` is true and `listDirectory("")` lists it, where natively the first
   is false and the second raises). `host.mjs` normalizes `//tmp`; `fileExists("")` is true there too.
5. **`writer.putSubString` out of range raises `string.error`,** not `writer.error`; and `reader.getSubString` on
   a short read leaves its destination untouched, where natively the bytes read are there before the raise.
6. New, lesser: `reader.file` of a directory raises `reader.error`; natively it opens, and `more` is false.

### 1.3. Traps a Program Can Reach

§2.10 of the plan allows a trap for the stack and the heap only.

1. **A string's size is not tested** (`wasm/runtime`, `stringNew` and `concat`). `string.new(4294967296 ' ')`
   gives a string of length 0, the size having wrapped; 3×10⁹ traps ("requested new array is too large").
   An array's size is tested (`arrayRep`); every byte array's allocation needs the same.
2. **`system.sysexit(200)` fails in wasmtime,** which takes a status below 126 only.
3. New: **a program with no string literal is an invalid module.** `import system: System; system.sysexit(3);`
   gives "invalid data segment index: 0" in node and "unknown data segment 0" in wasmtime. A string literal
   anywhere makes it valid.

### 1.4. The Driver and the Tests

1. **`./quest --backend wasm FILE` still runs the native JIT** and ignores the backend, with no word of it: a
   recursion 10⁹ deep that overflows at once in both engines runs to its end there.
2. **wasmtime is run with its default stack,** 512 KiB, not the 8 MB of §8.1 of the plan, and **a program's stack
   overflow is reported as the engine's own text.** A session reports `Exception: stack.overflow`, as it should.
3. New: **a build directory from an earlier compiler of this series fails at instantiation** ("incompatible
   import type for `quest.runtime::exception:int.error`"). The runtime's types changed and the ABI version stayed
   at 76 through the whole series, so nothing marks the older objects stale. The page has the same gap between
   its scripts and its archives (§2.3, 5).

---

## 2. New Confirmed Bugs

### 2.1. The Code Generator (Steps 15 to 17)

1. **A record or variant held boxed, used as a plain value, gives an invalid module.** A `var` parameter of
   record or variant type, or a local of such a type whose address is taken, is held as its box. `atom` pushes
   the box, one `eqref`; only `opAtom`, `recordAtom`, and `variantAtom` unbox it. Four statements call `atom` and
   expect the type's two parts: `sReturn`, `sJump`, `sAssign`, and `sVarDecl` with a value. The whole unit then
   fails to load.

   ```
   Def P = Record a: Int end;
   let rec last(var q: P k: Int): P = if k > 0 then last(@q k - 1) else q end;
   let arr: Array(P) = array of record a = 5 end end;
   writer.putString(writer.output conv.int(last(@arr[0] 2).a) <> "\n");
   ```

   arm64 prints 5; wasmtime: "type mismatch: expected eqref but nothing on stack"; node: "expected 2 elements on
   the stack for return, found 1". The same for `if c then q else … end`, a `case` arm, `try q else … end`,
   `let var cur = q`, `cur := q`, and a local `let var l = variant …` passed by `@l` and then returned. Passing
   `q` as an argument, or putting it in a tuple, an array, or a closure, works: the represent pass converts there.
2. **A value of a bounded type parameter that is a proxy traps on any access through the bound.** Every path
   through a view map casts to `$tuple` or `$option`. A proxy reaches it when the type argument is the supertype
   and the value is an upcast tuple or option; natively `quest_view_tuple_slot` and its siblings take proxies.

   ```
   Def Small = Record a: Int end;  Def Big = Record a: Int b: Int end;
   Def TS = Tuple x: Small var n: Int end;  Def TB = Tuple x: Big var n: Int end;
   let readN0(A <: TS p: A): Int = p.n;
   let readN: All(A <: TS p: A) Int = readN0;
   let tb: TB = tuple let x = record a = 1 b = 2 end let var n = 7 end;
   let ts: TS = tb;
   writer.putString(writer.output conv.int(readN(:TS ts)) <> "\n");
   ```

   arm64 prints 7; wasmtime: "wasm trap: cast failure" in `readN0`; node: "illegal cast". A store (`p.n := v`),
   an address (`@p.n`), a nested read, and a `case` on a proxied option at `A <: OB` trap the same way. The
   places: `tupleField` with a view map and direct access; `sStoreComponent` and `opAddrComponent`, which ignore
   the view map; `viewTag`; `switch`; `payload`'s viewed path; and `wasm/core`'s `viewOptionComponent`, which
   does not unproxy as `viewOptionPayload` beside it does.
3. **A module's bounded abstract type as the argument of a bounded type parameter raises `dynamic.error`.**
   `wasm/core`'s `viewMap` takes `storedType(actual0)` where the C it ports (`quest_view_map`) takes the concrete
   representation of the stored one. With `P::POWER(Record x: Int end)` in an interface, `Let P = Record w: Real
   x: Int y: Int end` in its module, and `getX(A <: Record x: Int end r: A): Int = r.x` held as a value:
   `getX(:ab.P ab.p(4))` is 4 on arm64 and `Exception: dynamic.error` here. A variant bound does the same.
   Suspected, of the same family: `makeProxy`, `mayBeProxied`, and `proxiesAgreeIn` use `storedType` where C uses
   `quest_proxied_type`.
4. **An `Ok`-returning tail recursion overflows under the JIT** at a few thousand calls:
   `let rec b(n: Int): Ok = if n is 0 then ok else b(n - 1) end` and `b(100000)` in the REPL give
   `stack.overflow`. Returning `Int` or `Bool` it runs, and compiled as a program it runs a million deep. In a
   REPL every recursive loop of type `Ok` stops at about 5,000 turns.

### 2.2. Recovery and the Session (Steps 11 and 13)

1. **An overflow rolled back with no replay can leave type tests unsound.** `wasm/core`'s `isSubtype` pushes the
   pair under proof on `trail`, recurses, and pops. An engine's overflow between the two leaves the pair there
   for the rest of the session, and every later test of it is assumed true. The count that §6.3 of the plan uses
   to decide on a replay covers three tables and not this one.

   ```
   import dynamic: Dynamic
   Let P = Tuple a: Tuple x: Int y: Tuple z: Int w: Int end end b: String end
   Let Q = Tuple a: Tuple x: Int y: Tuple z: Int w: Int end end b: Int end
   let d = dynamic.new(:P tuple let a = tuple let x = 1 let y = tuple let z = 2 let w = 3 end end let b = "s" end)
   let test(): Int = try begin let q = dynamic.be(:Q d) q.b end when dynamic.error then ~1 end
   test()
   let rec deep(n: Int): Int = begin let unused = test() 1 + deep(n + 1) end
   deep(0)
   test()
   ```

   The first `test()` is -1; `deep(0)` is `stack.overflow`, with no replay; after it `test()` is
   `Exception: trap`: `dynamic.be(:Q d)` succeeded on a `P`, and `q.b` read a `String` as an `Int`. Either the
   trail is cleared on a rollback, or any state the runtime keeps across calls is under the count.
2. **A stack overflow inside a host's file call becomes a wrong answer.** `host.mjs`'s `NodeMount.stat` and
   `call` catch every exception, a `RangeError` among them, and make it an error number or "not there".
   `let rec down(n: Int): Int = if system.fileExists("flag") then 1 + down(n + 1) else 0 end`, with the file
   there, gives `4287 : Int`; natively `stack.overflow`. `worker.mjs`'s `getSync` does the same (suspected).
3. **A replay drops, without a word, each committed input that does not succeed again, and all that depends on
   it.** With `gone.txt` there: `let removed = begin system.removeFile("gone.txt") 5 end`, `let after = removed +
   1`, then an input that overflows the compiler (3,000 additions). Afterward `removed` and `after` are
   undefined. §6.3's assumption that inputs give the same results is not tested, and the page keeps its files
   across a replay, which makes it false for any input that tests or removes one. At the least a replay that
   loses a binding should say so.
4. **Heap exhaustion ends the session in node and the tab in Chrome.** An input that fills the heap gives
   `ERR_WORKER_OUT_OF_MEMORY` and exit 70 in node, with no replay; in Chrome the renderer dies. §2.10 and §6.3
   treat the heap as a trap to recover from. In node the worker could be given a limit and replayed on its exit.
5. **`session-node.mjs --kernel`: an interrupt that arrives as a cell ends puts every later reply one request
   out of step and loses that cell's commit.** The worker writes its records to descriptor 4 and then posts
   `{records, committed}`; a SIGINT handled before that message ends the worker, drops the message, replays, and
   writes a second `interrupted` and `done`. After `let b1 = 1` and a SIGINT at once: `1 * 1000` answers
   `interrupted`, `b1` answers `1000 : Int`, and the next answers `b1`'s "undefined". `kernel_protocol.py
   --session` failed three checks by this race on one run under load and passed alone, so the test is flaky as
   it stands. Also: an interrupt handled just after the next request arrives ends that cell, where natively it is
   forgotten.
6. **A Quest exception that escapes the driver ends the session with "[object WebAssembly.Exception]".**
   `session.mjs`'s `request` replays for a `RangeError` and a `RuntimeError` only. Found with the interpreter and
   a library archive whose interface differs from the driver's; an overflow while `-i FILE` runs at the start
   takes the same path. A replay is there and not used.
7. **Writing to `/dev/fd/4` from a program ends the session:** the bytes reach `JSON.parse` in `session.mjs`'s
   `record`. Natively the open raises `writer.error`.
8. **A replay inside a replay turns output back on** (`replay`'s `finally` sets `quiet` false), so an earlier
   input's output is printed again; and after an interrupt, the `-i FILE`'s output is printed again, a new
   worker's first start not being quiet. `wasm_page.mjs` expects the second.
9. **A deeply nested line replays twice:** `isComplete` overflows and replays, and returns records with no
   status, which `repl.mjs` takes for "complete" and executes. By the same rule a request interrupted during
   `isComplete` executes the phrase.
10. **A driver that exits 0 while starting is reported as started,** and then answers nothing: `-i` of a file
    that calls `system.sysexit(0)` leaves a prompt that does nothing.

### 2.3. The Page (Steps 12 and 14)

1. **Printing in a loop freezes the page.** Each `fd_write` is a message, and `ui.mjs`'s `append` does
   `textContent +=` and reads `scrollHeight` for each. In headless Chrome, lines of 41 bytes: 1,000 take 1.3 s,
   2,000 take 5.4 s, 4,000 take 21.5 s, and 20,000 were not done after four minutes (1.8 s with the transcript
   hidden). The page's timer did not fire during the flood, so the Interrupt button is unlikely to answer. One
   write of 2 MB takes 0.2 s: the cost is by the message. Batch the output for each frame and append nodes.
2. **Restart while an input runs leaves the prompt dead:** the old request's promise never resolves, `drain`
   never returns, and later lines wait for ever. Only a reload recovers.
3. **A written file is invisible until closed,** flushed or not; natively a flush shows it.
4. **`MemoryMount.rename` does not test its target:** `renameFile("d" "d/e")` leaves an orphan (the directory
   lists as empty while `isDirectory("d/e")` is true); renaming a file onto a directory that is not empty leaves
   its children reachable; renaming `/quest` "succeeds".
5. **Suspected: nothing ties the page's scripts to its archives.** `build.py` writes fixed names, and `page.mjs`
   fetches them with no build identifier. A cache or a partial deployment can pair scripts with another build's
   driver, and `jit.mjs` already depends on exports added after step 14.
6. **Suspected: `?path=` and `?load=` make the page a confused deputy.** A link can name a prefix on another
   site and a program there to run at load, with no confirmation; the program can read any URL of the page's own
   origin through `/remote/0/…`, with the user's cookies, and send what it reads as file names asked of the other
   prefix. Harmless where the origin serves public files only. Displays are properly sandboxed.

### 2.4. The Dynamic Runtime (Step 18)

§8.4 of the plan has this "ported from the C as it stands, not redesigned". Each of these is a place where the
port departs from the C.

1. **A function adapter past arity 8 is skipped without a word.** `core.convert` calls `adaptClosure`, and the
   backend's `adapters` (`maxAdapted = 8`) returns the closure unconverted for more parameters; C's adapters have
   no limit. The arguments then keep the wrong views.

   ```
   Def Big = Record name: String y: Int end;
   Def Small = Record y: Int end;
   let f9(p1: Small p2: Int p3: Int p4: Int p5: Int p6: Int p7: Int p8: Int p9: Int): Int = p1.y + p9;
   let g9 = dynamic.be(:All(p1: Big p2: Int p3: Int p4: Int p5: Int p6: Int p7: Int p8: Int p9: Int) Int
       dynamic.new(:All(p1: Small p2: Int p3: Int p4: Int p5: Int p6: Int p7: Int p8: Int p9: Int) Int f9));
   writer.putString(writer.output conv.int(g9(record name = "n" y = 40 end 0 0 0 0 0 0 0 2)) <> "\n");
   ```

   arm64 prints 42; wasmtime traps ("cast failure" in `unboxInt`); node: "illegal cast". Where the slot misread
   happens to hold an `Int` the answer is wrong instead: 2 for 4, and 2 for 7. Step 18's record states the limit
   and not that the conversion is dropped past it; it should raise at the least.
2. **`core.convert` has no case for auto values:** `quest_convert_auto` was not ported, so an auto value seen at
   an auto supertype at run time keeps its components' old views. With `VS = Variant b: String c: Bool end` a
   component of one auto type and `VB = Variant a: Int b: String c: Bool end` of the other, a value made with
   `variant c` and taken through `dynamic.be` reads as `c` natively and as `b` here, the tag not renumbered.
   With a record component it traps.
3. **An option's identity hash follows a component that `is` does not compare.** `identityHashAt` hashes any
   case of one component by that component; `valIs` and C's `quest_option_identity_hash` do so for the
   single-word case only. With `Def MV = Option none some with var v: Int end end`, a key `m` put in an identity
   map, and then `c.v := 2` through a case binder: natively the hash is unchanged and the map has its key; here
   the hash changes and the map has lost it, while `m is m` is true on both.
4. **`dynamic.intern` never returns on a cyclic type table.**

   ```
   {"quest":1,"types":[{"abstract":"elsewhere.T","rep":0}],"type":0,"value":42}
   ```

   Natively `stack.overflow`; here no output, in either engine, until killed. `readValue`'s arms for a bound
   variable and an opaque type are self tail calls, which step 20 made loops, and `concrete`'s `while` has the
   same shape. A count of depth, as `identityType` has, would end it.
5. **Echo traps on two kinds of value and prints a third wrongly** (`wasm/print`, `show`):
   - a record's field held at another type (`record f = big g = 7 end` at `Record f: Mid g: Int end`): the
     record arm reads the field without `core.storedField`, and traps;
   - a nested auto type's reference to the outer parameter (`Auto A::TYPE with a: A inner: Auto B::TYPE with b: B
     a2: A end end`): the arm takes the last witness and ignores `core.boundIndex`, shows an `Int` as a
     `String`, and traps;
   - a bounded abstract type inside an aggregate prints `<val>` where natively it is `<hidden>`: `show` has no
     arm for a stored descriptor.
6. **Run-time subtyping takes a quantifier's bound contravariantly,** where C requires equal bounds: a function
   of type `All(A <: Small x: A) A` in a `Dynamic` is accepted by `dynamic.be` at `All(A <: Big x: A) A`, and
   natively refused.
7. **The check of an abstract type's recorded representation never fires.** `readTypes` clears the `rep` part's
   flag before it calls `core.abstractRep`, which then counts that part as an argument, so the arity never
   matches the registry. A document that gives `u/ab.T` another tuple, another kind, or a wrong number of
   arguments is refused natively and read here. Values are still read at the registered representation, so this
   is lax checking and not unsoundness.
8. **The JSON reader accepts malformed scalars.** `readJson` skips four or five characters for `true`, `false`,
   and `null` without comparing them (`txxx` is `true`); `readNumber` takes any run of digits, signs, points,
   and `e` (`-` is 0, `--1.5` is a `Real`); an integer past 18 digits wraps where natively it saturates
   (`9223372036854775808` reads as the least `Int`). Natively each but the last is `dynamic.error`. Lesser: a
   key given twice takes the last value where C takes the first; `[]` is accepted for `Record end`.
9. **A closed reader or writer:** `dynamic.intern` on a closed reader raises `reader.error` where natively it is
   `dynamic.error`, and `dynamic.extern` to a closed writer writes (§1.2, 2).
10. **Serialization's recursion runs out of stack early:** a list of 1,000 cells traps in wasmtime in `emit`
    (the default stack again, §1.4), and 5,000 in node; natively 5,000 is read and 20,000 is a `stack.overflow`
    that can be caught.

---

## 3. Where the Build Departs From the Plan

1. **A function that accumulates is not a loop.** Natively `let rec depth(n) = if n is 0 then 0 else 1 +
   depth(n - 1) end` runs 100 million deep by the SSA's `accumulate` pass. Self tail calls are loops here now
   (step 20), but this is not one, and it overflows at 200,000 in wasmtime.
2. **Boxing an `Int` is a call into another module** (`boxInt` and `unboxInt`), about 10 percent of the
   self-compilation by the first review's profile.
3. **§6.3's count does not cover all the runtime's shared state** (§2.2, 1), and its assumption about replay is
   neither tested nor reported (§2.2, 3).
4. **Step 17's record says a read, a store into a field, and an address go through the view map;** for a tuple's
   components the store and the address do not (§2.1, 2).
5. **§5.2, "each URL is fetched at most once in a session":** it is once for each worker, and an interrupt's new
   worker fetches again, so a replay can compile other sources (read, not run).
6. **§4.3 and step 19 on `Real`'s mathematics** claim more than was measured (§4, 2).
7. **The self loop encloses the prologue,** so captured descriptors are read again each time around; and whether
   a self tail call is inside a `try` is decided by the label's name (`try…` and `….body`), which is fragile.

---

## 4. Lesser Findings

1. **Reading a `Real` is still quadratic in its digits:** 400,000 digits take 8.6 s natively through
   `realconv.toReal` against 0.13 s for `strtod`; on this target three such reads take over 50 s.
2. **`Real`'s mathematics: no bug in the port, three statements to correct.**
   - `tan` differs from Apple's libm by 3 ulp for about 6 arguments in 200,000 (`tan(~8.109259628597705)`), where
     the plan and `stdlib/realmath_operations` say 2. The port is the right one (0.64 ulp against a 120-digit
     reference; libm 2.45); the test passes by its seed.
   - `realmath`'s header says each function is under 1 ulp; `sinh` reaches 1.66 and `tanh` 1.93. §7's item 6
     says "may differ in the last bit"; from native it is up to 2 ulp, 3 for `tan`.
   - `real.format` with `'g'` differs from native on exact ties that land in the exponent form:
     `real.format(9805.0 'g' 3)` is `9.80e+03` natively and `9.8e+03` here. Apple's `snprintf` is the one at
     fault, but §7 does not list it and the shared goldens hold only away from such values.
   - Accepted by the plan, measured: `pow` with x within 2⁻²⁰ of 1 and |y| over 2³¹ is off by up to 670 ulp.
     This is fdlibm's own defect; musl's current `pow` does not have it.
3. **Suspected: `isUnitImport` exempts `util/realconv` and `util/realmath` by name** from importing `real`'s
   record. It is sound while they use `real`'s externals only; a later use of `real.abs` would reach a record
   never imported.
4. **An `out` argument that needs a conversion and that the callee does not assign** traps here ("cast failure")
   and is a segmentation fault natively: the IR's fault (§7), but a trap a program can reach.
5. **`wasm/core`'s caches are linear scans compared by `is`** (`instantiate`, `viewMap`, `recordDict`, the
   abstract types' registry), they are never emptied, and `copy` still keeps identity only for descriptors
   with no parts. No wrong result came of it, subtyping being structural; the cost shows where descriptors are
   fresh each time. Reading a document and taking it at a supertype, 16,000 times: 12 s in wasmtime, 1 s
   natively. Serialization's own tables (`findShared`, `findId`) are linear too: 40,000 distinct records
   written and read take 39 s in wasmtime and 8 s in node against 1 s. `viewMap` is also called at each entry
   of a function with a bounded parameter, and `convert` on a record makes a new box even when the types are
   one.
   An `Array(Real)` of 100,000 written and read takes 71 s in wasmtime (11 s in node, 1 s natively): linear,
   but `realText` derives the digits twice.
6. **The whole list of committed inputs is posted with every reply,** in node and in the page.
7. **Nothing can interrupt a replay itself:** after an input that ran 0.7 s, an interrupt took 1.9 s.
8. **Formatting `Real`s is slow in wasmtime:** 1.14 million mixed formats take about 38 s, 8 s in node, 4 s
   natively. The mathematical functions are fast.
9. Smaller, suspected: `page.mjs`'s `pendingRecord` is not reset when a worker is ended in the middle of a
   record; a server that answers 200 for a missing file makes every probe a file; `build.py` removes whatever
   directory `-o` names; after the session exits the page's status shows the last input's time.
10. Suspected: `registerAbstracts` skips, without a word, an abstract type whose representation's descriptor the
    unit does not make; no case was found.
11. From the first review, not run again: the encoder and printer accept different modules at three edges;
    calls of another unit's function are never tail calls.

---

## 5. What Held Up

- **The code generator.** The first review's nine programs give arm64's output in both engines at bc0d67bc, but
  for the stack's depth. Fifteen more for the new work: locations of every kind, `out` parameters with an
  exception midway, variants with every kind of payload, records and views through generic code, proxies outside
  bounded code, and self tail calls a million deep.
- **The reuse of locals.** Read in full, and a generator of random programs with long-lived variables of every
  kind across calls, loops, and handlers: 48 seeds, some of 400 statements a function, with no difference.
- **`Real`'s mathematics and formatting.** 810,000 calls give the same checksums natively, in wasmtime, and in
  node; 104 edge values for each function and all their pairs for `atan2` and `pow`; no difference in what
  raises in about 13 million calls; no break of monotonicity in 240,000 steps for each function; `real.format`
  against `snprintf` in 1.14 million cases with the six ties of §4 the only differences.
- **`util/realconv`,** from the first review: about 2.9 million comparisons with the C runtime and none differed.
- **The JIT across inputs.** About 45 inputs: closures with state, generic functions, exceptions declared in
  one input and raised and caught in others, option types, modules with state, redefinition seen by earlier
  callers, all right, and right again after a replay. 36 inputs agree with the native `-i`. A generative type
  and an exception keep their identity across a replay.
- **Scaling.** 2,000 inputs go from 1.9 ms each to 3.4 ms; a replay of them takes 4.7 s, linear.
- **The page.** Program output, results, payloads, and error text holding markup arrive as text; `display.html`
  and `display.svg` run no script. It starts without cross-origin isolation. The file system does not escape
  its mounts in 20 attempts. Bytes of every value cross the records intact.
- **The dynamic runtime, on well-formed input.** About 110 values written give the same bytes on all three:
  `Int`s and `Real`s at their edges, every byte in a string, sharing and cycles, nested `Dynamic`s, auto types.
  463 documents read alike but for §2.4's cases; 816 truncated documents all raise `dynamic.error`, and 1,500
  mutated ones gave no trap or hang. `inspect` and `dynamic.be` at right and wrong types for some 30 kinds, the
  abstract types' registry, adapters up to arity 8, and about 90 echoed phrases agree.
- **Step 20:** self tail calls as loops in every position tried, every built-in operator as a value.
- **The encoder,** from the first review: every operation checked against the specification, and 72 programs
  gave bytes equal to `wasm-tools parse` of their text.

Not covered: the page in any browser but Chrome; a real network and a stale cache; an overflow inside
`instantiate` with the count not zero; timings on a quiet machine (the session's were taken under load).

---

## 6. Suggested Order

1. The subtype trail and the host's swallowed overflow (§2.2, 1 and 2): both give wrong answers after an error
   that looks handled.
2. The boxed record or variant as a plain value (§2.1, 1): a whole unit fails to load, for plain code.
3. Proxies and abstract types in bounded code (§2.1, 2 and 3); the adapter past arity 8, the conversion of
   auto values, the option's hash, and the reader's loop on a cyclic table (§2.4, 1 to 4).
4. One loop that writes until all is written, in the base's `write` and in `session-node.mjs`; a writer with a
   closed flag (§1.2).
5. The page's output batched, and Restart freed of the old request (§2.3, 1 and 2).
6. A replay that reports what it lost; the kernel's reply made one message (§2.2, 3 and 5).
7. The identity hash of a `Real`; one test of size before every byte array (§1.1, §1.3).
8. `--backend wasm` without the phase runs WebAssembly or is refused; wasmtime given its stack; the ABI version
   or a stamp of the runtime's types in a wasm object (§1.4).

Each bug wants a test with it. None of the first review's was caught by the run goldens or by
`tests/self-hosted/wasm`, and none of §2's is caught now.

## 7. Found on the Way, in Shared and Native Code

Not this series' doing:

- **A bounded quantifier in an interface cannot be imported:** `getA(A <: Small x: A): Int` in an `.int.quest`
  gives "malformed type 'All(A::<: Small x: A) Int'" at the import. So bounded generic code cannot live in
  another unit at all.
- The native compiler fails with `arrayOp.error` in `ssa/build/aggregates.recordField` on a `var` parameter of
  record type raised as an exception's payload; this backend compiles it.
- An abstract type bounded by a tuple or an option fails in shared code (`ir/slots.operation`,
  `ir/represent.viewPlan`).
- The unassigned `out` argument with a conversion is a segmentation fault natively (§4, 4).
- Subsumption of an auto value with a covariant record component fails on both: a segmentation fault natively,
  a cast failure here.
- A record type with a field name given twice in a serialized document ends the native program with a fatal
  error; here it is `dynamic.error`.
- Natively `identityHash` of an option's proxy differs from its original's while `is` is true.
- `is` between records in code of known type is refused by the SSA ("unsupported: is of a value of
  QRecordVal") and runs here.
- The JIT fails on one of the first review's probes with "ssa: unsupported: a use of variable qj_1_record (423),
  which nothing binds"; and a conversion the represent pass rejects is, under the JIT, an uncaught
  `rejectedConversion` with the compiler's own traceback.
