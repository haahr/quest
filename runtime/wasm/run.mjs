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
const runtime = await WebAssembly.instantiate(fs.readFileSync(runtimePath),
                                              {wasi_snapshot_preview1: wasi.wasiImport});
wasi.initialize(runtime.instance);
const imports = {"quest.runtime": runtime.instance.exports};
for (const unit of units) {
  const instance = await WebAssembly.instantiate(fs.readFileSync(unit.path), imports);
  imports[unit.name] = instance.instance.exports;
}
const program = await WebAssembly.instantiate(fs.readFileSync(programPath), imports);
program.instance.exports._start();
