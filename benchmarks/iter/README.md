# util/iter's Benchmark

What a pipeline of iterators costs per element, against a loop written out ([docs/iter.md](../../docs/iter.md) §2).

| Path | What |
|---|---|
| `iter.quest` | The workloads: `PROGRAM WORKLOAD N` runs the workload over the integers below N and prints its sum |
| `run.py` | The runner: it builds `iter.quest` as separate units and with `--whole-program`, runs each workload once in each, checks that both builds print the same sum, and prints the instructions retired per element and the seconds |

```bash
benchmarks/iter/run.py
```

`--elements N` sets the integers walked (20,000,000 by default), and `--only NAME,...` runs some workloads. The
instructions come from `/usr/bin/time -l`, which load barely changes; the seconds need a quiet machine (load under 5
for 3 minutes).

| Workload | What it does |
|---|---|
| `loop` | A `for` loop with the map and filter written inline: what the others are measured against |
| `map` | `range`, `map`, and the program's loop through `iter.more` and `iter.next` |
| `filter` | `range`, `map`, `filter`, and the program's loop |
| `sumInt` | `range`, `map`, `filter`, and `iter.sumInt`, a consumer inside `util/iter`, which reads the closures in place |

At `7e9b5f89`, the library's first version (2026-11-20, arm64), instructions retired per element:

| Workload | Separate | Whole program |
|---|---:|---:|
| `loop` | 17 | 17 |
| `map` | 82 | 56 |
| `filter` | 151 | 116 |
| `sumInt` | 140 | 116 |

Under `--whole-program`, the stages are not inlined into the loop, as they are when `iter.T` is a visible type (11
instructions per element through `map`): the simplifier does not see through the `let` that gives the tuple its
abstract type ([docs/iter.md](../../docs/iter.md) §7).
