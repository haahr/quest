"""Unit tests for Phase 4.8a: C Runtime Type Descriptors, Interning, and Dynamic Operations."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure bootstrap/python is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.codegen.compiler_runner import compile_c_source, run_binary


class TestRuntimeDescriptors(unittest.TestCase):
    """Tests QTypeDescriptor static allocation, interning table, and dynamic operations."""

    def compile_and_run_c(self, c_code: str, nogc: bool = False) -> subprocess.CompletedProcess[str]:
        with tempfile.NamedTemporaryFile(suffix="", delete=False) as f:
            bin_path = Path(f.name)

        try:
            compile_c_source(c_code, output_path=bin_path, nogc=nogc)
            proc = run_binary(bin_path)
            return proc
        finally:
            if bin_path.exists():
                bin_path.unlink()

    def test_base_type_descriptors(self):
        """Tests that base type descriptors exist, have correct names/sizes, and can be interned."""
        c_code = """
        #include "quest_runtime.h"
        #include <assert.h>
        #include <stdio.h>

        int main(void) {
            quest_gc_init();

            /* Check pre-allocated static descriptors */
            assert(quest_type_Int.kind == QTYPE_KIND_INT);
            assert(strcmp(quest_type_Int.name, "Int") == 0);
            assert(quest_type_Int.size == sizeof(QInt));

            assert(quest_type_Real.kind == QTYPE_KIND_REAL);
            assert(strcmp(quest_type_Real.name, "Real") == 0);

            assert(quest_type_Bool.kind == QTYPE_KIND_BOOL);
            assert(strcmp(quest_type_Bool.name, "Bool") == 0);

            assert(quest_type_Char.kind == QTYPE_KIND_CHAR);
            assert(strcmp(quest_type_Char.name, "Char") == 0);

            assert(quest_type_String.kind == QTYPE_KIND_STRING);
            assert(strcmp(quest_type_String.name, "String") == 0);

            assert(quest_type_Ok.kind == QTYPE_KIND_OK);
            assert(strcmp(quest_type_Ok.name, "Ok") == 0);


            assert(quest_type_EmptyTuple.kind == QTYPE_KIND_TUPLE);
            assert(strcmp(quest_type_EmptyTuple.name, "Tuple end") == 0);

            /* Check interning of base descriptors returns the same static pointer */
            const QTypeDescriptor *d_int = quest_intern_type_descriptor(&quest_type_Int);
            assert(d_int == &quest_type_Int);

            /* Subtyping: Int <: Int, but Tuple end is a supertype only of tuples */
            assert(quest_type_Int.is_subtype(&quest_type_Int, &quest_type_Int));
            assert(!quest_type_Int.is_subtype(&quest_type_Int, &quest_type_EmptyTuple));
            assert(!quest_type_Int.is_subtype(&quest_type_Int, &quest_type_Real));

            printf("BASE_DESCRIPTORS_OK\\n");
            return 0;
        }
        """
        proc = self.compile_and_run_c(c_code)
        self.assertEqual(proc.returncode, 0, f"Failed: {proc.stderr}")
        self.assertIn("BASE_DESCRIPTORS_OK", proc.stdout)

    def test_array_descriptor_interning(self):
        """Tests that array descriptors are memoized such that Array(Int) == Array(Int)."""
        c_code = """
        #include "quest_runtime.h"
        #include <assert.h>
        #include <stdio.h>

        int main(void) {
            quest_gc_init();

            const QTypeDescriptor *arr1 = quest_make_array_descriptor(&quest_type_Int);
            const QTypeDescriptor *arr2 = quest_make_array_descriptor(&quest_type_Int);
            const QTypeDescriptor *arr_str = quest_make_array_descriptor(&quest_type_String);

            assert(arr1 != NULL);
            assert(arr2 != NULL);
            /* Canonical pointer equality check */
            assert(arr1 == arr2);
            assert(arr1 != arr_str);

            assert(arr1->kind == QTYPE_KIND_ARRAY);
            assert(strcmp(arr1->name, "Array(Int)") == 0);
            assert(strcmp(arr_str->name, "Array(String)") == 0);

            /* Nested array: Array(Array(Int)) */
            const QTypeDescriptor *nested1 = quest_make_array_descriptor(arr1);
            const QTypeDescriptor *nested2 = quest_make_array_descriptor(arr2);
            assert(nested1 == nested2);
            assert(strcmp(nested1->name, "Array(Array(Int))") == 0);

            /* Subtyping checks */
            assert(arr1->is_subtype(arr1, arr1));
            assert(!arr1->is_subtype(arr1, &quest_type_EmptyTuple));
            assert(!arr1->is_subtype(arr1, arr_str));

            printf("ARRAY_INTERN_OK\\n");
            return 0;
        }
        """
        proc = self.compile_and_run_c(c_code)
        self.assertEqual(proc.returncode, 0, f"Failed: {proc.stderr}")
        self.assertIn("ARRAY_INTERN_OK", proc.stdout)

    def test_opaque_descriptor_identity(self):
        """Tests that opaque type descriptors have nominal identity (never equal even with same name)."""
        c_code = """
        #include "quest_runtime.h"
        #include <assert.h>
        #include <stdio.h>

        int main(void) {
            quest_gc_init();

            const QTypeDescriptor *t1 = quest_make_opaque_descriptor("T");
            const QTypeDescriptor *t2 = quest_make_opaque_descriptor("T");

            assert(t1 != NULL);
            assert(t2 != NULL);
            assert(t1 != t2); /* Unique nominal pointer identity */
            assert(strcmp(t1->name, "T") == 0);
            assert(strcmp(t2->name, "T") == 0);
            assert(t1->kind == QTYPE_KIND_OPAQUE);

            printf("OPAQUE_IDENTITY_OK\\n");
            return 0;
        }
        """
        proc = self.compile_and_run_c(c_code)
        self.assertEqual(proc.returncode, 0, f"Failed: {proc.stderr}")
        self.assertIn("OPAQUE_IDENTITY_OK", proc.stdout)

    def test_auto_value_and_conversion_success(self):
        """Tests packaging a value as an auto value and converting it at a matching descriptor (as dynamic.be does)."""
        c_code = """
        #include "quest_runtime.h"
        #include <assert.h>
        #include <stdio.h>

        int main(void) {
            quest_gc_init();

            /* A dynamic value's one component is stored as a QVal */
            QVal *component = (QVal *)quest_alloc(sizeof(QVal));
            component->i = 42LL;
            QAuto *d = quest_auto_new(&quest_type_Int, (QVal){ .p = component });
            assert(d != NULL);
            assert(d->type_desc == &quest_type_Int);
            assert(((QVal *)d->payload.p)->i == 42LL);

            /* dynamic.be(:Int d): the type component is a subtype, and the value converts unchanged */
            assert(quest_is_subtype(d->type_desc, &quest_type_Int));
            QVal extracted = quest_convert(*(QVal *)d->payload.p, d->type_desc, &quest_type_Int);
            assert(extracted.i == 42LL);

            /* An Int is not a tuple, so it cannot be extracted at Tuple end (that raises dynamic.error) */
            assert(!quest_is_subtype(&quest_type_Int, &quest_type_EmptyTuple));

            printf("DYNAMIC_SUCCESS_OK\\n");
            return 0;
        }
        """
        proc = self.compile_and_run_c(c_code)
        self.assertEqual(proc.returncode, 0, f"Failed: {proc.stderr}")
        self.assertIn("DYNAMIC_SUCCESS_OK", proc.stdout)

    def test_conversion_failure_raises_dynamic_error(self):
        """Tests that a record conversion raises quest_exc_dynamic_error when the layout lacks a field of the view."""
        c_code = """
        #include "quest_runtime.h"
        #include <assert.h>
        #include <stdio.h>

        int main(void) {
            quest_gc_init();

            /* A record payload whose layout lacks the field y of the record type it is converted to */
            struct Rx { QRecordHeader header; int64_t qf_x; };
            struct Ry { QRecordHeader header; int64_t qf_y; };
            QRecordFieldDescriptor x_fields[] = {
                { .name = "x", .type = &quest_type_Int, .offset = offsetof(struct Rx, qf_x), .is_var = false } };
            QRecordFieldDescriptor y_fields[] = {
                { .name = "y", .type = &quest_type_Int, .offset = offsetof(struct Ry, qf_y), .is_var = false } };
            const QTypeDescriptor *x_desc = quest_make_record_descriptor("Record x: Int end", sizeof(struct Rx), 8, 1, x_fields);
            const QTypeDescriptor *y_desc = quest_make_record_descriptor("Record y: Int end", sizeof(struct Ry), 8, 1, y_fields);
            struct Rx *payload = (struct Rx *)quest_alloc(sizeof(struct Rx));
            payload->header.descriptor = x_desc;
            QRecordVal rec = { .val = payload, .dict = quest_record_dict(x_desc, x_desc) };

            QExceptionHandler handler;
            handler.prev = quest_current_exception_handler;
            quest_current_exception_handler = &handler;

            if (setjmp(handler.env_jmp) == 0) {
                /* Converting it to Record y: Int end must fail */
                quest_convert((QVal){ .p = quest_record_box(rec) }, x_desc, y_desc);
                printf("UNREACHABLE\\n");
                return 1;
            } else {
                /* Exception caught! Verify it is quest_exc_dynamic_error */
                quest_current_exception_handler = handler.prev;
                assert(quest_current_exception.exc == &quest_exc_dynamic_error);
                assert(strcmp(quest_current_exception.exc->name, "dynamic.error") == 0);
                printf("DYNAMIC_ERROR_CAUGHT_OK\\n");
                return 0;
            }
        }
        """
        proc = self.compile_and_run_c(c_code)
        self.assertEqual(proc.returncode, 0, f"Failed: {proc.stderr}")
        self.assertIn("DYNAMIC_ERROR_CAUGHT_OK", proc.stdout)

    def test_compound_record_subtyping_and_adaptation(self):
        """Tests record width/depth subtyping and dynamic dictionary synthesis."""
        c_code = """
        #include "quest_runtime.h"
        #include <assert.h>
        #include <stdio.h>

        /* Big record: { x: Int, y: Int, z: Int } */
        struct BigRec {
            QRecordHeader header;
            int64_t qf_x;
            int64_t qf_y;
            int64_t qf_z;
        };
        /* Small record: { y: Int } */
        struct SmallRec {
            QRecordHeader header;
            int64_t qf_y;
        };

        /* Offset dict for SmallRec */
        struct DictSmall {
            size_t offset_y;
        };

        int main(void) {
            quest_gc_init();

            QRecordFieldDescriptor big_fields[] = {
                { .name = "x", .type = &quest_type_Int, .offset = offsetof(struct BigRec, qf_x), .is_var = false },
                { .name = "y", .type = &quest_type_Int, .offset = offsetof(struct BigRec, qf_y), .is_var = false },
                { .name = "z", .type = &quest_type_Int, .offset = offsetof(struct BigRec, qf_z), .is_var = false }
            };
            const QTypeDescriptor *big_desc = quest_make_record_descriptor(
                "Record x: Int y: Int z: Int end", sizeof(struct BigRec), 8, 3, big_fields);

            QRecordFieldDescriptor small_fields[] = {
                { .name = "y", .type = &quest_type_Int, .offset = offsetof(struct SmallRec, qf_y), .is_var = false }
            };
            const QTypeDescriptor *small_desc = quest_make_record_descriptor(
                "Record y: Int end", sizeof(struct SmallRec), 8, 1, small_fields);

            /* Subtyping: big <: small, but NOT small <: big */
            assert(quest_is_subtype(big_desc, small_desc));
            assert(!quest_is_subtype(small_desc, big_desc));

            /* Allocate big record payload */
            struct BigRec *b = (struct BigRec *)quest_alloc(sizeof(struct BigRec));
            b->header.descriptor = big_desc;
            b->qf_x = 100;
            b->qf_y = 200;
            b->qf_z = 300;

            QRecordVal r_big = { .val = b, .dict = NULL };

            /* Convert to SmallRec, as dynamic.be does */
            assert(quest_is_subtype(big_desc, small_desc));
            QVal extracted = quest_convert((QVal){ .p = quest_record_box(r_big) }, big_desc, small_desc);
            QRecordVal *r_small = (QRecordVal *)extracted.p;
            assert(r_small != NULL);

            /* Check that dictionary correctly mapped 'y' offset to BigRec.qf_y */
            const struct DictSmall *dict = (const struct DictSmall *)r_small->dict;
            assert(dict->offset_y == offsetof(struct BigRec, qf_y));

            int64_t val_y = *(int64_t *)((char *)r_small->val + dict->offset_y);
            assert(val_y == 200);

            printf("RECORD_SUBTYPING_OK\\n");
            return 0;
        }
        """
        proc = self.compile_and_run_c(c_code)
        self.assertEqual(proc.returncode, 0, f"Failed: {proc.stderr}")
        self.assertIn("RECORD_SUBTYPING_OK", proc.stdout)

    def test_compound_variant_subtyping_and_adaptation(self):
        """Tests variant subtyping and dynamic tag remapping."""
        c_code = """
        #include "quest_runtime.h"
        #include <assert.h>
        #include <stdio.h>

        int main(void) {
            quest_gc_init();

            /* Subvariant: Option b end (case count 1, tag 'b' = 0) */
            QVariantCaseDescriptor sub_cases[] = {
                { .name = "b", .payload_type = NULL, .tag_index = 0, .is_var = false }
            };
            const QTypeDescriptor *sub_desc = quest_make_variant_descriptor(
                "Option b end", sizeof(QVariantVal), 8, 1, sub_cases);

            /* Supervariant: Option a b c end (tag 'a' = 0, 'b' = 1, 'c' = 2) */
            QVariantCaseDescriptor super_cases[] = {
                { .name = "a", .payload_type = NULL, .tag_index = 0, .is_var = false },
                { .name = "b", .payload_type = NULL, .tag_index = 1, .is_var = false },
                { .name = "c", .payload_type = NULL, .tag_index = 2, .is_var = false }
            };
            const QTypeDescriptor *super_desc = quest_make_variant_descriptor(
                "Option a b c end", sizeof(QVariantVal), 8, 3, super_cases);

            /* Subtyping: sub <: super (fewer cases is subtype of more cases) */
            assert(quest_is_subtype(sub_desc, super_desc));
            assert(!quest_is_subtype(super_desc, sub_desc));

            /* Create variant 'b' with local tag 0 */
            QVariantVal v = { .tag = 0, .payload = (QVal){ .u = 0 } };
            /* Convert to the supervariant, as dynamic.be does */
            QVal extracted = quest_convert((QVal){ .p = quest_variant_box(v) }, sub_desc, super_desc);
            QVariantVal *res_v = (QVariantVal *)extracted.p;
            assert(res_v != NULL);
            /* Tag must be remapped from 0 to 1! */
            assert(res_v->tag == 1);

            printf("VARIANT_SUBTYPING_OK\\n");
            return 0;
        }
        """
        proc = self.compile_and_run_c(c_code)
        self.assertEqual(proc.returncode, 0, f"Failed: {proc.stderr}")
        self.assertIn("VARIANT_SUBTYPING_OK", proc.stdout)


    def test_templates_instances_and_layout_conversion(self):
        """Templates are instantiated at run time; instances describe generic layouts, which convert to native ones."""
        c_code = """
        #include "quest_runtime.h"
        #include <assert.h>
        #include <stdio.h>

        /* Tuple fst: A snd: Int end as generic code lays it out, and Tuple fst: Real snd: Int end natively */
        typedef struct { QVal _0; QInt _1; } Generic;
        typedef struct { QReal _0; QInt _1; } NativeReal;
        typedef struct { QRecordVal _0; QInt _1; } NativeRecord;

        static const QTypeDescriptor hole0 = {
            QTYPE_KIND_HOLE, "?0", sizeof(QVal), sizeof(void *), quest_is_subtype,
            &(const QHoleDescriptor){ .index = 0, .storage = NULL } };
        static const struct { size_t n; QTupleElementDescriptor e[2]; } tmpl_meta = { 2, {
            { "fst", &hole0, offsetof(Generic, _0), false },
            { "snd", &quest_type_Int, offsetof(Generic, _1), false } } };
        static const QTypeDescriptor tmpl = {
            QTYPE_KIND_TUPLE, "Tuple fst: ?0 snd: Int end", sizeof(Generic), sizeof(void *), quest_is_subtype,
            &tmpl_meta };
        static const struct { size_t n; QTupleElementDescriptor e[2]; } real_meta = { 2, {
            { "fst", &quest_type_Real, offsetof(NativeReal, _0), false },
            { "snd", &quest_type_Int, offsetof(NativeReal, _1), false } } };
        static const QTypeDescriptor real_tuple = {
            QTYPE_KIND_TUPLE, "Tuple fst: Real snd: Int end", sizeof(NativeReal), sizeof(void *), quest_is_subtype,
            &real_meta };

        static const struct { size_t n; QRecordFieldDescriptor f[1]; } obj_meta = { 1, {
            { "age", &quest_type_Int, sizeof(QRecordHeader), false } } };
        static const QTypeDescriptor obj = {
            QTYPE_KIND_RECORD, "Record age: Int end", sizeof(QRecordHeader) + sizeof(QInt), sizeof(void *),
            quest_is_subtype, &obj_meta };
        static const struct { size_t n; QTupleElementDescriptor e[2]; } rec_meta = { 2, {
            { "fst", &obj, offsetof(NativeRecord, _0), false },
            { "snd", &quest_type_Int, offsetof(NativeRecord, _1), false } } };
        static const QTypeDescriptor rec_tuple = {
            QTYPE_KIND_TUPLE, "Tuple fst: Record age: Int end snd: Int end", sizeof(NativeRecord), sizeof(void *),
            quest_is_subtype, &rec_meta };

        int main(void) {
            quest_gc_init();

            /* Instances are memoized, and have the type of the native descriptor */
            const QTypeDescriptor *args_real[1] = { &quest_type_Real };
            const QTypeDescriptor *at_real = quest_instantiate_descriptor(&tmpl, 1, args_real);
            assert(at_real == quest_instantiate_descriptor(&tmpl, 1, args_real));
            assert(at_real != &tmpl);
            assert(quest_is_subtype(at_real, &real_tuple) && quest_is_subtype(&real_tuple, at_real));
            const QTupleTypeDescriptor *meta = (const QTupleTypeDescriptor *)at_real->extra;
            assert(meta->elements[0].type->kind == QTYPE_KIND_STORED);
            assert(quest_stored_type(meta->elements[0].type) == &quest_type_Real);
            assert(meta->elements[1].type == &quest_type_Int);

            /* A Real stored as a QVal is laid out as a native Real: the value is used as it is */
            assert(quest_layout_equivalent(at_real, &real_tuple));
            Generic *g = (Generic *)quest_alloc(sizeof(Generic));
            g->_0 = (QVal){ .r = 2.5 };
            g->_1 = 7;
            QVal same = quest_convert((QVal){ .p = g }, at_real, &real_tuple);
            assert(same.p == g);
            assert(((NativeReal *)same.p)->_0 == 2.5);

            /* A record stored as a QVal (a boxed QRecordVal) is not: the tuple is copied, the record unboxed */
            const QTypeDescriptor *args_obj[1] = { &obj };
            const QTypeDescriptor *at_obj = quest_instantiate_descriptor(&tmpl, 1, args_obj);
            assert(!quest_layout_equivalent(at_obj, &rec_tuple));
            void *payload = quest_alloc(sizeof(QRecordHeader) + sizeof(QInt));
            ((QRecordHeader *)payload)->descriptor = &obj;
            *(QInt *)((char *)payload + sizeof(QRecordHeader)) = 42;
            QRecordVal r = quest_record_view((QRecordVal){ .val = payload, .dict = NULL }, &obj);
            Generic *h = (Generic *)quest_alloc(sizeof(Generic));
            h->_0 = (QVal){ .p = quest_record_box(r) };
            h->_1 = 3;
            QVal native = quest_convert((QVal){ .p = h }, at_obj, &rec_tuple);
            assert(native.p != h);
            NativeRecord *n = (NativeRecord *)native.p;
            assert(n->_1 == 3);
            assert(*(QInt *)((char *)n->_0.val + quest_record_field_offset(n->_0, 0)) == 42);

            printf("OK\\n");
            return 0;
        }
        """
        proc = self.compile_and_run_c(c_code)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)

if __name__ == "__main__":
    unittest.main()

