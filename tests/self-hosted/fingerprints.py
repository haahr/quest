"""Checks the fingerprints that module units export for the JIT (docs/jit.md
sections 3.3 and 3.3.1): a self-hosted driver compiles a program that prints
two of its units' qh_ symbols, which an unsound module of its own reads
through os/code. They must

- be the same through the c, ssac, and arm64 backends;
- be the SHA-256 of the text below, made from the units' .qi files, so that
  they cover the ABI version and nothing the .qi does not record;
- be unchanged by an interface's comments, declaration order, and location
  (the same units in another directory);
- change with an exported type, and with a manifest type that an interface
  imports, which changes the importer's too.

run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/fingerprints.py DRIVER
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

BASE_INT = """interface Base
export
    Def Pair = Tuple a: Int b: Int end
    origin: Pair
end
"""

BASE_MOD = """module base : fp/Base
export
    Let Pair = Tuple a: Int b: Int end
    let origin = tuple let a = 0 let b = 0 end
end
"""

SHAPE_INT = """interface Shape
import
    fp/base : fp/Base
export
    T::TYPE
    Def Size = Int
    make(p: base.Pair): T
    width(s: T): Size
end
"""

SHAPE_MOD = """module shape : fp/Shape
import
    fp/base : fp/Base
export
    Let T = base.Pair
    Let Size = Int
    let make(p: base.Pair): T = p
    let width(s: T): Size = s.a
end
"""

READER_INT = """interface Fingerprints
export
    (* The fingerprint the unit exports, or "none" *)
    exported(unit: String): String
end
"""

READER_MOD = """unsound module fingerprints : fp/Fingerprints
import
    os/value : os/Value
    os/code : os/Code
    word : Word
    ascii : Ascii
    util/maybe : util/Maybe
    util/stringBuilder : util/StringBuilder
export
    (* qh_<unit> is a C string of 64 hexadecimal digits, read a word at a
     * time, since fetch takes aligned addresses *)
    let exported(unit: String): String =
        begin
            let at = code.symbol("qh_" <> unit)
            if maybe.isNone(:value.T at) then
                "none"
            else
                let start = value.be(:Int maybe.unwrap(:value.T at))
                let b = stringBuilder.new()
                for i = 0 upto 63 do
                    let addr = start + i
                    let w = value.be(:word.T value.fetch(value.new(:Int addr - addr % 8) 0))
                    b.char(ascii.char(word.toInt(word.extract(w 8 * {addr % 8} 8))))
                end
                b.toString()
            end
        end
end
"""

PROGRAM = """import writer: Writer;
import fp/base: fp/Base;
import fp/shape: fp/Shape;
import fp/fingerprints: fp/Fingerprints;

shape.width(shape.make(base.origin));
writer.putString(writer.output "fp/Base " <> fingerprints.exported("fp__base") <> "\\n");
writer.putString(writer.output "fp/Shape " <> fingerprints.exported("fp__shape") <> "\\n")
"""

# The interfaces' variants: comments and declaration order, which must not
# change a fingerprint, and an exported type, and a manifest type imported,
# which must
SHAPE_INT_REORDERED = """(* The same interface, written differently *)
interface Shape
import
    fp/base : fp/Base
export
    Def Size = Int  (* a size *)
    T::TYPE


    (* Its operations, the other way round *)
    width(s: T): Size
    make(p: base.Pair): T
end
"""

SHAPE_INT_RETYPED = SHAPE_INT.replace("Def Size = Int", "Def Size = Bool")
SHAPE_MOD_RETYPED = SHAPE_MOD.replace("Let Size = Int", "Let Size = Bool").replace("= s.a", "= s.a > 0")
BASE_INT_WIDENED = BASE_INT.replace("b: Int end", "b: Int c: Int end")
BASE_MOD_WIDENED = BASE_MOD.replace("let b = 0 end", "let b = 0 let c = 0 end").replace("b: Int end", "b: Int c: Int end")

UNITS = ("fp/Base", "fp/Shape")


def abi_version() -> int:
    text = (ROOT_DIR / "questlang" / "config" / "abi.mod.quest").read_text(encoding="utf-8")
    return int(text.split("let abiVersion = ")[1].split()[0])


def digest(canonical: str, qi_file: Path, qi_files: dict[str, Path]) -> str:
    """What modules/artifacts/fingerprint computes for an interface from its .qi, the
    .qi files of the interfaces it imports by path."""
    record = json.loads(qi_file.read_text(encoding="utf-8"))["value"]
    imports = sorted(f"import {i}\n" for i in record["imports"])
    uses = sorted(f"uses {i.rsplit(':', 1)[-1]} "
                  f"{digest(i.rsplit(':', 1)[-1], qi_files[i.rsplit(':', 1)[-1]], qi_files)}\n"
                  for i in record["imports"])
    types = sorted(f"type {t['name']} {t['kind']}" + (f" = {t['manifestType']}" if t["isManifest"] else "") + "\n"
                   for t in record["types"])
    values = sorted(f"value {v['name']}: {v['typeSig']}\n" for v in record["values"])
    text = f"abi {abi_version()}\ninterface {canonical}\n" + "".join(imports + types + values + uses)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(driver: str, directory: Path, files: dict[str, str], backend: str) -> dict[str, str] | str:
    """The fingerprints the program prints, built in directory from files with
    backend, by unit; or why it could not be built and run."""
    for name, text in files.items():
        (directory / name).parent.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(text, encoding="utf-8")
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    command = [driver, "compile", "--backend", backend, "--build-dir", "build", "main.quest", "-o", "main"]
    built = subprocess.run(command, capture_output=True, text=True, cwd=directory, env=environment)
    if built.returncode != 0:
        return f"the {backend} build in {directory} failed:\n{built.stdout}{built.stderr}"
    ran = subprocess.run(["./main"], capture_output=True, text=True, cwd=directory, timeout=60)
    if ran.returncode != 0:
        return f"the {backend} program failed:\n{ran.stdout}{ran.stderr}"
    return dict(line.split(" ", 1) for line in ran.stdout.splitlines())


def check(driver: str) -> list[str]:
    problems: list[str] = []
    base = {"fp/base.int.quest": BASE_INT, "fp/base.mod.quest": BASE_MOD, "fp/shape.int.quest": SHAPE_INT,
            "fp/shape.mod.quest": SHAPE_MOD, "fp/fingerprints.int.quest": READER_INT,
            "fp/fingerprints.mod.quest": READER_MOD, "main.quest": PROGRAM}
    variants = {
        "reordered": {**base, "fp/shape.int.quest": SHAPE_INT_REORDERED},
        "retyped": {**base, "fp/shape.int.quest": SHAPE_INT_RETYPED, "fp/shape.mod.quest": SHAPE_MOD_RETYPED},
        "widened": {**base, "fp/base.int.quest": BASE_INT_WIDENED, "fp/base.mod.quest": BASE_MOD_WIDENED},
    }
    # Which units' fingerprints each variant must change
    changes = {"reordered": set(), "retyped": {"fp/Shape"}, "widened": {"fp/Base", "fp/Shape"}}
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        results: dict[str, dict[str, str]] = {}
        for backend in ("c", "ssac", "arm64"):
            result = build(driver, root / f"base-{backend}", base, backend)
            if isinstance(result, str):
                return [result]
            results[backend] = result
        printed = results["c"]
        for backend in ("ssac", "arm64"):
            if results[backend] != printed:
                problems.append(f"{backend}'s fingerprints differ from c's: {results[backend]} {printed}")
        if any(printed.get(unit, "none") == "none" for unit in UNITS):
            return problems + [f"a unit exports no fingerprint: {printed}"]
        qi_files = {unit: root / "base-c" / "build" / (unit.lower() + ".qi") for unit in UNITS}
        for unit in UNITS:
            expected = digest(unit, qi_files[unit], qi_files)
            if printed[unit] != expected:
                problems.append(f"{unit}'s fingerprint is {printed[unit]}, not the digest of its .qi, {expected}")
        for name, files in variants.items():
            result = build(driver, root / name, files, "c")
            if isinstance(result, str):
                problems.append(result)
                continue
            for unit in UNITS:
                changed = result[unit] != printed[unit]
                if changed != (unit in changes[name]):
                    problems.append(f"{name}: {unit}'s fingerprint {'changed' if changed else 'did not change'}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    found = check(str(Path(sys.argv[1]).resolve()))
    for problem in found:
        print(problem)
    print(f"fingerprints: {len(found)} problems")
    sys.exit(1 if found else 0)
