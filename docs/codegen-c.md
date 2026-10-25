# C Code Generator and Host Compilation Architecture (`codegen_c`)

This document specifies the C the compiler generates and the host compiler driver (`bootstrap/python/quest/codegen/`).
How a program gets there, the IR and its passes, is [ir.md](ir.md); the representations of values in C are
[c-representation.md](c-representation.md).

---

## 1. Overview and Architecture

C compilation lowers a type-checked program (`TypedProgram`), or a module file, to the IR, runs the IR's passes, and
prints the result as portable C99, which the host C toolchain (`clang` or `gcc`) compiles and links with the runtime
and the objects of the modules the unit imports.

```
Typed AST (TypedProgram, or a module file's TypedModule)
           |
           v  ir/lower.py: Core IR (ANF with join points)
           v  ir/specialize.py, ir/closure.py, ir/represent.py, ir/describe.py: the passes (ir.md §8)
           |
+-----------------------+      layout.py, descriptors.py, symbols.py (shared by backends)
|   c/printer.py        | <--- c/types.py: C spellings; c/declarations.py: structs, tables, descriptors
|   (CPrinter)          |      Prints what the passes decided: no representation decisions or descriptors of its own
+-----------------------+
           |
           v  (C99 source)
+-----------------------+
| c/compiler_runner.py  | <--- Locates clang/gcc, auto-detects Boehm GC, adds -I runtime/
+-----------------------+
           |
           v
    Native Binary (Executable), or a module's object (.o)
```

### Module Structure (`bootstrap/python/quest/codegen/`)
What every backend shares, since a backend's units use the C runtime and link with the C backend's:
- **`backend.py`:** The IR's passes after lowering (`run_passes`), and the modules a unit uses without importing them.
- **`layout.py`:** How values are laid out, computed from shapes (`ir/shapes.py`) and cached per shape: layout tags
  (which name structs and descriptors), type digests and identity keys, representations (`representation`, named by
  the runtime's C types, and `signature_representation` for calls), slot representations (`slot_representation`: as
  an aggregate's slot or a `QVal` holds a value, a record or variant boxed) and location representations
  (`location_representation`: as a `var` parameter's location holds it), and whether generic code's layout agrees
  with the native one (`generic_layout_agrees`). The IR's represent pass decides its plans from these. Reduced types and the
  canonical forms of recursive types, which shapes are built from, are `types/canonical.py`'s.
- **`descriptors.py`:** Runtime descriptors' type-level forms: placeholders for bound type parameters and template
  holes, and the canonical function and auto types that descriptors compare.
- **`symbols.py`:** The names units link against (identifier and module mangling).

The C backend (`codegen/c/`):
- **`backend.py`:** Its entry points, `program_to_c` and `module_file_to_c` (lowering, passes, printing), used by
  `module_compiler.py` and `BuildEngine`; the pipeline runs the same steps as phases (`ir_core` ...
  `ir_described`, then `codegen_c`).
- **`printer.py`:** `CPrinter`, printing a described IR unit as C: the descriptors it is given (descriptor variables,
  static descriptors, instantiated templates) and the unit's static data (static descriptors, offset tables, tag
  maps), which declarations.py declares.
- **`declarations.py`:** The declarations of the types a unit uses (structs, offset and coercion tables, type
  descriptors, function type adapters), the extern declarations of imported modules' functions, and the signature of
  the functions a module file exports (`module_function_signature`).
- **`headers.py`:** Interfaces' C headers (`.int.h`): generating them, and writing those C compilation needs beside
  their `.qi` files, up to date when at least as new as the `.qi` ([build-process.md §5.3](build-process.md)).
- **`types.py`:** C spellings: the C types of representations, function pointer types, `QVal` wrapping, literals,
  record struct and offset table names, and descriptor expressions (`descriptor_form`).
- **`compiler_runner.py`:** Discovers host compiler, auto-detects Boehm GC, compiles C source, and runs binaries.

Only C compilation's drivers import `codegen/c/` (`tests/python/test_dependencies.py`).

---

## 2. Type Mapping and Identifier Mangling (`layout.py`, `symbols.py`, `c/types.py`)

### 2.1. Scalar Type Mapping
Quest scalar types map to native C99 types defined in `runtime/quest_runtime.h`:

| Quest Type | C Type | Description |
| :--- | :--- | :--- |
| `Int` | `QInt` (`int64_t`) | 64-bit signed integer |
| `Real` | `QReal` (`double`) | 64-bit IEEE-754 double precision float |
| `Bool` | `QBool` (`bool`) | C99 boolean (`true` / `false`) |
| `Char` | `QChar` (`char`) | 8-bit character (extended in 64-bit word when in `QVal`) |
| `String` | `QString *` | Pointer to heap-allocated string descriptor |
| `Ok` | `void` / `QVal` | Statement completion indicator (`Q_OK_VAL`) |
| Polymorphic / Generic | `QVal` | Uniform 64-bit value word union |

### 2.2. Identifier Namespacing and Name Mangling
To prevent collisions with C99 keywords (`int`, `return`, `default`, `static`, etc.), standard library symbols,
and C struct member keywords, Quest applies a comprehensive, deterministic name mangling scheme:
- **Value and variable names:** a unit's variables are `g_<name>` (globals) and `l_<name>` (locals), its functions
  `qf_<name>`; what other units link against, a module's exported functions, is `qv_<module>_<member>`.
- **Record field names** inside C structs are prefixed with `qf_` (e.g. `qf_default`, `qf_x`).
- **Hierarchical module paths** are flattened using `__` (e.g. `util/path` $\rightarrow$ `util__path`).
- **Symbolic operators** are mapped via `SYMBOL_MANGLE_MAP` with prefix `qv_sym_`
  (e.g. `:=` $\rightarrow$ `qv_sym_colon_equals`).
- **Temporary variable names** are generated uniquely with fresh counters (e.g. `_t1`, `_t2`).

> [!NOTE]
> For the complete, definitive specification of all generated C identifiers—including external ABI symbols,
> static module initializers, lifted lambdas, closure environments, struct tags, evidence dictionaries,
> runtime type descriptors, and local temporaries—see [docs/name-mangling.md](name-mangling.md).

---

## 3. Program Structure

### 3.1. A Unit's C
The printer writes a unit's C in this order (`CPrinter.print_unit`):
1. `#include "quest_runtime.h"`, and a module file's interface header (`<interface>.int.h`) if it has one.
2. The declarations of the types the unit uses (`c/declarations.py`), and extern declarations of the modules it
   imports: their records (`qm_<module>`), initializers (`qv_mod_<module>_init`), and exported functions.
3. The environment struct of each closure that captures values (`struct QEnv_<function>`).
4. A prototype of each of the unit's functions (every function, lifted by closure conversion), with a static closure
   of it for when it captures nothing (`static QClosure qf_<name>_closure = { (void *)qf_<name>, NULL };`).
5. Globals: the variables the top levels bind outside loops, at file scope (`static QInt g_x;`), and the records of
   the unit's modules.
6. Thunks (adapters, type applications, external C functions as closures), and `qr_register_dicts`, which registers
   the offset tables of the records the unit views at supertypes, for dynamic values.
7. The functions, the thunks, and the modules' initializers.
8. For a program, `main`: it initializes the runtime and the imported modules and the unit's own, then runs the
   program's top-level phrases. A module file has no `main`.

```c
int main(int argc, char **argv) {
    quest_gc_init();
    quest_builtins_init(argc, argv);
    qr_register_dicts();
    qv_mod_writer_init();
    /* Top-level phrases */
    ...
    return 0;
}
```

A program prints its phrases' results only with `--echo` (every phrase) or `--print-result` (the last one, as the
interpreter prints it, which `--stop-after run_c_compiled` turns on); the IR prints them (`echo`, `result`, ir.md
§6.6).

### 3.2. Variables
Each IR variable is a C variable of its type's representation: a global (`g_<name>`) if the top level binds it
outside a loop, and otherwise a local of its function (`l_<name>`), declared at the function's start. A name used
twice in one unit gets a suffix (`l_x_2`). Mutable variables are C variables too, assigned in place
(`count := count + 1` assigns `l_count`); those a `try` body assigns are `volatile` (c-representation.md §6.4).

### 3.3. Cardelli Non-Overloaded Operators
In Quest, operators are strictly non-overloaded (§4.2). The printer writes direct C99 expressions:

- **Integer Arithmetic:** `+`, `-`, `*` map to C `+`, `-`, `*`.
- **Integer Division & Modulo:** `/` and `%` call inline runtime functions with zero-divisor checks:
  ```c
  /* 42 / x */
  quest_int_div(42LL, qv_x)
  /* 42 % x */
  quest_int_mod(42LL, qv_x)
  ```
- **Real Arithmetic (Doubled Symbols):** each calls a runtime function that raises `real.error` instead of producing
  a NaN ([type-system.md](type-system.md) §6.3.1):
  - `++` $\rightarrow$ `quest_real_add((l), (r))`
  - `--` $\rightarrow$ `quest_real_sub((l), (r))`
  - `**` $\rightarrow$ `quest_real_mul((l), (r))`
  - `//` $\rightarrow$ `quest_real_divide((l), (r))` (also raises for a zero divisor)
  - `^^` (exponentiation) $\rightarrow$ `quest_real_pow((l), (r))` (also raises for a zero base and negative exponent)
  - An infinite literal is emitted as `INFINITY` or `(-INFINITY)`.
- **Relational Comparisons:**
  - Integer: `<`, `<=`, `>`, `>=`
  - Real: `<<` $\rightarrow$ `<`, `<<=` $\rightarrow$ `<=`, `>>` $\rightarrow$ `>`, `>>=` $\rightarrow$ `>=`
- **Identity and Equality:**
  - `is` and `==` map to C `==` (for scalars) or `quest_string_equal` (for strings).
  - `isnot` maps to C `!=` (or `!quest_string_equal`).
  - On a value represented as `QVal` (a type parameter or abstract type), `is` becomes
    `quest_val_is(descriptor, l, r)`, which compares bits and, for a `Real`, the doubles, so that `0.0 is ~0.0`
    holds in polymorphic code too. A type with no runtime descriptor passes `NULL` and compares bits.
- **String Concatenation:**
  - `<>` calls `quest_string_concat(s1, s2)`.

---

## 4. Control Flow

The IR is in A-normal form, with structured control and join points (ir.md §6), so each statement is a C statement,
in strict ISO C99 without statement expressions:
- **Conditionals:** `if (c) { ... } else { ... }`; a `case` over tags is a `switch`.
- **Join points:** a value-producing construct (`let x = if ... end`) jumps to a join point with its value: the join
  point's parameters are C variables, the jump assigns them and `goto`s the join point's label, which precedes its
  continuation.
- **Loops:** `for (;;) { ... }`, with `goto <label>_break` and `goto <label>_continue` for `exit` and the loops'
  conditions (a `for` loop's counter and limit are IR variables).
- **Exceptions:** a `try` region is a `setjmp` handler pushed onto `quest_current_exception_handler`, popped on every
  way out: falling off the end, a jump or loop exit out of it, a `return`, and the handler itself.

---

## 5. Functions and Calls

Closure conversion lifts every function to file scope (ir.md §8.2). Each is a static C function taking its closure's
environment first, then its type parameters' descriptors, then its parameters (pointers for `var` and `out`):
```c
/* let add(x: Int y: Int): Int = x + y; */
static QInt qf_add(void *_raw_env, QInt l_x, QInt l_y) {
    (void)_raw_env;
    ...
    return l_t;
}
```
- **Calls:** a call of a closure the unit makes (a variable bound to it) calls its function directly, passing its
  environment (`qf_add(NULL, 10LL, 20LL)`), and any other call goes through the closure (§7.4). `Ok`-returning
  functions return `void`.
- **Imported modules:** a call of an imported module's function calls the function the module exports,
  `qv_<module>_<member>` (§10.7), and its other members are fields of its record.
- **Externals:** a function defined as `external "symbol"` calls the C function with its type parameters'
  descriptors and its parameters (`call external`); an external C function used as a value is a static closure over
  a thunk calling it, and a call of a variable bound to one calls the C function directly.

---

## 6. Tuples & Concrete Records

Tuples and concrete records compile to C99 structs with heap allocation, uniform 64-bit slot layout, and direct
pointer-based field access.

### 6.1. C Struct Layout & Tag Generation
- **Positional Tuple Structs:** Tuple types map to positional members `_0`, `_1`, ... based on their component value
  fields (`t.value_fields`). Struct names are deterministic and reflect component types:
  ```c
  /* Tuple x: Int y: Real end */
  typedef struct QTuple_Int_Real QTuple_Int_Real;

  struct QTuple_Int_Real {
      QInt _0;
      QReal _1;
  };
  ```
- **Canonical Alphabetized Record Structs:** Records are unordered product types with structural equivalence. To ensure
  structurally identical record types share the same C struct definition, record struct members are sorted
  alphabetically by field name, prefixed with `qf_` (to avoid C keyword collisions):
  ```c
  /* record x = 10, y = 20.0 end */
  typedef struct QRecord_x_Int_y_Real QRecord_x_Int_y_Real;

  struct QRecord_x_Int_y_Real {
      QInt qf_x;
      QReal qf_y;
  };
  ```
- **Forward Typedef Hoisting:** The printer discovers all `QTupleType` and `QRecordType` instances
  across the AST and emits forward declarations (`typedef struct Tag Tag;`) before any struct bodies, static variables,
  or function prototypes. This guarantees that mutually referencing or nested aggregate types compile cleanly without
  ordering dependencies.

### 6.2. Heap Allocation & Member Initialization
Tuples and records are heap-allocated via `quest_alloc(sizeof(StructTag))` (managed by Boehm GC or standard `calloc`
in `--nogc` mode):
```c
/* origin = tuple let x = 0 let y = 0.0 end */
qv_origin = (QTuple_Int_Real *)quest_alloc(sizeof(QTuple_Int_Real));
qv_origin->_0 = 0LL;
qv_origin->_1 = 0.0;
```
When an aggregate expression appears in a value context (e.g. passed directly to a function call or returned from an
expression), a local temporary pointer is allocated and returned.

### 6.3. Field Selection & Mutable Field Assignment
- **Selection (`TypedSelect`):**
  - For tuples: Named fields are mapped to their 0-based value component index at compile-time (`p.x` -> `qv_p->_0`).
    Unnamed fields accessed by index also map directly (`t._0` -> `qv_t->_0`).
  - For records: Field accesses map directly to the mangled field name (`r.x` -> `qv_r->qf_x`).
- **Mutable Assignment (`TypedAssign`):**
  - When the target of `TypedAssign` is a `TypedSelect` expression on a mutable record field (`var y = ...`), the
    target expression is evaluated as an lvalue pointer dereference, storing the value directly into the heap struct:
  ```c
  /* r.y := 42; */
  qv_r->qf_y = 42LL;
  ```

---

## 7. Closures, Function Values & Lambda Lifting

In Quest, functions are first-class values that can be passed to higher-order functions, returned from functions,
and capture variables from enclosing lexical scopes.

### 7.1. Closure Representation (`QClosure`)
First-class function values use the uniform 16-byte `QClosure` struct defined in `runtime/quest_runtime.h`:
```c
typedef struct QClosure {
    void *fn;   /* C function pointer: RetType (*)(void *env, ...) */
    void *env;  /* Captured environment struct pointer or NULL */
} QClosure;

static_assert(sizeof(QClosure) == 16, qclosure_must_be_16_bytes);
static_assert(offsetof(QClosure, env) == 8, qclosure_env_at_offset_8);
```

### 7.2. Closures
Closure conversion (ir.md §8.2) decides what each closure captures: the values it uses from enclosing functions (the
top levels' variables are globals, which it uses instead), and the descriptors of the enclosing functions' type
parameters its types mention.
- **Capturing closures** get an environment struct, allocated with the closure where the closure is made:
  ```c
  _t1 = (struct QEnv_qf_h *)quest_alloc(sizeof(struct QEnv_qf_h));
  _t1->c0 = l_x;
  _t2 = (QClosure *)quest_alloc(sizeof(QClosure));
  _t2->fn = (void *)qf_h;
  _t2->env = (void *)_t1;
  ```
  The function reads its captures from the environment (`env_field`).
- **Closures capturing nothing** are the function's static closure, `(&qf_<name>_closure)`, with no allocation.
- **Recursive groups:** a closure capturing a member of its own recursive group (`let rec f ... and g ...`) is made in
  a `let rec`, and the captures of the group's members are stored in the environments once every member has been
  made.

### 7.4. Indirect Closure Invocations
When calling an indirect target (such as a closure parameter or returned function), the call site casts `fn` to the
expected C function pointer signature and passes `env` as the first argument:
```c
((QInt (*)(void *, QInt))(qv_f->fn))(qv_f->env, qv_x)
```

---

## 8. Arrays and Strings

### 8.1. Array Representation (`QArray`)
Arrays are mutable buffers of 64-bit `QVal` words with an explicit length prefix:
```c
typedef struct QArray {
    int64_t length;
    QVal    data[];
} QArray;

static_assert(offsetof(QArray, data) == 8, qarray_data_at_offset_8);
```

### 8.2. Allocation and Construction
- **Explicit Element Lists (`TypedArray`):**
  Allocates the structure and populates each element wrapped as a `QVal`:
  ```c
  QArray *qv_arr = (QArray *)quest_alloc(sizeof(QArray) + (size_t)(4LL) * sizeof(QVal));
  qv_arr->length = 4LL;
  qv_arr->data[0LL] = ((QVal){ .i = (int64_t)(10LL) });
  ...
  ```
- **Repetition (`TypedArrayRep`):**
  Invokes `quest_array_new(length, init_val)` which verifies $N \ge 0$ and initializes all elements.

### 8.3. Indexing and Mutation
Array indexing (`a[i]`) and mutation (`a[i] := v`) emit inline bounds checking followed by direct access into `data[]`:
```c
quest_check_array_bounds(qv_arr, qv_i);
QInt elem = qv_arr->data[qv_i].i;

quest_check_array_bounds(qv_arr, qv_i);
qv_arr->data[qv_i] = ((QVal){ .i = (int64_t)(99LL) });
```
Out-of-bounds indices and negative sizes trigger `quest_raise_array_error()`, printing `Exception: arrayOp.error\n`
and terminating with exit code 1.

---

## 9. Options and Variants (Sums)

### 9.1. Option Types
Option types are ordered sums with inline union payloads. Each unique `QOptionType` synthesizes:
- A tag enumeration: `QTAG_<Option>_<branch> = <index>`.
- A C struct containing `int64_t tag` and an inline union of branch structs for branches carrying components:
  ```c
  typedef struct QOption_... {
      int64_t tag;
      union {
          struct { QInt _0; } branch1;
          ...
      } u;
  } QOption_...;
  ```

### 9.2. Variant Types
Variant types are unordered sums with a single 64-bit payload word, represented as first-class 16-byte values:
```c
typedef struct QVariantVal {
    int64_t tag;
    QVal    payload;
} QVariantVal;

static_assert(sizeof(QVariantVal) == 16, qvariantval_must_be_16_bytes);
static_assert(offsetof(QVariantVal, tag) == 0, qvariantval_tag_at_offset_0);
static_assert(offsetof(QVariantVal, payload) == 8, qvariantval_payload_at_offset_8);
```

### 9.3. Injections, Tag Queries, Extractions, and Pattern Matching
- **Injection:** `option b of T with payload end` allocates and populates the union branch; `variant b of T with v end`
  constructs an unboxed `QVariantVal` compound literal directly with zero heap allocations.
- **Tag Query (`target?tag`):** Checks `target.tag == EXPECTED_TAG` on variants (or `target->tag == EXPECTED_TAG`
  on options).
- **Tag Assertion (`target!tag`):** Asserts tag match (panics with `Exception: variant.tagMismatch\n` on failure).
  Returns `payload` for variants, or a `QTuple` prepending the ordinal for options.
- **Pattern Matching (`case`):** Lowers to standard C `switch (target.tag)` (or `target->tag` for options) with
  branch payload binders.

---

## 10. Structural Subtyping & Dynamic Dispatch

Cardelli's structural subtyping is supported across tuples, records, and variants:

### 10.1. Prefix Tuple Subtyping
- **Direct Pointer Coercion:** A wider tuple pointer `QT_Triple *` is cast directly to a prefix tuple `(QT_Pair *)`.
- **Memoized Compile-Time Layout Verification:**
  ```c
  static_assert(offsetof(QT_Triple, _0) == offsetof(QT_Pair, _0), tuple_subtyping_offset_match_0);
  static_assert(offsetof(QT_Triple, _1) == offsetof(QT_Pair, _1), tuple_subtyping_offset_match_1);
  ```

### 10.2. Evidence-Passing Record Subtyping
- **Object Header:** Every concrete record structure begins with `QRecordHeader header;` at offset 0, set at
  allocation to the descriptor of the record's layout (`header.descriptor = &quest_type_QT_Point;`).
- **Polymorphic Call Arguments:** For a call with type arguments, each argument is first coerced to its parameter's
  type with the type arguments substituted (so `f(:Small big)` passes a `Small` view), then to the generic
  representation of the parameter.
- **Offset Table Map:** `main` registers each static `offsetdict_<Target>_<Source>` of the unit's static data
  (its record literals' tables, ir.md §8.4) whose types are closed with
  `quest_register_record_dict(&quest_type_<Target>, &quest_type_<Source>, &offsetdict_<Target>_<Source>)`; tables
  for other (view, layout) pairs are built by the runtime on demand (`quest_record_dict`).
- **First-Class Fat Pointers (`QRecordVal`):** All records are represented uniformly as a 16-byte struct:
  ```c
  typedef struct QRecordVal {
      void       *val;   /* Pointer to heap-allocated QT_<Record> payload */
      const void *dict;  /* Pointer to static OffsetDict_<Record> */
  } QRecordVal;
  ```
- **Function Parameters & Returns:** Functions take `QRecordVal` directly and return `QRecordVal` directly
  (passed in `x0, x1` under AAPCS64), eliminating companion dictionary arguments.
- **Dictionary Naming:** Uses the alias name when available (`OffsetDict_<Alias>_<digest>`), or
  `OffsetDict_record_<digest>`, where the digest is of the record's field names and types (docs/name-mangling.md §6.1).
- **Field Selection:** Dynamic dispatch reads fields via byte offsets from embedded dictionaries:
  ```c
  (*((QInt *)((char *)qv_pt.val + ((const OffsetDict_Point2D *)qv_pt.dict)->offset_x)))
  ```
- **Aggregate Storage:** Every slot of an aggregate (tuple, option payload, record, array, auto payload, module
  record) is one word: records and variants are pointers to immutable 16-byte boxes (`QRecordVal *`, `QVariantVal *`,
  made by `quest_record_box` and `quest_variant_box`), `Bool`s and `Char`s words of their own (`QBoolSlot`,
  `QCharSlot`) (c-representation.md §5.1, Slots). Reading a slot reads the box; storing makes one, or reuses the box
  the value was read from. Subtyped variants apply static tag remapping (`tagmap_<Target>_<Source>`) before they are
  stored.

### 10.3. Variant Subtyping & Static Tag Remapping
- **First-Class Value Representation:** `QVariantVal` is a 16-byte value type (`int64_t tag; QVal payload;`).
  Variant creation, checks (`v?x`), assertions (`v!x`), and `case` pattern matching execute with zero heap allocations.
- **Static Tag Tables:** Static lookup tables in `.rodata` translate source tags to target tags:
  ```c
  static const int64_t tagmap_Large_Small[] = { 2LL, 1LL };
  ```
- **Zero-Allocation Upcast:** Coercion emits an unboxed compound literal:
  `((QVariantVal){ .tag = tagmap_Large_Small[src.tag], .payload = src.payload })`.

### 10.4. Bounded Specialization for Records and Variants
- **Runtime Descriptor Retention:** Bounded polymorphic functions retain `const QTypeDescriptor *descriptor_<T>`
  parameters in their C signatures to facilitate separate compilation and uniform reflection.
- **Bounded Record Parameters & Field Selection:** Functions expecting `A <: Record` receive `QRecordVal` directly.
  Field selection `p.x` dynamically indexes through the passed-in dictionary:
  `((const OffsetDict_Bound *)p.dict)->offset_x`.
- **Caller Dictionary Restoration on Return:** When returning a bounded type variable `A <: Record`, the caller
  restores the dictionary (`Option A: Caller Restores Dictionary`), attaching the identity dictionary `&offsetdict_T_T`
  of the concrete type argument `T` to the returned `.val`.
- **Bounded Variant Parameters & Call-Site Tag Alignment:** Callers align variant tags to the bound variant type using
  static `.rodata` tag tables into an unboxed compound literal, allowing callees to switch directly on `v.tag` without
  runtime translation or heap allocation.

### 10.5. Call-Site Specialization for Unbounded Quantifiers
When unbounded polymorphic functions (`All(A::TYPE)`) are invoked at call sites with concrete `Record` or `Variant`
arguments:
- **Specialization Pass (`ir/specialize.py`, ir.md §8.1):** Clones a function called with type arguments that hold
  records or variants (decided on their shapes), local functions included, substituting the types (a module's clones
  are its members `<name>_spec<n>`), to a bounded depth.
- **Direct Calling Convention & Zero-Boxing:** Specialized function clones take unboxed `QRecordVal` and `QVariantVal`
  parameters directly without descriptor parameters (unless uninstantiated quantifiers remain) and pass them in
  register pairs `(x0, x1)` without heap boxing.
- **Struct Layout:** Generic tuples within specialized clones instantiate concrete C structs
  (`struct QTuple_<TypeTags>`), which agree with the generic ones in memory anyway, every slot being a word.
- **First-Class Fallback:** The canonical unspecialized `QVal` version is retained for indirect calls and closures.

### 10.6. Arrays of Records and Variants
Arrays of records and variants are `QArray`s like any other, of slots holding boxes (c-representation.md §5.4).
Indexing reads the box; assignment stores one (applying the offset table or tag remapping of a subtype first). An
array of records passes to generic code (`Array(A)`) by cast.

### 10.7. Unified Native Module Mechanism & Hybrid Modules
All modules—whether pure Quest, standard library built-ins (`writer`, `reader`, `conv`, `ascii`, `int`, `real`,
`string`, `system`, `arrayOp`, `dynamic`), or user-defined hybrid modules—are compiled uniformly:
- **Module files through the IR:** a module file is a unit of its own (`module_file_to_c`), whose module has
  exports: its interface's members at the interface's types, converted from its own members by the represent pass
  (ir.md §3). Its record holds them, and it exports a C function `qv_<module>_<member>` for each that is a function or
  a polymorphic value, which calls the export's closure (the ABI importers call, `module_function_signature`).
- **Topological Lazy Initializers (`qv_mod_<name>_init`):**
  - Each module emits an initialization function guarded by `qv_mod_<name>_initialized` for idempotent execution.
  - Recursively triggers initializers of dependency modules in topological order before executing local bindings.
  - Allocates the module payload struct (`QT_<Interface>`) and populates all exported fields with **concrete values**:
    - Functions are closures; external C functions are closures over thunks calling them.
    - External C values and evaluated `let` bindings populate fields directly, boxed (`QVal`) where the interface's
      type is abstract.
- **Calls of Library Functions:** A call of an imported module's function (e.g. `writer.putString(w s)`) calls the
  function the module exports (`qv_writer_putString`), which calls the C function (`quest_writer_put_string`).
  In `lib/dynamic.mod.quest`, `dynamic.new` and `dynamic.be` are Quest functions (`auto :A with a end` and `inspect`),
  while `dynamic.copy`, `dynamic.extern`, and `dynamic.intern` are declared `external` with zero compiler
  special-casing.
- **External C Types and Values:** `external "C_TYPE"` and `external "C_SYMBOL"` seamlessly bridge C runtime
  structures (e.g. `QWriter *`, `QReader *`) into Quest's type system without compiler special-casing.

### 10.8. Mutable Reference Parameters (`out` and `var`) and `@` Lvalues
Cardelli's mutable reference parameters compile directly to native C pointers:
- **Native Pointer Parameters (`T *`):** Parameters marked `var p: T` or `out p: T` compile directly to
  `T *l_p` in C declarations, definitions, and closures. Reads from `var` parameters dereference the
  pointer (`*l_p`), and writes to `var`/`out` parameters assign through the pointer (`*l_p = val;`).
- **Callsite Lvalue Emission (`@`):**
  - Variable references `@x` emit `&qv_x`.
  - Pointer parameter forwarding `g(@y)` directly passes `qv_y` without taking its address (`&`).
  - Record field references `@r.f` emit pointers into the heap record buffer
    (`(({fld_t} *)((char *)rec.val + offset))`).
  - Array element references `@a[i]` emit pointers into the flat array buffer (`&arr->data[i]`).
  - Tuple element references `@t.1` emit pointers to tuple components (`&tup->_1`).
  - Temporary cells `var(e)` evaluate `e` into a stack local and pass its address (`&_var_cell`).
- **Polymorphic Reference Invocations (Two-Tier Model):**
  - **Tier 1 (Specialization):** Direct calls in the unit are specialized (`ir/specialize.py`); the clone takes
    native `T *` parameters, passing lvalue pointers directly without overhead.
  - **Tier 2 (Unspecialized callees):** For an unspecialized polymorphic callee (`var p: A`, a `QVal *`), a location
    holding a record or variant passes as it is (cast to `QVal *`): a `var` parameter's location holds a record or
    variant boxed, as a slot does (`location_representation`; a local variable whose address is taken is held boxed),
    so a field or element is updated in place. Any other location whose representation differs from a `QVal` (a
    `Bool` local, a closure) is passed as the address of a shadow cell of the parameter's representation, copied in
    from the location for `var` and copied out to it after the call (`ref_argument`, ir.md §8.3).
- **Closure Capture Restrictions:** Closure capture of `out`/`var` parameters or local stack mutable variables
  is prohibited at compile time, guaranteeing that pointers never outlive their stack frames.

### 10.9. Existential Tuples & Dot-Projections
Existential tuples (weak sums `Tuple A::TYPE ... end`), path-type projection (`p.T`), and member projection (`p.v`)
are lowered as follows:
- **Struct Layout & Type Formal Erasure:** In static compilation, type formal components (`A::TYPE`, `A <: T`) are
  erased from the physical C struct layout. Positional value indices (`_0`, `_1`, etc.) correspond strictly to the
  tuple's value components.
- **Bounded Path-Type Native Lowering (`resolve_type_bound`):**
  - Unbounded type variables and path-types (`A::TYPE`, `p.T`) map to uniform 64-bit `QVal`. Scalar values are boxed
    via `qval_wrap` and unboxed via `qval_unwrap`.
  - Bounded type variables and path-types (`A::POWER(T)`, `p.T <: T`) unbox directly to the bound's native C type
    (e.g., `QInt`, `QReal`), eliminating dynamic boxing and preserving full native performance.
- **Closure Adaptation Thunks (`adapt` plans, ir.md §8.3):** When packaging or coercing a tuple containing closures
  whose concrete signatures differ from the abstract interface signature (e.g., `create(init: Int): Counter` where
  `Counter = Int` coerced to `create(init: Int): A`), the printer makes static adaptation thunks
  (`qa_adapt`). The thunk unpacks/forwards the original closure's environment, unwraps any `QVal` arguments with
  `qval_unwrap`, invokes the underlying native function, and wraps any abstract return value with `qval_wrap`. A thunk
  is also made when a closure is used at a function supertype whose arguments or result need converting (records,
  variants, options, tuples, functions): it coerces each argument from the target parameter type to the closure's
  and the result back, so `Fun(x: Small): Big` works as `Fun(x: Big): Small`.
- **Function Type Adapters (`quest_adapt_fun_<digest>`) and Invokers (`quest_invoke_fun_<digest>`):** Every
  function type with a runtime descriptor gets an adapter and an invoker, referenced by the descriptor, for
  conversions known only at run time; see [c-representation.md](c-representation.md) §6.4 (Compound Descriptor
  Payloads, Functions).
- **Descriptors:** Every descriptor the code uses is an operand the describe pass gave it (ir.md §8.4): a descriptor
  variable (a function's `descriptor_<T>` parameter, a thunk's `qd_<k>`, an inspected auto value's `->type_desc`), a
  static descriptor (`&quest_type_<tag>`), or a template (a type that mentions type parameters in scope, its holes
  `?0`, `?1`, ...) instantiated at run time with their descriptors (`quest_instantiate_descriptor`); see
  [c-representation.md](c-representation.md) §6.4.5. The printer declares only the static descriptors (with those
  of their parts) and the offset tables and tag maps the unit's static data lists, ahead of the function
  definitions.
- **Tuple Upcasts (`view` plans, proxies):** An upcast of a tuple or option whose components change view (a record
  at a supertype, a variant or option whose cases the supertype numbers differently, a closure whose signature
  changes) makes a proxy of the original, `quest_make_proxy` (c-representation.md §5.8). For a tuple or option type
  that may be proxied (`may_be_proxied`), the represent pass records each read's access (ir.md §8.3), which the
  printer prints: through `quest_is_proxy` checks (`tuple_component`, `option_tag`, `option_component`), from the
  original's slot through `quest_unproxy` for components that cannot change view, or directly for tuples and options
  a function made itself; `var` components are written into the original (`quest_proxy_store`, `quest_proxy_slot`),
  and `is` compares the originals. An upcast that changes no component's view is a cast; one to a type that cannot be
  proxied is an `unproxy` plan.
- **Slots:** records and variants are boxed in aggregate slots; the represent pass makes boxing explicit (boxed
  variables, `slot_box` and `slot_unbox` conversions, components boxed in a tuple's or record's own allocation), so
  that the printer reuses the box a value was read from only where the IR says so (ir.md §8.3).
- **End-to-End Golden Verification:** Verified across all phases (`tokenize`, `parse`, `typecheck`, `interpret`,
  `run_c_compiled`) via `existential_packages.quest`, `existential_adt.quest`, `cardelli_syntax.quest`, and
  `polymorphic_refs_records.quest`.

---

## 11. Host Compiler Runner (`c/compiler_runner.py`)

The compiler runner manages external C compiler toolchain discovery, Boehm GC flags, and native executable generation:

### 11.1. Compiler Discovery
`find_c_compiler()` searches `PATH` in order:
1. `clang` (preferred on macOS/Linux for optimal diagnostic output and C99 statement expression support).
2. `gcc` (fallback).

### 11.2. Boehm GC Auto-Detection & `--nogc`
`detect_gc_flags(nogc: bool)` locates the Boehm Garbage Collector:
- Standard paths checked: `/opt/homebrew/opt/bdw-gc` (Apple Silicon), `/usr/local/opt/bdw-gc` (Intel macOS), `/usr`.
- If found: passes `-I<prefix>/include -L<prefix>/lib -lgc`.
- If not found or when `--nogc` flag is specified: passes `-DQUEST_NOGC`, using standard libc `calloc`/`malloc`.

### 11.3. Compilation Invocation
`compile_c_source(c_source, output_path, nogc)`:
1. Writes emitted C source to a temporary file (`.c`).
2. Constructs compilation command:
   ```bash
   clang -std=c99 -Wall -Wextra -O2 \
     -I <repo_root>/runtime <repo_root>/runtime/quest_runtime.c \
     <repo_root>/runtime/quest_serialization.c \
     <temp.c> -o <out_bin> [GC_FLAGS]
   ```
3. Executes command via `subprocess.run()`. On failure, captures `stderr` and raises `RuntimeError`.
4. Cleans up temporary C source file.

---

## 12. Verification & Test Suite

Every golden test program is compiled to C and run (`run_c_compiled`), and its output compared with the
interpreter's; the run error tests are compiled too ([testing.md](testing.md)). The IR's passes are checked on their
own (`run_ir_<stage>`, and unit tests in `tests/python/test_ir_*.py`). Unit tests cover what goldens cannot express:
the pipeline's phases, `--nogc`, and `quest compile` (`test_phase4_1_c_codegen.py`); layouts and conversions
(`test_generic_layouts.py`, `test_layout_differential.py`, `test_conversion_rejections.py`), and the conversion
matrix (`tests/conversions/generate.py`); module files and
separate compilation (`test_module_compiler.py`, `test_separate_compilation_types.py`, and others); existential
tuples (`test_existential_tuples.py`); and runtime descriptors (`test_runtime_descriptors.py`).

---

## See Also
- [c-representation.md](c-representation.md): 64-bit `QVal` representation, ABI assertions, and aggregate layouts.
- [pipeline.md](pipeline.md): Pipeline passes and driver CLI commands.
- [runtime-design.md](runtime-design.md): Architectural design for Evidence Passing and runtime representations.
