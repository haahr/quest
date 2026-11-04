#ifndef QUEST_INTF_QUESTLANG__SYNTAX__PARSER_H
#define QUEST_INTF_QUESTLANG__SYNTAX__PARSER_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/common/location.int.h"
#include "questlang/common/diagbag.int.h"
#include "questlang/syntax/tokens.int.h"
#include "questlang/syntax/ast.int.h"
#include "collections/vector.int.h"
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_TYPEDEF
typedef struct QTuple_QVal QTuple_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end;
#endif
#ifndef QUEST_TYPE_QOption_assign_at_bang_c_9d67c602c649263b_TYPEDEF
#define QUEST_TYPE_QOption_assign_at_bang_c_9d67c602c649263b_TYPEDEF
typedef struct QOption_assign_at_bang_c_9d67c602c649263b QOption_assign_at_bang_c_9d67c602c649263b;
#endif
#ifndef QUEST_TYPE_QTuple_Char_TYPEDEF
#define QUEST_TYPE_QTuple_Char_TYPEDEF
typedef struct QTuple_Char QTuple_Char;
#endif
#ifndef QUEST_TYPE_QTuple_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_TYPEDEF
typedef struct QTuple_Int QTuple_Int;
#endif
#ifndef QUEST_TYPE_QTuple_Real_TYPEDEF
#define QUEST_TYPE_QTuple_Real_TYPEDEF
typedef struct QTuple_Real QTuple_Real;
#endif
#ifndef QUEST_TYPE_QTuple_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_TYPEDEF
typedef struct QTuple_String QTuple_String;
#endif
#ifndef QUEST_TYPE_QOption_charVal_QTuple_C_858f5528ce3cda86_TYPEDEF
#define QUEST_TYPE_QOption_charVal_QTuple_C_858f5528ce3cda86_TYPEDEF
typedef struct QOption_charVal_QTuple_C_858f5528ce3cda86 QOption_charVal_QTuple_C_858f5528ce3cda86;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_assign_at_723595ebb1959a6e_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_assign_at_723595ebb1959a6e_TYPEDEF
typedef struct QTuple_QOption_assign_at_723595ebb1959a6e QTuple_QOption_assign_at_723595ebb1959a6e;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_end_QVal QTuple_QTuple_String_Int_Int_end_QVal;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_9d01f59cb270e31c_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_9d01f59cb270e31c RecGroup0_0_QTuple_Strin_9d01f59cb270e31c;
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
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_TYPEDEF
#define QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_TYPEDEF
typedef struct QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f7fc5015b9916587_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f7fc5015b9916587_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_f7fc5015b9916587 RecGroup0_0_QTuple_Self1_f7fc5015b9916587;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QVal_end_TYPEDEF
typedef struct QTuple_QTuple_QVal_end QTuple_QTuple_QVal_end;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_207dfc51170cbf82_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_207dfc51170cbf82_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_207dfc51170cbf82 RecGroup0_0_QTuple_Strin_207dfc51170cbf82;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__8125940b8c9a97fb_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__8125940b8c9a97fb_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__8125940b8c9a97fb RecGroup0_0_QTuple_QVal__8125940b8c9a97fb;
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTupl_1bed08606e9713cc_TYPEDEF
#define QUEST_TYPE_QTuple_String_Rec0_QTupl_1bed08606e9713cc_TYPEDEF
typedef struct QTuple_String_Rec0_QTupl_1bed08606e9713cc QTuple_String_Rec0_QTupl_1bed08606e9713cc;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_0fec3081802cb44f_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_0fec3081802cb44f_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_0fec3081802cb44f RecGroup0_0_QTuple_Self1_0fec3081802cb44f;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__ed42d4a4e7a90905_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__ed42d4a4e7a90905_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__ed42d4a4e7a90905 RecGroup0_0_QTuple_QVal__ed42d4a4e7a90905;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_51a9249fea29350a_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_51a9249fea29350a_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_51a9249fea29350a RecGroup0_0_QTuple_Self1_51a9249fea29350a;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Rec0__11eb9c355dab0a64_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Rec0__11eb9c355dab0a64_TYPEDEF
typedef struct RecGroup0_0_QTuple_Rec0__11eb9c355dab0a64 RecGroup0_0_QTuple_Rec0__11eb9c355dab0a64;
#endif
#ifndef QUEST_TYPE_QTuple_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_Bool_TYPEDEF
typedef struct QTuple_Bool QTuple_Bool;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_e54c411ddbf3ef61_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_e54c411ddbf3ef61_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_e54c411ddbf3ef61 RecGroup0_0_QTuple_Self1_e54c411ddbf3ef61;
#endif
#ifndef QUEST_TYPE_QTuple_Char_String_TYPEDEF
#define QUEST_TYPE_QTuple_Char_String_TYPEDEF
typedef struct QTuple_Char_String QTuple_Char_String;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_39a356dbab394b79_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_39a356dbab394b79_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_39a356dbab394b79 RecGroup0_0_QTuple_Self1_39a356dbab394b79;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_TYPEDEF
typedef struct QTuple_String_QVal QTuple_String_QVal;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_381b7827861b578b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_381b7827861b578b_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_381b7827861b578b RecGroup0_0_QTuple_Strin_381b7827861b578b;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__1847facea2962c15_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__1847facea2962c15_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__1847facea2962c15 RecGroup0_0_QTuple_QVal__1847facea2962c15;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_52a1dae19a690242_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_52a1dae19a690242_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_52a1dae19a690242 RecGroup0_0_QTuple_Self1_52a1dae19a690242;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_685e17ed6c516429_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_685e17ed6c516429_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_685e17ed6c516429 RecGroup0_0_QTuple_Self1_685e17ed6c516429;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_330d0d06061b76f4_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_330d0d06061b76f4_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_330d0d06061b76f4 RecGroup0_0_QTuple_Self1_330d0d06061b76f4;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_9d0ec312b46c0f52_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_9d0ec312b46c0f52_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_9d0ec312b46c0f52 RecGroup0_0_QTuple_Self1_9d0ec312b46c0f52;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_9c053eef48f65652_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_9c053eef48f65652_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_9c053eef48f65652 RecGroup0_0_QTuple_Self1_9c053eef48f65652;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_TYPEDEF
typedef struct QTuple_Int_String QTuple_Int_String;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_de0ad03b8b33fdb7_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_de0ad03b8b33fdb7_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_de0ad03b8b33fdb7 RecGroup0_0_QTuple_Self1_de0ad03b8b33fdb7;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__e6c2570029403b35_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__e6c2570029403b35_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__e6c2570029403b35 RecGroup0_0_QTuple_QVal__e6c2570029403b35;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_e2e0fe9e23e0ac01_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_e2e0fe9e23e0ac01_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_e2e0fe9e23e0ac01 RecGroup0_0_QTuple_Self1_e2e0fe9e23e0ac01;
#endif
#ifndef QUEST_TYPE_QTuple_Real_String_TYPEDEF
#define QUEST_TYPE_QTuple_Real_String_TYPEDEF
typedef struct QTuple_Real_String QTuple_Real_String;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__f6ce20a90e06976c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__f6ce20a90e06976c_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__f6ce20a90e06976c RecGroup0_0_QTuple_QVal__f6ce20a90e06976c;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_9eb422a280a8e70f_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_9eb422a280a8e70f_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_9eb422a280a8e70f RecGroup0_0_QTuple_Self1_9eb422a280a8e70f;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_bc696a89664b0c47_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_bc696a89664b0c47_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_bc696a89664b0c47 RecGroup0_0_QTuple_Self1_bc696a89664b0c47;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__cf46abde22fe7504_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__cf46abde22fe7504_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__cf46abde22fe7504 RecGroup0_0_QTuple_QVal__cf46abde22fe7504;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_48efa6e14b8d1acf_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_48efa6e14b8d1acf_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_48efa6e14b8d1acf RecGroup0_0_QTuple_Self1_48efa6e14b8d1acf;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_6d5ed75234bde796_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_6d5ed75234bde796_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_6d5ed75234bde796 RecGroup0_0_QTuple_Strin_6d5ed75234bde796;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_6983958d7d151f83_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_6983958d7d151f83_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_6983958d7d151f83 RecGroup0_0_QTuple_Self1_6983958d7d151f83;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_2ddba152dec20ce9_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_2ddba152dec20ce9_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_2ddba152dec20ce9 RecGroup0_0_QTuple_Self1_2ddba152dec20ce9;
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_TYPEDEF
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_TYPEDEF
typedef struct QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280;
#endif
#ifndef QUEST_TYPE_Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_TYPEDEF
#define QUEST_TYPE_Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_TYPEDEF
typedef struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_089a135111b1225c_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_089a135111b1225c_TYPEDEF
typedef struct Rec0_QTuple_QTuple_String_Int_089a135111b1225c Rec0_QTuple_QTuple_String_Int_089a135111b1225c;
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_089a135111b1225c_TYPEDEF
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_089a135111b1225c_TYPEDEF
typedef struct QTuple_Rec0_QTuple_QTuple_String_Int_089a135111b1225c QTuple_Rec0_QTuple_QTuple_String_Int_089a135111b1225c;
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
#ifndef QUEST_TYPE_QOption_phraseDecl_QTupl_ad82f14acbc48f7e_TYPEDEF
#define QUEST_TYPE_QOption_phraseDecl_QTupl_ad82f14acbc48f7e_TYPEDEF
typedef struct QOption_phraseDecl_QTupl_ad82f14acbc48f7e QOption_phraseDecl_QTupl_ad82f14acbc48f7e;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_664554c46614a00a_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_664554c46614a00a_TYPEDEF
typedef struct QTuple_QTuple_String_Int_664554c46614a00a QTuple_QTuple_String_Int_664554c46614a00a;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QVal_String_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QVal_String_QVal_QVal_TYPEDEF
typedef struct QTuple_Int_QVal_String_QVal_QVal QTuple_Int_QVal_String_QVal_QVal;
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
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_DEFINED
struct QTuple_QVal {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end_DEFINED
struct QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end {
    QTuple_String_Int_Int * _0;
    QTuple_QVal * _1;
};
#endif
#ifndef QUEST_TYPE_QOption_assign_at_bang_c_9d67c602c649263b_DEFINED
#define QUEST_TYPE_QOption_assign_at_bang_c_9d67c602c649263b_DEFINED
struct QOption_assign_at_bang_c_9d67c602c649263b {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_Char_DEFINED
#define QUEST_TYPE_QTuple_Char_DEFINED
struct QTuple_Char {
    QCharSlot _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_DEFINED
struct QTuple_Int {
    QInt _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Real_DEFINED
#define QUEST_TYPE_QTuple_Real_DEFINED
struct QTuple_Real {
    QReal _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
#endif
#ifndef QUEST_TYPE_QOption_charVal_QTuple_C_858f5528ce3cda86_DEFINED
#define QUEST_TYPE_QOption_charVal_QTuple_C_858f5528ce3cda86_DEFINED
struct QOption_charVal_QTuple_C_858f5528ce3cda86 {
    int64_t tag;
    union {
        struct QOption_charVal_QTuple_C_858f5528ce3cda86_charVal_payload {
            QCharSlot _0;
        } qo_charVal;
        struct QOption_charVal_QTuple_C_858f5528ce3cda86_intVal_payload {
            QInt _0;
        } qo_intVal;
        struct QOption_charVal_QTuple_C_858f5528ce3cda86_realVal_payload {
            QReal _0;
        } qo_realVal;
        struct QOption_charVal_QTuple_C_858f5528ce3cda86_stringVal_payload {
            QString * _0;
        } qo_stringVal;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QOption_assign_at_723595ebb1959a6e_DEFINED
#define QUEST_TYPE_QTuple_QOption_assign_at_723595ebb1959a6e_DEFINED
struct QTuple_QOption_assign_at_723595ebb1959a6e {
    QOption_assign_at_bang_c_9d67c602c649263b * _0;
    QString * _1;
    QOption_charVal_QTuple_C_858f5528ce3cda86 * _2;
    QTuple_String_Int_Int * _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
struct QTuple_QTuple_String_Int_Int_end_QVal {
    QTuple_String_Int_Int * _0;
    QVal _1;
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
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
#define QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
struct QTuple_String_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f7fc5015b9916587_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f7fc5015b9916587_DEFINED
struct RecGroup0_0_QTuple_Self1_f7fc5015b9916587 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QVal_end_DEFINED
struct QTuple_QTuple_QVal_end {
    QTuple_QVal * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_207dfc51170cbf82_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_207dfc51170cbf82_DEFINED
struct RecGroup0_0_QTuple_Strin_207dfc51170cbf82 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
    QVal _2;
    QVal _3;
    QBoolSlot _4;
    QBoolSlot _5;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__8125940b8c9a97fb_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__8125940b8c9a97fb_DEFINED
struct RecGroup0_0_QTuple_QVal__8125940b8c9a97fb {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTupl_1bed08606e9713cc_DEFINED
#define QUEST_TYPE_QTuple_String_Rec0_QTupl_1bed08606e9713cc_DEFINED
struct QTuple_String_Rec0_QTupl_1bed08606e9713cc {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    QVal _2;
    QVal _3;
    QBoolSlot _4;
    QBoolSlot _5;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_0fec3081802cb44f_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_0fec3081802cb44f_DEFINED
struct RecGroup0_0_QTuple_Self1_0fec3081802cb44f {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__ed42d4a4e7a90905_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__ed42d4a4e7a90905_DEFINED
struct RecGroup0_0_QTuple_QVal__ed42d4a4e7a90905 {
    QVal _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_51a9249fea29350a_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_51a9249fea29350a_DEFINED
struct RecGroup0_0_QTuple_Self1_51a9249fea29350a {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Rec0__11eb9c355dab0a64_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Rec0__11eb9c355dab0a64_DEFINED
struct RecGroup0_0_QTuple_Rec0__11eb9c355dab0a64 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_Bool_DEFINED
#define QUEST_TYPE_QTuple_Bool_DEFINED
struct QTuple_Bool {
    QBoolSlot _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_e54c411ddbf3ef61_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_e54c411ddbf3ef61_DEFINED
struct RecGroup0_0_QTuple_Self1_e54c411ddbf3ef61 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_39a356dbab394b79_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_39a356dbab394b79_DEFINED
struct RecGroup0_0_QTuple_Self1_39a356dbab394b79 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_DEFINED
struct QTuple_String_QVal {
    QString * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_381b7827861b578b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_381b7827861b578b_DEFINED
struct RecGroup0_0_QTuple_Strin_381b7827861b578b {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
    QBoolSlot _2;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _3;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _4;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__1847facea2962c15_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__1847facea2962c15_DEFINED
struct RecGroup0_0_QTuple_QVal__1847facea2962c15 {
    QVal _0;
    QVal _1;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_52a1dae19a690242_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_52a1dae19a690242_DEFINED
struct RecGroup0_0_QTuple_Self1_52a1dae19a690242 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
    QVal _2;
    QVal _3;
    QBoolSlot _4;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_685e17ed6c516429_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_685e17ed6c516429_DEFINED
struct RecGroup0_0_QTuple_Self1_685e17ed6c516429 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_330d0d06061b76f4_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_330d0d06061b76f4_DEFINED
struct RecGroup0_0_QTuple_Self1_330d0d06061b76f4 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_9d0ec312b46c0f52_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_9d0ec312b46c0f52_DEFINED
struct RecGroup0_0_QTuple_Self1_9d0ec312b46c0f52 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_9c053eef48f65652_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_9c053eef48f65652_DEFINED
struct RecGroup0_0_QTuple_Self1_9c053eef48f65652 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_de0ad03b8b33fdb7_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_de0ad03b8b33fdb7_DEFINED
struct RecGroup0_0_QTuple_Self1_de0ad03b8b33fdb7 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__e6c2570029403b35_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__e6c2570029403b35_DEFINED
struct RecGroup0_0_QTuple_QVal__e6c2570029403b35 {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_e2e0fe9e23e0ac01_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_e2e0fe9e23e0ac01_DEFINED
struct RecGroup0_0_QTuple_Self1_e2e0fe9e23e0ac01 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__f6ce20a90e06976c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__f6ce20a90e06976c_DEFINED
struct RecGroup0_0_QTuple_QVal__f6ce20a90e06976c {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_9eb422a280a8e70f_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_9eb422a280a8e70f_DEFINED
struct RecGroup0_0_QTuple_Self1_9eb422a280a8e70f {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_bc696a89664b0c47_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_bc696a89664b0c47_DEFINED
struct RecGroup0_0_QTuple_Self1_bc696a89664b0c47 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
    QVal _1;
    QVal _2;
    QVal _3;
    QVal _4;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__cf46abde22fe7504_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__cf46abde22fe7504_DEFINED
struct RecGroup0_0_QTuple_QVal__cf46abde22fe7504 {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_48efa6e14b8d1acf_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_48efa6e14b8d1acf_DEFINED
struct RecGroup0_0_QTuple_Self1_48efa6e14b8d1acf {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_6d5ed75234bde796_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_6d5ed75234bde796_DEFINED
struct RecGroup0_0_QTuple_Strin_6d5ed75234bde796 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
    QBoolSlot _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_6983958d7d151f83_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_6983958d7d151f83_DEFINED
struct RecGroup0_0_QTuple_Self1_6983958d7d151f83 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_2ddba152dec20ce9_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_2ddba152dec20ce9_DEFINED
struct RecGroup0_0_QTuple_Self1_2ddba152dec20ce9 {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280_DEFINED
struct QTuple_Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 {
    Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
};
#endif
#ifndef QUEST_TYPE_Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_DEFINED
#define QUEST_TYPE_Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_DEFINED
struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad {
    int64_t tag;
    union {
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_declDefKind_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
        } qo_declDefKind;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_declExprStmt_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
        } qo_declExprStmt;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_declImport_payload {
            QTuple_QVal * _0;
        } qo_declImport;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_declLetVal_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
            QVal _2;
            QVal _3;
            QBoolSlot _4;
            QBoolSlot _5;
        } qo_declLetVal;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_declLetValGroup_payload {
            QVal _0;
        } qo_declLetValGroup;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_declTypeBinding_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QVal _2;
            QVal _3;
            QBoolSlot _4;
            QBoolSlot _5;
        } qo_declTypeBinding;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_declTypeBindingGroup_payload {
            QVal _0;
        } qo_declTypeBindingGroup;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprApp_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            QVal _1;
        } qo_exprApp;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprArray_payload {
            QVal _0;
            QVal _1;
        } qo_exprArray;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprArrayRep_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
        } qo_exprArrayRep;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprAuto_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
            QVal _2;
            QVal _3;
        } qo_exprAuto;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprBlock_payload {
            QVal _0;
        } qo_exprBlock;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprBool_payload {
            QBoolSlot _0;
        } qo_exprBool;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprCase_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            QVal _1;
            QVal _2;
        } qo_exprCase;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprChar_payload {
            QCharSlot _0;
            QString * _1;
        } qo_exprChar;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprDerefCell_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
        } qo_exprDerefCell;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprException_payload {
            QString * _0;
            QVal _1;
        } qo_exprException;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprExternal_payload {
            QString * _0;
        } qo_exprExternal;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprFor_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
            QBoolSlot _2;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _3;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _4;
        } qo_exprFor;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprFun_payload {
            QVal _0;
            QVal _1;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _2;
            QVal _3;
        } qo_exprFun;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprId_payload {
            QString * _0;
        } qo_exprId;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprIf_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
            QVal _2;
            QVal _3;
            QBoolSlot _4;
        } qo_exprIf;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprIndex_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
        } qo_exprIndex;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprIndexAssign_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _2;
        } qo_exprIndexAssign;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprInfix_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            QString * _1;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _2;
        } qo_exprInfix;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprInspect_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            QVal _1;
            QVal _2;
        } qo_exprInspect;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprInt_payload {
            QInt _0;
            QString * _1;
        } qo_exprInt;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprLoop_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
        } qo_exprLoop;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprOption_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QVal _2;
            QVal _3;
        } qo_exprOption;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprRaise_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            QVal _1;
            QVal _2;
        } qo_exprRaise;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprReal_payload {
            QReal _0;
            QString * _1;
        } qo_exprReal;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprRecord_payload {
            QVal _0;
        } qo_exprRecord;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprSelect_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            QString * _1;
        } qo_exprSelect;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprString_payload {
            QString * _0;
            QString * _1;
        } qo_exprString;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprTry_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            QVal _1;
            QVal _2;
            QVal _3;
            QVal _4;
        } qo_exprTry;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprTuple_payload {
            QVal _0;
        } qo_exprTuple;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprVarCell_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
        } qo_exprVarCell;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprVariant_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _1;
            QBoolSlot _2;
            QVal _3;
        } qo_exprVariant;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprVariantAssert_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            QString * _1;
        } qo_exprVariantAssert;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprVariantCheck_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            QString * _1;
        } qo_exprVariantCheck;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_exprWhile_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _1;
        } qo_exprWhile;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_kindArg_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } qo_kindArg;
        struct Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad_typeArg_payload {
            Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * _0;
        } qo_typeArg;
    } u;
};
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_089a135111b1225c_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_089a135111b1225c_DEFINED
struct Rec0_QTuple_QTuple_String_Int_089a135111b1225c {
    QTuple_String_Int_Int * _0;
    Rec0_QOption_declDefKind_QTup_6ffc24fd8c63bcad * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_089a135111b1225c_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_089a135111b1225c_DEFINED
struct QTuple_Rec0_QTuple_QTuple_String_Int_089a135111b1225c {
    Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
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
#ifndef QUEST_TYPE_QOption_phraseDecl_QTupl_ad82f14acbc48f7e_DEFINED
#define QUEST_TYPE_QOption_phraseDecl_QTupl_ad82f14acbc48f7e_DEFINED
struct QOption_phraseDecl_QTupl_ad82f14acbc48f7e {
    int64_t tag;
    union {
        struct QOption_phraseDecl_QTupl_ad82f14acbc48f7e_phraseDecl_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
        } qo_phraseDecl;
        struct QOption_phraseDecl_QTupl_ad82f14acbc48f7e_phraseExpr_payload {
            Rec0_QTuple_QTuple_String_Int_089a135111b1225c * _0;
        } qo_phraseExpr;
        struct QOption_phraseDecl_QTupl_ad82f14acbc48f7e_phraseImport_payload {
            QTuple_QVal * _0;
        } qo_phraseImport;
        struct QOption_phraseDecl_QTupl_ad82f14acbc48f7e_phraseInterface_payload {
            QTuple_String_QVal_QVal_Bool * _0;
        } qo_phraseInterface;
        struct QOption_phraseDecl_QTupl_ad82f14acbc48f7e_phraseModule_payload {
            QTuple_String_String_QVal_QVal_Bool * _0;
        } qo_phraseModule;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_664554c46614a00a_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_664554c46614a00a_DEFINED
struct QTuple_QTuple_String_Int_664554c46614a00a {
    QTuple_String_Int_Int * _0;
    QOption_phraseDecl_QTupl_ad82f14acbc48f7e * _1;
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
typedef QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end * (*quest_sig_questlang__syntax__Parser_parseProgram)(QVal toks, QVal sm, QVal bag);
typedef Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * (*quest_sig_questlang__syntax__Parser_parseType)(QVal toks, QVal sm, QVal bag);
typedef Rec0_QTuple_QTuple_String_Int_f591fb7dcee73280 * (*quest_sig_questlang__syntax__Parser_parseKind)(QVal toks, QVal sm, QVal bag);
typedef Rec0_QTuple_QTuple_String_Int_089a135111b1225c * (*quest_sig_questlang__syntax__Parser_parseValue)(QVal toks, QVal sm, QVal bag);
#ifdef __cplusplus
}
#endif
#endif
