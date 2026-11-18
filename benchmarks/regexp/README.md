# util/regexp's Benchmark

util/regexp against Go's `regexp` (RE2's syntax and leftmost-first semantics, matched without backtracking, like
this library) and Python's `re` (a backtracking matcher in C), on the same workloads
([docs/regexp-plan.md](../../docs/regexp-plan.md) step 5).

| Path | What |
|---|---|
| `regexp.quest`, `regexp.go`, `regexp.py` | The workloads: `PROGRAM WORKLOAD FILE REPEAT` does the workload REPEAT times over FILE and prints one number, the same in each |
| `run.py` | The runner: it generates the inputs, builds the Quest and Go programs, checks that all three print the same numbers, and times them |
| `baselines/` | Tables `run.py` printed, one for each change to the matcher (below) |

```bash
benchmarks/regexp/run.py --repeat 10
```

`--only NAME,...` runs some workloads, and `--no-python` leaves Python out. The inputs, made once in
`.build/regexp-bench/` and the same bytes each time, are a log of 100,000 lines and 2 MB of the tree's Quest source,
ASCII only (Go matches UTF-8). Each program runs once per workload, after one untimed run of each, since the first run
after a build pays for loading the program and its input. Wait for a quiet machine (load under 5 for 3 minutes).

| Workload | What it does |
|---|---|
| `walk` | The lines walked and no regexp: the harness's own cost |
| `literal` | Lines containing `ERROR` |
| `caseless` | Lines containing `(?i)error` |
| `alternation` | Lines containing `\b(?:timeout\|refused\|reset\|unreachable)\b` |
| `prefix` | `user=(\w+)` found in each line |
| `date` | A timestamp with six groups found in each line |
| `anchored` | `^([A-Z]+) ` found in each line |
| `tokens` | `findAll` of a tokenizer's pattern over the source |
| `replace` | `replaceAll` of `\s+` over the source |

The baselines, in order: `0-pike-vm.txt`, the Pike VM alone; `1-scratch.txt`, with each search's scratch reused;
`2-fast-paths.txt`, with the start set, anchoring, and literal patterns; `3-prefix.txt`, with a multi-byte prefix
skipped to. The first three were taken before the untimed first run, so their first row, `literal`, includes the cold
start (about 0.3 s more); the other rows are unaffected.
