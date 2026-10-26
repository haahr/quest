"""Generates the self-hosted type model's golden test (questlang/types/model, symbols, and dump) from the bootstrap's.

The cases below build types and kinds with the bootstrap's model (bootstrap/python/quest/types/model.py) and apply its
operations to them: printing (str, format_type_compact, qtype_dump, short_type_name), hash-consing, free variables,
substitution, lazy evaluation and unfolding, metavariables, and the model's queries. The generator writes
tests/source/questlang/types_model.quest, which builds the same types with the self-hosted model and applies the same
operations, and its golden, which holds what the bootstrap gives.

    python tests/types/generate.py

Run it after changing a case; the test runs as part of the test suite.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

from quest.types.model import (  # noqa: E402
    BOOL_TYPE,
    BOTTOM_TYPE,
    CHAR_TYPE,
    DYNAMIC_TYPE,
    EXCEPTION_TYPE,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    TYPE_KIND,
    QAbstractType,
    QAliasType,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
    QExternalType,
    QFunType,
    QKindVar,
    QOptionField,
    QOptionType,
    QOutType,
    QParam,
    QPathType,
    QPowerKind,
    QQuantifier,
    QRecGroupType,
    QRecType,
    QRecordField,
    QRecordType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QTypeApp,
    QTypeFormal,
    QTypeFun,
    QTypeMeta,
    QTypeVar,
    QVariantField,
    QVariantType,
    QVarType,
    alias_reference,
    auto_matches_subtypes,
    auto_payload_type,
    find_path_types,
    map_aliases,
    strip_aliases,
    type_mentions_symbol_ids,
    unalias,
    unsolved_metas,
)
from quest.types.dump import format_type_compact, qtype_dump, short_type_name  # noqa: E402

TEST_FILE = ROOT_DIR / "tests" / "source" / "questlang" / "types_model.quest"
GOLDEN_FILE = ROOT_DIR / "tests" / "golden" / "run" / "questlang" / "types_model.out"


# =========================================================================
# Quest literals
# =========================================================================

def qstr(s: str) -> str:
    out = ['"']
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def qint(n: int) -> str:
    return f"~{-n}" if n < 0 else str(n)


def qbool(b: bool) -> str:
    return "true" if b else "false"


def qopt_str(s: Optional[str]) -> str:
    return f"maybe.some(:String {qstr(s)})" if s is not None else "maybe.none(:String)"


# =========================================================================
# Emitting the Quest that builds a type
# =========================================================================

class Emitter:
    """Emits a let for each node the cases build, once, in an order that defines each before its uses, so that the
    Quest program builds the same graph (and so the same identities) as the bootstrap's."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.names: dict[int, str] = {}
        self.keep: list[Any] = []

    def bind(self, node: Any, expr: str) -> str:
        name = f"n{len(self.names)}"
        self.names[id(node)] = name
        self.keep.append(node)
        self.lines.append(f"let {name} = {expr};")
        return name

    def meta(self, m: QTypeMeta) -> str:
        """Declares a metavariable, in the order the bootstrap made them."""
        return self.bind(m, f"model.newMeta({self.kind(m.bound)} maybe.some(:String {qstr(m.name)}))")

    def opt_type(self, t: Optional[Any]) -> str:
        return f"maybe.some(:model.Type {self.type(t)})" if t is not None else "maybe.none(:model.Type)"

    def opt_kind(self, k: Optional[Any]) -> str:
        return f"maybe.some(:model.Kind {self.kind(k)})" if k is not None else "maybe.none(:model.Kind)"

    def kind(self, k: Any) -> str:
        if k is TYPE_KIND:
            return "model.typeKind"
        if id(k) in self.names:
            return self.names[id(k)]
        match k:
            case QPowerKind(bound=b):
                return self.bind(k, f"model.powerKind({self.type(b)})")
            case QAllKind():
                return self.bind(k, f"model.allKind({qstr(k.param_name)} {qint(k.param_id)} "
                                    f"{self.kind(k.param_kind)} {self.kind(k.result_kind)})")
            case QKindVar():
                return self.bind(k, f"model.kindVar({qstr(k.name)} {qint(k.symbol_id)})")
        raise TypeError(k)

    def array(self, element_type: str, items: list[str]) -> str:
        return f"array of {' '.join(items)} end" if items else f"array of :{element_type} end"

    def fields(self, fields: tuple[QRecordField, ...]) -> str:
        return self.array("model.RecordField", [
            f"tuple let name = {qstr(f.name)} let type = {self.type(f.type_val)} let isVar = {qbool(f.is_var)} end"
            for f in fields])

    def component(self, c: Any) -> str:
        match c:
            case QTupleField():
                return f"model.tupleField({qopt_str(c.name)} {self.type(c.type_val)} {qbool(c.is_var)})"
            case QTupleTypeFormal():
                return (f"option tupleTypeFormal of model.TupleComponent with let name = {qstr(c.name)} "
                        f"let symbolId = {qint(c.symbol_id)} let bound = {self.kind(c.bound)} end")
            case QTupleTypeBinding():
                return (f"option tupleTypeBinding of model.TupleComponent with let name = {qstr(c.name)} "
                        f"let type = {self.type(c.type_val)} let bound = {self.opt_kind(c.bound)} end")
        raise TypeError(c)

    def type(self, t: Any) -> str:
        singletons = {
            id(INT_TYPE): "model.intType", id(REAL_TYPE): "model.realType", id(BOOL_TYPE): "model.boolType",
            id(CHAR_TYPE): "model.charType", id(STRING_TYPE): "model.stringType", id(OK_TYPE): "model.okType",
            id(BOTTOM_TYPE): "model.bottomType", id(EXCEPTION_TYPE): "model.exceptionType",
            id(DYNAMIC_TYPE): "model.dynamicType",
        }
        if id(t) in singletons:
            return singletons[id(t)]
        if id(t) in self.names:
            return self.names[id(t)]
        match t:
            case QExceptionType():
                return self.bind(t, f"model.exceptionOf({self.type(t.payload_type)})")
            case QExternalType():
                return self.bind(t, f"model.externalType({qstr(t.name)} {qstr(t.c_type)})")
            case QTupleType():
                comps = [self.component(c) for c in t.fields]
                return self.bind(t, f"model.tupleType({self.array('model.TupleComponent', comps)})")
            case QRecordType():
                return self.bind(t, f"model.recordType({self.fields(t.fields)} {qopt_str(t.provenance)})")
            case QVariantType():
                items = [f"tuple let name = {qstr(v.name)} let type = {self.opt_type(v.type_val)} "
                         f"let isVar = {qbool(v.is_var)} end" for v in t.variants]
                return self.bind(t, f"model.variantType({self.array('model.VariantField', items)})")
            case QOptionType():
                items = [f"tuple let name = {qstr(o.name)} let payload = {self.opt_type(o.payload_type)} end"
                         for o in t.options]
                return self.bind(t, f"model.optionType({self.array('model.OptionField', items)})")
            case QFunType():
                items = [f"tuple let name = {qstr(p.name)} let type = {self.type(p.type_val)} "
                         f"let isVar = {qbool(p.is_var)} let isOut = {qbool(p.is_out)} end" for p in t.params]
                return self.bind(t, f"model.funType({self.array('model.Param', items)} {self.type(t.result_type)})")
            case QVarType():
                return self.bind(t, f"model.varType({self.type(t.element_type)})")
            case QArrayType():
                return self.bind(t, f"model.arrayType({self.type(t.element_type)})")
            case QOutType():
                return self.bind(t, f"model.outType({self.type(t.element_type)})")
            case QAllType():
                items = [f"tuple let name = {qstr(q.name)} let symbolId = {qint(q.symbol_id)} "
                         f"let bound = {self.kind(q.bound)} end" for q in t.quantifiers]
                return self.bind(t, f"model.allType({self.array('model.Quantifier', items)} {self.type(t.body)})")
            case QAutoType():
                return self.bind(t, f"model.autoType({qstr(t.type_param)} {qint(t.symbol_id)} "
                                    f"{self.kind(t.kind_bound)} {self.fields(t.signature)})")
            case QTypeFun():
                items = [f"tuple let name = {qstr(p.name)} let symbolId = {qint(p.symbol_id)} "
                         f"let bound = {self.kind(p.bound)} end" for p in t.params]
                return self.bind(t, f"model.typeOperator({self.array('model.TypeFormal', items)} {self.type(t.body)})")
            case QTypeApp():
                args = [self.type(a) for a in t.arguments]
                return self.bind(t, f"model.typeApp({self.type(t.constructor)} {self.array('model.Type', args)})")
            case QRecType():
                return self.bind(t, f"model.recType({qstr(t.var_name)} {qint(t.symbol_id)} "
                                    f"{self.kind(t.bound)} {self.type(t.body)})")
            case QRecGroupType():
                items = [f"tuple let name = {qstr(b[0])} let symbolId = {qint(b[1])} let bound = {self.kind(b[2])} "
                         f"let body = {self.type(b[3])} end" for b in t.bindings]
                return self.bind(t, f"model.recGroupType({self.array('model.RecBinding', items)} {t.active_index})")
            case QTypeVar():
                return self.bind(t, f"model.typeVariable({qstr(t.name)} {qint(t.symbol_id)} {self.opt_kind(t.bound)})")
            case QAbstractType():
                return self.bind(t, f"model.abstractType({qstr(t.name)} {qint(t.symbol_id)} {self.kind(t.bound)})")
            case QPathType():
                return self.bind(t, f"model.pathType({qstr(t.root_name)} {qint(t.root_symbol_id)} "
                                    f"{qstr(t.field_name)} {self.kind(t.bound)})")
            case QAliasType():
                return self.bind(t, f"model.aliasType({qstr(t.name)} {qint(t.symbol_id)} {self.type(t.target)})")
        raise TypeError(t)


# =========================================================================
# The cases
# =========================================================================

def build_cases(em: Emitter) -> list[tuple[str, str]]:
    """(Quest expression of a String, the bootstrap's value) for each check."""
    checks: list[tuple[str, str]] = []

    def check(label: str, quest: str, value: str) -> None:
        checks.append((f"{qstr(label + ': ')} <> {quest}", f"{label}: {value}"))

    def show_all(label: str, t: Any) -> None:
        n = em.type(t)
        check(label + " str", f"model.show({n})", str(t))
        check(label + " compact", f"dump.formatCompact({n})", format_type_compact(t))
        check(label + " short", f"dump.shortTypeName({n})", short_type_name(t))
        check(label + " dump", f"dump.typeDump({n} 0)", qtype_dump(t))
        check(label + " fv", f"ids({n}.fv)", " ".join(str(i) for i in sorted(t._fv)))

    def show_kind(label: str, k: Any) -> None:
        n = em.kind(k)
        check(label + " str", f"model.showKind({n})", str(k))
        check(label + " compact", f"dump.formatKindCompact({n})", format_type_compact(k))
        check(label + " dump", f"dump.kindDump({n} 0)", qtype_dump(k))

    def same(label: str, a: Any, b: Any) -> None:
        check(label, f"conv.bool(model.same({em.type(a)} {em.type(b)}))", "true" if a is b else "false")

    A = QTypeVar("A", 101, TYPE_KIND)
    B = QTypeVar("B", 102, TYPE_KIND)
    X = QTypeVar("X", 103, TYPE_KIND)

    # Kinds
    show_kind("TYPE", TYPE_KIND)
    show_kind("power", QPowerKind(QRecordType((QRecordField("x", INT_TYPE),))))
    show_kind("all", QAllKind("A", 101, TYPE_KIND, TYPE_KIND))
    show_kind("kind var", QKindVar("K", 104))

    # Primitives and simple types
    for name, t in [("Int", INT_TYPE), ("Real", REAL_TYPE), ("Bool", BOOL_TYPE), ("Char", CHAR_TYPE),
                    ("String", STRING_TYPE), ("Ok", OK_TYPE), ("Bottom", BOTTOM_TYPE), ("Exception", EXCEPTION_TYPE),
                    ("Dynamic", DYNAMIC_TYPE)]:
        show_all(name, t)
    show_all("exception of", QExceptionType(STRING_TYPE))
    show_all("external", QExternalType("", "FILE *"))
    show_all("named external", QExternalType("Handle", "void *"))

    # Aggregates
    show_all("empty tuple", QTupleType(()))
    tuple_t = QTupleType((
        QTupleField("x", INT_TYPE), QTupleField(None, BOOL_TYPE, is_var=True),
        QTupleTypeFormal("T", 105, TYPE_KIND), QTupleField("t", QTypeVar("T", 105, TYPE_KIND)),
        QTupleTypeBinding("U", STRING_TYPE), QTupleTypeBinding("V", INT_TYPE, QPowerKind(INT_TYPE)),
    ))
    show_all("tuple", tuple_t)
    show_all("empty record", QRecordType(()))
    record_t = QRecordType((QRecordField("a", INT_TYPE), QRecordField("b", STRING_TYPE, is_var=True)))
    show_all("record", record_t)
    show_all("module record", QRecordType((QRecordField("f", INT_TYPE),), provenance="m"))
    show_all("variant", QVariantType((QVariantField("a"), QVariantField("b", INT_TYPE, is_var=True),
                                       QVariantField("c", OK_TYPE))))
    show_all("empty variant", QVariantType(()))
    show_all("option", QOptionType((QOptionField("none"), QOptionField("some", QTupleType((QTupleField("val", A),))))))
    show_all("empty option", QOptionType(()))
    fun_params = (QParam("x", INT_TYPE), QParam("y", STRING_TYPE, is_var=True), QParam("z", BOOL_TYPE, is_out=True))
    fun_t = QFunType(fun_params, record_t)
    show_all("fun", fun_t)
    show_all("fun no params", QFunType((), OK_TYPE))
    show_all("var", QVarType(INT_TYPE))
    show_all("array", QArrayType(QArrayType(CHAR_TYPE)))
    show_all("out", QOutType(REAL_TYPE))

    # Polymorphism and operators
    all_t = QAllType((QQuantifier("A", 101, TYPE_KIND), QQuantifier("B", 102, QPowerKind(A))),
                     QFunType((QParam("a", A),), B))
    show_all("all", all_t)
    auto_t = QAutoType("P", 106, TYPE_KIND, (QRecordField("v", QTypeVar("P", 106, TYPE_KIND)),
                                             QRecordField("f", QFunType((QParam("p", QTypeVar("P", 106)),), INT_TYPE))))
    show_all("auto", auto_t)
    bounded_auto = QAutoType("P", 107, QPowerKind(record_t), (QRecordField("v", QTypeVar("P", 107)),))
    show_all("bounded auto", bounded_auto)
    box = QTypeFun((QTypeFormal("A", 101, TYPE_KIND),), QTupleType((QTupleField("x", A),)))
    show_all("operator", box)
    box_alias = QAliasType("Box", 108, box)
    app_t = QTypeApp(box_alias, (INT_TYPE,))
    show_all("app", app_t)
    show_all("app of exception", QTypeApp(EXCEPTION_TYPE, (STRING_TYPE,)))

    # Recursion
    list_t = QRecType("L", 109, TYPE_KIND, QOptionType((QOptionField("nil"), QOptionField("cons", QTupleType(
        (QTupleField("head", INT_TYPE), QTupleField("tail", QTypeVar("L", 109, TYPE_KIND))))))))
    show_all("rec", list_t)
    list_alias = QAliasType("List", 109, list_t)
    show_all("rec alias", list_alias)
    tree_body = QRecordType((QRecordField("kids", QTypeVar("Forest", 111, TYPE_KIND)),))
    forest_body = QOptionType((QOptionField("none"), QOptionField("some", QTypeVar("Tree", 110, TYPE_KIND))))
    group = QRecGroupType((("Tree", 110, TYPE_KIND, tree_body), ("Forest", 111, TYPE_KIND, forest_body)), 0)
    show_all("rec group", group)
    show_all("rec group sibling", group.siblings()[1])
    tree_alias = QAliasType("m.Tree", 110, group)
    show_all("group alias", tree_alias)

    # Variables
    show_all("type var", QTypeVar("A", 101, TYPE_KIND))
    show_all("unbounded type var", QTypeVar("A", 101))
    show_all("abstract", QAbstractType("T", 112, QPowerKind(INT_TYPE)))
    path_t = QPathType("p", 113, "T", QPowerKind(record_t))
    show_all("path", path_t)
    show_all("alias", QAliasType("Point", 114, record_t))

    # Hash-consing
    same("same int", INT_TYPE, INT_TYPE)
    same("same record", record_t,
         QRecordType((QRecordField("a", INT_TYPE), QRecordField("b", STRING_TYPE, is_var=True))))
    same("different record", record_t, QRecordType((QRecordField("a", INT_TYPE), QRecordField("b", STRING_TYPE))))
    same("provenance distinguishes", QRecordType((QRecordField("f", INT_TYPE),)),
         QRecordType((QRecordField("f", INT_TYPE),), provenance="m"))
    same("same fun", fun_t, QFunType((QParam("x", INT_TYPE), QParam("y", STRING_TYPE, is_var=True),
                                      QParam("z", BOOL_TYPE, is_out=True)), record_t))
    same("same var by name and id", QTypeVar("A", 101, TYPE_KIND), A)
    same("var names distinguish", QTypeVar("A", 101, TYPE_KIND), QTypeVar("A2", 101, TYPE_KIND))

    # Substitution
    def subst(label: str, t: Any, pairs: list[tuple[int, Any]]) -> None:
        result = t.substitute(dict(pairs))
        items = " ".join(f"model.singleSubst({qint(i)} {em.type(u)})" for i, u in pairs)
        quest_subst = f"substOf(array of {items} end)" if pairs else "model.newSubst()"
        n = em.type(t)
        check(label, f"model.show(model.substitute({n} {quest_subst}))", str(result))
        check(label + " is input",
              f"conv.bool(model.same(model.substitute({n} {quest_subst}) {n}))", "true" if result is t else "false")

    subst("subst var", A, [(101, INT_TYPE)])
    subst("subst fun", QFunType((QParam("a", A),), B), [(101, INT_TYPE), (102, STRING_TYPE)])
    subst("subst untouched", record_t, [(101, INT_TYPE)])
    subst("subst all binds", all_t, [(101, INT_TYPE), (102, STRING_TYPE)])
    subst("subst all free", QAllType((QQuantifier("A", 101, TYPE_KIND),), QFunType((QParam("x", X),), A)),
          [(103, BOOL_TYPE)])
    subst("subst tuple telescope", QTupleType((QTupleField("x", X), QTupleTypeFormal("X", 103, TYPE_KIND),
                                               QTupleField("y", X))), [(103, INT_TYPE)])
    subst("subst rec", QRecType("L", 109, TYPE_KIND, QFunType((QParam("x", X),), QTypeVar("L", 109))),
          [(103, INT_TYPE), (109, STRING_TYPE)])
    subst("subst alias kept", QAliasType("Point", 114, record_t), [(101, INT_TYPE)])
    subst("subst alias dropped", QAliasType("Pair", 115, QTupleType((QTupleField("a", A),))), [(101, INT_TYPE)])
    subst("subst operator", box, [(101, INT_TYPE)])
    subst("subst auto", QAutoType("P", 106, TYPE_KIND, (QRecordField("v", A), QRecordField("p", QTypeVar("P", 106)))),
          [(101, INT_TYPE), (106, STRING_TYPE)])
    subst("subst path bound", QPathType("p", 113, "T", QPowerKind(A)), [(101, INT_TYPE)])

    # Lazy evaluation and unfolding (without an environment)
    def evaluate(label: str, t: Any) -> None:
        check(label, f"model.show(model.evaluateLazily({em.type(t)} model.noLookup))", str(t.evaluate_lazily(None)))

    evaluate("eval app", app_t)
    evaluate("eval app of exception", QTypeApp(EXCEPTION_TYPE, (STRING_TYPE,)))
    evaluate("eval rec", list_t)
    evaluate("eval rec alias", list_alias)
    evaluate("eval group", group)
    evaluate("eval group alias", tree_alias)
    evaluate("eval alias", QAliasType("Point", 114, record_t))
    evaluate("eval var without env", A)
    check("unfold rec alias", f"model.show(model.unfoldLazily({em.type(list_alias)}))", str(list_alias.unfold_lazily()))
    check("unfold group alias", f"model.show(model.unfoldLazily({em.type(tree_alias)}))",
          str(tree_alias.unfold_lazily()))
    check("unfold cached",
          f"conv.bool(model.same(model.unfoldLazily({em.type(list_t)}) model.unfoldLazily({em.type(list_t)})))",
          "true" if list_t.unfold_lazily() is list_t.unfold_lazily() else "false")
    siblings = group.siblings()
    check("siblings shared",
          f"conv.bool(model.same(model.siblings({em.type(group)})[1] model.siblings({em.type(siblings[1])})[1]))",
          "true" if siblings[1] is siblings[1].siblings()[1] else "false")

    # Queries
    check("auto payload", f"model.show(model.autoPayloadType({em.type(auto_t)} maybe.none(:model.Type)))",
          str(auto_payload_type(auto_t)))
    check("auto payload at witness",
          f"model.show(model.autoPayloadType({em.type(auto_t)} maybe.some(:model.Type model.intType)))",
          str(auto_payload_type(auto_t, INT_TYPE)))
    check("auto matches subtypes", f"conv.bool(model.autoMatchesSubtypes({em.type(auto_t)}))",
          "true" if auto_matches_subtypes(auto_t) else "false")
    check("dynamic matches subtypes", "conv.bool(model.autoMatchesSubtypes(model.dynamicType))",
          "true" if auto_matches_subtypes(DYNAMIC_TYPE) else "false")
    for name, target, sym_id in [("Int", INT_TYPE, 2), ("Point", record_t, 114)]:
        result = alias_reference(name, sym_id, target)
        check(f"alias reference {name}", f"model.show(model.aliasReference({qstr(name)} {sym_id} {em.type(target)}))",
              str(result))
    check("unalias", f"model.show(model.unalias(model.aliasType(\"Q\" 116 {em.type(list_alias)})))",
          str(unalias(QAliasType("Q", 116, list_alias))))
    paths_in = QFunType((QParam("x", path_t), QParam("y", QPathType("q", 117, "U", TYPE_KIND))), path_t)
    check("find path types", f"showAll(model.findPathTypes({em.type(paths_in)}))",
          " ".join(str(p) for p in find_path_types(paths_in)))
    check("mentions", f"conv.bool(model.typeMentionsSymbolIds({em.type(all_t)} idSet(array of 102 end)))",
          "true" if type_mentions_symbol_ids(all_t, {102}) else "false")
    check("does not mention", f"conv.bool(model.typeMentionsSymbolIds({em.type(record_t)} idSet(array of 102 end)))",
          "true" if type_mentions_symbol_ids(record_t, {102}) else "false")
    with_aliases = QFunType((QParam("p", QAliasType("Point", 114, record_t)),), QAliasType("List", 109, list_t))
    check("strip aliases", f"model.show(model.stripAliases({em.type(with_aliases)}))", str(strip_aliases(with_aliases)))
    check("map aliases", f"model.show(model.mapAliases({em.type(with_aliases)} renamePoint))",
          str(map_aliases(with_aliases, lambda a: INT_TYPE if a.name == "Point" else None)))

    # Metavariables
    QTypeMeta.reset_counter()
    m1 = QTypeMeta()
    m2 = QTypeMeta(QPowerKind(INT_TYPE))
    n1, n2 = em.meta(m1), em.meta(m2)
    with_metas = QFunType((QParam("a", m1), QParam("b", m2)), QArrayType(m1))
    check("metas str", f"model.show({em.type(with_metas)})", str(with_metas))
    check("unsolved metas", f"showAll(model.unsolvedMetas({em.type(with_metas)}))",
          " ".join(str(m) for m in unsolved_metas(with_metas)))
    param_a = f"tuple let name = \"a\" let type = {n1} let isVar = false let isOut = false end"
    param_b = f"tuple let name = \"b\" let type = {n2} let isVar = false let isOut = false end"
    check("meta not hash-consed", f"conv.bool(model.same({em.type(with_metas)} "
          f"model.funType(array of {param_a} {param_b} end model.arrayType({n1}))))", "false")
    m1.instance = STRING_TYPE
    check("solved metas", f"begin solve({n1} model.stringType) showAll(model.unsolvedMetas({em.type(with_metas)})) end",
          " ".join(str(m) for m in unsolved_metas(with_metas)))
    check("solved str", f"model.show({em.type(with_metas)})", str(with_metas))
    check("resolved", f"model.show(model.resolveMetas({em.type(with_metas)}))", str(with_metas.substitute({})))
    check("pruned", f"model.show(model.prune({n1}))", str(m1.prune()))
    return checks


PRELUDE = """import
    questlang/types/model : questlang/types/Model
    questlang/types/dump : questlang/types/Dump
    collections/hashMap : collections/HashMap
    collections/vector : collections/Vector
    util/hash : util/Hash
    util/maybe : util/Maybe
    util/strutil : util/Strutil
    writer : Writer
    conv : Conv
;

let emit(s: String): Ok = begin writer.putString(writer.output s) writer.putString(writer.output "\\n") end;

let ids(a: Array(Int)): String =
    begin
        let parts = vector.new(:String)
        for i = 0 upto {extent a - 1} do vector.append(:String parts conv.int(a[i])) end
        strutil.join(" " parts)
    end;

let showAll(ts: Array(model.Type)): String =
    begin
        let parts = vector.new(:String)
        for i = 0 upto {extent ts - 1} do vector.append(:String parts model.show(ts[i])) end
        strutil.join(" " parts)
    end;

(* The union of single substitutions *)
let substOf(parts: Array(model.Subst)): model.Subst =
    begin
        let s = model.newSubst()
        for i = 0 upto {extent parts - 1} do
            hashMap.forEach(:Int :model.Type parts[i]
                fun(k: Int v: model.Type): Ok begin hashMap.insert(:Int :model.Type s k v) ok end)
        end
        s
    end;

let idSet(a: Array(Int)): hashMap.T(Int Bool) =
    begin
        let s = hashMap.new(:Int :Bool fun(x: Int y: Int): Bool x is y hash.int)
        for i = 0 upto {extent a - 1} do hashMap.insert(:Int :Bool s a[i] true) end
        s
    end;

let renamePoint(alias: model.Type): maybe.T(model.Type) =
    case alias.form
        when typeAlias with x then
            if string.equal(x.name "Point") then maybe.some(:model.Type model.intType) else maybe.none(:model.Type) end
        else maybe.none(:model.Type)
    end;

let solve(meta: model.Type solution: model.Type): Ok =
    case meta.form when typeMeta with x then x.meta.instance := maybe.some(:model.Type solution) else ok end;

model.resetMetaCounter();
"""

HEADER = """(* Self-Hosted Quest Compiler: Test the Type Model (generated by tests/types/generate.py; do not edit)
 *
 * Builds types and kinds with the self-hosted model (questlang/types/model) and applies its operations to them; the
 * golden holds what the bootstrap's model gives for the same types. *)
(* @skip-phase: tokenize, parse, typecheck, ir_core *)
(* @timeout: 300.0 *)

"""


def main() -> None:
    em = Emitter()
    QTypeMeta.reset_counter()
    checks = build_cases(em)
    # The lets come before the checks: each check's types are bound by then. Metavariables are made among the lets,
    # in the order the bootstrap made them.
    body = [HEADER, PRELUDE, "\n", "\n".join(em.lines), "\n\n"]
    body.extend(f"emit({q});\n" for q, _ in checks)
    TEST_FILE.write_text("".join(body), encoding="utf-8")
    GOLDEN_FILE.write_text("".join(v + "\n" for _, v in checks), encoding="utf-8")
    print(f"wrote {TEST_FILE.relative_to(ROOT_DIR)} and {GOLDEN_FILE.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
