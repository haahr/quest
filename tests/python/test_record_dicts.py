"""Unit tests for the C runtime's record offset table map (quest_record_dict) and record layout headers."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.codegen.compiler_runner import compile_c_source, run_binary

# Three record layouts: Big = {a b c}, Mid = {b c}, Other = {x}; all fields Int.
PRELUDE = r"""
#include "quest_runtime.h"
#include <assert.h>
#include <stdio.h>

typedef struct { QRecordHeader header; QInt qf_a; QInt qf_b; QInt qf_c; } Big;
typedef struct { QRecordHeader header; QInt qf_b; QInt qf_c; } Mid;
typedef struct { QRecordHeader header; QInt qf_x; } Other;

#define FIELD(rec, fld) { .name = #fld, .type = &quest_type_Int, .offset = offsetof(rec, qf_##fld), .is_var = false }

static const struct { size_t field_count; const QRecordFieldDescriptor fields[3]; } big_meta = {
    3, { FIELD(Big, a), FIELD(Big, b), FIELD(Big, c) } };
static const struct { size_t field_count; const QRecordFieldDescriptor fields[2]; } mid_meta = {
    2, { FIELD(Mid, b), FIELD(Mid, c) } };
static const struct { size_t field_count; const QRecordFieldDescriptor fields[1]; } other_meta = {
    1, { FIELD(Other, x) } };

#define RECORD_DESC(var, rec, meta_var, nm) static const QTypeDescriptor var = { \
    .kind = QTYPE_KIND_RECORD, .name = nm, .size = sizeof(rec), .alignment = sizeof(void *), \
    .is_subtype = quest_is_subtype, .extra = &meta_var }

RECORD_DESC(big_desc, Big, big_meta, "Record a: Int b: Int c: Int end");
RECORD_DESC(mid_desc, Mid, mid_meta, "Record b: Int c: Int end");
RECORD_DESC(other_desc, Other, other_meta, "Record x: Int end");

/* OuterBig = {inner: Big n: Int}, OuterMid = {inner: Mid n: Int}: depth subtypes */
typedef struct { QRecordHeader header; QRecordVal qf_inner; QInt qf_n; } OuterBig;
typedef struct { QRecordHeader header; QRecordVal qf_inner; QInt qf_n; } OuterMid;
static const struct { size_t field_count; const QRecordFieldDescriptor fields[2]; } outer_big_meta = { 2, {
    { .name = "inner", .type = &big_desc, .offset = offsetof(OuterBig, qf_inner), .is_var = false },
    FIELD(OuterBig, n) } };
static const struct { size_t field_count; const QRecordFieldDescriptor fields[2]; } outer_mid_meta = { 2, {
    { .name = "inner", .type = &mid_desc, .offset = offsetof(OuterMid, qf_inner), .is_var = false },
    FIELD(OuterMid, n) } };
RECORD_DESC(outer_big_desc, OuterBig, outer_big_meta, "Record inner: Record a: Int b: Int c: Int end n: Int end");
RECORD_DESC(outer_mid_desc, OuterMid, outer_mid_meta, "Record inner: Record b: Int c: Int end n: Int end");

/* Tuple Big Int and Tuple Mid Int */
typedef struct { QRecordVal _0; QInt _1; } PairBig;
static const struct { size_t element_count; const QTupleElementDescriptor elements[2]; } pair_big_meta = { 2, {
    { .name = NULL, .type = &big_desc, .offset = offsetof(PairBig, _0) },
    { .name = NULL, .type = &quest_type_Int, .offset = offsetof(PairBig, _1) } } };
static const struct { size_t element_count; const QTupleElementDescriptor elements[2]; } pair_mid_meta = { 2, {
    { .name = NULL, .type = &mid_desc, .offset = offsetof(PairBig, _0) },
    { .name = NULL, .type = &quest_type_Int, .offset = offsetof(PairBig, _1) } } };
static const QTypeDescriptor pair_big_desc = { .kind = QTYPE_KIND_TUPLE, .name = "Tuple :Big :Int end",
    .size = sizeof(PairBig), .alignment = sizeof(void *), .is_subtype = quest_is_subtype, .extra = &pair_big_meta };
static const QTypeDescriptor pair_mid_desc = { .kind = QTYPE_KIND_TUPLE, .name = "Tuple :Mid :Int end",
    .size = sizeof(PairBig), .alignment = sizeof(void *), .is_subtype = quest_is_subtype, .extra = &pair_mid_meta };

static Big *new_big(void) {
    Big *b = (Big *)quest_alloc(sizeof(Big));
    b->header.descriptor = &big_desc;
    b->qf_a = 1; b->qf_b = 2; b->qf_c = 3;
    return b;
}
"""


class TestRecordDicts(unittest.TestCase):

    def run_c(self, body: str) -> str:
        source = PRELUDE + "\nint main(void) {\n    quest_gc_init();\n" + body + "\n    puts(\"OK\");\n    return 0;\n}\n"
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "test_bin"
            compile_c_source(source, output_path=binary)
            proc = run_binary(binary)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def test_tables_are_built_from_descriptors_and_cached(self) -> None:
        self.assertIn("OK", self.run_c(r"""
    const size_t *d = (const size_t *)quest_record_dict(&mid_desc, &big_desc);
    assert(d != NULL);
    assert(d[0] == offsetof(Big, qf_b) && d[1] == offsetof(Big, qf_c));
    assert(quest_record_dict(&mid_desc, &big_desc) == d);
    const size_t *self_dict = (const size_t *)quest_record_dict(&big_desc, &big_desc);
    assert(self_dict[0] == offsetof(Big, qf_a) && self_dict[2] == offsetof(Big, qf_c));
"""))

    def test_registered_tables_are_returned(self) -> None:
        self.assertIn("OK", self.run_c(r"""
    static const size_t mid_of_big[2] = { offsetof(Big, qf_b), offsetof(Big, qf_c) };
    quest_register_record_dict(&mid_desc, &big_desc, mid_of_big);
    assert(quest_record_dict(&mid_desc, &big_desc) == (const void *)mid_of_big);
    /* A later registration does not replace a table already in the map */
    static const size_t again[2] = { offsetof(Big, qf_b), offsetof(Big, qf_c) };
    quest_register_record_dict(&mid_desc, &big_desc, again);
    assert(quest_record_dict(&mid_desc, &big_desc) == (const void *)mid_of_big);
"""))

    def test_no_table_when_layout_lacks_a_view_field(self) -> None:
        self.assertIn("OK", self.run_c(r"""
    assert(quest_record_dict(&big_desc, &mid_desc) == NULL);
    assert(quest_record_dict(&other_desc, &big_desc) == NULL);
    assert(quest_record_dict(&quest_type_Int, &big_desc) == NULL);
    assert(quest_record_dict(NULL, &big_desc) == NULL);
"""))

    def test_many_keys_survive_growth(self) -> None:
        self.assertIn("OK", self.run_c(r"""
    /* Distinct descriptor copies make distinct keys with equal tables */
    enum { N = 500 };
    QTypeDescriptor *views = (QTypeDescriptor *)quest_alloc(sizeof(QTypeDescriptor) * N);
    const void *dicts[N];
    for (int i = 0; i < N; ++i) {
        views[i] = mid_desc;
        dicts[i] = quest_record_dict(&views[i], &big_desc);
        assert(dicts[i] != NULL);
    }
    for (int i = 0; i < N; ++i) {
        assert(quest_record_dict(&views[i], &big_desc) == dicts[i]);
        assert(((const size_t *)dicts[i])[1] == offsetof(Big, qf_c));
    }
"""))

    def test_record_layout_reads_the_header(self) -> None:
        self.assertIn("OK", self.run_c(r"""
    Big *payload = (Big *)quest_alloc(sizeof(Big));
    payload->header.descriptor = &big_desc;
    QRecordVal r = { .val = payload, .dict = quest_record_dict(&mid_desc, &big_desc) };
    assert(quest_record_layout(r) == &big_desc);
"""))

    def test_tables_note_fields_stored_at_a_subtype(self) -> None:
        self.assertIn("OK", self.run_c(r"""
    /* Same field types: no notes */
    QRecordVal mid_self = { .val = NULL, .dict = quest_record_dict(&mid_desc, &big_desc) };
    assert(quest_record_stored_types(mid_self, 2) == NULL);
    /* OuterMid viewing an OuterBig payload: field inner (index 0) is stored as Big */
    OuterBig *o = (OuterBig *)quest_alloc(sizeof(OuterBig));
    o->header.descriptor = &outer_big_desc;
    o->qf_inner = (QRecordVal){ .val = new_big(), .dict = quest_record_dict(&big_desc, &big_desc) };
    o->qf_n = 7;
    QRecordVal viewed = quest_record_view(
        (QRecordVal){ .val = o, .dict = quest_record_dict(&outer_big_desc, &outer_big_desc) }, &outer_mid_desc);
    QRecordStoredTypes stored = quest_record_stored_types(viewed, 2);
    assert(stored != NULL && stored[0] == &big_desc && stored[1] == NULL);
    /* Reading the field converts it to its view at Mid */
    QRecordVal inner = *(const QRecordVal *)quest_record_field_value(viewed, &outer_mid_desc, 0).p;
    assert(*(const QInt *)((const char *)inner.val + quest_record_field_offset(inner, 1)) == 3);
    assert(quest_record_field_value(viewed, &outer_mid_desc, 1).i == 7);
"""))

    def test_convert_copies_tuples_with_converted_elements(self) -> None:
        self.assertIn("OK", self.run_c(r"""
    PairBig *pair = (PairBig *)quest_alloc(sizeof(PairBig));
    pair->_0 = (QRecordVal){ .val = new_big(), .dict = quest_record_dict(&big_desc, &big_desc) };
    pair->_1 = 5;
    PairBig *converted = (PairBig *)quest_convert((QVal){ .p = pair }, &pair_big_desc, &pair_mid_desc).p;
    assert(converted != pair && converted->_1 == 5);
    assert(converted->_0.dict == quest_record_dict(&mid_desc, &big_desc));
    /* Converting between equal descriptors leaves the value alone */
    assert(quest_convert((QVal){ .p = pair }, &pair_big_desc, &pair_big_desc).p == pair);
"""))


if __name__ == "__main__":
    unittest.main()
