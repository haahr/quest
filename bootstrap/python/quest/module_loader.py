"""Quest Module and Interface File Loader.

Implements file-based loading of interfaces and modules for the Quest compiler
and interpreter:
- Resolves interface files as <name.lower()>.int.quest
- Resolves module files as <name.lower()>.mod.quest
- Search order: current file directory first, then include paths (-I)
- Verifies single top-level interface/module declaration matching filename
- Enforces interface conformance and case normalization
- Prevents cyclic dependencies with cycle detection
- Caches loaded modules for singleton evaluation
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import quest.ast as ast
from quest.diagnostics import QuestCompilerError, QuestTypeError
from quest.grammar import parse_quest_program
from quest.tokens import SourceMap, TokenKind, display_file_name
from quest.tokenizer import Tokenizer

if TYPE_CHECKING:
    from quest.env import Environment, Scope
    from quest.interpreter import RuntimeEnvironment
    from quest.runtime import QValue
    from quest.typed_ast import TypedModule

DEFAULT_LIB_DIR = (Path(__file__).parent.parent.parent.parent / "lib").resolve()
DEFAULT_PROJECT_DIR = (Path(__file__).parent.parent.parent.parent).resolve()


def is_c_compilation_mode(env: Environment) -> bool:
    """Checks whether the compiler environment is actively compiling or generating C code."""
    opts = getattr(env, "options", None)
    if opts is None:
        return False
    if getattr(opts, "whole_program", False):
        return False
    if getattr(opts, "stop_after", None) in ("codegen_c", "run_c_compiled"):
        return True
    if getattr(opts, "emit_c", False):
        return True
    if getattr(opts, "output_path", None) is not None:
        return True
    if any(p in ("codegen_c", "run_c_compiled") for p in getattr(opts, "dump_after", ())):
        return True
    return False


def resolve_interface_file(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
) -> Optional[Path]:
    """Finds interface `name` on the search path: a fresh .qi if there is one, else its .int.quest.

    A .qi is fresh when it records this compiler's ABI version and the source it was built from, and is at
    least as new as that source (docs/build-process.md §5.2). Without a source, the first .qi found is returned
    whatever its ABI version; loading it reports an incompatible one.
    """
    from quest.build.abi import built_from, has_current_abi

    source_file = resolve_interface_source_file(name, current_dir, include_paths)
    source_mtime = source_file.stat().st_mtime if source_file is not None else None

    stem = name.lower()
    dirs_to_check: list[Path] = []
    if current_dir is not None:
        dirs_to_check.append(current_dir)
    for inc in include_paths:
        dirs_to_check.append(Path(inc))
    env_lib = os.environ.get("QUEST_LIB")
    if env_lib:
        dirs_to_check.append(Path(env_lib))
    if DEFAULT_LIB_DIR.is_dir():
        dirs_to_check.append(DEFAULT_LIB_DIR)
    if DEFAULT_PROJECT_DIR.is_dir():
        dirs_to_check.append(DEFAULT_PROJECT_DIR)

    for d in dirs_to_check:
        qi_candidate = d / f"{stem}.qi"
        if not qi_candidate.is_file():
            continue
        if source_mtime is None:
            return qi_candidate.resolve()
        if (
            has_current_abi(qi_candidate)
            and qi_candidate.stat().st_mtime >= source_mtime
            and built_from(qi_candidate, source_file)
        ):
            return qi_candidate.resolve()

    return source_file


def resolve_interface_source_file(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
) -> Optional[Path]:
    """Finds <name.lower()>.int.quest in current_dir, include_paths, or DEFAULT_LIB_DIR."""
    filename = f"{name.lower()}.int.quest"
    if current_dir is not None:
        candidate = current_dir / filename
        if candidate.is_file():
            return candidate.resolve()

    for inc in include_paths:
        candidate = Path(inc) / filename
        if candidate.is_file():
            return candidate.resolve()

    env_lib = os.environ.get("QUEST_LIB")
    if env_lib:
        candidate = Path(env_lib) / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_LIB_DIR.is_dir():
        candidate = DEFAULT_LIB_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_PROJECT_DIR.is_dir():
        candidate = DEFAULT_PROJECT_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    return None


def resolve_module_file(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
) -> Optional[Path]:
    """Finds <name.lower()>.mod.quest in current_dir, include_paths, or DEFAULT_LIB_DIR."""
    filename = f"{name.lower()}.mod.quest"
    if current_dir is not None:
        candidate = current_dir / filename
        if candidate.is_file():
            return candidate.resolve()

    for inc in include_paths:
        candidate = Path(inc) / filename
        if candidate.is_file():
            return candidate.resolve()

    env_lib = os.environ.get("QUEST_LIB")
    if env_lib:
        candidate = Path(env_lib) / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_LIB_DIR.is_dir():
        candidate = DEFAULT_LIB_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_PROJECT_DIR.is_dir():
        candidate = DEFAULT_PROJECT_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    return None


def resolve_object_file(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
) -> Optional[Path]:
    """Finds <name.lower()>.o in current_dir, include_paths, or DEFAULT_LIB_DIR."""
    filename = f"{name.lower()}.o"
    if current_dir is not None:
        candidate = current_dir / filename
        if candidate.is_file():
            return candidate.resolve()

    for inc in include_paths:
        candidate = Path(inc) / filename
        if candidate.is_file():
            return candidate.resolve()

    env_lib = os.environ.get("QUEST_LIB")
    if env_lib:
        candidate = Path(env_lib) / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_LIB_DIR.is_dir():
        candidate = DEFAULT_LIB_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_PROJECT_DIR.is_dir():
        candidate = DEFAULT_PROJECT_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    return None


UNIT_SUFFIXES = (".int.quest", ".mod.quest", ".qi", ".o")

# Each directory and file name in a canonical name; anything else could not be mangled into C identifiers
# unambiguously (docs/modules.md §2.3, docs/name-mangling.md §4.1).
_NAME_COMPONENT = re.compile(r"[A-Za-z0-9]+")


def _strip_unit_suffix(filename: str) -> str:
    for ext in UNIT_SUFFIXES:
        if filename.endswith(ext):
            return filename[: -len(ext)]
    return filename


def canonical_roots(include_paths: list[Path], program_dir: Optional[Path] = None) -> list[Path]:
    """Returns the directories canonical names are relative to, in the order canonicalize_module_path tries them.

    The include roots (QUEST_LIB, include paths, lib/, the project directory) come first, deepest first, then the
    program's directory, which names only the units under none of the include roots.
    """
    roots: list[Path] = []
    env_lib = os.environ.get("QUEST_LIB")
    if env_lib:
        roots.append(Path(env_lib).resolve())
    for inc in include_paths:
        roots.append(Path(inc).resolve())
    if DEFAULT_LIB_DIR.is_dir():
        roots.append(DEFAULT_LIB_DIR.resolve())
    if DEFAULT_PROJECT_DIR.is_dir():
        roots.append(DEFAULT_PROJECT_DIR.resolve())
    roots.sort(key=lambda p: len(p.parts), reverse=True)
    if program_dir is not None:
        roots.append(Path(program_dir).resolve())
    return list(dict.fromkeys(roots))


def canonicalize_module_path(
    file_path: Path,
    include_paths: list[Path],
    program_dir: Optional[Path] = None,
) -> str:
    """Computes the canonical hierarchical name of the unit in file_path (e.g. 'util/path').

    The name is the file's path, without its suffix, relative to the first of canonical_roots that contains it
    (docs/modules.md §2.3); a file under none of them is named by its base name. It depends only on the file and
    the roots, not on the import that found it, so importers, the unit itself, manifests, and mangled C symbols
    all agree on it as long as they pass the same include paths and program directory.

    Raises QuestTypeError if a directory or file name in it contains anything but ASCII letters and digits.
    """
    resolved = file_path.resolve()
    parts = [resolved.name]
    for root in canonical_roots(include_paths, program_dir):
        try:
            parts = list(resolved.relative_to(root).parts)
        except ValueError:
            continue
        break
    parts[-1] = _strip_unit_suffix(parts[-1])
    bad = [part for part in parts if not _NAME_COMPONENT.fullmatch(part)]
    if bad:
        raise QuestTypeError(
            f"Invalid module path '{'/'.join(parts)}' for '{resolved}': '{bad[0]}' contains characters other than "
            f"letters and digits, which are the only ones allowed in the directory and file names of interfaces "
            f"and modules"
        )
    return "/".join(parts)


def find_canonical_module_source(
    canon_name: str,
    include_paths: list[Path],
    program_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Finds the module source whose canonical name is canon_name, the inverse of canonicalize_module_path."""
    relative = f"{canon_name.lower()}.mod.quest"
    for root in canonical_roots(include_paths, program_dir):
        candidate = root / relative
        if candidate.is_file() and canonicalize_module_path(candidate, include_paths, program_dir) == canon_name:
            return candidate.resolve()
    return None


def canonicalize_interface_name(
    file_path: Optional[Path],
    include_paths: list[Path],
    declared_name: str,
    program_dir: Optional[Path] = None,
) -> str:
    """Computes canonical hierarchical interface name (e.g. 'util/Path')."""
    if file_path is None:
        return declared_name
    canon_mod = canonicalize_module_path(file_path, include_paths, program_dir)
    base_name = declared_name.split("/")[-1]
    if "/" in canon_mod:
        parent_dir = str(Path(canon_mod).parent)
        return f"{parent_dir}/{base_name}"
    if "/" in declared_name:
        return declared_name
    return base_name


def canonicalize_module_name(
    file_path: Optional[Path],
    include_paths: list[Path],
    raw_name: str,
    program_dir: Optional[Path] = None,
) -> str:
    """Computes canonical hierarchical module name (e.g. 'util/path')."""
    if file_path is None:
        return raw_name
    return canonicalize_module_path(file_path, include_paths, program_dir)


def canonical_import_name(mod_path: str, env: Environment) -> str:
    """Returns the canonical name of the module an import in env's current directory names mod_path.

    Builtin and source-less (precompiled) modules keep the name they are imported by.
    """
    src = resolve_module_file(mod_path, env.current_dir, env.include_paths)
    return canonicalize_module_name(src, env.include_paths, mod_path, env.program_dir)


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
        from quest.interface_compiler import load_interface_from_qi_file
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
    opts = getattr(env, "options", None)
    build_dir = getattr(opts, "build_dir", None)
    if is_c_compilation_mode(env) or build_dir is not None:
        if build_dir is not None:
            out_root = Path(build_dir).resolve()
        elif int_src is not None:
            # Standalone compilation: artifacts go next to the source, under the search root that gives
            # it its canonical name (adding the source's own directory as a root would change that name).
            out_root = int_src.parents[len(Path(canon_name).parts) - 1].resolve()
        elif file_path is not None and "/" in name:
            rel_parts = len(Path(name.lower()).parts)
            out_root = file_path.parents[rel_parts - 1].resolve()
        else:
            out_root = (env.current_dir or Path.cwd()).resolve()
        from quest.interface_compiler import ensure_interface_artifacts
        qi_file, _, _ = ensure_interface_artifacts(
            name, env.current_dir, env.include_paths, out_root, file_path, header=is_c_compilation_mode(env),
            program_dir=env.program_dir,
        )

        if qi_file and qi_file.is_file():
            if out_root not in env.include_paths:
                env.include_paths.insert(0, out_root)
            return _register(_load_qi(qi_file))

    if file_path is None:
        from quest.builtins import BuiltinModuleRegistry
        builtin_iface = BuiltinModuleRegistry.get_interface(name, env)
        if builtin_iface is not None:
            env.register_interface(name, builtin_iface)
            return builtin_iface

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
            from quest.modules import elaborate_interface
            with env.unit_names():
                typed_iface = elaborate_interface(decl, env)
        finally:
            env._loading_interfaces.pop()
            env.current_dir = saved_dir
        if decl.name != name:
            env.register_interface(decl.name, typed_iface.scope)
        return _register(typed_iface.scope)


def _declared_module_name(file_path: Optional[Path], canon_name: str) -> str:
    """Returns the name declared by `module <name>` in file_path, else the last segment of canon_name."""
    fallback = canon_name.split("/")[-1]
    if file_path is None or not file_path.is_file():
        return fallback
    try:
        tokens = Tokenizer(file_path.read_text(encoding="utf-8"), str(file_path)).tokenize_all()
    except (OSError, QuestCompilerError):
        return fallback
    for tok, nxt in zip(tokens, tokens[1:]):
        if tok.kind == TokenKind.KW_MODULE:
            return nxt.lexeme
    return fallback


def _is_typecheck_only(env: Environment) -> bool:
    opts = getattr(env, "options", None)
    return getattr(opts, "stop_after", None) == "typecheck" and not is_c_compilation_mode(env)


def _has_fresh_module_artifacts(file_path: Path, canon_name: str, env: Environment) -> bool:
    """True if module source file_path has up-to-date .qm/.mod.c/.o in the build directory or beside it."""
    from quest.build.manifest import unit_staleness

    build_dir = getattr(getattr(env, "options", None), "build_dir", None)
    stem = Path(canon_name).name.lower()
    candidates = [file_path.parent]
    if build_dir is not None:
        root = Path(build_dir).resolve()
        candidates.insert(0, root / Path(canon_name).parent if "/" in canon_name else root)
    return any(
        unit_staleness(file_path, d / f"{stem}.qm", d / f"{stem}.mod.c", d / f"{stem}.o") is None for d in candidates
    )


def load_module(name: str, expected_interface: str, env: Environment) -> TypedModule:
    """Loads, validates, and elaborates module `name`, as imported from env.current_dir.

    Loaded modules are shared by all importers through env.loaded_modules_ast, keyed by canonical name
    (docs/modules.md §2.3); modules without a source file (builtins and prebuilt objects) by the name imported.
    """
    norm_name = name.lower()
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

        from quest.modules import create_module_export_scope
        # All importers share one export scope (docs/modules.md §2.3). Name opaque exported types after the
        # module's declared name, as elaborating its source does.
        module_export_scope = env.module_export_scopes.get(canon_name)
        if module_export_scope is None:
            module_export_scope = create_module_export_scope(
                _declared_module_name(file_path, canon_name), target_interface_scope, env
            )
            env.module_export_scopes[canon_name] = module_export_scope
        env.register_module(canon_name, module_export_scope)
        if name != canon_name:
            env.register_module(name, module_export_scope)

        from quest.typed_ast import TypedModule
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
    if file_path is not None and _is_typecheck_only(env) and _has_fresh_module_artifacts(file_path, canon_name, env):
        env.precompiled_modules.add(canon_name)
        return _synthesize_precompiled_module()

    if file_path is None:
        from quest.builtins import BuiltinModuleRegistry
        builtin_ast = BuiltinModuleRegistry.get_module_ast(name, env)
        if builtin_ast is not None:
            env.loaded_modules_ast[name] = builtin_ast
            return builtin_ast

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

                from quest.modules import elaborate_module
                from quest.env import Scope
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


def load_module_for_interpreter(
    name: str,
    expected_interface: str,
    r_env: RuntimeEnvironment,
) -> Optional[QValue]:
    """Loads and evaluates module `name`, as imported from r_env.current_dir, for the interpreter.

    Evaluated modules are shared by canonical name (docs/modules.md §2.3), so each is evaluated once.
    """
    file_path = resolve_module_file(name, r_env.current_dir, r_env.include_paths)
    canon_name = canonicalize_module_path(file_path, r_env.include_paths, r_env.program_dir) if file_path else name
    if canon_name in r_env.evaluated_modules:
        return r_env.evaluated_modules[canon_name]

    if canon_name in r_env.loaded_modules_ast:
        typed_mod = r_env.loaded_modules_ast[canon_name]
    else:
        from quest.env import Environment
        type_env = Environment()
        type_env.include_paths = list(r_env.include_paths)
        type_env.current_dir = r_env.current_dir
        type_env.program_dir = r_env.program_dir
        typed_mod = load_module(name, expected_interface, type_env)
        r_env.loaded_modules_ast[canon_name] = typed_mod

    from quest.builtins import BuiltinModuleRegistry
    builtin_rec = BuiltinModuleRegistry.get_runtime_module(name)
    if not typed_mod.bindings and builtin_rec is not None:
        r_env.evaluated_modules[canon_name] = builtin_rec
        return builtin_rec

    from quest.interpreter import eval_binding
    from quest.runtime import QRecord

    # The module's own imports are resolved from its directory.
    mod_env = r_env.push_scope()
    if file_path is not None:
        mod_env.current_dir = file_path.parent
    for b in typed_mod.bindings:
        eval_binding(b, mod_env)

    exported_fields = {}
    for val_name in typed_mod.scope.values:
        exported_fields[val_name] = mod_env.lookup(val_name)

    rec = QRecord(exported_fields)
    r_env.evaluated_modules[canon_name] = rec
    return rec
