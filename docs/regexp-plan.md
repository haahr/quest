# Plan: A Regular Expression Library in Quest

A library of regular expressions, `util/regexp : util/Regexp`, written in Quest with no externals, so that it runs
alike on every target: the interpreters, C, arm64, the JIT, and WebAssembly, in a browser included. Steps 1 and 2
are built (§6).

## 1. Decisions

1. **The syntax is RE2's** (and Go's `regexp`), Perl's without the features that need backtracking. It is the syntax
   most programmers already write, and everything in it can be matched in time linear in the subject.
2. **Matching is in linear time, always.** No backreferences and no lookaround, so no pattern can take exponential
   time on any subject: a library in a language meant for typed, predictable programs should not hide a catastrophe
   behind `(a*)*b`. Programs that need backreferences are rare and can test the group's text after a match.
3. **Semantics are leftmost-first**, as Perl's, Python's, RE2's, and Go's: of the matches starting leftmost, the one
   the pattern prefers (alternatives in order, greedy quantifiers longest first). Not POSIX's leftmost-longest.
4. **Bytes, not characters.** A Quest `String` is bytes and a `Char` a byte (stringop.int.quest), so the library
   matches bytes: `.` matches any byte but newline, a class is a set of bytes, and offsets are byte offsets, as
   `stringOp.getSub` takes them. A UTF-8 mode, where `.` and classes match encoded code points, is a later step
   (§6) that changes no signature.
5. **Offsets are start and size**, as `getSub(source start size)` takes them, not start and end (`end` is a keyword).
6. **The name is `regexp`** (user, 2026-11-17), Unix's traditional abbreviation (Spencer's `regexp(3)`, Emacs, Tcl,
   Go), for a language from 1989. Where "re" abbreviates "regular expression" in a name, it is written `re` or `RE`,
   never `Re`.
7. **The compiled expression is immutable** and may be shared by any number of matches at once. A match holds the
   subject and the offsets; the text of a group is copied when asked for, so a subject changed after matching
   (strings are mutable) changes what a match then returns, as a `getSub` would see it.
8. **Patterns are values too** (user, 2026-11-17), as in OCaml's `re` library: `regexp.RE`, built by functions
   (`seq`, `alt`, `repeat`, `capture`, `literal`, `set`, ...) and compiled by `compileRE`. A pattern built so needs no
   escaping, cannot have a syntax error, and composes: a tokenizer defines `ident` once and uses it in larger
   patterns. The string syntax is a front end that makes the same values: `compile(s)` is `compileRE(parse(s))`.

## 2. The Syntax

| Form | Meaning |
| :--- | :--- |
| `x` | the byte `x`, unless it is one of `\ . + * ? ( ) \| [ ] { } ^ $` |
| `\x` for those | that byte; `\t \n \r \f \v \a \0`, `\xHH` |
| `.` | any byte but `\n` (any byte with `s`) |
| `[abc]`, `[a-z]`, `[^...]` | a class, its complement; `]` first is literal; `[[:alpha:]]` and the other POSIX names |
| `\d \w \s`, `\D \W \S` | ASCII digits, word bytes (`[0-9A-Za-z_]`), space bytes, and their complements, in or out of a class |
| `xy`, `x\|y` | concatenation, alternation (left preferred) |
| `x*`, `x+`, `x?`, `x{n}`, `x{n,}`, `x{n,m}` | greedy repetition; `{n,m}` with `m` at most 1,000 |
| the same with `?` after | lazy repetition |
| `(x)`, `(?:x)`, `(?P<name>x)`, `(?<name>x)` | a numbered capture, a group that captures nothing, a named capture |
| `^ $` | the subject's start and end (a line's with `m`) |
| `\A \z` | the subject's start and end, whatever the flags |
| `\b \B` | an ASCII word boundary, and not one |
| `(?flags)`, `(?flags:x)` | flags from here to the group's end, or within `x`: `i` (ASCII case folding), `m` (multiline), `s` (`.` matches `\n`), `U` (swap greedy and lazy); `-` clears |

Anything else is a syntax error, with the offset in the pattern where it was found: a backreference (`\1`) or
lookaround (`(?=`) is refused by name ("backreferences are not supported"), so the reason is clear.

## 3. The Interface

```quest
interface Regexp
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
export
    (* A compiled regular expression: immutable, shared freely *)
    T::TYPE

    (* What compile raises for a pattern that is not one: why, and where in
     * the pattern (a byte offset) *)
    Def SyntaxError = Tuple message: String offset: Int end
    syntax: Exception(SyntaxError)

    (* Raised for an argument out of range: a start outside the subject, or a
     * group the expression does not have *)
    error: Exception

    (* ---- Compiling *)
    compile(pattern: String): T
    (* The pattern r was compiled from *)
    pattern(r: T): String
    (* s with every byte that has a meaning in a pattern escaped, so that
     * compile(quote(s)) matches s and nothing else *)
    quote(s: String): String
    (* The number of capturing groups; group 0, the whole match, not counted *)
    groupCount(r: T): Int
    (* The number of the group named name, or ~1 if r has none *)
    groupIndex(r: T name: String): Int

    (* ---- Patterns as values: what parse makes of a pattern, and what
     * compileRE compiles. Each function makes a new pattern; none changes
     * its arguments *)
    RE::TYPE
    (* The pattern a string is, in the syntax of section 2; raises syntax *)
    parse(pattern: String): RE
    compileRE(re: RE): T
    (* The bytes of s, in order *)
    literal(s: String): RE
    (* Any one byte of s; any one byte from lo to hi *)
    set(s: String): RE
    range(lo: Char hi: Char): RE
    (* Any one byte that re does not match; raises error unless re matches
     * one byte only (a set, a range, a class, or an alternation of them) *)
    complement(re: RE): RE
    (* Any byte; any byte but newline (the syntax's .); and the ASCII classes
     * \d, \w, \s *)
    anyByte: RE
    notNewline: RE
    digit: RE
    wordByte: RE
    space: RE
    (* The patterns one after another; any one of them, the first preferred *)
    seq(res: Array(RE)): RE
    alt(res: Array(RE)): RE
    (* re at least min times and at most max (~1: no limit), as many as can
     * be if greedy, as few if not; star, plus, and opt are repeat's commonest
     * uses, greedy *)
    repeat(re: RE min: Int max: Int greedy: Bool): RE
    star(re: RE): RE
    plus(re: RE): RE
    opt(re: RE): RE
    (* A capturing group, numbered in the order compileRE meets them; a named
     * one *)
    capture(re: RE): RE
    namedCapture(name: String re: RE): RE
    (* re with ASCII letters matching either case *)
    caseless(re: RE): RE
    (* The zero-width assertions: ^ and $ (a line's start and end), \A and \z
     * (the subject's), \b and \B *)
    lineStart: RE
    lineEnd: RE
    textStart: RE
    textEnd: RE
    wordBoundary: RE
    notWordBoundary: RE

    (* ---- Testing: no match is made, so these are the fastest *)
    (* Whether r matches the whole of s *)
    matches(r: T s: String): Bool
    (* Whether r matches somewhere in s *)
    contains(r: T s: String): Bool

    (* ---- Finding *)
    (* A match: the subject, and where each group matched in it *)
    Match::TYPE
    (* The leftmost match of r in s, if any *)
    find(r: T s: String): maybe.T(Match)
    (* The leftmost match of r in s at or after start; ^ and \b still see the
     * bytes before start. Raises error unless 0 <= start <= length(s) *)
    findFrom(r: T s: String start: Int): maybe.T(Match)
    (* A match of r beginning exactly at start, if any *)
    matchAt(r: T s: String start: Int): maybe.T(Match)
    (* Every match, left to right, none overlapping; an empty match is not
     * found where the previous match ended *)
    findAll(r: T s: String): vector.T(Match)

    (* ---- A match's parts: group 0 is the whole match *)
    subject(m: Match): String
    (* Whether group i took part in the match: in (a)|(b), only one does *)
    matched(m: Match i: Int): Bool
    (* Where group i matched: its start and size in the subject, or ~1 for a
     * group that took no part; raises error unless 0 <= i <= groupCount *)
    start(m: Match i: Int): Int
    size(m: Match i: Int): Int
    (* The text group i matched, copied; "" for a group that took no part *)
    group(m: Match i: Int): String
    (* The same for a named group; raises error if there is none of that name *)
    named(m: Match name: String): String

    (* ---- Replacing and splitting *)
    (* s with the first match, or every match, replaced by template, where $n
     * and ${n} are group n's text, ${name} a named group's, and $$ a $ *)
    replaceFirst(r: T s: String template: String): String
    replaceAll(r: T s: String template: String): String
    (* s with every match replaced by what f makes of it *)
    replaceWith(r: T s: String f: All(m: Match) String): String
    (* The pieces of s between the matches of r, as strutil.split gives them
     * between occurrences of a string *)
    split(r: T s: String): vector.T(String)
end
```

Typical use:

```quest
import regexp = util/regexp : util/Regexp;
let date = regexp.compile("(?P<y>\\d{4})-(?P<m>\\d\\d)-(?P<d>\\d\\d)");
(* the same, as a value *)
let digits(n: Int): regexp.RE = regexp.repeat(regexp.digit n n true);
let date2 = regexp.compileRE(regexp.seq(array of
    regexp.namedCapture("y" digits(4)) regexp.literal("-")
    regexp.namedCapture("m" digits(2)) regexp.literal("-")
    regexp.namedCapture("d" digits(2)) end));
let found = regexp.find(date line);
if maybe.isSome(:regexp.Match found) then print(regexp.named(maybe.unwrap(:regexp.Match found) "y")) end
```

Why this shape:
- **One opaque expression and one opaque match**, as `stringBuilder.T` and `bitset.T` are, so the representation
  (§4) can change without breaking callers.
- **`maybe.T(Match)` for a search**, the library's convention for "found or not" (`strutil.tryToInt`), rather than
  ~1 or an exception: not finding a match is not an error.
- **`contains` and `matches` apart from `find`**, because a test that needs no offsets can skip the work captures
  take, and is the common case (§4.3).
- **A payload on `syntax`**, so a program can show where a user's pattern went wrong; `error` stays a plain
  exception, as `strutil.error` and `bitset.error` are, for a caller's mistake.
- **Group text copied on request**, not up front, so that `find` allocates a match and its offsets and nothing per
  group.
- **`RE` opaque, built by functions,** rather than an option type callers take apart: its representation is the
  parser's tree (§4.1), which simplification is free to change. `capture` and `namedCapture`, not `group` and
  `named`, because a match's `group` and `named` read a group's text.
- **No flags argument** to compile: `(?i)` at the pattern's start does it, and `caseless` for a value. A
  `compileWith` taking a flags tuple can come later without changing `compile`.

## 4. Implementation

RE2's design, as Russ Cox describes it in *Regular Expression Matching Can Be Simple And Fast* and its sequels:
parse to a syntax tree, compile to a small instruction program, and run the program as a Pike VM, which simulates the
automaton with its capture positions in one pass over the subject.

### 4.1. Parsing

A recursive-descent parser over the pattern's bytes makes a syntax tree, `RE`'s representation, an option type:
literal, class (256 bits: four `word.T`s, or a `bitset.T`), any byte, the anchors and boundaries, concatenation,
alternation, repetition (with its bounds and greediness), and capture (index and name). `compileRE` then simplifies
it:
- **Case folding** (`i`) becomes classes: `a` becomes `[Aa]`, a class gains its other case.
- **Counted repetition** `x{2,4}` becomes `xx(x(x)?)?`, which is why `m` is capped (RE2 caps it at 1,000).
- **Adjacent literals** merge into one string, and a class of one byte becomes a literal.

The parser records each node's offset in the pattern, for the `SyntaxError` and for tests. `RE`'s functions (§3)
make the same tree directly, so simplification happens in `compileRE`, whichever made the tree.

### 4.2. Compiling

The tree becomes a program: parallel `Array(Int)`s of opcode and operands, indexed by instruction, and an array of
the classes the program tests. The opcodes:
- `byte b` and `class k`: consume one byte if it is `b` or in class `k`;
- `split x y`: continue at both, `x` preferred (this is how alternation, repetition, and greediness are compiled);
- `jump x`;
- `save n`: record the current offset in capture slot `n` (group `i` uses slots `2i` and `2i+1`);
- `assert a`: a zero-width test (`^ $ \A \z \b \B`, line forms included);
- `match`.

Arrays of `Int` rather than an array of an option type, because the VM's inner loop then reads unboxed words and
allocates nothing. The compiler also works out, once, what the matcher uses to skip ahead (§4.3): whether the program
is anchored at the start, its literal prefix if it has one, and the set of bytes a match can begin with.

### 4.3. Matching

**The Pike VM.** Two thread lists, each a sparse set of program counters (an array of counters and an array of
positions in it, so adding, testing, and clearing are constant time), each thread with its capture slots in a flat
`Array(Int)`. At each byte the current list's threads step into the next's, and a thread that reaches `match` cuts
off every thread of lower priority. Time is linear in the subject times the program's size; memory is the program's
size times the slots, allocated once per call, not per byte. It gives exact leftmost-first captures, and is what
every operation uses at first.

**Fast paths**, each simple and each a large win where it applies:
- **A literal pattern** (no operators at all) is a substring search, `strutil.findFrom`.
- **A literal prefix** lets the search jump to its next occurrence instead of starting a thread at every byte.
- **An anchored pattern** (`^` or `\A` first) is tried at the start only.
- **`contains` and `matches`** run the VM with no capture slots, which is most of its copying.

**Later, if measurements ask for it: a lazy DFA.** States made on demand, each the set of program counters the VM
would hold, cached in a `hashMap` with a cap on its size (flushed when full, as RE2's is). It answers `contains` and
`matches`, and finds a match's end, many times faster than the VM; `find` then runs the VM only over the match's
range, to get the captures. It is the largest piece and the one most worth leaving until the VM is measured.

### 4.4. Alternatives Not Chosen

- **Backtracking**, as Perl, PCRE, Python, and Java do: the smallest matcher, and it would allow backreferences, but
  exponential time on patterns like `(a|aa)*b`, which decision 2 rules out.
- **Combinators** (each node a Quest closure that takes the subject and a continuation): elegant in Quest, but it is
  backtracking again, and allocates closures as it runs.
- **Compiling each pattern to machine code** with `os/code`, as the JIT does: fastest, but only on arm64, and not in
  the interpreters or a browser. A program compiled to Quest source would work everywhere but needs the compiler at
  run time. Neither is worth it before the VM and DFA are measured.

## 5. Modules and Tests

- `lib/util/regexp.{int,mod}.quest`, the interface of §3. Its implementation is in three modules the interface does not
  name, each with a narrow interface of its own so that it can be tested apart: `util/regexpSyntax` (§4.1),
  `util/regexpProgram` (§4.2), and `util/regexpMatch` (§4.3). Filenames lowercase, as libraries.md requires.
- **Golden tests** under `tests/source/stdlib/`, which run in every phase and on every backend, wasm included, for what
  the corpora below do not cover: each operation of §3, the empty-match rules of `findAll` and `split`, the
  replacement template, and every syntax error's message and offset.
- **RE2's search tests, `re2-search.txt`**, the main corpus: 944 regexps in 236 groups, each tried against a set of
  subjects, with the match and every group's offsets recorded by RE2 itself (`make log` in RE2's distribution) in four
  modes. Two are this library's, a match of the whole subject and a search, both leftmost-first; the other two,
  leftmost-longest, are skipped. A Quest test program reads the file and checks every case, so it runs on every
  backend.
- **The AT&T POSIX tests' patterns and subjects**, from `basic.dat`, `nullsubexpr.dat`, and `repetition.dat` (Glenn
  Fowler's `testregex`, as Go edited them): the edge cases of empty matches under repetition (`(a*)*`, `(a|)+`) and
  of counted repetition. Their recorded answers are POSIX's leftmost-longest (Go runs them with `syntax.POSIX` and
  its longest mode), not this library's, so the answers come from Go's `regexp`, as the random cases' do (below).
- **RE2's exhaustive tests, `re2-exhaustive.txt.bz2`** (428 KB compressed, enormous uncompressed: every small pattern
  over a small alphabet against every short string), run by hand, not in every check: before the library is called
  done, and after any change to the matcher.
- **The corpora's files** are copied from Go's distribution (`$(go env GOROOT)/src/regexp/testdata/`) into
  `tests/data/regexp/`, with a README giving each file's source and keeping its license: BSD for RE2's and Go's, and
  AT&T's own permissive license, which covers `testregex`'s data, for the `.dat` files. A list there names each case
  skipped and why: Unicode classes (`\pL`) and RE2's `\C`, and non-ASCII subjects until the UTF-8 step (§6), so no
  case is skipped silently.
- **A live comparison against Go's `regexp`** (`tests/python/`), for what the corpora miss: a generator makes random
  patterns in this syntax and random subjects, a small Go program gives the expected match and groups, and the library
  must agree. Go's, not Python's `re`, because Go's is RE2's semantics exactly where Python's differs in corners (`$`
  before a final newline). Subjects are ASCII, since Go matches UTF-8 and this library bytes, until the UTF-8 step.
  Skipped where Go is not installed, as the wasm tests are without their engines.
- **A test of linear time:** `(a*)*b` and `(a|aa)*b` against 100,000 `a`s finish well within the test's time limit,
  where a backtracking matcher would not finish at all.
- **A benchmark** beside the MLton programs (benchmarks.md), a log scan and a tokenizer, to decide whether the lazy
  DFA (§4.3) is wanted.
- **libraries.md** gains a section, §1.9, from §2 and §3.

## 6. Steps

1. **The pattern tree, its functions, the parser, and syntax errors** (§3, §4.1), tested by printing the simplified
   tree, of parsed patterns and of patterns built as values.
   *Built 2026-11-17:* `util/regexpSyntax` (the tree, the parser, `simplify`, and `show`) and the first part of
   `util/regexp` (`RE`, its functions, `parse`, `show`, `syntax`, and `error`), tested by
   `tests/source/stdlib/regexp_syntax.quest` in every phase of both compilers and in the arm64, JIT, and wasm-node
   modes. The parser folds case itself, before a class is complemented, so `(?i)[^a]` excludes both `a` and `A`, as
   RE2's does; a `caseless` node, which only `regexp.caseless` makes, is folded by `simplify`.
2. **Compiler and Pike VM** (§4.2, §4.3): `compile`, `matches`, `contains`, `find`, `findFrom`, `matchAt`, and the
   match's parts. The corpora, the comparison with Go, and the linear-time test land here.
   *Built 2026-11-17:* `util/regexpProgram` and `util/regexpMatch`, and those operations in `util/regexp`. Repetition
   is compiled as Go's `regexp/syntax` compiles it, which is what RE2's and Go's answers need: `x+` as one copy of `x`
   that loops back, `x*` as `(x+)?` when `x` can match the empty string (golang.org/issue/46123), `x{n,}` as `n - 1`
   copies and `x+`, and `x{0}` keeping its groups' numbers. Groups are numbered before compiling, so the copies a
   counted repetition makes share slots. The pattern constructors are `capture` and `namedCapture`, since a match's
   `group` and `named` read text. `tests/python/test_regexp.py` passes: RE2's search tests (1,660 cases), the AT&T
   cases and 10,000 random ones against Go, and the linear-time patterns against 100,000 bytes; RE2's exhaustive
   tests, by hand, pass all 4,935,736 cases (24 s compiled). `tests/source/stdlib/regexp_match.quest` covers the
   operations in every phase and in the arm64, JIT, and wasm-node modes.
3. **`findAll`, `replaceFirst`, `replaceAll`, `replaceWith`, `split`, `quote`, and named groups.**
4. **Fast paths:** literal patterns, literal prefixes, anchors, and capture-free tests, each measured.
5. **The benchmark**, and then the lazy DFA if it is wanted.
6. **UTF-8 mode** (`(?u)`, and perhaps by default later): `.` and classes over code points, compiled to byte
   sequences as RE2 compiles them, so the VM is unchanged.

Steps 1 to 3 are the library; 4 to 6 make it faster or wider without changing its interface. **Landing** (user,
2026-11-17): steps 1 to 3 are built and committed one by one, each with its own tests run as it lands (its goldens
in every phase, `run_tests.py -k`, with both compilers); then one full `tools/check`, since `lib/` changes run every
suite, wasm's included; then the user is asked before the push.
