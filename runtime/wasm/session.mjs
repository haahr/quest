// A session of the driver compiled to wasm (docs/wasm.md section 6.1), for
// node and for a page alike: the driver's modules instantiated over a Host
// (host.mjs), its requests those of the kernel's protocol
// (docs/jupyter-kernel.md section 2), and its recovery from a stack overflow
// by replay (docs/wasm.md section 6.3).
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

// A request's line, as the kernel's client writes it: JSON whose strings hold
// the UTF-8 bytes of request's, a character for each byte, each above 126
// escaped as \u00XX, since the driver's strings are bytes
// (docs/jupyter-kernel.md section 2)
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
// engine's worker (docs/wasm.md section 6.2): Chromium's 181, Firefox's
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

// The driver's options that take a value (questlang/driver/options.mod.quest)
const valued = new Set(["--stop-after", "--stop_after", "--build-dir", "--build_dir", "--dump-after", "--dump_after",
  "-o", "--output", "-I", "--include", "-j", "--backend", "--wasm-engine", "--unit-backend", "--variant",
  "--expected-exit", "--expected_exit", "-e", "--eval", "--code", "--command"]);

// The driver's arguments without the program file, the one -i runs first:
// a -- in its place keeps the program's arguments after it
function withoutLoad(args) {
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--") return args;
    if (valued.has(arg)) i++;
    else if (arg === "-" || !arg.startsWith("-")) return [...args.slice(0, i), "--", ...args.slice(i + 1)];
  }
  return args;
}

// The names an input's records show it bound: each result's let or Let
function boundNames(records) {
  const names = [];
  for (const r of records) {
    if (typeof r.result !== "string") continue;
    const m = /^(?:let|Let)\s+(?:var\s+|rec\s+)?([^\s:(]+)/.exec(r.result);
    if (m) names.push(m[1]);
  }
  return names;
}

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
//   stdout, stderr: each called with bytes the driver writes
//   record     called with each record's line, as bytes, and the record
//   quietStart true to start without writing (a worker that replaces one)
export class Session {
  constructor(options) {
    this.options = options;
    // The inputs that committed, in order, which a replay runs again, and
    // the names each bound (by its line), which a replay that loses it
    // reports; the input the last request committed, or null; and whether
    // a replay changed the committed inputs since the client last read them
    this.committed = [];
    this.bound = new Map();
    this.commit = null;
    this.replayed = false;
    this.quiet = !!options.quietStart;
  }

  // Instantiates the driver and runs its _start: 0 when it returned to the
  // host to serve requests. Throws Exited if it exits instead.
  start() {
    const o = this.options;
    let pending = new Uint8Array(0);
    this.records = [];
    // Descriptor 4's writes, split into lines: a write may end part way
    // through a line, which waits in pending for the rest
    const record = bytes => {
      const all = new Uint8Array(pending.length + bytes.length);
      all.set(pending);
      all.set(bytes, pending.length);
      let start = 0;
      for (let i = 0; i < all.length; i++) {
        if (all[i] === 10) {
          // A line that is not a record, which a program wrote to descriptor
          // 4 (io/display writes there too), is its standard error's, not
          // the end of the session (docs/wasm.md section 7)
          const text = decoder.decode(all.subarray(start, i));
          let parsed;
          try { parsed = JSON.parse(text); } catch { parsed = undefined; }
          if (parsed !== null && typeof parsed === "object") {
            this.records.push(parsed);
            // the client gets each record as it is written, and nothing else
            if (!this.quiet && o.record) o.record(all.slice(start, i + 1), parsed);
          } else if (!this.quiet && o.stderr) o.stderr(encoder.encode(`descriptor 4, not a record: ${text}\n`));
          start = i + 1;
        }
      }
      pending = all.slice(start);
    };
    this.host = new Host({
      args: ["quest", ...(this.loadFailed ? withoutLoad(o.args) : o.args)], env: {QUEST_CALL_LIMIT: String(callLimit), ...o.env, QUEST_HOST_SESSION: "1"},
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
      // The driver's _start ends with exit 0 once its kernel holds the
      // session for the host's requests, having opened descriptor 4 for
      // their records; any other exit, 0 before that among them (a file -i
      // runs that exits), ends the session
      if (e instanceof Exit) {
        if (e.code !== 0 || !this.host.serving) throw new Exited(e.code);
        return 0;
      }
      // An overflow, a trap, or an exception that escapes the driver while
      // -i's file runs at the start: the driver's own start is cut short, so
      // the session starts again without the file, which it reports
      const escaped = e instanceof WebAssembly.Exception;
      if (this.loadFailed || !(isStackOverflow(e) || e instanceof WebAssembly.RuntimeError || escaped)) throw e;
      const kind = isStackOverflow(e) ? "stack.overflow" : escaped ? "an exception" : "a trap";
      if (o.stderr) o.stderr(encoder.encode(`quest: the file -i runs failed (${kind}); the session starts without it\n`));
      this.loadFailed = true;
      return this.start();
    } finally {
      if (o.quietStart) { this.quiet = false; o.quietStart = false; }
    }
    return 0;
  }

  // The records of a request (an object, or its line as the client wrote
  // it). Throws Exited if the driver exits. A stack overflow, a trap, or a
  // Quest exception that escapes the driver, in an input, replays the session
  // (replay) and gives that input's failure.
  request(request) {
    const line = typeof request === "string" ? request : requestLine(request);
    this.records = [];
    this.host.queue(line);
    try {
      this.kernel.request(this.noClosure);
    } catch (e) {
      if (e instanceof Exit) throw new Exited(e.code);
      const escaped = e instanceof WebAssembly.Exception;
      if (!isStackOverflow(e) && !(e instanceof WebAssembly.RuntimeError) && !escaped) throw e;
      // No Quest handler saw it, and the interpreter's structures may be half
      // updated: a new session, with the committed inputs run again
      const lost = this.replay();
      const kind = isStackOverflow(e) ? "stack.overflow" : escaped ? "exception" : "trap";
      const records = failure(kind, escaped ? "an exception the driver did not catch" : String(e.message));
      if (lost) records[0].rendered += lost;
      if (this.options.record && !this.quiet) {
        for (const r of records) this.options.record(encoder.encode(requestLine(r) + "\n"), r);
      }
      this.commit = null;
      return records;
    }
    const records = this.records;
    // An input whose overflow or trap the JIT's host caught part way through
    // an update of the runtime's shared tables: a new session
    // (docs/wasm.md section 6.3)
    let lost = null;
    if (this.jit.mustReplay) lost = this.replay();
    const parsed = JSON.parse(line);
    const done = records.find(r => "done" in r);
    this.commit = null;
    if (parsed.execute !== undefined && done && done.done === "ok") {
      this.committed.push(line);
      this.bound.set(line, boundNames(records));
      this.commit = line;
    }
    if (lost && this.options.stderr && !this.quiet) this.options.stderr(encoder.encode(lost));
    return records;
  }

  // How many updates of the runtime's shared tables are in progress: the
  // JIT's host reads it after an overflow in an input's code (jit.mjs)
  updating() { return Number(this.core.updating(this.noClosure)); }

  // A new instance, the committed inputs run again with their output
  // suppressed. An input that does not succeed again is lost, and so are
  // the names it bound: the session goes on without them, and this gives
  // the text that says so, or null if none was lost. A replay inside a
  // replay stays quiet.
  replay() {
    const quiet = this.quiet;
    this.quiet = true;
    this.replayed = true;
    const lost = [];
    try {
      this.start();
      const inputs = this.committed;
      this.committed = [];
      for (const line of inputs) {
        const records = this.request(line);
        const done = records.find(r => "done" in r);
        if (!done || done.done !== "ok") lost.push(line);
      }
    } finally {
      this.quiet = quiet;
    }
    if (lost.length === 0) return null;
    const names = new Set();
    for (const line of lost) for (const name of this.bound.get(line) || []) names.add(name);
    for (const line of this.committed) for (const name of this.bound.get(line) || []) names.delete(name);
    const count = lost.length === 1 ? "1 input" : `${lost.length} inputs`;
    return `quest: the session started again, and ${count} that ran before did not run again` +
      (names.size > 0 ? `; no longer bound: ${[...names].join(", ")}` : "") + "\n";
  }
}
