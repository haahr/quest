#ifndef QUEST_INTF_QUESTLANG__TYPECHECKER__ELABORATETYPES_H
#define QUEST_INTF_QUESTLANG__TYPECHECKER__ELABORATETYPES_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/syntax/ast.int.h"
#include "questlang/types/model.int.h"
#include "questlang/types/symbols.int.h"
#include "questlang/types/env.int.h"
#include "collections/vector.int.h"
#include "util/maybe.int.h"
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
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_S_56c0b1530a080c74_TYPEDEF
typedef struct RecGroup0_0_QTuple_Int_S_56c0b1530a080c74 RecGroup0_0_QTuple_Int_S_56c0b1530a080c74;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_483bc82e07ff306c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_483bc82e07ff306c_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_483bc82e07ff306c RecGroup0_0_QTuple_Strin_483bc82e07ff306c;
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_TYPEDEF
typedef struct QTuple_String_Int QTuple_String_Int;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QOption_kind_5404ddb6c01acca4_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QOption_kind_5404ddb6c01acca4_TYPEDEF
typedef struct RecGroup0_0_QOption_kind_5404ddb6c01acca4 RecGroup0_0_QOption_kind_5404ddb6c01acca4;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_TYPEDEF
typedef struct RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_QVal_TYPEDEF
typedef struct QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_QVal QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_RecGroup0_0_QTupl_162221c52a42adfe_TYPEDEF
#define QUEST_TYPE_QTuple_RecGroup0_0_QTupl_162221c52a42adfe_TYPEDEF
typedef struct QTuple_RecGroup0_0_QTupl_162221c52a42adfe QTuple_RecGroup0_0_QTupl_162221c52a42adfe;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_QVal_QVal_QVal_Bool_Bool_TYPEDEF
typedef struct QTuple_Int_String_QVal_QVal_QVal_Bool_Bool QTuple_Int_String_QVal_QVal_QVal_Bool_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_QVal_TYPEDEF
typedef struct QTuple_Int_String_QVal QTuple_Int_String_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_end_QVal QTuple_QTuple_String_Int_Int_end_QVal;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_TYPEDEF
typedef struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_TYPEDEF
typedef struct QTuple_QTuple_QVal_end_QVal QTuple_QTuple_QVal_end_QVal;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_TYPEDEF
typedef struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_TYPEDEF
typedef struct QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5;
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
#ifndef QUEST_TYPE_QTuple_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_DEFINED
struct QTuple_String_String {
    QString * _0;
    QString * _1;
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_483bc82e07ff306c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_483bc82e07ff306c_DEFINED
struct RecGroup0_0_QTuple_Strin_483bc82e07ff306c {
    QString * _0;
    QInt _1;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _3;
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d_DEFINED
struct RecGroup0_0_QTuple_Self2_8d20e21e0b0ba87d {
    RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_DEFINED
struct QTuple_String_Int {
    QString * _0;
    QInt _1;
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
#ifndef QUEST_TYPE_QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_QVal_DEFINED
struct QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_QVal {
    QString * _0;
    QInt _1;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_RecGroup0_0_QTupl_162221c52a42adfe_DEFINED
#define QUEST_TYPE_QTuple_RecGroup0_0_QTupl_162221c52a42adfe_DEFINED
struct QTuple_RecGroup0_0_QTupl_162221c52a42adfe {
    RecGroup0_0_QTuple_Int_S_56c0b1530a080c74 * _0;
    QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_QVal * _1;
    QVal _2;
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
#ifndef QUEST_TYPE_QTuple_Int_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_Int_String_QVal_DEFINED
struct QTuple_Int_String_QVal {
    QInt _0;
    QString * _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
struct QTuple_QTuple_String_Int_Int_end_QVal {
    QTuple_String_Int_Int * _0;
    QVal _1;
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
#ifndef QUEST_TYPE_QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_DEFINED
#define QUEST_TYPE_QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_DEFINED
struct QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 {
    QString * _0;
    QInt _1;
    RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * _2;
};
#endif
typedef QTuple_RecGroup0_0_QTupl_162221c52a42adfe * quest_type_questlang__typechecker__ElaborateTypes_TupleTypeBinding;
typedef void (*quest_sig_questlang__typechecker__ElaborateTypes_requireUnsoundModule)(Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f * e, QInt offset);
typedef RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * (*quest_sig_questlang__typechecker__ElaborateTypes_elaborateKind)(Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * k, Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f * e);
typedef RecGroup0_0_QTuple_Int_Q_1ac3f974e02e8874 * (*quest_sig_questlang__typechecker__ElaborateTypes_elaborateType)(Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * t, Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f * e);
typedef QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5 * (*quest_sig_questlang__typechecker__ElaborateTypes_elaborateKindBinding)(QString * name, Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * kindVal, Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f * e);
typedef QVal (*quest_sig_questlang__typechecker__ElaborateTypes_tupleTypeBindingMembers)(QVal members, QBool isGroup);
typedef QArray * (*quest_sig_questlang__typechecker__ElaborateTypes_elaborateTupleTypeBindings)(QVal members, QBool isGroup, Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f * e);
typedef QArray * (*quest_sig_questlang__typechecker__ElaborateTypes_elaborateRecTypeOperators)(QVal members, Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f * e);
typedef QArray * (*quest_sig_questlang__typechecker__ElaborateTypes_elaborateTypeBindingGroup)(QVal members, Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f * e);
typedef QTuple_String_Int_RecGroup0_0_QTuple_Int_Q_ec9f82cf5c45c8e5_QVal * (*quest_sig_questlang__typechecker__ElaborateTypes_elaborateTypeBinding)(RecGroup0_0_QTuple_Int_S_56c0b1530a080c74 * b, Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f * e);
typedef QArray * (*quest_sig_questlang__typechecker__ElaborateTypes_elaborateMutualRecTypeGroup)(QVal members, Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f * e);
#ifdef __cplusplus
}
#endif
#endif
