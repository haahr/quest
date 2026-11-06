"""The layouts of the objects generated code allocates (docs/collector.md
§3.2), for every backend. Each allocation names a layout, a static QLayout of
the unit, which says for each word of the object whether it is a pointer, a
scalar, or ambiguous (a QVal of generic code, whose kind the site does not
know), so that a precise collector can scan the object and
QUEST_GC_CHECK=layouts can check what the compilers say. The kinds come from the shapes the slots hold
(codegen/layout): a slot's representation, or a value's representation for a
closure environment's captures. A unit's layouts are collected in a table by
tag, and the C printer lays them out as static data (quest_layout_<tag>); the
runtime defines the common ones (a closure, an array, an adapter's environment),
which generated code names by symbol. The self-hosted compiler's
questlang/codegen/objectLayout is this module in Quest."""

from __future__ import annotations

from dataclasses import dataclass, field

from quest.codegen.layout import layout_of, resolved_shape, shape_tag, type_digest, type_tag
from quest.ir.shapes import Shape, shape
from quest.types import QType

SCALAR, POINTER, AMBIGUOUS = 0, 1, 2
KIND_LETTERS = {SCALAR: "s", POINTER: "p", AMBIGUOUS: "a"}

CLOSURE_SYMBOL = "quest_layout_closure"
ADAPTER_ENV_SYMBOL = "quest_layout_adapter_env"
ARRAY_SYMBOLS = {
    SCALAR: "quest_layout_array_scalar",
    POINTER: "quest_layout_array_pointer",
    AMBIGUOUS: "quest_layout_array_ambiguous",
}

_SCALAR_REPRESENTATIONS = {"QInt", "QReal", "QBool", "QChar", "uint64_t", "void"}


def representation_kinds(s: Shape) -> list[int]:
    """The kinds of the words of a value of shape s in its representation, as
    a closure environment holds a capture: none for an Ok, a pointer and a
    pointer for a record, a scalar and an ambiguous word for a variant (its tag
    and its payload), and one word otherwise."""
    rep = layout_of(resolved_shape(s)).representation
    if rep == "void":
        return []
    if rep == "QVal":
        return [AMBIGUOUS]
    if rep == "QRecordVal":
        return [POINTER, POINTER]
    if rep == "QVariantVal":
        return [SCALAR, AMBIGUOUS]
    if rep in _SCALAR_REPRESENTATIONS:
        return [SCALAR]
    return [POINTER]


def slot_kind(s: Shape) -> int:
    """The kind of the word an aggregate slot holds a value of shape s in: a
    record or variant is a pointer to its box, an Ok the word Q_OK_VAL."""
    rep = layout_of(resolved_shape(s)).representation
    if rep == "QVal":
        return AMBIGUOUS
    if rep in ("QRecordVal", "QVariantVal"):
        return POINTER
    if rep in _SCALAR_REPRESENTATIONS:
        return SCALAR
    return POINTER


def box_kinds(s: Shape) -> list[int]:
    """The kinds of a box embedded in an aggregate's allocation: a
    QVariantVal's, or a QRecordVal's."""
    rep = layout_of(resolved_shape(s)).representation
    return [SCALAR, AMBIGUOUS] if rep == "QVariantVal" else [POINTER, POINTER]


@dataclass(frozen=True)
class Layout:
    """A layout: its tag (its symbol is quest_layout_<tag>), the kinds of its
    words, its bytes, and its size as C spells it (sizeof a struct the C
    backend declares, so that the two agree by construction), or "" for the
    bytes. Generated code makes fixed layouts only; the runtime's array
    layouts serve arrays."""
    tag: str
    words: tuple[int, ...]
    bytes: int
    c_size: str = ""

    @property
    def symbol(self) -> str:
        return f"quest_layout_{self.tag}"


def _with_boxes(words: list[int], boxes: list[Shape]) -> str:
    """Adds the boxes' kinds after the object's words, returning the tag's
    suffix naming them (none without boxes)."""
    suffix = ""
    for s in boxes:
        kinds = box_kinds(s)
        words.extend(kinds)
        suffix += KIND_LETTERS[kinds[1]]
    return f"_b{suffix}" if boxes else ""


def _c_size(struct: str, boxes: int) -> str:
    if not struct:
        return ""
    return f"sizeof({struct})" if boxes == 0 else f"sizeof({struct}) + {boxes} * sizeof(QRecordVal)"


def tuple_layout(ts: Shape, struct: str, boxes: list[Shape]) -> Layout:
    """A tuple of shape ts, whose struct C names `struct`, with the boxes of
    the fields of shapes `boxes` embedded after it."""
    words = [slot_kind(c.shape) for c in ts.components]
    if not words:
        # A struct of no slots has a char of its own, one word's worth
        words = [SCALAR]
    suffix = _with_boxes(words, boxes)
    return Layout(shape_tag(ts) + suffix, tuple(words), 8 * len(words), _c_size(struct, len(boxes)))


def tuple_prefix_layout(ts: Shape, n: int) -> Layout:
    """The first n components of a tuple of shape ts, as a copy of them is
    laid out."""
    words = [slot_kind(c.shape) for c in ts.components[:n]] or [SCALAR]
    return Layout(f"{shape_tag(ts)}_{n}", tuple(words), 8 * len(words))


def record_layout(t: QType, struct: str, boxes: list[Shape]) -> Layout:
    """A record made in its box (docs/c-representation.md §5.1): the
    QRecordVal, then the payload of record type t, whose struct C names
    `struct`, then the embedded boxes."""
    rs = shape(t)
    # The box: the payload and the dictionary; the payload's header: its
    # descriptor; then its fields in the order of their names
    words = [POINTER, POINTER, POINTER]
    fields = sorted(rs.components, key=lambda c: c.name or "")
    words.extend(slot_kind(c.shape) for c in fields)
    if not fields:
        # A record of no fields has a word of padding after its header
        words.append(SCALAR)
    suffix = _with_boxes(words, boxes)
    c_size = f"sizeof(QRecordVal) + {_c_size(struct, len(boxes))}" if struct else ""
    # Named by the struct where the unit names one (two aliases of one record
    # type name two structs, each sized as itself), and otherwise by the type
    tag = struct if struct else f"record_{type_tag(t)}_{type_digest(t)}"
    return Layout(tag + suffix, tuple(words), 8 * len(words), c_size)


def _case_kinds(c) -> list[int]:
    """The kinds of the words of a case (its tag, then its components)."""
    words = [SCALAR]
    cs = c.shape
    if cs is not None:
        if cs.kind in ("tuple", "record"):
            words.extend(slot_kind(comp.shape) for comp in cs.components)
        else:
            words.append(slot_kind(cs))
    return words


def option_layout(os: Shape, struct: str, tag: str | None) -> Layout:
    """An option of shape os, whose struct C names `struct`, of the case named
    tag, or of any case (None): then each word is the kind its cases give it,
    ambiguous where they differ."""
    # The struct: the tag, then the union of the cases' payloads, each a
    # struct of its slots (layout.option_bytes in the self-hosted compiler)
    most = max((len(_case_kinds(c)) - 1 for c in os.cases if c.shape is not None), default=0)
    n = 1 + most
    size = 8 * n
    words = [SCALAR] * n
    if tag is not None:
        index = next((i for i, c in enumerate(os.cases) if c.name == tag), 0)
        for i, k in enumerate(_case_kinds(os.cases[index])[:n]):
            words[i] = k
        suffix = f"_{index}"
    else:
        # A case that lacks a word leaves it zero, which suits any kind
        seen = [False] * n
        for c in os.cases:
            for i, k in enumerate(_case_kinds(c)[:n]):
                if not seen[i]:
                    seen[i] = True
                    words[i] = k
                elif words[i] != k:
                    words[i] = AMBIGUOUS
        suffix = "_any"
    return Layout(shape_tag(os) + suffix, tuple(words), size, _c_size(struct, 0))


def env_layout(code: str, kinds: list[int], size: int, c_size: str) -> Layout:
    """A closure's environment (struct QEnv_<code>) of the given words."""
    return Layout(f"env_{code}", tuple(kinds), size, c_size)


@dataclass
class Table:
    """A unit's layouts, by tag and in the order first registered."""
    by_tag: dict[str, Layout] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)

    def register(self, layout: Layout) -> str:
        """Registers layout, returning its symbol; a layout registered before
        under the same tag must be the same."""
        found = self.by_tag.get(layout.tag)
        if found is None:
            self.by_tag[layout.tag] = layout
            self.order.append(layout.tag)
        elif found != layout:
            raise ValueError(f"internal: two layouts named {layout.tag}")
        return layout.symbol

    def layouts(self) -> list[Layout]:
        return [self.by_tag[tag] for tag in self.order]


def c_definitions(table: Table) -> list[str]:
    """The C definitions of a unit's layouts: each one's kinds, then its
    QLayout."""
    lines = []
    for l in table.layouts():
        kinds = ", ".join(str(k) for k in l.words) or "0"
        size = l.c_size or str(l.bytes)
        lines.append(f"static const uint8_t qlk_{l.tag}[] = {{ {kinds} }};")
        # A layout of scalars alone is noscan: the collector never scans its objects
        flags = "Q_LAYOUT_NOSCAN" if all(k == SCALAR for k in l.words) else "0"
        lines.append(f'static const QLayout {l.symbol} Q_UNUSED = {{ "{l.tag}", Q_LAYOUT_FIXED, {flags}, {size}, 0, 0, '
                     f"{len(l.words)}, qlk_{l.tag} }};")
    if lines:
        lines.append("")
    return lines
