"""Quest Module Compiler (Phase 4.16 Step 2).

Compiles Quest module implementation files (.mod.quest) into:
1. Standard C99 source (<name>.mod.c) including the interface header and defining
   direct C functions (qv_<mod>_<func>), closure trampolines, module record
   (QRecordVal qm_<mod>), and idempotent initialization (qv_mod_<mod>_init).
2. Native relocatable object file (<name>.o) via the host C compiler.

Generated file names keep the .int/.mod of their sources' names, so that the header of an interface named like a
C standard header (math.int.h, not math.h) cannot shadow it (<math.h>) on the C compiler's include path.
"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Optional

import quest.syntax.ast as ast
from quest.modules.stdlib import BuiltinModuleRegistry
from quest.codegen.c.backend import module_file_to_c
from quest.codegen.c.compiler_runner import compile_c_to_object
from quest.codegen.c.headers import ensure_imported_interface_header
from quest.config import CompilerOptions
from quest.diagnostics import in_unit
from quest.modules.manifest import (
    ImportedInterfaceRef,
    ImportedModuleRef,
    ModuleManifest,
    write_qm,
)
from quest.types.env import Environment
from quest.syntax.desugar import desugar
from quest.syntax.grammar import parse_quest_program
from quest.modules.elaboration import elaborate_module
from quest.modules.interface_compiler import indirect_interface_refs
from quest.modules.units import unit_declaration
from quest.modules.loader import load_interface
from quest.modules.graph import Resolver, Roots, UnitGraph, resolve_interface, resolve_module, unit_artifact_dir
from quest.modules.paths import DEFAULT_LIB_DIR, DEFAULT_PROJECT_DIR, resolve_object_file
from quest.syntax.tokenizer import Tokenizer
from quest.syntax.sources import SourceMap, display_file_name


class ModuleCompileResult(tuple):
    """Tuple of (c_file, o_file) with additional metadata attributes."""
    c_file: Path
    o_file: Path
    qm_file: Path

    def __new__(cls, c_file: Path, o_file: Path, qm_file: Path):
        obj = super().__new__(cls, (c_file, o_file))
        obj.c_file = c_file
        obj.o_file = o_file
        obj.qm_file = qm_file
        return obj


def header_search_dirs(output_dir: Path, env: Environment, include_paths: Optional[list[Path]]) -> list[Path]:
    """The directories a module file's C translation is compiled with, where its interface's header is found."""
    search_dirs = [output_dir]
    if env.current_dir:
        search_dirs.append(env.current_dir)
    search_dirs.extend(include_paths or [])
    search_dirs.append(DEFAULT_LIB_DIR)
    search_dirs.append(DEFAULT_PROJECT_DIR)
    return search_dirs


def find_interface_header(interface_name: str, search_dirs: list[Path], header: Optional[Path]) -> Optional[str]:
    """The name a module file's C translation includes its interface's header (.int.h) by, if it has one.

    The interface path as written names the header if the C compiler finds one by that name on its include path;
    otherwise header, the interface's header as C compilation brought it up to date (ensure_imported_interface_header),
    is named relative to the include path.
    """
    header_name = f"{interface_name.lower()}.int.h"
    for s_dir in search_dirs:
        if (s_dir / header_name).is_file():
            return header_name

    if header is not None:
        cand_h = header
        if cand_h.is_file():
            for s_dir in search_dirs:
                try:
                    return str(cand_h.relative_to(s_dir))
                except ValueError:
                    continue
            return cand_h.name
    return None


def compile_module(
    module_decl: ast.ModuleDecl,
    env: Environment,
    output_dir: Optional[Path] = None,
    include_paths: Optional[list[Path]] = None,
    compiler_path: Optional[str] = None,
    nogc: bool = False,
    extra_c_flags: Optional[list[str]] = None,
    source_map: Optional[SourceMap] = None,
    stem_name: Optional[str] = None,
    canonical_name: Optional[str] = None,
    emit_deps: bool = False,
    source_file: Optional[Path] = None,
    build_dir: Optional[Path] = None,
) -> ModuleCompileResult:
    """Compiles an AST ModuleDecl into .mod.c, .o, and .qm files."""
    if output_dir is None:
        output_dir = Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    if getattr(env, "options", None) is None:
        env.options = CompilerOptions(
            stop_after="codegen_c",
            build_dir=build_dir,
            include_paths=list(env.include_paths),
            current_dir=env.current_dir,
            program_dir=env.program_dir,
        )
    else:
        if not env.options.include_paths and env.include_paths:
            env.options.include_paths = list(env.include_paths)
        if env.options.current_dir is None:
            env.options.current_dir = env.current_dir
        if env.options.program_dir is None:
            env.options.program_dir = env.program_dir

    if canonical_name is None and source_file is not None:
        roots = Roots.of(env.include_paths, env.program_dir)
        canonical_name = env.units.resolver.file(source_file, roots).canonical_name

    imported_modules: list[ImportedModuleRef] = []
    imported_interfaces: list[ImportedInterfaceRef] = []

    # 1. Load target interface (from .qi or .int.quest)
    target_interface_scope = env.lookup_interface(module_decl.interface_name)
    if target_interface_scope is None:
        target_interface_scope = load_interface(module_decl.interface_name, env)

    # The manifest records each import as the unit graph resolved it (docs/build-process.md §2.1, §4.3)
    target = resolve_interface(module_decl.interface_name, env)
    tgt_src = target.source
    canon_target_interface = target.interface_name
    tgt_mtime = tgt_src.stat().st_mtime if tgt_src and tgt_src.is_file() else 0.0
    imported_interfaces.append(
        ImportedInterfaceRef(
            name=canon_target_interface,
            source=str(tgt_src.resolve()) if tgt_src else "",
            mtime=tgt_mtime,
            path=module_decl.interface_name,
        )
    )

    # 2. Load any imported interfaces or modules
    for imp in module_decl.imports:
        iface_path = imp.effective_interface_path
        if env.lookup_interface(iface_path) is None and env.lookup_interface(imp.interface_name) is None:
            load_interface(iface_path, env)

        imported = resolve_interface(iface_path, env)
        imp_src = imported.source
        canon_imp_iface = imported.interface_name
        imp_mtime = imp_src.stat().st_mtime if imp_src and imp_src.is_file() else 0.0
        imported_interfaces.append(
            ImportedInterfaceRef(
                name=canon_imp_iface,
                source=str(imp_src.resolve()) if imp_src else "",
                mtime=imp_mtime,
                path=iface_path,
            )
        )

        for iname, mpath in zip(imp.names, imp.effective_module_paths):
            mod_ref = mpath if mpath else iname
            module = resolve_module(mod_ref, env)
            mod_src = module.source
            imported_modules.append(
                ImportedModuleRef(
                    name=module.canonical_name,
                    interface=canon_imp_iface,
                    source=str(mod_src) if mod_src else "",
                    path=mod_ref,
                )
            )

    # 3. Elaborate module
    typed_mod = elaborate_module(module_decl, env)

    # 4. Bring the interface's header (.int.h), which the C translation includes, up to date, and find it
    header = ensure_imported_interface_header(module_decl.interface_name, env)
    search_dirs = header_search_dirs(output_dir, env, include_paths)
    interface_header = find_interface_header(module_decl.interface_name, search_dirs, header)

    mod_name = canonical_name or module_decl.name
    if mod_name != typed_mod.name:
        typed_mod = replace(typed_mod, name=mod_name)

    # 5. Emit C source (exporting the interface's members)
    c_source = module_file_to_c(typed_mod, env, interface_header)

    base = stem_name or module_decl.name.lower()
    c_file = output_dir / f"{base}.mod.c"
    o_file = output_dir / f"{base}.o"
    c_file.parent.mkdir(parents=True, exist_ok=True)
    o_file.parent.mkdir(parents=True, exist_ok=True)

    c_file.write_text(c_source, encoding="utf-8")

    # 6. Compile .c to .o
    compile_dirs = list(dict.fromkeys(search_dirs))
    compile_c_to_object(
        c_file,
        o_file,
        include_paths=compile_dirs,
        nogc=nogc,
        compiler_path=compiler_path,
        extra_flags=extra_c_flags,
    )

    if emit_deps:
        dep_objects: list[str] = []
        for imp in module_decl.imports:
            for iname, mpath in zip(imp.names, imp.effective_module_paths):
                mod_ref = mpath if mpath else iname
                module = resolve_module(mod_ref, env)
                f_path = module.source
                canon = module.canonical_name
                if "/" in canon:
                    obj_rel = f"{canon.lower()}.o"
                    if obj_rel not in dep_objects:
                        dep_objects.append(obj_rel)
                else:
                    # A module with a source is always a dependency, even before its object is built.
                    if f_path is not None or resolve_object_file(canon, env.current_dir, env.include_paths) is not None:
                        obj_rel = f"{canon.lower()}.o"
                        if obj_rel not in dep_objects:
                            dep_objects.append(obj_rel)

        target_rel = f"{mod_name.lower()}.o"
        deps_dir = o_file.parent / ".deps"
        deps_dir.mkdir(parents=True, exist_ok=True)
        dep_file = deps_dir / f"{o_file.stem}.d"
        prereqs_str = " ".join(dep_objects)
        dep_file.write_text(f"{target_rel}: {prereqs_str}\n", encoding="utf-8")

    # 7. Emit .qm metadata file
    qm_file = output_dir / f"{base}.qm"
    manifest = ModuleManifest(
        name=mod_name,
        interface=canon_target_interface,
        source=str(source_file.resolve()) if source_file else "",
        object=str(o_file.resolve()),
        imported_modules=imported_modules,
        imported_interfaces=imported_interfaces
        + indirect_interface_refs(imported_interfaces, env.include_paths, env.program_dir, env.units.resolver),
    )
    write_qm(manifest, qm_file)

    return ModuleCompileResult(c_file, o_file, qm_file)


def compile_module_file(
    mod_path: Path,
    output_dir: Optional[Path] = None,
    include_paths: Optional[list[Path]] = None,
    compiler_path: Optional[str] = None,
    nogc: bool = False,
    extra_c_flags: Optional[list[str]] = None,
    emit_deps: bool = False,
    build_dir: Optional[Path] = None,
    program_dir: Optional[Path] = None,
    resolver: Optional[Resolver] = None,
) -> ModuleCompileResult:
    """Compiles a Quest module file (.mod.quest) into .mod.c, .o, and .qm files.

    program_dir is the directory of the program the module is built for, which names units under no include root
    (docs/modules.md §2.3). The module is elaborated in an environment of its own, whose imports resolver resolves
    (the build's, or a new one if None).
    """
    mod_path = Path(mod_path).resolve()
    if not mod_path.is_file():
        raise FileNotFoundError(f"Module file not found: '{mod_path}'")

    source_text = mod_path.read_text(encoding="utf-8")
    source_map = SourceMap(source_text, display_file_name(mod_path))
    # Errors are located in this file, and the imports it makes are located in it (docs/diagnostics.md §4.4)
    with in_unit(source_map):
        tokenizer = Tokenizer(source_text, str(mod_path))
        tokens = tokenizer.tokenize_all()
        prog = desugar(parse_quest_program(tokens, source_map))

        decl = unit_declaration(prog, mod_path)

        file_name = mod_path.name
        if file_name.endswith(".mod.quest"):
            stem = file_name[:-len(".mod.quest")]
        elif file_name.endswith(".quest"):
            stem = file_name[:-len(".quest")]
        else:
            stem = mod_path.stem

        env = Environment(builtin_registry=BuiltinModuleRegistry)
        env.units = UnitGraph(resolver=resolver or Resolver())
        env.current_dir = mod_path.parent
        env.include_paths = list(include_paths) if include_paths else []
        env.program_dir = program_dir
        env.source_map = source_map
        if build_dir is not None:
            b_dir = Path(build_dir).resolve()
            if b_dir not in env.include_paths:
                env.include_paths.insert(0, b_dir)

        canon_name = env.units.resolver.file(mod_path, Roots.of(env.include_paths, program_dir)).canonical_name

        if build_dir is not None and output_dir is None:
            output_dir = unit_artifact_dir(Path(build_dir).resolve(), canon_name)
        elif output_dir is None:
            output_dir = mod_path.parent
        else:
            output_dir = Path(output_dir).resolve()

        return compile_module(
            decl,
            env,
            output_dir=output_dir,
            include_paths=env.include_paths,
            compiler_path=compiler_path,
            nogc=nogc,
            extra_c_flags=extra_c_flags,
            source_map=source_map,
            stem_name=stem,
            canonical_name=canon_name,
            emit_deps=emit_deps,
            source_file=mod_path,
            build_dir=build_dir,
        )
