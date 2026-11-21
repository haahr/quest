"""util/datetime's calendar against Python's datetime (docs/libraries.md
section 1.10), as tests/python/test_regexp.py checks util/regexp against Go.

tests/datetime/calendar.quest, compiled once with ./quest, writes for random
instants over the whole range (1677 to 2262) at random offsets the date by
format's directives that strftime has too, its nanosecond, the instant in RFC
3339, and whether parse and parseIso8601 read them back; this test computes the
same with datetime and compares every line.
"""

import random
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CALENDAR = ROOT_DIR / "tests" / "datetime" / "calendar.quest"
PATTERN = "%Y-%m-%d %H:%M:%S %j %y %I %p %a %A %b %B %z %e %u %w %%"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def expected(ns: int, offset: int) -> str:
    """The line calendar.quest should write for an instant and an offset"""
    seconds, nanosecond = divmod(ns, 10**9)
    instant = EPOCH + timedelta(seconds=seconds)
    there = instant.astimezone(timezone(timedelta(seconds=offset)))
    fraction = f".{nanosecond:09d}".rstrip("0") if nanosecond else ""
    iso = instant.strftime("%Y-%m-%dT%H:%M:%S") + fraction + "Z"
    return f"{there.strftime(PATTERN)}|{nanosecond}|{iso}|true|true"


def cases(count: int):
    rng = random.Random(1989)
    special = [0, -1, 1, 2**63 - 1, -2**63, 951782400 * 10**9, 951868800 * 10**9, -2208988800 * 10**9]
    for ns in special:
        yield ns, 0
    for _ in range(count):
        # an offset of whole minutes, as strftime's %z writes only those
        yield rng.randrange(-2**63, 2**63), 60 * rng.randrange(-1439, 1440)
    # instants near the range's ends, at offsets that keep their dates in it
    for _ in range(50):
        yield 2**63 - 1 - rng.randrange(10**15), -60 * rng.randrange(1440)
        yield -2**63 + rng.randrange(10**15), 60 * rng.randrange(1440)


class DateTimeTest(unittest.TestCase):

    def test_against_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "calendar"
            built = subprocess.run([str(ROOT_DIR / "quest"), "--build-dir", str(Path(tmp) / "build"), "-o",
                                    str(harness), str(CALENDAR)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            chosen = list(cases(20000))
            path = Path(tmp) / "cases.txt"
            path.write_text("".join(f"{ns} {offset}\n" for ns, offset in chosen))
            done = subprocess.run([str(harness), str(path)], capture_output=True, text=True, timeout=600)
            self.assertEqual(done.returncode, 0, done.stderr)
            have = done.stdout.split("\n")[:-1]
            self.assertEqual(len(have), len(chosen))
            wrong = [f"{ns} {offset}: have {h!r}, want {expected(ns, offset)!r}"
                     for (ns, offset), h in zip(chosen, have) if h != expected(ns, offset)]
            self.assertEqual(wrong, [], "\n".join(wrong[:20]))


if __name__ == "__main__":
    unittest.main()
