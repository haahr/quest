#ifndef QUEST_INTF_QUESTLANG__SSA__STATICS_H
#define QUEST_INTF_QUESTLANG__SSA__STATICS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/ssa/nodes.int.h"
#include "questlang/codegen/staticdata.int.h"
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
#ifndef QUEST_TYPE_QTuple_String_String_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_Int_TYPEDEF
typedef struct QTuple_String_String_Int QTuple_String_String_Int;
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
#ifndef QUEST_TYPE_QTuple_String_String_QVal_String_String_String_QVal_String_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_QVal_String_String_String_QVal_String_Int_TYPEDEF
typedef struct QTuple_String_String_QVal_String_String_String_QVal_String_Int QTuple_String_String_QVal_String_String_String_QVal_String_Int;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_Int_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_String_Int_end_TYPEDEF
typedef struct QTuple_QTuple_String_String_Int_end QTuple_QTuple_String_String_Int_end;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_Strin_e02676d93d90c568_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_Strin_e02676d93d90c568_TYPEDEF
typedef struct QTuple_QVal_QTuple_Strin_e02676d93d90c568 QTuple_QVal_QTuple_Strin_e02676d93d90c568;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Str_966909f48bbe24d1_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Str_966909f48bbe24d1_TYPEDEF
typedef struct QTuple_QTuple_String_Str_966909f48bbe24d1 QTuple_QTuple_String_Str_966909f48bbe24d1;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_Int_end_Bool_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_String_Int_end_Bool_Bool_TYPEDEF
typedef struct QTuple_QTuple_String_String_Int_end_Bool_Bool QTuple_QTuple_String_String_Int_end_Bool_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_QTu_985437708e416f86_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QTuple_QTu_985437708e416f86_TYPEDEF
typedef struct QTuple_QArray_QTuple_QTu_985437708e416f86 QTuple_QArray_QTuple_QTu_985437708e416f86;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QTuple_String_String_Int_end_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QTuple_String_String_Int_end_TYPEDEF
typedef struct QTuple_Int_QTuple_String_String_Int_end QTuple_Int_QTuple_String_String_Int_end;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_String_String_Int_end_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QTuple_String_String_Int_end_TYPEDEF
typedef struct QTuple_QArray_QTuple_String_String_Int_end QTuple_QArray_QTuple_String_String_Int_end;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_String_String_Int_end_Int_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_String_String_Int_end_Int_Bool_TYPEDEF
typedef struct QTuple_String_QTuple_String_String_Int_end_Int_Bool QTuple_String_QTuple_String_String_Int_end_Int_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_Str_e17c6ec29546c79b_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QTuple_Str_e17c6ec29546c79b_TYPEDEF
typedef struct QTuple_QArray_QTuple_Str_e17c6ec29546c79b QTuple_QArray_QTuple_Str_e17c6ec29546c79b;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_QVal_QTuple_Strin_e02676d93d90c568_end_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QTuple_QVal_QTuple_Strin_e02676d93d90c568_end_TYPEDEF
typedef struct QTuple_QArray_QTuple_QVal_QTuple_Strin_e02676d93d90c568_end QTuple_QArray_QTuple_QVal_QTuple_Strin_e02676d93d90c568_end;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_TYPEDEF
typedef struct QTuple_Int_String QTuple_Int_String;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_Int_97c8fdb185623c6d_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QTuple_Int_97c8fdb185623c6d_TYPEDEF
typedef struct QTuple_QArray_QTuple_Int_97c8fdb185623c6d QTuple_QArray_QTuple_Int_97c8fdb185623c6d;
#endif
#ifndef QUEST_TYPE_QOption_payloadArray_QTu_86d6a7a3ccc30623_TYPEDEF
#define QUEST_TYPE_QOption_payloadArray_QTu_86d6a7a3ccc30623_TYPEDEF
typedef struct QOption_payloadArray_QTu_86d6a7a3ccc30623 QOption_payloadArray_QTu_86d6a7a3ccc30623;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Str_966feaa19dc543cd_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Str_966feaa19dc543cd_TYPEDEF
typedef struct QTuple_QTuple_String_Str_966feaa19dc543cd QTuple_QTuple_String_Str_966feaa19dc543cd;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_483bc82e07ff306c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_483bc82e07ff306c_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_483bc82e07ff306c RecGroup0_0_QTuple_Strin_483bc82e07ff306c;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QOption_kind_5404ddb6c01acca4_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QOption_kind_5404ddb6c01acca4_TYPEDEF
typedef struct RecGroup0_0_QOption_kind_5404ddb6c01acca4 RecGroup0_0_QOption_kind_5404ddb6c01acca4;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_TYPEDEF
typedef struct RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_194f294b44f1322f_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_194f294b44f1322f_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_194f294b44f1322f RecGroup0_0_QTuple_Strin_194f294b44f1322f;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_52d4a987f1a49725_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_52d4a987f1a49725_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_52d4a987f1a49725 RecGroup0_0_QTuple_Strin_52d4a987f1a49725;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_ad6fb8ee47ebf8e9_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_ad6fb8ee47ebf8e9_TYPEDEF
typedef struct RecGroup0_0_QTuple_QArra_ad6fb8ee47ebf8e9 RecGroup0_0_QTuple_QArra_ad6fb8ee47ebf8e9;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_8fcb1094f58faf54_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_8fcb1094f58faf54_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self2_8fcb1094f58faf54 RecGroup0_0_QTuple_Self2_8fcb1094f58faf54;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_c5f45c993819c661_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_c5f45c993819c661_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self2_c5f45c993819c661 RecGroup0_0_QTuple_Self2_c5f45c993819c661;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_701bb4382ecd036e_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_701bb4382ecd036e_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_701bb4382ecd036e RecGroup0_0_QTuple_Strin_701bb4382ecd036e;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_44826dd1448b0684_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_44826dd1448b0684_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_44826dd1448b0684 RecGroup0_0_QTuple_Strin_44826dd1448b0684;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_3b978c5cdd954e30_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_3b978c5cdd954e30_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self2_3b978c5cdd954e30 RecGroup0_0_QTuple_Self2_3b978c5cdd954e30;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_7e6c6e26396f582e_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_7e6c6e26396f582e_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_7e6c6e26396f582e RecGroup0_0_QTuple_Strin_7e6c6e26396f582e;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_cf1fea11f4f1fd73_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_cf1fea11f4f1fd73_TYPEDEF
typedef struct RecGroup0_0_QTuple_QArra_cf1fea11f4f1fd73 RecGroup0_0_QTuple_QArra_cf1fea11f4f1fd73;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_S_e030b7b17c66d57e_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_S_e030b7b17c66d57e_TYPEDEF
typedef struct RecGroup0_0_QTuple_Int_S_e030b7b17c66d57e RecGroup0_0_QTuple_Int_S_e030b7b17c66d57e;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QTupl_5b183cfbae3e8a30_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QTupl_5b183cfbae3e8a30_TYPEDEF
typedef struct RecGroup0_0_QTuple_QTupl_5b183cfbae3e8a30 RecGroup0_0_QTuple_QTupl_5b183cfbae3e8a30;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_4e8cc7c4db8085f3_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_4e8cc7c4db8085f3_TYPEDEF
typedef struct RecGroup0_0_QTuple_QArra_4e8cc7c4db8085f3 RecGroup0_0_QTuple_QArra_4e8cc7c4db8085f3;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_3e526ed08e667f25_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_3e526ed08e667f25_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_3e526ed08e667f25 RecGroup0_0_QTuple_Strin_3e526ed08e667f25;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_8fa9737dd5face61_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_8fa9737dd5face61_TYPEDEF
typedef struct RecGroup0_0_QTuple_QArra_8fa9737dd5face61 RecGroup0_0_QTuple_QArra_8fa9737dd5face61;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_13da4434cc3d7950_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_13da4434cc3d7950_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_13da4434cc3d7950 RecGroup0_0_QTuple_Strin_13da4434cc3d7950;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_ab137605dc72ed05_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_ab137605dc72ed05_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_ab137605dc72ed05 RecGroup0_0_QTuple_Strin_ab137605dc72ed05;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_8d79da5444c415a9_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_8d79da5444c415a9_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_8d79da5444c415a9 RecGroup0_0_QTuple_Strin_8d79da5444c415a9;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_33bcb62f0fe20d1e_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_33bcb62f0fe20d1e_TYPEDEF
typedef struct RecGroup0_0_QTuple_QArra_33bcb62f0fe20d1e RecGroup0_0_QTuple_QArra_33bcb62f0fe20d1e;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_0bf905da734c84fe_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_0bf905da734c84fe_TYPEDEF
typedef struct RecGroup0_0_QTuple_QArra_0bf905da734c84fe RecGroup0_0_QTuple_QArra_0bf905da734c84fe;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0909b0b2decf3db9_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0909b0b2decf3db9_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__0909b0b2decf3db9 RecGroup0_0_QTuple_QVal__0909b0b2decf3db9;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_edbf69e0a6017bff_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_edbf69e0a6017bff_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_edbf69e0a6017bff RecGroup0_0_QTuple_Strin_edbf69e0a6017bff;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QOption_tupl_05259466b555c52e_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QOption_tupl_05259466b555c52e_TYPEDEF
typedef struct RecGroup0_0_QOption_tupl_05259466b555c52e RecGroup0_0_QOption_tupl_05259466b555c52e;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_9e5a10d76b597163_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_9e5a10d76b597163_TYPEDEF
typedef struct RecGroup0_0_QTuple_QArra_9e5a10d76b597163 RecGroup0_0_QTuple_QArra_9e5a10d76b597163;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_9090d707cc236f33_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_9090d707cc236f33_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_9090d707cc236f33 RecGroup0_0_QTuple_Strin_9090d707cc236f33;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_5b49b3573fbebbdf_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_5b49b3573fbebbdf_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_5b49b3573fbebbdf RecGroup0_0_QTuple_Strin_5b49b3573fbebbdf;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_0b526577c1ff0fea_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_0b526577c1ff0fea_TYPEDEF
typedef struct RecGroup0_0_QTuple_QArra_0b526577c1ff0fea RecGroup0_0_QTuple_QArra_0b526577c1ff0fea;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_TYPEDEF
typedef struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5 RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874_TYPEDEF
typedef struct RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874;
#endif
#ifndef QUEST_TYPE_QTuple_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_DEFINED
struct QTuple_Int {
    QInt _0;
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
#ifndef QUEST_TYPE_QTuple_String_String_Int_DEFINED
#define QUEST_TYPE_QTuple_String_String_Int_DEFINED
struct QTuple_String_String_Int {
    QString * _0;
    QString * _1;
    QInt _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
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
#ifndef QUEST_TYPE_QTuple_String_String_QVal_String_String_String_QVal_String_Int_DEFINED
#define QUEST_TYPE_QTuple_String_String_QVal_String_String_String_QVal_String_Int_DEFINED
struct QTuple_String_String_QVal_String_String_String_QVal_String_Int {
    QString * _0;
    QString * _1;
    QVal _2;
    QString * _3;
    QString * _4;
    QString * _5;
    QVal _6;
    QString * _7;
    QInt _8;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_Int_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_String_Int_end_DEFINED
struct QTuple_QTuple_String_String_Int_end {
    QTuple_String_String_Int * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_Strin_e02676d93d90c568_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_Strin_e02676d93d90c568_DEFINED
struct QTuple_QVal_QTuple_Strin_e02676d93d90c568 {
    QVal _0;
    QTuple_String_String_Int * _1;
    QTuple_String_Int * _2;
    QBoolSlot _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Str_966909f48bbe24d1_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Str_966909f48bbe24d1_DEFINED
struct QTuple_QTuple_String_Str_966909f48bbe24d1 {
    QTuple_String_String_Int * _0;
    QTuple_String_Int * _1;
    QArray * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_Int_end_Bool_Bool_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_String_Int_end_Bool_Bool_DEFINED
struct QTuple_QTuple_String_String_Int_end_Bool_Bool {
    QTuple_String_String_Int * _0;
    QBoolSlot _1;
    QBoolSlot _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_QTu_985437708e416f86_DEFINED
#define QUEST_TYPE_QTuple_QArray_QTuple_QTu_985437708e416f86_DEFINED
struct QTuple_QArray_QTuple_QTu_985437708e416f86 {
    QArray * _0;
    QTuple_String_String_Int * _1;
    QArray * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_QTuple_String_String_Int_end_DEFINED
#define QUEST_TYPE_QTuple_Int_QTuple_String_String_Int_end_DEFINED
struct QTuple_Int_QTuple_String_String_Int_end {
    QInt _0;
    QTuple_String_String_Int * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_String_String_Int_end_DEFINED
#define QUEST_TYPE_QTuple_QArray_QTuple_String_String_Int_end_DEFINED
struct QTuple_QArray_QTuple_String_String_Int_end {
    QArray * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_String_String_Int_end_Int_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_String_String_Int_end_Int_Bool_DEFINED
struct QTuple_String_QTuple_String_String_Int_end_Int_Bool {
    QString * _0;
    QTuple_String_String_Int * _1;
    QInt _2;
    QBoolSlot _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_Str_e17c6ec29546c79b_DEFINED
#define QUEST_TYPE_QTuple_QArray_QTuple_Str_e17c6ec29546c79b_DEFINED
struct QTuple_QArray_QTuple_Str_e17c6ec29546c79b {
    QArray * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_QVal_QTuple_Strin_e02676d93d90c568_end_DEFINED
#define QUEST_TYPE_QTuple_QArray_QTuple_QVal_QTuple_Strin_e02676d93d90c568_end_DEFINED
struct QTuple_QArray_QTuple_QVal_QTuple_Strin_e02676d93d90c568_end {
    QArray * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_DEFINED
#define QUEST_TYPE_QTuple_Int_String_DEFINED
struct QTuple_Int_String {
    QInt _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_Int_97c8fdb185623c6d_DEFINED
#define QUEST_TYPE_QTuple_QArray_QTuple_Int_97c8fdb185623c6d_DEFINED
struct QTuple_QArray_QTuple_Int_97c8fdb185623c6d {
    QArray * _0;
    QArray * _1;
};
#endif
#ifndef QUEST_TYPE_QOption_payloadArray_QTu_86d6a7a3ccc30623_DEFINED
#define QUEST_TYPE_QOption_payloadArray_QTu_86d6a7a3ccc30623_DEFINED
struct QOption_payloadArray_QTu_86d6a7a3ccc30623 {
    int64_t tag;
    union {
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadArray_payload {
            QTuple_String_String_Int * _0;
        } qo_payloadArray;
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadAuto_payload {
            QTuple_String_String_Int * _0;
            QTuple_String_Int * _1;
            QArray * _2;
        } qo_payloadAuto;
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadException_payload {
            QTuple_String_String_Int * _0;
        } qo_payloadException;
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadFun_payload {
            QArray * _0;
            QTuple_String_String_Int * _1;
            QArray * _2;
        } qo_payloadFun;
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadHole_payload {
            QInt _0;
            QTuple_String_String_Int * _1;
        } qo_payloadHole;
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadOpaque_payload {
            QArray * _0;
        } qo_payloadOpaque;
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadOption_payload {
            QArray * _0;
        } qo_payloadOption;
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadRecord_payload {
            QArray * _0;
        } qo_payloadRecord;
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadStored_payload {
            QTuple_String_String_Int * _0;
        } qo_payloadStored;
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadTuple_payload {
            QArray * _0;
            QArray * _1;
        } qo_payloadTuple;
        struct QOption_payloadArray_QTu_86d6a7a3ccc30623_payloadVariant_payload {
            QArray * _0;
        } qo_payloadVariant;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Str_966feaa19dc543cd_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Str_966feaa19dc543cd_DEFINED
struct QTuple_QTuple_String_Str_966feaa19dc543cd {
    QTuple_String_String_QVal_String_String_String_QVal_String_Int * _0;
    QString * _1;
    QString * _2;
    QString * _3;
    QTuple_String_Int * _4;
    QOption_payloadArray_QTu_86d6a7a3ccc30623 * _5;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_483bc82e07ff306c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_483bc82e07ff306c_DEFINED
struct RecGroup0_0_QTuple_Strin_483bc82e07ff306c {
    QString * _0;
    QInt _1;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d_DEFINED
struct RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d {
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QOption_kind_5404ddb6c01acca4_DEFINED
#define QUEST_TYPE_RecGroup0_0_QOption_kind_5404ddb6c01acca4_DEFINED
struct RecGroup0_0_QOption_kind_5404ddb6c01acca4 {
    int64_t tag;
    union {
        struct RecGroup0_0_QOption_kind_5404ddb6c01acca4_kindAll_payload {
            QString * _0;
            QInt _1;
            RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
            RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _3;
        } qo_kindAll;
        struct RecGroup0_0_QOption_kind_5404ddb6c01acca4_kindPower_payload {
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
        } qo_kindPower;
        struct RecGroup0_0_QOption_kind_5404ddb6c01acca4_kindVar_payload {
            QString * _0;
            QInt _1;
        } qo_kindVar;
    } u;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_DEFINED
struct RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 {
    QInt _0;
    RecGroup0_0_QOption_kind_5404ddb6c01acca4 * _1;
    QArray * _2;
    QBoolSlot _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_194f294b44f1322f_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_194f294b44f1322f_DEFINED
struct RecGroup0_0_QTuple_Strin_194f294b44f1322f {
    QString * _0;
    QInt _1;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_52d4a987f1a49725_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_52d4a987f1a49725_DEFINED
struct RecGroup0_0_QTuple_Strin_52d4a987f1a49725 {
    QString * _0;
    QInt _1;
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_ad6fb8ee47ebf8e9_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_ad6fb8ee47ebf8e9_DEFINED
struct RecGroup0_0_QTuple_QArra_ad6fb8ee47ebf8e9 {
    QArray * _0;
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_8fcb1094f58faf54_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_8fcb1094f58faf54_DEFINED
struct RecGroup0_0_QTuple_Self2_8fcb1094f58faf54 {
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
    QArray * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_c5f45c993819c661_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_c5f45c993819c661_DEFINED
struct RecGroup0_0_QTuple_Self2_c5f45c993819c661 {
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_701bb4382ecd036e_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_701bb4382ecd036e_DEFINED
struct RecGroup0_0_QTuple_Strin_701bb4382ecd036e {
    QString * _0;
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
    QBoolSlot _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_44826dd1448b0684_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_44826dd1448b0684_DEFINED
struct RecGroup0_0_QTuple_Strin_44826dd1448b0684 {
    QString * _0;
    QInt _1;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
    QArray * _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_3b978c5cdd954e30_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_3b978c5cdd954e30_DEFINED
struct RecGroup0_0_QTuple_Self2_3b978c5cdd954e30 {
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_DEFINED
struct QTuple_String_String {
    QString * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_7e6c6e26396f582e_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_7e6c6e26396f582e_DEFINED
struct RecGroup0_0_QTuple_Strin_7e6c6e26396f582e {
    QString * _0;
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
    QBoolSlot _2;
    QBoolSlot _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_cf1fea11f4f1fd73_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_cf1fea11f4f1fd73_DEFINED
struct RecGroup0_0_QTuple_QArra_cf1fea11f4f1fd73 {
    QArray * _0;
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_S_e030b7b17c66d57e_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_S_e030b7b17c66d57e_DEFINED
struct RecGroup0_0_QTuple_Int_S_e030b7b17c66d57e {
    QInt _0;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _1;
    QString * _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QTupl_5b183cfbae3e8a30_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QTupl_5b183cfbae3e8a30_DEFINED
struct RecGroup0_0_QTuple_QTupl_5b183cfbae3e8a30 {
    RecGroup0_0_QTuple_Int_S_e030b7b17c66d57e * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_4e8cc7c4db8085f3_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_4e8cc7c4db8085f3_DEFINED
struct RecGroup0_0_QTuple_QArra_4e8cc7c4db8085f3 {
    QArray * _0;
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_3e526ed08e667f25_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_3e526ed08e667f25_DEFINED
struct RecGroup0_0_QTuple_Strin_3e526ed08e667f25 {
    QString * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_8fa9737dd5face61_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_8fa9737dd5face61_DEFINED
struct RecGroup0_0_QTuple_QArra_8fa9737dd5face61 {
    QArray * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_13da4434cc3d7950_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_13da4434cc3d7950_DEFINED
struct RecGroup0_0_QTuple_Strin_13da4434cc3d7950 {
    QString * _0;
    QInt _1;
    QString * _2;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_ab137605dc72ed05_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_ab137605dc72ed05_DEFINED
struct RecGroup0_0_QTuple_Strin_ab137605dc72ed05 {
    QString * _0;
    QInt _1;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_8d79da5444c415a9_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_8d79da5444c415a9_DEFINED
struct RecGroup0_0_QTuple_Strin_8d79da5444c415a9 {
    QString * _0;
    QInt _1;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_33bcb62f0fe20d1e_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_33bcb62f0fe20d1e_DEFINED
struct RecGroup0_0_QTuple_QArra_33bcb62f0fe20d1e {
    QArray * _0;
    QInt _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_0bf905da734c84fe_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_0bf905da734c84fe_DEFINED
struct RecGroup0_0_QTuple_QArra_0bf905da734c84fe {
    QArray * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0909b0b2decf3db9_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0909b0b2decf3db9_DEFINED
struct RecGroup0_0_QTuple_QVal__0909b0b2decf3db9 {
    QVal _0;
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
    QBoolSlot _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_edbf69e0a6017bff_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_edbf69e0a6017bff_DEFINED
struct RecGroup0_0_QTuple_Strin_edbf69e0a6017bff {
    QString * _0;
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QOption_tupl_05259466b555c52e_DEFINED
#define QUEST_TYPE_RecGroup0_0_QOption_tupl_05259466b555c52e_DEFINED
struct RecGroup0_0_QOption_tupl_05259466b555c52e {
    int64_t tag;
    union {
        struct RecGroup0_0_QOption_tupl_05259466b555c52e_tupleField_payload {
            QVal _0;
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
            QBoolSlot _2;
        } qo_tupleField;
        struct RecGroup0_0_QOption_tupl_05259466b555c52e_tupleTypeBinding_payload {
            QString * _0;
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
            QVal _2;
        } qo_tupleTypeBinding;
        struct RecGroup0_0_QOption_tupl_05259466b555c52e_tupleTypeFormal_payload {
            QString * _0;
            QInt _1;
            RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
        } qo_tupleTypeFormal;
    } u;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_9e5a10d76b597163_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_9e5a10d76b597163_DEFINED
struct RecGroup0_0_QTuple_QArra_9e5a10d76b597163 {
    QArray * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_9090d707cc236f33_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_9090d707cc236f33_DEFINED
struct RecGroup0_0_QTuple_Strin_9090d707cc236f33 {
    QString * _0;
    QInt _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_5b49b3573fbebbdf_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_5b49b3573fbebbdf_DEFINED
struct RecGroup0_0_QTuple_Strin_5b49b3573fbebbdf {
    QString * _0;
    QVal _1;
    QBoolSlot _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QArra_0b526577c1ff0fea_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QArra_0b526577c1ff0fea_DEFINED
struct RecGroup0_0_QTuple_QArra_0b526577c1ff0fea {
    QArray * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_DEFINED
#define QUEST_TYPE_RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_DEFINED
struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5 {
    int64_t tag;
    union {
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeAbstract_payload {
            QString * _0;
            QInt _1;
            RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
        } qo_typeAbstract;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeAlias_payload {
            QString * _0;
            QInt _1;
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _2;
        } qo_typeAlias;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeAll_payload {
            QArray * _0;
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
        } qo_typeAll;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeApp_payload {
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
            QArray * _1;
        } qo_typeApp;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeArray_payload {
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
        } qo_typeArray;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeAuto_payload {
            QString * _0;
            QInt _1;
            RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
            QArray * _3;
        } qo_typeAuto;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeException_payload {
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
        } qo_typeException;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeExternal_payload {
            QString * _0;
            QString * _1;
        } qo_typeExternal;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeFun_payload {
            QArray * _0;
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
        } qo_typeFun;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeMeta_payload {
            RecGroup0_0_QTuple_Int_S_e030b7b17c66d57e * _0;
        } qo_typeMeta;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeOperator_payload {
            QArray * _0;
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _1;
        } qo_typeOperator;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeOption_payload {
            QArray * _0;
        } qo_typeOption;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeOut_payload {
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
        } qo_typeOut;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typePath_payload {
            QString * _0;
            QInt _1;
            QString * _2;
            RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _3;
        } qo_typePath;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeRec_payload {
            QString * _0;
            QInt _1;
            RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _3;
        } qo_typeRec;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeRecGroup_payload {
            QArray * _0;
            QInt _1;
        } qo_typeRecGroup;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeRecord_payload {
            QArray * _0;
            QVal _1;
        } qo_typeRecord;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeTuple_payload {
            QArray * _0;
        } qo_typeTuple;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeVar_payload {
            RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
        } qo_typeVar;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeVariable_payload {
            QString * _0;
            QInt _1;
            QVal _2;
        } qo_typeVariable;
        struct RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5_typeVariant_payload {
            QArray * _0;
        } qo_typeVariant;
    } u;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874_DEFINED
struct RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 {
    QInt _0;
    RecGroup0_0_QOption_type_8b0ae4b2c2d35fb5 * _1;
    QArray * _2;
    QBoolSlot _3;
    QVal _4;
    QArray * _5;
};
#endif
typedef QOption_wordInt_QTuple_Int_end_wordSymbol_QTuple_String_Int_end * (*quest_sig_questlang__ssa__Statics_refWord)(QTuple_String_String_Int * r);
typedef QArray * (*quest_sig_questlang__ssa__Statics_descriptorData)(QTuple_QTuple_String_Str_966feaa19dc543cd * d, QClosure * text);
#ifdef __cplusplus
}
#endif
#endif
