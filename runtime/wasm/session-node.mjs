// The driver compiled to wasm, as a session in node (docs/wasm.md sections
// 6.1 and 8.2), standing in for `quest` where the tests run one:
//
//     node --no-warnings session-node.mjs [--stack-kb N] DRIVER.wasm --kernel [ARG...]
//     node --no-warnings session-node.mjs [--stack-kb N] DRIVER.wasm -i [FILE] [ARG...]
//
// DRIVER.wasm is the driver's program module, DRIVER.wasm.runtime.wasm and
// DRIVER.wasm.units beside it, as the driver's -o writes them. The session
// runs in a worker whose stack is N KB (512 by default, a Chromium worker's),
// and whose heap --heap-mb limits, if given (main), compiling each input with
// the driver's JIT, or interpreting it with --no-jit.
//
// With --kernel it speaks the kernel's protocol (docs/jupyter-kernel.md
// section 2): requests from descriptor 3, records to descriptor 4, a SIGINT
// ending the input running, as `interrupted`, by ending the worker and
// replaying the session in a new one (docs/wasm.md section 6.4). With -i it
// reads lines from standard input as the REPL does, writing its prompts and
// results, so that the REPL's transcripts run against it.

import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import process from "node:process";
import readline from "node:readline";
import {Worker, isMainThread, parentPort, workerData} from "node:worker_threads";
import {NodeMount} from "./host.mjs";
import {Repl} from "./repl.mjs";
import {Session, Exited, failure, requestLine} from "./session.mjs";

if (isMainThread) await main(); else serve();

// ---------------------------------------------------------------------------
// The worker: a Session, its writes made directly to the process's
// descriptors, so that a cell's output and its records keep their order

// All of b (a string or bytes) written to fd: a write to a pipe may take only
// some, and one to a pipe whose reader is slow may say "try again" (EAGAIN),
// after which this waits a millisecond
const pause = new Int32Array(new SharedArrayBuffer(4));
function writeAll(fd, b) {
  let bytes = typeof b === "string" ? Buffer.from(b) : b;
  while (bytes.length > 0) {
    let n;
    try {
      n = fs.writeSync(fd, bytes);
    } catch (e) {
      if (e.code !== "EAGAIN") throw e;
      Atomics.wait(pause, 0, 0, 1);
      continue;
    }
    bytes = bytes.subarray(n);
  }
}

function serve() {
  const {modules, args, env, cwd, kernel, committed} = workerData;
  const write = fd => b => writeAll(fd, b);
  // A request's records as they come, but its last, done, which the main
  // thread writes when it has the reply, so that an interrupt handled before
  // the reply cannot follow it with a second done
  const record = (b, r) => { if (!("done" in r)) writeAll(4, b); };
  const session = new Session({
    modules, args, env, cwd, mounts: {"/": new NodeMount(fs, "/")},
    stdout: write(1), stderr: write(2), record: kernel ? record : null,
    // a worker that replaces one: the -i file's output not written again
    quietStart: committed !== null,
  });
  const post = message => parentPort.postMessage(message);
  try {
    session.start();
    // A replacement for a worker that was ended: the inputs that committed
    if (committed !== null && committed.length > 0) {
      session.committed = committed;
      const lost = session.replay();
      if (lost) writeAll(2, lost);
    }
    post({started: true, committed: session.committed});
  } catch (e) {
    if (e instanceof Exited) post({exited: e.status}); else throw e;
    return;
  }
  parentPort.on("message", ({line}) => {
    try {
      // the input committed, not the whole list, which only a replay changes
      session.replayed = false;
      const records = session.request(line);
      post({records, commit: session.commit, committed: session.replayed ? session.committed : undefined});
    } catch (e) {
      if (e instanceof Exited) post({exited: e.status}); else throw e;
    }
  });
}

// ---------------------------------------------------------------------------
// The main thread: the options, the worker, and the protocol or the REPL

async function main() {
  const argv = process.argv.slice(2);
  let stackKb = 512;
  if (argv[0] === "--stack-kb") { stackKb = Number(argv[1]); argv.splice(0, 2); }
  // A limit for the worker's heap, if given: node ends a worker that it
  // finds over its limit, and the session replays in a new one. Not by
  // default: with WebAssembly's GC objects V8 aborts the whole process at
  // the limit for a large allocation, and slows near it for small ones
  // (docs/wasm.md section 7)
  let heapMb = null;
  if (argv[0] === "--heap-mb") { heapMb = Number(argv[1]); argv.splice(0, 2); }
  const [driver, ...rest] = argv;
  if (!driver) {
    process.stderr.write("usage: node session-node.mjs [--stack-kb N] [--heap-mb N] DRIVER.wasm (--kernel | -i [FILE]) [ARG...]\n");
    process.exit(2);
  }
  const kernel = rest.includes("--kernel");
  const compile = file => new WebAssembly.Module(fs.readFileSync(file));
  const units = fs.readFileSync(driver + ".units", "utf8").split(/\s+/).filter(Boolean).map(entry => {
    const at = entry.indexOf("=");
    return {name: entry.slice(0, at), module: compile(entry.slice(at + 1))};
  });
  const modules = {runtime: compile(driver + ".runtime.wasm"), units, program: compile(driver)};
  const env = {...process.env, PWD: process.cwd()};
  // --no-jit first, before a file -i runs and its arguments
  const args = rest.includes("--no-jit") ? ["--no-jit", ...rest.filter(a => a !== "--no-jit")] : rest;
  // A worker, started and given the committed inputs to replay (null for
  // the first)
  let committed = null;
  let worker = null;
  // What takes the worker's next message: startWorker's, until the worker
  // has started, then each request's
  let waiting = null;
  const startWorker = () => new Promise(resolve => {
    worker = new Worker(new URL(import.meta.url), {
      workerData: {modules, args, env, cwd: process.cwd(), kernel, committed},
      // node keeps 192 KB of a worker's stack from V8 (kStackBufferSize), so
      // that V8 has the N KB that a browser's worker gives it
      resourceLimits: {stackSizeMb: (stackKb + 192) / 1024, ...(heapMb ? {maxOldGenerationSizeMb: heapMb} : {})},
    });
    waiting = message => {
      if (message.exited !== undefined) process.exit(message.exited);
      committed = message.committed;
      resolve();
    };
    worker.on("message", message => {
      const w = waiting;
      waiting = null;
      if (w) w(message);
    });
    worker.on("error", e => {
      if (e.code === "ERR_WORKER_OUT_OF_MEMORY" && running) { outOfMemory(); return; }
      process.stderr.write(`quest: the session's worker failed: ${e.stack || e}\n`);
      process.exit(70);
    });
  });
  await startWorker();
  // After the driver has checked its options, as natively, where it opens
  // descriptor 3 itself. node holds descriptors of its own, pipes too, where
  // none was given it, which a socket refuses (ENOTTY).
  let requests = null;
  if (kernel) {
    try {
      requests = new net.Socket({fd: 3, readable: true, writable: false});
    } catch {
      process.stderr.write("quest: error: --kernel reads requests from descriptor 3, which is not open\n");
      process.exit(2);
    }
  }

  // One request: its records; an interrupt (interrupt()) ends it as one
  let running = null;
  const request = line => new Promise(resolve => {
    running = {resolve};
    waiting = message => {
      running = null;
      // process.exit ends the worker too
      if (message.exited !== undefined) process.exit(message.exited);
      if (message.committed !== undefined) committed = message.committed;
      else if (message.commit) committed.push(message.commit);
      if (kernel) {
        const done = message.records.find(r => "done" in r);
        if (done) writeAll(4, requestLine(done) + "\n");
      }
      resolve(message.records);
    };
    worker.postMessage({line});
  });
  // An interrupt during a request ends it: a new worker replays the inputs
  // that committed. One while that worker replays them ends the replay too,
  // and the session starts again without them (docs/wasm.md section 6.4)
  let restarting = null;
  const interrupt = async () => {
    if (restarting) {
      const done = restarting;
      restarting = null;
      waiting = null;
      await worker.terminate();
      const count = committed.length;
      committed = [];
      await startWorker();
      process.stderr.write(`quest: the replay was interrupted; ${count} inputs that ran before did not run again\n`);
      done();
      return;
    }
    if (!running) return;  // between inputs, forgotten
    const {resolve} = running;
    running = null;
    waiting = null;
    await worker.terminate();
    await new Promise(finished => {
      restarting = finished;
      startWorker().then(() => { if (restarting === finished) { restarting = null; finished(); } });
    });
    const records = failure("interrupted", "interrupted");
    if (kernel) writeAll(4, records.map(r => requestLine(r)).join("\n") + "\n");
    resolve(records);
  };
  process.on("SIGINT", () => { interrupt(); });
  // An input that filled the worker's heap: as an interrupt ends one, a new
  // worker replaying the inputs that committed, and the input's failure
  const outOfMemory = async () => {
    const {resolve} = running;
    running = null;
    waiting = null;
    await startWorker();
    const records = failure("memory", "out of memory");
    if (kernel) writeAll(4, records.map(r => requestLine(r)).join("\n") + "\n");
    resolve(records);
  };

  if (kernel) {
    // A socket, not a file stream: a file stream's blocking read in node's
    // thread pool keeps the process from exiting
    const lines = readline.createInterface({input: requests});
    for await (const line of lines) {
      if (line.trim() !== "") await request(line);
    }
  } else {
    await repl(request);
  }
  await worker.terminate();
  process.exit(0);
}

// The REPL's loop (repl.mjs) over standard input, read without editing
async function repl(request) {
  const r = new Repl(request, s => writeAll(1, s), s => writeAll(2, s));
  r.begin();
  const input = readline.createInterface({input: process.stdin, terminal: false});
  for await (const line of input) await r.line(line);
  r.end();
}
