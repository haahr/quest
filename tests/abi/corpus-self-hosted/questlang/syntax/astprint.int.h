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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__8af453701359b971_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__8af453701359b971_DEFINED
struct RecGroup0_0_QTuple_QVal__8af453701359b971 {
    QVal _0;
    QVal _1;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__8af453701359b971, _0) == 0, layout_RecGroup0_0_QTuple_QVal__8af453701359b971__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__8af453701359b971, _1) == 8, layout_RecGroup0_0_QTuple_QVal__8af453701359b971__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__8af453701359b971, _2) == 16, layout_RecGroup0_0_QTuple_QVal__8af453701359b971__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__8af453701359b971) == 24, layout_RecGroup0_0_QTuple_QVal__8af453701359b971_size);
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__4219dbdf893818d4_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__4219dbdf893818d4_DEFINED
struct RecGroup0_0_QTuple_QVal__4219dbdf893818d4 {
    QVal _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__4219dbdf893818d4, _0) == 0, layout_RecGroup0_0_QTuple_QVal__4219dbdf893818d4__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__4219dbdf893818d4) == 8, layout_RecGroup0_0_QTuple_QVal__4219dbdf893818d4_size);
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2_DEFINED
struct RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2 {
    QVal _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2, _0) == 0, layout_RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2) == 8, layout_RecGroup0_0_QTuple_QVal__9adeebaf0e57feb2_size);
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
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
#define QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
struct QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
};
static_assert(offsetof(struct QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280, _0) == 0, layout_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280__0);
static_assert(offsetof(struct QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280, _1) == 8, layout_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280__1);
static_assert(sizeof(struct QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280) == 16, layout_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_size);
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
static_assert(offsetof(struct QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a, _0) == 0, layout_QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a__0);
static_assert(offsetof(struct QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a, _1) == 8, layout_QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a__1);
static_assert(offsetof(struct QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a, _2) == 16, layout_QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a__2);
static_assert(offsetof(struct QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a, _3) == 24, layout_QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a__3);
static_assert(offsetof(struct QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a, _4) == 32, layout_QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a__4);
static_assert(sizeof(struct QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a) == 40, layout_QTuple_String_Rec0_QTupl_37c6e5c8ef4c546a_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_6849178448fde400_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_6849178448fde400_DEFINED
struct RecGroup0_0_QTuple_Self1_6849178448fde400 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_6849178448fde400, _0) == 0, layout_RecGroup0_0_QTuple_Self1_6849178448fde400__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_6849178448fde400) == 8, layout_RecGroup0_0_QTuple_Self1_6849178448fde400_size);
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
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71, _0) == 0, layout_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71, _1) == 8, layout_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71, _2) == 16, layout_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71__2);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71, _3) == 24, layout_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71__3);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71, _4) == 32, layout_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71__4);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71, _5) == 40, layout_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71__5);
static_assert(sizeof(struct RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71) == 48, layout_RecGroup0_0_QTuple_Strin_0e5e393dfeb2eb71_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23_DEFINED
struct RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QVal _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23, _0) == 0, layout_RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23, _1) == 8, layout_RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23) == 16, layout_RecGroup0_0_QTuple_Self1_7dcc90fea7aebf23_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0e061144a4b2aebd_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0e061144a4b2aebd_DEFINED
struct RecGroup0_0_QTuple_QVal__0e061144a4b2aebd {
    QVal _0;
    QVal _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__0e061144a4b2aebd, _0) == 0, layout_RecGroup0_0_QTuple_QVal__0e061144a4b2aebd__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__0e061144a4b2aebd, _1) == 8, layout_RecGroup0_0_QTuple_QVal__0e061144a4b2aebd__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__0e061144a4b2aebd) == 16, layout_RecGroup0_0_QTuple_QVal__0e061144a4b2aebd_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_c31a1fd463fc374c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_c31a1fd463fc374c_DEFINED
struct RecGroup0_0_QTuple_Self1_c31a1fd463fc374c {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_c31a1fd463fc374c, _0) == 0, layout_RecGroup0_0_QTuple_Self1_c31a1fd463fc374c__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_c31a1fd463fc374c, _1) == 8, layout_RecGroup0_0_QTuple_Self1_c31a1fd463fc374c__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_c31a1fd463fc374c) == 16, layout_RecGroup0_0_QTuple_Self1_c31a1fd463fc374c_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_812c6b1d55ba8239_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_812c6b1d55ba8239_DEFINED
struct RecGroup0_0_QTuple_Self1_812c6b1d55ba8239 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_812c6b1d55ba8239, _0) == 0, layout_RecGroup0_0_QTuple_Self1_812c6b1d55ba8239__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_812c6b1d55ba8239, _1) == 8, layout_RecGroup0_0_QTuple_Self1_812c6b1d55ba8239__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_812c6b1d55ba8239) == 16, layout_RecGroup0_0_QTuple_Self1_812c6b1d55ba8239_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__1d09368daff43424_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__1d09368daff43424_DEFINED
struct RecGroup0_0_QTuple_QVal__1d09368daff43424 {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__1d09368daff43424, _0) == 0, layout_RecGroup0_0_QTuple_QVal__1d09368daff43424__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__1d09368daff43424, _1) == 8, layout_RecGroup0_0_QTuple_QVal__1d09368daff43424__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__1d09368daff43424, _2) == 16, layout_RecGroup0_0_QTuple_QVal__1d09368daff43424__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__1d09368daff43424) == 24, layout_RecGroup0_0_QTuple_QVal__1d09368daff43424_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__3aad380a76677e23_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__3aad380a76677e23_DEFINED
struct RecGroup0_0_QTuple_QVal__3aad380a76677e23 {
    QVal _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__3aad380a76677e23, _0) == 0, layout_RecGroup0_0_QTuple_QVal__3aad380a76677e23__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__3aad380a76677e23) == 8, layout_RecGroup0_0_QTuple_QVal__3aad380a76677e23_size);
#endif
#ifndef QUEST_TYPE_QTuple_Bool_DEFINED
#define QUEST_TYPE_QTuple_Bool_DEFINED
struct QTuple_Bool {
    QBoolSlot _0;
};
static_assert(offsetof(struct QTuple_Bool, _0) == 0, layout_QTuple_Bool__0);
static_assert(sizeof(struct QTuple_Bool) == 8, layout_QTuple_Bool_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_13b821ed702bc901_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_13b821ed702bc901_DEFINED
struct RecGroup0_0_QTuple_Self1_13b821ed702bc901 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QVal _1;
    QVal _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_13b821ed702bc901, _0) == 0, layout_RecGroup0_0_QTuple_Self1_13b821ed702bc901__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_13b821ed702bc901, _1) == 8, layout_RecGroup0_0_QTuple_Self1_13b821ed702bc901__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_13b821ed702bc901, _2) == 16, layout_RecGroup0_0_QTuple_Self1_13b821ed702bc901__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_13b821ed702bc901) == 24, layout_RecGroup0_0_QTuple_Self1_13b821ed702bc901_size);
#endif
#ifndef QUEST_TYPE_QTuple_Char_String_DEFINED
#define QUEST_TYPE_QTuple_Char_String_DEFINED
struct QTuple_Char_String {
    QCharSlot _0;
    QString * _1;
};
static_assert(offsetof(struct QTuple_Char_String, _0) == 0, layout_QTuple_Char_String__0);
static_assert(offsetof(struct QTuple_Char_String, _1) == 8, layout_QTuple_Char_String__1);
static_assert(sizeof(struct QTuple_Char_String) == 16, layout_QTuple_Char_String_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_ba754337f0abe989_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_ba754337f0abe989_DEFINED
struct RecGroup0_0_QTuple_Self1_ba754337f0abe989 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_ba754337f0abe989, _0) == 0, layout_RecGroup0_0_QTuple_Self1_ba754337f0abe989__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_ba754337f0abe989) == 8, layout_RecGroup0_0_QTuple_Self1_ba754337f0abe989_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_DEFINED
struct QTuple_String_QVal {
    QString * _0;
    QVal _1;
};
static_assert(offsetof(struct QTuple_String_QVal, _0) == 0, layout_QTuple_String_QVal__0);
static_assert(offsetof(struct QTuple_String_QVal, _1) == 8, layout_QTuple_String_QVal__1);
static_assert(sizeof(struct QTuple_String_QVal) == 16, layout_QTuple_String_QVal_size);
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
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4, _0) == 0, layout_RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4, _1) == 8, layout_RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4, _2) == 16, layout_RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4__2);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4, _3) == 24, layout_RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4__3);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4, _4) == 32, layout_RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4__4);
static_assert(sizeof(struct RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4) == 40, layout_RecGroup0_0_QTuple_Strin_fa52b6c954cb43f4_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce_DEFINED
struct RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce {
    QVal _0;
    QVal _1;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
    QVal _3;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce, _0) == 0, layout_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce, _1) == 8, layout_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce, _2) == 16, layout_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce__2);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce, _3) == 24, layout_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce__3);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce) == 32, layout_RecGroup0_0_QTuple_QVal__15cc2d577b76c6ce_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a_DEFINED
struct RecGroup0_0_QTuple_Self1_cf5dd043ec97507a {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
    QVal _2;
    QVal _3;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_cf5dd043ec97507a, _0) == 0, layout_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_cf5dd043ec97507a, _1) == 8, layout_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_cf5dd043ec97507a, _2) == 16, layout_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a__2);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_cf5dd043ec97507a, _3) == 24, layout_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a__3);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_cf5dd043ec97507a) == 32, layout_RecGroup0_0_QTuple_Self1_cf5dd043ec97507a_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_25966076b45188cd_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_25966076b45188cd_DEFINED
struct RecGroup0_0_QTuple_Self1_25966076b45188cd {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_25966076b45188cd, _0) == 0, layout_RecGroup0_0_QTuple_Self1_25966076b45188cd__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_25966076b45188cd, _1) == 8, layout_RecGroup0_0_QTuple_Self1_25966076b45188cd__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_25966076b45188cd) == 16, layout_RecGroup0_0_QTuple_Self1_25966076b45188cd_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_fc450a64fc6458eb_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_fc450a64fc6458eb_DEFINED
struct RecGroup0_0_QTuple_Self1_fc450a64fc6458eb {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_fc450a64fc6458eb, _0) == 0, layout_RecGroup0_0_QTuple_Self1_fc450a64fc6458eb__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_fc450a64fc6458eb, _1) == 8, layout_RecGroup0_0_QTuple_Self1_fc450a64fc6458eb__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_fc450a64fc6458eb, _2) == 16, layout_RecGroup0_0_QTuple_Self1_fc450a64fc6458eb__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_fc450a64fc6458eb) == 24, layout_RecGroup0_0_QTuple_Self1_fc450a64fc6458eb_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd_DEFINED
struct RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd, _0) == 0, layout_RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd, _1) == 8, layout_RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd, _2) == 16, layout_RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd) == 24, layout_RecGroup0_0_QTuple_Self1_cd8cac6324cd97cd_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c_DEFINED
struct RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QVal _1;
    QVal _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c, _0) == 0, layout_RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c, _1) == 8, layout_RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c, _2) == 16, layout_RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c) == 24, layout_RecGroup0_0_QTuple_Self1_f8c00531c2a78e4c_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_DEFINED
#define QUEST_TYPE_QTuple_Int_String_DEFINED
struct QTuple_Int_String {
    QInt _0;
    QString * _1;
};
static_assert(offsetof(struct QTuple_Int_String, _0) == 0, layout_QTuple_Int_String__0);
static_assert(offsetof(struct QTuple_Int_String, _1) == 8, layout_QTuple_Int_String__1);
static_assert(sizeof(struct QTuple_Int_String) == 16, layout_QTuple_Int_String_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc_DEFINED
struct RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc, _0) == 0, layout_RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc) == 8, layout_RecGroup0_0_QTuple_Self1_d9b8adc7c31417bc_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb_DEFINED
struct RecGroup0_0_QTuple_QVal__f4b00ba508067fbb {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    QVal _2;
    QVal _3;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__f4b00ba508067fbb, _0) == 0, layout_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__f4b00ba508067fbb, _1) == 8, layout_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__f4b00ba508067fbb, _2) == 16, layout_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb__2);
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__f4b00ba508067fbb, _3) == 24, layout_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb__3);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__f4b00ba508067fbb) == 32, layout_RecGroup0_0_QTuple_QVal__f4b00ba508067fbb_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_b88fff5cd7686321_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_b88fff5cd7686321_DEFINED
struct RecGroup0_0_QTuple_Self1_b88fff5cd7686321 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QVal _1;
    QVal _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_b88fff5cd7686321, _0) == 0, layout_RecGroup0_0_QTuple_Self1_b88fff5cd7686321__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_b88fff5cd7686321, _1) == 8, layout_RecGroup0_0_QTuple_Self1_b88fff5cd7686321__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_b88fff5cd7686321, _2) == 16, layout_RecGroup0_0_QTuple_Self1_b88fff5cd7686321__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_b88fff5cd7686321) == 24, layout_RecGroup0_0_QTuple_Self1_b88fff5cd7686321_size);
#endif
#ifndef QUEST_TYPE_QTuple_Real_String_DEFINED
#define QUEST_TYPE_QTuple_Real_String_DEFINED
struct QTuple_Real_String {
    QReal _0;
    QString * _1;
};
static_assert(offsetof(struct QTuple_Real_String, _0) == 0, layout_QTuple_Real_String__0);
static_assert(offsetof(struct QTuple_Real_String, _1) == 8, layout_QTuple_Real_String__1);
static_assert(sizeof(struct QTuple_Real_String) == 16, layout_QTuple_Real_String_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__6b91ee745ebc179e_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__6b91ee745ebc179e_DEFINED
struct RecGroup0_0_QTuple_QVal__6b91ee745ebc179e {
    QVal _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__6b91ee745ebc179e, _0) == 0, layout_RecGroup0_0_QTuple_QVal__6b91ee745ebc179e__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__6b91ee745ebc179e) == 8, layout_RecGroup0_0_QTuple_QVal__6b91ee745ebc179e_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_3a0026501c5a603d_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_3a0026501c5a603d_DEFINED
struct RecGroup0_0_QTuple_Self1_3a0026501c5a603d {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QString * _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_3a0026501c5a603d, _0) == 0, layout_RecGroup0_0_QTuple_Self1_3a0026501c5a603d__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_3a0026501c5a603d, _1) == 8, layout_RecGroup0_0_QTuple_Self1_3a0026501c5a603d__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_3a0026501c5a603d) == 16, layout_RecGroup0_0_QTuple_Self1_3a0026501c5a603d_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_ff86257d289780fa_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_ff86257d289780fa_DEFINED
struct RecGroup0_0_QTuple_Self1_ff86257d289780fa {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QVal _1;
    QVal _2;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_ff86257d289780fa, _0) == 0, layout_RecGroup0_0_QTuple_Self1_ff86257d289780fa__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_ff86257d289780fa, _1) == 8, layout_RecGroup0_0_QTuple_Self1_ff86257d289780fa__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_ff86257d289780fa, _2) == 16, layout_RecGroup0_0_QTuple_Self1_ff86257d289780fa__2);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_ff86257d289780fa) == 24, layout_RecGroup0_0_QTuple_Self1_ff86257d289780fa_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__5d81d0133a66431b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__5d81d0133a66431b_DEFINED
struct RecGroup0_0_QTuple_QVal__5d81d0133a66431b {
    QVal _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_QVal__5d81d0133a66431b, _0) == 0, layout_RecGroup0_0_QTuple_QVal__5d81d0133a66431b__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_QVal__5d81d0133a66431b) == 8, layout_RecGroup0_0_QTuple_QVal__5d81d0133a66431b_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_065ce605433df960_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_065ce605433df960_DEFINED
struct RecGroup0_0_QTuple_Self1_065ce605433df960 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_065ce605433df960, _0) == 0, layout_RecGroup0_0_QTuple_Self1_065ce605433df960__0);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_065ce605433df960) == 8, layout_RecGroup0_0_QTuple_Self1_065ce605433df960_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_791c377112c6e240_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_791c377112c6e240_DEFINED
struct RecGroup0_0_QTuple_Strin_791c377112c6e240 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    QBoolSlot _2;
    QVal _3;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_791c377112c6e240, _0) == 0, layout_RecGroup0_0_QTuple_Strin_791c377112c6e240__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_791c377112c6e240, _1) == 8, layout_RecGroup0_0_QTuple_Strin_791c377112c6e240__1);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_791c377112c6e240, _2) == 16, layout_RecGroup0_0_QTuple_Strin_791c377112c6e240__2);
static_assert(offsetof(struct RecGroup0_0_QTuple_Strin_791c377112c6e240, _3) == 24, layout_RecGroup0_0_QTuple_Strin_791c377112c6e240__3);
static_assert(sizeof(struct RecGroup0_0_QTuple_Strin_791c377112c6e240) == 32, layout_RecGroup0_0_QTuple_Strin_791c377112c6e240_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc_DEFINED
struct RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    QString * _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc, _0) == 0, layout_RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc, _1) == 8, layout_RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc) == 16, layout_RecGroup0_0_QTuple_Self1_2ed4ca5bc0f7d2fc_size);
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f463316737062533_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f463316737062533_DEFINED
struct RecGroup0_0_QTuple_Self1_f463316737062533 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
};
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_f463316737062533, _0) == 0, layout_RecGroup0_0_QTuple_Self1_f463316737062533__0);
static_assert(offsetof(struct RecGroup0_0_QTuple_Self1_f463316737062533, _1) == 8, layout_RecGroup0_0_QTuple_Self1_f463316737062533__1);
static_assert(sizeof(struct RecGroup0_0_QTuple_Self1_f463316737062533) == 16, layout_RecGroup0_0_QTuple_Self1_f463316737062533_size);
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
struct QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
};
static_assert(offsetof(struct QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280, _0) == 0, layout_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280__0);
static_assert(sizeof(struct QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280) == 8, layout_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_size);
#endif
#ifndef QUEST_TYPE_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_DEFINED
#define QUEST_TYPE_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_DEFINED
struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932 {
    int64_t tag;
    union {
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_declDefKind_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
        } qo_declDefKind;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_declDefType_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QVal _2;
            QVal _3;
            QBoolSlot _4;
        } qo_declDefType;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_declExprStmt_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } qo_declExprStmt;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_declLetType_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QVal _2;
            QVal _3;
            QBoolSlot _4;
        } qo_declLetType;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_declLetVal_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
            QVal _2;
            QVal _3;
            QBoolSlot _4;
            QBoolSlot _5;
        } qo_declLetVal;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprApp_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QVal _1;
        } qo_exprApp;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprArray_payload {
            QVal _0;
            QVal _1;
        } qo_exprArray;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprArrayRep_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
        } qo_exprArrayRep;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprAssign_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
        } qo_exprAssign;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprAuto_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
        } qo_exprAuto;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprBlock_payload {
            QVal _0;
        } qo_exprBlock;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprBool_payload {
            QBoolSlot _0;
        } qo_exprBool;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprCase_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QVal _1;
            QVal _2;
        } qo_exprCase;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprChar_payload {
            QCharSlot _0;
            QString * _1;
        } qo_exprChar;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprDerefCell_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } qo_exprDerefCell;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprException_payload {
            QString * _0;
            QVal _1;
        } qo_exprException;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprExternal_payload {
            QString * _0;
        } qo_exprExternal;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprFor_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
            QBoolSlot _2;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _3;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _4;
        } qo_exprFor;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprFun_payload {
            QVal _0;
            QVal _1;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
            QVal _3;
        } qo_exprFun;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprId_payload {
            QString * _0;
        } qo_exprId;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprIf_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
            QVal _2;
            QVal _3;
        } qo_exprIf;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprIndex_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
        } qo_exprIndex;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprIndexAssign_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
        } qo_exprIndexAssign;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprInfix_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QString * _1;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _2;
        } qo_exprInfix;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprInspect_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QVal _1;
            QVal _2;
        } qo_exprInspect;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprInt_payload {
            QInt _0;
            QString * _1;
        } qo_exprInt;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprLoop_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } qo_exprLoop;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprOption_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QVal _2;
            QVal _3;
        } qo_exprOption;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprRaise_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QVal _1;
            QVal _2;
        } qo_exprRaise;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprReal_payload {
            QReal _0;
            QString * _1;
        } qo_exprReal;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprRecord_payload {
            QVal _0;
        } qo_exprRecord;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprSelect_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QString * _1;
        } qo_exprSelect;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprString_payload {
            QString * _0;
            QString * _1;
        } qo_exprString;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprTry_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QVal _1;
            QVal _2;
        } qo_exprTry;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprTuple_payload {
            QVal _0;
        } qo_exprTuple;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprVarCell_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } qo_exprVarCell;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprVariant_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QBoolSlot _2;
            QVal _3;
        } qo_exprVariant;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprVariantAssert_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QString * _1;
        } qo_exprVariantAssert;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprVariantCheck_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            QString * _1;
        } qo_exprVariantCheck;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_exprWhile_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _1;
        } qo_exprWhile;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_kindArg_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } qo_kindArg;
        struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_typeArg_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } qo_typeArg;
    } u;
};
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declDefKind._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declDefKind__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declDefKind._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declDefKind__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declDefType._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declDefType__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declDefType._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declDefType__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declDefType._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declDefType__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declDefType._3) == 32, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declDefType__3);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declDefType._4) == 40, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declDefType__4);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declExprStmt._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declExprStmt__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetType._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetType__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetType._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetType__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetType._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetType__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetType._3) == 32, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetType__3);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetType._4) == 40, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetType__4);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetVal._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetVal__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetVal._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetVal__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetVal._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetVal__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetVal._3) == 32, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetVal__3);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetVal._4) == 40, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetVal__4);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_declLetVal._5) == 48, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_declLetVal__5);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprApp._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprApp__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprApp._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprApp__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprArray._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprArray__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprArray._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprArray__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprArrayRep._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprArrayRep__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprArrayRep._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprArrayRep__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprAssign._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprAssign__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprAssign._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprAssign__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprAuto._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprAuto__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprAuto._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprAuto__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprAuto._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprAuto__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprBlock._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprBlock__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprBool._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprBool__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprCase._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprCase__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprCase._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprCase__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprCase._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprCase__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprChar._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprChar__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprChar._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprChar__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprDerefCell._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprDerefCell__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprException._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprException__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprException._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprException__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprExternal._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprExternal__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprFor._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprFor__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprFor._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprFor__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprFor._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprFor__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprFor._3) == 32, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprFor__3);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprFor._4) == 40, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprFor__4);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprFun._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprFun__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprFun._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprFun__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprFun._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprFun__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprFun._3) == 32, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprFun__3);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprId._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprId__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprIf._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprIf__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprIf._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprIf__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprIf._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprIf__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprIf._3) == 32, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprIf__3);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprIndex._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprIndex__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprIndex._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprIndex__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprIndexAssign._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprIndexAssign__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprIndexAssign._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprIndexAssign__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprIndexAssign._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprIndexAssign__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprInfix._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprInfix__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprInfix._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprInfix__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprInfix._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprInfix__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprInspect._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprInspect__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprInspect._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprInspect__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprInspect._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprInspect__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprInt._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprInt__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprInt._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprInt__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprLoop._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprLoop__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprOption._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprOption__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprOption._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprOption__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprOption._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprOption__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprOption._3) == 32, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprOption__3);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprRaise._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprRaise__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprRaise._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprRaise__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprRaise._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprRaise__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprReal._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprReal__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprReal._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprReal__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprRecord._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprRecord__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprSelect._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprSelect__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprSelect._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprSelect__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprString._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprString__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprString._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprString__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprTry._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprTry__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprTry._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprTry__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprTry._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprTry__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprTuple._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprTuple__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprVarCell._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprVarCell__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprVariant._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprVariant__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprVariant._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprVariant__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprVariant._2) == 24, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprVariant__2);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprVariant._3) == 32, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprVariant__3);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprVariantAssert._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprVariantAssert__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprVariantAssert._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprVariantAssert__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprVariantCheck._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprVariantCheck__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprVariantCheck._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprVariantCheck__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprWhile._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprWhile__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_exprWhile._1) == 16, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_exprWhile__1);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_kindArg._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_kindArg__0);
static_assert(offsetof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932, u.qo_typeArg._0) == 8, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_u_qo_typeArg__0);
static_assert(sizeof(struct Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932) == 56, layout_Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932_size);
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_DEFINED
struct Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 {
    QTuple_String_Int_Int * _0;
    Rec0_QOption_declDefKind_QTup_a8a8dcd87d27b932 * _1;
};
static_assert(offsetof(struct Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23, _0) == 0, layout_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23__0);
static_assert(offsetof(struct Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23, _1) == 8, layout_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23__1);
static_assert(sizeof(struct Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23) == 16, layout_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_size);
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_DEFINED
struct QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 {
    Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
};
static_assert(offsetof(struct QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23, _0) == 0, layout_QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23__0);
static_assert(sizeof(struct QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23) == 8, layout_QTuple_Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QVal_end_DEFINED
struct QTuple_QTuple_QVal_end {
    QTuple_QVal * _0;
};
static_assert(offsetof(struct QTuple_QTuple_QVal_end, _0) == 0, layout_QTuple_QTuple_QVal_end__0);
static_assert(sizeof(struct QTuple_QTuple_QVal_end) == 8, layout_QTuple_QTuple_QVal_end_size);
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
#ifndef QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_end_DEFINED
struct QTuple_QTuple_String_QVal_QVal_Bool_end {
    QTuple_String_QVal_QVal_Bool * _0;
};
static_assert(offsetof(struct QTuple_QTuple_String_QVal_QVal_Bool_end, _0) == 0, layout_QTuple_QTuple_String_QVal_QVal_Bool_end__0);
static_assert(sizeof(struct QTuple_QTuple_String_QVal_QVal_Bool_end) == 8, layout_QTuple_QTuple_String_QVal_QVal_Bool_end_size);
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
static_assert(offsetof(struct QTuple_String_String_QVal_QVal_Bool, _0) == 0, layout_QTuple_String_String_QVal_QVal_Bool__0);
static_assert(offsetof(struct QTuple_String_String_QVal_QVal_Bool, _1) == 8, layout_QTuple_String_String_QVal_QVal_Bool__1);
static_assert(offsetof(struct QTuple_String_String_QVal_QVal_Bool, _2) == 16, layout_QTuple_String_String_QVal_QVal_Bool__2);
static_assert(offsetof(struct QTuple_String_String_QVal_QVal_Bool, _3) == 24, layout_QTuple_String_String_QVal_QVal_Bool__3);
static_assert(offsetof(struct QTuple_String_String_QVal_QVal_Bool, _4) == 32, layout_QTuple_String_String_QVal_QVal_Bool__4);
static_assert(sizeof(struct QTuple_String_String_QVal_QVal_Bool) == 40, layout_QTuple_String_String_QVal_QVal_Bool_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_end_DEFINED
struct QTuple_QTuple_String_String_QVal_QVal_Bool_end {
    QTuple_String_String_QVal_QVal_Bool * _0;
};
static_assert(offsetof(struct QTuple_QTuple_String_String_QVal_QVal_Bool_end, _0) == 0, layout_QTuple_QTuple_String_String_QVal_QVal_Bool_end__0);
static_assert(sizeof(struct QTuple_QTuple_String_String_QVal_QVal_Bool_end) == 8, layout_QTuple_QTuple_String_String_QVal_QVal_Bool_end_size);
#endif
#ifndef QUEST_TYPE_QOption_phraseDecl_QTupl_f4b2199674f48181_DEFINED
#define QUEST_TYPE_QOption_phraseDecl_QTupl_f4b2199674f48181_DEFINED
struct QOption_phraseDecl_QTupl_f4b2199674f48181 {
    int64_t tag;
    union {
        struct QOption_phraseDecl_QTupl_f4b2199674f48181_phraseDecl_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } qo_phraseDecl;
        struct QOption_phraseDecl_QTupl_f4b2199674f48181_phraseExpr_payload {
            Rec0_QTuple_QTuple_String_Int_f7a377db19fd7b23 * _0;
        } qo_phraseExpr;
        struct QOption_phraseDecl_QTupl_f4b2199674f48181_phraseImport_payload {
            QTuple_QVal * _0;
        } qo_phraseImport;
        struct QOption_phraseDecl_QTupl_f4b2199674f48181_phraseInterface_payload {
            QTuple_String_QVal_QVal_Bool * _0;
        } qo_phraseInterface;
        struct QOption_phraseDecl_QTupl_f4b2199674f48181_phraseModule_payload {
            QTuple_String_String_QVal_QVal_Bool * _0;
        } qo_phraseModule;
    } u;
};
static_assert(offsetof(struct QOption_phraseDecl_QTupl_f4b2199674f48181, u.qo_phraseDecl._0) == 8, layout_QOption_phraseDecl_QTupl_f4b2199674f48181_u_qo_phraseDecl__0);
static_assert(offsetof(struct QOption_phraseDecl_QTupl_f4b2199674f48181, u.qo_phraseExpr._0) == 8, layout_QOption_phraseDecl_QTupl_f4b2199674f48181_u_qo_phraseExpr__0);
static_assert(offsetof(struct QOption_phraseDecl_QTupl_f4b2199674f48181, u.qo_phraseImport._0) == 8, layout_QOption_phraseDecl_QTupl_f4b2199674f48181_u_qo_phraseImport__0);
static_assert(offsetof(struct QOption_phraseDecl_QTupl_f4b2199674f48181, u.qo_phraseInterface._0) == 8, layout_QOption_phraseDecl_QTupl_f4b2199674f48181_u_qo_phraseInterface__0);
static_assert(offsetof(struct QOption_phraseDecl_QTupl_f4b2199674f48181, u.qo_phraseModule._0) == 8, layout_QOption_phraseDecl_QTupl_f4b2199674f48181_u_qo_phraseModule__0);
static_assert(sizeof(struct QOption_phraseDecl_QTupl_f4b2199674f48181) == 16, layout_QOption_phraseDecl_QTupl_f4b2199674f48181_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_d6360d88b72646e2_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_d6360d88b72646e2_DEFINED
struct QTuple_QTuple_String_Int_d6360d88b72646e2 {
    QTuple_String_Int_Int * _0;
    QOption_phraseDecl_QTupl_f4b2199674f48181 * _1;
};
static_assert(offsetof(struct QTuple_QTuple_String_Int_d6360d88b72646e2, _0) == 0, layout_QTuple_QTuple_String_Int_d6360d88b72646e2__0);
static_assert(offsetof(struct QTuple_QTuple_String_Int_d6360d88b72646e2, _1) == 8, layout_QTuple_QTuple_String_Int_d6360d88b72646e2__1);
static_assert(sizeof(struct QTuple_QTuple_String_Int_d6360d88b72646e2) == 16, layout_QTuple_QTuple_String_Int_d6360d88b72646e2_size);
#endif
#ifndef QUEST_TYPE_QTuple_QVal_String_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_String_QVal_QVal_DEFINED
struct QTuple_QVal_String_QVal_QVal {
    QVal _0;
    QString * _1;
    QVal _2;
    QVal _3;
};
static_assert(offsetof(struct QTuple_QVal_String_QVal_QVal, _0) == 0, layout_QTuple_QVal_String_QVal_QVal__0);
static_assert(offsetof(struct QTuple_QVal_String_QVal_QVal, _1) == 8, layout_QTuple_QVal_String_QVal_QVal__1);
static_assert(offsetof(struct QTuple_QVal_String_QVal_QVal, _2) == 16, layout_QTuple_QVal_String_QVal_QVal__2);
static_assert(offsetof(struct QTuple_QVal_String_QVal_QVal, _3) == 24, layout_QTuple_QVal_String_QVal_QVal__3);
static_assert(sizeof(struct QTuple_QVal_String_QVal_QVal) == 32, layout_QTuple_QVal_String_QVal_QVal_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_DEFINED
struct QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end {
    QTuple_String_Int_Int * _0;
    QTuple_QVal * _1;
};
static_assert(offsetof(struct QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end, _0) == 0, layout_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end__0);
static_assert(offsetof(struct QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end, _1) == 8, layout_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end__1);
static_assert(sizeof(struct QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end) == 16, layout_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_size);
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
