# The MLton benchmarks in Quest

The Standard ML programs of MLton's benchmark suite, each converted to Quest, with a runner that checks the
conversions' output against MLton's and times both.

| Path | What |
|---|---|
| `sml/` | The SML originals, from `benchmark/tests` in MLton at commit 5fe943391e539a502699327a6266b6e8e97939e1 |
| `NAME.quest` | The conversions, one program each |
| `support/` | Modules the conversions share: SML's lists (`lists`), its real formatting and parsing (`reals`), arbitrary-precision integers (`intinf`), and the count argument (`bench`) |
| `DATA/` | The programs' input files |
| `expected/` | The originals' output, as MLton-compiled programs produce it: standard output and exit status (`NAME.out`), and the path, size, and SHA-256 of each file written (`NAME.files`) |
| `tools/` | Scripts that transliterated the originals' large data sections and generated tables into Quest |
| `run.py` | The runner |

The originals keep their authors' copyrights, noted in each file; MLton's license is in `sml/MLton-LICENSE`.

## Running

```bash
./run.py check
```

```bash
./run.py time --mlton --scale 0.1
```

`run.py check [NAME...]` builds the conversions with `./quest` (or `--compiler`) and compares a run of each, at count 1,
with `expected/`. `run.py time [NAME...]` times them at MLton's counts times `--scale`, and with `--mlton` the
originals too. `run.py reference [NAME...]` rebuilds the originals with `mlton` and records their output in
`expected/` again. Each program runs in a scratch directory holding a copy of `DATA/`, so the files some of them write
stay out of the tree. Builds go to `.build/`.

A program does its work n times, n being its first argument. MLton's counts make each original run for 30 to 45 seconds
on its authors' machine; the conversions take longer.

## How the conversions are checked

A conversion's standard output, exit status, and written files must match the original's byte for byte. For life,
logic, mandelbrot, and tsp, whose `testit` prints their results, `run.py check` compares those runs too. For programs
that print nothing (count-graphs, fft, knuth-bendix, mpuz, nucleic, ratio-regions, simple, barnes-hut among them),
each conversion was checked during conversion against a copy of the original changed to print its intermediate results,
the same change made to the conversion.

model-elimination prints its progress once per third of a second of CPU time spent on its search, and the times it
took, so no two runs of the original print quite the same thing. Its conversion, which cannot read the clock, sees no
time pass and prints exactly what the original prints when its timers are changed to read 0; `run.py check` compares
its output with `expected/` without the progress lines and the times.

clang merges calls to `sin` and `cos` of one argument into one call of `__sincos_stret` in the C MLton generates, which
can change their results' last bits. Built with `-cc-opt "-fno-builtin-sin -fno-builtin-cos"`, MLton's simple prints
exactly what its conversion does. No recorded output depends on those bits.

## How the programs are converted

- The algorithms and data structures are the originals', and so is the order of operations where it shows: the order
  in which folds visit elements and in which side effects happen, and the association of real arithmetic (Quest's
  infix operators are right associative, so left-associative SML arithmetic is braced).
- Code the benchmark never runs is left out: other entry points, debugging output, and unused library functions. Each
  conversion's header says what it leaves out. Top-level effects are kept.
- Quest's `Int` has 64 bits and MLton's `int` 32; programs whose results depend on overflow do the 32-bit arithmetic
  explicitly, and `Word32` values are masked to 32 bits.
- An SML `ref` that a closure captures becomes a tuple with a `var` field, since closures cannot capture `var` locals.
- SML's formatting of reals (`Real.toString`, `Real.fmt`) and its `IntInf` come from `support/`, checked against MLton.
- Where Quest lacks something the original uses, the header says what replaces it. Quest cannot read the clock: zern,
  tensor, and model-elimination, which time their work, read 0.

## Programs not in the suite

| Program | Why |
|---|---|
| fxp | Not a benchmark: an XML parser with no `Main.doit` and no input, which MLton's suite omits too |
| merge | Recurses 200,000 calls deep, needing about 10 MB of stack, more than macOS lets a process have |
| hamlet | Not converted yet; `run.py` skips it unless it is named |

## Notes on timings

- tensor's operations produce results nothing uses, and MLton removes the work, so its original runs in milliseconds.
  The conversion does all the work, so tensor's ratio says nothing about either compiler.
- `run.py` raises the stack limit as far as the system allows before each run, since the originals assume MLton's
  stack, which grows on the heap; macOS keeps the limit at 8 MB.
