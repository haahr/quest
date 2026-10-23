"""Quest Module and Interface System.

This package provides:
- quest.modules.paths: File discovery, search paths, and canonical name computation.
- quest.modules.elaboration: Elaboration of module and interface declarations and imports.
- quest.modules.loader: File-based loading, cycle detection, and caching.
- quest.modules.interface_compiler: Compilation of .int.quest into .qi and C .int.h headers.
- quest.modules.module_compiler: Separate compilation of .mod.quest into .qm manifests and host .o objects.
- quest.modules.manifest: Module manifest (.qm) serialization, deserialization, and staleness.
"""

from __future__ import annotations

# 1. Elaboration
from quest.modules.elaboration import (
    build_record_type_from_scope,
    create_module_export_scope,
    elaborate_import,
    elaborate_interface,
    elaborate_module,
    import_interface,
    separately_compiled_module_scope,
)

# 2. Paths and Name Canonicalization
from quest.modules.paths import (
    DEFAULT_LIB_DIR,
    DEFAULT_PROJECT_DIR,
    UNIT_SUFFIXES,
    canonical_import_name,
    canonical_roots,
    canonicalize_interface_name,
    canonicalize_module_name,
    canonicalize_module_path,
    declared_module_name,
    find_canonical_module_source,
    has_fresh_module_artifacts,
    is_c_compilation_mode,
    is_typecheck_only,
    resolve_interface_file,
    resolve_interface_source_file,
    resolve_module_file,
    resolve_object_file,
    strip_unit_suffix,
)

# 3. Loader
from quest.modules.loader import (
    load_interface,
    load_module,
)

# 4. Interface Compiler
from quest.modules.interface_compiler import (
    compile_interface_file,
    compile_interface_to_header,
    compile_interface_to_qi,
    ensure_interface_artifacts,
    load_interface_from_qi_file,
)

# 5. Module Compiler
from quest.modules.module_compiler import (
    ModuleCompileResult,
    compile_module,
    compile_module_file,
)

# 6. Manifest (.qm)
from quest.modules.manifest import (
    ImportedInterfaceRef,
    ImportedModuleRef,
    ModuleManifest,
    is_manifest_stale,
    read_qm,
    unit_staleness,
    write_qm,
)

