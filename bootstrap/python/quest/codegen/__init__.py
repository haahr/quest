"""Code generation: what the backends share, and the backends.

- quest.codegen.backend: the IR's passes after lowering, and a unit's implicit imports.
- quest.codegen.canonical, layout, descriptors: reduced and canonical types, how values are laid out (their
  representations, the runtime's), and runtime descriptors' type-level forms.
- quest.codegen.symbols: the names units link against.
- quest.codegen.c: the C backend (printing C, its declarations and spellings, and the host C compiler).

What is shared is the runtime's (runtime/quest_runtime.h), so a backend's units link with the C backend's.
"""
