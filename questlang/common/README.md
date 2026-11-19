# questlang/common: foundations shared by every phase

This directory is the bottom layer of the self-hosted compiler. Its modules import nothing else from `questlang/`
(only the standard library in `lib/`), and every other directory may import them. They hold what the phases share
but no phase owns: where things are in the source and how errors about them are reported, and a few general tools
(files, JSON, SHA-256, interning keys) that the standard library does not provide or that must behave exactly as the
bootstrap's Python libraries do. Nothing here knows about types, the IR, or code generation.

## Source locations

Every token, syntax node, and error carries a location. [`location.int.quest`](location.int.quest) represents it
cheaply: a `Span` is a file name and a half-open range of 0-based character offsets, `[startOffset, endOffset)`. Lines
and columns are worked out only when a diagnostic is printed: a `SourceMap` holds a file's text and the offset at which
each line starts, and `locate` finds an offset's 1-based line and column by binary search over those starts. Keeping
offsets rather than line/column pairs in the tree keeps each node small, and most locations are never printed.

## Diagnostics: two forms of error

The compiler reports errors in two ways, because the code that finds an error does not always know enough to report
it ([docs/diagnostics.md](../../docs/diagnostics.md) §2).

A `Diagnostic` ([`diagnostics.int.quest`](diagnostics.int.quest)) is what the user sees: a severity, a message, a
span, and optional secondary labels, notes, help, and, for an uncaught exception, a stack trace. `format` renders it
in the familiar style:

```
two.quest:1:14: error: Type mismatch: ...
    let x: Int = "a"
                 ^
```

A `CompilerError` is how code deep in the compiler, the type checker or the module loader, signals an error: it is
raised as the exception `compilerError` where it is found, stopping that piece of work, and carries only an offset in
the unit being checked, since the raiser often does not know which file that is. As it propagates outward, `inFile`
attaches the file, and `atImport` adds an "imported here" label for each import that led to it. The code that catches
it turns it into a `Diagnostic` with `errorDiagnostic`. A *silent* error stops a binding that used a symbol whose
declaration already failed, without reporting a second, derivative error.

Diagnostics accumulate in a *diagnostic bag* ([`diagbag.int.quest`](diagbag.int.quest)), one per compilation, in the
order they are found, so that a phase can report several errors and keep going. The driver runs each phase only while
the bag has no errors, and prints them all at the end. An error after which a phase cannot continue, such as a syntax
error, is added to the bag and then raised as `fatalError`, which the code that started the phase catches
([docs/diagnostics.md](../../docs/diagnostics.md) §3).

## Matching the bootstrap

The two compilers share their golden test outputs, so the self-hosted compiler must print the same text as the
bootstrap wherever the tests look, and must read and write the same artifact files. Several modules here exist to
reproduce what the bootstrap gets from Python's standard library:

- [`json.int.quest`](json.int.quest) parses and prints JSON as Python's `json` module does, keeping object members in
  insertion order and numbers as their text (a full machine word's integer does not fit Quest's `Int`). The dynamic
  format, `.qi` and `.qm` artifacts, and the Jupyter kernel's protocol use it.
- [`pyrepr.int.quest`](pyrepr.int.quest) writes strings, lists, and tuples as Python's `repr` does, for dumps and
  messages that show them.
- [`sha256.int.quest`](sha256.int.quest) gives the hexadecimal SHA-256 of a text, as `hashlib` does, for layout
  tags, type digests, and interface fingerprints. It is `util/digest` after the bootstrap's UTF-8 step
  ([libraries.md](../../docs/libraries.md) §1.12).

## Files

[`files.int.quest`](files.int.quest) is the compiler's view of paths and files, over `util/path`, `os/path`, and
`os/fileStats`: joining and normalizing paths lexically, reading text, modification times in nanoseconds, and
`writeAtomically`, which writes through a temporary file renamed into place so that the workers of a parallel build,
which may rebuild the same interface at once, never read a half-written file. Some files exist only in memory:
[`memoryfiles.int.quest`](memoryfiles.int.quest) keeps the JIT's build artifacts as strings under a pseudo-directory
that is never a real one, and `files` reads and writes them like any other, so the module loader works unchanged
whether its artifacts are on disk or not ([docs/jit.md](../../docs/jit.md) §3.4.1).

## Interning keys

The type tables in `questlang/types` look things up by composite keys, sequences of integers, strings, and flags.
The bootstrap uses Python tuples, which hash for free; building strings to serve as keys made the self-hosted compiler
several times slower. [`keys.int.quest`](keys.int.quest) instead numbers each distinct key in order of first
appearance: the caller writes a key's parts into a reusable buffer (`start`, then `int`, `bool`, `str`) and asks for
its number (`find` or `intern`), so a lookup allocates nothing.

[`strings.int.quest`](strings.int.quest) holds the one string helper the compiler needs beyond `lib/util/strutil`. It
lives here rather than in `lib/` because the released compiler that builds this one compiles it against the release's
own `lib/`.

## Connections

The bootstrap counterparts are in [`bootstrap/python/quest/common/`](../../bootstrap/python/quest/common):
`location.py` (`SourceMap`) and `diagnostics.py` (`Diagnostic`, `QuestCompilerError`, `DiagnosticSink`); for the
rest, the bootstrap uses Python's own `json`, `hashlib`, and `pathlib`.

## Further reading

- [docs/diagnostics.md](../../docs/diagnostics.md): both forms of error (§2), reporting (§3), recovery after an error
  (§4.5), and rendering (§5).
- [docs/exceptions.md](../../docs/exceptions.md) §2.3: the names of stack frames in traces.
- [docs/compiler-organization.md](../../docs/compiler-organization.md) §2: where this layer sits.
