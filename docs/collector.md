# Plan: Replacing the Boehm Collector

Quest allocates through the Boehm-Demers-Weiser conservative collector: every object by `GC_MALLOC`, scanned word by
word for anything that looks like a pointer, and the stack, registers, and data segments likewise. It has served well
because it asks nothing of the compilers: no object headers, no stack maps, no write barriers. It is also the
largest cost in the benchmark suite (benchmarks.md §3.1: allocation and collection are 50 to 90 percent of the
samples in half the programs), and it keeps dead data alive through stale stack slots (arm64-performance-review.md
§3.2). This document designs a collector of Quest's own: precise where the compilers can make it so, generational,
bump-allocating, able to move but not obliged to, and asks what must change to get there.

**Status: step 4 done, 2026-11-05** (decided 2026-11-02; reviewed and reorganized 2026-11-03). Section 6
records the decisions, section 7 the risks and the checking modes that catch them, section 8 the steps, and section
9 what the reviews changed. The committed collector is steps 1 to 6 of §8; evacuation and generic layouts (steps 7
and 8) are designed and taken only on measurement.

---

## 1. What the Runtime Is Today

What a collector must fit, from `runtime/quest_runtime.h`, `c-representation.md`, and `arm64.md` §3.13:

- **Allocation** is `quest_alloc(size)` (zeroed, scanned) and `quest_alloc_atomic(size)` (pointer-free: string
  buffers, `Array(Int)`, `Array(Real)`, `Array(Bool)`, `Array(Char)`, traces). The C backend prints the calls, the
  arm64 backend selects them as calls, the runtime makes about ninety more for its own data. Each is a call into the
  libgc dylib through thread-specific free lists; a per-size cache tried in the runtime gained 1.3 to 1.7x on the
  allocation-heavy programs by itself (benchmarks.md §3.1).
- **Objects have no header.** A tuple is its words (`{QVal _0; int64_t _1}`), a closure two words (`fn`, `env`), a
  closure environment a struct of its captures, an option a tag and words, an array a length and words, a string a
  length, capacity, and buffer pointer, an auto value a descriptor and a word. Only a record's payload carries a
  descriptor (`QRecordHeader`), and a `QRecordVal` is two words, payload and dictionary, boxed when stored.
- **Every aggregate slot is one word** (runtime-design.md §2.2), a `QVal` union: a pointer, an `Int`, a `Real`, a
  `Bool` or `Char` widened. Which it is follows from the static type, except for a slot of a type parameter's type in
  generic code, whose word is whatever the type argument's representation is. The SSA keeps `ptr`, `int`, `real`,
  and `val` apart (ssa.md §1), where `val` is a word the code does not know the kind of.
- **Interior pointers are everywhere by design:** a record's payload follows its box in one allocation, an aggregate
  allocates the boxes of its fields after itself (`embedded`), and a proxy is its original's address plus one, a
  tagged pointer (`QUEST_PROXY_TAG`). The representation relies on the collector recognizing a pointer into the
  middle of an allocation.
- **Roots** are found conservatively everywhere: the C stack and registers in both backends (clang emits no maps, and
  the arm64 backend emits none, though `codegen.frameSlots` knows each slot's class), the data segments (module
  records `qm_*`, the runtime's statics: function tables, record dictionaries, the descriptor and view-map caches,
  `quest_system_args`), the thread-locals holding the exception state, and the JIT's data regions, registered with
  `GC_add_roots`.
- **One mutator thread.** The driver's `-j` compiles in child processes; nothing else is concurrent. A collection
  can therefore happen only inside an allocation, which is a call, and the backends already treat an allocation as a
  call that may do anything.
- **No finalizers, no weak references.** Files are `FILE *`s closed by the program; processes are reaped on wait.
- **Identity** is the address: `is` compares words (originals, through proxies), and `quest_identity_hash` mixes the
  word (`util/hash.identityHash`, which the library's hash maps keyed by identity use). `quest_serialization.c`
  shares cyclic data through a table keyed by address (`quest_ptr_hash`), live across the allocations it makes.
- **Runtime metadata lives in the collected heap:** instantiated descriptors (`quest_instantiate_descriptor`,
  memoized in `quest_inst_cache`), view maps, record dictionaries, variant adapters, abstract type entries, all
  allocated with `quest_alloc` and kept in tables keyed by their addresses.
- **The bootstrap shares the runtime,** and its C printer declares the same structs and prints the same `quest_alloc`
  calls, so a change to the object model is a change to both compilers (two-compilers policy, testing.md §2.8).
- **Darwin arm64 is the platform;** the C backend also runs on Linux, which the runtime keeps working (the stack
  guard and the frame walk are conditional).

## 2. What Recent Collectors Do, and What Carries Over

- **Go** is non-moving and non-generational: concurrent tri-color marking with a hybrid insertion-and-deletion write
  barrier, size-classed spans with per-thread caches, pointer bitmaps per span rather than object headers, separate
  "noscan" spans for pointer-free objects, large objects (over 32 KB) straight from the page heap, precise stack maps,
  and a pacer that spends about a quarter of the CPU on background marking. It optimizes for pause time over
  throughput and pays for it: no bump allocation, no compaction, every pointer store barriered. What carries over:
  noscan spans, and that a type's pointer map is set at allocation rather than read from a header.
- **Java (HotSpot)** has moved from Parallel (throughput, copying young generation, mark-compact old) through G1
  (regions, SATB concurrent marking, card-table remembered sets, evacuation pauses) to ZGC and Shenandoah, which
  compact concurrently behind load barriers (colored pointers, forwarding tables) and became generational in JDK 21
  and 24. Load barriers cost on every pointer load, which a language whose data is mostly immutable and read often
  should not pay. What carries over: regions evacuated selectively by garbage density, and the header word's role in
  forwarding and hashing.
- **V8 (Orinoco)** is generational with a parallel copying scavenger (Cheney) for the young generation, mark-compact
  for the old with concurrent marking behind a write barrier, selective evacuation of fragmented pages, and a large
  object space. Because it moves objects, an identity hash is stored in the object once computed. What carries over:
  a young generation collected in parallel, and evacuating only the pages worth it.
- **.NET** is generational (0, 1, 2 and a large object heap over 85,000 bytes, not compacted by default), compacting
  with pinning, card tables, bump allocation from per-thread allocation contexts, background marking of generation 2,
  and regions since .NET 7. Its object header sits *before* the method-table pointer the object reference points to.
  What carries over: pinning as a first-class state, and a header at a negative offset, which leaves the object's own
  layout untouched.
- **JavaScriptCore (Riptide)** is the closest relative in constraints: a conservative stack (its cells sit in blocks
  segregated by size, so an ambiguous word is validated by arithmetic rather than a bitmap), a precise heap, no
  moving, generational by sticky mark bits (an object once marked stays marked, so a minor collection marks only
  what is new), mostly concurrent marking behind one barrier that serves both purposes, and bump allocation inside
  blocks. It shows that conservative roots and a fast generational collector are compatible.
- **Immix** (Blackburn and McKinley, 2008) organizes the heap in 32 KB blocks of 128-byte lines, allocates by bumping
  through runs of free lines, marks lines as well as objects, and defragments opportunistically: it evacuates objects
  from fragmented blocks when it has room, and leaves the rest where they are. Its sticky-mark-bit generational
  variant was within a few percent of a copying nursery. *Fast Conservative Garbage Collection* (Shahriyar, Blackburn,
  McKinley, 2014) added ambiguous roots to it: a bitmap of object starts validates a word that may be a pointer, the
  object it refers to is pinned (its line is not evacuated), and the cost against fully precise collection was about
  one percent. This is the design this document recommends.
- **OCaml and MLton,** the functional relatives: a bump-allocated minor heap, promotion on first survival, a header
  word per object, and (MLton) full knowledge of every object's layout because it monomorphizes. Quest keeps
  polymorphism at run time, so it cannot have MLton's certainty everywhere (§3.3).
- **Hash codes under moving** (Agesen, 1999; used by JikesRVM and others): two header bits say *unhashed*, *hashed by
  address*, or *hashed and moved*. Hashing an object sets the second state and returns its address; a collector that
  moves such an object appends a word holding the old address and sets the third state, after which the hash is read
  from that word. Objects never hashed, the vast majority, cost nothing, and this is the scheme the question proposes.

## 3. The Design

In one sentence: an Immix heap with sticky mark bits, a header word before each object naming its layout, bump
allocation inlined in both backends, a write barrier on the few mutating stores, precise scanning of every word whose
kind the compiler knew, conservative treatment of the words it did not (the stack, `val` words, the JIT's data), and
the right to move reserved: evacuation is designed here (§3.6) and taken only if fragmentation is measured (§8, step
7), since it is where most of the collector's difficulty lies and least of its gain.

### 3.1. The heap

- **Blocks and lines:** 32 KB blocks of 128-byte lines, as Immix. A block is free, recyclable (some lines free), or
  full. Allocation bumps through the next hole of free lines; a 128-byte line is the unit of reclamation. A medium
  object (over a line, up to 8 KB) is allocated from a fresh hole, as Immix's overflow allocator.
- **A large object space** for objects of 8 KB and up (strings, arrays), page-granular, never moved, marked in a
  side bitmap, freed when unmarked. The threshold is a parameter to measure (§6).
- **Runtime metadata stays in the ordinary heap:** descriptors, instantiation caches, view maps, record dictionaries,
  abstract types, adapters, allocated as now and reached from the runtime's listed roots (§3.8), so a full collection
  marks them at a cost proportional to their size, small outside a long JIT session. They are keyed by address, which
  nothing in the committed collector changes; should evacuation be taken (§3.6), they are allocated pinned at birth
  into blocks of their own, a third cursor beside the noscan one (§3.9), so that they neither move nor pin lines of
  other blocks. A REPL or Jupyter session, with module rollback and redefinition, keeps making them and keeps them,
  as it keeps JIT code already (decided 2026-11-03). An earlier draft put them in an immortal space of their own,
  never collected and never scanned; it existed to keep them out of the moving question, and went when moving became
  conditional (2026-11-03).
- **One reserved virtual range** for all of it (tens of gigabytes reserved, committed as used), so that "is this word
  in the heap" is two comparisons, and the metadata (object-start bitmap, line marks, block table) is indexed by
  address. The range is asked for at 2^46, above any integer a program is likely to hold, since an ambiguous word
  holding an integer equal to an object's address keeps the object (and reads as a store without a barrier to the
  `barriers` check); the system may decline the hint and place it lower. The tables are mapped after the range, not
  where the system would put them, just above the binary, which the JIT's regions need (jit.md §3.6).
- **Metadata off to the side:** an object-start bitmap (one bit per 8 bytes, as conservative Immix; set by every
  allocation, §3.4, and intersected with the mark bitmap at the end of every collection, §3.6, so that only live
  objects validate), which validates ambiguous words, finds an object from an interior pointer, and finds objects
  inside a remembered region; a mark bitmap (one bit per 8 bytes, the truth about liveness, §3.2); line marks (a
  byte per line); a block table (state, hole cursor, live lines).

### 3.2. Objects

- **A header word before each object,** at the address the pointer points to minus 8 (.NET's placement). The object's
  own words are unchanged, so every struct the C backends declare and every offset the arm64 backend selects stays
  as it is; only the allocation changes, returning the address after the header. Embedded boxes and a record's
  payload have no headers of their own: they are words of their allocation, described by its layout, reached by
  interior pointers that the object-start bitmap resolves to the allocation.
- **The header holds a layout pointer and two bytes of flags:** the pointer to a *layout* (below), 8-byte aligned,
  in the low 48 bits; the top sixteen (free on a 48-bit address space, and layouts are static data or run-time data
  the collector places below that line) are two bytes with one writer each. The collector's byte holds *old* (the
  barrier's hint that the object has been marked, §3.5), and, reserved for evacuation, *pinned* and *forwarded*; the
  mutator's byte holds *logged* (for the barrier) and, reserved likewise, the two hash bits of §3.7. Each side writes
  its byte with a byte store, so no read-modify-write of the word is shared, and a marker thread (step 9) would need
  fences but no atomics. The mark bit itself is not in the header: liveness lives in a side mark bitmap per block
  (§3.1), which a full collection clears a block at a time instead of touching every object, and which keeps the
  minor collection's test of an old referent, most of what a young object's words point at, in a small hot structure
  rather than a load of each referent's line. The header's *old* byte is written by the marker as it marks and is
  only a hint for the barrier: a stale value (an object the current cycle has not yet reached) makes the barrier
  conservative, logging an object that needed no logging, never wrong. Variable-sized objects (arrays, strings'
  buffers, option payloads) keep their lengths where they are; the layout says where to read them.
- **A layout** describes an allocation's words: for each word, pointer, scalar, or *ambiguous* (a `val` word whose
  kind the allocation site did not know, §3.3), plus the size or where to find it. For a record, the layout is its
  existing `QRecordHeader` descriptor's information in this form. Layouts are static data: the describe pass already
  emits descriptors per unit; it emits layouts the same way, deduplicated per unit, and the runtime's own allocations
  name theirs from a fixed table. A layout for a pointer-free object marks it *noscan*.
- **Cost:** 8 bytes per object, which is half again on the commonest object: a two-word tuple is 16 bytes today and
  24 after, a closure the same, a string header 24 and 32. Against that, Boehm's 16-byte granules round a 24-byte
  object to 32 today and bump allocation wastes nothing beyond 8-byte alignment, so a three-word object costs what
  it does now. Step 1 measures the growth on Boehm, where the 24-byte object rounds to 32 and the number comes out
  double; it is translated to the design's (8 bytes per object, from the allocation counts by size) before it is
  recorded.
- **Alignment:** objects are 8-byte aligned, headers included, and the allocator bumps in multiples of 8. Nothing
  the backends emit needs more: every slot is a word, a `Real` is a word, and arm64's paired loads and stores
  (`ldp`, `stp`, which the backend emits for adjacent words) need only the alignment of one register, 8 bytes for
  `x` registers; their 16-byte requirement applies to the stack pointer as a base, never to heap addresses. clang's
  copies of 16-byte structs (`QRecordVal`) use pairs or NEON loads, which on arm64 and x86-64 take any alignment on
  ordinary memory. Boehm's 16-byte alignment was incidental, and nothing relies on it: the proxy tag uses one low
  bit, and the header's flag bits live in the layout pointer, whose static data can be aligned as widely as the bits
  need. The hash word of §3.7, should evacuation be taken, goes before the header and keeps every object's
  alignment. If a platform ever needs 16-byte objects (a vector type in the runtime, say), the allocator bumps in 16s
  and the header sits in the 8 bytes before the object, with 8 bytes of padding before that; nothing else changes.

### 3.3. What is a pointer

Three classes of word, decided when the code is compiled:

1. **Precise:** a word whose static type is a pointer type (`ptr` in the SSA), or a scalar. The collector follows or
   skips it by the layout, and may rewrite it should the object it refers to move. Interior and tagged pointers are
   precise too: the collector resolves the allocation through the object-start bitmap, and a move would rewrite the
   word keeping its offset and tag.
2. **Ambiguous:** a `val` word of an object allocated in generic code (`Tuple A Int end` made by a polymorphic
   function, `Array(A)`'s elements), whose kind depends on a type argument the code did not have. The collector
   validates it (in the heap range, at or inside a live allocation, or at one's end: no Quest program can form a
   pointer one past an array, but clang can from the C backends' output and in the runtime, a loop's end kept with
   its base dead, so such a word counts for the object it ends and for any that begins there) and, if it is valid,
   marks the object; with evacuation on, it also **pins** it: the word is never rewritten, so the object never moves.
   An `Int` that happens to look like a heap address keeps an object alive, as under Boehm today; it is never
   corrupted. Only a live object validates (§3.6), so the precise words of what an ambiguous word reaches are
   current, and the marker may trust them.
3. **Roots:** the stack and registers (conservative in both backends, as now, saving the registers to the stack
   first), the per-unit root tables of §3.8 (precise), the runtime's statics (precise, listed), and the JIT's data
   regions (ambiguous).

So the heap is precise wherever the compiler knows, and nothing is less safe than under Boehm. What ambiguity costs
the committed collector is a validation per ambiguous word and the false retention Boehm has today, both small. What
it would cost a moving one is the right to move: a pinned object stays, and its line is not reclaimed by evacuation.
How much would be pinned depends on the program: the MLton suite's programs are mostly monomorphic; the compiler,
whose data lives in `vector.T(A)` and `hashMap.T(K V)`, would pin a great deal. Two steps reduce it, neither needed
for correctness (§8): **stack maps for the arm64 backend** (step 5; arm64.md §3.13 describes what they need, and the
frame-pointer walk of jit.md §3.9 already finds the frames), worth taking for the dead-slot retention they end
whether or not anything moves; and **layouts for generic allocation sites** (step 8, taken on what step 7 measures),
which the specializer already removes in part, and which the descriptor-passing machinery (`DescriptorParam`)
completes: a polymorphic function that allocates an aggregate holding type-parameter words takes its arguments'
descriptors, as one that builds a descriptor mentioning them does now, and builds the layout once per distinct set
of arguments, through an inline cache at the site. A frame without a map is scanned conservatively, so units
compiled through C, by either C backend, need nothing and get nothing: their stacks stay conservative by design,
since clang emits no maps for ordinary C. A mapped frame's memory-class slots, where escape analysis puts the
aggregates that do not escape (ssa.md §4.2), are scanned conservatively too, since nothing describes their words.
A mapped frame's pointer in a callee-saved register across a call is precise only when every younger frame that
saved that register is mapped too: a C-built callee's or the runtime's save slot is in a frame no map describes and
cannot be rewritten, so the frame walk treats such a register's value as ambiguous, which matters only to evacuation.

### 3.4. Allocation

- **Bump allocation inline** in both backends: compare the cursor and the limit, bump, store the header, set the
  object's bit in the object-start bitmap (a byte loaded, or'ed, and stored: the bitmap is what validates ambiguous
  words, §3.1, and only the allocator knows where objects begin), return the address. About ten instructions, which
  step 3 measures against the call into libgc. The cursor and limit are two words in a global the runtime owns, not
  a register the arm64 backend dedicates: a raise is `_longjmp` (`Q_LONGJMP`), which restores the callee-saved
  registers to their values when the `try` was entered, so a cursor in one would be rolled back and the next
  allocation would overwrite live objects; and the C-built units and the runtime bump the same words. There are two
  cursor pairs, one per kind of block (§3.9), chosen by the site's layout. The slow path, a call into the runtime,
  finds the next hole or collects, and during an incremental cycle serves every allocation (§3.10). This is the
  inline allocation path the arm64 review set aside while the collector was Boehm's (arm64.md §6.3, item 2); with
  Quest's own collector, the dependency is on itself.
- **Zeroing:** holes are zeroed when a block is recycled, not per object, so the compilers' assumption that fresh
  memory is zero holds.
- **Escape analysis is unchanged:** an allocation that does not escape is a stack slot (ssa.md §4.2), and stack slots
  have no headers, which is fine since nothing in the heap refers to them and the stack is scanned conservatively.
  A barrier call is not an escape: it keeps no pointer, and the pass drops the barriers of an allocation it makes a
  slot, which needs none (a slot is a root) and has no header word for the object barrier to read.
- **`--nogc`** becomes the collector with collection disabled (allocation only), for debugging, or goes; libgc is no
  longer a prerequisite.

### 3.5. Generations

- **Sticky mark bits:** an object's mark bit is cleared only by a full collection. A minor collection marks from the
  roots and the remembered objects, and stops at anything already marked, so it visits the young objects only, and
  "promotion" is being marked where the object lies. The young objects are the unmarked ones, in the holes allocated
  into since the last collection, whether in fresh blocks or in recyclable ones; after the minor collection the line
  marks of those blocks say which holes are free again. A copying nursery would gain locality but requires every
  reference into it to be rewritable, which §3.3's ambiguous words forbid; the sticky-bit variant was within a few
  percent of copying in Immix's measurements, and nothing stops a later measurement here.
- **The write barrier:** on a store of a word that may be a pointer (`ptr` or `val` in the SSA; a `val` store in
  generic code, an `Array(A)` element or a hash map's bucket, may be one) into an object that already exists, if the
  header's *old* byte says it has been marked and its *logged* bit is clear, log it (set the bit, push its address).
  A minor collection scans the logged objects' pointer words by their layouts, then clears the log. A load of the
  header's flag bytes, a mask, a compare, and a branch on the fast path; nothing on stores of scalars, and nothing on
  the stores that initialize an object being made (`opMake*`) outside an incremental cycle, unless a call is printed
  between its allocation and its last store (a string literal's allocation, a conversion, a descriptor's
  instantiation), in which a collection may run and mark it old: the printers and the SSA's builder keep the objects
  being initialized, and from the first such call on log each through the barrier before every later call and after
  its last store, so that no collection finds one old with a store since its last logging; inside a cycle the
  object is logged as it is allocated (§3.10), which covers its initializing stores at once. *The barrier follows
  its store*, with no call between the two: a barrier before the store is forgotten by a collection inside the
  stored value's own computation (`r.name := "literal"`, a `var` parameter assigned a call's result, a slot whose
  value is boxed), which logs nothing for the store that follows it. The runtime's C does the same by hand (the
  value into a local, then the barrier and the store), and where an operation builds many objects with stores
  between their allocations (a descriptor's instance, a dynamic value's reading and writing, a directory's
  listing, the program's arguments) it holds collections off for the operation (`quest_gc_hold`,
  `quest_gc_release`): everything it allocates stays young, so only its stores into older objects need barriers,
  and a pointer it parks outside the heap and the stack is not lost. A hold is for an operation bounded by its
  result's size that runs none of the program's code; a raise releases every hold. The same barrier serves
  incremental marking (§3.10), and a marker thread if one is ever added, as Riptide's does. Stores by a slot's address
  (an array's element, and the interior stores below) mark a *card* instead, 512 bytes of the heap with a byte each
  in a table beside it: the fast path is a range check and two bytes' loads, the slot's line mark (a slot in an
  unmarked line is a young object's, whose stores need no barrier; a large run's lines are marked with it) and its
  card, the slow path marks the card and lists it, and a minor collection scans the dirty cards' words by the
  layouts of the old objects in them (the one that starts before the card and reaches into it, by the start bits,
  and those that start in it; a young object's words are left to marking, since scanning a dead one's would keep
  what it points at alive). Added 2026-11-04 (step 4), when the
  compiler's build showed its tables logged whole: the log's scan was 17.5 s of the build's 20.5 s of minor pauses,
  a hundred logged objects taking 26 ms late in the build. The log and the dirty list live outside the heap (as do
  the work list and, should evacuation be taken, the slot log), so the slow paths never collect and §1's rule that a
  collection happens only inside an allocation holds.
- **Stores through interior pointers** find no header at the address minus 8: a record's `var` field is stored
  through its payload pointer, and the payload sits after the box when the record was made in it, at the start of
  its allocation when it is a module's, and elsewhere when `quest_record_box` boxed a viewed record; `sStoreAt`
  through a `var` or `out` location, and a view's slot, are interior too. The IR marks these forms, and for them the
  backends emit the slot's barrier, which checks that the address is in the heap at all (a location is often a
  stack slot) and marks its card, so no header is read and no allocation resolved. (Before card marking, the slot's
  barrier resolved the allocation through the object-start bitmap and logged it; a tuple bound by a case binder, an
  option's payload, keeps the object barrier, which takes a word under 65536 before the tuple for the option's tag
  and the header one word further back.)
- **Where the mutating stores are:** the IR's `sStoreField`, `sStoreComponent`, `sStoreElement`, `sStoreAt`, and
  `sAssign` to a captured box; the library's hash maps and vectors are compiled Quest, so their barriers come from
  the IR; and every pointer store into an existing object in the runtime's C, which no list here can name in full
  (`quest_proxy_store`, the proxy caches, the module records' fields written by JIT inputs, a string's buffer
  replaced as it grows, a cache's chain extended), found by an audit of the runtime in step 2 and afterwards by
  `barriers`. The IR verifier checks that every store of a `ptr` or `val` word into heap memory is one of these.

### 3.6. Collection

- **A minor collection** stops the mutator (there is one), saves registers, scans roots, logged objects, and dirty
  cards, marks young objects by their layouts, and sweeps the line marks of the blocks allocated into. Its pause is what
  survives and the roots: 8.6 ms on average on the compiler's build, whose nursery adapts upward, 27 ms at the longest,
  and 1.8 ms on a REPL session (§8, step 4). The nursery (`QUEST_GC_NURSERY`, 64 MB by default, the heap's least size,
  chosen on step 4's measurements of 4 to 128) adapts to what survives: doubled while more than a quarter of the young
  bytes survive a minor collection (a program building a structure it keeps, whose minor collections would mark what the
  next full one marks again, as tailmerge's do), up to a quarter of the heap's target and then off, with one minor
  collection at that size every eighth full one to see whether the program still keeps what it allocates, and halved
  back toward the configured size while under a sixteenth survives.
- **A full collection** clears the mark bitmaps a block at a time, marks everything, and sweeps every block's lines.
  Marking is a work list over precise and ambiguous words, which incremental marking (§3.10) later cuts into slices.
- **Only live objects validate.** At the end of every collection, minor or full, the object-start bitmap is
  intersected with the mark bitmap, a pass over 1/64 of the heap, so that a dead object's start bit goes with its
  liveness. Without this a dead object in a live line, which keeps its header, could be validated by an ambiguous
  word (an `Int` on the stack) and scanned, and its precise words, which the marker trusts, may point into lines the
  same collection reclaimed and later reused. Boehm is immune because it validates every word; this collector is
  immune because nothing dead validates. A young object that dies and is resurrected by the stack in a minor
  collection is harmless, since nothing was reclaimed since it was allocated; its start bit goes at the end of that
  collection. The `layouts` walk (§7) uses the same intersection.
- **Evacuation, designed here and taken only on a measurement** (§8, step 7). Fragmentation under Immix is a line
  matter: a block whose survivors are scattered keeps their lines and recycles the rest, so the cost of never moving
  is the lines the survivors hold, and the Immix paper found defragmentation worth a few percent on average and more
  only in tight heaps. Steps 3 and 4 record live lines against live bytes on the suite, the compiler's build, and
  long REPL sessions; evacuation is taken if that ratio shows holes that recycling does not recover. Its design, so
  that nothing before it is built in its way: it runs in a full collection, after marking and never during it.
  Candidate blocks are chosen before marking by fragmentation (live lines against free, from the last sweep), as
  Immix. Marking moves nothing: it pins what ambiguous words reach, and it records in a *slot log* the address of
  every precise word (in the heap, a root table, or a listed root) that refers into a candidate block, a log
  proportional to the references into the candidates, a small part of the heap. When marking is done the live bytes
  of each candidate are exact, so the collector takes the candidates it can empty into the free blocks it holds,
  copies their unpinned live objects to fresh holes, marks each old copy forwarded with the new address, rewrites the
  logged words (a logged word is rewritten only if it still refers to a forwarded object, and one inside an object
  that itself moved is rewritten in the copy), and clears the mark bits, start bits, and line marks of the old
  copies, which the trace had set, leaving the pinned objects' lines. If the log reaches its bound, the candidates
  it does not cover stay in place, so the collection degrades to a non-moving one rather than failing; this is G1's
  remembered set for its collection set, built during marking. Moving during marking, as Immix proper does and as
  this document first said, would be unsound here: an ambiguous word found after its referent moved could neither be
  rewritten (it may be an `Int`) nor have the move undone. The other sound order, two traces (mark and pin, then
  trace again copying), is simpler and doubles the marking of a defragmenting collection; the log is preferred
  because evacuation then costs in proportion to what moves. Pinned objects, large objects, and the metadata blocks
  of §3.1 never move.

### 3.7. Identity hash

In the committed collector nothing moves, so `identityHash` stays the mix of the address, as now, and `is` compares
addresses. The scheme for a moving collector, as the question proposed, is designed with the header bits of §3.2
reserved for it and taken with evacuation (step 7): the two hash bits are *unhashed*, *hashed*, *moved*.
`identityHash` of an unhashed object sets *hashed* and returns the mix of its address; of a hashed object, the same;
of a moved object, the mix of the word at the address minus 16, where the collector put the original address when
it copied the object (it allocates the copy 8 bytes larger, writes the old address before the header, sets *moved*;
a further move copies that word along). Pinned objects are never copied, so their addresses stay their hashes. An
interior object (an embedded box, a record's payload) shares its allocation's header and states, so hashing it sets
the allocation's state (found through the object-start bitmap, as §3.5's interior stores find it), and its hash
after a move is the mix of the allocation's old base plus the object's offset, which a copy preserves. `is` needs
nothing: it compares current addresses, which the collector keeps consistent by rewriting every precise reference
and moving nothing an ambiguous one reaches. Options and reals hash by value already, and keep doing so.

Serialization's table keyed by address (`quest_ptr_hash`) must not see an object move while it runs: it allocates
its output as it walks, and its nodes' `ptr` words are precise, so a move would rewrite them while each node stayed
in the bucket of the old address. Evacuation is optional in any collection, so with step 7 the collector keeps a
hold count (`quest_gc_hold_moves`, released when the walk ends, by a raise included) under which no collection
evacuates, and serialization takes it for the walk. Keying the table by identity hash, which the scheme makes
stable, would work too and is not needed.

### 3.8. Roots and the backends

- **Per-unit root tables:** each compiled unit lists its global pointer slots (its module record, its statics holding
  heap pointers), registered at initialization as `qr_register_dicts` registers dictionaries today. An ABI change,
  in both backends and the bootstrap's. Until then, the data segment can be scanned conservatively as Boehm scans
  it; the table makes it precise and small.
- **The runtime's statics** holding heap pointers are enumerated in one place (`quest_gc_roots`): the descriptor and
  view-map caches, the dictionaries, the abstract types, the adapters, through which the metadata of §3.1 is reached.
- **The JIT:** its data regions are ambiguous roots, registered as `GC_add_roots` registers them now; its inputs'
  module records are reached through them, which is right (their addresses are in JIT code's GOT).
- **Thread-locals** (`quest_current_exception`, the handler chain) are listed roots.
- **The stack:** conservative in both backends to begin with; the arm64 backend's maps later (§3.3). The frame walk
  is the one exceptions use.

### 3.9. Large and pointer-free objects

- **Large objects** (§3.1) are their own space because moving them is never worth it and bump-allocating them wastes
  holes. Their layouts are ordinary (an array's, a string buffer's).
- **Pointer-free objects** are marked *noscan* by their layouts and skipped by the marker, and kept in blocks of
  their own (Go's noscan spans): a second allocation cursor, so that a full collection skips whole blocks and string
  buffers do not fragment pointer-bearing blocks. Part of the collector's first version (step 3), brought up with one
  cursor and measured with two on the string-heavy programs. Should evacuation be taken, the runtime's metadata gets
  a third cursor the same way (§3.1).
- **Small objects** are the common case and the design's center: a two- or three-word tuple, a closure and its
  environment, a boxed record, allocated at a rate of hundreds of millions per run in the benchmarks.

### 3.10. Latency and concurrency

With one mutator thread and heaps of tens of megabytes (the compiler's own), stop-the-world collections are short:
minor ones sub-millisecond, full ones tens of milliseconds at a gigabyte per second of marking. The design starts
there, and bounds the pauses of full collections by **incremental marking in the mutator thread** (§8, step 6), with
the pieces it needs decided now so that the earlier steps do not have to be redone. The runtime has no threads of
its own (libgc's marker threads are the only ones in a Quest process today, and they go with it), and the design
keeps it so: a marker thread is the optional last step, not the plan.

- **Incremental marking,** as OCaml's major collector, Lua, and V8 before it went concurrent: a full collection's
  mark is cut into slices, and each allocation slow path does a slice proportional to the bytes allocated since the
  last (the pace a tunable, with the slice bounded in time). A cycle starts with a short pause that scans the roots
  (the stack, registers, root tables, and the log) and ends with one that rescans the stack and drains the log;
  between them the mutator runs. An object allocated during a cycle is born marked, with its header saying *old*,
  and logged, so that a slice scans what it was built from: the stores that initialize it (`opMake*`) have no
  barrier, and without this an object built during the cycle from a pointer loaded out of an unscanned object, whose
  field is then overwritten, would be the only holder of that pointer and would never be scanned, and the pointer
  would be lost (decided 2026-11-03: initializing stores are covered while a cycle runs and cost nothing outside
  one). The cover costs nothing on the inline path: for the cycle the collector sets both cursors' limits to their
  cursors, so every allocation takes the slow path, which bumps, sets the start bit, marks, writes the header, and
  logs (a noscan object is marked and not logged); the cost is a call per allocation for the cycle's duration,
  measured in step 6, with a flag word loaded on the inline path (two instructions on every allocation, always) as
  the fallback. The slices drain the log as well as the work list, rescanning a logged object by its layout as a
  minor collection would, so the final pause's log is only what was logged since the last slice.
- **The final pause is budgeted.** Its rescan of the stack can expose unmarked objects: one loaded out of a grey
  object before a slice scanned it, whose field was then overwritten, and which the mutator kept only in a register
  or a slot. Tracing from them is unbounded in principle, so the pause has a budget: if the rescan exposes more work
  than it, the collector marks that work in further slices and rescans again, as V8 does, with a cap on the retries
  after which it finishes stop-the-world. No barrier changes for this; the alternative, shading the overwritten value
  in the slow path during a cycle, closes the window only if every store into an old object takes the slow path for
  the cycle, which would put a global back on the fast path.
- **Minor collections are suspended while a cycle runs:** the mark bitmaps are cleared at its start, so a minor
  collection could not tell old from new, and the nursery grows for the cycle's duration, which the pace bounds (a
  cycle finishes within a fixed fraction of the live heap's size in allocation); a mark state with an epoch, telling
  *old* from *marked in this cycle*, is the alternative kept in reserve should that growth show. Should evacuation be
  taken (step 7), it stays inside the final pause, with the slot log of §3.6 built by the slices and finished by the
  final rescan. The slices run where a collection may run already, at allocations, so every invariant of the
  stop-the-world collector holds between them, and a run is deterministic given its allocation sequence, which the
  suites and the goldens are.
- **The barrier serves both** (§3.5): logging an already-marked object when a pointer is stored into it is what a
  minor collection needs (old objects pointing at young ones) and what an interrupted mark needs (black objects
  written between slices). The fast path reads the header's flag bytes and takes the slow path when the object is
  old and not logged; nothing about it changes for a cycle, because objects born in one are born old, so inside a
  cycle and outside one the barrier is a load, a mask, a compare, and a branch, and the slow path logs. No fence:
  the only interleaving is at the slices.
- **What it costs:** the marking stays on the mutator's core, so throughput is a few percent below stop-the-world
  (the barrier is active for the cycle, the slices have overhead) rather than above it; a cycle takes longer in wall
  time, so there is more floating garbage and a somewhat larger heap; a long stretch that does not allocate delays
  the cycle, harmlessly, since it needs no memory either.
- **A marker thread, optionally, later** (§8, step 9): the slices move to a thread of their own, Riptide's and Go's
  way, so that marking leaves the mutator's core. Everything above stays; what the thread adds is the race between
  it marking and scanning an object and the mutator storing into it and reading its mark as not yet set, resolved by
  the marker setting the mark, fencing, then scanning, and the mutator's barrier storing, fencing, then reading
  (`dmb ish` on arm64, a locked instruction on x86-64, paid only inside the slow path of a running cycle; the
  header's two flag bytes have one writer each, §3.2, so no atomic read-modify-write is needed), plus a protocol for
  the structures both read while the mutator allocates (the object-start and mark bitmaps, the line marks, the log).
  Go keeps the incremental slices as mutator assists even with its marker threads, so nothing of step 6 is undone.
  Taken only if a measured workload shows the mutator paying for marking it could offload.
- **Not planned:** parallel marking with helper threads inside a pause, the least dangerous use of threads (the heap
  is frozen while they run) but of little use to a generational collector, whose full collections are rare and
  whose heaps are small; and concurrent evacuation (ZGC's, Shenandoah's), which needs load barriers on every pointer
  read, a cost on all the immutable data Quest reads, for latency beyond what a compiler and a REPL need.
- **Sweeping** is lazy already (§3.6); it needs no further step.

Nothing here is specific to Darwin: the reserved range is `mmap`, the fences (if step 9 is taken) the
architecture's, the frame walk the one exceptions use, which Linux would gain for precise stacks only (§3.8).

### 3.11. Why in C, and not in Quest

*Typeful Programming* §9.2 holds that a real language expresses its own run-time system, collector included, and
sketches how: an allocation-free subset (stack-allocated `Still` values, and a compiler check that a module allocates
nothing), unsound modules for the type violations a collector needs (§9.3), and a thin core of what the language
cannot say. Quest has the unsound modules, and used them once already: the JIT's loader and session are about 800
lines of unsound Quest over 260 lines of C in `quest_code.c`. The collector is nevertheless written in C, decided
2026-11-02, for reasons specific to now rather than to the idea.

**For writing it in Quest:**

- Cardelli's argument: the low-level parts in another language are checked by nothing and blamed on no one;
  `unsound` makes the trust boundary visible (`grep unsound` lists it).
- One set of definitions: the layouts the describe pass emits, the block tables, the bitmaps, and the statistics as
  Quest types shared by the compiler and the collector, rather than C structs agreeing with Quest by convention; the
  checking modes in ordinary Quest with the compiler's libraries to hand.
- The bootstrap compiles unsound modules, `Word`, and externals already, so a collector in Quest would be in stage 1
  like everything else.
- The JIT shows the shape: the algorithm in the language, the primitives in a core the size of `quest_code.c`.

**Against, today:**

- **No allocation-free subset.** Quest has neither `Still` types nor the check that a module allocates nothing. Every
  tuple, closure, record, string, and option is a heap allocation; escape analysis stack-allocates what does not
  escape (ssa.md §4.2), an optimization and not a guarantee, and a collector that allocates while it marks corrupts
  the heap it is marking. `raise` allocates, so the collector could not raise; a module's initializer allocates its
  record, so the collector's module could not be initialized by the ordinary path. What remains, integers, words,
  `var` locals, pre-allocated arrays, and calls, suffices for a marking loop and forbids every structured value, a
  work-list entry among them.
- **The core stays in C regardless:** saving the registers and walking the stack for roots, `mmap`, the fault
  handler, fences and atomics should a marker thread come, thread-locals. Cardelli's "assembly language insert". The
  question is only whether marking, sweeping, and evacuation, perhaps two thirds of the code, move to Quest.
- **Unsound Quest is C with worse tools:** `value.fetch(addr, displ)` is pointer arithmetic by hand, with no fields by
  name over raw memory, no bitfields, no count-leading-zeros, no `dmb`. §9.3's "memory mapping", a structured view of
  an unstructured area, is the facility a collector needs most, and Quest has nothing for it short of another
  extension.
- **Two compilers compile it,** and a codegen bug in either becomes heap corruption indistinguishable from a
  collector bug. The plan already changes every allocation site in both compilers; a collector in the language whose
  compilers are under change couples the two largest risks into one debugging surface.
- **The inner loops:** bit manipulation and pointer chasing, where clang's output of hand-written C is hard to match
  (the arm64 backend runs the suite at 1.46 times the C backend's time, benchmarks.md §11). The C backend would
  recover most of it, in generated C harder to read in a debugger than C someone wrote.

**Where it lands.** Cardelli's destination, the wrong order for this tree: the C collector comes first because there
is no allocation-free guarantee to write a Quest one against, and because a working C collector is the oracle a Quest
one would be validated against (the checking modes of §7 already compare one marker's result with another's). Two of
Cardelli's extensions are worth adopting on their own merits, before any port, and are candidates for tasklist.md:
the **allocation-free check** for a module, cheap given the IR after escape analysis and useful for the inlined
externals and for loops that must not allocate; and a **typed overlay on raw memory**, a `Still`-like view of an
address as a record of words, which would make `os/value` code readable (the JIT's session reads record payloads by
hand-computed offsets today). With both in the language, porting the marker, the sweeper, and the evacuator to an
unsound module over a C core of a few hundred lines is a real option, for a plan of its own once this one is done.

## 4. Where Changes Are Needed

| Component | Change |
|---|---|
| `runtime/quest_gc.c` (new) | The heap, allocation slow path, barrier slow path (interior stores included), marking, sweeping, roots, the statistics; replaces `GC_*`. With step 7: the slot log, evacuation, hash words, the hold count |
| `runtime/quest_runtime.h` | `quest_alloc(size, layout)` returning past the header; barrier and root macros; layout structs. With step 7: `quest_alloc_pinned` for metadata |
| `runtime/quest_runtime.c` | Its ninety allocations named by layout; its pointer stores into existing objects audited and barriered (`quest_proxy_store` among them); roots enumerated in `quest_gc_roots`. With step 7: `quest_identity_hash` by hash state, metadata allocated pinned |
| `runtime/quest_serialization.c` | With step 7: evacuation held while the sharing table is live |
| `runtime/quest_code.c`, `jit/loader` | Data regions as ambiguous roots through the new API |
| `ir/describe` (both compilers) | Layouts per allocation site, emitted as static data with the descriptors |
| `ir/represent`, `ir/lower` (both) | Allocation operations carry their layout; `val` words marked ambiguous in it; stores marked mutating, and interior where they are |
| `codegen/c/printer`, bootstrap printer | Allocation with header, inline bump fast path (from the header file), barrier on mutating stores (a call for interior ones), root table per unit |
| `codegen/arm64/select`, `ssa/build` | Inline bump allocation, barrier sequence, root table; later stack maps from `frameSlots` |
| `ssa/escape` | Recognize the new allocation form |
| `ir/verify`, `ssa/verify` | Every store of a `ptr` or `val` word into the heap is a barriered form |
| `build`, `tools/release`, docs | No libgc; `--nogc` retired or redefined; runtime-design.md §3, c-representation.md §9, arm64.md §3.13 rewritten |
| `tools/perf/gcstats.py`, `retention.py` | Read the new collector's statistics |

The interpreters need nothing: they are compiled Quest, and their values are ordinary objects.

## 5. What Changes for Programs

Nothing in the language. Programs see: faster allocation; memory per object up by a word and down by Boehm's
rounding; `identityHash` unchanged (the address, and stable across moves should evacuation be taken); collections
at the same places (allocations). Programs that held pointers in ways Boehm tolerated but the design does not are
none: no Quest program can form a pointer one past an array's end as a loop bound (arm64.md §3.13 forbids the
backends to make one too), and where clang forms one from the C backends' output or in the runtime, the
conservative scan takes a word at an object's end as that object's (§3.3), as Boehm does.

## 6. Decisions

Decided 2026-11-02, with 11 to 14 added and 2, 7, 8 revised after the reviews of 2026-11-03; the first four shape
everything else.

1. **Precise heap, conservative stack, pinning for the ambiguous** (§3.3), rather than fully precise (which needs
   stack maps in both backends, a shadow stack for the C one, and layouts for every generic allocation site before
   anything works) or fully conservative (Boehm again). *Recommended:* it is the only one of the three that can be
   built in steps, each correct, and conservative Immix measured the cost at about one percent.
2. **Immix mark-region with sticky mark bits; evacuation designed, and taken only on a measurement** (§3.5, §3.6;
   revised 2026-11-03 from "opportunistic evacuation" as part of the collector), rather than a copying nursery with
   a mark-compact old generation (OCaml, MLton, V8). *Recommended:* copying needs every reference into the nursery
   rewritable, which decision 1 cannot promise; sticky Immix bump-allocates without moving, recovers space by the
   line, and is where the throughput is; moving is where the difficulty is (the slot log, forwarding, the hash
   states, pinning that matters), and the Immix paper found it worth a few percent on average.
3. **A header word at a negative offset, holding a layout pointer and flags** (§3.2), rather than a pointer bitmap
   per span set at allocation (Go) or headers inside the structs. The structs, the offsets, and the bootstrap's
   generated C stay as they are; logging and the *old* hint need bits somewhere, and forwarding, pinning, and the
   hash state are reserved beside them; and a layout pointer is 8 bytes either way. Objects stay 8-byte aligned,
   which is all the backends' loads need (§3.2). The mark bit is the exception: it lives in a side bitmap, and the
   header keeps the byte the barrier reads (decision 12).
4. **One mutator, stop-the-world first, then incremental marking in the mutator thread; a marker thread optional
   and last** (§3.10, §8 steps 6 and 9). Throughput is the goal the benchmarks set, so the collector is built and
   measured stop-the-world; incremental marking bounds the pauses without a thread, and is designed in now (the
   barrier, objects born old and logged during a cycle, the pacing, the budgeted final pause) so that nothing
   earlier is built in its way. The runtime stays single-threaded unless a measurement says the mutator is paying
   for marking a thread could take; parallel marking inside a pause is not planned (revised 2026-11-02, from
   "parallel, then concurrent").
5. **The barrier:** object logging through the header (§3.5) rather than card marking. *Recommended* for its
   precision (logged objects are scanned by layout, no card walking) and its reuse for incremental marking; card
   marking for large arrays is a possible addition. Reaffirmed 2026-11-03 against card marking, which would free the
   barrier from reading the header (and so from the interior-store case) but dirties cards on stores into young
   objects, the common mutable stores, and rescans them. Taken up in part 2026-11-04 (step 4): the slot's barrier
   (an array's element, a record's field, a location) marks a card, the object's logs as before, after the
   compiler's build showed its tables rescanned whole at every minor collection (§3.5).
6. **Large objects from 8 KB, in their own space, never moved; pointer-free objects in their own blocks** (§3.9),
   both in the collector's first version; both thresholds are parameters to measure.
7. **Identity hash stays the address; the three-state scheme with a prepended word is designed and reserved for
   evacuation** (§3.7; revised 2026-11-03 with decision 2), interior objects hashing by their allocation's old base
   plus their offset. The alternative, a hash field in every object, costs a word on every object for the few that
   are ever hashed.
8. **Runtime metadata stays in the ordinary heap, reached from listed roots** (§3.1, §3.8; revised 2026-11-03 from
   an immortal space, which existed to keep address-keyed metadata out of the moving question). Should evacuation be
   taken, metadata is allocated pinned at birth into blocks of its own, simpler than a space of its own with the
   root list and the invariant that space needed.
9. **Both compilers emit layouts, barriers, and root tables.** The runtime is shared, so the bootstrap's C must be
   correct under the new collector; the inline fast path and stack maps are self-hosted only (optimizations, by
   the two-compilers policy). *Recommended;* there is no version of this in which the bootstrap's objects lack
   headers.
10. **libgc goes.** No fallback collector is kept: a second allocator behind `quest_alloc` would keep every
    representation decision hostage to Boehm's. `--nogc` is retired, or becomes "never collect". *Recommended.*
11. **Evacuation, when taken, runs after marking and never during it, through a bounded slot log** (§3.6; added
    2026-11-03). Moving as the trace goes, Immix's way, is unsound with ambiguous words inside the heap; two traces
    are the sound alternative, at twice the marking cost of a defragmenting collection.
12. **Marks in a side bitmap; the header's flags in two bytes with one writer each** (§3.2; added 2026-11-03). A
    full collection clears a block's marks at once instead of touching every object, a minor collection's tests of
    old referents stay in a hot structure, and a marker thread would need no atomics.
13. **Generic layouts after evacuation, on its measurement** (step 8; added 2026-11-03, revising the order of
    2026-11-02, which had them second; confirmed). They are an ABI change whose benefit, less pinning, nothing can
    measure before evacuation exists; `layouts` counts the ambiguous words from step 1 on.
14. **Only live objects validate** (§3.6; added 2026-11-03): the object-start bitmap is intersected with the mark
    bitmap at the end of every collection, so that the marker may trust the precise words of whatever an ambiguous
    word reaches.

## 7. Risks, and the Checking Modes That Catch Them

The collector's failures are silent and late: a wrong layout or a missed barrier corrupts memory that is read long
after. So the runtime has checking modes, chosen by `QUEST_GC_CHECK`, slow but exhaustive, under which any program,
the test suites, and the compiler's own build can run; tools/check runs the suites under them for a change that
touches layouts, barriers, roots, or the collector (testing.md §4.1 lists which).

| Mode | What it does | Catches |
|---|---|---|
| `layouts` | After every collection, walks every live allocation (start bits intersected with marks) by its layout: each precise pointer word is null, outside the heap (static data, code), or points at or into a live allocation; each ambiguous word is counted; sizes agree with the lines marked. On Boehm (step 1) the check is against `GC_base` after a forced collection, every 64 MB allocated (`QUEST_GC_CHECK_INTERVAL`; at least four times the heap's size, so that the walks stay a fraction of the run) and at exit, and a pointer word to nothing allocated is counted (`dangling`) rather than fatal, since Boehm resurrects a dead object that a stale stack word points at with the words it died with; `report` prints the counts per layout | A layout that lies about a word, a size, or a length field |
| `barriers` | At every minor collection, before the log is used, scans the whole old generation by layouts for pointers into the nursery, and reports any in an object that is not logged | A mutating store without a barrier, in generated code or in the runtime's C, an interior store among them |
| `roots` | At every collection, scans the data segments and thread-locals conservatively and reports a heap pointer that no root table or listed root covers | A global pointer slot missing from a unit's root table or `quest_gc_roots` |
| `poison` | Every reclaimed line and freed large object is filled with a pattern that is never a valid pointer (0x5A bytes) | A use after reclamation, a dead object resurrected |
| `collect` | Forces the collections the other modes would, checking nothing: every `QUEST_GC_CHECK_INTERVAL` bytes, or every `QUEST_GC_COLLECT_EVERY` allocations, with `QUEST_GC_COLLECT_TRAP=k` stopping in `quest_gc_trap` before the kth, for tools/perf/retention.py | Nothing; it makes builds of one program collect at the same points |
| `allocations` | Counts every allocation and its bytes by the allocating function and its caller, written at exit to `$QUEST_ALLOCATIONS_OUT`, for benchmarks/mlton/allocations.py | Nothing; it says who allocates |
| `incremental` (step 6) | Makes every slice as small as it can be (one object), and at the end of each cycle marks the same heap again stop-the-world and compares the marks | A barrier that let an object escape the cycle, a slice that broke an invariant |
| `stress` | Collects before every allocation (`QUEST_GC_STRESS=n`: every nth), minor collections with each sixteenth full, running the other modes' checks at each. The count between collections doubles each time the collections at the current count have walked `QUEST_GC_STRESS_BUDGET` megabytes of heap (256; a collection counts as the heap in use), so a small program is checked at every allocation and the compiler at its first few hundred and then at a thinning sample. The collections fall by count, so a failure repeats; a failing check gives its collection's number, and `QUEST_GC_TRAP=k` calls `quest_gc_trap` before the kth for a debugger. With step 7, each full collection also takes every block as a candidate with the slot log unbounded, so every object that may move does, and the vacated memory is poisoned and, in large runs, unmapped | A store without a barrier, a barrier with an allocation between it and its store, an initializing store after a collection, a root left out (a global now, a stack map's slot with step 5), each within a few allocations of the fault, in generated code, the runtime, serialization, and the JIT; with step 7, a stale address kept across an allocation |
| `sites` | Keeps, by each object's address, the three functions above its allocation (from the frame records, in a table outside the heap), and a failing check names them for its object and for the object its word points at | Nothing; it says which code made the objects a report is about |
| `concurrent` (step 9, if taken) | As `incremental`, with the marker thread forced to yield between objects | A barrier race, a lost mark |

Modes combine (`QUEST_GC_CHECK=layouts,poison`), and `stress` with `barriers`, `roots`, and `poison` is the one that
finds the most: tools/check runs the compiled tests under it, with `sites`, before its suites (testing.md §4.1).
`QUEST_GC_CHECK_CHILDREN` gives the modes of the programs a program runs, in place of its own, so that a compiler runs
under the plain checks and the test it builds and runs under `stress`. Under any mode every allocation takes the slow
path, which counts it; `QUEST_GC_STATS=1` (a summary at exit) and `each` (a line per collection too) report what the
collector did, under a mode or not. The checks are in the runtime, so the bootstrap's C and the JIT's code are checked
by the same code as the self-hosted backends', and the interpreters' transcripts can run under them too.

The risks themselves:

- **A layout that lies** (a pointer word described as scalar) is a leak at worst while nothing moves, as under
  Boehm, and memory corruption under evacuation. Step 1 builds `layouts` on Boehm, and `stress` is the first thing
  step 7 runs.
- **The barrier missed** on a store the IR did not classify, an interior store that found the wrong header, or one
  of the runtime's few pointer stores into an existing object, loses a young object. `barriers` finds it by
  exhaustion, and the IR and SSA verifiers reject a store of a `ptr` or `val` word into heap memory that is not one
  of the barriered forms.
- **A dead object resurrected** by an ambiguous word, its stale precise words followed into reused memory, is the
  failure decision 14 prevents; `poison` makes it loud if the intersection is ever skipped.
- **Fragmentation** that line recycling does not recover would leave the heap larger than its live data; steps 3
  and 4 measure live lines against live bytes, and step 7 is the answer if they show it. **Pinning in generic-heavy
  programs** (the compiler) would then leave evacuation with little to do; stack maps (step 5) and generic layouts
  (step 8) are in the plan for this, and the collector's statistics report the pinned fraction.
- **Linux.** Nothing in the design is Darwin's (§3.10), and nothing in the plan may make it so; the C backend's
  Linux build keeps conservative stacks. There is no Linux machine to test on, so the plan keeps the Linux build
  compiling, by inspection and by the conditionals the runtime has, and leaves running it until one exists.
- **Memory growth** from headers in tuple-heavy programs; measured in step 1, on Boehm, before the collector exists.
- **An interrupted mark** that misses an object is a lost object, found late; `incremental` finds it at the end of
  the cycle it happened in, by comparing with a stop-the-world mark. Should step 9 be taken, concurrency bugs are
  the hardest of all to see; `concurrent` finds some by exhaustion, and the marker's protocol is written down
  before it is coded.

## 8. Steps

Each correct on its own, each measured, each ending with tools/check passing (under the checking modes that apply)
and its documentation, in the order that retires the risks first. Steps 1 to 6 are the collector; 7 and 8 are
taken on what 4 and 7 measure; 9 is optional.

1. **Layouts and headers, on Boehm.** Both compilers' describe passes emit layouts; `quest_alloc(size, layout)` writes
   the header before the object and returns past it; the runtime's allocations name theirs; `QUEST_GC_CHECK=layouts`
   against `GC_base`. *Done when:* every suite passes with `layouts` on through every backend and both compilers, and
   the heap growth from headers is recorded here, translated from Boehm's rounding to the design's (§3.2).
   *Done 2026-11-03.* The layouts are computed from shapes by `codegen/objectLayout` (the bootstrap's
   `quest/codegen/objectlayout.py`), registered per unit by both C printers and the SSA's builder, and laid out as
   static data (`quest_layout_<tag>`, its kinds `qlk_<tag>`); the runtime's own are in `runtime/quest_gc.c`, with
   the `layouts` and `report` modes. Three forms of layout were needed, not two: a *sized* one for the allocations
   whose size is known only at the call and recorded nowhere else (string buffers, the runtime's tables), which
   record their byte count in the word before the header. The runtime's generic copies of values (`quest_convert`'s,
   serialization's) and its tables of mixed words take a layout of ambiguous words for now. What the headers cost,
   measured by the runtime's counters (`QUEST_GC_CHECK=report`) over the allocation-heavy MLton benchmarks at scale
   0.25, with the design's growth as 8 bytes per object (16 per sized one) and Boehm's as its 16-byte granules
   with the header against without:

   | Benchmark | Objects (M) | Bytes without headers (GB) | Average object (bytes) | Design | Boehm |
   |---|--:|--:|--:|--:|--:|
   | tailmerge | 4,916 | 98.3 | 20.0 | +40% | +33% |
   | ratio-regions | 811 | 26.2 | 32.3 | +25% | +30% |
   | logic | 2,213 | 43.3 | 19.6 | +41% | +33% |
   | zebra | 1,376 | 24.4 | 17.7 | +45% | +63% |
   | hamlet | 806 | 24.8 | 30.8 | +26% | +31% |
   | barnes-hut | 1,253 | 25.9 | 20.7 | +39% | +26% |
   | knuth-bendix | 3,645 | 54.8 | 15.0 | +64% | +43% |
   | boyer | 1,687 | 32.4 | 19.2 | +44% | +37% |
   | imp-for | 1,138 | 9.1 | 8.0 | +100% | +0% |
   | count-graphs | 1,249 | 26.2 | 21.0 | +38% | +53% |
   | wc-scanStream | 16,396 | 336.1 | 20.5 | +39% | +33% |
   | all eleven | 35,489 | 701.5 | 19.8 | +41% | +34% |
   | the compiler, on `ir/lower.mod.quest` | 127 | 5.9 | 46.7 | +20% | +13% |

   The benchmarks' objects are small (a cons cell is 16 bytes, two words), so the header is a third to half again
   on them, where §3.2's estimate said "half again on the commonest object"; the compiler's are larger, and its
   growth a fifth. Under Boehm the growth is what the granules make of it, between nothing (imp-for's 8-byte
   objects were already rounded to 16) and 63 percent (zebra's 24-byte objects become 32 after rounding to 48).
   Two things learned for the later steps: Boehm enumerates its own internal objects as reachable, without
   headers, which the check skips and counts as foreign; and a stale stack word resurrects a dead object with the
   words it died with, so a pointer to a freed object is not proof of a lying layout on Boehm (one in fifty
   million words on the compiler's own build), which is why decision 14 matters to the collector of step 3. One
   failure remains unexplained: the backends' suite once reported an array (`QArray(QVal)`, at the start of a
   block) whose element count its allocation could not hold, in the arm64 build of `language/option_identity`,
   which neither the runner's rerun nor sixty runs of the binary under the check at varied intervals repeated;
   the check now prints the object's first words, for the next time.
2. **Barriers and root tables, logging only.** The IR marks mutating stores of `ptr` and `val` words, and the interior
   forms among them (§3.5), and its verifier enforces the forms; the runtime's pointer stores into existing objects
   are audited and marked; both backends emit the barrier calls (to a runtime stub that counts, by form) and the
   per-unit root tables; `roots` checks the tables against a conservative scan. *Done when:* the suites pass under
   `layouts,roots`, and the barrier counts per benchmark, interior stores apart, are recorded.
   *Done 2026-11-04.* No IR change was needed: the IR's five store statements are the only stores of words into
   memory, so the backends barrier a store by its form and the stored word's kind (`holdsPointer`), with
   `quest_barrier(obj)` where the site has the object (a tuple's component, an array's element, a closure
   environment filled after a `let rec`'s body) and `quest_barrier_slot(slot)` where it has only the slot (a
   record's field through its payload, a `var` or `out` location, a view's slot). The runtime's own stores were
   audited by a rule rather than a list: a pointer store into an object needs no barrier only when nothing can
   have allocated since the object was made, so the runtime allocates an object's parts before the object where
   it can (strings and their buffers, descriptors and their metadata) and barriers the rest (proxy caches, the
   string builder's chunks, the instantiation and view-map caches, serialization's tables as they are filled).
   The root tables list each unit's globals that may hold a pointer and its module records, ended by a null slot;
   the runtime lists its own statics and thread-locals, and `roots` scans the executable's data segment
   (`getsegmentdata` on Darwin, `__data_start` to `_end` on Linux) for a heap pointer nothing covers, naming the
   symbol. The JIT never unmaps a unit's data, so its tables stay registered. The barriers, as counting stubs, on
   the allocation-heavy MLton benchmarks at scale 0.25 (`QUEST_GC_CHECK=report`): every one was on an object; no
   benchmark stores a pointer through a slot, and the compiler's own build makes 160 million object barriers
   compiling `ir/lower.mod.quest` and none through a slot.

   | Benchmark | Barriers (M) | Objects allocated (M) | Barriers per 100 allocations |
   |---|--:|--:|--:|
   | tailmerge | 0.006 | 4,916 | 0 |
   | ratio-regions | 340 | 811 | 42 |
   | logic | 248 | 2,213 | 11 |
   | zebra | 140 | 1,376 | 10 |
   | hamlet | 72 | 806 | 9 |
   | barnes-hut | 11 | 1,253 | 1 |
   | knuth-bendix | 798 | 3,645 | 22 |
   | boyer | 2.9 | 1,687 | 0.2 |
   | imp-for | 0 | 1,138 | 0 |
   | count-graphs | 4.4 | 1,249 | 0.4 |
   | wc-scanStream | 2.0 | 16,396 | 0 |
   | the compiler, on `ir/lower.mod.quest` | 160 | 127 | 126 |

   So the barrier's fast path matters to the compiler and to the array-heavy benchmarks, and the generational
   collector of step 4 will log few objects on the rest.
3. **The collector, stop-the-world, non-generational.** `quest_gc.c`: the heap of §3.1, marking by layouts (marks in
   the side bitmap, the header's *old* byte written by the marker alone, §3.2), the intersection of start bits with
   marks (§3.6), lazy line sweeping, the large object space, noscan blocks (§3.9, brought up with one cursor and
   measured with two), the statistics (`tools/perf/gcstats.py` reads them; live lines against live bytes among
   them); libgc out of the build; inline allocation in both self-hosted backends, the object-start bit included
   (§3.4); `poison`. *Done when:* the suites pass on it under `layouts,roots,poison`, the self-hosting fixed point
   holds, the inline allocation's cost against libgc's call is recorded, and the MLton suite is no slower than on
   Boehm (expected: much faster, from allocation alone).
   *Done 2026-11-04.* `runtime/quest_gc.c` is the collector: one reserved range (64 GB, `QUEST_GC_RESERVE` gigabytes,
   halved until the system grants it; committed as touched) of 32 KB blocks of 128-byte lines, with a block table, a
   mark byte per line, and two bitmaps with a bit per 8 bytes (the objects' starts, set by every allocation, and the
   marks) beside it. The header's `quest_alloc` bumps the cursor of the object's space through the current hole and sets
   the start bit; `quest_gc_alloc_slow` takes the next hole of the current block, a recyclable block's, or a free
   block's (zeroing each hole as it is entered, unless the block is fresh), medium objects (over a line) from an
   overflow cursor of fresh blocks, and large ones (8 KB and up) from runs of blocks; it collects when the blocks in use
   reach their target (twice those in use after the last collection, at least `QUEST_GC_MIN_HEAP` megabytes, 64 by
   default). A collection clears the marks and line marks of the blocks in use, marks from the root tables, the
   runtime's listed roots, the JIT's regions, and the stack (registers spilled by `setjmp`), setting each marked
   object's lines, then intersects the start bits with the marks, frees dead large runs, and classifies each block. The
   SSA's backends select the same sequence inline (`ssa/allocations`, ssa.md §4.1): arm64 and the JIT, which cannot get
   it from the header, and ssac, whose printer calls every runtime function out of line. Learned: C compilers keep the
   address an allocation returned *before* the header was skipped (clang folds the `+ 8` into every field's offset), so
   an ambiguous word at an object's header, or at a sized object's byte count, must mark that object, as one at its end
   must (§3.3 said only the latter). Statistics: `QUEST_GC_STATS=1` (a summary at exit) and `each` (a line per
   collection); the modes gained `poison` (reclaimed lines filled with 0x5A), `collect` (forced collections only: every
   `QUEST_GC_CHECK_INTERVAL` bytes, or every `QUEST_GC_COLLECT_EVERY` allocations with `QUEST_GC_COLLECT_TRAP` for a
   debugger, which `tools/perf/retention.py` uses in place of its Boehm shim), and `allocations` (counts by site, for
   `benchmarks/mlton/allocations.py`, in place of its interposer); under any mode every allocation takes the slow path,
   which counts it. `--nogc` is the collector never collecting. libgc is gone from both runners, and from the release's
   prerequisites. ABI 66.
   Measured ([benchmarks.md](benchmarks.md) §16, on a loaded machine, wall and processor time both, to be retaken idle
   after step 4): the MLton suite at scale 0.25 against §13's Boehm times takes 0.79 of the time through C (0.69 by
   processor time), 0.89 through ssac (0.69), and 0.88 through arm64 (0.82), the allocation-heavy programs halving
   (wc-scanStream 0.39, tensor 0.40, barnes-hut 0.48, logic 0.49 on C), and against MLton the suite goes from 0.69 to
   0.54 of its time on C, 0.55 to 0.49 on ssac, and 0.72 to 0.63 on arm64. The inline sequence against the call of the
   slow path, on arm64, is 0.99 over the suite by processor time and 0.77 to 0.88 on the allocation-heavy programs;
   ssac's printer had been calling `quest_alloc` out of line, so the pass runs before it too: wc-scanStream through ssac
   takes 0.70 of its time with the sequence, logic 0.93. Two programs lost: imp-for (1.85 on C), a billion one-word
   boxes, and matrix-multiply (1.39 on C), which hardly allocates; their inner loops are the same instructions whatever
   the allocation sequence, and their times swing by 40 percent with where clang places `main`'s loops (matrix-multiply
   5.1 s without the start bit's five instructions, below Boehm's 5.7), so the ratios measure code placement, and the
   sequence's own cost against `GC_malloc`'s call is at most 1.6 ns per allocation by imp-for's best placement. The
   compiler's own build (`-j 8`) takes 0.83 of its wall time and 0.77 of its processor time, and three times the memory:
   the trigger counts a block with one live line as in use and doubles the blocks in use, which after the compiler's
   collections are 3.2 times its live lines and 6.6 times its live bytes (live lines against live bytes, step 7's
   number, is 2.1), and one process building the driver reaches 9.9 GB of blocks for 848 MB live, with 23 collections
   pausing 5.0 s in all and 994 ms at the longest. Step 4's minor collections change both numbers, and its trigger
   should count a recyclable block's holes as free.
4. **Generations.** Sticky marks, the barrier live (interior stores through the slow path), minor collections,
   `barriers`. *Done when:* the suites pass under `barriers`, the suite's and the driver's own build times are
   recorded against step 3, and fragmentation (live lines against live bytes after the compiler's build and after a
   long REPL session) is recorded for step 7's decision.
   *Done 2026-11-05.* The mark bits are sticky (§3.5): a full collection clears them, a minor one keeps them, so that
   marking from the roots, the log, and the dirty cards stops at every old object and visits the young ones alone, those
   in the holes allocated into since the last collection. Their blocks are listed as their holes are entered (`young` in
   the block table), and a minor collection sweeps those alone: only live objects validate there, the live lines are
   recounted, a young block or large run with nothing live is freed, and the old recyclable blocks not yet allocated
   into keep their holes. A minor collection runs every nursery of blocks taken (`QUEST_GC_NURSERY`, 64 MB by default; 0
   leaves full collections alone), a full one when the blocks in use reach their target, or when the minor one leaves
   them there; the nursery adapts to what survives (§3.6). The barrier is live in both forms: `quest_barrier`, inline in
   `quest_runtime.h`, loads the header word and calls `quest_barrier_log` when the collector's *old* byte is set and the
   mutator's *logged* byte (bit 48) is not, and a minor collection scans each logged object whole; `quest_barrier_slot`,
   inline too, for an array's element, a record's field, a location, and a view's slot, reads the slot's line mark
   (unmarked: a young object's, nothing to do) and its card's byte (512-byte cards, a byte each beside the heap), and
   `quest_barrier_card` marks and lists a clean one, which the minor collection scans by the layouts of the old objects
   in it. Learned, first: a case binder's tuple is an option's payload, which shares the option's allocation
   (c-representation.md §9), so the word before it is the option's tag, not a header, and the object barrier on it
   logged nothing; `barriers` found this on the compiler's first build under it (an `opCall`'s `args` replaced by
   `ir/walk`), and the barrier now takes a word under 65536 for a tag and the header one word further back, logging the
   option, so §3.5's "interior stores through the slow path" needed no IR marking. Second, the compiler's build logged
   its tables (arrays of a million entries) at every minor collection and rescanned them whole, 17.5 s of 20.5 s of
   minor pauses in one process, which is what the cards are for; the first cards scanned every object in a dirty card,
   young ones too, and so kept what dead young vectors pointed at, survival rising to 42 percent and the heap to 8.9 GB,
   until the scan was confined to old objects; and the barrier then marked a card for every store into a young vector,
   22,000 cards a minor collection, until the line mark's test. Third, the runtime's startup allocated the argument
   array and then its strings, with no barrier between, which a checking mode's early collection caught in two tests;
   the strings come first now. Fourth, from the check's first full run: the printers allocate a string literal where it
   is used, inside the store that initializes a record's field or an array's element, after the container, and the SSA's
   builder lowers an aggregate's component atoms in its store loop likewise, so a minor collection during the literal's
   allocation aged the container and the store had no barrier (three compiled tests); the printers and the builder log
   the object through the barrier after such stores (`tests/source/language/aggregate_literals.quest` makes a hundred
   thousand such aggregates; the rule's final form is under Eighth). Fifth, the JIT: a session stores the program's
   arguments into the driver's `system` record through `value.store`, the raw word store, which now marks the slot's
   card; and the loader's code and data regions, two anonymous mappings, were more than 4 GB apart (adrp's reach) in
   three runs of a hundred: the collector's tables, which the system put just above the binary, pushed the code region
   up under Darwin's shared cache, and the data region past it, 7 GB away. `quest_code_reserve` asks for the first just
   above the runtime's text and each later one after the last, and again from the first address when one lands out of
   reach, and the collector maps its tables after its heap; of 400 runs then, every region was where it was asked for.
   Sixth, the barrier after the stores was a call with the object as its argument, which the SSA's escape pass took for
   an escape: regenerating the SSA goldens showed fifteen tests losing stack slots (`auto_types` 38 of its 54 slot
   uses), and the proxy folds with them; a barrier call keeps no pointer, so the pass now passes over it, and drops the
   barriers of an allocation it makes a slot (ssa.md §4.2), and the barriers are declared as reading memory rather than
   writing it, since they write only the header word, the log, and the cards, none of which compiled code loads, so
   value numbering keeps its loads across them. Seventh, the heap's address: the system placed the reserve at
   0x70_0000_0000, where the compiler's packed source locations (a file's number above bit 32) are addresses once the
   heap passes 4 GB, and the whole-program build, the only one that large, stored one (file 113, offset 2752) in a
   generic `some`, an ambiguous word, that equaled a young object's address, which `barriers` reported as a store
   without a barrier (a debugger's watchpoint on the word showed its one store, before the object was old); the reserve
   is now asked for at 2^46, where such integers do not reach, which also spares the objects they would have kept alive.
   Eighth, what three passing runs of the whole check had not reached. The check's collections are megabytes apart, so a
   store that needs two of them a few instructions apart, or one inside a particular call, is found only by chance; the
   `stress` mode (§7; a collection before every allocation, thinning as the heap grows) was built before the commit and
   failed 30 of the bootstrap's 275 compiled tests and 17 of arm64's on its first runs, each within a few hundred
   collections, and `sites` named the allocating functions. What it found: (a) an aggregate with two literals: the
   barrier after the stores came one collection late, the first literal's store unlogged when the second literal's
   allocation collected, so the object is now logged before every call after the first as well as at the end
   (`begin_init`, `beginInit`; the builder counts only the calls that may collect); (b) every mutating store had its
   barrier before it, and the stored value computed between the two (`r.name := "literal"` in the compiler's own
   `newUnit` records, a `var` parameter assigned a call's result, a slot whose value is boxed): the barrier now follows
   the store in both printers and the builder; (c) the runtime's C had the same two shapes throughout its descriptor and
   serialization code (`out->name = quest_inst_name(...)` after `quest_barrier(out)`, a type graph's labels, a record
   dictionary's stored types, a viewed copy's converted components), fixed by hand where values are converted, and by
   holding collections off (`quest_gc_hold`, §3.5) around a descriptor's instantiation and a dynamic value's reading and
   writing; (d) the fix to the startup's arguments above had parked their strings in `malloc`ed memory, which no
   collection scans, as a directory's listing always had (under Boehm too): both hold collections off; (e) a
   record-dictionary entry of three words took one slot barrier and lay across two cards; (f) the serializer's witness
   stack, a global array, was in no root list (`quest_serialization_roots`); (g) the `allocations` mode's frame walk was
   one frame off wherever the compiler had inlined the check's tick, which is now kept out of line. tools/check runs the
   compiled tests under `stress` first, and its suites only if they pass (testing.md §4.1): arm64, the C backend, the
   JIT, and the bootstrap's C, 1,111 runs in about ten minutes beside another session's check, with the tests alone
   under it where a compiler builds and runs them (`QUEST_GC_CHECK_CHILDREN`; the compiler under `stress` for every test
   took the tier to 43 minutes). The `barriers` check reports an old unlogged object's pointer at a young object in a
   clean card, and an ambiguous word only at a young object's start or payload, since a packed integer (a location's)
   fell inside one. `layouts` after a minor collection walks the young blocks alone; under a checking mode the nursery
   is at least a quarter of the heap. tools/check sets `layouts,roots,poison,barriers`. The statistics count minor
   collections, their pauses, what survived them, the objects logged and the cards marked, with each minor collection's
   phases under `each` (`gcstats.py` reads the lines); `report` adds the objects and bytes logged per layout. The SSA's
   backends still call both barriers out of line; no profile here shows the calls. Ninth, the nursery's size. The
   suite's first taking, with the 8 MB the design gave the nursery, lost 3 percent to step 3 through C (the geometric
   mean; 10 to 17 percent on the programs that allocate most), and the compiler's build 5 percent, for a third of step
   3's memory. The loss is the minor collections', not the barriers': with them off the same binaries run about as fast
   as step 3's. Nor is it their pauses, which on barnes-hut come to the same third of a second either way: it is where
   allocation goes after them. A minor collection leaves its survivors where they are, one or two percent of the
   nursery's bytes, small objects scattered over nearly every block it filled, and their marks are sticky until the next
   full collection, so allocation, which takes a block's holes before a free block, hops between ever smaller holes:
   barnes-hut's 34 GB went into 32.7 million holes, 1.0 KB each on average, against 2.1 million of 16 KB with full
   collections alone; the slow path took four times the samples, and the program's own two hot functions a tenth more. A
   larger nursery dilutes this (2.7 KB a hole at 64 MB), and the ten programs that lost most gain steadily with it (0.97
   of their time at 16 MB, 0.95 at 32, 0.93 at 64, 0.91 with no minor collections; benchmarks.md §17.2), while the
   compiler's build at 64 MB is as fast as with none, in 1.39 GB against 3.66. So the default is 64 MB, the heap's least
   size: a heap whose blocks in use stay under half of that has full collections alone, which for so small a heap are as
   cheap. This is evidence for step 7 that the fragmentation ratio below does not show: the lines the survivors hold are
   few, but they are everywhere, and only moving the young survivors would give the blocks back whole. Tenth, ssac's
   column: its two worst programs against step 3 (model-elimination 1.38, psdes-random 1.26) are not generations' doing
   but the inline allocation sequence's, which ssac's suite has for the first time here: with allocations left as calls
   the same programs take 26.8 s against 37.2 and 14.0 against 19.3, and over the whole suite the sequence against the
   calls is 1.00, from 0.69 (wc-scanStream) to 1.39, so ssac keeps it: it is the path arm64 takes, which ssac is there
   to test, and the swings are clang's. Measured ([benchmarks.md](benchmarks.md) §17): through C the suite is level with
   step 3 (geometric mean 0.99 by wall time and 0.98 by processor time), through ssac 0.95 and 0.96, and through arm64
   0.93 and 0.95, which is 0.54, 0.47, and 0.59 of MLton's time; the compiler's own build takes 22.6 s against 23.3
   (0.97) in 1.39 GB against 3.77 (0.37), and in one process has 271 minor collections pausing 2.3 s in all and 27 ms at
   the longest, and 9 full ones pausing 1.75 s in all and 876 ms at the longest, which is step 6's to shorten.
   Fragmentation, for step 7: live lines against live bytes is 2.1 (1,067 MB in 2,259 MB of lines) after the compiler's
   build (-j 1) and 2.2 after a REPL session of the transcripts of `tests/repl` replayed twenty times (4.4 GB allocated;
   22 minor collections pausing 38 ms in all and 8 full ones pausing 15 ms, 3.4 ms the longest of either; 13.1 MB live
   in 28.5 MB of lines).
5. **arm64 stack maps** from `codegen.frameSlots` (arm64.md §3.13): at each call, the frame slots holding live
   pointers and the callee-saved registers holding them, with where the function saves each such register, emitted
   as a table per function the collector finds from the return address. The frame walk scans a mapped frame's
   pointer slots precisely and its memory-class slots conservatively; finds a register's value in the youngest frame
   that saved it, precisely when every frame between is mapped and as an ambiguous word otherwise (§3.3); and scans
   any unmapped frame (a C-built unit's, the runtime's) conservatively. The JIT's units carry maps the same way. This
   ends the dead-slot retention of arm64-performance-review.md §3.2 for mapped frames, which is its gain whether or
   not anything ever moves. Nothing of the kind for code compiled through C. *Done when:* the suites pass through
   the arm64 backend and the JIT under `layouts,roots,barriers`, and the live data on the compiler's build is
   recorded against step 4.
6. **Incremental marking** (§3.10): the initial pause; every allocation through the slow path for the cycle, born old
   and logged; the slices paced by allocation and draining the log; minor collections suspended for the cycle; the
   budgeted final pause with its retries; `incremental`. *Done when:* the suites pass under `incremental,poison`, and
   the pauses (the final pause's worst case and its retries among them), the throughput, the cost of the slow-path
   allocation during a cycle (against the flag-word fallback, §3.10), and the nursery's growth during a cycle on the
   compiler's build and the REPL's inputs are recorded against step 5, with the pace and slice bound that were
   chosen.
7. **Evacuation and the hash, taken on step 4's measurement** (§3.6, §3.7): candidates chosen before marking, the
   slot log and its bound, copying and rewriting after marking, the old copies' bits and lines cleared; metadata
   allocated pinned at birth into blocks of its own; the three hash states, interior objects included;
   serialization holding evacuation off; evacuation inside the final pause of a cycle; `stress`. *Done when:* the
   suites, the transcripts, and the driver's build pass under `stress,barriers,incremental`, `identityHash` is
   stable under a test that forces moves, and fragmentation before and after, the slot log's size, and the pinned
   fraction after long compiler runs are recorded, the last by what pins it (the stack, the JIT's data, ambiguous
   words in the heap).
8. **Layouts for generic allocation sites** (§3.3), in both compilers, taken when step 7's pinned fraction on the
   compiler's build shows evacuation held back by ambiguous words in the heap (§3.3 expects it will be; the step
   follows the measurement because it changes the ABI): the analysis that gives a polymorphic function its
   descriptor parameters extends to a function that allocates an aggregate holding type-parameter words, and such a
   site builds its layout from the descriptors through an inline cache (a comparison of the descriptors with the
   last seen, then the cached layout). Descriptors are passed only where an allocation or a descriptor needs them,
   as now; the specializer's clones need none. *Done when:* `layouts` reports the ambiguous words of the compiler's
   own build and of the suite, before and after, the pinned fraction is recorded against step 7, and the cost of the
   added descriptor arguments on the MLton suite is recorded.
9. **A marker thread, optional** (§3.10): the slices on a thread of their own, the fenced slow path, the protocol for
   the structures both sides read, `concurrent`. Taken only if step 6's measurement shows the mutator paying for
   marking a thread could take. *Done when:* the suites pass under `concurrent,incremental`, and the throughput and
   pauses are recorded against step 6.

A release follows step 1 and step 3, since each changes the ABI (the allocation call, then the runtime's heap).

When the plan is complete, what it found moves into runtime-design.md §3, c-representation.md §9, arm64.md §3.13,
and profiling.md §6, and this document is deleted.

## 9. Reviews (2026-11-03)

**First review,** from another session (e3cd1e9a): fourteen points after the decisions of §6, each answered the same
day and folded into the section it concerns. Two were soundness holes. Evacuating during marking, as §3.6 first
said, is unsound once ambiguous words are inside the heap, since a word found after its referent moved can neither
be rewritten nor have the move undone: §3.6 marks first, logging the slots that refer into the candidate blocks, and
copies and rewrites afterwards (decision 11). Incremental marking lost an object built, during a cycle, from a
pointer loaded out of an unscanned object whose field was then overwritten, because the initializing stores have no
barrier: objects born in a cycle are born old and logged (§3.10; decided by the user). Minor collections are
suspended during a cycle (§3.10). Of the mechanisms: the mark bit moved to a side bitmap and the header's flags into
two bytes with one writer each (§3.2, decision 12); a callee-saved register in a mapped frame is precise only through
mapped frames (§3.3, step 5); the allocation cursor is a global, since `_longjmp` would restore a register (§3.4);
the object-start bit is set by every allocation and counted in the fast path (§3.4); the metadata of a JIT session
grows with it (decided by the user); interior objects hash by the old base plus their offset (§3.7); serialization
holds evacuation off rather than keying by hash (§3.7). Slips fixed: record dictionaries are not large objects; the
object-start bitmap is conservative Immix's, not Riptide's (§2, §3.1); `layouts` accepts pointers outside the heap
(§7); a word at an object's end is that object's (§3.3, §5); the header's cost is half again on a two-word tuple, and
step 1's number on Boehm is translated (§3.2); §3.5's list of the runtime's mutating stores became an audit. Generic
layouts moved from step 2 to after evacuation, taken on its measurement (decision 13; confirmed by the user).

**Second review,** a reread by the authoring session the same day. One soundness hole: a dead object in a live line
keeps its header and start bit, an ambiguous word can validate it, and its precise words, which the marker trusts,
may point into reclaimed and reused lines; the start bitmap is now intersected with the mark bitmap at the end of
every collection (§3.6, decision 14). Two gaps in the barrier: stores through interior pointers (a record's `var`
field through its payload, `sStoreAt` through a location, a view's slot) find no header at the address minus 8 and
go through the slow path with a bitmap lookup (§3.5); stores of `val` words may be pointer stores and take the
barrier (§3.5). The final pause of an incremental cycle was claimed bounded and is not, since the stack's rescan can
expose unmarked work; it is budgeted and retried, as V8's (§3.10). Evacuated copies' marks and lines are cleared
(§3.6); the logs live outside the heap (§3.5); both cursors take the slow path during a cycle, and a mapped frame's
memory-class slots stay conservative. The reread then asked what the fixes had cost in complexity, and the plan was
reorganized (decisions 2, 7, 8 revised): evacuation, where the slot log, forwarding, the hash states, the hold count,
and pinning's consequences all live, became a step taken only on a fragmentation measurement, with its design kept
and the header's bits reserved for it; the immortal space, whose reason was to keep address-keyed metadata out of the
moving question, went with it, replaced by ordinary heap data reached from listed roots and, should evacuation be
taken, blocks of metadata pinned at birth. Card marking was weighed against object logging and not taken (decision
5). The committed collector is sticky-mark Immix with a conservative stack, a precise heap, a header word, object
logging, noscan blocks, a large object space, and incremental marking: the published design with less in it.
