#ifndef QUEST_INTF_QUESTLANG__CODEGEN__ARM64__ASM_H
#define QUEST_INTF_QUESTLANG__CODEGEN__ARM64__ASM_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/ssa/nodes.int.h"
#include "questlang/codegen/arm64/minst.int.h"
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
#endif
#ifndef QUEST_TYPE_QOption_relocGot_relocPage_relocTlv_TYPEDEF
#define QUEST_TYPE_QOption_relocGot_relocPage_relocTlv_TYPEDEF
typedef struct QOption_relocGot_relocPage_relocTlv QOption_relocGot_relocPage_relocTlv;
#endif
#ifndef QUEST_TYPE_QTuple_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_TYPEDEF
typedef struct QTuple_String QTuple_String;
#endif
#ifndef QUEST_TYPE_QTuple_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_TYPEDEF
typedef struct QTuple_Int QTuple_Int;
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
#ifndef QUEST_TYPE_QTuple_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_DEFINED
struct QTuple_String_String {
    QString * _0;
    QString * _1;
};
static_assert(offsetof(struct QTuple_String_String, _0) == 0, layout_QTuple_String_String__0);
static_assert(offsetof(struct QTuple_String_String, _1) == 8, layout_QTuple_String_String__1);
static_assert(sizeof(struct QTuple_String_String) == 16, layout_QTuple_String_String_size);
#endif
#ifndef QUEST_TYPE_QOption_relocGot_relocPage_relocTlv_DEFINED
#define QUEST_TYPE_QOption_relocGot_relocPage_relocTlv_DEFINED
struct QOption_relocGot_relocPage_relocTlv {
    int64_t tag;
};
static_assert(sizeof(struct QOption_relocGot_relocPage_relocTlv) == 8, layout_QOption_relocGot_relocPage_relocTlv_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
static_assert(offsetof(struct QTuple_String, _0) == 0, layout_QTuple_String__0);
static_assert(sizeof(struct QTuple_String) == 8, layout_QTuple_String_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_DEFINED
struct QTuple_Int {
    QInt _0;
};
static_assert(offsetof(struct QTuple_Int, _0) == 0, layout_QTuple_Int__0);
static_assert(sizeof(struct QTuple_Int) == 8, layout_QTuple_Int_size);
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
typedef QTuple_String_String * quest_type_questlang__codegen__arm64__Asm_DebugFunction;
typedef QString * (*quest_sig_questlang__codegen__arm64__Asm_symbol)(QString * name);
typedef QString * (*quest_sig_questlang__codegen__arm64__Asm_decimal)(QInt n);
typedef QString * (*quest_sig_questlang__codegen__arm64__Asm_reference)(QString * name, QOption_relocGot_relocPage_relocTlv * reloc, QBool pageOffset);
typedef QArray * (*quest_sig_questlang__codegen__arm64__Asm_functionStart)(QString * name, QBool exported);
typedef QArray * quest_sig_questlang__codegen__arm64__Asm_functionEnd;
typedef QArray * (*quest_sig_questlang__codegen__arm64__Asm_data)(QTuple_String_Bool_Bool__330533165c015005 * d);
typedef QArray * quest_sig_questlang__codegen__arm64__Asm_unitStart;
typedef QArray * quest_sig_questlang__codegen__arm64__Asm_unitEnd;
typedef QArray * (*quest_sig_questlang__codegen__arm64__Asm_files)(QArray * paths);
typedef QArray * (*quest_sig_questlang__codegen__arm64__Asm_debugInfo)(QString * file, QArray * functions);
#ifdef __cplusplus
}
#endif
#endif
