#ifndef QUEST_INTF_QUESTLANG__CODEGEN__ARM64__CODEGEN_H
#define QUEST_INTF_QUESTLANG__CODEGEN__ARM64__CODEGEN_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/ssa/nodes.int.h"
#include "questlang/codegen/arm64/minst.int.h"
#include "questlang/codegen/arm64/encode.int.h"
#include "collections/vector.int.h"
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QTuple_Int_Int_QVal_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_QVal_Int_TYPEDEF
typedef struct QTuple_Int_Int_QVal_Int QTuple_Int_Int_QVal_Int;
#endif
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_TYPEDEF
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_TYPEDEF
typedef struct QOption_typeInt_typePtr_typeReal_typeVal QOption_typeInt_typePtr_typeReal_typeVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QVal QTuple_QVal_QVal_QVal;
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
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_Int_TYPEDEF
typedef struct QTuple_Int_Int_Int QTuple_Int_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_String_Bool_QVal__2ce49d2a84d5590a_TYPEDEF
#define QUEST_TYPE_QTuple_String_Bool_QVal__2ce49d2a84d5590a_TYPEDEF
typedef struct QTuple_String_Bool_QVal__2ce49d2a84d5590a QTuple_String_Bool_QVal__2ce49d2a84d5590a;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QArray_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QArray_Int_TYPEDEF
typedef struct QTuple_Int_QArray_Int QTuple_Int_QArray_Int;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end_TYPEDEF
typedef struct QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_QArray_Int_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_Int_QArray_Int_end_TYPEDEF
typedef struct QTuple_QTuple_Int_QArray_Int_end QTuple_QTuple_Int_QArray_Int_end;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_Int_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_Int_TYPEDEF
typedef struct QTuple_QArray_Int QTuple_QArray_Int;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48_TYPEDEF
typedef struct QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48 QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48;
#endif
#ifndef QUEST_TYPE_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_TYPEDEF
#define QUEST_TYPE_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_TYPEDEF
typedef struct QOption_opAdd_opAnd_opAs_0293d61f8c93e36e QOption_opAdd_opAnd_opAs_0293d61f8c93e36e;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_opAdd_opA_c80de261989503a7_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_opAdd_opA_c80de261989503a7_TYPEDEF
typedef struct QTuple_QOption_opAdd_opA_c80de261989503a7 QTuple_QOption_opAdd_opA_c80de261989503a7;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end_TYPEDEF
typedef struct QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_Int_TYPEDEF
typedef struct QTuple_Int_QTuple_Int_QArray_Int_end_Int QTuple_Int_QTuple_Int_QArray_Int_end_Int;
#endif
#ifndef QUEST_TYPE_QOption_termBranch_QTupl_fb14070ded119ae8_TYPEDEF
#define QUEST_TYPE_QOption_termBranch_QTupl_fb14070ded119ae8_TYPEDEF
typedef struct QOption_termBranch_QTupl_fb14070ded119ae8 QOption_termBranch_QTupl_fb14070ded119ae8;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QOption_419977b801e61011_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QOption_419977b801e61011_TYPEDEF
typedef struct QTuple_QVal_QVal_QOption_419977b801e61011 QTuple_QVal_QVal_QOption_419977b801e61011;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_TYPEDEF
typedef struct QTuple_Int_Int QTuple_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_TYPEDEF
typedef struct QTuple_String QTuple_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_TYPEDEF
typedef struct QTuple_String_Int QTuple_String_Int;
#endif
#ifndef QUEST_TYPE_QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_TYPEDEF
#define QUEST_TYPE_QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_TYPEDEF
typedef struct QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5_TYPEDEF
typedef struct QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5 QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5;
#endif
#ifndef QUEST_TYPE_QOption_contentsText_QTu_6bf31e28bb3b7166_TYPEDEF
#define QUEST_TYPE_QOption_contentsText_QTu_6bf31e28bb3b7166_TYPEDEF
typedef struct QOption_contentsText_QTu_6bf31e28bb3b7166 QOption_contentsText_QTu_6bf31e28bb3b7166;
#endif
#ifndef QUEST_TYPE_QTuple_String_Bool_Bool__330533165c015005_TYPEDEF
#define QUEST_TYPE_QTuple_String_Bool_Bool__330533165c015005_TYPEDEF
typedef struct QTuple_String_Bool_Bool__330533165c015005 QTuple_String_Bool_Bool__330533165c015005;
#endif
#ifndef QUEST_TYPE_QOption_relocAbsolute64__44c66b1db190bdc3_TYPEDEF
#define QUEST_TYPE_QOption_relocAbsolute64__44c66b1db190bdc3_TYPEDEF
typedef struct QOption_relocAbsolute64__44c66b1db190bdc3 QOption_relocAbsolute64__44c66b1db190bdc3;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QOption_reloc_9c145bed7730d35a_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QOption_reloc_9c145bed7730d35a_TYPEDEF
typedef struct QTuple_Int_QOption_reloc_9c145bed7730d35a QTuple_Int_QOption_reloc_9c145bed7730d35a;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_Bool_TYPEDEF
typedef struct QTuple_String_Int_Int_Bool QTuple_String_Int_Int_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_Int_Int_TYPEDEF
typedef struct QTuple_Int_Int_Int_Int QTuple_Int_Int_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_Int_QArray_f0593bc63ece5e04_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_Int_QArray_f0593bc63ece5e04_TYPEDEF
typedef struct QTuple_QArray_Int_QArray_f0593bc63ece5e04 QTuple_QArray_Int_QArray_f0593bc63ece5e04;
#endif
#ifndef QUEST_TYPE_QOption_relocGot_relocPage_relocTlv_TYPEDEF
#define QUEST_TYPE_QOption_relocGot_relocPage_relocTlv_TYPEDEF
typedef struct QOption_relocGot_relocPage_relocTlv QOption_relocGot_relocPage_relocTlv;
#endif
#ifndef QUEST_TYPE_QTuple_String_QOption_relocGot_relocPage_relocTlv_end_TYPEDEF
#define QUEST_TYPE_QTuple_String_QOption_relocGot_relocPage_relocTlv_end_TYPEDEF
typedef struct QTuple_String_QOption_relocGot_relocPage_relocTlv_end QTuple_String_QOption_relocGot_relocPage_relocTlv_end;
#endif
#ifndef QUEST_TYPE_QOption_arithAdd_arithAn_c473bdf6463401a5_TYPEDEF
#define QUEST_TYPE_QOption_arithAdd_arithAn_c473bdf6463401a5_TYPEDEF
typedef struct QOption_arithAdd_arithAn_c473bdf6463401a5 QOption_arithAdd_arithAn_c473bdf6463401a5;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_TYPEDEF
typedef struct QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end;
#endif
#ifndef QUEST_TYPE_QOption_condEq_condGe_co_eabed1dd4e938ad3_TYPEDEF
#define QUEST_TYPE_QOption_condEq_condGe_co_eabed1dd4e938ad3_TYPEDEF
typedef struct QOption_condEq_condGe_co_eabed1dd4e938ad3 QOption_condEq_condGe_co_eabed1dd4e938ad3;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String_TYPEDEF
typedef struct QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_TYPEDEF
typedef struct QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_TYPEDEF
typedef struct QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_TYPEDEF
typedef struct QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end;
#endif
#ifndef QUEST_TYPE_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_TYPEDEF
#define QUEST_TYPE_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_TYPEDEF
typedef struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f QOption_modeBase_modeInd_c9e05f3a0acd9b8f;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end_TYPEDEF
typedef struct QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end;
#endif
#ifndef QUEST_TYPE_QOption_load64_loadS32_loadS8_loadU8_TYPEDEF
#define QUEST_TYPE_QOption_load64_loadS32_loadS8_loadU8_TYPEDEF
typedef struct QOption_load64_loadS32_loadS8_loadU8 QOption_load64_loadS32_loadS8_loadU8;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4_TYPEDEF
typedef struct QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4 QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int_TYPEDEF
typedef struct QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int;
#endif
#ifndef QUEST_TYPE_QOption_store32_store64_store8_TYPEDEF
#define QUEST_TYPE_QOption_store32_store64_store8_TYPEDEF
typedef struct QOption_store32_store64_store8 QOption_store32_store64_store8;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_store32_s_5bbc7285dc38388c_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_store32_s_5bbc7285dc38388c_TYPEDEF
typedef struct QTuple_QOption_store32_s_5bbc7285dc38388c QTuple_QOption_store32_s_5bbc7285dc38388c;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Bool_TYPEDEF
typedef struct QTuple_String_Int_Bool QTuple_String_Int_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_TYPEDEF
typedef struct QTuple_Int_String QTuple_Int_String;
#endif
#ifndef QUEST_TYPE_QOption_opAddImm_QTuple__31f18ef922269f96_TYPEDEF
#define QUEST_TYPE_QOption_opAddImm_QTuple__31f18ef922269f96_TYPEDEF
typedef struct QOption_opAddImm_QTuple__31f18ef922269f96 QOption_opAddImm_QTuple__31f18ef922269f96;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int_TYPEDEF
typedef struct QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_QVal_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_QVal_Int_DEFINED
struct QTuple_Int_Int_QVal_Int {
    QInt _0;
    QInt _1;
    QVal _2;
    QInt _3;
};
static_assert(offsetof(struct QTuple_Int_Int_QVal_Int, _0) == 0, layout_QTuple_Int_Int_QVal_Int__0);
static_assert(offsetof(struct QTuple_Int_Int_QVal_Int, _1) == 8, layout_QTuple_Int_Int_QVal_Int__1);
static_assert(offsetof(struct QTuple_Int_Int_QVal_Int, _2) == 16, layout_QTuple_Int_Int_QVal_Int__2);
static_assert(offsetof(struct QTuple_Int_Int_QVal_Int, _3) == 24, layout_QTuple_Int_Int_QVal_Int__3);
static_assert(sizeof(struct QTuple_Int_Int_QVal_Int) == 32, layout_QTuple_Int_Int_QVal_Int_size);
#endif
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
struct QOption_typeInt_typePtr_typeReal_typeVal {
    int64_t tag;
};
static_assert(sizeof(struct QOption_typeInt_typePtr_typeReal_typeVal) == 8, layout_QOption_typeInt_typePtr_typeReal_typeVal_size);
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_DEFINED
struct QTuple_QVal_QVal_QVal {
    QVal _0;
    QVal _1;
    QVal _2;
};
static_assert(offsetof(struct QTuple_QVal_QVal_QVal, _0) == 0, layout_QTuple_QVal_QVal_QVal__0);
static_assert(offsetof(struct QTuple_QVal_QVal_QVal, _1) == 8, layout_QTuple_QVal_QVal_QVal__1);
static_assert(offsetof(struct QTuple_QVal_QVal_QVal, _2) == 16, layout_QTuple_QVal_QVal_QVal__2);
static_assert(sizeof(struct QTuple_QVal_QVal_QVal) == 24, layout_QTuple_QVal_QVal_QVal_size);
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
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_Int_DEFINED
struct QTuple_Int_Int_Int {
    QInt _0;
    QInt _1;
    QInt _2;
};
static_assert(offsetof(struct QTuple_Int_Int_Int, _0) == 0, layout_QTuple_Int_Int_Int__0);
static_assert(offsetof(struct QTuple_Int_Int_Int, _1) == 8, layout_QTuple_Int_Int_Int__1);
static_assert(offsetof(struct QTuple_Int_Int_Int, _2) == 16, layout_QTuple_Int_Int_Int__2);
static_assert(sizeof(struct QTuple_Int_Int_Int) == 24, layout_QTuple_Int_Int_Int_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_Bool_QVal__2ce49d2a84d5590a_DEFINED
#define QUEST_TYPE_QTuple_String_Bool_QVal__2ce49d2a84d5590a_DEFINED
struct QTuple_String_Bool_QVal__2ce49d2a84d5590a {
    QString * _0;
    QBoolSlot _1;
    QVal _2;
    QVal _3;
    QTuple_QArray_QOption_pa_88eba21d06adf8d8 * _4;
    QVal _5;
    QVal _6;
    QVal _7;
    QTuple_Int_Int_Int * _8;
};
static_assert(offsetof(struct QTuple_String_Bool_QVal__2ce49d2a84d5590a, _0) == 0, layout_QTuple_String_Bool_QVal__2ce49d2a84d5590a__0);
static_assert(offsetof(struct QTuple_String_Bool_QVal__2ce49d2a84d5590a, _1) == 8, layout_QTuple_String_Bool_QVal__2ce49d2a84d5590a__1);
static_assert(offsetof(struct QTuple_String_Bool_QVal__2ce49d2a84d5590a, _2) == 16, layout_QTuple_String_Bool_QVal__2ce49d2a84d5590a__2);
static_assert(offsetof(struct QTuple_String_Bool_QVal__2ce49d2a84d5590a, _3) == 24, layout_QTuple_String_Bool_QVal__2ce49d2a84d5590a__3);
static_assert(offsetof(struct QTuple_String_Bool_QVal__2ce49d2a84d5590a, _4) == 32, layout_QTuple_String_Bool_QVal__2ce49d2a84d5590a__4);
static_assert(offsetof(struct QTuple_String_Bool_QVal__2ce49d2a84d5590a, _5) == 40, layout_QTuple_String_Bool_QVal__2ce49d2a84d5590a__5);
static_assert(offsetof(struct QTuple_String_Bool_QVal__2ce49d2a84d5590a, _6) == 48, layout_QTuple_String_Bool_QVal__2ce49d2a84d5590a__6);
static_assert(offsetof(struct QTuple_String_Bool_QVal__2ce49d2a84d5590a, _7) == 56, layout_QTuple_String_Bool_QVal__2ce49d2a84d5590a__7);
static_assert(offsetof(struct QTuple_String_Bool_QVal__2ce49d2a84d5590a, _8) == 64, layout_QTuple_String_Bool_QVal__2ce49d2a84d5590a__8);
static_assert(sizeof(struct QTuple_String_Bool_QVal__2ce49d2a84d5590a) == 72, layout_QTuple_String_Bool_QVal__2ce49d2a84d5590a_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_QArray_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_QArray_Int_DEFINED
struct QTuple_Int_QArray_Int {
    QInt _0;
    QArray * _1;
};
static_assert(offsetof(struct QTuple_Int_QArray_Int, _0) == 0, layout_QTuple_Int_QArray_Int__0);
static_assert(offsetof(struct QTuple_Int_QArray_Int, _1) == 8, layout_QTuple_Int_QArray_Int__1);
static_assert(sizeof(struct QTuple_Int_QArray_Int) == 16, layout_QTuple_Int_QArray_Int_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end_DEFINED
#define QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end_DEFINED
struct QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end {
    QInt _0;
    QTuple_Int_QArray_Int * _1;
    QTuple_Int_QArray_Int * _2;
};
static_assert(offsetof(struct QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end, _0) == 0, layout_QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end__0);
static_assert(offsetof(struct QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end, _1) == 8, layout_QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end__1);
static_assert(offsetof(struct QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end, _2) == 16, layout_QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end__2);
static_assert(sizeof(struct QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end) == 24, layout_QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_QArray_Int_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_Int_QArray_Int_end_DEFINED
struct QTuple_QTuple_Int_QArray_Int_end {
    QTuple_Int_QArray_Int * _0;
};
static_assert(offsetof(struct QTuple_QTuple_Int_QArray_Int_end, _0) == 0, layout_QTuple_QTuple_Int_QArray_Int_end__0);
static_assert(sizeof(struct QTuple_QTuple_Int_QArray_Int_end) == 8, layout_QTuple_QTuple_Int_QArray_Int_end_size);
#endif
#ifndef QUEST_TYPE_QTuple_QArray_Int_DEFINED
#define QUEST_TYPE_QTuple_QArray_Int_DEFINED
struct QTuple_QArray_Int {
    QArray * _0;
};
static_assert(offsetof(struct QTuple_QArray_Int, _0) == 0, layout_QTuple_QArray_Int__0);
static_assert(sizeof(struct QTuple_QArray_Int) == 8, layout_QTuple_QArray_Int_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48_DEFINED
#define QUEST_TYPE_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48_DEFINED
struct QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48 {
    QInt _0;
    QArray * _1;
    QArray * _2;
    QTuple_Int_QArray_Int * _3;
};
static_assert(offsetof(struct QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48, _0) == 0, layout_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48__0);
static_assert(offsetof(struct QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48, _1) == 8, layout_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48__1);
static_assert(offsetof(struct QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48, _2) == 16, layout_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48__2);
static_assert(offsetof(struct QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48, _3) == 24, layout_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48__3);
static_assert(sizeof(struct QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48) == 32, layout_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48_size);
#endif
#ifndef QUEST_TYPE_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_DEFINED
#define QUEST_TYPE_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_DEFINED
struct QOption_opAdd_opAnd_opAs_0293d61f8c93e36e {
    int64_t tag;
};
static_assert(sizeof(struct QOption_opAdd_opAnd_opAs_0293d61f8c93e36e) == 8, layout_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_opAdd_opA_c80de261989503a7_DEFINED
#define QUEST_TYPE_QTuple_QOption_opAdd_opA_c80de261989503a7_DEFINED
struct QTuple_QOption_opAdd_opA_c80de261989503a7 {
    QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * _0;
    QArray * _1;
    QArray * _2;
    QInt _3;
    QString * _4;
    QInt _5;
    QBoolSlot _6;
    QTuple_QArray_QOption_pa_88eba21d06adf8d8 * _7;
    QTuple_Int_Int_Int * _8;
    QBoolSlot _9;
};
static_assert(offsetof(struct QTuple_QOption_opAdd_opA_c80de261989503a7, _0) == 0, layout_QTuple_QOption_opAdd_opA_c80de261989503a7__0);
static_assert(offsetof(struct QTuple_QOption_opAdd_opA_c80de261989503a7, _1) == 8, layout_QTuple_QOption_opAdd_opA_c80de261989503a7__1);
static_assert(offsetof(struct QTuple_QOption_opAdd_opA_c80de261989503a7, _2) == 16, layout_QTuple_QOption_opAdd_opA_c80de261989503a7__2);
static_assert(offsetof(struct QTuple_QOption_opAdd_opA_c80de261989503a7, _3) == 24, layout_QTuple_QOption_opAdd_opA_c80de261989503a7__3);
static_assert(offsetof(struct QTuple_QOption_opAdd_opA_c80de261989503a7, _4) == 32, layout_QTuple_QOption_opAdd_opA_c80de261989503a7__4);
static_assert(offsetof(struct QTuple_QOption_opAdd_opA_c80de261989503a7, _5) == 40, layout_QTuple_QOption_opAdd_opA_c80de261989503a7__5);
static_assert(offsetof(struct QTuple_QOption_opAdd_opA_c80de261989503a7, _6) == 48, layout_QTuple_QOption_opAdd_opA_c80de261989503a7__6);
static_assert(offsetof(struct QTuple_QOption_opAdd_opA_c80de261989503a7, _7) == 56, layout_QTuple_QOption_opAdd_opA_c80de261989503a7__7);
static_assert(offsetof(struct QTuple_QOption_opAdd_opA_c80de261989503a7, _8) == 64, layout_QTuple_QOption_opAdd_opA_c80de261989503a7__8);
static_assert(offsetof(struct QTuple_QOption_opAdd_opA_c80de261989503a7, _9) == 72, layout_QTuple_QOption_opAdd_opA_c80de261989503a7__9);
static_assert(sizeof(struct QTuple_QOption_opAdd_opA_c80de261989503a7) == 80, layout_QTuple_QOption_opAdd_opA_c80de261989503a7_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end_DEFINED
struct QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end {
    QTuple_QOption_opAdd_opA_c80de261989503a7 * _0;
};
static_assert(offsetof(struct QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end, _0) == 0, layout_QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end__0);
static_assert(sizeof(struct QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end) == 8, layout_QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_Int_DEFINED
struct QTuple_Int_QTuple_Int_QArray_Int_end_Int {
    QInt _0;
    QTuple_Int_QArray_Int * _1;
    QInt _2;
};
static_assert(offsetof(struct QTuple_Int_QTuple_Int_QArray_Int_end_Int, _0) == 0, layout_QTuple_Int_QTuple_Int_QArray_Int_end_Int__0);
static_assert(offsetof(struct QTuple_Int_QTuple_Int_QArray_Int_end_Int, _1) == 8, layout_QTuple_Int_QTuple_Int_QArray_Int_end_Int__1);
static_assert(offsetof(struct QTuple_Int_QTuple_Int_QArray_Int_end_Int, _2) == 16, layout_QTuple_Int_QTuple_Int_QArray_Int_end_Int__2);
static_assert(sizeof(struct QTuple_Int_QTuple_Int_QArray_Int_end_Int) == 24, layout_QTuple_Int_QTuple_Int_QArray_Int_end_Int_size);
#endif
#ifndef QUEST_TYPE_QOption_termBranch_QTupl_fb14070ded119ae8_DEFINED
#define QUEST_TYPE_QOption_termBranch_QTupl_fb14070ded119ae8_DEFINED
struct QOption_termBranch_QTupl_fb14070ded119ae8 {
    int64_t tag;
    union {
        struct QOption_termBranch_QTupl_fb14070ded119ae8_termBranch_payload {
            QInt _0;
            QTuple_Int_QArray_Int * _1;
            QTuple_Int_QArray_Int * _2;
        } qo_termBranch;
        struct QOption_termBranch_QTupl_fb14070ded119ae8_termJump_payload {
            QTuple_Int_QArray_Int * _0;
        } qo_termJump;
        struct QOption_termBranch_QTupl_fb14070ded119ae8_termReturn_payload {
            QArray * _0;
        } qo_termReturn;
        struct QOption_termBranch_QTupl_fb14070ded119ae8_termSwitch_payload {
            QInt _0;
            QArray * _1;
            QArray * _2;
            QTuple_Int_QArray_Int * _3;
        } qo_termSwitch;
        struct QOption_termBranch_QTupl_fb14070ded119ae8_termTailCall_payload {
            QTuple_QOption_opAdd_opA_c80de261989503a7 * _0;
        } qo_termTailCall;
        struct QOption_termBranch_QTupl_fb14070ded119ae8_termTry_payload {
            QInt _0;
            QTuple_Int_QArray_Int * _1;
            QInt _2;
        } qo_termTry;
    } u;
};
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termBranch._0) == 8, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termBranch__0);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termBranch._1) == 16, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termBranch__1);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termBranch._2) == 24, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termBranch__2);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termJump._0) == 8, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termJump__0);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termReturn._0) == 8, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termReturn__0);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termSwitch._0) == 8, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termSwitch__0);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termSwitch._1) == 16, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termSwitch__1);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termSwitch._2) == 24, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termSwitch__2);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termSwitch._3) == 32, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termSwitch__3);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termTailCall._0) == 8, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termTailCall__0);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termTry._0) == 8, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termTry__0);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termTry._1) == 16, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termTry__1);
static_assert(offsetof(struct QOption_termBranch_QTupl_fb14070ded119ae8, u.qo_termTry._2) == 24, layout_QOption_termBranch_QTupl_fb14070ded119ae8_u_qo_termTry__2);
static_assert(sizeof(struct QOption_termBranch_QTupl_fb14070ded119ae8) == 40, layout_QOption_termBranch_QTupl_fb14070ded119ae8_size);
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QOption_419977b801e61011_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QOption_419977b801e61011_DEFINED
struct QTuple_QVal_QVal_QOption_419977b801e61011 {
    QVal _0;
    QVal _1;
    QOption_termBranch_QTupl_fb14070ded119ae8 * _2;
    QTuple_Int_Int_Int * _3;
};
static_assert(offsetof(struct QTuple_QVal_QVal_QOption_419977b801e61011, _0) == 0, layout_QTuple_QVal_QVal_QOption_419977b801e61011__0);
static_assert(offsetof(struct QTuple_QVal_QVal_QOption_419977b801e61011, _1) == 8, layout_QTuple_QVal_QVal_QOption_419977b801e61011__1);
static_assert(offsetof(struct QTuple_QVal_QVal_QOption_419977b801e61011, _2) == 16, layout_QTuple_QVal_QVal_QOption_419977b801e61011__2);
static_assert(offsetof(struct QTuple_QVal_QVal_QOption_419977b801e61011, _3) == 24, layout_QTuple_QVal_QVal_QOption_419977b801e61011__3);
static_assert(sizeof(struct QTuple_QVal_QVal_QOption_419977b801e61011) == 32, layout_QTuple_QVal_QVal_QOption_419977b801e61011_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_DEFINED
struct QTuple_Int_Int {
    QInt _0;
    QInt _1;
};
static_assert(offsetof(struct QTuple_Int_Int, _0) == 0, layout_QTuple_Int_Int__0);
static_assert(offsetof(struct QTuple_Int_Int, _1) == 8, layout_QTuple_Int_Int__1);
static_assert(sizeof(struct QTuple_Int_Int) == 16, layout_QTuple_Int_Int_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
static_assert(offsetof(struct QTuple_String, _0) == 0, layout_QTuple_String__0);
static_assert(sizeof(struct QTuple_String) == 8, layout_QTuple_String_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_DEFINED
struct QTuple_String_Int {
    QString * _0;
    QInt _1;
};
static_assert(offsetof(struct QTuple_String_Int, _0) == 0, layout_QTuple_String_Int__0);
static_assert(offsetof(struct QTuple_String_Int, _1) == 8, layout_QTuple_String_Int__1);
static_assert(sizeof(struct QTuple_String_Int) == 16, layout_QTuple_String_Int_size);
#endif
#ifndef QUEST_TYPE_QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_DEFINED
#define QUEST_TYPE_QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_DEFINED
struct QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end {
    int64_t tag;
    union {
        struct QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_wordInt_payload {
            QInt _0;
        } qo_wordInt;
        struct QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_wordSymbol_payload {
            QString * _0;
            QInt _1;
        } qo_wordSymbol;
    } u;
};
static_assert(offsetof(struct QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end, u.qo_wordInt._0) == 8, layout_QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_u_qo_wordInt__0);
static_assert(offsetof(struct QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end, u.qo_wordSymbol._0) == 8, layout_QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_u_qo_wordSymbol__0);
static_assert(offsetof(struct QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end, u.qo_wordSymbol._1) == 16, layout_QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_u_qo_wordSymbol__1);
static_assert(sizeof(struct QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end) == 24, layout_QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_size);
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5_DEFINED
#define QUEST_TYPE_QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5_DEFINED
struct QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5 {
    QArray * _0;
};
static_assert(offsetof(struct QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5, _0) == 0, layout_QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5__0);
static_assert(sizeof(struct QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5) == 8, layout_QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5_size);
#endif
#ifndef QUEST_TYPE_QOption_contentsText_QTu_6bf31e28bb3b7166_DEFINED
#define QUEST_TYPE_QOption_contentsText_QTu_6bf31e28bb3b7166_DEFINED
struct QOption_contentsText_QTu_6bf31e28bb3b7166 {
    int64_t tag;
    union {
        struct QOption_contentsText_QTu_6bf31e28bb3b7166_contentsText_payload {
            QString * _0;
        } qo_contentsText;
        struct QOption_contentsText_QTu_6bf31e28bb3b7166_contentsWords_payload {
            QArray * _0;
        } qo_contentsWords;
        struct QOption_contentsText_QTu_6bf31e28bb3b7166_contentsZero_payload {
            QInt _0;
        } qo_contentsZero;
    } u;
};
static_assert(offsetof(struct QOption_contentsText_QTu_6bf31e28bb3b7166, u.qo_contentsText._0) == 8, layout_QOption_contentsText_QTu_6bf31e28bb3b7166_u_qo_contentsText__0);
static_assert(offsetof(struct QOption_contentsText_QTu_6bf31e28bb3b7166, u.qo_contentsWords._0) == 8, layout_QOption_contentsText_QTu_6bf31e28bb3b7166_u_qo_contentsWords__0);
static_assert(offsetof(struct QOption_contentsText_QTu_6bf31e28bb3b7166, u.qo_contentsZero._0) == 8, layout_QOption_contentsText_QTu_6bf31e28bb3b7166_u_qo_contentsZero__0);
static_assert(sizeof(struct QOption_contentsText_QTu_6bf31e28bb3b7166) == 16, layout_QOption_contentsText_QTu_6bf31e28bb3b7166_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_Bool_Bool__330533165c015005_DEFINED
#define QUEST_TYPE_QTuple_String_Bool_Bool__330533165c015005_DEFINED
struct QTuple_String_Bool_Bool__330533165c015005 {
    QString * _0;
    QBoolSlot _1;
    QBoolSlot _2;
    QOption_contentsText_QTu_6bf31e28bb3b7166 * _3;
};
static_assert(offsetof(struct QTuple_String_Bool_Bool__330533165c015005, _0) == 0, layout_QTuple_String_Bool_Bool__330533165c015005__0);
static_assert(offsetof(struct QTuple_String_Bool_Bool__330533165c015005, _1) == 8, layout_QTuple_String_Bool_Bool__330533165c015005__1);
static_assert(offsetof(struct QTuple_String_Bool_Bool__330533165c015005, _2) == 16, layout_QTuple_String_Bool_Bool__330533165c015005__2);
static_assert(offsetof(struct QTuple_String_Bool_Bool__330533165c015005, _3) == 24, layout_QTuple_String_Bool_Bool__330533165c015005__3);
static_assert(sizeof(struct QTuple_String_Bool_Bool__330533165c015005) == 32, layout_QTuple_String_Bool_Bool__330533165c015005_size);
#endif
#ifndef QUEST_TYPE_QOption_relocAbsolute64__44c66b1db190bdc3_DEFINED
#define QUEST_TYPE_QOption_relocAbsolute64__44c66b1db190bdc3_DEFINED
struct QOption_relocAbsolute64__44c66b1db190bdc3 {
    int64_t tag;
};
static_assert(sizeof(struct QOption_relocAbsolute64__44c66b1db190bdc3) == 8, layout_QOption_relocAbsolute64__44c66b1db190bdc3_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_QOption_reloc_9c145bed7730d35a_DEFINED
#define QUEST_TYPE_QTuple_Int_QOption_reloc_9c145bed7730d35a_DEFINED
struct QTuple_Int_QOption_reloc_9c145bed7730d35a {
    QInt _0;
    QOption_relocAbsolute64__44c66b1db190bdc3 * _1;
    QString * _2;
    QInt _3;
};
static_assert(offsetof(struct QTuple_Int_QOption_reloc_9c145bed7730d35a, _0) == 0, layout_QTuple_Int_QOption_reloc_9c145bed7730d35a__0);
static_assert(offsetof(struct QTuple_Int_QOption_reloc_9c145bed7730d35a, _1) == 8, layout_QTuple_Int_QOption_reloc_9c145bed7730d35a__1);
static_assert(offsetof(struct QTuple_Int_QOption_reloc_9c145bed7730d35a, _2) == 16, layout_QTuple_Int_QOption_reloc_9c145bed7730d35a__2);
static_assert(offsetof(struct QTuple_Int_QOption_reloc_9c145bed7730d35a, _3) == 24, layout_QTuple_Int_QOption_reloc_9c145bed7730d35a__3);
static_assert(sizeof(struct QTuple_Int_QOption_reloc_9c145bed7730d35a) == 32, layout_QTuple_Int_QOption_reloc_9c145bed7730d35a_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_Bool_DEFINED
struct QTuple_String_Int_Int_Bool {
    QString * _0;
    QInt _1;
    QInt _2;
    QBoolSlot _3;
};
static_assert(offsetof(struct QTuple_String_Int_Int_Bool, _0) == 0, layout_QTuple_String_Int_Int_Bool__0);
static_assert(offsetof(struct QTuple_String_Int_Int_Bool, _1) == 8, layout_QTuple_String_Int_Int_Bool__1);
static_assert(offsetof(struct QTuple_String_Int_Int_Bool, _2) == 16, layout_QTuple_String_Int_Int_Bool__2);
static_assert(offsetof(struct QTuple_String_Int_Int_Bool, _3) == 24, layout_QTuple_String_Int_Int_Bool__3);
static_assert(sizeof(struct QTuple_String_Int_Int_Bool) == 32, layout_QTuple_String_Int_Int_Bool_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_Int_Int_DEFINED
struct QTuple_Int_Int_Int_Int {
    QInt _0;
    QInt _1;
    QInt _2;
    QInt _3;
};
static_assert(offsetof(struct QTuple_Int_Int_Int_Int, _0) == 0, layout_QTuple_Int_Int_Int_Int__0);
static_assert(offsetof(struct QTuple_Int_Int_Int_Int, _1) == 8, layout_QTuple_Int_Int_Int_Int__1);
static_assert(offsetof(struct QTuple_Int_Int_Int_Int, _2) == 16, layout_QTuple_Int_Int_Int_Int__2);
static_assert(offsetof(struct QTuple_Int_Int_Int_Int, _3) == 24, layout_QTuple_Int_Int_Int_Int__3);
static_assert(sizeof(struct QTuple_Int_Int_Int_Int) == 32, layout_QTuple_Int_Int_Int_Int_size);
#endif
#ifndef QUEST_TYPE_QTuple_QArray_Int_QArray_f0593bc63ece5e04_DEFINED
#define QUEST_TYPE_QTuple_QArray_Int_QArray_f0593bc63ece5e04_DEFINED
struct QTuple_QArray_Int_QArray_f0593bc63ece5e04 {
    QArray * _0;
    QArray * _1;
    QArray * _2;
    QArray * _3;
    QArray * _4;
    QArray * _5;
    QArray * _6;
    QArray * _7;
};
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _0) == 0, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__0);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _1) == 8, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__1);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _2) == 16, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__2);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _3) == 24, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__3);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _4) == 32, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__4);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _5) == 40, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__5);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _6) == 48, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__6);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _7) == 56, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__7);
static_assert(sizeof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04) == 64, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04_size);
#endif
#ifndef QUEST_TYPE_QOption_relocGot_relocPage_relocTlv_DEFINED
#define QUEST_TYPE_QOption_relocGot_relocPage_relocTlv_DEFINED
struct QOption_relocGot_relocPage_relocTlv {
    int64_t tag;
};
static_assert(sizeof(struct QOption_relocGot_relocPage_relocTlv) == 8, layout_QOption_relocGot_relocPage_relocTlv_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_QOption_relocGot_relocPage_relocTlv_end_DEFINED
#define QUEST_TYPE_QTuple_String_QOption_relocGot_relocPage_relocTlv_end_DEFINED
struct QTuple_String_QOption_relocGot_relocPage_relocTlv_end {
    QString * _0;
    QOption_relocGot_relocPage_relocTlv * _1;
};
static_assert(offsetof(struct QTuple_String_QOption_relocGot_relocPage_relocTlv_end, _0) == 0, layout_QTuple_String_QOption_relocGot_relocPage_relocTlv_end__0);
static_assert(offsetof(struct QTuple_String_QOption_relocGot_relocPage_relocTlv_end, _1) == 8, layout_QTuple_String_QOption_relocGot_relocPage_relocTlv_end__1);
static_assert(sizeof(struct QTuple_String_QOption_relocGot_relocPage_relocTlv_end) == 16, layout_QTuple_String_QOption_relocGot_relocPage_relocTlv_end_size);
#endif
#ifndef QUEST_TYPE_QOption_arithAdd_arithAn_c473bdf6463401a5_DEFINED
#define QUEST_TYPE_QOption_arithAdd_arithAn_c473bdf6463401a5_DEFINED
struct QOption_arithAdd_arithAn_c473bdf6463401a5 {
    int64_t tag;
};
static_assert(sizeof(struct QOption_arithAdd_arithAn_c473bdf6463401a5) == 8, layout_QOption_arithAdd_arithAn_c473bdf6463401a5_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_DEFINED
#define QUEST_TYPE_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_DEFINED
struct QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end {
    QOption_arithAdd_arithAn_c473bdf6463401a5 * _0;
};
static_assert(offsetof(struct QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end, _0) == 0, layout_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end__0);
static_assert(sizeof(struct QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end) == 8, layout_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_size);
#endif
#ifndef QUEST_TYPE_QOption_condEq_condGe_co_eabed1dd4e938ad3_DEFINED
#define QUEST_TYPE_QOption_condEq_condGe_co_eabed1dd4e938ad3_DEFINED
struct QOption_condEq_condGe_co_eabed1dd4e938ad3 {
    int64_t tag;
};
static_assert(sizeof(struct QOption_condEq_condGe_co_eabed1dd4e938ad3) == 8, layout_QOption_condEq_condGe_co_eabed1dd4e938ad3_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String_DEFINED
#define QUEST_TYPE_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String_DEFINED
struct QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String {
    QOption_condEq_condGe_co_eabed1dd4e938ad3 * _0;
    QString * _1;
};
static_assert(offsetof(struct QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String, _0) == 0, layout_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String__0);
static_assert(offsetof(struct QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String, _1) == 8, layout_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String__1);
static_assert(sizeof(struct QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String) == 16, layout_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_String_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_DEFINED
#define QUEST_TYPE_QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_DEFINED
struct QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end {
    QInt _0;
    QOption_condEq_condGe_co_eabed1dd4e938ad3 * _1;
};
static_assert(offsetof(struct QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end, _0) == 0, layout_QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end__0);
static_assert(offsetof(struct QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end, _1) == 8, layout_QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end__1);
static_assert(sizeof(struct QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end) == 16, layout_QTuple_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_DEFINED
struct QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end {
    QInt _0;
    QInt _1;
    QOption_condEq_condGe_co_eabed1dd4e938ad3 * _2;
};
static_assert(offsetof(struct QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end, _0) == 0, layout_QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end__0);
static_assert(offsetof(struct QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end, _1) == 8, layout_QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end__1);
static_assert(offsetof(struct QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end, _2) == 16, layout_QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end__2);
static_assert(sizeof(struct QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end) == 24, layout_QTuple_Int_Int_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_DEFINED
#define QUEST_TYPE_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_DEFINED
struct QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end {
    QOption_condEq_condGe_co_eabed1dd4e938ad3 * _0;
};
static_assert(offsetof(struct QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end, _0) == 0, layout_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end__0);
static_assert(sizeof(struct QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end) == 8, layout_QTuple_QOption_condEq_condGe_co_eabed1dd4e938ad3_end_size);
#endif
#ifndef QUEST_TYPE_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_DEFINED
#define QUEST_TYPE_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_DEFINED
struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f {
    int64_t tag;
    union {
        struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f_modeIndex_payload {
            QInt _0;
        } qo_modeIndex;
        struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f_modeOffset_payload {
            QInt _0;
        } qo_modeOffset;
        struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f_modePageOff_payload {
            QString * _0;
            QOption_relocGot_relocPage_relocTlv * _1;
        } qo_modePageOff;
        struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f_modePost_payload {
            QInt _0;
        } qo_modePost;
        struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f_modePre_payload {
            QInt _0;
        } qo_modePre;
    } u;
};
static_assert(offsetof(struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f, u.qo_modeIndex._0) == 8, layout_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_u_qo_modeIndex__0);
static_assert(offsetof(struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f, u.qo_modeOffset._0) == 8, layout_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_u_qo_modeOffset__0);
static_assert(offsetof(struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f, u.qo_modePageOff._0) == 8, layout_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_u_qo_modePageOff__0);
static_assert(offsetof(struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f, u.qo_modePageOff._1) == 16, layout_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_u_qo_modePageOff__1);
static_assert(offsetof(struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f, u.qo_modePost._0) == 8, layout_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_u_qo_modePost__0);
static_assert(offsetof(struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f, u.qo_modePre._0) == 8, layout_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_u_qo_modePre__0);
static_assert(sizeof(struct QOption_modeBase_modeInd_c9e05f3a0acd9b8f) == 24, layout_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end_DEFINED
#define QUEST_TYPE_QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end_DEFINED
struct QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end {
    QOption_modeBase_modeInd_c9e05f3a0acd9b8f * _0;
};
static_assert(offsetof(struct QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end, _0) == 0, layout_QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end__0);
static_assert(sizeof(struct QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end) == 8, layout_QTuple_QOption_modeBase_modeInd_c9e05f3a0acd9b8f_end_size);
#endif
#ifndef QUEST_TYPE_QOption_load64_loadS32_loadS8_loadU8_DEFINED
#define QUEST_TYPE_QOption_load64_loadS32_loadS8_loadU8_DEFINED
struct QOption_load64_loadS32_loadS8_loadU8 {
    int64_t tag;
};
static_assert(sizeof(struct QOption_load64_loadS32_loadS8_loadU8) == 8, layout_QOption_load64_loadS32_loadS8_loadU8_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4_DEFINED
#define QUEST_TYPE_QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4_DEFINED
struct QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4 {
    QOption_load64_loadS32_loadS8_loadU8 * _0;
    QOption_modeBase_modeInd_c9e05f3a0acd9b8f * _1;
};
static_assert(offsetof(struct QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4, _0) == 0, layout_QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4__0);
static_assert(offsetof(struct QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4, _1) == 8, layout_QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4__1);
static_assert(sizeof(struct QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4) == 16, layout_QTuple_QOption_load64_lo_ff4a9f0cc49e7ef4_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int_DEFINED
#define QUEST_TYPE_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int_DEFINED
struct QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int {
    QOption_arithAdd_arithAn_c473bdf6463401a5 * _0;
    QInt _1;
};
static_assert(offsetof(struct QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int, _0) == 0, layout_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int__0);
static_assert(offsetof(struct QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int, _1) == 8, layout_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int__1);
static_assert(sizeof(struct QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int) == 16, layout_QTuple_QOption_arithAdd_arithAn_c473bdf6463401a5_end_Int_size);
#endif
#ifndef QUEST_TYPE_QOption_store32_store64_store8_DEFINED
#define QUEST_TYPE_QOption_store32_store64_store8_DEFINED
struct QOption_store32_store64_store8 {
    int64_t tag;
};
static_assert(sizeof(struct QOption_store32_store64_store8) == 8, layout_QOption_store32_store64_store8_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_store32_s_5bbc7285dc38388c_DEFINED
#define QUEST_TYPE_QTuple_QOption_store32_s_5bbc7285dc38388c_DEFINED
struct QTuple_QOption_store32_s_5bbc7285dc38388c {
    QOption_store32_store64_store8 * _0;
    QOption_modeBase_modeInd_c9e05f3a0acd9b8f * _1;
};
static_assert(offsetof(struct QTuple_QOption_store32_s_5bbc7285dc38388c, _0) == 0, layout_QTuple_QOption_store32_s_5bbc7285dc38388c__0);
static_assert(offsetof(struct QTuple_QOption_store32_s_5bbc7285dc38388c, _1) == 8, layout_QTuple_QOption_store32_s_5bbc7285dc38388c__1);
static_assert(sizeof(struct QTuple_QOption_store32_s_5bbc7285dc38388c) == 16, layout_QTuple_QOption_store32_s_5bbc7285dc38388c_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Bool_DEFINED
struct QTuple_String_Int_Bool {
    QString * _0;
    QInt _1;
    QBoolSlot _2;
};
static_assert(offsetof(struct QTuple_String_Int_Bool, _0) == 0, layout_QTuple_String_Int_Bool__0);
static_assert(offsetof(struct QTuple_String_Int_Bool, _1) == 8, layout_QTuple_String_Int_Bool__1);
static_assert(offsetof(struct QTuple_String_Int_Bool, _2) == 16, layout_QTuple_String_Int_Bool__2);
static_assert(sizeof(struct QTuple_String_Int_Bool) == 24, layout_QTuple_String_Int_Bool_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_DEFINED
#define QUEST_TYPE_QTuple_Int_String_DEFINED
struct QTuple_Int_String {
    QInt _0;
    QString * _1;
};
static_assert(offsetof(struct QTuple_Int_String, _0) == 0, layout_QTuple_Int_String__0);
static_assert(offsetof(struct QTuple_Int_String, _1) == 8, layout_QTuple_Int_String__1);
static_assert(sizeof(struct QTuple_Int_String) == 16, layout_QTuple_Int_String_size);
#endif
#ifndef QUEST_TYPE_QOption_opAddImm_QTuple__31f18ef922269f96_DEFINED
#define QUEST_TYPE_QOption_opAddImm_QTuple__31f18ef922269f96_DEFINED
struct QOption_opAddImm_QTuple__31f18ef922269f96 {
    int64_t tag;
    union {
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opAddImm_payload {
            QInt _0;
            QInt _1;
        } qo_opAddImm;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opAddPageOff_payload {
            QString * _0;
        } qo_opAddPageOff;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opAdr_payload {
            QString * _0;
        } qo_opAdr;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opAdrp_payload {
            QString * _0;
            QOption_relocGot_relocPage_relocTlv * _1;
        } qo_opAdrp;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opArith_payload {
            QOption_arithAdd_arithAn_c473bdf6463401a5 * _0;
        } qo_opArith;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opB_payload {
            QString * _0;
        } qo_opB;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opBCond_payload {
            QOption_condEq_condGe_co_eabed1dd4e938ad3 * _0;
            QString * _1;
        } qo_opBCond;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opBSymbol_payload {
            QString * _0;
        } qo_opBSymbol;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opBl_payload {
            QString * _0;
        } qo_opBl;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opBrk_payload {
            QInt _0;
        } qo_opBrk;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opCbnz_payload {
            QString * _0;
        } qo_opCbnz;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opCbz_payload {
            QString * _0;
        } qo_opCbz;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opCcmp_payload {
            QInt _0;
            QOption_condEq_condGe_co_eabed1dd4e938ad3 * _1;
        } qo_opCcmp;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opCcmpImm_payload {
            QInt _0;
            QInt _1;
            QOption_condEq_condGe_co_eabed1dd4e938ad3 * _2;
        } qo_opCcmpImm;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opCfiDefCfa_payload {
            QInt _0;
        } qo_opCfiDefCfa;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opCfiOffset_payload {
            QInt _0;
        } qo_opCfiOffset;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opCmpImm_payload {
            QInt _0;
        } qo_opCmpImm;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opCset_payload {
            QOption_condEq_condGe_co_eabed1dd4e938ad3 * _0;
        } qo_opCset;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opLabel_payload {
            QString * _0;
        } qo_opLabel;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opLdp_payload {
            QOption_modeBase_modeInd_c9e05f3a0acd9b8f * _0;
        } qo_opLdp;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opLoad_payload {
            QOption_load64_loadS32_loadS8_loadU8 * _0;
            QOption_modeBase_modeInd_c9e05f3a0acd9b8f * _1;
        } qo_opLoad;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opLoc_payload {
            QInt _0;
            QInt _1;
            QInt _2;
        } qo_opLoc;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opLogicImm_payload {
            QOption_arithAdd_arithAn_c473bdf6463401a5 * _0;
            QInt _1;
        } qo_opLogicImm;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opMovConst_payload {
            QInt _0;
        } qo_opMovConst;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opMovImm_payload {
            QInt _0;
        } qo_opMovImm;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opMovk_payload {
            QInt _0;
            QInt _1;
        } qo_opMovk;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opMovz_payload {
            QInt _0;
            QInt _1;
        } qo_opMovz;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opShiftImm_payload {
            QOption_arithAdd_arithAn_c473bdf6463401a5 * _0;
            QInt _1;
        } qo_opShiftImm;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opStore_payload {
            QOption_store32_store64_store8 * _0;
            QOption_modeBase_modeInd_c9e05f3a0acd9b8f * _1;
        } qo_opStore;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opStp_payload {
            QOption_modeBase_modeInd_c9e05f3a0acd9b8f * _0;
        } qo_opStp;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opSubImm_payload {
            QInt _0;
        } qo_opSubImm;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opSymbolAddress_payload {
            QString * _0;
            QInt _1;
            QBoolSlot _2;
        } qo_opSymbolAddress;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opTbnz_payload {
            QInt _0;
            QString * _1;
        } qo_opTbnz;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opTbz_payload {
            QInt _0;
            QString * _1;
        } qo_opTbz;
        struct QOption_opAddImm_QTuple__31f18ef922269f96_opTlvAddress_payload {
            QString * _0;
        } qo_opTlvAddress;
    } u;
};
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opAddImm._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opAddImm__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opAddImm._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opAddImm__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opAddPageOff._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opAddPageOff__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opAdr._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opAdr__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opAdrp._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opAdrp__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opAdrp._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opAdrp__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opArith._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opArith__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opB._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opB__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opBCond._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opBCond__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opBCond._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opBCond__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opBSymbol._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opBSymbol__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opBl._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opBl__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opBrk._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opBrk__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCbnz._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCbnz__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCbz._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCbz__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCcmp._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCcmp__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCcmp._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCcmp__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCcmpImm._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCcmpImm__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCcmpImm._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCcmpImm__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCcmpImm._2) == 24, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCcmpImm__2);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCfiDefCfa._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCfiDefCfa__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCfiOffset._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCfiOffset__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCmpImm._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCmpImm__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opCset._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opCset__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opLabel._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opLabel__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opLdp._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opLdp__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opLoad._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opLoad__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opLoad._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opLoad__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opLoc._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opLoc__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opLoc._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opLoc__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opLoc._2) == 24, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opLoc__2);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opLogicImm._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opLogicImm__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opLogicImm._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opLogicImm__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opMovConst._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opMovConst__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opMovImm._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opMovImm__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opMovk._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opMovk__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opMovk._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opMovk__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opMovz._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opMovz__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opMovz._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opMovz__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opShiftImm._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opShiftImm__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opShiftImm._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opShiftImm__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opStore._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opStore__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opStore._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opStore__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opStp._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opStp__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opSubImm._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opSubImm__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opSymbolAddress._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opSymbolAddress__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opSymbolAddress._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opSymbolAddress__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opSymbolAddress._2) == 24, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opSymbolAddress__2);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opTbnz._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opTbnz__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opTbnz._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opTbnz__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opTbz._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opTbz__0);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opTbz._1) == 16, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opTbz__1);
static_assert(offsetof(struct QOption_opAddImm_QTuple__31f18ef922269f96, u.qo_opTlvAddress._0) == 8, layout_QOption_opAddImm_QTuple__31f18ef922269f96_u_qo_opTlvAddress__0);
static_assert(sizeof(struct QOption_opAddImm_QTuple__31f18ef922269f96) == 32, layout_QOption_opAddImm_QTuple__31f18ef922269f96_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int_DEFINED
#define QUEST_TYPE_QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int_DEFINED
struct QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int {
    QOption_opAddImm_QTuple__31f18ef922269f96 * _0;
    QArray * _1;
};
static_assert(offsetof(struct QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int, _0) == 0, layout_QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int__0);
static_assert(offsetof(struct QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int, _1) == 8, layout_QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int__1);
static_assert(sizeof(struct QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int) == 16, layout_QTuple_QOption_opAddImm_QTuple__31f18ef922269f96_end_QArray_Int_size);
#endif
typedef QTuple_Int_Int_QVal_Int * quest_type_questlang__codegen__arm64__Codegen_FrameSlot;
typedef const QException * quest_sig_questlang__codegen__arm64__Codegen_unsupported;
typedef QString * (*quest_sig_questlang__codegen__arm64__Codegen_assembleUnit)(QTuple_QVal_QVal_QVal * u);
typedef QTuple_QArray_Int_QArray_f0593bc63ece5e04 * (*quest_sig_questlang__codegen__arm64__Codegen_encodeUnit)(QTuple_QVal_QVal_QVal * u);
typedef QVal (*quest_sig_questlang__codegen__arm64__Codegen_relaxBranches)(QVal code, QString * prefix, QInt reach);
typedef QArray * (*quest_sig_questlang__codegen__arm64__Codegen_frameSlots)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f);
#ifdef __cplusplus
}
#endif
#endif
