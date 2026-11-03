"""The Jupyter kernel for Quest (docs/jupyter-kernel.md): an ipykernel kernel
that runs each cell in a session of the self-hosted driver's kernel mode
(quest_session.py), started when the kernel starts and again after it ends.

The driver is QUEST_KERNEL_DRIVER, which tools/jupyter/install sets to the
checkout's ./quest. It runs under jupyterlab's own Python, which has ipykernel:

    python quest_kernel.py -f CONNECTION_FILE
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ipykernel.kernelbase import Kernel, StdinNotImplementedError  # noqa: E402

from quest_session import DriverExited, Session  # noqa: E402

RESTARTED = "the session restarted, and its bindings are gone"


class QuestKernel(Kernel):
    implementation = "quest"
    implementation_version = "0.1"
    banner = "Quest, through the self-hosted driver's JIT"
    language_info = {
        "name": "quest",
        "mimetype": "text/x-quest",
        "file_extension": ".quest",
        "pygments_lexer": "quest",
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.quest_session: Optional[Session] = None

    def driver(self) -> list[str]:
        """The driver's command: QUEST_KERNEL_DRIVER, with any options in
        QUEST_KERNEL_OPTIONS (--no-jit, say)."""
        driver = os.environ.get("QUEST_KERNEL_DRIVER")
        if not driver:
            raise RuntimeError("QUEST_KERNEL_DRIVER does not name a Quest driver (run tools/jupyter/install)")
        return [driver, *os.environ.get("QUEST_KERNEL_OPTIONS", "").split()]

    def quest(self) -> Session:
        """The session, started if there is none."""
        if self.quest_session is None:
            self.quest_session = Session(self.driver())
        return self.quest_session

    def end_session(self) -> None:
        if self.quest_session is not None:
            self.quest_session.kill()
            self.quest_session = None

    def stream(self, name: str, text: str) -> None:
        self.send_response(self.iopub_socket, "stream", {"name": name, "text": text})

    def failed(self, ename: str, evalue: str, traceback: list[str]) -> dict:
        """The reply of a cell that failed, its error published too."""
        content = {"ename": ename, "evalue": evalue, "traceback": traceback}
        self.send_response(self.iopub_socket, "error", content)
        return {"status": "error", "execution_count": self.execution_count, **content}

    async def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False,
                         *, cell_meta=None, cell_id=None):
        on_stream = None if silent else self.stream

        def on_display(bundle: dict) -> None:
            if not silent:
                self.send_response(self.iopub_socket, "display_data", {"data": bundle, "metadata": {}})

        # raw_input asks the notebook only if the request allows it, as
        # ipykernel's own kernel arranges
        self._allow_stdin = allow_stdin

        def on_input(prompt: str) -> Optional[str]:
            if not allow_stdin:
                return None
            try:
                return self.raw_input(prompt)
            except (EOFError, StdinNotImplementedError):
                return None

        try:
            reply = self.quest().execute(code, on_stream, on_display, on_input)
        except KeyboardInterrupt:
            # The cell didn't end when interrupted
            self.end_session()
            return self.failed("Interrupted", f"the cell did not stop when interrupted; {RESTARTED}", [
                f"Interrupted: the cell did not stop when interrupted; {RESTARTED}"])
        except DriverExited as e:
            self.quest_session = None
            lines = [f"DriverExited: the Quest driver exited with status {e.status}; {RESTARTED}"]
            if e.stderr.strip():
                lines += ["", *e.stderr.rstrip().splitlines()]
            return self.failed("DriverExited", f"the Quest driver exited with status {e.status}; {RESTARTED}", lines)
        if reply.error is not None:
            error = reply.error
            return self.failed(error["error"], error["message"], error["rendered"].rstrip("\n").split("\n"))
        if reply.results and not silent:
            self.send_response(self.iopub_socket, "execute_result", {
                "execution_count": self.execution_count,
                "data": {"text/plain": "\n".join(reply.results)},
                "metadata": {},
            })
        return {"status": "ok", "execution_count": self.execution_count, "payload": [], "user_expressions": {}}

    async def do_complete(self, code, cursor_pos):
        try:
            matches, start, end = self.quest().complete(code, cursor_pos)
        except DriverExited:
            self.quest_session = None
            matches, start, end = [], cursor_pos, cursor_pos
        return {"status": "ok", "matches": matches, "cursor_start": start, "cursor_end": end, "metadata": {}}

    async def do_inspect(self, code, cursor_pos, detail_level=0, omit_sections=()):
        try:
            text = self.quest().inspect(code, cursor_pos)
        except DriverExited:
            self.quest_session = None
            text = None
        return {"status": "ok", "found": text is not None, "data": {"text/plain": text} if text else {},
                "metadata": {}}

    async def do_is_complete(self, code):
        try:
            complete = self.quest().is_complete(code)
        except DriverExited:
            self.quest_session = None
            return {"status": "unknown"}
        return {"status": "complete"} if complete else {"status": "incomplete", "indent": "    "}

    async def do_shutdown(self, restart):
        self.end_session()
        return {"status": "ok", "restart": restart}


if __name__ == "__main__":
    from ipykernel.kernelapp import IPKernelApp

    IPKernelApp.launch_instance(kernel_class=QuestKernel)
