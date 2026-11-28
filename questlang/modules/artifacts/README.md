# questlang/modules/artifacts: compiled interfaces and modules

Separate compilation compiles each unit on its own, against the interfaces of the units it imports rather than their
implementations, and keeps what it produces on disk so that only units whose inputs changed are compiled again. This
directory produces and reads the files that describe units: an interface's `.qi`, and the `.qm` manifest of a module
or a program. Its input is a unit file found and elaborated by the parent directory
([`questlang/modules`](../README.md)). Its callers are the driver (`quest -c x.int.quest`, or a unit file given
alone), the build ([`questlang/build`](../../build/README.md)), whose module compiler writes modules' C, objects,
and manifests, the loader, which reads `.qi` files instead of re-elaborating interface sources, and the JIT, which
compiles modules into a running process.

## Interfaces compiled: the `.qi`

[`interfacecompiler.int.quest`](interfacecompiler.int.quest) compiles an interface file to a `.qi`: a description of
the interface's elaborated scope, from which an importer can rebuild the scope without parsing and elaborating the
source, or the interfaces it imports. A `.qi` is itself a Quest value serialized in the dynamic format
([docs/dynamic.md](../../../docs/dynamic.md) §2, written by `questlang/values`): a *shadow record* whose type,
`qiSchemaType`, has fields for the interface's name, its imports, its types (each with its kind and, if manifest, its
definition), its values' signatures, the source it was compiled from, the interfaces it depends on, the ABI version,
and the compiler that wrote it. Types and kinds are stored as Quest type syntax (`formatTypeForQi`), with type
aliases kept by name so that the file stays small and readable ([docs/build-process.md](../../../docs/build-process.md)
§4.2). Loading one (`loadInterfaceFromQiFile`) parses those strings back into semantic types.

The other half of the interface compiler decides when a `.qi` can be trusted. `ensureResolvedInterfaceArtifacts` uses
a `.qi` only if it is *current*: it records this compiler's ABI version (a number bumped whenever the layout of data
or calls changes, so artifacts of another version cannot be linked with this compiler's code), it records this source
and is at least as new as it, and no interface it depends on, directly or through other interfaces, is newer or
would now resolve to a different file. Otherwise the source is compiled again, the interfaces it imports first
([docs/build-process.md](../../../docs/build-process.md) §5). An interface's C header (`.int.h`) is not made here; the
C backend writes it, and [`questlang/build/interfaceHeaders`](../../build/interfaceheaders.int.quest) keeps it beside the `.qi`.

## Manifests: the `.qm`

[`manifest.int.quest`](manifest.int.quest) defines a unit's *manifest*, its build metadata: its source and object,
the modules it imports (each with the interface the importer expects and the source it was found in), the interfaces
it was compiled against with their modification times, and the ABI version, compiler, and backend of its artifacts.
A program's main routine has one too. The build engine reads it for two things: to learn which modules a unit
imports, so it can queue them, and to decide whether the unit is stale: `unitStaleness` judges the artifacts (one
missing or old, another ABI version, a manifest written by the other compiler, a newer interface), and the engine's
`buildStaleness` adds its own reasons (another backend, or an import that would now find another file). The `.qm` is JSON written exactly as the bootstrap writes it, but each compiler uses only the
module artifacts it made itself ([docs/build-process.md](../../../docs/build-process.md) §4.3).

## Fingerprints for the JIT

Code the JIT compiles links against units already in the running driver, and must not run against a unit whose
interface has changed since. [`fingerprint.int.quest`](fingerprint.int.quest) computes an interface's fingerprint, a
SHA-256 digest of its `.qi`'s content (not its comments, layout, declaration order, paths, or producer), of the
fingerprints of the interfaces it imports, and of the ABI version. Each compiled module exports its interface's
fingerprint as a C string `qh_<unit>`, and the JIT compares it with the fingerprint of the interface it compiled
against ([docs/jit.md](../../../docs/jit.md) §3.3.1). The bootstrap has no JIT and no counterpart.

## Further reading

- [docs/modules.md](../../../docs/modules.md) §9: interface, module, and client compilation; §10: manifests.
- [docs/build-process.md](../../../docs/build-process.md) §4: the artifacts' formats; §5: staleness and the ABI
  version.
- [docs/dynamic.md](../../../docs/dynamic.md) §2: the serialized format a `.qi` uses.
- [docs/jit.md](../../../docs/jit.md) §3.3.1, §3.4: fingerprints, and units outside the driver.
- The bootstrap counterpart:
  [`bootstrap/python/quest/modules/artifacts/`](../../../bootstrap/python/quest/modules/README.md#artifacts).
