// Times the probes in node: the best of five runs after a warm-up, in ms.
// COL=0 or COL=1 runs one column only, so that one variant's heap does not disturb the other's.
import { readFileSync } from 'node:fs';
const here = new URL('.', import.meta.url);
const load = (name, imports = {}) =>
  new WebAssembly.Instance(new WebAssembly.Module(readFileSync(new URL(name + '.wasm', here))), imports).exports;
const col = process.env.COL;
const best = (f) => {
  f();
  let b = Infinity;
  for (let i = 0; i < 5; i++) { const t = performance.now(); f(); b = Math.min(b, performance.now() - t); }
  return b.toFixed(1).padStart(8);
};
const row = (label, ...cells) =>
  console.log(label.padEnd(58), ...cells.map((c, i) => (col === undefined || +col === i) ? c() : '       -'));

const t = load('tuples');
console.log('TUPLES: a tree of 2^21 nodes (kind, span, left, right)                slot array     flat');
for (const big of [0, 1]) {
  const what = big ? 'span boxed (file * 2^32 + d)' : 'span fits i31';
  row(`build once, ${what}`, () => best(() => t.buildA(20n, 1n, big)), () => best(() => t.buildB(20n, 1n, big)));
  row(`walk 10 times, ${what}`,
      () => { const a = t.buildA(20n, 1n, big); return best(() => { for (let i = 0; i < 10; i++) t.walkA(a); }); },
      () => { const b = t.buildB(20n, 1n, big); return best(() => { for (let i = 0; i < 10; i++) t.walkB(b); }); });
}

const ar = load('arrays');
console.log('\nARRAYS, direct access at a known type: 1M elements                     eqref      i64');
for (const big of [0, 1]) {
  const what = big ? 'full-width values (boxed)' : 'values fit i31';
  row(`fill 20 times, ${what}`, () => best(() => ar.runEq(1000000, big, 20, 0)), () => best(() => ar.runI(1000000, big, 20, 0)));
  row(`fill once and sum 100 times, ${what}`, () => best(() => ar.runEq(1000000, big, 1, 100)), () => best(() => ar.runI(1000000, big, 1, 100)));
}

const vec = load('vec');
const u = load('user', { vec });
console.log('\nVECTOR through another unit\'s generic get and set: 1M elements        uniform    typed');
for (const big of [0, 1]) {
  const what = big ? 'full-width Words (hashes)' : 'values fit i31';
  row(`set all 20 times, ${what}`, () => best(() => u.runU(1000000, big, 20, 0)), () => best(() => u.runT(1000000, big, 20, 0)));
  row(`set all once, get all 50 times, ${what}`, () => best(() => u.runU(1000000, big, 1, 50)), () => best(() => u.runT(1000000, big, 1, 50)));
}

console.log('\nCASTS: 100M calls across units, three reference parameters           precise   eqref+cast');
row('call', () => best(() => u.callPrecise(100000000)), () => best(() => u.callCast(100000000)));
