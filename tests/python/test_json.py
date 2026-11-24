"""util/json against Python's json module (docs/json.md section 5).

tests/json/corpus.quest, compiled once with ./quest, checks a file of cases
that this test makes and answers with Python's json, reading and writing text
as Latin-1, as the library treats a string's bytes:

- texts to accept or reject, in the manner of JSONTestSuite: each accepted
  one printed compact (separators "," and ":") and indented by 2, as
  json.dumps prints it, but with each number as written, since the library
  keeps a number's text;
- random documents, printed by json.dumps in either form or with random
  whitespace, which the library must print back as json.dumps does;
- repeated member names, the last value winning in the first one's place, or
  rejected when unique;
- reals written as Python's repr writes them, and integers at an Int's ends.

Python accepts what the library rejects in three places, which the expected
answers follow: NaN and the infinities (parse_constant), escapes above
\\u00ff (a character is a byte), and with unique, a repeated name.

The UTF-8 mode's cases (parse8) are answered by Python reading the text as
UTF-8, each ill-formed sequence replaced by U+FFFD (errors="replace"), and
printing with ensure_ascii=False, encoded as UTF-8. There the library rejects
what Python accepts in one more place: a surrogate's escape without its
partner.
"""

import json
import random
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CORPUS = ROOT_DIR / "tests" / "json" / "corpus.quest"


def hexed(b: bytes) -> str:
    return b.hex() if b else "-"


class Rejected(Exception):
    pass


def reject_constant(name: str):
    raise Rejected(name)


def unique_pairs(pairs):
    names = [n for n, _ in pairs]
    if len(set(names)) != len(names):
        raise Rejected("repeated")
    return dict(pairs)


class Raw:
    """A number as written, printed as its text"""

    def __init__(self, text: str):
        self.text = text


def printed(value, indent, ensure_ascii=True) -> str:
    """json.dumps of value, a Raw number as its text: each Raw is printed as a
    placeholder string, which is then replaced"""
    raws = []

    def placeholders(v):
        if isinstance(v, Raw):
            raws.append(v.text)
            return f"\x00{len(raws) - 1}\x00"
        if isinstance(v, list):
            return [placeholders(x) for x in v]
        if isinstance(v, dict):
            return {k: placeholders(x) for k, x in v.items()}
        return v

    text = json.dumps(placeholders(value), separators=(",", ":") if indent is None else None, indent=indent,
                      ensure_ascii=ensure_ascii)
    for i, raw in enumerate(raws):
        text = text.replace(f'"\\u0000{i}\\u0000"', raw)
    return text


def wide(v) -> bool:
    """Whether a string in v has a character past \\u00ff"""
    if isinstance(v, str):
        return any(ord(c) > 255 for c in v)
    if isinstance(v, list):
        return any(wide(x) for x in v)
    if isinstance(v, dict):
        return any(wide(k) or wide(x) for k, x in v.items())
    return False


def answer(text: bytes, unique: bool) -> str:
    """A parse case, with Python's answer"""
    try:
        value = json.loads(text.decode("latin-1"), parse_constant=reject_constant, parse_int=Raw, parse_float=Raw,
                           object_pairs_hook=unique_pairs if unique else None)
        if wide(value):
            raise Rejected("wide")
        expected = f"{hexed(printed(value, None).encode('latin-1'))} {hexed(printed(value, 2).encode('latin-1'))}"
    except (ValueError, Rejected):
        expected = "error"
    return f"parse {hexed(text)} {int(unique)} {expected}"


def lone_surrogate(v) -> bool:
    """Whether a string in v has a surrogate, which only an escape without its
    partner gives"""
    if isinstance(v, str):
        return any(0xD800 <= ord(c) <= 0xDFFF for c in v)
    if isinstance(v, list):
        return any(lone_surrogate(x) for x in v)
    if isinstance(v, dict):
        return any(lone_surrogate(k) or lone_surrogate(x) for k, x in v.items())
    return False


def answer8(text: bytes, unique: bool) -> str:
    """A parse case in the UTF-8 mode, with Python's answer"""
    try:
        value = json.loads(text.decode("utf-8", errors="replace"), parse_constant=reject_constant, parse_int=Raw,
                           parse_float=Raw, object_pairs_hook=unique_pairs if unique else None)
        if lone_surrogate(value):
            raise Rejected("lone surrogate")
        compact = printed(value, None, ensure_ascii=False).encode("utf-8")
        indented = printed(value, 2, ensure_ascii=False).encode("utf-8")
        expected = f"{hexed(compact)} {hexed(indented)}"
    except (ValueError, Rejected):
        expected = "error"
    return f"parse8 {hexed(text)} {int(unique)} {expected}"


# Cases for the UTF-8 mode: escapes past ÿ, surrogate pairs and lone
# surrogates, well-formed sequences of each length, and ill-formed ones
# (truncated, overlong, a surrogate's encoding, past U+10FFFF, stray
# continuation bytes)
HANDWRITTEN_UTF8 = [
    b'"\\u00e9"', b'"\\u0100"', b'"\\u4e2d"', b'"\\uffff"', b'"\\ud83d\\ude00"', b'"\\uD83D\\uDE00"',
    b'"\\ud83d"', b'"\\ude00"', b'"\\ud83dx"', b'"\\ud83d\\u0041"', b'"\\ud83d\\ud83d"', b'"\\ud83d\\ude0"',
    b'"\\ud83d\\"', b'"a\\u0000b"', b'"\x7f"', b'"\xc3\xa9"', b'"\xe4\xb8\xad"', b'"\xf0\x9f\x98\x80"',
    b'"\xef\xbf\xbd"', b'"\xf4\x8f\xbf\xbf"', b'"\xff"', b'"\x80abc"', b'"\xc3"', b'"\xe4\xb8"', b'"\xf0\x9f\x98"',
    b'"\xc3x"', b'"\xe4\xb8x"', b'"\xed\xa0\x80"', b'"\xc0\xaf"', b'"\xc1\xbf"', b'"\xe0\x80\x80"',
    b'"\xe0\x9f\xbf"', b'"\xf0\x80\x80\x80"', b'"\xf4\x90\x80\x80"', b'"\xf5\x80\x80\x80"', b'"\xfe\xff"',
    b'"\xc3\\u0041"', b'"\xe4\\u00e9"', b'{"\xc3\xa9":"\xff"}', b'["\xe9\xff\x7f"]', b'\xc3\xa9', b'"\xe9"',
]


def random_string8(rng: random.Random) -> str:
    """A string of characters from every plane, surrogates aside"""
    def char() -> str:
        r = rng.random()
        if r < 0.5:
            return rng.choice("abcxyz \"\\/\x00\x1f\x7f")
        if r < 0.7:
            return chr(rng.randrange(0x80, 0x800))
        if r < 0.9:
            return chr(rng.choice([rng.randrange(0x800, 0xD800), rng.randrange(0xE000, 0x10000)]))
        return chr(rng.randrange(0x10000, 0x110000))
    return "".join(char() for _ in range(rng.randrange(0, 8)))


def random_value8(rng: random.Random, depth: int):
    kind = rng.randrange(6 if depth < 3 else 3)
    if kind == 0:
        return rng.choice([None, True, 1, -2.5])
    if kind in (1, 2):
        return random_string8(rng)
    if kind in (3, 4):
        return [random_value8(rng, depth + 1) for _ in range(rng.randrange(0, 4))]
    return {random_string8(rng): random_value8(rng, depth + 1) for _ in range(rng.randrange(0, 5))}


def mangled(rng: random.Random, text: bytes) -> bytes:
    """text with random bytes above 127 put in its strings, and some of its
    multibyte sequences cut short"""
    out, in_string, escaped = bytearray(), False, False
    for i, c in enumerate(text):
        if in_string and not escaped and c >= 0x80 and rng.random() < 0.1:
            continue
        out.append(c)
        if in_string:
            if escaped:
                escaped = False
            elif c == 0x5C:
                escaped = True
            elif c == 0x22:
                in_string = False
            elif rng.random() < 0.1:
                out.append(rng.randrange(0x80, 0x100))
        elif c == 0x22:
            in_string = True
    return bytes(out)


# Texts to accept or reject, as JSONTestSuite's y_ and n_ cases are
HANDWRITTEN = [
    b'null', b'true', b'false', b'0', b'-0', b'1', b'-1', b'12345678901234567890123', b'1.5', b'-0.0', b'1e5',
    b'1E+5', b'1e-5', b'1.25e10', b'"x"', b'""', b'[]', b'{}', b' [ 1 , 2 ] ', b'\t\n\r{"a"\n:\r1}\t',
    b'[[[[[]]]]]', b'{"a":{"b":{"c":[]}}}', b'"\\u0041\\u00e9\\u00ff"', b'"\\"\\\\\\/\\b\\f\\n\\r\\t"',
    b'"\xe9\xff\x7f"', b'[1,"a",null,true,{"k":[false]}]', b'{"":0}', b'{"a":1,"a":2}', b'{"a":1,"b":2,"a":3}',
    # Rejected
    b'', b' ', b'[', b']', b'{', b'[1,]', b'[,1]', b'{"a":1,}', b'{,}', b'{"a"}', b'{"a":}', b'{a:1}',
    b"{'a':1}", b'["a\nb"]', b'"\x01"', b'"\\x41"', b'"\\u12"', b'"\\u0100"', b'"\\ud83d\\ude00"', b'"abc',
    b'01', b'00', b'-01', b'+1', b'.5', b'1.', b'1.e5', b'1e', b'1e+', b'-', b'--1', b'0x10', b'1 2',
    b'NaN', b'Infinity', b'-Infinity', b'nul', b'truex', b'[true false]', b'{"a":1 "b":2}', b'[1]x',
    b'/* c */ 1', b'1 // c', b'\xef\xbb\xbf1', b'[\x0c1]', b'"\t"',
]

REALS = ["0", "1", "-1", "0.1", "1e16", "1e-5", "1e-4", "123456789012345678", "3.141592653589793", "2.5e-308",
         "1.7976931348623157e308", "1e309", "-1e400", "5e-324", "1e-400", "0.000123", "-0.0", "1E22", "9007199254740993"]

INTS = ["0", "-0", "1", "-1", "9223372036854775807", "-9223372036854775808", "9223372036854775808",
        "-9223372036854775809", "1.0", "1e3", "123456789012345678901234567890"]


def random_string(rng: random.Random) -> str:
    alphabet = [chr(i) for i in range(256)]
    common = "abcxyz \"\\/"
    return "".join(rng.choice(common) if rng.random() < 0.6 else rng.choice(alphabet)
                   for _ in range(rng.randrange(0, 8)))


def random_value(rng: random.Random, depth: int):
    kind = rng.randrange(8 if depth < 4 else 5)
    if kind == 0:
        return rng.choice([None, True, False])
    if kind == 1:
        return rng.randrange(-10 ** rng.randrange(1, 20), 10 ** rng.randrange(1, 20))
    if kind == 2:
        return rng.choice([rng.random() * 10 ** rng.randrange(-8, 20), -rng.random(), float(rng.randrange(100))])
    if kind in (3, 4):
        return random_string(rng)
    if kind in (5, 6):
        return [random_value(rng, depth + 1) for _ in range(rng.randrange(0, 5))]
    return {random_string(rng): random_value(rng, depth + 1) for _ in range(rng.randrange(0, 12))}


def spaced(rng: random.Random, text: str) -> str:
    """text with random whitespace between its tokens, outside strings"""
    out, in_string, escaped = [], False, False
    for c in text:
        if not in_string and c in "[]{},:" and rng.random() < 0.3:
            out.append(rng.choice([" ", "\n", "\t", "\r\n", "  "]))
        out.append(c)
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
        elif c == '"':
            in_string = True
    return "".join(out)


class JsonTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        target = tmp / "corpus"
        built = subprocess.run([str(ROOT_DIR / "quest"), "--build-dir", str(tmp / "build"), "-o", str(target),
                                str(CORPUS)], capture_output=True, text=True)
        if built.returncode != 0:
            raise RuntimeError(f"corpus.quest did not compile:\n{built.stdout}{built.stderr}")
        cls.harness = str(target)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def check(self, cases) -> None:
        path = Path(self.tmp.name) / "cases.txt"
        path.write_text("".join(c + "\n" for c in cases))
        done = subprocess.run([self.harness, str(path)], capture_output=True, text=True, timeout=600)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        last = done.stdout.strip().split("\n")[-1]
        self.assertEqual(last, f"cases {len(cases)} failures 0", done.stdout[-6000:])

    def test_handwritten(self):
        self.check([answer(t, u) for t in HANDWRITTEN for u in (False, True)])

    def test_random_documents(self):
        rng = random.Random(20261118)
        cases = []
        for _ in range(2000):
            value = random_value(rng, 0)
            form = rng.randrange(3)
            if form == 0:
                text = json.dumps(value, separators=(",", ":"))
            elif form == 1:
                text = json.dumps(value, indent=rng.choice([1, 2, 4]))
            else:
                text = spaced(rng, json.dumps(value))
            cases.append(answer(text.encode("latin-1"), rng.random() < 0.2))
        self.check(cases)

    def test_round_trip_is_json_dumps(self):
        """A document json.dumps printed, parsed and printed again, is the same
        text, compact and indented"""
        rng = random.Random(7)
        cases = []
        for _ in range(500):
            value = random_value(rng, 0)
            compact = json.dumps(value, separators=(",", ":")).encode("latin-1")
            indented = json.dumps(value, indent=2).encode("latin-1")
            cases.append(f"parse {hexed(compact)} 0 {hexed(compact)} {hexed(indented)}")
        self.check(cases)

    def test_utf8_handwritten(self):
        self.check([answer8(t, u) for t in HANDWRITTEN + HANDWRITTEN_UTF8 for u in (False, True)])

    def test_utf8_random_documents(self):
        """Documents json.dumps printed with escapes or as UTF-8, some with
        ill-formed bytes put in their strings"""
        rng = random.Random(20261123)
        cases = []
        for _ in range(2000):
            value = random_value8(rng, 0)
            form = rng.randrange(3)
            if form == 0:
                text = json.dumps(value, separators=(",", ":")).encode("ascii")
            elif form == 1:
                text = json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8")
            else:
                text = mangled(rng, json.dumps(value, ensure_ascii=False).encode("utf-8"))
            cases.append(answer8(text, rng.random() < 0.2))
        self.check(cases)

    def test_reals(self):
        rng = random.Random(3)
        texts = REALS + [repr(rng.random() * 10 ** rng.randrange(-30, 30)) for _ in range(300)]
        cases = []
        for t in texts:
            r = float(t)
            expected = "error" if r in (float("inf"), float("-inf")) else hexed(repr(r).encode())
            cases.append(f"real {hexed(t.encode())} {expected}")
        self.check(cases)

    def test_ints(self):
        cases = []
        for t in INTS:
            integral = all(c.isdigit() or c == "-" for c in t)
            fits = integral and -2 ** 63 <= int(t) < 2 ** 63
            cases.append(f"int {hexed(t.encode())} {hexed(str(int(t)).encode()) if fits else 'error'}")
        self.check(cases)


if __name__ == "__main__":
    unittest.main()
