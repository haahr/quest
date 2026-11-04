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
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_QVal_Bool_DEFINED
struct QTuple_String_QVal_QVal_Bool {
    QString * _0;
    QVal _1;
    QVal _2;
    QBoolSlot _3;
};
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
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c_DEFINED
struct RecGroup0_0_QTuple_Strin_9d01f59cb270e31c {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_d76052ac4845c382_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_d76052ac4845c382_DEFINED
struct RecGroup0_0_QTuple_Self1_d76052ac4845c382 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__6296130457467eeb_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__6296130457467eeb_DEFINED
struct RecGroup0_0_QTuple_QVal__6296130457467eeb {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_677fd9955907c104_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_677fd9955907c104_DEFINED
struct RecGroup0_0_QTuple_Self1_677fd9955907c104 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_9fa51444ab435999_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_9fa51444ab435999_DEFINED
struct RecGroup0_0_QTuple_Self1_9fa51444ab435999 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__49536c8a5b3334ae_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__49536c8a5b3334ae_DEFINED
struct RecGroup0_0_QTuple_QVal__49536c8a5b3334ae {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7_DEFINED
struct RecGroup0_0_QTuple_QVal__62f7bdc90afd8ed7 {
    QVal _0;
    QVal _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917_DEFINED
struct RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__512028a68c9e3086_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__512028a68c9e3086_DEFINED
struct RecGroup0_0_QTuple_QVal__512028a68c9e3086 {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_DEFINED
struct QTuple_QVal {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f_DEFINED
struct RecGroup0_0_QTuple_Strin_c9f96b844e52fd7f {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b_DEFINED
struct RecGroup0_0_QTuple_QVal__e401ce0b0b096e1b {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1_DEFINED
struct RecGroup0_0_QTuple_QVal__5329b8ba97de6cc1 {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__071ada0d0f71da3b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__071ada0d0f71da3b_DEFINED
struct RecGroup0_0_QTuple_QVal__071ada0d0f71da3b {
    QVal _0;
};
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
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
struct Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 {
    QTuple_String_Int_Int * _0;
    Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_S_2be6d72c360a809a_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_S_2be6d72c360a809a_DEFINED
struct RecGroup0_0_QTuple_Int_S_2be6d72c360a809a {
    QInt _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a_DEFINED
struct RecGroup0_0_QTuple_QTupl_96ec97a89d856d9a {
    RecGroup0_0_QTuple_Int_S_2be6d72c360a809a * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_d00a7583d32d9357_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_d00a7583d32d9357_DEFINED
struct RecGroup0_0_QTuple_Self2_d00a7583d32d9357 {
    RecGroup0_0_QTuple_Int_S_2be6d72c360a809a * _0;
};
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
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75_DEFINED
struct RecGroup0_0_QTuple_Self2_ae4a3e8f23e82f75 {
    RecGroup0_0_QTuple_Int_S_56c0b1530a080c74 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23_DEFINED
struct RecGroup0_0_QTuple_Int_Q_14744dffc3b82b23 {
    QInt _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QOption_modeOut_modeValue_modeVar_DEFINED
#define QUEST_TYPE_QOption_modeOut_modeValue_modeVar_DEFINED
struct QOption_modeOut_modeValue_modeVar {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_0fb8912496805194_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_0fb8912496805194_DEFINED
struct RecGroup0_0_QTuple_Int_Q_0fb8912496805194 {
    QInt _0;
    QVal _1;
    QVal _2;
    QOption_modeOut_modeValue_modeVar * _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6_DEFINED
struct RecGroup0_0_QTuple_Self2_b196bcbf619d9ab6 {
    RecGroup0_0_QTuple_Int_Q_0fb8912496805194 * _0;
};
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
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_Int_String_QVal_DEFINED
struct QTuple_Int_String_QVal {
    QInt _0;
    QString * _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_String_QVal_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_Int_String_QVal_end_DEFINED
struct QTuple_QTuple_Int_String_QVal_end {
    QTuple_Int_String_QVal * _0;
};
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
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end_DEFINED
struct QTuple_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_end {
    QTuple_Int_String_QVal_QVal_QVal_Bool_Bool * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_Int_QVal_DEFINED
struct QTuple_Int_QVal {
    QInt _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end_DEFINED
#define QUEST_TYPE_QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end_DEFINED
struct QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end {
    QInt _0;
    QVal _1;
    QVal _2;
    QOption_modeOut_modeValue_modeVar * _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1_DEFINED
#define QUEST_TYPE_QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1_DEFINED
struct QTuple_QTuple_Int_QVal_Q_3dc52e530dd3b9e1 {
    QTuple_Int_QVal_QVal_QOption_modeOut_modeValue_modeVar_end * _0;
};
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
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
struct QTuple_QTuple_String_Int_Int_end_QVal {
    QTuple_String_Int_Int * _0;
    QVal _1;
};
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
#endif
#ifndef QUEST_TYPE_QOption_interfaceUnit_moduleUnit_programUnit_DEFINED
#define QUEST_TYPE_QOption_interfaceUnit_moduleUnit_programUnit_DEFINED
struct QOption_interfaceUnit_moduleUnit_programUnit {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_String_QVal_String_DEFINED
#define QUEST_TYPE_QTuple_QArray_String_QVal_String_DEFINED
struct QTuple_QArray_String_QVal_String {
    QArray * _0;
    QVal _1;
    QString * _2;
};
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
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_DEFINED
struct QTuple_QTuple_QVal_end_QVal {
    QTuple_QVal * _0;
    QVal _1;
};
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
