# Quest C Representation and Runtime ABI Design

This document specifies the C representation of Quest values, types, aggregates, closures, environments, exceptions,
and identifier mappings for **Step 4: Bootstrap C Transpiler** and the shared runtime in `runtime/`.

These representations are designed to be shared directly with the **Step 6: Native AArch64 Backend** and future
64-bit architectures (such as x86-64).

---

## 1. Design Goals and Architectural Principles

1. **64-bit Word Uniformity:** Every Quest value in a generic variable, parameter, or aggregate field occupies
   exactly one 64-bit word (`QVal`). All pointers and integer/floating-point primitives are 64 bits.
2. **Recommended Synthesis for Aggregates:**
   - Specific, typed C `struct` definitions for concrete, statically-known types (enabling natural field access and
     seamless debugger inspection in `lldb` and `gdb`).
   - Binary layout compatibility with uniform generic representations (`QVal[]`, `QVariantVal`), ensuring zero-cost
     coercions for prefix tuple subtyping, evidence-passing record subtyping, and static variant tag remapping.
3. **Clean Identifier Namespacing:** Use prefix tags (`qv_`, `QT_`, `QK_`) to prevent collisions with C keywords and
   standard library symbols.
4. **Human-Readable Operator Mangling:** Map symbolic operators to descriptive English names
   (e.g., `<-=` $\rightarrow$ `qv_sym_lessthan_minus_equals`).
5. **Portable C99 Compile-Time Layout Enforcement:** Enforce ABI assumptions (word sizes, alignments, struct field
   offsets) at compile time via portable static assertions.
6. **Shared Runtime ABI:** Place common runtime definitions in a top-level `runtime/` directory usable by both
   transpiled C and native assembly backends.

---

## 2. Compile-Time Layout Assertions in Portable C99

To guarantee that C compilers lay out memory identically to our ABI expectations across platforms, we enforce layout
properties at compile time via `static_assert`.

While C11 standardizes `<assert.h>` `static_assert` as `_Static_assert`, portable C99 achieves compile-time assertions
without language extensions via a standard negative-sized array in a typedef. This macro works uniformly with both
`sizeof` and `<stddef.h>`'s `offsetof(...)` constructs because both evaluate to compile-time integer constants:

```c
/* runtime/quest_runtime.h */

#include <stddef.h>

#define Q_ASSERT_CONCAT_(a, b) a##b
#define Q_ASSERT_CONCAT(a, b)  Q_ASSERT_CONCAT_(a, b)

#ifndef static_assert
#  if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
#    define static_assert(cond, msg) _Static_assert(cond, #msg)
#  else
#    define static_assert(cond, msg) \
       typedef char Q_ASSERT_CONCAT(q_assert_##msg##_, __LINE__)[(cond) ? 1 : -1]
#  endif
#endif
```

If `cond` evaluates to 0, the array dimension is `-1`, triggering an immediate compiler error pointing to the
declaration and printing the descriptive message token in the error output.

---

## 3. Primitives and the Universal Value Word (`QVal`)

All Quest values stored in registers, local variable slots, arrays, and tuple/record fields are 64-bit words:

```c
#include <stdint.h>
#include <stdbool.h>

typedef int64_t QInt;
typedef double  QReal;
typedef bool    QBool;
typedef char    QChar;

typedef union QVal {
    void    *p;   /* Heap pointers: records, tuples, arrays, strings, closures */
    QInt     i;   /* 64-bit signed two's complement integer */
    QReal    r;   /* 64-bit IEEE-754 double precision float */
    uint64_t u;   /* Raw 64-bit unsigned word for bitwise/identity checks */
} QVal;

/* ABI layout assertions */
static_assert(sizeof(QInt)     == 8, qint_must_be_8_bytes);
static_assert(sizeof(QReal)    == 8, qreal_must_be_8_bytes);
static_assert(sizeof(void *)   == 8, ptr_must_be_8_bytes);
static_assert(sizeof(QVal)     == 8, qval_must_be_8_bytes);
static_assert(sizeof(uint64_t) == 8, u64_must_be_8_bytes);
```

### 3.1. Standard Constant Definitions
Standard scalar constants are defined for `Ok` and boolean values:
```c
#define Q_OK_VAL    ((QVal){ .u = 0x0ULL })
#define Q_TRUE_VAL  ((QVal){ .i = 1LL })
#define Q_FALSE_VAL ((QVal){ .i = 0LL })
```

### 3.2. String Representation (`QString`)
Quest strings are immutable byte sequences with explicit length and trailing null byte:
```c
typedef struct QString {
    size_t length;
    char   chars[];
} QString;
```
- Strings are allocated via `quest_alloc_atomic(sizeof(QString) + length + 1)`.
- Runtime functions `quest_string_new(const char *data, size_t len)`, `quest_string_concat(s1, s2)`, and
  `quest_string_equal(s1, s2)` provide safe string manipulation.

### 3.3. Opaque C Data Structures (`QExternalType`)
Quest allows native C pointer and handle types to be declared directly in source code using the `external` keyword
(`type Handle = external "QWriter *"`):
- **Scalar Representation**: In the emitted C code, variables, function parameters, and return types of external
  types are emitted verbatim as their C type (`QWriter *`, `QReader *`, etc.).
- **Universal Word Boxing (`QVal`)**: When passed into generic polymorphic parameters (`All(A::TYPE)`), arrays, or
  abstract interface record fields, external pointer types are boxed into `QVal` via `(QVal){ .p = (void *)(expr) }`
  and unboxed via `((C_TYPE)(val.p))`.
- **Runtime Descriptors**: Polymorphic operations and reflection synthesize opaque descriptors for external types:
  `quest_make_opaque_descriptor("Handle")`.

### 3.4. Word Representation (`Word.T` / `QWord`)
Quest provides a standard `Word` module for 64-bit unsigned machine operations:
- **Concrete Representation**: `Word.T` maps to C `uint64_t` (`typedef uint64_t QWord;`).
- **Universal Word Boxing (`QVal`)**: When boxed into `QVal`, `Word.T` occupies `uint64_t u;`:
  `((QVal){ .u = (uint64_t)(expr) })` and is unboxed via `((expr).u)`.
- **Expression Inlining**: Operations like `andBits`, `orBits`, `xorBits`, `notBits`, `add`, `sub`, `mul`, `lt`,
  `le`, `gt`, and `ge` are inlined directly to C expressions (`&`, `|`, `^`, `~`, `+`, `-`, `*`, `<`, `<=`, `>`, `>=`).
- **Float and Integer Bit-Casts**: `toReal` and `fromReal` perform zero-copy type punning directly through `QVal`
  compound literals (`(((QVal){ .u = (w) }).r)` and `(((QVal){ .r = (r) }).u)`), compiling to register moves (`movq`).
- **Safety Wrappers & Bit Helpers**: `shift`, `rotate`, `extract`, `replace`, `popCount`, `countLeadingZeros`,
  `countTrailingZeros`, `div`, and `mod` use inline runtime helpers (`quest_word_shift`, `quest_word_rotate`,
  `quest_word_extract`, `quest_word_replace`, `quest_word_pop_count`, `quest_word_count_leading_zeros`,
  `quest_word_count_trailing_zeros`, `quest_word_div`, `quest_word_mod`) ensuring well-defined bounds and
  raising `word.error` on zero divisors.
- **Quest-Implemented Operations**: Single-bit operations `getBit`, `setBit`, and `clearBit` are implemented in Quest
  within `lib/word.mod.quest` utilizing `shift`, `andBits`, `orBits`, and `notBits`.
- **Word Size Constant**: `word.bits` provides the word width `64`.

### 3.5. Rationale for Uniform 64-Bit Representation vs. Non-64-Bit Alternatives
During C backend design, alternatives such as unboxed 8-bit integers/chars or unboxed heterogenous tuples were
evaluated:
1. **Generic Uniformity & Polymorphism:** In Quest, any polymorphic type variable `X <: Any` or higher-order quantifier
   can be instantiated with arbitrary types. Variable-width types (e.g. 1-byte chars or 2-byte ints) would necessitate:
   - Dynamic boxing/unboxing overhead on every generic parameter or aggregate field read.
   - Whole-program whole-type specialization, which cannot handle polymorphic recursion, existential types, or
     dynamic typing.
   - Fat pointers or runtime layout descriptors.
2. **Predictable Stride and Alignment:** Uniform 64-bit words guarantee that all aggregate slots are multiples of 8
   bytes, enabling zero-cost prefix tuple subtyping and constant-stride array indexing without struct padding anomalies.
3. **Specialized Scalar Optimization:** While the universal representation is 64-bit `QVal`, the C transpiler emits
   native C scalar types (`QInt`, `QReal`, `QBool`, `QChar`, `QString*`) for statically-known local variables and
   non-generic functions. This preserves register allocation and zero-boxing overhead where types are known at compile
   time.

### 3.5. ABI and Calling Convention Properties
- Under **AAPCS64** (macOS and Linux AArch64), `QVal` is an 8-byte composite type containing integer/pointer members;
  it is passed in a single **64-bit general-purpose register** (`x0`–`x7`) and returned in `x0`.
- Under **System V AMD64** (x86-64), `QVal` is classified as `INTEGER` class and passed in `rdi`, `rsi`, `rdx`, etc.,
  and returned in `rax`.
- For non-generic, specialized Quest functions whose types are statically known, the transpiler generates native C
  signatures (e.g. `QReal qv_add(QReal qv_a, QReal qv_b)`), allowing floats to remain in floating-point registers
  (`d0`–`d7`) without `fmov` overhead.

---

## 4. Identifier Mapping and Operator Mangling

### 4.1. Namespace Prefixes
All Quest identifiers map to C identifiers using explicit namespace prefixes:
- **`qv_` for Quest Values and Functions:**
  - `fib` $\rightarrow$ `qv_fib`
  - `factorial` $\rightarrow$ `qv_factorial`
  - `x` $\rightarrow$ `qv_x`
  - `int` $\rightarrow$ `qv_int` *(safely avoids collision with C `int`)*
  - `default` $\rightarrow$ `qv_default` *(safely avoids collision with C `default`)*
- **`QT_` for Quest Types:**
  - `Int` $\rightarrow$ `QT_Int`
  - `Real` $\rightarrow$ `QT_Real`
  - `List` $\rightarrow$ `QT_List`
- **`QK_` for Quest Kinds:**
  - `TYPE` $\rightarrow$ `QK_TYPE`
  - `POWER` $\rightarrow$ `QK_POWER`

### 4.2. Operator and Symbol Name Mangling
Quest supports arbitrary symbolic operator names. Symbolic characters map to human-readable names prefixed by `qv_sym_`:

| Symbol | Mangle Segment | Symbol | Mangle Segment | Symbol | Mangle Segment |
| :---: | :--- | :---: | :--- | :---: | :--- |
| `+` | `plus` | `-` | `minus` | `*` | `star` |
| `/` | `slash` | `=` | `equals` | `<` | `lt` |
| `>` | `gt` | `!` | `bang` | `?` | `question` |
| `:` | `colon` | `@` | `at` | `#` | `hash` |
| `$` | `dollar` | `%` | `percent` | `^` | `caret` |
| `&` | `amp` | `|` | `pipe` | `~` | `tilde` |
| `\` | `backslash` | `.` | `dot` | `'` | `prime` |

#### Examples:
- `+` $\rightarrow$ `qv_sym_plus`
- `++` $\rightarrow$ `qv_sym_plus_plus`
- `<-=` $\rightarrow$ `qv_sym_lt_minus_equals`
- `<>` $\rightarrow$ `qv_sym_lt_gt`
- `:=` $\rightarrow$ `qv_sym_colon_equals`
- `>>=` $\rightarrow$ `qv_sym_gt_gt_equals`

---

## 5. Aggregate Representations

### 5.1. Tuples
Tuples are ordered collections of 64-bit values. In Quest, tuple components can have explicit names
(`Tuple a:Int b:Real end`) or be positional (`Tuple Int Real end`), or a mix of both.

- **Field Naming Conventions:**
  - **Tuple components** use 0-indexed numerical tags: `_<index>` (`_0`, `_1`, etc.).
  - Named components (e.g. `p.x`) are resolved at compile time to their corresponding positional slot (`p->_0`).
  ```c
  /* Quest: Tuple x:Int y:Real String end */
  typedef struct QTuple_Int_Real_String {
      QInt     _0;  /* Component 0 (named x in signature) */
      QReal    _1;  /* Component 1 (named y in signature) */
      QString *_2;  /* Component 2 */
  } QTuple_Int_Real_String;
  ```

- **Generic View:**
  Any tuple pointer can be treated as a sequence of `QVal` words:
  ```c
  typedef struct QTuple {
      QVal elements[];
  } QTuple;
  ```

- **Zero-Cost Prefix Subtyping & Memoized Cast Verification:**
  Because each field is 8 bytes at consecutive 8-byte offsets, a pointer to an extended tuple (e.g. 3 components) is
  physically identical in its first 16 bytes to its prefix tuple (2 components). Passing an extended tuple to a
  function expecting a prefix requires only a pointer cast in C:
  ```c
  QTuple_Int_Real *sub = (QTuple_Int_Real *)tuple_3;
  ```
  To guarantee that compiler layout and alignment assumptions hold true, the transpiler **memoizes every tuple
  coercion pair** `(SourceTuple, TargetTuple)` encountered during translation. For each unique pair, the transpiler
  emits compile-time `static_assert` statements verifying that the byte offset of each prefix field in `SourceTuple`
  exactly matches the corresponding field in `TargetTuple`:
  ```c
  /* Memoized Tuple Coercion Assertions for (QTuple_Int_Real_String -> QTuple_Int_Real) */
  static_assert(offsetof(QTuple_Int_Real_String, _0) == offsetof(QTuple_Int_Real, _0),
                tuple_cast_offset_match_0);
  static_assert(offsetof(QTuple_Int_Real_String, _1) == offsetof(QTuple_Int_Real, _1),
                tuple_cast_offset_match_1);
  ```
  If field padding or struct alignment ever differs between the two types, compilation fails immediately.

- **Existential Tuples & Erasure of Type Formals:**
  In existential tuple types (`Tuple A::TYPE a: A end`, `Tuple T::POWER(Int) value: T end`), type formal components
  are erased from the physical C struct in static compilation. Only value components occupy struct fields
  (`_0`, `_1`, etc.). Runtime type descriptors for existential witnesses will be incorporated when `Dynamic.intern`
  and `Dynamic.extern` serialization is implemented.

- **Unbounded vs. Bounded Path-Type Lowering:**
  - Unbounded type variables and path-types (`A::TYPE`, `p.T`) map to uniform 64-bit `QVal`. Concrete scalar values
    assigned to abstract slots are boxed via `qval_wrap`, and extracted abstract values are unboxed via `qval_unwrap`.
  - Bounded type variables and path-types (`A::POWER(T)`, `p.T` where `p.T <: T`) resolve directly to the bound's
    native C type (e.g. `A <: Int` resolves to `QInt`, `A <: Real` to `QReal`), enabling unboxed, zero-overhead access.

- **Closure Adaptation Thunks:**
  When a tuple with concrete function signatures (e.g. `create: Int -> Counter` where `Counter = Int`) is coerced or
  packed into an existential tuple with abstract signatures (e.g. `create: Int -> A`), the underlying C function
  pointer types differ (`QInt (*)(void *, QInt)` vs `QVal (*)(void *, QInt)`). The transpiler synthesizes a static
  adaptation thunk (`qv_adapt_<id>`) that forwards the environment, unwraps any `QVal` arguments, calls the concrete
  function, and wraps abstract return values with `qval_wrap`. The same thunks implement function subtyping: a closure
  of type `Fun(x: Small): Big` used at `Fun(x: Big): Small` gets a thunk that coerces each argument from the target's
  parameter type to the closure's (giving the `Big` record a `Small` view) and the result from the closure's result
  type to the target's, with the ordinary coercions (record views, variant tag maps, nested thunks).

- **Tuple Structural Coercion & Generic Returns:**
  When field types between source and target tuples differ in C representation (due to scalar-to-QVal boxing, closure
  signature adaptation, generic function returns, or nested tuple coercion), the transpiler allocates a new target
  tuple struct and maps each field via `_coerce_tuple_val`:
  - **Generic Tuple Returns (`QVal` to Concrete):** Generic functions returning tuples (e.g.
    `let pair(A::TYPE B::TYPE a: A b: B): Tuple :A :B end = tuple a b end`) construct tuples whose fields are `QVal`.
    When instantiated at concrete types (e.g., `pair(:Point :Int pt 1)`), the caller coerces the returned tuple to the
    concrete tuple struct. For each field where the source is `QVal` and the target is concrete, `_qval_unwrap` unboxes
    the value. If the target field is a 16-byte record fat pointer (`QRecordVal`), `_qval_unwrap` unboxes it from the
    heap cell (`quest_record_unbox`); if a 16-byte variant, it unboxes the `QVariantVal`.
  - **Record Width Subtyping in Tuples:** When a tuple field contains a record subtype whose field dictionary differs
    from the target tuple field, the compiler synthesizes the new fat pointer by attaching the target evidence
    dictionary (`(QRecordVal){ .val = src._i.val, .dict = &... }`) rather than an unsafe pointer cast.
  - **Variant Tag Remapping in Tuples:** When tuple fields contain variants upcast across subtyping boundaries, static
    tag remapping lookup tables are applied to align the tag space to the target variant type.
  - **Zero-Cost Pointer Cast:** If all field C types match identically, zero-cost pointer casting is preserved.

### 5.2. Records and Subtyping (Evidence Passing)
Under Cardelli's structural subtyping with multiple inheritance, field offsets cannot be assigned globally.
As established in `docs/runtime-design.md`, Quest uses the **Evidence Passing** model:

1. **Concrete Record Payload & Object Header:**
   A heap-allocated block of 64-bit words beginning with an 8-byte object header (`QRecordHeader`), followed by
   fields sorted alphabetically by field name and prefixed with `qf_` (named `QT_<Alias>` or sequential `QT_record<N>`):
   ```c
   /* Quest: Let Point = Record x: Int y: Real end */
   typedef struct QT_Point {
       QRecordHeader header;  /* { const QTypeDescriptor *descriptor; } (8 bytes): the payload's layout */
       QInt          qf_x;
       QReal         qf_y;
   } QT_Point;
   ```
2. **Evidence Dictionary (`OffsetDict_<Name>`):**
   A concrete C struct whose members are `size_t offset_<field>` corresponding to the expected fields of the target record type.
   Static instances in `.rodata` (`offsetdict_<Target>_<Source>`) initialize these offsets using `<stddef.h>`'s `offsetof`:
   ```c
   typedef struct OffsetDict_Point {
       size_t offset_x;
       size_t offset_y;
       QRecordStoredTypes stored_types;
   } OffsetDict_Point;

   static const OffsetDict_Point offsetdict_Point_Point3D = {
       offsetof(QT_Point3D, qf_x),
       offsetof(QT_Point3D, qf_y),
       NULL
   };
   ```
   The trailing `stored_types` handles depth subtyping without copying. It is `NULL` when the payload stores every
   field at the view's type for it; otherwise it is an array giving, for each field the payload stores at a
   different type (a subtype: a `Record inner: Big end` payload viewed as `Record inner: Small end`), that type's
   descriptor, and `NULL` for the others. Static tables relate only records whose shared fields have equal types, so
   their `stored_types` is always `NULL`; the runtime fills it in when it builds a table.
   The header records the payload's *layout*, the descriptor of the record type it was created with
   (`&quest_type_QT_Point`); `quest_record_layout(r)` reads it. A value whose static type is `Point` may have a larger
   layout, such as `Point3D`'s.
3. **Offset Table Map:** The runtime keeps every offset table in one map keyed by (view type, layout), where the
   view is the record type the table serves. Coercing a record to a supertype whose layout is not known statically
   (anything but a record literal) uses it: `quest_record_view(r, &quest_type_<Target>)` keeps the payload and looks
   up the table for the payload's layout, read from its header. The record's static type is not enough, because it
   may itself be a view of a larger record. `quest_record_dict(view, layout)` returns the table, building it from the
   two descriptors on a miss (`NULL` if the layout lacks a field of the view), and `quest_register_record_dict`
   adds one. A compiled program pre-populates the map in `main` with its static `offsetdict_<Target>_<Source>`
   tables, registered under (`Target`, `Source`). Deserialization (`dynamic.intern`) takes its tables from the map.
4. **First-Class Uniform Record Value (`QRecordVal`):**
   - Every record value in variables, function parameters, and returns is represented as a first-class 16-byte struct:
     ```c
     typedef struct QRecordVal {
         void       *val;   /* Pointer to heap-allocated QT_<Record> payload */
         const void *dict;  /* Pointer to static OffsetDict_<Record> */
     } QRecordVal;
     ```
   - On AAPCS64, `QRecordVal` is passed and returned directly in register pairs (`x0, x1`) without heap allocation.
5. **Field Access:**
   - Evaluates dynamic offset from the embedded evidence dictionary:
     ```c
     (*((QFieldType *)((char *)r.val + ((const OffsetDict_Target *)r.dict)->offset_x)))
     ```
   - Reading an immutable field whose type is a record, variant, option, or nonempty tuple also checks the table's
     `stored_types`. When it names a type for the field, the value is converted to its view at the field's type
     with `quest_convert(v, stored, &quest_type_<FieldType>)`: records get the offset table for the view, variants
     and options their tags in the field's type, and tuples are copied with converted elements. Scalar, `var`, and
     other fields are read with the single offset load. `quest_record_field_value` does the same for the runtime.
6. **Storage in Aggregates:**
   - **Tuples:** Tuple fields of record type store `QRecordVal` inline (16 bytes).
   - **Flat Stride Arrays:** `Array(Record)` and `Array(Variant)` store 16-byte elements directly in contiguous
     memory without individual heap boxing using specialized wide array structures (`QArrayWideRecord` and
     `QArrayWideVariant`). Reading (`arr[i]`) and writing (`arr[i] := val`) operate directly on 16-byte slots
     in-place. Subtyping coercion (dictionary attachment for records, static tag remapping for variants) is
     applied at insertion time and stored flat.
   - **Unspecialized Generic Arrays:** When arrays are manipulated through unspecialized first-class polymorphic
     closures (`Array(A)` with erased uniform representation), slots use 8-byte `QVal` words in `QArray`,
     boxing wide elements via `quest_record_box` / `quest_variant_box`. Concrete arrays are specialized to flat
     stride buffers.
 6. **Bounded Specialization for Records (`A <: Record`):**
    - **Descriptor Retention:** Bounded polymorphic functions retain `const QTypeDescriptor *descriptor_A` in their
      C function signatures to support separate compilation and uniform reflection.
    - **Uniform Fat Pointer Parameter Passing:** Parameters of bounded type `p: A` are passed as unboxed 16-byte
      `QRecordVal` structs. At the call site, the caller coerces the concrete subtype argument to `A`'s bound by
      attaching the appropriate static subtyping offset dictionary (`(const void *)&offsetdict_Bound_Actual`).
    - **Dynamic Offset Evaluation:** Field access `p.x` inside the bounded function evaluates dynamic byte offsets
      through the passed-in dictionary: `((const OffsetDict_Bound *)p.dict)->offset_x`.
    - **Caller Dictionary Restoration on Return:** When a bounded function returns a bounded type variable `A` and the
      caller receives it as concrete subtype `T`, the caller restores the dictionary (`Option A: Caller Restores
      Dictionary`) by attaching `T`'s identity dictionary `&offsetdict_T_T` to the returned `.val`.

### 5.3. Options and Variants (Sums)

Cardelli's *Typeful Programming* establishes a fundamental distinction between **ordered sums (`Option`)** and
**unordered sums (`Variant`)**. The C runtime reflects this exact distinction:

#### 1. Option Types (Ordered, Dense 0-Indexed Enums with Inline Union Payloads)
By language definition, `Option` types are strictly ordered collections of signatures (§4.5). Unlike variants, an
option branch carries a full signature, meaning a branch may contain **zero, one, or multiple components**:
```quest
Let T =
  Option
    a                     (* 0 components *)
    b with x:Bool end     (* 1 component:  x:Bool *)
    c with x,y:String end (* 2 components: x,y:String *)
  end;
```
Cardelli explicitly defines the `ordinal(o)` operator, which exposes the 0-based integer index of an option at
runtime, and the `!` extraction operator, which unpacks the branch signature:
```quest
• bOption!b;
» tuple 1 let x=true end : Tuple :Int x:Bool end
```

To support zero or multiple components without auxiliary heap allocations, each concrete `Option` type emits a C
`struct` containing the 0-based `tag` followed by an **inline `union` of branch structs**:
```c
/* Generated for Option type T */
typedef enum {
    QTAG_T_a = 0,
    QTAG_T_b = 1,
    QTAG_T_c = 2,
} QT_T_Tag;

typedef struct QT_T {
    int64_t tag; /* 0-based ordinal matching Cardelli's ordinal(o) */
    union {
        /* branch 'a' has 0 components */
        struct {
            QBool qv_x;
        } b;
        struct {
            QString *qv_x;
            QString *qv_y;
        } c;
    } u;
} QT_T;
```

- **Generic View (`QOptionHeader`):** Because all payload components are 64-bit aligned words, generic runtime routines
  (such as `ordinal(o)` or generic `!`) can inspect any option through a common header:
  ```c
  typedef struct QOptionHeader {
      int64_t tag;
      QVal    fields[]; /* Inline 64-bit payload fields */
  } QOptionHeader;

  static_assert(offsetof(QOptionHeader, fields) == 8, qoption_fields_at_offset_8);
  ```
- **Zero-Cost Prefix Subtyping:** Because every union branch in C begins at offset 0 of the union (offset 8 of the
  struct), branch fields in a subtype maintain identical offsets in any extended supertype.
- **Fast Pattern Matching:**
  ```c
  switch (opt->tag) {
      case QTAG_T_a: /* 0 fields */ break;
      case QTAG_T_b: use(opt->u.b.qv_x); break;
      case QTAG_T_c: use(opt->u.c.qv_x, opt->u.c.qv_y); break;
  }
  ```

#### 2. Variant Types (Unordered, First-Class 16-Byte `QVariantVal`, Zero-Allocation Tag Remapping)
Unlike options, variants are unordered and each branch has **exactly one type** $A_i$ (§6.3):
```quest
Variant x1:A1 .. xn:An end
variant x of A with a end
```
If a branch requires no payload value, it uses the unit type `Ok` (`Variant mon,tue:Ok end`). Thus, every variant
payload is always **exactly one 64-bit word** (`QVal`). Variants are first-class unboxed values represented by
the 16-byte structure `QVariantVal`:
```c
typedef struct QVariantVal {
    int64_t tag;        /* Local dense tag index (0, 1, ...) */
    QVal    payload;    /* Exactly one 64-bit word */
} QVariantVal;

static_assert(sizeof(QVariantVal) == 16, qvariantval_must_be_16_bytes);
static_assert(offsetof(QVariantVal, tag) == 0, qvariantval_tag_at_offset_0);
static_assert(offsetof(QVariantVal, payload) == 8, qvariantval_payload_at_offset_8);
```
- **Zero-Allocation Construction & Operations:** Local variants, function parameters, returns, and variable
  bindings use `QVariantVal` directly by value. Variant construction `variant x of V with a end`, checks `v?x`,
  assertions `v!x`, and `case` pattern matching require **zero heap allocations**.
- **Static Tag Remapping Dictionaries (`.rodata`):** When a variant is upcast across an unordered subtyping boundary,
  the compiler emits a static lookup table `static const int64_t tagmap_<Target>_<Source>[]` in `.rodata`, and
  performs a zero-allocation upcast by returning an unboxed compound literal:
  ```c
  (QVariantVal){ .tag = tagmap_Large_Small[src.tag], .payload = src.payload }
  ```
- **Aggregate Storage:** Storing a subtyped variant into an aggregate (`Array` or `Tuple`) applies the static
  `tagmap` remapping at insertion time. In `Tuple`, `QVariantVal` is stored inline (16 bytes). In `Array`, it is
  boxed into an 8-byte pointer (`QVariantVal *`) via `quest_variant_box`, setting the stage for future flat stride
  arrays. Reading from aggregates accesses values whose tags are pre-aligned to the supertype's tag space,
  allowing normal, zero-cost dynamic tag dispatch on extraction and `case` expressions.
- **Polymorphic Contexts:** When passed to unbounded polymorphic functions (`All(A::TYPE)`), `QVariantVal` is
  boxed via `quest_variant_box(v)` into `QVal.p` and unboxed via `(*((QVariantVal *)qval.p))`.
- **Bounded Specialization for Variants (`V <: Variant`):**
  - **Descriptor Retention:** Bounded variant functions retain `const QTypeDescriptor *descriptor_V` in their C
    function signature.
  - **Call-Site Tag Alignment:** When invoking a function expecting `V <: BoundVariant`, the caller aligns the
    variant's tag to `BoundVariant`'s tag space via the static `tagmap_Bound_Actual[]` table using an unboxed compound
    literal `(QVariantVal){ .tag = tagmap[v.tag], .payload = v.payload }`.
  - **Zero-Allocation Callee Dispatch:** Because tags are pre-aligned at call sites, the callee evaluates `case`, `?`,
    and `!` directly on `v.tag` without runtime tag translation, dictionary lookups, or heap allocations.
- **Specialization:** Eliminated entirely when the variant type is statically known.

### 5.4. Arrays
Arrays are mutable, length-prefixed contiguous buffers. In Quest, arrays are invariant (`Array(S) <: Array(T)`
iff `S == T`), allowing the transpiler to statically select the optimal representation without covariance anomalies:

1. **Standard Arrays (`QArray`):**
   Length-prefixed buffer of uniform 64-bit `QVal` words for scalar types (`Int`, `Real`, `Bool`, `Char`, `String`)
   and pointer types (`Tuple`, `Array`, `Closure`):
   ```c
   typedef struct QArray {
       int64_t length;
       QVal    data[];
   } QArray;

   static_assert(offsetof(QArray, data) == 8, qarray_data_at_offset_8);
   ```

2. **Flat Stride Record Arrays (`QArrayWideRecord`):**
   Length-prefixed buffer storing 16-byte `QRecordVal` elements directly in contiguous memory. Eliminates per-element
   heap boxing:
   ```c
   typedef struct QArrayWideRecord {
       int64_t    length;
       QRecordVal data[];
   } QArrayWideRecord;

   static_assert(offsetof(QArrayWideRecord, data) == 8, qarray_wide_rec_data_at_offset_8);
   ```

3. **Flat Stride Variant Arrays (`QArrayWideVariant`):**
   Length-prefixed buffer storing 16-byte `QVariantVal` elements directly in contiguous memory:
   ```c
   typedef struct QArrayWideVariant {
       int64_t     length;
       QVariantVal data[];
   } QArrayWideVariant;

   static_assert(offsetof(QArrayWideVariant, data) == 8, qarray_wide_var_data_at_offset_8);
   ```

All three array layouts place `length` at offset 0, enabling uniform bounds checking
(`quest_check_array_bounds(const void *arr_ptr, int64_t idx)`) and length inspection (`arr->length`)
without pointer type casting overhead.

### 5.5. Strings
In Quest, strings are mutable character sequences (supporting Cardelli's `StringOp` interface):
```c
typedef struct QString {
    int64_t length;
    int64_t capacity;
    char   *data;     /* Null-terminated UTF-8 / ASCII buffer */
} QString;
```

### 5.6. Module Records and Lazy Initialization
Quest modules compile to first-class record values (`QRecordVal`), allowing modules to be passed as arguments or
manipulated dynamically:
- **Module State Variable**: Each compiled module emits a static fat pointer:
  ```c
  static QRecordVal qm_<mod>;
  static bool qv_mod_<mod>_initialized = false;
  static void qv_mod_<mod>_init(void);
  ```
- **Record Struct Shape**: The module interface generates a concrete struct `QT_<Interface>` containing fields
  for each exported function closure (`QClosure *`) or value (`QVal` or concrete scalar/pointer).
- **Concrete Value Population**: When `qv_mod_<mod>_init()` executes (lazily on program startup or first import):
  1. It recursively invokes initializers for all imported modules in topological order.
  2. It evaluates local bindings and allocates `QT_<Interface>` payload struct via `quest_alloc`.
  3. All fields are populated with **concrete values**: functions wrap static trampolines
     (`qv_<mod>_<fn>_trampoline`) in allocated `QClosure` structs; data fields hold evaluated constants or pointers.
  4. `qv_<mod>` is initialized with `.val = (void *)payload` and `.dict = (const void *)&offsetdict_<I>_<I>`.
- **Zero-Cost Direct Calls**: Calling a known module function (e.g. `writer.putString(w s)`) directly invokes
  `quest_writer_put_string(...)`, entirely bypassing record dispatch.

### 5.7. Recursive Types
Quest's recursive types are equi-recursive: `Rec(X) T` is equal to its unfolding `T[X := Rec(X) T]`, to any depth.
Equal types share one C representation, so a value moves between them with a plain assignment:

- **Values:** A recursive type whose unfolding is a tuple, record, variant, or option type (directly or through a
  type operator application, as `List(Int)`) is represented like its unfolding: a recursive tuple or option is a
  pointer to its struct, whose recursive components point to that same struct.
- **Struct tags:** The tag of a recursive type is built from its body with each recursion variable replaced by a
  placeholder numbered by nesting depth (`Rec0_QOption_nil_cons_QTuple_Int_Self0` for
  `Rec(L) Option nil cons with head: Int tail: L end end`), so that it is finite and the same for alpha-equivalent
  types. An aggregate type equal to a recursive type it contains (an unfolding, written out) takes that recursive
  type's tag (`type_to_c_tag`), and its descriptor (`descriptor_form`); so do aggregates built from such types.
- **Limitation:** Equal recursive types with different periods (`Rec(L) Option nil cons with head: Int tail: L end
  end` and the same type unrolled twice inside its `Rec`) still get different tags.

---

## 6. Closures and Calling Convention (Phase 4.2c)

In Quest, functions are first-class values and can capture lexical bindings:

### 6.1. Closure Representation (`QClosure`)
Every closure is a uniform 16-byte structure containing a C function pointer and an environment pointer:
```c
typedef struct QClosure {
    void *fn;   /* C function pointer */
    void *env;  /* Captured environment pointer or NULL */
} QClosure;

static_assert(sizeof(QClosure) == 16, qclosure_must_be_16_bytes);
static_assert(offsetof(QClosure, env) == 8, qclosure_env_at_offset_8);
```

### 6.2. Function Signatures and Calling Conventions
1. **Direct Top-Level Functions:** Keep clean standard C signatures without an unused environment parameter:
   `static QInt qv_square(QInt qv_x);`.
2. **First-Class Top-Level Functions:** When a top-level function is referenced as a value, the compiler generates a
   static trampoline adapter:
   ```c
   static QInt qv_square_trampoline(void *env, QInt qv_x) {
       (void)env;
       return qv_square(qv_x);
   }
   static QClosure qv_square_closure = { (void *)qv_square_trampoline, NULL };
   ```
   Referencing `square` emits `(&qv_square_closure)`.
3. **Lifted Lambdas:** Every non-top-level lambda is lifted to file scope with signature:
   `static RetType qv_lambda_<id>(void *_raw_env, Params...)`.
4. **Indirect Call Site:**
   ```c
   ((RetType (*)(void *, ParamTypes...))(c_func->fn))(c_func->env, args...);
   ```

### 6.3. Flat Environment Frames
Captured variables are grouped into flat environment structs allocated via `quest_alloc`:
```c
struct QEnv_lambda_1 {
    QInt qv_x;
    QReal qv_y;
};
```
Non-capturing lambdas omit the environment struct and use file-scope static singleton closures.

### 6.4. Polymorphic Functions and Runtime Type Descriptors (`QTypeDescriptor`)
While monomorphic functions pass values directly, polymorphic functions (`All(A::K) ...`) require **Intensional Type Analysis (ITA)** (see `docs/type-system.md` §6.10.1) to support Cardelli's `Dynamic` operations (`dynamic.new`, `dynamic.be`) and first-class abstraction barriers without restricting generic wrappers.

#### 1. The Uniform Quantifier Rule
> **Rule:** Every universal type quantifier `(A::K)` in a function or method signature compiles to a preceding `const QTypeDescriptor *descriptor_<A>` parameter in C.

- Direct polymorphic function:
  ```quest
  let id(A::TYPE x:A): A = x;
  ```
  Compiles to C:
  ```c
  static QVal qv_id(const QTypeDescriptor *descriptor_A, QVal qv_x) {
      (void)descriptor_A;
      return qv_x;
  }
  ```
- Polymorphic closure signature:
  ```c
  RetType (*fn)(void *env, const QTypeDescriptor *descriptor_A, ..., ParamTypes...);
  ```
- Higher-Order Quantifier Subtyping:
  Because every quantifier corresponds to exactly one pointer parameter `const QTypeDescriptor *` in C regardless of its subkinding bound (`TYPE` vs `POWER(Point)`), a general polymorphic function $\text{All}(A::\text{TYPE}) (A \to \text{Ok})$ has the exact same C signature and calling convention as a bounded function $\text{All}(A <: \text{Point}) (A \to \text{Ok})$, requiring zero adaptation thunks.
- Existential Packages (Weak Sums):
  In static compilation, type formal components `X::K` are erased from runtime tuple structs (`struct QTuple`),
  allocating only for value fields. Path-types `p.X` resolve to `QVal` (if unbounded) or to the native C type of
  `K`'s bound (if `K = POWER(T)`). Full runtime type descriptors for existential witnesses will be incorporated
  when `Dynamic.intern` and `Dynamic.extern` are implemented.

#### 2. Types of Polymorphic Instantiation Call Sites
In Cardelli's formal terminology (*Typeful Programming* §3 & §5), applying a polymorphic value to a type argument is **polymorphic instantiation** (or **type application**):
1. **Closed / Ground Type Instantiation** (*static monomorphic instantiation* in C++/Rust):
   The type argument is a closed ground type (`Int`, `String`). The compiler passes the static global descriptor directly:
   `qv_id(&quest_type_Int, (QVal){.i = 42LL});`.
2. **Type Variable Instantiation / Forwarding** (*generic call forwarding* in modern generic languages):
   Inside a polymorphic function with a bound type variable in scope, the type parameter is forwarded as the runtime descriptor:
   Inside `foo(X::TYPE x:X)` calling `id(:X x)`: `qv_id(descriptor_X, qv_x);`.
3. **Compound Type Operator Instantiation:**
   When the type argument is formed by applying a type operator (`Array(Int)` or `Array(X)`):
   - Ground compounds emit a memoized, statically initialized compound descriptor `&quest_type_Array_Int`.
   - Open compounds involving type variables emit a call to an allocator helper `quest_make_array_descriptor(descriptor_X)`.

#### 3. Call-Site Specialization for Unbounded Quantifiers (`A::TYPE`)
While the uniform quantifier rule guarantees modular separate compilation with uniform 8-byte `QVal` representations,
unbounded generic functions called with 16-byte record fat pointers (`QRecordVal`) or 16-byte unboxed variants
(`QVariantVal`) undergo **Selective Call-Site Specialization**:
- **Selective Trigger**: Specialization is only synthesized when at least one concrete type argument involves a
  `Record`, `Variant`, or aggregate containing them. Calls with standard 8-byte types (`Int`, `Bool`, `String`)
  continue executing via the canonical uniform `QVal` implementation without code bloat.
- **Typed AST Cloning & Type Substitution**: When `c_analysis.py` encounters a call site `f(:Point, p)`, the compiler
  clones the `TypedFun` AST node with all occurrences of type parameter `A` substituted by `Point`. The specialized
  clone is emitted as `static Q_UNUSED ret_t qv_<name>_spec_<type_tags>(param_types...)`.
- **Layout Alignment & Zero-Boxing**: Inside the specialized clone, any generic tuple (e.g. `Tuple item: A end`)
  allocates a concrete specialized struct (`struct QTuple_QRecord_x_Int` with a 16-byte `QRecordVal` slot) matching the
  exact struct and layout expected by the caller. Arguments and return values are passed unboxed in register pairs
  `(x0, x1)` without heap allocation (`quest_record_box` and `quest_variant_box` eliminated).
- **First-Class Fallback**: The canonical boxed (`QVal`) version of any generic function is always emitted to serve
  indirect closure calls and first-class function values.

#### 4. Optimization via Inlining and Partial Evaluation
While the uniform quantifier rule guarantees modular separate compilation, it does not mandate runtime overhead when
optimizations are enabled:
- **Inlining:** When a polymorphic call site is inlined into the caller, the concrete type descriptor becomes statically
  known. If the inlined body does not perform dynamic inspection or packaging, the unused descriptor parameter is
  eliminated via dead-code elimination.
- **Partial Evaluation with Respect to Types (Specialization):** Call sites with concrete type arguments can be
  specialized at compile time, eliminating descriptor parameters and generating unboxed, zero-overhead native code.

#### 4. Descriptor Structure and Memory Management
Every type descriptor is an instance of `QTypeDescriptor`:
```c
typedef enum QTypeKind {
    QTYPE_KIND_INT, QTYPE_KIND_REAL, QTYPE_KIND_BOOL, QTYPE_KIND_CHAR,
    QTYPE_KIND_STRING, QTYPE_KIND_OK, QTYPE_KIND_TUPLE, QTYPE_KIND_RECORD,
    QTYPE_KIND_VARIANT, QTYPE_KIND_OPTION, QTYPE_KIND_ARRAY, QTYPE_KIND_FUN,
    QTYPE_KIND_DYNAMIC, QTYPE_KIND_EXCEPTION,
    QTYPE_KIND_OPAQUE  /* Nominal abstract types and existential package witnesses */
} QTypeKind;

struct QTypeDescriptor {
    QTypeKind   kind;
    const char *name;
    size_t      size;
    size_t      alignment;
    bool      (*is_subtype)(const QTypeDescriptor *sub, const QTypeDescriptor *super_type);
    const void *extra;
};
```

##### Compound Descriptor Payloads (`.extra`)
- **Records (`QRecordTypeDescriptor`):** Holds `size_t field_count` and an array of `QRecordFieldDescriptor`
  (`name`, `type`, `offset`, `is_var`). Fields are canonically ordered alphabetically by field name so that index $i$
  corresponds directly to the field's position in `QRecordVal.dict`.
- **Tuples (`QTupleTypeDescriptor`):** Holds `size_t element_count` and an array of `QTupleElementDescriptor`
  (`name`, `type`, `offset`).
- **Variants & Options (`QVariantTypeDescriptor`):** Holds `size_t case_count` and an array of `QVariantCaseDescriptor`
  (`name`, `payload_type`, `tag_index`, `is_var`).
- **Arrays (`QArrayTypeDescriptor`):** Holds `const QTypeDescriptor *element_type`.
- **Functions (`QFunTypeDescriptor`):** Holds `size_t param_count`, `QFunParamDescriptor *params`,
  `const QTypeDescriptor *result_type`, and `QFunAdapter adapt`. Each monomorphic function type has its own descriptor
  (`quest_type_fun_<digest>`, a digest of the type's text, since all closures share the C tag `QClosure`); `adapt`
  points to the compiled `quest_adapt_fun_<digest>`, which wraps a closure of a subtype in a thunk with this type's C
  signature that converts arguments and result by descriptor with `quest_convert`. `quest_convert` uses it for
  function values, so `dynamic.be`, `inspect`, and reads of function fields stored at a subtype adapt closures at run
  time. Runtime subtyping of function types is contravariant in value parameters, invariant in `var` parameters, and
  covariant in `out` parameters and the result. Polymorphic function types (`All(A::TYPE x: A) A`) are described the
  same way, plus `quantifier_count` and `quantifier_bounds`: their type parameters are passed as descriptors before the
  values (and adapters pass them through), and within the parameter and result types a type parameter is described
  by `quest_type_bound_vars[i]` (kind `QTYPE_KIND_BOUND_VAR`), where `i` is its de Bruijn index. So types differing
  only in the names of their type or value parameters have equal descriptors (`canonical_fun_type`), and their
  subtyping requires equal bounds and compares parameter and result types as above.
- **Exceptions (`QExceptionTypeDescriptor`):** Holds `payload_type`; subtyping is invariant in it.

##### Choosing a Descriptor (`descriptor_form`)
Every type the program describes gets its own descriptor, chosen by `descriptor_form` (`codegen/c_types.py`), which
both descriptor references (`c_type_descriptor`) and descriptor emission use. A type parameter in scope is described
by the descriptor passed for it. Tags of compound types include a digest of the type's text, because C tags conflate
types with the same representation. Recursive types (`Rec(X) ...`, recursive type operator applications) are
described by their unfoldings, which refer back to them, so their descriptors are cyclic; the emitter defines any
struct that such an unfolding names. Applications of abstract type operators (`list.T(Int)`), type operators passed
for higher-kinded type parameters, and abstract types of package values (`t.A`, distinguished by binding) are opaque,
compared by name. Inside the module that implements an abstract type, the type is its representation, so a value
given a run-time type there carries the representation's descriptor, which does not match the abstract type's
name outside. A type with no descriptor (such as a type metavariable) is a compile-time error rather than a
descriptor that matches the wrong values.

##### Static Compilation (.rodata) vs. Runtime Synthesis
- **Closed Types in Code:** For all concrete types appearing in the program, the C emitter synthesizes `static const`
  descriptor structs in `.rodata` with `Q_UNUSED` attribute. Forward declarations ensure that self-referential or
  mutually recursive types can cross-reference descriptor addresses as compile-time address constants.
- **Runtime Synthesis & Interning:** The C runtime provides constructor functions (`quest_make_record_descriptor`,
  `quest_make_tuple_descriptor`, `quest_make_variant_descriptor`, `quest_make_fun_descriptor`,
  `quest_make_array_descriptor`, `quest_make_opaque_descriptor`) with hash-interning in a global bucket table to ensure
  canonical pointer equality for dynamically constructed types.
- **Opaque Types (`QTYPE_KIND_OPAQUE`):** Represent nominal abstract types (`T::TYPE` in an interface or existential
  package). Subtyping checks compare pointers or canonical nominal names to preserve module encapsulation barriers.
- **Manifest Types (`Def T = ...`):** Pure compile-time aliases, completely erased at runtime with no separate
  descriptors.

##### Subtyping Verification (`quest_is_subtype`)
Subtyping checks are unified under `quest_is_subtype(sub, super_type)`:
- **Identity & Base Types:** Exact descriptor pointer match or matching primitive kind.
- **Tuples:** Prefix subtyping ($N_{\text{sub}} \ge N_{\text{super}}$ with covariant element types); `Tuple end` is
  thus a supertype of every tuple, and only of tuples.
- **Records:** Width subtyping ($S \subseteq R$ where every supertype field is present in the subtype), permutation
  subtyping (field order is irrelevant), depth subtyping on immutable fields ($T_{\text{sub}} <: T_{\text{super}}$),
  and invariance on mutable `var` fields ($T_{\text{sub}} \equiv T_{\text{super}}$).
- **Variants:** Case inclusion ($R_{\text{sub}} \subseteq R_{\text{super}}$) with covariant immutable payload types
  and invariant mutable payload types.
- **Coinduction:** Cyclic type comparisons are tracked via an active subtyping trail (`quest_subtyping_trail`) to
  prevent infinite recursion on recursive records or variants.

##### Dynamic Value Adaptation (`dynamic.be` and `inspect`)
When extracting a value from a dynamic package (`dynamic.be[:T](d)` or `inspect d when T with x then ...`):
1. The runtime checks `quest_is_subtype(d->type_desc, target_desc)`. If not a subtype, `dynamic.be` raises
   `dynamic.error` (or `inspect` falls through to the next branch or `else`).
2. If exact descriptor match, the payload is returned unchanged.
3. If structural subtyping holds:
   - **Record View (`quest_record_view`):** Keeps the payload and takes the offset table for (target type, the
     payload's layout) from the offset table map (§5.2), so a record packaged as a view of a larger record is read
     correctly. (Records nested in the payload keep their own tables.)
   - **Variant Adaptation (`quest_variant_adapt`):** Dynamically remaps the variant tag using a synthesized tag map
     from source branch names to target branch tag indices, and adapts the payload if needed. Memoized in an adapter
     cache.

### 6.5. Mutable Reference Parameters (`out` and `var`) and `@` Lvalues (Phase 4.12)

Following Cardelli's *Typeful Programming* (§4.8), Quest supports passing mutable memory locations to functions via
`var` (read-write) and `out` (write-only) parameters:

#### 1. Native C Representation (`T *`)
- Parameters declared as `var p: T` or `out p: T` compile directly to native C pointers `T *qv_p`.
- In the function body, writes to `qv_p` dereference the pointer (`*qv_p = val;`).
- Reads from `var` parameters dereference the pointer (`*qv_p`).
- Direct reads from `out` parameters are strictly rejected at compile time (strict write-only enforcement).
- When a function takes polymorphic parameters (`var p: A`), the unspecialized signature uses `QVal *qv_p`.

#### 2. Polymorphic `out` and `var` Parameters: Two-Tier Invocation Model
When calling a generic function with polymorphic reference parameters (e.g. `assignPoly(:A @x val)` where `x: T`):
- **Tier 1 (Direct Call Specialization):** Within the same compilation unit, calls with concrete type arguments
  specialize the function. The specialized function receives a direct native pointer `T *qv_p`, passing the address of
  the native memory location without any boxing or intermediate allocation.
- **Tier 2 (Shadow Cell Fallback Mode):** When calling an unspecialized polymorphic function (such as across separate
  compilation boundaries or through first-class generic closures):
  - The caller allocates a stack-allocated shadow cell: `QVal _shadow_cell;`.
  - **Copy-in (`var` only):** For `var` parameters, the caller wraps the current native value into the shadow cell:
    `_shadow_cell = _qval_wrap(*_loc_ptr, T);`. If `T` is a 16-byte record fat pointer (`QRecordVal`), it is heap-boxed
    via `quest_record_box`; if `T` is a 16-byte `QVariantVal`, it is boxed via `quest_variant_box`. For `out`
    parameters, copy-in is skipped because the callee cannot read the parameter.
  - **Callee Invocation:** Callee receives `&_shadow_cell` (`QVal *`).
  - **Copy-out Writeback (`var` and `out`):** Immediately after the callee returns, the caller executes the writeback:
    `*_loc_ptr = _qval_unwrap(_shadow_cell, T);`. If `T` is a record, `_qval_unwrap` unboxes the `QRecordVal` fat
    pointer; if a variant, it unboxes the `QVariantVal`.
  - **Writeback Semantics:** In fallback mode, writes made by the callee are buffered in the shadow cell and committed
    to the target location only upon function return. If the target location is aliased by another reference or accessed
    by another thread during callee execution, in-flight mutations are not visible until the writeback executes.

#### 3. Call Sites and `@` Lvalue Expressions
- Call sites for `var` and `out` parameters strictly require explicit `@` lvalue references or temporary cells `var(e)`.
  Passing bare identifiers without `@` is rejected as a type error.
- Supported lvalue targets for `@`:
  - Variables: `@x` passes `&qv_x`.
  - Record fields: `@r.f` passes pointer to the field within the record heap buffer.
  - Array elements: `@a[i]` passes pointer to the element slot within the flat array buffer.
  - Tuple elements: `@t.1` passes pointer to the tuple component `&tup->_1`.
  - Nested chained paths: `@r.a.b` and `@a[i].f` evaluate prefix paths and take the address of the terminal mutable
    location.
  - Temporary cells: `var(e)` evaluates expression `e` into a stack cell and passes its address (`&_var_cell`).
- **Pointer Forwarding:** When forwarding an existing pointer parameter `y` to another callee expecting a reference
  (`g(@y)`), the compiler detects that `y` is already a pointer and passes `qv_y` directly without taking its
  address (`&`).

#### 4. Closure Capture Restrictions
To prevent dangling stack references and escaping pointers without requiring full static lifetime analysis or boxing
every variable into a heap cell:
- Capturing `out` or `var` parameters inside local closures is prohibited and rejected with a type error.
- Capturing local stack-allocated mutable variables (`let var x = ...` inside a function body) inside escaping closures
  is prohibited and rejected with a type error.
- Top-level module-level `var` variables are global module state and may be accessed from closures.

---

## 7. Exception Handling with `setjmp` and `longjmp`

Quest's `try...when...else` and `raise` are lowered using a thread-local exception handler stack:

```c
#include <setjmp.h>

typedef struct QException {
    const char *name;
} QException;

typedef struct QExceptionState {
    const QException *exc;
    QVal              payload;
} QExceptionState;

typedef struct QExceptionHandler {
    jmp_buf                     env_jmp;
    struct QExceptionHandler   *prev;
} QExceptionHandler;

/* Thread-local exception handler chain */
#if defined(_MSC_VER)
#  define Q_THREAD_LOCAL __declspec(thread)
#else
#  define Q_THREAD_LOCAL _Thread_local
#endif

extern Q_THREAD_LOCAL QExceptionHandler *quest_current_exception_handler;
extern Q_THREAD_LOCAL QExceptionState    quest_current_exception;
```

### 7.1. Generative Exception Values
Cardelli's Quest specification (§4.9) states:
> *"The `exception` construct generates a new unique exception value whenever it is evaluated..."*

Evaluating `exception name [: Type] end` invokes `quest_alloc_exception("name")`, returning a heap-allocated pointer `const QException *`. Because each allocation produces a distinct memory address, **pointer equality (`==`)** directly provides unique generative identity without requiring an integer exception ID.

Built-in exceptions (e.g. `quest_exc_int_error`, `quest_exc_real_error`, `quest_exc_arrayOp_error`, `quest_exc_string_error`, `quest_exc_variant_error`) are pre-allocated global `QException` singletons whose static addresses provide their immutable identity.

### 7.2. Raising an Exception (`raise E [with payload] end`)
```c
void quest_raise(const QException *exc, QVal payload) {
    if (!quest_current_exception_handler) {
        /* Uncaught exception diagnostic */
        const char *name = (exc && exc->name) ? exc->name : "<unknown>";
        fprintf(stderr, "Exception: %s\n", name);
        exit(1);
    }
    quest_current_exception.exc = exc;
    quest_current_exception.payload = payload;
    longjmp(quest_current_exception_handler->env_jmp, 1);
}
```

### 7.3. Try-Handler Block (`try ... when ... else ... end`)
```c
QExceptionHandler q_handler;
q_handler.prev = quest_current_exception_handler;
quest_current_exception_handler = &q_handler;

if (setjmp(q_handler.env_jmp) == 0) {
    /* Protected body evaluated into destination */
    ...
    quest_current_exception_handler = q_handler.prev; /* Pop handler on normal completion */
} else {
    /* Pop handler before executing catch block so nested raises propagate outwards */
    quest_current_exception_handler = q_handler.prev;
    QExceptionState q_caught = quest_current_exception;
    
    if (q_caught.exc == qv_Exc1) {
        /* If branch has binder: bind q_caught.payload */
        /* Evaluate branch body into destination */
    } else if (q_caught.exc == qv_Exc2) {
        /* Handle branch 2 */
    } else {
        /* Else clause, or re-raise if no matching when */
        quest_raise(q_caught.exc, q_caught.payload);
    }
}
```

---

## 8. Auto Values and Dynamic Values (`QAuto`)

An auto value, including a dynamic value (`Dynamic.T` is `Auto A::TYPE with a:A end`, see
[dynamic.md](dynamic.md)), is a pointer to its type component's descriptor and its components:
```c
typedef struct QAuto {
    const QTypeDescriptor *type_desc;  /* the type component */
    QVal                   payload;    /* .p: the components, in the stored layout (§8.1) */
} QAuto;
```
- `dynamic.new` and `dynamic.be` are Quest code in `lib/dynamic.mod.quest` (`auto :A with a end` and an `inspect`
  at `A`), compiled like any other library module; inside them `A`'s descriptor is the one passed for the type
  parameter.
- `dynamic.copy`, `dynamic.extern`, and `dynamic.intern` are declared `external` in the module and implemented by
  `quest_dynamic_copy`, `quest_dynamic_extern`, and `quest_dynamic_intern`, which rely on `Dynamic.T`'s stored layout:
  one component, a `QVal`.
- `dynamic.error` is `(&quest_exc_dynamic_error)`, which `inspect` also raises when no branch matches.

### 8.1. Auto Values

An auto value (`Auto A::K with S end`, [type-system.md](type-system.md) §6.11) is a `QAuto *`: `type_desc` is the
descriptor of its type component and `payload.p` points to a tuple struct holding its components. The tuple is
stored in a layout that does not depend on the type component, that of `Tuple S end` with `A` an abstract type of
kind `K` (`auto_payload_type(auto_t)`). As for any abstract type, a component of type `A` is a `QVal`, or the
representation of `B` when `K` is `POWER(B)` (so `Auto A<:Object with a:A end` stores a `QRecordVal`); components
of other types that mention `A`, such as `show(:A):String`, take the generic form too (here a closure taking a
`QVal`). Auto types have descriptors of kind `QTYPE_KIND_AUTO` (`QAutoTypeDescriptor`): the bound of the type
parameter, the size of the stored payload, and for each component its name, its type (the type parameter is
`quest_type_bound_vars[0]`, so equal auto types have equal descriptors), its offset in the payload, and its storage
(a record or variant stored inline, or else 8 bytes that are its `QVal` form). Runtime subtyping of auto types
follows §6.7: a subtype bound and, as for tuples, a prefix of the components with matching names. Serialization
supports auto values with one component.

- **Construction:** `auto :T with ... end` builds the `Tuple S[T/A] end` struct, converts it to the stored layout
  with the static tuple coercion (`_coerce_tuple_val`: boxing to `QVal`, closure adapters), and calls
  `quest_auto_new(descriptor_T, payload)`.
- **Inspect, exact match:** a branch tests `quest_is_subtype` in both directions. When every stored component has
  the representation of the corresponding `S[T/A]` component, or is a `QVal` holding a scalar or pointer of that
  type, the binder is the stored struct itself, cast to the `Tuple S[T/A] end` struct, so updates of `var`
  components are shared with the auto value. Otherwise the binder is a converted copy; this is rejected with an
  error for signatures with `var` components, whose updates would be lost (for example `Auto A::TYPE with a:A var
  n:Int end` inspected at a record type: give the auto type a bound, `A<:Object`, so that records are stored
  unboxed).
- **Inspect, subtype match** (signatures where `A` is only the whole type of immutable components): a branch tests
  `quest_is_subtype(d->type_desc, descriptor_T)`; the binder is a fresh `Tuple S[T/A] end` struct whose `A`
  components are converted from the type component to `T` with `quest_convert` (record views, variant tag maps,
  function adapters) and whose other components are copied.
- **No match:** without an `else` branch, `quest_raise_dynamic_error()`.
- **Auto subtyping:** converting `Auto A::K1 with S1 end` to `Auto B::K2 with S2 end` re-stores the payload with
  `_coerce_tuple_val` from the `S1` layout to the `S2` layout, keeping the type descriptor, when the two stored
  layouts differ; otherwise the pointer is reused.

---

## 9. Memory Management Abstraction & `--nogc` Support

All heap allocations route through two runtime allocator functions:
- `quest_alloc(size_t bytes)`: Allocates memory that may contain pointers (scanned by GC).
- `quest_alloc_atomic(size_t bytes)`: Allocates memory guaranteed not to contain pointers (e.g., string buffers,
  atomic raw bytes).

```c
/* runtime/quest_runtime.h */

#ifdef QUEST_NOGC
#  include <stdlib.h>
   static inline void *quest_alloc(size_t sz)        { return calloc(1, sz); }
   static inline void *quest_alloc_atomic(size_t sz) { return malloc(sz); }
   static inline void  quest_gc_init(void)           { /* no-op */ }
#else
#  include <gc.h>
   static inline void *quest_alloc(size_t sz)        { return GC_MALLOC(sz); }
   static inline void *quest_alloc_atomic(size_t sz) { return GC_MALLOC_ATOMIC(sz); }
   static inline void  quest_gc_init(void)           { GC_INIT(); }
#endif
```

- When compiled without flags, Quest links with Boehm GC (`-lgc`).
- When invoked with `--nogc`, the compiler passes `-DQUEST_NOGC` and omits `-lgc`.

---

## 10. Shared `runtime/` Directory Structure & Implemented Functions

The runtime files are located at the repository root and shared with future native code backends:
```
runtime/
├── quest_runtime.h         /* Core ABI, QVal union, layout assertions, allocator macros */
├── quest_runtime.c         /* String primitives, math helpers, panic handlers, printing */
├── quest_serialization.h   /* Dynamic serialization & deserialization API */
├── quest_serialization.c   /* dynamic.extern & dynamic.intern (docs/dynamic.md §2) */
├── quest_io.c              /* Future: C implementation of Writer and Reader stream modules */
└── quest_conv.c            /* Future: C implementation of Conv, Ascii, IntOp, RealOp, StringOp */
```

### 10.1. Implemented Runtime Functions (`runtime/quest_runtime.c`)
- **String Primitives:**
  - `QString *quest_string_new(const char *data, size_t len)`: Allocates `QString` with trailing null byte.
  - `QString *quest_string_concat(const QString *s1, const QString *s2)`: Implements Quest `<>` string concatenation.
  - `bool quest_string_equal(const QString *s1, const QString *s2)`: Compares string length and characters.
  - `QChar quest_string_get_char(const QString *s, int64_t idx)`: Retrieves character at 0-based index.
  - `void quest_string_set_char(QString *s, int64_t idx, QChar ch)`: Mutates character at 0-based index.
  - `QString *quest_string_get_sub(const QString *s, int64_t start, int64_t len)`: Extracts substring slice.
  - `void quest_string_set_sub(QString *dest, int64_t d_start, const QString *src, int64_t s_start, int64_t len)`: Overwrites slice.
- **Array Primitives:**
  - `QArray *quest_array_new(int64_t len, QVal init_val)`: Allocates length-prefixed array with initial element values.
  - `void quest_check_array_bounds(const QArray *a, int64_t idx)`: Inline guard checking `idx >= 0 && idx < a->length`.
- **Floating-Point Math:**
  - `double quest_real_add/sub/mul(double a, double b)`, `double quest_real_divide(double a, double b)`: Implement
    `++`, `--`, `**`, and `//` inline, raising `real.error` for a result that would be NaN (and, for `//`, a zero
    divisor). Infinities pass through. See [type-system.md](type-system.md) §6.3.1.
  - `double quest_real_pow(double base, double exp)`: Implements Quest `^^` (and `real.exp`) via `pow()`, raising
    `real.error` for a zero base with a negative exponent or a NaN result.
  - `bool quest_val_is(const QTypeDescriptor *t, QVal a, QVal b)`: `is` on `QVal`-represented values; bit equality,
    or IEEE equality when `t` describes `Real` (so `0.0 is ~0.0`).
  - `uint64_t quest_identity_hash(const QTypeDescriptor *t, QVal x)`: `hash.identityHash`; hashes `~0.0` as `0.0` for
    a `Real` so that it agrees with `quest_val_is`. As a polymorphic external it receives its type parameter's
    descriptor first: the C function wrapping an external body passes its descriptors ahead of its value
    parameters, matching the wrapper's own signature.
- **Runtime Panic / Exception Handlers:**
  - `void quest_raise_int_error(void)`, `void quest_raise_real_error(void)`, `void quest_raise_word_error(void)`:
    Triggered on division or modulo by zero for `Int` (`/`, `%`), `Real` (`//`, and `^^` with a zero base and
    negative exponent), and `word.div`/`word.mod` respectively. Uncaught, they print `Exception: int.error\n` (or
    `real.error`, `word.error`) to `stderr` and terminate the process with exit code 1.
  - `void quest_option_ordinal_error(int64_t n, int64_t count)`: Triggered by `option ordinal(n) of T end` when
    `n` is outside `0 <= n < count`. Prints the same message as the interpreter and exits with code 1; like the
    interpreter's runtime error, it cannot be caught.
  - `void quest_raise_array_error(void)`: Triggered on out-of-bounds array access or negative array sizes. Prints
    `Exception: arrayOp.error\n` to `stderr` and terminates the process with exit code 1.
  - `void quest_raise_string_error(void)`: Triggered on out-of-bounds string index or slice bounds. Prints
    `Exception: string.error\n` to `stderr` and terminates the process with exit code 1.
  - `void quest_raise_dynamic_error(void)`: Triggered on dynamic coercion failure (`dynamic.be`) or invalid
    serialization/deserialization. Prints `Exception: dynamic.error\n` to `stderr` and terminates process.
- **Debug & Value Printing:**
  - `void quest_raise_variant_error(void)`: Triggered on failed variant tag assertions (`!tag`). Prints
    `Exception: variant.tagMismatch\n` to `stderr` and terminates the process with exit code 1.
  - `void quest_print_val(QVal val, const char *type_name)`: Formats and prints interactive expression results
    matching Cardelli's typescript format (e.g., `42 : Int`, `15.75 : Real`, `true : Bool`, `"hello" : String`).

---

## 11. Dynamic Serialization (`runtime/quest_serialization.c`)

Quest supports graph serialization and deserialization of dynamically typed values via `dynamic.extern(w d)` and
`dynamic.intern(r)`, in the format of [dynamic.md](dynamic.md) §2:
- **Format Parity:** The output is byte-for-byte that of the interpreter (`dynamic_json.py`): the type table is
  canonical (structurally equivalent nodes merged by partition refinement, the rest numbered depth-first from the
  roots), record fields are written by name, cases in declaration order, and reals as Python's `repr` writes them.
- **Type Tables from Descriptors:** The writer walks the descriptors of the value's type and of every nested dynamic
  value's type; recursive types, whose descriptors are cyclic, become cycles in the table.
- **Cycle & Multi-Reference Detection:** A pre-scan traversal with an address hash table finds records, arrays, and
  nonempty tuples reached more than once, which are written once with an integer `@id`. Option components are stored
  in the option value itself, so they are never shared.
- **Streaming Single-Value Parser:** `quest_dynamic_intern` streams characters from `QReader`, parsing exactly one JSON
  object/array/value while preserving unread stream characters in `peek_char` so consecutive objects can be read
  sequentially from a single stream.
- **Descriptors from Tables:** The reader allocates a descriptor for every table entry, then fills them in, so they may
  refer to each other cyclically. Static descriptors are not registered or looked up by name; `dynamic.be` compares
  descriptors structurally.
- **Single-Pass Decoding:** An object with an `@id` is allocated and registered before its components are decoded, so
  `@ref`s inside it (cycles) and after it (sharing) resolve to the same block.
- **Natural C ABI Struct Packing:** Records and tuples read from a table use standard C struct packing (8-byte
  scalars/pointers, 16-byte wide records/variants) matching static compiler emission; an option is its tag followed
  by its case's components.

---

## 12. Interface C Headers & Linkage ABI (`.int.h` generation)

When an interface `x.int.quest` is compiled (`quest -c x.int.quest`), the compiler emits a standard C header `x.int.h`
(not `x.h`, which could shadow a C library header such as `<math.h>`; see [build-process.md §3.2](build-process.md)):
- **Include Guard:** Uses standard preprocessor guards `#ifndef QUEST_INTF_<NAME>_H ... #endif`.
- **Runtime Dependency:** Always includes `#include "quest_runtime.h"`.
- **Recursive Interface Includes:** For every imported interface (`import : Dep`), emits `#include "dep.int.h"`.
- **Abstract Type Erasure:** Abstract types (`T::TYPE`) cannot have a fixed scalar size across implementations and
  erase uniformly to `typedef QVal quest_type_<Interface>_T;`.
- **Manifest Types:** Transparent types (`Def T = ...`) emit concrete C typedefs or struct definitions (e.g.
  `struct quest_rec_<Interface>_<Name>` for records).
- **Function Signature Typedefs:** Exported member functions emit function pointer typedefs
  `typedef <Ret> (*quest_sig_<Interface>_<Member>)(<Params>);`, with uniform parameter conversions
  (integers to `QInt`, reals to `QReal`, strings to `QString *`, records to `QRecordVal`, and abstract types to `QVal`).

---

## See Also
- [name-mangling.md](name-mangling.md): Comprehensive specification of compiler-generated C identifiers.
- [codegen-c.md](codegen-c.md): C Code Generator architecture, AST lowering, and compiler runner.
- [pipeline.md](pipeline.md): Compiler pipeline passes and dual-pipeline CLI driver.
- [runtime-design.md](runtime-design.md): Evidence Passing vs. Fat Pointers and AAPCS64 register ABI.
- [roadmap.md](roadmap.md): 7-stage compiler implementation roadmap.
- [type-system.md](type-system.md): Quest higher-order subtyping and typing rules.
- [step3-interpreter.md](step3-interpreter.md): Python interpreter architecture and standard library modules.

