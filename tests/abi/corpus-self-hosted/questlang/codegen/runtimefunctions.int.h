#ifndef QUEST_INTF_QUESTLANG__CODEGEN__RUNTIMEFUNCTIONS_H
#define QUEST_INTF_QUESTLANG__CODEGEN__RUNTIMEFUNCTIONS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/ssa/nodes.int.h"
#ifndef QUEST_TYPE_QOption_memoryNone_memoryReads_memoryWrites_TYPEDEF
#define QUEST_TYPE_QOption_memoryNone_memoryReads_memoryWrites_TYPEDEF
typedef struct QOption_memoryNone_memoryReads_memoryWrites QOption_memoryNone_memoryReads_memoryWrites;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_memoryNon_f53d08940a7f9418_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_memoryNon_f53d08940a7f9418_TYPEDEF
typedef struct QTuple_QOption_memoryNon_f53d08940a7f9418 QTuple_QOption_memoryNon_f53d08940a7f9418;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QAr_e2330c20843b42b1_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_QAr_e2330c20843b42b1_TYPEDEF
typedef struct QTuple_String_String_QAr_e2330c20843b42b1 QTuple_String_String_QAr_e2330c20843b42b1;
#endif
#ifndef QUEST_TYPE_QTuple_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_TYPEDEF
typedef struct QTuple_Int QTuple_Int;
#endif
#ifndef QUEST_TYPE_QOption_passByte_passInt_cafeff5ade35f658_TYPEDEF
#define QUEST_TYPE_QOption_passByte_passInt_cafeff5ade35f658_TYPEDEF
typedef struct QOption_passByte_passInt_cafeff5ade35f658 QOption_passByte_passInt_cafeff5ade35f658;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QOption_pa_88eba21d06adf8d8_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QOption_pa_88eba21d06adf8d8_TYPEDEF
typedef struct QTuple_QArray_QOption_pa_88eba21d06adf8d8 QTuple_QArray_QOption_pa_88eba21d06adf8d8;
#endif
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_TYPEDEF
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_TYPEDEF
typedef struct QOption_typeInt_typePtr_typeReal_typeVal QOption_typeInt_typePtr_typeReal_typeVal;
#endif
#ifndef QUEST_TYPE_QOption_memoryNone_memoryReads_memoryWrites_DEFINED
#define QUEST_TYPE_QOption_memoryNone_memoryReads_memoryWrites_DEFINED
struct QOption_memoryNone_memoryReads_memoryWrites {
    int64_t tag;
};
static_assert(sizeof(struct QOption_memoryNone_memoryReads_memoryWrites) == 8, layout_QOption_memoryNone_memoryReads_memoryWrites_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_memoryNon_f53d08940a7f9418_DEFINED
#define QUEST_TYPE_QTuple_QOption_memoryNon_f53d08940a7f9418_DEFINED
struct QTuple_QOption_memoryNon_f53d08940a7f9418 {
    QOption_memoryNone_memoryReads_memoryWrites * _0;
    QBoolSlot _1;
    QBoolSlot _2;
    QBoolSlot _3;
};
static_assert(offsetof(struct QTuple_QOption_memoryNon_f53d08940a7f9418, _0) == 0, layout_QTuple_QOption_memoryNon_f53d08940a7f9418__0);
static_assert(offsetof(struct QTuple_QOption_memoryNon_f53d08940a7f9418, _1) == 8, layout_QTuple_QOption_memoryNon_f53d08940a7f9418__1);
static_assert(offsetof(struct QTuple_QOption_memoryNon_f53d08940a7f9418, _2) == 16, layout_QTuple_QOption_memoryNon_f53d08940a7f9418__2);
static_assert(offsetof(struct QTuple_QOption_memoryNon_f53d08940a7f9418, _3) == 24, layout_QTuple_QOption_memoryNon_f53d08940a7f9418__3);
static_assert(sizeof(struct QTuple_QOption_memoryNon_f53d08940a7f9418) == 32, layout_QTuple_QOption_memoryNon_f53d08940a7f9418_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QAr_e2330c20843b42b1_DEFINED
#define QUEST_TYPE_QTuple_String_String_QAr_e2330c20843b42b1_DEFINED
struct QTuple_String_String_QAr_e2330c20843b42b1 {
    QString * _0;
    QString * _1;
    QArray * _2;
    QTuple_QOption_memoryNon_f53d08940a7f9418 * _3;
};
static_assert(offsetof(struct QTuple_String_String_QAr_e2330c20843b42b1, _0) == 0, layout_QTuple_String_String_QAr_e2330c20843b42b1__0);
static_assert(offsetof(struct QTuple_String_String_QAr_e2330c20843b42b1, _1) == 8, layout_QTuple_String_String_QAr_e2330c20843b42b1__1);
static_assert(offsetof(struct QTuple_String_String_QAr_e2330c20843b42b1, _2) == 16, layout_QTuple_String_String_QAr_e2330c20843b42b1__2);
static_assert(offsetof(struct QTuple_String_String_QAr_e2330c20843b42b1, _3) == 24, layout_QTuple_String_String_QAr_e2330c20843b42b1__3);
static_assert(sizeof(struct QTuple_String_String_QAr_e2330c20843b42b1) == 32, layout_QTuple_String_String_QAr_e2330c20843b42b1_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_DEFINED
struct QTuple_Int {
    QInt _0;
};
static_assert(offsetof(struct QTuple_Int, _0) == 0, layout_QTuple_Int__0);
static_assert(sizeof(struct QTuple_Int) == 8, layout_QTuple_Int_size);
#endif
#ifndef QUEST_TYPE_QOption_passByte_passInt_cafeff5ade35f658_DEFINED
#define QUEST_TYPE_QOption_passByte_passInt_cafeff5ade35f658_DEFINED
struct QOption_passByte_passInt_cafeff5ade35f658 {
    int64_t tag;
    union {
        struct QOption_passByte_passInt_cafeff5ade35f658_passMemory_payload {
            QInt _0;
        } qo_passMemory;
    } u;
};
static_assert(offsetof(struct QOption_passByte_passInt_cafeff5ade35f658, u.qo_passMemory._0) == 8, layout_QOption_passByte_passInt_cafeff5ade35f658_u_qo_passMemory__0);
static_assert(sizeof(struct QOption_passByte_passInt_cafeff5ade35f658) == 16, layout_QOption_passByte_passInt_cafeff5ade35f658_size);
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QOption_pa_88eba21d06adf8d8_DEFINED
#define QUEST_TYPE_QTuple_QArray_QOption_pa_88eba21d06adf8d8_DEFINED
struct QTuple_QArray_QOption_pa_88eba21d06adf8d8 {
    QArray * _0;
    QArray * _1;
};
static_assert(offsetof(struct QTuple_QArray_QOption_pa_88eba21d06adf8d8, _0) == 0, layout_QTuple_QArray_QOption_pa_88eba21d06adf8d8__0);
static_assert(offsetof(struct QTuple_QArray_QOption_pa_88eba21d06adf8d8, _1) == 8, layout_QTuple_QArray_QOption_pa_88eba21d06adf8d8__1);
static_assert(sizeof(struct QTuple_QArray_QOption_pa_88eba21d06adf8d8) == 16, layout_QTuple_QArray_QOption_pa_88eba21d06adf8d8_size);
#endif
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
struct QOption_typeInt_typePtr_typeReal_typeVal {
    int64_t tag;
};
static_assert(sizeof(struct QOption_typeInt_typePtr_typeReal_typeVal) == 8, layout_QOption_typeInt_typePtr_typeReal_typeVal_size);
#endif
typedef QOption_memoryNone_memoryReads_memoryWrites * quest_type_questlang__codegen__RuntimeFunctions_Memory;
typedef QTuple_QOption_memoryNon_f53d08940a7f9418 * quest_type_questlang__codegen__RuntimeFunctions_Effects;
typedef QTuple_String_String_QAr_e2330c20843b42b1 * quest_type_questlang__codegen__RuntimeFunctions_Function;
typedef QArray * quest_sig_questlang__codegen__RuntimeFunctions_functions;
typedef const QException * quest_sig_questlang__codegen__RuntimeFunctions_unknown;
typedef QTuple_String_String_QAr_e2330c20843b42b1 * (*quest_sig_questlang__codegen__RuntimeFunctions_function)(QString * name);
typedef QBool (*quest_sig_questlang__codegen__RuntimeFunctions_isPure)(QTuple_String_String_QAr_e2330c20843b42b1 * f);
typedef QTuple_QArray_QOption_pa_88eba21d06adf8d8 * (*quest_sig_questlang__codegen__RuntimeFunctions_signature)(QTuple_String_String_QAr_e2330c20843b42b1 * f);
typedef QArray * (*quest_sig_questlang__codegen__RuntimeFunctions_paramTypes)(QTuple_String_String_QAr_e2330c20843b42b1 * f);
typedef QArray * (*quest_sig_questlang__codegen__RuntimeFunctions_resultTypes)(QTuple_String_String_QAr_e2330c20843b42b1 * f);
#ifdef __cplusplus
}
#endif
#endif
