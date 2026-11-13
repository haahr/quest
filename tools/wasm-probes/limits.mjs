// The largest array of each element kind that V8 will make, by bisection.
import { readFileSync } from 'node:fs';
const e = new WebAssembly.Instance(new WebAssembly.Module(readFileSync(new URL('limits.wasm', import.meta.url)))).exports;
for (const f of ['newEq', 'newI64', 'newI8']) {
  let lo = 0, hi = 2 ** 31 - 1;
  let why = '';
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    try { e[f](mid); lo = mid; } catch (err) { hi = mid - 1; why = String(err).slice(0, 70); }
  }
  console.log(f.padEnd(8), lo, `(2^${Math.log2(lo).toFixed(2)})`, why);
}
