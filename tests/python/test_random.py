"""util/random's known answers against reference implementations
(docs/libraries.md section 1.11): xoshiro256** (Blackman and Vigna's
xoshiro256starstar.c), seeded by SplitMix64 (Vigna's splitmix64.c), with
Lemire's bounded integers. tests/source/stdlib/random_operations.quest prints
the first numbers from several seeds into its golden; this test computes them
here and compares, so the golden cannot drift from the algorithms."""

import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
GOLDEN = ROOT_DIR / "tests" / "golden" / "run" / "stdlib" / "random_operations.out"
MASK = 2**64 - 1
GOLDEN_GAMMA = 0x9E3779B97F4A7C15


def splitmix(x: int) -> int:
    """splitmix64's output for the counter x after its step"""
    z = (x + GOLDEN_GAMMA) & MASK
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
    return z ^ (z >> 31)


def rotl(x: int, k: int) -> int:
    return ((x << k) | (x >> (64 - k))) & MASK


class Xoshiro:
    def __init__(self, seed: int):
        s = seed & MASK
        self.s = [splitmix((s + i * GOLDEN_GAMMA) & MASK) for i in range(4)]

    def next(self) -> int:
        s = self.s
        result = (rotl((s[1] * 5) & MASK, 7) * 9) & MASK
        t = (s[1] << 17) & MASK
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = rotl(s[3], 45)
        return result

    def below_word(self, n: int) -> int:
        """Lemire's method: the high word of x * n, rejecting low words below
        2^64 mod n"""
        x = self.next()
        m = x * n
        if (m & MASK) < n:
            threshold = (2**64 - n) % n
            while (m & MASK) < threshold:
                x = self.next()
                m = x * n
        return m >> 64

    def between(self, lo: int, hi: int) -> int:
        span = (hi - lo + 1) & MASK
        if span == 0:
            return signed(self.next())
        return signed((lo + self.below_word(span)) & MASK)


def signed(w: int) -> int:
    return w - 2**64 if w >= 2**63 else w


def quest(n: int) -> str:
    """n as Quest writes an Int, with ~ for a negative"""
    return f"~{-n}" if n < 0 else str(n)


class RandomTest(unittest.TestCase):

    def lines(self) -> dict[str, str]:
        found = {}
        for line in GOLDEN.read_text().split("\n"):
            head, _, rest = line.partition(":")
            found[head] = rest.strip()
        return found

    def test_xoshiro_reference(self):
        # xoshiro256** from the state {1, 2, 3, 4}: rotl(2 * 5, 7) * 9
        x = Xoshiro(0)
        x.s = [1, 2, 3, 4]
        self.assertEqual(x.next(), 11520)

    def test_seeds(self):
        found = self.lines()
        for seed in (0, 1, 1989, -1, 2**63 - 1):
            x = Xoshiro(seed)
            want = " ".join(quest(signed(x.next())) for _ in range(6))
            self.assertEqual(found[f"seed {quest(seed)}"], want)

    def test_bounded(self):
        found = self.lines()
        x = Xoshiro(42)
        bounds = (1, 2, 3, 6, 7, 10, 100, 1000000007, 4611686018427387904, 9223372036854775807)
        self.assertEqual(found["below 42"], " ".join(quest(x.below_word(n)) for n in bounds))
        y = Xoshiro(7)
        want = [y.between(-5, 5), y.between(0, 0), y.between(-2**63, 2**63 - 1), y.between(2**63 - 2, 2**63 - 1)]
        self.assertEqual(found["between 7"], " ".join(quest(v) for v in want))


if __name__ == "__main__":
    unittest.main()
