"""Checks the Jupyter kernel (docs/jupyter.md step 2, tools/jupyter/quest_kernel.py)
through jupyter_client, as a notebook drives it: with a self-hosted driver, the
kernel's info names Quest; cells keep their bindings and show every phrase's
result as one execute_result; a cell's output is a stream ahead of its result;
a failing cell is an error of its kind, its rendering the traceback; an
interrupt during an endless loop restarts the session, as does a cell that
exits, and the next cell runs in the new one; completion, inspection, and
complete input are answered.

It needs jupyter_client and ipykernel, so it runs itself again with
jupyterlab's Python (QUEST_JUPYTER_PYTHON, or Homebrew's), and is skipped,
saying so, when there is none. run_tests.py --self-hosted runs it
(docs/testing.md).

    python tests/self-hosted/jupyter_kernel.py DRIVER
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
JUPYTER_PYTHON = os.environ.get("QUEST_JUPYTER_PYTHON", "/opt/homebrew/opt/jupyterlab/libexec/bin/python")
TIMEOUT = 120


def run(client, code: str) -> tuple[dict, list[tuple[str, dict]]]:
    """Runs a cell: its execute reply's content, and the messages it
    published, but for its status and its input."""
    msg_id = client.execute(code)
    published = []
    while True:
        message = client.get_iopub_msg(timeout=TIMEOUT)
        if message["parent_header"].get("msg_id") != msg_id:
            continue
        kind = message["msg_type"]
        if kind == "status":
            if message["content"]["execution_state"] == "idle":
                break
        elif kind != "execute_input":
            published.append((kind, message["content"]))
    while True:
        reply = client.get_shell_msg(timeout=TIMEOUT)
        if reply["parent_header"].get("msg_id") == msg_id:
            return reply["content"], published


def result(published: list[tuple[str, dict]]) -> object:
    texts = [c["data"]["text/plain"] for kind, c in published if kind == "execute_result"]
    return texts[0] if len(texts) == 1 else texts


def check(driver: str) -> list[str]:
    from jupyter_client.manager import KernelManager

    sys.path.insert(0, str(ROOT_DIR / "tools" / "jupyter"))
    import install

    problems: list[str] = []

    def expect(what: str, actual: object, expected: object) -> None:
        if actual != expected:
            problems.append(f"{what}: expected {expected!r}, got {actual!r}")

    with tempfile.TemporaryDirectory() as d:
        spec = Path(d) / "kernels" / "quest-test"
        spec.mkdir(parents=True)
        (spec / "kernel.json").write_text(json.dumps(install.kernelspec(driver)))
        os.environ["JUPYTER_PATH"] = d
        cwd = Path(d) / "work"
        cwd.mkdir()
        manager = KernelManager(kernel_name="quest-test")
        manager.start_kernel(cwd=str(cwd), env={**os.environ, "QUEST_HOME": str(ROOT_DIR)})
        client = manager.client()
        client.start_channels()
        try:
            client.wait_for_ready(timeout=TIMEOUT)
            client.kernel_info()
            info = client.get_shell_msg(timeout=TIMEOUT)["content"]
            expect("the language", info["language_info"]["name"], "quest")

            reply, published = run(client, "let a = 10")
            expect("a binding", (reply["status"], result(published)), ("ok", "let a:Int = 10"))
            reply, published = run(client, "a * 4; let b = 2")
            expect("two phrases", result(published), "40 : Int\nlet b:Int = 2")
            reply, published = run(client, "let var t = 0; t := 1")
            reply, published = run(client, "t := 2")
            expect("an ok cell", (reply["status"], published), ("ok", []))

            reply, published = run(client, 'import writer: Writer\nwriter.putString(writer.output "hi é\\n")\n7')
            expect("output, then the result", [(k, c.get("name"), c.get("text") or c["data"]["text/plain"])
                                               for k, c in published],
                   [("stream", "stdout", "hi é\n"), ("execute_result", None, "7 : Int")])

            reply, published = run(client, 'let c: Int = "s"')
            expect("a type error", (reply["status"], reply.get("ename"), [k for k, _ in published]),
                   ("error", "type", ["error"]))
            if not any("Type mismatch" in line for line in reply.get("traceback", [])):
                problems.append(f"a type error's traceback: {reply.get('traceback')!r}")

            # Completion, inspection, and complete input
            client.complete("let alpha = a", 13)
            reply = client.get_shell_msg(timeout=TIMEOUT)["content"]
            expect("completion", (reply["matches"], reply["cursor_start"], reply["cursor_end"]),
                   (["a", "and", "andif", "array", "as", "auto"], 12, 13))
            client.inspect("a + 1", 0)
            reply = client.get_shell_msg(timeout=TIMEOUT)["content"]
            expect("inspection", (reply["found"], reply["data"].get("text/plain")), (True, "let a:Int"))
            client.is_complete("let f(): Int =")
            reply = client.get_shell_msg(timeout=TIMEOUT)["content"]
            expect("incomplete input", reply["status"], "incomplete")

            # An interrupt during an endless loop restarts the session
            msg_id = client.execute("let var i = 0\nwhile true do i := i + 1 end")
            time.sleep(2)
            manager.interrupt_kernel()
            while True:
                message = client.get_shell_msg(timeout=30)
                if message["parent_header"].get("msg_id") == msg_id:
                    break
            expect("an interrupt", (message["content"]["status"], message["content"].get("ename")),
                   ("error", "Interrupted"))
            reply, published = run(client, "1 + 1")
            expect("a cell after an interrupt", result(published), "2 : Int")
            reply, published = run(client, "a")
            expect("a binding after an interrupt", reply["status"], "error")

            reply, published = run(client, "import system: System\nsystem.sysexit(3)")
            expect("a cell that exits", (reply["status"], reply.get("ename")), ("error", "DriverExited"))
            reply, published = run(client, "3")
            expect("a cell after an exit", result(published), "3 : Int")
        finally:
            client.stop_channels()
            manager.shutdown_kernel(now=False)
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    driver = str(Path(sys.argv[1]).resolve())
    try:
        import jupyter_client  # noqa: F401
        import ipykernel  # noqa: F401
    except ImportError:
        if os.environ.get("QUEST_JUPYTER_RERUN") or not os.access(JUPYTER_PYTHON, os.X_OK):
            print(f"no Python with Jupyter at {JUPYTER_PYTHON}: the Jupyter kernel not checked")
            sys.exit(0)
        sys.exit(subprocess.run([JUPYTER_PYTHON, __file__, driver],
                                env={**os.environ, "QUEST_JUPYTER_RERUN": "1"}).returncode)
    found = check(driver)
    for problem in found:
        print(problem)
    print(f"jupyter kernel: {len(found)} problems")
    sys.exit(1 if found else 0)
