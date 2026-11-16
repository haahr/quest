// The page's side of a session (docs/wasm-plan.md step 12), which the prompt
// (ui.mjs) and the check of the transcripts (check.mjs) share: the driver's
// modules fetched and compiled once, a worker (worker.mjs) that runs the
// session, its requests one at a time, and an interrupt, which ends the
// worker and starts another that replays the committed inputs (section 6.4).

import {MemoryMount} from "./host.mjs";
import {unpack} from "./archive.mjs";
import {Repl} from "./repl.mjs";
import {decodeRecord, failure} from "./session.mjs";

const decoder = () => new TextDecoder("utf-8");

// Fetches a file of the page's, as bytes
async function fetchBytes(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: ${response.status} ${response.statusText}`);
  return new Uint8Array(await response.arrayBuffer());
}

// The driver's modules, compiled, and the library's files: what every session
// of the page starts from. timings records how long each part took, in
// milliseconds, and sizes the archives' bytes.
export async function load(base = new URL(".", import.meta.url)) {
  const timings = {}, sizes = {};
  const started = performance.now();
  const lap = name => { timings[name] = Math.round(performance.now() - started); };
  const [driverBytes, libBytes] = await Promise.all([
    fetchBytes(new URL("driver.qar.gz", base)), fetchBytes(new URL("lib.qar.gz", base))]);
  sizes.driver = driverBytes.length;
  sizes.lib = libBytes.length;
  lap("fetched");
  const [driver, lib] = await Promise.all([unpack(driverBytes), unpack(libBytes)]);
  lap("unpacked");
  const names = [...driver.keys()].filter(n => n.startsWith("units/"));
  const [runtime, program, ...units] = await Promise.all(
    ["runtime.wasm", "program.wasm", ...names].map(n => WebAssembly.compile(driver.get(n))));
  lap("compiled");
  const modules = {runtime, program, units: names.map((n, i) => ({name: n.slice("units/".length), module: units[i]}))};
  return {modules, lib, timings, sizes, base};
}

// A session, given what load gives. options:
//   jit        false to interpret each input, rather than compile it (the
//              default, step 14)
//   args       the program's arguments (system.args after <repl>)
//   load       a file for -i to run first, a path in the session
//   env        more of the driver's environment
//   prefixes   URL prefixes, mounted at /remote/0, /remote/1, ... and named in
//              QUEST_PATH
//   files      the session's own files to start with (a MemoryMount's)
//   stdout, stderr   called with the text the driver writes to each
//   display    called with a display's bundle, {MIMETYPE: DATA}
//   exited     called with the driver's status when it exits
export class PageSession {
  constructor(loaded, options = {}) {
    this.loaded = loaded;
    this.options = options;
    // null until a worker has started, and then the inputs that committed
    this.committed = null;
    // while a worker that replaces an interrupted one replays: what its
    // interrupt waits for
    this.restarting = null;
    this.files = new MemoryMount(options.files || {work: null});
    this.worker = null;
    this.running = null;
    this.queue = [];
    this.status = null;
    this.timings = {};
  }

  // The driver's arguments: the JIT or not, interactive, a file to run first
  arguments() {
    const o = this.options, args = o.args || [];
    return [...(o.jit === false ? ["--no-jit"] : []), "-i", ...(o.load ? [o.load] : args.length > 0 ? ["--"] : []),
            ...args];
  }

  environment() {
    const prefixes = (this.options.prefixes || []).map((_, i) => `/remote/${i}`);
    return {QUEST_HOME: "/quest", QUEST_KERNEL: "1", PWD: "/work", HOME: "/work",
            ...(prefixes.length > 0 ? {QUEST_PATH: prefixes.join(":")} : {}), ...(this.options.env || {})};
  }

  // Starts a worker, replaying the committed inputs: resolves when it is
  // ready for requests, or when the driver exited
  start() {
    const began = performance.now();
    return new Promise(resolve => {
      const worker = new Worker(new URL("worker.mjs", this.loaded.base), {type: "module"});
      this.worker = worker;
      const text = {stdout: decoder(), stderr: decoder()};
      let records = new Uint8Array(0);
      const recordText = decoder();
      worker.onmessage = ({data}) => {
        if (worker !== this.worker) return;
        if (data.stdout) this.options.stdout?.(text.stdout.decode(data.stdout, {stream: true}));
        else if (data.stderr) this.options.stderr?.(text.stderr.decode(data.stderr, {stream: true}));
        else if (data.record) this.record(data.record, recordText);
        else if (data.change) { const [op, ...args] = data.change; this.files[op](...args); }
        else if (data.started) {
          this.committed = data.committed;
          this.timings.started = Math.round(performance.now() - began);
          resolve();
        }
        else if (data.exited !== undefined) this.exit(data.exited, resolve);
        else if (data.failed) {
          this.options.stderr?.(`the session's worker failed: ${data.failed}\n`);
          this.exit(70, resolve);
        } else if (data.records) {
          if (data.committed !== undefined) this.committed = data.committed;
          else if (data.commit) this.committed.push(data.commit);
          this.finish(data.records);
        }
      };
      worker.onerror = e => {
        if (worker !== this.worker) return;
        this.options.stderr?.(`the session's worker failed: ${e.message}\n`);
        this.exit(70, resolve);
      };
      worker.postMessage({
        modules: this.loaded.modules, lib: this.loaded.lib, files: this.files.entries,
        prefixes: (this.options.prefixes || []).map(p => new URL(p, location.href).href),
        args: this.arguments(), env: this.environment(), committed: this.committed,
      });
    });
  }

  // A write to descriptor 4: displays are shown as they come; the rest come
  // with the request's records
  record(bytes, text) {
    this.pendingRecord = (this.pendingRecord || "") + text.decode(bytes, {stream: true});
    let at;
    while ((at = this.pendingRecord.indexOf("\n")) >= 0) {
      const line = this.pendingRecord.slice(0, at);
      this.pendingRecord = this.pendingRecord.slice(at + 1);
      const r = JSON.parse(line);
      if (r.display) this.options.display?.(decodeRecord(r.display));
    }
  }

  exit(status, resolve) {
    this.status = status;
    this.worker?.terminate();
    this.worker = null;
    if (this.running) this.finish([{done: "error"}]);
    for (const q of this.queue.splice(0)) q.resolve([{done: "error"}]);
    this.options.exited?.(status);
    resolve?.();
  }

  // A request's records (its line as session.mjs's requestLine writes it),
  // after the requests before it
  request(line) {
    return new Promise(resolve => {
      if (this.status !== null) { resolve([{done: "error"}]); return; }
      this.queue.push({line, resolve});
      this.next();
    });
  }

  next() {
    if (this.running || this.queue.length === 0 || !this.worker) return;
    this.running = this.queue.shift();
    this.running.began = performance.now();
    this.worker.postMessage({line: this.running.line});
  }

  finish(records) {
    const r = this.running;
    this.running = null;
    this.lastTime = Math.round(performance.now() - r.began);
    r.resolve(records);
    this.next();
  }

  // Whether a request is running
  busy() { return this.running !== null; }

  // Ends the request running, if one is, as interrupted: a new worker replays
  // the committed inputs. Resolves once it is ready. An interrupt while that
  // worker replays them ends the replay too, and the session starts again
  // without them (wasm-review.md section 4, 7).
  async interrupt() {
    if (this.restarting) {
      const done = this.restarting;
      this.restarting = null;
      this.worker?.terminate();
      this.worker = null;
      const count = this.committed?.length ?? 0;
      this.committed = [];
      await this.start();
      this.options.stderr?.(`quest: the replay was interrupted; ${count} inputs that ran before did not run again\n`);
      done();
      return;
    }
    if (!this.running || !this.worker) return;
    const r = this.running;
    this.worker.terminate();
    this.worker = null;
    this.running = null;
    const began = performance.now();
    await new Promise(finished => {
      this.restarting = finished;
      this.start().then(() => { if (this.restarting === finished) { this.restarting = null; finished(); } });
    });
    this.timings.replay = Math.round(performance.now() - began);
    r.resolve(failure("interrupted", "interrupted"));
    this.next();
  }

  // The REPL's loop over this session (repl.mjs)
  repl(out, err, prompt) { return new Repl(line => this.request(line), out, err, prompt); }
}
