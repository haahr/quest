"""Tracebacks of uncaught exceptions (docs/exceptions.md): the interpreters report the frames active where an
exception was raised, most recent first, and the IR interpreter reports them exactly as the source interpreter does,
at every stage of the IR."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest_driver import run_driver

INTERPRETER_PHASES = ("interpret", "run_ir_core", "run_ir_specialized", "run_ir_closed", "run_ir_represented")

M_INTERFACE = """interface M
export
    fail(n: Int): Int
    apply(f(): Int): Int
end;
"""

M_MODULE = """module m : M
export
    let failure: Exception = exception failure end;
    let fail(n: Int): Int = if n > 0 then n else raise failure end end;
    let apply(f(): Int): Int = f();
end;
"""

BROKEN_INTERFACE = """interface Broken
export
    x: Int
end;
"""

BROKEN_MODULE = """module broken : Broken
export
    let zero = 0;
    let x = 1 / zero;
end;
"""

# Programs, and the frames each one's uncaught exception reports
CASES = {
    "nested": (
        """exception Boom end;
let rec inner(n: Int): Int = if n is 0 then raise Boom end else inner(n - 1) end;
let outer(n: Int): Int = begin
  let step(k: Int): Int = inner(k);
  step(n) + 1
end;
let twice(f(x: Int): Int n: Int): Int = f(f(n));
twice(fun(x: Int): Int begin outer(x) end 3);
""",
        ["in inner", "... inner repeated 3 more times", "in outer.step", "in outer", "in <anon>", "in twice",
         "in <main>"],
    ),
    "module": (
        """import m: M;
let call(): Int = m.fail(0);
m.apply(call);
""",
        ["in m.fail", "in call", "in m.apply", "in <main>"],
    ),
    "callback": (
        """import m: M;
exception Callback end;
m.apply(fun(): Int raise Callback end);
""",
        ["in <anon>", "in m.apply", "in <main>"],
    ),
    "reraise": (
        """exception Inner end;
exception Other end;
let f(): Int = raise Inner end;
let g(): Int = try f() when Other then 0 end;
g();
""",
        ["in f", "in g", "in <main>"],
    ),
    "module_initializer": (
        """import broken: Broken;
broken.x;
""",
        ["in broken.<init>", "in <main>"],
    ),
}


def _frames(stderr: str) -> list[str]:
    return [line.strip() for line in stderr.splitlines() if line.startswith(("  in ", "  ... "))]


class TestInterpreterTracebacks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp_dir.name)
        cls.build_dir = cls.root / ".build"
        for name, text in (("m.int.quest", M_INTERFACE), ("m.mod.quest", M_MODULE),
                           ("broken.int.quest", BROKEN_INTERFACE), ("broken.mod.quest", BROKEN_MODULE)):
            (cls.root / name).write_text(text, encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def stderr_of(self, program: Path, phase: str) -> str:
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertNotEqual(run_driver([str(program), "--stop-after", phase, "--build-dir", str(self.build_dir)]),
                                0)
        return err.getvalue()

    def test_frames_are_reported_alike_by_every_interpreter(self) -> None:
        for name, (text, frames) in CASES.items():
            program = self.root / f"{name}.quest"
            program.write_text(text, encoding="utf-8")
            expected = self.stderr_of(program, "interpret")
            with self.subTest(case=name):
                self.assertIn("error: Exception: ", expected)
                self.assertEqual(_frames(expected), frames)
                for phase in INTERPRETER_PHASES[1:]:
                    self.assertEqual(self.stderr_of(program, phase), expected, phase)


if __name__ == "__main__":
    unittest.main()
