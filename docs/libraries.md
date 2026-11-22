# Extended Standard Libraries

This document specifies the extended standard libraries for Quest that reside in hierarchical namespaces
(subdirectories of `lib/`) rather than the flat Cardelli standard library (`lib/*.{int,mod}.quest`).

These libraries provide optional values, string building, text manipulation, and core data structures
essential for writing complex applications and the self-hosted Quest compiler (`questlang/`).

---

## Namespace and Import Conventions

Hierarchical libraries are organized by domain under `lib/<category>/`:
- Source files: `lib/<category>/<module>.int.quest` (interface) and
  `lib/<category>/<module>.mod.quest` (implementation).
- Filenames are strictly lowercase (e.g. `maybe.int.quest`, `stringbuilder.mod.quest`, `strutil.mod.quest`); an
  import may name them in any case (`util/stringBuilder`, `collections/hashMap`), since a path is looked up in lower
  case ([modules.md](modules.md) §2.1).
- Import syntax:
  ```quest
  import category/module : category/Interface
  ```
  or aliased:
  ```quest
  import m = category/module : category/Interface
  ```
- Compiled artifacts (`.qi`, `.int.h`, `.mod.c` or `.mod.s`, `.o`) are placed mirror-wise under `.build/<category>/`
  ([build-process.md](build-process.md) §3).
- Type functors follow Cardelli's convention: `vector.T(A)`, `maybe.T(A)`, `stringBuilder.T`.

---

## 1. Utilities (`lib/util/`)

### 1.1. `util/maybe : util/Maybe`

Standalone polymorphic option type functor and constructors for optional values and non-throwing operations.

#### Interface Summary

```quest
interface Maybe export
    (* Polymorphic optional value type *)
    T::ALL(A::TYPE) TYPE

    (* Exception raised on invalid option unwrapping *)
    error: Exception

    (* Test if an option value is present *)
    isSome: All(A::TYPE) All(o: T(A)) Bool

    (* Test if an option value is absent *)
    isNone: All(A::TYPE) All(o: T(A)) Bool

    (* Extract the payload from an option, or raise error if none *)
    unwrap: All(A::TYPE) All(o: T(A)) A

    (* Extract the payload from an option, or return default if none *)
    unwrapOr: All(A::TYPE) All(o: T(A) default: A) A

    (* Construct a some option value *)
    some: All(A::TYPE) All(val: A) T(A)

    (* Construct a none option value *)
    none: All(A::TYPE) T(A)
end
```

---

### 1.2. `util/stringBuilder : util/StringBuilder`

String accumulator with $O(N)$ construction, backed by a native buffer in the runtime (`quest_sb_*` in
`runtime/quest_stdlib.c`, with a matching implementation in each interpreter). Short appends are written into a
working buffer, made on the first append at 32 bytes and doubled up to 512, and numbers are formatted straight into
it; a full buffer becomes a finished chunk, and a string longer than 256 characters is copied into a chunk of its
own. `toString` hands over a buffer that holds everything rather than copying it (sizes chosen by timing,
[benchmarks.md](benchmarks.md) §26.1).

A builder is an abstract native type, as `writer.T` is, and each operation is a function of the module that is the
runtime's function itself, so an append is one direct call and a new builder one allocation. The functions that add to
a builder take it first and return `Ok`; callers that append often import the module as `sb`:

```quest
let b = sb.new()
sb.str(b "x = ")
sb.int(b x)
sb.char(b '\n')
writer.putString(writer.output sb.toString(b))
```

- **`str` copies,** so changing a string after appending it does not change the result. **`strShared`** may instead
  keep the string itself until the builder's next `toString` or `clear`, and its caller promises not to change it until
  then; a long string then costs no copy until `toString`. A short one is copied either way. A string changed against
  the promise leaves the old text or the new in the result, unspecified which, never a memory error. `strutil.join`
  and `joinArray` share their items, since nothing else runs before their `toString`; `questlang/` shares the long
  strings it appends (`ssac`'s text, `ssa/printer`'s functions, `repr/digests`' texts), since the compiler never
  changes a string once made.
- **`toString` empties the builder:** it returns a new string, after which the builder is as `clear` leaves it, and
  can be reused without affecting strings it returned earlier.
- **`<>` or the builder.** A chain of `<>` allocates its result once (the SSA's `concats` pass, [ssa.md](ssa.md)
  §4.1, and WASM's backend), so a string that can be written as one `<>` expression within one function is written
  that way, conditionals as operands (`if c then x else "" end`); a builder used in straight-line code would cost its
  buffer and its `toString` besides. A string accumulated across a loop's iterations, or by helpers that take the
  builder, uses the builder or `strutil.join`, since `s := s <> piece` in a loop copies `s` each time.
- The object style, a recursive tuple of closures whose appends return the builder so that calls chain
  (`b.str("x = ").int(x)`), is what this module was; it cost a tuple and eleven closures per builder and a closure call
  per append, and now survives as a test of the compiler (`tests/source/modules/chainbuilder`).

#### Interface Summary

```quest
interface StringBuilder
    import wordLib = word: Word
export
    T::TYPE
    new(): T
    str(b: T s: String): Ok                         (* a string, copied *)
    strShared(b: T s: String): Ok                   (* a string, which b may keep until toString or clear *)
    char(b: T c: Char): Ok                          (* a character *)
    int(b: T n: Int): Ok                            (* as conv.int: decimal, ~ for negatives *)
    real(b: T r: Real): Ok                          (* as conv.real *)
    bool(b: T v: Bool): Ok                          (* "true" or "false" *)
    word(b: T w: wordLib.T): Ok                     (* unsigned decimal *)
    sub(b: T s: String start: Int size: Int): Ok    (* a substring; string.error if not within s *)
    repeat(b: T c: Char n: Int): Ok                 (* n copies of c; string.error if n < 0 *)
    clear(b: T): Ok                                 (* reset to empty *)
    length(b: T): Int                               (* characters accumulated *)
    toString(b: T): String                          (* a new string of them; b is then empty *)
end
```

---

### 1.3. `util/strutil : util/Strutil`

Comprehensive string utilities: text splitting, joining, pattern search, whitespace trimming, C escaping,
and numerical string parsing.

#### Interface Summary

```quest
interface Strutil
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
    word: Word
export
    error: Exception

    (* Splitting & Joining *)
    split(s: String delim: String): vector.T(String)
    splitlines(s: String): vector.T(String)
    join(delim: String items: vector.T(String)): String
    joinArray(delim: String items: Array(String)): String

    (* Searching & Predicates *)
    startsWith(s: String prefix: String): Bool
    endsWith(s: String suffix: String): Bool
    find(s: String sub: String): Int
    findFrom(s: String sub: String start: Int): Int
    rfind(s: String sub: String): Int
    contains(s: String sub: String): Bool
    strip(s: String): String
    stripLeading(s: String): String
    stripTrailing(s: String): String

    (* Replacement & Escaping *)
    replace(s: String oldSub: String newSub: String): String
    escapeC(s: String): String
    unescapeC(s: String): String

    (* Character Classification *)
    isDigit(c: Char): Bool
    isAlpha(c: Char): Bool
    isAlnum(c: Char): Bool
    isSpace(c: Char): Bool

    (* Parsing *)
    toInt(s: String): Int
    tryToInt(s: String): maybe.T(Int)
    toIntBase(s: String base: Int): Int
    tryToIntBase(s: String base: Int): maybe.T(Int)
    toWord(s: String): word.T
    tryToWord(s: String): maybe.T(word.T)
    toWordBase(s: String base: Int): word.T
    tryToWordBase(s: String base: Int): maybe.T(word.T)
    formatWord(w: word.T base: Int): String
    wordToString(w: word.T): String
    toReal(s: String): Real
    tryToReal(s: String): maybe.T(Real)
    toBool(s: String): Bool
    tryToBool(s: String): maybe.T(Bool)
end
```

---

### 1.4. `util/path : util/Path`

POSIX paths as Strings: their decomposition, normalization, and relative resolution. `os/path` (§4.1) has paths as
values of their own type, built on these, with the file system over them.

#### Interface Summary

```quest
interface Path
import
    collections/vector : collections/Vector
export
    error: Exception

    (* Constants *)
    separator: Char
    separatorString: String

    (* Decomposition & Components *)
    dirName(path: String): String
    baseName(path: String): String
    extension(path: String): String
    stem(path: String): String
    parts(path: String): vector.T(String)

    (* Composition & Joining *)
    join(part1: String part2: String): String
    joinVector(items: vector.T(String)): String
    joinArray(items: Array(String)): String
    withExtension(path: String newExt: String): String

    (* Inspection & Predicates *)
    isAbsolute(path: String): Bool
    isRelative(path: String): Bool
    hasExtension(path: String): Bool

    (* Normalization & Relationships *)
    normalize(path: String): String
    relativeTo(path: String base: String): String
    resolve(path: String): String

    (* Patterns: one name against a shell pattern *)
    matches(pattern: String name: String): Bool
end
```

`matches` takes `*`, `?`, `[abc]`, `[a-z]`, and `[!...]`, as Python's `fnmatch` does, with two differences that
make it `glob`'s rule for one component (§4.6): nothing but a `.` written in the pattern matches a name's leading `.`,
so `*` passes over `.git`; and a `[` with no `]` is itself. It touches no file.

---

### 1.5. `util/argparse : util/ArgParse`

Command-line argument parser patterned after Python's `argparse.ArgumentParser`. Supports flags, string options,
restricted choices, integer options, accumulating multi-value options, positional arguments, and `--` passthrough.
Error messages are written to `writer.err` before raising `argparse.error`. Help generation (`-h`, `--help`) is
automatically registered by default.

#### Interface Summary

```quest
interface ArgParse
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
    writer: Writer
export
    error: Exception

    Parser::TYPE
    Results::TYPE

    (* Parser Construction *)
    new(prog: String description: String): Parser

    (* Option Registration *)
    addFlag(p: Parser name: String flags: String help: String): Ok
    addString(p: Parser name: String flags: String defaultVal: String help: String): Ok
    addChoice(
        p: Parser
        name: String
        flags: String
        choices: Array(String)
        defaultVal: String
        help: String
    ): Ok
    addInt(p: Parser name: String flags: String defaultVal: Int help: String): Ok
    addMulti(p: Parser name: String flags: String help: String): Ok
    addPositional(p: Parser name: String help: String): Ok

    (* Parsing & Help *)
    parse(p: Parser args: Array(String)): Results
    parseVector(p: Parser args: vector.T(String)): Results
    printHelp(p: Parser w: writer.T): Ok
    formatHelp(p: Parser): String

    (* Result Inspection *)
    getBool(r: Results name: String): Bool
    getString(r: Results name: String): maybe.T(String)
    getStringOr(r: Results name: String defaultVal: String): String
    getInt(r: Results name: String): maybe.T(Int)
    getIntOr(r: Results name: String defaultVal: Int): Int
    getMulti(r: Results name: String): vector.T(String)
    positionals(r: Results): vector.T(String)
    targetArgs(r: Results): vector.T(String)
end
```

---

### 1.6. `util/hash : util/Hash`

Universal identity equality, address-based identity hashing, 64-bit SplitMix64 mixing, hash combining, and primitive
hashing functions.

#### Interface Summary

```quest
interface Hash
import
    word: Word
export
    (* Universal identity equality matching Quest's 'is' semantics *)
    identityEqual: All(A::TYPE) All(x1: A x2: A) Bool

    (* Universal identity hash derived from pointer/machine address *)
    identityHash: All(A::TYPE) All(x: A) word.T

    (* 64-bit SplitMix64 bit avalanche mixer *)
    mix(w: word.T): word.T

    (* 64-bit hash combiner for composite keys *)
    combine(h1: word.T h2: word.T): word.T

    (* Primitives to word.T hashes *)
    int(n: Int): word.T
    bool(b: Bool): word.T
    char(c: Char): word.T
    word(w: word.T): word.T
    string(s: String): word.T
end
```

---

### 1.7. `util/sort : util/Sort`

Comparators, binary search, and sorting over arrays and vectors, in Quest alone. A comparator returns a negative
number, 0, or a positive one as its first argument precedes, equals, or follows its second (`~1`, 0, or 1 for the
library's own). `sort` is a 3-way quicksort pivoting on the middle element, in place and not stable: O(n log n)
comparisons on most inputs, O(n * n) at worst. `tests/source/stdlib/sort_operations.quest` tests it.

#### Interface Summary

```quest
interface Sort
import
    collections/vector : collections/Vector
    util/maybe : util/Maybe
export
    (* Comparators *)
    intCompare(a: Int b: Int): Int
    stringCompare(a: String b: String): Int
    realCompare(a: Real b: Real): Int
    reverse: All(A::TYPE) All(cmp: All(a: A b: A) Int) All(a: A b: A) Int

    (* Python's bisect: the index at which key would be inserted after (Right) or before (Left) equal elements; each
       also has a Vector variant (bisectRightVector) and a Range variant over [lo, hi) of an array *)
    bisectRight: All(A::TYPE) All(arr: Array(A) key: A cmp: All(a: A b: A) Int) Int
    bisectLeft: All(A::TYPE) All(arr: Array(A) key: A cmp: All(a: A b: A) Int) Int
    ...

    (* The index of an element equal to key, or none; also binarySearchVector *)
    binarySearch: All(A::TYPE) All(arr: Array(A) key: A cmp: All(a: A b: A) Int) maybe.T(Int)
    ...

    (* In place, and as a new array or vector, leaving the argument unchanged *)
    sort: All(A::TYPE) All(arr: Array(A) cmp: All(a: A b: A) Int) Ok
    sortVector: All(A::TYPE) All(v: vector.T(A) cmp: All(a: A b: A) Int) Ok
    sorted: All(A::TYPE) All(arr: Array(A) cmp: All(a: A b: A) Int) Array(A)
    sortedVector: All(A::TYPE) All(v: vector.T(A) cmp: All(a: A b: A) Int) vector.T(A)
end
```

---

### 1.8. `util/bignum : util/Bignum`

Integers of any size: SML's `IntInf`, with the word conversions, shifts, powers, greatest common divisors, and bitwise
operations of two's complement integers. It is Quest alone, on 64-bit limbs with `word.mulHi`. Every operation makes
a new value and none changes one, so values may be shared freely. A value that fits in an `Int` costs one small
allocation, and its arithmetic is `Int`'s. The MLton benchmarks that need big integers use it
([benchmarks.md](benchmarks.md) §15); `tests/source/stdlib/bignum_operations.quest` tests it.

#### Interface Summary

```quest
interface Bignum
import
    util/maybe : util/Maybe
    word : Word
export
    T::TYPE
    overflow: Exception                 (* toInt and toWord of a value out of their range *)
    divide: Exception                   (* division by zero, and pow of zero to a negative power *)

    fromInt(n: Int): T
    toInt(t: T): Int
    fromWord(w: word.T): T
    toWord(t: T): word.T
    toString(t: T): String              (* decimal, ~ for negatives, as IntInf.toString *)
    fromString(s: String): maybe.T(T)   (* as IntInf.fromString *)

    add(a: T b: T): T
    sub(a: T b: T): T
    mul(a: T b: T): T
    neg(a: T): T
    abs(a: T): T
    quot(a: T b: T): T                  (* truncating, with rem *)
    rem(a: T b: T): T
    div(a: T b: T): T                   (* flooring, with mod *)
    mod(a: T b: T): T
    pow(a: T n: Int): T
    gcd(a: T b: T): T

    equal(a: T b: T): Bool
    less(a: T b: T): Bool
    compare(a: T b: T): Int
    sign(t: T): Int

    andBits(a: T b: T): T               (* on the infinitely sign-extended two's complement *)
    orBits(a: T b: T): T
    xorBits(a: T b: T): T
    notBits(t: T): T
    shiftLeft(t: T count: Int): T
    shiftRight(t: T count: Int): T      (* the floor of t / 2^count *)
end
```

---

### 1.9. `util/regexp : util/Regexp`

Regular expressions in RE2's syntax, matched in time linear in the subject: no pattern takes exponential time on any
subject, since there are no backreferences or lookaround. Matching is on bytes, leftmost-first (as Perl, Python, RE2,
and Go match), and offsets are a start and a size, as `stringOp.getSub` takes them. A pattern is a string, compiled,
or a value, built by functions (as in OCaml's `re`) and compiled with `compileRE`; a pattern so built needs no
escaping and cannot have a syntax error. Quest alone, so it runs alike on every target, a browser included. The
syntax, the design, and the implementation are in [regexp.md](regexp.md) (§2–§3): three modules the interface does
not name, `util/regexpSyntax` (the parser), `util/regexpProgram` (the compiler, as Go's `regexp/syntax` compiles),
and `util/regexpMatch` (the matchers: a literal search, a bounded backtracker, and a Pike VM).
`tests/source/stdlib/regexp_*.quest` test it, and `tests/python/test_regexp.py` checks it against RE2's corpora and
Go's `regexp`.

#### Interface Summary

```quest
interface Regexp
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
    util/iter : util/Iter
export
    Def SyntaxError = Tuple message: String offset: Int end
    syntax: Exception(SyntaxError)      (* a pattern that is not one: why, and where in it *)
    error: Exception                    (* an argument out of range *)

    T::TYPE                             (* a compiled expression, immutable *)
    compile(pattern: String): T
    pattern(r: T): String
    groupCount(r: T): Int
    groupIndex(r: T name: String): Int  (* ~1 for no such group *)

    matches(r: T s: String): Bool       (* the whole of s *)
    contains(r: T s: String): Bool      (* somewhere in s *)

    Match::TYPE
    find(r: T s: String): maybe.T(Match)
    findFrom(r: T s: String start: Int): maybe.T(Match)   (* ^ and \b still see the bytes before start *)
    matchAt(r: T s: String start: Int): maybe.T(Match)    (* a match beginning at start *)
    subject(m: Match): String
    matched(m: Match i: Int): Bool      (* group 0 is the whole match *)
    start(m: Match i: Int): Int         (* ~1 for a group that took no part *)
    size(m: Match i: Int): Int
    group(m: Match i: Int): String      (* "" for a group that took no part *)
    named(m: Match name: String): String

    findAll(r: T s: String): vector.T(Match)              (* none overlapping, as Go's FindAll *)
    findIter(r: T s: String): iter.T(Match)               (* findAll's, found as they are pulled *)
    findStringIter(r: T s: String): iter.T(String)        (* the text of each *)
    replaceFirst(r: T s: String template: String): String (* $1, ${1}, $name, ${name}, $$, as Go's Expand *)
    replaceAll(r: T s: String template: String): String
    replaceWith(r: T s: String f: All(m: Match) String): String
    split(r: T s: String): vector.T(String)              (* as Go's Split(s, -1) *)
    quote(s: String): String            (* s escaped: compile(quote(s)) matches s only *)

    RE::TYPE                            (* a pattern as a value *)
    parse(pattern: String): RE
    compileRE(re: RE): T
    literal(s: String): RE
    set(s: String): RE                  (* any one byte of s *)
    range(lo: Char hi: Char): RE
    complement(re: RE): RE              (* of a pattern that matches one byte *)
    anyByte: RE
    notNewline: RE                      (* the syntax's . *)
    digit: RE
    wordByte: RE
    space: RE
    seq(res: Array(RE)): RE
    alt(res: Array(RE)): RE             (* the first preferred *)
    repeat(re: RE min: Int max: Int greedy: Bool): RE     (* max ~1 for no limit *)
    star(re: RE): RE
    plus(re: RE): RE
    opt(re: RE): RE
    capture(re: RE): RE
    namedCapture(name: String re: RE): RE
    caseless(re: RE): RE                (* ASCII letters of either case *)
    lineStart: RE
    lineEnd: RE
    textStart: RE
    textEnd: RE
    wordBoundary: RE
    notWordBoundary: RE
    show(re: RE): String                (* re simplified and written out, for tests *)
end
```

---

### 1.10. `util/datetime : util/DateTime`

Durations, instants, calendar dates, and their text, in Quest, on `os/time`'s clocks (§4.5), so alike on every
target. It follows SML's Basis (`Time`, `Date`) where that fits, and Go's `time` in keeping wall-clock and monotonic
readings apart.

- **Durations are `Int` nanoseconds** (`Def Duration = Int`), so that they add, subtract, and compare with `Int`'s
  own operators (`2 * datetime.second`), which an opaque type could not; 64 bits of nanoseconds span 292 years
  either way. A difference of two `ticks()` readings is a duration as it is. `fromSeconds` rounds to the nearest
  nanosecond, and `durationString` writes as Go does: `0s`, `250ms`, `1.5us`, `1h2m3.5s`, with no trailing zeros.
- **Instants are opaque:** nanoseconds since the Unix epoch, from 1677-09-21 to 2262-04-11, taken from the wall clock
  only, so that one cannot be mistaken for a duration or a `ticks()` reading. Their arithmetic is a few functions,
  used far less than durations'; `add` and `diff` raise `error` for a result outside the range.
- **POSIX time:** a day is 86,400 seconds and leap seconds do not exist, as for `clock_gettime`, Python, and Go.
- **The calendar is computed in Quest:** the proleptic Gregorian calendar by Howard Hinnant's `days_from_civil` and
  `civil_from_days` ("chrono-Compatible Low-Level Date Algorithms").
- **`Date` is a plain tuple,** not opaque, since programs build dates and read their fields, as they do
  `fileStats.T`'s. Weekday and day of the year are functions, not fields, so that a built date cannot carry an
  inconsistent one. `instant` checks every field (month 1 to 12, a day the month has, hour 0 to 23, minute and second
  0 to 59, nanosecond below 10^9, an offset of less than a day) and raises `error` for a date that does not exist.
- **Time zones are offsets alone:** a date is in UTC, at an offset in seconds east, or in the local zone, whose
  offset `local` asks `os/time` for at that instant, daylight saving included. `instant` uses the date's own `offset`,
  so a local date converts back exactly. There is no zone database: named zones (`America/Los_Angeles`) and their
  rules need data that changes every year, and would be a library of their own.
- **Text is `strftime`'s directives,** a fixed subset (`%Y %m %d %H %M %S %f %j %y %I %p %a %A %b %B %z %e %u %w %%`),
  written and read in Quest in the C locale (English names) rather than by calling `strftime`, so that every target
  writes the same text. `%f` is nine digits of nanoseconds and `%z` is `+hhmm`. A pattern with any other directive
  raises `error`, in `parse` as in `format`; text that does not fit the pattern is `none`. `parse` reads names in
  either case, whole or by their first three letters, a `%y` year as 1969 to 2068, and a `%j` day of the year as its
  month and day; fields the pattern lacks are those of 1970-01-01T00:00:00Z.
- **RFC 3339:** `iso8601` writes UTC with `Z`, and a fraction, without trailing zeros, only when the instant has one
  (`2026-11-17T21:37:41.250Z`). `parseIso8601` takes `T`, `t`, or a space between date and time, and `Z`, `z`, or an
  offset (`+08:00` or `+0800`).

`elapsedSince` and `sleep` are `os/time`'s `ticks()` and `sleepNanoseconds` as durations, so that a program that only
measures needs `os/time` for no more than `ticks()`. `tests/source/stdlib/datetime_operations.quest` tests the fixed
behavior: known instants in UTC and at offsets, round trips, leap years and month lengths, every directive of
`format` and `parse`, RFC 3339 both ways, durations' text, and every error; the local zone only by its round trip,
since it differs by machine. `tests/python/test_datetime.py` runs `tests/datetime/calendar.quest` on 20,000 random
instants over the whole range at random offsets, plus the range's ends, and checks its dates, `format` for the
directives `strftime` shares, RFC 3339, and both parsers' round trips against Python's `datetime`.

#### Interface Summary

```quest
interface DateTime
import
    util/maybe : util/Maybe
export
    error: Exception                    (* a date that does not exist, an instant out of range, a bad pattern *)

    Def Duration = Int                  (* nanoseconds *)
    nanosecond: Duration
    microsecond: Duration
    millisecond: Duration
    second: Duration
    minute: Duration
    hour: Duration
    seconds(d: Duration): Real
    fromSeconds(s: Real): Duration
    durationString(d: Duration): String (* as Go writes them: 1h2m3.5s, 250ms, 1.5us *)
    elapsedSince(ticks: Int): Duration  (* since a reading of os/time's ticks() *)
    sleep(d: Duration): Ok

    Instant::TYPE
    now(): Instant
    epoch: Instant
    fromNanoseconds(ns: Int): Instant
    toNanoseconds(i: Instant): Int
    add(i: Instant d: Duration): Instant
    diff(a: Instant b: Instant): Duration
    compare(a: Instant b: Instant): Int
    before(a: Instant b: Instant): Bool

    Def Date = Tuple year: Int month: Int day: Int hour: Int minute: Int second: Int nanosecond: Int offset: Int end
    utc(i: Instant): Date
    local(i: Instant): Date             (* at the local zone's offset at i *)
    atOffset(i: Instant offset: Int): Date
    instant(d: Date): Instant
    weekday(d: Date): Int               (* 0 for Sunday *)
    yearDay(d: Date): Int
    isLeapYear(year: Int): Bool
    daysInMonth(year: Int month: Int): Int

    format(d: Date pattern: String): String           (* strftime's directives, in the C locale *)
    parse(s: String pattern: String): maybe.T(Date)
    iso8601(i: Instant): String                       (* RFC 3339, in UTC *)
    parseIso8601(s: String): maybe.T(Instant)
end
```

---

### 1.11. `util/random : util/Random`

Pseudo-random numbers in Quest: xoshiro256** (Blackman and Vigna), seeded by SplitMix64, so the same seed gives the
same numbers on every target and every run. The generator is fast, small, and good for simulation and testing; it is
not for cryptography.

- **Seeded explicitly.** `new(seed)` is deterministic, for tests and benchmarks; `fromClock()` seeds from `os/time`
  (§4.5) for different numbers each run. There is no hidden shared generator. `fromClock` mixes `nowInNanoseconds()`,
  `ticks()`, and a count of its own calls, since two calls can read the same clocks.
- **The state** is four `word.T`s, never all zero, stepped with `word`'s rotations, shifts, exclusive ors, and
  multiplications. SplitMix64's first four outputs from the seed fill it, so that nearby seeds give unrelated
  streams. `copy` repeats a generator's future numbers; `split` seeds a new generator from the next output, for a part
  of a program that needs its own.
- **Bounded integers are unbiased,** by Lemire's multiply-and-reject on `word.mulHi`; `between` covers any range,
  the whole of `Int` included. `fraction` is the top 53 bits times 2^-53, `normal` is Box and Muller's method,
  `shuffle` is Fisher and Yates's, and `sample` is the first `k` steps of that shuffle on a copy.
- **Names** are not those of the modules a program uses beside it: `bits`, `anyInt`, and `fraction`, not `word`,
  `int`, and `real`.

`tests/source/stdlib/random_operations.quest` tests the first numbers from known seeds, `below` and `between` at
their edges and without bias, fractions in range, `shuffle` and `sample` as permutations, `copy` and `split`,
`normal`'s mean and spread, and the errors. `tests/python/test_random.py` recomputes the golden's known answers with
reference implementations of xoshiro256** and SplitMix64, so the golden cannot drift from the algorithms.

#### Interface Summary

```quest
interface Random
import
    collections/vector : collections/Vector
    word : Word
export
    T::TYPE
    error: Exception
    new(seed: Int): T
    fromClock(): T
    copy(r: T): T
    split(r: T): T
    bits(r: T): word.T
    anyInt(r: T): Int
    below(r: T n: Int): Int
    between(r: T lo: Int hi: Int): Int
    fraction(r: T): Real
    bool(r: T): Bool
    normal(r: T): Real
    shuffle: All(A::TYPE) All(r: T a: Array(A)) Ok
    shuffleVector: All(A::TYPE) All(r: T v: vector.T(A)) Ok
    choice: All(A::TYPE) All(r: T a: Array(A)) A
    sample: All(A::TYPE) All(r: T a: Array(A) k: Int) vector.T(A)
end
```

### 1.12. `util/digest : util/Digest`

SHA-256 (FIPS 180-4) and CRC-32 (IEEE 802.3, as zlib, gzip, zip, and PNG compute it), in Quest alone, so alike on
every target.

- **Bytes, not text.** A String's characters are its bytes, and each is hashed as one byte with no encoding applied.
  `sha256Hex` of a file's text, read by `os/path.readText`, is what `sha256sum` prints for the file.
- **One state type.** A `digest.T` is made by an algorithm's constructor, for now only `sha256()`, and takes bytes
  in pieces (`add`, `addSub`, `addChar`). A later algorithm adds a constructor and nothing else. The state holds one
  64-byte block and the running hash, never the whole message. `finish` returns the raw digest and leaves the state
  empty, as `stringBuilder.toString` leaves a builder.
- **Raw digests and hex.** `finish` and `sha256Of` return bytes, and `hex` writes any bytes as lowercase digits;
  `sha256Hex` does both in one call.
- **CRC-32 as an Int,** from 0 to 2^32 − 1, continued by passing the value, as zlib's `crc32(crc, buf)` does:
  `crc32Add(crc32(a) b)` is `crc32(a <> b)`.
- **Not here:** FNV, since `util/hash.string` (§1.6) is 64-bit FNV-1a already. HMAC, SHA-1, and MD5 wait until
  something needs them.

The compiler hashes through `questlang/common/sha256`, whose `hexDigest` first turns each byte above 127 into two, as
UTF-8 encodes that character. That matches the bootstrap, which hashes `text.encode("utf-8")` of text read one
character per byte, so the compiler's digests match the bootstrap's. For ASCII text, `hexDigest(t)` is
`digest.sha256Hex(t)`.

`tests/source/stdlib/digest_operations.quest` tests it, and `tests/python/test_digest.py` recomputes its digests
with `hashlib` and `zlib`.

#### Interface Summary

```quest
interface Digest
export
    T::TYPE
    sha256(): T
    size(d: T): Int
    add(d: T text: String): Ok
    addSub(d: T text: String start: Int size: Int): Ok
    addChar(d: T c: Char): Ok
    finish(d: T): String
    hex(bytes: String): String
    sha256Of(text: String): String
    sha256Hex(text: String): String
    crc32(text: String): Int
    crc32Add(crc: Int text: String): Int
end
```

---

### 1.13. `util/json : util/Json`

JSON (RFC 8259) in Quest ([json.md](json.md)), for programs, for the compiler (`.qm` manifests, `.qi`
files, the build workers' messages, the Jupyter kernel), and for the interpreters' `dynamic.intern`. A parsed text
is a `Value` tree; `dump`, `dumpWith`, and `write` print one, and an `Emitter` writes a value to a writer as its
parts are given, with no tree, exactly as `write` would print it.

- **Strings are bytes,** each the code point of the same number (Latin-1), as Quest has no UTF-8: a byte that is not
  printable ASCII is written as `\u00XX`, and an escape above `ÿ` is an error. Every string round-trips exactly.
- **Output is Python's,** for the same value read as Latin-1: compact (`separators=(",", ":")`) or indented
  (`indent=n`), members in the order first put, a real as `repr` writes it.
- **A number keeps its text,** so an integer of any size reads exactly; `toInt`, `toWord`, and `toReal` convert,
  raising `error` when it does not fit.
- **Parsing is strict:** no comments, trailing commas, `NaN`, infinities, or leading zeros. A repeated member name
  keeps its last value in its first place, as Python's does, unless `parsingDynamic` (`unique`) refuses it.
- **`read` takes one value from a reader** and no further, but that a number at the top level is read to the
  character after it, so a reader may hold several documents in a row.
- **`error` carries a `Failure`:** a message, and a byte offset in the text (or `~1` for a value of the wrong kind,
  a number that does not fit, or an emitter's parts out of order).
- **`Object` is manifest** only because an interface's manifest type cannot name its own abstract type
  ([json.md](json.md) rule 6): use its operations, not its fields. It is two arrays in insertion order,
  indexed by a hash map past 8 members.

`tests/source/stdlib/json_values.quest` tests the operations, `tests/python/test_json.py` checks the text against
Python's `json` (`tests/json/corpus.quest`), and `tests/source/stdlib/json_dynamic.quest` holds `dynamic.extern`'s
documents, in every implementation of the format, to the same text.

#### Interface Summary

```quest
interface Json
import
    collections/hashMap : collections/HashMap
    collections/vector : collections/Vector
    util/maybe : util/Maybe
    wordLib = word : Word
    reader : Reader
    writer : Writer
export
    Def Rec Value = Option
        jNull
        jBool with b: Bool end
        jNumber with text: String isInteger: Bool end
        jString with s: String end
        jArray with items: vector.T(Value) end
        jObject with o: Object end
    end
    and Object = Tuple ... end

    null: Value
    bool(b: Bool): Value
    int(n: Int): Value
    word(w: wordLib.T): Value
    real(r: Real): Value
    number(text: String): Value
    string(s: String): Value
    arrayValue(items: vector.T(Value)): Value
    object(o: Object): Value
    newObject(): Object
    put(o: Object name: String v: Value): Ok
    get(o: Object name: String): maybe.T(Value)
    remove(o: Object name: String): maybe.T(Value)
    names(o: Object): Array(String)
    size(o: Object): Int
    forEach(o: Object action: All(name: String v: Value) Ok): Ok
    equal(a: Value b: Value): Bool

    Def ParseOptions = Record unique: Bool end
    parsing: ParseOptions
    parsingDynamic: ParseOptions
    Def PrintOptions = Record indent: Int end
    compact: PrintOptions
    indented(n: Int): PrintOptions

    Def Failure = Tuple message: String offset: Int end
    error: Exception(Failure)
    parse(text: String): Value
    parseWith(text: String options: ParseOptions): Value
    read(rd: reader.T options: ParseOptions): Value
    dump(v: Value): String
    dumpWith(v: Value options: PrintOptions): String
    write(wr: writer.T v: Value options: PrintOptions): Ok

    toBool(v: Value): Bool
    toInt(v: Value): Int
    toWord(v: Value): wordLib.T
    toReal(v: Value): Real
    toString(v: Value): String
    toArray(v: Value): vector.T(Value)
    toObject(v: Value): Object
    member(v: Value name: String): Value
    optional(v: Value name: String): maybe.T(Value)

    Emitter::TYPE
    emitter(wr: writer.T options: PrintOptions): Emitter
    beginObject(e: Emitter): Ok
    name(e: Emitter n: String): Ok
    endObject(e: Emitter): Ok
    beginArray(e: Emitter): Ok
    endArray(e: Emitter): Ok
    value(e: Emitter v: Value): Ok
    nullValue(e: Emitter): Ok
    boolValue(e: Emitter b: Bool): Ok
    intValue(e: Emitter n: Int): Ok
    wordValue(e: Emitter w: wordLib.T): Ok
    realValue(e: Emitter r: Real): Ok
    stringValue(e: Emitter s: String): Ok
    finish(e: Emitter): Ok
end
```

### 1.14. `util/iter : util/Iter`

Iterators ([iter.md](iter.md)): one way to walk a vector, a hash set, a sorted map's range, a string's
characters, or a regular expression's matches, and to chain stages over any of them without building vectors in
between. An iterator is pulled, an ordinary loop:

```quest
while iter.more(it) do let x = iter.next(it) ... end
```

- **`more` changes nothing a caller can see** (calling it twice is calling it once); **`next` raises `exhausted`**
  when there is no next element.
- **An iterator is one-shot.** Walking a source again means asking it for another; a function that walks its
  argument more than once takes an `All() iter.T(A)` (an interface's manifest type cannot name its own abstract type,
  so there is no name for it).
- **An iterator over a collection sees it live:** if the collection gains or loses elements while an iterator is in
  use, other than through it, what the iterator returns from then on is unspecified.
- **Stages pull as they are pulled,** and allocate their closures once, when the pipeline is built. Those that look
  ahead (`filter`, `filterMap`, `takeWhile`, `dropWhile`, `merge`, a peekable iterator) hold the element in an option
  they reuse, so nothing is allocated per element. `map`'s function runs once per element.
- **Pairs are records:** `enumerate`'s `Indexed(A)`, `zip`'s `Pair(A B)`, and `unfold`'s `Step(A S)`, the element
  and the next seed, which its step returns in a `maybe.T`.
- **A producer** makes an iterator with `make(more next)` from closures over its own state, keeping `more`'s and
  `next`'s contract.
- **Cost:** a call into `util/iter` for each `more` and `next` the program makes, under separate compilation, and a
  closure call per stage per element (`benchmarks/iter/`: 82 instructions per element through a `map`, against 17
  for a loop written out). The consumers here (`forEach`, `fold`, `sumInt`, ...) read the closures in place.

`tests/source/stdlib/iter_operations.quest` tests each operation, `more` called repeatedly, `next` past the end, and
peeking.

#### Interface Summary

```quest
interface Iter
import
    util/maybe : util/Maybe
export
    T::ALL(A::TYPE) TYPE
    Peekable::ALL(A::TYPE) TYPE
    Def Indexed = Fun(A::TYPE) Record index: Int value: A end
    Def Pair = Fun(A::TYPE B::TYPE) Record first: A second: B end
    Def Step = Fun(A::TYPE S::TYPE) Record value: A seed: S end
    exhausted: Exception
    error: Exception
    more: All(A::TYPE) All(it: T(A)) Bool
    next: All(A::TYPE) All(it: T(A)) A
    make: All(A::TYPE) All(more: All() Bool next: All() A) T(A)
    empty: All(A::TYPE) T(A)
    once: All(A::TYPE) All(a: A) T(A)
    range: All(lo: Int hi: Int) T(Int)
    rangeBy: All(lo: Int hi: Int step: Int) T(Int)
    ofArray: All(A::TYPE) All(a: Array(A)) T(A)
    chars: All(s: String) T(Char)
    unfold: All(A::TYPE S::TYPE) All(seed: S step: All(s: S) maybe.T(Step(A S))) T(A)
    map: All(A::TYPE B::TYPE) All(it: T(A) f: All(a: A) B) T(B)
    filter: All(A::TYPE) All(it: T(A) p: All(a: A) Bool) T(A)
    filterMap: All(A::TYPE B::TYPE) All(it: T(A) f: All(a: A) maybe.T(B)) T(B)
    take: All(A::TYPE) All(it: T(A) n: Int) T(A)
    drop: All(A::TYPE) All(it: T(A) n: Int) T(A)
    takeWhile: All(A::TYPE) All(it: T(A) p: All(a: A) Bool) T(A)
    dropWhile: All(A::TYPE) All(it: T(A) p: All(a: A) Bool) T(A)
    concat: All(A::TYPE) All(a: T(A) b: T(A)) T(A)
    flatMap: All(A::TYPE B::TYPE) All(it: T(A) f: All(a: A) T(B)) T(B)
    enumerate: All(A::TYPE) All(it: T(A)) T(Indexed(A))
    zip: All(A::TYPE B::TYPE) All(a: T(A) b: T(B)) T(Pair(A B))
    merge: All(A::TYPE) All(a: T(A) b: T(A) compare: All(x: A y: A) Int) T(A)
    peekable: All(A::TYPE) All(it: T(A)) Peekable(A)
    peek: All(A::TYPE) All(p: Peekable(A)) A
    asIter: All(A::TYPE) All(p: Peekable(A)) T(A)
    forEach: All(A::TYPE) All(it: T(A) f: All(a: A) Ok) Ok
    fold: All(A::TYPE Acc::TYPE) All(it: T(A) init: Acc f: All(acc: Acc a: A) Acc) Acc
    count: All(A::TYPE) All(it: T(A)) Int
    any: All(A::TYPE) All(it: T(A) p: All(a: A) Bool) Bool
    all: All(A::TYPE) All(it: T(A) p: All(a: A) Bool) Bool
    find: All(A::TYPE) All(it: T(A) p: All(a: A) Bool) maybe.T(A)
    first: All(A::TYPE) All(it: T(A)) maybe.T(A)
    last: All(A::TYPE) All(it: T(A)) maybe.T(A)
    min: All(A::TYPE) All(it: T(A) compare: All(x: A y: A) Int) maybe.T(A)
    max: All(A::TYPE) All(it: T(A) compare: All(x: A y: A) Int) maybe.T(A)
    toArray: All(A::TYPE) All(it: T(A)) Array(A)
    sumInt(it: T(Int)): Int
    equal: All(A::TYPE) All(a: T(A) b: T(A) eq: All(x: A y: A) Bool) Bool
end
```

### 1.15. `util/iterTools : util/IterTools`

More iterators, after Python's `itertools` ([iter.md](iter.md) §4): sources without end, stages
that group, window, or interleave, the combinatoric iterators, and a few consumers. `util/iter` has the common stages;
this module has the ones reached for less often, and depends on `collections/vector`, `deque` and `hashSet`, which
`util/iter` cannot.

- **Built on `iter.make`, `more` and `next` alone,** since `iter.T` is abstract outside `util/iter`, so a stage
  costs what a `util/iter` stage does: a closure call per stage per element.
- **One-shot, as in `util/iter`.** `cycle(it)` keeps the elements of its first pass and replays them; `cycleFrom`
  takes an `All() iter.T(A)` it calls for each pass instead, keeping nothing. `tee(it n)` gives `n` branches that
  each walk every element, queueing what one has pulled and another has not reached; `it` must not be pulled
  otherwise from then on.
- **Fresh arrays.** `batched`, `windows`, `groupBy`'s `values`, and the combinatoric iterators make a new array for
  each element, which the caller may keep or change.
- **`groupBy` hands out whole runs,** a `Group(K A)` record of the key and an array of the run's elements, rather
  than Python's sub-iterators sharing the source; `key` is called once per element.
- **The combinatoric iterators take arrays** and give Python's order: by the positions chosen, earlier ones changing
  slowest. `product` of two gives `iter.Pair`s; `productOf` of any number and `power(a r)` (`r` copies of `a`) give
  arrays.
- **Errors raise `iterTools.error`,** when the stage is made: a `step` or `size` below 1, a `lo` below 0 (`slice`),
  an `r` below 0, an `n` below 0 (`tee`, `nth`). An `r` past the array's length gives no elements.
- **Names** follow Python's where they fit Quest's conventions; otherwise `islice` is `slice`, `filterfalse` is
  `reject`, `zip_longest` is `zipLongest`, `chain.from_iterable` is `flatten`, and the recipes `roundrobin`,
  `unique_justseen`, `unique_everseen`, `all_equal` and `sliding_window` are `interleave`, `uniqueRuns`, `unique`,
  `allEqual` and `windows`. `scan` is `accumulate` with an initial value; `chain` is `iter.concat`.

`tests/source/stdlib/itertools_operations.quest` tests each operation against Python's results, the edge cases,
`more` called repeatedly, `next` past the end, and the errors.

#### Interface Summary

```quest
interface IterTools
import
    util/iter : util/Iter
    util/maybe : util/Maybe
    word: Word
export
    Def Group = Fun(K::TYPE A::TYPE) Record key: K values: Array(A) end
    error: Exception
    count: All(start: Int step: Int) iter.T(Int)
    repeat: All(A::TYPE) All(a: A) iter.T(A)
    repeatN: All(A::TYPE) All(a: A n: Int) iter.T(A)
    cycle: All(A::TYPE) All(it: iter.T(A)) iter.T(A)
    cycleFrom: All(A::TYPE) All(source: All() iter.T(A)) iter.T(A)
    iterate: All(A::TYPE) All(a: A f: All(a: A) A) iter.T(A)
    accumulate: All(A::TYPE) All(it: iter.T(A) f: All(acc: A a: A) A) iter.T(A)
    scan: All(A::TYPE Acc::TYPE) All(it: iter.T(A) init: Acc f: All(acc: Acc a: A) Acc) iter.T(Acc)
    flatten: All(A::TYPE) All(its: iter.T(iter.T(A))) iter.T(A)
    reject: All(A::TYPE) All(it: iter.T(A) p: All(a: A) Bool) iter.T(A)
    compress: All(A::TYPE) All(it: iter.T(A) selectors: iter.T(Bool)) iter.T(A)
    stepBy: All(A::TYPE) All(it: iter.T(A) step: Int) iter.T(A)
    slice: All(A::TYPE) All(it: iter.T(A) lo: Int hi: Int step: Int) iter.T(A)
    pairwise: All(A::TYPE) All(it: iter.T(A)) iter.T(iter.Pair(A A))
    windows: All(A::TYPE) All(it: iter.T(A) size: Int) iter.T(Array(A))
    batched: All(A::TYPE) All(it: iter.T(A) size: Int) iter.T(Array(A))
    groupBy: All(K::TYPE A::TYPE) All(it: iter.T(A) key: All(a: A) K eq: All(x: K y: K) Bool) iter.T(Group(K A))
    uniqueRuns: All(A::TYPE) All(it: iter.T(A) eq: All(x: A y: A) Bool) iter.T(A)
    unique: All(A::TYPE) All(it: iter.T(A) equal: All(x: A y: A) Bool hash: All(a: A) word.T) iter.T(A)
    intersperse: All(A::TYPE) All(it: iter.T(A) sep: A) iter.T(A)
    interleave: All(A::TYPE) All(its: Array(iter.T(A))) iter.T(A)
    zipLongest: All(A::TYPE B::TYPE) All(a: iter.T(A) b: iter.T(B) fillA: A fillB: B) iter.T(iter.Pair(A B))
    tee: All(A::TYPE) All(it: iter.T(A) n: Int) Array(iter.T(A))
    product: All(A::TYPE B::TYPE) All(a: Array(A) b: Array(B)) iter.T(iter.Pair(A B))
    productOf: All(A::TYPE) All(pools: Array(Array(A))) iter.T(Array(A))
    power: All(A::TYPE) All(a: Array(A) r: Int) iter.T(Array(A))
    permutations: All(A::TYPE) All(a: Array(A) r: Int) iter.T(Array(A))
    combinations: All(A::TYPE) All(a: Array(A) r: Int) iter.T(Array(A))
    combinationsWithReplacement: All(A::TYPE) All(a: Array(A) r: Int) iter.T(Array(A))
    nth: All(A::TYPE) All(it: iter.T(A) n: Int) maybe.T(A)
    allEqual: All(A::TYPE) All(it: iter.T(A) eq: All(x: A y: A) Bool) Bool
    partition: All(A::TYPE) All(it: iter.T(A) p: All(a: A) Bool) iter.Pair(Array(A) Array(A))
end
```

### 1.16. `util/lazy : util/Lazy`

A value computed the first time it is asked for, and kept, as OCaml's `Lazy` and Rust's `LazyCell`:

```quest
let table = lazy.make(fun(): Array(Int) buildTable());
... lazy.force(table)[i] ...
```

- **The function runs at most once if it returns.** `force` calls it the first time, keeps its result, and drops the
  function, so what it captured can be collected. `fromValue(a)` makes one already computed, for an argument some
  callers have at hand and others compute.
- **A raise keeps nothing.** If the function raises, the value goes back to pending, the exception reaches `force`'s
  caller with its own raise site (`raised.reraise`), and the next `force` calls the function again, as Python's
  `functools.cache` does not keep an exception either. OCaml instead raises the same exception on every later force.
- **Forcing a value inside its own computation raises `cycle`,** as OCaml's raises `Lazy.Undefined`, instead of
  recursing until the stack overflows; the value is pending again after it.
- **`map` is lazy too,** forcing its source only when it is forced; `once(f)` is Go's `sync.OnceValue`, `f` called the
  first time the function it returns is. `isForced` and `peek` look without forcing.
- **Cost:** `make` allocates the value and its pending state, and the first `force` its forced state; a forced value
  costs a call, a tag test, and a load.
- **Names:** `fromValue` is OCaml's `from_val` spelled out, naming its source as `hashMap.fromEntries` does; `value`
  would read as an accessor (Kotlin's `Lazy.value` forces), and a bare `from` as a conversion, inviting `from(f)` for
  `make(f)`, which type-checks. Lazy streams are left to `util/iter`.

`tests/source/stdlib/lazy_operations.quest` tests that the function runs once and on the first force, each operation,
a raise and the retry after it, and `cycle`.

#### Interface Summary

```quest
interface Lazy
import
    util/maybe : util/Maybe
export
    T::ALL(A::TYPE) TYPE
    cycle: Exception
    make: All(A::TYPE) All(f: All() A) T(A)
    fromValue: All(A::TYPE) All(a: A) T(A)
    force: All(A::TYPE) All(l: T(A)) A
    isForced: All(A::TYPE) All(l: T(A)) Bool
    peek: All(A::TYPE) All(l: T(A)) maybe.T(A)
    map: All(A::TYPE B::TYPE) All(l: T(A) f: All(a: A) B) T(B)
    once: All(A::TYPE) All(f: All() A) All() A
end
```

### 1.17. `util/memo : util/Memo`

A function of one argument wrapped with a table of the results it has returned, as Python's `functools.cache` and
`lru_cache`, keyed by an `equal` and a `hash` as `collections/hashMap` is:

```quest
let area = memo.memoize(fun(s: String): Int slowArea(s) stringOp.equal hash.string);
let fib = memo.asFunction(memo.makeRecursive(fun(self: All(n: Int) Int n: Int): Int
    if n < 2 then n else self(n - 1) + self(n - 2) end
    fun(a: Int b: Int): Bool a is b hash.int));
```

- **Four constructors:** `make` keeps every result; `makeBounded` keeps the `capacity` most recently used, dropping the
  least recently used to make room; `makeRecursive` and `makeBoundedRecursive` pass the memoized function to the
  function as `self`, so that its own calls are memoized too. (A Quest function's own name always means itself, so a
  wrapper cannot take its place as Python's decorator does.) `memoize` is `asFunction` of `make`, for the common case.
- **One argument.** A function of several takes them as a tuple or a record, with an `equal` and a `hash` for it
  (`hash.combine`); `hash.identityEqual` and `hash.identityHash` key by identity.
- **A result is kept only when the function returns;** one that raises keeps nothing, and is called again the next
  time. A recursive call for a key whose result is being computed computes it again, as Python's does.
- **`contains` is not a use;** `forget` drops one result, `clear` all of them. `hits` and `misses` count the applies
  that found their result kept and those that computed it, as Python's `cache_info`; `clear` keeps them.
- **The bounded caches are a `collections/linkedHashMap` (§2.9) in the order of use:** a hit moves its key to the end,
  a miss at capacity pops the first.
- **Cost:** a hit is a closure call, the key's hash, and a hash map lookup; bounded, a second lookup and a relinking.
- **`make`, not `new`,** as `iter.make` and `lazy.make`: a value built from the functions given, where `new` makes an
  empty container the caller fills.
- **Left out:** expiry by time (a caller can `forget`), weak keys or values (the collector has none), and detecting a
  recursive call for the key in progress, which would cost a set of keys per cache on every miss for a mistake the
  stack overflow already reports.

`tests/source/stdlib/memo_operations.quest` tests each constructor, `fib` of 80 in 81 calls, a raise, the least
recently used order through hits, `forget`, and `clear`, a key of two values, and the error for a capacity below 1.

#### Interface Summary

```quest
interface Memo
import
    word: Word
export
    T::ALL(K::TYPE) ALL(V::TYPE) TYPE
    error: Exception
    make: All(K::TYPE V::TYPE)
        All(f: All(k: K) V equal: All(k1: K k2: K) Bool hash: All(k: K) word.T) T(K V)
    makeBounded: All(K::TYPE V::TYPE)
        All(f: All(k: K) V capacity: Int equal: All(k1: K k2: K) Bool hash: All(k: K) word.T) T(K V)
    makeRecursive: All(K::TYPE V::TYPE)
        All(f: All(self: All(k: K) V k: K) V equal: All(k1: K k2: K) Bool hash: All(k: K) word.T) T(K V)
    makeBoundedRecursive: All(K::TYPE V::TYPE)
        All(f: All(self: All(k: K) V k: K) V capacity: Int equal: All(k1: K k2: K) Bool hash: All(k: K) word.T)
        T(K V)
    apply: All(K::TYPE V::TYPE) All(c: T(K V) k: K) V
    asFunction: All(K::TYPE V::TYPE) All(c: T(K V)) All(k: K) V
    memoize: All(K::TYPE V::TYPE)
        All(f: All(k: K) V equal: All(k1: K k2: K) Bool hash: All(k: K) word.T) All(k: K) V
    contains: All(K::TYPE V::TYPE) All(c: T(K V) k: K) Bool
    size: All(K::TYPE V::TYPE) All(c: T(K V)) Int
    forget: All(K::TYPE V::TYPE) All(c: T(K V) k: K) Bool
    clear: All(K::TYPE V::TYPE) All(c: T(K V)) Ok
    hits: All(K::TYPE V::TYPE) All(c: T(K V)) Int
    misses: All(K::TYPE V::TYPE) All(c: T(K V)) Int
end
```

### 1.18. `util/rational : util/Rational`

Exact rational numbers, as Python's `fractions.Fraction`: a numerator and a positive denominator of any size
(`util/bignum`), in lowest terms, so equal numbers have equal parts.

```quest
let third = rational.make(1 3);
rational.toString(rational.add(third rational.make(1 6)))    (* "1/2" *)
```

- **Every operation is exact; only `toReal` rounds.** `add`, `sub`, `mul`, `div`, `neg`, `abs`, `inv`, and `pow` (of
  either sign) reduce by the parts' gcd; `div`, `inv`, a zero denominator, and zero to a negative power raise `divide`.
  `floor`, `ceil`, `trunc`, and `round` (ties to even, as Python's) give bignums.
- **Reals convert exactly, and back correctly rounded.** `fromReal` gives a finite real's exact value (every one is a
  fraction with a power of two below), as `Fraction(x)` does, and raises `error` for an infinity or a NaN. `toReal`
  rounds to the nearest real, ties to even, as `float(Fraction)` does: the magnitudes' quotient scaled to 54 to 56
  bits, rounded to 53 by hand with the remainder breaking a tie, then scaled back by a power of two. It is exact for
  results of normal magnitude and gives an infinity past the largest real; a subnormal result may be off in its last
  bit (untested).
- **`limitDenominator`** is Python 3.11's `limit_denominator`: the continued fraction's convergents, then the closer of
  the last one and the best semiconvergent.
- **Strings** are `util/bignum`'s, `~` for negatives: `toString` writes `"~3/4"` or `"5"`; `fromString` reads an
  integer, `"num/den"`, or a decimal (`"1.25"`, `".5"`), each with an optional `~`, `-`, or `+`, and gives none for
  anything else or a zero denominator. `toDecimal(t places)` writes a fixed number of places, the last rounded half
  to even.
- **`hash`** agrees with `equal`, for hash maps; it hashes the parts' decimal strings, so it costs their conversion.
- **Left out:** Python's arithmetic mixing fractions with ints and floats (Quest has no overloading; `fromInt` and
  `fromReal` say where a conversion happens), `Decimal` input, and `__format__`.

`tests/source/stdlib/rational_operations.quest` tests lowest terms and signs, the arithmetic, the roundings with
negatives and ties, reals both ways (ties to even, 2000 round trips, an overflow), `limitDenominator`, the strings
both ways, `toDecimal`, `hash`, and the errors; every line was checked against Python 3.11's `fractions`.

#### Interface Summary

```quest
interface Rational
import
    util/bignum : util/Bignum
    util/maybe : util/Maybe
    word: Word
export
    T::TYPE
    divide: Exception
    error: Exception
    zero: T
    one: T
    make(num: Int den: Int): T
    fromBignums(num: bignum.T den: bignum.T): T
    fromInt(n: Int): T
    fromBignum(n: bignum.T): T
    fromReal(r: Real): T
    numerator(t: T): bignum.T
    denominator(t: T): bignum.T
    add(a: T b: T): T
    sub(a: T b: T): T
    mul(a: T b: T): T
    div(a: T b: T): T
    neg(t: T): T
    abs(t: T): T
    inv(t: T): T
    pow(t: T n: Int): T
    equal(a: T b: T): Bool
    less(a: T b: T): Bool
    compare(a: T b: T): Int
    sign(t: T): Int
    isInteger(t: T): Bool
    floor(t: T): bignum.T
    ceil(t: T): bignum.T
    trunc(t: T): bignum.T
    round(t: T): bignum.T
    toReal(t: T): Real
    limitDenominator(t: T maxDenominator: Int): T
    toString(t: T): String
    fromString(s: String): maybe.T(T)
    toDecimal(t: T places: Int): String
    hash(t: T): word.T
end
```

### 1.19. `util/stats : util/Stats`

Statistics of real data, as Python 3.11's `statistics`, function by function, so that the results are Python's to the
last bit:

```quest
let heights = iter.map(vector.iter(people) fun(p: Person): Real p.height);
stats.mean(heights)
```

- **Data comes as an iterator** (§1.14), as Python's functions take any iterable, so a vector, a map's values, or a
  pipeline is read without being copied; an array is `iter.ofArray(xs)`. An iterator is one-shot, so two statistics
  of the same data take two iterators of an array or a vector.
- **One pass, or an array form.** `fsum`, the means, the variances and standard deviations, `mode`, and `multimode`
  read the iterator as they go. The seven that need all the data at once collect it (`iter.toArray`) and call an
  array form, exported too, for data already in an array: `median`, `medianLow`, `medianHigh`, and `quantiles` sort,
  and `covariance`, `correlation`, and `linearRegression` pass twice. The array forms are named for what they are
  computed from, `medianOfArray` (the median of an array), not `medianArray` (which could read as an array that is a
  median), nor `arrayMedian` (`lib/`'s container prefixes, as in `iterFrom`, name what is made); they never change
  their arrays.
- **Exact where Python is.** `mean`, `variance`, `pvariance`, and `harmonicMean` sum the data's exact values as
  rationals (§1.18) and round once, as Python's `_sum` and `_ss` do (the sum of the squared deviations is the sum of
  the squares less the square of the sum over n). `stdev` and `pstdev` are Python's `_float_sqrt_of_frac`: the
  integer square root of the exact variance, scaled to 2 × 53 + 3 bits and rounded to odd, so the one rounding to a
  real is correct. These cost a rational sum, a gcd per value, as Python's do.
- **In reals where Python is.** `fsum` is CPython's `math.fsum` (Shewchuk's partials and its half-way correction),
  correctly rounded; `fmean` is `fsum` over n, the fast mean; `covariance`, `correlation`, and `linearRegression` are
  computed over it with Python's formulas; `geometricMean` is `exp` of the `fmean` of the logs, so its last bit is the
  platform's `exp` and `log`'s.
- **`median`, `quantiles`, and `mode` are Python's code:** the even median is the mean of the middle two;
  `quantiles(it n inclusive)` is Python's exclusive method (a sample) or inclusive one (a population), with its
  clamping and exact integer interpolation weights. `mode` and `multimode` are generic over any `A` with an `equal`
  and a `hash`, counting in a `hashMap`, which keeps first-seen order, so `mode`'s tie goes to the first value seen.
- **Errors are one exception, `error`,** Python's `StatisticsError`: too few values, a negative value for
  `harmonicMean` (where a zero before any negative gives 0, as in Python), a zero or negative one for
  `geometricMean`, two variables of different lengths, and a constant variable for `correlation` and
  `linearRegression`. Data must be finite for the exact functions: `rational.fromReal` raises `rational.error` for an
  infinity or a NaN.
- **Left out:** `NormalDist`, `median_grouped`, weights, a mean passed in (`xbar`, `mu`), `linear_regression`'s
  `proportional`, and `Decimal` or `Fraction` data (a rational version of each function would be a module of its
  own). `util/stats` and `util/rational` each have their own small bit length; `stats` its own integer square root,
  which `util/bignum` could gain.

`tests/source/stdlib/stats_operations.quest` tests every function on Python's documentation examples and on data
where exact and naive arithmetic part (values that cancel, a variance of values offset by 4e9), the medians, `mode`'s
tie, both quantile methods, the array forms, a vector and pipelines as sources, and the errors. Every line was checked
against Python 3.11's `statistics`; `geometricMean`'s is printed to nine places, since `exp` and `log` may differ in
their last bit between backends.

#### Interface Summary

```quest
interface Stats
import
    util/iter : util/Iter
    word: Word
export
    error: Exception
    Def Regression = Tuple slope: Real intercept: Real end
    fromInts(it: iter.T(Int)): iter.T(Real)
    fsum(it: iter.T(Real)): Real
    mean(it: iter.T(Real)): Real
    fmean(it: iter.T(Real)): Real
    geometricMean(it: iter.T(Real)): Real
    harmonicMean(it: iter.T(Real)): Real
    median(it: iter.T(Real)): Real
    medianLow(it: iter.T(Real)): Real
    medianHigh(it: iter.T(Real)): Real
    medianOfArray(xs: Array(Real)): Real
    medianLowOfArray(xs: Array(Real)): Real
    medianHighOfArray(xs: Array(Real)): Real
    mode: All(A::TYPE) All(it: iter.T(A) equal: All(x: A y: A) Bool hash: All(x: A) word.T) A
    multimode: All(A::TYPE) All(it: iter.T(A) equal: All(x: A y: A) Bool hash: All(x: A) word.T) Array(A)
    quantiles(it: iter.T(Real) n: Int inclusive: Bool): Array(Real)
    quantilesOfArray(xs: Array(Real) n: Int inclusive: Bool): Array(Real)
    variance(it: iter.T(Real)): Real
    pvariance(it: iter.T(Real)): Real
    stdev(it: iter.T(Real)): Real
    pstdev(it: iter.T(Real)): Real
    covariance(x: iter.T(Real) y: iter.T(Real)): Real
    covarianceOfArray(x: Array(Real) y: Array(Real)): Real
    correlation(x: iter.T(Real) y: iter.T(Real)): Real
    correlationOfArray(x: Array(Real) y: Array(Real)): Real
    linearRegression(x: iter.T(Real) y: iter.T(Real)): Regression
    linearRegressionOfArray(x: Array(Real) y: Array(Real)): Regression
end
```

### 1.20. `util/format : util/Format`

Values formatted to a width, an alignment, and a precision, as Python 3.11's `format(value, spec)` and `str.format`
write them, so that a table, a report, or a benchmark summary reads as Python's would:

```quest
import fmt = util/format : util/Format;
fmt.real(x ">10.3f")                       (* Python's format(x, ">10.3f") *)
fmt.template("{:<20} {:>10,} {:>8.2%}" array of fmt.ofString(name) fmt.ofInt(n) fmt.ofReal(share) end)
```

- **A spec is Python's mini-language,** `[[fill]align][sign][z][#][0][width][grouping][.precision][type]`, parsed on
  every call as CPython's `parse_internal_render_format_spec` parses it. `int`, `word`, `bignum`, `real`, and
  `string` take one; `bool` formats `"true"` or `"false"` as a string. An integer takes `d b o x X`, or a real's
  type, which formats the real nearest it; a real takes `e E f F g G %`, or none (Python's `repr`, or with a
  precision `g`'s form keeping a digit after the point); a string takes `s`, its precision the most bytes kept.
  Python's `c` and `n` are left out, and precisions are at most 100.
- **Numbers are assembled as CPython's `calc_number_widths` assembles them:** a sign, a prefix (`0x`), the
  magnitude's text, and a suffix (`%`). The leading digits are grouped (every three, or four for `_` on `b o x X`)
  and padded by `InsertThousandsGrouping`'s rule, so zero padding takes the separators too: `fmt.int(1234 "010,")` is
  `00,001,234`. Every integer kind is formatted from its bignum, so Int's least value needs no case of its own.
- **Real digits are exact:** `e`, `f`, and `%` are `real.format`'s (C's `%e` and `%f`, correctly rounded, as Python's
  are), `g` is built from `%e`'s rounded digits by CPython's `format_float_short` rules (including the empty type's
  threshold one place earlier), and the empty type is `conv.real` of the magnitude, the shortest digits that read
  back. Negatives are written with `-`, not `conv`'s `~`, since this is output for people; `z` drops the sign of a
  zero after rounding (not of an infinity). NaN cannot arise in Quest's arithmetic, which raises instead, so its
  `nan` is untested.
- **Templates** are `str.format` with positional fields: `{}` takes the next argument and `{i}` the i-th (the two not
  mixed), `{:spec}` formats it, `{{` and `}}` are braces. Arguments are `Arg`s made by `ofInt`, `ofWord`,
  `ofBignum`, `ofReal`, `ofString`, and `ofBool`, since Quest has no variadic functions. Named fields, conversions
  (`!r`), and nested specs (`{:>{}}`) are left out, and are errors.
- **Tables** lay out cells already formatted: `table(rows layout)` sizes each column to its widest cell, aligns it by
  `layout.aligns` (`<`, `>`, or `^` per column), joins columns with `layout.separator`, underlines a header row with
  dashes when `layout.header` (joined by the same separator, so the rule lines up), gives a short row empty cells,
  and drops each line's trailing spaces. `layout(aligns)` has a two-space separator and no header.
- **Alignment** alone is `alignLeft`, `alignRight`, and `alignCenter` (an odd space on the right, as `^` puts it).
- **Errors are one exception, `error`,** where Python raises `ValueError`, `IndexError`, or `KeyError`: a spec that
  is not one or a part that does not apply to the value, a real type on a bignum too large for a real, and a
  template's malformed field, missing argument, or mixed indexes.

`tests/source/stdlib/format_operations.quest` formats six integers (Int's least among them), a word, two bignums, a
bignum beyond a real, seventeen reals (both zeros, ties, a subnormal, the infinities, a negative that rounds to
zero), and three strings, each with every spec of its list, the errors among them; bools; templates and their errors;
alignment; and tables. Every line but the tables' was checked against Python 3.11, error where it raises; the two
template features left out are errors here where Python succeeds.

#### Interface Summary

```quest
interface Format
import
    bignumLib = util/bignum : util/Bignum
    wordLib = word : Word
export
    error: Exception
    alignLeft(s: String width: Int): String
    alignRight(s: String width: Int): String
    alignCenter(s: String width: Int): String
    int(n: Int spec: String): String
    word(w: wordLib.T spec: String): String
    bignum(n: bignumLib.T spec: String): String
    real(r: Real spec: String): String
    string(s: String spec: String): String
    bool(b: Bool spec: String): String
    Arg::TYPE
    ofInt(n: Int): Arg
    ofWord(w: wordLib.T): Arg
    ofBignum(n: bignumLib.T): Arg
    ofReal(r: Real): Arg
    ofString(s: String): Arg
    ofBool(b: Bool): Arg
    template(t: String args: Array(Arg)): String
    Def Layout = Tuple aligns: String separator: String header: Bool end
    layout(aligns: String): Layout
    table(rows: Array(Array(String)) layout: Layout): String
end
```

---

## 2. Collections (`lib/collections/`)

### 2.1. `collections/vector : collections/Vector`

Growable, dynamically-resizing array collection parameterized over element type `A`.

#### Interface Summary

```quest
interface Vector
import
    util/maybe : util/Maybe
    iterLib = util/iter : util/Iter
export
    (* The polymorphic growable vector type constructor *)
    T::ALL(A::TYPE) TYPE

    (* Exception raised on out-of-bounds access or empty vector operations *)
    error: Exception

    (* Create a new empty vector *)
    new: All(A::TYPE) T(A)

    (* Create a new empty vector with preallocated capacity hint *)
    newWithCapacity: All(A::TYPE) All(capacity: Int) T(A)

    (* Return the number of elements in a vector *)
    length: All(A::TYPE) All(v: T(A)) Int

    (* Test whether a vector is empty *)
    empty: All(A::TYPE) All(v: T(A)) Bool

    (* Return the element at the specified index, or raise error *)
    get: All(A::TYPE) All(v: T(A) index: Int) A

    (* Update the element at the specified index, or raise error *)
    set: All(A::TYPE) All(v: T(A) index: Int value: A) Ok

    (* Return the first element of a vector, or raise error if empty *)
    first: All(A::TYPE) All(v: T(A)) A

    (* Return the last element of a vector, or raise error if empty *)
    last: All(A::TYPE) All(v: T(A)) A

    (* Append a new element to the end of a vector *)
    append: All(A::TYPE) All(v: T(A) value: A) Ok

    (* Remove and return the last element of a vector, or raise error if empty *)
    pop: All(A::TYPE) All(v: T(A)) A

    (* Delete element at index and shift subsequent elements left; linear time *)
    delete: All(A::TYPE) All(v: T(A) index: Int) Ok

    (* Remove all elements from a vector *)
    clear: All(A::TYPE) All(v: T(A)) Ok

    (* Create a shallow copy of a vector *)
    copy: All(A::TYPE) All(v: T(A)) T(A)

    (* Concatenate two vectors into a new vector *)
    concat: All(A::TYPE) All(v1: T(A) v2: T(A)) T(A)

    (* Create a new vector containing the elements of an array *)
    fromArray: All(A::TYPE) All(arr: Array(A)) T(A)

    (* Create an array containing the elements of a vector *)
    toArray: All(A::TYPE) All(v: T(A)) Array(A)

    (* Iterate over all elements of a vector *)
    forEach: All(A::TYPE) All(v: T(A) action: All(elem: A) Ok) Ok

    (* New vectors of f's results, of the elements pred holds for, and of f's some results; and a fold, in order *)
    map: All(A::TYPE B::TYPE) All(v: T(A) f: All(elem: A) B) T(B)
    filter: All(A::TYPE) All(v: T(A) pred: All(elem: A) Bool) T(A)
    fold: All(A::TYPE Acc::TYPE) All(v: T(A) init: Acc f: All(acc: Acc elem: A) Acc) Acc
    filterMap: All(A::TYPE B::TYPE) All(v: T(A) f: All(elem: A) maybe.T(B)) T(B)

    (* Iterators (§1.14), and building from one *)
    iter: All(A::TYPE) All(v: T(A)) iterLib.T(A)
    iterReversed: All(A::TYPE) All(v: T(A)) iterLib.T(A)
    fromIter: All(A::TYPE) All(it: iterLib.T(A)) T(A)
    appendIter: All(A::TYPE) All(v: T(A) it: iterLib.T(A)) Ok
end
```

#### Memory and Growth Strategy

- **Initial Floor**: When appending to an empty vector, initial capacity is allocated to 4 elements (or the
  capacity hint, when it is larger).
- **Growth Factor**: When capacity is exceeded, storage doubles, ensuring $O(1)$ amortized append time. Most vectors
  stay short (half of those a build of the compiler fills hold one element), and doubling from 4 allocates a fifth
  fewer bytes than growing by half from 6 ([benchmarks.md](benchmarks.md) §28).
- **Copies**: `copy`, `concat`, and `fromArray` allocate exactly as many elements as they hold.
- **Shrinking**: When utilization drops to 25% or below (`length * 4 <= capacity`), the backing array shrinks by 50%
  (bounded below by the floor of 4).
- **GC Safety**: Vacated slots on `pop` and `delete` are overwritten to prevent reference leaks. Emptying a vector
  via `clear` resets the backing array to zero elements.

---

### 2.2. `collections/hashMap : collections/HashMap`

Compact, insertion-order preserving polymorphic hash table parameterized over key type `K` and value type `V`.
Uses the Python 3.6+ / PyPy architecture (sparse power-of-two index array with dense parallel arrays)
with secondary perturbation probing and periodic tombstone compaction.

#### Interface Summary

```quest
interface HashMap
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
    word: Word
    iterLib = util/iter : util/Iter
export
    (* The polymorphic hash map type constructor *)
    T::ALL(K::TYPE) ALL(V::TYPE) TYPE

    (* Key-value pair entry *)
    Def Entry = Fun(K::TYPE V::TYPE) Tuple key: K value: V end

    (* Exception raised on lookup failure when using unwrap-style access *)
    error: Exception

    (* Create a new empty hash map with custom equality and hash functions *)
    new: All(K::TYPE V::TYPE)
        All(equal: All(k1: K k2: K) Bool
            hash: All(k: K) word.T)
        T(K V)

    (* Create a new empty hash map using object identity equality and hashing *)
    newIdentityMap: All(K::TYPE V::TYPE) T(K V)

    (* Create a new hash map with preallocated initial capacity *)
    newWithCapacity: All(K::TYPE V::TYPE)
        All(capacity: Int
            equal: All(k1: K k2: K) Bool
            hash: All(k: K) word.T)
        T(K V)

    (* Create a new hash map using object identity with preallocated initial capacity *)
    newIdentityMapWithCapacity: All(K::TYPE V::TYPE) All(capacity: Int) T(K V)

    (* Return the number of active key-value pairs stored in the map *)
    size: All(K::TYPE V::TYPE) All(m: T(K V)) Int

    (* Check if the map is empty *)
    empty: All(K::TYPE V::TYPE) All(m: T(K V)) Bool

    (* Retrieve value associated with key, returning maybe.some(v) or maybe.none *)
    get: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(V)

    (* Check if key exists in the map *)
    contains: All(K::TYPE V::TYPE) All(m: T(K V) key: K) Bool

    (* Retrieve value or raise error if key is not present *)
    find: All(K::TYPE V::TYPE) All(m: T(K V) key: K) V

    (* Insert or overwrite key-value pair. Returns true if key was newly inserted *)
    insert: All(K::TYPE V::TYPE) All(m: T(K V) key: K value: V) Bool

    (* Remove a key and its associated value. Returns maybe.some(v) if found, else none *)
    delete: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(V)

    (* Clear all key-value pairs in the map *)
    clear: All(K::TYPE V::TYPE) All(m: T(K V)) Ok

    (* Return all keys as a vector in insertion order *)
    keys: All(K::TYPE V::TYPE) All(m: T(K V)) vector.T(K)

    (* Return all values as a vector in insertion order *)
    values: All(K::TYPE V::TYPE) All(m: T(K V)) vector.T(V)

    (* Return all entries as a vector of (key, value) tuples in insertion order *)
    entries: All(K::TYPE V::TYPE) All(m: T(K V)) vector.T(Entry(K V))

    (* Iterate over all key-value pairs in insertion order *)
    forEach: All(K::TYPE V::TYPE)
        All(m: T(K V) action: All(k: K v: V) Ok)
        Ok

    (* Transform values in place while preserving keys, equality, and hash table layout *)
    map: All(K::TYPE V::TYPE W::TYPE)
        All(m: T(K V) f: All(k: K v: V) W)
        T(K W)

    (* Retain entries where predicate holds *)
    filter: All(K::TYPE V::TYPE)
        All(m: T(K V) pred: All(k: K v: V) Bool)
        T(K V)

    (* Fold over key-value pairs in insertion order *)
    fold: All(K::TYPE V::TYPE Acc::TYPE)
        All(m: T(K V) init: Acc f: All(acc: Acc k: K v: V) Acc)
        Acc

    (* Combined map and filter on values: retains keys where f returns maybe.some(w) *)
    filterMap: All(K::TYPE V::TYPE W::TYPE)
        All(m: T(K V) f: All(k: K v: V) maybe.T(W))
        T(K W)

    (* Iterators (§1.14), in insertion order, and building from one *)
    entryIter: All(K::TYPE V::TYPE) All(m: T(K V)) iterLib.T(Entry(K V))
    keyIter: All(K::TYPE V::TYPE) All(m: T(K V)) iterLib.T(K)
    valueIter: All(K::TYPE V::TYPE) All(m: T(K V)) iterLib.T(V)
    fromEntries: All(K::TYPE V::TYPE)
        All(it: iterLib.T(Entry(K V)) equal: All(k1: K k2: K) Bool hash: All(k: K) word.T)
        T(K V)
end
```

#### Memory and Growth Strategy

- **Empty maps allocate nothing more**: a map makes its arrays on its first insert, so an empty map is its own tuple
  alone. Most maps stay empty: 89% of the 23 million a build of the compiler makes ([benchmarks.md](benchmarks.md)
  §28).
- **First table**: 8 index slots and 6 dense entries, or, from `newWithCapacity(n ...)`, the smallest power of two of
  index slots that holds `n` entries without growing.
- **Dense arrays**: keys, values, and hashes, each as long as the 2/3 of the index slots they fill before the table
  grows; the deleted flags are allocated on the first `delete`.
- **Growth**: when the dense arrays are full, the table doubles, or is compacted at the same size when more than a
  third of its entries are deleted.

---

### 2.3. `collections/hashSet : collections/HashSet`

Polymorphic hash set parameterized over element type `A`, implemented directly on top of `collections/hashMap(A, Ok)`.
Maintains insertion ordering and provides standard set membership, manipulation, and set algebra operations.

#### Interface Summary

```quest
interface HashSet
import
    collections/vector : collections/Vector
    util/maybe : util/Maybe
    word: Word
    iterLib = util/iter : util/Iter
export
    (* The polymorphic hash set type constructor *)
    T::ALL(A::TYPE) TYPE

    (* Create a new empty hash set with custom equality and hash functions *)
    new: All(A::TYPE)
        All(equal: All(a1: A a2: A) Bool
            hash: All(a: A) word.T)
        T(A)

    (* Create a new empty hash set using object identity equality and hashing *)
    newIdentitySet: All(A::TYPE) T(A)

    (* Create a new hash set with preallocated initial capacity *)
    newWithCapacity: All(A::TYPE)
        All(capacity: Int
            equal: All(a1: A a2: A) Bool
            hash: All(a: A) word.T)
        T(A)

    (* Create a new hash set using object identity with preallocated initial capacity *)
    newIdentitySetWithCapacity: All(A::TYPE) All(capacity: Int) T(A)

    (* Return the number of elements in the set *)
    size: All(A::TYPE) All(s: T(A)) Int

    (* Check if the set is empty *)
    empty: All(A::TYPE) All(s: T(A)) Bool

    (* Check if an element exists in the set *)
    contains: All(A::TYPE) All(s: T(A) elem: A) Bool

    (* Insert an element into the set. Returns true if newly added, false if already present *)
    insert: All(A::TYPE) All(s: T(A) elem: A) Bool

    (* Remove an element from the set. Returns true if element was found and removed *)
    delete: All(A::TYPE) All(s: T(A) elem: A) Bool

    (* Clear all elements from the set *)
    clear: All(A::TYPE) All(s: T(A)) Ok

    (* Return all elements as a vector in insertion order *)
    elements: All(A::TYPE) All(s: T(A)) vector.T(A)

    (* Iterate over all elements in insertion order *)
    forEach: All(A::TYPE)
        All(s: T(A) action: All(elem: A) Ok)
        Ok

    (* Create a shallow copy of the set *)
    copy: All(A::TYPE) All(s: T(A)) T(A)

    (* Return the union of s1 and s2 (elements in s1 or s2) *)
    union: All(A::TYPE) All(s1: T(A) s2: T(A)) T(A)

    (* Return the intersection of s1 and s2 (elements in both s1 and s2) *)
    intersection: All(A::TYPE) All(s1: T(A) s2: T(A)) T(A)

    (* Return the set difference s1 \ s2 (elements in s1 that are not in s2) *)
    difference: All(A::TYPE) All(s1: T(A) s2: T(A)) T(A)

    (* Check if s1 is a subset of s2 (every element in s1 is in s2) *)
    isSubset: All(A::TYPE) All(s1: T(A) s2: T(A)) Bool

    (* Check if s1 and s2 are equal (same size and every element of s1 is in s2) *)
    equal: All(A::TYPE) All(s1: T(A) s2: T(A)) Bool

    (* Retain only elements satisfying the predicate *)
    filter: All(A::TYPE)
        All(s: T(A) pred: All(elem: A) Bool)
        T(A)

    (* Fold over elements in insertion order *)
    fold: All(A::TYPE Acc::TYPE)
        All(s: T(A) init: Acc f: All(acc: Acc elem: A) Acc)
        Acc

    (* Transform elements into a new set with equality and hash functions for B *)
    map: All(A::TYPE B::TYPE)
        All(s: T(A)
            equal: All(b1: B b2: B) Bool
            hash: All(b: B) word.T
            f: All(elem: A) B)
        T(B)

    (* Combined map and filter into a new set with equality and hash functions for B *)
    filterMap: All(A::TYPE B::TYPE)
        All(s: T(A)
            equal: All(b1: B b2: B) Bool
            hash: All(b: B) word.T
            f: All(elem: A) maybe.T(B))
        T(B)

    (* An iterator (§1.14), in insertion order, and building from one *)
    iter: All(A::TYPE) All(s: T(A)) iterLib.T(A)
    fromIter: All(A::TYPE) All(it: iterLib.T(A) equal: All(a1: A a2: A) Bool hash: All(a: A) word.T) T(A)
end
```

### 2.4. `collections/bitset : collections/Bitset`

Fixed-size sets of the integers `0` to `size - 1`, a bit for each, 64 to a `word.T`, written in Quest on `word`'s
operations, with no natives. It is for the dense integer numberings of the native backend's SSA ([arm64.md](arm64.md)
§3.15), where liveness and other dataflow analyses iterate unions to a fixpoint: `unionWith`, `intersectWith`, and
`subtract` change a set in place and say whether they changed it. Bits beyond a set's size are always 0, so whole
words compare, count, and combine without masking. An integer outside a set's range, a negative size, and an
operation on sets of different sizes raise `bitset.error`.

#### Interface Summary

```quest
interface Bitset
import
    word: Word
    iterLib = util/iter : util/Iter
export
    T::TYPE
    error: Exception
    new(size: Int): T
    size(s: T): Int
    contains(s: T i: Int): Bool
    insert(s: T i: Int): Bool           (* whether i was not there *)
    remove(s: T i: Int): Bool           (* whether i was there *)
    clear(s: T): Ok
    count(s: T): Int
    isEmpty(s: T): Bool
    copy(s: T): T
    assign(s: T t: T): Ok
    unionWith(s: T t: T): Bool          (* whether s changed *)
    intersectWith(s: T t: T): Bool
    subtract(s: T t: T): Bool
    equal(s: T t: T): Bool
    isSubset(s: T t: T): Bool
    next(s: T from: Int): Int           (* the least integer of s at least from, or ~1 *)
    elements(s: T): Array(Int)

    (* An iterator (§1.14), in increasing order, and building from one *)
    iter(s: T): iterLib.T(Int)
    fromIter(size: Int it: iterLib.T(Int)): T
end
```

`tests/source/stdlib/bitset_operations.quest` tests it at word boundaries, through every operation and whether it
changes a set, with errors, and in a dataflow fixpoint.

---

### 2.5. `collections/sortedMap : collections/SortedMap`

A map in the order of a comparison given when it is made (~1, 0, or 1, as `sort.intCompare`; keys that compare 0 are
one key): `hashMap`'s operations, plus the least and greatest entries, the nearest on either side of a key, ranges
from `lo` (included) to `hi` (excluded), and a key's rank. Like `hashMap`, it is changed in place, and results that
are many come as a `vector.T`.

It is a B-tree of minimum degree 16 in `collections/btree`, an interface `sortedMap` and `sortedSet` share and
programs do not import, after Cormen, Leiserson, Rivest, and Stein (chapter 18). A node other than the root holds
15 to 31 keys, with their values beside them, in arrays; insertion splits a full node on the way down and deletion
fills a minimal one on the way down, so neither goes back up. Each node counts the keys at and below it, for `rank`.
A B-tree makes logarithmic operations with few allocations and a shallow tree, where a red-black tree would make a
node for every key. Unused slots in a node's arrays hold one of the node's own keys and values, so the tree keeps
nothing alive that it has let go.

The tree counts the keys added and removed. Adding or removing a key while `forEach` (or an iterator) walks the map
raises `error` at the walk's next step, rather than giving an order that depends on the implementation; changing a
value does not. `tests/source/stdlib/sortedmap_operations.quest` inserts 1,200 keys in a random order (three
levels), makes random inserts, deletes, and lookups, then deletes every key in a random order, so that the tree
splits, borrows, and merges at every level, checking each step against a model with the order queries, ranges, and
rank; then the smaller operations, a change during `forEach`, and the errors.

#### Interface Summary

```quest
interface SortedMap
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
    iterLib = util/iter : util/Iter
export
    T::ALL(K::TYPE) ALL(V::TYPE) TYPE
    Def Entry = Fun(K::TYPE V::TYPE) Tuple key: K value: V end
    error: Exception
    new: All(K::TYPE V::TYPE) All(compare: All(a: K b: K) Int) T(K V)
    size: All(K::TYPE V::TYPE) All(m: T(K V)) Int
    empty: All(K::TYPE V::TYPE) All(m: T(K V)) Bool
    get: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(V)
    contains: All(K::TYPE V::TYPE) All(m: T(K V) key: K) Bool
    find: All(K::TYPE V::TYPE) All(m: T(K V) key: K) V
    insert: All(K::TYPE V::TYPE) All(m: T(K V) key: K value: V) Bool
    delete: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(V)
    clear: All(K::TYPE V::TYPE) All(m: T(K V)) Ok
    copy: All(K::TYPE V::TYPE) All(m: T(K V)) T(K V)
    least: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    greatest: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    floor: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(Entry(K V))
    ceiling: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(Entry(K V))
    below: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(Entry(K V))
    above: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(Entry(K V))
    removeLeast: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    removeGreatest: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    keys: All(K::TYPE V::TYPE) All(m: T(K V)) vector.T(K)
    values: All(K::TYPE V::TYPE) All(m: T(K V)) vector.T(V)
    entries: All(K::TYPE V::TYPE) All(m: T(K V)) vector.T(Entry(K V))
    forEach: All(K::TYPE V::TYPE) All(m: T(K V) action: All(k: K v: V) Ok) Ok
    forEachInRange: All(K::TYPE V::TYPE) All(m: T(K V) lo: K hi: K action: All(k: K v: V) Ok) Ok
    entriesInRange: All(K::TYPE V::TYPE) All(m: T(K V) lo: K hi: K) vector.T(Entry(K V))
    rank: All(K::TYPE V::TYPE) All(m: T(K V) key: K) Int
    map: All(K::TYPE V::TYPE W::TYPE) All(m: T(K V) f: All(k: K v: V) W) T(K W)
    filter: All(K::TYPE V::TYPE) All(m: T(K V) pred: All(k: K v: V) Bool) T(K V)

    (* Iterators (§1.14), in key order, raising error if the map changes
     * while one is in use, and building from one *)
    entryIter: All(K::TYPE V::TYPE) All(m: T(K V)) iterLib.T(Entry(K V))
    entryIterFrom: All(K::TYPE V::TYPE) All(m: T(K V) lo: K) iterLib.T(Entry(K V))
    entryIterInRange: All(K::TYPE V::TYPE) All(m: T(K V) lo: K hi: K) iterLib.T(Entry(K V))
    keyIter: All(K::TYPE V::TYPE) All(m: T(K V)) iterLib.T(K)
    valueIter: All(K::TYPE V::TYPE) All(m: T(K V)) iterLib.T(V)
    fromEntries: All(K::TYPE V::TYPE) All(it: iterLib.T(Entry(K V)) compare: All(a: K b: K) Int) T(K V)
end
```

---

### 2.6. `collections/sortedSet : collections/SortedSet`

A set in the order of a comparison, on the same B-tree as `sortedMap`, its values `Ok`: `hashSet`'s operations, with
the order queries, ranges, rank, and change detection of §2.5. `union`, `intersection`, `difference`, and `filter`
each make a new set with the first set's comparison. `tests/source/stdlib/sortedset_operations.quest` tests random
inserts and deletes against a model, the order queries, ranges, and rank, the set operations, and the errors; the
tree itself is tested at depth through `sortedMap`.

#### Interface Summary

```quest
interface SortedSet
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
    iterLib = util/iter : util/Iter
export
    T::ALL(A::TYPE) TYPE
    error: Exception
    new: All(A::TYPE) All(compare: All(a: A b: A) Int) T(A)
    size: All(A::TYPE) All(s: T(A)) Int
    empty: All(A::TYPE) All(s: T(A)) Bool
    contains: All(A::TYPE) All(s: T(A) elem: A) Bool
    insert: All(A::TYPE) All(s: T(A) elem: A) Bool
    delete: All(A::TYPE) All(s: T(A) elem: A) Bool
    clear: All(A::TYPE) All(s: T(A)) Ok
    copy: All(A::TYPE) All(s: T(A)) T(A)
    least: All(A::TYPE) All(s: T(A)) maybe.T(A)
    greatest: All(A::TYPE) All(s: T(A)) maybe.T(A)
    floor: All(A::TYPE) All(s: T(A) elem: A) maybe.T(A)
    ceiling: All(A::TYPE) All(s: T(A) elem: A) maybe.T(A)
    below: All(A::TYPE) All(s: T(A) elem: A) maybe.T(A)
    above: All(A::TYPE) All(s: T(A) elem: A) maybe.T(A)
    removeLeast: All(A::TYPE) All(s: T(A)) maybe.T(A)
    removeGreatest: All(A::TYPE) All(s: T(A)) maybe.T(A)
    elements: All(A::TYPE) All(s: T(A)) vector.T(A)
    forEach: All(A::TYPE) All(s: T(A) action: All(elem: A) Ok) Ok
    forEachInRange: All(A::TYPE) All(s: T(A) lo: A hi: A action: All(elem: A) Ok) Ok
    elementsInRange: All(A::TYPE) All(s: T(A) lo: A hi: A) vector.T(A)
    rank: All(A::TYPE) All(s: T(A) elem: A) Int
    union: All(A::TYPE) All(s1: T(A) s2: T(A)) T(A)
    intersection: All(A::TYPE) All(s1: T(A) s2: T(A)) T(A)
    difference: All(A::TYPE) All(s1: T(A) s2: T(A)) T(A)
    isSubset: All(A::TYPE) All(s1: T(A) s2: T(A)) Bool
    equal: All(A::TYPE) All(s1: T(A) s2: T(A)) Bool
    filter: All(A::TYPE) All(s: T(A) pred: All(elem: A) Bool) T(A)

    (* Iterators (§1.14), in order, raising error if the set changes while
     * one is in use, and building from one *)
    iter: All(A::TYPE) All(s: T(A)) iterLib.T(A)
    iterFrom: All(A::TYPE) All(s: T(A) lo: A) iterLib.T(A)
    iterInRange: All(A::TYPE) All(s: T(A) lo: A hi: A) iterLib.T(A)
    fromIter: All(A::TYPE) All(it: iterLib.T(A) compare: All(a: A b: A) Int) T(A)
end
```

---

### 2.7. `collections/heap : collections/Heap`

A priority queue: a binary heap in a vector, the least element by its comparison first (`sort.reverse` of one, for
the greatest). Element k's children are at 2k + 1 and 2k + 2, and none is less than its parent. `fromVector` (and
`fromIter`) heapify by sifting down from the middle, Floyd's method, in linear time. `pushPop` pushes and pops in one
sift, giving `elem` itself if it is least. Push and pop only: no handles, so no decrease-key. `pop` and `peek` of an
empty heap raise `error`. The register allocator keeps its unhandled intervals in one
(`questlang/codegen/machine/regalloc.mod.quest`). `tests/source/stdlib/heap_operations.quest` heapsorts random vectors,
by pushes and by `fromVector`, against `util/sort`, and tests a greatest-first heap, duplicates, `pushPop`, strings,
and the errors.

#### Interface Summary

```quest
interface Heap
import
    collections/vector : collections/Vector
    iterLib = util/iter : util/Iter
export
    T::ALL(A::TYPE) TYPE
    error: Exception
    new: All(A::TYPE) All(compare: All(a: A b: A) Int) T(A)
    fromVector: All(A::TYPE) All(v: vector.T(A) compare: All(a: A b: A) Int) T(A)
    size: All(A::TYPE) All(h: T(A)) Int
    empty: All(A::TYPE) All(h: T(A)) Bool
    push: All(A::TYPE) All(h: T(A) elem: A) Ok
    pop: All(A::TYPE) All(h: T(A)) A
    peek: All(A::TYPE) All(h: T(A)) A
    pushPop: All(A::TYPE) All(h: T(A) elem: A) A
    clear: All(A::TYPE) All(h: T(A)) Ok
    elements: All(A::TYPE) All(h: T(A)) vector.T(A)

    (* Iterators (§1.14): the elements in heap order, and popped, least
     * first; and building from one *)
    iter: All(A::TYPE) All(h: T(A)) iterLib.T(A)
    drain: All(A::TYPE) All(h: T(A)) iterLib.T(A)
    fromIter: All(A::TYPE) All(it: iterLib.T(A) compare: All(a: A b: A) Int) T(A)
end
```

---

### 2.8. `collections/deque : collections/Deque`

A double-ended queue: a ring buffer in an array, with a head index and a count, its capacity doubled when full (from
at least 8), with pushes and pops at both ends in constant time and its elements indexed from the front. As in
`vector`, a vacated slot is filled with an element still held, so the deque keeps nothing alive that it has let go,
and an emptied deque drops its array. Any change while `forEach` walks the deque, `set` included, raises `error`; a
pop, `front`, or `back` of an empty deque and an index outside 0 to `length - 1` do too.
`tests/source/stdlib/deque_operations.quest` makes random pushes and pops at both ends against a vector model,
through the buffer's wrapping and growth, and tests indexing, conversions, a change during `forEach`, and the errors.

#### Interface Summary

```quest
interface Deque
import
    collections/vector : collections/Vector
    iterLib = util/iter : util/Iter
export
    T::ALL(A::TYPE) TYPE
    error: Exception
    new: All(A::TYPE) T(A)
    newWithCapacity: All(A::TYPE) All(capacity: Int) T(A)
    length: All(A::TYPE) All(d: T(A)) Int
    empty: All(A::TYPE) All(d: T(A)) Bool
    pushFront: All(A::TYPE) All(d: T(A) elem: A) Ok
    pushBack: All(A::TYPE) All(d: T(A) elem: A) Ok
    popFront: All(A::TYPE) All(d: T(A)) A
    popBack: All(A::TYPE) All(d: T(A)) A
    front: All(A::TYPE) All(d: T(A)) A
    back: All(A::TYPE) All(d: T(A)) A
    get: All(A::TYPE) All(d: T(A) index: Int) A
    set: All(A::TYPE) All(d: T(A) index: Int value: A) Ok
    clear: All(A::TYPE) All(d: T(A)) Ok
    copy: All(A::TYPE) All(d: T(A)) T(A)
    forEach: All(A::TYPE) All(d: T(A) action: All(elem: A) Ok) Ok
    toVector: All(A::TYPE) All(d: T(A)) vector.T(A)
    fromVector: All(A::TYPE) All(v: vector.T(A)) T(A)

    (* An iterator (§1.14), front to back, and building from one *)
    iter: All(A::TYPE) All(d: T(A)) iterLib.T(A)
    fromIter: All(A::TYPE) All(it: iterLib.T(A)) T(A)
end
```

### 2.9. `collections/linkedHashMap : collections/LinkedHashMap`

A hash map with an order of its own, as Python's `OrderedDict` and Java's `LinkedHashMap`: keys are kept in the order
they were inserted, and any key can be moved to either end, and the first or last taken off, in constant time.
`hashMap` keeps insertion order too, but cannot reorder a key or take the first off cheaply, since a deleted entry
stays in its dense arrays until a rebuild; this is the map for a least recently used cache (`util/memo`'s bounded
caches), a queue keyed by value, or anything else whose order changes after insertion.

- **Only the operations that say so change the order.** `get`, `find`, and `contains` do not, and inserting a key
  already present changes its value and leaves it in place, as in Python's `OrderedDict`; Java's access order, which
  moves a key on every read, is left to the caller's `moveToEnd`.
- **Representation:** the entries in the first `count` slots of four arrays (keys, values, and the previous and next
  slot in the order), doubled when full (from at least 8), with a `hashMap` from keys to slots. Moving an entry
  relinks it, and nothing is allocated except when the arrays grow. A delete moves the last slot into the deleted
  one's place, so the slots stay dense, and fills the slot left over with an entry still held, so the map keeps
  nothing alive that it has let go; an emptied map drops its arrays. The arrays do not shrink otherwise.
- **The iterators** (§1.14) read the map as it is at each step; what one returns after the map changes other than
  through it is unspecified. `forEach`'s action must not change the map.
- **`first`, `last`, and the pops** give an `Entry`, the same shape as `hashMap.Entry`, or none for an empty map;
  `find` raises `error` for a key not present. `hashMap`'s `map`, `filter`, `fold`, and conversions are left out
  until something wants them.

`tests/source/stdlib/linkedhashmap_operations.quest` tests the order through insertion, reinsertion, both moves, the
pops, and deletes at the front, the back, and in the middle, growth, the iterators, and `find`'s error, and checks a
thousand random operations against a list kept by hand.

#### Interface Summary

```quest
interface LinkedHashMap
import
    util/maybe : util/Maybe
    iterLib = util/iter : util/Iter
    word: Word
export
    T::ALL(K::TYPE) ALL(V::TYPE) TYPE
    Def Entry = Fun(K::TYPE V::TYPE) Tuple key: K value: V end
    error: Exception
    new: All(K::TYPE V::TYPE) All(equal: All(k1: K k2: K) Bool hash: All(k: K) word.T) T(K V)
    size: All(K::TYPE V::TYPE) All(m: T(K V)) Int
    empty: All(K::TYPE V::TYPE) All(m: T(K V)) Bool
    get: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(V)
    contains: All(K::TYPE V::TYPE) All(m: T(K V) key: K) Bool
    find: All(K::TYPE V::TYPE) All(m: T(K V) key: K) V
    insert: All(K::TYPE V::TYPE) All(m: T(K V) key: K value: V) Bool
    delete: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(V)
    clear: All(K::TYPE V::TYPE) All(m: T(K V)) Ok
    moveToEnd: All(K::TYPE V::TYPE) All(m: T(K V) key: K) Bool
    moveToFront: All(K::TYPE V::TYPE) All(m: T(K V) key: K) Bool
    first: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    last: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    popFirst: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    popLast: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    forEach: All(K::TYPE V::TYPE) All(m: T(K V) action: All(k: K v: V) Ok) Ok
    entryIter: All(K::TYPE V::TYPE) All(m: T(K V)) iterLib.T(Entry(K V))
    keyIter: All(K::TYPE V::TYPE) All(m: T(K V)) iterLib.T(K)
    valueIter: All(K::TYPE V::TYPE) All(m: T(K V)) iterLib.T(V)
end
```

---

## 3. Input and Output (`lib/io/`)

### 3.1. `io/readline : io/Readline`

Lines read from the user, edited at a terminal, with a history; both REPLs, the bootstrap's and the self-hosted one,
read their input through it ([repl.md](repl.md) §4). Its externals are
`runtime/quest_readline.c`'s, built with GNU readline when it is installed, else libedit, else neither (lines are then
not edited); `QUEST_READLINE=gnu|edit|none` chooses. The bootstrap's interpreters implement them with Python's
`readline`, and the self-hosted interpreter with the compiled library's own (`questlang/interpreter/builtins`), so a
program interpreted by the self-hosted driver edits lines as a compiled one does.

#### Interface Summary

```quest
interface Readline export
    (* Raised on a system error, such as a history file that cannot be written *)
    error: Exception
    (* Raised by readLine at the end of the input (Ctrl-D on an empty line) *)
    endOfInput: Exception
    (* Raised by readLine when the line is interrupted (Ctrl-C); the line typed so far is discarded *)
    interrupted: Exception

    (* Whether readLine edits lines: standard input and output are terminals, TERM is not empty, dumb, or emacs, and
       the runtime has a line editor *)
    editing(): Bool
    (* Writes prompt and reads a line, without its newline, editing it if editing() is true. Without editing, it reads
       from the same buffer as reader.input, so a program may use both; a last line without a newline is a line *)
    readLine(prompt: String): String

    (* The history, which Up and Down move through when editing. A history file holds a line per entry, whatever the
       line editor, so a line holding a newline is read back as two *)
    addHistory(line: String): Ok
    readHistory(path: String): Ok
    writeHistory(path: String maxLines: Int): Ok
end
```

`readLine` does not add the lines it reads to the history: its caller decides which lines to keep. `readHistory`
does nothing if the file does not exist, and `writeHistory` writes the history's last `maxLines` lines.

#### The Runtime (`runtime/quest_readline.c`)

- **The line editor.** The readline API, which GNU readline and libedit both provide (`<readline/readline.h>`). The
  build detects them (`detect_readline_flags` in `build/compiler_runner.py`, and
  `build/compilerrunner` in `questlang/`): GNU readline where it is installed (Homebrew's `readline`, or the
  system's), compiled `-DQUEST_GNU_READLINE`; else libedit (`-ledit`, part of macOS, and `libedit-dev` on Linux); else
  neither, `-DQUEST_NOREADLINE`, when `editing` is false. The runtime keeps the two libraries' differences (signal
  handling, history truncation) behind that flag. GNU readline is GPL, which binds the programs linked with it; that
  is the user's choice when they install it.
- **Linking.** `quest_readline.c` is compiled and linked with every program, as `quest_serialization.c` is. Linking
  only the programs that import `io/readline` would need the build to know a module's link flags, which it does not;
  libedit is a system library, so linking it always costs little.
- **Editing.** `readLine` uses readline's callback interface, waiting for input with `select`, as CPython's `readline`
  module does. Its `SIGINT` handler, installed only while it reads, sets a flag that ends the wait (the handler has no
  `SA_RESTART`); the line is then abandoned (`rl_free_line_state`, `rl_callback_sigcleanup` for GNU readline,
  `rl_cleanup_after_signal`) and `interrupted` raised. Nothing `longjmp`s out of the library.
- **Without editing,** `readLine` writes the prompt to `writer.output`, flushes it, and reads up to a newline through
  `quest_reader_input`'s buffer. End of input before any byte is `endOfInput`.
- **In a Jupyter kernel's driver** (`QUEST_KERNEL` set, [jupyter-kernel.md](jupyter-kernel.md) §2), `readLine` asks the
  notebook: it writes an `{"input": PROMPT}` record to descriptor 4, the driver's records, and reads the reply from
  descriptor 3, its requests: `L` and the line, or `E` for the end of the input, which a cell run without input allowed
  gets. The C runtime does this, so a program the self-hosted driver interprets asks too; the bootstrap's externals
  don't.
- **The history** is the runtime's own list, mirrored into the line editor's, and its file is plain lines. The line
  editors' own files differ (libedit's starts with a cookie and escapes its lines), and the bootstrap's REPL, whose
  Python may use libedit, shares `~/.quest_history` with compiled REPLs, which may use GNU readline.
- **The bootstrap** implements the externals with Python's `readline` module, and `input()` with standard input read
  as bytes, and keeps a history list of its own, as the C runtime does (Python's automatic history is off, since
  `readLine`'s caller adds lines). Its REPL reads lines and history through these same functions, not through
  `readline` directly, so the two REPLs share one definition of editing, dumb terminals, and the end of input.

`tests/python/test_readline_terminal.py` runs editing, history, Ctrl-C, and Ctrl-D through a pseudo-terminal, for a
program compiled with each line editor installed and interpreted by the bootstrap, and for both REPLs.

### 3.2. `io/display : io/Display`

Values shown as HTML, Markdown, SVG, or images where a notebook shows the program's output (the Quest kernel,
[jupyter-kernel.md](jupyter-kernel.md)), and as text elsewhere. It is Quest alone, with no externals.

#### Interface Summary

```quest
interface Display export
    (* One form of a value: its MIME type, and its data, an image's bytes *)
    Def Item = Tuple mimeType: String data: String end
    (* Whether the program runs in a Jupyter kernel's driver (QUEST_KERNEL is set) *)
    inKernel(): Bool
    (* Shows a value's forms, after what the program has written *)
    bundle(items: Array(Item)): Ok
    html(text: String): Ok
    markdown(text: String): Ok
    svg(text: String): Ok
    png(bytes: String): Ok
end
```

- **In a kernel,** `bundle` flushes standard output and error, then writes `{"display": {MIMETYPE: DATA, ...}}` to
  descriptor 4, the driver's records, which the kernel sends as `display_data`. Its strings are bytes, as the
  driver's are; an image's data (an `image/` type but SVG) is encoded in base64.
- **Elsewhere,** it writes the `text/plain` form and a newline to standard output, or, for a value without one, its
  forms' types (`<application/json>`). `html`, `markdown`, and `svg` give their text as the plain form, and `png` a
  line naming its size.

`tests/source/stdlib/io_display.quest` tests the text; `tests/self-hosted/kernel_protocol.py` the records.

### 3.3. `io/lines : io/Lines`

A reader's lines, one at a time or as an iterator (§1.14). It is Quest alone, over `reader.getChar` and
`util/stringBuilder`, so it runs on every backend unchanged, and it reads nothing past a line's newline: the reader
holds the position, and `getLine` and the iterator mix freely with `reader.getChar`, `getString`, and `more` on one
reader. `Reader` itself is left as it is.

#### Interface Summary

```quest
interface Lines
import
    reader : Reader
    iterLib = util/iter : util/Iter
export
    (* The next line, without its newline; reader.error at end of stream *)
    getLine(rd: reader.T): String
    (* The rest of rd's lines; next raises iterLib.exhausted at the end *)
    iter(rd: reader.T): iterLib.T(String)
end
```

- **A line** ends at `'\n'`, which is not part of it, or at the end of the stream: `"a\nb"` is two lines, `"a\n"`
  one, and `""` none. Only `'\n'` ends a line, so a `'\r'` before it is kept, as `reader` keeps it.
- **Reading them all:** `while reader.more(rd) do ... lines.getLine(rd) ... end`, or
  `vector.fromIter(lines.iter(rd))`; `iterLib.enumerate` numbers them.
- **The iterator holds no line of its own.** Its `more` is `reader.more`, which is idempotent, and its `next` is
  `getLine`. So it is a view of the stream, not of a collection: two iterators over one reader share its position,
  each line going to whichever takes it first, and calling `lines.iter` again walks the rest, not the start. It does
  not close the reader.
- **Speed:** one call of `reader.getChar` per character, with the stream unlocked (benchmarks.md §31).

`tests/source/stdlib/io_lines.quest` tests it, standard input included.

---

## 4. The Operating System (`lib/os/`)

The file system is in four places: `system`, over paths as Strings (`fileExists`, `isFile`, `isDirectory`,
`listDirectory`, `makeDirectory`, `removeFile`, `removeDirectory`, `renameFile`, `currentDirectory`,
`changeDirectory`); `os/fileStats` (§4.2), what `stat(2)` says about a path; `os/files` (§4.6), copying, moving, and
removing trees, walking them, `glob`, temporaries, symlinks, and permissions, over Strings, with failures that say
what and why; and `os/path` (§4.1), paths as values with all of these over them, and reading and writing a file's
text. New code should prefer `os/files` to `system`'s file functions, whose `system.error` says nothing of the
failure. `util/path` (§1.4) has the string operations on
paths, which touch no file.

### 4.1. `os/path : os/Path`

Paths as values of their own type, `path.T`, with the file system operations a program needs over them (Python's
`pathlib.Path`), built on `util/path`'s string functions.

#### Interface Summary

```quest
interface Path
import
    collections/vector : collections/Vector
    util/maybe : util/Maybe
    os/fileStats : os/FileStats
    word : Word
export
    (* Paths as values, normalized as PurePath normalizes them *)
    T::TYPE
    fromString(s: String): T
    toString(p: T): String
    equal(a: T b: T): Bool
    hash(p: T): word.T
    name(p: T): String
    parent(p: T): T
    suffix(p: T): String
    stem(p: T): String
    withSuffix(p: T newSuffix: String): T
    parts(p: T): vector.T(String)
    child(p: T s: String): T
    join(p: T q: T): T
    isAbsolute(p: T): Bool
    normalize(p: T): T
    relativeTo(p: T base: T): T
    resolve(p: T): T

    (* The file system, over T *)
    exists(p: T): Bool
    isFile(p: T): Bool
    isDir(p: T): Bool
    stat(p: T): fileStats.T
    find(p: T): maybe.T(fileStats.T)
    iterDir(p: T): Array(T)
    mkdir(p: T parents: Bool): Ok
    unlink(p: T): Ok
    rename(p: T q: T): Ok
    readText(p: T): String
    writeText(p: T text: String): Ok

    (* os/files (§4.6), over T *)
    copy(p: T q: T): Ok
    copyTree(p: T q: T): Ok
    removeTree(p: T): Ok
    move(p: T q: T): Ok
    walk(p: T visit: All(q: T stats: fileStats.T depth: Int) Bool): Ok
    glob(p: T pattern: String): vector.T(T)
    makeTempDirectory(prefix: String): T
    makeTempFile(prefix: String suffix: String): T
    withTempDirectory(A::TYPE prefix: String action: All(dir: T) A): A
end
```

A `path.T` is the string it was made from, normalized: repeated separators collapse, and `.` components and a trailing
separator drop, so `fromString("./a//b/")` is `a/b`. `..` components stay, as in Python, because cancelling them can
change what a path names when a component is a symlink; `normalize` cancels them lexically. Normalized paths that name
a file the same way are equal strings, so `equal` and `hash` make `path.T` a `hashMap` key. The functions take the
names Python's `Path` gives them; `of`, a keyword, is `fromString`. `withSuffix` and `relativeTo` raise `util/path`'s
`error`. `iterDir` gives a directory's entries sorted by name, and `mkdir` raises `system.error` if the directory
exists, as Python's does without `exist_ok`. A module that needs both modules imports one of them under another name
(`strings = util/path : util/Path`, as `os/path` does).

### 4.2. `os/fileStats : os/FileStats`

What `stat(2)` says about a path, modeled on Python's `os.stat_result` (what `pathlib.Path(...).stat()` returns). One
call gives a path's kind, size, permissions, and times, so a caller that needs to know whether a file exists and when
it changed makes a single system call, with no race between the two questions. Its one external,
`quest_filestats_stat`, is in `runtime/quest_os.c`. The bootstrap's interpreters implement it with `os.stat`
and `os.lstat`, and the self-hosted interpreter with the compiled library's own (`questlang/interpreter/builtins`).

#### Interface Summary

```quest
interface FileStats
import
    util/maybe : util/Maybe
export
    Def Kind = Option file directory symlink other end

    Def T = Tuple
        size: Int
        (* The permission bits (st_mode & 0o7777); the file type is in kind *)
        mode: Int
        kind: Kind
        (* Seconds since the epoch, as Python's st_atime, st_mtime, st_ctime *)
        accessTime: Real
        modifiedTime: Real
        changeTime: Real
        (* Nanoseconds since the epoch, as st_atime_ns, st_mtime_ns, st_ctime_ns *)
        accessNs: Int
        modifiedNs: Int
        changeNs: Int
    end

    (* Following symlinks; raises system.error if the path names nothing *)
    stat(path: String): T
    (* Not following a final symlink *)
    lstat(path: String): T
    (* stat and lstat, but none if the path names nothing *)
    find(path: String): maybe.T(T)
    lfind(path: String): maybe.T(T)
end
```

A path names nothing when `stat(2)` fails with `ENOENT` or `ENOTDIR`, so `find("file.txt/x")` is none. Any other
failure, such as a directory that cannot be searched, raises `system.error` from `find` too. The Real times are
computed as Python computes them (seconds plus nanoseconds times 1e-9), so a compiled program and an interpreted one
agree exactly. Compare the integer times when an exact order matters, as staleness checks do.

### 4.3. `os/process : os/Process`

Programs started without waiting for them, so that a program can run several at once (`system.run` starts one and
waits). Its externals, `quest_process_*`, are in `runtime/quest_os.c`. The bootstrap's interpreters implement
them with `subprocess.Popen`, and the self-hosted interpreter with the compiled library's own
(`questlang/interpreter/builtins`).

#### Interface Summary

```quest
interface Process
export
    T::TYPE
    Def Result = Tuple code: Int stdout: String stderr: String end

    (* Start args[0], found on PATH, without a shell and without waiting; raises system.error if it cannot start *)
    spawn(args: Array(String)): T
    (* spawn, in directory dir *)
    spawnIn(args: Array(String) dir: String): T
    pid(p: T): Int
    (* Whether the child has finished, without waiting *)
    isDone(p: T): Bool
    (* What system.run gives, and the same result each time *)
    wait(p: T): Result
    (* The index of the first of ps to finish; raises system.error if ps is empty *)
    waitAny(ps: Array(T)): Int
    (* Send signal sig to the child, unless it has finished *)
    kill(p: T sig: Int): Ok
end
```

A child's standard output and error go to unlinked temp files, not pipes, so a child never blocks on a full pipe while
its parent is busy elsewhere, and `wait` reads them back once the child has finished. Its standard input and
environment are the parent's. `waitAny` reaps whichever child finishes first (`waitpid(-1)`), so the runtime keeps a
list of the children not yet reaped and records each status on its handle; a child that is not `os/process`'s is
reaped and ignored. A child killed by a signal has that signal's number, negated, as its code, as with `system.run`.

### 4.4. `os/value : os/Value` and `os/code : os/Code`

The JIT's primitives ([jit.md](jit.md) §3.11), behind unsound interfaces, so that only an unsound module may import
them ([modules.md](modules.md) §4.4). Their externals, `quest_value_*` and `quest_code_*`, are in
`runtime/quest_code.c`. Neither interpreter runs them: loading either module is an error, by its name, since the
interpreters have no builtins for them.

`os/value` is Cardelli's `Value` (*Typeful Programming*, appendix), with its signature unchanged:

```quest
unsound interface Value
export
    T::TYPE                              (* an arbitrary value: one word *)
    error: Exception(Ok)                 (* a null address, or one not a multiple of length *)
    length: Int                          (* the size of a T, in bytes: 8 *)
    new(A::TYPE a: A): T                 (* any value as a T *)
    be(A::TYPE v: T): A                  (* a T as a value of any type. Unsound! *)
    fetch(addr: T displ: Int): T         (* the word at addr + displ bytes *)
    store(addr: T displ: Int w: T): Ok   (* store a word at addr + displ bytes. Unsound! *)
end
```

Every slot holds one word, the value's slot representation ([c-representation.md](c-representation.md), "Slots"), so
`new` gives that word and `be` takes it back: a tuple's is a pointer to its components' words, and a record's a
pointer to a box of its payload and its view's offset table (§5.2 there).

`os/code` holds the rest:

```quest
unsound interface Code
import os/value : os/Value  raised : Raised  util/maybe : util/Maybe
export
    Region::TYPE
    (* Zeroed memory for code (executable, MAP_JIT) or data, never freed; raises value.error if it cannot be had *)
    reserve(size: Int executable: Bool): Region
    base(r: Region): value.T
    size(r: Region): Int
    (* Words as 32 or 64 bits from offset bytes, aligned and inside r; the instruction cache is kept coherent *)
    write32(r: Region offset: Int words: Array(Int)): Ok
    write64(r: Region offset: Int words: Array(Int)): Ok
    (* A symbol of the running binary, by its C name (dlsym) *)
    symbol(name: String): maybe.T(value.T)
    (* A function for a thread-local's descriptor that returns the descriptor's second word *)
    threadLocalGetter(): value.T
    (* Call a function of no arguments under a handler that catches everything: none if it returned *)
    call(entry: value.T): maybe.T(raised.T)
    exceptionName(r: raised.T): String
    raiseSite(r: raised.T): String       (* "" if unknown *)
    frames(r: raised.T): String          (* as the runtime prints them for an uncaught exception *)
    addRoots(low: value.T high: value.T): Ok
    addFunction(start: value.T limit: value.T): Ok
    setArgs(args: Array(String)): Ok
end
```

Executable regions are Darwin arm64's: writing toggles `pthread_jit_write_protect_np` for the thread and ends with
`sys_icache_invalidate`. Compiled code reads a thread-local by calling its descriptor's first word with the
descriptor in `x0`, and expects only `x0`, `x16`, and `x17` to change, so `threadLocalGetter` is two instructions of
assembly (`ldr x0, [x0, #8]; ret`). `call` sets a handler record whose resume address is null, so a raise from code
built by either backend jumps to it with `longjmp`. `addFunction` registers code no image describes, which the frame
walk ([exceptions.md](exceptions.md) §5.3) consults before `dladdr`.

---

### 4.5. `os/time : os/Time`

The system's clocks, as `Int`s with their units in their names, since an `Int` carries none: the wall clock, the
monotonic clock (`ticks`, in nanoseconds from an unspecified start), the process's CPU time, sleeping, and the local
time zone's offset from UTC at an instant. The module is only the native calls; a type that keeps the clocks apart
belongs where their readings are used, in `util/datetime` (§1.10), whose epoch is the only one.

- **Two clocks.** The wall clock (what time it is) can jump when the system's time is set; the monotonic clock (how
  long something took) never goes back, and a reading means something only against another in the same run. A
  program that measures subtracts two `ticks()`; one that records or shows a time reads `nowInNanoseconds()`.
- **The local offset at an instant,** not one offset, since it changes twice a year where daylight saving is kept:
  dates on either side of a change each get their own.

Each function is one runtime function:

| External | C | wasm (`runtime/wasm/host.mjs` in node and a page) | Bootstrap |
| :--- | :--- | :--- | :--- |
| `quest_time_now_ns` | `clock_gettime(CLOCK_REALTIME)` | `performance.timeOrigin + performance.now()` | `time.time_ns()` |
| `quest_time_ticks_ns` | `clock_gettime(CLOCK_MONOTONIC)` | `performance.now()` | `time.monotonic_ns()` |
| `quest_time_cpu_ns` | `clock_gettime(CLOCK_PROCESS_CPUTIME_ID)` | `process.cpuUsage()` in node; the monotonic clock in a page | `time.process_time_ns()` |
| `quest_time_sleep_ns` | `nanosleep`, resumed after a signal | `Atomics.wait`, or a wait on the clock in the page's worker | `time.sleep` |
| `quest_time_local_offset` | `localtime_r`'s `tm_gmtoff` at the instant | 0 | `time.localtime(s).tm_gmtoff` |

Under wasm the clocks are WASI's `clock_time_get` and `poll_oneoff`, which wasmtime has and the host gives node and
the page. WASI has no time zone, so the local offset is 0 (a host function of its own would not link in wasmtime); a
page has no CPU clock per process, so it reports the monotonic one; and `Atomics.wait` needs a `SharedArrayBuffer`,
which a page has only when cross-origin isolated (GitHub Pages' is not), so there a sleep waits on the clock. A page's
clock has a resolution of a few microseconds, or coarser where the browser reduces it. A sleep of 0 or less returns
at once. The self-hosted interpreter's builtins call the library, as for `os/fileStats`; the JIT uses the C runtime.

The readings cannot be goldens, so `tests/source/stdlib/os_time.quest` tests their properties: `ticks()` never goes
back, a 50 ms sleep lasts at least 50 ms, CPU time grows under work, the wall clock is a time of this century that
keeps pace with the monotonic one, and the local offset is less than a day.

```quest
interface Time
export
    nowInNanoseconds(): Int                          (* since 1970-01-01T00:00:00Z *)
    ticks(): Int                                     (* nanoseconds, never going back *)
    cpuTimeInNanoseconds(): Int
    sleepNanoseconds(nanoseconds: Int): Ok
    localOffsetInSeconds(secondsSinceEpoch: Int): Int (* seconds east of UTC *)
end
```

### 4.6. `os/files : os/Files`

File-system operations over Strings, as in `system` and `os/fileStats`: copying, moving, and removing files and trees;
walking a tree and finding files by a shell pattern; temporary files and directories; symlinks, permissions, and
times. A failure raises `files.error` with a `Failure`: the operation, the path that failed, a `Code` from the short
list of errors a program acts on, and a message, the same text on every target. Symlinks are never followed when
changing anything: `removeTree` removes a symlink, `walk` shows one without entering it, and `copyTree` makes one
anew with the same target.

```quest
interface Files
import
    collections/vector : collections/Vector
    os/fileStats : os/FileStats
export
    Def Code = Option
        notFound exists notDirectory isDirectory notEmpty permission crossDevice unsupported other
    end
    Def Failure = Tuple operation: String path: String code: Code message: String end
    error: Exception(Failure)

    (* One system call each *)
    remove(path: String): Ok                          (* unlink *)
    removeDirectory(path: String): Ok                 (* rmdir *)
    rename(from: String to: String): Ok
    makeDirectory(path: String mode: Int): Ok
    createNew(path: String mode: Int): Ok             (* O_CREAT | O_EXCL *)
    list(path: String): vector.T(String)              (* sorted, without . and .. *)
    symlink(target: String path: String): Ok
    readLink(path: String): String
    setMode(path: String mode: Int): Ok               (* chmod; unsupported under wasm *)
    setTimes(path: String accessNs: Int modifiedNs: Int): Ok

    (* Built on them, in Quest *)
    realPath(path: String): String
    makeDirectories(path: String): Ok                 (* mkdir -p *)
    copy(from: String to: String): Ok                 (* content and permission bits *)
    copyTree(from: String to: String): Ok
    removeTree(path: String): Ok
    move(from: String to: String): Ok                 (* rename, or copy and remove across devices *)
    Def Entry = Tuple path: String stats: fileStats.T depth: Int end
    walk(root: String visit: All(e: Entry) Bool): Ok  (* pre-order, names sorted *)
    allFiles(root: String): vector.T(String)
    glob(pattern: String): vector.T(String)
    globIn(root: String pattern: String): vector.T(String)

    (* Temporaries *)
    tempDirectory(): String                           (* TMPDIR, or /tmp *)
    makeTempDirectory(prefix: String): String         (* mode 0o700 *)
    makeTempFile(prefix: String suffix: String): String (* mode 0o600 *)
    withTempDirectory(A::TYPE prefix: String action: All(dir: String) A): A
end
```

**Primitives and failures.** The module has two layers, as os/time and util/datetime do, but in one module, because the
Quest layer is small and copying a file should take one import. The primitives are ten private runtime functions, one
system call each, for the operations listed as such; everything else, `realPath` included, is Quest over them and
`os/fileStats`, so only the primitives need each target's runtime and the rest behaves alike everywhere. A primitive
returns 0 for success or a negative status: −1 to −8 for `notFound` through `unsupported`, in `Code`'s order, and
−(1000 + errno) for `other`. `list` and `readLink` return their value (empty on failure) and keep the status for an
eleventh function, `quest_files_last_status`, so that no primitive returns a tuple, which C would need a layout for.
The module turns a status into `error` with a `Failure` it builds, so C never constructs an exception with a payload,
and the messages are one table in Quest: `strerror`'s text for the eight named codes, and "Error *n*" naming the errno
for `other`. The codes are the errors a program acts on, so that `removeTree` of a missing directory can be told apart
from one it may not enter; `system.error` has no payload. `files` has its own `remove`, `removeDirectory`, `rename`,
`makeDirectory`, and `list` so that they raise `files.error`; `system`'s stay for the programs that use them. A failed
`rename` names `from` if it is missing, else `to`.

**Targets.** In C (`runtime/quest_os.c`) the primitives are `unlink`, `rmdir`, `rename`, `mkdir`,
`open(O_CREAT | O_EXCL)` then `close`, `opendir`/`readdir`, `symlink`, `readlink`, `chmod`, and `utimensat`, each
mapping `errno` as above. Under wasm they are WASI's `path_*` calls (`runtime/wasm/core.mod.quest`, with `path_symlink`,
`path_readlink`, and `path_filestat_set_times` in `questlang/wasm/runtime.mod.quest`'s imports and
`runtime/wasm/host.mjs`), whose errno numbers `core` maps to the same statuses. WASI preview 1 has symlinks and times
but no permission bits, so `setMode` is `unsupported` and `copy` and `copyTree` keep no mode. Under node, `setTimes`
goes through `fs.utimesSync`, which takes seconds as a Number, so it is exact to the microsecond. The browser page's
in-memory mount has neither symlinks nor times (`symlink` and `setTimes` are `unsupported`) and starts with a `/tmp`
(`tools/wasm-page/page.mjs`), so the temporaries work there. The bootstrap interpreter's builtins give the same
statuses from Python's `os`, and the self-hosted interpreter calls the externals through
`questlang/interpreter/fileCalls`, since `os/files` keeps them private.

**Behavior.** Symlinks are never followed when changing anything, as `cp -R`, `cp -a`, and
`shutil.copytree(symlinks=True)` behave; the path a caller names is followed where reading it is the point.

- `realPath` resolves one component at a time with `lfind`, putting a symlink's target in its place (from `/` for an
  absolute one) and taking `..` off what is resolved, and gives up with `other` after 40 symlinks, as `ELOOP`. Being
  Quest, it needs no `realpath` under WASI, which has none.
- `makeDirectories` makes each missing component with mode 0o777 before the umask; a component that exists must be a
  directory, or it raises `exists`.
- `copy` follows `from`, refuses a directory with `isDirectory`, and refuses `from` and `to` naming the same file (the
  same `realPath`) with `exists`, as `cp` does, rather than truncating the source. It reads with `reader.file` and
  writes with `writer.file` in 64 KiB pieces (byte-exact, since strings are bytes), so a file of any size copies in
  bounded memory, then sets `to`'s permission bits to `from`'s. Like `shutil.copy`, it copies no times or ownership.
- `copyTree` raises `exists` if anything is at `to`. It follows `from`, then copies by `lstat`: directories made,
  files copied, symlinks made anew with the same target. A directory's mode is set after its contents are copied, so a
  read-only directory copies.
- `removeTree` raises `notFound` if nothing is at `path`; it removes a directory's entries and then the directory, and
  anything else with `remove`. A failure partway raises with the path that failed and leaves the rest, as `rm -r`
  does.
- `move` is `rename` when that succeeds. On `crossDevice` it copies (`copyTree`, a new symlink, or `copy`) and then
  removes the source, so a failure leaves the source whole.
- `walk` follows `root`, then uses `lstat` below it, so a symlink's `kind` is `symlink` and it is not entered. It visits
  in pre-order with names sorted; `visit`'s `false` skips a directory's contents, and an entry gone between `list` and
  `lstat` is skipped, not raised. It builds nothing, so a large tree costs memory in proportion to its depth.
  `allFiles` is the paths of `walk`'s regular files, in its order.
- `glob` takes the pattern a component at a time and lists only the directories the components can reach. A component
  with no `*`, `?`, or `[` is a name, looked up with `lfind` rather than listed; any other is matched against `list` of
  the directory with util/path's `matches` (§1.4), which passes over names that start with `.` unless the pattern's
  component does, and reads an unclosed `[` as a literal, so no pattern is an error. `**` as a whole component is the
  directory itself and every directory under it whose name does not start with `.`; it starts only from a directory
  (`x/**` matches nothing for a file `x`), steps only into directories that are not symlinks, and matches a symlink only
  as the last component, so nothing is reached through a symlink, as with `pathlib`'s glob (Python's `glob.glob` goes
  through one). A pattern ending in `/` matches directories only, each given with its `/`. A directory that cannot be
  listed is skipped. Results are sorted as strings with duplicates removed; an absolute pattern gives absolute paths,
  a relative one paths relative to the current directory. `globIn`'s pattern must be relative (else `other`), and its
  results are relative to `root`. There is no brace expansion (`{a,b}`); two calls do the same.
- A temporary's name is the prefix, 10 characters from `[a-z0-9]` (about 51 bits, from a `util/random.fromClock()`
  generator the module keeps), and the suffix, in `tempDirectory()`: `TMPDIR` if set and not empty, else `/tmp`. It is
  created exclusively, with `mkdir` (mode 0o700) or `O_CREAT | O_EXCL` (0o600), as `mkdtemp` and `mkstemp` do, and a
  new name is tried on `exists`, up to 100 times; any other failure raises at once. Doing this in Quest needs no
  `mkstemp` external, which WASI has no counterpart for. `withTempDirectory` removes its directory with `removeTree`
  whether its action returns or raises, and re-raises what the action raised.

**Tests.** `tests/source/stdlib/os_files.quest`, a golden test, runs in a directory from `makeTempDirectory` and
prints paths relative to it, so its output is the same on every run and in every mode, wasmtime and node included. It
covers each primitive and each `Code` a program can provoke (`notFound`, `exists`, `notEmpty`, `notDirectory`,
`isDirectory`); `copy` of an empty file, of a 200 KB file of every byte value, and onto itself; `copyTree`, `walk` (its
order, a skipped directory, a symlink not entered), `allFiles`, `move`, and `removeTree` on a tree with nested, empty,
and hidden directories, a hidden file, and a symlink; `glob` and `globIn` with each construct, `**` at the start,
middle, and end, a trailing `/`, a symlinked directory under `**`, and a pattern that matches nothing; and the
temporaries. It asks `setMode` once, and under wasm the lines about modes hold without setting any.
`tests/python/test_files.py` compiles `tests/files/globber.quest` and compares its `walk` and `glob` with
`os.listdir` in pre-order and `glob.glob(recursive=True)`, on seeded random trees of a few hundred entries without
symlinks (where the two globs differ). `tests/source/stdlib/path_operations.quest` tests `matches`, and
`tests/repl/temporary_files.quest` uses `withTempDirectory` and `globIn` in the REPL, natively, under node, and in the
page.

**Left out**, until a program needs them: `appendText`, a writer that appends to a file, which `writer.file` cannot
make, since it truncates; hard links (`link`); and a native `copy` (`copyfile`, `copy_file_range`) in place of the
Quest loop, which could replace it without changing the interface if large copies prove slow.

