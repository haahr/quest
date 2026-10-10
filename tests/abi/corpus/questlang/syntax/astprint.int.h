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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_871fc589fc7d4a6c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_871fc589fc7d4a6c_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_871fc589fc7d4a6c RecGroup0_0_QTuple_Self1_871fc589fc7d4a6c;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_84cd86f63fab7311_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_84cd86f63fab7311_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_84cd86f63fab7311 RecGroup0_0_QTuple_Strin_84cd86f63fab7311;
#endif
#ifndef QUEST_TYPE_QTuple_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_TYPEDEF
typedef struct QTuple_String QTuple_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_TYPEDEF
typedef struct QTuple_QVal QTuple_QVal;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__204bcf31a605c31f_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__204bcf31a605c31f_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__204bcf31a605c31f RecGroup0_0_QTuple_QVal__204bcf31a605c31f;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0bf9b089b31bade1_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0bf9b089b31bade1_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__0bf9b089b31bade1 RecGroup0_0_QTuple_QVal__0bf9b089b31bade1;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__33eb30f04a2da736_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__33eb30f04a2da736_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__33eb30f04a2da736 RecGroup0_0_QTuple_QVal__33eb30f04a2da736;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__bb80425c4cebb19a_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__bb80425c4cebb19a_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__bb80425c4cebb19a RecGroup0_0_QTuple_QVal__bb80425c4cebb19a;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__4461947c97f68ff0_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__4461947c97f68ff0_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__4461947c97f68ff0 RecGroup0_0_QTuple_QVal__4461947c97f68ff0;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__5aca0f22fd6a76fa_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__5aca0f22fd6a76fa_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__5aca0f22fd6a76fa RecGroup0_0_QTuple_QVal__5aca0f22fd6a76fa;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__aba49f98f62226ba_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__aba49f98f62226ba_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__aba49f98f62226ba RecGroup0_0_QTuple_QVal__aba49f98f62226ba;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_2a5d9fd069d9c3be_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_2a5d9fd069d9c3be_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_2a5d9fd069d9c3be RecGroup0_0_QTuple_Strin_2a5d9fd069d9c3be;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_2df6f7b5ce9442c7_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_2df6f7b5ce9442c7_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_2df6f7b5ce9442c7 RecGroup0_0_QTuple_Self1_2df6f7b5ce9442c7;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_95c6a03a504b1b94_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_95c6a03a504b1b94_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_95c6a03a504b1b94 RecGroup0_0_QTuple_Self1_95c6a03a504b1b94;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_319f870b9e9af6c0_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_319f870b9e9af6c0_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_319f870b9e9af6c0 RecGroup0_0_QTuple_Self1_319f870b9e9af6c0;
#endif
#ifndef QUEST_TYPE_Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_TYPEDEF
#define QUEST_TYPE_Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_TYPEDEF
typedef struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_TYPEDEF
typedef struct Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_end_QVal QTuple_QTuple_String_Int_Int_end_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_TYPEDEF
typedef struct QTuple_Int_String QTuple_Int_String;
#endif
#ifndef QUEST_TYPE_QTuple_Real_String_TYPEDEF
#define QUEST_TYPE_QTuple_Real_String_TYPEDEF
typedef struct QTuple_Real_String QTuple_Real_String;
#endif
#ifndef QUEST_TYPE_QTuple_Char_String_TYPEDEF
#define QUEST_TYPE_QTuple_Char_String_TYPEDEF
typedef struct QTuple_Char_String QTuple_Char_String;
#endif
#ifndef QUEST_TYPE_QTuple_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_Bool_TYPEDEF
typedef struct QTuple_Bool QTuple_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_TYPEDEF
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_TYPEDEF
typedef struct QTuple_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 QTuple_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__aaf33babfc10a737_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__aaf33babfc10a737_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__aaf33babfc10a737 RecGroup0_0_QTuple_QVal__aaf33babfc10a737;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_ed81d1e015afcc29_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_ed81d1e015afcc29_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_ed81d1e015afcc29 RecGroup0_0_QTuple_Self1_ed81d1e015afcc29;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_564388b89ef416f7_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_564388b89ef416f7_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_564388b89ef416f7 RecGroup0_0_QTuple_Self1_564388b89ef416f7;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_75dab429a38434fd_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_75dab429a38434fd_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_75dab429a38434fd RecGroup0_0_QTuple_Self1_75dab429a38434fd;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_79ad1f78a84cd642_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_79ad1f78a84cd642_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_79ad1f78a84cd642 RecGroup0_0_QTuple_Strin_79ad1f78a84cd642;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__877796574c0b8c9c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__877796574c0b8c9c_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__877796574c0b8c9c RecGroup0_0_QTuple_QVal__877796574c0b8c9c;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_ee516046ccc9a9c9_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_ee516046ccc9a9c9_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_ee516046ccc9a9c9 RecGroup0_0_QTuple_Self1_ee516046ccc9a9c9;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_5f2ec11e64613896_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_5f2ec11e64613896_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_5f2ec11e64613896 RecGroup0_0_QTuple_Self1_5f2ec11e64613896;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__7a54d6d9e7b0abba_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__7a54d6d9e7b0abba_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__7a54d6d9e7b0abba RecGroup0_0_QTuple_QVal__7a54d6d9e7b0abba;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__19be99cedaad3510_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__19be99cedaad3510_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__19be99cedaad3510 RecGroup0_0_QTuple_QVal__19be99cedaad3510;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__d3c4bd38a9792d76_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__d3c4bd38a9792d76_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__d3c4bd38a9792d76 RecGroup0_0_QTuple_QVal__d3c4bd38a9792d76;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_39be1210fd1f8ab1_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_39be1210fd1f8ab1_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_39be1210fd1f8ab1 RecGroup0_0_QTuple_Self1_39be1210fd1f8ab1;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0d68360de3411f7a_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0d68360de3411f7a_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__0d68360de3411f7a RecGroup0_0_QTuple_QVal__0d68360de3411f7a;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_23883f6d91343a6c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_23883f6d91343a6c_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_23883f6d91343a6c RecGroup0_0_QTuple_Strin_23883f6d91343a6c;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__4a7b720b5f8351dd_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__4a7b720b5f8351dd_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__4a7b720b5f8351dd RecGroup0_0_QTuple_QVal__4a7b720b5f8351dd;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_99d7b4bfa0d6caef_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_99d7b4bfa0d6caef_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_99d7b4bfa0d6caef RecGroup0_0_QTuple_Self1_99d7b4bfa0d6caef;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_af89b7cce8a4c547_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_af89b7cce8a4c547_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_af89b7cce8a4c547 RecGroup0_0_QTuple_Self1_af89b7cce8a4c547;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_30491a9a85cafe19_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_30491a9a85cafe19_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_30491a9a85cafe19 RecGroup0_0_QTuple_Self1_30491a9a85cafe19;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_22a01a042388efe1_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_22a01a042388efe1_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_22a01a042388efe1 RecGroup0_0_QTuple_Self1_22a01a042388efe1;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_49defb3d68f8399d_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_49defb3d68f8399d_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_49defb3d68f8399d RecGroup0_0_QTuple_Self1_49defb3d68f8399d;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_d07881c124ad5a63_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_d07881c124ad5a63_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_d07881c124ad5a63 RecGroup0_0_QTuple_Self1_d07881c124ad5a63;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_8c53cb4d65bc25d7_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_8c53cb4d65bc25d7_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_8c53cb4d65bc25d7 RecGroup0_0_QTuple_Self1_8c53cb4d65bc25d7;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_2c9ece956a84c8fd_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_2c9ece956a84c8fd_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_2c9ece956a84c8fd RecGroup0_0_QTuple_Self1_2c9ece956a84c8fd;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f509343d4fd84c7b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f509343d4fd84c7b_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_f509343d4fd84c7b RecGroup0_0_QTuple_Self1_f509343d4fd84c7b;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_TYPEDEF
typedef struct QTuple_String_QVal QTuple_String_QVal;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_fe21024731fe44aa_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_fe21024731fe44aa_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_fe21024731fe44aa RecGroup0_0_QTuple_Self1_fe21024731fe44aa;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_4807f87d0d998c5f_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_4807f87d0d998c5f_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_4807f87d0d998c5f RecGroup0_0_QTuple_Self1_4807f87d0d998c5f;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_eb14858355c059f7_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_eb14858355c059f7_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_eb14858355c059f7 RecGroup0_0_QTuple_Strin_eb14858355c059f7;
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTupl_af5c3802d6575478_TYPEDEF
#define QUEST_TYPE_QTuple_String_Rec0_QTupl_af5c3802d6575478_TYPEDEF
typedef struct QTuple_String_Rec0_QTupl_af5c3802d6575478 QTuple_String_Rec0_QTupl_af5c3802d6575478;
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_TYPEDEF
#define QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_TYPEDEF
typedef struct QTuple_String_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 QTuple_String_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_1d817d552f14347b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_1d817d552f14347b_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_1d817d552f14347b RecGroup0_0_QTuple_Self1_1d817d552f14347b;
#endif
#ifndef QUEST_TYPE_Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_TYPEDEF
#define QUEST_TYPE_Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_TYPEDEF
typedef struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1 Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3_TYPEDEF
typedef struct Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3;
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
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3_TYPEDEF
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3_TYPEDEF
typedef struct QTuple_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 QTuple_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3;
#endif
#ifndef QUEST_TYPE_QOption_phraseImport_QTu_ada7791ae0d57768_TYPEDEF
#define QUEST_TYPE_QOption_phraseImport_QTu_ada7791ae0d57768_TYPEDEF
typedef struct QOption_phraseImport_QTu_ada7791ae0d57768 QOption_phraseImport_QTu_ada7791ae0d57768;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_a9e2cf43a5159852_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_a9e2cf43a5159852_TYPEDEF
typedef struct QTuple_QTuple_String_Int_a9e2cf43a5159852 QTuple_QTuple_String_Int_a9e2cf43a5159852;
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
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_871fc589fc7d4a6c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_871fc589fc7d4a6c_DEFINED
struct RecGroup0_0_QTuple_Self1_871fc589fc7d4a6c {
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_84cd86f63fab7311_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_84cd86f63fab7311_DEFINED
struct RecGroup0_0_QTuple_Strin_84cd86f63fab7311 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _2;
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
#ifndef QUEST_TYPE_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_DEFINED
struct QTuple_QVal {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__204bcf31a605c31f_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__204bcf31a605c31f_DEFINED
struct RecGroup0_0_QTuple_QVal__204bcf31a605c31f {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0bf9b089b31bade1_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0bf9b089b31bade1_DEFINED
struct RecGroup0_0_QTuple_QVal__0bf9b089b31bade1 {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__33eb30f04a2da736_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__33eb30f04a2da736_DEFINED
struct RecGroup0_0_QTuple_QVal__33eb30f04a2da736 {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__bb80425c4cebb19a_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__bb80425c4cebb19a_DEFINED
struct RecGroup0_0_QTuple_QVal__bb80425c4cebb19a {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__4461947c97f68ff0_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__4461947c97f68ff0_DEFINED
struct RecGroup0_0_QTuple_QVal__4461947c97f68ff0 {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__5aca0f22fd6a76fa_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__5aca0f22fd6a76fa_DEFINED
struct RecGroup0_0_QTuple_QVal__5aca0f22fd6a76fa {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__aba49f98f62226ba_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__aba49f98f62226ba_DEFINED
struct RecGroup0_0_QTuple_QVal__aba49f98f62226ba {
    QVal _0;
    QVal _1;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_2a5d9fd069d9c3be_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_2a5d9fd069d9c3be_DEFINED
struct RecGroup0_0_QTuple_Strin_2a5d9fd069d9c3be {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_2df6f7b5ce9442c7_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_2df6f7b5ce9442c7_DEFINED
struct RecGroup0_0_QTuple_Self1_2df6f7b5ce9442c7 {
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_95c6a03a504b1b94_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_95c6a03a504b1b94_DEFINED
struct RecGroup0_0_QTuple_Self1_95c6a03a504b1b94 {
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_319f870b9e9af6c0_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_319f870b9e9af6c0_DEFINED
struct RecGroup0_0_QTuple_Self1_319f870b9e9af6c0 {
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
};
#endif
#ifndef QUEST_TYPE_Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_DEFINED
#define QUEST_TYPE_Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_DEFINED
struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d {
    int64_t tag;
    union {
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_kindPower_payload {
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
        } kindPower;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_kindAll_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _2;
        } kindAll;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_kindId_payload {
            QString * _0;
        } kindId;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_kindManifest_payload {
            QString * _0;
            QString * _1;
        } kindManifest;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typePath_payload {
            QVal _0;
        } typePath;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeAll_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
        } typeAll;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeTuple_payload {
            QVal _0;
        } typeTuple;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeRecord_payload {
            QVal _0;
        } typeRecord;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeOption_payload {
            QVal _0;
        } typeOption;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeVariant_payload {
            QVal _0;
        } typeVariant;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeAuto_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
            QVal _2;
        } typeAuto;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeFun_payload {
            QVal _0;
            QVal _1;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _2;
        } typeFun;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeRec_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _2;
        } typeRec;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeApp_payload {
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
            QVal _1;
        } typeApp;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeInfix_payload {
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
            QString * _1;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _2;
        } typeInfix;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeArray_payload {
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
        } typeArray;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeVar_payload {
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
        } typeVar;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeOut_payload {
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
        } typeOut;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeManifest_payload {
            QString * _0;
            QString * _1;
        } typeManifest;
        struct Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d_typeExternal_payload {
            QString * _0;
        } typeExternal;
    } u;
};
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_DEFINED
struct Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 {
    QTuple_String_Int_Int * _0;
    Rec0_QOption_kindType_kindPow_6e0e16f5f4fcfb4d * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_QVal_DEFINED
struct QTuple_QTuple_String_Int_Int_end_QVal {
    QTuple_String_Int_Int * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_DEFINED
#define QUEST_TYPE_QTuple_Int_String_DEFINED
struct QTuple_Int_String {
    QInt _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Real_String_DEFINED
#define QUEST_TYPE_QTuple_Real_String_DEFINED
struct QTuple_Real_String {
    QReal _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Char_String_DEFINED
#define QUEST_TYPE_QTuple_Char_String_DEFINED
struct QTuple_Char_String {
    QChar _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Bool_DEFINED
#define QUEST_TYPE_QTuple_Bool_DEFINED
struct QTuple_Bool {
    QBool _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_DEFINED
struct QTuple_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 {
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__aaf33babfc10a737_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__aaf33babfc10a737_DEFINED
struct RecGroup0_0_QTuple_QVal__aaf33babfc10a737 {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_ed81d1e015afcc29_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_ed81d1e015afcc29_DEFINED
struct RecGroup0_0_QTuple_Self1_ed81d1e015afcc29 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_564388b89ef416f7_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_564388b89ef416f7_DEFINED
struct RecGroup0_0_QTuple_Self1_564388b89ef416f7 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_75dab429a38434fd_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_75dab429a38434fd_DEFINED
struct RecGroup0_0_QTuple_Self1_75dab429a38434fd {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_79ad1f78a84cd642_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_79ad1f78a84cd642_DEFINED
struct RecGroup0_0_QTuple_Strin_79ad1f78a84cd642 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
    QBool _2;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _3;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _4;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__877796574c0b8c9c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__877796574c0b8c9c_DEFINED
struct RecGroup0_0_QTuple_QVal__877796574c0b8c9c {
    QVal _0;
    QVal _1;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_ee516046ccc9a9c9_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_ee516046ccc9a9c9_DEFINED
struct RecGroup0_0_QTuple_Self1_ee516046ccc9a9c9 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_5f2ec11e64613896_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_5f2ec11e64613896_DEFINED
struct RecGroup0_0_QTuple_Self1_5f2ec11e64613896 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__7a54d6d9e7b0abba_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__7a54d6d9e7b0abba_DEFINED
struct RecGroup0_0_QTuple_QVal__7a54d6d9e7b0abba {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__19be99cedaad3510_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__19be99cedaad3510_DEFINED
struct RecGroup0_0_QTuple_QVal__19be99cedaad3510 {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__d3c4bd38a9792d76_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__d3c4bd38a9792d76_DEFINED
struct RecGroup0_0_QTuple_QVal__d3c4bd38a9792d76 {
    QVal _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_39be1210fd1f8ab1_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_39be1210fd1f8ab1_DEFINED
struct RecGroup0_0_QTuple_Self1_39be1210fd1f8ab1 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0d68360de3411f7a_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0d68360de3411f7a_DEFINED
struct RecGroup0_0_QTuple_QVal__0d68360de3411f7a {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_23883f6d91343a6c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_23883f6d91343a6c_DEFINED
struct RecGroup0_0_QTuple_Strin_23883f6d91343a6c {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
    QBool _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__4a7b720b5f8351dd_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__4a7b720b5f8351dd_DEFINED
struct RecGroup0_0_QTuple_QVal__4a7b720b5f8351dd {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_99d7b4bfa0d6caef_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_99d7b4bfa0d6caef_DEFINED
struct RecGroup0_0_QTuple_Self1_99d7b4bfa0d6caef {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_af89b7cce8a4c547_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_af89b7cce8a4c547_DEFINED
struct RecGroup0_0_QTuple_Self1_af89b7cce8a4c547 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_30491a9a85cafe19_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_30491a9a85cafe19_DEFINED
struct RecGroup0_0_QTuple_Self1_30491a9a85cafe19 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_22a01a042388efe1_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_22a01a042388efe1_DEFINED
struct RecGroup0_0_QTuple_Self1_22a01a042388efe1 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_49defb3d68f8399d_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_49defb3d68f8399d_DEFINED
struct RecGroup0_0_QTuple_Self1_49defb3d68f8399d {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_d07881c124ad5a63_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_d07881c124ad5a63_DEFINED
struct RecGroup0_0_QTuple_Self1_d07881c124ad5a63 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_8c53cb4d65bc25d7_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_8c53cb4d65bc25d7_DEFINED
struct RecGroup0_0_QTuple_Self1_8c53cb4d65bc25d7 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_2c9ece956a84c8fd_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_2c9ece956a84c8fd_DEFINED
struct RecGroup0_0_QTuple_Self1_2c9ece956a84c8fd {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f509343d4fd84c7b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f509343d4fd84c7b_DEFINED
struct RecGroup0_0_QTuple_Self1_f509343d4fd84c7b {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_DEFINED
struct QTuple_String_QVal {
    QString * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_fe21024731fe44aa_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_fe21024731fe44aa_DEFINED
struct RecGroup0_0_QTuple_Self1_fe21024731fe44aa {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_4807f87d0d998c5f_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_4807f87d0d998c5f_DEFINED
struct RecGroup0_0_QTuple_Self1_4807f87d0d998c5f {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_eb14858355c059f7_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_eb14858355c059f7_DEFINED
struct RecGroup0_0_QTuple_Strin_eb14858355c059f7 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
    QVal _2;
    QVal _3;
    QBool _4;
    QBool _5;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTupl_af5c3802d6575478_DEFINED
#define QUEST_TYPE_QTuple_String_Rec0_QTupl_af5c3802d6575478_DEFINED
struct QTuple_String_Rec0_QTupl_af5c3802d6575478 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
    QVal _2;
    QVal _3;
    QBool _4;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_DEFINED
#define QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2_DEFINED
struct QTuple_String_Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_1d817d552f14347b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_1d817d552f14347b_DEFINED
struct RecGroup0_0_QTuple_Self1_1d817d552f14347b {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
};
#endif
#ifndef QUEST_TYPE_Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_DEFINED
#define QUEST_TYPE_Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_DEFINED
struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1 {
    int64_t tag;
    union {
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprInt_payload {
            QInt _0;
            QString * _1;
        } exprInt;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprReal_payload {
            QReal _0;
            QString * _1;
        } exprReal;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprChar_payload {
            QChar _0;
            QString * _1;
        } exprChar;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprString_payload {
            QString * _0;
            QString * _1;
        } exprString;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprBool_payload {
            QBool _0;
        } exprBool;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprId_payload {
            QString * _0;
        } exprId;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprExternal_payload {
            QString * _0;
        } exprExternal;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_typeArg_payload {
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
        } typeArg;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_kindArg_payload {
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _0;
        } kindArg;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprBlock_payload {
            QVal _0;
        } exprBlock;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprIf_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
            QVal _2;
            QVal _3;
        } exprIf;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprWhile_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
        } exprWhile;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprLoop_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
        } exprLoop;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprFor_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
            QBool _2;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _3;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _4;
        } exprFor;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprFun_payload {
            QVal _0;
            QVal _1;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _2;
            QVal _3;
        } exprFun;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprApp_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            QVal _1;
        } exprApp;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprInfix_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            QString * _1;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _2;
        } exprInfix;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprTuple_payload {
            QVal _0;
        } exprTuple;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprRecord_payload {
            QVal _0;
        } exprRecord;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprArray_payload {
            QVal _0;
            QVal _1;
        } exprArray;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprArrayRep_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
        } exprArrayRep;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprOption_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
            QVal _2;
            QVal _3;
        } exprOption;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprVariant_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
            QBool _2;
            QVal _3;
        } exprVariant;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprAuto_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _2;
        } exprAuto;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprSelect_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            QString * _1;
        } exprSelect;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprIndex_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
        } exprIndex;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprIndexAssign_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _2;
        } exprIndexAssign;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprAssign_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
        } exprAssign;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprVarCell_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
        } exprVarCell;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprDerefCell_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
        } exprDerefCell;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprVariantCheck_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            QString * _1;
        } exprVariantCheck;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprVariantAssert_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            QString * _1;
        } exprVariantAssert;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprCase_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            QVal _1;
            QVal _2;
        } exprCase;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprInspect_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            QVal _1;
            QVal _2;
        } exprInspect;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprException_payload {
            QString * _0;
            QVal _1;
        } exprException;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprRaise_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            QVal _1;
            QVal _2;
        } exprRaise;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_exprTry_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
            QVal _1;
            QVal _2;
        } exprTry;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_declLetVal_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _1;
            QVal _2;
            QVal _3;
            QBool _4;
            QBool _5;
        } declLetVal;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_declLetType_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declLetType;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_declDefType_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declDefType;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_declDefKind_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * _1;
        } declDefKind;
        struct Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1_declExprStmt_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
        } declExprStmt;
    } u;
};
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3_DEFINED
struct Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 {
    QTuple_String_Int_Int * _0;
    Rec0_QOption_exprInt_QTuple_I_acec3382f9d87ff1 * _1;
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
    QBool _3;
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
    QBool _4;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_end_DEFINED
struct QTuple_QTuple_String_String_QVal_QVal_Bool_end {
    QTuple_String_String_QVal_QVal_Bool * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3_DEFINED
struct QTuple_Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 {
    Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
};
#endif
#ifndef QUEST_TYPE_QOption_phraseImport_QTu_ada7791ae0d57768_DEFINED
#define QUEST_TYPE_QOption_phraseImport_QTu_ada7791ae0d57768_DEFINED
struct QOption_phraseImport_QTu_ada7791ae0d57768 {
    int64_t tag;
    union {
        struct QOption_phraseImport_QTu_ada7791ae0d57768_phraseImport_payload {
            QTuple_QVal * _0;
        } phraseImport;
        struct QOption_phraseImport_QTu_ada7791ae0d57768_phraseInterface_payload {
            QTuple_String_QVal_QVal_Bool * _0;
        } phraseInterface;
        struct QOption_phraseImport_QTu_ada7791ae0d57768_phraseModule_payload {
            QTuple_String_String_QVal_QVal_Bool * _0;
        } phraseModule;
        struct QOption_phraseImport_QTu_ada7791ae0d57768_phraseDecl_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
        } phraseDecl;
        struct QOption_phraseImport_QTu_ada7791ae0d57768_phraseExpr_payload {
            Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * _0;
        } phraseExpr;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_a9e2cf43a5159852_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_a9e2cf43a5159852_DEFINED
struct QTuple_QTuple_String_Int_a9e2cf43a5159852 {
    QTuple_String_Int_Int * _0;
    QOption_phraseImport_QTu_ada7791ae0d57768 * _1;
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
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpTypeExpr)(Rec0_QTuple_QTuple_String_Int_e1a8f2413afa8de2 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpExpr)(Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpDecl)(Rec0_QTuple_QTuple_String_Int_a20d3b973ed606b3 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpPhrase)(QTuple_QTuple_String_Int_a9e2cf43a5159852 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpProgram)(QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dump)(QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end * node);
typedef QString * (*quest_sig_questlang__syntax__AstPrint_dumpWithOptions)(QTuple_QTuple_String_Int_Int_end_QTuple_QVal_end * node, QBool showOffsets);
#ifdef __cplusplus
}
#endif
#endif
