"""The Jupyter kernel for Quest (docs/jupyter.md): an ipykernel kernel that runs
each cell in a session of the self-hosted driver's kernel mode
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

from ipykernel.kernelbase import Kernel  # noqa: E402

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
        try:
            reply = self.quest().execute(code, on_stream)
        except KeyboardInterrupt:
            self.end_session()
            return self.failed("Interrupted", f"the cell was interrupted; {RESTARTED}", [
                f"Interrupted: the cell was interrupted; {RESTARTED}"])
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

    async def do_shutdown(self, restart):
        self.end_session()
        return {"status": "ok", "restart": restart}


if __name__ == "__main__":
    from ipykernel.kernelapp import IPKernelApp

    IPKernelApp.launch_instance(kernel_class=QuestKernel)
