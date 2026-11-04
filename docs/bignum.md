# Plan: Arbitrary-Precision Integers in the Library

A library module, `util/bignum`, of integers of any size, written in Quest on 64-bit limbs, with one new primitive in
the word module, and the MLton suite's two programs that use big integers moved to it from the suite's own
`support/intinf`.

## 1. Why

pidigits and smith-normal-form take 43 and 190 times MLton's time, through every backend alike
([benchmarks.md](benchmarks.md) §3.7, §13): their time is in `benchmarks/mlton/support/intinf`, a library written
for the conversions, in base 10^9 limbs held in arrays of `Int`, sign and magnitude, every result a new array and
trimmed by another copy. MLton's `IntInf` is GMP, on 64-bit limbs, and keeps values that fit in a word out of GMP,
so most of smith-normal-form's arithmetic never reaches it. The library's loops are already tight (§3.7); the gap is
the representation and the limb size. Quest has no big integers of its own, so a library module serves programs as
well as the suite.

## 2. Representation

```
Let T = Array(word.T)
```

A value is its two's complement representation in base 2^64, little-endian: element 0 is the least significant
limb. Every limb but the last is unsigned; the last is signed, and gives the value its sign. `word.toInt` and
`word.fromInt` convert the last limb between `word.T` and `Int`; both compile to nothing (the SSA takes each as its
operand, `ssa/build/calls` `inlineExternal`).

- **T is abstract.** The interface exports `T::TYPE`, so that no client can write to a value's array; the module
  never writes to an array once it is returned.
- **Canonical length.** A value is never empty, zero is `[0]`, and the last limb is never a redundant sign
  extension: a last limb of 0 follows a limb whose high bit is set, and one of `~1` (all ones) a limb whose high bit
  is clear. Every value has exactly one representation, so:
  - every `Int` is exactly a one-limb array, and a one-limb array is an `Int`: `toInt` is the limb or `overflow`,
    and the fast path of every operation is `extent a is 1 andif extent b is 1`;
  - `equal` compares lengths, then limbs;
  - `compare` compares lengths and signs, then the last limbs as signed, then the rest as unsigned from the top.
- **Shorter operands** are read past their end as their sign extension, 0 or `~1` by their last limb's sign, so
  `add` and `sub` of different lengths need no copy of the shorter.

A small value costs one 16-byte array (length and limb) for each result, where the suite's library allocates a tuple
and an array, and MLton nothing. A one-word tagged representation would remove that, but needs
`os/value`, which neither interpreter runs, and a collector that knows the tag ([collector.md](collector.md)); it is
not part of this plan.

## 3. Operations

The module is `lib/util/bignum`, imported as `util/bignum : util/Bignum`. Its interface is the suite's `IntInf`
(`support/intinf.int.quest`), with words, shifts, powers, greatest common divisors, and bitwise operations on the
two's complement values (decided 2026-11-03), all written in Quest:

| Operation | Small (both one limb) | Large |
|---|---|---|
| `add`, `sub` | `Int` arithmetic; overflow from the operands' and the result's signs | Limbwise with a carry, `word.lt(sum, a)` |
| `mul` | `Int` product; fits when the signed high word is the low word's sign | Schoolbook with `word.mul` and `word.mulHi` |
| `quot`, `rem`, `div`, `mod` | `Int` division, but `int.minInt / ~1` | Knuth's algorithm D on magnitudes |
| `neg`, `abs` | `Int`, but `int.minInt` | Limbwise negation |
| `equal`, `less`, `compare` | `Int` | §2 |
| `toString`, `fromString` | `conv` | Chunks of 19 decimal digits, by 10^19 |
| `fromInt`, `toInt` | The limb | `overflow` |
| `fromWord`, `toWord` | The limb, if not negative, else `overflow` | Two limbs, the last 0, else `overflow` |
| `andBits`, `orBits`, `xorBits`, `notBits` | `word`'s | Limbwise, the shorter sign-extended (§2) |
| `shiftLeft`, `shiftRight` (arithmetic) | `Int` shift, if it fits | Whole limbs, then a bit shift across limbs |
| `pow` (`Int` exponent) | | Repeated squaring |
| `gcd` | Euclid on `Int` | Euclid by division (Lehmer's if a program needs it) |

- **Signed high words.** `word.mulHi` is unsigned; the signed high word of `a * b` is `mulHi(a b)`, less `b` if `a`
  is negative and less `a` if `b` is.
- **Multiplication** treats both arrays as unsigned and corrects the product as the signed high word above does: less
  `b` shifted by `extent a` limbs if `a` is negative, less `a` shifted by `extent b` if `b` is. Karatsuba is left
  until a program's sizes call for it.
- **Division** works on magnitudes: a negative operand is negated into scratch space, and the quotient and remainder
  negated after, `div` and `mod` adjusted from `quot` and `rem` by the signs. A one-limb divisor divides each limb
  by a precomputed reciprocal (Möller and Granlund, *Improved division by invariant integers*, 2011), which needs
  only `mul`, `mulHi`, `add`, and `lt`; algorithm D normalizes the divisor with `word.countLeadingZeros` and takes
  each quotient limb by the same step.
- **Result lengths.** An array cannot shrink, so a result made longer than its canonical length is copied:
  - `add` and `sub` make `max(la lb)` limbs, and copy into one more only when the last limb overflows, or into
    fewer when cancellation leaves redundant limbs;
  - `mul` and division compute in a scratch array the module owns and grows, and copy the result at its length (an
    O(n) copy of O(n^2) work). The scratch array is the module's state, which is safe while Quest programs run on one
    thread.

## 4. Primitives

**`word.mulHi(w1: T w2: T): T`**, the high 64 bits of the unsigned 128-bit product, is the one the library needs:

- the runtime's inline helper in `runtime/quest_runtime.h`, `(uint64_t)(((unsigned __int128)w1 * w2) >> 64)`;
- an SSA opcode, `opMulHiU`, which `inlineExternal` makes of the call, ssac prints as the C above, and arm64 selects
  as `umulh` (and so the JIT);
- both interpreters' builtins;
- `tools/externals`'s table, and with it a new ABI version.

Two more would help, each measured before it is kept:

- **`word.zeros(n: Int): Array(T)`**, an array of n zero words allocated with `quest_alloc_atomic`: without it every
  result is filled by a loop when it is made, and scanned by the collector, to which a limb that looks like a heap
  address keeps memory alive.
- **`word.copy(from: Array(T) start: Int to: Array(T) at: Int n: Int): Ok`**, a `memmove` of limbs, for §3's copies,
  which are otherwise loops with a bounds check a limb.

Not needed: an add with carry (the SSA would have to carry flags; `lt` costs one instruction a limb), a 128-by-64
division (arm64 has none, and C's `__udivti3` is slower than the reciprocal), and a signed `mulHi` (§3).

## 5. Steps

1. **`word.mulHi`** (§4) through C, ssac, arm64, the JIT, and both interpreters, with `tests/source/stdlib/
   word_operations.quest` extended, and a new ABI version.
2. **`util/bignum`** (§2, §3), with a test in `tests/source/stdlib/` whose expected output is computed by Python's
   integers: every operation over values at the limb boundaries (0, ±1, ±2^63, ±2^64, `int.minInt`, `int.maxInt`,
   and their neighbors) and pseudo-random values of 1 to 40 limbs.
3. **The suite:** pidigits and smith-normal-form import `util/bignum` (their algorithms unchanged: the originals call
   SML's own `IntInf`), `support/intinf` is deleted, and both are timed through C, ssac, and arm64 against §13, in a
   new section of [benchmarks.md](benchmarks.md).
4. **`word.zeros` and `word.copy`**, each kept if it moves step 3's times.

Then this plan's design moves into a reference document (the library's interface comment and
[c-representation.md](c-representation.md) §3.4), and this file is deleted.
