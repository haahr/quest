# util/regexp's Test Corpora

The files here are copied unchanged from Go's distribution (Go 1.27.1, `$(go env GOROOT)/src/regexp/testdata/`),
which tests Go's `regexp` package with them. `tests/python/test_regexp.py` runs util/regexp against them
([docs/regexp-plan.md](../../../docs/regexp-plan.md) §5).

| File | What it is | How the test uses it |
| :--- | :--- | :--- |
| `re2-search.txt` | RE2's search tests, made by `make log` in RE2's distribution: 944 regexps, each against a set of subjects, with the match and every group's offsets in four modes | Its recorded answers for the two leftmost-first modes, the whole subject and a search; the leftmost-longest modes are not checked |
| `re2-exhaustive.txt.bz2` | RE2's exhaustive tests: every small pattern over a small alphabet against every short string, in the same format | The same, run by hand (`QUEST_REGEXP_EXHAUSTIVE=1`), not in every check |
| `basic.dat`, `nullsubexpr.dat`, `repetition.dat` | Glenn Fowler's AT&T POSIX tests (`testregex`), as Go edited them | Their patterns and subjects, with the answers taken from Go's `regexp` when the test runs: the files record POSIX leftmost-longest answers, which are not this library's |

## What is skipped

A case is skipped, and counted as skipped in the test's output, when:
- its pattern or its subject has a byte above 127: Go and RE2 match UTF-8, this library bytes, until its UTF-8 step
  (§6, step 6);
- its pattern uses a Unicode class (`\p`, `\P`) or RE2's `\C`, which this library does not have;
- (the AT&T files) it is not an extended-syntax (`E`) test, or Go's `regexp` does not compile its pattern.

## Licenses

`re2-search.txt`, `re2-exhaustive.txt.bz2`, and Go's edits to the `.dat` files are distributed with Go under its BSD
license, in `LICENSE-go` here.

The `.dat` files are AT&T's, under the license in `testregex.c`, which covers "testregex.c and all associated test
data":

> Permission is hereby granted, free of charge, to any person obtaining a copy of THIS SOFTWARE FILE (the
> "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy,
> modify, merge, publish, distribute, and/or sell copies of the Software, and to permit persons to whom the Software
> is furnished to do so, subject to the following disclaimer:
>
> THIS SOFTWARE IS PROVIDED BY AT&T ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
> THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
> AT&T BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
> NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
> INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
> (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
> POSSIBILITY OF SUCH DAMAGE.
