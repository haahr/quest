# The Quest Language Server

A Language Server Protocol server for Quest, written in Quest: `questlang/lsp/`, run as `quest lsp`, with a VS Code
extension in `tools/vscode/`. It answers:
- diagnostics, as a document is edited;
- hover, with the declaration's comment;
- go to definition, in the document or in an imported module's interface;
- references and highlights in the document;
- completion;
- the document's outline;
- formatting by `quest fmt`.

It checks documents with the self-hosted compiler's own front end. Self-hosted only, like the Jupyter kernel
([jupyter-kernel.md](jupyter-kernel.md) §1): the bootstrap is untouched, and nothing here changes what either
compiler prints for a program.

---

## 1. Running It

- **`quest lsp`** serves the protocol on standard input and output; it takes no arguments. In a checkout,
  `./quest lsp` first rebuilds the stages if they are stale, as any `./quest` command does, with the build's
  messages on standard error, since standard output is the protocol's. `tools/lsp/quest-lsp` runs `./quest lsp`, for
  editors that want one command.
- **VS Code:** `tools/vscode/install` fetches the extension's one dependency (`vscode-languageclient`, with npm),
  records the checkout, and links the extension into `~/.vscode/extensions`. VS Code then starts `./quest lsp` for
  `.quest` files (§9).
- **Other editors** start `quest lsp` as a language server for `*.quest`.
- **Initialization options:** `buildDir`, where artifacts go, and `includePaths`, directories to search for imported
  units besides a document's own and the standard library, relative to the workspace. VS Code's setting for them is
  `quest.server.includePaths`; this repository's `.vscode/settings.json`, the one file of `.vscode/` it tracks, lists
  `lib` and `.`, the top of the project, where imports such as `questlang/lsp/server` begin.

## 2. Design

- **Standard input and output, no sockets.** Editors start a server as a child process; the protocol's socket
  transport is not offered.
- **One thread, one message at a time.** Quest has no threads, and the runtime and collector assume one. An edit
  only marks documents to be checked. They are checked when no message is waiting (`reader.ready`, which never
  blocks, §11), so a burst of keystrokes costs one check. A request that needs a document checks it first, if it is
  stale.
- **A command of the driver, like `quest fmt`.** It runs in the compiler that checks documents, so the two never
  disagree. The release compiles the driver ([release-compiler.md](release-compiler.md) §2), so a library function
  the server uses must be in the release before the server can use it; `util/uri` and `util/json`'s UTF-8 mode were
  released (7a6f57a4) before the server moved into the driver.
- **Full document sync.** Each change carries the whole text.
- **Positions:** every offset inside the server is a byte offset. The protocol's columns are UTF-16 code units by
  default, so `questlang/lsp/positions` converts at the edge:
  - a lead byte of a UTF-8 sequence of one to three bytes is one unit, of four bytes two;
  - a byte that is not part of a well-formed sequence is one unit;
  - a column between a surrogate pair's halves goes back to the character's first byte.

  When the client lists `utf-8` in `general.positionEncodings`, the server chooses it, and columns are bytes. Lines
  are split at `\n` alone, as `location.SourceMap` splits them; a lone `\r`, which the protocol also counts as a line
  end, would put the two out of step.
- **A build directory out of the tree:** by default `~/Library/Caches/quest-lsp/` (or `$XDG_CACHE_HOME/quest-lsp/`
  or `~/.cache/quest-lsp/`), one directory per workspace root.
- **Standard output carries only protocol messages.** Anything else, such as the server's log, goes to standard
  error, which editors show as the server's output.

## 3. Checking a Document

`questlang/lsp/analysis` checks a document as the driver checks a program, in an environment of its own:
- **What it sees:** the units it imports, through their interfaces (`importsThroughInterfaces`), with `.qi` artifacts in the build
  directory, which is searched first.
- **Units files too:** a module or interface file type-checks as a program whose one phrase declares it.
- **Fresh each time:** each check starts from a new environment. Only the interfaces' artifacts carry over between
  checks.

On a loaded machine, `questlang/lsp/analysis.mod.quest` with its imports checks in 334 ms the first time, and in
17 ms once its interfaces' artifacts are built.

What the compiler gives the server, beyond what a build uses:

- **Overlays** (`common/overlays`): an open document's text stands in for its file, for the document and for every
  unit that imports it. `common/files` reads, times, and finds sources through the table (`files.isSourceFile`), and
  an overlay's stamp, the time of its last edit, stands for its file's modification time, so an artifact built
  before the edit is stale. With the table empty, as in every build, no path is looked up. When a document closes
  with text the disk does not hold, the build directory is removed, since artifacts built from the overlay would
  look fresh.
- **Partial results:**
  - `typecheck.Result.partial` holds the phrases that checked, whether or not others failed.
  - `elaboration.hooks.keepMembers` gives a module's members that checked, and its internal scope (its imports and
    members), before a failed member fails the module.
- **Recorded expressions:** `typedAst.startRecording` and `stopRecording` keep every expression the checker makes.
  The parts of a binding that checked before the binding failed, which no typed tree holds, are among them (§5).

What a check keeps for the other requests: the problems, the tokens and comments, the syntax tree, the typed
bindings, the recorded expressions when anything failed, the document's scope, and the environment.

**Hazards of a long-lived process.**
- **Memory:** the checker's caches keyed by symbol ids grow with each check, as they do in a REPL session.
- **Source maps:** those registered for diagnostics are replaced by file, so they do not accumulate.
- **Escaping exceptions:** an exception that escapes a check becomes an "internal error" diagnostic, not the end of
  the server.

## 4. Diagnostics

Each checker diagnostic becomes a protocol diagnostic:
- **Message:** with its help and notes after it.
- **Labels:** its secondary labels, the imports that led to an error, become `relatedInformation`.
- **Errors in other files:** an error in an imported unit is published for that unit's file, and also in the
  document, at the import the error's labels name. A file's diagnostics are cleared when its errors are gone.
- **Several errors at once:** independent errors are all reported, as the self-hosted checker reports them
  ([diagnostics.md](diagnostics.md) §4.5), and so are syntax errors past the first (§8).

## 5. Hover, Definition, References

`questlang/lsp/navigation` indexes a checked document's names. Typed nodes give the offsets of their syntax, not of
their names: a let's offset is its keyword's, and a selection's is its target's. So each name is found among the
tokens at or after its node's offset, as the first identifier that spells it, after a `.` for a field.

- **Occurrences:** each binder and use of a value or type symbol, with its symbol id and its declaration as the REPL
  shows it (`echo.valueDeclaration`, in `types/echo`); each module member selected (`m.f`); and each unit name (imports,
  modules, interfaces).
- **Definition:**
  - of a symbol, its binder in the document;
  - of a member of an imported module, its declaration in the module's interface, which is parsed when first asked
    for, the member found by name;
  - of a module's name, its interface.
- **Hover:** the declaration, and the comment just before it, in the document or in the interface. Only declaration
  keywords may stand between the two.
- **References and highlights:** the occurrences in the document of the same symbol, member, or unit.
- **No typed node:** a name in a type, for example, is looked up by name: after `m.`, in m's interface; otherwise in
  the document's scope, whose symbol ids find their binders.
- **Inside a binding that failed:** the recorded expressions (§3) supply the variables and module members it checked
  before it failed. A recorded node may come from another unit the check loaded, so it is taken only where the
  document's token at its offset spells its name, and only where the typed bindings put nothing.

## 6. Completion

After `m.`, where m names an imported module, the names its interface declares, from the interface's syntax.
Otherwise:
- the document's binders;
- its imports;
- the names in its scope and the scopes around it;
- the keywords.

Each is offered once, filtered by the prefix typed. While a document does not parse, completion uses the index of its
last check that typed anything, with the current text.

## 7. Outline and Formatting

- **The outline** (document symbols) comes from the syntax tree alone, so a document that does not type-check still
  has one: an interface and its members, a module and its bindings, and a program's bindings, each with its whole
  span and its name's. A binding's name is the first token after its keyword that spells it. A member's signature
  has only an offset, which may lie past its name, so the name is the nearest before it, within 128 tokens, and the
  member's span runs from its name to its offset. The protocol requires the name inside the span.
- **Formatting** returns `quest fmt`'s text as one edit of the whole document, or no edit when the text is already
  formatted, does not parse, or the formatter fails, which is logged.

## 8. Recovering From Syntax Errors

The parser stops at the first syntax error. A token keeps its offset in the text, so the server cuts the declaration
holding the error out of the token vector and parses the rest again. It repeats until the tokens parse, or a cut does
not move the error on, or 20 cuts are made. Each error is reported as the parser words it. The parser is unchanged,
so its golden tests and the bootstrap's agreement are untouched.

- **A declaration** is a line that starts at a unit's members' column (5, in an interface or module) or at a
  program's (1), with the lines after it, up to the next that starts at that column or left of it.
- **An error at a declaration's first token** is the end of the one before it, which is incomplete, so the one
  before is cut.
- **What can't be cut:** a unit's header, its `import` or `export` line, and `end`. An error there leaves the
  document with no syntax tree.
- **Stubs:** a let or type binding cut out is replaced by `let NAME = questLspBroken` (or `Let NAME =
  QuestLspBroken`), which fails to check. That poisons its name as a failed binding's is, so its uses fail silently
  rather than as undefined names. The stub's own error is not reported.

## 9. The VS Code Extension

`tools/vscode/` is a plain-JavaScript extension:
- **`extension.js`** runs `quest lsp` through `vscode-languageclient`. The quest command is the
  `quest.server.path` setting, else `./quest` in the checkout `install` recorded.
- **`syntaxes/quest.tmLanguage.json`** is a TextMate grammar with the Pygments lexer's tokens
  (`tools/jupyter/quest_lexer.py`).
- **`language-configuration.json`** has comments, brackets, and indentation.

`test_lsp.py` checks that the grammar's keywords are the lexer's. The extension's first run in VS Code turned up
outline symbols whose names lay outside their ranges, which VS Code rejects (fixed; §7); the rest has yet to be tried
by hand (§12).

## 10. Testing

`tests/python/test_lsp.py`, in the unit suite, drives the server through the protocol with
`tests/python/lsp_client.py`, a client that is also for trying the server by hand. It checks what each request
answers, not whole texts, since paths vary:
- the lifecycle, and the errors before `initialize` and for an unknown method;
- both position encodings, with non-ASCII text;
- diagnostics appearing and clearing;
- hover, definition, and references, locally and into `util/Maybe`'s interface;
- the outline of a program and of an interface;
- each outline symbol's name inside its range, and each range inside its parent's;
- completion after `maybe.` and of a local name;
- formatting against `quest fmt`;
- a module whose member fails;
- an open interface's unsaved text seen by its importer;
- recovery in a program and in a module.

`QUEST_LSP_COMPILER` names a quest to run instead of `./quest`, to try changes while `./quest`'s stage build waits
for the lock.

## 11. What It Needed of the Libraries and Runtime

- **`util/json`'s UTF-8 mode** ([json.md](json.md) §5): `parsingUtf8` and `compactUtf8`. The default Latin-1 mode
  would show each byte of a UTF-8 character as a character of its own.
- **`util/uri : util/URI`** ([libraries.md](libraries.md) §1.23): file URIs to and from paths. Documents are keyed by
  path, never by URI text, since clients encode URIs differently.
- **`reader.ready`**, which now never blocks: true when a character, or the end, can be read without waiting. It
  is true for one read ahead, or one in the C stream's buffer (BSD's and glibc's `FILE`), or when the descriptor
  polls readable. Nothing used the old one, which blocked as `more` does. The bootstrap answers from `select`.
  WebAssembly has no way to poll, so there it still answers as `more` does, which may wait.

## 12. Open Work

- **Try the extension in VS Code:** it starts, and its outline works (§9); try highlighting, diagnostics, hover,
  definition, completion, and formatting by hand. Record here what doesn't work.
- **References across the workspace:** they are found in the open document only. Workspace-wide references, and a
  rename built on them, need an index of every unit under the root, or of those the open documents import.
- **Signature help and code actions:** not built.
- **Caching per binding:** if large documents check too slowly, reuse unchanged bindings' results. The one
  measurement (§3) does not ask for it yet.
- **Incremental document sync:** worth it only if copying whole texts ever shows up.
