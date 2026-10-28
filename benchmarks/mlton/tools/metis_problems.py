"""Transliterates the problems of model-elimination's Problem1 structure that
its benchmark proves into Quest.

    python tools/metis_problems.py > problems.txt

Each problem is a name and a goal, a quotation of one string; each of the
three collections (nonequality, equality, tptp) becomes an array of problem(name
goal) calls holding the problems the benchmark proves, in their order there.
"""

import re
import sys
from pathlib import Path

from mllex_tables import sml_string, wrap

HERE = Path(__file__).resolve().parent.parent

USED = {
    "nonequality": ["P26", "P29", "P46", "GILMORE_1", "LOS", "STEAM_ROLLER"],
    "equality": ["P48", "P49", "AGATHA"],
    "tptp": ["LCL009-1", "COL060-3", "COL058-2", "LCL107-1", "LDA007-3", "GRP010-4", "BOO021-1", "GEO002-4",
             "GRP128-4.003"],
}


def quest_string(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def main():
    text = (HERE / "sml" / "model-elimination.sml").read_text(encoding="latin-1")
    start = text.index("structure Problem1 :> Problem1")
    out = []
    for collection, names in USED.items():
        begin = text.index(f"\nval {collection} = [", start)
        end = text.index("\n];", begin)
        problems = re.findall(r'\{name = "([^"]*)",\s*goal = \[\s*QUOTE "((?:\\\s+\\|[^"\\]|\\.)*)"\]\}',
                              text[begin:end], re.S)
        found = {name: "".join(map(chr, sml_string(goal))) for name, goal in problems}
        out.append(f"let {collection}Problems: lists.T(Problem) = lists.fromArray(:Problem)(array of")
        for name, _ in problems:
            if name in names:
                lines = found[name].split("\n")
                pieces = [quest_string(line + "\n") for line in lines[:-1]] + [quest_string(lines[-1])]
                pieces = [p for p in pieces if p != '""'] or ['""']
                items = pieces[:1] + [f"<> {p}" for p in pieces[1:]]
                items[-1] += ")"
                out += wrap(f"    problem({quest_string(name)}", items, "        ")
        out.append("end)")
        missing = set(names) - set(found)
        assert not missing, missing
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
