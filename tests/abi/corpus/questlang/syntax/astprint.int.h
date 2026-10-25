#ifndef QUEST_INTF_QUESTLANG__SYNTAX__ASTPRINT_H
#define QUEST_INTF_QUESTLANG__SYNTAX__ASTPRINT_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/syntax/ast.int.h"
#include "questlang/common/location.int.h"
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__8af453701359b971_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__8af453701359b971_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__8af453701359b971 RecGroup0_0_QTuple_QVal__8af453701359b971;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917 RecGroup0_0_QTuple_Self1_0f3bd7cc576c9917;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__4219dbdf893818d4_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__4219dbdf893818d4_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__4219dbdf893818d4 RecGroup0_0_QTuple_QVal__4219dbdf893818d4;
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2 RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2;
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
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_end_QVal QTuple_QTuple_String_Int_Int_end_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_TYPEDEF
#define QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_TYPEDEF
typedef struct QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280;
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a_TYPEDEF
#define QUEST_TYPE_QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a_TYPEDEF
typedef struct QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_6849178448fde400_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_6849178448fde400_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_6849178448fde400 RecGroup0_0_QTuple_Self1_6849178448fde400;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71 RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23 RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0e061144a4b2aebd_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0e061144a4b2aebd_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__0e061144a4b2aebd RecGroup0_0_QTuple_QVal__0e061144a4b2aebd;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_c31a1fd463fc374c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_c31a1fd463fc374c_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_c31a1fd463fc374c RecGroup0_0_QTuple_Self1_c31a1fd463fc374c;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_812c6b1d55ba8239_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_812c6b1d55ba8239_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_812c6b1d55ba8239 RecGroup0_0_QTuple_Self1_812c6b1d55ba8239;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__1d09368daff43424_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__1d09368daff43424_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__1d09368daff43424 RecGroup0_0_QTuple_QVal__1d09368daff43424;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__3aad380a76677e23_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__3aad380a76677e23_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__3aad380a76677e23 RecGroup0_0_QTuple_QVal__3aad380a76677e23;
#endif
#ifndef QUEST_TYPE_QTuple_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_Bool_TYPEDEF
typedef struct QTuple_Bool QTuple_Bool;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_13b821ed702bc901_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_13b821ed702bc901_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_13b821ed702bc901 RecGroup0_0_QTuple_Self1_13b821ed702bc901;
#endif
#ifndef QUEST_TYPE_QTuple_Char_String_TYPEDEF
#define QUEST_TYPE_QTuple_Char_String_TYPEDEF
typedef struct QTuple_Char_String QTuple_Char_String;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_ba754337f0abe989_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_ba754337f0abe989_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_ba754337f0abe989 RecGroup0_0_QTuple_Self1_ba754337f0abe989;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_TYPEDEF
typedef struct QTuple_String_QVal QTuple_String_QVal;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4 RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_cf5dd043ec97507a RecGroup0_0_QTuple_Self1_cf5dd043ec97507a;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_25966076b45188cd_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_25966076b45188cd_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_25966076b45188cd RecGroup0_0_QTuple_Self1_25966076b45188cd;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_fc450a64fc6458eb_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_fc450a64fc6458eb_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_fc450a64fc6458eb RecGroup0_0_QTuple_Self1_fc450a64fc6458eb;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_TYPEDEF
typedef struct QTuple_Int_String QTuple_Int_String;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__f4b00ba508067fbb RecGroup0_0_QTuple_QVal__f4b00ba508067fbb;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_b88fff5cd7686321_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_b88fff5cd7686321_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_b88fff5cd7686321 RecGroup0_0_QTuple_Self1_b88fff5cd7686321;
#endif
#ifndef QUEST_TYPE_QTuple_Real_String_TYPEDEF
#define QUEST_TYPE_QTuple_Real_String_TYPEDEF
typedef struct QTuple_Real_String QTuple_Real_String;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__6b91ee745ebc179e_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__6b91ee745ebc179e_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__6b91ee745ebc179e RecGroup0_0_QTuple_QVal__6b91ee745ebc179e;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_3a0026501c5a603d_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_3a0026501c5a603d_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_3a0026501c5a603d RecGroup0_0_QTuple_Self1_3a0026501c5a603d;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_ff86257d289780fa_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_ff86257d289780fa_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_ff86257d289780fa RecGroup0_0_QTuple_Self1_ff86257d289780fa;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__5d81d0133a66431b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__5d81d0133a66431b_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__5d81d0133a66431b RecGroup0_0_QTuple_QVal__5d81d0133a66431b;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_065ce605433df960_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_065ce605433df960_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_065ce605433df960 RecGroup0_0_QTuple_Self1_065ce605433df960;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_791c377112c6e240_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_791c377112c6e240_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_791c377112c6e240 RecGroup0_0_QTuple_Strin_791c377112c6e240;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f463316737062533_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f463316737062533_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_f463316737062533 RecGroup0_0_QTuple_Self1_f463316737062533;
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_TYPEDEF
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_TYPEDEF
typedef struct QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280;
#endif
#ifndef QUEST_TYPE_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_TYPEDEF
#define QUEST_TYPE_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_TYPEDEF
typedef struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932 Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_TYPEDEF
typedef struct Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23;
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_TYPEDEF
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_TYPEDEF
typedef struct QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QVal_end_TYPEDEF
typedef struct QTuple_QTuple_QVal_end QTuple_QTuple_QVal_end;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_String_QVal_QVal_Bool QTuple_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_end_TYPEDEF
typedef struct QTuple_QTuple_String_QVal_QVal_Bool_end QTuple_QTuple_String_QVal_QVal_Bool_end;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_String_String_QVal_QVal_Bool QTuple_String_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_end_TYPEDEF
typedef struct QTuple_QTuple_String_String_QVal_QVal_Bool_end QTuple_QTuple_String_String_QVal_QVal_Bool_end;
#endif
#ifndef QUEST_TYPE_QOption_phraseDecl_QTupl_f4b2199674f48181_TYPEDEF
#define QUEST_TYPE_QOption_phraseDecl_QTupl_f4b2199674f48181_TYPEDEF
typedef struct QOption_phraseDecl_QTupl_f4b2199674f48181 QOption_phraseDecl_QTupl_f4b2199674f48181;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_d6360d88b72646e2_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_d6360d88b72646e2_TYPEDEF
typedef struct QTuple_QTuple_String_Int_d6360d88b72646e2 QTuple_QTuple_String_Int_d6360d88b72646e2;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_String_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_String_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_String_QVal_QVal QTuple_QVal_String_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end;
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__8af453701359b971_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__8af453701359b971_DEFINED
struct RecGroup0_0_QTuple_QVal__8af453701359b971 {
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__4219dbdf893818d4_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__4219dbdf893818d4_DEFINED
struct RecGroup0_0_QTuple_QVal__4219dbdf893818d4 {
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2_DEFINED
struct RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2 {
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
        } kindAll;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_kindId_payload {
            QString * _0;
        } kindId;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_kindManifest_payload {
            QString * _0;
            QString * _1;
        } kindManifest;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_kindPower_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } kindPower;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeAll_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
        } typeAll;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeApp_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
            QVal _1;
        } typeApp;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeArray_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } typeArray;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeAuto_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QVal _2;
        } typeAuto;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeExternal_payload {
            QString * _0;
        } typeExternal;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeFun_payload {
            QVal _0;
            QVal _1;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
        } typeFun;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeInfix_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
            QString * _1;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
        } typeInfix;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeManifest_payload {
            QString * _0;
            QString * _1;
        } typeManifest;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeOption_payload {
            QVal _0;
        } typeOption;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeOut_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } typeOut;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typePath_payload {
            QVal _0;
        } typePath;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeRec_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
        } typeRec;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeRecord_payload {
            QVal _0;
        } typeRecord;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeTuple_payload {
            QVal _0;
        } typeTuple;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeVar_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } typeVar;
        struct Rec0_QOption_kindAll_QTuple_S_780dca736dfc2ff4_typeVariant_payload {
            QVal _0;
        } typeVariant;
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
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
struct QTuple_QTuple_String_Int_Int_end_QVal {
    QTuple_String_Int_Int * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
#define QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
struct QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a_DEFINED
#define QUEST_TYPE_QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a_DEFINED
struct QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    QVal _2;
    QVal _3;
    QBoolSlot _4;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_6849178448fde400_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_6849178448fde400_DEFINED
struct RecGroup0_0_QTuple_Self1_6849178448fde400 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71_DEFINED
struct RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
    QVal _2;
    QVal _3;
    QBoolSlot _4;
    QBoolSlot _5;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23_DEFINED
struct RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0e061144a4b2aebd_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0e061144a4b2aebd_DEFINED
struct RecGroup0_0_QTuple_QVal__0e061144a4b2aebd {
    QVal _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_c31a1fd463fc374c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_c31a1fd463fc374c_DEFINED
struct RecGroup0_0_QTuple_Self1_c31a1fd463fc374c {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_812c6b1d55ba8239_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_812c6b1d55ba8239_DEFINED
struct RecGroup0_0_QTuple_Self1_812c6b1d55ba8239 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__1d09368daff43424_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__1d09368daff43424_DEFINED
struct RecGroup0_0_QTuple_QVal__1d09368daff43424 {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__3aad380a76677e23_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__3aad380a76677e23_DEFINED
struct RecGroup0_0_QTuple_QVal__3aad380a76677e23 {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Bool_DEFINED
#define QUEST_TYPE_QTuple_Bool_DEFINED
struct QTuple_Bool {
    QBoolSlot _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_13b821ed702bc901_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_13b821ed702bc901_DEFINED
struct RecGroup0_0_QTuple_Self1_13b821ed702bc901 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_Char_String_DEFINED
#define QUEST_TYPE_QTuple_Char_String_DEFINED
struct QTuple_Char_String {
    QCharSlot _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_ba754337f0abe989_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_ba754337f0abe989_DEFINED
struct RecGroup0_0_QTuple_Self1_ba754337f0abe989 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_DEFINED
struct QTuple_String_QVal {
    QString * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4_DEFINED
struct RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
    QBoolSlot _2;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _3;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _4;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce_DEFINED
struct RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce {
    QVal _0;
    QVal _1;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a_DEFINED
struct RecGroup0_0_QTuple_Self1_cf5dd043ec97507a {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_25966076b45188cd_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_25966076b45188cd_DEFINED
struct RecGroup0_0_QTuple_Self1_25966076b45188cd {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_fc450a64fc6458eb_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_fc450a64fc6458eb_DEFINED
struct RecGroup0_0_QTuple_Self1_fc450a64fc6458eb {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd_DEFINED
struct RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c_DEFINED
struct RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_DEFINED
#define QUEST_TYPE_QTuple_Int_String_DEFINED
struct QTuple_Int_String {
    QInt _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc_DEFINED
struct RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb_DEFINED
struct RecGroup0_0_QTuple_QVal__f4b00ba508067fbb {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_b88fff5cd7686321_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_b88fff5cd7686321_DEFINED
struct RecGroup0_0_QTuple_Self1_b88fff5cd7686321 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_Real_String_DEFINED
#define QUEST_TYPE_QTuple_Real_String_DEFINED
struct QTuple_Real_String {
    QReal _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__6b91ee745ebc179e_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__6b91ee745ebc179e_DEFINED
struct RecGroup0_0_QTuple_QVal__6b91ee745ebc179e {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_3a0026501c5a603d_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_3a0026501c5a603d_DEFINED
struct RecGroup0_0_QTuple_Self1_3a0026501c5a603d {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_ff86257d289780fa_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_ff86257d289780fa_DEFINED
struct RecGroup0_0_QTuple_Self1_ff86257d289780fa {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__5d81d0133a66431b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__5d81d0133a66431b_DEFINED
struct RecGroup0_0_QTuple_QVal__5d81d0133a66431b {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_065ce605433df960_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_065ce605433df960_DEFINED
struct RecGroup0_0_QTuple_Self1_065ce605433df960 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_791c377112c6e240_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_791c377112c6e240_DEFINED
struct RecGroup0_0_QTuple_Strin_791c377112c6e240 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    QBoolSlot _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc_DEFINED
struct RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f463316737062533_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f463316737062533_DEFINED
struct RecGroup0_0_QTuple_Self1_f463316737062533 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
struct QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
};
#endif
#ifndef QUEST_TYPE_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_DEFINED
#define QUEST_TYPE_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_DEFINED
struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932 {
    int64_t tag;
    union {
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_declDefKind_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
        } declDefKind;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_declDefType_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QVal _2;
            QVal _3;
            QBoolSlot _4;
        } declDefType;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_declExprStmt_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } declExprStmt;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_declLetType_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QVal _2;
            QVal _3;
            QBoolSlot _4;
        } declLetType;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_declLetVal_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
            QVal _2;
            QVal _3;
            QBoolSlot _4;
            QBoolSlot _5;
        } declLetVal;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprApp_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QVal _1;
        } exprApp;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprArray_payload {
            QVal _0;
            QVal _1;
        } exprArray;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprArrayRep_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
        } exprArrayRep;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprAssign_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
        } exprAssign;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprAuto_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
        } exprAuto;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprBlock_payload {
            QVal _0;
        } exprBlock;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprBool_payload {
            QBoolSlot _0;
        } exprBool;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprCase_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QVal _1;
            QVal _2;
        } exprCase;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprChar_payload {
            QCharSlot _0;
            QString * _1;
        } exprChar;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprDerefCell_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } exprDerefCell;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprException_payload {
            QString * _0;
            QVal _1;
        } exprException;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprExternal_payload {
            QString * _0;
        } exprExternal;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprFor_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
            QBoolSlot _2;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _3;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _4;
        } exprFor;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprFun_payload {
            QVal _0;
            QVal _1;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
            QVal _3;
        } exprFun;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprId_payload {
            QString * _0;
        } exprId;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprIf_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
            QVal _2;
            QVal _3;
        } exprIf;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprIndex_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
        } exprIndex;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprIndexAssign_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
        } exprIndexAssign;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprInfix_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QString * _1;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
        } exprInfix;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprInspect_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QVal _1;
            QVal _2;
        } exprInspect;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprInt_payload {
            QInt _0;
            QString * _1;
        } exprInt;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprLoop_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } exprLoop;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprOption_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QVal _2;
            QVal _3;
        } exprOption;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprRaise_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QVal _1;
            QVal _2;
        } exprRaise;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprReal_payload {
            QReal _0;
            QString * _1;
        } exprReal;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprRecord_payload {
            QVal _0;
        } exprRecord;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprSelect_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QString * _1;
        } exprSelect;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprString_payload {
            QString * _0;
            QString * _1;
        } exprString;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprTry_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QVal _1;
            QVal _2;
        } exprTry;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprTuple_payload {
            QVal _0;
        } exprTuple;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprVarCell_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } exprVarCell;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprVariant_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QBoolSlot _2;
            QVal _3;
        } exprVariant;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprVariantAssert_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QString * _1;
        } exprVariantAssert;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprVariantCheck_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QString * _1;
        } exprVariantCheck;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprWhile_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
        } exprWhile;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_kindArg_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } kindArg;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_typeArg_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } typeArg;
    } u;
};
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_DEFINED
struct Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 {
    QTuple_String_Int_Int * _0;
    Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932 * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_DEFINED
struct QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QVal_end_DEFINED
struct QTuple_QTuple_QVal_end {
    QTuple_QVal * _0;
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
#ifndef QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_end_DEFINED
struct QTuple_QTuple_String_QVal_QVal_Bool_end {
    QTuple_String_QVal_QVal_Bool * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_String_QVal_QVal_Bool_DEFINED
struct QTuple_String_String_QVal_QVal_Bool {
    QString * _0;
    QString * _1;
    QVal _2;
    QVal _3;
    QBoolSlot _4;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_end_DEFINED
struct QTuple_QTuple_String_String_QVal_QVal_Bool_end {
    QTuple_String_String_QVal_QVal_Bool * _0;
};
#endif
#ifndef QUEST_TYPE_QOption_phraseDecl_QTupl_f4b2199674f48181_DEFINED
#define QUEST_TYPE_QOption_phraseDecl_QTupl_f4b2199674f48181_DEFINED
struct QOption_phraseDecl_QTupl_f4b2199674f48181 {
    int64_t tag;
    union {
        struct QOption_phraseDecl_QTupl_f4b2199674f48181_phraseDecl_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } phraseDecl;
        struct QOption_phraseDecl_QTupl_f4b2199674f48181_phraseExpr_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } phraseExpr;
        struct QOption_phraseDecl_QTupl_f4b2199674f48181_phraseImport_payload {
            QTuple_QVal * _0;
        } phraseImport;
        struct QOption_phraseDecl_QTupl_f4b2199674f48181_phraseInterface_payload {
            QTuple_String_QVal_QVal_Bool * _0;
        } phraseInterface;
        struct QOption_phraseDecl_QTupl_f4b2199674f48181_phraseModule_payload {
            QTuple_String_String_QVal_QVal_Bool * _0;
        } phraseModule;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_d6360d88b72646e2_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_d6360d88b72646e2_DEFINED
struct QTuple_QTuple_String_Int_d6360d88b72646e2 {
    QTuple_String_Int_Int * _0;
    QOption_phraseDecl_QTupl_f4b2199674f48181 * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_String_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_String_QVal_QVal_DEFINED
struct QTuple_QVal_String_QVal_QVal {
    QVal _0;
    QString * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_DEFINED
struct QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end {
    QTuple_String_Int_Int * _0;
    QTuple_QVal * _1;
};
#endif
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpTypeExpr)(Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpExpr)(Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpDecl)(Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpPhrase)(QTuple_QTuple_String_Int_d6360d88b72646e2 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpProgram)(QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dump)(QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end * node);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpWithOptions)(QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end * node, QBool showOffsets);
#ifdef __cplusplus
}
#endif
#endif
