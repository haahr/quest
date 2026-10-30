# Rethrowing Caught Exceptions (`else with` and `raised`)

This document specifies an extension that lets a `try`'s `else` branch name the exception it caught, whatever its
type, and raise it again: the binder `else with e then`, and the library module `raised` (`lib/raised.int.quest`,
`lib/raised.mod.quest`), whose type `raised.T` is the binder's type and whose function `raised.reraise` raises a caught
exception again. The plan for implementing it is [raised-plan.md](raised-plan.md).

---

## 1. Motivation

A `try` catches an exception it does not know with `else`, but the `else` branch cannot refer to that exception, so
it cannot raise it again. Code that must do something whenever its body fails, and then let the failure go on (the
idiom other languages call `finally`), can only list the exceptions it expects and raise each again by hand, as
`flushingLog` in `questlang/build/engine.mod.quest`, `loading` in `questlang/modules/loader.mod.quest`, and
`inScope` in `questlang/modules/elaboration.mod.quest` do today:

```quest
let result = try
    body()
when diagnostics.compilerError with err then
    restore()
    diagnostics.raiseError(:A err)
end
```

This is wrong in two ways. An exception the list leaves out (`int.error`, `arrayOp.error`, `stack.overflow`) skips
`restore()`. And raising again is a new raise: the exception is reported at the handler, with the handler's frames,
rather than where it was raised ([exceptions.md](exceptions.md) §1).

With this extension:

```quest
let result = try
    body()
else with e then
    restore()
    raised.reraise(:A e)
end
restore()
result
```

---

## 2. Syntax

A `try`'s `else` branch may name a variable, with `with`, as a `when` branch names its payload:

```
TryBranches ::=
    {"when" Binding ["with" ide [":" Type]] "then" Binding}
    ["else" ["with" ide [":" Type] "then"] Binding]
```

`else with e then body` binds `e` in `body`. Without `with`, `else body` is unchanged. `with` cannot begin a
Binding, so the two forms are told apart by the token after `else`. (`else e then` would need lookahead past the
binding `e`, which today is itself a valid `else` branch.)

The annotation, if written, must be a type equal to `raised.T`.

---

## 3. The Binder's Type

### 3.1. What Was Caught

What an `else` branch catches is not an exception alone but a *raised exception*: an exception, the payload it was
raised with, and (for tracebacks) where it was raised and the frames then active. Its meaning is the existential

```quest
Some(A::TYPE) Tuple exc: Exception(A) payload: A end
```

The raise that made it type checked, so its payload has the type its exception declares, whatever that is. Raising
the two again together is therefore sound without knowing `A`.

Two simpler types are wrong:

- **`Exception` (`Exception(Ok)`) is unsound.** Raising it again would raise the caught exception without its
  payload; if it was `Fail: String`, a handler `when Fail with m` would receive `ok` as a `String`.
- **`Some(A::TYPE) Exception(A)` is sound but useless.** It cannot be raised, as there is no payload of type `A`.

### 3.2. `raised.T`

The binder's type is `raised.T`. The interface declares it abstract (`T::TYPE`, §4.1), as `os/process` declares
`process.T`, and the module defines it as an external type whose C type is `QRaised *`. The type checker knows it, as
it knows `Exception`, so `else with` needs no import: a program imports `raised` only to name the type or to call its
functions. The type an importer of `raised` sees as `raised.T` is the same type: an importer's export scope gives an
abstract type that its module defines as external that external type as its definition (`create_module_export_scope`
in `modules/elaboration.py`, and for the library's modules the externals table's `types` rows in the self-hosted
compiler), and external types are equal when their C types are ([extensions.md](extensions.md)). So a binder's value
can be passed to `raised.reraise`, stored in a variable declared `raised.T`, and so on.

`raised.T` is related to no other type by subtyping, in either direction, other than through `Dynamic` (§4.3). It
is opaque: its exception and payload cannot be selected. (If they could, `raise r.exc with r.payload end` would type
check, but would be a new raise, losing the original site and frames.)

`raise` is unchanged: it raises an `Exception(T)`, and `raise e end` with `e: raised.T` is the existing error
"Cannot raise non-exception type 'raised.T'".

---

## 4. The `raised` Module

### 4.1. Interface

```quest
interface Raised
export
    (* An exception raised and then caught by a try's else branch that names
     * it (else with e then ...), with the payload it was raised with *)
    T::TYPE

    (* Raise r again: the same exception with the same payload, reported, if
     * nothing catches it, where it was first raised and with the frames
     * active then. It does not return, so its result has any type *)
    reraise(A::TYPE r: T): A
end
```

The module:

```quest
module raised : Raised export
    Let T = external "QRaised *"
    let reraise(A::TYPE r: T): A = external "quest_raised_reraise"
end
```

### 4.2. `reraise`

`raised.reraise(r)` raises the exception `r` holds with its payload. To a handler it is indistinguishable from the
original raise: `when E with p` matches it if and only if it matched the original, and `p` is the original payload.
It is the same operation as a `try` re-raising an exception none of its branches matched (`ir.Reraise`), so an
uncaught exception raised again is reported with its original raise site, and, in the interpreters, its original
frames (§5).

`reraise`'s result type `A` is only there so that a call can stand wherever a value is expected, since it does not
return: Quest has no bottom type in its source language. Where the context fixes the type (a checked `let`, a
function body with a declared result, an argument), `A` is inferred; in a position whose type is synthesized, such as
an unannotated `let x = try ... end`, it is written: `raised.reraise(:A e)`, as `raise E as A end` is today.

### 4.3. Values of `raised.T`

- **First-class and immutable.** A binder is a `let`, not a `var`. A value of `raised.T` may be stored, passed,
  returned, and captured by a closure (the binder's scope is a `try_` scope, local by the rules of type-system.md
  §6.2.3), and raised again any number of times, from anywhere, including after its `try` has finished.
- **Independent of later raises.** Exceptions raised and caught while handling it, in the `else` branch or later,
  do not change it.
- **No equality.** `raised.T` has no `is` and no operations other than those of the module.
- **Dynamic.** `dynamic.new(:raised.T e)` packages it as for any type; `dynamic.extern` of it raises
  `dynamic.error`, as for the library's other external types.
- **Display.** The REPL shows a value of `raised.T` as `<hidden>`, as it does the library's other abstract types.

---

## 5. Tracebacks

The rules of [exceptions.md](exceptions.md) apply, with these additions:

- **Interpreters.** A value of `raised.T` holds the caught exception object itself (`QuestException` in the
  bootstrap, the `model.runError` in the self-hosted interpreter), and `reraise` raises that object, which keeps its
  offset and frames (§3.2, §4 there).
- **Compiled code.** A `try` whose `else` names its exception records that it catches everything *and* must capture
  frames: a raise into it captures them (§5.4 there) before jumping to the handler, as for a handler with a pattern
  that is not pure (`CATCH_UNKNOWN`, §5.1 there). The cost falls only on raises that such a handler catches. Without
  it, an exception that `reraise` raises and nothing catches would print the frames active at the `reraise`, not at
  the raise.
- `stack.overflow` cannot be caught in compiled code (§6 there), so it never reaches an `else with` there; in the
  interpreters it is caught and raised again like any other exception.

---

## 6. Representation

- **Bootstrap interpreters** (tree-walking and IR): a value wrapping the caught `QuestException`.
- **Self-hosted interpreters**: a new `Value` form holding the caught `model.runError`.
- **Compiled code**: `QRaised *`, a pointer to a heap copy of the handler's `QExceptionState` (exception, payload,
  site, captured frames), allocated with `quest_alloc` when the binder is bound. Nothing is allocated on any other
  path. `raised.reraise` is the runtime's `QVal quest_raised_reraise(const QTypeDescriptor *a, QRaised *r)`, which never
  returns: it calls `quest_reraise(*r)`.

---

## 7. Not Included

- **More operations on `raised.T`**, which can be added to the module without changing the language: the exception's
  name (`raised.name(r): String`, for logging), a test of whether `r` holds a given exception, and a `finally`-like
  helper, `raised.ensure(A::TYPE body: All() A cleanup: All() Ok): A`, which would replace the hand-written idiom in
  the sites of §1.
- **A binder on `when` branches** for the whole raised exception (`when E as r then`): a known exception can already be
  raised again with its payload.
- **A bottom type** in the source language, which would let `reraise` return it instead of taking a type parameter.
