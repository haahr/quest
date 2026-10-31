---
name: write-clear-comments
description: Write or revise comments in this tree (Quest, Python, or C) for functions, types, modules, interfaces, or code inside blocks, so that they explain why and how the code does what it does, with the context a reader needs. Use when asked to write, add, improve, or review comments or docstrings, or when new code needs them.
---

# Writing Clear Comments

A comment in this tree tells the reader what the code is for, why it is built the way it is, and how it works where
that is not plain from the code. It gives the context the code cannot: the invariant relied on, the case handled, the
other part of the compiler this depends on, the document that specifies it.

## The Reader

Write for a computer scientist who knows Quest well enough to read it, knows functional languages generally (ML,
Haskell: algebraic data types, pattern matching, closures, polymorphism), and likely Python and C. They are *not* an
expert in compiler design, type theory, or Quest's internals. They know what a parser, a type checker, and a register
are, but not what a "coinductive trail", "hash-consed type", "spill slot", or "existential" means here without a few
words of explanation, or why this compiler needs one.

## What a Good Comment Does

- **Why before how.** Say what problem the code solves and why it takes this approach, especially when the obvious
  approach would be wrong ("Pairs involving a metavariable are never cached, because isSubtype solves metavariables
  as a side effect"). Then say how, where the mechanism is not plain from the code.
- **Context.** Name what the code relies on or serves: the caller's expectation, the invariant, the other compiler
  (the bootstrap's counterpart of a self-hosted function), the runtime function, the document and section
  (`docs/exceptions.md` §5.1). Say what happens on failure: what is raised, what is left unchanged.
- **Terms of art, briefly glossed.** Use the precise term, and the first time a term a generalist may not know
  appears in a comment, give it a few words ("a trail, the subtyping assumptions made so far, which let a proof about
  recursive types end"). Do not write a tutorial; link to the document instead.
- **Direct and short.** Declarative sentences; the subject first; no filler ("This function is used to...", "Note
  that", "basically"). A one-line function often needs a one-line comment or none. Length follows the difficulty of the
  code, not its size.
- **Describe the code as it is.** No history ("now", "previously", "fixed", "new"): that belongs in commit messages.
  No narration of the statements that follow ("loop over the list", "increment i").
- **Concrete over abstract.** An example input, a case the code handles, or the shape of a value is often clearer
  than a general statement.

### By Kind of Comment

- **Module and interface headers:** what the unit provides and its place in the compiler or library, the main data it
  works on, its counterpart in the other compiler, and its document. Self-hosted units start
  `(* Quest Self-Hosted Compiler: <Topic> Implementation *)` (or `Interface`), with the description after a blank
  comment line.
- **Functions:** what it returns or does in terms of its parameters by name, what it requires of them, what it
  raises, and side effects (state changed, state restored). Quest comments on functions often read as a noun phrase
  for the result: `(* body with the current scope s, which is restored even if body raises an exception *)`.
- **Types:** what a value represents, the meaning of each field or case that is not obvious from its name, and the
  invariants a value keeps (sorted, never empty, ids unique).
- **Inside code blocks:** only where the reader would stop and ask why: a non-obvious ordering, a case that seems
  impossible but is not, a deliberate omission, a workaround and what it works around.
- **Section banners** (`(* ====...` with a numbered title) group a long module; follow the module's existing banners.

## Mechanics

- **Wrap comments at 80 columns,** indentation included (docs/instructions.md §4), even though code goes to 120.
  Keep examples, aligned text, and lists on lines of their own.
- **Quest:** `(* ... *)`, continuation lines starting ` * ` aligned under the opening `*`, the closing `*)` on the last
  text line. No period after a single noun phrase or sentence, matching the tree; multiple sentences end with periods
  except the last, as the surrounding code does.
- **Python:** docstrings for modules, classes, and functions; `#` comments inside code. **C:** `/* ... */` as in
  `runtime/`.
- **Match the surrounding code's density and idiom.** Don't comment every binding in a module that comments few; don't
  leave a hard function bare in a module that explains its hard functions.
- **Names in comments are real.** Refer to code by its name (`quest_reraise`, `createModuleExportScope`) and check
  that it exists.

## The Process

Write every comment in three passes. Do them in order, for each comment or batch of comments; show the final result,
and summarize what the later passes changed only if asked.

### 1. Draft as a Compiler Expert

Write the comment as someone who knows this compiler, compiler construction, and type theory thoroughly would: read
the code, its callers, and its callees first, and state precisely what it does, why, and what it depends on. Favor
completeness and precision over accessibility in this pass: get every relevant fact down.

### 2. Critique and Revise as a Generalist

Reread the draft as the reader above, a computer scientist who is not a compiler expert, and ask:

- Which terms would I not know, or know with a different meaning? Gloss them or replace them with plain words.
- What context am I missing to see why this matters: what would go wrong without this code?
- Is the why there, or only the what?
- Which sentences could I drop without losing anything? Which are hard to parse? Is it longer than the code merits?
- Would an example make it clear faster?

Revise for each answer. Keep the precision of the draft; clarity must not come from vagueness.

### 3. Review for Accuracy

Check every claim in the revised comment against the code, not against memory or the draft:

- Read the code the comment describes, and the callers and callees it mentions. Does the code do exactly this, in
  every case (empty input, failure path, the case the comment calls impossible)?
- Do the names, files, and document sections it cites exist, and say what the comment says they say?
- Are claims about the other compiler, the runtime, or a document true of them now?
- Did simplifying in pass 2 make something false ("always" where it is "usually", a dropped exception)?

Fix what is wrong, and if a fix brings back expert terms, apply pass 2 to that part again. If the code itself
looks wrong, say so to the user rather than writing a comment that describes the bug as intended.

## Examples

Too expert, no why:

```quest
(* Memoizes synthUncached under the active memo; clears it on unwind *)
```

Narration, no context:

```quest
(* Set active to a new memo, call synthUncached, then set active to none *)
```

Clear:

```quest
(* The kind of t. Elaborated types share subterms (an alias used twice is
 * one node), so a naive walk checks a shared subterm once per path to it.
 * The outermost call keeps the kinds it finds in a memo, by node id, that
 * nested calls with the same environment reuse; the memo is dropped when that
 * call returns or raises *)
```

(The first draft of this example said the memo was for recursive types. Pass 3, reading the code and its existing
comment, showed that the reason is sharing.)

Before finishing, check that the comment would still be true and useful to someone reading this code a year from
now, without this conversation.
