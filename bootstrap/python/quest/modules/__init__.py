"""Quest Module and Interface System. (Its modules are imported by name; the
package re-exports nothing, so that importing one does not import the others,
such as the module compiler and its C backend.)

This package provides:
- quest.modules.resolution: Imports resolved once, and the edges between
  interfaces.
- quest.modules.graph: The unit graph: loaded units and their typed forms.
- quest.modules.paths: File discovery, search paths, and canonical name
  computation.
- quest.modules.elaboration: Elaboration of module and interface declarations
  and imports.
- quest.modules.loader: File-based loading, cycle detection, and caching.
- quest.modules.artifacts: the artifacts of separate compilation, .qi files
  (interface_compiler; C headers are the C backend's) and .qm manifests
  (manifest); quest.build.module_compiler writes modules' C and objects.
"""
