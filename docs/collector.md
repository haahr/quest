# The Collector

Quest allocates through a collector of its own, `runtime/quest_gc.c`: an Immix heap of blocks and lines with sticky
mark bits (generational, and non-moving), a header word before each object naming its layout, bump allocation inline
in every backend, write barriers on the stores that mutate existing objects, precise scanning of every word whose kind
the compiler knew, ambiguous treatment of the words it did not (frames without a stack map, `val` words, the JIT's
data), and full collections marked incrementally in the program's own thread when they would otherwise pause too
long. It replaced the Boehm-Demers-Weiser conservative collector, which asked nothing of the compilers but was the
largest cost in the benchmark suite (benchmarks.md §3.1: allocation and collection were 50 to 90 percent of the
samples in half the programs) and kept dead data alive through stale stack slots ([benchmarks.md](benchmarks.md) §24.1).

This document is the collector's reference: what it must fit (§1), the collectors it learned from (§2), its design
(§3), where it lives in the tree (§4), what programs see (§5), the decisions that shaped it (§6), the checking modes
that keep it honest (§7), what it was measured to cost and gain (§8), and the work designed but not taken, moving
objects above all (§9).

---

## 1. What the Collector Must Fit

From `runtime/quest_runtime.h`, [c-representation.md](c-representation.md), and [arm64.md](arm64.md) §3.13:

- **Allocation** is `quest_alloc(size, layout)` and its variants (`quest_alloc_sized`, `quest_alloc_bytes` for
  pointer-free bytes, `quest_alloc_words`; [c-representation.md](c-representation.md) §9), every one naming the
  object's layout. The C backends print calls of the header's inline functions; the SSA's backends select the same
  sequence themselves ([ssa.md](ssa.md) §4.1); the runtime makes its own allocations by the same functions, naming
  layouts from a fixed table in `quest_gc.c`.
- **Objects are their words, after a header.** A tuple is its words (`{QVal _0; int64_t _1}`), a closure its code
  pointer and then its descriptors and captures, an option a tag and words, an array a length and
  words, a string a length and buffer pointer, an auto value a descriptor and a word. A record's payload
  also carries a descriptor (`QRecordHeader`), and a `QRecordVal` is two words, payload and dictionary, boxed when
  stored. The header word sits before the object, outside every struct (§3.2).
- **Every aggregate slot is one word** ([runtime-design.md](runtime-design.md) §2.2), a `QVal` union: a pointer, an
  `Int`, a `Real`, a `Bool` or `Char` widened. Which it is follows from the static type, except for a slot of a type
  parameter's type in generic code, whose word is whatever the type argument's representation is. The SSA keeps
  `ptr`, `int`, `real`, and `val` apart ([ssa.md](ssa.md) §1), where `val` is a word the code does not know the kind
  of.
- **Interior pointers are everywhere by design:** a record's payload follows its box in one allocation, an aggregate
  allocates the boxes of its fields after itself (`embedded`), an option's case payload follows its tag, and a proxy
  is its `QProxy`'s address plus one, a tagged pointer (`QUEST_PROXY_TAG`). The collector resolves a pointer into the
  middle of an allocation through its object-start bitmap (§3.1).
- **One mutator thread.** The driver's `-j` compiles in child processes; nothing else is concurrent. A collection
  happens only inside an allocation, which is a call, and the backends already treat an allocation as a call that may
  do anything.
- **No finalizers, no weak references.** Files are `FILE *`s closed by the program; processes are reaped on wait.
- **Identity** is the address: `is` compares words (originals, through proxies), and `quest_identity_hash` mixes the
  word (`util/hash.identityHash`, which the library's hash maps keyed by identity use). `quest_serialization.c`
  shares cyclic data through a table keyed by address (`quest_ptr_hash`), live across the allocations it makes. Both
  rely on objects not moving.
- **Runtime metadata lives in the collected heap:** instantiated descriptors (`quest_instantiate_descriptor`), the
  instantiation and view-map caches, record dictionaries, variant adapters, abstract type entries, all allocated with
  `quest_alloc` and kept in tables keyed by their addresses.
- **The bootstrap shares the runtime,** and its C printer declares the same structs and prints the same `quest_alloc`
  calls, layouts, barriers, and root tables, so a change to the object model is a change to both compilers
  (two-compilers policy, [testing.md](testing.md) §2.8).
- **Darwin arm64 is the platform;** the C backend also runs on Linux, which the runtime keeps compiling (the stack
  guard, the frame walk, and the data segment's bounds are conditional), though no Linux machine runs it (§7).

## 2. What Recent Collectors Do, and What Carries Over

- **Go** is non-moving and non-generational: concurrent tri-color marking with a hybrid insertion-and-deletion write
  barrier, size-classed spans with per-thread caches, pointer bitmaps per span rather than object headers, separate
  "noscan" spans for pointer-free objects, large objects (over 32 KB) straight from the page heap, precise stack maps,
  and a pacer that spends about a quarter of the CPU on background marking. It optimizes for pause time over
  throughput and pays for it: no bump allocation, no compaction, every pointer store barriered. What carried over:
  noscan spans, and that a type's pointer map is set at allocation rather than discovered.
- **Java (HotSpot)** has moved from Parallel (throughput, copying young generation, mark-compact old) through G1
  (regions, SATB concurrent marking, card-table remembered sets, evacuation pauses) to ZGC and Shenandoah, which
  compact concurrently behind load barriers (colored pointers, forwarding tables) and became generational in JDK 21
  and 24. Load barriers cost on every pointer load, which a language whose data is mostly immutable and read often
  should not pay. What carried over: card marking for stores into large objects, and, for the evacuation not taken,
  regions evacuated selectively by garbage density and a remembered set built while marking (§9.1).
- **V8 (Orinoco)** is generational with a parallel copying scavenger (Cheney) for the young generation, mark-compact
  for the old with concurrent marking behind a write barrier, selective evacuation of fragmented pages, and a large
  object space. Because it moves objects, an identity hash is stored in the object once computed. What carried over:
  the incremental final pause that gives work back to slices when the rescan exposes more than its budget (§3.10).
- **.NET** is generational (0, 1, 2 and a large object heap over 85,000 bytes, not compacted by default), compacting
  with pinning, card tables, bump allocation from per-thread allocation contexts, background marking of generation 2,
  and regions since .NET 7. Its object header sits *before* the method-table pointer the object reference points to.
  What carried over: a header at a negative offset, which leaves the object's own layout untouched.
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
  one percent. Quest's collector is conservative Immix with sticky mark bits, without the evacuation (§9.1).
- **OCaml and MLton,** the functional relatives: a bump-allocated minor heap, promotion on first survival, a header
  word per object, and (MLton) full knowledge of every object's layout because it monomorphizes. Quest keeps
  polymorphism at run time, so it cannot have MLton's certainty everywhere (§3.3).
- **Hash codes under moving** (Agesen, 1999; used by JikesRVM and others): two header bits say *unhashed*, *hashed by
  address*, or *hashed and moved*. Hashing an object sets the second state and returns its address; a collector that
  moves such an object appends a word holding the old address and sets the third state, after which the hash is read
  from that word. Objects never hashed, the vast majority, cost nothing. It is the scheme reserved for Quest should
  objects ever move (§9.2).

## 3. The Design

In one sentence: an Immix heap with sticky mark bits, a header word before each object naming its layout, bump
allocation inlined in every backend, a write barrier on the few mutating stores (object logging, and card marking for
stores through a slot's address), precise scanning of every word whose kind the compiler knew, conservative treatment
of the words it did not, and incremental marking for full collections that would pause too long. Nothing moves: the
right to move is reserved in the header and designed (§9.1), and not taken (decision 2).

### 3.1. The heap

- **Blocks and lines:** 32 KB blocks of 128-byte lines, as Immix. A block is free, recyclable (some lines free), or
  full. Allocation bumps through the next hole of free lines, zeroing each hole as it is entered (unless the block is
  fresh from the system, and so zero already); a 128-byte line is the unit of reclamation. A medium object (over a
  line, under 8 KB) comes from an overflow cursor that takes free blocks whole, as Immix's overflow allocator, so that
  it does not skip the small holes the ordinary cursor would fill.
- **Large objects,** 8 KB and up (`Q_GC_LARGE`; strings' buffers, arrays), take a run of blocks of their own
  (`QB_LARGE_HEAD` and its tails in the block table), never moved, marked as any object is, and freed whole when
  unmarked. A run of one block (an object under 32 KB) is the free list's next block, as a small block is; a longer
  run is the first fit below the high-water mark, else fresh blocks beyond it (`quest_gc_take_run`). One-block runs
  scanned the block table for their first fit too, which a big heap made a build's bottleneck: the code generator's
  per-function tables, which grow with the function, are such objects (2026-11-23).
- **Runtime metadata stays in the ordinary heap:** descriptors, instantiation caches, view maps, record dictionaries,
  abstract types, adapters, allocated as any object and reached from the runtime's listed roots (§3.8), so a full
  collection marks them at a cost proportional to their size, small outside a long JIT session. They are keyed by
  address, which nothing moving disturbs. A REPL or Jupyter session, with module rollback and redefinition, keeps
  making them and keeps them, as it keeps JIT code already (decided 2026-11-03).
- **One reserved virtual range** for all of it: 64 GB by default (`QUEST_GC_RESERVE` gigabytes), halved until the
  system grants it, committed as touched, so that "is this word in the heap" is two comparisons
  (`quest_gc_heap_lo`, `quest_gc_heap_hi`), and the metadata is indexed by address. The range is asked for at 2^46
  (`Q_GC_HEAP_HINT`), above any integer a program is likely to hold: an ambiguous word holding an integer equal to an
  object's address keeps the object alive, and reads as a store without a barrier to the `barriers` check (the
  compiler's packed source locations, a file's number above bit 32, were such integers when the system placed the
  range at 0x70_0000_0000). The system may decline the hint and place it lower. The tables are mapped after the
  range, not where the system would put them, just above the binary, which the JIT's code regions need within
  `adrp`'s reach ([jit.md](jit.md) §3.6).
- **Metadata off to the side:** a block table (`QBlock`: state, space, fresh, young, run, live lines); a mark byte
  per line (`quest_gc_lines`); an object-start bitmap (`quest_gc_start_bits`, one bit per 8 bytes, as conservative
  Immix: set by every allocation, §3.4, and intersected with the mark bitmap at the end of every collection, §3.6,
  so that only live objects validate), which validates ambiguous words, finds an object from an interior pointer, and
  finds the objects in a card; a mark bitmap (`quest_gc_marks`, one bit per 8 bytes, the truth about liveness, §3.2);
  and a card table (`quest_gc_cards`, a byte per 512 bytes, §3.5).
- **Sizing:** a full collection is due when the blocks in use reach their target, twice those in use after the last
  collection and at least `QUEST_GC_MIN_HEAP` megabytes (64 by default). A block with one live line counts as in use,
  so a heap of scattered survivors holds more blocks than its live bytes need (§8.3); counting a recyclable block's
  holes as free is open work (§9.6).

### 3.2. Objects

- **A header word before each object,** at the address the pointer points to minus 8 (.NET's placement). The object's
  own words are unchanged, so every struct the C backends declare and every offset the arm64 backend selects is as it
  would be without a collector; only the allocation changes, returning the address after the header. Embedded boxes,
  a record's payload, and an option's case payload have no headers of their own: they are words of their
  allocation, described by its layout, reached by interior pointers that the object-start bitmap resolves to the
  allocation.
- **The header holds a layout pointer and two bytes of flags:** the layout's address in the low 48 bits
  (`Q_HEADER_LAYOUT_MASK`; free on a 48-bit address space), and above it two bytes with one writer each. The
  collector's byte (bits 56 to 63) holds *old* (`Q_HEADER_OLD`), set when a collection marks the object, the barrier's
  hint (§3.5); the mutator's byte (bits 48 to 55) holds *logged* (`Q_HEADER_LOGGED`), set when the barrier logs it.
  One bit breaks the rule: *read-only* (`Q_HEADER_READONLY`, bit 63), a string literal's mark, is in the collector's
  byte although the mutator sets it, since a static object's header is a relocated pointer and arm64 Darwin's chained
  fixups keep only a pointer's low 36 bits and top byte. It is set once, when the string is made (static data, or
  `quest_string_freeze` before the string is shared), and never cleared, and the collector's writes keep it.
  The bits left in each are reserved for moving (*pinned*, *forwarded*, and the hash states, §9). Each side writes
  its byte with a byte store, so no read-modify-write of the word is shared, and a marker thread would need fences
  but no atomics (§9.3). The mark bit itself is not in the header: liveness lives in the side mark bitmap, which a
  full collection clears a block at a time instead of touching every object, and which keeps a minor collection's
  test of an old referent, most of what a young object's words point at, in a small hot structure rather than a load
  of each referent's line. *Old* is only a hint for the barrier: a stale value (an object the current cycle has not
  yet reached) makes the barrier conservative, logging an object that needed no logging, never wrong.
- **A layout** (`QLayout`, `runtime/quest_gc.h`) describes an allocation's words, each a pointer, a scalar, or
  *ambiguous* (a `val` word whose kind the allocation site did not know, §3.3), in one of three forms. A *fixed*
  layout describes an object of a known size word by word. An *array* layout describes a header of known size and
  then elements, their count at a fixed offset in the header. A *sized* layout describes an allocation whose size is
  known only at the call and recorded nowhere else (a string's buffer, the runtime's tables): the allocation records
  its byte count in the word before the header (shifted left one bit with the low bit set, which tells the two
  prefixes apart), and the layout gives a pattern of words that repeats over it. A layout whose words are all scalars
  is *noscan*, and the collector never scans its objects. For a record, the layout is its `QRecordHeader`
  descriptor's information in this form.
- **Where layouts come from:** the compilers compute them from shapes (`repr/objectLayout`, the bootstrap's
  `quest/repr/objectlayout.py`), deduplicated per unit, and emit them as static data (`quest_layout_<tag>`, its kinds
  `qlk_<tag>`) beside the descriptors: both C printers, and the SSA's builder through `ssa/statics`. The runtime's own
  are a fixed table in `runtime/quest_gc.c` (`quest_layout_adapt_closure`, `quest_layout_array_pointer`, `_scalar`,
  `_ambiguous`, `quest_layout_string`, the descriptors' and caches' layouts, ...), checked against the C structs'
  sizes by static assertions where they can be. The runtime's generic copies of values (`quest_convert`'s,
  serialization's) and its tables of mixed words take a layout of ambiguous words (`quest_layout_words`).
- **Cost:** 8 bytes per object, and 16 per sized one, which is half again on a two-word tuple. Measured over the
  allocation-heavy MLton benchmarks, the headers add 41 percent to the bytes allocated, and a fifth to the compiler's
  (§8.1). Bump allocation wastes nothing beyond 8-byte alignment, where Boehm's 16-byte granules rounded a 24-byte
  object to 32.
- **Alignment:** objects are 8-byte aligned, headers included, and the allocator bumps in multiples of 8. Nothing
  the backends emit needs more: every slot is a word, a `Real` is a word, and arm64's paired loads and stores
  (`ldp`, `stp`, which the backend emits for adjacent words) need only the alignment of one register, 8 bytes for
  `x` registers; their 16-byte requirement applies to the stack pointer as a base, never to heap addresses. clang's
  copies of 16-byte structs (`QRecordVal`) use pairs or NEON loads, which on arm64 and x86-64 take any alignment on
  ordinary memory. The proxy tag uses one low bit, and the header's flag bits live in the layout pointer's high bits.
  If a platform ever needs 16-byte objects (a vector type in the runtime, say), the allocator bumps in 16s and the
  header sits in the 8 bytes before the object, with 8 bytes of padding before that; nothing else changes.

### 3.3. What is a pointer

Three classes of word, decided when the code is compiled:

1. **Precise:** a word whose static type is a pointer type (`ptr` in the SSA), or a scalar. The collector follows or
   skips it by the layout. Interior and tagged pointers are precise too: the collector resolves the allocation
   through the object-start bitmap.
2. **Ambiguous:** a `val` word of an object allocated in generic code (`Tuple A Int end` made by a polymorphic
   function, `Array(A)`'s elements), whose kind depends on a type argument the code did not have. The collector
   validates it (in the heap range, and at or inside a live allocation) and, if it is valid, marks the object. A word
   that validates may also be at an allocation's end, or at its header or a sized allocation's byte count: no Quest
   program forms a pointer one past an array, but clang can from the C backends' output and in the runtime (a loop's
   end kept with its base dead), and C compilers keep the address an allocation returned *before* the header was
   skipped (clang folds the `+ 8` into every field's offset), so such a word counts for the object it ends, the
   object whose header it is at, and any that begins there. An `Int` that happens to look like a heap address keeps
   an object alive, as under Boehm; it is never corrupted. Only a live object validates (§3.6), so the precise words
   of what an ambiguous word reaches are current, and the marker may trust them.
3. **Roots:** the stack and registers (the registers saved to the stack first, by `setjmp`; a frame of arm64 code by
   its map, the words live across its call, a `ptr` precise and an `int` or a `val` ambiguous; every other frame
   conservatively), the per-unit root tables of §3.8 (precise), the runtime's statics (precise, listed), and the JIT's
   data regions (ambiguous).

So the heap is precise wherever the compiler knows, and nothing is less safe than under Boehm. What ambiguity costs a
non-moving collector is a validation per ambiguous word and some false retention, both small; what it would cost a
moving one is the right to move what an ambiguous word reaches (§9.1).

**Stack maps** ([arm64.md](arm64.md) §3.13 has the maps, the frame tables, and the walk): each unit the arm64 backend
compiles, and each the JIT loads, registers a frame table (`qr_frames`, `quest_register_frames`), giving per function
the words from `sp` to its frame record, the pairs of callee-saved registers it saves, and the words at `sp` that
nothing describes, and per call the return address with a map of the callee-saved registers and frame words live
across it. `quest_gc_scan_stack` walks the frame records from its own frame: a caller whose call a table lists is
scanned by the map, every other frame whole. A callee-saved register live across a mapped call is read where the
youngest frame after it saved it, which the walk knows while every frame since is mapped; past an unmapped frame (a
C-built unit's, the runtime's) the places known so far are scanned as ambiguous words and forgotten. A function that
enters a `try` has no maps, since its handler reads slots where liveness does not see it. A mapped frame's
memory-class slots, where escape analysis puts the aggregates that do not escape ([ssa.md](ssa.md) §4.2), are scanned
conservatively, since nothing describes their words. Units compiled through C, by either C backend, get no maps:
clang emits none for ordinary C, so their frames stay conservative by design. The maps make the backend's clearing of
dead values' slots unnecessary, and it does none. `QUEST_GC_MAPS=0` scans every frame whole.

### 3.4. Allocation

- **Bump allocation inline** in every backend: compare the cursor and the limit, bump, store the header, set the
  object's bit in the object-start bitmap (a byte loaded, or'ed, and stored: the bitmap is what validates ambiguous
  words, §3.1, and only the allocator knows where objects begin), return the address. The bit's byte is
  `quest_gc_start_base` plus the address shifted right 6, and the bit the address shifted right 3, and 7: the base is
  the bitmap's address less the heap's low address shifted right 6, which a block's boundary makes exact, so that the
  sequence reads one global for it, not two. The C backends get the sequence
  from the header (`quest_alloc`, `quest_gc_bump`, `quest_gc_note_start` in `runtime/quest_gc.h`); the SSA's backends
  select it (`ssa/passes/allocations`, [ssa.md](ssa.md) §4.1), arm64 and the JIT because they cannot take it from the
  header, and ssac because its printer calls every runtime function out of line. The inline sequence's base, the
  header word's address, is an `int` in the SSA and the object's address the first `ptr`: a `ptr` from which
  selection folds the object's offsets would point a word before its object, which a precise scan of a mapped frame
  takes for the end of the object before ([arm64.md](arm64.md) §3.13 states what a `ptr` in a frame may point at).
- **The cursors are globals,** `quest_gc_cursor[2]` and `quest_gc_limit[2]`, one pair per space (pointer-bearing,
  and noscan, §3.9) chosen by the site's layout, not registers the arm64 backend dedicates: a raise is `_longjmp`
  (`Q_LONGJMP`), which restores the callee-saved registers to their values when the `try` was entered, so a cursor in
  one would be rolled back and the next allocation would overwrite live objects; and the C-built units and the
  runtime bump the same words.
- **The slow path,** `quest_gc_alloc_slow`, takes the next hole of the current block, then a recyclable block's, then
  a free block's; medium objects take the overflow cursor and large ones runs of blocks (§3.1); and it collects first
  when a collection is due (§3.6). While a checking mode is on (`quest_gc_check_flags` nonzero) every allocation takes
  it, and it counts them: the slow path hides the limits (each made its cursor, the real ones kept) after each
  allocation, as during a cycle, so that the inline test of the limit alone sends the next one there too. During an
  incremental cycle it serves every allocation too, and stores the header word
  itself with the flags of an object born during the cycle (§3.10); the inline path stores the header only for what
  it bumps itself.
- **Zeroing:** holes are zeroed when they are entered, not per object, so the compilers' assumption that fresh memory
  is zero holds for every allocation, pointer-free bytes included.
- **Escape analysis is unchanged:** an allocation that does not escape is a stack slot ([ssa.md](ssa.md) §4.2), and
  stack slots have no headers, which is fine since nothing in the heap refers to them and the stack is scanned. A
  barrier call is not an escape: it keeps no pointer, and the pass drops the barriers of an allocation it makes a
  slot, which needs none (a slot is a root) and has no header word for the object barrier to read.
- **`--nogc`** compiles the runtime with `-DQUEST_NOGC`, under which the collector allocates and never collects
  (`QUEST_GC_NEVER` does the same at run time), for debugging. libgc is not a prerequisite of anything.

### 3.5. Generations

- **Sticky mark bits:** an object's mark bit is cleared only by a full collection. A minor collection marks from the
  roots, the logged objects, and the dirty cards, and stops at anything already marked, so it visits the young objects
  only, and "promotion" is being marked where the object lies. The young objects are the unmarked ones, in the holes
  allocated into since the last collection, whether in fresh blocks or in recyclable ones; their blocks are listed as
  their holes are entered (`young` in the block table), and a minor collection sweeps those alone: only live objects
  validate there, the live lines are recounted, a young block or large run with nothing live is freed, and the old
  recyclable blocks not yet allocated into keep their holes. A copying nursery would gain locality but requires every
  reference into it to be rewritable, which §3.3's ambiguous words forbid; the sticky-bit variant was within a few
  percent of copying in Immix's measurements.
- **The object barrier,** `quest_barrier(obj)`: on a store of a word that may be a pointer (`ptr` or `val` in the SSA;
  a `val` store in generic code, an `Array(A)` element or a hash map's bucket, may be one) into an object that
  already exists, if the header's *old* bit is set and its *logged* bit is clear, log it (`quest_barrier_log` sets
  the bit and pushes its address). A minor collection scans the logged objects' words by their layouts, whole, then
  clears the log. The fast path, inline in `quest_runtime.h` (through `quest_gc.h`), is a load of the header, a mask,
  a compare, and a branch; nothing on stores of scalars. A tuple bound by a case binder is an option's payload, which
  shares the option's allocation ([c-representation.md](c-representation.md) §5.3), so the word before it is the
  option's tag, not a header: the barrier takes a word under 65536 (`Q_BARRIER_TAG_LIMIT`) for a tag and reads the
  header one word further back, logging the option.
- **The slot barrier,** `quest_barrier_slot(slot)`, for stores by a slot's address: an array's element, a record's
  field through its payload (which sits after its box when the record was made in it, at the start of its allocation
  when it is a module's, and elsewhere when `quest_record_box` boxed a viewed record), a `var` or `out` location
  (often a stack slot), and a view's slot. None of these has a header at a fixed distance, and a large array logged
  whole would be rescanned whole, so the slot barrier marks a *card* instead, 512 bytes of the heap with a byte each
  in a table beside it. The fast path is a range check (a slot outside the heap is a stack or static slot) and two
  bytes' loads: the slot's line mark (a slot in an unmarked line is a young object's, whose stores need no barrier; a
  large run's lines are marked with it) and its card; the slow path, `quest_barrier_card`, marks the card and lists
  it. A minor collection scans each dirty card's words by the layouts of the old objects in it (the one that starts
  before the card and reaches into it, found by the start bits, and those that start in it); a young object's words
  are left to marking, since scanning a dead one's would keep what it points at alive. Card marking was added when
  the compiler's build showed its tables (arrays of a million entries) logged whole at every minor collection: the
  log's scan was 17.5 s of the build's 20.5 s of minor pauses.
- **The barrier follows its store,** with no call that may collect between the two. A barrier before the store is
  forgotten by a collection inside the stored value's own computation (`r.name := "literal"`, a `var` parameter
  assigned a call's result, a slot whose value is boxed), which logs nothing for the store that follows it.
- **Initializing stores** (`opMake*`) need no barrier while nothing that may collect is called between the object's
  allocation and its last store, since the object is young. When a call comes between them (a string literal's
  allocation inside the store that initializes a field, a conversion, a descriptor's instantiation), a collection may
  run and mark the object old, so the printers and the SSA's builder keep the objects being initialized and, from the
  first such call on, log each through the object barrier before every later call and after its last store
  (`begin_init` in the bootstrap's printer, `beginInit` in the self-hosted one and the builder; the builder counts
  only the calls that may collect: the program's functions, and the runtime's that allocate). Inside an incremental
  cycle the object is logged as it is allocated (§3.10), which covers its initializing stores at once.
- **The runtime's own stores** keep the same rules by hand: a pointer store into an object needs no barrier only when
  nothing can have allocated since the object was made, so the runtime allocates an object's parts before the object
  where it can (strings and their buffers, descriptors and their metadata, the program's arguments before their
  array) and otherwise computes the stored value into a local, then stores and barriers (proxy caches, the string
  builder's chunks, the instantiation and view-map caches, serialization's tables as they are filled). Where an
  operation builds many objects with stores between their allocations (a descriptor's instance, a dynamic value's
  reading and writing, a directory's listing, the program's arguments) it holds collections off for the operation
  (`quest_gc_hold`, `quest_gc_release`): everything it allocates stays young, so only its stores into older objects
  need barriers, and a pointer it parks outside the heap and the stack (in `malloc`ed memory) is not lost. A hold is
  for an operation bounded by its result's size that runs none of the program's code; a raise releases every hold
  (`quest_gc_release_all`, from `quest_reraise`). The JIT's raw word store (`quest_value_store`, `os/value.store`)
  marks the slot's card.
- **Where the mutating stores are:** the IR's five store statements are the only stores of words into memory
  (`sStoreField`, `sStoreComponent`, `sStoreElement`, `sStoreAt`, and `sAssign` to a captured box), so the backends
  barrier a store by its form and the stored word's kind (`holdsPointer`) with no IR change; the library's hash maps
  and vectors are compiled Quest, so their barriers come from the backends; and the runtime's C, by the rules above.
  The `barriers` check (§7) finds a missed one at run time, and `ssa/barriers` ([ssa.md](ssa.md) §7) at compile time,
  for the SSA's backends: after the pipeline it holds every function to the rule that a store of a pointer into an
  object a collection may have seen is followed by its barrier before the next call that may collect, by a forward
  dataflow over the young allocations and the stores owed a barrier. It covers a `ptr` and a `val` made from one; a
  `val` of unknown kind is the builder's to judge, since the SSA has not the type that says.
- **The barriers are declared as reading memory** (`effects(memoryReads ...)` in `ssa/runtimeFunctions`), not
  writing it: they write only the header's logged byte, the log, and the cards, none of which compiled code loads, so
  value numbering keeps its loads across them. The SSA's backends call both out of line; their fast paths inline in
  the SSA were tried and not kept ([arm64.md](arm64.md) §3.13, §9.5).
- **The log and the dirty list live outside the heap** (as do the work list and the young list), so the barriers'
  slow paths never collect and §1's rule that a collection happens only inside an allocation holds.

### 3.6. Collection

- **A minor collection** runs once a nursery of blocks has been taken since the last collection (`QUEST_GC_NURSERY`
  megabytes, 64 by default, the heap's least size; 0 leaves full collections alone). It stops the mutator, saves
  registers, scans the roots, the logged objects, and the dirty cards, marks young objects by their layouts, and
  sweeps the young blocks (§3.5). Its pause is what survives and the roots: 8.6 ms on average on the compiler's
  build, 27 ms at the longest, and 1.8 ms on a REPL session (§8.4). The nursery adapts to what survives: doubled
  while more than a quarter of the young bytes survive a minor collection (a program building a structure it keeps,
  whose minor collections would mark what the next full one marks again, as tailmerge's do), up to a quarter of the
  heap's target and then off, with one minor collection at that size every eighth full one to see whether the
  program still keeps what it allocates, and halved back toward the configured size while under a sixteenth
  survives (`quest_gc_adapt_nursery`). Under a checking mode the nursery is at least a quarter of the heap, so that the
  walks a minor collection makes stay a fraction of the run.
- **Why 64 MB:** a minor collection leaves its survivors where they are, one or two percent of the nursery's bytes,
  small objects scattered over nearly every block it filled, and their marks are sticky until the next full
  collection, so allocation, which takes a block's holes before a free block, hops between ever smaller holes. With
  an 8 MB nursery barnes-hut's 34 GB went into 32.7 million holes of 1.0 KB on average, against 2.1 million of 16 KB
  with full collections alone, and the allocation-heavy programs lost 10 to 17 percent; a larger nursery dilutes
  this, and at 64 MB the compiler's build is as fast as with no minor collections, in 1.39 GB of blocks against 3.66
  (§8.4). A heap whose blocks in use stay under half the nursery has full collections alone, which for so small a heap
  are as cheap. Only moving the young survivors would give the blocks back whole (§9.1).
- **A full collection** is due when the blocks in use reach their target (§3.1), or when a minor collection leaves
  them there. It clears the marks and line marks of the blocks in use, marks everything from the roots, sets each
  marked object's lines, intersects the start bits with the marks, frees dead large runs, and classifies each block
  as free, recyclable, or full by its live lines. It stops the world unless the last full collection took longer
  than a pause may, in which case it is an incremental cycle (§3.10). Marking is a work list over precise and
  ambiguous words, outside the heap.
- **Only live objects validate.** At the end of every collection, minor or full, the object-start bitmap is
  intersected with the mark bitmap (in the blocks swept), a pass over 1/64 of the memory, so that a dead object's
  start bit goes with its liveness (decision 14). Without this a dead object in a live line, which keeps its header,
  could be validated by an ambiguous word (an `Int` on the stack) and scanned, and its precise words, which the
  marker trusts, may point into lines the same collection reclaimed and later reused. Boehm was immune because it
  validated every word; this collector is immune because nothing dead validates. A young object that dies and is
  resurrected by the stack in a minor collection is harmless, since nothing was reclaimed since it was allocated; its
  start bit goes at the end of that collection. The `layouts` walk (§7) uses the same intersection.
- **Sweeping is lazy:** a collection only classifies blocks and counts their live lines; the allocator finds a
  recyclable block's holes from its line marks as it enters the block.
- **Nothing moves.** A block whose survivors are scattered keeps their lines and recycles the rest, so the cost of
  never moving is the lines the survivors hold: after the compiler's build live lines are 2.1 times live bytes, and
  2.2 after a long REPL session (§8.4). Evacuation is designed (§9.1) and not built.

### 3.7. Identity hash

Nothing moves, so `identityHash` is the mix of the address (`quest_identity_hash`, through `quest_unproxy` for a
proxy), and `is` compares addresses. Options and reals hash by value already. Serialization's table keyed by address
(`quest_ptr_hash`) is sound for the same reason. The scheme that would keep hashes stable under moving, and what
serialization would need, are in §9.2.

### 3.8. Roots and the backends

- **Per-unit root tables:** each compiled unit lists its globals that may hold a heap pointer and its module records
  (`qr_roots`, `QRootEntry`s ended by a null slot), registered at initialization by `qr_register_dicts` through
  `quest_register_roots`, in both C printers and the SSA's builder. The JIT never unmaps a unit's data, so its tables
  stay registered.
- **The runtime's statics** holding heap pointers are listed by each runtime file through a callback
  (`quest_runtime_roots`, `quest_code_roots`, `quest_serialization_roots`): the descriptor and view-map caches, the
  dictionaries, the abstract types, the adapters, the program's arguments, serialization's witness stack, through
  which the metadata of §3.1 is reached.
- **The JIT:** its data regions are ambiguous roots, registered with `quest_gc_add_roots`; its inputs' module
  records are reached through them, which is right (their addresses are in JIT code's GOT).
- **The exception state** (`quest_current_exception`, the handler chain) is a listed root.
- **The stack:** by the frame tables for arm64 frames, conservatively for every other (§3.3).
- **The `roots` check** (§7) scans the executable's data segment (`getsegmentdata` on Darwin, `__data_start` to
  `_end` on Linux) for a heap pointer no table or listed root covers, naming the symbol.

### 3.9. Large and pointer-free objects

- **Large objects** (§3.1) are their own space because moving them is never worth it and bump-allocating them wastes
  holes. Their layouts are ordinary (an array's, a string buffer's).
- **Pointer-free objects** are marked *noscan* by their layouts, skipped by the marker, and kept in blocks of their
  own (Go's noscan spans): a second allocation cursor, so that a collection never reads their words and string
  buffers do not fragment pointer-bearing blocks.
- **Small objects** are the common case and the design's center: a two- or three-word tuple, a closure, a boxed
  record, allocated at a rate of hundreds of millions per run in the benchmarks.

### 3.10. Latency and incremental marking

With one mutator thread and heaps of tens of megabytes to a few gigabytes (the compiler's own), stop-the-world
collections are short for minor collections and for small heaps' full ones. A large heap's full collections are
bounded by **incremental marking in the mutator thread**: the runtime has no threads of its own, and the design keeps
it so (a marker thread is §9.3).

- **When a full collection is a cycle:** when the heap's growth asks for one and the last full collection took
  longer than a pause may (`QUEST_GC_PAUSE`, 10 ms; 0 makes every one a cycle; `QUEST_GC_INCREMENTAL=0` makes none
  one). A collection asked for outright (`quest_gc_collect`, a checking mode's) stops the world, and finishes a cycle
  under way. A small heap's full collections are a few milliseconds each and stop the world, since a cycle's own
  costs, the call for every allocation while it runs and the scan of every object born in it, are paid at each of
  them and buy nothing there: with every full collection a cycle, tailmerge, whose 15 MB of live data in the least
  heap are marked 1,535 times, took 1.17 of its time, for pauses of 1.4 ms instead of 21 (§8.6).
- **The cycle:** a first pause clears the marks and marks the roots. Slices in the allocation slow path, one each
  `QUEST_GC_SLICE` kilobytes allocated (32), drain the log and the dirty cards, rescanning a logged object by its
  layout and a card's marked objects as a minor collection would, and mark `QUEST_GC_PACE` bytes for each byte
  allocated (4), a megabyte at most (the rest of a large allocation's share is left to the slices after), an object
  over 128 KB a piece at a time (`Q_GC_SCAN_PIECE`). None runs while collections are held off (§3.5). A last pause
  scans the log and the cards, marks the roots again, finishes, and sweeps.
- **Objects born during a cycle** are born marked, with *old* set, and logged, so that a slice scans what they were
  built from: their initializing stores (`opMake*`) have no barrier, and without this an object built during the
  cycle from a pointer loaded out of an unscanned object, whose field is then overwritten, would be the only holder of
  that pointer and would never be scanned, and the pointer would be lost (decided 2026-11-03). For the cycle the
  collector sets both cursors' limits to their cursors (keeping the real limits itself), so every allocation takes
  the slow path, which bumps, sets the start bit, marks, writes the header with its flags, and logs (a noscan object
  is marked and not logged; one over 128 KB goes to the work list instead, to be scanned in pieces). The slow path
  stores the header word whenever it allocates, and the inline path only for what it bumps itself (§3.4), so that the
  flags stand. The cost is a call per allocation for the cycle's duration; 0.6 percent of the compiler's build's
  allocation is made while a cycle runs, and the build takes the same time with cycles as without, so the
  alternative, a flag word loaded on the inline path (two instructions on every allocation, always), was not needed.
- **Allocation during a cycle:** the line marks, by which the allocator finds a block's holes, are cleared at the
  cycle's start and are the marker's until its sweep, so during a cycle allocation finishes the holes it is in and
  then takes free blocks alone, and the heap passes its target by what the pace lets the program allocate.
- **The final pause is budgeted.** It rescans the roots, the stack and registers and the root tables and the JIT's
  data too, since a store into a global has no barrier. The rescan can expose unmarked objects: one loaded out of a
  grey object before a slice scanned it, whose field was then overwritten, and which the mutator kept only in a
  register, a slot, or a global. Tracing from them is unbounded in principle, so if the rescan exposes more than 2 MB
  of work, the collector gives it back to further slices and rescans again, as V8 does, three times at most
  (`Q_GC_FINAL_RETRIES`), after which it finishes stop-the-world. No barrier changes for this; the alternative,
  shading the overwritten value in the slow path during a cycle, closes the window only if every store into an old
  object takes the slow path for the cycle, which would put a global back on the fast path.
- **Minor collections are suspended while a cycle runs:** the mark bitmaps are cleared at its start, so a minor
  collection could not tell old from new, and the nursery grows for the cycle's duration, which the pace bounds (41
  MB on the compiler's build, §8.6). A mark state with an epoch, telling *old* from *marked in this cycle*, is the
  alternative kept in reserve should that growth matter. The slices run where a collection may run already, at
  allocations, so every invariant of the stop-the-world collector holds between them, and a run is deterministic
  given its allocation sequence, which the suites and the goldens are.
- **The barrier serves both** generations and cycles (§3.5): logging an already-marked object when a pointer is
  stored into it is what a minor collection needs (old objects pointing at young ones) and what an interrupted mark
  needs (black objects written between slices). Nothing about it changes for a cycle, because objects born in one are
  born old. No fence: the only interleaving is at the slices.
- **What it costs:** the marking stays on the mutator's core, so throughput is below stop-the-world's by the slices'
  overhead; a cycle takes longer in wall time, so there is more floating garbage and a somewhat larger heap (3
  percent more blocks at the most on the compiler's build); a long stretch that does not allocate delays the cycle,
  harmlessly, since it needs no memory either. On the compiler's build the longest full pause went from 660 ms to 12
  ms (§8.6). What is left of the collector's latency is the minor collections': 30 ms at the longest on the
  compiler's build, where the nursery adapts to 160 MB.
- **Not taken:** parallel marking with helper threads inside a pause, the least dangerous use of threads (the heap
  is frozen while they run) but of little use to a generational collector, whose full collections are rare and whose
  heaps are small; and concurrent evacuation (ZGC's, Shenandoah's), which needs load barriers on every pointer read,
  a cost on all the immutable data Quest reads, for latency beyond what a compiler and a REPL need.

Nothing here is specific to Darwin: the reserved range is `mmap`, and the frame walk is the one exceptions use.

### 3.11. Why in C, and not in Quest

*Typeful Programming* §9.2 holds that a real language expresses its own run-time system, collector included, and
sketches how: an allocation-free subset (stack-allocated `Still` values, and a compiler check that a module allocates
nothing), unsound modules for the type violations a collector needs (its §9.3), and a thin core of what the language
cannot say. Quest has the unsound modules, and used them once already: the JIT's loader and session are unsound Quest
over a small C core in `quest_code.c`. The collector is nevertheless written in C, decided 2026-11-02, for reasons of
the language as it is rather than of the idea.

**For writing it in Quest:**

- Cardelli's argument: the low-level parts in another language are checked by nothing and blamed on no one;
  `unsound` makes the trust boundary visible (`grep unsound` lists it).
- One set of definitions: the layouts the compilers emit, the block tables, the bitmaps, and the statistics as Quest
  types shared by the compiler and the collector, rather than C structs agreeing with Quest by convention (as
  `repr/runtimeLayout` agrees with `quest_gc.h`, checked by a test); the checking modes in ordinary Quest with the
  compiler's libraries to hand.
- The bootstrap compiles unsound modules, `Word`, and externals already, so a collector in Quest would be in stage 1
  like everything else.
- The JIT shows the shape: the algorithm in the language, the primitives in a core the size of `quest_code.c`.

**Against:**

- **No allocation-free subset.** Quest has neither `Still` types nor the check that a module allocates nothing. Every
  tuple, closure, record, string, and option is a heap allocation; escape analysis stack-allocates what does not
  escape ([ssa.md](ssa.md) §4.2), an optimization and not a guarantee, and a collector that allocates while it marks
  corrupts the heap it is marking. `raise` allocates, so the collector could not raise; a module's initializer
  allocates its record, so the collector's module could not be initialized by the ordinary path. What remains,
  integers, words, `var` locals, pre-allocated arrays, and calls, suffices for a marking loop and forbids every
  structured value, a work-list entry among them.
- **The core stays in C regardless:** saving the registers and walking the stack for roots, `mmap`, fences and
  atomics should a marker thread come, thread-locals. Cardelli's "assembly language insert". The question is only
  whether marking and sweeping, perhaps two thirds of the code, move to Quest.
- **Unsound Quest is C with worse tools:** `value.fetch(addr, displ)` is pointer arithmetic by hand, with no fields by
  name over raw memory, no bitfields, no count-leading-zeros, no `dmb`. *Typeful Programming*'s "memory mapping"
  (its §9.3), a structured view of an unstructured area, is the facility a collector needs most, and Quest has
  nothing for it short of another extension.
- **Two compilers compile it,** and a codegen bug in either becomes heap corruption indistinguishable from a
  collector bug.
- **The inner loops:** bit manipulation and pointer chasing, where clang's output of hand-written C is hard to match.

**Where it lands.** Cardelli's destination, in the wrong order for this tree: the C collector comes first because
there is no allocation-free guarantee to write a Quest one against, and because a working C collector is the oracle a
Quest one would be validated against (the checking modes of §7 already compare one marker's result with another's).
Two of Cardelli's extensions are worth having on their own merits, before any port: the **allocation-free check** for
a module, and a **typed overlay on raw memory** (§9.4). With both in the language, porting the marker and the sweeper
to an unsound module over a C core of a few hundred lines would be a real option.

## 4. Where the Collector Lives

| Component | What it does for the collector |
|---|---|
| `runtime/quest_gc.c` | The heap, the allocation slow path, the barriers' slow paths, marking, sweeping, the stack walk by frame tables, incremental cycles, holds, the statistics, the checking modes, and the runtime's own layouts |
| `runtime/quest_gc.h` (included by `quest_runtime.h`) | `QLayout` and the header's bits; the barriers' inline fast paths; root and frame table registration; `quest_gc_hold`; inline allocation (`quest_alloc`, `quest_alloc_sized`, `quest_alloc_bytes`, `quest_alloc_words`) |
| `runtime/quest_runtime.c` and the files beside it | Allocations by layout; barriers on their stores into existing objects; holds around descriptors' instantiation, dynamic values, directory listings, and the arguments; their roots (`quest_runtime_roots`, `quest_serialization_roots`) |
| `runtime/quest_code.c` | The JIT's data regions as ambiguous roots (`quest_gc_add_roots`) and its own statics (`quest_code_roots`); `quest_value_store`'s card; code regions placed within reach of the heap's tables (`quest_code_reserve`) |
| `repr/objectLayout` (bootstrap: `quest/repr/objectlayout.py`) | The layout of every object generated code allocates |
| `codegen/c/printer` (both compilers) | Layouts as static data, the barriers after stores and around initializing stores (`beginInit`, `begin_init`), the root table |
| `ssa/build`, `ssa/statics` | The same for the SSA's backends; the frame table's placeholder and its registration |
| `ssa/passes/allocations` | The inline allocation sequence ([ssa.md](ssa.md) §4.1) |
| `ssa/passes/escape` | Barrier calls are not escapes; a slot's barriers are dropped ([ssa.md](ssa.md) §4.2) |
| `ssa/barriers` | The compile-time barrier check ([ssa.md](ssa.md) §7) |
| `codegen/arm64/codegen` | Frame tables (`frameSlots`, the call maps, `frameMaps`; [arm64.md](arm64.md) §3.13) |
| `tools/perf/gcstats.py`, `tools/perf/retention.py`, `benchmarks/mlton/allocations.py` | Read the statistics, force collections at fixed points, count allocations by site ([profiling.md](profiling.md) §6) |
| `tools/check` | Runs the suites under the checking modes, and the stress tier first ([testing.md](testing.md) §4.1) |

The interpreters need nothing: they are compiled Quest, and their values are ordinary objects.

## 5. What Programs See

Nothing in the language. Programs see: fast allocation; memory per object up by a word and down by Boehm's rounding;
`identityHash` the address, as before; collections at the same places (allocations). No program held pointers in ways
Boehm tolerated and this collector does not: no Quest program can form a pointer one past an array's end as a loop
bound ([arm64.md](arm64.md) §3.13 forbids the backends to make one too), and where clang forms one from the C
backends' output or in the runtime, the conservative scan takes a word at an object's end as that object's (§3.3), as
Boehm did.

## 6. Decisions

Decided 2026-11-02, with 11 to 14 added and 2, 5, 7, 8 revised after two reviews on 2026-11-03 and the building of
steps 1 to 6 (2026-11-03 to 2026-11-05); the first four shape everything else. On 2026-11-05 the owner chose not to
take the conditional steps (moving, generic layouts, a marker thread) for now (§9).

1. **Precise heap, conservative stack, ambiguous words validated** (§3.3), rather than fully precise (which needs
   stack maps in both backends, a shadow stack for the C one, and layouts for every generic allocation site before
   anything works) or fully conservative (Boehm again). It is the only one of the three that could be built in steps,
   each correct, and conservative Immix measured its cost at about one percent.
2. **Immix mark-region with sticky mark bits, non-moving; evacuation designed and not taken** (§3.5, §3.6, §9.1),
   rather than a copying nursery with a mark-compact old generation (OCaml, MLton, V8). Copying needs every reference
   into the nursery rewritable, which decision 1 cannot promise; sticky Immix bump-allocates without moving, recovers
   space by the line, and is where the throughput is; moving is where the difficulty is (the slot log, forwarding, the
   hash states, pinning that matters), and the Immix paper found it worth a few percent on average.
3. **A header word at a negative offset, holding a layout pointer and flags** (§3.2), rather than a pointer bitmap
   per span set at allocation (Go) or headers inside the structs. The structs, the offsets, and the bootstrap's
   generated C stay as they are; logging and the *old* hint need bits somewhere, and forwarding, pinning, and the
   hash state are reserved beside them; and a layout pointer is 8 bytes either way. Objects stay 8-byte aligned,
   which is all the backends' loads need (§3.2). The mark bit is the exception: it lives in a side bitmap (decision
   12).
4. **One mutator, stop-the-world first, then incremental marking in the mutator thread; a marker thread optional**
   (§3.10, §9.3). Throughput is the goal the benchmarks set, so the collector was built and measured stop-the-world;
   incremental marking bounds the pauses without a thread. The runtime stays single-threaded unless a measurement says
   the mutator is paying for marking a thread could take; parallel marking inside a pause is not taken.
5. **Object logging through the header, and card marking for stores by a slot's address** (§3.5). Logging is precise
   (logged objects are scanned by layout, no card walking) and serves incremental marking too; card marking would
   free the barrier from reading the header but dirties cards on stores into young objects, the common mutable
   stores, and rescans them. The slot barrier marks cards (only for slots in old objects' lines) because a slot has no
   header at a fixed distance and the compiler's large tables, logged whole, were rescanned whole at every minor
   collection (§3.5).
6. **Large objects from 8 KB, in their own runs, never moved; pointer-free objects in their own blocks** (§3.9).
7. **Identity hash is the address** (§3.7). The three-state scheme with a prepended word is designed for moving
   (§9.2); the alternative, a hash field in every object, costs a word on every object for the few that are ever
   hashed.
8. **Runtime metadata stays in the ordinary heap, reached from listed roots** (§3.1, §3.8), rather than an immortal
   space of its own, which existed only to keep address-keyed metadata out of the moving question.
9. **Both compilers emit layouts, barriers, and root tables.** The runtime is shared, so the bootstrap's C must be
   correct under the collector; the inline allocation sequence of the SSA and the stack maps are self-hosted only
   (optimizations, by the two-compilers policy). There is no version of this in which the bootstrap's objects lack
   headers.
10. **libgc is gone.** No fallback collector is kept: a second allocator behind `quest_alloc` would keep every
    representation decision hostage to Boehm's. `--nogc` is the collector never collecting.
11. **Evacuation, if ever taken, runs after marking and never during it, through a bounded slot log** (§9.1). Moving
    as the trace goes, Immix's way, is unsound with ambiguous words inside the heap; two traces are the sound
    alternative, at twice the marking cost of a defragmenting collection.
12. **Marks in a side bitmap; the header's flags in two bytes with one writer each** (§3.2). A full collection clears
    a block's marks at once instead of touching every object, a minor collection's tests of old referents stay in a
    hot structure, and a marker thread would need no atomics.
13. **Generic layouts only after evacuation, on its measurement** (§9.2). They are an ABI change whose benefit, less
    pinning, nothing can measure before evacuation exists; `layouts` counts the ambiguous words meanwhile.
14. **Only live objects validate** (§3.6): the object-start bitmap is intersected with the mark bitmap at the end of
    every collection, so that the marker may trust the precise words of whatever an ambiguous word reaches.

## 7. Risks, and the Checking Modes That Catch Them

The collector's failures are silent and late: a wrong layout or a missed barrier corrupts memory that is read long
after. So the runtime has checking modes, chosen by `QUEST_GC_CHECK` (read by `quest_gc_read_options`), slow but
exhaustive, under which any program, the test suites, and the compiler's own build can run; `tools/check` runs the
suites under them ([testing.md](testing.md) §4.1).

| Mode | What it does | Catches |
|---|---|---|
| `layouts` | After every full collection, walks every live allocation (start bits intersected with marks) by its layout, and after a minor one the young blocks': each precise pointer word is null, outside the heap (static data, code), or points at or into a live allocation; each ambiguous word is counted; sizes agree with the lines marked. Forces a full collection every 64 MB allocated (`QUEST_GC_CHECK_INTERVAL` bytes; at least four times the heap's size, so that the walks stay a fraction of the run) and at exit | A layout that lies about a word, a size, or a length field |
| `report` | Prints at exit the counts per layout: objects, bytes, ambiguous words, and the objects and bytes logged; and the cards marked | Nothing; it says what the heap holds |
| `barriers` | At every minor collection, before the log is used, scans the whole old generation by layouts, and reports an old object that is not logged whose pointer, in a clean card, is at a young object. An ambiguous word is reported only at a young object's start or payload, since a packed integer (a source location's) may fall inside one | A mutating store without a barrier, in generated code or in the runtime's C, an interior store among them |
| `roots` | At every collection, scans the data segment and thread-locals conservatively and reports a heap pointer that no root table or listed root covers, naming the symbol | A global pointer slot missing from a unit's root table or the runtime's lists |
| `poison` | Every reclaimed line and freed large run is filled with a pattern that is never a valid pointer (0x5A bytes) | A use after reclamation, a dead object resurrected |
| `collect` | Forces the collections the other modes would, checking nothing: every `QUEST_GC_CHECK_INTERVAL` bytes, or every `QUEST_GC_COLLECT_EVERY` allocations, with `QUEST_GC_COLLECT_TRAP=k` stopping in `quest_gc_trap` before the kth, for `tools/perf/retention.py` | Nothing; it makes builds of one program collect at the same points |
| `allocations` | Counts every allocation and its bytes by the allocating function and its caller, written at exit to `$QUEST_ALLOCATIONS_OUT`, for `benchmarks/mlton/allocations.py` | Nothing; it says who allocates |
| `incremental` | Keeps a cycle always under way, with a slice of one object (or one piece of a large one) before every allocation and a final pause that gives up after one, and at the end of each cycle's marking marks the same heap again from the same roots with the world stopped: an object that marking reaches and the cycle did not mark is reported, with its allocating functions under `sites`. The cycle's own marks are put back for the sweep. As `stress`, thinned by `QUEST_GC_STRESS_BUDGET`: once the cycles have walked that much heap, a gap of allocations (1024, then doubling) is left between one and the next | A barrier that let an object escape the cycle, an initializing store the log missed, a slice that broke an invariant, at the end of the cycle that lost the object and not when its memory is used again |
| `stress` | Collects before every allocation (`QUEST_GC_STRESS=n`: every nth), minor collections with each sixteenth full, running the other modes' checks at each. The count between collections doubles each time the collections at the current count have walked `QUEST_GC_STRESS_BUDGET` megabytes of heap (256; a collection counts as the heap in use), so a small program is checked at every allocation and the compiler at its first few hundred and then at a thinning sample. The collections fall by count, so a failure repeats; a failing check gives its collection's number, and `QUEST_GC_TRAP=k` calls `quest_gc_trap` before the kth for a debugger | A store without a barrier, a barrier with an allocation between it and its store, an initializing store after a collection, a root left out (a global, a stack map's slot), each within a few allocations of the fault, in generated code, the runtime, serialization, and the JIT |
| `sites` | Keeps, by each object's address, the three functions above its allocation (from the frame records, in a table outside the heap), and a failing check names them for its object and for the object its word points at | Nothing; it says which code made the objects a report is about |

Modes combine (`QUEST_GC_CHECK=layouts,poison`), and `stress` with `barriers`, `roots`, and `poison` is the one that
finds the most: `tools/check` runs the compiled tests under it, with `sites`, before its suites, and the suites under
`layouts,roots,poison,barriers`. `QUEST_GC_CHECK_CHILDREN` gives the modes of the programs a program runs, in place of
its own, so that a compiler runs under the plain checks and the test it builds and runs under `stress`. Under any
mode every allocation takes the slow path, which counts it. `QUEST_GC_STATS=1` (a summary at exit) and `each` (a line
per collection too, a minor one's with its phases' times) report what the collector did, under a mode or not: the
collections of each kind and their pauses, what survived, the objects logged and the cards marked, and the frames
scanned by map and whole; `tools/perf/gcstats.py` reads the lines. The checks are in the runtime, so the bootstrap's C
and the JIT's code are checked by the same code as the self-hosted backends', and the interpreters' transcripts can
run under them too.

The risks themselves:

- **A layout that lies** (a pointer word described as scalar) is a leak at worst while nothing moves, and memory
  corruption should anything move. `layouts` checks every object at every collection it runs.
- **A missed barrier** on a store the backends did not classify, an interior store that found the wrong header, or
  one of the runtime's pointer stores into an existing object, loses a young object. `barriers` finds it by
  exhaustion, `stress` makes it find one within a few allocations, and `ssa/barriers` rejects at compile time the
  SSA's stores of a pointer owed a barrier. The three checks found different faults: `barriers` the case binder's
  payload (§3.5); `stress`, on its first runs, 30 of the bootstrap's compiled tests and 17 of arm64's failing, from
  barriers placed before their stores, an aggregate with two literals logged one collection late, the runtime's
  descriptor and serialization code storing values computed after the barrier, the arguments parked in `malloc`ed
  memory, and a root left out (§8.4); `ssa/barriers` nothing on the compiler's source, once it read a barrier that is
  its function's tail call.
- **A dead object resurrected** by an ambiguous word, its stale precise words followed into reused memory, is the
  failure decision 14 prevents; `poison` makes it loud if the intersection is ever skipped.
- **A wrong stack map** (a slot or register left out of a call's map) frees a live object; `stress` with `poison`
  finds it at the first collection that falls inside the call, as it found the allocation's base kept as a `ptr`
  (§3.4). A live value in a caller-saved register across a call is refused when the maps are computed.
- **Fragmentation** that line recycling does not recover leaves the heap larger than its live data; live lines
  against live bytes are about 2 (§8.4), and moving is the answer if they grow (§9.1).
- **Linux.** Nothing in the design is Darwin's, and nothing in it may become so; the C backend's Linux build keeps
  conservative stacks. There is no Linux machine to test on, so the Linux build is kept compiling by inspection and
  by the conditionals the runtime has, and running it waits until one exists.
- **An interrupted mark** that misses an object is a lost object, found late; `incremental` finds it at the end of
  the cycle it happened in, by comparing with a stop-the-world mark.

## 8. Measurements

The collector was built in six steps, each correct on its own, each ending with `tools/check` passing under the modes
that applied and with its measurements, which [benchmarks.md](benchmarks.md) §16 to §19 record in full. The steps
were built and measured from 2026-11-03 to 2026-11-05 and replayed onto `main` as step 1 `fc39f38f`, 2 `67f30479`, 3
`ef209c78`, 4 `feef499e`, 5 `d55564b3`, and 6 `aaa7149e` (ABI 73 at the end).

### 8.1. Step 1: layouts and headers, on Boehm (2026-11-03)

Headers and layouts first, on Boehm, with `layouts` checked against `GC_base`. What the headers cost, measured by the
runtime's counters (`QUEST_GC_CHECK=report`) over the allocation-heavy MLton benchmarks at scale 0.25, with the
design's growth as 8 bytes per object (16 per sized one) and Boehm's as its 16-byte granules with the header against
without:

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

The benchmarks' objects are small (a cons cell is 16 bytes, two words), so the header is a third to half again on
them; the compiler's are larger, and its growth a fifth. Under Boehm the growth was what the granules made of it,
between nothing (imp-for's 8-byte objects were already rounded to 16) and 63 percent (zebra's 24-byte objects became
32 after rounding to 48). Boehm resurrected a dead object that a stale stack word pointed at, with the words it died
with (one in fifty million words on the compiler's own build), which is why decision 14 matters to a collector that
validates by start bits.

### 8.2. Step 2: barriers and root tables, logging only (2026-11-04)

The barriers as counting stubs, on the allocation-heavy MLton benchmarks at scale 0.25 (`QUEST_GC_CHECK=report`).
Every one was on an object; no benchmark stores a pointer through a slot, and the compiler's own build made 160
million object barriers compiling `ir/lower.mod.quest` and none through a slot.

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

So the barrier's fast path matters to the compiler and to the array-heavy benchmarks, and a generational collector
logs few objects on the rest.

### 8.3. Step 3: the collector, stop-the-world, non-generational (2026-11-04)

[benchmarks.md](benchmarks.md) §16, on a loaded machine: the MLton suite at scale 0.25 against §13's Boehm times took
0.79 of the time through C (0.69 by processor time), 0.89 through ssac (0.69), and 0.88 through arm64 (0.82), the
allocation-heavy programs halving (wc-scanStream 0.39, tensor 0.40, barnes-hut 0.48, logic 0.49 on C); against MLton
the suite went from 0.69 to 0.54 of its time on C, 0.55 to 0.49 on ssac, and 0.72 to 0.63 on arm64. The inline
sequence against the call of the slow path, on arm64, was 0.99 over the suite by processor time and 0.77 to 0.88 on
the allocation-heavy programs. Two programs lost, imp-for (1.85 on C), a billion one-word boxes, and matrix-multiply
(1.39 on C), which hardly allocates; their inner loops are the same instructions whatever the allocation sequence, and
their times swing by 40 percent with where clang places `main`'s loops, so the ratios measure code placement, and the
sequence's own cost against `GC_malloc`'s call is at most 1.6 ns per allocation. The compiler's own build (`-j 8`)
took 0.83 of its wall time and 0.77 of its processor time, and three times the memory: the trigger counts a block with
one live line as in use and doubles the blocks in use, which after the compiler's collections were 3.2 times its live
lines and 6.6 times its live bytes, and one process building the driver reached 9.9 GB of blocks for 848 MB live, with
23 collections pausing 5.0 s in all and 994 ms at the longest. Generations brought both down (§8.4).

### 8.4. Step 4: generations (2026-11-05)

[benchmarks.md](benchmarks.md) §17: through C the suite is level with step 3 (geometric mean 0.99 by wall time and
0.98 by processor time), through ssac 0.95 and 0.96, and through arm64 0.93 and 0.95, which is 0.54, 0.47, and 0.59 of
MLton's time; the compiler's own build takes 22.6 s against 23.3 (0.97) in 1.39 GB against 3.77 (0.37), and in one
process has 271 minor collections pausing 2.3 s in all and 27 ms at the longest, and 9 full ones pausing 1.75 s in all
and 876 ms at the longest. The nursery's size decides this (§3.6): with the 8 MB first tried, the suite lost 3 percent
to step 3 through C and the compiler's build 5 percent; the ten programs that lost most gain steadily with a larger
nursery (0.97 of their time at 16 MB, 0.95 at 32, 0.93 at 64, 0.91 with no minor collections; benchmarks.md §17.2).
ssac's two worst programs against step 3 (model-elimination 1.38, psdes-random 1.26) are the inline allocation
sequence's, which ssac's suite had for the first time: over the whole suite the sequence against the calls is 1.00,
from 0.69 (wc-scanStream) to 1.39, and ssac keeps it, since it is the path arm64 takes, which ssac is there to test.

Fragmentation: live lines against live bytes is 2.1 (1,067 MB in 2,259 MB of lines) after the compiler's build (`-j
1`) and 2.2 after a REPL session of the transcripts of `tests/repl` replayed twenty times (4.4 GB allocated; 22 minor
collections pausing 38 ms in all and 8 full ones pausing 15 ms, 3.4 ms the longest of either; 13.1 MB live in 28.5 MB
of lines).

What the checks found while this step was built, besides the rules of §3.5 it produced: three passing runs of the
whole check left dozens of stores whose barrier was wrong only when a collection fell inside one particular call,
which the `stress` mode, built for this, found within a few hundred collections each; a record-dictionary entry of
three words that took one slot barrier and lay across two cards; serialization's witness stack in no root list; and
the `allocations` mode's frame walk one frame off wherever the compiler had inlined the check's tick, which is kept out
of line.

### 8.5. Step 5: arm64 stack maps (2026-11-05)

[benchmarks.md](benchmarks.md) §18: through arm64 the suite is level with step 4 (geometric mean 1.00), mpuz at 0.91
without the dead slots' clears and psdes-random at 1.22 by a pair of stores the object's base let the backend merge;
the compiler built by arm64 and building itself keeps 1,062 MB live at most against step 4's 1,083 (0.98) and 1,140
with the tables unread (0.93), in the same time; the tables are 822 KB, 13 percent of the code, and the code 125 KB
smaller without the clears. The table is in `__TEXT,__const`, its addresses differences the linker resolves, so it
costs nothing at startup.

### 8.6. Step 6: incremental marking (2026-11-05)

[benchmarks.md](benchmarks.md) §19: the suite is level with what came before (1.00 through C against step 4, 0.99
through arm64 against step 5); the compiler's own build takes the same time in one process and in eight, with 3
percent more in blocks at the most; its longest full collection's pause goes from 660 ms to 12 ms, the 12 being the
last collection that stopped the world, with first pauses of 1.3 ms at most, slices of 2.5 ms, and last pauses of 2.3
ms, none retried; 41 MB is allocated in a cycle, which is the nursery's growth during one; a REPL session's full
collections are 2 ms and stop the world, and as cycles have no pause over 0.65 ms. The pause's condition came from the
suite's first taking, with every full collection the heap asked for a cycle: 1.02 of step 4's time through C over the
46 programs, and 1.17 on tailmerge (§3.10); a faster pace only shrinks the loss (1.06 at 16, 1.04 at 64). The pace (4
bytes marked for a byte allocated), the allocation between slices (32 KB), a slice's most (1 MB), and a piece (128 KB)
are those the first numbers were taken with; the two bounds came from them: a slice that met a table of a million
words took 13 ms, and one that followed a 4 MB allocation 16 ms. `incremental` passed on its first run; `roots`, in
the stress tier, found the two statics of the piecewise scan holding heap addresses unlisted.

## 9. Open Work

Three steps were designed with the collector and left conditional on measurements; on 2026-11-05 the owner chose to
take none of them for now. Their designs stay here so that nothing built since is built in their way: the header's
bits are reserved for them (§3.2), and decisions 11 and 13 fix their order. §9.4 holds the language facilities a
collector in Quest would need, and §9.5 and §9.6 two smaller items: barrier fast paths tried and not kept, and the
growth target.

### 9.1. Evacuation

The case for it is §3.6's: minor collections scatter small survivors over nearly every block they filled, and only
moving them gives the blocks back whole; the measured ratio of live lines to live bytes (about 2, §8.4) is not by
itself a case. Its design:

- **It runs in a full collection, after marking and never during it.** Candidate blocks are chosen before marking by
  fragmentation (live lines against free, from the last sweep), as Immix. Marking moves nothing: it pins what
  ambiguous words reach (the *pinned* bit), and it records in a *slot log* the address of every precise word (in the
  heap, a root table, or a listed root) that refers into a candidate block, a log proportional to the references into
  the candidates, a small part of the heap, kept outside the heap. When marking is done the live bytes of each
  candidate are exact, so the collector takes the candidates it can empty into the free blocks it holds, copies their
  unpinned live objects to fresh holes, marks each old copy *forwarded* with the new address, rewrites the logged
  words (a logged word is rewritten only if it still refers to a forwarded object, and one inside an object that
  itself moved is rewritten in the copy, keeping its offset and tag), and clears the mark bits, start bits, and line
  marks of the old copies, leaving the pinned objects' lines. If the log reaches its bound, the candidates it does not
  cover stay in place, so the collection degrades to a non-moving one rather than failing; this is G1's remembered set
  for its collection set, built during marking. In an incremental cycle it stays inside the final pause, with the slot
  log built by the slices and finished by the final rescan.
- **Why not during marking:** moving as the trace goes, as Immix proper does, would be unsound here: an ambiguous
  word found after its referent moved could neither be rewritten (it may be an `Int`) nor have the move undone. The
  other sound order, two traces (mark and pin, then trace again copying), is simpler and doubles the marking of a
  defragmenting collection; the log is preferred because evacuation then costs in proportion to what moves.
- **What never moves:** pinned objects, large objects, and the runtime's metadata, which is keyed by address: it
  would be allocated pinned at birth into blocks of its own, a third cursor beside the noscan one, so that it neither
  moves nor pins lines of other blocks (`quest_alloc_pinned`).
- **What pins:** the stack's conservative frames (C-built units', the runtime's), a mapped frame's memory-class
  slots, a callee-saved register saved by an unmapped frame (§3.3), the JIT's data, and ambiguous words in the heap.
  The compiler, whose data lives in `vector.T(A)` and `hashMap.T(K V)`, would pin a great deal through the last of
  these (§9.2).
- **Checking:** under `stress`, each full collection would take every block as a candidate with the slot log
  unbounded, so every object that may move does, and the vacated memory is poisoned and, in large runs, unmapped,
  catching a stale address kept across an allocation.
- **Done when** the suites, the transcripts, and the driver's build pass under `stress,barriers,incremental`,
  `identityHash` is stable under a test that forces moves, and fragmentation before and after, the slot log's size,
  and the pinned fraction after long compiler runs are recorded, the last by what pins it, or the idea is dropped with
  its measurement.
- **Where to start:** this section and §9.2's hash and serialization, and the header's reserved bits in
  `runtime/quest_gc.h`.

### 9.2. The identity hash under moving, and generic layouts

- **The hash:** the two hash bits of the mutator's header byte are *unhashed*, *hashed*, *moved*. `identityHash` of
  an unhashed object sets *hashed* and returns the mix of its address; of a hashed object, the same; of a moved
  object, the mix of the word at the address minus 16, where the collector put the original address when it copied
  the object (it allocates the copy 8 bytes larger, writes the old address before the header, sets *moved*; a further
  move copies that word along), which keeps every object's alignment. Pinned objects are never copied, so their
  addresses stay their hashes. An interior object (an embedded box, a record's payload) shares its allocation's
  header and states, so hashing it sets the allocation's state (found through the object-start bitmap), and its hash
  after a move is the mix of the allocation's old base plus the object's offset, which a copy preserves. `is` needs
  nothing: it compares current addresses, which the collector keeps consistent by rewriting every precise reference
  and moving nothing an ambiguous one reaches.
- **Serialization** keys its sharing table by address (`quest_ptr_hash`) and allocates its output as it walks, and
  its nodes' `ptr` words are precise, so a move would rewrite them while each node stayed in the bucket of the old
  address. The collector would keep a hold count (`quest_gc_hold_moves`, released when the walk ends, by a raise
  included) under which no collection evacuates, and serialization would take it for the walk. Keying the table by
  identity hash would work too.
- **Generic layouts** (decision 13), taken when evacuation's pinned fraction on the compiler's build shows it held back
  by ambiguous words in the heap: the analysis that gives a polymorphic function its descriptor parameters
  (`DescriptorParam`) extends to a function that allocates an aggregate holding type-parameter words, and such a site
  builds its layout from the descriptors through an inline cache (a comparison of the descriptors with the last seen,
  then the cached layout). Descriptors are passed only where an allocation or a descriptor needs them, as now; the
  specializer's clones need none. An ABI change, in both compilers. *Done when* `layouts` reports the ambiguous words
  of the compiler's build and of the suite before and after, the pinned fraction is recorded against evacuation's,
  and the cost of the added descriptor arguments on the MLton suite is recorded, or the idea is dropped. *Where to
  start:* `repr/objectLayout` in both compilers.

### 9.3. A marker thread

The slices of §3.10 on a thread of their own, Riptide's and Go's way, so that marking leaves the mutator's core.
Everything in §3.10 stays; what the thread adds is the race between it marking and scanning an object and the mutator
storing into it and reading its mark as not yet set, resolved by the marker setting the mark, fencing, then scanning,
and the mutator's barrier storing, fencing, then reading (`dmb ish` on arm64, a locked instruction on x86-64, paid
only inside the slow path of a running cycle; the header's two flag bytes have one writer each, §3.2, so no atomic
read-modify-write is needed), plus a protocol for the structures both read while the mutator allocates (the
object-start and mark bitmaps, the line marks, the log), written down before it is coded. Go keeps the incremental
slices as mutator assists even with its marker threads, so nothing of §3.10 would be undone. A checking mode,
`concurrent`, would run as `incremental` with the marker forced to yield between objects. Taken only if a measured
workload shows the mutator paying for marking it could offload; on 2026-11-05 none did (§8.6: the compiler's build
takes the same time with cycles as without). *Done when* such a workload is measured and the thread recovers what it
pays, or the idea is dropped. *Where to start:* the protocol, written down, then the `concurrent` mode beside
`incremental` in `runtime/quest_gc.c`.

### 9.4. Language facilities a collector in Quest would need

From §3.11, worth having on their own merits: an **allocation-free check** for a module, cheap given the IR after
escape analysis and useful for the inlined externals and for loops that must not allocate; and a **typed overlay on
raw memory**, a `Still`-like view of an address as a record of words, which would make `os/value` code readable (the
JIT's session reads record payloads by hand-computed offsets, as `os/value.fetch` does). Neither is started.
*Where to start:* the IR after escape analysis, for the check; *Typeful Programming* §9.2 (`Still` values) for the
overlay. *Done when* either facility exists with tests, or the idea is dropped.

### 9.5. The write barriers' inline fast paths, tried and not kept

The arm64-built compiler spends time in `quest_barrier_slot` and `quest_barrier_object`, called out of line at every
barriered store. Inlining their fast paths (an SSA expansion after the barrier rule's check, in arm64's and the JIT's
code) took `quest_barrier_slot` from 924 of the compiler's samples to 27, but made the compiler 1.3 percent slower
(0.9 percent with the slot barrier alone inline) and its text 1.8 percent larger, and the suite didn't move
([benchmarks.md](benchmarks.md) §22.2, item 3). It wasn't kept. It may pay once the code around a barrier is shorter,
or with a smaller expansion: only in loops, only the slot barrier, or a shared out-of-line tail.

*Where to start:* branch `claude/inline-barriers-not-kept` on origin (`87acb5e7`, on `238a594f`):
`questlang/ssa/writeBarriers` and its test `ssa_write_barriers`, the runtime's entries in `codegen/runtimeFunctions`
and `codegen/runtimeLayout`, and the pipeline's call. It predates the restructuring: the pass belongs in
`questlang/ssa/passes/`, and `runtimeLayout` is now `questlang/repr/runtimeLayout`. *Done when* a variant makes the
compiler or the suite faster, measured as benchmarks.md §22.1 measures, and is kept, or the idea is dropped and the
branch with it.

### 9.6. The growth target counts a recyclable block as wholly in use

After a full collection the heap may grow to `Q_GC_GROWTH` times the blocks in use (the target `quest_gc_sweep` sets
in `runtime/quest_gc.c`), and a recyclable block with one live line counts as a block in use, so a heap of mostly
empty recyclable blocks collects more often than its live data warrants ([benchmarks.md](benchmarks.md) §16.3).

*Where to start:* the target's computation after the sweep, which could count a recyclable block's free lines (its
holes) as free, as the allocator does (§3.1). *Done when* the target counts holes as free, and the suite and the
compiler's timings (benchmarks.md §16.1) are no worse.

*Tried 2026-11-25, not kept* ([optimization-experiments.md](optimization-experiments.md) §5.9). Two targets were
measured on the compiler: the blocks in use plus the live lines, and twice the live lines. They saved 10% and 23% of
peak memory, for 3–5% and 9–11% more cycles. barnes-hut's heap now stays at the floor.
