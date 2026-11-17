# Probes From the Review of the WebAssembly Backend

The generators and drivers behind a review of the wasm backend (2026-11-15; what it found still open is in
[docs/wasm.md](../../docs/wasm.md) §10), kept as a start for tests. None is run by `tools/check`. Each takes a
scratch directory, `OUT` below, and writes its programs, builds, and outputs there; give it one outside the tree.
They need `wasmtime` and `node`, and the page's probes need Chrome.

Every comparison is of three runs of one program: compiled by arm64 (the reference), and by the wasm backend in
wasmtime and in node. [compare.sh](compare.sh) does it for any `NAME.quest` in the current directory and exits 1 if
the outputs differ. The first run after a change to the compiler may differ only by the driver's "building stage"
lines; run it again.

## Random Programs

[programs/gen.py](programs/gen.py) `SEED [FUNCTIONS SIZE]` prints a random program that stresses the reuse of
locals (`questlang/wasm/locals`): variables of every kind (`Int`, `Real`, `String`, record, option, variant,
closure) with long lives across calls into another unit, nested loops, conditionals, and handlers, and `@`
locations. A local reused while still live would show as a difference in output.

    sh tools/wasm-review/programs/fuzz.sh OUT 1 40          # 40 seeds, 6 functions of 60 statements
    sh tools/wasm-review/programs/fuzz.sh OUT 101 108 3 400 # functions of several hundred variables

The review ran these 48 seeds with no difference.

## Serialized Documents

Two generators of documents for `dynamic.intern`, and [documents/read.quest](documents/read.quest), which reads
each and prints whether it was taken, what was left unread, and the value written again:

- [documents/handwritten.py](documents/handwritten.py): 463 documents, by hand: numbers and literals at each
  type, well-formed and not; malformed and cyclic type tables; abstract types against the registry of
  `documents/u/ab`; sharing and cycles.
- [documents/mutations.py](documents/mutations.py): three well-formed documents, every prefix of two of them,
  and 1,500 seeded mutations, 2,319 in all.

    sh tools/wasm-review/documents/run.sh OUT handwritten.py
    sh tools/wasm-review/documents/run.sh OUT mutations.py 800 860   # a range of documents

The differences are left in `OUT/all.diff.wt` and `OUT/all.diff.node`. A document that ends a run (a trap, or the
limit of `T` seconds) gets a line `N: <DIED ...>`. At the time of the review the differences were the review's
§2.4 items 4, 7, and 8.

## The Page in Chrome

[page/chrome-probe](page/chrome-probe) serves a built page, opens it in headless Chrome with a script that drives
the page's own controls, and prints the script's lines.

    tools/wasm-page/build -o OUT/page
    tools/wasm-review/page/chrome-probe OUT/page probe=restart
    PROBE_JS=probe2.mjs tools/wasm-review/page/chrome-probe OUT/page probe=output 300

| Script | `probe=` | What it does |
|---|---|---|
| `probe.mjs` | `basic` | Markup in output, results, payloads, and errors; `display.html` and `display.svg`; type-ahead |
| | `restart` | Restart while an input runs, then a line |
| | `interrupt` | Interrupt of a loop with lines typed ahead; at the prompt; an exit |
| | `output` | A loop printing 2,000 to 100,000 lines, with the main thread's longest stall; one write of 20 MB |
| | `oom` | An input that fills the heap |
| `probe2.mjs` | `output` | The printing loop at 500 to 4,000 lines, then with the transcript hidden |
| | `oom` | As above |
| | `restartidle` | Restart at the prompt: bindings gone, files kept |

The probes print what they see and assert nothing: read the lines against the review's §2.3 and §5. They depend
on the page's element ids and on `window.quest` (`session`, `pending`, `draining`).
