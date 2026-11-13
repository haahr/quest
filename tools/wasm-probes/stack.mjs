// The deepest recursion of each function, on this thread and in a worker of 512 KB of stack.
import { readFileSync } from 'node:fs';
import { Worker, isMainThread, parentPort } from 'node:worker_threads';
const measure = () => {
  const bytes = readFileSync(new URL('stack.wasm', import.meta.url));
  const out = {};
  for (const f of ['small', 'distinct', 'reused']) {
    const e = new WebAssembly.Instance(new WebAssembly.Module(bytes)).exports;
    try { e[f](100000000n); } catch (err) { if (!(err instanceof RangeError)) throw err; }
    out[f] = e.depth.value;
  }
  return out;
};
if (isMainThread) {
  console.log('main thread     ', JSON.stringify(measure()));
  for (const mb of [0.5, 1]) {
    const w = new Worker(new URL(import.meta.url), { resourceLimits: { stackSizeMb: mb } });
    await new Promise((res) => w.on('message', (m) => { console.log(`worker, ${mb} MB  `, JSON.stringify(m)); res(); }));
  }
} else {
  parentPort.postMessage(measure());
}
