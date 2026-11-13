// Runs a program the wasm backend compiled (docs/wasm-plan.md, step 3) in node:
//
//     node run.mjs RUNTIME.wasm PROGRAM.wasm [ARG...]
//
// The runtime module (questlang/wasm/runtime) is instantiated first, over the
// part of WASI's first preview it imports, and the program's module over the
// runtime's exports, as wasmtime's --preload links them; then the program's
// _start runs. Bytes cross through the runtime's memory (section 4.4 of the
// plan): fd_write writes each iovec's bytes to its descriptor, and proc_exit
// ends the process with its status.

import fs from "node:fs";

const [runtimePath, programPath] = process.argv.slice(2);
if (!runtimePath || !programPath) {
  process.stderr.write("usage: node run.mjs RUNTIME.wasm PROGRAM.wasm [ARG...]\n");
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
const program = await WebAssembly.instantiate(fs.readFileSync(programPath),
                                              {"quest.runtime": runtime.instance.exports});
program.instance.exports._start();
