"""Transliterates the lemmas of sml/boyer.sml's Rules structure into Quest,
for boyer.quest.

    python tools/boyer_rules.py > boyer-rules.txt

Each lemma is add (CProp (name, [args])) over CProp and CVar terms; each
becomes add(cp(name array of args end)) with cv(n) for CVar n.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOKEN = re.compile(r'\s+|"[^"]*"|[()\[\],;]|[A-Za-z_][A-Za-z0-9_]*|\d+')
WIDTH = 120


def tokens(text):
    out, pos = [], 0
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise SyntaxError(text[pos:pos + 40])
        pos = m.end()
        if not m.group(0).isspace():
            out.append(m.group(0))
    return out


class Parser:
    def __init__(self, toks):
        self.toks, self.i = toks, 0

    def take(self, expected=None):
        tok = self.toks[self.i]
        if expected is not None and tok != expected:
            raise SyntaxError(f"expected {expected}, got {tok}")
        self.i += 1
        return tok

    def term(self):
        kind = self.take()
        if kind == "CVar":
            return ("var", self.take())
        if kind != "CProp":
            raise SyntaxError(kind)
        self.take("(")
        name = self.take()
        self.take(",")
        self.take("[")
        args = []
        if self.toks[self.i] != "]":
            args.append(self.term())
            while self.toks[self.i] == ",":
                self.take(",")
                args.append(self.term())
        self.take("]")
        self.take(")")
        return ("prop", name, args)


def inline(t):
    if t[0] == "var":
        return f"cv({t[1]})"
    if not t[2]:
        return f"cp({t[1]} array of :CTerm end)"
    return f"cp({t[1]} array of " + " ".join(inline(a) for a in t[2]) + " end)"


def lines(t, indent):
    pad = " " * indent
    text = pad + inline(t)
    if len(text) <= WIDTH or t[0] == "var" or not t[2]:
        return [text]
    out = [f"{pad}cp({t[1]} array of"]
    for a in t[2]:
        out.extend(lines(a, indent + 4))
    out.append(f"{pad}end)")
    return out


def main():
    src = (HERE / "sml" / "boyer.sml").read_text()
    start = src.index("    val _ = (\nadd")
    stop = src.index("  end; (* Rules *)")
    body = src[start + len("    val _ = ("):stop].strip()
    toks = tokens(body)
    p = Parser(toks)
    out = []
    while p.i < len(toks):
        p.take("add")
        p.take("(")
        t = p.term()
        p.take(")")
        if p.i < len(toks) and toks[p.i] in (";", ")"):
            p.take()
        ls = lines(t, 8)
        ls[0] = "    add(" + ls[0].lstrip()
        ls = [ls[0]] + [line[4:] for line in ls[1:]]
        ls[-1] += ")"
        out.extend(ls)
    sys.stdout.write("\n".join(out) + "\n")
    sys.stderr.write(f"{len([l for l in out if l.startswith('    add(')])} lemmas\n")


if __name__ == "__main__":
    main()
