# questlang/modules: interfaces, modules, and imports

Quest programs are built from units: a program (a `.quest` file, `-e` code, or a REPL input), interface files
(`.int.quest`), each holding one `interface` declaration, and module files (`.mod.quest`), each holding one `module`
declaration that implements an interface. This directory is where the compiler deals with units as units. It finds
the file an import names, loads and elaborates interfaces and modules for the type checker, checks that a module
conforms to its interface, hides its abstract types, and keeps track of what has been loaded. The type checker
(`questlang/typechecker`) calls into it when it meets an `import` phrase or a unit file. What it produces, scopes of
semantic types (`questlang/types`) and typed modules (`questlang/typechecker`), goes on to the interpreter, the IR
lowering (`questlang/ir`), and the backends. Its [`artifacts/`](artifacts/README.md) subdirectory compiles units
apart into the files separate compilation keeps on disk.

## An example

Consider an interface and a module that implements it, and a program that uses them:

```quest
(* util/counter.int.quest *)          (* util/counter.mod.quest *)        (* main.quest *)
interface Counter                     module counter : Counter            import counter : util/Counter
export                                export                              let c = counter.inc(counter.new(1))
    T::TYPE                               Let T = Int
    new(init: Int): T                     let new(init: Int): T = init
    inc(c: T): T                          let inc(c: T): T = c + 1
end                                   end
```

Type-checking `main.quest` reaches the import, and this directory resolves `util/Counter` and `counter` to the two
files, parses each, elaborates the interface into a scope (a symbol table of its types, kinds, and value signatures),
elaborates the module against that interface, and binds `counter` in the program to a record of the module's exports.
In that record `T` is an opaque type: the program can pass a `counter.T` around but cannot use it as an `Int`. The
module itself, inside, sees `T = Int`.

## Finding units: paths, canonical names, and the unit graph

An import path such as `util/counter` is searched for in the importing unit's directory, then the include paths
(`-I`), `$QUEST_LIB`, and the standard library's `lib/` ([docs/modules.md](../../docs/modules.md) §2.2). The file is
named by the path lowercased: `util/Counter` is `util/counter.int.quest`. [`paths.int.quest`](paths.int.quest) does
this search, and also computes each unit's *canonical name*: its file's path, without suffix, relative to the search
root that contains it. Two imports written differently, from different directories, that reach the same file get the
same canonical name, and the compiler identifies units by that name everywhere after: in symbol names in the
generated code, in the build directory's layout, and in the type tables. Paths are handled as strings, normalized
lexically, over [`common/files`](../common/files.int.quest).

[`graph.int.quest`](graph.int.quest) memoizes resolution. A `Resolver` maps (kind, path, importing directory, roots)
to a `Resolved`, the unit's source file (or, for an interface distributed without one, a prebuilt `.qi`) and its
names, so each import is searched for on disk once, and every consumer (the loader, the interface and module
compilers, the build engine's queue and staleness checks) sees the same answer. A `UnitGraph` holds the units an
environment has loaded, by kind and canonical name, with their type-checked forms: an interface's scope, a module's
typed module, or, for a module known only through its interface, its export scope. A unit is *precompiled* when its
object is built apart, so importers are typed against its interface and its source is never elaborated.

The REPL needs the graph to be transactional. `newSession` forgets resolutions (so files created since the last input
are found) while keeping loaded units, and `snapshot` and `restore` put the units back as they were when an input
fails ([docs/repl.md](../../docs/repl.md) §5).

## Loading

[`loader.int.quest`](loader.int.quest) loads a unit when the type checker asks for one by name. For an interface it
takes the first of: a scope already loaded under the same canonical name; with a build directory, the `.qi` there,
rebuilt first if stale; a fresh `.qi` elsewhere on the search path; or the `.int.quest` source, parsed by
[`units.int.quest`](units.int.quest) (which runs the tokenizer, parser, and desugarer on a unit file and checks that it
holds the one declaration its name promises). A `.qi` is the interface's compiled form, a serialized description of
its scope, so loading from one skips re-elaborating the source and the interfaces it imports. For a module the loader
elaborates its source once per canonical name and shares the result with every later importer, which matters for
module identity: two importers must see the same opaque types. A precompiled module instead gets a binding without
code, typed against its interface. The loader also detects import cycles, which Cardelli's module system forbids,
from the chain of units being loaded.

## Elaboration: Cardelli's module system

[`elaboration.int.quest`](elaboration.int.quest) gives interfaces, modules, and imports their meaning
([docs/modules.md](../../docs/modules.md), [docs/type-system.md](../../docs/type-system.md)):

- `elaborateInterface` turns an interface declaration into a scope: its abstract types (`T::TYPE`, possibly with a
  bound or a kind), its manifest types (`Def`), and its values' signatures.
- `elaborateModule` checks a module in a scope that sees only its own imports, elaborates each member, and checks the
  result against the interface: manifest types must be equal, abstract types' kinds must be subkinds of the declared
  ones, and each value's type a subtype of its signature. It then makes the module's export scope, in which each of
  the interface's abstract types is an opaque type variable rather than the module's definition, and binds the
  module as a record of its exports. Each member is a recovery point: a member that fails is reported, and checking
  continues with the next ([docs/diagnostics.md](../../docs/diagnostics.md) §4.5).
- `elaborateImport` binds a program's imported interfaces and modules under their local names, as the import's
  aliasing syntax asks ([docs/modules.md](../../docs/modules.md) §4.3).

Elaboration sits below the loader and the type checker in the module hierarchy, since both call it, yet it must call
both: to load the units an import names, and to type-check a module's member. Quest interfaces may not import one
another cyclically, so elaboration exports a record of mutable function slots, `hooks`, which `loader.install` and
the type checker fill in when they start. This is the usual way the compiler breaks a dependency cycle between
layers.

## Abstract types by global name

An abstract type that leaves its module is opaque, but some parts of the system need to know what it stands for.
[`abstracttypes.int.quest`](abstracttypes.int.quest) records each exported abstract type under a *global name*, the
module's canonical name, a dot, and the type's name (`geo/coord.P`), with one opaque symbol id per global name for the
whole process, so that every environment that elaborates or imports the module agrees on the type. Two consumers use
it. `dynamic.extern` and `dynamic.intern` serialize values of abstract types at their representations and check them
on the way back in ([docs/dynamic.md](../../docs/dynamic.md) §2.3). And a whole program (`--whole-program`), whose
modules are merged into one unit, sees through its modules' unbounded abstract types: `representations()` is the
substitution from opaque types to their definitions that lets `questlang/repr` lay them out as what they are. A
module compiled apart is excluded (`setRegisteringApart`), since other units still see its types as opaque.

## The standard library

The standard modules (`string`, `list`, `conv`, `writer`, `system`, ...) are usable without an import:
`string.length("abc")` just works. [`stdlib.int.quest`](stdlib.int.quest) provides a *registry*, which an environment
consults when a lookup of an interface, module, or value name fails. It elaborates the standard interface from `lib/`
on first use, in an environment of its own so the result can be cached for the process, and declares the module's
record in the asking environment. A standard module is never elaborated from its source: its code is the native
library, so its scope is made from its interface. The driver, the build engine, and its workers call `install` to
make this registry every new environment's default.

## Connections

The type checker ([`../typechecker`](../typechecker)) calls `elaborateImport` for import phrases and fills the
`elaborateBinding` hook; the environment ([`../types/env.int.quest`](../types/env.int.quest)) holds the unit graph and
resolves imports through it. The driver ([`../driver`](../driver/README.md)) installs the standard library and
compiles unit files through [`artifacts/`](artifacts/README.md); the build engine ([`../build`](../build/README.md))
uses the graph's resolver and artifact paths to decide what to compile, and compiles modules with its module
compiler, through which the JIT ([`../jit`](../jit)) loads module units too. The bootstrap counterpart is
[`bootstrap/python/quest/modules/`](../../bootstrap/python/quest/modules/README.md), module for module.

## Further reading

- [docs/modules.md](../../docs/modules.md): the module system, search rules (§2), canonical names (§2.3), syntax
  (§4), separate compilation (§9), and manifests (§10).
- [docs/build-process.md](../../docs/build-process.md) §2.1: the unit graph; §5: when a `.qi` is stale.
- [docs/type-system.md](../../docs/type-system.md): subtyping and kinds, which conformance checking uses.
- [docs/dynamic.md](../../docs/dynamic.md) §2.3: abstract types in serialized values.
- [docs/diagnostics.md](../../docs/diagnostics.md) §4.4, §4.5: errors in imported units, and recovery.
