// The host's half of the JIT on WebAssembly (docs/wasm.md section 6.1): the
// functions of quest.host, which questlang/jit/target's wasm variant imports,
// over the modules a driver compiled to wasm was instantiated from. A
// session (session.mjs), a page through it, and run.mjs, which runs a file
// through the driver's JIT as `quest FILE` does natively, each make one.
//
// An input (a phrase unit, docs/jit.md section 3.2) or a module file the
// session compiles is given as its module's bytes (give), then loaded under
// its unit's name (load), which instantiates it with the runtime, the
// driver's units, and the units loaded before, by the names its imports
// give; and an input is run (run), its init called. A module an input
// declares (qj_N_k) is exported by the input's module as qj_N_k.FIELD, and
// is given to later importers as the module qj_N_k.
//
// Each function takes a string as its bytes in the runtime's memory, at
// and n, and gives an Int (an i32): load the length of its error's message,
// written at at, or 0; run 0, 1 for an engine's stack overflow, 2 for a
// trap, or 3 for a fatal error, which the runtime holds while an input runs
// (its holdFatal: it keeps the report and traps), each caught here, at the
// host's frame, so that only the input's frames are unwound. A Quest
// exception the input raises is not caught: it crosses this frame to the
// driver's handler.

const decoder = new TextDecoder();
const encoder = new TextEncoder();

import {isStackOverflow} from "./host.mjs";

export {isStackOverflow};

export class Jit {
  constructor() {
    // The exports of every unit by name: the runtime's, the driver's, and
    // those loaded
    this.units = {};
    // The driver's own units, which has answers for: a unit loaded is the
    // session's to know of, and is loaded again after an input that loaded
    // it fails (docs/jit.md section 3.4)
    this.driver = new Set();
    // Each unit's interface fingerprint (docs/jit.md section 3.3.1), from its
    // module's custom section quest.fingerprint
    this.fingerprints = new Map();
    // The pieces of the module the next load instantiates, as give passed
    // them
    this.given = [];
    this.memory = null;
    this.core = null;
    this.noClosure = null;
    // Whether an overflow or a trap caught here interrupted an update of the
    // runtime's shared tables, so that the session must replay
    // (docs/wasm.md section 6.3)
    this.mustReplay = false;
    this.imports = {
      give: (at, n) => { this.given.push(this.bytes(at, n).slice()); return 0; },
      load: (at, n) => this.load(this.string(at, n), at),
      run: (at, n) => this.run(this.string(at, n)),
      // 1 if the unit is one of the driver's own, else 0
      has: (at, n) => (this.driver.has(this.string(at, n)) ? 1 : 0),
      // The unit's fingerprint, written over its name at at: its length, or
      // 0 if the unit has none
      fingerprint: (at, n) => {
        const fp = this.fingerprints.get(this.string(at, n));
        return fp === undefined ? 0 : this.put(at, fp);
      },
    };
  }

  // The runtime's instance, whose memory the functions read and write
  attachRuntime(instance) {
    this.memory = instance.exports.memory;
    this.noClosure = instance.exports.noClosure.value;
    this.units["quest.runtime"] = instance.exports;
  }

  // A unit instantiated from module: the driver's, or one loaded
  addUnit(name, module, exports, loaded = false) {
    this.units[name] = exports;
    if (!loaded) this.driver.add(name);
    if (name === "wasm/core") this.core = exports;
    const sections = WebAssembly.Module.customSections(module, "quest.fingerprint");
    if (sections.length > 0) this.fingerprints.set(name, decoder.decode(sections[0]));
  }

  // The import object every unit is instantiated with
  importObject() { return {...this.units, "quest.host": this.imports}; }

  bytes(at, n) { return new Uint8Array(this.memory.buffer, at, n); }
  string(at, n) { return decoder.decode(this.bytes(at, n)); }
  // text's bytes at at, the memory grown if need be: their length
  put(at, text) {
    const b = encoder.encode(text);
    const short = at + b.length - this.memory.buffer.byteLength;
    if (short > 0) this.memory.grow(Math.ceil(short / 65536));
    this.bytes(at, b.length).set(b);
    return b.length;
  }

  // Instantiates the module given since the last load as the unit name: 0,
  // or the length of the error's message, written at at. Each module the
  // unit declares becomes a unit of its own, of the fields exported as
  // MODULE.FIELD, with the unit's init, which an importer imports from each
  // unit it imports.
  load(name, at) {
    const all = new Uint8Array(this.given.reduce((n, b) => n + b.length, 0));
    let k = 0;
    for (const b of this.given) { all.set(b, k); k += b.length; }
    this.given = [];
    try {
      const module = new WebAssembly.Module(all);
      const exports = new WebAssembly.Instance(module, this.importObject()).exports;
      this.addUnit(name, module, exports, true);
      // The modules the unit declares, by their names
      const declared = {};
      for (const field of Object.keys(exports)) {
        const dot = field.indexOf(".");
        if (dot > 0 && field.startsWith(name + "_")) {
          const unit = field.slice(0, dot);
          (declared[unit] ||= {init: exports.init})[field.slice(dot + 1)] = exports[field];
        }
      }
      Object.assign(this.units, declared);
      return 0;
    } catch (e) {
      return this.put(at, `the host could not load ${name}: ${e.message}`);
    }
  }

  // Calls the init of the unit name: 0, or 1, 2, or 3 for an overflow, a
  // trap, or a fatal error it caught (see the top of this file). Anything
  // else thrown, a Quest exception among them, goes on to the caller.
  run(name) {
    const runtime = this.units["quest.runtime"];
    runtime.holdFatal(1);
    try {
      const entry = this.units[name].init;
      if (typeof entry !== "function") throw new Error(`${name} exports no init: ${Object.keys(this.units[name])}`);
      entry();
      return 0;
    } catch (e) {
      const overflow = isStackOverflow(e);
      if (!overflow && !(e instanceof WebAssembly.RuntimeError)) throw e;
      if (this.core && Number(this.core.updating(this.noClosure)) !== 0) this.mustReplay = true;
      // What the call left half done that the count of updates (updating)
      // does not cover, and so no replay undoes: the assumptions of the
      // core's subtype and equivalence proofs (its trails), and print's
      // nesting of the values being shown; none is in progress now
      for (const unit of ["wasm/core", "wasm/print"]) this.units[unit]?.recover?.(this.noClosure);
      return overflow ? 1 : runtime.fatalReport() !== null ? 3 : 2;
    } finally {
      runtime.holdFatal(0);
    }
  }
}
