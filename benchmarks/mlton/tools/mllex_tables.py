"""Transliterates the tables of a lexer that ml-lex generated, in one of the
SML programs, into Quest.

    python tools/mllex_tables.py raytrace PREFIX > tables.txt

ml-lex writes its transition rows as strings, either in a list,
val s = [(row, "..."), ...], or (older versions) each in its own value,
val sROW = "...", and its states as a list of {fin = [(N action), ...],
trans = row} (or trans = sROW). The rows become arrays of the next states, 129
or 256 of them (PREFIXRows), and the states an array of PREFIXState(fin trans)
calls, fin an array of action numbers and trans an index into PREFIXRows. The
PROGRAM's nth table (counting from 0) is chosen with an optional third
argument.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
WIDTH = 120


def sml_string(body):
    """The characters of the SML string literal body (without its quotes)."""
    out, i = [], 0
    while i < len(body):
        c = body[i]
        if c != "\\":
            out.append(ord(c))
            i += 1
            continue
        e = body[i + 1]
        if e.isdigit():
            out.append(int(body[i + 1:i + 4]))
            i += 4
        elif e.isspace():
            i = body.index("\\", i + 1) + 1
        else:
            out.append({"n": 10, "t": 9, "\\": 92, '"': 34}[e])
            i += 2
    return out


def wrap(prefix, items, indent):
    lines, line = [], prefix
    for item in items:
        if len(line) + 1 + len(item) > WIDTH:
            lines.append(line)
            line = indent + item
        else:
            line += ("" if line.isspace() else " ") + item
    lines.append(line)
    return lines


def main():
    program, prefix = sys.argv[1], sys.argv[2]
    nth = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    text = (HERE / "sml" / f"{program}.sml").read_text(encoding="latin-1")
    string = r'"((?:[^"\\]|\\.|\\\s+\\)*)"'
    lists = [m.start() for m in re.finditer(r"val s = \[", text)]
    if lists:
        start = lists[nth]
        end = text.index('(0, "")]', start)
        rows = {int(n): sml_string(body)
                for n, body in re.findall(r"\(\s*(\d+),\s*" + string + r"\s*\)", text[start:end], re.S)}
    else:
        start = [m.start() for m in re.finditer(r"\nval s0 =\n", text)][nth]
        end = text.index("in Vector.fromList", start)
        rows = {int(n): sml_string(body) for n, body in re.findall(r"val s(\d+) =\s*" + string, text[start:end], re.S)}
    tab_start = text.index("in Vector.fromList", end)
    tab_end = text.index("}]", tab_start)
    states = re.findall(r"\{fin = \[([^\]]*)\], trans = s?(\d+)\}", text[tab_start:tab_end + 1])
    order = sorted(rows)
    index = {n: k for k, n in enumerate(order)}
    out = [f"let {prefix}Rows: Array(Array(Int)) = array of"]
    for n in order:
        assert len(rows[n]) == len(rows[order[0]]) in (129, 256), (n, len(rows[n]))
        out += wrap("    array of", [str(b) for b in rows[n]] + ["end"], "        ")
    out.append("end")
    out.append(f"let {prefix}Tab: Array({prefix[0].upper()}{prefix[1:]}State) = array of")
    calls = []
    for fin, trans in states:
        actions = re.findall(r"N (\d+)", fin)
        calls.append(f"{prefix}State(array of {' '.join(actions + ['end'])} {index[int(trans)]})")
    out += wrap("    ", calls, "    ")
    out.append("end")
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
