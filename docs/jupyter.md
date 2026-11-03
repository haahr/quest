# Plan: A Jupyter Kernel for Quest

Quest in Jupyter notebooks: a kernel that runs each cell in the self-hosted driver's REPL ([repl.md](repl.md)),
compiled by the JIT ([jit.md](jit.md)), with the session's bindings kept from cell to cell.

---

## 1. Decisions

- **A Python wrapper kernel driving the REPL.** A kernel is a process that Jupyter starts from a kernelspec
  (`kernel.json`), handing it a connection file. The kernel speaks Jupyter's messaging protocol: signed JSON messages
  on five ZeroMQ sockets (shell, iopub, stdin, control, heartbeat). ipykernel's `Kernel` class does all of that, so
  the kernel is a subclass of it, as `bash_kernel` is. It keeps one `quest` process for the session and passes it each
  cell. The REPL already has what a kernel needs:
  - Each input is compiled by the JIT and runs in the driver's own process.
  - Bindings and types carry over from input to input.
  - An input that fails is rolled back (repl.md §5).
  - Diagnostics carry their positions.

  Two alternatives were rejected:
  - A kernel written in Quest would need libzmq bindings, HMAC-SHA256 and UUIDs, only to replace ipykernel.
  - xeus is C++, and the REPL is Quest, not a library linked into a C++ program.
- **The REPL gets a mode for programs, not people.** The kernel does not read the terminal REPL's output (prompts,
  continuation lines, the `==` prefix, results that span lines). `quest --kernel` takes requests and writes records as
  JSON, one per line, on descriptors of their own, using `questlang/values/json`. The program's own output stays on
  standard output and error. The JIT runs the program in the driver's process, so what the program writes never mixes
  with the records, and nothing has to be captured or redirected.
- **The self-hosted driver only.** The kernel needs the JIT, so the bootstrap's REPL gets no kernel mode. Its tests
  are the self-hosted compiler's own (testing.md §2.8), not shared goldens.
- **jupyterlab's Python.** The kernel and its tests run under the Python inside Homebrew's jupyterlab,
  `/opt/homebrew/opt/jupyterlab/libexec/bin/python`. It has ipykernel, jupyter_client and Pygments, and its `opt`
  path survives jupyterlab's upgrades. `/opt/homebrew/bin/python3.11` stays as it is. Its version (3.15 today) is not
  ours to choose, so the kernel's code avoids anything newer than 3.11 needs.
- **A cell shows every phrase's result, as the REPL does.** A cell's `execute_result` holds every result that isn't
  `ok`, in order, one to a line, without the `==` prefix. Notebooks and the REPL's transcripts therefore agree.
- **Interrupting restarts the session at first.** Jupyter interrupts a kernel by sending it SIGINT. Nothing in JIT
  code handles SIGINT, so until step 5, the wrapper ends the `quest` process and starts another. The wrapper itself
  survives. The cell reports that the session restarted and its bindings are gone. Step 5 replaces this with an
  interrupt that unwinds the cell and rolls it back. Its checks are compiled only under `--kernel`.

## 2. The protocol (`quest --kernel`)

The driver reads requests from descriptor 3 and writes records to descriptor 4. Each request and record is one JSON
object on one line, so a cell's newlines are escaped inside its string. A string's characters are bytes, as Quest's
are: each byte above 126 is escaped as `\u00XX` (`questlang/values/json`). The wrapper therefore sends a cell's UTF-8
bytes and decodes records' strings from theirs (`tools/jupyter/quest_session.py`). The driver's standard input is
`/dev/null` until step 4 connects Jupyter's stdin channel. Standard output and error are the program's.

Requests:

- `{"execute": CODE}` runs a cell. CODE is evaluated as one input, the way the REPL evaluates a completed phrase: its
  phrases run in order, and an input that fails is rolled back whole. The REPL's check for incomplete lines doesn't
  apply. A cell that ends in the middle of a phrase gets the syntax error the parser gives at its end.
- `{"complete": CODE, "cursor": N}`: the names that complete the one before byte offset N (the end of CODE if N is
  missing). Its record is `{"matches": NAMES, "start": S, "end": N}`, S where the name begins. After `m.`, they are the
  members of the module m; otherwise the session's bindings and types, its modules and interfaces, and the keywords.
- `{"inspect": CODE, "cursor": N}`: what the name at N is, as the REPL shows a binding (`let a:Int`), or a module's
  members, a line each. Its record is `{"found": true, "text": T}`, or `{"found": false}`.
- `{"isComplete": CODE}`: whether CODE needs more lines, by the REPL's test. Its record is `{"status": S}`, S
  `complete` or `incomplete`.
- Each request ends with a `done` record. The wrapper turns Jupyter's character offsets into byte offsets and back.

Records, for each request in order:

- `{"result": TEXT}`: one phrase's result, as `formatInteractiveResult` shows it (`40 : Int`), lines after the first
  not indented. There is one for each phrase that isn't `ok`.
- `{"error": KIND, "message": M, "rendered": R, "line": L, "column": C}`: why the input failed.
  - KIND is `syntax`, `type`, or the name of an exception the program raised.
  - R is the diagnostic as the REPL renders it (`diagnostics.format`), with its source line, pointers and frames.
  - L and C are given when the diagnostic has a position in the cell.
- `{"done": STATUS}`: STATUS is `ok` or `error`. Nothing more is written for the request.

**Order across the descriptors.** Before writing any record, the driver flushes `writer.output` and `writer.err`.
The pipes are separate, so the wrapper could read a record before output written ahead of it. It therefore drains
standard output and error, without waiting, each time it reads a record. Anything the program wrote before the record
is already in its pipe. The wrapper reads all three descriptors through one `selectors` loop, so a full pipe never
blocks the driver.

## 3. Steps

Each step is a commit or a few. Run times and check runs are recorded as steps finish.

### Step 1: The REPL's kernel mode

- `quest --kernel` (`questlang/driver/main`, `questlang/driver/repl`): a loop that reads requests from descriptor 3 and
  hands each cell to the existing `evaluate`, then writes the records of §2 to descriptor 4. The descriptors are opened
  as `/dev/fd/3` and `/dev/fd/4` through `reader.file` and `writer.file`. A driver started without them reports so
  and exits 2.
- Rendering a diagnostic to a string for `rendered`: `diagnostics.format` exists for one diagnostic. A diagbag's
  diagnostics are rendered in turn.
- Output during a long phrase: `writer.output` writes through C's `stdout`, which is fully buffered on a pipe (and
  `writer.err` through `stderr`, unbuffered). The runtime makes `stdout` line-buffered (`setvbuf(stdout, NULL,
  _IOLBF, 0)`) as it starts, before anything is written, when `QUEST_LINE_BUFFERED` is set, and the wrapper sets it
  for the driver. A driver of its own calling the runtime would need a release between the runtime's commit and the
  driver's (release-compiler.md §2), and an environment variable needs none. A program a cell starts inherits it,
  and is line-buffered too, which a notebook wants. A cell's progress then appears while it runs, as at a terminal,
  for C linked into the program too, at a `write` per line.
  The wrapper sends what is readable as one `stream` message, so bursts of lines don't flood the notebook. A
  pseudo-terminal would make the program think it was at a terminal, and flushing on a timer isn't safe in the
  runtime.
- `quest --help` and repl.md describe the mode.
- *Test:* `tests/python/test_kernel_protocol.py`, using only the standard library (`subprocess` with `pass_fds`). It
  runs the self-hosted driver named by `QUEST_SELF_HOSTED_DRIVER`, as `test_readline_terminal.py` does (testing.md
  §2.7). It runs cells that:
  - bind names and use them in a later cell
  - show several results
  - print and then return a result, checking the order across pipes
  - have syntax and type errors
  - raise an exception, then use a binding from before it to show the rollback
  - import a module the test writes
- *Done when* the test passes, and tools/check runs it. *Done* (2026-11-03, e44abc9f): a unit check of the
  self-hosted suite, `self-hosted/kernel_protocol`, which tools/check runs.

### Step 2: The wrapper kernel

- `tools/jupyter/quest_kernel.py`: an ipykernel `Kernel` subclass. Its `language_info` gives the name `quest`, the
  extension `.quest` and the MIME type `text/x-quest`.
  - It starts `quest --kernel` with the pipes, in a process group of its own. The driver is the `quest` launcher of the
    checkout the kernel was installed from, or `QUEST_KERNEL_DRIVER`.
  - `do_execute` sends a cell, sends standard output and error as `stream` messages as they arrive, and makes the
    results one `execute_result`. An error becomes an `error` reply: its `ename` is KIND, its `evalue` the message and
    its `traceback` the rendered lines.
  - If the driver exits unexpectedly (a crash in JIT code, say), the cell fails with its status and the last of its
    standard error, and a new driver starts.
  - An interrupt (SIGINT to the wrapper, which ipykernel turns into `KeyboardInterrupt` in `do_execute`) ends the
    driver's process group and starts a new driver. The cell's error says the session restarted.
- `tools/jupyter/install` (a shell script running `install.py` with jupyterlab's Python) installs a kernelspec named
  `quest` for the user, its `kernel.json` written then: it names jupyterlab's Python by its `opt` path and this
  checkout's `quest_kernel.py` and `./quest`. `--uninstall` removes it, and `--prefix DIR` installs under
  `DIR/share/jupyter` instead. A notebook then has *Quest* among its kernels. The kernel's first cell after the
  compiler's sources change shows `./quest` rebuilding its stages, as its output.
- *Test:* `tests/self-hosted/jupyter_kernel.py`, a unit check of the self-hosted suite (as step 1's is), under
  jupyterlab's Python with `jupyter_client`'s `KernelManager`. It starts the kernel, runs cells (bindings, output, an
  error, an interrupt during an endless loop, a cell that exits), and checks the messages and the restarts. When
  jupyterlab's Python is missing, it skips the test and says so.
- *Done when* the test passes, and a notebook run by hand in JupyterLab binds, prints, fails and recovers, and restarts
  on an interrupt. *Done* (2026-11-03) but for the hand run: the test passes, and `jupyter nbconvert --execute` ran a
  notebook through a kernel installed with `--prefix` (its first cell showing `./quest` rebuilding). JupyterLab's own
  page is left to its user, since signing in to it takes its token.

### Step 3: Completion, inspection, and complete input

- `complete`: names in scope at the cursor from the REPL's typechecker environment: bindings, modules, a module's
  members after `m.`, and keywords. The wrapper answers `complete_request` with them.
- `inspect`: the type of the name under the cursor, as the REPL shows a binding (`let fib:All(n:Int):Int`), for
  `inspect_request` (Shift-Tab in a notebook).
- `isComplete`: the REPL's `incomplete`, for `is_complete_request`, which `jupyter console` uses to decide whether
  Enter runs the input.
- *Done when* the protocol test and the kernel test cover each, and Tab completes `vector.` in a notebook. *Done*
  (2026-11-03) but for the notebook by hand: both tests cover each, the protocol test completing `vector.ap` after
  `vector` is imported. A module the session has not imported completes only if the library's registry knows its
  name, as using it would (`string.l` does; `vector.` needs `import collections/vector`).

### Step 4: Rich display and input

- A library module, `io/display`: `display.html(s)`, `display.markdown(s)`, `display.png(bytes)`, and
  `display.bundle(mimeTypes values)`.
  - In kernel mode, each writes a `{"display": BUNDLE}` record through a hook the driver installs, after flushing
    standard output so the order holds. The wrapper sends it as `display_data`.
  - Outside kernel mode, each writes its text/plain form to standard output, so programs that use it run anywhere.
- Jupyter's stdin channel: in kernel mode, reading standard input sends an `{"input": PROMPT}` record and waits for
  the reply on descriptor 3. The wrapper asks the notebook with `input_request`. A cell run with input disallowed gets
  end of input.
- *Done when* a notebook shows an HTML table and a PNG drawn by Quest, and a cell reads a line the notebook types.
  *Done* (2026-11-03) but for the notebook by hand. The kernel's driver knows it is one by `QUEST_KERNEL`, which the
  session sets, so `io/display` is Quest alone and `readLine`'s request is the C runtime's: the driver, which could
  install a hook only after a release (release-compiler.md §2), is unchanged. `readLine`'s reply comes on descriptor
  3, so reading standard input otherwise still ends at once. The protocol test checks the records (base64 at each
  padding), and the kernel test `display_data` and an `input_request` answered, and refused when input isn't
  allowed.

### Step 5: Interrupts that unwind

- **Only with `--kernel` (user, 2026-11-02).** The interrupt checks are compiled in, and the handler installed, only
  in a driver started with `--kernel`. Everything else is unchanged and pays nothing:
  - code the JIT compiles for the terminal REPL, for `-e` or for a file
  - every binary `quest compile` writes, on any backend
  - the interpreter outside kernel mode

  Ctrl-C keeps its default meaning there.
- In kernel mode, the driver installs a SIGINT handler that sets a flag. The code the JIT compiles for a cell polls the
  flag at loop back-edges and function entries, and when it is set, raises `system.interrupted`. The cell then fails
  and is rolled back like any other failing input, and its bindings from earlier cells survive. The poll is an option
  of the arm64 code generator, which only kernel mode turns on. The interpreter polls too, under `--kernel --no-jit`.
- Code that is already compiled doesn't poll: the driver's own modules and the library that cells call. A cell stuck
  inside a library call stays uninterruptible until the call returns. If the cell hasn't ended a few seconds after
  SIGINT, the wrapper falls back to restarting the driver, as in step 2.
- The wrapper sends SIGINT to the driver instead of ending it.
- *Measure:* the six of arm64-performance-review.md through the JIT, with and without `--kernel`, so the poll's cost
  to a cell is known. Check that code generated without `--kernel` is identical to before (the SSA and IR goldens
  don't change).
- *Done when* interrupting a cell in an infinite loop in a notebook leaves the session's bindings, nothing compiled
  without `--kernel` changes, and the poll's cost is in benchmarks.md.

### Step 6: Highlighting

- A Pygments lexer for Quest, in `tools/jupyter/` and installed as a plugin with the kernel, named in `language_info`
  as `pygments_lexer`. nbconvert uses it when it exports a notebook to HTML or PDF.
- In the notebook itself, JupyterLab 4's editor is CodeMirror 6, which needs a JupyterLab extension (TypeScript, built
  with jupyterlab's tools) for a new language. That is a separate decision, after steps 1–5. Until then, cells are
  highlighted as plain text.
- *Done when* an exported notebook's Quest cells are highlighted.

### Step 7: Retire the plan

- What remains true moves into the reference documents:
  - the protocol and the mode into repl.md
  - the kernel, its install and its Python into a new section of repl.md or a short `docs/jupyter-kernel.md`
  - the tests into testing.md
  - the interrupt's cost into benchmarks.md
- Whatever is left over goes to tasklist.md, and this document is deleted.

## 4. Later

- Connecting a notebook to a running program (a REPL served on a socket) instead of starting a session.
- Notebooks as tests: running a `.ipynb`'s cells in the protocol test, and comparing outputs.
- The JupyterLab extension of step 6.
