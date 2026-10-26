"""Quest Interface Compiler (Phase 4.16 Step 1).

Compiles interface files (.int.quest) to .qi files: portable, cycle-safe JSON/JSOG metadata encoded using shadow
Quest record types compatible with dynamic.extern / dynamic.intern, from which importers load interfaces, and keeps
them up to date (docs/build-process.md §5). An interface's C header (.int.h) is the C backend's: it is written from
the compiled interface by quest.codegen.c.headers, when C compilation needs it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import quest.syntax.ast as ast
from quest.config.abi import (
    ABI_VERSION,
    PRODUCER,
    built_from,
    has_current_abi,
    incompatible_artifact_message,
)
from quest.modules.stdlib import BuiltinModuleRegistry
from quest.config import CompilerOptions
from quest.modules.manifest import ImportedInterfaceRef
from quest.modules.graph import (
    Resolved,
    Resolver,
    Roots,
    UnitGraph,
    fresh_interface_qi,
    interface_qi_file,
    unit_artifact_dir,
)
from quest.modules.paths import (
    InterfaceDependency,
    dependency_change,
    recorded_dependencies,
)
from quest.diagnostics import Diagnostic, QuestCompilerError, QuestTypeError, at_import, diagnostic_of, in_unit
from quest.values.dynamic_json import jsog_decode, jsog_encode, parse_type_string
from quest.typechecker.elaborate_types import elaborate_kind, elaborate_rec_type_operators, elaborate_type
from quest.types.env import Environment, Scope, TypeSymbol, ValueSymbol
from quest.syntax.grammar import parse_quest_program
from quest.modules.elaboration import elaborate_interface, load_interface, separately_compiled_module_scope
from quest.modules.units import parse_unit, unit_declaration
from quest.values.model import (
    FALSE_VALUE,
    TRUE_VALUE,
    QArray,
    QBool,
    QAutoVal,
    QTuple,
    QInt,
    QRecord,
    QString,
)
from quest.syntax.tokenizer import Tokenizer
from quest.syntax.sources import SourceMap, display_file_name, read_source
from quest.types import (
    QAliasType,
    BOOL_TYPE,
    CHAR_TYPE,
    DYNAMIC_TYPE,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    TYPE_KIND,
    QAbstractType,
    QAllType,
    QAutoType,
    QArrayType,
    QFunType,
    QOptionType,
    QParam,
    QPathType,
    QQuantifier,
    QRecordField,
    QRecordType,
    QTupleComponent,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QType,
    QTypeApp,
    QTypeFun,
    QTypeVar,
    QVarType,
    QOutType,
    QRecType,
    QRecGroupType,
    QKind,
    QTypeKind,
    QPowerKind,
    QAllKind,
    QVariantField,
    QVariantType,
    pruned,
)

QI_SCHEMA_TYPE_STR = (
    "Record "
    "abi: Int "
    "deps: Array(Record dir: String path: String source: String end) "
    "imports: Array(String) "
    "name: String "
    "producer: String "
    "source: String "
    "types: Array(Record group: Int isManifest: Bool kind: String manifestType: String name: String end) "
    "values: Array(Record isPoly: Bool name: String typeSig: String end) "
    "end"
)

def format_type_for_qi(
    t: QType | None,
    visited: Optional[set[int]] = None,
) -> str:
    """Formats a semantic QType into Quest type syntax for .qi metadata; alias references keep their names."""
    if t is None:
        return ""
    t = pruned(t)
    if isinstance(t, QAliasType):
        return t.name
    if visited is None:
        visited = set()

    def format_param(p: QParam) -> str:
        if not p.name:
            return format_type_for_qi(p.type_val, visited)
        mode = "var " if p.is_var else "out " if p.is_out else ""
        return f"{mode}{p.name}: {format_type_for_qi(p.type_val, visited)}"

    if t is INT_TYPE:
        return "Int"
    if t is REAL_TYPE:
        return "Real"
    if t is BOOL_TYPE:
        return "Bool"
    if t is CHAR_TYPE:
        return "Char"
    if t is STRING_TYPE:
        return "String"
    if t is OK_TYPE:
        return "Ok"
    if t is DYNAMIC_TYPE:
        return "Dynamic"

    match t:
        case QTypeVar() | QAbstractType():
            return t.name
        case QPathType():
            return f"{t.module_name}.{t.type_name}"
        case QArrayType():
            return f"Array({format_type_for_qi(t.element_type, visited)})"
        case QRecordType():
            fields = " ".join(
                f"{'var ' if f.is_var else ''}{f.name}: {format_type_for_qi(f.type_val, visited)}"
                for f in t.fields
            )
            return f"Record {fields} end" if fields else "Record end"
        case QTupleType():
            parts: list[str] = []
            for f in t.fields:
                match f:
                    case QTupleField():
                        var_p = "var " if f.is_var else ""
                        if f.name:
                            parts.append(f"{var_p}{f.name}: {format_type_for_qi(f.type_val, visited)}")
                        else:
                            parts.append(f"{var_p}:{format_type_for_qi(f.type_val, visited)}")
                    case QTupleTypeFormal():
                        parts.append(f"{f.name}::{format_kind_for_qi(f.bound)}")
                    case QTupleTypeBinding():
                        b_str = f"::{format_kind_for_qi(f.bound)} " if f.bound else ""
                        parts.append(f"Let {f.name}{b_str}= {format_type_for_qi(f.type_val, visited)}")
            return f"Tuple {' '.join(parts)} end" if parts else "Tuple end"
        case QVariantType():
            variants = " ".join(
                f"{v.name}: {format_type_for_qi(v.type_val, visited)}" if v.type_val is not OK_TYPE else v.name
                for v in t.variants
            )
            return f"Variant {variants} end" if variants else "Variant end"
        case QOptionType():
            opts: list[str] = []
            for o in t.options:
                if o.payload_type is not None:
                    if isinstance(o.payload_type, QTupleType):
                        parts = [
                            f"{f.name}: {format_type_for_qi(f.type_val, visited)}"
                            if f.name else format_type_for_qi(f.type_val, visited)
                            for f in o.payload_type.fields
                        ]
                        opts.append(f"{o.name} with {' '.join(parts)} end")
                    else:
                        opts.append(f"{o.name} with {format_type_for_qi(o.payload_type, visited)} end")
                else:
                    opts.append(o.name)
            opts_str = " ".join(opts)
            return f"Option {opts_str} end" if opts_str else "Option end"
        case QAutoType():
            sig = " ".join(
                f"{'var ' if f.is_var else ''}{f.name}: {format_type_for_qi(f.type_val, visited)}"
                for f in t.signature
            )
            return f"Auto {t.type_param}::{format_kind_for_qi(t.kind_bound)} with {sig} end"
        case QFunType():
            params_str = " ".join(format_param(p) for p in t.params)
            return f"All({params_str}) {format_type_for_qi(t.result_type, visited)}"
        case QAllType():
            quants_str = " ".join(f"{q.name}::{q.bound}" for q in t.quantifiers)
            if isinstance(t.body, QFunType):
                params_str = " ".join(format_param(p) for p in t.body.params)
                return f"All({quants_str} {params_str}) {format_type_for_qi(t.body.result_type, visited)}"
            return f"All({quants_str}) {format_type_for_qi(t.body, visited)}"
        case QTypeFun():
            params_str = " ".join(f"{p.name}::{format_kind_for_qi(p.bound)}" for p in t.params)
            return f"Fun({params_str}) {format_type_for_qi(t.body, visited)}"
        case QTypeApp():
            args_str = " ".join(format_type_for_qi(a, visited) for a in t.arguments)
            ctor_str = format_type_for_qi(t.constructor, visited)
            if (
                isinstance(t.constructor, (QTypeFun, QAllType, QRecType, QRecGroupType))
                and not isinstance(t.constructor, QAliasType)
            ):
                ctor_str = f"{{{ctor_str}}}"
            return f"{ctor_str}({args_str})"
        case QVarType():
            return f"Var({format_type_for_qi(t.value_type, visited)})"
        case QOutType():
            return f"Out({format_type_for_qi(t.value_type, visited)})"
        case QRecType() | QRecGroupType() if id(t) in visited:
            return t.var_name if isinstance(t, QRecType) else "RecType"
        case QRecType():
            visited.add(id(t))
            return (
                f"Rec({t.var_name} :: {format_kind_for_qi(t.bound)}) "
                f"{format_type_for_qi(t.body, visited)}"
            )
        case QRecGroupType():
            # Format the active recursive type definition
            visited.add(id(t))
            _, _, bound, body = t.bindings[t.active_index]
            return (
                f"Rec({t.current_name} :: {format_kind_for_qi(bound)}) "
                f"{format_type_for_qi(body, visited)}"
            )
        case _:
            return str(t)


def format_kind_for_qi(k: ast.Kind | QKind | None) -> str:
    """Formats an AST or semantic Kind into a valid Quest syntax string for .qi metadata."""
    if k is None or isinstance(k, (ast.KindType, QTypeKind)):
        return "TYPE"
    if isinstance(k, QPowerKind):
        return f"POWER({format_type_for_qi(k.bound)})"
    if isinstance(k, QAllKind):
        return f"ALL({k.param_name}::{format_kind_for_qi(k.param_kind)}) {format_kind_for_qi(k.result_kind)}"
    match k:
        case ast.KindAll(param_name=pname, param_kind=pkind, body_kind=bkind):
            return f"ALL({pname}::{format_kind_for_qi(pkind)}) {format_kind_for_qi(bkind)}"
        case ast.KindPower(bound=bound):
            return f"POWER({bound})"
        case ast.KindId(name=name):
            return name
        case ast.KindManifest(interface_name=iname, kind_name=kname):
            return f"{iname}_{kname}"
        case _:
            return "TYPE"


def _parse_and_elaborate_kind_in_env(kind_str: str, env: Environment) -> QKind:
    """Parses and elaborates a Quest kind string within an existing environment/scope."""
    source_map = SourceMap(kind_str, "<kind>")
    tokens = Tokenizer(kind_str, "<kind>").tokenize_all()
    ast_k = parse_quest_program(tokens, source_map, target="Kind")
    return elaborate_kind(ast_k, env)


def _parse_type(type_str: str) -> ast.Type:
    """Parses a Quest type string."""
    source_map = SourceMap(type_str, "<type>")
    tokens = Tokenizer(type_str, "<type>").tokenize_all()
    return parse_quest_program(tokens, source_map, target="Type")


def _parse_and_elaborate_type_in_env(type_str: str, env: Environment) -> QType:
    """Parses and elaborates a Quest type string within an existing environment/scope."""
    return elaborate_type(_parse_type(type_str), env)


def _format_rec_operator_member_for_qi(definition: QTypeFun, kind: QKind) -> str:
    """Formats a member of a group of recursive type operators (Fun(A::K) applied to a group) as the operator it
    declares, Fun(A::K) Body, with the group's variables written as their operators applied to the parameters, as in
    its declaration; the loader elaborates the group's members together, like Let Rec T(A::K) = Body and ...."""
    group = definition.body
    assert isinstance(group, QRecGroupType)
    params = tuple(QTypeVar(name=p.name, symbol_id=p.symbol_id, bound=p.bound) for p in definition.params)
    subst: dict[int, QType] = {
        rec_id: QTypeApp(constructor=QTypeVar(name=name, symbol_id=rec_id, bound=bound), arguments=params)
        for name, rec_id, bound, _ in group.bindings
    }
    body = group.bindings[group.active_index][3].substitute(subst)
    params_str = " ".join(f"{p.name}::{format_kind_for_qi(p.bound)}" for p in definition.params)
    result_kind = kind
    for _ in definition.params:
        assert isinstance(result_kind, QAllKind)
        result_kind = result_kind.result_kind
    result_str = "" if isinstance(result_kind, QTypeKind) else f" :: {format_kind_for_qi(result_kind)}"
    return f"Fun({params_str}){result_str} {format_type_for_qi(body)}"


def _type_signatures(
    decl: ast.InterfaceDecl,
) -> list[tuple[ast.TypeFormal | ast.TypeBinding | ast.FieldSig | ast.DefKindBinding, int]]:
    """The signatures of an interface with each simultaneous type declaration replaced by its members, paired with
    the number of the recursive group each belongs to (counting from 1), or 0 if it is not in one. The members of a
    group without Rec are independent declarations once elaborated."""
    result: list[tuple[Any, int]] = []
    groups = 0
    for sig in decl.signatures:
        if isinstance(sig, ast.TypeBindingGroup):
            if sig.bindings[0].is_rec:
                groups += 1
                result.extend((member, groups) for member in sig.bindings)
            else:
                result.extend((member, 0) for member in sig.bindings)
        else:
            result.append((sig, 0))
    return result


def compile_interface_to_qi(
    decl: ast.InterfaceDecl,
    iface_scope: Scope,
    env: Optional[Environment] = None,
    source: Optional[Path] = None,
    deps: Optional[list[InterfaceDependency]] = None,
) -> str:
    """Serializes interface declarations to portable JSON/JSOG .qi format using shadow Quest records.

    source is the .int.quest the interface was compiled from; it is recorded (resolved) so that a .qi is used only
    for the source it was built from (docs/build-process.md §5). deps are the interfaces it depends on
    (Resolver.interface_dependencies), recorded so that the .qi is stale when one of them changes.
    """
    imports_elems: list[QString] = []
    for imp in decl.imports:
        if not imp.names:
            imports_elems.append(QString(f":{imp.effective_interface_path}"))
        elif imp.module_paths:
            imports_elems.append(
                QString(f"{','.join(imp.names)}={','.join(imp.module_paths)}:{imp.effective_interface_path}")
            )
        else:
            imports_elems.append(
                QString(f"{','.join(imp.names)}:{imp.effective_interface_path}")
            )
    imports_arr = QArray(imports_elems)

    type_records: list[QRecord] = []
    value_records: list[QRecord] = []

    # Collect types. A member of a recursive group records its body, with the other members as their names, and
    # the group's number; the loader rebuilds the group from its members' records.
    for sig, group in _type_signatures(decl):
        match sig:
            case ast.TypeFormal():
                # The elaborated kind, whose bound (for POWER) is printed as a type, not as syntax
                formal_sym = iface_scope.lookup_type_local(sig.name)
                kind_str = format_kind_for_qi(formal_sym.kind if formal_sym is not None else sig.bound)
                type_records.append(
                    QRecord(
                        {
                            "group": QInt(0),
                            "name": QString(sig.name),
                            "kind": QString(kind_str),
                            "isManifest": FALSE_VALUE,
                            "manifestType": QString(""),
                        }
                    )
                )
            case ast.TypeBinding():
                type_sym = iface_scope.lookup_type_local(sig.name)
                concrete_t = type_sym.definition if type_sym and type_sym.definition else None
                if group and isinstance(concrete_t, QRecGroupType):
                    concrete_t = concrete_t.bindings[concrete_t.active_index][3]
                if group and isinstance(concrete_t, QTypeFun) and isinstance(concrete_t.body, QRecGroupType):
                    m_type_str = _format_rec_operator_member_for_qi(concrete_t, type_sym.kind)
                else:
                    m_type_str = (
                        format_type_for_qi(concrete_t)
                        if concrete_t
                        else str(sig.type_val)
                    )
                kind_str = format_kind_for_qi(type_sym.kind) if type_sym and type_sym.kind else "TYPE"
                type_records.append(
                    QRecord(
                        {
                            "group": QInt(group),
                            "name": QString(sig.name),
                            "kind": QString(kind_str),
                            "isManifest": TRUE_VALUE,
                            "manifestType": QString(m_type_str),
                        }
                    )
                )
            case ast.FieldSig() if sig.name:
                val_sym = iface_scope.lookup_value_local(sig.name)
                val_t = val_sym.type_val if val_sym else None
                sig_str = format_type_for_qi(val_t) if val_t else ""
                is_poly = isinstance(val_t, QAllType)
                value_records.append(
                    QRecord(
                        {
                            "name": QString(sig.name),
                            "typeSig": QString(sig_str),
                            "isPoly": TRUE_VALUE if is_poly else FALSE_VALUE,
                        }
                    )
                )

    desc_record = QRecord(
        {
            "abi": QInt(ABI_VERSION),
            "deps": QArray(
                [
                    QRecord({"dir": QString(d.dir), "path": QString(d.path), "source": QString(d.source)})
                    for d in deps or []
                ]
            ),
            "producer": QString(PRODUCER),
            "source": QString(str(source.resolve()) if source is not None else ""),
            "name": QString(decl.name),
            "imports": imports_arr,
            "types": QArray(type_records),
            "values": QArray(value_records),
        }
    )

    schema_type = parse_type_string(QI_SCHEMA_TYPE_STR)
    dyn = QAutoVal(QTuple((desc_record,), ("a",)), schema_type)
    return jsog_encode(dyn)


def indirect_interface_refs(
    direct: list[ImportedInterfaceRef],
    include_paths: list[Path],
    program_dir: Optional[Path] = None,
    resolver: Optional[Resolver] = None,
) -> list[ImportedInterfaceRef]:
    """The manifest entries for the interfaces a unit depends on through the interfaces it imports itself.

    direct are the unit's own imported interfaces. Each entry records the directory its path was resolved from, so
    that the staleness checks resolve it again the same way (graph.import_resolution_change). Interfaces the unit
    also imports directly are left out.
    """
    resolver = resolver or Resolver()
    roots = Roots.of(include_paths, program_dir)
    refs: list[ImportedInterfaceRef] = []
    seen = {ref.source for ref in direct if ref.source}
    for ref in direct:
        if not ref.source:
            continue
        for dep in resolver.interface_dependencies(Path(ref.source), include_paths):
            if dep.source and dep.source in seen:
                continue
            if dep.source:
                seen.add(dep.source)
            src = Path(dep.source) if dep.source else None
            refs.append(
                ImportedInterfaceRef(
                    name=resolver.interface(dep.path, Path(dep.dir), roots).interface_name,
                    source=dep.source,
                    mtime=src.stat().st_mtime if src is not None and src.is_file() else 0.0,
                    path=dep.path,
                    dir=dep.dir,
                )
            )
    return refs


@dataclass(frozen=True)
class CompiledInterface:
    """An interface compiled from its source: its declaration and elaborated scope, from which the C backend writes
    its header, and its .qi (written unless the compilation only elaborated the interface)."""
    decl: ast.InterfaceDecl
    scope: Scope
    source: Path
    source_map: SourceMap
    qi_file: Path
    # The search paths the interface was compiled with, from which its imports were resolved
    include_paths: tuple[Path, ...]


# What a caller of compile_interface_file or ensure_resolved_interface_artifacts does with each interface they compile,
# including the interfaces compiled because it imports them (the C backend writes their headers)
OnCompiled = Callable[[CompiledInterface], None]


@dataclass(frozen=True)
class InterfaceArtifacts:
    """Where an interface's .qi is, as ensure_resolved_interface_artifacts found or rebuilt it."""
    # The .qi, which may not exist if the interface has neither a source nor prebuilt artifacts (a builtin)
    qi_file: Path
    canonical_name: str
    # The .int.quest it is built from, None without one (a binary distribution, Rule 3, or a builtin)
    source: Optional[Path]
    # Where the interface's artifacts are rebuilt in the build directory, and the search paths they are built with
    target_dir: Path
    search_paths: tuple[Path, ...]


# The interface files being compiled, outermost first, with their canonical names. Compiling an interface first
# compiles the interfaces it imports, each in an environment of its own, so a cycle of imports is detected here.
_compiling_interfaces: list[tuple[Path, str]] = []


def compile_interface_file(
    file_path: Path,
    output_dir: Optional[Path] = None,
    include_paths: Optional[list[Path]] = None,
    build_dir: Optional[Path] = None,
    program_dir: Optional[Path] = None,
    write_qi: bool = True,
    on_compiled: Optional[OnCompiled] = None,
    resolver: Optional[Resolver] = None,
) -> CompiledInterface:
    """Compiles a .int.quest file to a .qi file, or with write_qi False, only elaborates it.

    With a build directory, the interfaces it imports are brought up to date there first. on_compiled is called
    for each interface compiled, the interfaces it imports first and this one last. The interface is elaborated in
    an environment of its own, whose imports resolver resolves (a new one if None).
    """

    key = file_path.resolve()
    resolver = resolver or Resolver()
    canon_name = resolver.file(key, Roots.of(include_paths, program_dir)).canonical_name
    compiling = [path for path, _ in _compiling_interfaces]
    if key in compiling:
        chain = [name for _, name in _compiling_interfaces[compiling.index(key):]] + [canon_name]
        raise QuestTypeError(f"Cyclic dependency detected in interface imports: {' -> '.join(chain)}")
    _compiling_interfaces.append((key, canon_name))
    try:
        compiled = _compile_interface_file(
            file_path, output_dir, include_paths, build_dir, program_dir, write_qi, on_compiled, resolver
        )
    finally:
        _compiling_interfaces.pop()
    if on_compiled is not None:
        on_compiled(compiled)
    return compiled


def _compile_interface_file(
    file_path: Path,
    output_dir: Optional[Path],
    include_paths: Optional[list[Path]],
    build_dir: Optional[Path],
    program_dir: Optional[Path],
    write_qi: bool,
    on_compiled: Optional[OnCompiled],
    resolver: Resolver,
) -> CompiledInterface:
    try:
        source_text = read_source(file_path)
    except OSError as err:
        raise QuestTypeError(f"Error reading interface file '{file_path}': {err}")

    source_map = SourceMap(source_text, display_file_name(file_path))
    # Errors are located in this file, and the imports it makes are located in it (docs/diagnostics.md §4.4)
    with in_unit(source_map):
        prog = parse_unit(source_text, file_path, source_map)

        decl = unit_declaration(prog, file_path)

        env = Environment(builtin_registry=BuiltinModuleRegistry)
        env.units = UnitGraph(resolver=resolver)
        env.include_paths = list(include_paths) if include_paths else []
        if build_dir is not None:
            b_dir = Path(build_dir).resolve()
            if b_dir not in env.include_paths:
                env.include_paths.insert(0, b_dir)
            # Imported interfaces are loaded from their (fresh or rebuilt) artifacts in the same build directory
            # rather than re-elaborated from source in every nested compilation.
            env.options = CompilerOptions(build_dir=b_dir, include_paths=list(env.include_paths))
        env.current_dir = file_path.parent
        env.program_dir = program_dir
        env.source_map = source_map

        if build_dir is not None:
            # Every interface it imports is brought up to date in the build directory, including builtin
            # interfaces that are never loaded from source, so that their artifacts exist beside its own.
            roots = Roots.of(env.include_paths, program_dir)
            for imp in decl.imports:
                with at_import(imp.offset, source_map):
                    ensure_resolved_interface_artifacts(
                        resolver.interface(imp.effective_interface_path, file_path.parent, roots),
                        Path(build_dir).resolve(), on_compiled=on_compiled, resolver=resolver,
                    )
        typed_iface = elaborate_interface(decl, env)

    if build_dir is not None and output_dir is None:
        canon_name = resolver.file(file_path.resolve(), Roots.of(env.include_paths, program_dir)).canonical_name
        target_dir = unit_artifact_dir(Path(build_dir).resolve(), canon_name)
    else:
        target_dir = output_dir if output_dir is not None else file_path.parent
    base_name = file_path.name
    if base_name.endswith(".int.quest"):
        stem = base_name[:-10]
    else:
        stem = file_path.stem

    qi_path = target_dir / f"{stem.lower()}.qi"
    if write_qi:
        deps = resolver.interface_dependencies(file_path, env.include_paths)
        qi_content = compile_interface_to_qi(decl, typed_iface.scope, env=env, source=file_path, deps=deps)
        qi_path.parent.mkdir(parents=True, exist_ok=True)
        qi_path.write_text(qi_content, encoding="utf-8")

    return CompiledInterface(
        decl=decl,
        scope=typed_iface.scope,
        source=file_path,
        source_map=source_map,
        qi_file=qi_path,
        include_paths=tuple(env.include_paths),
    )


def ensure_interface_artifacts(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
    build_dir: Path,
    program_dir: Optional[Path] = None,
    on_compiled: Optional[OnCompiled] = None,
    resolver: Optional[Resolver] = None,
) -> InterfaceArtifacts:
    """Rebuilds interface `name`'s .qi under build_dir if stale (docs/build-process.md §5), resolving the import of
    `name` from current_dir with include_paths (ensure_resolved_interface_artifacts)."""
    resolver = resolver or Resolver()
    resolved = resolver.interface(name, current_dir, Roots.of(include_paths, program_dir))
    return ensure_resolved_interface_artifacts(resolved, build_dir, on_compiled=on_compiled, resolver=resolver)


def ensure_resolved_interface_artifacts(
    resolved: Resolved,
    build_dir: Path,
    on_compiled: Optional[OnCompiled] = None,
    resolver: Optional[Resolver] = None,
) -> InterfaceArtifacts:
    """Rebuilds the .qi of a resolved interface under build_dir if stale (docs/build-process.md §5).

    The interface is rebuilt with the search paths it was resolved with, and build_dir first. on_compiled is called
    for each interface compiled (compile_interface_file); resolver resolves the imports of those compiled.
    """
    resolver = resolver or Resolver()
    include_paths = list(resolved.roots.search_paths)
    program_dir = resolved.roots.program_dir
    src = resolved.source

    canon_name = resolved.artifact_name
    target_dir = unit_artifact_dir(build_dir, canon_name)
    qi_file = interface_qi_file(build_dir, canon_name)
    search_paths = list(include_paths)
    if build_dir not in search_paths:
        search_paths.insert(0, build_dir)

    def artifacts(qi: Path) -> InterfaceArtifacts:
        has_source = src is not None and src.is_file()
        return InterfaceArtifacts(qi, canon_name, src if has_source else None, target_dir, tuple(search_paths))

    def current(qi: Path) -> bool:
        """Rules 1 and 2 plus the ABI version: the .qi exists, is fresh, matches this compiler, was built from this
        source (not a same-named interface elsewhere), and none of the interfaces it depends on has changed or
        would resolve elsewhere."""
        if not qi.is_file() or not has_current_abi(qi):
            return False
        if src is None or not src.is_file():
            return True
        qi_mtime = qi.stat().st_mtime
        deps = recorded_dependencies(qi)
        return (
            src.stat().st_mtime <= qi_mtime
            and built_from(qi, src)
            and deps is not None
            and dependency_change(deps, include_paths, qi_mtime, resolver) is None
        )

    # A fresh .qi found elsewhere on the search path (e.g. next to the source, from a standalone compilation) is
    # used like one in the build directory.
    if not current(qi_file):
        file_path = fresh_interface_qi(resolved)
        if file_path is not None and file_path.suffix == ".qi":
            if current(file_path) or (src is None and not qi_file.is_file()):
                qi_file = file_path

    # Rule 3: without a source, existing artifacts cannot be rebuilt (binary distribution).
    if src is None or not src.is_file():
        if qi_file.is_file() and not has_current_abi(qi_file):
            raise QuestTypeError(incompatible_artifact_message(qi_file))
        return artifacts(qi_file)
    if not current(qi_file):
        target_dir.mkdir(parents=True, exist_ok=True)
        qi_file = compile_interface_file(
            src, output_dir=target_dir, include_paths=search_paths, build_dir=build_dir, program_dir=program_dir,
            on_compiled=on_compiled, resolver=resolver,
        ).qi_file
    return artifacts(qi_file)


def load_interface_from_qi_file(file_path: Path, env: Environment) -> Scope:
    """Loads and deserializes an interface Scope directly from a precompiled .qi file."""
    if not has_current_abi(file_path):
        raise QuestTypeError(incompatible_artifact_message(file_path))
    try:
        raw_json = file_path.read_text(encoding="utf-8")
    except OSError as err:
        raise QuestTypeError(f"Error reading .qi file '{file_path}': {err}")

    dyn = jsog_decode(raw_json)
    if not isinstance(dyn.value.elements[0], QRecord):
        raise QuestTypeError(f"Malformed .qi metadata in '{file_path}'")

    rec = dyn.value.elements[0]
    name = str(rec.fields["name"].value) if "name" in rec.fields else file_path.stem
    imp_scope_frame = Scope(name=f"imports_{name}", parent=env.current_scope)

    # 1. Resolve imported interfaces
    if "imports" in rec.fields and isinstance(rec.fields["imports"], QArray):

        for imp_elem in rec.fields["imports"].elements:
            imp_str = str(imp_elem.value)
            if imp_str.startswith(":"):
                imp_name = imp_str[1:]
                imp_scope = env.lookup_interface(imp_name)
                if imp_scope is None:
                    imp_scope = load_interface(imp_name, env)
                for t_name, t_sym in imp_scope.types.items():
                    imp_scope_frame.declare_type(t_sym)
                for k_name, k_sym in imp_scope.kinds.items():
                    imp_scope_frame.declare_kind(k_sym)
            else:
                if "=" in imp_str:
                    names_part, rest = imp_str.split("=", 1)
                    mpaths_part, iface_part = rest.split(":", 1)
                    names = tuple(names_part.split(","))
                    mpaths = tuple(mpaths_part.split(","))
                    imp_name = iface_part
                elif ":" in imp_str:
                    names_part, iface_part = imp_str.split(":", 1)
                    names = tuple(names_part.split(","))
                    mpaths = names
                    imp_name = iface_part
                else:
                    names = ()
                    mpaths = ()
                    imp_name = imp_str

                imp_scope = env.lookup_interface(imp_name)
                if imp_scope is None:
                    imp_scope = load_interface(imp_name, env)

                if not names:
                    for t_name, t_sym in imp_scope.types.items():
                        imp_scope_frame.declare_type(t_sym)
                    for k_name, k_sym in imp_scope.kinds.items():
                        imp_scope_frame.declare_kind(k_sym)
                else:
                    for iname, mod_path in zip(names, mpaths):
                        registered_scope = separately_compiled_module_scope(mod_path, imp_scope, env)
                        env.register_module(iname, registered_scope)
                        env.register_module(mod_path, registered_scope)
                        env.register_module(imp_name, registered_scope)

    iface_scope = Scope(name=f"interface_{name}", parent=imp_scope_frame)
    for t_name, t_sym in imp_scope_frame.types.items():
        iface_scope.declare_type(t_sym)
    for k_name, k_sym in imp_scope_frame.kinds.items():
        iface_scope.declare_kind(k_sym)

    # 2. Declare types
    saved_scope = env.current_scope
    env.current_scope = iface_scope
    try:
        if "types" in rec.fields and isinstance(rec.fields["types"], QArray):
            type_records_list: list[tuple[str, bool, str, str, TypeSymbol, int]] = []
            # Pass 1: Declare all type symbols with fresh IDs and bound kinds so they are visible in iface_scope
            for t_item in rec.fields["types"].elements:
                if isinstance(t_item, QRecord):
                    t_name = str(t_item.fields["name"].value)
                    is_manifest = (
                        t_item.fields["isManifest"].value
                        if "isManifest" in t_item.fields
                        else False
                    )
                    kind_str = str(t_item.fields["kind"].value)
                    manifest_str = str(t_item.fields["manifestType"].value)
                    group = t_item.fields["group"].value if "group" in t_item.fields else 0

                    bound_kind: QKind = TYPE_KIND
                    if kind_str and kind_str != "TYPE":
                        bound_kind = _parse_and_elaborate_kind_in_env(kind_str, env)

                    sym_id = env.fresh_symbol_id()
                    type_sym = TypeSymbol(
                        name=t_name,
                        symbol_id=sym_id,
                        kind=bound_kind,
                        definition=None,
                    )
                    iface_scope.declare_type(type_sym)
                    type_records_list.append((t_name, is_manifest, kind_str, manifest_str, type_sym, group))

            # Pass 2: Elaborate concrete definitions with all interface types in scope. The members of a recursive
            # group are consecutive; their bodies are elaborated before any member is defined, so that each refers
            # to the others by their symbols, which become the group's variables.
            # The members of a group of recursive type operators are recorded as Fun(A::K) Body, with each other
            # applied to the parameters, and are elaborated together as declared.
            group_members: list[tuple[str, TypeSymbol, QType]] = []
            operator_members: list[tuple[TypeSymbol, ast.TypeBinding]] = []
            for idx, (t_name, is_manifest, kind_str, manifest_str, type_sym, group) in enumerate(
                type_records_list
            ):
                if group:
                    if isinstance(type_sym.kind, QAllKind):
                        member = ast.TypeBinding(name=t_name, type_val=_parse_type(manifest_str), is_rec=True)
                        operator_members.append((type_sym, member))
                    else:
                        body = _parse_and_elaborate_type_in_env(manifest_str, env)
                        group_members.append((t_name, type_sym, body))
                    if idx + 1 == len(type_records_list) or type_records_list[idx + 1][5] != group:
                        if operator_members:
                            symbols = elaborate_rec_type_operators([member for _, member in operator_members], env)
                            for (sym, _), elaborated in zip(operator_members, symbols):
                                sym.definition = elaborated.definition
                        else:
                            bindings = tuple(
                                (name, sym.symbol_id, sym.kind, body) for name, sym, body in group_members
                            )
                            for active, (_, sym, _) in enumerate(group_members):
                                sym.definition = QRecGroupType(bindings=bindings, active_index=active)
                        group_members = []
                        operator_members = []
                elif is_manifest and manifest_str:
                    concrete_def = _parse_and_elaborate_type_in_env(manifest_str, env)
                    type_sym.definition = concrete_def

        # 3. Declare values
        if "values" in rec.fields and isinstance(rec.fields["values"], QArray):
            for v_item in rec.fields["values"].elements:
                if isinstance(v_item, QRecord):
                    v_name = str(v_item.fields["name"].value)
                    type_sig_str = str(v_item.fields["typeSig"].value)
                    val_type = _parse_and_elaborate_type_in_env(type_sig_str, env)
                    val_sym = ValueSymbol(name=v_name, type_val=val_type)
                    iface_scope.declare_value(val_sym)
    finally:
        env.current_scope = saved_scope

    env.register_interface(name, iface_scope)
    return iface_scope
