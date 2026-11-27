"""The artifacts of separate compilation: interfaces compiled into .qi files
(interface_compiler.py), and the .qm manifests of modules and programs
(manifest.py), which the build's module compiler (quest.build.module_compiler)
writes with their C and objects. The self-hosted counterpart is
questlang/modules/artifacts/, which holds the interfaces' fingerprints too."""
