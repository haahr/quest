"""Transliterates the Data structure of sml/logic.sml (Prolog clauses compiled
to SML in continuation-passing style) into Quest, for logic.quest.

    python tools/logic_data.py > logic-data.txt

The structure is generated code over a small subset of SML: curried
applications, fn () => and fn X =>, tuples, sequences, and lists. This parses
that subset and prints the equivalent Quest, which logic.quest holds.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOKEN = re.compile(r"\s+|\(\*.*?\*\)|=>|[()\[\],;=]|[A-Za-z_][A-Za-z0-9_']*|\d+", re.S)
CONSTANTS = {"cons_s": "consS", "x_s": "xS", "nil_s": "nilS", "o_s": "oS", "s_s": "sS",
             "CON_o_s": "conO", "CON_nil_s": "conNil", "CON_x_s": "conX"}
FUNCTIONS = {"move_horiz": "moveHoriz", "rotate": "rotate", "move": "move", "solitaire": "solitaire",
             "solution1": "solution1", "solution2": "solution2", "trail": "trail", "exists": "exists",
             "unify": "unify", "STR": "str", "INT": "intTerm", "sc": "sc"}


def tokens(text):
    pos = 0
    out = []
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise SyntaxError(text[pos:pos + 40])
        tok = m.group(0)
        pos = m.end()
        if not tok.isspace() and not tok.startswith("(*"):
            out.append(tok)
    return out


def name(ident):
    if ident in CONSTANTS:
        return CONSTANTS[ident]
    if ident in FUNCTIONS:
        return FUNCTIONS[ident]
    return ident.replace("_", "").lower()


class Parser:
    def __init__(self, toks):
        self.toks = toks
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self, expected=None):
        tok = self.toks[self.i]
        if expected is not None and tok != expected:
            raise SyntaxError(f"expected {expected}, got {tok} at {self.toks[self.i - 5:self.i + 5]}")
        self.i += 1
        return tok

    def expr(self):
        if self.peek() == "fn":
            self.take("fn")
            if self.peek() == "(":
                self.take("(")
                self.take(")")
                self.take("=>")
                return ("fn0", self.expr())
            var = self.take()
            self.take("=>")
            return ("fn1", var, self.expr())
        head = self.atom()
        args = []
        while self.peek() not in (None, ")", "]", ",", ";", "and"):
            args.append(self.atom())
        return ("app", head, args) if args else head

    def atom(self):
        tok = self.peek()
        if tok == "(":
            self.take("(")
            if self.peek() == ")":
                self.take(")")
                return ("unit",)
            items = [self.expr()]
            sep = self.peek()
            while self.peek() in (",", ";"):
                self.take()
                items.append(self.expr())
            self.take(")")
            if len(items) == 1:
                return items[0]
            return ("tuple" if sep == "," else "seq", items)
        if tok == "[":
            self.take("[")
            items = [self.expr()]
            while self.peek() == ",":
                self.take(",")
                items.append(self.expr())
            self.take("]")
            return ("list", items)
        if tok == "fn":
            return self.expr()
        self.take()
        return ("id", tok) if not tok.isdigit() else ("int", tok)


WIDTH = 120


def inline(e):
    """e on one line."""
    kind = e[0]
    if kind == "id":
        return name(e[1])
    if kind == "int":
        return e[1]
    if kind == "unit":
        return ""
    if kind == "fn0":
        return f"fun(): Ok {inline(e[1])}"
    if kind == "fn1":
        return f"fun({name(e[1])}: Term): Ok {inline(e[2])}"
    if kind == "seq":
        return "begin " + " ".join(inline(x) for x in e[1]) + " end"
    if kind == "list":
        return f"terms{len(e[1])}(" + " ".join(inline(x) for x in e[1]) + ")"
    if kind == "tuple":
        return " ".join(inline(x) for x in e[1])
    if kind == "app":
        return f"{inline(e[1])}(" + " ".join(x for x in (inline(a) for a in e[2]) if x) + ")"
    raise ValueError(kind)


def args_of(e):
    """An application's arguments, tuples spread."""
    out = []
    for a in e[2]:
        out.extend(a[1] if a[0] == "tuple" else [a])
    return [a for a in out if a[0] != "unit"]


def fn_header(e):
    return "fun(): Ok" if e[0] == "fn0" else f"fun({name(e[1])}: Term): Ok"


def fn_body(e):
    return e[1] if e[0] == "fn0" else e[2]


def lines(e, indent):
    """e as lines at indentation indent. A function value that is an
    application's last argument (a continuation) has its body on the following
    lines at the same indentation, as the original lays them out, and the
    closing parentheses at the end."""
    pad = " " * indent
    kind = e[0]
    if kind == "seq":
        # Flat, as the original's parenthesized sequences are
        out = [f"{pad}begin"]
        for x in e[1]:
            out.extend(lines(x, indent))
        return out + [f"{pad}end"]
    if kind == "app":
        args = args_of(e)
        head = inline(e[1])
        if args and args[-1][0] in ("fn0", "fn1"):
            first = " ".join([inline(a) for a in args[:-1]] + [fn_header(args[-1])])
            text = f"{pad}{head}({first}"
            if len(text) <= WIDTH:
                out = [text]
            else:
                out = [f"{pad}{head}("]
                for a in args[:-1]:
                    out.extend(lines(a, indent + 4))
                out.append(f"{pad}    {fn_header(args[-1])}")
            body = lines(fn_body(args[-1]), indent)
            body[-1] += ")"
            return out + body
        text = pad + inline(e)
        if len(text) <= WIDTH:
            return [text]
        out = [f"{pad}{head}("]
        for a in args:
            out.extend(lines(a, indent + 4))
        out[-1] += ")"
        return out
    if kind == "list":
        text = pad + inline(e)
        if len(text) <= WIDTH:
            return [text]
        out = [f"{pad}terms{len(e[1])}("]
        for a in e[1]:
            out.extend(lines(a, indent + 4))
        out[-1] += ")"
        return out
    return [pad + inline(e)]


def fit(ls):
    """ls with the closing parentheses that take a line past WIDTH moved to a
    line of their own."""
    out = []
    for line in ls:
        if len(line) > WIDTH:
            stripped = line.rstrip(")")
            closers = line[len(stripped):]
            indent = min(len(line) - len(line.lstrip()), WIDTH - len(closers))
            out.extend([stripped, " " * indent + closers])
        else:
            out.append(line)
    return out


def main():
    src = (HERE / "sml" / "logic.sml").read_text()
    start = src.index("fun move_horiz")
    stop = src.index("  end (* local *)\nend; (* Data *)")
    toks = tokens(src[start:stop])
    p = Parser(toks)
    out = []
    first = True
    while p.peek() is not None:
        p.take("fun" if first else "and")
        fname = p.take()
        params = p.atom()
        p.take("sc")
        p.take("=")
        body = p.expr()
        names = [name(x[1]) for x in (params[1] if params[0] == "tuple" else [params])]
        sig = " ".join(f"{n}: Term" for n in names)
        keyword = "let rec" if first else "and"
        out.append(f"{keyword} {name(fname)}({sig} sc: All() Ok): Ok =\n" + "\n".join(fit(lines(body, 4))) + "\n")
        first = False
    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
