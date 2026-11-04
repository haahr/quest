#ifndef QUEST_INTF_QUESTLANG__SSA__ACCUMULATE_H
#define QUEST_INTF_QUESTLANG__SSA__ACCUMULATE_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/ssa/nodes.int.h"
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
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QVal QTuple_QVal_QVal_QVal;
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
#ifndef QUEST_TYPE_QTuple_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_DEFINED
struct QTuple_Int {
    QInt _0;
};
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
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QOption_pa_88eba21d06adf8d8_DEFINED
#define QUEST_TYPE_QTuple_QArray_QOption_pa_88eba21d06adf8d8_DEFINED
struct QTuple_QArray_QOption_pa_88eba21d06adf8d8 {
    QArray * _0;
    QArray * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_Int_DEFINED
struct QTuple_Int_Int_Int {
    QInt _0;
    QInt _1;
    QInt _2;
};
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
#endif
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
struct QOption_typeInt_typePtr_typeReal_typeVal {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_QArray_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_QArray_Int_DEFINED
struct QTuple_Int_QArray_Int {
    QInt _0;
    QArray * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end_DEFINED
#define QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end_DEFINED
struct QTuple_Int_QTuple_Int_QArray_Int_end_QTuple_Int_QArray_Int_end {
    QInt _0;
    QTuple_Int_QArray_Int * _1;
    QTuple_Int_QArray_Int * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_QArray_Int_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_Int_QArray_Int_end_DEFINED
struct QTuple_QTuple_Int_QArray_Int_end {
    QTuple_Int_QArray_Int * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_Int_DEFINED
#define QUEST_TYPE_QTuple_QArray_Int_DEFINED
struct QTuple_QArray_Int {
    QArray * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48_DEFINED
#define QUEST_TYPE_QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48_DEFINED
struct QTuple_Int_QArray_Int_QA_6b2f89db4ca75d48 {
    QInt _0;
    QArray * _1;
    QArray * _2;
    QTuple_Int_QArray_Int * _3;
};
#endif
#ifndef QUEST_TYPE_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_DEFINED
#define QUEST_TYPE_QOption_opAdd_opAnd_opAs_0293d61f8c93e36e_DEFINED
struct QOption_opAdd_opAnd_opAs_0293d61f8c93e36e {
    int64_t tag;
};
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
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end_DEFINED
struct QTuple_QTuple_QOption_opAdd_opA_c80de261989503a7_end {
    QTuple_QOption_opAdd_opA_c80de261989503a7 * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_QTuple_Int_QArray_Int_end_Int_DEFINED
struct QTuple_Int_QTuple_Int_QArray_Int_end_Int {
    QInt _0;
    QTuple_Int_QArray_Int * _1;
    QInt _2;
};
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
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QOption_419977b801e61011_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QOption_419977b801e61011_DEFINED
struct QTuple_QVal_QVal_QOption_419977b801e61011 {
    QVal _0;
    QVal _1;
    QOption_termBranch_QTupl_fb14070ded119ae8 * _2;
    QTuple_Int_Int_Int * _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_DEFINED
struct QTuple_Int_Int {
    QInt _0;
    QInt _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_DEFINED
struct QTuple_QVal_QVal_QVal {
    QVal _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_DEFINED
struct QTuple_String_Int {
    QString * _0;
    QInt _1;
};
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
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5_DEFINED
#define QUEST_TYPE_QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5_DEFINED
struct QTuple_QArray_QOption_wordInt_Q_0dc01402b7ce16e5 {
    QArray * _0;
};
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
#endif
#ifndef QUEST_TYPE_QTuple_String_Bool_Bool__330533165c015005_DEFINED
#define QUEST_TYPE_QTuple_String_Bool_Bool__330533165c015005_DEFINED
struct QTuple_String_Bool_Bool__330533165c015005 {
    QString * _0;
    QBoolSlot _1;
    QBoolSlot _2;
    QOption_contentsText_QTu_6bf31e28bb3b7166 * _3;
};
#endif
typedef void (*quest_sig_questlang__ssa__Accumulate_accumulateFunction)(QTuple_String_Bool_QVal__2ce49d2a84d5590a * f);
typedef void (*quest_sig_questlang__ssa__Accumulate_accumulateUnit)(QTuple_QVal_QVal_QVal * u);
#ifdef __cplusplus
}
#endif
#endif
