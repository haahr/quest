"""Code generation: the backends.

- quest.codegen.backend: their entry points, a typed program or module file
  lowered, its IR's passes run (quest.ir.pipeline), and its code printed.
- quest.codegen.c: the C backend (printing C, its declarations and spellings).

What the backends share is the representation of values (quest.repr) and the
runtime (runtime/quest_runtime.h), so a backend's units link with the C
backend's.
"""
