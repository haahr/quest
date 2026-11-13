"""Quest Module and Interface System. (Its modules are imported by name; the
package re-exports nothing, so that importing one does not import the others,
such as the module compiler and its C backend.)

This package provides:
- quest.modules.graph: The unit graph: imports resolved once, loaded units and
  their typed forms, artifact paths.
- quest.modules.paths: File discovery, search paths, and canonical name
  computation.
- quest.modules.elaboration: Elaboration of module and interface declarations
  and imports.
- quest.modules.loader: File-based loading, cycle detection, and caching.
- quest.modules.artifacts: the artifacts of separate compilation, .qi files
  (interface_compiler; C headers are the C backend's), .qm manifests and host
  .o objects (module_compiler, manifest).
"""
