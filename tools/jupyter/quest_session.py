"""A session of the self-hosted driver's kernel mode (docs/jupyter.md section 2):
`quest --kernel` started with its requests on descriptor 3 and its records on
descriptor 4, cells sent to it one at a time, and what each wrote collected as
it comes. The Jupyter kernel (quest_kernel.py) and the protocol's test
(tests/self-hosted/kernel_protocol.py) share it; it needs only the standard
library.

The protocol's strings are bytes, each above 126 escaped as \\u00XX, so text is
sent as its UTF-8 bytes and decoded from them."""

from __future__ import annotations

import codecs
import fcntl
import json
import os
import selectors
import signal
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Optional

# A stream's text as it arrives: the stream's name (stdout or stderr), and the
# text
StreamHandler = Callable[[str, str], None]


@dataclass
class Reply:
    """What a cell did: its phrases' results, its error record if it failed,
    and its status (ok or error)."""

    results: list[str] = field(default_factory=list)
    error: Optional[dict] = None
    status: str = "ok"


class DriverExited(Exception):
    """The driver ended before the cell was done: a crash, say, or a cell that
    called system.sysexit. Its exit status (a signal's negated number if one
    killed it), and the last of its standard error."""

    def __init__(self, status: int, stderr: str) -> None:
        super().__init__(f"the Quest driver exited with status {status}")
        self.status = status
        self.stderr = stderr


def to_bytes_text(text: str) -> str:
    """text's UTF-8 bytes, a character each, as the protocol's strings are."""
    return text.encode("utf-8").decode("latin-1")


def from_bytes_text(text: str) -> str:
    """The text whose UTF-8 bytes are text's characters."""
    return text.encode("latin-1").decode("utf-8", "replace")


def decoded(value: object) -> object:
    """A record's value, its strings decoded from bytes."""
    if isinstance(value, str):
        return from_bytes_text(value)
    if isinstance(value, dict):
        return {k: decoded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decoded(v) for v in value]
    return value


class Session:
    """A driver in kernel mode, in a process group of its own, so that ending
    it ends whatever it started too."""

    def __init__(self, command: list[str], cwd: Optional[str] = None,
                 env: Optional[dict[str, str]] = None) -> None:
        requests_read, requests_write = os.pipe()
        records_read, records_write = os.pipe()
        # Above any descriptor the child could be given, so that placing them
        # at 3 and 4 overwrites neither
        high_read = fcntl.fcntl(requests_read, fcntl.F_DUPFD_CLOEXEC, 10)
        high_write = fcntl.fcntl(records_write, fcntl.F_DUPFD_CLOEXEC, 10)

        def place() -> None:
            os.dup2(high_read, 3)
            os.dup2(high_write, 4)

        environment = dict(os.environ if env is None else env)
        environment["QUEST_LINE_BUFFERED"] = "1"
        try:
            self.process = subprocess.Popen(
                [*command, "--kernel"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, pass_fds=(3, 4), preexec_fn=place, start_new_session=True,
                cwd=cwd, env=environment)
        finally:
            for fd in (requests_read, records_write, high_read, high_write):
                os.close(fd)
        self.requests = os.fdopen(requests_write, "wb", buffering=0)
        self.records = records_read
        for fd in (self.process.stdout.fileno(), self.process.stderr.fileno(), self.records):
            os.set_blocking(fd, False)
        self.decoders = {name: codecs.getincrementaldecoder("utf-8")("replace") for name in ("stdout", "stderr")}
        self.pending = b""
        # The last of standard error, for DriverExited
        self.stderr_tail = ""
        self.closed = False

    def _drain(self, name: str, fd: int, on_stream: Optional[StreamHandler]) -> bool:
        """Reads what fd holds now, passing it on; whether fd has ended."""
        ended = False
        chunks = []
        while True:
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                break
            if not chunk:
                ended = True
                break
            chunks.append(chunk)
        text = self.decoders[name].decode(b"".join(chunks), final=ended)
        if text:
            if name == "stderr":
                self.stderr_tail = (self.stderr_tail + text)[-4000:]
            if on_stream is not None:
                on_stream(name, text)
        return ended

    def _drain_streams(self, on_stream: Optional[StreamHandler]) -> None:
        self._drain("stdout", self.process.stdout.fileno(), on_stream)
        self._drain("stderr", self.process.stderr.fileno(), on_stream)

    def request(self, message: dict, on_stream: Optional[StreamHandler] = None) -> list[dict]:
        """Sends a request, and returns its records, through its done record;
        what the driver writes meanwhile goes to on_stream, ahead of any record
        written after it. Raises DriverExited if the driver ends first."""
        line = json.dumps({k: to_bytes_text(v) if isinstance(v, str) else v for k, v in message.items()})
        try:
            self.requests.write(line.encode("ascii") + b"\n")
        except BrokenPipeError:
            pass  # Reported below, once the driver's end is seen
        records: list[dict] = []
        selector = selectors.DefaultSelector()
        streams = {self.process.stdout.fileno(): "stdout", self.process.stderr.fileno(): "stderr"}
        for fd in streams:
            selector.register(fd, selectors.EVENT_READ)
        selector.register(self.records, selectors.EVENT_READ)
        try:
            while True:
                for key, _ in selector.select():
                    fd = key.fd
                    if fd in streams:
                        if self._drain(streams[fd], fd, on_stream):
                            selector.unregister(fd)
                        continue
                    try:
                        chunk = os.read(fd, 65536)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        self.process.wait()
                        self._drain_streams(on_stream)
                        raise DriverExited(self.process.returncode, self.stderr_tail)
                    self.pending += chunk
                    while b"\n" in self.pending:
                        text, self.pending = self.pending.split(b"\n", 1)
                        # What the driver wrote before the record is in its
                        # pipes already, since it flushes before each record
                        self._drain_streams(on_stream)
                        record = decoded(json.loads(text.decode("ascii")))
                        records.append(record)
                        if "done" in record:
                            return records
        finally:
            selector.close()

    def execute(self, code: str, on_stream: Optional[StreamHandler] = None) -> Reply:
        """Runs a cell (request)."""
        reply = Reply()
        for record in self.request({"execute": code}, on_stream):
            if "result" in record:
                reply.results.append(record["result"])
            elif "done" in record:
                reply.status = record["done"]
            elif "error" in record:
                reply.error = record
        return reply

    def kill(self) -> None:
        """Ends the driver and everything it started."""
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.close()

    def close(self) -> int:
        """Ends the driver's requests, and waits for it to exit; its status."""
        if self.closed:
            return self.process.returncode
        self.closed = True
        try:
            self.requests.close()
        except BrokenPipeError:
            pass
        status = self.process.wait()
        os.close(self.records)
        self.process.stdout.close()
        self.process.stderr.close()
        return status
