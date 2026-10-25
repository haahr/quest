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
- **Canonical Alphabetized Record Structs:** Records are unordered product types with structural equivalence. Record
  struct members begin with `QRecordHeader header;` (pointing to the creation-time `QTypeDescriptor`) followed by fields
  sorted alphabetically by field name and prefixed with `qf_` (to avoid C keyword collisions), using each field's
  8-byte slot representation (`slot_representation`):
  ```c
  /* record x = 10, y = 20.0 end */
  typedef struct QT_record_<digest> QT_record_<digest>;

  struct QT_record_<digest> {
      QRecordHeader header;
      QInt          qf_x;
      QReal         qf_y;
  };
  ```
- **Forward Typedef Hoisting:** The declaration collector (`codegen/c/declarations.py`) discovers all aggregate types in
  `Unit.static_data` and emits forward declarations (`typedef struct Tag Tag;`) before struct bodies, static variables,
  or function prototypes. This guarantees that mutually referencing or nested aggregate types compile cleanly without
  ordering dependencies.

### 6.2. Heap Allocation, Embedded Boxes, & Member Initialization
Tuples and records (`ir.MakeTuple`, `ir.MakeRecord`) are heap-allocated via `quest_alloc` (managed by Boehm GC or
standard `calloc` in `--nogc` mode):
```c
/* origin = tuple let x = 0 let y = 0.0 end */
g_origin = (QTuple_Int_Real *)quest_alloc(sizeof(QTuple_Int_Real));
g_origin->_0 = 0LL;
g_origin->_1 = 0.0;
```
- **Records Allocated in Their Box:** Every record value in a local or parameter is an unboxed 16-byte `QRecordVal`
  (`{ val, dict }`), whereas a record stored in an aggregate slot is a `QRecordVal *` box pointer. `ir.MakeRecord`
  allocates `sizeof(QRecordVal) + sizeof(struct QT_...)` in a single block so that boxing the newly created record into
  a slot (`ir.SlotBox` with `embedded`) reuses that prefix box without a second allocation.
- **Embedded Slot Boxes:** When an aggregate constructor stores newly boxed records or variants (`embedded = (True,
  ...)` from `ir/represent.py`), `CPrinter.embedded_boxes` appends `k * sizeof(QRecordVal)` bytes to the aggregate
  allocation and slices embedded boxes directly from the trailing space.

### 6.3. Field Selection, Proxy Access Modes, & Mutable Assignment
All aggregate slots are 8-byte words (`slot_representation`). The representation pass (`ir/represent.py`) annotates each
`ir.Field`, `ir.Tag`, `ir.Addr`, and `ir.Store` with how the aggregate is accessed:
- **Tuple and Option Selection (`ir.Field`):**
  - **`direct`** (the static type cannot hold a `QProxy`, e.g. `Tuple Int Real end`): emits a direct struct member read
    `l_p->_0`.
  - **`original`** (reading through a `var` location where invariance guarantees no conversion on the component): strips
    any proxy tag via `((TupleStruct *)quest_unproxy(l_p))->_0`.
  - **`proxy`** (the tuple or option type may hold a `QProxy` from a depth upcast,
    [runtime-design.md §2.3](runtime-design.md)): tests `quest_is_proxy(l_p)` first; on the fast path reads `l_p->_0`
    directly, and on the proxy path calls `quest_proxy_field(l_p, 0, is_mutable)` to convert on demand (memoizing
    immutable components in `proxy->cache`).
- **Record Selection (`ir.Field` on `QRecordVal`):**
  - Looks up the byte offset in the fat pointer's `.dict` (`((const OffsetDict_Target *)l_r.dict)->offset_x`). If the
    field's type could differ by depth subtyping, checks `dict->stored_types` via `quest_record_field_value`.
- **Mutable Field Assignment (`ir.Store`):**
  - Assigning to a mutable record field writes through the offset dictionary:
    `*((QInt *)((char *)l_r.val + ((const OffsetDict_Target *)l_r.dict)->offset_y)) = 42LL;`.
  - Assigning to a mutable tuple component writes to the unproxied root tuple (`quest_unproxy(l_t)`) via
    `quest_proxy_store(l_t, index, val_word)` when the tuple type may be proxied, or `l_t->_0 = val` when direct.

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
Closure conversion ([ir.md §8.3](ir.md)) decides what each closure captures: the values it uses from enclosing functions
(the top levels' variables are globals, which it uses instead), and the descriptors of the enclosing functions' type
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

### 7.3. Indirect Closure Invocations
When calling an indirect target (`ir.Call` with a closure callee), the call site casts `fn` to the expected C function
pointer signature and passes `env` as the first argument:
```c
((QInt (*)(void *, QInt))(l_f->fn))(l_f->env, l_x)
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
- **Explicit Element Lists (`ir.MakeArray`):**
  Allocates the structure (`quest_alloc_atomic` for scalar elements, `quest_alloc` for pointer/boxed elements) and
  populates each 8-byte slot:
  ```c
  l_arr = (QArray *)quest_alloc_atomic(sizeof(QArray) + (size_t)(4LL) * sizeof(QVal));
  l_arr->length = 4LL;
  ((QInt *)l_arr->data)[0LL] = 10LL;
  ...
  ```
- **Repetition (`ir.ArrayRep`):**
  Checks `quest_check_array_count_at(count, "file:line:col")` and initializes all `count` slots with the evaluated
  initial value.

### 8.3. Indexing and Mutation
Array indexing (`ir.Index`) and mutation (`ir.Store` to an array element) emit inline bounds checking with source
location (`quest_check_array_bounds_at`) followed by direct slot access:
```c
quest_check_array_bounds_at(l_arr, l_i, "file.quest:12:5");
l_elem = ((QInt *)l_arr->data)[l_i];

quest_check_array_bounds_at(l_arr, l_i, "file.quest:13:5");
((QInt *)l_arr->data)[l_i] = 99LL;
```
Out-of-bounds indices and negative sizes call `quest_raise_array_error_at(loc)`, reporting the raise site and active
call frames ([exceptions.md](exceptions.md)).

---

## 9. Options and Variants (Sums)

### 9.1. Option Types
Option types are ordered sums with inline union payloads (`QOption_<tags>`):
- Because option types with the same cases in different orders are equal ([type-system.md §6.8](type-system.md)),
  canonical shapes order option cases alphabetically by name (`cases_by_name` in `ir/shapes.py`), so equal option types
  share one C struct and tag numbering (`0, 1, ...` in alphabetical order).
- A C struct containing `int64_t tag` and an inline union of branch structs for branches carrying components, where
  each component uses its 8-byte `slot_representation`:
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
Variant types are sums with a single 64-bit payload slot (also ordered by case name in shapes), represented in locals,
parameters, and return values as first-class 16-byte structs (`QVariantVal`), and in aggregate slots as `QVariantVal *`
box pointers:
```c
typedef struct QVariantVal {
    int64_t tag;
    QVal    payload;
} QVariantVal;
```

### 9.3. Injections, Tag Queries, Extractions, Ordinals, and Pattern Matching
- **Injection:** `ir.MakeOption` allocates and populates the union branch; `ir.MakeVariant` constructs an unboxed
  `QVariantVal` compound literal directly with zero heap allocations. For `option ordinal(n) of T end`, if `T` as
  written lists its cases in an order other than alphabetical, `CPrinter` maps `n` through a constant permutation table
  from the written order to the struct's alphabetical tag order.
- **Tag Extraction (`ir.Tag`) and `ordinal(o)`:** Reads `v.tag` on variants, or `p->tag` (or `quest_option_tag(p)` when
  `via proxy`) on options. For `ordinal(o)`, if the static option type as written lists its cases in a non-alphabetical
  order (recorded in `ir.Prim.cases`), `CPrinter` maps the alphabetical tag to the case's 0-based index in the static
  type via a constant table.
- **Tag Assertion (`ir.Payload`):** Asserts tag match (raising `variant.tagMismatch` at `node.offset` on failure) and
  extracts the payload (`v.payload` for variants, or the branch tuple prepending the static type's case ordinal
  `ir.Payload.ordinal` for options).
- **Pattern Matching (`ir.Case`):** Emits a C `switch` over the extracted tag with each arm jumping to its join point or
  returning.

---

## 10. Structural Subtyping, Proxies, & Specialization

Cardelli's structural subtyping is lowered to explicit conversion plans (`ir.Convert`) by `ir/represent.py`
([ir.md §8.4](ir.md)):

### 10.1. Tuple & Option Subtyping (`cast` vs. `view` / `proxy_tuple`)
- **Prefix Tuple & Index-Preserving Option Subtyping (`cast`):** When a wider tuple is coerced to a prefix tuple and all
  kept components have the same representation, or when an option is coerced to a supertype option where every subtype
  case keeps the same alphabetical tag index and payload representation (e.g. `Option a b end <: Option a b c end`),
  `ir.Convert` uses a direct pointer `cast` `(TargetStruct *)l_src`, accompanied by memoized `static_assert` checks on
  tuple field offsets.
- **View-Changing Upcasts via Tagged Proxies (`view` / `proxy_tuple` / `proxy_option`):** When a tuple or option is
  upcast to a supertype where a component changes representation (e.g. a record component gets a narrower offset
  dictionary, a variant component remaps tags, or a closure component is wrapped in an adapter thunk) or where an
  option's alphabetical tag indices shift (e.g. `Option b c end <: Option a b c end`), copying the aggregate would break
  object identity (`is`) and disconnect mutable `var` components. Instead, the value is wrapped in a tagged `QProxy`
  ([runtime-design.md §2.3](runtime-design.md)) via `quest_make_tuple_proxy`, `quest_make_option_proxy`, or
  `quest_convert`.

### 10.2. Evidence-Passing Record Subtyping (`record_dict` / `record_view`)
- **Object Header:** Every concrete record structure begins with `QRecordHeader header;` at offset 0, set at
  allocation to the descriptor of the record's layout (`header.descriptor = &quest_type_QT_Point;`).
- **Static vs. Dynamic Dictionary Attachment:** Coercing a freshly constructed record literal with statically known
  layout attaches `&offsetdict_<Target>_<Source>` (`record_dict`); coercing an arbitrary record value looks up or builds
  the offset dictionary from `r.val`'s header descriptor via `quest_record_view(r, &quest_type_<Target>)`.
- **Aggregate Storage:** Inside any aggregate slot, a record or variant is stored as an immutable 16-byte heap box
  pointer (`QRecordVal *`, `QVariantVal *`). Reading a slot unboxes (`ir.SlotUnbox`) or forwards the box pointer
  directly (`ir/slots.py`); storing a subtyped record or variant updates its `.dict` or `tag` before boxing.

### 10.3. Variant Subtyping & Static Tag Remapping
- **First-Class Value Representation:** `QVariantVal` is a 16-byte value type (`int64_t tag; QVal payload;`).
  Variant creation, checks (`v?x`), assertions (`v!x`), and `case` pattern matching execute with zero heap allocations.
- **Static Tag Tables:** Static lookup tables in `.rodata` translate source tags to target tags:
  ```c
  static const int64_t tagmap_Large_Small[] = { 2LL, 1LL };
  ```
- **Zero-Allocation Upcast:** Coercion emits an unboxed compound literal:
  `((QVariantVal){ .tag = tagmap_Large_Small[src.tag], .payload = src.payload })`.

### 10.4. Bounded Type Parameters: Own Views and View Maps
- **Runtime Descriptor Retention:** Bounded polymorphic functions retain `const QTypeDescriptor *descriptor_<T>`
  parameters in their C signatures to facilitate separate compilation, runtime reflection, and view-map lookup.
- **Own Views at Call Sites:** Callers pass and receive values of a bounded type parameter (`A <: B` where `B` is a
  record, variant, or option type) at their **own view**—their type argument's view—in the bound's representation
  (`QRecordVal`, `QVariantVal`, or option pointer), with zero conversion on entry or return.
- **Reading Through a View Map (`QViewMap`):** For each bounded type parameter whose values the function body accesses
  through its bound (`ir.Function.view_maps`), the function prologue fetches a memoized view map via
  `quest_view_map(descriptor_A, &quest_type_Bound)`. Record fields are read or addressed through the view map
  (`quest_view_record_field`, `quest_view_record_slot` for `var` fields), variant and option tags are mapped via
  `quest_view_option_tag`, and payloads or option components whose stored types narrow by depth subtyping are converted
  via `quest_view_part` / `quest_view_option_component` ([c-representation.md §5.1](c-representation.md)).

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
