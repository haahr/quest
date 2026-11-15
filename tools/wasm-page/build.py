"""Builds the page of the REPL on WasmGC (docs/wasm-plan.md step 12): a
directory of static files that any static server serves, such as

    python3 -m http.server -d .build/wasm-page

The directory holds index.html, the prompt; the page's scripts (here) and the
host's (runtime/wasm); driver.qar.gz, the driver's modules, compiled by DRIVER
with --backend wasm; and lib.qar.gz, the library's sources, with the .qi files
of the library's units the driver's build made when --qi is given. An archive
is the format runtime/wasm/archive.mjs reads.

    tools/wasm-page/build [-o DIR] [--driver DRIVER | --driver-wasm PATH [--driver-build B]] [--qi]
                          [--tests] [--check]

DRIVER is ./quest unless given; --driver-wasm takes a driver already built
(PATH its program module, with PATH.runtime.wasm and PATH.units beside it)
rather than building one, which takes a minute, and B is its build directory,
where --qi finds the .qi files (PATH's directory's build/ unless given).
--tests adds check.html, which runs the REPL's transcripts (tests/repl) in the
page against their goldens. --check implies --tests, and then runs check.html
in Google Chrome or Chromium, headless, with a profile of its own, served from
DIR on a port of localhost: it exits 1 if a transcript fails.
"""

from __future__ import annotations

import argparse
import functools
import gzip
import http.server
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
PAGE_FILES = ["index.html", "style.css", "ui.mjs", "page.mjs", "worker.mjs"]
CHECK_FILES = ["check.html", "check.mjs"]
HOST_FILES = ["host.mjs", "session.mjs", "jit.mjs", "repl.mjs", "archive.mjs"]


def archive(members: list[tuple[str, bytes]]) -> bytes:
    """The archive of members, uncompressed: "QAR1", the index's length, the
    index ([NAME, SIZE] in order, as JSON), and the members' bytes"""
    index = json.dumps([[name, len(data)] for name, data in members], separators=(",", ":")).encode()
    return b"QAR1" + struct.pack("<I", len(index)) + index + b"".join(data for _, data in members)


def write_archive(path: Path, members: list[tuple[str, bytes]]) -> tuple[int, int]:
    """Writes the archive of members, compressed, to path: its sizes,
    uncompressed and compressed"""
    data = archive(members)
    compressed = gzip.compress(data, compresslevel=9, mtime=0)
    path.write_bytes(compressed)
    return len(data), len(compressed)


def build_driver(driver: str, build_dir: Path) -> Path:
    target = build_dir / "quest.wasm"
    environment = {**os.environ, "QUEST_HOME": str(ROOT)}
    result = subprocess.run([driver, "--backend", "wasm", "--build-dir", str(build_dir / "build"), "-o", str(target),
                             str(ROOT / "questlang" / "driver" / "main.quest")],
                            capture_output=True, text=True, env=environment, cwd=build_dir)
    if result.returncode != 0:
        sys.exit(f"build: the driver did not compile:\n{result.stdout}{result.stderr}")
    return target


def driver_members(program: Path) -> list[tuple[str, bytes]]:
    """The driver's modules: the runtime's, the program's, and the units', in
    the order they are instantiated"""
    members = [("runtime.wasm", Path(f"{program}.runtime.wasm").read_bytes()), ("program.wasm", program.read_bytes())]
    for entry in Path(f"{program}.units").read_text().split():
        name, _, file = entry.partition("=")
        members.append((f"units/{name}", Path(file).read_bytes()))
    return members


def library_members(qi_dir: Path | None) -> list[tuple[str, bytes]]:
    """The library's sources, by their paths under lib/, and, from qi_dir,
    the .qi of each of its interfaces that the driver's build made"""
    lib = ROOT / "lib"
    members = []
    for source in sorted(lib.rglob("*.quest")):
        rel = source.relative_to(lib).as_posix()
        members.append((rel, source.read_bytes()))
        if qi_dir is not None and rel.endswith(".int.quest"):
            qi = qi_dir / (rel[:-len(".int.quest")] + ".qi")
            if qi.exists():
                members.append((rel[:-len(".int.quest")] + ".qi", qi.read_bytes()))
    return members


def copy_tests(into: Path) -> None:
    """tests/repl's transcripts and files, their goldens, and a list of them"""
    repl = ROOT / "tests" / "repl"
    names = sorted(p.stem for p in repl.glob("*.quest"))
    for source in repl.rglob("*.quest"):
        target = into / "tests" / "repl" / source.relative_to(repl)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    goldens = into / "tests" / "golden" / "repl"
    goldens.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copyfile(ROOT / "tests" / "golden" / "repl" / f"{name}.out", goldens / f"{name}.out")
    (into / "tests" / "transcripts.json").write_text(json.dumps(names) + "\n")


CHROME = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium",
          "chromium-browser"]


def check_in_chrome(out: Path) -> bool:
    """Runs out's check.html in headless Chrome, with the JIT and then
    interpreted: whether every transcript passed in each. check.mjs logs its
    outcome to the console, which Chrome writes to its standard error."""
    chrome = next((c for c in CHROME if shutil.which(c) or Path(c).exists()), None)
    if chrome is None:
        sys.exit("build: --check needs Google Chrome or Chromium")
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

    handler = functools.partial(Quiet, directory=str(out))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    passed = True
    for query in ("", "?jit=0"):
        url = f"http://127.0.0.1:{server.server_address[1]}/check.html{query}"
        with tempfile.TemporaryDirectory() as profile, tempfile.TemporaryFile("w+") as log:
            browser = subprocess.Popen([chrome, "--headless=new", f"--user-data-dir={profile}", "--no-first-run",
                                        "--enable-logging=stderr", "--v=0", url], stdout=log, stderr=log)
            outcome = None
            deadline = time.monotonic() + 600
            while outcome is None and time.monotonic() < deadline and browser.poll() is None:
                time.sleep(1)
                log.seek(0)
                outcome = re.search(r'questCheck: ([^"]*)"', log.read())
            browser.kill()
            browser.wait()
        if outcome is None:
            print(f"check: check.html{query} gave no outcome")
            passed = False
            continue
        print(f"check: {outcome.group(1)}")
        passed = passed and re.match(r"\w+: \d+ passed, 0 failed$", outcome.group(1)) is not None
    server.shutdown()
    return passed


def kb(n: int) -> str:
    return f"{n / 1024:,.0f} KB"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-o", dest="out", default=str(ROOT / ".build" / "wasm-page"))
    parser.add_argument("--driver", default=str(ROOT / "quest"))
    parser.add_argument("--driver-wasm")
    parser.add_argument("--driver-build", help="the build directory of --driver-wasm's driver, for --qi")
    parser.add_argument("--qi", action="store_true", help="add the library's .qi files to its archive")
    parser.add_argument("--tests", action="store_true", help="add check.html and the REPL's transcripts")
    parser.add_argument("--check", action="store_true", help="run check.html in headless Chrome")
    options = parser.parse_args()
    options.tests = options.tests or options.check
    out = Path(options.out).resolve()
    if options.driver_wasm:
        program = Path(options.driver_wasm).resolve()
        qi_dir = Path(options.driver_build).resolve() if options.driver_build else program.parent / "build"
        qi_dir = qi_dir if qi_dir.is_dir() else None
    else:
        build_dir = out.parent / (out.name + "-driver")
        build_dir.mkdir(parents=True, exist_ok=True)
        program = build_driver(options.driver, build_dir)
        qi_dir = build_dir / "build"
    if options.qi and qi_dir is None:
        sys.exit("build: --qi needs the build directory of --driver-wasm's driver (--driver-build)")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name in PAGE_FILES + (CHECK_FILES if options.tests else []):
        shutil.copyfile(HERE / name, out / name)
    for name in HOST_FILES:
        shutil.copyfile(ROOT / "runtime" / "wasm" / name, out / name)
    driver = write_archive(out / "driver.qar.gz", driver_members(program))
    library = write_archive(out / "lib.qar.gz", library_members(qi_dir if options.qi else None))
    if options.tests:
        copy_tests(out)
    print(f"build: wrote {out}")
    print(f"  driver.qar.gz: {kb(driver[0])}, {kb(driver[1])} compressed")
    print(f"  lib.qar.gz:    {kb(library[0])}, {kb(library[1])} compressed{' (with .qi files)' if options.qi else ''}")
    if options.check and not check_in_chrome(out):
        sys.exit(1)


if __name__ == "__main__":
    main()
