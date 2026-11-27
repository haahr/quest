# bootstrap/python/quest/modules: interfaces, modules, and imports

This package is the bootstrap compiler's module system: it finds the files that imports name, loads and elaborates
interfaces and modules for the type checker, checks that each module conforms to its interface and hides its abstract
types, and compiles units apart into the artifacts of separate compilation. It is the Python original of
[`questlang/modules`](../../../../questlang/modules/README.md), which was ported from it module for module (each
snake_case Python module is the Quest module of the same name, lowercased with its underscores removed:
`abstract_types.py` is `abstracttypes`). That README introduces the concepts; this one says where they are here and
what differs.

## The concepts, here

- **Paths and canonical names.** [`paths.py`](paths.py) searches the importing directory, `-I`, `$QUEST_LIB`, and
  `lib/` for a unit's file, and names each unit by its path relative to its search root
  ([docs/modules.md](../../../../docs/modules.md) §2.2, §2.3). It also answers which options compile C
  (`is_c_compilation_mode`), which decides whether interfaces are loaded from `.qi` artifacts.
- **The unit graph.** [`graph.py`](graph.py) memoizes import resolution (`Resolver`, `Resolved`) and records the
  units an environment has loaded with their typed forms (`UnitGraph`), which the REPL snapshots and restores. Its
  docstring is the best overview of why every consumer must share one resolution. The checks of whether a unit's
  recorded imports would now resolve differently (`import_resolution_change`) live here; the self-hosted compiler
  keeps them in its build engine.
- **Loading.** [`loader.py`](loader.py) loads an interface from a scope already loaded, a current `.qi`, or its
  source, and elaborates each module once per canonical name. The interpreter evaluates the modules it loads through
  its own entry point, `load_module_for_interpreter` in `quest/interpreter/treewalk.py`.
- **Elaboration.** [`elaboration.py`](elaboration.py) implements Cardelli's module system: interfaces into scopes,
  modules checked against their interfaces (type equality, subkinding, subtyping) with their abstract types made
  opaque, and import phrases. As in questlang, the loader and the type checker register callbacks with it
  (`register_unit_loader`, `register_binding_elaborator`) rather than being imported by it.
- **Abstract types by global name.** [`abstract_types.py`](abstract_types.py) gives each module abstract type
  (`geo/coord.P`) one symbol id for the process, and records its representation, for `dynamic.extern` and
  `dynamic.intern` ([docs/dynamic.md](../../../../docs/dynamic.md) §2.3). The self-hosted compiler also uses these
  representations to lay out a whole program's abstract types; the bootstrap does not.
- **Units and the standard library.** [`units.py`](units.py) parses a unit file and checks it holds one declaration;
  [`stdlib.py`](stdlib.py) is the registry that loads the standard library's interfaces and module scopes on demand,
  so `string.length` needs no import. Their implementations are elsewhere: C in `runtime/` and `lib/` for compiled
  code, Python in `quest/interpreter/builtins` for the interpreter.

## artifacts

The [`artifacts/`](artifacts) subpackage compiles units apart, as
[`questlang/modules/artifacts`](../../../../questlang/modules/artifacts/README.md) does:

- [`interface_compiler.py`](artifacts/interface_compiler.py) compiles an interface to a `.qi`, a shadow record of its
  scope in the dynamic serialization format, and decides when a `.qi` is current (the same ABI version, the same
  source, nothing it depends on changed) or must be rebuilt ([docs/build-process.md](../../../../docs/build-process.md)
  §4.2, §5).
- [`manifest.py`](artifacts/manifest.py) reads and writes `.qm` manifests, the record of what a unit imported and was
  compiled against, from which the build engine decides staleness. Both compilers write the same JSON, and each
  treats a manifest the other wrote as stale.

The module compiler, which compiles a module file to C, an object, and a manifest, is the build's
([`build/module_compiler.py`](../build/module_compiler.py)), as in questlang. The bootstrap has no JIT, and so no interface
fingerprints and no in-memory compilation of module units.

## Further reading

- [docs/modules.md](../../../../docs/modules.md): the module system, search rules, separate compilation (§9), and
  manifests (§10).
- [docs/build-process.md](../../../../docs/build-process.md) §2.1, §4, §5: the unit graph, artifacts, and staleness.
- [`bootstrap/python/quest/build/`](../build/README.md): the build engine and the module compiler.
