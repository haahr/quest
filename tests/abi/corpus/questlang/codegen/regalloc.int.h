#ifndef QUEST_INTF_QUESTLANG__CODEGEN__REGALLOC_H
#define QUEST_INTF_QUESTLANG__CODEGEN__REGALLOC_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/codegen/target.int.h"
#include "questlang/codegen/machine.int.h"
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_Int_Int_TYPEDEF
typedef struct QTuple_Int_Int_Int_Int QTuple_Int_Int_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QArray_Int_d8309201fbf75735_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QArray_Int_d8309201fbf75735_TYPEDEF
typedef struct QTuple_QArray_QArray_Int_d8309201fbf75735 QTuple_QArray_QArray_Int_d8309201fbf75735;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_Int_QVal_TYPEDEF
typedef struct QTuple_QVal_Int_QVal QTuple_QVal_Int_QVal;
#endif
#ifndef QUEST_TYPE_QOption_classInt_classReal_TYPEDEF
#define QUEST_TYPE_QOption_classInt_classReal_TYPEDEF
typedef struct QOption_classInt_classReal QOption_classInt_classReal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_TYPEDEF
#define QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_TYPEDEF
typedef struct QTuple_String_QOption_classInt_classReal_end QTuple_String_QOption_classInt_classReal_end;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_TYPEDEF
typedef struct QTuple_QArray_QTuple_Str_822a60fcf247226d QTuple_QArray_QTuple_Str_822a60fcf247226d;
#endif
#ifndef QUEST_TYPE_QOption_kindBranch_kindC_7d8ae4b5f95ba23a_TYPEDEF
#define QUEST_TYPE_QOption_kindBranch_kindC_7d8ae4b5f95ba23a_TYPEDEF
typedef struct QOption_kindBranch_kindC_7d8ae4b5f95ba23a QOption_kindBranch_kindC_7d8ae4b5f95ba23a;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Bool_TYPEDEF
typedef struct QTuple_Int_Bool QTuple_Int_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_kindBranc_0424c7e5eabdd0e7_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_kindBranc_0424c7e5eabdd0e7_TYPEDEF
typedef struct QTuple_QOption_kindBranc_0424c7e5eabdd0e7 QTuple_QOption_kindBranc_0424c7e5eabdd0e7;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_QVal_QVal_Bool QTuple_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QClosure_QClosure_128bc3c9c5d535b4_TYPEDEF
#define QUEST_TYPE_QTuple_QClosure_QClosure_128bc3c9c5d535b4_TYPEDEF
typedef struct QTuple_QClosure_QClosure_128bc3c9c5d535b4 QTuple_QClosure_QClosure_128bc3c9c5d535b4;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_Int_Int_DEFINED
struct QTuple_Int_Int_Int_Int {
    QInt _0;
    QInt _1;
    QInt _2;
    QInt _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QArray_Int_d8309201fbf75735_DEFINED
#define QUEST_TYPE_QTuple_QArray_QArray_Int_d8309201fbf75735_DEFINED
struct QTuple_QArray_QArray_Int_d8309201fbf75735 {
    QArray * _0;
    QArray * _1;
    QArray * _2;
    QArray * _3;
    QArray * _4;
    QArray * _5;
    QArray * _6;
    QArray * _7;
    QArray * _8;
    QArray * _9;
    QArray * _10;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_Int_QVal_DEFINED
struct QTuple_QVal_Int_QVal {
    QVal _0;
    QInt _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QOption_classInt_classReal_DEFINED
#define QUEST_TYPE_QOption_classInt_classReal_DEFINED
struct QOption_classInt_classReal {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_DEFINED
#define QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_DEFINED
struct QTuple_String_QOption_classInt_classReal_end {
    QString * _0;
    QOption_classInt_classReal * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_DEFINED
#define QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_DEFINED
struct QTuple_QArray_QTuple_Str_822a60fcf247226d {
    QArray * _0;
    QArray * _1;
    QArray * _2;
    QArray * _3;
    QArray * _4;
    QArray * _5;
    QInt _6;
    QInt _7;
};
#endif
#ifndef QUEST_TYPE_QOption_kindBranch_kindC_7d8ae4b5f95ba23a_DEFINED
#define QUEST_TYPE_QOption_kindBranch_kindC_7d8ae4b5f95ba23a_DEFINED
struct QOption_kindBranch_kindC_7d8ae4b5f95ba23a {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_Bool_DEFINED
#define QUEST_TYPE_QTuple_Int_Bool_DEFINED
struct QTuple_Int_Bool {
    QInt _0;
    QBoolSlot _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QOption_kindBranc_0424c7e5eabdd0e7_DEFINED
#define QUEST_TYPE_QTuple_QOption_kindBranc_0424c7e5eabdd0e7_DEFINED
struct QTuple_QOption_kindBranc_0424c7e5eabdd0e7 {
    QOption_kindBranch_kindC_7d8ae4b5f95ba23a * _0;
    QArray * _1;
    QInt _2;
    QInt _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_Bool_DEFINED
struct QTuple_QVal_QVal_Bool {
    QVal _0;
    QVal _1;
    QBoolSlot _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QClosure_QClosure_128bc3c9c5d535b4_DEFINED
#define QUEST_TYPE_QTuple_QClosure_QClosure_128bc3c9c5d535b4_DEFINED
struct QTuple_QClosure_QClosure_128bc3c9c5d535b4 {
    QClosure * _0;
    QClosure * _1;
    QClosure * _2;
    QArray * _3;
    QClosure * _4;
    QClosure * _5;
};
#endif
typedef QTuple_Int_Int_Int_Int * quest_type_questlang__codegen__Regalloc_Move;
typedef QTuple_QArray_QArray_Int_d8309201fbf75735 * quest_type_questlang__codegen__Regalloc_Allocation;
typedef QInt quest_sig_questlang__codegen__Regalloc_memory;
typedef QTuple_QArray_QArray_Int_d8309201fbf75735 * (*quest_sig_questlang__codegen__Regalloc_allocate)(QTuple_QVal_Int_QVal * f, QTuple_QArray_QTuple_Str_822a60fcf247226d * t, QClosure * rematerializable, QClosure * cold);
typedef QInt (*quest_sig_questlang__codegen__Regalloc_home)(QTuple_QArray_QArray_Int_d8309201fbf75735 * a, QInt v, QInt p);
typedef QBool (*quest_sig_questlang__codegen__Regalloc_needsSlot)(QTuple_QArray_QArray_Int_d8309201fbf75735 * a, QInt v);
typedef QArray * (*quest_sig_questlang__codegen__Regalloc_shareSlots)(QTuple_QVal_Int_QVal * f, QTuple_QArray_QArray_Int_d8309201fbf75735 * a, QTuple_QClosure_QClosure_128bc3c9c5d535b4 * lowering, QClosure * kind);
typedef void (*quest_sig_questlang__codegen__Regalloc_rewrite)(QTuple_QVal_Int_QVal * f, QTuple_QArray_QArray_Int_d8309201fbf75735 * a, QTuple_QClosure_QClosure_128bc3c9c5d535b4 * lowering);
#ifdef __cplusplus
}
#endif
#endif
