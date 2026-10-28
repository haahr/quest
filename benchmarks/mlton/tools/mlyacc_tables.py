"""Transliterates the parse tables of the parser that ML-Yacc generated, in one
of the SML programs, into Quest.

    python tools/mlyacc_tables.py mlyacc > tables.txt

ML-Yacc writes its tables (actionRows, actionRowNumbers, and gotoT) as strings
of 16-bit integers, each two characters, low byte first. Each becomes an array
of those integers, which the program decodes as the original decodes its
strings.
"""

import re
import sys
from pathlib import Path

from mllex_tables import sml_string, wrap

HERE = Path(__file__).resolve().parent.parent


def main():
    program = sys.argv[1]
    text = (HERE / "sml" / f"{program}.sml").read_text(encoding="latin-1")
    out = []
    for name in ["actionRows", "actionRowNumbers", "gotoT"]:
        body = re.search(r"val " + name + r'\s*=\s*"((?:\\\s+\\|[^"\\]|\\.)*)"', text, re.S).group(1)
        chars = sml_string(body)
        assert len(chars) % 2 == 0, name
        ints = [chars[i] + chars[i + 1] * 256 for i in range(0, len(chars), 2)]
        out += wrap(f"let {name}Data: Array(Int) = array of", [str(n) for n in ints] + ["end"], "    ")
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
