"""Generates a random Quest program that stresses the reuse of locals: many
variables of each kind, live across calls, loops, handlers, and closures."""
import random
import sys

seed = int(sys.argv[1])
nfun = int(sys.argv[2]) if len(sys.argv) > 2 else 6
size = int(sys.argv[3]) if len(sys.argv) > 3 else 60
rnd = random.Random(seed)
out = []
counter = [0]


def fresh(p):
    counter[0] += 1
    return f"{p}{counter[0]}"


class Scope:
    def __init__(self, parent=None):
        self.ints = list(parent.ints) if parent else []
        self.reals = list(parent.reals) if parent else []
        self.strs = list(parent.strs) if parent else []
        self.vints = list(parent.vints) if parent else []
        self.vreals = list(parent.vreals) if parent else []
        self.recs = list(parent.recs) if parent else []
        self.opts = list(parent.opts) if parent else []
        self.vars = list(parent.vars) if parent else []
        self.funs = list(parent.funs) if parent else []


def pick(xs):
    # favor old variables, so that lives are long
    if rnd.random() < 0.5:
        return xs[rnd.randrange(0, max(1, len(xs) // 3))]
    return rnd.choice(xs)


def intExpr(s, depth=0):
    c = rnd.random()
    pool = s.ints + s.vints
    if depth > 2 or c < 0.3:
        return pick(pool) if pool and rnd.random() < 0.85 else str(rnd.choice([0, 1, 7, 1073741823, 1073741824, 5000000000, 99]))
    if c < 0.5:
        return "{{" + intExpr(s, depth + 1) + " + " + intExpr(s, depth + 1) + "} % 1000003}"
    if c < 0.6:
        return "{{{" + intExpr(s, depth + 1) + " * 3} - " + intExpr(s, depth + 1) + "} % 1000003}"
    if c < 0.7:
        return "g.id(:Int " + intExpr(s, depth + 1) + ")"
    if c < 0.78 and s.recs:
        r = pick(s.recs)
        return rnd.choice([f"{r}.x", f"{r}.y"])
    if c < 0.84 and s.opts:
        return f"case {pick(s.opts)} when none then 3 when some with c then c.v end"
    if c < 0.9 and s.funs:
        return f"{pick(s.funs)}({intExpr(s, depth + 1)})"
    if c < 0.95 and s.vars:
        return f"case {pick(s.vars)} when n with k then k when x with k then real.round(k) when s with k then string.length(k) end"
    return f"if {{{intExpr(s, depth + 1)}}} > {{{intExpr(s, depth + 1)}}} then {intExpr(s, depth + 1)} else {intExpr(s, depth + 1)} end"


def realExpr(s, depth=0):
    c = rnd.random()
    pool = s.reals + s.vreals
    if depth > 2 or c < 0.4:
        return pick(pool) if pool and rnd.random() < 0.85 else rnd.choice(["0.5", "1.25", "3.0"])
    if c < 0.7:
        return "{{" + realExpr(s, depth + 1) + " ++ " + realExpr(s, depth + 1) + "} ** 0.5}"
    if c < 0.85:
        return "g.id(:Real " + realExpr(s, depth + 1) + ")"
    return "real.int({" + intExpr(s, depth + 1) + "} % 1000)"


def strExpr(s, depth=0):
    c = rnd.random()
    if depth > 1 or c < 0.4:
        return pick(s.strs) if s.strs and rnd.random() < 0.85 else '"q"'
    if c < 0.7:
        return "tail(" + strExpr(s, depth + 1) + " <> conv.int(" + intExpr(s, 2) + "))"
    if c < 0.85:
        return "g.id(:String " + strExpr(s, depth + 1) + ")"
    return "tail(" + strExpr(s, depth + 1) + " <> conv.real(" + realExpr(s, 2) + "))"


def stmts(s, n, ind, depth):
    lines = []
    for _ in range(n):
        c = rnd.random()
        pad = "    " * ind
        if c < 0.2:
            v = fresh("i")
            lines.append(f"{pad}let {v} = {intExpr(s)}")
            s.ints.append(v)
        elif c < 0.3:
            v = fresh("r")
            lines.append(f"{pad}let {v} = {realExpr(s)}")
            s.reals.append(v)
        elif c < 0.38:
            v = fresh("s")
            lines.append(f"{pad}let {v} = {strExpr(s)}")
            s.strs.append(v)
        elif c < 0.44:
            v = fresh("vi")
            lines.append(f"{pad}let var {v} = {intExpr(s)}")
            s.vints.append(v)
        elif c < 0.48:
            v = fresh("vr")
            lines.append(f"{pad}let var {v} = {realExpr(s)}")
            s.vreals.append(v)
        elif c < 0.53:
            v = fresh("p")
            lines.append(f"{pad}let {v}: P = record x = {intExpr(s)} var y = {intExpr(s)} end")
            s.recs.append(v)
        elif c < 0.57:
            v = fresh("o")
            if rnd.random() < 0.3:
                lines.append(f"{pad}let {v} = option none of O end")
            else:
                lines.append(f"{pad}let {v} = option some of O with let v = {intExpr(s)} end")
            s.opts.append(v)
        elif c < 0.61:
            v = fresh("w")
            k = rnd.random()
            if k < 0.4:
                lines.append(f"{pad}let {v} = variant n of V with {intExpr(s)} end")
            elif k < 0.7:
                lines.append(f"{pad}let {v} = variant x of V with {realExpr(s)} end")
            else:
                lines.append(f"{pad}let {v} = variant s of V with {strExpr(s)} end")
            s.vars.append(v)
        elif c < 0.65:
            v = fresh("f")
            lines.append(f"{pad}let {v} = fun(a: Int): Int {{{{a + {intExpr(s, 1)}}} % 1000003}}")
            s.funs.append(v)
        elif c < 0.71 and s.vints:
            lines.append(f"{pad}{pick(s.vints)} := {intExpr(s)}")
        elif c < 0.74 and s.vreals:
            lines.append(f"{pad}{pick(s.vreals)} := {realExpr(s)}")
        elif c < 0.77 and s.vints:
            lines.append(f"{pad}inc(@{pick(s.vints)})")
        elif c < 0.79 and s.recs:
            lines.append(f"{pad}{pick(s.recs)}.y := {intExpr(s)}")
        elif c < 0.83:
            lines.append(f"{pad}log := tail(log <> conv.int({intExpr(s)}) <> {strExpr(s)} <> conv.real({realExpr(s)}))")
        elif depth < 3 and c < 0.88:
            k = fresh("k")
            inner = Scope(s)
            inner.ints.append(k)
            lines.append(f"{pad}for {k} = 0 upto {rnd.randrange(1, 4)} do")
            lines.append(f"{pad}    begin")
            lines += stmts(inner, rnd.randrange(2, 7), ind + 2, depth + 1)
            lines.append(f"{pad}        ok")
            lines.append(f"{pad}    end")
            lines.append(f"{pad}end")
        elif depth < 3 and c < 0.91:
            w = fresh("vi")
            lines.append(f"{pad}let var {w} = 0")
            inner = Scope(s)
            lines.append(f"{pad}while {w} < {rnd.randrange(1, 4)} do")
            lines.append(f"{pad}    begin")
            lines += stmts(inner, rnd.randrange(2, 6), ind + 2, depth + 1)
            lines.append(f"{pad}        {w} := {w} + 1")
            lines.append(f"{pad}    end")
            lines.append(f"{pad}end")
            s.vints.append(w)
        elif depth < 3 and c < 0.96:
            a, b = Scope(s), Scope(s)
            lines.append(f"{pad}if {{{intExpr(s)}}} > {{{intExpr(s)}}} then")
            lines.append(f"{pad}    begin")
            lines += stmts(a, rnd.randrange(1, 6), ind + 2, depth + 1)
            lines.append(f"{pad}        ok")
            lines.append(f"{pad}    end")
            lines.append(f"{pad}else")
            lines.append(f"{pad}    begin")
            lines += stmts(b, rnd.randrange(1, 6), ind + 2, depth + 1)
            lines.append(f"{pad}        ok")
            lines.append(f"{pad}    end")
            lines.append(f"{pad}end")
        elif depth < 3:
            a, b = Scope(s), Scope(s)
            v = fresh("i")
            b.ints.append(v)
            lines.append(f"{pad}try")
            lines.append(f"{pad}    begin")
            lines += stmts(a, rnd.randrange(1, 5), ind + 2, depth + 1)
            lines.append(f"{pad}        if {{{{{intExpr(a)}}} % 3}} isnot 0 then raise stop with {intExpr(a)} end end")
            lines += stmts(a, rnd.randrange(1, 4), ind + 2, depth + 1)
            lines.append(f"{pad}        ok")
            lines.append(f"{pad}    end")
            lines.append(f"{pad}when stop with {v} then")
            lines.append(f"{pad}    begin")
            lines += stmts(b, rnd.randrange(1, 5), ind + 2, depth + 1)
            lines.append(f"{pad}        ok")
            lines.append(f"{pad}    end")
            lines.append(f"{pad}end")
    return lines


out.append("""import u/g : u/G ;
let say(s: String): Ok = writer.putString(writer.output s <> "\\n");
let tail(s: String): String = if string.length(s) > 40 then string.getSub(s {string.length(s) - 40} 40) else s end;
let inc(var k: Int): Ok = k := {{k + 1} % 1000003};
exception stop: Int end;
Def P = Record x: Int var y: Int end;
Def O = Option none some with v: Int end end;
Def V = Variant n: Int x: Real s: String end;""")
for fi in range(nfun):
    s = Scope()
    s.ints += ["a0", "a1"]
    s.reals += ["x0"]
    s.strs += ["s0"]
    s.vints += []
    body = stmts(s, size, 2, 0)
    out.append(f"let fn{fi}(a0: Int a1: Int x0: Real s0: String): String =")
    out.append("    begin")
    out.append('        let var log = ""')
    out += body
    final = " <> \" \" <> ".join(
        [f"conv.int({v})" for v in s.ints + s.vints] + [f"conv.real({v})" for v in s.reals + s.vreals] + s.strs
        + [f"conv.int({v}.x + {v}.y)" for v in s.recs])
    out.append(f"        log <> \"|\" <> {final}")
    out.append("    end;")
    out.append(f'say(fn{fi}(3 4 0.5 "a"));')
    out.append(f'say(fn{fi}(1073741824 ~9 2.5 "bb"));')
print("\n".join(out))
