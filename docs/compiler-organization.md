# Organization of the Self-Hosted Quest Compiler and Interpreter

This document specifies the directory, module, and type architecture for the **self-hosted Quest compiler and
interpreter** (`questlang`). The self-hosted system replaces the Python bootstrap implementation
(`bootstrap/python/quest/`) with clean, modular Quest code organized as an acyclic directed graph of interfaces
(`.int.quest`) and module implementations (`.mod.quest`).

---

## 1. Design Principles

1. **Strictly Acyclic Dependencies:** Cardelli's module system forbids mutual/cyclic dependencies between interfaces.
   The subsystem hierarchy is strictly layered: lower layers never import from higher layers.
2. **Deep, Cohesive Module Hierarchy:** Rather than large monolithic files, functionality is divided into focused,
   single-responsibility modules across up to three directory levels.
3. **Algebraic Data Types via `Option`:** Every AST and semantic model variant is defined as an `Option` type with
   case tags and payload records/tuples.
4. **Valid Quest Identifier Syntax:** Quest type names cannot contain underscores (`_`). All type names use `CamelCase`
   (e.g., `Expr`, `TypeExpr`, `TokenKind`, `AstPrint`).
5. **Data-Driven PEG Parser:** The parser decouples grammar rules, PEG parsing engine, and AST construction actions.
6. **Uncurried Value Arguments by Default:** Standard operations take uncurried value argument lists (`f(a b c)`),
   reserving currying for type parameter groups (`f(A::TYPE)(...)`) and higher-order combinators.
7. **Strict Minimization of `dynamic.T`:** A primary architectural goal is to use `dynamic.T` only where strictly
   necessary, such as serializing data structures externally. Everywhere else within the compiler and interpreter,
   Quest-native algebraic data types (`Option`) and records must always be used.

---

## 2. Subsystem Layout and Directory Structure

All self-hosted compiler and interpreter source code lives under the `questlang/` directory with module path prefixes
starting with `questlang/`.

```
questlang/
├── common/                  # Cross-cutting foundational utilities
│   ├── location             # Source coordinates (Pos, Span)
│   ├── diagnostics          # Diagnostic messages, error severity
│   └── diagbag              # Diagnostic accumulator and reporter
│
├── syntax/                  # Concrete syntax and parsing
│   ├── tokens               # TokenKind and Token definitions
│   ├── tokenizer            # Lexical scanner
│   ├── ast                  # Abstract syntax tree: Node, TypeForm, ExprForm, PhraseForm (§3)
│   ├── astprint             # Canonical S-expression printer, matching the bootstrap ast_dump
│   └── parser/              # Data-driven PEG / Packrat parser
│       ├── engine           # Generic PEG engine (Construct, SyntaxTarget, Rule, Memo)
│       ├── rules/           # Grammar rule definitions
│       │   ├── expr         # Expression and operator grammar rules
│       │   ├── type         # Type expression grammar rules
│       │   ├── decl         # Declaration grammar rules
│       │   └── module       # Interface and module grammar rules
│       └── actions/         # Semantic action callbacks constructing AST nodes
│           ├── expr         # Expression AST construction
│           ├── type         # Type AST construction
│           ├── decl         # Declaration AST construction
│           └── module       # Module AST construction
│
├── types/                   # Semantic type system model
│   ├── kind                 # Kind representations (Kind)
│   ├── model                # Semantic type representations (Type)
│   ├── env                  # Lexical scoping and type/term environments
│   ├── subtyping            # Cardelli subtyping judgments and bound checks
│   ├── normalize            # Type normalization and expansion
│   └── builtins             # Predefined basic types and root interface models
│
├── typecheck/               # Typechecker and semantic elaboration
│   ├── typedast             # Type-annotated AST nodes
│   ├── elaborate            # Syntactic TypeExpr -> semantic Type transformation
│   ├── checkexpr            # Expression typechecking and bidirectional inference
│   ├── checkdecl            # Declaration typechecking
│   └── pattern              # Pattern matching exhaustiveness and reachability
│
├── modules/                 # Module system, dependency DAG, and linking
│   ├── modid                # Hierarchical module paths and alias management
│   ├── loader               # Filesystem module discovery and reading (QUESTPATH)
│   ├── graph                # Dependency DAG construction, topological sort, cycle check
│   ├── interfacecheck       # Module-to-interface conformance verification
│   └── linker               # Compilation unit assembly and pre-linking
│
├── eval/                    # Tree-walking interpreter & runtime environment
│   ├── value                # Runtime value representations (Val)
│   ├── env                  # Runtime evaluation frames and closures
│   ├── eval                 # Tree-walking evaluator
│   ├── builtins             # Native execution hooks for stdlib interfaces
│   └── dynamic              # Dynamic type boxing and JSON serialization
│
├── codegen/                 # C code generator targeting C99
│   ├── cmodel               # C intermediate representation
│   ├── ctypes               # Quest-to-C type mapping and representation strategy
│   ├── cclosure             # Closure capture analysis and environment layout
│   ├── cdecl                # C typedefs, struct declarations, function prototypes
│   ├── cemit                # C99 code emission for statements and expressions
│   └── crunner              # C compiler invocation (clang/gcc) and linking
│
└── driver/                  # Compiler pipeline and CLI driver
    ├── options              # Command-line option parsing (using util/argparse)
    ├── pipeline             # Multi-phase execution orchestrator
    └── main                 # Top-level executable entry point
```

So far `common/*` and, in `syntax/`, `tokens`, `tokenizer`, `ast`, and `astprint` exist; the rest of the tree is the
plan.

---

## 3. AST Representation and Design

The AST is one module, `questlang/syntax/ast` (interface `Ast`, in [ast.int.quest](../questlang/syntax/ast.int.quest)).
It mirrors the bootstrap parser's AST (`bootstrap/python/quest/syntax/ast.py`) node for node, so that
`questlang/syntax/astprint` can print it in the same canonical S-expression form as the bootstrap `ast_dump`, and the
two can be compared on every parseable Quest file (§6). The interface declares its types with `Def`, so that importers
see their structure; the module defines them with `Let`.

In Quest, type names must be alphanumeric and cannot contain underscores (`_`). Furthermore, the term "Kind" has a
precise, formal meaning in Quest's type system (kinds are the "types of types", such as `TYPE`). To avoid semantic
confusion, the option types of syntactic variants are named **`Form`** (`TypeForm`, `ExprForm`, `PhraseForm`). Their
tags are prefixed by category (`typeTuple`, `exprIf`, `declLetVal`, `phraseModule`), which also keeps them clear of
keywords such as `tuple` and `if`.

### 3.1. Parameterized Node Wrapper (`Node(Form)`)

To ensure uniform source location tracking without code duplication, every AST node is a parameterized tuple holding a
common `span` and a category-specific syntactic form:

```quest
Def Node(Form::TYPE) = Tuple
    span: location.Span
    form: Form
end
```

`Node`, like the other components of the AST, is a tuple rather than a record because tuples are cheaper. A tuple is one
pointer to its components, each at a fixed offset, so `node.span` is a single load
([c-representation.md](c-representation.md) §5.1). A record allows subtyping in any order, so it is a 16-byte pair of
payload and offset table, its payload carries a header, and each field access goes through the table (same document,
§5.2). The AST needs none of that subtyping.

#### Trade-off Analysis: Parameterized `Node(Form)` vs. Flat Variants

- **Pros:**
  1. *Uniform Span Access:* Operations like diagnostic reporting, error formatting, and source mapping access
     `node.span` directly in $O(1)$ without writing 20+ arm `case` expressions just to extract the location.
  2. *DRY Variant Definitions:* The tags of `TypeForm`, `ExprForm`, etc., define only their syntactic payloads
     without repeating `span: location.Span` in 60+ payloads.
  3. *Shared Node Metadata:* Common metadata (node IDs, comments, docstrings, or type annotations) can be added once
     to `Node` without modifying every individual variant.
  4. *Generic Utilities:* Diagnostic and source map utilities can accept any `Node(F)` generically.
  5. *Zero Collision with Type Kinds:* Naming the variant `form` (`node.form`) cleanly decouples AST structure from
     Quest's semantic `Kind` system.
- **Cons:**
  1. *Two-level matching:* Matching requires `case node.form when ... end` rather than matching on `node`
     directly.
  2. *Constructor wrapping:* Creating a node requires wrapping the form in the outer tuple (mitigated with helper
     functions like `makeExpr(span form)`, §3.5).
  3. *C runtime indirection:* An outer tuple pointing to an inner option introduces an extra pointer indirection in
     the C runtime compared to a flat variant.

**Decision:** The parameterized `Node(Form)` design is adopted for its decisive advantages in diagnostic precision,
simplicity of variant definitions, and elimination of boilerplate across the compiler.

### 3.2. Types and Kinds (`TypeForm`)

Types (level 1) and kinds (level 2) share one form, so `TypeExpr` and `KindExpr` are the same type:

```quest
Def TypeFormalOf(T::TYPE) = Tuple name: String bound: T end
Def QuantifierOf(T::TYPE) = Tuple name: String bound: T mode: ParamMode isType: Bool end
...
Def SignatureOf(T::TYPE) = Option
    sigValue with val: FieldSigOf(T) end
    sigType with val: TypeFormalOf(T) end
    sigTypeBinding with val: TypeBindingOf(T) end
    sigTypeBindingGroup with val: vector.T(TypeBindingOf(T)) end
    sigKindBinding with val: Tuple name: String kindVal: T end end
end

Def Rec TypeForm = Option
    (* Level 2: Kinds *)
    kindType
    kindPower with bound: Node(TypeForm) end
    kindAll with paramName: String paramKind: Node(TypeForm) bodyKind: Node(TypeForm) end
    ...
    (* Level 1: Types *)
    typePath with path: vector.T(String) end
    typeAll with quantifiers: vector.T(QuantifierOf(Node(TypeForm))) resultType: Node(TypeForm) end
    typeTuple with fields: vector.T(SignatureOf(Node(TypeForm))) end
    typeRecord with fields: vector.T(RecordFieldSigOf(Node(TypeForm))) end
    ...
    typeExternal with cType: String end
end

Def TypeExpr = Node(TypeForm)
Def KindExpr = Node(TypeForm)

Def TypeFormal = TypeFormalOf(KindExpr)
Def Signature = SignatureOf(TypeExpr)
...
```

The components of the forms (a formal parameter, a quantifier, a field of a signature) are written once, as type
operators over the type of the subterms (`TypeFormalOf(T)`), because `TypeForm` uses them before `TypeExpr` is
defined; the named types after it (`TypeFormal`, `Signature`) apply them to `TypeExpr` or `KindExpr`. `ParamMode` is
an option of `modeValue`, `modeVar`, and `modeOut`.

### 3.3. Expressions and Declarations (`ExprForm`)

Expressions and declarations share one form. A declaration is a phrase of a binding, written among expressions in
blocks, tuples, and modules, as in the paper's `Binding` rule, so `Expr` and `Decl` are the same type:

```quest
Def Rec ExprForm = Option
    (* Literals *)
    exprInt with value: Int lexeme: String end
    ...
    (* Identifiers & Arguments *)
    exprId with name: String end
    typeArg with typeVal: TypeExpr end
    ...
    (* Control Flow & Blocks *)
    exprBlock with bindings: vector.T(Node(ExprForm)) end
    exprIf with
        cond: Node(ExprForm)
        thenBranch: Node(ExprForm)
        elsifs: vector.T(ElsifBranchOf(Node(ExprForm)))
        elseBranch: maybe.T(Node(ExprForm))
    end
    ...
    (* Declarations / Bindings inside Blocks, Tuples, and Modules *)
    declLetVal with
        name: String
        value: Node(ExprForm)
        params: vector.T(FormalParam)
        typeAnnot: maybe.T(TypeExpr)
        isRec: Bool
        isVar: Bool
    end
    ...
    declExprStmt with expr: Node(ExprForm) end
end

Def Expr = Node(ExprForm)
Def Decl = Node(ExprForm)
```

The tags fall into groups:

| Group | Tags |
| :--- | :--- |
| Literals | `exprInt`, `exprReal`, `exprChar`, `exprString`, `exprBool`, `exprOk` |
| Identifiers and arguments | `exprId`, `exprExternal`, `typeArg`, `kindArg` (a type or kind among a call's arguments) |
| Control flow and blocks | `exprBlock`, `exprIf`, `exprWhile`, `exprLoop`, `exprExit`, `exprFor` |
| Functions and calls | `exprFun`, `exprApp`, `exprInfix` |
| Aggregates | `exprTuple`, `exprRecord`, `exprArray`, `exprArrayRep`, `exprOption`, `exprVariant`, `exprAuto` |
| Selection and indexing | `exprSelect`, `exprIndex`, `exprIndexAssign` |
| Cells and variant tests | `exprVarCell`, `exprDerefCell`, `exprVariantCheck`, `exprVariantAssert` |
| Matching and exceptions | `exprCase`, `exprInspect`, `exprException`, `exprRaise`, `exprTry` |
| Value declarations | `declLetVal`, `declLetValGroup` |
| Type and kind declarations | `declTypeBinding`, `declTypeBindingGroup`, `declDefKind` |
| Expressions as phrases | `declExprStmt` |

`declExprStmt` wraps an expression used as a phrase of a binding. Body fields (`thenBranch`, `elseBranch`, loop and
branch bodies) hold an expression, never a `declExprStmt`; a body that is a lone declaration is a one-phrase
`exprBlock`. A group (`declLetValGroup`, `declTypeBindingGroup`) holds the members of a `let ... and ...` or
`Let ... and ...` declaration. As for types, the components of the forms (`CaseBranchOf(E)`, `TupleFieldOf(E)`, ...)
are operators over the type of the subterms, applied to `Expr` by named types after `ExprForm` (`CaseBranch`,
`TupleField`).

### 3.4. Modules, Interfaces, and Programs

Imports, interfaces, and modules are plain tuples (`ImportItem`, `ImportPhrase`, `InterfaceDecl` with its
`signatures`, `ModuleDecl` with its `bindings`), and a top-level phrase is one of five forms:

```quest
Def PhraseForm = Option
    phraseImport with phrase: ImportPhrase end
    phraseInterface with iface: InterfaceDecl end
    phraseModule with modDecl: ModuleDecl end
    phraseDecl with decl: Decl end
    phraseExpr with expr: Expr end
end

Def Phrase = Node(PhraseForm)

Def ProgramForm = Tuple
    phrases: vector.T(Phrase)
end

Def Program = Node(ProgramForm)
```

### 3.5. Constructors

The interface exports a constructor for each category of node (`makeType`, `makeKind`, `makeExpr`, `makeDecl`,
`makePhrase`, which take a span and a form, and `makeProgram`, which takes a span and the phrases), and shorthands for
common nodes, such as
`exprInt(span value lexeme)`, `exprApp(span func args)`, `typePathSimple(span name)`, and
`declLetVal(span name value typeAnnot)`.

---

## 4. Parser Architecture: Decoupled Data-Driven PEG

The parser preserves the architecture of the Python implementation (`bootstrap/python/quest/syntax/parser.py` and
`grammar.py`), separating:
1. **Engine (`questlang/syntax/parser/engine`):** Generic PEG parser combinators (`MatchToken`, `SyntaxTarget`,
   `Optional`, `Repeated`, `Sequence`, `SepBy`, with silent tokens) and packrat memoization tables.
2. **Rules (`questlang/syntax/parser/rules/*`):** Declarative definitions of grammar non-terminals and production rules.
3. **Actions (`questlang/syntax/parser/actions/*`):** Semantic action callbacks that transform matched tokens and child
   nodes into concrete AST objects.

### 4.1. Intermediate Semantic Values (`SemanticVal`)
In accordance with Principle 7 (minimizing `dynamic.T`), intermediate values produced by PEG combinators use a
dedicated sum type (`Option`) rather than dynamic boxing:

```quest
Let Rec SemanticVal = Option
    none
    tok with val: tokens.Token end
    expr with val: ast.Expr end
    typeExpr with val: ast.TypeExpr end
    phrase with val: ast.Phrase end
    list with val: vector.T(SemanticVal) end
    opt with val: maybe.T(SemanticVal) end
end
```
This provides complete static type safety, avoids runtime boxing/unboxing overhead, and allows clean pattern matching
in semantic actions.

### 4.2. Packrat Memoization & Syntax Target Identification
Syntax targets (`SyntaxTarget`) are identified by instance identity using machine addresses (`identityHash`),
matching Quest's `is` / `isnot` semantics. The packrat memoization table in `parser/engine` maps a target and a
position to an optional entry:
```quest
Let MemoLookup = All(target: SyntaxTarget pos: Int) maybe.T(MemoEntry)
```
It hashes targets with `identityHash` and compares them with `is`, for $O(1)$ lookup and linear-time parsing.

---

## 5. Topological Dependency Layers

Module imports strictly respect the following layered DAG:

```
Layer 0: [questlang/common]
             ↓
Layer 1: [questlang/syntax/tokens] → [questlang/syntax/tokenizer]
             ↓
Layer 2: [questlang/syntax/ast]
             ↓
Layer 3: [questlang/syntax/astprint] ← [questlang/syntax/parser/*]
             ↓
Layer 4: [questlang/types/*] (kind, model, env, builtins, subtyping)
             ↓
Layer 5: [questlang/typecheck/*] (elaborate, checkexpr, checkdecl, pattern)
             ↓
Layer 6: [questlang/modules/*] (modid, loader, graph, interfacecheck, linker)
             ↓
┌────────────────────────────┴────────────────────────────┐
↓                                                         ↓
Layer 7a: [questlang/eval/*] (interpreter)    Layer 7b: [questlang/codegen/*] (C emitter)
└────────────────────────────┬────────────────────────────┘
                             ↓
Layer 8:  [questlang/driver/*] (options, pipeline, main)
```

---

## 6. Implementation Milestones

Porting proceeds through four self-contained milestones:

### Milestone 1: Frontend & Syntax (`common` and `syntax`)
- `questlang/common/location`, `diagnostics`, `diagbag`.
- `questlang/syntax/tokens` and `questlang/syntax/tokenizer` (verified against `tokenize` goldens).
- `questlang/syntax/ast` and `questlang/syntax/astprint` (verified against `ast_dump` for every parseable `.quest`
  file by `tests/astprint/generate.py --check`; see [testing.md](testing.md)).
- `questlang/syntax/parser/*`: generic PEG engine with memoization and grammar rules/actions for types, declarations,
  expressions, operators, and modules (verified against `parse` goldens).

### Milestone 2: Types & Typechecking (`types` and `typecheck`)
- Semantic `kind`, `model` (Cardelli types), and lexical `env`.
- `subtyping` rules (Cardelli subtyping judgments, bound checking, and recursion contractiveness).
- `elaborate` (syntactic `TypeExpr` $\to$ semantic `Type`) and `builtins` (initial typing environment and root
  interface signatures).
- `checkexpr`, `checkdecl` bidirectional typechecker, and `pattern` exhaustiveness analysis (verified against
  `typecheck` goldens).

### Milestone 3: Modules & Interpreter (`modules` and `eval`)
- `modules/modid`, `loader`, `graph` (dependency DAG and cycle validation), `interfacecheck`, and `linker`.
- `eval/value`, `env`, `eval_builtins`, `eval/eval` tree-walking evaluator (verified against `interpret` goldens),
  `eval/dynamic` serialization, and interactive REPL.

### Milestone 4: C Code Generation & Self-Hosting (`codegen` and `driver`)
- IR lowering and passes, `codegen` C99 emission, and compiler driver / runtime linking.
- `driver/options`, `pipeline`, `main` entrypoint, and complete self-hosting verification (`questc` compiling
  `questc`).

---

### 6.1. Milestone 1 Verification Strategy

Milestone 1 is validated using the Python test runner (`run_tests.py`) via focused Quest CLI driver harnesses:
- `tests/questlang_tokenize.quest`: Invokes `questlang/syntax/tokenizer` and emits token outputs matching the exact
  format of `tests/golden/tokenize/*.out`.
- `tests/questlang_parse.quest`: Invokes `questlang/syntax/parser` and formats AST outputs matching
  `tests/golden/parse/*.out`.

This allows `run_tests.py --phase tokenize` and `run_tests.py --phase parse` to verify the self-hosted frontend
against all existing language tests.
