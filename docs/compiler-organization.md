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
starting with `questlang/`. The tree follows the bootstrap (`bootstrap/python/quest/`) module for module: each
bootstrap module is the Quest module of the same name, lowercased with its underscores removed (canonical names are
letters and digits, [modules.md](modules.md) §2.3), so that the port was translation rather than redesign. Where Quest
needed a split the bootstrap did not have (an import cycle, §5), the bootstrap was refactored first, so the two trees
match.

```
questlang/
├── common/                  # Cross-cutting foundational utilities
│   ├── location             # Source coordinates (Pos, Span) and source maps (bootstrap syntax/sources)
│   ├── diagnostics          # Diagnostic messages, error severity
│   ├── diagbag              # Diagnostic accumulator and reporter
│   └── keys                 # Integer keys for the type tables (the bootstrap keys them by tuples)
│
├── syntax/                  # Concrete syntax and parsing
│   ├── tokens               # TokenKind and Token definitions
│   ├── tokenizer            # Lexical scanner
│   ├── ast                  # Abstract syntax tree: Node, TypeForm, ExprForm, PhraseForm (§3)
│   ├── astprint             # Canonical S-expression printer, matching the bootstrap ast_dump
│   ├── parser               # Parsing a program, a type, a kind, or a value (§4)
│   ├── parser/              # Data-driven PEG / Packrat parser (bootstrap syntax/parser and grammar)
│   │   ├── engine           # Generic PEG engine (constructs, syntax targets, rules, memo) and semantic values
│   │   ├── grammar          # The grammar's syntax targets and rules
│   │   └── actions          # Semantic actions constructing AST nodes
│   └── desugar              # Rewriting syntactic sugar into the forms the type checker elaborates
│
├── types/                   # Semantic types and kinds
│   ├── symbols              # Symbols and scopes
│   ├── model                # Types, kinds, substitution, interning
│   ├── kinds                # Kind synthesis and checking, operator signatures
│   ├── subtyping            # Equi-recursive subtyping and type equivalence
│   ├── contractiveness      # Contractiveness of recursive types
│   ├── env                  # Type-checking environments and the builtin registry
│   ├── dump                 # Canonical and compact type formatters
│   └── canonical            # Reduced and canonical forms of types, for the backends
│
├── typechecker/             # Bidirectional type checker
│   ├── typedast             # The typed AST
│   ├── typedastprint        # Its printer, matching the bootstrap's typed AST dump
│   ├── checker              # The checker's state, shared helpers, and dispatch hooks
│   ├── checks, escape, lvalues, metas   # Shared checks
│   ├── elaboratetypes       # Syntactic types and kinds to semantic ones
│   ├── bindings, application, aggregates, control, exceptions, autovalues   # Construct families
│   ├── typecheck            # Dispatch on expression forms, phrases, programs, entry points
│   └── scoping              # Well-scopedness check of typed programs
│
├── modules/                 # Units, imports, interfaces, modules, and their artifacts
│   ├── paths                # File discovery, search paths, canonical names; files' text and times (over util/path)
│   ├── units                # Unit files
│   ├── graph                # The unit graph: resolution, loaded units
│   ├── abstracttypes        # Modules' abstract types by global name
│   ├── loader               # Loading interfaces and modules
│   ├── elaboration          # Elaborating interfaces, modules, and imports
│   ├── stdlib               # The standard library's interfaces and module scopes
│   ├── interfacecompiler, modulecompiler, manifest   # .qi and .qm artifacts, compiled modules
│
├── values/                  # Runtime values
│   ├── model                # Values, and the interpreter's frames
│   ├── json                 # JSON text, as the dynamic format uses it
│   └── dynamicjson          # The serialized form of dynamic values
│
├── interpreter/             # Interpreters: tree walking and IR
│   ├── primitives, formatting, builtins
│   ├── treewalk             # Tree-walking interpreter over the typed AST
│   └── irinterp             # IR interpreter
│
├── ir/                      # IR lowering and passes (docs/ir.md)
│   └── nodes, walk, lower, specialize, closure, shapes, represent, slots, describe, thunks, written, verify, printer
│
├── ssa/                     # The native backends' SSA (docs/ssa.md): nodes, build, statics, verify, printer
│
├── codegen/                 # Backends: the shared layer and the C backend
│   ├── syntax, layout, descriptors, sha256   # C spelling, layouts and digests, descriptors' type-level forms
│   ├── staticdata, runtimeLayout   # Static data described for every backend; the runtime's struct layouts
│   ├── backend, symbols
│   ├── choice, ssac         # The backend each unit is compiled by; the SSA's C printer (docs/arm64.md §3.14)
│   ├── arm64/               # The native backend: codegen (instructions, frames, calls), asm (Darwin's spellings)
│   └── c/                   # backend, declarations, headers, printer, types, compilerrunner
│
├── config/                  # The ABI version and artifacts' format
├── build/                   # The build engine and its log
│
└── driver/                  # Compiler driver (bootstrap pipeline and quest/__main__)
    ├── main                 # Main routine: every phase, -e, -i, and the bootstrap's compiling options
    └── repl                 # The REPL: input completeness, rollback, the loop over io/readline
```

The self-hosted compiler compiles itself to a fixed point, and it is the primary compiler: the two compilers agree
on what programs do, not on how they compile them ([testing.md](testing.md) §2.8). `./quest` runs it, built from the
tree by a released self-hosted compiler ([release-compiler.md](release-compiler.md)) or by the bootstrap. So
`questlang/` may use only what the current release compiles. The bootstrap's `config/options` was not ported, because
the driver and the build engine take their options directly. (`codegen/sha256` is the SHA-256 that the bootstrap takes
from Python's `hashlib`, for layout tags and type digests.)

---

## 3. AST Representation and Design

The AST is one module, `questlang/syntax/ast` (interface `Ast`, in [ast.int.quest](../questlang/syntax/ast.int.quest)).
It mirrors the bootstrap parser's AST (`bootstrap/python/quest/syntax/ast.py`) node for node, so that
`questlang/syntax/astprint` can print it in the same canonical S-expression form as the bootstrap `ast_dump`, and the
two can be compared on every parseable Quest file ([testing.md](testing.md) §2.3). The interface declares its types with `Def`, so that importers
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
1. **Engine (`questlang/syntax/parser/engine`):** Generic PEG constructs (tokens, silent punctuation, optional and
   repeated items, sequences, separated lists), syntax targets and their rules, and the packrat parser that evaluates
   them, with the bootstrap's semantics: a target's first matching rule wins, a left-recursive attempt fails, and a
   parse that does not reach EOF reports the farthest failure and what was expected there, in the bootstrap's words.
2. **Grammar (`questlang/syntax/parser/grammar`):** The syntax targets and their rules, rule for rule and in the order
   of `grammar.py` (PEG tries rules in order), written as `rule(x.type actions.typeInfix) of x.postfixType opt of
   t(symbolicInfix) x.type end end`.
3. **Actions (`questlang/syntax/parser/actions`):** The rules' semantic actions, which build the AST as `grammar.py`'s
   actions and helpers build the bootstrap's. A node starts where the bootstrap positions it and extends to the end of
   the rule that builds it.

`questlang/syntax/parser` parses tokens as a program, a type, a kind, or a value. The bootstrap's grammar actions stay
as they are, so the self-hosted actions follow them even where Quest would suggest another shape (postfix operators,
for instance, match as functions from their operand to the node).

### 4.1. Intermediate Semantic Values (`engine.Val`)
In accordance with Principle 7 (minimizing `dynamic.T`), intermediate values produced by PEG constructs use a dedicated
sum type (`Option`) rather than dynamic boxing: an optional construct that did not match (Python's `None`), a token, a
string, a list (the results of a repetition, a separated list, or a sequence of several non-silent items), or one of
the AST's values (types, expressions and declarations, top-level phrases, signature items with their positions, the
components of records, options, imports, and branches, and postfix operators). An action receives its rule's
non-silent results as an `Array(engine.Val)`, with an `engine.Ctx` that gives the span the rule matched and the
diagnostic bag.

The AST cannot hold some things the bootstrap parses and its later phases reject: an interface or a module below the
top level, and declarations in an Auto type, are fatal errors of the parser. An import below the top level is a
declaration (`declImport`), which the type checker rejects, as the bootstrap's does.

### 4.2. Packrat Memoization & Syntax Target Identification
A grammar numbers its syntax targets as it makes them, and the parser's memo is an array with an entry for each target
at each position (at `pos * targets + id`): not yet tried, being tried, or the outcome. Lookups take constant time, so
parsing is linear in the number of tokens.

---

## 5. Topological Dependency Layers

Module imports form a DAG. The layers, lowest first, by module rather than directory, since the module system sits
between parts of the type checker:

```
Layer 0: common/*
Layer 1: syntax/* (tokens, tokenizer, ast, astprint, parser, parser/*, desugar)
Layer 2: types/model → symbols, dump → subtyping; typechecker/typedast
Layer 3: modules/paths, units, graph
Layer 4: types/env → kinds, contractiveness
Layer 5: typechecker/typedastprint, elaboratetypes, checks, escape, lvalues, metas
Layer 6: modules/abstracttypes, loader, elaboration, stdlib
Layer 7: typechecker/checker → bindings, application, aggregates, control, exceptions, autovalues → typecheck,
         scoping
Layer 8: types/canonical, values/json → values/model → dynamicjson → interpreter/primitives, builtins,
         formatting → treewalk | ir/* | codegen/*, modules' artifacts, config/*, build/*
Layer 9: driver/*
```

The bootstrap's lazy imports made cycles that this order does not allow; they were broken in the bootstrap before the
port: symbols and scopes are `types/symbols`; the operator table is
`types/env`'s, so that `kinds`, which uses environments, is above it; the loader and the checker
register the functions module elaboration calls back, rather than elaboration importing them; and the checker's
construct families reach the dispatch through `typechecker/checker` (in Quest, a tuple whose function fields
`typecheck` fills).

---

## 6. Differences from the Bootstrap

The self-hosted compiler prints what the bootstrap prints, in every shared phase ([testing.md](testing.md) §2.8). Where
the two differ inside, it is because Quest cannot hold what Python does, or because the self-hosted compiler goes
further:

- **Errors.** The self-hosted type checker reports several errors, not only the first
  ([diagnostics.md](diagnostics.md) §4.5). One Quest exception, `diagnostics.compilerError`, stands for the
  bootstrap's `QuestCompilerError` and its subclasses, and in the interpreters `model.runError` for both
  `QuestException` and `QuestRuntimeError`; its cause tells a Quest exception from an error of the interpreter.
- **The checker's families** are one tuple, `checker.T`, which holds the checker's state and, in `var` fields, the
  dispatch functions that `typecheck` fills; a family calls the families below it directly. Module elaboration calls
  the loader and the checker back through hooks, `var` fields of a tuple that `elaboration` exports (§5).
- **Keys.** The bootstrap keys its type tables by tuples, which Python hashes. Keys built as strings made the
  self-hosted compiler several times slower, so its tables use integer keys interned through `common/keys`. Caches
  that the bootstrap keys by an object's identity are hash maps keyed by its id, or its identity hash.
- **Traversals.** Quest has no reflection, so every walk over the nodes of a family (the syntax tree, the typed AST,
  the IR, types) lists each node's fields, case by case. The bootstrap uses the same explicit tables
  (`ir/walk.py`'s `fields_of` and `rebuild`, [ir.md](ir.md) §5), but its debugging printers read fields by name.
- **Names.** Fields and variables named with Quest's keywords are renamed (`ir/nodes`), and the IR's `Var` is
  `Variable`, since `Var` is a type keyword. The C printer names keyword-named variables of the bootstrap's otherwise
  (`rec`, `out`, `record`, `inspect`).
- **Paths** are `util/path`'s, normalized lexically without following symbolic links. The project directory, which
  the bootstrap knows as its own source tree, is `QUEST_HOME`, which the runners set, or else the current directory.
- **JSON.** `values/json`, private to `questlang/values/`, keeps a number's text, so that a word's integer (up to
  2^64 - 1) is read exactly; an integer read as an `Int` must fit one, where Python's are unbounded. A `\u` escape
  above `\u00ff` fails as the text is parsed, since a character is a byte. `dynamic.intern` reads from a native reader,
  which cannot put a character back, so after a value that is not an object, array, or string it reads the delimiter
  that ends it too; such a document is not a dynamic value, so it fails either way.
- **Thunks are IR functions.** The described stage ends with a pass of its own, `ir/thunks`, which makes adapters,
  type applications' thunks, and closures of external functions into functions of the unit, so that every backend
  compiles them alike ([ir.md](ir.md) §8.4.1); the bootstrap's C printer makes them as it prints. Its IR dumps of the
  described stage show them, and are its own (testing.md §2.8).
- **The interpreters' builtins** are only the symbols `lib/` binds, and each calls the native library
  ([interpreter.md](interpreter.md) §1).
- **The build.** A Quest program can neither read the clock nor append to a file, so the build log's entries are
  timestamped and appended by `sh` with `date` (`build/logger`). Temporary files are made by `mktemp`, and a program's
  C goes into a temporary directory of its own. A compiled program runs without the bootstrap's 10-second timeout. An
  error that is not a compiler error (a C compiler's failure, say) is reported at the program's first character,
  without the bootstrap's Python traceback. `--dump-after` is ported for the C phases only.
- **The REPL's snapshots** record no symbol counter and no frame parent, neither of which the self-hosted compiler can
  observe ([repl.md](repl.md) §7).
