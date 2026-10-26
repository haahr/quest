"""io/readline at a terminal: line editing, history, Ctrl-C, and Ctrl-D, through
a pseudo-terminal, compiled with each line editor installed and in the
bootstrap's interpreter, and the REPL that reads its input through it
(docs/self-hosted-repl.md §1). Golden tests and REPL transcripts cover what
needs no terminal (tests/source/stdlib/readline.quest, tests/repl)."""

from __future__ import annotations

import os
import pty
import re
import select
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DRIVER = ROOT_DIR / "bootstrap" / "python" / "quest_driver.py"
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

from quest.codegen.c.compiler_runner import _sdk_has  # noqa: E402

# Echoes each line it reads, and reports the exceptions readLine raises; at the
# end of the input, writes the history's last three lines to $HIST, from which
# it read the history first
PROGRAM = """import io/readline : io/Readline
import writer: Writer
import system: System
let say(s: String): Ok = begin writer.putString(writer.output s) writer.flush(writer.output) end
say(if readline.editing() then "[EDITING]\\n" else "[PLAIN]\\n" end)
readline.readHistory(system.getEnv("HIST"))
let var going = true
while going do
    try
        let line = readline.readLine("> ")
        readline.addHistory(line)
        say("[LINE:" <> line <> "]\\n")
    when readline.interrupted then
        say("\\n[INT]\\n")
    when readline.endOfInput then
        say("\\n[EOF]\\n")
        readline.writeHistory(system.getEnv("HIST") 3)
        going := false
    end
end
"""

CTRL_A, CTRL_C, CTRL_D, CTRL_P = "\x01", "\x03", "\x04", "\x10"


class Terminal:
    """A program run on a pseudo-terminal, whose output is matched as it
    comes."""

    def __init__(self, command: list[str], env: dict[str, str]) -> None:
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.execve(command[0], command, env)
        self.output = ""
        self.seen = 0

    def expect(self, pattern: str, timeout: float = 30.0) -> str:
        """Waits for pattern to appear after what earlier expects matched, and
        returns the match."""
        regex = re.compile(pattern)
        deadline = time.monotonic() + timeout
        while True:
            found = regex.search(self.output, self.seen)
            if found:
                self.seen = found.end()
                return found.group(0)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(f"timed out waiting for {pattern!r}; output so far: {self.output!r}")
            ready, _, _ = select.select([self.fd], [], [], remaining)
            if ready:
                try:
                    chunk = os.read(self.fd, 4096)
                except OSError:
                    chunk = b""
                if not chunk:
                    raise AssertionError(f"ended waiting for {pattern!r}; output: {self.output!r}")
                self.output += chunk.decode("latin-1")

    def send(self, keys: str) -> None:
        os.write(self.fd, keys.encode("latin-1"))

    def wait(self, timeout: float = 30.0) -> int:
        """The program's exit status, once it exits. Its output meanwhile is
        read: a line editor restoring the terminal at exit (tcsetattr with
        TCSADRAIN) waits until its output has been read."""
        deadline = time.monotonic() + timeout
        while True:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid != 0:
                os.close(self.fd)
                return os.waitstatus_to_exitcode(status)
            if time.monotonic() > deadline:
                os.kill(self.pid, 9)
                os.waitpid(self.pid, 0)
                os.close(self.fd)
                raise AssertionError(f"timed out waiting for the program to exit; output: {self.output!r}")
            ready, _, _ = select.select([self.fd], [], [], 0.05)
            if ready:
                try:
                    self.output += os.read(self.fd, 4096).decode("latin-1")
                except OSError:
                    pass


class TestReadlineTerminal(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.dir = Path(tmp.name)
        cls.program = cls.dir / "echo.quest"
        cls.program.write_text(PROGRAM, encoding="utf-8")

    def environment(self, history: Path, term: str = "xterm") -> dict[str, str]:
        env = dict(os.environ, TERM=term, HIST=str(history), PYTHONPATH=str(ROOT_DIR / "bootstrap" / "python"))
        env["QUEST_HOME"] = str(ROOT_DIR)
        return env

    def compiled(self, editor: str) -> list[str]:
        """The program compiled with a line editor (QUEST_READLINE)."""
        binary = self.dir / f"echo-{editor}"
        if not binary.exists():
            env = dict(os.environ, QUEST_READLINE=editor, PYTHONPATH=str(ROOT_DIR / "bootstrap" / "python"))
            subprocess.run(
                [sys.executable, str(DRIVER), "--build-dir", str(self.dir / f"build-{editor}"), "-o", str(binary),
                 str(self.program)],
                check=True, env=env, capture_output=True,
            )
        return [str(binary)]

    def commands(self) -> dict[str, list[str]]:
        """The ways to run the program: compiled with each line editor
        installed, and interpreted."""
        found = {"interpreted": [sys.executable, str(DRIVER), str(self.program)]}
        if Path("/opt/homebrew/opt/readline/include/readline/rlconf.h").exists() or Path(
                "/usr/include/readline/rlconf.h").exists():
            found["gnu"] = self.compiled("gnu")
        if _sdk_has("readline/readline.h"):
            found["edit"] = self.compiled("edit")
        return found

    def test_editing_history_interrupt_and_end(self) -> None:
        for name, command in self.commands().items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                history = Path(tmp) / "history"
                history.write_text("from the file\n", encoding="utf-8")
                term = Terminal(command, self.environment(history))
                term.expect(r"\[EDITING\]")
                term.expect("> ")
                # Ctrl-A moves to the start of the line
                term.send("abc" + CTRL_A + "X\r")
                term.expect(r"\[LINE:Xabc\]")
                # Up (Ctrl-P) recalls the line before, then the one the history
                # file held
                term.expect("> ")
                term.send(CTRL_P + "\r")
                term.expect(r"\[LINE:Xabc\]")
                term.expect("> ")
                term.send(CTRL_P + CTRL_P + CTRL_P + "\r")
                term.expect(r"\[LINE:from the file\]")
                # Ctrl-C abandons the line, and reading goes on
                term.expect("> ")
                term.send("partial" + CTRL_C)
                term.expect(r"\[INT\]")
                term.expect("> ")
                term.send("q\r")
                term.expect(r"\[LINE:q\]")
                # Ctrl-D on an empty line ends the input
                term.expect("> ")
                term.send(CTRL_D)
                term.expect(r"\[EOF\]")
                self.assertEqual(term.wait(), 0)
                self.assertEqual(history.read_text(encoding="utf-8"), "Xabc\nfrom the file\nq\n")

    def test_no_editing_on_a_dumb_terminal(self) -> None:
        for name, command in self.commands().items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                term = Terminal(command, self.environment(Path(tmp) / "history", term="dumb"))
                term.expect(r"\[PLAIN\]")
                term.expect("> ")
                term.send("plain\n")
                term.expect(r"\[LINE:plain\]")
                term.expect("> ")
                term.send(CTRL_D)
                term.expect(r"\[EOF\]")
                self.assertEqual(term.wait(), 0)


class TestReplTerminal(unittest.TestCase):
    """The REPL at a terminal: it starts without -i, edits lines, keeps a
    history in ~/.quest_history, and Ctrl-C abandons the phrase being typed
    (docs/repl.md)."""

    def drivers(self) -> dict[str, list[str]]:
        return {"bootstrap": [sys.executable, str(DRIVER)]}

    def test_editing_history_interrupt_and_end(self) -> None:
        for name, command in self.drivers().items():
            with self.subTest(name), tempfile.TemporaryDirectory() as home:
                history = Path(home) / ".quest_history"
                history.write_text("let a = 4\n", encoding="utf-8")
                env = dict(os.environ, TERM="xterm", HOME=home, QUEST_HOME=str(ROOT_DIR),
                           PYTHONPATH=str(ROOT_DIR / "bootstrap" / "python"))
                term = Terminal(command, env)
                # The history file's line, recalled
                term.expect(">>  ")
                term.send(CTRL_P + "\r")
                term.expect(r"==  let a:Int = 4")
                term.expect(">>  ")
                term.send("* 10" + CTRL_A + "a \r")
                term.expect(r"==  40 : Int")
                # Ctrl-C abandons a phrase continued over lines
                term.expect(">>  ")
                term.send("let f(): Int =\r")
                term.expect("    ")
                term.send("1 +" + CTRL_C)
                term.expect(">>  ")
                term.send("a\r")
                term.expect(r"==  4 : Int")
                term.expect(">>  ")
                term.send(CTRL_D)
                self.assertEqual(term.wait(), 0)
                self.assertEqual(history.read_text(encoding="utf-8"),
                                 "let a = 4\nlet a = 4\na * 10\nlet f(): Int =\na\n")


if __name__ == "__main__":
    unittest.main()
