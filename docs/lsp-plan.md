# Plan: A Language Server for Quest, in Quest

A plan for `quest --lsp`, a Language Server Protocol server in the self-hosted driver, and a small VS Code extension
that starts it. It covers what exists already (§1), the design (§2), the steps in three tiers (§3), testing (§4),
hazards (§5), and open questions (§6). Self-hosted compiler only, as the Jupyter kernel is
([jupyter-kernel.md](jupyter-kernel.md) §1): the bootstrap is untouched, and nothing here changes what either compiler
prints for a program.

**Status (2026-11-23):** not started.

## 1. What exists already

- **Framing and JSON.** A message is `Content-Length: N`, a blank line, and N bytes of JSON. `reader.getChar` reads the
  header lines, `reader.getString(r N)` the body, and `util/json` ([json.md](json.md)) parses and prints it.
- **Waiting input.** `reader.ready(reader.input)` says whether more bytes are waiting, so the server can tell, between
  bindings, that a newer edit or a `$/cancelRequest` has arrived.
- **A driver mode that speaks JSON.** `quest --kernel` (`questlang/driver/kernel`) reads requests and writes records,
  and already answers `complete` and `inspect` for a REPL session ([jupyter-kernel.md](jupyter-kernel.md) §2). Its
  member completion after `m.` is the model for §3.3's first step.
- **Several errors per unit.** The self-hosted checker reports the first error and then every independent one, with
  no cascades ([diagnostics.md](diagnostics.md) §4.5). Each diagnostic has an offset, a length, help, notes, and
  secondary labels, and `location.SourceMap` turns an offset into a line and column.
- **Offsets in the typed AST.** Every node of `questlang/typechecker/typedast` records its byte offset, and binders
  hold their `symbols.ValueSymbol` or `TypeSymbol`.
- **The formatter.** `quest fmt` ([formatter.md](formatter.md)) gives whole-document formatting.

What is missing:

- **UTF-8 in JSON.** `util/json` reads a string's bytes as Latin-1 (json.md §5). It writes each byte above 127 as
  `\u00XX`, so an editor would see each byte of a UTF-8 character as a separate character, and it refuses an escape
  above `ÿ`. §3.0 gives it a UTF-8 mode.
- **File URIs.** The protocol names documents by URI (`file:///Users/x/a%20b.quest`), and nothing in lib encodes or
  decodes them. §3.0 adds `util/uri`.
- **Declaration places.** `ValueSymbol` and `TypeSymbol` (`questlang/types/symbols`) hold a name, a type or kind, and
  an id, but not where they were declared.
- **Source text from the editor.** A unit's text is read from its file in three places:
  - `modules/loader`'s `readUnit`;
  - `modules/artifacts/fingerprint`, which also reads modification times;
  - `modules/artifacts/interfacecompiler`.
- **Syntax error recovery.** The parser stops at the first syntax error, so a typo hides every type error in its
  file ([parser/README.md](../questlang/syntax/parser/README.md), "Syntax errors").
- **Partly typed bindings.** "A failed binding contributes nothing to the typed AST" (diagnostics.md §4.5), so hover
  and definition have nothing to work with in the binding being edited, which is usually the one that fails.

## 2. Design

- **Standard input and output, no sockets.** Editors start a server as a child process and talk over its standard
  input and output. The protocol's socket transport is optional and is left out.
- **One thread, one message at a time.** Quest has no threads, and the runtime and collector assume one.
  Responsiveness comes instead from two habits:
  - **Coalescing edits:** after a `didChange`, read every message already waiting before checking, so a burst of
    keystrokes costs one check.
  - **Giving up stale work:** check `reader.ready` between bindings, and stop a check whose text is no longer
    current. A cancelled request is answered with `RequestCancelled`, as the protocol requires. The REPL's interrupt
    flag (jupyter-kernel.md §5) is the fallback if per-binding checks prove too coarse.
- **In `questlang/`, as a driver mode.** The server needs the compiler's modules, so it is `questlang/lsp/` behind a
  `--lsp` option, like `--kernel`. It may use only library functions the current release has
  ([release-compiler.md](release-compiler.md) §2).
- **Full document sync first.** Each `didChange` carries the whole text (`TextDocumentSyncKind.Full`). Incremental
  sync is a later change, and is worth it only if large files show that copying the text costs anything.
- **Positions in UTF-16, converted at the edge.** Quest strings are bytes, and every offset inside the server is a
  byte offset. The protocol's default column is a count of UTF-16 code units, and every client must support it.
  LSP 3.17 lets a server choose `utf-8` instead when the client lists it in `general.positionEncodings`. I haven't
  confirmed whether VS Code's client lists it; step 5 finds out. So conversion is the normal path, and `utf-8` is
  used when it's offered. Conversion is a few dozen lines in `questlang/lsp/positions`, not a library (§3.0).
- **A build directory out of the tree.** Interfaces the server compiles go in a cache directory, never beside the
  sources (as with `--build-dir`). The cache is per workspace, under `$XDG_CACHE_HOME/quest-lsp/` or
  `~/Library/Caches/quest-lsp/`.
- **Standard output is the protocol's.** Nothing but frames may go to `writer.output`. The checker's diagnostics are
  values and are never printed. Anything that would print, such as a warning written by the driver, goes to standard
  error, which editors show as the server's log.

## 3. Steps

Each step ends with tools/check passing and a commit. Steps L1 and L2 are libraries, which must be released before the
server can use them. Steps 1–5 are tier 1, a usable server; steps 6–8 are tier 2, navigation; steps 9–10 are tier 3,
editing help.

### 3.0. Libraries first

Code in `questlang/` may use only library functions that the current release has (release-compiler.md §2). So L1
and L2 are written, pushed and released before step 2, in the order the digest plan used: library, release,
compiler. Neither touches the runtime, the externals, or the ABI: both are pure Quest, so every backend and both
interpreters run them unchanged, and the WebAssembly backend needs nothing of its own.

**L1. A UTF-8 mode for `util/json`.**

- **The decision it reverses.** json.md §5 records "no UTF-8 mode (user, 2026-11-18)". This step needs the user to
  lift that, for this mode only: the Latin-1 behavior stays the default, and every existing caller is unchanged.
- **The interface.** `ParseOptions` and `PrintOptions` each gain a field, `utf8: Bool`, which is false in `parsing`,
  `parsingDynamic`, `compact` and `indented(n)`. Two new values cover what the server needs: `parsingUtf8` (not
  unique) and `compactUtf8`. Nothing outside `util/json` builds these records, so the new field breaks no caller.
- **Writing in UTF-8 mode.** The output is what Python's `json.dumps(v, ensure_ascii=False)` writes, encoded as
  UTF-8, so it can be checked against Python as the Latin-1 output is:
  - control characters (below 32), `"` and `\` are escaped as they are now;
  - every other byte, DEL and bytes above 127 included, is written unchanged when it is part of a well-formed UTF-8
    sequence;
  - a byte that isn't (a stray continuation byte, a truncated sequence, an overlong form, a surrogate's encoding) is
    written as `�`. The text is then always valid UTF-8, which a client's JSON parser requires. Such a string
    does not round-trip, and the mode's comment says so.
- **Reading in UTF-8 mode.**
  - Raw bytes are read unchanged, as now, and are not checked.
  - `\uXXXX` gives the UTF-8 encoding of that code point: one byte below 128, two below 2048, three otherwise.
  - A high surrogate escape followed by a low surrogate escape gives the four-byte encoding of the pair's code point.
  - A surrogate escape without its partner is an error at its offset, in keeping with the parser's strictness.
    Python accepts it, which is the one place where the two differ, and the documentation says so.
- **Where the change goes.** The string scanner's escape case (`lib/util/json.mod.quest`, where it raises "an escape
  past \\u00ff") and the printer's string writer. The emitter shares the printer's writer, so its `stringValue`
  follows. `read` collects a value's text by counting brackets and is unaffected.
- **Tests.**
  - New cases in `tests/source/stdlib/json_*`: two-, three- and four-byte characters both ways, surrogate pairs,
    lone surrogates, malformed bytes written as `�`, and DEL.
  - The expected output is checked once against Python 3.11's `json.dumps(ensure_ascii=False)` and `json.loads`.
  - The existing Latin-1 goldens stay as they are, which shows the default didn't move.
- **Done when:** the new cases pass in every mode, json.md §5 describes both modes, and libraries.md §1.13 lists the
  new values.

**L2. `util/uri : util/Uri`, file URIs and percent-encoding.**

- **Scope.** Only what URIs need in general, plus file URIs, with no networking. A URI is RFC 3986 text, and Quest
  strings are its bytes.
- **The interface.**

  ```
  interface Uri
  import
      util/maybe : util/Maybe
  export
      (* Raised on text that is not a URI, a malformed %XX, or a file URI
       * that names no local path *)
      error: Exception(String)

      (* A URI's five parts (RFC 3986 §3). The authority is present when the
       * URI has "//", even if it is empty, as in file:///a. The path is still
       * percent-encoded *)
      Def Parts = Tuple
          scheme: String
          authority: maybe.T(String)
          path: String
          query: maybe.T(String)
          fragment: maybe.T(String)
      end
      parse(text: String): Parts
      (* The text of parts; toString(parse(t)) is t *)
      toString(parts: Parts): String

      (* Each byte outside the unreserved set (A-Z a-z 0-9 - . _ ~) and
       * keep as %XX, with upper-case hex digits *)
      encode(s: String keep: String): String
      (* Each %XX as its byte; raises error on % not followed by two hex
       * digits *)
      decode(s: String): String

      (* The file URI of an absolute path: file:// and the path, with each
       * segment encoded and the separators kept; raises error on a relative
       * path *)
      fromPath(path: String): String
      (* The path a file URI names: its decoded path, if its scheme is file
       * (in any case) and its authority is empty or localhost; raises error
       * otherwise *)
      toPath(uri: String): String
  end
  ```
- **Comparing documents.** Clients differ in what they encode. VS Code writes `:` as `%3A`, and others leave it as
  it is. So the server compares documents by `toPath`, never by URI text. It answers with the URI the client sent
  for an open document, and with `fromPath` for any other.
- **POSIX only.** There are no drive letters and no backslashes, as `util/path` has none.
- **Tests.** `tests/source/stdlib/uri_*`:
  - `parse` and `toString` on the RFC's examples;
  - `encode` and `decode` round trips over every byte;
  - `fromPath` and `toPath` round trips on paths with spaces, `%`, `#`, `?` and non-ASCII bytes;
  - the error cases;
  - expected values checked once against Python's `urllib.parse` and `pathlib.Path.as_uri`.
- **Done when:** the tests pass in every mode, and libraries.md has a section for the module.

**Not a library: UTF-16 columns.** The server converts columns in `questlang/lsp/positions`, step 2. It is not
lib, for two reasons:
- future-libraries.md and the regexp decision keep Unicode out of the libraries for now;
- nothing but the server needs the conversion.

Since it lives in `questlang/`, it also needs no release first. The conversion, over one line's bytes:
- a UTF-8 lead byte of a one-, two- or three-byte sequence is one UTF-16 unit, a four-byte one is two, and
  continuation bytes are none;
- a byte that isn't part of a well-formed sequence is one unit, as an editor showing it as U+FFFD counts it;
- going from UTF-16 to bytes, a column between the two halves of a surrogate pair moves back to the character's
  first byte.

Lines are split at `\n` alone, as `location.SourceMap` splits them, which treats a `\r` before it as part of the
line. The protocol also ends lines at `\r\n` and a lone `\r`. A `\r\n` file therefore has the same line numbers in
both; only its last column differs, and no diagnostic points there. A lone `\r`, which nothing in the tree has,
would put the two out of step. If that ever matters, the fix is to have the source map split lines as the protocol
does.

### 3.1. Tier 1: diagnostics, formatting, and an outline

1. **Source text from a table.**
   - **What:** a module, `modules/sources`, through which all three readers in §1 get a unit's text. It maps an
     absolute path to the editor's text and a version number. The fingerprint uses the version in place of the
     file's modification time for an open buffer, so a cached interface that depends on an edited buffer is out of
     date at once. With an empty table, as in every build, behavior is unchanged.
   - **Done when:** the existing suites pass, and a unit test checks a module whose import is supplied from the
     table with no file on disk.
2. **The server's skeleton.**
   - **What:** `quest --lsp` with framing and the lifecycle (`initialize`, `initialized`, `shutdown`, `exit`).
     - Messages go through `util/json`'s UTF-8 mode (L1).
     - Documents are keyed by `uri.toPath` (L2).
     - Columns go through `questlang/lsp/positions` (§3.0), with the encoding chosen in `initialize`.

     It keeps a document table updated from `didOpen`, `didChange` and `didClose`, and answers an unknown request
     with `MethodNotFound`.
   - **Done when:** the protocol test (§4) runs a session that opens, edits and closes a document and shuts down
     cleanly.
3. **Diagnostics.**
   - **What:** after edits coalesce, check the changed document and the open documents that import it. Each
     checker diagnostic becomes an LSP `Diagnostic`:
     - its range comes from the offset and length;
     - its message is the message, with the help text after it;
     - its secondary labels become `relatedInformation`;
     - an error in an imported file is reported in that file, with a diagnostic at the import that led there.

     Publishing an empty list clears a document's diagnostics once its errors are fixed. This step also measures the
     time from edit to diagnostics on the largest files under `questlang/` and records it here; that decides whether
     §6's question about caching per binding needs an answer.
   - **Done when:** the protocol test sees a type error appear, then clear, as a document is edited, and sees an
     error in an imported unit reported at the import.
4. **Formatting and document symbols.**
   - **What:** `textDocument/formatting` runs the formatter on the document's text and returns one edit replacing
     the whole document, or none when the text is already formatted. If the text does not parse, it returns no edits.
     `textDocument/documentSymbol` lists a unit's bindings, types and nested modules from the AST, which needs no type
     checking.
   - **Done when:** the protocol test formats an unformatted document into `quest fmt`'s output, and gets an outline
     that matches the bindings.
5. **The VS Code extension.**
   - **What:** `tools/vscode/`, a TypeScript extension that starts `quest --lsp` through `vscode-languageclient`,
     with a TextMate grammar made from the tokens of the Pygments lexer (`tools/jupyter/quest_lexer.py`) and a
     language configuration for comments and brackets. It is installed by a script, as the kernel is. It is not
     published to the marketplace.
   - **Done when:** in VS Code, a `.quest` file is highlighted, shows its errors as it's typed, formats on request,
     and has an outline.

### 3.2. Tier 2: hover, definition, and references

6. **Declaration places.**
   - **What:** a side table from a symbol's id to the unit and offset of its declaration, filled as the checker
     declares symbols. The id-to-place table is kept apart from `ValueSymbol` and `TypeSymbol`, so the symbols,
     their tuples and the ABI are left alone. For a symbol from a compiled interface (`.qi`), the server parses the
     interface's `.int.quest` when a place is first asked for, and finds the member's declaration by name, so the
     `.qi` format is unchanged.
   - **Done when:** a unit test finds the places of local, top-level and imported members, including a member of a
     nested module.
7. **Hover, definition, and references.**
   - **What:** an index for each checked unit, from offsets to the innermost typed node that spans them, kept until
     the unit changes.
     - **Hover** shows the type of the name under the cursor in the REPL's own form (`let a: Int`), and the doc
       comment above its declaration when it has one.
     - **Definition** is the place from step 6.
     - **References** lists the open and checked units' uses of the symbol id. Until a workspace index exists,
       "checked" means the units the server has already loaded.
   - **Done when:** the protocol test hovers over, jumps from and finds references to a local, a parameter, a
     top-level binding, an imported library member and a type.
8. **Partly typed bindings.**
   - **What:** when a binding fails, the checker still keeps the typed nodes it finished, with the failed
     subexpression marked. This happens only when the server asks for it, with a flag the driver never sets, so
     compiling is unchanged and the typed AST that later phases see is the same. The silent errors that prevent
     cascades (diagnostics.md §4.5) stay as they are.
   - **Done when:** hover and definition work on the rest of a binding that has one type error in it.

### 3.3. Tier 3: completion and edits

9. **Completion.**
   - **What, in two parts:**
     - First, members after `m.`, from the module's interface, as the kernel's `complete` already does
       (jupyter-kernel.md §2). This needs only the import list and the text up to the cursor.
     - Second, names in scope at the cursor: the scope chain of the innermost typed node from step 7, plus keywords.
       While the text up to the cursor does not parse, this needs step 10, or, until then, the scope at the last
       position that does parse.
   - **Done when:** completion after `vector.` lists vector's members, and completion inside a function lists its
     parameters and the unit's bindings.
10. **Syntax error recovery.**
    - **What:** the parser reports its first error exactly as it does now, then resynchronizes and parses on,
      reporting further syntax errors. It resumes at the next top-level binding, or at `end` matched by depth. This
      happens only in the server's mode, so the golden error tests and the bootstrap are unaffected. A part that
      fails to parse becomes an error node that the checker skips, without errors of its own.
    - **Done when:** a file with a typo early on still shows its later type errors, and completion works after the
      typo.

Rename (from step 7's references), signature help, and code actions are left for later. Each waits until someone wants
it.

## 4. Testing

- **A protocol test,** run with the self-hosted compiler's suites (testing.md §2.8, as the kernel's are). A Python
  client using only the standard library starts `quest --lsp`, sends scripted sessions and compares the responses with
  goldens, after removing whatever varies between runs (process ids, paths under the cache).
- **Unit tests** for the source table (step 1), declaration places (step 6) and recovery (step 10), in
  `tests/source/`.
- **By hand:** the VS Code extension (step 5), once per tier, with what was tried recorded here.

## 5. Hazards

- **Long-lived process.** A compiler run ends in seconds; a server runs all day. Tables kept between checks must drop
  what a closed or changed document no longer needs: the elaboration cache, interfaces compiled from buffers, and
  source maps registered with `diagnostics.registerSource`. Step 3 watches the heap over a long scripted session.
- **Global state in the compiler.** Some module-level state assumes one compilation per process. Checking again after
  an edit must reset it, or must give each check its own copy. Step 3 finds out which.
- **Exceptions that escape a check.** A compiler bug that raises past the recovery points must become an error
  response, or a diagnostic at offset 0, never the end of the server.
- **Interfaces built under another ABI.** A `.qi` in the cache from an older compiler is rebuilt, as any build does.
  Since the cache is the server's own, it can simply be cleared.

## 6. Open questions

- **Caching per binding.** If step 3's measurements show that checking a large unit after each edit is too slow,
  should the checker reuse unchanged bindings' results? The answer waits for the numbers.
- **The workspace.** Should references and completion index every unit under the workspace root, or only those the
  open documents import?
- **Other editors.** Neovim and Emacs (eglot) need only a few lines of configuration to start the server. Should
  those lines ship in `tools/`, or only be documented?
