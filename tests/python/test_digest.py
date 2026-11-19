"""util/digest's known answers against hashlib and zlib (docs/libraries.md
section 1.12). tests/source/stdlib/digest_operations.quest prints the SHA-256 and
CRC-32 of its messages into its golden; this test computes them here and
compares, so the golden cannot drift from the algorithms."""

import hashlib
import unittest
import zlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
GOLDEN = ROOT_DIR / "tests" / "golden" / "run" / "stdlib" / "digest_operations.out"
ALL_BYTES = bytes(i % 256 for i in range(512))
LENGTHS = (1, 55, 56, 57, 63, 64, 65, 119, 120, 127, 128, 1000)


class DigestTest(unittest.TestCase):

    def lines(self) -> dict[str, str]:
        found = {}
        for line in GOLDEN.read_text().split("\n"):
            head, _, rest = line.partition(": ")
            found[head] = rest
        return found

    def test_sha256(self):
        found = self.lines()
        messages = {
            "empty": b"",
            "abc": b"abc",
            "fips56": b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            "bytes": ALL_BYTES,
        }
        messages.update({f"a*{n}": b"a" * n for n in LENGTHS})
        for name, message in messages.items():
            self.assertEqual(found[f"sha256 {name}"], hashlib.sha256(message).hexdigest(), name)

    def test_crc32(self):
        found = self.lines()
        messages = {"empty": b"", "check": b"123456789", "bytes": ALL_BYTES, "a*1000": b"a" * 1000}
        for name, message in messages.items():
            self.assertEqual(found[f"crc32 {name}"], str(zlib.crc32(message)), name)

    def test_hex(self):
        self.assertEqual(self.lines()["hex"], ALL_BYTES[250:260].hex() + " ()")


if __name__ == "__main__":
    unittest.main()
