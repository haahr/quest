#ifndef QUEST_INTF_QUESTLANG__SSA__NODES_H
#define QUEST_INTF_QUESTLANG__SSA__NODES_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/vector.int.h"
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_TYPEDEF
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_TYPEDEF
typedef struct QOption_typeInt_typePtr_typeReal_typeVal QOption_typeInt_typePtr_typeReal_typeVal;
#endif
#ifndef QUEST_TYPE_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_TYPEDEF
#define QUEST_TYPE_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_TYPEDEF
typedef struct QOption_opAdd_opAnd_opAs_0293d61f8c93e36e QOption_opAdd_opAnd_opAs_0293d61f8c93e36e;
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
#ifndef QUEST_TYPE_QTuple_QOption_opAdd_opA_c80de261989503a7_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_opAdd_opA_c80de261989503a7_TYPEDEF
typedef struct QTuple_QOption_opAdd_opA_c80de261989503a7 QTuple_QOption_opAdd_opA_c80de261989503a7;
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
#ifndef QUEST_TYPE_QTuple_String_Bool_QVal__2ce49d2a84d5590a_TYPEDEF
#define QUEST_TYPE_QTuple_String_Bool_QVal__2ce49d2a84d5590a_TYPEDEF
typedef struct QTuple_String_Bool_QVal__2ce49d2a84d5590a QTuple_String_Bool_QVal__2ce49d2a84d5590a;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_TYPEDEF
typedef struct QTuple_String_Int QTuple_String_Int;
#endif
#ifndef QUEST_TYPE_QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_TYPEDEF
#define QUEST_TYPE_QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end_TYPEDEF
typedef struct QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end;
#endif
#ifndef QUEST_TYPE_QTuple_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_TYPEDEF
typedef struct QTuple_String QTuple_String;
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
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QVal QTuple_QVal_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
struct QOption_typeInt_typePtr_typeReal_typeVal {
    int64_t tag;
};
static_assert(sizeof(struct QOption_typeInt_typePtr_typeReal_typeVal) == 8, layout_QOption_typeInt_typePtr_typeReal_typeVal_size);
#endif
#ifndef QUEST_TYPE_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_DEFINED
#define QUEST_TYPE_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_DEFINED
struct QOption_opAdd_opAnd_opAs_0293d61f8c93e36e {
    int64_t tag;
};
static_assert(sizeof(struct QOption_opAdd_opAnd_opAs_0293d61f8c93e36e) == 8, layout_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_size);
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
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
static_assert(offsetof(struct QTuple_String, _0) == 0, layout_QTuple_String__0);
static_assert(sizeof(struct QTuple_String) == 8, layout_QTuple_String_size);
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
typedef QOption_typeInt_typePtr_typeReal_typeVal * quest_type_questlang__ssa__Nodes_Type;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_type_questlang__ssa__Nodes_Opcode;
typedef QOption_passByte_passInt_cafeff5ade35f658 * quest_type_questlang__ssa__Nodes_Passed;
typedef QTuple_QArray_QOption_pa_88eba21d06adf8d8 * quest_type_questlang__ssa__Nodes_Signature;
typedef QTuple_Int_Int_Int * quest_type_questlang__ssa__Nodes_Loc;
typedef QTuple_QOption_opAdd_opA_c80de261989503a7 * quest_type_questlang__ssa__Nodes_Inst;
typedef QTuple_Int_QArray_Int * quest_type_questlang__ssa__Nodes_Target;
typedef QOption_termBranch_QTupl_fb14070ded119ae8 * quest_type_questlang__ssa__Nodes_Terminator;
typedef QTuple_QVal_QVal_QOption_419977b801e61011 * quest_type_questlang__ssa__Nodes_Block;
typedef QTuple_Int_Int * quest_type_questlang__ssa__Nodes_Slot;
typedef QTuple_String_Bool_QVal__2ce49d2a84d5590a * quest_type_questlang__ssa__Nodes_Function;
typedef QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end * quest_type_questlang__ssa__Nodes_Word;
typedef QOption_contentsText_QTu_6bf31e28bb3b7166 * quest_type_questlang__ssa__Nodes_Contents;
typedef QTuple_String_Bool_Bool__330533165c015005 * quest_type_questlang__ssa__Nodes_Data;
typedef QTuple_QVal_QVal_QVal * quest_type_questlang__ssa__Nodes_Unit;
typedef QTuple_QArray_QOption_pa_88eba21d06adf8d8 * (*quest_sig_questlang__ssa__Nodes_signature)(QArray * params, QArray * results, QArray * pairs, QArray * narrow);
typedef QTuple_QArray_QOption_pa_88eba21d06adf8d8 * quest_sig_questlang__ssa__Nodes_emptySignature;
typedef QOption_passByte_passInt_cafeff5ade35f658 * quest_sig_questlang__ssa__Nodes_passWord;
typedef QOption_passByte_passInt_cafeff5ade35f658 * quest_sig_questlang__ssa__Nodes_passReal;
typedef QOption_passByte_passInt_cafeff5ade35f658 * quest_sig_questlang__ssa__Nodes_passPair;
typedef QOption_passByte_passInt_cafeff5ade35f658 * quest_sig_questlang__ssa__Nodes_passPairRest;
typedef QOption_passByte_passInt_cafeff5ade35f658 * quest_sig_questlang__ssa__Nodes_passByte;
typedef QOption_passByte_passInt_cafeff5ade35f658 * quest_sig_questlang__ssa__Nodes_passInt32;
typedef QTuple_QArray_QOption_pa_88eba21d06adf8d8 * (*quest_sig_questlang__ssa__Nodes_withParam)(QTuple_QArray_QOption_pa_88eba21d06adf8d8 * s, QInt k, QOption_passByte_passInt_cafeff5ade35f658 * passed);
typedef QTuple_QArray_QOption_pa_88eba21d06adf8d8 * (*quest_sig_questlang__ssa__Nodes_withResult)(QTuple_QArray_QOption_pa_88eba21d06adf8d8 * s, QOption_passByte_passInt_cafeff5ade35f658 * passed);
typedef QArray * (*quest_sig_questlang__ssa__Nodes_pairsOf)(QArray * ps);
typedef QArray * (*quest_sig_questlang__ssa__Nodes_narrowOf)(QArray * ps);
typedef QArray * (*quest_sig_questlang__ssa__Nodes_int32Of)(QArray * ps);
typedef QArray * (*quest_sig_questlang__ssa__Nodes_memoryOf)(QArray * ps);
typedef QOption_typeInt_typePtr_typeReal_typeVal * quest_sig_questlang__ssa__Nodes_typeInt;
typedef QOption_typeInt_typePtr_typeReal_typeVal * quest_sig_questlang__ssa__Nodes_typePtr;
typedef QOption_typeInt_typePtr_typeReal_typeVal * quest_sig_questlang__ssa__Nodes_typeReal;
typedef QOption_typeInt_typePtr_typeReal_typeVal * quest_sig_questlang__ssa__Nodes_typeVal;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opConst;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opRealConst;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opSymbol;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opNull;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opSlot;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opAdd;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opSub;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opMul;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opDiv;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opRem;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opAnd;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opOr;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opXor;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opShl;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opLshr;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opAshr;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opEq;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opNe;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opLt;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opLe;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opGt;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opGe;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opUlt;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opPeq;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opPne;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opFadd;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opFsub;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opFmul;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opFdiv;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opFeq;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opFlt;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opFle;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opFgt;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opFge;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opIsNaN;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opIntToPtr;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opPtrToInt;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opRealBits;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opBitsReal;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opSext8;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opZext8;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opLoad;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opStore;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opCall;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opCallIndirect;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opCopy;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opPtrAdd;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opThreadLocal;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opToVal;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opFromVal;
typedef QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * quest_sig_questlang__ssa__Nodes_opMulHiU;
typedef QOption_termBranch_QTupl_fb14070ded119ae8 * quest_sig_questlang__ssa__Nodes_termNone;
typedef QOption_termBranch_QTupl_fb14070ded119ae8 * quest_sig_questlang__ssa__Nodes_termUnreachable;
typedef QTuple_QVal_QVal_QVal * (*quest_sig_questlang__ssa__Nodes_newUnit)(void);
typedef QTuple_Int_Int_Int * quest_sig_questlang__ssa__Nodes_noLoc;
typedef QBool (*quest_sig_questlang__ssa__Nodes_hasLoc)(QTuple_Int_Int_Int * l);
typedef QBool (*quest_sig_questlang__ssa__Nodes_sameLoc)(QTuple_Int_Int_Int * a, QTuple_Int_Int_Int * b);
typedef QTuple_String_Bool_Bool__330533165c015005 * (*quest_sig_questlang__ssa__Nodes_words)(QString * symbol, QBool exported, QBool writable, QArray * ws);
typedef QInt (*quest_sig_questlang__ssa__Nodes_wordsBytes)(QOption_contentsText_QTu_6bf31e28bb3b7166 * c);
typedef QTuple_String_Bool_QVal__2ce49d2a84d5590a * (*quest_sig_questlang__ssa__Nodes_newFunction)(QString * symbol, QBool exported, QArray * params, QArray * results);
typedef QInt (*quest_sig_questlang__ssa__Nodes_newValue)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QOption_typeInt_typePtr_typeReal_typeVal * t);
typedef QInt (*quest_sig_questlang__ssa__Nodes_newBlock)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f);
typedef QInt (*quest_sig_questlang__ssa__Nodes_addParam)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt block, QOption_typeInt_typePtr_typeReal_typeVal * t);
typedef QInt (*quest_sig_questlang__ssa__Nodes_newSlot)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt bytes, QInt align);
typedef QTuple_QVal_QVal_QOption_419977b801e61011 * (*quest_sig_questlang__ssa__Nodes_block)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b);
typedef QOption_typeInt_typePtr_typeReal_typeVal * (*quest_sig_questlang__ssa__Nodes_typeOf)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt v);
typedef QArray * (*quest_sig_questlang__ssa__Nodes_valueTypes)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QArray * vs);
typedef void (*quest_sig_questlang__ssa__Nodes_append)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QTuple_QOption_opAdd_opA_c80de261989503a7 * inst);
typedef QTuple_QOption_opAdd_opA_c80de261989503a7 * (*quest_sig_questlang__ssa__Nodes_inst)(QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * op, QArray * args, QArray * results);
typedef QTuple_QOption_opAdd_opA_c80de261989503a7 * (*quest_sig_questlang__ssa__Nodes_instruction)(QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * op, QArray * args, QArray * results, QInt imm, QString * symbol, QInt width, QBool q_signed, QTuple_QArray_QOption_pa_88eba21d06adf8d8 * s);
typedef QInt (*quest_sig_questlang__ssa__Nodes_emit)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * op, QArray * args, QOption_typeInt_typePtr_typeReal_typeVal * t);
typedef QInt (*quest_sig_questlang__ssa__Nodes_constant)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QInt n);
typedef QInt (*quest_sig_questlang__ssa__Nodes_realConstant)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QInt n);
typedef QInt (*quest_sig_questlang__ssa__Nodes_null)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b);
typedef QInt (*quest_sig_questlang__ssa__Nodes_symbolAddress)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QString * symbol);
typedef QInt (*quest_sig_questlang__ssa__Nodes_symbolPlus)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QString * symbol, QInt addend);
typedef QInt (*quest_sig_questlang__ssa__Nodes_threadLocal)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QString * symbol);
typedef QInt (*quest_sig_questlang__ssa__Nodes_ptrAdd)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QInt p, QInt n);
typedef QInt (*quest_sig_questlang__ssa__Nodes_toVal)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QInt v);
typedef QInt (*quest_sig_questlang__ssa__Nodes_fromVal)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QInt v, QOption_typeInt_typePtr_typeReal_typeVal * t);
typedef QInt (*quest_sig_questlang__ssa__Nodes_slotAddress)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QInt s);
typedef QInt (*quest_sig_questlang__ssa__Nodes_binary)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * op, QInt x, QInt y);
typedef QInt (*quest_sig_questlang__ssa__Nodes_load)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QInt address, QInt offset, QInt width, QBool q_signed, QOption_typeInt_typePtr_typeReal_typeVal * t);
typedef QInt (*quest_sig_questlang__ssa__Nodes_invariantLoad)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QInt address, QInt offset, QInt width, QBool q_signed, QOption_typeInt_typePtr_typeReal_typeVal * t);
typedef void (*quest_sig_questlang__ssa__Nodes_store)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QInt address, QInt offset, QInt width, QInt value);
typedef QArray * (*quest_sig_questlang__ssa__Nodes_call)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QString * symbol, QArray * args, QTuple_QArray_QOption_pa_88eba21d06adf8d8 * s, QArray * results);
typedef void (*quest_sig_questlang__ssa__Nodes_tailCall)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QString * symbol, QArray * args, QTuple_QArray_QOption_pa_88eba21d06adf8d8 * s, QArray * results);
typedef void (*quest_sig_questlang__ssa__Nodes_terminate)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b, QOption_termBranch_QTupl_fb14070ded119ae8 * t);
typedef QTuple_Int_QArray_Int * (*quest_sig_questlang__ssa__Nodes_target)(QInt block, QArray * args);
typedef QBool (*quest_sig_questlang__ssa__Nodes_isTerminated)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QInt b);
typedef QArray * (*quest_sig_questlang__ssa__Nodes_terminatorUses)(QOption_termBranch_QTupl_fb14070ded119ae8 * t);
typedef QArray * (*quest_sig_questlang__ssa__Nodes_successors)(QOption_termBranch_QTupl_fb14070ded119ae8 * t);
typedef QArray * (*quest_sig_questlang__ssa__Nodes_targets)(QOption_termBranch_QTupl_fb14070ded119ae8 * t);
typedef QOption_termBranch_QTupl_fb14070ded119ae8 * (*quest_sig_questlang__ssa__Nodes_mapTargets)(QOption_termBranch_QTupl_fb14070ded119ae8 * t, QClosure * map);
typedef QOption_termBranch_QTupl_fb14070ded119ae8 * (*quest_sig_questlang__ssa__Nodes_mapBlocks)(QOption_termBranch_QTupl_fb14070ded119ae8 * t, QClosure * map);
typedef void (*quest_sig_questlang__ssa__Nodes_replaceUses)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f, QClosure * replace);
typedef QBool (*quest_sig_questlang__ssa__Nodes_isOp)(QTuple_QOption_opAdd_opA_c80de261989503a7 * i, QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * op);
typedef QBool (*quest_sig_questlang__ssa__Nodes_isCall)(QTuple_QOption_opAdd_opA_c80de261989503a7 * i);
typedef QString * (*quest_sig_questlang__ssa__Nodes_typeName)(QOption_typeInt_typePtr_typeReal_typeVal * t);
typedef QString * (*quest_sig_questlang__ssa__Nodes_opcodeName)(QOption_opAdd_opAnd_opAs_0293d61f8c93e36e * op);
typedef QVal (*quest_sig_questlang__ssa__Nodes_opcodeNamed)(QString * name);
#ifdef __cplusplus
}
#endif
#endif
