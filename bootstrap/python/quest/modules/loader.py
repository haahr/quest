"""Quest Module and Interface File Loader.

Implements file-based loading of interfaces and modules for the Quest compiler and the type checker (the interpreter
evaluates the modules it loads, load_module_for_interpreter in quest.interpreter.treewalk):
- Resolves interface files as <name.lower()>.int.quest or <name.lower()>.qi
- Resolves module files as <name.lower()>.mod.quest
- Search order: current file directory first, then include paths (-I)
- Verifies single top-level interface/module declaration matching filename
- Enforces interface conformance and case normalization
- Prevents cyclic dependencies with cycle detection
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

import quest.syntax.ast as ast
from quest.diagnostics import QuestTypeError
from quest.syntax.grammar import parse_quest_program
from quest.modules.elaboration import (
    create_module_export_scope,
    elaborate_interface,
    elaborate_module,
)
from quest.modules.interface_compiler import (
    ensure_interface_artifacts,
    load_interface_from_qi_file,
)
from quest.modules.paths import (
    DEFAULT_LIB_DIR,
    DEFAULT_PROJECT_DIR,
    canonicalize_module_path,
    declared_module_name,
    has_fresh_module_artifacts,
    is_c_compilation_mode,
    is_typecheck_only,
    resolve_interface_file,
    resolve_interface_source_file,
    resolve_module_file,
    resolve_object_file,
)
from quest.syntax.tokenizer import Tokenizer
from quest.syntax.sources import SourceMap, display_file_name

if TYPE_CHECKING:
    from quest.types.env import Environment, Scope
    from quest.typechecker.typed_ast import TypedModule


def interface_artifact_root(name: str, env: Environment) -> Optional[Path]:
    """The directory under which interface `name`, imported from env.current_dir, has its artifacts when env loads it
    from its .qi (load_interface): the build directory, or in a standalone C compilation (no build directory), the
    search root of its source. None when env elaborates interfaces from source."""
    file_path = resolve_interface_file(name, env.current_dir, env.include_paths)
    int_src = resolve_interface_source_file(name, env.current_dir, env.include_paths)
    if int_src is None and file_path is not None and file_path.name.endswith(".int.quest"):
        int_src = file_path
    unit_file = int_src or file_path
    canon_name = canonicalize_module_path(unit_file, env.include_paths, env.program_dir) if unit_file else name.lower()
    return _artifact_root(name, env, file_path, int_src, canon_name)


def _artifact_root(
    name: str, env: Environment, file_path: Optional[Path], int_src: Optional[Path], canon_name: str
) -> Optional[Path]:
    """interface_artifact_root, given the interface's resolved file, source, and canonical name."""
    opts = getattr(env, "options", None)
    build_dir = getattr(opts, "build_dir", None)
    if build_dir is not None:
        return Path(build_dir).resolve()
    if not is_c_compilation_mode(env):
        return None
    if int_src is not None:
        # Standalone compilation: artifacts go next to the source, under the search root that gives
        # it its canonical name (adding the source's own directory as a root would change that name).
        return int_src.parents[len(Path(canon_name).parts) - 1].resolve()
    if file_path is not None and "/" in name:
        rel_parts = len(Path(name.lower()).parts)
        return file_path.parents[rel_parts - 1].resolve()
    return (env.current_dir or Path.cwd()).resolve()


def load_interface(name: str, env: Environment) -> Scope:
    """Loads, validates, and elaborates interface `name`, as imported from env.current_dir.

    An interface with a file is the one in that file: interfaces loaded from files (or builtins with sources in lib/)
    are shared by all importers, cached by canonical name (docs/modules.md §2.3). Only an interface without a file
    (a builtin, or one declared in the program) is found by the name registered for it. The name is registered for
    the importer.
    """
    norm_name = name.lower()
    file_path = resolve_interface_file(name, env.current_dir, env.include_paths)
    int_src = resolve_interface_source_file(name, env.current_dir, env.include_paths)
    if int_src is None and file_path is not None and file_path.name.endswith(".int.quest"):
        int_src = file_path
    unit_file = int_src or file_path
    canon_name = canonicalize_module_path(unit_file, env.include_paths, env.program_dir) if unit_file else norm_name

    def _register(scope: Scope) -> Scope:
        env.register_interface(name, scope)
        decl_name = name.split("/")[-1]
        if decl_name != name:
            env.register_interface(decl_name, scope)
        if canon_name != name:
            env.register_interface(canon_name, scope)
        if unit_file is not None:
            env.loaded_interfaces[canon_name] = scope
        return scope

    if unit_file is None:
        existing = env.lookup_interface(name)
        if existing is not None:
            return existing
    elif canon_name in env.loaded_interfaces:
        return _register(env.loaded_interfaces[canon_name])

    # Cycle detection
    if canon_name in env._loading_interfaces:
        chain = env._loading_interfaces + [canon_name]
        raise QuestTypeError(
            f"Cyclic dependency detected in interface imports: {' -> '.join(chain)}"
        )

    def _load_qi(qi_file: Path) -> Scope:
        # The .qi records the interface's imports as written in its source, so they are resolved from there.
        saved_dir = env.current_dir
        env.current_dir = int_src.parent if int_src is not None else qi_file.parent
        env._loading_interfaces.append(canon_name)
        try:
            with env.unit_names():
                return load_interface_from_qi_file(qi_file, env)
        finally:
            env._loading_interfaces.pop()
            env.current_dir = saved_dir

    # With a build directory (every driver run) or in C compilation mode, the interface is loaded from its
    # .qi, which is rebuilt first if stale (docs/build-process.md §5).
    out_root = _artifact_root(name, env, file_path, int_src, canon_name)
    if out_root is not None:
        qi_file = ensure_interface_artifacts(
            name, env.current_dir, env.include_paths, out_root, file_path, program_dir=env.program_dir,
        ).qi_file

        if qi_file and qi_file.is_file():
            if out_root not in env.include_paths:
                env.include_paths.insert(0, out_root)
            return _register(_load_qi(qi_file))

    if file_path is None:
        searched = [str(env.current_dir)] if env.current_dir else []
        searched.extend(str(p) for p in env.include_paths)
        if DEFAULT_LIB_DIR.is_dir():
            searched.append(str(DEFAULT_LIB_DIR))
        if DEFAULT_PROJECT_DIR.is_dir():
            searched.append(str(DEFAULT_PROJECT_DIR))
        raise QuestTypeError(
            f"Undefined interface '{name}': cannot find interface file for '{name}' "
            f"(looked for '{norm_name}.qi' or '{norm_name}.int.quest' in {searched})"
        )

    if file_path.suffix == ".qi":
        return _register(_load_qi(file_path))

    try:
        source_text = file_path.read_text(encoding="utf-8")
    except OSError as err:
        raise QuestTypeError(f"Error reading interface file '{file_path}': {err}")

    source_map = SourceMap(source_text, display_file_name(file_path))
    with env.unit_source(source_map):
        tokenizer = Tokenizer(source_text, str(file_path))
        tokens = tokenizer.tokenize_all()
        prog = parse_quest_program(tokens, source_map)

        if not isinstance(prog, ast.Program):
            raise QuestTypeError(f"Malformed parse result in '{file_path}'")

        if len(prog.phrases) != 1:
            raise QuestTypeError(
                f"Interface file '{file_path.name}' must contain only a single interface declaration, "
                f"but found {len(prog.phrases)} phrases"
            )

        decl = prog.phrases[0]
        if not isinstance(decl, ast.InterfaceDecl):
            raise QuestTypeError(
                f"Expected interface declaration in '{file_path.name}', but found {type(decl).__name__}"
            )

        expected_base = file_path.name.split(".")[0].lower()
        if decl.name.lower() != expected_base or decl.name.lower() != norm_name.split("/")[-1]:
            raise QuestTypeError(
                f"Interface declared in '{file_path.name}' has name '{decl.name}', which does not match file name"
            )

        saved_dir = env.current_dir
        env.current_dir = file_path.parent
        env._loading_interfaces.append(canon_name)
        try:
            with env.unit_names():
                typed_iface = elaborate_interface(decl, env)
        finally:
            env._loading_interfaces.pop()
            env.current_dir = saved_dir
        if decl.name != name:
            env.register_interface(decl.name, typed_iface.scope)
        return _register(typed_iface.scope)


def load_module(name: str, expected_interface: str, env: Environment) -> TypedModule:
    """Loads, validates, and elaborates module `name`, as imported from env.current_dir.

    Loaded modules are shared by all importers through env.loaded_modules_ast, keyed by canonical name
    (docs/modules.md §2.3); modules without a source file (builtins and prebuilt objects) by the name imported.
    """
    file_path = resolve_module_file(name, env.current_dir, env.include_paths)
    canon_name = canonicalize_module_path(file_path, env.include_paths, env.program_dir) if file_path else name
    if canon_name in env.loaded_modules_ast:
        return env.loaded_modules_ast[canon_name]

    # Cycle detection
    if canon_name.lower() in [x.lower() for x in env._loading_modules]:
        chain = env._loading_modules + [canon_name]
        raise QuestTypeError(
            f"Cyclic dependency detected in module imports: {' -> '.join(chain)}"
        )

    def _synthesize_precompiled_module() -> TypedModule:
        target_interface_scope = env.lookup_interface(expected_interface)
        if target_interface_scope is None:
            target_interface_scope = load_interface(expected_interface, env)

        # All importers share one export scope (docs/modules.md §2.3). Name opaque exported types after the
        # module's declared name, as elaborating its source does.
        module_export_scope = env.module_export_scopes.get(canon_name)
        if module_export_scope is None:
            module_export_scope = create_module_export_scope(
                declared_module_name(file_path, canon_name), canon_name, target_interface_scope, env
            )
            env.module_export_scopes[canon_name] = module_export_scope
        env.register_module(canon_name, module_export_scope)
        if name != canon_name:
            env.register_module(name, module_export_scope)

        from quest.typechecker.typed_ast import TypedModule
        typed_mod = TypedModule(
            name=canon_name,
            interface_name=expected_interface,
            bindings=(),
            scope=module_export_scope,
            is_precompiled=True,
        )
        env.loaded_modules_ast[canon_name] = typed_mod
        return typed_mod

    # A module with a source is known by its canonical name; prebuilt objects without one are known by name.
    if canon_name in env.precompiled_modules:
        return _synthesize_precompiled_module()

    # Separate compilation of hierarchical modules: importers are typed against the module's interface.
    # Building its object is left to the BuildEngine (docs/build-process.md §7.3).
    if is_c_compilation_mode(env) and ("/" in canon_name or "/" in name) and file_path is not None:
        env.precompiled_modules.add(canon_name)
        return _synthesize_precompiled_module()

    # A typecheck-only run types a module with fresh artifacts through its interface alone, without
    # elaborating its body (docs/build-process.md §5.2.4). Interpreting needs module bodies.
    if file_path is not None and is_typecheck_only(env) and has_fresh_module_artifacts(file_path, canon_name, env):
        env.precompiled_modules.add(canon_name)
        return _synthesize_precompiled_module()

    if file_path is None:
        obj_file = resolve_object_file(name, env.current_dir, env.include_paths)
        if obj_file is not None or name in env.precompiled_modules:
            env.precompiled_modules.add(name)
            return _synthesize_precompiled_module()

        searched = [str(env.current_dir)] if env.current_dir else []
        searched.extend(str(p) for p in env.include_paths)
        if DEFAULT_LIB_DIR.is_dir():
            searched.append(str(DEFAULT_LIB_DIR))
        if DEFAULT_PROJECT_DIR.is_dir():
            searched.append(str(DEFAULT_PROJECT_DIR))
        norm_name = name.lower()
        raise QuestTypeError(
            f"Undefined module '{name}': cannot find module file for '{name}' "
            f"(looked for '{norm_name}.mod.quest' or '{norm_name}.o' in {searched})"
        )

    try:
        source_text = file_path.read_text(encoding="utf-8")
    except OSError as err:
        raise QuestTypeError(f"Error reading module file '{file_path}': {err}")

    source_map = SourceMap(source_text, display_file_name(file_path))
    with env.unit_source(source_map):
        tokenizer = Tokenizer(source_text, str(file_path))
        tokens = tokenizer.tokenize_all()
        prog = parse_quest_program(tokens, source_map)

        if not isinstance(prog, ast.Program):
            raise QuestTypeError(f"Malformed parse result in '{file_path}'")

        if len(prog.phrases) != 1:
            raise QuestTypeError(
                f"Module file '{file_path.name}' must contain only a single module definition, "
                f"but found {len(prog.phrases)} phrases"
            )

        decl = prog.phrases[0]
        if not isinstance(decl, ast.ModuleDecl):
            raise QuestTypeError(
                f"Expected module definition in '{file_path.name}', but found {type(decl).__name__}"
            )

        norm_name = name.lower()
        expected_base = file_path.name.split(".")[0].lower()
        if decl.name.lower() != expected_base or decl.name.lower() != norm_name.split("/")[-1]:
            raise QuestTypeError(
                f"Module declared in '{file_path.name}' has name '{decl.name}', which does not match file name"
            )

        if (
            decl.interface_name != expected_interface
            and decl.interface_name.split("/")[-1] != expected_interface
            and decl.interface_name != expected_interface.split("/")[-1]
        ):
            raise QuestTypeError(
                f"Module '{decl.name}' in '{file_path.name}' implements interface '{decl.interface_name}', "
                f"expected '{expected_interface}'"
            )

        # The interface the importer expects, which the module's header names unless it cannot be resolved from the
        # module's directory (a hierarchical path relative to the program's directory, which is not searched).
        importer_interface = env.lookup_interface(expected_interface)

        saved_dir = env.current_dir
        saved_scope = env.current_scope
        env.current_dir = file_path.parent
        env._loading_modules.append(canon_name)
        try:
            # The module is elaborated with its own interface and module names, resolved from its directory.
            with env.unit_names():
                if (
                    importer_interface is not None
                    and resolve_interface_file(decl.interface_name, env.current_dir, env.include_paths) is None
                ):
                    env.register_interface(decl.interface_name, importer_interface)
                elif env.lookup_interface(decl.interface_name) is None:
                    load_interface(decl.interface_name, env)

                from quest.types.env import Scope
                temp_scope = Scope(parent=env.base_scope, name=f"temp_load_{decl.name}")
                env.current_scope = temp_scope
                typed_mod = elaborate_module(decl, env)
        finally:
            env.current_scope = saved_scope
            env._loading_modules.pop()
            env.current_dir = saved_dir

        # The module is named in C symbols by its canonical name, as importers refer to it. Mangling ignores case,
        # and a name differing only in case (arrayOp) is kept, as builtin modules are known by it.
        if typed_mod.name.lower() != canon_name.lower():
            from dataclasses import replace
            typed_mod = replace(typed_mod, name=canon_name)

        # Importers look the export scope up by the path they imported.
        env.register_module(name, typed_mod.scope)
        if canon_name != name:
            env.register_module(canon_name, typed_mod.scope)
        env.loaded_modules_ast[canon_name] = typed_mod
        return typed_mod
