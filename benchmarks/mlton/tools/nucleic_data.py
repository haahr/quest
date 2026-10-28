"""Transliterates the nucleotide conformation database of sml/nucleic.sml into
Quest, for nucleic.quest.

    python tools/nucleic_data.py > nucleic-data.txt

Each conformation (val rA = (tfo, tfo, tfo, tfo, pt, ..., A (pt, ...))) becomes
let rA = nuc(tfo(...) ... pt(...) ... option a of Specific with pt(...) ... end).
rG01 through rG10 are left out: only the anticodon problem, which the
benchmark does not run, would use them. rG' and rU' become rGp and rUp.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOKEN = re.compile(r"\s+|\(\*.*?\*\)|[(),\[\]=]|~?\d+\.\d+|[A-Za-z_][A-Za-z0-9_']*", re.S)
SKIP = {f"rG{i:02}" for i in range(1, 11)}


def tokens(text):
    out, pos = [], 0
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise SyntaxError(text[pos:pos + 40])
        pos = m.end()
        t = m.group(0)
        if not t.isspace() and not t.startswith("(*"):
            out.append(t)
    return out


def parse(toks, i):
    """Parses a parenthesized tuple, a constructor application, or a number;
    returns (value, next index). Tuples are lists, numbers strings, and
    constructor applications (name, value) pairs."""
    t = toks[i]
    if t == "(":
        items = []
        i += 1
        while True:
            v, i = parse(toks, i)
            items.append(v)
            if toks[i] == ",":
                i += 1
            elif toks[i] == ")":
                i += 1
                break
            else:
                raise SyntaxError(toks[i:i + 5])
        return (items[0] if len(items) == 1 else items), i
    if t in ("A", "C", "G", "U"):
        v, i = parse(toks, i + 1)
        return (t, v), i
    if re.fullmatch(r"~?\d+\.\d+", t):
        return t, i + 1
    raise SyntaxError(toks[i:i + 5])


def call(name, reals):
    return f"{name}({' '.join(reals)})"


def emit(name, nuc):
    tfos, pts, (tag, specific) = nuc[:4], nuc[4:-1], nuc[-1]
    assert len(tfos) == 4 and len(pts) == 25 and all(len(t) == 12 for t in tfos)
    lines = [f"let {name} = nuc("]
    lines += ["    " + call("tfo", t) for t in tfos]
    for k in range(0, len(pts), 4):
        lines.append("    " + " ".join(call("pt", p) for p in pts[k:k + 4]))
    lines.append(f"    option {tag.lower()} of Specific with")
    for k in range(0, len(specific), 4):
        lines.append("        " + " ".join(call("pt", p) for p in specific[k:k + 4]))
    lines.append("    end)")
    return "\n".join(lines)


def main():
    text = (HERE / "sml" / "nucleic.sml").read_text()
    start = text.index("(* Database of nucleotide conformations: *)")
    end = text.index("(* -- PARTIAL INSTANTIATIONS")
    toks = tokens(text[start:end])
    out, i = [], 0
    while i < len(toks):
        if toks[i] != "val":
            raise SyntaxError(toks[i:i + 5])
        name = toks[i + 1]
        assert toks[i + 2] == "="
        if toks[i + 3] == "[":
            i = toks.index("]", i) + 1
            continue
        nuc, i = parse(toks, i + 3)
        if name not in SKIP:
            out.append(emit(name.replace("'", "p"), nuc))
    sys.stdout.write("\n\n".join(out) + "\n")


if __name__ == "__main__":
    main()
