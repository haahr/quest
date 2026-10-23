"""Quest Module, Interface, and Import Elaboration (Phase 6).

Implements Cardelli's module system for Quest:
- Interface declarations with type formals, manifest types, and value signatures.
- Module definitions with conformance checking (type equality, subkinding, subtyping).
- Information hiding via opaque type variables for abstract interface types.
- Top-level and module-level import resolution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import quest.syntax.ast as ast
from quest.diagnostics import Diagnostic, QuestCompilerError, QuestTypeError, at_import, diagnostic_of
from quest.elaborate_types import (
    elaborate_kind,
    elaborate_kind_binding,
    elaborate_type,
    elaborate_type_binding,
    elaborate_type_binding_group,
)
from quest.env import (
    Environment,
    Scope,
    TypeSymbol,
    ValueSymbol,
)
from quest.modules.paths import (
    canonical_import_name,
    canonicalize_module_name,
    declared_module_name,
    is_c_compilation_mode,
    resolve_module_file,
    resolve_object_file,
)
from quest.typed_ast import (
    TypedBinding,
    TypedImport,
    TypedImportItem,
    TypedInterface,
    TypedModule,
)
from quest.types import (
    TYPE_KIND,
    KindError,
    QExternalType,
    QRecordField,
    QRecordType,
    QType,
    QTypeVar,
    check_kind,
    is_subkind,
    is_subtype,
    is_type_equal,
)


def build_record_type_from_scope(scope: Scope, provenance: Optional[str] = None) -> QRecordType:
    """Constructs a QRecordType matching the values exposed by a module or interface scope."""
    fields = [
        QRecordField(name=name, type_val=sym.type_val, is_var=sym.is_var)
        for name, sym in scope.values.items()
    ]
    return QRecordType(tuple(fields), provenance=provenance)


def import_interface(iface_path: str, local_name: str, env: Environment) -> Scope:
    """Returns the interface an import names by iface_path, binding it to local_name (and iface_path) in env.

    The path is resolved from env.current_dir, so an earlier import's binding of the same local name (`Counter`
    for both `counter.int.quest` and `util/counter.int.quest`) does not stand in for it (docs/modules.md §2.3).
    """
    from quest.modules.loader import load_interface
    scope = load_interface(iface_path, env)
    env.register_interface(local_name, scope)
    if iface_path != local_name:
        env.register_interface(iface_path, scope)
    return scope


def elaborate_interface(decl: ast.InterfaceDecl, env: Environment) -> TypedInterface:
    """Elaborates an interface declaration into a specification scope and TypedInterface."""
    import_scope = Scope(name=f"interface_imports_{decl.name}", parent=env.current_scope)
    interface_scope = Scope(name=f"interface_{decl.name}", parent=import_scope)
    interface_scope.module_name = decl.name

    # 1. Resolve imports into import_scope (available for signatures, not exported by interface)
    for imp in decl.imports:
        with at_import(imp.offset, env.source_map):
            iface_path = imp.effective_interface_path
            source_interface_scope = import_interface(iface_path, imp.interface_name, env)

            if not imp.names:
                # Unaliased interface import / interface inheritance
                is_alias = imp.interface_path is not None and imp.interface_name != imp.effective_interface_path
                target_scope = import_scope if is_alias else interface_scope
                for type_name, type_sym in source_interface_scope.types.items():
                    target_scope.declare_type(type_sym)
                for kind_name, kind_sym in source_interface_scope.kinds.items():
                    target_scope.declare_kind(kind_sym)
            else:
                for name, mod_path in zip(imp.names, imp.effective_module_paths):
                    type_symbol = source_interface_scope.lookup_type_local(name)
                    if type_symbol is not None:
                        interface_scope.declare_type(type_symbol)
                        continue
                    value_symbol = source_interface_scope.lookup_value_local(name)
                    if value_symbol is not None:
                        interface_scope.declare_value(value_symbol)
                        continue
                    kind_symbol = source_interface_scope.lookup_kind_local(name)
                    if kind_symbol is not None:
                        interface_scope.declare_kind(kind_symbol)
                        continue

                    from quest.modules.loader import load_module
                    mod_scope = None
                    if (
                        mod_path in env.loaded_modules_ast
                        or mod_path in env.precompiled_modules
                        or resolve_module_file(mod_path, env.current_dir, env.include_paths) is not None
                        or resolve_object_file(mod_path, env.current_dir, env.include_paths) is not None
                    ):
                        try:
                            typed_mod = load_module(mod_path, iface_path, env)
                            mod_scope = typed_mod.scope
                        except (QuestCompilerError, OSError) as err:
                            if getattr(env, "sink", None) is not None:
                                if isinstance(err, QuestCompilerError):
                                    env.sink.emit(diagnostic_of(err))
                                else:
                                    env.sink.emit(Diagnostic.make_from_exception(err, 0))
                            mod_scope = None

                    registered_scope = (
                        mod_scope if mod_scope is not None
                        else separately_compiled_module_scope(mod_path, source_interface_scope, env)
                    )
                    env.register_module(name, registered_scope)
                    if mod_path != name:
                        env.register_module(mod_path, registered_scope)
                    mod_type = build_record_type_from_scope(
                        registered_scope, provenance=name
                    )
                    import_scope.declare_value(ValueSymbol(name=name, type_val=mod_type))

    # 2. Elaborate signatures in a child scope of the interface
    saved_scope = env.current_scope
    env.current_scope = interface_scope
    try:
        for sig in decl.signatures:
            match sig:
                case ast.TypeFormal(name=name, bound=bound):
                    bound_kind = elaborate_kind(bound, env) if bound else TYPE_KIND
                    symbol_id = env.fresh_symbol_id()
                    type_symbol = TypeSymbol(name=name, symbol_id=symbol_id, kind=bound_kind, definition=None)
                    interface_scope.declare_type(type_symbol)

                case ast.TypeBinding():
                    type_symbol = elaborate_type_binding(sig, env)
                    interface_scope.declare_type(type_symbol)

                case ast.TypeBindingGroup():
                    for type_symbol in elaborate_type_binding_group(sig, env):
                        interface_scope.declare_type(type_symbol)

                case ast.FieldSig(name=field_name, type_sig=type_sig, mode=mode):
                    if field_name:
                        val_type = elaborate_type(type_sig, env)
                        val_symbol = ValueSymbol(
                            name=field_name,
                            type_val=val_type,
                            is_var=(mode == ast.ParamMode.VAR),
                            is_out=(mode == ast.ParamMode.OUT),
                        )
                        interface_scope.declare_value(val_symbol)

                case ast.DefKindBinding():
                    kind_symbol = elaborate_kind_binding(sig, env)
                    interface_scope.declare_kind(kind_symbol)
    finally:
        env.current_scope = saved_scope

    env.register_interface(decl.name, interface_scope)
    return TypedInterface(name=decl.name, signatures=(), scope=interface_scope, offset=decl.offset)


def extract_module_external_types(src: Optional[Path]) -> dict[str, QType]:
    """Extracts external type declarations (Let T = external "...") from a module source file."""
    if src is None or not src.is_file():
        return {}
    try:
        source_text = src.read_text(encoding="utf-8")
        from quest.syntax.grammar import parse_quest_program
        from quest.syntax.sources import SourceMap
        from quest.syntax.tokenizer import Tokenizer

        source_map = SourceMap(source_text, src.name)
        tokens = Tokenizer(source_text, str(src)).tokenize_all()
        prog = parse_quest_program(tokens, source_map)
        if isinstance(prog, ast.Program) and len(prog.phrases) == 1:
            decl = prog.phrases[0]
            if isinstance(decl, ast.ModuleDecl):
                defs: dict[str, QType] = {}
                for b in decl.bindings:
                    if isinstance(b, ast.TypeBinding) and isinstance(b.type_val, ast.TypeExternal):
                        defs[b.name] = QExternalType(name=f"{decl.name}.{b.name}", c_type=b.type_val.c_type)
                return defs
    except Exception:
        pass
    return {}


def separately_compiled_module_scope(mod_path: str, interface_scope: Scope, env: Environment) -> Scope:
    """Returns the export scope of a module known only through its interface (separate compilation).

    Each module gets its own opaque copies of the interface's abstract types, exactly as elaborating
    its source would, so that two modules implementing one interface never share an abstract type.
    """
    src = resolve_module_file(mod_path, env.current_dir, env.include_paths)
    canon = canonicalize_module_name(src, env.include_paths, mod_path, env.program_dir)
    loaded = env.loaded_modules_ast.get(canon)
    mod_scope = loaded.scope if loaded is not None else env.module_export_scopes.get(canon)
    if mod_scope is None:
        concrete_defs = extract_module_external_types(src)
        mod_scope = create_module_export_scope(
            declared_module_name(src, mod_path), canon, interface_scope, env, concrete_defs=concrete_defs
        )
        env.module_export_scopes[canon] = mod_scope
    env.register_module(mod_path, mod_scope)
    return mod_scope


def create_module_export_scope(
    module_name: str,
    canon: str,
    target_interface_scope: Scope,
    env: Environment,
    concrete_defs: Optional[dict[str, QType]] = None,
) -> Scope:
    """Creates the exported scope for a module conforming to an interface scope.

    canon is the module's canonical name. Each abstract type's opaque type has the symbol id of its global name,
    canon.T, in every environment (docs/dynamic.md §2.3).
    """
    from quest.modules.abstract_types import abstract_type_symbol_id, register_exported_abstract_type

    module_export_scope = Scope(name=f"module_export_{module_name}")
    module_export_scope.module_name = module_name
    export_type_subst: dict[int, QType] = {}

    for type_name, interface_type_symbol in target_interface_scope.types.items():
        if interface_type_symbol.definition is None:
            export_sym_id = abstract_type_symbol_id(f"{canon}.{type_name}")
            if (
                concrete_defs is not None
                and type_name in concrete_defs
                and isinstance(concrete_defs[type_name], QExternalType)
            ):
                ext_def: Optional[QType] = concrete_defs[type_name]
            else:
                ext_def = None
            opaque_type_symbol = TypeSymbol(
                name=type_name,
                symbol_id=export_sym_id,
                kind=interface_type_symbol.kind,
                definition=ext_def,
            )
            module_export_scope.declare_type(opaque_type_symbol)
            opaque_type = QTypeVar(
                name=f"{module_name}.{type_name}",
                symbol_id=export_sym_id,
                bound=interface_type_symbol.kind,
            )
            export_type_subst[interface_type_symbol.symbol_id] = opaque_type
            if ext_def is None:
                register_exported_abstract_type(f"{canon}.{type_name}", opaque_type)
        else:
            manifest_type_symbol = TypeSymbol(
                name=type_name,
                symbol_id=env.fresh_symbol_id(),
                kind=interface_type_symbol.kind,
                definition=interface_type_symbol.definition,
            )
            module_export_scope.declare_type(manifest_type_symbol)

    for val_name, interface_val_symbol in target_interface_scope.values.items():
        exported_val_type = interface_val_symbol.type_val.substitute(export_type_subst)
        module_export_scope.declare_value(
            ValueSymbol(
                name=val_name,
                type_val=exported_val_type,
                is_var=interface_val_symbol.is_var,
                is_out=interface_val_symbol.is_out,
            )
        )

    return module_export_scope


def _register_abstract_types(canon: str, export_scope: Scope, internal_scope: Scope) -> None:
    """Records the abstract types a module exports with their representations (docs/dynamic.md §2.3)."""
    from quest.modules.abstract_types import register_abstract_type_representation

    for type_name, export_sym in export_scope.types.items():
        internal_sym = internal_scope.types.get(type_name)
        if export_sym.definition is not None or internal_sym is None or internal_sym.definition is None:
            continue
        type_var = QTypeVar(name=f"{export_scope.module_name}.{type_name}", symbol_id=export_sym.symbol_id,
                            bound=export_sym.kind)
        register_abstract_type_representation(f"{canon}.{type_name}", type_var, internal_sym.definition)


def elaborate_module(
    decl: ast.ModuleDecl,
    env: Environment,
    binding_elaborator: Optional[Callable[[ast.BindingNode, Environment, int], TypedBinding]] = None,
) -> TypedModule:
    """Elaborates and typechecks a module against its interface, enforcing information hiding."""
    target_interface_scope = env.lookup_interface(decl.interface_name)
    if target_interface_scope is None:
        from quest.modules.loader import load_interface
        target_interface_scope = load_interface(decl.interface_name, env)

    module_internal_scope = Scope(name=f"module_internal_{decl.name}", parent=env.base_scope)

    # 1. Resolve imports into module_internal_scope
    import_symbols: list[list[Optional[ValueSymbol]]] = []
    for imp in decl.imports:
        symbols: list[Optional[ValueSymbol]] = []
        import_symbols.append(symbols)
        with at_import(imp.offset, env.source_map):
            iface_path = imp.effective_interface_path
            source_interface_scope = import_interface(iface_path, imp.interface_name, env)

            if not imp.names:
                for type_name, type_sym in source_interface_scope.types.items():
                    module_internal_scope.declare_type(type_sym)
                for kind_name, kind_sym in source_interface_scope.kinds.items():
                    module_internal_scope.declare_kind(kind_sym)
            else:
                for local_name, mod_path in zip(imp.names, imp.effective_module_paths):
                    symbols.append(None)
                    if local_name == mod_path:
                        type_symbol = source_interface_scope.lookup_type_local(local_name)
                        if type_symbol is not None:
                            module_internal_scope.declare_type(type_symbol)
                            continue
                        value_symbol = source_interface_scope.lookup_value_local(local_name)
                        if value_symbol is not None:
                            module_internal_scope.declare_value(value_symbol)
                            continue
                        kind_symbol = source_interface_scope.lookup_kind_local(local_name)
                        if kind_symbol is not None:
                            module_internal_scope.declare_kind(kind_symbol)
                            continue
                    from quest.modules.loader import load_module
                    if is_c_compilation_mode(env):
                        mod_scope = separately_compiled_module_scope(mod_path, source_interface_scope, env)
                        mod_type = build_record_type_from_scope(
                            mod_scope, provenance=local_name
                        )
                        registered_scope = mod_scope
                    else:
                        if mod_path not in env.loaded_modules_ast:
                            load_module(mod_path, iface_path, env)
                        mod_scope = separately_compiled_module_scope(mod_path, source_interface_scope, env)
                        mod_type = build_record_type_from_scope(
                            mod_scope, provenance=local_name
                        )
                        registered_scope = mod_scope
                    env.register_module(mod_path, registered_scope)
                    if local_name != mod_path:
                        env.register_module(local_name, registered_scope)
                    symbols[-1] = ValueSymbol(name=local_name, type_val=mod_type)
                    module_internal_scope.declare_value(symbols[-1])

    # 2. Elaborate module internal bindings
    if binding_elaborator is None:
        from quest.typechecker.typecheck import elaborate_binding
        binding_elaborator = elaborate_binding

    saved_scope = env.current_scope
    env.current_scope = module_internal_scope
    typed_bindings: list[TypedBinding] = []
    if decl.imports:
        from quest.typed_ast import TypedImportItem
        typed_items = tuple(
            TypedImportItem(
                names=imp.names,
                interface_name=imp.interface_name,
                module_paths=imp.module_paths,
                interface_path=imp.interface_path,
                canonical_module_paths=tuple(
                    canonical_import_name(mod_path, env, current_dir=env.current_dir)
                    for mod_path in imp.effective_module_paths
                ),
                symbol_ids=tuple(s.symbol_id if s is not None else None for s in symbols),
            )
            for imp, symbols in zip(decl.imports, import_symbols)
        )
        typed_bindings.append(TypedImport(items=typed_items, offset=decl.offset))
    try:
        for b in decl.bindings:
            typed_b = binding_elaborator(b, env, 0)
            typed_bindings.append(typed_b)

        # 3. Conformance checking against interface
        type_subst: dict[int, QType] = {}
        for type_name, interface_type_symbol in target_interface_scope.types.items():
            mod_type_symbol = module_internal_scope.lookup_type_local(type_name)
            if mod_type_symbol is None:
                raise QuestTypeError(
                    f"Module '{decl.name}' does not implement required type '{type_name}' "
                    f"from interface '{decl.interface_name}'",
                    offset=decl.offset,
                )
            if interface_type_symbol.definition is not None:
                mod_def = (
                    mod_type_symbol.definition
                    if mod_type_symbol.definition is not None
                    else mod_type_symbol.type_val
                )
                if not is_type_equal(mod_def, interface_type_symbol.definition, env):
                    raise QuestTypeError(
                        f"Module '{decl.name}' defines manifest type '{type_name}' "
                        f"incompatibly with interface '{decl.interface_name}'",
                        offset=decl.offset,
                    )
            if interface_type_symbol.kind is not None and mod_type_symbol.kind is not None:
                # A defined type has the interface's kind if it is a member of it (for POWER(B), a subtype of B),
                # whatever kind it was declared with; an undefined one must have been declared with a subkind
                if mod_type_symbol.definition is not None:
                    try:
                        check_kind(mod_type_symbol.definition, interface_type_symbol.kind, env)
                        satisfies = True
                    except KindError:
                        satisfies = False
                else:
                    satisfies = is_subkind(mod_type_symbol.kind, interface_type_symbol.kind, env)
                if not satisfies:
                    raise QuestTypeError(
                        f"Type '{type_name}' in module '{decl.name}' does not satisfy "
                        f"kind bound from interface '{decl.interface_name}'",
                        offset=decl.offset,
                    )
            if interface_type_symbol.definition is None:
                concrete_def = (
                    mod_type_symbol.definition
                    if mod_type_symbol.definition is not None
                    else mod_type_symbol.type_val
                )
                type_subst[interface_type_symbol.symbol_id] = concrete_def

        for val_name, interface_val_symbol in target_interface_scope.values.items():
            mod_val_symbol = module_internal_scope.lookup_value_local(val_name)
            if mod_val_symbol is None:
                raise QuestTypeError(
                    f"Module '{decl.name}' does not implement required value '{val_name}' "
                    f"from interface '{decl.interface_name}'",
                    offset=decl.offset,
                )
            expected_type = interface_val_symbol.type_val.substitute(type_subst)
            if not is_subtype(mod_val_symbol.type_val, expected_type, env):
                raise QuestTypeError(
                    f"Value '{val_name}' in module '{decl.name}' has type '{mod_val_symbol.type_val}', "
                    f"which is not a subtype of interface signature '{expected_type}'",
                    offset=decl.offset,
                )
    finally:
        env.current_scope = saved_scope

    # 4. Create exported module scope (strictly opaque for abstract interface types)
    src = resolve_module_file(decl.name, env.current_dir, env.include_paths)
    canon = canonicalize_module_name(src, env.include_paths, decl.name, env.program_dir)
    module_export_scope = env.module_export_scopes.get(canon)
    if module_export_scope is None:
        concrete_defs = {
            name: sym.definition
            for name, sym in module_internal_scope.types.items()
            if sym.definition is not None
        }
        module_export_scope = create_module_export_scope(
            decl.name, canon, target_interface_scope, env, concrete_defs=concrete_defs
        )
        env.module_export_scopes[canon] = module_export_scope
    else:
        for t_name, mod_type_sym in module_internal_scope.types.items():
            if t_name in module_export_scope.types and module_export_scope.types[t_name].definition is None:
                if isinstance(mod_type_sym.definition, QExternalType):
                    module_export_scope.types[t_name].definition = mod_type_sym.definition
    _register_abstract_types(canon, module_export_scope, module_internal_scope)

    env.register_module(decl.name, module_export_scope)

    rec_fields = tuple(
        QRecordField(name=v.name, type_val=v.type_val, is_var=v.is_var)
        for v in module_export_scope.values.values()
    )
    module_symbol = ValueSymbol(name=decl.name, type_val=QRecordType(fields=rec_fields, provenance=decl.name))
    env.current_scope.declare_value(module_symbol)

    return TypedModule(
        name=decl.name,
        interface_name=decl.interface_name,
        bindings=tuple(typed_bindings),
        scope=module_export_scope,
        offset=decl.offset,
        symbol_id=module_symbol.symbol_id,
    )


def elaborate_import(phrase: ast.ImportPhrase, env: Environment) -> TypedImport:
    """Elaborates a top-level import statement, loading interfaces/modules from BuiltinModuleRegistry or files."""
    typed_items: list[TypedImportItem] = []
    for item in phrase.items:
        with at_import(item.offset, env.source_map):
            iface_path = item.effective_interface_path
            local_iface_name = item.interface_name
            iface_scope = import_interface(iface_path, local_iface_name, env)

            if not item.names:
                # import : Interface
                # Direct interface import: bind interface types and kinds into current scope
                for type_name, type_sym in iface_scope.types.items():
                    env.current_scope.declare_type(type_sym)
                for kind_name, kind_sym in iface_scope.kinds.items():
                    env.current_scope.declare_kind(kind_sym)
                typed_items.append(
                    TypedImportItem(
                        names=(),
                        interface_name=local_iface_name,
                        module_paths=(),
                        interface_path=item.interface_path,
                    )
                )
            else:
                # import mod1, mod2: Interface
                symbols: list[ValueSymbol] = []
                for local_mod_name, mod_path in zip(item.names, item.effective_module_paths):
                    from quest.modules.loader import load_module
                    if is_c_compilation_mode(env):
                        # In separate compilation mode, type the module via its interface without loading source
                        mod_scope = separately_compiled_module_scope(mod_path, iface_scope, env)
                        mod_type = build_record_type_from_scope(
                            mod_scope, provenance=local_mod_name
                        )
                        registered_scope = mod_scope
                    else:
                        if mod_path not in env.loaded_modules_ast:
                            load_module(mod_path, iface_path, env)
                        mod_scope = separately_compiled_module_scope(mod_path, iface_scope, env)
                        mod_type = build_record_type_from_scope(
                            mod_scope, provenance=local_mod_name
                        )
                        registered_scope = mod_scope
                    env.register_module(mod_path, registered_scope)
                    if local_mod_name != mod_path:
                        env.register_module(local_mod_name, registered_scope)
                    symbols.append(ValueSymbol(name=local_mod_name, type_val=mod_type))
                    env.current_scope.declare_value(symbols[-1])
                typed_items.append(
                    TypedImportItem(
                        names=item.names,
                        interface_name=local_iface_name,
                        module_paths=item.module_paths,
                        interface_path=item.interface_path,
                        canonical_module_paths=tuple(
                            canonical_import_name(mod_path, env, current_dir=env.current_dir)
                            for mod_path in item.effective_module_paths
                        ),
                        symbol_ids=tuple(s.symbol_id for s in symbols),
                    )
                )

    return TypedImport(items=tuple(typed_items), offset=phrase.offset)
