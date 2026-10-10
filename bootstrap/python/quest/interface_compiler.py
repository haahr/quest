"""Quest Interface Compiler (Phase 4.16 Step 1).

Compiles interface files (.int.quest) to:
1. .qi: Portable, cycle-safe JSON/JSOG metadata encoded using shadow Quest record types
   compatible with dynamic.extern / dynamic.intern.
2. .int.h: C header file providing include guards, dependency includes, abstract type erasure
   to QVal, manifest type definitions, and function signature typedefs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import quest.ast as ast
from quest.build.abi import (
    ABI_VERSION,
    PRODUCER,
    built_from,
    has_current_abi,
    header_stamp,
    incompatible_artifact_message,
)
from quest.codegen.c_types import qtype_to_c_type
from quest.diagnostics import Diagnostic, QuestCompilerError, QuestTypeError, at_import, diagnostic_of, in_unit
from quest.dynamic_json import jsog_decode, jsog_encode, parse_type_string
from quest.elaborate_types import elaborate_kind, elaborate_type
from quest.env import Environment, Scope, TypeSymbol, ValueSymbol
from quest.grammar import parse_quest_program
from quest.modules import elaborate_interface
from quest.runtime import (
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
from quest.tokenizer import Tokenizer
from quest.tokens import SourceMap, display_file_name
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
)

QI_SCHEMA_TYPE_STR = (
    "Record "
    "abi: Int "
    "imports: Array(String) "
    "name: String "
    "producer: String "
    "source: String "
    "types: Array(Record group: Int isManifest: Bool kind: String manifestType: String name: String end) "
    "values: Array(Record isPoly: Bool name: String typeSig: String end) "
    "end"
)

C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while", "_Alignas", "_Alignof",
    "_Atomic", "_Bool", "_Complex", "_Generic", "_Imaginary", "_Noreturn",
    "_Static_assert", "_Thread_local",
}



def format_type_for_qi(
    t: QType | None,
    visited: Optional[set[int]] = None,
) -> str:
    """Formats a semantic QType into Quest type syntax for .qi metadata; alias references keep their names."""
    if t is None:
        return ""
    t = t.prune() if hasattr(t, "prune") else t
    if isinstance(t, QAliasType):
        return t.name
    if visited is None:
        visited = set()

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

    if isinstance(t, QTypeVar):
        return t.name
    if isinstance(t, QAbstractType):
        return t.name
    if isinstance(t, QPathType):
        return f"{t.module_name}.{t.type_name}"

    if isinstance(t, QArrayType):
        return f"Array({format_type_for_qi(t.element_type, visited)})"

    if isinstance(t, QRecordType):
        fields = " ".join(
            f"{'var ' if f.is_var else ''}{f.name}: {format_type_for_qi(f.type_val, visited)}"
            for f in t.fields
        )
        return f"Record {fields} end" if fields else "Record end"

    if isinstance(t, QTupleType):
        parts: list[str] = []
        for f in t.fields:
            if isinstance(f, QTupleField):
                var_p = "var " if f.is_var else ""
                if f.name:
                    parts.append(f"{var_p}{f.name}: {format_type_for_qi(f.type_val, visited)}")
                else:
                    parts.append(f"{var_p}:{format_type_for_qi(f.type_val, visited)}")
            elif isinstance(f, QTupleTypeFormal):
                parts.append(f"{f.name}::{format_kind_for_qi(f.bound)}")
            elif isinstance(f, QTupleTypeBinding):
                b_str = f"::{format_kind_for_qi(f.bound)} " if f.bound else ""
                parts.append(f"Let {f.name}{b_str}= {format_type_for_qi(f.type_val, visited)}")
        return f"Tuple {' '.join(parts)} end" if parts else "Tuple end"

    if isinstance(t, QVariantType):
        variants = " ".join(
            f"{v.name}: {format_type_for_qi(v.type_val, visited)}" if v.type_val is not OK_TYPE else v.name
            for v in t.variants
        )
        return f"Variant {variants} end" if variants else "Variant end"

    if isinstance(t, QOptionType):
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

    if isinstance(t, QAutoType):
        sig = " ".join(
            f"{'var ' if f.is_var else ''}{f.name}: {format_type_for_qi(f.type_val, visited)}"
            for f in t.signature
        )
        return f"Auto {t.type_param}::{format_kind_for_qi(t.kind_bound)} with {sig} end"

    def format_param(p: QParam) -> str:
        if not p.name:
            return format_type_for_qi(p.type_val, visited)
        mode = "var " if p.is_var else "out " if p.is_out else ""
        return f"{mode}{p.name}: {format_type_for_qi(p.type_val, visited)}"

    if isinstance(t, QFunType):
        params_str = " ".join(format_param(p) for p in t.params)
        return f"All({params_str}) {format_type_for_qi(t.result_type, visited)}"

    if isinstance(t, QAllType):
        quants_str = " ".join(f"{q.name}::{q.bound}" for q in t.quantifiers)
        if isinstance(t.body, QFunType):
            params_str = " ".join(format_param(p) for p in t.body.params)
            return f"All({quants_str} {params_str}) {format_type_for_qi(t.body.result_type, visited)}"
        return f"All({quants_str}) {format_type_for_qi(t.body, visited)}"

    if isinstance(t, QTypeApp):
        args_str = " ".join(format_type_for_qi(a, visited) for a in t.arguments)
        ctor_str = format_type_for_qi(t.constructor, visited)
        if (
            isinstance(t.constructor, (QTypeFun, QAllType, QRecType, QRecGroupType))
            and not isinstance(t.constructor, QAliasType)
        ):
            ctor_str = f"{{{ctor_str}}}"
        return f"{ctor_str}({args_str})"

    if isinstance(t, QArrayType):
        return f"Array({format_type_for_qi(t.element_type, visited)})"

    if isinstance(t, QVarType):
        return f"Var({format_type_for_qi(t.value_type, visited)})"

    if isinstance(t, QOutType):
        return f"Out({format_type_for_qi(t.value_type, visited)})"

    if isinstance(t, (QRecType, QRecGroupType)):
        t_id = id(t)
        if t_id in visited:
            return getattr(t, "var_name", getattr(t, "current_name", "RecType"))
        visited.add(t_id)

    if isinstance(t, QRecType):
        return (
            f"Rec({t.var_name} :: {format_kind_for_qi(t.bound)}) "
            f"{format_type_for_qi(t.body, visited)}"
        )

    if isinstance(t, QRecGroupType):
        # Format the active recursive type definition
        _, _, bound, body = t.bindings[t.active_index]
        return (
            f"Rec({t.current_name} :: {format_kind_for_qi(bound)}) "
            f"{format_type_for_qi(body, visited)}"
        )

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


def _parse_and_elaborate_type_in_env(type_str: str, env: Environment) -> QType:
    """Parses and elaborates a Quest type string within an existing environment/scope."""
    source_map = SourceMap(type_str, "<type>")
    tokens = Tokenizer(type_str, "<type>").tokenize_all()
    ast_t = parse_quest_program(tokens, source_map, target="Type")
    return elaborate_type(ast_t, env)


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
) -> str:
    """Serializes interface declarations to portable JSON/JSOG .qi format using shadow Quest records.

    source is the .int.quest the interface was compiled from; it is recorded (resolved) so that a .qi is used only
    for the source it was built from (docs/build-process.md §5).
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
        if isinstance(sig, ast.TypeFormal):
            kind_str = format_kind_for_qi(sig.bound)
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
        elif isinstance(sig, ast.TypeBinding):
            type_sym = iface_scope.lookup_type_local(sig.name)
            concrete_t = type_sym.definition if type_sym and type_sym.definition else None
            if group and isinstance(concrete_t, QRecGroupType):
                concrete_t = concrete_t.bindings[concrete_t.active_index][3]
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
        elif isinstance(sig, ast.FieldSig) and sig.name:
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


def compile_interface_to_header(decl: ast.InterfaceDecl, iface_scope: Scope, canonical_name: str) -> str:
    """Generates the C header (.int.h) for an interface declaration.

    The include guard and typedef names are derived from canonical_name, the interface's include-relative path
    (e.g. 'util/Math'), so same-named interfaces in different directories can be included in one translation unit.
    """
    c_name = canonical_name.replace("/", "__")
    guard_name = f"QUEST_INTF_{c_name.upper()}_H"
    lines: list[str] = [
        header_stamp(),
        f"/* Generated by Quest compiler for interface {decl.name} */",
        f"#ifndef {guard_name}",
        f"#define {guard_name}",
        "",
        '#include "quest_runtime.h"',
        "",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        "",
    ]

    # Imported interfaces
    if decl.imports:
        lines.append("/* --- Imported Interfaces --- */")
        for imp in decl.imports:
            path = imp.effective_interface_path.lower()
            if path not in ("word",):
                lines.append(f'#include "{path}.int.h"')
        lines.append("")

    # Aggregate struct definitions used in the interface
    from quest.codegen.c_analysis import collect_aggregate_types
    from quest.codegen.c_declarations import CDeclarationEmitter
    from quest.codegen.c_types import RecordNamingContext

    record_ctx = RecordNamingContext()
    agg_types: list[tuple[str, QType]] = []
    agg_names: set[str] = set()
    for name, tsym in iface_scope.types.items():
        if tsym and tsym.definition:
            s_agg, _, _ = collect_aggregate_types(tsym.definition, record_ctx)
            for item in s_agg:
                if item[0] not in agg_names:
                    agg_names.add(item[0])
                    agg_types.append(item)

    for name, vsym in iface_scope.values.items():
        if vsym and vsym.type_val:
            s_agg, _, _ = collect_aggregate_types(vsym.type_val, record_ctx)
            for item in s_agg:
                if item[0] not in agg_names:
                    agg_names.add(item[0])
                    agg_types.append(item)

    if agg_types:
        emitter = CDeclarationEmitter(record_ctx, qtype_to_c_type, lambda *_: ([], []))
        lines.extend(emitter.emit_forward_typedefs(agg_types))
        lines.extend(emitter.emit_aggregate_structs(agg_types))

    # Abstract types (erased to QVal in C)
    lines.append("/* --- Type Declarations --- */")
    has_types = False
    for sig, _ in _type_signatures(decl):
        if isinstance(sig, ast.TypeFormal):
            has_types = True
            kind_desc = (
                "TYPE"
                if sig.bound is None or isinstance(sig.bound, ast.KindType)
                else str(sig.bound)
            )
            lines.append(f"/* Abstract type {sig.name}::{kind_desc} */")
            lines.append(f"typedef QVal quest_type_{c_name}_{sig.name};")
        elif isinstance(sig, ast.TypeBinding) and not sig.is_rec:
            has_types = True
            type_sym = iface_scope.lookup_type_local(sig.name)
            concrete_t = type_sym.definition if type_sym and type_sym.definition else None
            c_type_name = qtype_to_c_type(concrete_t) if concrete_t else "QVal"
            lines.append(f"/* Manifest type {sig.name} */")
            if isinstance(concrete_t, QRecordType):
                lines.append(f"typedef struct quest_rec_{c_name}_{sig.name} {{")
                for f in concrete_t.fields:
                    f_c_type = qtype_to_c_type(f.type_val)
                    lines.append(f"    {f_c_type} {f.name};")
                lines.append(f"}} quest_rec_{c_name}_{sig.name};")
                lines.append(f"typedef QRecordVal quest_type_{c_name}_{sig.name};")
            else:
                lines.append(f"typedef {c_type_name} quest_type_{c_name}_{sig.name};")
    if not has_types:
        lines.append("/* (No types declared) */")
    lines.append("")

    # Member signatures as function pointer typedefs
    lines.append(f"/* --- Member Signatures for Interface {decl.name} --- */")
    has_values = False
    for sig in decl.signatures:
        if isinstance(sig, ast.FieldSig) and sig.name:
            has_values = True
            val_sym = iface_scope.lookup_value_local(sig.name)
            val_t = val_sym.type_val if val_sym else None
            if isinstance(val_t, (QFunType, QAllType)):
                inner_fn = val_t.body if isinstance(val_t, QAllType) else val_t
                if isinstance(inner_fn, QFunType):
                    ret_c_type = qtype_to_c_type(inner_fn.result_type)
                else:
                    ret_c_type = qtype_to_c_type(inner_fn)
                param_c_types: list[str] = []
                if isinstance(val_t, QAllType):
                    for q in val_t.quantifiers:
                        param_c_types.append(f"const QTypeDescriptor *desc_{q.name}")
                if isinstance(inner_fn, QFunType):
                    for p in inner_fn.params:
                        p_name = p.name or "arg"
                        if p_name in C_KEYWORDS:
                            p_name = f"q_{p_name}"
                        pointer = " *" if p.is_var or p.is_out else " "
                        param_c_types.append(f"{qtype_to_c_type(p.type_val)}{pointer}{p_name}")
                params_decl = ", ".join(param_c_types) if param_c_types else "void"
                lines.append(f"/* {sig.name}: {format_type_for_qi(val_t)} */")
                lines.append(
                    f"typedef {ret_c_type} (*quest_sig_{c_name}_{sig.name})({params_decl});"
                )
            else:
                c_val_type = qtype_to_c_type(val_t) if val_t else "QVal"
                lines.append(f"/* {sig.name}: {format_type_for_qi(val_t)} */")
                lines.append(f"typedef {c_val_type} quest_sig_{c_name}_{sig.name};")
    if not has_values:
        lines.append("/* (No values declared) */")
    lines.append("")

    lines.extend([
        "#ifdef __cplusplus",
        "}",
        "#endif",
        "",
        f"#endif /* {guard_name} */",
        "",
    ])

    return "\n".join(lines)


# The interface files being compiled, outermost first, with their canonical names. Compiling an interface first
# compiles the interfaces it imports, each in an environment of its own, so a cycle of imports is detected here.
_compiling_interfaces: list[tuple[Path, str]] = []


def compile_interface_file(
    file_path: Path,
    output_dir: Optional[Path] = None,
    include_paths: Optional[list[Path]] = None,
    build_dir: Optional[Path] = None,
    header: bool = True,
    program_dir: Optional[Path] = None,
) -> tuple[Path, Path]:
    """Compiles a .int.quest file to .qi and, unless header is False, .int.h files.

    Only C compilation needs headers; typecheck and interpret runs build just the .qi.
    """
    from quest.module_loader import canonicalize_module_path

    key = file_path.resolve()
    canon_name = canonicalize_module_path(file_path, list(include_paths or []), program_dir)
    compiling = [path for path, _ in _compiling_interfaces]
    if key in compiling:
        chain = [name for _, name in _compiling_interfaces[compiling.index(key):]] + [canon_name]
        raise QuestTypeError(f"Cyclic dependency detected in interface imports: {' -> '.join(chain)}")
    _compiling_interfaces.append((key, canon_name))
    try:
        return _compile_interface_file(file_path, output_dir, include_paths, build_dir, header, program_dir)
    finally:
        _compiling_interfaces.pop()


def _compile_interface_file(
    file_path: Path,
    output_dir: Optional[Path],
    include_paths: Optional[list[Path]],
    build_dir: Optional[Path],
    header: bool,
    program_dir: Optional[Path],
) -> tuple[Path, Path]:
    try:
        source_text = file_path.read_text(encoding="utf-8")
    except OSError as err:
        raise QuestTypeError(f"Error reading interface file '{file_path}': {err}")

    source_map = SourceMap(source_text, display_file_name(file_path))
    # Errors are located in this file, and the imports it makes are located in it (docs/diagnostics.md §4.4)
    with in_unit(source_map):
        tokens = Tokenizer(source_text, str(file_path)).tokenize_all()
        prog = parse_quest_program(tokens, source_map)

        if not isinstance(prog, ast.Program) or len(prog.phrases) != 1:
            raise QuestTypeError(
                f"Interface file '{file_path.name}' must contain exactly one interface declaration"
            )

        decl = prog.phrases[0]
        if not isinstance(decl, ast.InterfaceDecl):
            raise QuestTypeError(
                f"Expected interface declaration in '{file_path.name}', but found {type(decl).__name__}"
            )
        if decl.name.lower() != file_path.name.split(".")[0].lower():
            raise QuestTypeError(
                f"Interface declared in '{file_path.name}' has name '{decl.name}', which does not match file name",
                offset=decl.offset,
            )

        env = Environment()
        env.include_paths = list(include_paths) if include_paths else []
        if build_dir is not None:
            b_dir = Path(build_dir).resolve()
            if b_dir not in env.include_paths:
                env.include_paths.insert(0, b_dir)
            # Imported interfaces are loaded from their (fresh or rebuilt) artifacts in the same build directory
            # rather than re-elaborated from source in every nested compilation.
            from quest.pipeline import CompilerOptions
            env.options = CompilerOptions(build_dir=b_dir, include_paths=list(env.include_paths))
        env.current_dir = file_path.parent
        env.program_dir = program_dir
        env.source_map = source_map

        if build_dir is not None:
            # The generated header #includes the headers of imported interfaces, so they must exist in the
            # build directory too, including those of builtin interfaces that are never loaded from source.
            for imp in decl.imports:
                with at_import(imp.offset, source_map):
                    ensure_interface_artifacts(
                        imp.effective_interface_path, file_path.parent, env.include_paths, Path(build_dir).resolve(),
                        header=header, program_dir=program_dir,
                    )
        typed_iface = elaborate_interface(decl, env)

    qi_content = compile_interface_to_qi(decl, typed_iface.scope, env=env, source=file_path)

    if build_dir is not None and output_dir is None:
        from quest.module_loader import canonicalize_module_path
        canon_name = canonicalize_module_path(file_path, env.include_paths, program_dir)
        if "/" in canon_name:
            target_dir = Path(build_dir).resolve() / Path(canon_name).parent
        else:
            target_dir = Path(build_dir).resolve()
    else:
        target_dir = output_dir if output_dir is not None else file_path.parent
    base_name = file_path.name
    if base_name.endswith(".int.quest"):
        stem = base_name[:-10]
    else:
        stem = file_path.stem

    qi_path = target_dir / f"{stem.lower()}.qi"
    h_path = target_dir / f"{stem.lower()}.int.h"
    qi_path.parent.mkdir(parents=True, exist_ok=True)
    h_path.parent.mkdir(parents=True, exist_ok=True)

    qi_path.write_text(qi_content, encoding="utf-8")
    if header:
        from quest.module_loader import canonicalize_interface_name
        canonical_name = canonicalize_interface_name(file_path, env.include_paths, decl.name)
        h_path.write_text(compile_interface_to_header(decl, typed_iface.scope, canonical_name), encoding="utf-8")

    return h_path, qi_path


def ensure_interface_artifacts(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
    build_dir: Path,
    file_path: Optional[Path] = None,
    header: bool = True,
    program_dir: Optional[Path] = None,
) -> tuple[Path, Path, str]:
    """Regenerates interface `name`'s .qi and C header under build_dir if stale (docs/build-process.md §5).

    file_path is the result of resolve_interface_file, when the caller already has it. Returns
    (qi_file, h_file, canonical_name); the files may not exist if the interface has neither a source
    nor prebuilt artifacts (e.g. builtin interfaces).
    """
    from quest.module_loader import (
        canonicalize_module_path,
        resolve_interface_file,
        resolve_interface_source_file,
    )

    if file_path is None:
        file_path = resolve_interface_file(name, current_dir, include_paths)
    src = resolve_interface_source_file(name, current_dir, include_paths)
    if src is None and file_path is not None and file_path.name.endswith(".int.quest"):
        src = file_path

    canon_name = canonicalize_module_path(src, include_paths, program_dir) if src else name.lower()
    target_dir = build_dir / Path(canon_name).parent if "/" in canon_name else build_dir
    stem = Path(canon_name).name.lower()
    qi_file = target_dir / f"{stem}.qi"
    h_file = target_dir / f"{stem}.int.h"

    def current(qi: Path, h: Path) -> bool:
        """Rules 1 and 2 plus the ABI version: the artifacts exist, are fresh, match this compiler, and were
        built from this source (not a same-named interface elsewhere).

        The header is required only when one is wanted (C compilation).
        """
        if not qi.is_file() or (header and not h.is_file()) or not has_current_abi(qi):
            return False
        if src is None or not src.is_file():
            return True
        src_mtime = src.stat().st_mtime
        return (
            src_mtime <= qi.stat().st_mtime
            and (not header or src_mtime <= h.stat().st_mtime)
            and built_from(qi, src)
        )

    # Fresh artifacts found elsewhere on the search path (e.g. next to the source, from a standalone
    # compilation) are used like those in the build directory.
    if not current(qi_file, h_file) and file_path is not None and file_path.suffix == ".qi":
        cand_h = file_path.with_suffix(".int.h")
        if current(file_path, cand_h) or (src is None and not qi_file.is_file()):
            qi_file, h_file = file_path, cand_h

    # Rule 3: without a source, existing artifacts cannot be rebuilt (binary distribution).
    if src is None or not src.is_file():
        if qi_file.is_file() and not has_current_abi(qi_file):
            raise QuestTypeError(incompatible_artifact_message(qi_file))
        return qi_file, h_file, canon_name
    if not current(qi_file, h_file):
        target_dir.mkdir(parents=True, exist_ok=True)
        search_paths = list(include_paths)
        if build_dir not in search_paths:
            search_paths.insert(0, build_dir)
        h_file, qi_file = compile_interface_file(
            src, output_dir=target_dir, include_paths=search_paths, build_dir=build_dir, header=header,
            program_dir=program_dir,
        )
    return qi_file, h_file, canon_name


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
        from quest.module_loader import load_interface

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
                        from quest.module_loader import (
                            load_module,
                            resolve_module_file,
                            resolve_object_file,
                        )
                        mod_scope = None
                        if (
                            mod_path in env.loaded_modules_ast
                            or mod_path in env.precompiled_modules
                            or resolve_module_file(mod_path, env.current_dir, env.include_paths) is not None
                            or resolve_object_file(mod_path, env.current_dir, env.include_paths) is not None
                        ):
                            try:
                                typed_mod = load_module(mod_path, imp_name, env)
                                mod_scope = typed_mod.scope
                            except (QuestCompilerError, OSError) as err:
                                if getattr(env, "sink", None) is not None:
                                    if isinstance(err, QuestCompilerError):
                                        env.sink.emit(diagnostic_of(err))
                                    else:
                                        env.sink.emit(Diagnostic.make_from_exception(err, 0))
                                mod_scope = None

                        registered_scope = mod_scope if mod_scope is not None else imp_scope
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
            group_members: list[tuple[str, TypeSymbol, QType]] = []
            for idx, (t_name, is_manifest, kind_str, manifest_str, type_sym, group) in enumerate(
                type_records_list
            ):
                if group:
                    body = _parse_and_elaborate_type_in_env(manifest_str, env)
                    group_members.append((t_name, type_sym, body))
                    if idx + 1 == len(type_records_list) or type_records_list[idx + 1][5] != group:
                        bindings = tuple(
                            (name, sym.symbol_id, sym.kind, body) for name, sym, body in group_members
                        )
                        for active, (_, sym, _) in enumerate(group_members):
                            sym.definition = QRecGroupType(bindings=bindings, active_index=active)
                        group_members = []
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
