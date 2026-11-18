# Plan: Time, `os/time` and `util/datetime`

Clocks, durations, sleeping, and calendar dates for Quest, the first of [future-libraries.md](future-libraries.md)'s
"clearly missing" libraries. Quest has no clock today: util/regexp's benchmark times whole processes from Python
for lack of one. Built 2026-11-18 (§6).

## 1. Decisions

1. **Two modules** (user, 2026-11-17). `os/time` is what needs native code and nothing else: the clocks, sleeping,
   and the local time zone's offset. `util/datetime` is everything built on them, in Quest: durations, instants,
   calendar dates, and their text. Only `os/time` needs each target's runtime; `util/datetime` runs alike everywhere.
2. **`os/time` returns `Int`s, with the unit in the name** (user, 2026-11-17): `nowInNanoseconds()`,
   `cpuTimeInNanoseconds()`, `localOffsetInSeconds(...)`, so that a reading's unit is never in doubt where it is
   used. `ticks()` is the monotonic clock's reading, in nanoseconds from an unspecified start.
3. **Two clocks.** The wall clock (what time it is, `nowInNanoseconds`) can jump when the system's time is set; the
   monotonic clock (how long something took, `ticks`) never does. A program that measures subtracts two `ticks()`;
   one that records or shows a time reads `nowInNanoseconds()`. `util/datetime` keeps them apart by type: its
   `Instant` comes from the wall clock only.
4. **Durations are `Int` nanoseconds** in `util/datetime` too, the transparent type `Duration`, so that they add,
   subtract, and compare with Quest's own operators (`2 * datetime.second`), which no opaque type could; 64 bits of
   nanoseconds span 292 years either way. A `ticks()` difference is a `Duration` as it is.
5. **POSIX time:** a day is 86,400 seconds and leap seconds do not exist, as for `clock_gettime`, Python, and Go.
6. **The calendar is computed in Quest,** the proleptic Gregorian calendar by Howard Hinnant's days-from-civil
   algorithms, the same on every target.
7. **No time-zone database.** A date is in UTC, in the system's local zone (its offset at that instant, from
   `os/time`), or at an offset given in seconds. Named zones (`America/Los_Angeles`) and their rules need data that
   changes yearly, and are a library of their own if ever wanted.
8. **Text is `strftime`'s directives,** a fixed subset, done in Quest in the C locale (English names), not by
   calling `strftime`, so that every target writes the same text.
9. **Settled with the user (2026-11-17):** `os/time`'s wall clock is `nowInNanoseconds()`, with no separate epoch
   function (the epoch is `util/datetime`'s constant); `util/datetime`'s `Instant` is opaque; in a browser page,
   which has no CPU clock per process, `cpuTimeInNanoseconds()` returns the monotonic clock, as documented; and the
   interface is `util/DateTime` (the file `lib/util/datetime.*`, lowercase).
10. **Modeled on SML's Basis** (`Time`, `Timer`, `Date`, as util/bignum follows `IntInf`) where it fits, and on Go's
   `time` for the split between wall and monotonic readings.

## 2. `os/time : os/Time`

```quest
interface Time
export
    (* =========================================================================
     * The System's Clocks (Time)
     *
     * The readings and waits that need the operating system, as Ints in the
     * units their names give; util/datetime builds durations, instants, and
     * dates on them. The wall clock can jump when the system's time is set,
     * so a program that measures how long something takes subtracts two
     * ticks() instead:
     *
     *     let started = time.ticks()
     *     work()
     *     let took = time.ticks() - started   (* nanoseconds *)
     * ====================================================================== *)

    (* The wall clock: nanoseconds since the Unix epoch, 1970-01-01T00:00:00Z
     * (POSIX time, without leap seconds) *)
    nowInNanoseconds(): Int

    (* The monotonic clock: nanoseconds from an unspecified start, never
     * going back, meaningful only against another reading in the same run *)
    ticks(): Int

    (* The CPU time this process has used, user and system, in nanoseconds;
     * the wall clock's ticks where there is none (a browser) *)
    cpuTimeInNanoseconds(): Int

    (* Waits at least nanoseconds; returns at once for nanoseconds <= 0 *)
    sleepNanoseconds(nanoseconds: Int): Ok

    (* The local time zone's offset from UTC, in seconds east, at the instant
     * secondsSinceEpoch seconds after the epoch: what it was, or will be,
     * then, daylight saving included; 0 where there is no local zone (WASI) *)
    localOffsetInSeconds(secondsSinceEpoch: Int): Int
end
```

Why this shape:
- **Ints throughout,** so that the module is only the native calls, each its runtime's function and nothing more; a
  type that keeps the clocks apart belongs where the readings are used, in `util/datetime`.
- **Units in the names,** since an `Int` carries none. `ticks` is the exception, being a count of the monotonic
  clock's own ticks, which are nanoseconds on every target.
- **The local offset at an instant,** not "the local offset", since it changes twice a year where daylight saving
  is kept: dates on either side of a change each get their own.

## 3. `util/datetime : util/DateTime`

```quest
interface DateTime
import
    util/maybe : util/Maybe
export
    (* Raised for an argument out of range: a date that does not exist (the
     * 30th of February), an offset of more than a day, an instant outside
     * what nanoseconds since 1970 can hold, or a pattern with an unknown
     * directive *)
    error: Exception

    (* ---- Durations: nanoseconds, used with Int's operators *)

    Def Duration = Int
    nanosecond: Duration
    microsecond: Duration
    millisecond: Duration
    second: Duration
    minute: Duration
    hour: Duration
    (* d in seconds, and seconds as the nearest duration *)
    seconds(d: Duration): Real
    fromSeconds(s: Real): Duration
    (* d written as Go writes durations: "1h2m3.5s", "250ms", "0s" *)
    durationString(d: Duration): String
    (* How long since a reading of os/time's ticks() *)
    elapsedSince(ticks: Int): Duration
    (* Waits at least d *)
    sleep(d: Duration): Ok

    (* ---- Instants: the wall clock's readings *)

    (* An instant: nanoseconds since the Unix epoch, from 1677 to 2262 *)
    Instant::TYPE
    now(): Instant
    epoch: Instant
    (* From and to nanoseconds since the epoch (os/time's nowInNanoseconds,
     * os/fileStats's modifiedNs) *)
    fromNanoseconds(ns: Int): Instant
    toNanoseconds(i: Instant): Int
    (* An instant d after i (before, for a negative d); raises error outside
     * the range *)
    add(i: Instant d: Duration): Instant
    (* How long after b a is (negative if before) *)
    diff(a: Instant b: Instant): Duration
    compare(a: Instant b: Instant): Int
    before(a: Instant b: Instant): Bool

    (* ---- Calendar dates *)

    (* A date and time of day, at offset seconds east of UTC: month 1 to 12,
     * day 1 to 31, hour 0 to 23, minute and second 0 to 59, nanosecond 0 to
     * 999,999,999 *)
    Def Date = Tuple
        year: Int
        month: Int
        day: Int
        hour: Int
        minute: Int
        second: Int
        nanosecond: Int
        offset: Int
    end
    (* i's date in UTC, in the local zone (its offset at i), and at offset *)
    utc(i: Instant): Date
    local(i: Instant): Date
    atOffset(i: Instant offset: Int): Date
    (* The instant d names, d's fields checked; raises error for a date that
     * does not exist *)
    instant(d: Date): Instant
    (* 0 for Sunday to 6 for Saturday; 1 to 366 *)
    weekday(d: Date): Int
    yearDay(d: Date): Int
    isLeapYear(year: Int): Bool
    daysInMonth(year: Int month: Int): Int

    (* ---- Text *)

    (* d written by pattern's directives: %Y year, %m %d %H %M %S two
     * digits, %f nanoseconds (nine digits), %j day of year, %y two-digit
     * year, %I %p 12-hour clock, %a %A %b %B English names, %z offset
     * (+hhmm), %e day padded with a space, %u %w weekday numbers, %% a %;
     * raises error for any other *)
    format(d: Date pattern: String): String
    (* The date s is in pattern, as format writes it, if it is one *)
    parse(s: String pattern: String): maybe.T(Date)
    (* i as RFC 3339 in UTC: 2026-11-17T21:37:41Z, with a fraction when i has
     * one (2026-11-17T21:37:41.250Z); and such text read back, with Z or an
     * offset (+08:00), if it is one *)
    iso8601(i: Instant): String
    parseIso8601(s: String): maybe.T(Instant)
end
```

Typical use:

```quest
import time = os/time : os/Time;
import datetime = util/datetime : util/DateTime;
let started = time.ticks();
work();
print("took " <> datetime.durationString(datetime.elapsedSince(started)));
print("at " <> datetime.format(datetime.local(datetime.now()) "%Y-%m-%d %H:%M:%S %z"));
datetime.sleep(250 * datetime.millisecond);
```

Why this shape:
- **`Duration` transparent, `Instant` opaque:** durations are what programs compute with, and instants what they
  must not confuse with them or with `ticks()` readings. An instant's arithmetic (`add`, `diff`) is a few functions,
  used far less often.
- **`Date` a plain tuple,** not opaque: programs build them (`instant(tuple let year = 2026 ... end)`) and read their
  fields, as `fileStats.T`'s. Weekday and day of year are functions, not fields, so that a date a program builds
  cannot have an inconsistent one.
- **`local` takes the offset at that instant,** from `os/time`, and `instant` of a date uses the date's own `offset`,
  so a local date converts back exactly.
- **`elapsedSince` and `sleep`** are `os/time`'s readings and waits as durations, so that a program that only
  measures need import `os/time` for no more than `ticks()`.

## 4. Implementation

**`os/time`'s five externals,** each one runtime function:

| External | C | wasm host | Bootstrap |
| :--- | :--- | :--- | :--- |
| `quest_time_now_ns` | `clock_gettime(CLOCK_REALTIME)` | `performance.timeOrigin + performance.now()` | `time.time_ns()` |
| `quest_time_ticks_ns` | `clock_gettime(CLOCK_MONOTONIC)` | `performance.now()` | `time.monotonic_ns()` |
| `quest_time_cpu_ns` | `clock_gettime(CLOCK_PROCESS_CPUTIME_ID)` | `process.cpuUsage()` in node; the wall clock's ticks in a page, which has none | `time.process_time_ns()` |
| `quest_time_sleep_ns` | `nanosleep`, resumed after a signal | `Atomics.wait` on a buffer of its own, in node and in a page's worker | `time.sleep` |
| `quest_time_local_offset` | `localtime_r`'s `tm_gmtoff` at the instant | 0: WASI has no time zone, and a host function would not link in wasmtime | `time.localtime(s).tm_gmtoff` |

Under wasm the clocks are WASI's own (`clock_time_get`, and `poll_oneoff` for sleeping), which wasmtime has and
`runtime/wasm/host.mjs` gives node and the page. A page's sleep waits on the clock in its worker where it has no
`SharedArrayBuffer`, which a page has only when cross-origin isolated, as GitHub Pages' is not.

The self-hosted interpreter's builtins call the library, as for `os/fileStats`; the JIT uses the C runtime. New
externals change the compiler's externals table (`tools/externals`), so the change bumps the ABI version. A page's
clock has a few microseconds' resolution, or coarser where the browser reduces it.

**`util/datetime`, in Quest:** durations and their text; instants as nanoseconds, with range checks; Hinnant's
`days_from_civil` and `civil_from_days` for dates; `format`, `parse`, and RFC 3339 as small scanners over the
directives. It imports `os/time` for `now`, `elapsedSince`, `sleep`, and `local` alone.

## 5. Tests

- **`os/time`'s readings** cannot be goldens, so its test checks their properties: `ticks()` never goes back,
  `sleepNanoseconds(50,000,000)` takes at least 50 ms by `ticks()`, `cpuTimeInNanoseconds()` grows under work, the
  wall clock is within a second of the bootstrap's or the system's, and the local offset is within a day.
- **`util/datetime`'s goldens** show what is fixed: known instants and their dates in UTC and at offsets, the round
  trip `instant(utc(i))` is `i`, leap years and month lengths, every directive of `format` and `parse`, RFC 3339 both
  ways, durations' text, and every error.
- **A unit test against Python's `datetime`** (`tests/python/`), as util/regexp's corpus is checked against Go:
  random instants over the whole range, their dates, weekdays, and days of the year, and `format` against
  `strftime` for the directives both have.
- **Every target:** the goldens in both compilers' phases and the backends' modes, and `os/time`'s test under wasm
  in node and in the page.

## 6. Steps

1. **`os/time`:** the five externals in each target, the ABI bump, and its test. util/regexp's benchmark can then
   time itself.
2. **`util/datetime`'s durations and instants,** and its calendar dates: `utc`, `atOffset`, `instant`, weekdays,
   leap years, and `local`.
3. **`util/datetime`'s text:** `format`, `parse`, RFC 3339, and the comparison with Python.

*Built 2026-11-18,* the three steps in one change, at ABI 85: `lib/os/time.*` and `lib/util/datetime.*`, the five
externals in the C runtime, both interpreters' builtins, and the wasm runtime (with WASI's `clock_time_get` and
`poll_oneoff` added to its imports, and to `runtime/wasm/host.mjs` for node and the page), the externals table, the
ABI corpora with `os/time`'s interface snapshotted, and libraries.md §1.10 and §4.5. `tests/source/stdlib/os_time.quest`
and `datetime_operations.quest` pass in every phase of both compilers and in the arm64, ssac, JIT, wasm, wasm-node,
and wasm-jit modes, and `tests/python/test_datetime.py` agrees with Python's `datetime` on 20,058 instants. Since
the self-hosted interpreter's builtins import `os/time`, `questlang/` builds only from the bootstrap
(`QUEST_SEED=bootstrap`) until a release has it (docs/release-compiler.md §2).
