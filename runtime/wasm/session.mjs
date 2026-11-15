// A session of the driver compiled to wasm (docs/wasm-plan.md step 11), for
// node and for a page alike: the driver's modules instantiated over a Host
// (host.mjs), its requests those of the kernel's protocol
// (docs/jupyter-kernel.md section 2), and its recovery from a stack overflow
// by replay (section 6.3 of the plan).
//
// The driver runs with QUEST_HOST_SESSION set, so that after its _start has
// set the session up (and run a file -i names), it returns, and the host calls
// questlang/driver/kernel's request for each request, the request's line
// queued for the read of descriptor 3 that request makes. Records arrive as
// writes to descriptor 4, the program's output as writes to 1 and 2.

import {Host, Exit} from "./host.mjs";
import {Jit, isStackOverflow} from "./jit.mjs";

const encoder = new TextEncoder();
const decoder = new TextDecoder();

// A request's line: JSON whose strings are UTF-8's bytes, each above 126
// escaped as \u00XX, as the kernel's client writes them
export function requestLine(request) {
  const bytesOf = s => Array.from(encoder.encode(s), b => String.fromCharCode(b)).join("");
  const asBytes = v => typeof v === "string" ? bytesOf(v)
    : Array.isArray(v) ? v.map(asBytes)
    : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, asBytes(x)]))
    : v;
  return JSON.stringify(asBytes(request)).replace(/[\u007f-ÿ]/g,
    c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
}

// A record's strings, bytes as the driver writes them, decoded from UTF-8
export function decodeRecord(record) {
  const decode = v => typeof v === "string" ? decoder.decode(Uint8Array.from(v, c => c.charCodeAt(0)))
    : Array.isArray(v) ? v.map(decode)
    : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, decode(x)]))
    : v;
  return decode(record);
}

// The interpreter's limit on active calls in a session, unless the
// environment gives one: below what the engine's worker holds, so that a deep
// recursion raises the interpreter's own stack.overflow, which rolls its input
// back, rather than overflow the engine's stack, which replays the session.
// The stack a call takes depends on its body, and on how warm the code is: the
// limit is about two thirds of the depth of a function whose body nests a let,
// a tuple, a loop, and an if around the call, called in a new session, in each
// engine's worker (docs/wasm-plan.md section 6.2): Chromium's 181, Firefox's
// 378, Safari's 117 (which varies, one run overflowing at 100), and node's 175
// at the 512 KB a session's worker gets. An engine not known takes the least.
export const callLimits = {chromium: 150, firefox: 250, node: 150, other: 80};

// The engine running here, by its user agent: node, Firefox, Chromium (whose
// user agent names Chrome, as Edge's does), or another (Safari's names only
// Safari)
export function engine() {
  const agent = globalThis.navigator?.userAgent || "";
  if (globalThis.process?.versions?.node) return "node";
  if (/Firefox\//.test(agent)) return "firefox";
  if (/Chrome\/|Chromium\//.test(agent)) return "chromium";
  return "other";
}

export const callLimit = callLimits[engine()];

// Thrown by start or request when the driver exits: its status
export class Exited extends Error {
  constructor(status) { super(`the driver exited with status ${status}`); this.status = status; }
}

// The error records of an input the host ended: a stack overflow the
// driver's own code did not catch, or an interrupt
export function failure(kind, message) {
  return [{error: kind, message, rendered: `<repl>: error: Exception: ${kind}\n`}, {done: "error"}];
}

// options:
//   modules    {runtime, units: [{name, module}], program}, compiled
//   args       the driver's arguments, after its name
//   env, cwd, mounts, as Host takes them
//   stdout, stderr, record: each called with bytes the driver writes
export class Session {
  constructor(options) {
    this.options = options;
    // The inputs that committed, in order, which a replay runs again
    this.committed = [];
    this.quiet = false;
  }

  // Instantiates the driver and runs its _start: 0 when it returned to the
  // host to serve requests. Throws Exited if it exits instead.
  start() {
    const o = this.options;
    let pending = new Uint8Array(0);
    this.records = [];
    const record = bytes => {
      if (!this.quiet && o.record) o.record(bytes);
      const all = new Uint8Array(pending.length + bytes.length);
      all.set(pending);
      all.set(bytes, pending.length);
      let start = 0;
      for (let i = 0; i < all.length; i++) {
        if (all[i] === 10) {
          this.records.push(JSON.parse(decoder.decode(all.subarray(start, i))));
          start = i + 1;
        }
      }
      pending = all.slice(start);
    };
    this.host = new Host({
      args: ["quest", ...o.args], env: {QUEST_CALL_LIMIT: String(callLimit), ...o.env, QUEST_HOST_SESSION: "1"},
      cwd: o.cwd, mounts: o.mounts,
      onStdout: b => { if (!this.quiet && o.stdout) o.stdout(b); },
      onStderr: b => { if (!this.quiet && o.stderr) o.stderr(b); },
      onRecord: record,
    });
    const runtime = new WebAssembly.Instance(o.modules.runtime, {wasi_snapshot_preview1: this.host.wasiImport});
    this.host.attach(runtime);
    // The JIT's host (jit.mjs), which links each unit as it is instantiated
    this.jit = new Jit();
    this.jit.attachRuntime(runtime);
    for (const unit of o.modules.units) {
      this.jit.addUnit(unit.name, unit.module, new WebAssembly.Instance(unit.module, this.jit.importObject()).exports);
    }
    const program = new WebAssembly.Instance(o.modules.program, this.jit.importObject());
    this.noClosure = runtime.exports.noClosure.value;
    this.kernel = this.jit.units["questlang/driver/kernel"];
    this.core = this.jit.units["wasm/core"];
    try {
      program.exports._start();
    } catch (e) {
      if (!(e instanceof Exit)) throw e;
      if (e.code !== 0) throw new Exited(e.code);
    }
    return 0;
  }

  // The records of a request (an object, or its line as the client wrote
  // it). Throws Exited if the driver exits. A stack overflow, or a trap, in
  // an input replays the session (replay) and gives that input's failure.
  request(request) {
    const line = typeof request === "string" ? request : requestLine(request);
    this.records = [];
    this.host.queue(line);
    try {
      this.kernel.request(this.noClosure);
    } catch (e) {
      if (e instanceof Exit) throw new Exited(e.code);
      if (!isStackOverflow(e) && !(e instanceof WebAssembly.RuntimeError)) throw e;
      // No Quest handler saw it, and the interpreter's structures may be half
      // updated: a new session, with the committed inputs run again
      this.replay();
      const kind = isStackOverflow(e) ? "stack.overflow" : "trap";
      const records = failure(kind, String(e.message));
      if (this.options.record) this.options.record(encoder.encode(records.map(r => requestLine(r)).join("\n") + "\n"));
      return records;
    }
    const records = this.records;
    // An input whose overflow or trap the JIT's host caught part way through
    // an update of the runtime's shared tables: a new session (section 6.3)
    if (this.jit.mustReplay) this.replay();
    const parsed = JSON.parse(line);
    const done = records.find(r => "done" in r);
    if (parsed.execute !== undefined && done && done.done === "ok") this.committed.push(line);
    return records;
  }

  // How many updates of the runtime's shared tables are in progress: the
  // JIT's host reads it after an overflow in an input's code (jit.mjs)
  updating() { return Number(this.core.updating(this.noClosure)); }

  // A new instance, the committed inputs run again with their output
  // suppressed
  replay() {
    this.quiet = true;
    try {
      this.start();
      const inputs = this.committed;
      this.committed = [];
      for (const line of inputs) this.request(line);
    } finally {
      this.quiet = false;
    }
  }
}
