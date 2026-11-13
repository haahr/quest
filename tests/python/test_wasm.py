"""The WebAssembly encoder and printer (questlang/wasm, docs/wasm-plan.md section 8.1, step 2) agree with wasm-tools and
the engines: the questlang test wasm_encode prints a corpus of modules built by hand, each as its text and, in comments
after it, the encoder's bytes in hex. For each, wasm-tools parse of the text must be those bytes and they must validate;
the module marked run is a WASI command, which wasmtime and node must each run, writing what the golden's expect lines
say. Skipped where wasm-tools, wasmtime, or node is missing."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN = ROOT / "tests" / "golden" / "run" / "questlang" / "wasm_encode.out"

# wasmtime's features for the backend's modules, and its collector (docs/wasm-plan.md section 1)
WASMTIME = ["wasmtime", "run", "-W", "gc=y,function-references=y,tail-call=y,exceptions=y", "-C", "collector=copying"]

# A WASI command in node, with only the fd_write it imports, writing to standard output
NODE_HOST = r"""
const fs = require("fs");
const bytes = fs.readFileSync(process.argv[2]);
let memory;
const imports = {wasi_snapshot_preview1: {fd_write(fd, iovs, count, written) {
  const view = new DataView(memory.buffer);
  let total = 0;
  for (let i = 0; i < count; i++) {
    const base = view.getUint32(iovs + 8 * i, true), length = view.getUint32(iovs + 8 * i + 4, true);
    fs.writeSync(fd, new Uint8Array(memory.buffer, base, length));
    total += length;
  }
  view.setUint32(written, total, true);
  return 0;
}}};
WebAssembly.instantiate(bytes, imports).then(({instance}) => {
  memory = instance.exports.memory;
  instance.exports._start();
});
"""


class Module:
    """One module of the golden: its kind (module or run), its label, its text, and its bytes"""

    def __init__(self, kind: str, label: str) -> None:
        self.kind = kind
        self.label = label
        self.text: list[str] = []
        self.hex: list[str] = []


def corpus() -> tuple[list[Module], str]:
    """The golden's modules, and the output its expect lines give the one to run"""
    modules: list[Module] = []
    expected = []
    in_bytes = False
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        header = re.fullmatch(r";; (module|run) (\S+)", line)
        if header:
            modules.append(Module(header.group(1), header.group(2)))
            in_bytes = False
        elif line == ";; bytes":
            in_bytes = True
        elif line.startswith(";; expect "):
            expected.append(line[len(";; expect "):] + "\n")
        elif in_bytes:
            modules[-1].hex.append(line[2:].replace(" ", ""))
        else:
            modules[-1].text.append(line)
    return modules, "".join(expected)


def tool(name: str) -> bool:
    return shutil.which(name) is not None


@unittest.skipUnless(tool("wasm-tools"), "wasm-tools is not installed")
class TestWasm(unittest.TestCase):
    def setUp(self) -> None:
        self.modules, self.expected = corpus()
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)

    def write(self, module: Module) -> Path:
        path = Path(self.scratch.name) / f"{module.label}.wasm"
        path.write_bytes(bytes.fromhex("".join(module.hex)))
        return path

    def test_the_corpus_is_there(self) -> None:
        labels = [m.label for m in self.modules]
        self.assertEqual(labels, ["empty", "runtime", "numbers", "gc", "control", "indices", "run"])
        self.assertEqual(self.expected, "500000500000\n42\n7\n")

    def test_the_bytes_are_the_texts(self) -> None:
        for module in self.modules:
            with self.subTest(module=module.label):
                text = "\n".join(module.text) + "\n"
                parsed = subprocess.run(["wasm-tools", "parse", "-"], input=text.encode(), capture_output=True)
                self.assertEqual(parsed.returncode, 0, parsed.stderr.decode())
                self.assertEqual(parsed.stdout.hex(), "".join(module.hex))

    def test_every_module_validates(self) -> None:
        for module in self.modules:
            with self.subTest(module=module.label):
                checked = subprocess.run(["wasm-tools", "validate", str(self.write(module))], capture_output=True,
                                         text=True)
                self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_a_malformed_module_fails(self) -> None:
        # The check can fail: a function whose body adds an i64 to an i32 parses but does not validate
        module = next(m for m in self.modules if m.label == "numbers")
        text = "\n".join(module.text).replace("i64.add", "i32.add", 1)
        path = Path(self.scratch.name) / "broken.wasm"
        parsed = subprocess.run(["wasm-tools", "parse", "-", "-o", str(path)], input=text.encode(), capture_output=True)
        self.assertEqual(parsed.returncode, 0, parsed.stderr.decode())
        checked = subprocess.run(["wasm-tools", "validate", str(path)], capture_output=True)
        self.assertNotEqual(checked.returncode, 0)

    @unittest.skipUnless(tool("wasmtime"), "wasmtime is not installed")
    def test_wasmtime_runs_it(self) -> None:
        module = next(m for m in self.modules if m.kind == "run")
        ran = subprocess.run(WASMTIME + [str(self.write(module))], capture_output=True, text=True, timeout=60)
        self.assertEqual(ran.returncode, 0, ran.stderr)
        self.assertEqual(ran.stdout, self.expected)

    @unittest.skipUnless(tool("node"), "node is not installed")
    def test_node_runs_it(self) -> None:
        module = next(m for m in self.modules if m.kind == "run")
        host = Path(self.scratch.name) / "host.js"
        host.write_text(NODE_HOST)
        ran = subprocess.run(["node", str(host), str(self.write(module))], capture_output=True, text=True, timeout=60)
        self.assertEqual(ran.returncode, 0, ran.stderr)
        self.assertEqual(ran.stdout, self.expected)


if __name__ == "__main__":
    unittest.main()
