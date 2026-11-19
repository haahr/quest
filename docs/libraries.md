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
syntax and the design are [regexp-plan.md](regexp-plan.md)'s (§2–§4); its implementation is three modules the
interface does not name, `util/regexpSyntax` (the parser), `util/regexpProgram` (the compiler, as Go's
`regexp/syntax` compiles), and `util/regexpMatch` (a Pike VM). `tests/source/stdlib/regexp_*.quest` test it, and
`tests/python/test_regexp.py` checks it against RE2's corpora and Go's `regexp`.

#### Interface Summary

```quest
interface Regexp
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
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

Durations, instants, calendar dates, and their text, in Quest, on `os/time`'s clocks (§4.5,
[time-plan.md](time-plan.md)): the proleptic Gregorian calendar, POSIX time (no leap seconds), and time zones by
their offset from UTC alone, with no zone database. A duration is `Int` nanoseconds, used with `Int`'s operators; an
instant is opaque, nanoseconds since the epoch (1677 to 2262), so that it is not mistaken for a duration or a
`ticks()` reading. `tests/source/stdlib/datetime_operations.quest` tests it, and `tests/python/test_datetime.py`
checks its dates and text against Python's `datetime` on 20,000 random instants.

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

Pseudo-random numbers in Quest ([collections-plan.md](collections-plan.md) §2.5): xoshiro256**, seeded by SplitMix64,
so the same seed gives the same numbers on every target. `new(seed)` is deterministic, for tests and benchmarks;
`fromClock()` seeds from `os/time` (§4.5) for different numbers each run; there is no hidden shared generator.
Bounded integers are unbiased, by Lemire's method. Not for cryptography. `tests/source/stdlib/random_operations.quest`
tests it, and `tests/python/test_random.py` recomputes its known answers with a reference implementation.

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

---

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

## 2. Collections (`lib/collections/`)

### 2.1. `collections/vector : collections/Vector`

Growable, dynamically-resizing array collection parameterized over element type `A`.

#### Interface Summary

```quest
interface Vector
import
    util/maybe : util/Maybe
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
export
    (* The polymorphic hash map type constructor *)
    T::ALL(K::TYPE) ALL(V::TYPE) TYPE

    (* Key-value pair entry *)
    Def Entry = Fun(K::TYPE V::TYPE) Record key: K value: V end

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

    (* Return all entries as a vector of (key, value) records in insertion order *)
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
end
```

`tests/source/stdlib/bitset_operations.quest` tests it at word boundaries, through every operation and whether it
changes a set, with errors, and in a dataflow fixpoint.

---

### 2.5. `collections/sortedMap : collections/SortedMap`

A map in the order of a comparison given when it is made ([collections-plan.md](collections-plan.md) §2.1): `hashMap`'s
operations, plus the least and greatest entries, the nearest on either side of a key, ranges from `lo` (included) to
`hi` (excluded), and a key's rank. It is a B-tree of minimum degree 16, `collections/btree`, which counts the keys
below each node. Adding or removing a key while `forEach` walks the map raises `error`; changing a value does not.
`tests/source/stdlib/sortedmap_operations.quest` grows a map to three levels and empties it against a model.

#### Interface Summary

```quest
interface SortedMap
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
export
    T::ALL(K::TYPE) ALL(V::TYPE) TYPE
    Def Entry = Fun(K::TYPE V::TYPE) Record key: K value: V end
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
end
```

---

### 2.6. `collections/sortedSet : collections/SortedSet`

A set in the order of a comparison ([collections-plan.md](collections-plan.md) §2.2), on the same B-tree as
`sortedMap`: `hashSet`'s operations, with the order queries, ranges, and rank of §2.5.

#### Interface Summary

```quest
interface SortedSet
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
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
end
```

---

### 2.7. `collections/heap : collections/Heap`

A priority queue ([collections-plan.md](collections-plan.md) §2.3): a binary heap in a vector, the least element by its
comparison first (`sort.reverse` of one, for the greatest), built from a vector in linear time. Push and pop only: no
handles, so no decrease-key.

#### Interface Summary

```quest
interface Heap
import
    collections/vector : collections/Vector
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
end
```

---

### 2.8. `collections/deque : collections/Deque`

A double-ended queue ([collections-plan.md](collections-plan.md) §2.4): a ring buffer, its capacity doubled when full,
with pushes and pops at both ends in constant time and its elements indexed from the front.

#### Interface Summary

```quest
interface Deque
import
    collections/vector : collections/Vector
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

The system's clocks, as `Int`s with their units in their names ([time-plan.md](time-plan.md) §2): the wall clock,
the monotonic clock (`ticks`, for measuring, since the wall clock can jump), the process's CPU time, sleeping, and
the local time zone's offset from UTC at an instant. Each is one runtime function: `clock_gettime`, `nanosleep`, and
`localtime_r` in C; WASI's `clock_time_get` and `poll_oneoff` under wasm, where the local offset is 0 (WASI has no
time zone) and a page, which has no CPU clock, reports the monotonic one. `util/datetime` (§1.10) builds on it, and
`tests/source/stdlib/os_time.quest` tests the clocks by their properties.

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

File-system operations over Strings ([files-plan.md](files-plan.md)): copying, moving, and removing files and trees;
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

The primitives are ten runtime functions, each giving 0 or a negative status that the module turns into `error`: in
C, `unlink`, `rmdir`, `rename`, `mkdir`, `open`, `opendir`, `symlink`, `readlink`, `chmod`, and `utimensat`; under
wasm, WASI's `path_*` calls, where there are no permission bits, so `setMode` is `unsupported` and `copy` keeps no
mode. Everything else is Quest. `copy` reads and writes 64 KB at a time, so a file of any size copies in bounded
memory. `glob` follows Python's `glob.glob(recursive=True)`: `**` as a whole component is zero or more directories,
wildcards pass over names that start with `.`, a pattern ending in `/` matches directories only, and results are
sorted; unlike Python's, `**` never goes through a symlink, as `pathlib`'s does not. Temporary names are the prefix
and ten random letters and digits, made with `mkdir` or an exclusive create, and tried again if taken.
`withTempDirectory` removes its directory whether its action returns or raises. `tests/source/stdlib/os_files.quest`
runs alike in every mode, wasmtime and node included, and `tests/python/test_files.py` checks `walk` and `glob`
against Python's on random trees.

