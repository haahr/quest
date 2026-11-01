"""Checks the arm64 encoder (codegen/arm64/encode, docs/jit.md section 3.5)
against the assembler: a self-hosted driver compiles the run goldens' programs
with --backend arm64 into one build directory (or prints the assembly of one
that declares modules), with QUEST_CHECK_ENCODING=1, so that each unit's
assembly ends with the encoder's code and data for it, as comments. clang -c assembles each unit, and the encoder's words must be the
object's __text, its functions where the object's symbols put them, and its
data the bytes of the object's data symbols; a relocated field is compared
apart from its immediate, and the relocations by offset, kind, and symbol.
run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/encoder.py DRIVER
"""

from __future__ import annotations

import os
import struct
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SOURCE_DIR = ROOT_DIR / "tests" / "source"
RUN_GOLDEN_DIR = ROOT_DIR / "tests" / "golden" / "run"
PENDING = ROOT_DIR / "tests" / "self-hosted" / "pending-arm64.txt"

# Mach-O's arm64 relocation types, by the encoder's names for them
RELOC_TYPES = {"absolute64": 0, "branch26": 2, "page21": 3, "pageoff12": 4, "gotpage21": 5, "gotpageoff12": 6,
               "tlvpage21": 8, "tlvpageoff12": 9}
ADDEND = 10
# The bits of an instruction a relocation of each type leaves alone
KEPT_BITS = {2: 0xFC000000, 3: 0x9F00001F, 5: 0x9F00001F, 8: 0x9F00001F,
             4: 0xFFC003FF, 6: 0xFFC003FF, 9: 0xFFC003FF}


class MachO:
    """What the check reads of a Mach-O object: its sections (by segment and
    name: address, bytes, and relocations as (address, type, symbol)), and its
    symbols (name to section and address)."""

    def __init__(self, path: Path) -> None:
        data = path.read_bytes()
        magic, _, _, _, ncmds, _, _, _ = struct.unpack_from("<IiiIIIII", data, 0)
        assert magic == 0xFEEDFACF, f"{path} is not a 64-bit Mach-O object"
        self.sections: dict[tuple[str, str], tuple[int, bytes, list[tuple[int, int, str]]]] = {}
        raw_relocs = []
        self.symbols: dict[str, tuple[int, int]] = {}
        section_names: list[tuple[str, str]] = []
        offset = 32
        symtab = None
        for _ in range(ncmds):
            cmd, size = struct.unpack_from("<II", data, offset)
            if cmd == 0x19:  # LC_SEGMENT_64
                nsects = struct.unpack_from("<I", data, offset + 64)[0]
                at = offset + 72
                for _ in range(nsects):
                    sect = data[at:at + 16].rstrip(b"\0").decode()
                    seg = data[at + 16:at + 32].rstrip(b"\0").decode()
                    addr, sz, fileoff, _, reloff, nreloc, flags = struct.unpack_from("<QQIIIII", data, at + 32)
                    zerofill = (flags & 0xFF) in (1, 0x12)
                    contents = bytes(sz) if zerofill else data[fileoff:fileoff + sz]
                    section_names.append((seg, sect))
                    raw_relocs.append((seg, sect, addr, contents, reloff, nreloc))
                    at += 80
            elif cmd == 0x2:  # LC_SYMTAB
                symtab = struct.unpack_from("<IIII", data, offset + 8)
            offset += size
        names: list[str] = []
        if symtab:
            symoff, nsyms, stroff, _ = symtab
            for k in range(nsyms):
                strx, ntype, nsect, _, value = struct.unpack_from("<IBBHQ", data, symoff + 16 * k)
                name = data[stroff + strx:data.index(b"\0", stroff + strx)].decode()
                names.append(name)
                if nsect and not (ntype & 0xE0):
                    self.symbols[name] = (nsect, value)
        self.section_numbers = {k + 1: n for k, n in enumerate(section_names)}
        for seg, sect, addr, contents, reloff, nreloc in raw_relocs:
            relocs = []
            for k in range(nreloc):
                address, info = struct.unpack_from("<iI", data, reloff + 8 * k)
                number, extern, rtype = info & 0xFFFFFF, (info >> 27) & 1, info >> 28
                if rtype == ADDEND:
                    continue
                symbol = names[number] if extern else f"section {number}"
                relocs.append((address, rtype, symbol))
            self.sections[(seg, sect)] = (addr, contents, relocs)


def strip(symbol: str) -> str:
    return symbol[1:] if symbol.startswith("_") else symbol


def check_unit(assembly: Path, scratch: Path) -> list[str]:
    """How the encoder's code and data for one unit differ from what the
    assembler makes of its assembly."""
    lines = [line[len("// encoded "):].split() for line in assembly.read_text(encoding="utf-8").splitlines()
             if line.startswith("// encoded ")]
    if not lines:
        return [f"{assembly.name}: no encoding (was QUEST_CHECK_ENCODING set?)"]
    obj = scratch / (assembly.stem + "." + str(abs(hash(str(assembly)))) + ".o")
    built = subprocess.run(["clang", "-c", "-arch", "arm64", str(assembly), "-o", str(obj)], capture_output=True,
                           text=True)
    if built.returncode != 0:
        return [f"{assembly.name}: clang -c failed:\n{built.stderr}"]
    macho = MachO(obj)
    problems: list[str] = []
    name = assembly.name

    def fail(message: str) -> None:
        if len(problems) < 20:
            problems.append(f"{name}: {message}")

    text_addr, text, text_relocs = macho.sections.get(("__TEXT", "__text"), (0, b"", []))
    words = {int(item[1]): int(item[2], 16) for item in lines if item[0] == "code"}
    if len(words) * 4 != len(text):
        fail(f"{len(words)} words of code, but __text has {len(text)} bytes")
    code_relocs = {(int(i[2]), RELOC_TYPES[i[3]], i[4]) for i in lines if i[0] == "reloc" and i[1] == "code"}
    object_relocs = {(a, t, strip(s)) for a, t, s in text_relocs}
    for missing in sorted(object_relocs - code_relocs)[:5]:
        fail(f"the object's relocation {missing} is not the encoder's")
    for extra in sorted(code_relocs - object_relocs)[:5]:
        fail(f"the encoder's relocation {extra} is not the object's")
    kept = {a: KEPT_BITS.get(t, 0xFFFFFFFF) for a, t, _ in text_relocs}
    for at, w in sorted(words.items()):
        if at + 4 > len(text):
            break
        actual = struct.unpack_from("<I", text, at)[0]
        mask = kept.get(at, 0xFFFFFFFF)
        if (actual & mask) != (w & mask):
            fail(f"code at {at:#x} is {w:08x}, the assembler's {actual:08x}")
    for item in lines:
        if item[0] == "function":
            symbol = "_" + item[1]
            if symbol not in macho.symbols:
                fail(f"function {item[1]} is not in the object")
            elif macho.symbols[symbol][1] - text_addr != int(item[2]):
                fail(f"function {item[1]} is at {item[2]}, the object's at {macho.symbols[symbol][1] - text_addr}")
    data_relocs = [(int(i[2]), i[4], int(i[5])) for i in lines if i[0] == "reloc" and i[1] == "data"]
    for item in lines:
        if item[0] != "data":
            continue
        symbol, start = "_" + item[1], int(item[2])
        expected = bytes.fromhex(item[3]) if len(item) > 3 else b""
        if symbol not in macho.symbols:
            fail(f"datum {item[1]} is not in the object")
            continue
        nsect, value = macho.symbols[symbol]
        addr, contents, relocs = macho.sections[macho.section_numbers[nsect]]
        actual = bytearray(contents[value - addr:value - addr + len(expected)])
        mine = bytearray(expected)
        ours = {(o - start, strip_symbol) for o, strip_symbol, _ in data_relocs if start <= o < start + len(expected)}
        theirs = {(a - (value - addr), strip(s)) for a, _, s in relocs
                  if value - addr <= a < value - addr + len(expected)}
        if ours != theirs:
            fail(f"datum {item[1]}'s relocations {sorted(ours)} are not the object's {sorted(theirs)}")
        for o, _ in theirs:
            actual[o:o + 8] = bytes(8)
            mine[o:o + 8] = bytes(8)
        if actual != mine:
            fail(f"datum {item[1]} is {bytes(mine).hex()}, the object's {bytes(actual).hex()}")
    return problems


def programs() -> list[Path]:
    """The run goldens' programs that the arm64 backend compiles."""
    pending = set(PENDING.read_text(encoding="utf-8").split()) if PENDING.exists() else set()
    found = []
    for source in sorted(SOURCE_DIR.rglob("*.quest")):
        relative = source.relative_to(SOURCE_DIR).with_suffix("")
        if source.name.endswith((".int.quest", ".mod.quest")) or relative.as_posix() in pending:
            continue
        if (RUN_GOLDEN_DIR / relative).with_suffix(".out").exists():
            found.append(source)
    return found


def check(driver: str) -> tuple[int, list[str]]:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        build = root / "build"
        environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR), "QUEST_CHECK_ENCODING": "1"}
        problems: list[str] = []
        printed = root / "printed"
        printed.mkdir()
        for k, source in enumerate(programs()):
            # The program and the units it links, built into the build
            # directory; a program that declares modules, which builds only
            # as a whole, by its printed assembly
            compiled = subprocess.run([driver, "compile", "--backend", "arm64", "--build-dir", str(build),
                                       str(source), "-o", str(root / "program")], capture_output=True, text=True,
                                      env=environment, cwd=source.parent)
            if compiled.returncode != 0 and "contains a module/interface declaration" in compiled.stderr:
                compiled = subprocess.run([driver, "--backend", "arm64", "--stop-after", "codegen_c", "--build-dir",
                                           str(build), str(source)], capture_output=True, text=True,
                                          env=environment, cwd=source.parent)
                (printed / f"{k}.{source.stem}.s").write_text(compiled.stdout, encoding="utf-8")
            if compiled.returncode != 0:
                problems.append(f"{source.relative_to(ROOT_DIR)} did not compile:\n{compiled.stderr[-2000:]}")
        units = sorted(build.rglob("*.s")) + sorted(printed.glob("*.s"))
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            for found in pool.map(lambda unit: check_unit(unit, root), units):
                problems.extend(found)
        return len(units), problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    count, found = check(str(Path(sys.argv[1]).resolve()))
    for problem in found[:100]:
        print(problem)
    print(f"encoder: {count} units, {len(found)} problems")
    sys.exit(1 if found or count == 0 else 0)
