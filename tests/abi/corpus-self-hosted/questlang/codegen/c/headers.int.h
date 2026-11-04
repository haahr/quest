#ifndef QUEST_INTF_QUESTLANG__CODEGEN__C__HEADERS_H
#define QUEST_INTF_QUESTLANG__CODEGEN__C__HEADERS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/syntax/ast.int.h"
#include "questlang/types/symbols.int.h"
#include "questlang/types/env.int.h"
#include "questlang/modules/graph.int.h"
#include "questlang/modules/interfacecompiler.int.h"
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_String_QVal_QVal_Bool QTuple_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_TYPEDEF
typedef struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_9d01f59cb270e31c RecGroup0_0_QTuple_Strin_9d01f59cb270e31c;
#endif
#ifndef QUEST_TYPE_QTuple_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_TYPEDEF
typedef struct QTuple_String QTuple_String;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_d76052ac4845c382_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_d76052ac4845c382_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_d76052ac4845c382 RecGroup0_0_QTuple_Self1_d76052ac4845c382;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__6296130457467eeb_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__6296130457467eeb_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__6296130457467eeb RecGroup0_0_QTuple_QVal__6296130457467eeb;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_677fd9955907c104_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_677fd9955907c104_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_677fd9955907c104 RecGroup0_0_QTuple_Self1_677fd9955907c104;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_9fa51444ab435999_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_9fa51444ab435999_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_9fa51444ab435999 RecGroup0_0_QTuple_Self1_9fa51444ab435999;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__49536c8a5b3334ae_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__49536c8a5b3334ae_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__49536c8a5b3334ae RecGroup0_0_QTuple_QVal__49536c8a5b3334ae;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7 RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917 RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__512028a68c9e3086_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__512028a68c9e3086_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__512028a68c9e3086 RecGroup0_0_QTuple_QVal__512028a68c9e3086;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_TYPEDEF
typedef struct QTuple_QVal QTuple_QVal;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1 RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__071ada0d0f71da3b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__071ada0d0f71da3b_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__071ada0d0f71da3b RecGroup0_0_QTuple_QVal__071ada0d0f71da3b;
#endif
#ifndef QUEST_TYPE_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_TYPEDEF
#define QUEST_TYPE_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_TYPEDEF
typedef struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4 Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_TYPEDEF
typedef struct Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_S_2be6d72c360a809a_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_S_2be6d72c360a809a_TYPEDEF
typedef struct RecGroup0_0_QTuple_Int_S_2be6d72c360a809a RecGroup0_0_QTuple_Int_S_2be6d72c360a809a;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a_TYPEDEF
typedef struct RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_d00a7583d32d9357_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_d00a7583d32d9357_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self2_d00a7583d32d9357 RecGroup0_0_QTuple_Self2_d00a7583d32d9357;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74_TYPEDEF
typedef struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74 RecGroup0_0_QTuple_Int_S_56c0b1530a080c74;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75 RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23_TYPEDEF
typedef struct RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23 RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23;
#endif
#ifndef QUEST_TYPE_QOption_modeOut_modeValue_modeVar_TYPEDEF
#define QUEST_TYPE_QOption_modeOut_modeValue_modeVar_TYPEDEF
typedef struct QOption_modeOut_modeValue_modeVar QOption_modeOut_modeValue_modeVar;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_0fb8912496805194_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_0fb8912496805194_TYPEDEF
typedef struct RecGroup0_0_QTuple_Int_Q_0fb8912496805194 RecGroup0_0_QTuple_Int_Q_0fb8912496805194;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6 RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QOption_sigK_4e244b417c5c4821_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QOption_sigK_4e244b417c5c4821_TYPEDEF
typedef struct RecGroup0_0_QOption_sigK_4e244b417c5c4821 RecGroup0_0_QOption_sigK_4e244b417c5c4821;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_QVal_TYPEDEF
typedef struct QTuple_Int_String_QVal QTuple_Int_String_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_String_QVal_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_Int_String_QVal_end_TYPEDEF
typedef struct QTuple_QTuple_Int_String_QVal_end QTuple_QTuple_Int_String_QVal_end;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_TYPEDEF
typedef struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool QTuple_Int_String_QVal_QVal_QVal_Bool_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end_TYPEDEF
typedef struct QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QVal_TYPEDEF
typedef struct QTuple_Int_QVal QTuple_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end_TYPEDEF
typedef struct QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1_TYPEDEF
typedef struct QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1 QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1;
#endif
#ifndef QUEST_TYPE_QOption_sigKindBinding_Q_4da57efe619e4163_TYPEDEF
#define QUEST_TYPE_QOption_sigKindBinding_Q_4da57efe619e4163_TYPEDEF
typedef struct QOption_sigKindBinding_Q_4da57efe619e4163 QOption_sigKindBinding_Q_4da57efe619e4163;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_end_QVal QTuple_QTuple_String_Int_Int_end_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QVal_String_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QVal_String_QVal_QVal_TYPEDEF
typedef struct QTuple_Int_QVal_String_QVal_QVal QTuple_Int_QVal_String_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf_TYPEDEF
typedef struct QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf;
#endif
#ifndef QUEST_TYPE_QOption_interfaceUnit_moduleUnit_programUnit_TYPEDEF
#define QUEST_TYPE_QOption_interfaceUnit_moduleUnit_programUnit_TYPEDEF
typedef struct QOption_interfaceUnit_moduleUnit_programUnit QOption_interfaceUnit_moduleUnit_programUnit;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_String_QVal_String_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_String_QVal_String_TYPEDEF
typedef struct QTuple_QArray_String_QVal_String QTuple_QArray_String_QVal_String;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_interface_d389162375b8ce53_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_interface_d389162375b8ce53_TYPEDEF
typedef struct QTuple_QOption_interface_d389162375b8ce53 QTuple_QOption_interface_d389162375b8ce53;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_TYPEDEF
typedef struct QTuple_QTuple_QVal_end_QVal QTuple_QTuple_QVal_end_QVal;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_TYPEDEF
typedef struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f;
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
#ifndef QUEST_TYPE_QTuple_String_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_QVal_Bool_DEFINED
struct QTuple_String_QVal_QVal_Bool {
    QString * _0;
    QVal _1;
    QVal _2;
    QBoolSlot _3;
};
static_assert(offsetof(struct QTuple_String_QVal_QVal_Bool, _0) == 0, layout_QTuple_String_QVal_QVal_Bool__0);
static_assert(offsetof(struct QTuple_String_QVal_QVal_Bool, _1) == 8, layout_QTuple_String_QVal_QVal_Bool__1);
static_assert(offsetof(struct QTuple_String_QVal_QVal_Bool, _2) == 16, layout_QTuple_String_QVal_QVal_Bool__2);
static_assert(offsetof(struct QTuple_String_QVal_QVal_Bool, _3) == 24, layout_QTuple_String_QVal_QVal_Bool__3);
static_assert(sizeof(struct QTuple_String_QVal_QVal_Bool) == 32, layout_QTuple_String_QVal_QVal_Bool_size);
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_DEFINED
struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal {
    QVal _0;
    QString * _1;
    QVal _2;
    QBoolSlot _3;
    QVal _4;
    QVal _5;
    QVal _6;
    QVal _7;
    QVal _8;
    QVal _9;
};
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _0) == 0, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__0);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _1) == 8, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__1);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _2) == 16, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__2);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _3) == 24, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__3);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _4) == 32, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__4);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _5) == 40, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__5);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _6) == 48, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__6);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _7) == 56, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__7);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _8) == 64, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__8);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _9) == 72, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__9);
static_assert(sizeof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal) == 80, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
static_assert(offsetof(struct QTuple_String_Int_Int, _0) == 0, layout_QTuple_String_Int_Int__0);
static_assert(offsetof(struct QTuple_String_Int_Int, _1) == 8, layout_QTuple_String_Int_Int__1);
static_assert(offsetof(struct QTuple_String_Int_Int, _2) == 16, layout_QTuple_String_Int_Int__2);
static_assert(sizeof(struct QTuple_String_Int_Int) == 24, layout_QTuple_String_Int_Int_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c_DEFINED
struct RecGroup0_0_QTuple_Strin_9d01f59cb270e31c {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_9d01f59cb270e31c, _0) == 0, layout_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_9d01f59cb270e31c, _1) == 8, layout_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_9d01f59cb270e31c, _2) == 16, layout_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_Strin_9d01f59cb270e31c) == 24, layout_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
static_assert(offsetof(struct QTuple_String, _0) == 0, layout_QTuple_String__0);
static_assert(sizeof(struct QTuple_String) == 8, layout_QTuple_String_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_d76052ac4845c382_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_d76052ac4845c382_DEFINED
struct RecGroup0_0_QTuple_Self1_d76052ac4845c382 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_d76052ac4845c382, _0) == 0, layout_RecGroup0_0_QTuple_Self1_d76052ac4845c382__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_d76052ac4845c382) == 8, layout_RecGroup0_0_QTuple_Self1_d76052ac4845c382_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__6296130457467eeb_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__6296130457467eeb_DEFINED
struct RecGroup0_0_QTuple_QVal__6296130457467eeb {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__6296130457467eeb, _0) == 0, layout_RecGroup0_0_QTuple_QVal__6296130457467eeb__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__6296130457467eeb, _1) == 8, layout_RecGroup0_0_QTuple_QVal__6296130457467eeb__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__6296130457467eeb) == 16, layout_RecGroup0_0_QTuple_QVal__6296130457467eeb_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_677fd9955907c104_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_677fd9955907c104_DEFINED
struct RecGroup0_0_QTuple_Self1_677fd9955907c104 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
    QVal _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_677fd9955907c104, _0) == 0, layout_RecGroup0_0_QTuple_Self1_677fd9955907c104__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_677fd9955907c104, _1) == 8, layout_RecGroup0_0_QTuple_Self1_677fd9955907c104__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_677fd9955907c104) == 16, layout_RecGroup0_0_QTuple_Self1_677fd9955907c104_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_9fa51444ab435999_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_9fa51444ab435999_DEFINED
struct RecGroup0_0_QTuple_Self1_9fa51444ab435999 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_9fa51444ab435999, _0) == 0, layout_RecGroup0_0_QTuple_Self1_9fa51444ab435999__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_9fa51444ab435999) == 8, layout_RecGroup0_0_QTuple_Self1_9fa51444ab435999_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__49536c8a5b3334ae_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__49536c8a5b3334ae_DEFINED
struct RecGroup0_0_QTuple_QVal__49536c8a5b3334ae {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    QVal _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__49536c8a5b3334ae, _0) == 0, layout_RecGroup0_0_QTuple_QVal__49536c8a5b3334ae__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__49536c8a5b3334ae, _1) == 8, layout_RecGroup0_0_QTuple_QVal__49536c8a5b3334ae__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__49536c8a5b3334ae, _2) == 16, layout_RecGroup0_0_QTuple_QVal__49536c8a5b3334ae__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__49536c8a5b3334ae) == 24, layout_RecGroup0_0_QTuple_QVal__49536c8a5b3334ae_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7_DEFINED
struct RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7 {
    QVal _0;
    QVal _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7, _0) == 0, layout_RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7, _1) == 8, layout_RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7, _2) == 16, layout_RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7) == 24, layout_RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917_DEFINED
struct RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917, _0) == 0, layout_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917, _1) == 8, layout_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917, _2) == 16, layout_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917) == 24, layout_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__512028a68c9e3086_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__512028a68c9e3086_DEFINED
struct RecGroup0_0_QTuple_QVal__512028a68c9e3086 {
    QVal _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__512028a68c9e3086, _0) == 0, layout_RecGroup0_0_QTuple_QVal__512028a68c9e3086__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__512028a68c9e3086) == 8, layout_RecGroup0_0_QTuple_QVal__512028a68c9e3086_size);
#endif
#ifndef QUEST_TYPE_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_DEFINED
struct QTuple_QVal {
    QVal _0;
};
static_assert(offsetof(struct QTuple_QVal, _0) == 0, layout_QTuple_QVal__0);
static_assert(sizeof(struct QTuple_QVal) == 8, layout_QTuple_QVal_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f_DEFINED
struct RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f, _0) == 0, layout_RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f, _1) == 8, layout_RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f, _2) == 16, layout_RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f) == 24, layout_RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b_DEFINED
struct RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b {
    QVal _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b, _0) == 0, layout_RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b) == 8, layout_RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1_DEFINED
struct RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1 {
    QVal _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1, _0) == 0, layout_RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1) == 8, layout_RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__071ada0d0f71da3b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__071ada0d0f71da3b_DEFINED
struct RecGroup0_0_QTuple_QVal__071ada0d0f71da3b {
    QVal _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__071ada0d0f71da3b, _0) == 0, layout_RecGroup0_0_QTuple_QVal__071ada0d0f71da3b__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__071ada0d0f71da3b) == 8, layout_RecGroup0_0_QTuple_QVal__071ada0d0f71da3b_size);
#endif
#ifndef QUEST_TYPE_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_DEFINED
#define QUEST_TYPE_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_DEFINED
struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4 {
    int64_t tag;
    union {
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_kindAll_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
        } qo_kindAll;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_kindId_payload {
            QString * _0;
        } qo_kindId;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_kindManifest_payload {
            QString * _0;
            QString * _1;
        } qo_kindManifest;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_kindPower_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } qo_kindPower;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeAll_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
        } qo_typeAll;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeApp_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
            QVal _1;
        } qo_typeApp;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeArray_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } qo_typeArray;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeAuto_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QVal _2;
        } qo_typeAuto;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeExternal_payload {
            QString * _0;
        } qo_typeExternal;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeFun_payload {
            QVal _0;
            QVal _1;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
        } qo_typeFun;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeInfix_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
            QString * _1;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
        } qo_typeInfix;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeManifest_payload {
            QString * _0;
            QString * _1;
        } qo_typeManifest;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeOption_payload {
            QVal _0;
        } qo_typeOption;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeOut_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } qo_typeOut;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typePath_payload {
            QVal _0;
        } qo_typePath;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeRec_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
        } qo_typeRec;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeRecord_payload {
            QVal _0;
        } qo_typeRecord;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeTuple_payload {
            QVal _0;
        } qo_typeTuple;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeVar_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } qo_typeVar;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeVariant_payload {
            QVal _0;
        } qo_typeVariant;
    } u;
};
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_kindAll._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_kindAll__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_kindAll._1) == 16, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_kindAll__1);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_kindAll._2) == 24, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_kindAll__2);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_kindId._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_kindId__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_kindManifest._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_kindManifest__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_kindManifest._1) == 16, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_kindManifest__1);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_kindPower._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_kindPower__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeAll._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeAll__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeAll._1) == 16, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeAll__1);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeApp._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeApp__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeApp._1) == 16, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeApp__1);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeArray._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeArray__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeAuto._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeAuto__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeAuto._1) == 16, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeAuto__1);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeAuto._2) == 24, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeAuto__2);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeExternal._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeExternal__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeFun._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeFun__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeFun._1) == 16, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeFun__1);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeFun._2) == 24, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeFun__2);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeInfix._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeInfix__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeInfix._1) == 16, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeInfix__1);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeInfix._2) == 24, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeInfix__2);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeManifest._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeManifest__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeManifest._1) == 16, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeManifest__1);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeOption._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeOption__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeOut._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeOut__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typePath._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typePath__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeRec._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeRec__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeRec._1) == 16, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeRec__1);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeRec._2) == 24, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeRec__2);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeRecord._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeRecord__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeTuple._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeTuple__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeVar._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeVar__0);
static_assert(offsetof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4, u.qo_typeVariant._0) == 8, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_u_qo_typeVariant__0);
static_assert(sizeof(struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4) == 32, layout_Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_size);
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
struct Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 {
    QTuple_String_Int_Int * _0;
    Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4 * _1;
};
static_assert(offsetof(struct Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280, _0) == 0, layout_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280__0);
static_assert(offsetof(struct Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280, _1) == 8, layout_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280__1);
static_assert(sizeof(struct Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280) == 16, layout_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_S_2be6d72c360a809a_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_S_2be6d72c360a809a_DEFINED
struct RecGroup0_0_QTuple_Int_S_2be6d72c360a809a {
    QInt _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_S_2be6d72c360a809a, _0) == 0, layout_RecGroup0_0_QTuple_Int_S_2be6d72c360a809a__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_S_2be6d72c360a809a, _1) == 8, layout_RecGroup0_0_QTuple_Int_S_2be6d72c360a809a__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_S_2be6d72c360a809a, _2) == 16, layout_RecGroup0_0_QTuple_Int_S_2be6d72c360a809a__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_Int_S_2be6d72c360a809a) == 24, layout_RecGroup0_0_QTuple_Int_S_2be6d72c360a809a_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a_DEFINED
struct RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a {
    RecGroup0_0_QTuple_Int_S_2be6d72c360a809a * _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a, _0) == 0, layout_RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a) == 8, layout_RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_d00a7583d32d9357_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_d00a7583d32d9357_DEFINED
struct RecGroup0_0_QTuple_Self2_d00a7583d32d9357 {
    RecGroup0_0_QTuple_Int_S_2be6d72c360a809a * _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self2_d00a7583d32d9357, _0) == 0, layout_RecGroup0_0_QTuple_Self2_d00a7583d32d9357__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self2_d00a7583d32d9357) == 8, layout_RecGroup0_0_QTuple_Self2_d00a7583d32d9357_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74_DEFINED
struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74 {
    QInt _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
    QVal _3;
    QVal _4;
    QBoolSlot _5;
    QBoolSlot _6;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74, _0) == 0, layout_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74, _1) == 8, layout_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74, _2) == 16, layout_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74__2);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74, _3) == 24, layout_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74__3);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74, _4) == 32, layout_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74__4);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74, _5) == 40, layout_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74__5);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74, _6) == 48, layout_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74__6);
static_assert(sizeof(struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74) == 56, layout_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75_DEFINED
struct RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75 {
    RecGroup0_0_QTuple_Int_S_56c0b1530a080c74 * _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75, _0) == 0, layout_RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75) == 8, layout_RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23_DEFINED
struct RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23 {
    QInt _0;
    QVal _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23, _0) == 0, layout_RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23, _1) == 8, layout_RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23) == 16, layout_RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23_size);
#endif
#ifndef QUEST_TYPE_QOption_modeOut_modeValue_modeVar_DEFINED
#define QUEST_TYPE_QOption_modeOut_modeValue_modeVar_DEFINED
struct QOption_modeOut_modeValue_modeVar {
    int64_t tag;
};
static_assert(sizeof(struct QOption_modeOut_modeValue_modeVar) == 8, layout_QOption_modeOut_modeValue_modeVar_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_0fb8912496805194_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_0fb8912496805194_DEFINED
struct RecGroup0_0_QTuple_Int_Q_0fb8912496805194 {
    QInt _0;
    QVal _1;
    QVal _2;
    QOption_modeOut_modeValue_modeVar * _3;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_Q_0fb8912496805194, _0) == 0, layout_RecGroup0_0_QTuple_Int_Q_0fb8912496805194__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_Q_0fb8912496805194, _1) == 8, layout_RecGroup0_0_QTuple_Int_Q_0fb8912496805194__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_Q_0fb8912496805194, _2) == 16, layout_RecGroup0_0_QTuple_Int_Q_0fb8912496805194__2);
static_assert(offsetof(struct RecGroup0_0_QTuple_Int_Q_0fb8912496805194, _3) == 24, layout_RecGroup0_0_QTuple_Int_Q_0fb8912496805194__3);
static_assert(sizeof(struct RecGroup0_0_QTuple_Int_Q_0fb8912496805194) == 32, layout_RecGroup0_0_QTuple_Int_Q_0fb8912496805194_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6_DEFINED
struct RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6 {
    RecGroup0_0_QTuple_Int_Q_0fb8912496805194 * _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6, _0) == 0, layout_RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6) == 8, layout_RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QOption_sigK_4e244b417c5c4821_DEFINED
#define QUEST_TYPE_RecGroup0_0_QOption_sigK_4e244b417c5c4821_DEFINED
struct RecGroup0_0_QOption_sigK_4e244b417c5c4821 {
    int64_t tag;
    union {
        struct RecGroup0_0_QOption_sigK_4e244b417c5c4821_sigKindBinding_payload {
            RecGroup0_0_QTuple_Int_S_2be6d72c360a809a * _0;
        } qo_sigKindBinding;
        struct RecGroup0_0_QOption_sigK_4e244b417c5c4821_sigType_payload {
            RecGroup0_0_QTuple_Int_S_2be6d72c360a809a * _0;
        } qo_sigType;
        struct RecGroup0_0_QOption_sigK_4e244b417c5c4821_sigTypeBinding_payload {
            RecGroup0_0_QTuple_Int_S_56c0b1530a080c74 * _0;
        } qo_sigTypeBinding;
        struct RecGroup0_0_QOption_sigK_4e244b417c5c4821_sigTypeBindingGroup_payload {
            QInt _0;
            QVal _1;
        } qo_sigTypeBindingGroup;
        struct RecGroup0_0_QOption_sigK_4e244b417c5c4821_sigValue_payload {
            RecGroup0_0_QTuple_Int_Q_0fb8912496805194 * _0;
        } qo_sigValue;
    } u;
};
static_assert(offsetof(struct RecGroup0_0_QOption_sigK_4e244b417c5c4821, u.qo_sigKindBinding._0) == 8, layout_RecGroup0_0_QOption_sigK_4e244b417c5c4821_u_qo_sigKindBinding__0);
static_assert(offsetof(struct RecGroup0_0_QOption_sigK_4e244b417c5c4821, u.qo_sigType._0) == 8, layout_RecGroup0_0_QOption_sigK_4e244b417c5c4821_u_qo_sigType__0);
static_assert(offsetof(struct RecGroup0_0_QOption_sigK_4e244b417c5c4821, u.qo_sigTypeBinding._0) == 8, layout_RecGroup0_0_QOption_sigK_4e244b417c5c4821_u_qo_sigTypeBinding__0);
static_assert(offsetof(struct RecGroup0_0_QOption_sigK_4e244b417c5c4821, u.qo_sigTypeBindingGroup._0) == 8, layout_RecGroup0_0_QOption_sigK_4e244b417c5c4821_u_qo_sigTypeBindingGroup__0);
static_assert(offsetof(struct RecGroup0_0_QOption_sigK_4e244b417c5c4821, u.qo_sigTypeBindingGroup._1) == 16, layout_RecGroup0_0_QOption_sigK_4e244b417c5c4821_u_qo_sigTypeBindingGroup__1);
static_assert(offsetof(struct RecGroup0_0_QOption_sigK_4e244b417c5c4821, u.qo_sigValue._0) == 8, layout_RecGroup0_0_QOption_sigK_4e244b417c5c4821_u_qo_sigValue__0);
static_assert(sizeof(struct RecGroup0_0_QOption_sigK_4e244b417c5c4821) == 24, layout_RecGroup0_0_QOption_sigK_4e244b417c5c4821_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_Int_String_QVal_DEFINED
struct QTuple_Int_String_QVal {
    QInt _0;
    QString * _1;
    QVal _2;
};
static_assert(offsetof(struct QTuple_Int_String_QVal, _0) == 0, layout_QTuple_Int_String_QVal__0);
static_assert(offsetof(struct QTuple_Int_String_QVal, _1) == 8, layout_QTuple_Int_String_QVal__1);
static_assert(offsetof(struct QTuple_Int_String_QVal, _2) == 16, layout_QTuple_Int_String_QVal__2);
static_assert(sizeof(struct QTuple_Int_String_QVal) == 24, layout_QTuple_Int_String_QVal_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_String_QVal_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_Int_String_QVal_end_DEFINED
struct QTuple_QTuple_Int_String_QVal_end {
    QTuple_Int_String_QVal * _0;
};
static_assert(offsetof(struct QTuple_QTuple_Int_String_QVal_end, _0) == 0, layout_QTuple_QTuple_Int_String_QVal_end__0);
static_assert(sizeof(struct QTuple_QTuple_Int_String_QVal_end) == 8, layout_QTuple_QTuple_Int_String_QVal_end_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_DEFINED
#define QUEST_TYPE_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_DEFINED
struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool {
    QInt _0;
    QString * _1;
    QVal _2;
    QVal _3;
    QVal _4;
    QBoolSlot _5;
    QBoolSlot _6;
};
static_assert(offsetof(struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool, _0) == 0, layout_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool__0);
static_assert(offsetof(struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool, _1) == 8, layout_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool__1);
static_assert(offsetof(struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool, _2) == 16, layout_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool__2);
static_assert(offsetof(struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool, _3) == 24, layout_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool__3);
static_assert(offsetof(struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool, _4) == 32, layout_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool__4);
static_assert(offsetof(struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool, _5) == 40, layout_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool__5);
static_assert(offsetof(struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool, _6) == 48, layout_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool__6);
static_assert(sizeof(struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool) == 56, layout_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end_DEFINED
struct QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end {
    QTuple_Int_String_QVal_QVal_QVal_Bool_Bool * _0;
};
static_assert(offsetof(struct QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end, _0) == 0, layout_QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end__0);
static_assert(sizeof(struct QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end) == 8, layout_QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_Int_QVal_DEFINED
struct QTuple_Int_QVal {
    QInt _0;
    QVal _1;
};
static_assert(offsetof(struct QTuple_Int_QVal, _0) == 0, layout_QTuple_Int_QVal__0);
static_assert(offsetof(struct QTuple_Int_QVal, _1) == 8, layout_QTuple_Int_QVal__1);
static_assert(sizeof(struct QTuple_Int_QVal) == 16, layout_QTuple_Int_QVal_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end_DEFINED
#define QUEST_TYPE_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end_DEFINED
struct QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end {
    QInt _0;
    QVal _1;
    QVal _2;
    QOption_modeOut_modeValue_modeVar * _3;
};
static_assert(offsetof(struct QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end, _0) == 0, layout_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end__0);
static_assert(offsetof(struct QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end, _1) == 8, layout_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end__1);
static_assert(offsetof(struct QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end, _2) == 16, layout_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end__2);
static_assert(offsetof(struct QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end, _3) == 24, layout_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end__3);
static_assert(sizeof(struct QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end) == 32, layout_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1_DEFINED
#define QUEST_TYPE_QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1_DEFINED
struct QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1 {
    QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end * _0;
};
static_assert(offsetof(struct QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1, _0) == 0, layout_QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1__0);
static_assert(sizeof(struct QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1) == 8, layout_QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1_size);
#endif
#ifndef QUEST_TYPE_QOption_sigKindBinding_Q_4da57efe619e4163_DEFINED
#define QUEST_TYPE_QOption_sigKindBinding_Q_4da57efe619e4163_DEFINED
struct QOption_sigKindBinding_Q_4da57efe619e4163 {
    int64_t tag;
    union {
        struct QOption_sigKindBinding_Q_4da57efe619e4163_sigKindBinding_payload {
            QTuple_Int_String_QVal * _0;
        } qo_sigKindBinding;
        struct QOption_sigKindBinding_Q_4da57efe619e4163_sigType_payload {
            QTuple_Int_String_QVal * _0;
        } qo_sigType;
        struct QOption_sigKindBinding_Q_4da57efe619e4163_sigTypeBinding_payload {
            QTuple_Int_String_QVal_QVal_QVal_Bool_Bool * _0;
        } qo_sigTypeBinding;
        struct QOption_sigKindBinding_Q_4da57efe619e4163_sigTypeBindingGroup_payload {
            QInt _0;
            QVal _1;
        } qo_sigTypeBindingGroup;
        struct QOption_sigKindBinding_Q_4da57efe619e4163_sigValue_payload {
            QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end * _0;
        } qo_sigValue;
    } u;
};
static_assert(offsetof(struct QOption_sigKindBinding_Q_4da57efe619e4163, u.qo_sigKindBinding._0) == 8, layout_QOption_sigKindBinding_Q_4da57efe619e4163_u_qo_sigKindBinding__0);
static_assert(offsetof(struct QOption_sigKindBinding_Q_4da57efe619e4163, u.qo_sigType._0) == 8, layout_QOption_sigKindBinding_Q_4da57efe619e4163_u_qo_sigType__0);
static_assert(offsetof(struct QOption_sigKindBinding_Q_4da57efe619e4163, u.qo_sigTypeBinding._0) == 8, layout_QOption_sigKindBinding_Q_4da57efe619e4163_u_qo_sigTypeBinding__0);
static_assert(offsetof(struct QOption_sigKindBinding_Q_4da57efe619e4163, u.qo_sigTypeBindingGroup._0) == 8, layout_QOption_sigKindBinding_Q_4da57efe619e4163_u_qo_sigTypeBindingGroup__0);
static_assert(offsetof(struct QOption_sigKindBinding_Q_4da57efe619e4163, u.qo_sigTypeBindingGroup._1) == 16, layout_QOption_sigKindBinding_Q_4da57efe619e4163_u_qo_sigTypeBindingGroup__1);
static_assert(offsetof(struct QOption_sigKindBinding_Q_4da57efe619e4163, u.qo_sigValue._0) == 8, layout_QOption_sigKindBinding_Q_4da57efe619e4163_u_qo_sigValue__0);
static_assert(sizeof(struct QOption_sigKindBinding_Q_4da57efe619e4163) == 24, layout_QOption_sigKindBinding_Q_4da57efe619e4163_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
struct QTuple_QTuple_String_Int_Int_end_QVal {
    QTuple_String_Int_Int * _0;
    QVal _1;
};
static_assert(offsetof(struct QTuple_QTuple_String_Int_Int_end_QVal, _0) == 0, layout_QTuple_QTuple_String_Int_Int_end_QVal__0);
static_assert(offsetof(struct QTuple_QTuple_String_Int_Int_end_QVal, _1) == 8, layout_QTuple_QTuple_String_Int_Int_end_QVal__1);
static_assert(sizeof(struct QTuple_QTuple_String_Int_Int_end_QVal) == 16, layout_QTuple_QTuple_String_Int_Int_end_QVal_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_QVal_String_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_Int_QVal_String_QVal_QVal_DEFINED
struct QTuple_Int_QVal_String_QVal_QVal {
    QInt _0;
    QVal _1;
    QString * _2;
    QVal _3;
    QVal _4;
};
static_assert(offsetof(struct QTuple_Int_QVal_String_QVal_QVal, _0) == 0, layout_QTuple_Int_QVal_String_QVal_QVal__0);
static_assert(offsetof(struct QTuple_Int_QVal_String_QVal_QVal, _1) == 8, layout_QTuple_Int_QVal_String_QVal_QVal__1);
static_assert(offsetof(struct QTuple_Int_QVal_String_QVal_QVal, _2) == 16, layout_QTuple_Int_QVal_String_QVal_QVal__2);
static_assert(offsetof(struct QTuple_Int_QVal_String_QVal_QVal, _3) == 24, layout_QTuple_Int_QVal_String_QVal_QVal__3);
static_assert(offsetof(struct QTuple_Int_QVal_String_QVal_QVal, _4) == 32, layout_QTuple_Int_QVal_String_QVal_QVal__4);
static_assert(sizeof(struct QTuple_Int_QVal_String_QVal_QVal) == 40, layout_QTuple_Int_QVal_String_QVal_QVal_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf_DEFINED
struct QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf {
    QTuple_String_QVal_QVal_Bool * _0;
    Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal * _1;
    QString * _2;
    QVal _3;
    QString * _4;
    QArray * _5;
};
static_assert(offsetof(struct QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf, _0) == 0, layout_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf__0);
static_assert(offsetof(struct QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf, _1) == 8, layout_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf__1);
static_assert(offsetof(struct QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf, _2) == 16, layout_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf__2);
static_assert(offsetof(struct QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf, _3) == 24, layout_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf__3);
static_assert(offsetof(struct QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf, _4) == 32, layout_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf__4);
static_assert(offsetof(struct QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf, _5) == 40, layout_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf__5);
static_assert(sizeof(struct QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf) == 48, layout_QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf_size);
#endif
#ifndef QUEST_TYPE_QOption_interfaceUnit_moduleUnit_programUnit_DEFINED
#define QUEST_TYPE_QOption_interfaceUnit_moduleUnit_programUnit_DEFINED
struct QOption_interfaceUnit_moduleUnit_programUnit {
    int64_t tag;
};
static_assert(sizeof(struct QOption_interfaceUnit_moduleUnit_programUnit) == 8, layout_QOption_interfaceUnit_moduleUnit_programUnit_size);
#endif
#ifndef QUEST_TYPE_QTuple_QArray_String_QVal_String_DEFINED
#define QUEST_TYPE_QTuple_QArray_String_QVal_String_DEFINED
struct QTuple_QArray_String_QVal_String {
    QArray * _0;
    QVal _1;
    QString * _2;
};
static_assert(offsetof(struct QTuple_QArray_String_QVal_String, _0) == 0, layout_QTuple_QArray_String_QVal_String__0);
static_assert(offsetof(struct QTuple_QArray_String_QVal_String, _1) == 8, layout_QTuple_QArray_String_QVal_String__1);
static_assert(offsetof(struct QTuple_QArray_String_QVal_String, _2) == 16, layout_QTuple_QArray_String_QVal_String__2);
static_assert(sizeof(struct QTuple_QArray_String_QVal_String) == 24, layout_QTuple_QArray_String_QVal_String_size);
#endif
#ifndef QUEST_TYPE_QTuple_QOption_interface_d389162375b8ce53_DEFINED
#define QUEST_TYPE_QTuple_QOption_interface_d389162375b8ce53_DEFINED
struct QTuple_QOption_interface_d389162375b8ce53 {
    QOption_interfaceUnit_moduleUnit_programUnit * _0;
    QString * _1;
    QVal _2;
    QTuple_QArray_String_QVal_String * _3;
    QVal _4;
    QVal _5;
    QVal _6;
    QVal _7;
};
static_assert(offsetof(struct QTuple_QOption_interface_d389162375b8ce53, _0) == 0, layout_QTuple_QOption_interface_d389162375b8ce53__0);
static_assert(offsetof(struct QTuple_QOption_interface_d389162375b8ce53, _1) == 8, layout_QTuple_QOption_interface_d389162375b8ce53__1);
static_assert(offsetof(struct QTuple_QOption_interface_d389162375b8ce53, _2) == 16, layout_QTuple_QOption_interface_d389162375b8ce53__2);
static_assert(offsetof(struct QTuple_QOption_interface_d389162375b8ce53, _3) == 24, layout_QTuple_QOption_interface_d389162375b8ce53__3);
static_assert(offsetof(struct QTuple_QOption_interface_d389162375b8ce53, _4) == 32, layout_QTuple_QOption_interface_d389162375b8ce53__4);
static_assert(offsetof(struct QTuple_QOption_interface_d389162375b8ce53, _5) == 40, layout_QTuple_QOption_interface_d389162375b8ce53__5);
static_assert(offsetof(struct QTuple_QOption_interface_d389162375b8ce53, _6) == 48, layout_QTuple_QOption_interface_d389162375b8ce53__6);
static_assert(offsetof(struct QTuple_QOption_interface_d389162375b8ce53, _7) == 56, layout_QTuple_QOption_interface_d389162375b8ce53__7);
static_assert(sizeof(struct QTuple_QOption_interface_d389162375b8ce53) == 64, layout_QTuple_QOption_interface_d389162375b8ce53_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_DEFINED
struct QTuple_QTuple_QVal_end_QVal {
    QTuple_QVal * _0;
    QVal _1;
};
static_assert(offsetof(struct QTuple_QTuple_QVal_end_QVal, _0) == 0, layout_QTuple_QTuple_QVal_end_QVal__0);
static_assert(offsetof(struct QTuple_QTuple_QVal_end_QVal, _1) == 8, layout_QTuple_QTuple_QVal_end_QVal__1);
static_assert(sizeof(struct QTuple_QTuple_QVal_end_QVal) == 16, layout_QTuple_QTuple_QVal_end_QVal_size);
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_DEFINED
#define QUEST_TYPE_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_DEFINED
struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f {
    Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal * _0;
    Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal * _1;
    Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal * _2;
    QVal _3;
    QVal _4;
    QVal _5;
    QVal _6;
    QVal _7;
    QVal _8;
    QVal _9;
    QString * _10;
    QVal _11;
    QVal _12;
    QVal _13;
    QTuple_QTuple_QVal_end_QVal * _14;
    QVal _15;
    QVal _16;
    QVal _17;
    QBoolSlot _18;
    QBoolSlot _19;
    QBoolSlot _20;
    QBoolSlot _21;
    QVal _22;
};
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _0) == 0, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__0);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _1) == 8, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__1);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _2) == 16, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__2);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _3) == 24, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__3);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _4) == 32, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__4);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _5) == 40, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__5);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _6) == 48, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__6);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _7) == 56, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__7);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _8) == 64, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__8);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _9) == 72, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__9);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _10) == 80, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__10);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _11) == 88, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__11);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _12) == 96, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__12);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _13) == 104, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__13);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _14) == 112, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__14);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _15) == 120, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__15);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _16) == 128, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__16);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _17) == 136, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__17);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _18) == 144, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__18);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _19) == 152, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__19);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _20) == 160, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__20);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _21) == 168, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__21);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _22) == 176, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__22);
static_assert(sizeof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f) == 184, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_size);
#endif
typedef QTuple_String_String * quest_type_questlang__codegen__c__Headers_Artifacts;
typedef QString * (*quest_sig_questlang__codegen__c__Headers_compileInterfaceToHeader)(QTuple_String_QVal_QVal_Bool * decl, Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal * scope, QString * canonicalName);
typedef QString * (*quest_sig_questlang__codegen__c__Headers_interfaceHeaderFile)(QString * qi);
typedef QBool (*quest_sig_questlang__codegen__c__Headers_headerIsCurrent)(QString * qi, QString * header);
typedef QString * (*quest_sig_questlang__codegen__c__Headers_writeInterfaceHeader)(QTuple_QTuple_String_QVa_fa44c0bc3c99a9cf * compiled, QVal buildDir, QVal programDir, QTuple_QVal * res);
typedef QTuple_String_String * (*quest_sig_questlang__codegen__c__Headers_compileInterfaceWithHeader)(QString * file, QVal outputDir, QArray * includePaths, QVal buildDir, QVal programDir);
typedef QTuple_String_String * (*quest_sig_questlang__codegen__c__Headers_ensureResolvedInterfaceHeader)(QTuple_QOption_interface_d389162375b8ce53 * resolved, QString * buildDir, QTuple_QVal * res);
typedef QVal (*quest_sig_questlang__codegen__c__Headers_ensureImportedInterfaceHeader)(QString * name, Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f * e);
#ifdef __cplusplus
}
#endif
#endif
