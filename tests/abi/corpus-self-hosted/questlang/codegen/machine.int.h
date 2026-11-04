#ifndef QUEST_INTF_QUESTLANG__CODEGEN__MACHINE_H
#define QUEST_INTF_QUESTLANG__CODEGEN__MACHINE_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/codegen/target.int.h"
#include "collections/vector.int.h"
#include "collections/bitset.int.h"
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
#ifndef QUEST_TYPE_QTuple_QVal_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_Int_QVal_TYPEDEF
typedef struct QTuple_QVal_Int_QVal QTuple_QVal_Int_QVal;
#endif
#ifndef QUEST_TYPE_QOption_classInt_classReal_TYPEDEF
#define QUEST_TYPE_QOption_classInt_classReal_TYPEDEF
typedef struct QOption_classInt_classReal QOption_classInt_classReal;
#endif
#ifndef QUEST_TYPE_QTuple_QClosure_QClosure_128bc3c9c5d535b4_TYPEDEF
#define QUEST_TYPE_QTuple_QClosure_QClosure_128bc3c9c5d535b4_TYPEDEF
typedef struct QTuple_QClosure_QClosure_128bc3c9c5d535b4 QTuple_QClosure_QClosure_128bc3c9c5d535b4;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QVal_QArray_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QVal_QArray_QVal_TYPEDEF
typedef struct QTuple_QArray_QVal_QArray_QVal QTuple_QArray_QVal_QArray_QVal;
#endif
#ifndef QUEST_TYPE_QOption_kindBranch_kindC_7d8ae4b5f95ba23a_DEFINED
#define QUEST_TYPE_QOption_kindBranch_kindC_7d8ae4b5f95ba23a_DEFINED
struct QOption_kindBranch_kindC_7d8ae4b5f95ba23a {
    int64_t tag;
};
static_assert(sizeof(struct QOption_kindBranch_kindC_7d8ae4b5f95ba23a) == 8, layout_QOption_kindBranch_kindC_7d8ae4b5f95ba23a_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_Bool_DEFINED
#define QUEST_TYPE_QTuple_Int_Bool_DEFINED
struct QTuple_Int_Bool {
    QInt _0;
    QBoolSlot _1;
};
static_assert(offsetof(struct QTuple_Int_Bool, _0) == 0, layout_QTuple_Int_Bool__0);
static_assert(offsetof(struct QTuple_Int_Bool, _1) == 8, layout_QTuple_Int_Bool__1);
static_assert(sizeof(struct QTuple_Int_Bool) == 16, layout_QTuple_Int_Bool_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_kindBranc_0424c7e5eabdd0e7_DEFINED
#define QUEST_TYPE_QTuple_QOption_kindBranc_0424c7e5eabdd0e7_DEFINED
struct QTuple_QOption_kindBranc_0424c7e5eabdd0e7 {
    QOption_kindBranch_kindC_7d8ae4b5f95ba23a * _0;
    QArray * _1;
    QInt _2;
    QInt _3;
};
static_assert(offsetof(struct QTuple_QOption_kindBranc_0424c7e5eabdd0e7, _0) == 0, layout_QTuple_QOption_kindBranc_0424c7e5eabdd0e7__0);
static_assert(offsetof(struct QTuple_QOption_kindBranc_0424c7e5eabdd0e7, _1) == 8, layout_QTuple_QOption_kindBranc_0424c7e5eabdd0e7__1);
static_assert(offsetof(struct QTuple_QOption_kindBranc_0424c7e5eabdd0e7, _2) == 16, layout_QTuple_QOption_kindBranc_0424c7e5eabdd0e7__2);
static_assert(offsetof(struct QTuple_QOption_kindBranc_0424c7e5eabdd0e7, _3) == 24, layout_QTuple_QOption_kindBranc_0424c7e5eabdd0e7__3);
static_assert(sizeof(struct QTuple_QOption_kindBranc_0424c7e5eabdd0e7) == 32, layout_QTuple_QOption_kindBranc_0424c7e5eabdd0e7_size);
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_Bool_DEFINED
struct QTuple_QVal_QVal_Bool {
    QVal _0;
    QVal _1;
    QBoolSlot _2;
};
static_assert(offsetof(struct QTuple_QVal_QVal_Bool, _0) == 0, layout_QTuple_QVal_QVal_Bool__0);
static_assert(offsetof(struct QTuple_QVal_QVal_Bool, _1) == 8, layout_QTuple_QVal_QVal_Bool__1);
static_assert(offsetof(struct QTuple_QVal_QVal_Bool, _2) == 16, layout_QTuple_QVal_QVal_Bool__2);
static_assert(sizeof(struct QTuple_QVal_QVal_Bool) == 24, layout_QTuple_QVal_QVal_Bool_size);
#endif
#ifndef QUEST_TYPE_QTuple_QVal_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_Int_QVal_DEFINED
struct QTuple_QVal_Int_QVal {
    QVal _0;
    QInt _1;
    QVal _2;
};
static_assert(offsetof(struct QTuple_QVal_Int_QVal, _0) == 0, layout_QTuple_QVal_Int_QVal__0);
static_assert(offsetof(struct QTuple_QVal_Int_QVal, _1) == 8, layout_QTuple_QVal_Int_QVal__1);
static_assert(offsetof(struct QTuple_QVal_Int_QVal, _2) == 16, layout_QTuple_QVal_Int_QVal__2);
static_assert(sizeof(struct QTuple_QVal_Int_QVal) == 24, layout_QTuple_QVal_Int_QVal_size);
#endif
#ifndef QUEST_TYPE_QOption_classInt_classReal_DEFINED
#define QUEST_TYPE_QOption_classInt_classReal_DEFINED
struct QOption_classInt_classReal {
    int64_t tag;
};
static_assert(sizeof(struct QOption_classInt_classReal) == 8, layout_QOption_classInt_classReal_size);
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
static_assert(offsetof(struct QTuple_QClosure_QClosure_128bc3c9c5d535b4, _0) == 0, layout_QTuple_QClosure_QClosure_128bc3c9c5d535b4__0);
static_assert(offsetof(struct QTuple_QClosure_QClosure_128bc3c9c5d535b4, _1) == 8, layout_QTuple_QClosure_QClosure_128bc3c9c5d535b4__1);
static_assert(offsetof(struct QTuple_QClosure_QClosure_128bc3c9c5d535b4, _2) == 16, layout_QTuple_QClosure_QClosure_128bc3c9c5d535b4__2);
static_assert(offsetof(struct QTuple_QClosure_QClosure_128bc3c9c5d535b4, _3) == 24, layout_QTuple_QClosure_QClosure_128bc3c9c5d535b4__3);
static_assert(offsetof(struct QTuple_QClosure_QClosure_128bc3c9c5d535b4, _4) == 32, layout_QTuple_QClosure_QClosure_128bc3c9c5d535b4__4);
static_assert(offsetof(struct QTuple_QClosure_QClosure_128bc3c9c5d535b4, _5) == 40, layout_QTuple_QClosure_QClosure_128bc3c9c5d535b4__5);
static_assert(sizeof(struct QTuple_QClosure_QClosure_128bc3c9c5d535b4) == 48, layout_QTuple_QClosure_QClosure_128bc3c9c5d535b4_size);
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QVal_QArray_QVal_DEFINED
#define QUEST_TYPE_QTuple_QArray_QVal_QArray_QVal_DEFINED
struct QTuple_QArray_QVal_QArray_QVal {
    QArray * _0;
    QArray * _1;
};
static_assert(offsetof(struct QTuple_QArray_QVal_QArray_QVal, _0) == 0, layout_QTuple_QArray_QVal_QArray_QVal__0);
static_assert(offsetof(struct QTuple_QArray_QVal_QArray_QVal, _1) == 8, layout_QTuple_QArray_QVal_QArray_QVal__1);
static_assert(sizeof(struct QTuple_QArray_QVal_QArray_QVal) == 16, layout_QTuple_QArray_QVal_QArray_QVal_size);
#endif
typedef QOption_kindBranch_kindC_7d8ae4b5f95ba23a * quest_type_questlang__codegen__Machine_Kind;
typedef QTuple_Int_Bool * quest_type_questlang__codegen__Machine_Operand;
typedef QTuple_QOption_kindBranc_0424c7e5eabdd0e7 * quest_type_questlang__codegen__Machine_Inst;
typedef QTuple_QVal_QVal_Bool * quest_type_questlang__codegen__Machine_Block;
typedef QTuple_QVal_Int_QVal * quest_type_questlang__codegen__Machine_Function;
typedef QTuple_QClosure_QClosure_128bc3c9c5d535b4 * quest_type_questlang__codegen__Machine_Lowering;
typedef QTuple_QArray_QVal_QArray_QVal * quest_type_questlang__codegen__Machine_Live;
typedef QTuple_QVal_Int_QVal * (*quest_sig_questlang__codegen__Machine_newFunction)(QInt physical);
typedef QInt (*quest_sig_questlang__codegen__Machine_newBlock)(QTuple_QVal_Int_QVal * f);
typedef QTuple_QVal_QVal_Bool * (*quest_sig_questlang__codegen__Machine_block)(QTuple_QVal_Int_QVal * f, QInt b);
typedef QInt (*quest_sig_questlang__codegen__Machine_newVirtual)(QTuple_QVal_Int_QVal * f, QOption_classInt_classReal * c);
typedef QInt (*quest_sig_questlang__codegen__Machine_addParam)(QTuple_QVal_Int_QVal * f, QInt b, QOption_classInt_classReal * c);
typedef void (*quest_sig_questlang__codegen__Machine_append)(QTuple_QVal_Int_QVal * f, QInt b, QTuple_QOption_kindBranc_0424c7e5eabdd0e7 * i);
typedef QBool (*quest_sig_questlang__codegen__Machine_isVirtual)(QTuple_QVal_Int_QVal * f, QInt r);
typedef QInt (*quest_sig_questlang__codegen__Machine_index)(QTuple_QVal_Int_QVal * f, QInt r);
typedef QOption_classInt_classReal * (*quest_sig_questlang__codegen__Machine_virtualClass)(QTuple_QVal_Int_QVal * f, QInt r);
typedef QInt (*quest_sig_questlang__codegen__Machine_virtuals)(QTuple_QVal_Int_QVal * f);
typedef QTuple_Int_Bool * (*quest_sig_questlang__codegen__Machine_reads)(QInt r);
typedef QTuple_Int_Bool * (*quest_sig_questlang__codegen__Machine_writes)(QInt r);
typedef QOption_kindBranch_kindC_7d8ae4b5f95ba23a * quest_sig_questlang__codegen__Machine_kindOrdinary;
typedef QOption_kindBranch_kindC_7d8ae4b5f95ba23a * quest_sig_questlang__codegen__Machine_kindMove;
typedef QOption_kindBranch_kindC_7d8ae4b5f95ba23a * quest_sig_questlang__codegen__Machine_kindJump;
typedef QOption_kindBranch_kindC_7d8ae4b5f95ba23a * quest_sig_questlang__codegen__Machine_kindBranch;
typedef QOption_kindBranch_kindC_7d8ae4b5f95ba23a * quest_sig_questlang__codegen__Machine_kindCall;
typedef QOption_kindBranch_kindC_7d8ae4b5f95ba23a * quest_sig_questlang__codegen__Machine_kindReturn;
typedef QTuple_QOption_kindBranc_0424c7e5eabdd0e7 * (*quest_sig_questlang__codegen__Machine_inst)(QOption_kindBranch_kindC_7d8ae4b5f95ba23a * kind, QArray * operands, QInt op, QInt target);
typedef QBool (*quest_sig_questlang__codegen__Machine_isKind)(QTuple_QOption_kindBranc_0424c7e5eabdd0e7 * i, QOption_kindBranch_kindC_7d8ae4b5f95ba23a * k);
typedef QString * (*quest_sig_questlang__codegen__Machine_kindName)(QOption_kindBranch_kindC_7d8ae4b5f95ba23a * k);
typedef void (*quest_sig_questlang__codegen__Machine_removeDead)(QTuple_QVal_Int_QVal * f, QClosure * pure);
typedef QArray * (*quest_sig_questlang__codegen__Machine_successors)(QTuple_QVal_Int_QVal * f, QInt b);
typedef QArray * (*quest_sig_questlang__codegen__Machine_order)(QTuple_QVal_Int_QVal * f);
typedef QArray * (*quest_sig_questlang__codegen__Machine_loopDepths)(QTuple_QVal_Int_QVal * f);
typedef QTuple_QArray_QVal_QArray_QVal * (*quest_sig_questlang__codegen__Machine_live)(QTuple_QVal_Int_QVal * f);
typedef QString * (*quest_sig_questlang__codegen__Machine_format)(QTuple_QVal_Int_QVal * f, QClosure * name, QClosure * line);
#ifdef __cplusplus
}
#endif
#endif
