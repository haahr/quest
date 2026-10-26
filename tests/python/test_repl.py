"""Unit tests for the Quest interactive REPL subsystem (Phase 3.6)."""

import tempfile
import unittest
from pathlib import Path

from quest.config import CompilerOptions
from quest.modules.graph import UnitKind
from quest.pipeline import CompilerContext
from quest.repl import QuestREPL, check_input_completeness


class TestQuestREPL(unittest.TestCase):
    """The REPL's parts that its transcripts (tests/repl, docs/testing.md §2.7)
    cannot show."""

    def test_check_input_completeness(self) -> None:
        """Verifies EOF-continuation heuristics."""
        self.assertEqual(check_input_completeness(""), (False, None))
        self.assertEqual(check_input_completeness("   \n  "), (False, None))
        self.assertEqual(check_input_completeness("1 + 2"), (False, None))
        self.assertEqual(check_input_completeness("let x = 1"), (False, None))
        self.assertEqual(check_input_completeness("let x = 1;"), (False, None))

        # Incomplete (expecting more tokens)
        is_inc, _ = check_input_completeness("let f(x: Int): Int =")
        self.assertTrue(is_inc)

        is_inc, _ = check_input_completeness("if true then 1")
        self.assertTrue(is_inc)

        is_inc, _ = check_input_completeness("(* unclosed comment")
        self.assertTrue(is_inc)

        is_inc, _ = check_input_completeness('"unclosed string')
        self.assertTrue(is_inc)

        # Definite syntax error on non-EOF token
        is_inc, err = check_input_completeness("let 123 = 4")
        self.assertFalse(is_inc)
        self.assertIsNotNone(err)


COUNTER_INTERFACE = """interface Counter
export
    next(): Int
end;
"""

COUNTER_MODULE = """module counter : Counter
export
    let var n = 0
    let next(): Int = begin n := n + 1 n end
end;
"""


class TestREPLUnits(unittest.TestCase):
    """The REPL's unit graph: each input is a session of its own, and an input
    that fails, after importing modules, is rolled back, units and their values
    included (docs/repl.md §5)."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name).resolve()
        (self.dir / "counter.int.quest").write_text(COUNTER_INTERFACE, encoding="utf-8")
        (self.dir / "counter.mod.quest").write_text(COUNTER_MODULE, encoding="utf-8")
        ctx = CompilerContext.create("", "<repl>", options=CompilerOptions())
        # Imports are resolved from the REPL's directory
        ctx.env.current_dir = self.dir
        self.repl = QuestREPL(ctx=ctx)

    def session(self, inputs: list[str]) -> tuple[str, str]:
        """Runs inputs in the REPL, continuing its session, and returns its
        stdout and stderr."""
        queue = list(inputs)
        stdout: list[str] = []
        stderr: list[str] = []

        def mock_input(prompt: str) -> str:
            if not queue:
                raise EOFError()
            stdout.append(prompt + queue[0] + "\n")
            return queue.pop(0)

        self.repl.input_fn = mock_input
        self.repl.stdout_write = stdout.append
        self.repl.stderr_write = stderr.append
        self.repl.run()
        return "".join(stdout), "".join(stderr)

    def counter_unit(self):
        return self.repl.context.env.units.find(UnitKind.MODULE, "counter")

    def test_module_runs_once_per_session(self) -> None:
        """A module imported by successive inputs is run once, and keeps its
        state."""
        stdout, stderr = self.session(["import counter: Counter", "counter.next()", "import counter: Counter",
                                       "counter.next()"])
        self.assertEqual(stderr, "")
        self.assertIn("==  1 : Int\n", stdout)
        self.assertIn("==  2 : Int\n", stdout)
        self.assertIn("counter", self.repl.context.runtime_env.module_values)

    def test_runtime_failure_forgets_imported_module(self) -> None:
        """An input that imports a module and then fails at run time is rolled
        back: the module is forgotten, typed form and value, so importing it
        again elaborates and runs it again."""
        stdout, stderr = self.session(["import counter: Counter; counter.next(); 1 / 0"])
        self.assertIn("error: Exception: int.error", stderr)
        self.assertIsNone(self.counter_unit())
        ctx = self.repl.context
        # The runtime environment holds the type checker's graph, which the
        # rollback changed in place
        self.assertIs(ctx.runtime_env.units, ctx.env.units)
        self.assertNotIn("counter", ctx.runtime_env.module_values)
        stdout, stderr = self.session(["import counter: Counter", "counter.next()"])
        self.assertEqual(stderr, "")
        self.assertIn(">>  counter.next()\n==  1 : Int\n", stdout)
        self.assertIsNotNone(self.counter_unit().typed_module)

    def test_type_error_forgets_imported_module(self) -> None:
        """An input that imports a module and then fails to type check is rolled
        back, the module with it."""
        _, stderr = self.session(['import counter: Counter; let b: Int = "x"'])
        self.assertIn("error: Type mismatch", stderr)
        self.assertIsNone(self.counter_unit())
        self.assertIsNone(self.repl.context.env.units.interface_scope("counter"))
        stdout, stderr = self.session(["import counter: Counter", "counter.next()"])
        self.assertEqual(stderr, "")
        self.assertIn("==  1 : Int\n", stdout)

    def test_failure_keeps_modules_imported_before(self) -> None:
        """Rolling back an input keeps the modules earlier inputs imported, with
        their state."""
        stdout, stderr = self.session(["import counter: Counter", "counter.next()",
                                       "counter.next(); 1 / 0", "counter.next()"])
        self.assertIn("error: Exception: int.error", stderr)
        # The failed input's call changed the module's state, which a rollback
        # does not undo
        self.assertIn(">>  counter.next()\n==  3 : Int\n", stdout)
        self.assertIn("counter", self.repl.context.runtime_env.module_values)

    def test_input_finds_files_created_since(self) -> None:
        """Each input resolves its imports again, finding files created since an
        earlier input failed to."""
        _, stderr = self.session(["import later: Later"])
        self.assertIn("later", stderr.lower())
        (self.dir / "later.int.quest").write_text("interface Later export x: Int end;\n", encoding="utf-8")
        (self.dir / "later.mod.quest").write_text("module later : Later export let x = 7 end;\n",
                                                  encoding="utf-8")
        stdout, stderr = self.session(["import later: Later", "later.x"])
        self.assertEqual(stderr, "")
        self.assertIn("==  7 : Int\n", stdout)

    def test_module_declared_again(self) -> None:
        """A module declared again by a later input is the new one, and one
        declared by an input that fails is forgotten."""
        stdout, _ = self.session([
            "interface I export x: Int end",
            "module m: I export let x = 1 end",
            "module m: I export let x = 2 end",
            "m.x",
            "module k: I export let x = 3 end; 1 / 0",
            "module k: I export let x = 4 end",
            "k.x",
        ])
        self.assertIn(">>  m.x\n==  2 : Int\n", stdout)
        self.assertIn(">>  k.x\n==  4 : Int\n", stdout)


if __name__ == "__main__":
    unittest.main()
