"""Runs heavy work one job at a time on this machine, on a quiet machine
(docs/testing.md section 4.2).

    tools/exclusive COMMAND...    wait for the lock and a quiet machine,
                                  run COMMAND, and release the lock
    tools/exclusive --no-quiet COMMAND...
                                  the same, not waiting for a quiet machine
    tools/exclusive --status      who holds the lock, and who waits for it

Every worktree of the repository shares one lock, quest-exclusive.lock in the
git common directory (as the releases share quest-release there), so sessions
in different worktrees take turns. The holder, once it has the lock, waits
until the 1-minute load average has stayed under 5 for 3 minutes, so that
what it runs (tools/check, run.py time) is timed and timed out on a machine
doing nothing else.

tools/check, benchmarks/mlton/run.py time, and tools/release's cuts take the
lock themselves (unless given --no-exclusive); ./quest's stage builds,
run_tests.py, run.py's other commands, and allocations.py yield to it, waiting
while another job holds it.
A job run under the lock passes QUEST_EXCLUSIVE_HELD to what it starts, so
that nothing it runs waits on the lock it holds.

The lock is a flock, so it is released when its holder's process ends, however
it ends. A status file beside it, quest-exclusive.json, says who holds it and
who waits, for --status and for the messages of those waiting; an entry whose
process has ended is dropped when the file is next read.

For tests, QUEST_EXCLUSIVE_DIR moves the lock and status files, and
QUEST_EXCLUSIVE_LOAD, QUEST_EXCLUSIVE_QUIET_SECONDS, and
QUEST_EXCLUSIVE_INTERVAL change the quiet machine's load bound, how long it
must hold, and how often it is sampled.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Iterator

ROOT_DIR = Path(__file__).resolve().parent.parent
# Set in the environment of what runs under the lock: the holder's pid
HELD_VARIABLE = "QUEST_EXCLUSIVE_HELD"


def lock_dir() -> Path:
    """Where the lock and status files are: QUEST_EXCLUSIVE_DIR, or the git
    common directory, which every worktree shares (the repository's own
    directory if git cannot say)."""
    if os.environ.get("QUEST_EXCLUSIVE_DIR"):
        return Path(os.environ["QUEST_EXCLUSIVE_DIR"])
    process = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, cwd=ROOT_DIR)
    if process.returncode == 0 and process.stdout.strip():
        common = Path(process.stdout.strip())
        return common if common.is_absolute() else (ROOT_DIR / common).resolve()
    return ROOT_DIR / ".build"


def held_here() -> bool:
    """Whether this process runs under the lock, held by itself or by a job
    that started it."""
    return bool(os.environ.get(HELD_VARIABLE))


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextlib.contextmanager
def _status(directory: Path) -> Iterator[dict]:
    """The status, {"holder": entry or None, "waiting": [entries]}, to read or
    change, the change written back when the block ends; entries whose
    process has ended are dropped. A lock of its own keeps two changes from
    interleaving."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "quest-exclusive.json"
    with open(directory / "quest-exclusive.status.lock", "a") as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        try:
            status = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            status = {}
        holder = status.get("holder")
        status = {"holder": holder if holder and alive(holder["pid"]) else None,
                  "waiting": [e for e in status.get("waiting", []) if alive(e["pid"])]}
        yield status
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(status, indent=1) + "\n", encoding="utf-8")
        temporary.replace(path)


def read_status(directory: Path | None = None) -> dict:
    with _status(directory or lock_dir()) as status:
        return status


def describe(entry: dict) -> str:
    since = time.strftime("%H:%M:%S", time.localtime(entry["since"]))
    return f"{entry['command']} (pid {entry['pid']}, in {entry['worktree']}, since {since})"


def _entry(command: str) -> dict:
    return {"pid": os.getpid(), "worktree": str(ROOT_DIR), "command": command, "since": time.time()}


def quiet_bound() -> tuple[float, float, float]:
    """The load the machine must stay under, for how many seconds, sampled how
    often."""
    return (float(os.environ.get("QUEST_EXCLUSIVE_LOAD", "5")),
            float(os.environ.get("QUEST_EXCLUSIVE_QUIET_SECONDS", "180")),
            float(os.environ.get("QUEST_EXCLUSIVE_INTERVAL", "10")))


def wait_until_quiet(say: Callable[[str], None], load: Callable[[], float] = lambda: os.getloadavg()[0]) -> None:
    """Returns once the 1-minute load average has stayed under the bound for
    the bound's time, sampled at its interval."""
    bound, hold, interval = quiet_bound()
    quiet_since: float | None = None
    announced = False
    while True:
        now = time.monotonic()
        if load() < bound:
            if quiet_since is None:
                quiet_since = now
            if now - quiet_since >= hold:
                return
        else:
            quiet_since = None
            if not announced:
                say(f"waiting for the load to stay under {bound:g} for {hold:g} s (it is {load():.1f})")
                announced = True
        time.sleep(interval)


@contextlib.contextmanager
def exclusive(command: str, quiet: bool = True, say: Callable[[str], None] | None = None) -> Iterator[None]:
    """Holds the machine-wide lock, and with quiet, a quiet machine, while the
    block runs: waits its turn, saying behind whom, and then for the machine to
    be quiet. Does nothing if this process already runs under the lock."""
    if say is None:
        def say(message: str) -> None:
            print(f"exclusive: {message}", file=sys.stderr, flush=True)
    if held_here():
        yield
        return
    directory = lock_dir()
    directory.mkdir(parents=True, exist_ok=True)
    me = _entry(command)
    with open(directory / "quest-exclusive.lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            with _status(directory) as status:
                status["waiting"].append(me)
                holder = status["holder"]
            say("waiting behind " + (describe(holder) if holder else "a job that has not said what it is"))
            fcntl.flock(lock, fcntl.LOCK_EX)
        with _status(directory) as status:
            status["waiting"] = [e for e in status["waiting"] if e["pid"] != me["pid"]]
            status["holder"] = me
        os.environ[HELD_VARIABLE] = str(os.getpid())
        try:
            if quiet:
                wait_until_quiet(say)
            yield
        finally:
            del os.environ[HELD_VARIABLE]
            with _status(directory) as status:
                if status["holder"] and status["holder"]["pid"] == me["pid"]:
                    status["holder"] = None
            fcntl.flock(lock, fcntl.LOCK_UN)


def yield_to_holder(what: str, say: Callable[[str], None] | None = None) -> None:
    """Waits while another job holds the lock, so that heavy work started
    outside it (a build, a test run) does not load the machine it is timing.
    Returns at once under the lock, or when no one holds it."""
    if held_here():
        return
    directory = lock_dir()
    path = directory / "quest-exclusive.lock"
    if not path.exists():
        return
    with open(path, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            holder = read_status(directory)["holder"]
            message = f"{what} waits while " + (describe(holder) if holder else "another job") + " holds the lock"
            if say is None:
                print(f"exclusive: {message}", file=sys.stderr, flush=True)
            else:
                say(message)
            fcntl.flock(lock, fcntl.LOCK_SH)
        fcntl.flock(lock, fcntl.LOCK_UN)


def print_status() -> None:
    status = read_status()
    print("holder: " + (describe(status["holder"]) if status["holder"] else "none"))
    for entry in status["waiting"]:
        print("waiting: " + describe(entry))


def main(argv: list[str]) -> int:
    if argv[:1] == ["--status"]:
        print_status()
        return 0
    if argv[:1] == ["--yield"]:
        yield_to_holder(" ".join(argv[1:]) or "this job")
        return 0
    quiet = True
    if argv[:1] == ["--no-quiet"]:
        quiet = False
        argv = argv[1:]
    if not argv or argv[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    with exclusive(" ".join(argv), quiet=quiet):
        return subprocess.run(argv).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
