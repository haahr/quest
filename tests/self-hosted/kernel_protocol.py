"""Checks the self-hosted driver's kernel mode (docs/jupyter.md section 2), through
tools/jupyter/quest_session.py: cells run as REPL inputs with their bindings kept
from cell to cell, each phrase's result a record, the program's output ahead of
the records written after it and arriving while the cell runs, failures as
error records of their kind and position, rolled back, and the driver's end
reported. With --no-jit too, the interpreter serves the same requests.

run_tests.py --self-hosted runs it (docs/testing.md). A driver that cannot host
the JIT, a whole-program build (docs/jit.md section 3.10), is checked with
--no-jit alone.

    python tests/self-hosted/kernel_protocol.py DRIVER
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools" / "jupyter"))

from quest_session import DriverExited, Session  # noqa: E402

ENVIRONMENT = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}


class Checker:
    def __init__(self, label: str) -> None:
        self.label = label
        self.problems: list[str] = []

    def expect(self, what: str, actual: object, expected: object) -> None:
        if actual != expected:
            self.problems.append(f"{self.label}: {what}: expected {expected!r}, got {actual!r}")


def hosts_jit(driver: str) -> bool:
    """Whether the driver can host the JIT: a whole-program build cannot."""
    ran = subprocess.run([driver, "--jit", "-e", "1"], capture_output=True, text=True, env=ENVIRONMENT, timeout=120)
    return "cannot host the JIT" not in ran.stderr


def check_cells(driver: str, options: list[str], label: str, scratch: Path) -> list[str]:
    c = Checker(label)
    s = Session([driver, *options], cwd=str(scratch), env=ENVIRONMENT)
    try:
        # Bindings carry over; each phrase that is not ok is a result
        c.expect("a binding", s.execute("let a = 10").results, ["let a:Int = 10"])
        reply = s.execute("a * 4; let b = 2")
        c.expect("two phrases", (reply.results, reply.status), (["40 : Int", "let b:Int = 2"], "ok"))
        c.expect("ok phrases", s.execute("let var t = 0\nt := 5").results, ["let var t:Int = 0"])
        c.expect("an empty cell", (s.execute("  \n").results, s.execute("").status), ([], "ok"))
        c.expect("a tuple", s.execute('tuple let x = 1 let y = "s" end').results,
                 ['tuple x=1 y="s" end : Tuple x: Int y: String end'])

        # Output comes ahead of the records written after it, decoded from
        # UTF-8, standard error apart
        events: list[tuple[str, str]] = []
        reply = s.execute('import writer: Writer\nwriter.putString(writer.output "one é\\n")\n'
                          'writer.putString(writer.err "two\\n")\n7',
                          lambda name, text: events.append((name, text)))
        c.expect("output and a result", (sorted(events), reply.results), (
            [("stderr", "two\n"), ("stdout", "one é\n")], ["7 : Int"]))

        # Standard output is line-buffered: a line arrives while the cell runs
        times: dict[str, float] = {}
        start = time.monotonic()
        reply = s.execute('import system: System\nwriter.putString(writer.output "started\\n")\n'
                          'system.run(array of "sleep" "1" end); ok',
                          lambda name, text: times.setdefault(text, time.monotonic()))
        done = time.monotonic()
        arrived = times.get("started\n")
        if arrived is None or done - arrived < 0.5:
            c.problems.append(f"{label}: a line written before a second's sleep arrived "
                              f"{'never' if arrived is None else f'{arrived - start:.2f}s in, of {done - start:.2f}s'}")

        # A syntax error, at its position
        reply = s.execute("let x = ")
        c.expect("a syntax error", (reply.status, reply.error and reply.error["error"],
                                    reply.error and (reply.error.get("line"), reply.error.get("column"))),
                 ("error", "syntax", (1, 9)))

        # A type error, rolled back with the phrase before it in the cell
        reply = s.execute('let a = 99\nlet z: Int = "s"')
        c.expect("a type error", (reply.status, reply.error and reply.error["error"],
                                  reply.error and (reply.error.get("line"), reply.error.get("column"))),
                 ("error", "type", (2, 14)))
        if reply.error and "Type mismatch" not in reply.error["rendered"]:
            c.problems.append(f"{label}: a type error's rendering: {reply.error['rendered']!r}")
        c.expect("the binding before a type error", s.execute("a").results, ["10 : Int"])

        # An exception, named, rolled back
        reply = s.execute("let q = 1\n100 / {q - 1}")
        c.expect("an exception", (reply.status, reply.error and reply.error["error"]), ("error", "int.error"))
        c.expect("the binding before an exception", s.execute("q").status, "error")

        # A module of the user's, written by the test, imported by two cells
        (scratch / "counter.int.quest").write_text("interface Counter export next(): Int end\n")
        (scratch / "counter.mod.quest").write_text(
            "module counter: Counter export let s = tuple let var n = 0 end "
            "let next(): Int = begin s.n := s.n + 1 s.n end end\n")
        c.expect("a module", s.execute("import counter: Counter\ncounter.next()").results, ["1 : Int"])
        c.expect("a module again", s.execute("import counter: Counter\ncounter.next()").results, ["2 : Int"])

        # A request that is not one
        records = s.request({"run": "1"})
        c.expect("not a request", [r.get("error") or r.get("done") for r in records], ["protocol", "error"])

        # The driver's end, reported
        try:
            s.execute("import system: System\nsystem.sysexit(3)")
            c.problems.append(f"{label}: a cell that exits did not end the session")
        except DriverExited as e:
            c.expect("the driver's exit", e.status, 3)
    except DriverExited as e:
        c.problems.append(f"{label}: the driver exited with {e.status}:\n{e.stderr}")
    finally:
        s.kill()
    return c.problems


def check_usage(driver: str) -> list[str]:
    problems = []
    ran = subprocess.run([driver, "--kernel", "-e", "1"], capture_output=True, text=True, env=ENVIRONMENT,
                         timeout=120)
    if ran.returncode != 2 or "--kernel takes neither FILE nor -e PROGRAM" not in ran.stderr:
        problems.append(f"--kernel with -e: exit {ran.returncode}, {ran.stderr!r}")
    ran = subprocess.run([driver, "--kernel"], capture_output=True, text=True, env=ENVIRONMENT, timeout=120,
                         stdin=subprocess.DEVNULL)
    if ran.returncode != 2 or "descriptor 3, which is not open" not in ran.stderr:
        problems.append(f"--kernel without its descriptors: exit {ran.returncode}, {ran.stderr!r}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    driver = str(Path(sys.argv[1]).resolve())
    found = check_usage(driver)
    modes = [(["--no-jit"], "interpreted")]
    if hosts_jit(driver):
        modes.insert(0, ([], "jit"))
    else:
        print("the driver cannot host the JIT: kernel mode checked interpreted alone")
    for options, label in modes:
        with tempfile.TemporaryDirectory() as d:
            found += check_cells(driver, options, label, Path(d))
    for problem in found:
        print(problem)
    print(f"kernel protocol: {len(found)} problems")
    sys.exit(1 if found else 0)
