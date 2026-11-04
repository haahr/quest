"""Generates tests/source/stdlib/bignum_operations.quest, the test of util/bignum
(lib/util/bignum), and the output Python's integers say it must print.

The program prints each value in full with its one-operand results; for each
two-operand operation and each of a subset of the values as first operand, a
hash of its results with each of the subset as second operand (h * 31 + r,
modulo 2^64, in bignum arithmetic), so that the output stays small; parses of
strings; and products of a few large values, with a hash of each product's
decimal string and of its quotients and remainders. The golden comes from the
bootstrap's interpreter, as every run golden does; the expected output checks
it.

    # Regenerate the program, and compare the golden with Python's output:
    python tests/bignum/generate.py /tmp/bignum.expected
    python run_tests.py -k bignum_operations --suite golden --update-golden
    diff tests/golden/run/stdlib/bignum_operations.out /tmp/bignum.expected
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROGRAM = ROOT / "tests" / "source" / "stdlib" / "bignum_operations.quest"
M64 = (1 << 64) - 1

rng = random.Random(20261103)
values = [0, 1, -1, 2, -2, 10, -7, (1 << 63) - 1, -(1 << 63), 1 << 63, -(1 << 63) - 1, M64, 1 << 64, -(1 << 64),
          (1 << 64) + 1, 1 << 127, -(1 << 127), (1 << 128) - 1, -(1 << 128) + 1, (1 << 191) - 12345]
for limbs in [1, 2, 2, 3, 4, 5, 6]:
    v = rng.getrandbits(64 * limbs - rng.randrange(0, 40))
    values.append(-v if rng.random() < 0.5 else v)
# A divisor whose quotient estimates need the add-back step (Knuth's test case shape)
values.append((1 << 128) - (1 << 64) + 3)
values.append(((1 << 192) - 1) // 3)
# The values the two-operand table pairs: the limits of one and two limbs, a few
# random values, and the divisor that needs the add-back
PAIRED = [0, 1, 2, 6, 7, 8, 9, 10, 11, 12, 15, 21, 24, 26, 27]


def q(n):
    """Quest's decimal for n."""
    return str(n).replace("-", "~")


def h(strings):
    """The Quest program's hash of a list of strings: h * 31 + char, wrapping in 64 bits."""
    x = 0
    for s in strings:
        for c in s:
            x = (x * 31 + ord(c)) & M64
        x = (x * 31 + 10) & M64
    return x - (1 << 64) if x >> 63 else x


# The result that stands for divide raised
DIVIDE = -999


def mix(rs):
    """The program's hash of results: h * 31 + r, modulo 2^64."""
    x = 0
    for r in rs:
        x = (x * 31 + r) & M64
    return x


def tquot(a, b):
    """a quot b: truncating division."""
    r = abs(a) // abs(b)
    return r if (a < 0) == (b < 0) else -r


def binary_ops():
    return [
        ("add", lambda a, b: a + b),
        ("sub", lambda a, b: a - b),
        ("mul", lambda a, b: a * b),
        ("quot", lambda a, b: DIVIDE if b == 0 else tquot(a, b)),
        ("rem", lambda a, b: DIVIDE if b == 0 else a - b * tquot(a, b)),
        ("div", lambda a, b: DIVIDE if b == 0 else a // b),
        ("mod", lambda a, b: DIVIDE if b == 0 else a % b),
        ("compare", lambda a, b: (a > b) - (a < b)),
        ("equal", lambda a, b: int(a == b)),
        ("gcd", lambda a, b: math.gcd(a, b)),
        ("andBits", lambda a, b: a & b),
        ("orBits", lambda a, b: a | b),
        ("xorBits", lambda a, b: a ^ b),
    ]


def unary(v):
    out = [q(v), q(-v), q(abs(v)), q((v > 0) - (v < 0)), q(~v)]
    out.append(q(v) if -(1 << 63) <= v < (1 << 63) else "overflow")
    out.append(q(v) if 0 <= v <= M64 else "overflow")
    for k in [0, 1, 63, 64, 65, 130]:
        out.append(q(v << k))
        out.append(q(v >> k))
    for n in [0, 1, 2, 3]:
        out.append(q(v ** n))
    out.append(pow_neg(v))
    return out


def pow_neg(v):
    if v == 0:
        return "divide"
    if v == 1:
        return "1"
    if v == -1:
        return q(-1)
    return "0"


def expected():
    lines = []
    for v in values:
        lines.extend(unary(v))
    for name, f in binary_ops():
        for a in [values[i] for i in PAIRED]:
            lines.append(name + " " + q(mix([f(a, values[j]) for j in PAIRED])))
    # Strings
    for s, v in [("  +123", "123"), ("-5", q(-5)), ("~0", "0"), ("abc", "none"), ("12abc", "12"), ("", "none"),
                 ("-", "none"), ("00000000000000000000000000042", "42"),
                 ("-340282366920938463463374607431768211456", q(-(1 << 128)))]:
        lines.append(v)
    # Large values: products, and their quotients by the factors, as hashes
    big = [rng.getrandbits(64 * n) * (-1 if n % 2 else 1) for n in (40, 25, 17)]
    for a in big:
        for b in big:
            p = a * b
            lines.append(q(h([q(p)])) + " " + q(mix([tquot(p, b), p - b * tquot(p, b), (p + 12345) // b,
                                                      (p + 12345) % b])))
    return lines, big


def program(big):
    vs = "\n".join(f'    "{q(v)}"' for v in values)
    bs = "\n".join(f'    "{q(v)}"' for v in big)
    names = [n for n, _ in binary_ops()]
    calls = {
        "add": "bignum.add(a b)",
        "sub": "bignum.sub(a b)",
        "mul": "bignum.mul(a b)",
        "quot": "dividing(fun(): bignum.T bignum.quot(a b))",
        "rem": "dividing(fun(): bignum.T bignum.rem(a b))",
        "div": "dividing(fun(): bignum.T bignum.div(a b))",
        "mod": "dividing(fun(): bignum.T bignum.mod(a b))",
        "compare": "bignum.fromInt(bignum.compare(a b))",
        "equal": "bignum.fromInt(if bignum.equal(a b) then 1 else 0 end)",
        "gcd": "bignum.gcd(a b)",
        "andBits": "bignum.andBits(a b)",
        "orBits": "bignum.orBits(a b)",
        "xorBits": "bignum.xorBits(a b)",
    }
    ops = "\n".join(f'    {"if" if i == 0 else "elsif"} stringOp.equal(name "{n}") then {calls[n]}'
                    for i, n in enumerate(names)) + '\n    else bignum.fromInt(0) end'
    return f'''(* Standard library: util/bignum, against Python's integers:
 * each value in full with its one-operand results, then for each two-operand
 * operation and each first operand of a subset a hash of its results with
 * each of the subset as second, parses of strings, and products and
 * quotients of a few large values. Generated by tests/bignum/generate.py,
 * which also writes the output Python's integers give. *)
(* @timeout: 120.0 *)

import util/bignum : util/Bignum;
import util/maybe : util/Maybe;
import stringOp = string : StringOp;
import ascii : Ascii;
import conv : Conv;
import writer : Writer;

let show(s: String): Ok =
    begin
        writer.putString(writer.output s)
        writer.putString(writer.output "\\n")
    end;

let parse(s: String): bignum.T = maybe.unwrap(:bignum.T bignum.fromString(s));

(* The program's hash of strings, each followed by a newline *)
let hashOf(h: Int s: String): Int =
    begin
        let var x = h
        for i = 0 upto stringOp.length(s) - 1 do x := {{x * 31}} + ascii.val(stringOp.getChar(s i)) end
        {{x * 31}} + 10
    end;

let guarded(f: All() String): String = try f() when bignum.divide then "divide" end;

(* f's result, or ~999 for divide *)
let dividing(f: All() bignum.T): bignum.T = try f() when bignum.divide then bignum.fromInt(~999) end;

(* h * 31 + r, modulo 2^64 *)
let mask = maybe.unwrap(:bignum.T bignum.fromString("18446744073709551615"));
let thirtyOne = bignum.fromInt(31);
let mix(h: bignum.T r: bignum.T): bignum.T = bignum.andBits(bignum.add(bignum.mul(h thirtyOne) r) mask);

let values = array of
{vs}
end;
let ts = array of(extent values parse("0"));
for i = 0 upto extent values - 1 do ts[i] := parse(values[i]) end;
let paired = array of {" ".join(str(i) for i in PAIRED)} end;

for i = 0 upto extent ts - 1 do
    let t = ts[i]
    show(bignum.toString(t))
    show(bignum.toString(bignum.neg(t)))
    show(bignum.toString(bignum.abs(t)))
    show(conv.int(bignum.sign(t)))
    show(bignum.toString(bignum.notBits(t)))
    show(try conv.int(bignum.toInt(t)) when bignum.overflow then "overflow" end)
    show(try bignum.toString(bignum.fromWord(bignum.toWord(t))) when bignum.overflow then "overflow" end)
    let shifts = array of 0 1 63 64 65 130 end
    for k = 0 upto extent shifts - 1 do
        show(bignum.toString(bignum.shiftLeft(t shifts[k])))
        show(bignum.toString(bignum.shiftRight(t shifts[k])))
    end
    for n = 0 upto 3 do show(bignum.toString(bignum.pow(t n))) end
    show(guarded(fun(): String bignum.toString(bignum.pow(t ~1))))
end;

let names = array of {" ".join(f'"{n}"' for n in names)} end;
let result(name: String a: bignum.T b: bignum.T): bignum.T =
{ops};
for k = 0 upto extent names - 1 do
    for i = 0 upto extent paired - 1 do
        let var h = bignum.fromInt(0)
        for j = 0 upto extent paired - 1 do h := mix(h result(names[k] ts[paired[i]] ts[paired[j]])) end
        show(names[k] <> " " <> bignum.toString(h))
    end
end;

let strings = array of "  +123" "-5" "~0" "abc" "12abc" "" "-" "00000000000000000000000000042"
    "-340282366920938463463374607431768211456" end;
for i = 0 upto extent strings - 1 do
    let m = bignum.fromString(strings[i])
    show(if maybe.isSome(:bignum.T m) then bignum.toString(maybe.unwrap(:bignum.T m)) else "none" end)
end;

let big = array of
{bs}
end;
let offset = bignum.fromInt(12345);
for i = 0 upto extent big - 1 do
    for j = 0 upto extent big - 1 do
        let a = parse(big[i])
        let b = parse(big[j])
        let p = bignum.mul(a b)
        let var h = mix(bignum.fromInt(0) bignum.quot(p b))
        h := mix(h bignum.rem(p b))
        h := mix(h bignum.div(bignum.add(p offset) b))
        h := mix(h bignum.mod(bignum.add(p offset) b))
        show(conv.int(hashOf(0 bignum.toString(p))) <> " " <> bignum.toString(h))
    end
end;
'''


def main() -> None:
    lines, big = expected()
    PROGRAM.write_text(program(big))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
