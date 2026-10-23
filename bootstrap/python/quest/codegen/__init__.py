"""C code generation (the IR's C printer, codegen/backend.py) and host C compilation."""

from quest.codegen.compiler_runner import (
    compile_c_source,
    compile_c_to_object,
    link_objects,
    run_binary,
)

__all__ = [
    "compile_c_source",
    "compile_c_to_object",
    "link_objects",
    "run_binary",
]

