# Plan: Replacing the Boehm Collector

Quest allocates through the Boehm-Demers-Weiser conservative collector: every object by `GC_MALLOC`, scanned word by
word for anything that looks like a pointer, and the stack, registers, and data segments likewise. It has served well
because it asks nothing of the compilers: no object headers, no stack maps, no write barriers. It is also the
largest cost in the benchmark suite (benchmarks.md §3.1: allocation and collection are 50 to 90 percent of the
samples in half the programs), and it keeps dead data alive through stale stack slots (arm64-performance-review.md
§3.2). This document designs a collector of Quest's own: precise where the compilers can make it so, generational,
bump-allocating, moving where it may, and asks what must change to get there.

**Status: decided, not started** (2026-11-02). Section 6 records the decisions, section 7 the risks and the checking
modes that catch them, section 8 the steps, and section 9 a review's open points (2026-11-03).

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
- **JavaScriptCore (Riptide)** is the closest relative in constraints: a conservative stack, a precise heap, no
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
kind the compiler knew, conservative treatment of the words it did not (the stack, `val` words, the JIT's data),
pinning what they reach, and evacuation of everything else when it pays.

### 3.1. The heap

- **Blocks and lines:** 32 KB blocks of 128-byte lines, as Immix. A block is free, recyclable (some lines free), or
  full. Allocation bumps through the next hole of free lines; a 128-byte line is the unit of reclamation and of
  pinning. A medium object (over a line, up to 8 KB) is allocated from a fresh hole, as Immix's overflow allocator.
- **A large object space** for objects of 8 KB and up (strings, arrays, the record dictionaries), page-granular,
  never moved, marked in a side bitmap, freed when unmarked. The threshold is a parameter to measure (§6).
- **An immortal space** for runtime metadata that is keyed by address and lives for the process: descriptors,
  instantiation caches, view maps, record dictionaries, abstract types, adapters, function tables. Bump-allocated,
  never collected, scanned as a root region. This removes those structures from every collection and from every
  question of moving.
- **One reserved virtual range** for all of it (tens of gigabytes reserved, committed as used), so that "is this word
  in the heap" is two comparisons, and the metadata (object-start bitmap, line marks, block table) is indexed by
  address.
- **Metadata off to the side:** an object-start bitmap (one bit per 8 bytes, as conservative Immix and Riptide),
  which validates ambiguous words, finds an object from an interior pointer, and finds objects inside a remembered
  region; line marks (a byte per line); a block table (state, hole cursor, pinned count).

### 3.2. Objects

- **A header word before each object,** at the address the pointer points to minus 8 (.NET's placement). The object's
  own words are unchanged, so every struct the C backends declare and every offset the arm64 backend selects stays
  as it is; only the allocation changes, returning the address after the header. Embedded boxes and a record's
  payload have no headers of their own: they are words of their allocation, described by its layout, reached by
  interior pointers that the object-start bitmap resolves to the allocation.
- **The header holds a layout pointer and flag bits:** the pointer to a *layout* (below), 8-byte aligned, with its
  low three bits and its top sixteen (free on a 48-bit address space) holding: mark, logged (for the barrier),
  pinned, forwarded, and the two hash bits of §3.7. Variable-sized objects (arrays, strings' buffers, option payloads)
  keep their lengths where they are; the layout says where to read them.
- **A layout** describes an allocation's words: for each word, pointer, scalar, or *ambiguous* (a `val` word whose
  kind the allocation site did not know, §3.3), plus the size or where to find it. For a record, the layout is its
  existing `QRecordHeader` descriptor's information in this form. Layouts are static data: the describe pass already
  emits descriptors per unit; it emits layouts the same way, deduplicated per unit, and the runtime's own allocations
  name theirs from a fixed table. A layout for a pointer-free object marks it *noscan*.
- **Cost:** 8 bytes per object. A two-word tuple becomes 24 bytes, a closure 24, a string header 32. Boehm's 16-byte
  granules round a 24-byte object to 32 today, so on balance the heap grows little; bump allocation wastes nothing
  beyond 8-byte alignment.
- **Alignment:** objects are 8-byte aligned, headers included, and the allocator bumps in multiples of 8. Nothing
  the backends emit needs more: every slot is a word, a `Real` is a word, and arm64's paired loads and stores
  (`ldp`, `stp`, which the backend emits for adjacent words) need only the alignment of one register, 8 bytes for
  `x` registers; their 16-byte requirement applies to the stack pointer as a base, never to heap addresses. clang's
  copies of 16-byte structs (`QRecordVal`) use pairs or NEON loads, which on arm64 and x86-64 take any alignment on
  ordinary memory. Boehm's 16-byte alignment was incidental, and nothing relies on it: the proxy tag uses one low
  bit, and the header's flag bits live in the layout pointer, whose static data can be aligned as widely as the bits
  need. The hash word of §3.7 goes before the header and keeps every object's alignment. If a platform ever needs
  16-byte objects (a vector type in the runtime, say), the allocator bumps in 16s and the header sits in the 8 bytes
  before the object, with 8 bytes of padding before that; nothing else changes.

### 3.3. What is a pointer

Three classes of word, decided when the code is compiled:

1. **Precise:** a word whose static type is a pointer type (`ptr` in the SSA), or a scalar. The collector follows or
   skips it by the layout, and may rewrite it when the object it refers to moves. Interior and tagged pointers are
   precise too: the collector resolves the allocation through the object-start bitmap, moves it, and rewrites the
   word keeping its offset and tag.
2. **Ambiguous:** a `val` word of an object allocated in generic code (`Tuple A Int end` made by a polymorphic
   function, `Array(A)`'s elements), whose kind depends on a type argument the code did not have. The collector
   validates it (in the heap range, at or inside an allocated object) and, if it is valid, marks the object and
   **pins** it: the word is never rewritten, so the object never moves. An `Int` that happens to look like a heap
   address keeps an object alive, as under Boehm today; it is never corrupted.
3. **Roots:** the stack and registers (conservative in both backends, as now, saving the registers to the stack
   first), the per-unit root tables of §3.8 (precise), the runtime's statics (precise, listed), the immortal space
   (scanned by layouts), and the JIT's data regions (ambiguous). Everything an ambiguous root reaches is pinned.

So the heap is precise wherever the compiler knows, and nothing is less safe than under Boehm. What ambiguity costs
is only the right to move: a pinned object stays, and its line is not reclaimed by evacuation. How much is pinned
depends on the program: the MLton suite's programs are mostly monomorphic; the compiler, whose data lives in
`vector.T(A)` and `hashMap.T(K V)`, would pin a great deal. Two steps of the plan reduce it, neither needed for
correctness, both in the initial plan (§8): **layouts for generic allocation sites** (step 2), which the specializer
already removes in part, and which the descriptor-passing machinery (`DescriptorParam`) completes: a polymorphic
function that allocates an aggregate holding type-parameter words takes its arguments' descriptors, as one that
builds a descriptor mentioning them does now, and builds the layout once per distinct set of arguments, through an
inline cache at the site; and **stack maps for the arm64 backend** (step 6; arm64.md §3.13 describes what they need,
and the frame-pointer walk of jit.md §3.9 already finds the frames). A frame without a map is scanned conservatively,
so units compiled through C, by either C backend, need nothing and get nothing: their stacks stay conservative by
design, since clang emits no maps for ordinary C.

### 3.4. Allocation

- **Bump allocation inline** in both backends: compare the cursor and the limit (two words in a global the runtime
  owns, or a register the arm64 backend dedicates), store the header, return the address. The slow path, a call into
  the runtime, finds the next hole or collects. This is the inline allocation path the arm64 review set aside while
  the collector was Boehm's (arm64.md §6.3, item 2); with Quest's own collector, the dependency is on itself.
- **Zeroing:** holes are zeroed when a block is recycled, not per object, so the compilers' assumption that fresh
  memory is zero holds.
- **Escape analysis is unchanged:** an allocation that does not escape is a stack slot (ssa.md §4.2), and stack slots
  have no headers, which is fine since nothing in the heap refers to them and the stack is scanned conservatively.
- **`--nogc`** becomes the collector with collection disabled (allocation only), for debugging, or goes; libgc is no
  longer a prerequisite.

### 3.5. Generations

- **Sticky mark bits:** an object's mark bit is cleared only by a full collection. A minor collection marks from the
  roots and the remembered objects, and stops at anything already marked, so it visits the young objects only, and
  "promotion" is being marked where the object lies. Blocks allocated since the last collection are the nursery;
  after the minor collection their line marks say which holes are free again. A copying nursery would gain locality
  but requires every reference into it to be rewritable, which §3.3's ambiguous words forbid; the sticky-bit variant
  was within a few percent of copying in Immix's measurements, and nothing stops a later measurement here.
- **The write barrier:** on a store of a pointer into an object that already exists, if the object is marked and not
  yet logged, log it (set the bit, push its address). A minor collection scans the logged objects' pointer words by
  their layouts, then clears the log. One load, one test, one branch on the fast path; nothing on stores of scalars
  or into an object being made (the `opMake*` operations initialize, and need no barrier). The same barrier serves
  incremental marking later (§3.10), and a marker thread if one is ever added, as Riptide's does. Large arrays logged whole are rescanned whole; card marking
  for them is an option if a program shows it.
- **Where the mutating stores are:** the IR's `sStoreField`, `sStoreComponent`, `sStoreElement`, `sStoreAt`, and
  `sAssign` to a captured box; the runtime's `quest_proxy_store`, proxy caches, the module records' fields written by
  JIT inputs; the library's hash maps and vectors are compiled Quest, so their barriers come from the IR. The IR
  verifier can check that every pointer store into heap memory is one of these.

### 3.6. Collection

- **A minor collection** stops the mutator (there is one), saves registers, scans roots and logged objects, marks
  young objects by their layouts, and sweeps line marks of nursery blocks lazily as allocation reaches them. With a
  nursery of a few megabytes and little surviving it, this is well under a millisecond.
- **A full collection** clears mark bits, marks everything, and sweeps every block's lines. Marking is a work list
  over precise and ambiguous words, which incremental marking (§3.10) later cuts into slices.
- **Evacuation**, in a full collection: blocks are chosen by fragmentation (live lines against free), as Immix; a
  live object in a chosen block that is not pinned is copied to a fresh hole, its header marked forwarded with the new
  address, and every precise word that refers to it is rewritten as marking reaches it. Pinned objects, large
  objects, and immortal data never move. An ambiguous word's referent was pinned when the word was found, so by the
  time anything could move, nothing it refers to does; ordering is mark-with-pinning first, then choose and evacuate.

### 3.7. Identity hash

As the question proposes, with the layout of §3.2: the two hash bits are *unhashed*, *hashed*, *moved*. `identityHash`
of an unhashed object sets *hashed* and returns the mix of its address; of a hashed object, the same; of a moved
object, the mix of the word at the address minus 16, where the collector put the original address when it copied the
object (it allocates the copy 8 bytes larger, writes the old address before the header, sets *moved*; a further move
copies that word along). Pinned objects are never copied, so their addresses stay their hashes. `is` needs nothing: it
compares current addresses, which the collector keeps consistent by rewriting every precise reference and moving
nothing an ambiguous one reaches. Options and reals hash by value already, and keep doing so.

Serialization's table keyed by address (`quest_ptr_hash`) must not see an object move while it runs: it allocates
its output as it walks. The simplest fix is to key the table by identity hash (which this mechanism makes stable)
rather than by current address, with the address compared on a hit.

### 3.8. Roots and the backends

- **Per-unit root tables:** each compiled unit lists its global pointer slots (its module record, its statics holding
  heap pointers), registered at initialization as `qr_register_dicts` registers dictionaries today. An ABI change,
  in both backends and the bootstrap's. Until then, the data segment can be scanned conservatively as Boehm scans
  it; the table makes it precise and small.
- **The runtime's statics** holding heap pointers are enumerated in one place (`quest_gc_roots`), and most of them
  move to the immortal space anyway.
- **The JIT:** its data regions are ambiguous roots, registered as `GC_add_roots` registers them now; its inputs'
  module records are reached through them and so pinned, which is right (their addresses are in JIT code's GOT).
- **Thread-locals** (`quest_current_exception`, the handler chain) are listed roots.
- **The stack:** conservative in both backends to begin with; the arm64 backend's maps later (§3.3). The frame walk
  is the one exceptions use.

### 3.9. Large and pointer-free objects

- **Large objects** (§3.1) are their own space because moving them is never worth it and bump-allocating them wastes
  holes. Their layouts are ordinary (an array's, a string buffer's).
- **Pointer-free objects** are marked *noscan* by their layouts and skipped by the marker, and kept in blocks of
  their own (Go's noscan spans): a second allocation cursor, so that a full collection skips whole blocks and string
  buffers do not fragment pointer-bearing blocks. Part of the collector's first version (step 4), brought up with one
  cursor and measured with two on the string-heavy programs.
- **Small objects** are the common case and the design's center: a two- or three-word tuple, a closure and its
  environment, a boxed record, allocated at a rate of hundreds of millions per run in the benchmarks.

### 3.10. Latency and concurrency

With one mutator thread and heaps of tens of megabytes (the compiler's own), stop-the-world collections are short:
minor ones sub-millisecond, full ones tens of milliseconds at a gigabyte per second of marking. The design starts
there, and bounds the pauses of full collections by **incremental marking in the mutator thread** (§8, step 8), with
the pieces it needs decided now so that the earlier steps do not have to be redone. The runtime has no threads of
its own (libgc's marker threads are the only ones in a Quest process today, and they go with it), and the design
keeps it so: a marker thread is the optional last step, not the plan.

- **Incremental marking,** as OCaml's major collector, Lua, and V8 before it went concurrent: a full collection's
  mark is cut into slices, and each allocation slow path does a slice proportional to the bytes allocated since the
  last (the pace a tunable, with the slice bounded in time). A cycle starts with a short pause that scans the roots
  (the stack, registers, root tables, and the log) and ends with one that rescans the stack and drains the log,
  which bounds it by the stack's size and the number of objects mutated during the cycle; between them the mutator
  runs, allocating its new objects marked. Evacuation stays inside the final pause. The slices run where a
  collection may run already, at allocations, so every invariant of the stop-the-world collector holds between
  them, and a run is deterministic given its allocation sequence, which the suites and the goldens are.
- **The barrier serves both** (§3.5): logging an already-marked object when a pointer is stored into it is what a
  minor collection needs (old objects pointing at young ones) and what an interrupted mark needs (black objects
  written between slices). The fast path compares the header's state against a global threshold that the collector
  raises for the duration of a cycle, so outside one the barrier is a load, a compare, and a branch, and inside one
  the slow path logs. No fence: the only interleaving is at the slices.
- **What it costs:** the marking stays on the mutator's core, so throughput is a few percent below stop-the-world
  (the barrier is active for the cycle, the slices have overhead) rather than above it; a cycle takes longer in wall
  time, so there is more floating garbage and a somewhat larger heap; a long stretch that does not allocate delays
  the cycle, harmlessly, since it needs no memory either.
- **A marker thread, optionally, later** (§8, step 9): the slices move to a thread of their own, Riptide's and Go's
  way, so that marking leaves the mutator's core. Everything above stays; what the thread adds is the race between
  it marking and scanning an object and the mutator storing into it and reading its mark as not yet set, resolved by
  the marker setting the mark, fencing, then scanning, and the mutator's barrier storing, fencing, then reading
  (`dmb ish` on arm64, a locked instruction on x86-64, paid only inside the slow path of a running cycle), plus a
  protocol for the structures both read while the mutator allocates (the object-start bitmap, the line marks, the
  log). Go keeps the incremental slices as mutator assists even with its marker threads, so nothing of step 8 is
  undone. Taken only if a measured workload shows the mutator paying for marking it could offload.
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
| `runtime/quest_gc.c` (new) | The heap, allocation slow path, barrier slow path, marking, sweeping, evacuation, roots, hash words; replaces `GC_*` |
| `runtime/quest_runtime.h` | `quest_alloc(size, layout)` returning past the header; `quest_alloc_immortal`; barrier and root macros; layout structs |
| `runtime/quest_runtime.c` | Its ninety allocations named by layout; metadata to the immortal space; roots enumerated; `quest_identity_hash` by hash state; `quest_proxy_store` barriered |
| `runtime/quest_serialization.c` | Sharing table keyed by identity hash |
| `runtime/quest_code.c`, `jit/loader` | Data regions as ambiguous roots through the new API |
| `ir/describe` (both compilers) | Layouts per allocation site, emitted as static data with the descriptors |
| `ir/represent`, `ir/lower` (both) | Allocation operations carry their layout; `val` words marked ambiguous in it |
| `codegen/c/printer`, bootstrap printer | Allocation with header, inline bump fast path (from the header file), barrier on mutating stores, root table per unit |
| `codegen/arm64/select`, `ssa/build` | Inline bump allocation, barrier sequence, root table; later stack maps from `frameSlots` |
| `ssa/escape` | Recognize the new allocation form |
| `ir/verify`, `ssa/verify` | Every pointer store into the heap is a barriered form |
| `build`, `tools/release`, docs | No libgc; `--nogc` retired or redefined; runtime-design.md §3, c-representation.md §9, arm64.md §3.13 rewritten |
| `tools/perf/gcstats.py`, `retention.py` | Read the new collector's statistics |

The interpreters need nothing: they are compiled Quest, and their values are ordinary objects.

## 5. What Changes for Programs

Nothing in the language. Programs see: faster allocation; memory per object up by a word and down by Boehm's
rounding; `identityHash` stable across moves; collections at the same places (allocations). Programs that held
pointers in ways Boehm tolerated but the design does not (a pointer one past an array as a loop bound, which
arm64.md §3.13 already forbids the backends to make) are none, since no Quest program can form one.

## 6. Decisions

Decided 2026-11-02; the first four shape everything else.

1. **Precise heap, conservative stack, pinning for the ambiguous** (§3.3), rather than fully precise (which needs
   stack maps in both backends, a shadow stack for the C one, and layouts for every generic allocation site before
   anything works) or fully conservative (Boehm again). *Recommended:* it is the only one of the three that can be
   built in steps, each correct, and conservative Immix measured the cost at about one percent.
2. **Immix mark-region with sticky mark bits and opportunistic evacuation** (§3.5, §3.6), rather than a copying
   nursery with a mark-compact old generation (OCaml, MLton, V8). *Recommended:* copying needs every reference into
   the nursery rewritable, which decision 1 cannot promise; sticky Immix tolerates pinning at line granularity and
   still bump-allocates.
3. **A header word at a negative offset, holding a layout pointer and flags** (§3.2), rather than a pointer bitmap
   per span set at allocation (Go) or headers inside the structs. The structs, the offsets, and the bootstrap's
   generated C stay as they are; forwarding, logging, pinning, and the hash state need bits somewhere; and a layout
   pointer is 8 bytes either way. Objects stay 8-byte aligned, which is all the backends' loads need (§3.2).
4. **One mutator, stop-the-world first, then incremental marking in the mutator thread; a marker thread optional
   and last** (§3.10, §8 steps 8 and 9). Throughput is the goal the benchmarks set, so the collector is built and
   measured stop-the-world; incremental marking bounds the pauses without a thread, and is designed in now (the
   barrier, the threshold, allocation marked during a cycle, the pacing) so that nothing earlier is built in its
   way. The runtime stays single-threaded unless a measurement says the mutator is paying for marking a thread
   could take; parallel marking inside a pause is not planned (revised 2026-11-02, from "parallel, then concurrent").
5. **The barrier:** object logging through the header (§3.5) rather than card marking. *Recommended* for its
   precision (logged objects are scanned by layout, no card walking) and its reuse for incremental marking; card
   marking for large arrays is a possible addition.
6. **Large objects from 8 KB, in their own space, never moved; pointer-free objects in their own blocks** (§3.9),
   both in the collector's first version; both thresholds are parameters to measure.
7. **Identity hash by the three-state scheme with a prepended word** (§3.7), as proposed. *Recommended;* the
   alternative, a hash field in every object, costs a word on every object for the few that are ever hashed.
8. **Runtime metadata in an immortal space** (§3.1). *Recommended;* it takes the descriptor caches and dictionaries
   out of every collection and out of the moving question at once.
9. **Both compilers emit layouts, barriers, and root tables.** The runtime is shared, so the bootstrap's C must be
   correct under the new collector; the inline fast path and stack maps are self-hosted only (optimizations, by
   the two-compilers policy). *Recommended;* there is no version of this in which the bootstrap's objects lack
   headers.
10. **libgc goes.** No fallback collector is kept: a second allocator behind `quest_alloc` would keep every
    representation decision hostage to Boehm's. `--nogc` is retired, or becomes "never collect". *Recommended.*

## 7. Risks, and the Checking Modes That Catch Them

The collector's failures are silent and late: a wrong layout or a missed barrier corrupts memory that is read long
after. So the runtime has checking modes, chosen by `QUEST_GC_CHECK`, slow but exhaustive, under which any program,
the test suites, and the compiler's own build can run; tools/check runs the suites under them for a change that
touches layouts, barriers, roots, or the collector (testing.md §4.1 lists which).

| Mode | What it does | Catches |
|---|---|---|
| `layouts` | After every collection, walks every allocation by its layout: each precise pointer word is null or points at or into an allocation; each ambiguous word is counted; sizes agree with the lines marked. On Boehm (step 1) the check is against `GC_base`; afterwards against the object-start bitmap | A layout that lies about a word, a size, or a length field |
| `barriers` | At every minor collection, before the log is used, scans the whole old generation by layouts for pointers into the nursery, and reports any in an object that is not logged | A mutating store without a barrier, in generated code or in the runtime's C |
| `roots` | At every collection, scans the data segments and thread-locals conservatively and reports a heap pointer that no root table or listed root covers | A global pointer slot missing from a unit's root table or `quest_gc_roots` |
| `stress` | Collects on every allocation (or every Nth), each collection full, evacuating every object that may move; the vacated memory is poisoned (filled with a pattern that is never a valid pointer) and, in large runs, unmapped | A stale address kept across an allocation anywhere: generated code, the runtime, serialization, the JIT |
| `poison` | Every reclaimed line and freed large object is filled with the pattern | A use after reclamation |
| `incremental` (step 8) | Makes every slice as small as it can be (one object), and at the end of each cycle marks the same heap again stop-the-world and compares the marks | A barrier that let an object escape the cycle, a slice that broke an invariant |
| `concurrent` (step 9, if taken) | As `incremental`, with the marker thread forced to yield between objects | A barrier race, a lost mark |

Modes combine (`QUEST_GC_CHECK=layouts,stress`), and `stress` with `barriers` is the one that finds the most. The
checks are in the runtime, so the bootstrap's C and the JIT's code are checked by the same code as the self-hosted
backends', and the interpreters' transcripts can run under them too.

The risks themselves:

- **A layout that lies** (a pointer word described as scalar) is memory corruption under evacuation, where under
  Boehm it was a leak at worst. Step 1 builds `layouts` on Boehm, before any object moves, and `stress` is the
  first thing step 7 runs.
- **The barrier missed** on a store the IR did not classify, or one of the runtime's few pointer stores into an
  existing object, loses a young object. `barriers` finds it by exhaustion, and the IR and SSA verifiers reject a
  pointer store into heap memory that is not one of the barriered forms.
- **Pinning in generic-heavy programs** (the compiler) would leave evacuation with little to do, so the compiler's
  own build would see the allocator's gains but not compaction's. Generic layouts (step 2) and arm64 stack maps
  (step 6) are in the plan for this; the collector's statistics report the pinned fraction, so each step's effect
  on it is measured.
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
and its documentation, in the order that retires the risks first.

1. **Layouts and headers, on Boehm.** Both compilers' describe passes emit layouts; `quest_alloc(size, layout)` writes
   the header before the object and returns past it; the runtime's allocations name theirs; `QUEST_GC_CHECK=layouts`
   against `GC_base`. *Done when:* every suite passes with `layouts` on through every backend and both compilers, and
   the heap growth from headers is recorded here.
2. **Layouts for generic allocation sites** (§3.3), in both compilers: the analysis that gives a polymorphic
   function its descriptor parameters extends to a function that allocates an aggregate holding type-parameter
   words, and such a site builds its layout from the descriptors through an inline cache (a comparison of the
   descriptors with the last seen, then the cached layout). Descriptors are passed only where an allocation or a
   descriptor needs them, as now; the specializer's clones need none. *Done when:* `layouts` reports the ambiguous
   words of the compiler's own build and of the suite, before and after, and the cost of the added descriptor
   arguments on the MLton suite is recorded.
3. **Barriers and root tables, logging only.** The IR marks mutating stores and its verifier enforces the forms; both
   backends emit the barrier calls (to a runtime stub that counts) and the per-unit root tables; `roots` checks the
   tables against a conservative scan. *Done when:* the suites pass under `layouts,roots`, and the barrier counts per
   benchmark are recorded.
4. **The collector, stop-the-world, non-generational.** `quest_gc.c`: the heap of §3.1, marking by layouts with
   pinning (the mark bits behind one accessor, so that step 9 could make them atomic), lazy line sweeping, the large and immortal spaces, noscan
   blocks (§3.9, brought up with one cursor and measured with two), the statistics (`tools/perf/gcstats.py` reads
   them); libgc out of the build; inline allocation in both self-hosted backends; `poison`. *Done when:* the suites
   pass on it under `layouts,roots,poison`, the self-hosting fixed point holds, and the MLton suite is no slower than
   on Boehm (expected: much faster, from allocation alone).
5. **Generations.** Sticky marks, the barrier live, minor collections, `barriers`. *Done when:* the suites pass under
   `barriers`, and the suite's and the driver's own build times are recorded against step 4.
6. **arm64 stack maps** from `codegen.frameSlots` (arm64.md §3.13): at each call, the slots and callee-saved
   registers holding live pointers, emitted as a table per function the collector finds from the return address;
   the frame walk scans a frame with a map precisely and any other (a C-built unit's, the runtime's) conservatively.
   The JIT's units carry maps the same way. This also ends the dead-slot retention of arm64-performance-review.md
   §3.2 for mapped frames. Nothing of the kind for code compiled through C. *Done when:* the suites pass through the
   arm64 backend and the JIT under `layouts,roots,barriers`, and the pinned fraction and live data on the compiler's
   build are recorded against step 5.
7. **Evacuation and the hash.** Opportunistic defragmentation with pinning; the three hash states; serialization
   keyed by hash; `stress`. *Done when:* the suites, the transcripts, and the driver's build pass under
   `stress,barriers`, `identityHash` is stable under a test that forces moves, and fragmentation and the pinned
   fraction after long compiler runs are recorded.
8. **Incremental marking** (§3.10): the threshold in the barrier, the initial and final pauses, allocation marked
   during a cycle, the slices paced by allocation, `incremental`. *Done when:* the suites pass under
   `incremental,stress`, and the pauses and the throughput on the compiler's build and the REPL's inputs are
   recorded against step 7, with the pace and slice bound that were chosen.
9. **A marker thread, optional** (§3.10): the slices on a thread of their own, the fenced slow path, the protocol for
   the structures both sides read, `concurrent`. Taken only if step 8's measurement shows the mutator paying for
   marking a thread could take. *Done when:* the suites pass under `concurrent,stress`, and the throughput and
   pauses are recorded against step 8.

A release follows step 1 and step 4, since each changes the ABI (the allocation call, then the runtime's heap).

When the plan is complete, what it found moves into runtime-design.md §3, c-representation.md §9, arm64.md §3.13,
and profiling.md §6, and this document is deleted.

## 9. Review (2026-11-03)

A review from another session, after the decisions of §6. Each point is open for the authoring session to answer and
fold into the sections above, except where the user has already decided (marked *Decided*). When a point is settled,
its answer goes into the section it concerns and the point is removed from this list.

### 9.1. Soundness

1. **Evacuation and ambiguous words found mid-trace** (§3.6). Conservative Immix can pin before anything moves
   because its ambiguous words are all roots, scanned before tracing. Here ambiguous words are also in the heap (the
   `val` words of generically allocated objects), found only as the trace reaches them. If an object X has been copied
   and its precise referrers rewritten, and the trace then finds a `val` word pointing at X's old copy, the word cannot
   be rewritten (it may be an `Int`) and the move cannot be undone. "Rewritten as marking reaches it" and "mark with
   pinning first, then choose and evacuate" disagree; only the second is sound. Options:
   - *Two traces* per defragmenting collection: mark and pin, then copy and rewrite. Simple; doubles the cost of
     those collections.
   - *Mark first, with a slot log for the candidates* (the reviewer's recommendation): choose candidate blocks before
     marking, as Immix does; mark without moving, pinning what ambiguous words reach; record the address of every
     precise word that refers into a candidate block; then copy the unpinned live objects of the candidates and
     rewrite only the logged words. The log is proportional to the references into candidates, a small part of the
     heap; if it overflows a bound, the remaining candidates are left in place (pinned), so the collection degrades
     to non-moving rather than failing. This is G1's remembered set for its collection set, built during marking.
   - *Fewer ambiguous words* (step 2's generic layouts): shrinks the problem without removing it, since the stack's
     words stay ambiguous; the stack is scanned first, though, so it is only the heap's ambiguous words at issue.
2. **Incremental marking loses objects as written** (§3.10). Objects allocated during a cycle are allocated marked,
   the `opMake*` initializing stores have no barrier, and the barrier logs only objects already marked. The mutator
   loads an unmarked W from an unscanned object G, overwrites that field of G (G unmarked, nothing logged), builds a
   new, marked A holding W (unbarriered, so A is never scanned), and drops W from its stack: W is lost, and the final
   rescan of the stack does not find it. *Decided* (user, 2026-11-03): initializing stores are barriered while a cycle
   runs. The fast path's threshold test is already there; outside a cycle `opMake*` stays unbarriered. §3.5, §3.10,
   and step 8 to say so.
3. **Minor collections during an incremental cycle** are unspecified. "A full collection clears mark bits" and sticky
   marks meaning "old" conflict while a cycle is under way: either minor collections are suspended for the cycle (and
   the nursery grows), or the mark state distinguishes "old" from "marked in this cycle" (epochs, §9.2 item 1).

### 9.2. Mechanisms

1. **Where the mark state lives.** A header bit (§3.2) costs a touch of every object to clear at each full
   collection, and under step 9 shares a word with the mutator's logged and hash bits, so every hash or log write
   would need an atomic, not only marks; the single accessor of step 4 does not cover the mutator's writes. In a
   sticky minor collection most referents are old and already marked, and a header bit makes testing that a load of
   each old referent's line, where a side bitmap (one bit per 8 bytes, 1/64 of the heap) keeps the test in a small,
   hot structure and old objects untouched. The reviewer's recommendation: a side mark bitmap per block, beside the
   object-start bitmap (cleared per block, or swapped for a zeroed one as Go does); the logged and hash bits stay in
   the header, written by the mutator; forwarding stays in the header, written only in a pause.
2. **arm64 stack maps and callee-saved registers** (step 6). A mapped frame's pointer in x19 to x28 is saved by
   whichever callee saves it; if that callee is a C-built unit or the runtime, the saved copy is in a conservative
   frame and cannot be rewritten. Such registers are ambiguous unless the frame that saved them is mapped too.
3. **The allocation cursor in a register** (§3.4). Exceptions are `_setjmp` and `_longjmp` (`quest_runtime.h`); a
   callee-saved cursor would be restored to its value when the `try` was entered, and allocation would then overwrite
   live objects. The cursor lives in a global, or is reloaded at every handler's entry.
4. **The object-start bitmap is set by every allocation,** a read-modify-write that §3.4's fast path ("compare, store
   the header, return") does not count. Its cost belongs in the inline sequence and in step 4's measurement.
5. **The immortal space under the JIT** (§3.1). Module rollback, redefinition, and long REPL and Jupyter sessions
   keep making descriptors, dictionaries, and view maps. *Decided* (user, 2026-11-03): the immortal space grows with
   the session, as JIT code does already; §3.1 to say so. Still open: immortal caches that are written after they are
   made and point into the heap must either be rescanned at every minor collection (a cost growing with the space) or
   be barriered; which?
6. **Identity hash of interior objects** (§3.7). Embedded boxes and a record's payload share their allocation's
   header, so the *moved* word holds the allocation's old base, and the hash of an interior object is the mix of the
   old base plus its offset.
7. **Serialization** (§3.7). Its `QPtrNode`s are allocated with `quest_alloc`; a precise `ptr` field would be rewritten
   by a move while the node stays in the bucket of the old address. Keying by identity hash works; simpler is a
   counter that suspends evacuation while serialization runs, since evacuation is optional in any collection.

### 9.3. Accuracy

1. §3.1 puts the record dictionaries in both the large object space and the immortal space.
2. §2 and §3.1 cite Riptide for an object-start bitmap. JavaScriptCore's blocks are segregated by size, so a cell's
   start is arithmetic; only conservative Immix fits the citation.
3. The `layouts` check (§7: "each precise pointer word is null or points at or into an allocation") fails on every
   pointer to static data: the generated C's static `QTypeDescriptor`s, which auto values point at, the function
   tables, the module records. It needs "or outside the heap", or "or in a registered static region".
4. §5 says no program can form a pointer one past an array's end. Quest programs cannot, but clang can, from the C
   backends' output and in the runtime (a strength-reduced loop's end with its base dead). With the header at p-8,
   such a pointer validates as the *next* object. Boehm has the same exposure, so this is no regression, but the
   conservative rule should also take p equal to an object's end as that object's.
5. §3.2's "the heap grows little" understates the header's cost: a two-word tuple is 16 bytes today and 24 after,
   half again for the commonest object. Step 1 measures it on Boehm, where the 24 bytes round to 32 (double); that
   number needs translating before it is recorded as the design's growth.
6. §3.5's list of mutating stores should say every pointer store into an existing object in the runtime's C, found
   by audit, rather than name a few; replacing a string's buffer is one it misses.

### 9.4. Order

1. Step 2 (generic layouts) is an ABI change that adds descriptor arguments to polymorphic functions, before
   anything can measure whether pinning matters: pinning costs only evacuation (step 7), and step 1's `layouts` mode
   already counts ambiguous words. The reviewer suggests moving it after step 7, taken if the pinned fraction measured
   there warrants it, unless the answer to §9.1 item 1 favors shrinking the heap's ambiguity early.
