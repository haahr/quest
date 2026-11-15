# bootstrap/python/quest/driver: the `questboot` command

This package is the bootstrap compiler's command-line driver, which `./questboot` runs (through
`bootstrap/python/quest_driver.py`). It reads the command line, decides what was asked for, and runs the compiler's
phases, the build engine, or the REPL to do it. It is the original of
[`questlang/driver`](../../../../questlang/driver/README.md), whose README introduces the concepts; this one says
where they are here and what differs. The two drivers take the same command line, the self-hosted one with more
phases and options ([docs/pipeline.md](../../../../docs/pipeline.md) §4, §5).

## The concepts, here

- **The command line.** [`options.py`](options.py) builds two `argparse` parsers: `driver_parser` for running and
  dumping a program, and `compile_parser` for `questboot compile`. `split_program_args` separates the driver's
  arguments from the program's (those after the file, or after `--`), which the program sees as `system.args`.
- **What a run does.** [`main.py`](main.py)'s `run_driver` decides, in an order its docstring lists: hand `compile` to
  `run_compile`; compile a unit file alone or dump its phases (`run_unit_file`); build a program given `-o` with the
  build engine ([`quest/build`](../build/README.md)), each module compiled separately; or else run one phase pipeline
  over the whole program, through the tree-walking interpreter by default, or through the IR, the C backend, and a
  compiled run when a phase or option asks. Afterwards it prints the dumps asked for, the last phrase's result, and
  the diagnostics, and returns the exit status (70 for an internal compiler error, 1 for any other error).
- **Phases.** Unlike questlang's driver, which calls its phases in sequence, the bootstrap's phases are objects
  (`Phase` subclasses) run by a `PhasePipeline`, both in [`quest/pipeline.py`](../pipeline.py) beside this package.
  `default_pipeline`, `compile_pipeline`, `full_pipeline`, and the IR pipelines choose which phases a run goes through;
  `--stop-after` and `--dump-after` name them ([docs/pipeline.md](../../../../docs/pipeline.md) §1 to §3).
- **The REPL.** [`repl.py`](repl.py) reads inputs a line at a time, continuing while an input is incomplete
  (`check_input_completeness`), and evaluates each as a transaction (`QuestREPL.evaluate`): the environment, the unit
  graph, and the interpreter's state are rolled back when an input fails to type-check or raises
  ([docs/repl.md](../../../../docs/repl.md)).

## What differs from questlang/driver

The bootstrap interprets: a program, `-e` code, and every REPL input run in the tree-walking interpreter, since the
bootstrap has no JIT. It has only the C backend, so it has no SSA or arm64 phases, no `ir_simplified` stage, and no
`--backend` choice. It has no Jupyter kernel mode and no parallel-build workers. Its whole-program mode
(`--whole-program`) translates the program and its modules into one C file in the pipeline, rather than merging IR
units as `questlang/driver/whole` does. The translation of a compiled program's error output into a diagnostic,
`questlang/driver/binaryerrors`, is `binary_error_diagnostic` in `quest/pipeline.py`.

## Further reading

- [docs/pipeline.md](../../../../docs/pipeline.md): the phase framework (§1 to §3) and the command line (§4).
- [docs/repl.md](../../../../docs/repl.md): the REPL, including §8 on its two implementations.
- [docs/build-process.md](../../../../docs/build-process.md) §1: separate and whole-program compilation.
