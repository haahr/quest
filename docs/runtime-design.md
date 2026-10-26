# Quest Compiled Runtime Architecture (`runtime-design.md`)

This document explains the runtime representation and object model used by the Quest compiler—both in the current C99
backend ([c-representation.md](c-representation.md)) and in the planned native AArch64 backend ([roadmap.md](roadmap.md)
Steps 6–7).

If you are familiar with compiling either ML-family languages (which have parametric polymorphism and algebraic data
types, but no subtyping) or object-oriented languages (which have nominal subtyping and method tables, but usually not
higher-order structural subtyping), Quest sits at a fascinating intersection. Understanding how its runtime
representations fit together is the key to understanding the compiler's backend.

---

## 1. The Compilation Puzzle: Why Quest Is Subtle

Quest combines five language features that pull data representations in different directions:

1. **Higher-Order Parametric Polymorphism ($F_{<:}^\omega$):** A polymorphic function `All(A::TYPE) ...` or type
   operator `Fun(A::TYPE) ...` is compiled once without knowing what `A` will be. In generic code, values of type `A`
   must have a uniform representation so they can be passed in registers, stored in tuples or arrays, and returned.
2. **Structural Width and Depth Subtyping:**
   - A record `{x: Int, y: Real, z: String}` is a subtype of `{x: Int, z: String}` (**width**) and `{x: Super}`
     (**depth**), even though the two record types have completely different field layouts in memory. Looking up `.z` at
     a statically unknown offset cannot use a fixed struct displacement.
   - A tuple `Tuple Int Record x: Int y: Int end end` is a subtype of `Tuple Int Record x: Int end end`.
   - A variant `Variant b: Int c: String end` is a subtype of `Variant a: Bool b: Int c: String end`, and an option
     `Option b c end` is a subtype of `Option a b c end`. Because variant and option types are equal regardless of the
     order in which their cases are written ([type-system.md §6.8](type-system.md)), canonical shapes order cases
     alphabetically by name; upcasting to a supertype that inserts earlier case names shifts tag indices, while
     `ordinal(o)` counts in the declaration order of the static option type at the use site.
   - Function types `All(x: S) T` are contravariant in parameters and covariant in results.
3. **Mutable State (`var`) and Object Identity (`is`):**
   - Records, tuples, and local scopes can have mutable `var` fields or components (`r.x := 10`, `t.a := 20`), and can
     pass mutable locations by reference (`:var` and `:out` parameters).
   - Cardelli's identity operator `is` tests whether two non-scalar values (strings, records, tuples, variants, options,
     arrays, closures) are the **same memory location** (*Typeful Programming* §3.1).
   - Together, `var` and `is` forbid the classic functional-language trick of implementing depth subtyping by
     *allocating a converted copy* on upcast: if you copy a tuple or record when coercing it to a supertype, `sub is
     sup` becomes `false`, and mutating a `var` field through the supertype view fails to update the original object!
4. **Bounded Quantification (`A <: B`):** A function `All(A <: Point) All(p: A) A` knows that `A` is *some* subtype of
   `Point`, so inside the body it can project `p.x` as a `Point`, yet it must return the original `A` intact.
5. **Intensional Type Analysis (`auto`, `inspect`, `Dynamic`):** Programs can package a value with its runtime type
   (`auto :T with v end` or `dynamic.new(:T v)`) and later branch on full structural subtyping at runtime (`inspect`),
   or serialize and deserialize cyclic object graphs (`dynamic.extern` / `dynamic.intern`).

---

## 2. The Four Pillars of the Runtime Representation

Quest resolves the tension between fast monomorphic code, uniform polymorphic code, structural subtyping, and mutable
object identity through four cooperating mechanisms. The representation pass (`quest/ir/represent.py`,
[ir.md §8.4](ir.md)) and descriptor pass (`quest/ir/describe.py`, [ir.md §8.5](ir.md)) make all four explicit before
code emission:

| Mechanism | Size | Role |
| :--- | :--- | :--- |
| **1. Evidence-Passing** (`QRecordVal`, `QVariantVal`) | 16B (2 regs) | $O(1)$ record offset dicts; unboxed variants. |
| **2. Uniform 1-Word Slots** (`slot_representation`) | 8B (1 word) | Native & `QVal` layouts match; zero-copy casts. |
| **3. Tagged `QProxy` Views** (`QUEST_PROXY_TAG = 1`) | 8B tagged ptr | Upcast tuples/options keep `is` & `var`. |
| **4. `QTypeDescriptor`s** (`ir_described`) | 8B pointer | Runtime subtyping (`inspect`) & serialization. |

Let's look at how each piece works and why it was chosen over the alternatives.

---

### 2.1. Evidence Passing for Records and Variants (16-Byte Register Pairs)

In registers, local variables, function parameters, and return values, most Quest types occupy a single 64-bit word:
- Scalars (`Int`, `Real`, `Bool`, `Char`, `Ok`, `Word.T`) sit directly in a register.
- Heap aggregates (`Tuple`, `Option`, `Array`, `String`, `QClosure *`, `QAutoVal *`) are 64-bit heap pointers.

**Records** (`QRecordVal`) and **Variants** (`QVariantVal`), however, are represented in value positions as **16-byte
two-word structs** passed and returned in two registers (`x0` and `x1` on AArch64):

1. **Records as Fat Pointers (`QRecordVal = { void *val, const void *dict }`):**
   - `val` points to the heap-allocated record struct (whose first word is a `QRecordHeader` pointing to the record's
     creation-time `QTypeDescriptor`, followed by one 8-byte slot per field).
   - `dict` points to a compile-time **offset dictionary** (`OffsetDict_<RecordType>`) containing `size_t` byte offsets
     for every field visible in the static record type.
   - **Width subtyping** (`{x: Int, y: Int, z: Int} <: {x: Int, z: Int}`) simply pairs the *same* `val` pointer with a
     new static `dict` containing the offsets of `x` and `z` inside the 3-field struct. The heap object is never copied,
     `is` compares `r1.val == r2.val`, and `var` field writes (`*(T *)((char *)r.val + r.dict->offset_x) = v`) mutate
     the original struct in $O(1)$ time.
2. **Variants as Unboxed Tagged Values (`QVariantVal = { int64_t tag, QVal payload }`):**
   - `tag` holds the 0-based alphabetical index of the active case in the current static `Variant` type; `payload` holds
     the 8-byte boxed slot for the case payload.
   - **Variant subtyping** (`Variant a: Int b: String end <: Variant a: Int b: String c: Bool end`) remaps `tag` in
     $O(1)$ time via a static lookup table `tagmap_<Target>_<Source>[v.tag]`, and converts `payload` if the active
     branch's payload type also narrows by depth subtyping.

---

### 2.2. Uniform 1-Word Aggregate Slots (`slot_representation`)

What happens when a 16-byte `QRecordVal` or `QVariantVal` is placed *inside* another data structure—as a tuple
component, a record field, an option payload, or an array element—or passed as a generic type parameter `A::TYPE` where
`A` is erased to the 8-byte `QVal` union?

If native aggregates embedded 16-byte `QRecordVal` structs inline while generic aggregates (`Tuple A Int end`) used
8-byte `QVal` slots, then `Tuple Record x: Int end Int end` (24 bytes) and `Tuple A Int end` (16 bytes) would have
incompatible memory layouts. Passing an array or tuple of records to a polymorphic function would require allocating a
deep copy on entry and copying back on exit—and for a mutable `Array(R)` or a tuple with a `var` field, copying breaks
aliasing and mutability!

Quest solves this cleanly with **uniform 1-word aggregate slots** (`slot_representation` in `quest/codegen/layout.py`):
- **Every aggregate slot is one 64-bit word (8 bytes).**
  - In a native aggregate slot, a record has C type `QRecordVal *` and a variant has C type `QVariantVal *`—a pointer to
    an immutable 16-byte heap box (`quest_box_record` / `quest_box_variant`).
  - `Bool` and `Char` use 64-bit `QBoolSlot` (`uint64_t`) and `QCharSlot` (`uint64_t`) in aggregate slots and `var`
    locations so that taking the address of a mutable slot (`:var Bool`) yields the same 8-byte cell width as `QVal *`.
  - In a generic (`QVal`) slot, a record or variant is that exact same pointer stored in `qval.p`, and a `Bool` or
    `Char` sits in the same 64-bit word.
- **Why this is a huge win:**
  - **Locals, parameters, and return values stay unboxed** (`QRecordVal` and `QVariantVal` in register pairs), so
    ordinary code that creates, passes, or returns records and variants does not heap-box them.
  - **Every aggregate has identical memory layout in native and generic views.** A `Tuple Int Record x: Int end end` is
    two 8-byte words (`{ int64_t _0; QRecordVal *_1; }`), which has the exact same size and field offsets as
    `Tuple A B end` (`{ QVal _0; QVal _1; }`).
  - **Polymorphic boundary crossings for both unbounded (`A::TYPE`) and bounded (`A <: B`) type parameters are
    zero-cost!** Generic code holds values of bounded type parameters at their own view (their type argument's view)
    in the bound's representation and reads their bound's fields or cases through a memoized `QViewMap`
    (`quest_view_map(descriptor_A, &quest_type_B)`). Passing a `Tuple(R)`, `Option(R)`, `Record`, or `Array(R)` to
    polymorphic code requires no element-by-element copying and preserves `var` aliasing and `is` identity directly.
  - Even when allocating an aggregate with `N` boxed record/variant slots, `ir/represent.py` coalesces the struct and
    its `N` 16-byte boxes into a **single contiguous allocation** (`embedded` boxes), avoiding extra allocator calls.

---

### 2.3. Tagged `QProxy` Views on Tuples and Options

Uniform 1-word slots make generic/native conversions free, and `QRecordVal`'s `.dict` pointer handles record width
subtyping. But what about **depth subtyping** when an aggregate's component changes representation?

Consider:
```quest
Let SubRec = Record x: Int y: Int end
Let SupRec = Record x: Int end
let tSub: Tuple var r: SubRec end = tuple let var r = record x = 1 y = 2 end end
let tSup: Tuple r: SupRec end = tSub   (* depth + mutability forgetting upcast *)
```
Here `tSub._0` holds a `QRecordVal *` whose `.dict` is the 2-field dictionary for `SubRec`, whereas code reading
`tSup._0` expects a `QRecordVal *` whose `.dict` is the 1-field dictionary for `SupRec`. Even more importantly:
- `tSup is tSub` **must evaluate to `true`** (it is the same tuple!).
- If someone mutates `tSub.r := record x = 99 y = 100 end`, reading `tSup.r.x` **must see `99`!**

The same issue arises when a tuple or option component undergoes:
- record depth subtyping (new `.dict`),
- variant or option tag remapping (when a supertype inserts earlier alphabetical case names),
- tuple or option depth subtyping, or
- function contravariant/covariant adaptation (wrapping a `QClosure *` in an adapter closure).

Why not make every tuple and option a 16-byte fat pointer like `QRecordVal`? Because a record's `.dict` only maps field
names to byte offsets; a tuple's fields are already at fixed offsets `_0`, `_1`, ... unless a component *itself* needs a
conversion function. Turning every tuple and option into a 16-byte fat pointer would double the register pressure of
every tuple and `maybe.T(A)` option in the language just for the rare case of a depth-upcast tuple/option.

Instead, Quest keeps tuples and options as **single 8-byte pointers**, and uses a **low-bit pointer tag
(`QUEST_PROXY_TAG = 1`)** when a view-changing upcast occurs (`QProxy` in `runtime/quest_runtime.h`):

```c
#define QUEST_PROXY_TAG ((uintptr_t)1)

typedef struct QProxy {
    void *orig;                  /* Root unproxied heap tuple or option (for `is`, hash, and var writes) */
    void *stored;                /* Immediate wrapped tuple/option at the representation `view` expects */
    QVal (*view)(void *stored, int64_t index, const void *tags);  /* Per-component view converter */
    const void *tags;            /* Optional tag-remap table for variant components */
    QVal *cache;                 /* Memoized converted values for immutable components */
    uint8_t *cached;             /* Per-slot memoization flags */
} QProxy;
```

How `QProxy` works across the runtime:
1. **Creation (`quest_make_tuple_proxy` / `quest_make_option_proxy` / `quest_convert`):**
   When a `Convert` in `ir/represent.py` upcasts a tuple or option and at least one component changes view or an option
   case's index shifts (or when a value of a bounded type parameter `A <: B` is explicitly upcast to its bound `B` via
   `quest_convert`), it allocates a `QProxy` and returns `(T *)((uintptr_t)proxy | QUEST_PROXY_TAG)`.
   - `proxy->orig` always chases through any inner proxy to point directly to the underlying concrete heap object.
   - Pure width subtyping on a tuple (dropping trailing components where all kept components have identical
     representations) or an option upcast where all subtype cases keep their indices and payload views (e.g.
     `Option a b end <: Option a b c end`) does **not** allocate a proxy—it is a plain C pointer cast!
2. **Reading (`via proxy` vs. `direct`):**
   - If a tuple/option type can never hold a proxy (`type_may_be_proxied(T)` is false—e.g., `Tuple Int String end`,
     whose components have no subtypes), `ir/represent.py` marks every `Field` and `Tag` access as **`direct`**: a
     single C struct load `p->_0` with zero tag checks!
   - If `type_may_be_proxied(T)` is true, `Field` and `Tag` are marked **`proxy`**:
     - Fast path (`!quest_is_proxy(p)`): a single low-bit test (`((uintptr_t)p & 1) == 0`, ~3–6% overhead in tight
       loops) followed by a direct load `p->_0`.
     - Slow path (`quest_is_proxy(p)`): calls `quest_proxy_field(p, i, is_mutable)` (or `quest_option_tag(p)`). For an
       **immutable** component, the converted view is computed once by `proxy->view` and memoized in `proxy->cache[i]`
       (so repeated projections return the identical converted pointer, preserving `t.f is t.f`). For a **mutable**
       (`var`) component, `view` re-reads the live slot from `stored` every time so mutations are immediately visible!
3. **Writing (`quest_proxy_store`) and `@t.f` (`via original`):**
   - Because Quest's `Var(T)` is invariant in `T`, a `var` component can only be *written* or taken by reference
     (`@t.f`) at its exact original type `T` (mutable fields can only be forgotten to read-only fields on depth upcast,
     never widened mutably).
   - Therefore, any write or `@t.f` address calculation simply strips the proxy via `quest_unproxy(p)` (`proxy->orig`)
     and accesses the root struct at offset `_i` (`via original`)!
4. **Object Identity (`is` and `hash.identityHash`):**
   - Pointer equality (`quest_val_is`) and `quest_identity_hash` call `quest_unproxy(p)` on both operands before
     comparing addresses. Thus `tSup is tSub` is always `true` in $O(1)$ time.

---

### 2.4. Runtime Type Descriptors (`QTypeDescriptor`)

For `auto` values, `dynamic.T`, `inspect` typecase, and existential tuple witnesses, the compiler reifies static types
into runtime `QTypeDescriptor` graphs (`runtime/quest_runtime.h`, materialized by `quest/ir/describe.py`):
- **Closed types** become `static const QTypeDescriptor` globals emitted once per compilation unit.
- **Polymorphic functions** that construct descriptors mentioning a type parameter `A` receive an implicit
  `const QTypeDescriptor *descriptor_A` argument (or closure environment field) and instantiate a parameterized
  descriptor template at runtime (`quest_instantiate_descriptor`), memoized by argument descriptors.
- **Amadio–Cardelli Coinductive Runtime Subtyping:** `quest_is_subtype(sub, sup)` runs the full coinductive subtyping
  algorithm at runtime over `QTypeDescriptor` graphs, handling recursive types, type operators, record width/depth,
  tuple width/depth, variant/option subsets, and function variance ([dynamic.md §1](dynamic.md)).

---

## 3. Memory Management

Quest is a garbage-collected language with mutable references (`var`) and cyclic data structures (such as recursive
functions, doubly-linked structures, and self-referential records).

1. **Primary Collector: Boehm-Demers-Weiser Conservative GC (`libgc`)**
   - Pointer allocations (`quest_alloc(size)`) route to `GC_MALLOC(size)`, which zero-initializes memory and scans it
     for outgoing pointers.
   - Pointer-free leaf allocations (`quest_alloc_atomic(size)`—used for `String` character buffers, primitive arrays
     `Array(Int)` / `Array(Real)` / `Array(Bool)` / `Array(Char)`, and captured exception stack traces) route to
     `GC_MALLOC_ATOMIC(size)`, avoiding conservative pointer scanning inside binary/string payloads.
2. **Fallback Mode (`--nogc`):**
   - Compiling with `--nogc` defines `-DQUEST_NOGC`, routing `quest_alloc` and `quest_alloc_atomic` to standard
     `calloc(1, size)` so binaries can be built and tested on hosts without `libgc` installed.

---

## 4. Target ABI & AArch64 Register Mapping

Both the C99 backend (via the platform C compiler) and the planned native AArch64 backend (Steps 6–7) follow the
standard ARM64 **AAPCS64** calling convention:

| Register(s) | AAPCS64 Role | Quest Runtime Usage |
| :--- | :--- | :--- |
| `x0` – `x7` | Argument & Return | Closure `env` in `x0`, then descriptors & value args; returns in `x0`/`(x0, x1)`. |
| `d0` – `d7` | FP Arg & Return | Unboxed `Real` (`double`) args & results; boxed only at polymorphic boundaries. |
| `x8` | Indirect Result | Unused for Quest types, since all Quest values and fat pointers are $\le 16$ bytes. |
| `x9` – `x15` | Caller-Saved Temps | Expression evaluation scratch registers and offset dictionary lookups. |
| `x16`, `x17` | Scratch (`IP0`/`IP1`) | Linker veneers and indirect call trampolines. |
| `x18` | Platform Register | Reserved by macOS / OS ABI (**never touched** by generated code). |
| `x19` – `x28` | Callee-Saved Regs | Live-across-call locals allocated by the graph-coloring register allocator. |
| `x29` (`fp`) | Frame Pointer | Frame link; kept on every stack frame for unwinding ([exceptions.md](exceptions.md)). |
| `x30` (`lr`) | Link Register | Return address. |
| `sp` | Stack Pointer | 16-byte aligned at all call boundaries. |

### 4.1. Uniform Closure Calling Convention
Every first-class Quest function (`QClosure = { void *fn, void *env }`) is invoked by passing `closure->env` as the
first argument (`x0`), followed by any runtime type descriptors (`const QTypeDescriptor *`) for `All(A::TYPE)`
quantifiers, followed by the value parameters:
```c
((RetType (*)(void *, ...))closure->fn)(closure->env, descriptor_A, arg1, arg2);
```
Top-level and non-capturing functions use a static closure struct `{ (void *)qf_foo, NULL }` so that first-class
function values require zero heap allocation when they capture no local variables.

---

## See Also
- [ir.md](ir.md): How the IR lowers, specializes, closure-converts, represents, and describes Quest programs.
- [c-representation.md](c-representation.md): Concrete C99 struct definitions, conversion plans, and runtime APIs.
- [codegen-c.md](codegen-c.md): How the C printer emits C99 from the `ir_described` stage.
- [dynamic.md](dynamic.md): Runtime type descriptors, `auto`/`inspect`, and cyclic JSOG serialization.
- [exceptions.md](exceptions.md): Zero-overhead exception handling and native stack tracebacks.
