// Runs a program the wasm backend compiled (docs/wasm-plan.md, steps 3 and 9) in node:
//
//     node --no-warnings run.mjs [--module NAME=UNIT.wasm]... RUNTIME.wasm PROGRAM.wasm [ARG...]
//
// The runtime module (questlang/wasm/runtime) is instantiated first, over WASI's
// first preview as node:wasi provides it, with the program's arguments, the
// environment, and two directories opened: / for absolute paths and . for the
// rest, as the driver opens them for wasmtime. Then each unit's module, named by
// its canonical name, in the order given, which puts each after those it
// imports, and last the program's, each over the exports of those before it, as
// wasmtime's --preload links them; then the program's _start runs. Bytes cross
// through the runtime's memory (section 4.4).

import fs from "node:fs";
import process from "node:process";
import { WASI } from "node:wasi";
import {isStackOverflow} from "./host.mjs";
import { Jit } from "./jit.mjs";

const args = process.argv.slice(2);
const units = [];
while (args[0] === "--module") {
  const [name, path] = args[1].split("=");
  units.push({name, path});
  args.splice(0, 2);
}
const [runtimePath, programPath, ...programArgs] = args;
if (!runtimePath || !programPath) {
  process.stderr.write("usage: node run.mjs [--module NAME=UNIT.wasm]... RUNTIME.wasm PROGRAM.wasm [ARG...]\n");
  process.exit(2);
}

const wasi = new WASI({
  version: "preview1",
  args: [programPath, ...programArgs],
  env: {...process.env, PWD: process.cwd()},
  preopens: {"/": "/", ".": process.cwd()},
  returnOnExit: false,
});
// proc_exit ends the run by unwinding to here, so that node exits as it
// does after a script, writing what it writes then (--cpu-prof's profile)
class Exit { constructor(code) { this.code = code; } }
// node's fd_read of a pipe with nothing in it yet says "try again" (EAGAIN,
// 6) where a read natively waits, so a read waits here a few milliseconds at
// a time until the data comes (wasm-review.md section 1.2, 3)
const pause = new Int32Array(new SharedArrayBuffer(4));
function fd_read(...args) {
  for (;;) {
    const errno = wasi.wasiImport.fd_read(...args);
    if (errno !== 6) return errno;
    Atomics.wait(pause, 0, 0, 5);
  }
}
const wasiImports = {...wasi.wasiImport, fd_read, proc_exit(code) { throw new Exit(code); }};
const runtime = await WebAssembly.instantiate(fs.readFileSync(runtimePath), {wasi_snapshot_preview1: wasiImports});
wasi.initialize(runtime.instance);
// The units linked by the JIT's host (jit.mjs), so that the driver compiled to
// wasm runs a file through its JIT, as it does natively
const jit = new Jit();
jit.attachRuntime(runtime.instance);
for (const unit of units) {
  const module = new WebAssembly.Module(fs.readFileSync(unit.path));
  jit.addUnit(unit.name, module, new WebAssembly.Instance(module, jit.importObject()).exports);
}
const program = await WebAssembly.instantiate(fs.readFileSync(programPath), jit.importObject());
try {
  program.instance.exports._start();
} catch (e) {
  if (isStackOverflow(e)) {
    // as natively an overflow no handler caught ends a program
    // (docs/wasm-plan.md step 31)
    process.stderr.write("Exception: stack.overflow\n");
    process.exitCode = 1;
  } else {
    if (!(e instanceof Exit)) throw e;
    process.exitCode = e.code;
  }
}
