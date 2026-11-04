#ifndef QUEST_INTF_QUESTLANG__SSA__PARSER_H
#define QUEST_INTF_QUESTLANG__SSA__PARSER_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/ssa/nodes.int.h"
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
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_TYPEDEF
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_TYPEDEF
typedef struct QOption_typeInt_typePtr_typeReal_typeVal QOption_typeInt_typePtr_typeReal_typeVal;
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
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
struct QOption_typeInt_typePtr_typeReal_typeVal {
    int64_t tag;
};
static_assert(sizeof(struct QOption_typeInt_typePtr_typeReal_typeVal) == 8, layout_QOption_typeInt_typePtr_typeReal_typeVal_size);
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
typedef const QException * quest_sig_questlang__ssa__Parser_readError;
typedef QTuple_QVal_QVal_QVal * (*quest_sig_questlang__ssa__Parser_readUnit)(QString * text);
#ifdef __cplusplus
}
#endif
#endif
