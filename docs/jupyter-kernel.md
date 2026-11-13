# The Jupyter Kernel

Quest in Jupyter notebooks: a kernel that runs each cell in the self-hosted driver's REPL ([repl.md](repl.md)),
compiled by the JIT ([jit.md](jit.md)), with the session's bindings kept from cell to cell. Its parts:

- **`quest --kernel`**, the REPL's mode for a program: requests and records as JSON lines (§2).
- **`tools/jupyter/quest_kernel.py`**, an ipykernel kernel driving it (§3), through `tools/jupyter/quest_session.py`,
  the protocol's client.
- **`io/display`** and `io/readline` for a notebook's displays and lines (§4).
- **Interrupts** that end a cell and keep its session (§5).
- **A Pygments lexer** for exported notebooks (§6).

---

## 1. Design

- **A Python wrapper kernel driving the REPL.** A kernel is a process that Jupyter starts from a kernelspec
  (`kernel.json`), handing it a connection file. It speaks Jupyter's messaging protocol: signed JSON messages on five
  ZeroMQ sockets. ipykernel's `Kernel` class does all of that, so the kernel is a subclass of it, as `bash_kernel` is.
  It keeps one `quest --kernel` process for the session and passes it each cell. Two alternatives were rejected:
  - A kernel written in Quest would need libzmq bindings, HMAC-SHA256 and UUIDs, only to replace ipykernel.
  - xeus is C++, and the REPL is Quest, not a library linked into a C++ program.
- **The REPL has a mode for programs, not people.** The kernel doesn't read the terminal REPL's prompts and `==`
  lines. The program's own output stays on standard output and error, and the JIT runs the program in the driver's
  process, so what it writes never mixes with the records, and nothing is captured or redirected.
- **The self-hosted driver only.** The kernel needs the JIT, so the bootstrap's REPL has no kernel mode, and the
  kernel's tests are the self-hosted compiler's own (testing.md §2.8).
- **jupyterlab's Python.** The kernel and its tests run under the Python inside Homebrew's jupyterlab,
  `/opt/homebrew/opt/jupyterlab/libexec/bin/python`, which has ipykernel, jupyter_client and Pygments; its `opt` path
  survives jupyterlab's upgrades. `/opt/homebrew/bin/python3.11`, the project's Python, is left as it is. The
  protocol's client needs only the standard library, so the protocol's test runs under either.
- **A cell shows every phrase's result, as the REPL does:** its `execute_result` holds each result that isn't `ok`,
  in order, a line each, without the `==` prefix. Notebooks and the REPL's transcripts therefore agree.
- **No new library or runtime entry for the driver.** `questlang/` can't use a new library function or runtime
  primitive until a release has it (release-compiler.md §2). So the driver uses none: the runtime and the library
  learn they're in a kernel from environment variables the session sets (`QUEST_LINE_BUFFERED`, `QUEST_KERNEL`), and
  the driver reaches the interrupt flag through `os/code`'s `symbol` (§5).

## 2. The Protocol (`quest --kernel`)

The driver reads requests from descriptor 3 and writes records to descriptor 4 (`questlang/driver/repl`'s
`runKernel`), until descriptor 3 ends. Each request and record is one JSON object on one line. A string's characters
are bytes, as Quest's are: each byte above 126 is escaped as `\u00XX` (`questlang/common/json`), so the client sends
a cell's UTF-8 bytes and decodes records' strings from theirs. `--kernel` takes neither a file nor `-e` (arguments
after a `--` are the program's, `system.args`), and `--no-jit` interprets the cells. A driver started without the
descriptors says so and exits 2.

Requests, each answered by its records and then `{"done": STATUS}`, STATUS `ok` or `error`:

- `{"execute": CODE}` runs a cell as one input, the way the REPL runs a completed phrase: its phrases run in order,
  each that isn't `ok` giving `{"result": TEXT}` (`formatInteractiveResult`'s text, `40 : Int`), and an input that
  fails is rolled back whole (repl.md §5) and gives `{"error": KIND, "message": M, "rendered": R, "line": L, "column":
  C}`. KIND is `syntax`, `type`, `compile` (a module the cell imports), `unsupported` (what the JIT can't compile), or
  the name of the exception raised (`int.error`, `interrupted`). R is the diagnostic as the REPL renders it, and L
  and C its position, when it has one in the cell. A cell has no continuation lines: one that ends in the middle of a
  phrase is a syntax error.
- `{"complete": CODE, "cursor": N}`: `{"matches": NAMES, "start": S, "end": N}`, the names completing the one before
  byte offset N, which begins at S. After `m.`, they are the members of the module m, if the session imported or
  declared it or the library's registry knows its name (`string.`, but `collections/vector` must be imported first);
  otherwise the session's bindings and types, its modules and interfaces, and the keywords.
- `{"inspect": CODE, "cursor": N}`: `{"found": true, "text": T}`, what the name at N is, as the REPL shows a binding
  (`let a:Int`), or a module's members, a line each; or `{"found": false}`.
- `{"isComplete": CODE}`: `{"status": S}`, S `incomplete` if the REPL would wait for more lines, else `complete`.

While a cell runs, the program may also write `{"display": BUNDLE}` and `{"input": PROMPT}` records (§4).

**Order across the descriptors.** Before writing a record, the driver flushes `writer.output` and `writer.err`, so
whatever the program wrote before it is already in its pipe. The client reads the three descriptors through one
`selectors` loop, so a full pipe never blocks the driver, and drains standard output and error, without waiting, each
time it reads a record.

**Line buffering.** `writer.output` writes through C's `stdout`, which is fully buffered on a pipe (`writer.err`, C's
`stderr`, is unbuffered). When `QUEST_LINE_BUFFERED` is set and not empty, the runtime makes `stdout` line-buffered as
it starts, before anything is written, so a cell's lines arrive while it runs, as at a terminal, for C linked into the
program too, at a `write` per line. The client sets it; a program the cell starts inherits it, which a notebook wants.
A pseudo-terminal would make the program think it was at a terminal, and flushing on a timer isn't safe in the
runtime.

## 3. The Kernel

`tools/jupyter/quest_kernel.py` subclasses ipykernel's `Kernel`. Its `language_info` names `quest`, `.quest`,
`text/x-quest`, and the Pygments lexer `quest` (§6).

- It starts a session (`quest_session.Session`) when it starts and after one ends: `QUEST_KERNEL_DRIVER --kernel`, with
  `QUEST_KERNEL_OPTIONS` (`--no-jit`, say), in a process group of its own, in the notebook's directory, which the
  cells' imports resolve from.
- `do_execute` sends a cell, passes standard output and error on as `stream` messages as they arrive, the results as
  one `execute_result`, and an error record as an `error` reply: `ename` its KIND, `evalue` its message, `traceback`
  its rendered lines. A display record is `display_data`, and an input record an `input_request` (§4).
- `do_complete`, `do_inspect`, and `do_is_complete` ask the session, turning Jupyter's character offsets into byte
  offsets and back.
- A driver that exits (a crash in JIT code, or a cell calling `system.sysexit`) fails the cell with its status and the
  last of its standard error, and the next cell starts a new session.
- An interrupt is passed to the driver (§5); a cell that hasn't stopped five seconds later (`GRACE`), or a second
  interrupt, ends the session, and the cell's error says so.

**Installing.** `tools/jupyter/install` runs `install.py` with jupyterlab's Python (or `QUEST_JUPYTER_PYTHON`). It
installs a kernelspec named `quest` for the user, its `kernel.json` naming that Python by the path it was started with,
this checkout's `quest_kernel.py`, and its `./quest` as the driver (`--driver`); and the lexer (§6). `--prefix DIR`
installs under `DIR` instead, `--name` names the kernelspec, and `--uninstall` removes both. The first cell after the
compiler's sources change shows `./quest` rebuilding its stages, as its output.

## 4. Displays and Lines

`QUEST_KERNEL`, which the session sets, tells the library it runs in a kernel's driver.

- **`io/display`** (new-libraries.md §3.2), Quest alone, writes a value's forms as a `{"display": {MIMETYPE: DATA}}`
  record to descriptor 4, after flushing the program's output; an image's data (but SVG's) is in base64. Outside a
  kernel it writes the `text/plain` form.
- **`io/readline`'s `readLine`** (new-libraries.md §3.1), in the C runtime, writes `{"input": PROMPT}` to descriptor
  4 and reads the reply from descriptor 3: `L` and the line, or `E` for the end of the input. The kernel answers with
  Jupyter's `input_request` when the cell allows input, and with `E` when it doesn't. The driver's standard input is
  `/dev/null`, so reading it otherwise ends at once, rather than waiting on a pipe nothing writes.

A program a cell starts with `system.run` inherits `QUEST_KERNEL` and descriptors 3 and 4, so a Quest program it
runs displays and reads through the kernel too.

## 5. Interrupts

Jupyter interrupts a kernel with SIGINT, which ipykernel turns into `KeyboardInterrupt` in `do_execute`; the session
sends SIGINT on to the driver. **Only a driver given `--kernel` installs a handler, or checks for one** (a decision of
the user's, 2026-11-02). Everything else is as before and pays nothing: code the JIT compiles for the terminal REPL,
`-e` or a file; every binary `quest compile` writes; and the interpreter outside kernel mode. Ctrl-C keeps its
default meaning there.

- **The runtime** (`quest_runtime.c`) has the flag `quest_interrupt_pending`, a word, which an aligned store from the
  handler writes at once; `quest_interrupt_install`, which installs the handler; and `quest_interrupt_raise`, which
  clears the flag and raises `interrupted`. None is in `quest_runtime.h`.
- **The driver** (`questlang/driver/interrupts`) finds them by name, through `os/code`'s `symbol`, installs the
  handler, and clears the flag before each cell, so an interrupt between cells is forgotten. A driver whose runtime
  lacks them, stage 1, built against the release's, runs without interrupts.
- **The JIT's code** checks the flag at each function's entry and each loop's head: `ssa/interrupts`, run after the
  SSA's passes when the driver asks (`pipeline.setInterruptChecks`; ssa.md §4.1). `QUEST_SKIP_PASSES=interrupts`
  leaves it out.
- **The interpreter** (`--kernel --no-jit`) polls the flag at each loop iteration and call (`treewalk`'s
  `setInterruptPoll`). It has no tail calls, so a function that calls itself forever overflows its stack first.
- **What isn't checked:** code already compiled, the driver's own modules and the library, so a cell stuck in a
  library call (`system.run` of a long command, say) runs on until the call returns; the session's `GRACE` ends it.
- `interrupted` is the runtime's alone, declared by no interface, so a cell can't name it; a `try` with a catch-all
  branch catches it.

**What the checks cost** (benchmarks.md §12): about 2.5 percent of a cell's running time in the six (life, mlyacc,
zebra, and nucleic 2 to 3 percent; ray, unexplained, 10 percent less; hamlet not measurable this way).

## 6. Highlighting

`tools/jupyter/quest_lexer.py` is a Pygments lexer for Quest, its keywords the tokenizer's. jupyterlab's Python has pip
but not setuptools, so `install.py` builds it into a wheel itself (`quest_pygments`, its entry point in
`pygments.lexers`), and installs it with pip. nbconvert then highlights the Quest cells of a notebook that ran (whose
`language_info` names the lexer) when it exports one. In the notebook itself, JupyterLab 4's editor, CodeMirror 6,
would need a JupyterLab extension (tasklist.md).

## 7. Testing

Two unit checks of the self-hosted suite (`UNIT_CHECKS`; testing.md §2.3), which tools/check runs:

- `tests/self-hosted/kernel_protocol.py` drives the protocol with the JIT, and interpreted: bindings, results,
  output's order and line buffering, errors and rollbacks, modules, completion, inspection, complete input,
  displays, lines, interrupts (in a loop, and a recursion, compiled), and a driver's end.
- `tests/self-hosted/jupyter_kernel.py` drives the kernel through `jupyter_client` from a kernelspec in a temporary
  `JUPYTER_PATH`, and checks the lexer, under jupyterlab's Python; it is skipped, saying so, without one.

Neither runs JupyterLab's page, which needs its token to sign in to: a notebook by hand is left to its user.
