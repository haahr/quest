# Regular Expressions: `util/regexp`

`util/regexp : util/Regexp` is Quest's regular expression library, written in Quest with no externals, so that it
runs alike on every target: the interpreters, C, arm64, the JIT, and WebAssembly, in a browser included. Its interface
and a summary of its rules are in [libraries.md](libraries.md) §1.9. This document gives the syntax it accepts, why it
is the way it is, how it is built, how it is tested and measured, and what was left out.

The design is RE2's, as Russ Cox describes it in *Regular Expression Matching Can Be Simple And Fast* and its sequels:
a pattern is parsed to a tree, compiled to a small instruction program, and run by a matcher that never takes more
than linear time. Where RE2's and Go's `regexp` answers could differ, this library gives Go's.

## 1. Rules

1. **The syntax is RE2's** (and Go's), Perl's without the features that need backtracking (§2). It is the syntax most
   programmers already write, and everything in it can be matched in time linear in the subject.
2. **Matching is in linear time, always.** There are no backreferences and no lookaround, so no pattern takes
   exponential time on any subject: a library in a language meant for typed, predictable programs should not hide a
   catastrophe behind `(a*)*b`. A program that needs a backreference can test a group's text after the match.
3. **Semantics are leftmost-first**, as Perl's, Python's, RE2's, and Go's: of the matches that begin leftmost, the one
   the pattern prefers, alternatives in order and greedy repetitions longest first. Not POSIX's leftmost-longest.
4. **Bytes, not characters.** A Quest `String` is bytes and a `Char` a byte, so the library matches bytes: `.` matches
   any byte but newline, a class is a set of bytes, and offsets are byte offsets, as `stringOp.getSub` takes them.
   Quest has no UTF-8 (user, 2026-11-17), so there is no UTF-8 mode: a byte above 127 is a byte like any other.
5. **Offsets are a start and a size**, as `getSub(source start size)` takes them, not a start and an end (`end` is a
   keyword). A group that took no part has start and size ~1.
6. **The name is `regexp`** (user, 2026-11-17), Unix's traditional abbreviation (Spencer's `regexp(3)`, Emacs, Tcl,
   Go), for a language from 1989. Where "re" abbreviates "regular expression" in a name, it is written `re` or `RE`,
   never `Re`.
7. **A compiled expression is immutable** and may be used by any number of searches at once. A match holds its
   subject and its offsets; a group's text is copied from the subject when asked for, so a subject changed after the
   match (strings are mutable) changes what the match then returns, as a `getSub` would see it.
8. **Patterns are values too** (user, 2026-11-17), as in OCaml's `re` library: `regexp.RE`, built by functions (`seq`,
   `alt`, `repeat`, `capture`, `literal`, `set`, ...) and compiled by `compileRE`. A pattern built so needs no
   escaping, cannot have a syntax error, and composes: a tokenizer defines `ident` once and uses it in larger
   patterns. The string syntax is a front end that makes the same values: `compile(s)` compiles `parse(s)`.
9. **Every operation that takes more than one match takes them as Go's `regexp` does:** left to right, none
   overlapping, and an empty match where the previous match ended is not one. `findAll`, `findIter`, the replacing
   functions, and `split` all follow it (§3.4).

### 1.1. The Interface's Shape

- **One opaque expression and one opaque match**, `T` and `Match`, so that their representations can change without
  breaking callers.
- **`maybe.T(Match)` for a search**, the library's convention for "found or not" (`strutil.tryToInt`), rather than ~1
  or an exception: not finding a match is not an error.
- **`contains` and `matches` apart from `find`**, because a test that needs no offsets skips the work groups take,
  and is the common case.
- **A payload on `syntax`**, so that a program can show where a user's pattern went wrong; `error` stays a plain
  exception, as `strutil.error` and `bitset.error` are, for a caller's mistake.
- **Group text copied on request**, not up front, so that a search allocates a match and its offsets and nothing per
  group.
- **`RE` opaque, built by functions,** rather than an option type callers take apart: its representation is the
  parser's tree (§3.1), which simplification is free to change. The constructors are `capture` and `namedCapture`,
  not `group` and `named`, because a match's `group` and `named` read a group's text.
- **No flags argument** to `compile`: `(?i)` at the pattern's start does it, and `caseless` for a value.
- **`findIter` and `findStringIter`** give `findAll`'s matches as a `util/iter` iterator, each found as it is pulled
  ([libraries.md](libraries.md) §1.14), and `findAll` is made from `findIter`. They were to be named `matches` and
  `matchStrings`, but `matches` was already the test of a whole subject.

## 2. The Syntax

| Form | Meaning |
| :--- | :--- |
| `x` | the byte `x`, unless it is one of `\ . + * ? ( ) \| [ ] { } ^ $` |
| `\x`, `x` ASCII but not a letter, digit, or `_` | that byte |
| `\t \n \r \f \v \a` | tab, newline, carriage return, form feed, vertical tab, bell |
| `\0`, `\ooo`, `\xHH`, `\x{H...}` | a byte in octal (`\1` to `\7` only when an octal digit follows) or hexadecimal, at most 255 |
| `.` | any byte but `\n` (any byte with `s`) |
| `[abc]`, `[a-z]`, `[^...]` | a class, its complement; `]` first and `-` last are literal |
| `[[:alpha:]]`, `[[:^alpha:]]` | a POSIX class (`alnum alpha ascii blank cntrl digit graph lower print punct space upper word xdigit`), its complement |
| `\d \w \s`, `\D \W \S` | ASCII digits, word bytes (`[0-9A-Za-z_]`), space bytes (`[\t\n\f\r ]`, RE2's, without `\v`), and their complements, in or out of a class |
| `xy`, `x\|y` | concatenation, alternation (left preferred) |
| `x*`, `x+`, `x?`, `x{n}`, `x{n,}`, `x{n,m}` | greedy repetition; `n` and `m` at most 1,000; a `{` that begins no count is literal |
| the same with `?` after | lazy repetition |
| `(x)`, `(?:x)`, `(?P<name>x)`, `(?<name>x)` | a numbered capture, a group that captures nothing, a named capture (letters, digits, and `_`, not starting with a digit, each name once) |
| `^ $` | the subject's start and end, so `$` does not match before a final newline (a line's start and end with `m`) |
| `\A \z` | the subject's start and end, whatever the flags |
| `\b \B` | an ASCII word boundary, and not one; not in a class |
| `(?flags)`, `(?flags:x)` | flags from here to the group's end, or within `x`: `i` (ASCII case folding), `m` (multiline), `s` (`.` matches `\n`), `U` (swap greedy and lazy); `-` clears those after it |

Anything else is a syntax error, raised as `regexp.syntax` with a message and the byte offset in the pattern where it
was found. The messages are worded as Go's `regexp/syntax` words them ("missing closing ]", "invalid nested repetition
operator", "invalid repeat count", ...), and what is refused for a reason of design is refused by name, so the reason
is clear: "backreferences are not supported" for `\1` to `\9`, `(?P=name)`, and `(?P>name)`; "lookaround is not
supported" for `(?=`, `(?!`, `(?<=`, and `(?<!`; and "Unicode classes are not supported" for `\p` and `\P`. A repetition
of a repetition, such as `a**`, is an error, as in RE2. A pattern whose program would have more than 100,000
instructions is refused with "expression too large", at offset 0.

`quote(s)` escapes the bytes of the first row with `\`, Go's `QuoteMeta` set, so that `compile(quote(s))` matches `s`
and nothing else.

## 3. Implementation

`lib/util/regexp.{int,mod}.quest` is the interface programs import. The work is done by three modules it does not
name, each with a narrow interface of its own, so that it can be tested apart, and each `util/regexp`'s and not for
programs to import:

| Module | What it does |
| :--- | :--- |
| `util/regexpSyntax` | The pattern tree, the parser, simplification, and `show` (§3.1) |
| `util/regexpProgram` | The tree compiled to an instruction program, and what a search may skip by (§3.2) |
| `util/regexpMatch` | The program run over a subject: a literal search, a bounded backtracker, or a Pike VM (§3.3) |

Filenames are lowercase (`regexpsyntax.int.quest`, ...), as [libraries.md](libraries.md) requires.

### 3.1. Parsing: `util/regexpSyntax`

A recursive-descent parser over the pattern's bytes makes a tree, `syn.Node`, which is also `regexp.RE`'s
representation: `empty`; `bytes` (a string of literal bytes); `byteSet` (a `bitset.T` of 256, never changed once made,
so nodes may share it); `assertion`; `concat`; `alternate`; `repeat` (its body, bounds, max ~1 for no limit, and
greediness); `capture` (its body and name, "" for an unnamed group); and `caseless`. `regexp`'s functions build the
same nodes directly: `anyByte`, `digit`, `lineStart`, and the other constants are parses of the syntax that means them.

The parser folds case itself, as it reads: under `i`, a letter becomes a set of both its cases, and a class gains its
letters' other cases before it is complemented, so `(?i)[^a]` excludes both `a` and `A`, as RE2's does. A `caseless`
node, which only `regexp.caseless` makes, is folded by `simplify`.

`simplify` makes the tree a program is compiled from, whichever made it: caseless nodes folded into sets; nested
concatenations and alternations flattened; empties dropped and adjacent bytes merged; a set of one byte made a byte; and
repetitions of `{1,1}` removed, and of `{0,0}` too unless they hold a group, which keeps its number (as in RE2 and Go).
Counted repetitions stay counted; the compiler expands them. `show` writes a tree as an s-expression (`"ab"`, `[a-z]`,
`(cat ...)`, `(alt ...)`, `(rep 0 inf x)`, `(cap NAME x)`, ...), which is what `regexp.show` and the syntax test print,
and what `pattern` returns for an expression `compileRE` made.

### 3.2. Compiling: `util/regexpProgram`

The simplified tree becomes a program by Thompson's construction: parallel `Array(Int)`s of opcode and two operands,
indexed by instruction, and the classes the program tests, as one `Array(Bool)` of 256 entries a class (equal sets
share a class). The opcodes:
- `byte b` and `class k`: consume one byte, if it is `b` or class `k` holds it;
- `split x y`: go on at both, `x` preferred, which is how alternation, repetition, and greediness are compiled;
- `jump x`;
- `save k`: record the current offset in capture slot `k` (group `i` uses slots `2i` and `2i + 1`);
- `assert a`: a zero-width test (`^ $ \A \z \b \B`, the line forms included);
- `match`.

Instruction 0 saves slot 0 and the instruction before `match` saves slot 1, so group 0 is the whole match. Arrays of
`Int`, rather than an array of an option type, because the matchers' inner loops then read unboxed words and allocate
nothing.

Repetition is compiled as Go's `regexp/syntax` compiles it, which RE2's and Go's recorded answers need: `x+` as one
copy of `x` that loops back; `x*` as a loop, or as `(x+)?` when `x` can match the empty string, so that matches come
in priority order (golang.org/issue/46123); `x{n,}` as `n - 1` copies of `x` and then `x+`; `x{n,m}` as `n` copies
and `m - n` optional ones, each skipping to the end; and `x{0}` as nothing, its groups numbered all the same. Groups
are numbered before anything is emitted, in the order a left-to-right walk meets them, so the copies a counted
repetition makes share their slots. Before emitting, the compiler estimates the program's size, so that a pattern too
large, such as `((a{1000}){1000}){1000}`, is refused before any of it is made.

The compiler also works out, once, what a search may skip by:
- **the start set**, the bytes a match can begin with, found by following every path from the start that consumes no
  byte, through the assertions as though they held; empty if a match can be empty;
- **whether the program is anchored**: every path passes `\A` (or `^` without `m`) before it consumes a byte;
- **its literal**, if the pattern is bytes and nothing else (no operators and no groups);
- **its prefix**, the bytes every match begins with: a first part's, through groups and repetitions of at least one.

### 3.3. Matching: `util/regexpMatch`

`search(p s start anchored full captures)` finds the leftmost-first match that begins at `start` or later (only at
`start` if anchored), and that ends at the subject's end if `full`. The bytes before `start` are still seen by `^`
and `\b`. Its result is the match's capture slots, or an empty array if `captures` is false, when only whether there
is a match is wanted. `matches` is an anchored, full search without captures; `contains` a search without captures;
`find`, `findFrom`, and `matchAt` searches with them. It chooses one of three matchers:

1. **A literal pattern** is searched for directly: each occurrence of its first byte, the rest compared, rather than
   run as a program.
2. **The bounded backtracker** (Go's `regexp/backtrack.go`), for a search that records groups, of a program of at most
   500 instructions over a subject for which instructions times offsets is at most 256K, Go's limits. It follows one
   path at a time in priority order, as a backtracking matcher does, so the first match it meets is the leftmost-first
   one; but it visits each (instruction, offset) at most once in all, since a path from one that failed fails again,
   so its time is linear too. Its visited marks are generation numbers, so a search clears nothing, and its jobs (an
   instruction to follow, a split's second branch, a slot to put back) are a stack of three `Int`s each.
3. **The Pike VM**, for everything else: the tests without captures, and large programs or long subjects. Two thread
   lists, each a sparse set of instructions (an array of instructions and an array of positions in it, so adding,
   testing, and emptying take constant time), each thread with its capture slots in one flat `Array(Int)`. At each
   byte the current list's threads step into the next's, a thread being added together with every instruction it
   reaches without consuming a byte, in priority order; a thread that reaches `match` cuts off every thread of lower
   priority, and without captures the first match ends the search. Time is linear in the subject times the program's
   size, and memory is the program's size times the slots.

Both the backtracker and the Pike VM use the skips of §3.2: an anchored program is tried at the start only, and when
no thread is running the search moves to the next byte in the start set, or, in the Pike VM, to the next occurrence of
a prefix of more than one byte.

A search's scratch (the thread lists, the work stack, the slots, the backtracker's marks) costs as much to make as a
short search, so the last one made is kept and reused by the next search of the same program, unless a search of it
is still running, as in a `replaceWith` function. A match copies its slots out of the scratch.

### 3.4. Every Match: `util/regexp`

`util/regexp` itself holds the interface's own work over the matchers:
- **`findIter`** searches from a position for the next match, skips an empty one where the previous match ended
  (moving on a byte), and holds the match until `next` hands it out. `findAll` collects it into a vector, and
  `findStringIter` maps it to each match's text.
- **`replaceFirst`, `replaceAll`, and `replaceWith`** are one loop, Go's `replaceAll`, with what replaces a match
  given as a function. A template expands as Go's `Expand` does: `$n` and `${n}` are group `n`'s text, `$name` and
  `${name}` a named group's (`$name` taking as many letters, digits, and `_` as there are, so `$1x` is `${1x}`), and
  `$$` is a `$`; a group that does not exist or took no part expands to nothing, and a `$` that begins none of these
  is itself.
- **`split`** is Go's `Split(s, -1)`: an empty match at the subject's start or end makes no empty piece, and an empty
  subject is one empty piece (none, for the empty pattern).
- **`compileRE`** refuses two groups of one name, which only a pattern built as values can have, by raising `error`.

## 4. Performance

`benchmarks/regexp/` times the library against Go's `regexp` (RE2's semantics, matched without backtracking) and
Python's `re` (a backtracking matcher in C), on eight workloads over a log of 100,000 lines and 2 MB of the tree's
Quest source; its README lists them and says how to run it. `baselines/` keeps the table it printed after each change
to the matcher.

Ten repetitions, in seconds (2026-11-17). The columns are the Pike VM alone (`0-pike-vm.txt`); with the scratch kept,
the start set, anchoring, the literal search, and the prefix (`3-prefix.txt`); and with the bounded backtracker
recording groups (`4-backtracker.txt`), which is the library as it is:

| Workload | Pike VM | + fast paths | + backtracker | Go | Python | /Go |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| literal | (cold) | 0.12 | 0.12 | 0.06 | 0.14 | 2.1 |
| caseless | 1.66 | 0.65 | 0.67 | 1.15 | 0.58 | 0.58 |
| alternation | 3.10 | 0.62 | 0.69 | 1.51 | 0.67 | 0.45 |
| prefix (one group) | 2.53 | 0.50 | 0.33 | 0.16 | 0.21 | 2.1 |
| date (six groups) | 4.32 | 2.65 | 0.35 | 0.35 | 0.40 | 1.01 |
| anchored (one group) | 0.64 | 0.42 | 0.22 | 0.14 | 0.23 | 1.6 |
| tokens (`findAll`) | 2.45 | 1.41 | 1.42 | 1.24 | 0.67 | 1.15 |
| replace (`replaceAll`) | 1.00 | 0.62 | 0.61 | 0.64 | 0.43 | 0.95 |

With the fast paths, the tests that record no groups were already even with Go or faster; the workloads that record
groups were 3 to 8 times Go's, where Go uses not its Pike VM but its bounded backtracker. That is why the library has
the backtracker and no lazy DFA (§6). The baseline for `literal` in the first column includes the program's cold
start, about 0.3 s, as the first three baselines were taken before the runner made an untimed first run.

## 5. Tests

- **Golden tests** under `tests/source/stdlib/`, which run in every phase of both compilers and on every backend, wasm
  included, with their outputs in `tests/golden/<phase>/stdlib/`. They cover what the corpora below do not:
  - `regexp_syntax.quest`: the syntax of §2 parsed and simplified, written out by `show`; every syntax error, with its
    offset; and the same patterns built as values;
  - `regexp_match.quest`: compiling, `matches` and `contains`, `find`, `findFrom` and `matchAt` with the bytes before
    the start, the match's parts, named groups, patterns built as values, and the errors;
  - `regexp_replace.quest`: `findAll` and its empty-match rule, the templates, `replaceWith`, `split`, and `quote`;
  - `regexp_iterators.quest`: `findIter` and `findStringIter` against `findAll`.
- **`tests/python/test_regexp.py`**, the library against its corpora and against Go. `tests/regexp/corpus.quest`,
  compiled once with `./quest`, reads a file of cases, each a pattern and a subject with the expected match of the
  whole subject and of a search and every group's offsets (or, for the every-match cases, `findAll`'s spans, `split`'s
  pieces, and a `replaceAll`), and prints each case that differs. The cases come from:
  - **RE2's search tests**, `re2-search.txt`, made by RE2's `make log`: 944 regexps, each against a set of subjects,
    with the answers RE2 recorded in four modes. Two are this library's, the whole subject and a search, both
    leftmost-first; the leftmost-longest modes are not checked. 1,660 cases.
  - **The AT&T POSIX tests' patterns and subjects**, from `basic.dat`, `nullsubexpr.dat`, and `repetition.dat` (Glenn
    Fowler's `testregex`, as Go edited them): the edge cases of empty matches under repetition (`(a*)*`, `(a|)+`) and
    of counted repetition. Their recorded answers are POSIX's leftmost-longest, so the answers come from Go.
  - **Random patterns** over `a` and `b` in the syntax both libraries have, each against random subjects: 10,000
    cases for the match and the groups, and more, with the AT&T cases, for `findAll`, `split`, and `replaceAll`.
  - **The linear-time patterns**, `(a|aa)*b`, `(a*)*b`, `(?:a+)+b`, and `(a|a)*b`, against 100,000 `a`s, which the
    Pike VM matches, and 20,000, short enough for the backtracker: all within 30 s, where a backtracking matcher would
    not finish at all.

  The answers from Go come from `tests/regexp/oracle.go`, a small program that reads cases and writes them with Go's
  answers. Go's, not Python's `re`, because Go's are RE2's semantics exactly, where Python's differ in corners (`$`
  before a final newline). Subjects and patterns given to Go are ASCII, since Go matches UTF-8 and this library bytes.
  The cases that need Go are skipped where it is not installed. The same harness is also compiled with the wasm
  backend and run in wasmtime and in node, on RE2's search tests and the comparisons with Go, each skipped where its
  engine is not installed.
- **RE2's exhaustive tests**, `re2-exhaustive.txt.bz2` (every small pattern over a small alphabet against every short
  string), run by hand with `QUEST_REGEXP_EXHAUSTIVE=1`, not in every check: after any change to the matcher. They
  pass, 4,935,736 cases, in 24 s compiled.
- **The corpora's files** are copied unchanged from Go's distribution (`$(go env GOROOT)/src/regexp/testdata/`) into
  `tests/data/regexp/`, whose README gives each file's source and keeps its license (Go's BSD license, and AT&T's own
  for the `.dat` files) and says which cases are skipped and why, so none is skipped silently: patterns or subjects
  with a byte above 127, Unicode classes (`\p`, `\P`) and RE2's `\C`, and AT&T cases that are not extended syntax or
  that Go does not compile.

## 6. Left Out

- **Backreferences and lookaround** (rule 2), and with them **backtracking** as Perl, PCRE, Python, and Java do it:
  the smallest matcher, but exponential on patterns such as `(a|aa)*b`. Matching by **combinators**, each node a
  Quest closure taking the subject and a continuation, is elegant in Quest but is backtracking again, and allocates
  closures as it runs.
- **A lazy DFA**, RE2's states made on demand, each the set of instructions the Pike VM would hold, cached with a cap.
  It finds whether and where a match is many times faster than a Pike VM, but records no groups, and the tests that
  record none were already even with Go (§4); the user chose the bounded backtracker instead (2026-11-17).
- **Compiling each pattern to machine code** with `os/code`, as the JIT does: fastest, but only on arm64, and not in
  the interpreters or a browser. Compiling to Quest source would work everywhere but needs the compiler at run time.
- **UTF-8** (rule 4), and so Unicode classes (`\pL`) and RE2's `\C`, which matches one byte where `.` would match a
  character.
- **POSIX leftmost-longest matching**, RE2's and Go's `longest` mode.
- **`compileWith`**, taking a tuple of flags. `(?flags)` and `caseless` do its work, and it can come later without
  changing `compile`.
