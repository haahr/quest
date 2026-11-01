"""Builds benchmarks with several backends, for comparing their code
(docs/profiling.md section 2).

    python3.11 tools/perf/variants.py life mlyacc
        .build/perf/life.c, life.ssac, life.arm64, and mlyacc's, whole programs
    python3.11 tools/perf/variants.py --backends ssac,arm64 --separate life
        separately compiled units rather than whole programs
    python3.11 tools/perf/variants.py --dir /tmp/x --emit-c life
        also the SSA's C (life.ssac.c), to rebuild by hand

Each build gets a fresh build directory (DIR/build/BACKEND-NAME), since a
build directory's objects are not rebuilt when the compiler changes. The
compiler is ./quest, the self-hosted one, as the working tree builds it.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from perfutil import BENCHMARKS, BUILD, ROOT


def build(name: str, backend: str, out: Path, whole: bool, emit_c: bool) -> bool:
    """Builds benchmark name with backend into out/NAME.BACKEND (and, for
    emit_c, its C into out/NAME.BACKEND.c), returning whether it built"""
    build_dir = out / "build" / f"{backend}-{name}"
    shutil.rmtree(build_dir, ignore_errors=True)
    source = BENCHMARKS / f"{name}.quest"
    flags = ["--backend", backend, *(["--whole-program"] if whole else [])]
    outputs = [(out / f"{name}.{backend}", [])]
    if emit_c:
        outputs.append((out / f"{name}.{backend}.c", ["--emit-c"]))
    for target, extra in outputs:
        proc = subprocess.run([str(ROOT / "quest"), "compile", *flags, *extra, "--build-dir", str(build_dir),
                               "-o", str(target), str(source)], capture_output=True, text=True,
                              env={"QUEST_JOBS": "8", **os.environ})
        if proc.returncode != 0:
            sys.stderr.write(f"{name} ({backend}) failed to build:\n{proc.stdout}{proc.stderr}")
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="+", help="benchmarks (benchmarks/mlton/NAME.quest)")
    parser.add_argument("--backends", default="c,ssac,arm64", help="comma-separated (default c,ssac,arm64)")
    parser.add_argument("--dir", type=Path, default=BUILD, help="where to put the binaries (default .build/perf)")
    parser.add_argument("--separate", action="store_true", help="compile units separately, not --whole-program")
    parser.add_argument("--emit-c", action="store_true", help="also write each C or ssac build's C")
    args = parser.parse_args()
    args.dir.mkdir(parents=True, exist_ok=True)
    failed = False
    for name in args.names:
        for backend in args.backends.split(","):
            if build(name, backend, args.dir, not args.separate, args.emit_c and backend != "arm64"):
                print(args.dir / f"{name}.{backend}")
            else:
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
