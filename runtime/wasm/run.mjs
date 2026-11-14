// Runs a program the wasm backend compiled (docs/wasm-plan.md, step 3) in node:
//
//     node run.mjs [--module NAME=UNIT.wasm]... RUNTIME.wasm PROGRAM.wasm [ARG...]
//
// The runtime module (questlang/wasm/runtime) is instantiated first, over the
// part of WASI's first preview it imports, then each unit's module, named by
// its canonical name, in the order given, which puts each after those it
// imports, and last the program's, each over the exports of those before it,
// as wasmtime's --preload links them; then the program's _start runs. Bytes
// cross through the runtime's memory (section 4.4 of the plan): fd_write
// writes each iovec's bytes to its descriptor, and proc_exit ends the process
// with its status.

import fs from "node:fs";

const args = process.argv.slice(2);
const units = [];
while (args[0] === "--module") {
  const [name, path] = args[1].split("=");
  units.push({name, path});
  args.splice(0, 2);
}
const [runtimePath, programPath] = args;
if (!runtimePath || !programPath) {
  process.stderr.write("usage: node run.mjs [--module NAME=UNIT.wasm]... RUNTIME.wasm PROGRAM.wasm [ARG...]\n");
  process.exit(2);
}

let memory;
const wasi = {
  fd_write(fd, iovs, count, written) {
    const view = new DataView(memory.buffer);
    let total = 0;
    for (let i = 0; i < count; i++) {
      const base = view.getUint32(iovs + 8 * i, true);
      const length = view.getUint32(iovs + 8 * i + 4, true);
      fs.writeSync(fd, new Uint8Array(memory.buffer, base, length));
      total += length;
    }
    view.setUint32(written, total, true);
    return 0;
  },
  proc_exit(code) {
    process.exit(code);
  },
};

const runtime = await WebAssembly.instantiate(fs.readFileSync(runtimePath), {wasi_snapshot_preview1: wasi});
memory = runtime.instance.exports.memory;
const imports = {"quest.runtime": runtime.instance.exports};
for (const unit of units) {
  const instance = await WebAssembly.instantiate(fs.readFileSync(unit.path), imports);
  imports[unit.name] = instance.instance.exports;
}
const program = await WebAssembly.instantiate(fs.readFileSync(programPath), imports);
program.instance.exports._start();
