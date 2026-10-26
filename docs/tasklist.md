# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Characters 128-255

**Problem.** A character is ASCII (docs/syntax.md §2.3): source text, escapes, `ascii.char`, readers, `dynamic.intern`,
and the `system` strings from the OS reject codes above 127. But Typeful Programming's `Ascii` interface
(docs/TypefulProgramming.md, "interface Ascii") says `ascii.char(n)` raises its error only "if n<0 or n>255", so the
paper's characters may be bytes, with 128-255 allowed. The limit of 127 was chosen to keep the interpreter and C from
disagreeing about non-ASCII characters: the interpreter used Python's Unicode strings (UTF-8 I/O), C raw bytes.

**Reproduce.** `ascii.char(200)` raises `ascii.error`; `'\200'` and `"\xc8"` are tokenizer errors.

**Where to start.** Decide what a character above 127 is. If it is a byte (Latin-1 in the interpreter, as readers
already read files), allow 128-255 in `ascii.char`, escapes, readers, and `dynamic.intern` (whose JSON would write
them as `\u00XX`), and decide whether source text and OS strings may hold them. `pyRepr` in
`questlang/common/diagnostics` then has to match Python's `repr` of such characters.

**Done when.** The range is settled, the interpreter and C agree on it everywhere a character is made, and
docs/syntax.md §2.3 says why it differs from the paper, if it does.
