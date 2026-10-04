# Design Document: AST Dump Size Optimization and Type System Performance

## 1. Problem Statement

During the compilation and golden test verification of Milestone 1 Phase 3 (`questlang/syntax_ast.quest`), two major
issues emerged in the bootstrap compiler:

1. **Massive Golden File Explosion (111.34 MB)**:
   The generated typecheck output file (`tests/golden/typecheck/questlang/syntax_ast.out`) grew to **111.34 MB**,
   causing GitHub's pre-receive hook to reject `git push` due to exceeding GitHub's 100 MB file limit.
2. **Subtyping and Typechecking Latency**:
   Typechecking recursive types across modular interfaces incurred significant re-evaluation overhead due to repeated
   pairwise structural proofs across identical and compound types without persistent memoization.

---

## 2. Root Causes of AST Dump Size Explosion

### 2.1. Unchecked Equi-Recursive Type Expansion in `TypedNode.dump`
`typed_ast_dump` walks the typed AST and formats each node's `:type` attribute via `str(type_val)`. For large
equi-recursive sum types like `ast.ExprForm` (`Rec(ExprForm :: TYPE) Option ...`), `str()` recursively expands the
complete sum type across all 25+ variants, parameter lists, tuple fields, and nested type forms. A single formatted
instance of `ExprForm` is **118 KB**. When serialized across 278 typed nodes in `syntax_ast.out`, repeated expansions
produced over 30 MB.

### 2.2. Module Record Type Expansion
Whenever a qualified value or constructor is selected from an imported module (`ast.makeDecl`, `ast.exprId`, etc.), the
typechecker synthesizes a `TypedSelect` whose target is `TypedVar(name='ast', type_val=mod_type)`. The module type
`mod_type` is a `QRecordType` containing every single exported function, procedure, type constructor, and value
signature in the module. For `ast` (40+ exported functions taking and returning recursive AST types), stringifying
`mod_type` expands to **5,173,315 characters (5.17 MB)** on a single line. In `syntax_ast.out`,
`(TypedVar 'ast' :type Record ...)` was printed 15 times, generating **~77.6 MB** of redundant text alone.

### 2.3. Absence of Type Environment and Alias Awareness in AST Dumping
The AST dump function `typed_ast_dump` / `TypedNode.dump` formats `QType` instances without access to the compilation
environment's declared type aliases or module names. Instead of emitting `:type ast.ExprForm` or `:type Module 'ast'`,
it unconditionally invokes the default structural `__str__` of the unaliased type representation.

---

## 3. Goals & Non-Goals

### Goals
- **Compact & Deterministic Output**: Reduce AST dump output size for modular programs by $99\%+$ (e.g. `syntax_ast.out`
  from 111 MB to $< 250\text{ KB}$).
- **Human-Readable Dumps**: Preserve syntactic clarity by displaying canonical type alias paths (e.g. `ast.ExprForm`,
  `location.Span`, `ast.Decl`) instead of raw structural unfolds.
- **Persistent Memoization**: Introduce session-scoped subtyping memoization to accelerate typechecking without
  corrupting active cycle detection trails.
- **Elimination of Python Structural `==` / `__eq__` on Types**: Eliminate usage of Python's recursive `__eq__` on
  Quest `QType` objects to prevent recursion limit failures and redundant structural tree traversals.
- **Maintain Language & Source Integrity**: Never alter valid, idiomatic Quest user code to avoid compiler or dump
  limitations.
- **Line Length & Tooling Compliance**: Strictly adhere to the project constraint of $\le 120$ characters per line for
  all compiler source code and design documentation.

### Non-Goals
- Changing the underlying semantic type representations during typechecking or subtyping (types remain full
  equi-recursive `QType` structures internally).

---

## 4. Elimination of Python Structural `==` / `__eq__` on Quest Types

### 4.1. The Hazard of Naive Structural Equality on Types
In Python, dataclasses generate `__eq__` by performing elementwise recursive equality checks across all fields. For
recursive Quest types (`QRecType`, `QRecGroupType`, or cyclic type graphs), evaluating Python `sub == sup`:
1. Can blow the Python interpreter stack with `RecursionError` on cyclic or mutually recursive types.
2. Duplicates the coinductive reasoning that `is_subtype` already implements.
3. Obscures whether an equality check is intentional syntactic identity, nominal symbol matching, or semantic
   coinductive equivalence.

This same principle applies equally to future implementations in C or self-hosted Quest: **never perform naive
structural equality on recursive or cyclic types**. Equality between equi-recursive types must always be coinductive
or use canonical pointer identity / hash-consing.

### 4.2. Action Plan for `types.py`
1. **Remove `sub_lazy == sup_lazy` in `is_subtype`**:
   Line 1068 of `bootstrap/python/quest/types.py` currently contains:
   ```python
   if sub_lazy is sup_lazy or sub_lazy == sup_lazy:
       return True
   ```
   Replace this with:
   - Python object identity: `if sub_lazy is sup_lazy: return True`
   - Explicit symbol ID match for variables:
     ```python
     if (isinstance(sub_lazy, (QTypeVar, QAbstractType))
             and isinstance(sup_lazy, (QTypeVar, QAbstractType))
             and sub_lazy.symbol_id == sup_lazy.symbol_id):
         return True
     ```
   - For primitive singleton types (`QIntType`, `QBoolType`, `QStringType`, `QCharType`, `QRealType`, `QOkType`),
     match on their concrete type classes directly (`type(sub_lazy) is type(sup_lazy)`).
2. **Deprecate or Override `QType.__eq__`**:
   Override `__eq__` on `QType` to raise `NotImplementedError` or strictly enforce reference identity (`self is other`),
   directing callers to `is_type_equal(t1, t2, env)` which properly threads the coinductive trail and environment.

---

## 5. Persistent Subtyping Memoization

### 5.1. Session-Scoped Memoization Table
Currently, `is_subtype(sub, sup, env, trail, fuel)` uses an active assumption stack `trail: set[tuple[int, int]]`.
While this correctly detects coinductive cycles, its entries are ephemeral to each recursive branch and are not
reused across independent subtyping queries across the program.

### 5.2. Design of Persistent Memo Cache
1. **Scope**: Attached to the active compilation `Environment` (e.g. `env.subtype_cache: dict[tuple[int, int], bool]`).
2. **Lifetime**: Scoped strictly to the compilation session of a unit or program. Cleared between top-level runs to
   avoid retaining stale entries if environments mutate.
3. **Soundness with Respect to the Coinductive Trail**:
   - A subtyping check that succeeds *without* relying on an active cycle assumption in `trail` is unconditionally
     true and can be safely committed to the persistent cache: `env.subtype_cache[(id(sub), id(sup))] = True`.
   - Results conditional on active coinductive hypotheses in `trail` must not be cached globally without tracking the
     dependency set, ensuring cycle hypotheses do not falsely certify unrelated queries.
   - Negative results ($S \not\le T$) for closed, ground types are also permanently cacheable.

---

## 6. Architecture for Reducing AST Dump Output Size

### 6.1. Module Record Compaction
1. All module imports in `bootstrap/python/quest/modules.py` and `module_loader.py` assign the module's qualified import
   name or path to `provenance` (e.g. `provenance="ast"` or `provenance="writer"`).
2. In `QRecordType.__str__()` (or a dedicated `dump()` method):
   ```python
   def __str__(self) -> str:
       if self.provenance:
           return f"Module '{self.provenance}'"
       ...
   ```
   This immediately replaces 5.1 MB expansions like `(TypedVar 'ast' :type Record makeType: ...)` with
   `(TypedVar 'ast' :type Module 'ast')`, reducing the dump by over 77 MB with a single, semantically clearer token.

### 6.2. Context-Aware Type Printing with Alias Preservation
1. Introduce `TypeFormatContext` or provide `env: Optional[Environment]` to `TypedNode.dump(indent, env)` and
   `TypecheckPhase.dump(output_data, ctx)`:
   - Before stringifying a `QType`, check `env` for registered manifest type symbols or imported aliases.
   - If `id(type_val)` matches a registered type symbol (e.g. `ast.Expr`, `ast.TypeExpr`, `ast.Decl`), print its
     qualified name instead of unfolding the underlying `Rec(...)` or `Option ...`.
   - For `QRecType` without an alias, limit unfolding depth to 1 and print recursive references by their variable
     name (`Rec(ExprForm) Option ...`).
2. This will reduce `tests/golden/typecheck/questlang/syntax_ast.out` from **111 MB** down to **$< 200\text{ KB}$**,
   while making the typed AST dumps dramatically more readable and informative.

---

## 7. Phased Execution Plan

The implementation is structured into three self-contained, sequentially verifiable phases:

```
+------------------------------------+
| Phase 1: Type Equality & Subtyping |
|          Performance Hardening     |
+-----------------+------------------+
                  |
                  v
+-----------------+------------------+
| Phase 2: AST Dump Compaction &     |
|          Module Record Formatting  |
+-----------------+------------------+
                  |
                  v
+-----------------+------------------+
| Phase 3: Golden Verification &     |
|          Repository Hygiene        |
+------------------------------------+
```

### Phase 1: Type Equality & Subtyping Performance Hardening
**Objective**: Eliminate unsafe Python recursive `__eq__` on Quest types and establish persistent session-scoped
memoization in `is_subtype`.

- **Step 1.1**: Cleanse `is_subtype` of Python structural equality:
  - In `bootstrap/python/quest/types.py` (`is_subtype`), replace `if sub_lazy is sup_lazy or sub_lazy == sup_lazy:` with
    explicit reference identity (`is`), symbol ID equality for type variables, and class identity for primitive
    singletons.
- **Step 1.2**: Guard `QType.__eq__`:
  - Define `__eq__` on `QType` base class to enforce reference identity (`self is other`) or disallow naive structural
    recursion across unhashed type terms, pointing callers to `is_type_equal(t1, t2, env)`.
- **Step 1.3**: Add session-scoped subtyping memo cache:
  - Add `self.subtype_cache: dict[tuple[int, int], bool] = {}` to `Environment`.
  - In `is_subtype`, query `env.subtype_cache` for ground pairs.
  - Record verified independent results into `env.subtype_cache` when the query succeeds without depending on active
    trail hypotheses.
- **Deliverables & Verification**:
  - Run `tests/python` (all 382 tests pass).
  - Verify that no `RecursionError` or infinite loop can occur during type equality checks.

### Phase 2: AST Dump Compaction & Module Record Formatting (COMPLETED)
**Objective**: Eliminate multi-megabyte type expansions in typed AST dumps for imported modules and large recursive
record/variant types.

- **Step 2.1**: Module record provenance and representation:
  - Added `provenance: Optional[str]` to `BuiltinModuleRegistry._build_record_type_from_scope`.
  - Added provenance tracking across all module imports and interfaces (`ModuleBuilder.finish`, `import_module`).
  - Formatted module record types as `Module '<name>'` rather than listing all constituent type/value members.
- **Step 2.2**: Bounded recursive type stringification and alias preservation:
  - Implemented `format_type_compact(t, env, visited_ids, depth)` in `types.py`.
  - Prioritized alias names from `env` (Option B: Name/Alias priority) for module-exported types
    (`ast.ExprForm`, `location.Span`, `writer.T`).
  - Bounded unfolding depth of recursive types (`QRecType` / `QRecGroupType`) to prevent combinatorial expansion.
- **Step 2.3**: Context propagation in `TypedNode.dump`:
  - Updated `TypedNode.dump(indent, env=None)` and `dump_header(env=None)` across all node subclasses.
  - Propagated `ctx.env` from `TypecheckPhase.dump` down into `output_data.dump(env=ctx.env)`.
- **Measured Results**:
  - `tests/golden/typecheck/questlang/syntax_ast.out`: Shrank from **111.34 MB (116,746,265 bytes)** down to
    **172 KB (176,284 bytes)** — a **99.85% reduction**.
  - `tests/golden/typecheck/questlang/syntax_tokens.out`: Shrank from **448 KB** to **30 KB** (**93.3% reduction**).
  - `tests/golden/typecheck/questlang/syntax_tokenizer.out`: Shrank from **161 KB** to **21 KB** (**87.2% reduction**).
  - Across all 46 updated typecheck golden files: Total size dropped from **2.66 MB** down to **0.94 MB**
    (**64.6% reduction**).
  - Git push unblocked: all files well below GitHub's 100 MB hard limit.

### Phase 3: Golden Verification & Repository Hygiene
**Objective**: Re-generate golden files, verify all compiler phases end-to-end, and unblock git pushes.

- **Step 3.1**: Update test golden files:
  - Re-generate `tests/golden/typecheck/questlang/syntax_ast.out` with compacted output.
  - Verify that all other golden files continue to match or update expected outputs cleanly.
- **Step 3.2**: Full test suite validation:
  - Run complete end-to-end suite (`python3 run_tests.py` across all phases: tokenize, parse, typecheck, interpret,
    run_c_compiled).
- **Step 3.3**: Verify repository size limits:
  - Verify `git status` and file sizes: confirm no file exceeds GitHub's 100 MB limit, enabling clean commits and push.
