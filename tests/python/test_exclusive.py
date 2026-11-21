"""tools/exclusive (docs/testing.md section 4.2): the machine-wide lock
serializes its jobs, its status names the holder and the waiters and drops
entries whose process has ended, a job under the lock neither waits on it
nor yields to it, a job outside it yields while another holds it, the quiet
wait holds out for its time, and tools/check picks the failures to run again
alone."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EXCLUSIVE = ROOT / "tools" / "exclusive.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(ROOT / "tools"))
exclusive = load("exclusive", EXCLUSIVE)
check = load("tools_check", ROOT / "tools" / "check.py")

# A job that records when it starts and ends, holding the lock a while
RECORD = """
import sys, time
with open(sys.argv[1], "a") as f:
    f.write(f"start {time.time()}\\n")
time.sleep(float(sys.argv[2]))
with open(sys.argv[1], "a") as f:
    f.write(f"end {time.time()}\\n")
"""


class TestExclusive(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.dir = Path(self.directory.name)
        self.saved = {name: os.environ.get(name) for name in ("QUEST_EXCLUSIVE_DIR", exclusive.HELD_VARIABLE)}
        os.environ["QUEST_EXCLUSIVE_DIR"] = str(self.dir)
        os.environ.pop(exclusive.HELD_VARIABLE, None)
        self.environment = {**os.environ}

    def tearDown(self) -> None:
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.directory.cleanup()

    def start(self, *arguments: str) -> subprocess.Popen:
        return subprocess.Popen([sys.executable, str(EXCLUSIVE), *arguments], env=self.environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def wait_for(self, condition, seconds: float = 10.0) -> None:
        deadline = time.monotonic() + seconds
        while not condition():
            if time.monotonic() > deadline:
                self.fail("timed out waiting")
            time.sleep(0.05)

    def test_jobs_take_turns(self) -> None:
        log = self.dir / "log"
        jobs = [self.start("--no-quiet", sys.executable, "-c", RECORD, str(log), "0.5") for _ in range(3)]
        for job in jobs:
            job.communicate(timeout=30)
            self.assertEqual(job.returncode, 0)
        events = [line.split() for line in log.read_text().splitlines()]
        self.assertEqual([kind for kind, _ in events], ["start", "end"] * 3)
        times = [float(t) for _, t in events]
        self.assertEqual(times, sorted(times))

    def test_status_names_holder_and_waiters(self) -> None:
        log = self.dir / "log"
        holder = self.start("--no-quiet", sys.executable, "-c", RECORD, str(log), "3")
        self.wait_for(lambda: log.exists())
        waiter = self.start("--no-quiet", sys.executable, "-c", "pass")
        self.wait_for(lambda: exclusive.read_status(self.dir)["waiting"])
        status = exclusive.read_status(self.dir)
        self.assertIn("-c", status["holder"]["command"])
        self.assertEqual(status["holder"]["worktree"], str(ROOT))
        self.assertEqual([entry["pid"] for entry in status["waiting"]], [waiter.pid])
        _, waited = waiter.communicate(timeout=30)
        self.assertIn("waiting behind", waited)
        holder.communicate(timeout=30)
        status = exclusive.read_status(self.dir)
        self.assertIsNone(status["holder"])
        self.assertEqual(status["waiting"], [])

    def test_ended_processes_are_dropped(self) -> None:
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        entry = {"pid": dead.pid, "worktree": "w", "command": "c", "since": 0}
        (self.dir / "quest-exclusive.json").write_text(json.dumps({"holder": entry, "waiting": [entry]}))
        self.assertEqual(exclusive.read_status(self.dir), {"holder": None, "waiting": []})

    def test_a_job_under_the_lock_does_not_wait_on_it(self) -> None:
        log = self.dir / "log"
        holder = self.start("--no-quiet", sys.executable, "-c", RECORD, str(log), "3")
        self.wait_for(lambda: log.exists())
        os.environ[exclusive.HELD_VARIABLE] = "1"
        began = time.monotonic()
        with exclusive.exclusive("nested", quiet=False, say=lambda message: None):
            pass
        exclusive.yield_to_holder("nested", say=lambda message: None)
        self.assertLess(time.monotonic() - began, 1.0)
        holder.communicate(timeout=30)

    def test_a_job_outside_the_lock_yields_to_its_holder(self) -> None:
        exclusive.yield_to_holder("nothing held", say=lambda message: self.fail(message))
        log = self.dir / "log"
        holder = self.start("--no-quiet", sys.executable, "-c", RECORD, str(log), "1.5")
        self.wait_for(lambda: log.exists())
        said = []
        exclusive.yield_to_holder("a build", say=said.append)
        self.assertTrue(said and "a build waits while" in said[0])
        self.assertIn("end", log.read_text())
        holder.communicate(timeout=30)

    def test_the_quiet_wait_holds_out_for_its_time(self) -> None:
        os.environ.update({"QUEST_EXCLUSIVE_LOAD": "5", "QUEST_EXCLUSIVE_QUIET_SECONDS": "0.3",
                           "QUEST_EXCLUSIVE_INTERVAL": "0.05"})
        try:
            loads = iter([9.0, 2.0, 9.0] + [1.0] * 1000)
            samples = []

            def load() -> float:
                value = next(loads)
                samples.append(value)
                return value
            began = time.monotonic()
            said = []
            exclusive.wait_until_quiet(said.append, load)
            self.assertGreaterEqual(time.monotonic() - began, 0.3)
            self.assertTrue(said)
            self.assertGreater(len(samples), 6)
        finally:
            for name in ("QUEST_EXCLUSIVE_LOAD", "QUEST_EXCLUSIVE_QUIET_SECONDS", "QUEST_EXCLUSIVE_INTERVAL"):
                os.environ.pop(name, None)


class TestRerunSelection(unittest.TestCase):
    def test_only_timeouts_are_run_again(self) -> None:
        timeouts = ("--- Phase: run_c_compiled ---\n  [PASS] run_c_compiled:a\n"
                    "  [FAIL] run_c_compiled:stdlib/slow\n  (TIMED OUT after 30.0s)\n"
                    "  [FAIL] interpret:x/y\n  (TIMED OUT after 30.0s)\nSummary: 1/3 tests passed.\n")
        self.assertEqual(check.timed_out(timeouts), [("run_c_compiled", "stdlib/slow"), ("interpret", "x/y")])
        mixed = timeouts + "  [FAIL] parse:z\n  (stdout mismatch)\n"
        self.assertIsNone(check.timed_out(mixed))
        self.assertIsNone(check.timed_out("Traceback (most recent call last):\n"))

    def test_a_test_runs_again_alone(self) -> None:
        command = ["python", "run_tests.py", "--self-hosted", "--backend", "ssac,arm64", "-j", "4", "-k", "old"]
        self.assertEqual(check.alone(command, "run_c_compiled", "stdlib/slow"),
                         ["python", "run_tests.py", "--self-hosted", "--backend", "ssac,arm64",
                          "--phase", "run_c_compiled", "-k", "stdlib/slow", "-j", "1"])


if __name__ == "__main__":
    unittest.main()
