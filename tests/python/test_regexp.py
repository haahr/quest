"""util/regexp against the corpora and against Go's regexp
(docs/regexp-plan.md section 5, tests/data/regexp/README.md).

tests/regexp/corpus.quest, compiled once with ./quest, checks a file of cases,
each a pattern and a subject with the expected match of the whole subject and
of a search, both leftmost-first. The cases come from:

- RE2's search tests (re2-search.txt), with their recorded answers;
- the AT&T POSIX tests' patterns and subjects, answered by Go's regexp
  (tests/regexp/oracle.go), since the files record POSIX leftmost-longest
  answers;
- random patterns and subjects, answered by Go's regexp, for the match of the
  whole subject and of a search, and for findAll, split, and replaceAll;
- patterns that would take a backtracking matcher exponential time, which must
  finish quickly.

The cases that need Go are skipped where it is not installed. RE2's exhaustive
tests run only with QUEST_REGEXP_EXHAUSTIVE=1.
"""

import bz2
import os
import random
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA = ROOT_DIR / "tests" / "data" / "regexp"
CORPUS = ROOT_DIR / "tests" / "regexp" / "corpus.quest"
ORACLE = ROOT_DIR / "tests" / "regexp" / "oracle.go"

GO = shutil.which("go")


def go_unquote(text: str) -> bytes:
    """A Go double-quoted string literal's bytes"""
    assert text[0] == '"' and text[-1] == '"', text
    body, out, i = text[1:-1], bytearray(), 0
    simple = {"a": 7, "b": 8, "f": 12, "n": 10, "r": 13, "t": 9, "v": 11, "\\": 92, '"': 34, "'": 39}
    while i < len(body):
        c = body[i]
        if c != "\\":
            out += c.encode()
            i += 1
            continue
        e = body[i + 1]
        if e in simple:
            out.append(simple[e])
            i += 2
        elif e == "x":
            out.append(int(body[i + 2:i + 4], 16))
            i += 4
        elif e in "uU":
            width = 4 if e == "u" else 8
            out += chr(int(body[i + 2:i + 2 + width], 16)).encode()
            i += 2 + width
        elif e in "01234567":
            out.append(int(body[i + 1:i + 4], 8))
            i += 4
        else:
            raise ValueError(f"unknown escape in {text}")
    return bytes(out)


def hexed(b: bytes) -> str:
    return b.hex() if b else "-"


def re2_result(field: str) -> str:
    """An RE2 corpus result, "-" or space-separated lo-hi pairs (- for a group
    that took no part), in the cases' format"""
    return "-" if field == "-" else ",".join(field.split(" "))


def skipped(pattern: bytes, subject: bytes) -> bool:
    """Whether a case is one this library is not meant to agree on
    (tests/data/regexp/README.md)"""
    if any(b > 127 for b in pattern + subject):
        return True
    return any(x in pattern for x in (b"\\p", b"\\P", b"\\C"))


def re2_cases(lines):
    """(pattern, subject, full, partial) for each case of an RE2 corpus file"""
    strings, i = [], 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if line == "strings":
            strings = []
            while lines[i] != "regexps":
                strings.append(go_unquote(lines[i]))
                i += 1
            i += 1
        elif line.startswith('"'):
            pattern = go_unquote(line)
            for subject in strings:
                results = lines[i].split(";")
                i += 1
                yield pattern, subject, re2_result(results[0]), re2_result(results[1])


def att_cases():
    """(pattern, subject) for each extended-syntax case of the AT&T files, as Go's
    exec_test.go reads them"""
    for name in ("basic.dat", "nullsubexpr.dat", "repetition.dat"):
        last = ""
        for line in (DATA / name).read_text(encoding="latin-1").split("\n"):
            if not line or line[0] == "#":
                continue
            fields = [f for f in line.split("\t") if f]
            if any(f == "NIL" for f in fields) or len(fields) < 4:
                continue
            fields = ["" if f == "NULL" else f for f in fields]
            flag = fields[0]
            if flag[0] in "?&|;{}":
                flag = flag[1:]
            elif flag[0] == ":":
                continue
            if not flag or flag[0] in "CNT0123456789" or "E" not in flag:
                continue
            pattern, subject = fields[1], fields[2]
            if "$" in flag:
                pattern = go_unquote('"' + pattern + '"').decode("latin-1")
                subject = go_unquote('"' + subject + '"').decode("latin-1")
            if pattern == "SAME":
                pattern = last
            last = pattern
            if "i" in flag:
                pattern = "(?i)" + pattern
            yield pattern.encode("latin-1"), subject.encode("latin-1")


def random_pattern(rng: random.Random, depth: int) -> str:
    """A random pattern over a and b, in the syntax both this library and Go's
    have"""
    if depth == 0 or rng.random() < 0.3:
        return rng.choice(["a", "b", ".", "[ab]", "[^a]", "\\w", "^", "$", "\\b", "\\B", "", "(?i)A"])
    kind = rng.randrange(6)
    x = random_pattern(rng, depth - 1)
    if kind == 0:
        return x + random_pattern(rng, depth - 1)
    if kind == 1:
        return x + "|" + random_pattern(rng, depth - 1)
    if kind == 2:
        return "(" + x + ")"
    if kind == 3:
        return "(?:" + x + ")"
    if kind == 4:
        lo = rng.randrange(3)
        return "(?:" + x + ")" + rng.choice(["*", "+", "?", f"{{{lo}}}", f"{{{lo},}}", f"{{{lo},{lo + 2}}}"]) \
            + rng.choice(["", "?"])
    return "(" + x + ")" + rng.choice(["*", "+", "?"])


def random_cases(count: int):
    rng = random.Random(1989)
    for _ in range(count):
        pattern = random_pattern(rng, 4).encode()
        for _ in range(4):
            yield pattern, "".join(rng.choice("abc") for _ in range(rng.randrange(8))).encode()


class RegexpTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        cls.harness = tmp / "corpus"
        built = subprocess.run([str(ROOT_DIR / "quest"), "--build-dir", str(tmp / "build"), "-o", str(cls.harness),
                                str(CORPUS)], capture_output=True, text=True)
        if built.returncode != 0:
            raise RuntimeError(f"corpus.quest did not compile:\n{built.stdout}{built.stderr}")
        cls.oracle = None
        if GO:
            cls.oracle = tmp / "oracle"
            env = {**os.environ, "GOCACHE": str(tmp / "gocache"), "GOFLAGS": "-mod=mod"}
            done = subprocess.run([GO, "build", "-o", str(cls.oracle), str(ORACLE)], capture_output=True, text=True,
                                  env=env, cwd=tmp)
            if done.returncode != 0:
                raise RuntimeError(f"oracle.go did not build:\n{done.stdout}{done.stderr}")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def check(self, cases, timeout: float = 600) -> str:
        """Runs the harness on cases, lines of PATTERN SUBJECT FULL PARTIAL,
        and fails with its report unless every case passed; its last line"""
        path = Path(self.tmp.name) / "cases.txt"
        path.write_text("".join(c + "\n" for c in cases))
        done = subprocess.run([str(self.harness), str(path)], capture_output=True, text=True, timeout=timeout)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        last = done.stdout.strip().split("\n")[-1]
        self.assertTrue(last.endswith(" failures 0"), done.stdout[-6000:])
        return last

    def answered(self, pairs, every: bool = False):
        """Go's answers for (pattern, subject) pairs, as cases, without those Go
        does not compile or the library is not meant to agree on: the match of
        the whole subject and of a search, or with every, findAll, split, and
        replaceAll"""
        lines = "".join(f"{hexed(p)} {hexed(s)}\n" for p, s in pairs if not skipped(p, s))
        done = subprocess.run([str(self.oracle)] + (["-all"] if every else []), input=lines, capture_output=True,
                              text=True, check=True)
        return [line for line in done.stdout.split("\n") if line and not line.endswith(" error")]

    def test_re2_search(self):
        cases = [f"{hexed(p)} {hexed(s)} {full} {partial}"
                 for p, s, full, partial in re2_cases((DATA / "re2-search.txt").read_text().split("\n"))
                 if not skipped(p, s)]
        self.assertGreater(len(cases), 1500)
        self.check(cases)

    @unittest.skipUnless(os.environ.get("QUEST_REGEXP_EXHAUSTIVE"), "RE2's exhaustive tests run by hand")
    def test_re2_exhaustive(self):
        lines = bz2.decompress((DATA / "re2-exhaustive.txt.bz2").read_bytes()).decode("latin-1").split("\n")
        cases = [f"{hexed(p)} {hexed(s)} {full} {partial}"
                 for p, s, full, partial in re2_cases(lines) if not skipped(p, s)]
        print(self.check(cases, timeout=36000))

    @unittest.skipUnless(GO, "Go is not installed")
    def test_att_against_go(self):
        cases = self.answered(att_cases())
        self.assertGreater(len(cases), 200)
        self.check(cases)

    @unittest.skipUnless(GO, "Go is not installed")
    def test_random_against_go(self):
        cases = self.answered(random_cases(2500))
        self.assertGreater(len(cases), 8000)
        self.check(cases)

    @unittest.skipUnless(GO, "Go is not installed")
    def test_every_match_against_go(self):
        """findAll, split, and replaceAll on the AT&T cases and random ones"""
        cases = self.answered(list(att_cases()) + list(random_cases(1500)), every=True)
        self.assertGreater(len(cases), 5000)
        self.check(cases)

    def test_linear_time(self):
        """What a backtracking matcher takes exponential time over, against
        100,000 bytes"""
        a = b"a" * 100_000
        cases = [f"{hexed(p)} {hexed(s)} - -" for p, s in
                 ((b"(a|aa)*b", a), (b"(a*)*b", a), (b"(?:a+)+b", a), (b"(a|a)*b", a))]
        cases.append(f"{hexed(b'(a|aa)*')} {hexed(a)} 0-100000,99999-100000 0-100000,99999-100000")
        began = time.monotonic()
        self.check(cases, timeout=60)
        self.assertLess(time.monotonic() - began, 30)


if __name__ == "__main__":
    unittest.main()
