"""A client of the Quest language server (docs/lsp.md section 10), for
tests/python/test_lsp.py and for trying the server by hand: it starts the
server, frames and unframes messages, answers nothing the server asks, and
keeps the notifications it is sent."""

import json
import subprocess
import threading
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Optional


def uri_of(path: Path) -> str:
    return Path(path).resolve().as_uri()


class Client:
    def __init__(self, command: list, env: Optional[dict] = None, cwd: Optional[str] = None):
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, env=env, cwd=cwd)
        self.next_id = 0
        self.messages: Queue = Queue()
        self.notifications: list = []
        self.stderr: list = []
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read(self) -> None:
        out = self.process.stdout
        while True:
            length = None
            while True:
                line = out.readline()
                if not line:
                    self.messages.put(None)
                    return
                line = line.strip()
                if not line:
                    break
                name, _, value = line.decode("ascii").partition(":")
                if name.lower() == "content-length":
                    length = int(value.strip())
            body = out.read(length)
            self.messages.put(json.loads(body.decode("utf-8")))

    def _read_stderr(self) -> None:
        for line in self.process.stderr:
            self.stderr.append(line.decode("utf-8", "replace"))

    def send(self, message: dict) -> None:
        body = json.dumps(message, ensure_ascii=False).encode("utf-8")
        self.process.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        self.process.stdin.flush()

    def notify(self, method: str, params: Any) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method: str, params: Any, timeout: float = 120.0) -> dict:
        """The response to a request, keeping the notifications that come
        before it"""
        self.next_id += 1
        ident = self.next_id
        self.send({"jsonrpc": "2.0", "id": ident, "method": method, "params": params})
        while True:
            message = self.messages.get(timeout=timeout)
            if message is None:
                raise EOFError("the server ended: " + "".join(self.stderr))
            if message.get("id") == ident and "method" not in message:
                return message
            self.notifications.append(message)

    def result(self, method: str, params: Any) -> Any:
        response = self.request(method, params)
        if "error" in response:
            raise RuntimeError(f"{method}: {response['error']}")
        return response["result"]

    def diagnostics(self, uri: str, timeout: float = 120.0) -> list:
        """The next diagnostics published for uri, from those kept or to come"""
        while True:
            for i, n in enumerate(self.notifications):
                if n.get("method") == "textDocument/publishDiagnostics" and n["params"]["uri"] == uri:
                    del self.notifications[i]
                    return n["params"]["diagnostics"]
            try:
                message = self.messages.get(timeout=timeout)
            except Empty:
                raise TimeoutError(f"no diagnostics for {uri}")
            if message is None:
                raise EOFError("the server ended: " + "".join(self.stderr))
            self.notifications.append(message)

    def initialize(self, root: Path, encodings=("utf-16",), options: Optional[dict] = None) -> dict:
        params = {"processId": None, "rootUri": uri_of(root),
                  "capabilities": {"general": {"positionEncodings": list(encodings)}}}
        if options is not None:
            params["initializationOptions"] = options
        result = self.result("initialize", params)
        self.notify("initialized", {})
        return result

    def open(self, path: Path, text: str, version: int = 1) -> str:
        uri = uri_of(path)
        self.notify("textDocument/didOpen",
                    {"textDocument": {"uri": uri, "languageId": "quest", "version": version, "text": text}})
        return uri

    def change(self, uri: str, text: str, version: int) -> None:
        self.notify("textDocument/didChange",
                    {"textDocument": {"uri": uri, "version": version}, "contentChanges": [{"text": text}]})

    def at(self, method: str, uri: str, line: int, character: int, **extra) -> Any:
        params = {"textDocument": {"uri": uri}, "position": {"line": line, "character": character}}
        params.update(extra)
        return self.result(method, params)

    def close(self, timeout: float = 30.0) -> int:
        self.result("shutdown", None)
        self.notify("exit", None)
        code = self.process.wait(timeout=timeout)
        self.dispose()
        return code

    def dispose(self) -> None:
        """Ends the server if it is still running, and closes its pipes"""
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            try:
                stream.close()
            except OSError:
                pass
