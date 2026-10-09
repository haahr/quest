#ifndef QUEST_INTF_ASTPRINT_H
#define QUEST_INTF_ASTPRINT_H
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
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_078ab958ffb5fc9c_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_078ab958ffb5fc9c_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_078ab958ffb5fc9c QTuple_String_QTuple_QTu_078ab958ffb5fc9c;
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
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_TYPEDEF
typedef struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a QTuple_QVal_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_75e301123974ded1_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_75e301123974ded1_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_75e301123974ded1 QTuple_QTuple_QTuple_Str_75e301123974ded1;
#endif
#ifndef QUEST_TYPE_QOption_kindType_kindPow_1cb6727432a97f8f_TYPEDEF
#define QUEST_TYPE_QOption_kindType_kindPow_1cb6727432a97f8f_TYPEDEF
typedef struct QOption_kindType_kindPow_1cb6727432a97f8f QOption_kindType_kindPow_1cb6727432a97f8f;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_TYPEDEF
typedef struct QTuple_QTuple_String_Int_3a0c2e3aad3d333a QTuple_QTuple_String_Int_3a0c2e3aad3d333a;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_QVal QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_Int_QVal QTuple_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_4f82c651ca64293d_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_4f82c651ca64293d_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_4f82c651ca64293d QTuple_String_QTuple_QTu_4f82c651ca64293d;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_0189c9ffd21fac99_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_0189c9ffd21fac99_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_0189c9ffd21fac99 QTuple_QTuple_QTuple_Str_0189c9ffd21fac99;
#endif
#ifndef QUEST_TYPE_QOption_kindType_kindPow_72f4e761a8d49456_TYPEDEF
#define QUEST_TYPE_QOption_kindType_kindPow_72f4e761a8d49456_TYPEDEF
typedef struct QOption_kindType_kindPow_72f4e761a8d49456 QOption_kindType_kindPow_72f4e761a8d49456;
#endif
#ifndef QUEST_TYPE_QOption_modeValue_modeVar_modeOut_TYPEDEF
#define QUEST_TYPE_QOption_modeValue_modeVar_modeOut_TYPEDEF
typedef struct QOption_modeValue_modeVar_modeOut QOption_modeValue_modeVar_modeOut;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_e1dfc5ca9f901776_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_e1dfc5ca9f901776_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_e1dfc5ca9f901776 QTuple_String_QTuple_QTu_e1dfc5ca9f901776;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut_TYPEDEF
typedef struct QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool_TYPEDEF
typedef struct QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_TYPEDEF
typedef struct QTuple_String_QVal QTuple_String_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_String_QTuple_QTuple_String_Int_Int_QVal QTuple_String_QTuple_QTuple_String_Int_Int_QVal;
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
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_dcdf2e3869567e4e_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_dcdf2e3869567e4e_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_dcdf2e3869567e4e QTuple_QTuple_QTuple_Str_dcdf2e3869567e4e;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_a0ad571f01f1eebe_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_a0ad571f01f1eebe_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_a0ad571f01f1eebe QTuple_QTuple_QTuple_Str_a0ad571f01f1eebe;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2 QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_71e7552862ef6713_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_71e7552862ef6713_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_71e7552862ef6713 QTuple_String_QTuple_QTu_71e7552862ef6713;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal QTuple_QVal_QVal_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_4cbe271f6e457190_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_4cbe271f6e457190_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_4cbe271f6e457190 QTuple_QTuple_QTuple_Str_4cbe271f6e457190;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal QTuple_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_QVal QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_965b2bf3d703d533_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_965b2bf3d703d533_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_965b2bf3d703d533 QTuple_String_QTuple_QTu_965b2bf3d703d533;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTupl_f77b8905aff9e440_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTupl_f77b8905aff9e440_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTupl_f77b8905aff9e440 QTuple_QVal_QTuple_QTupl_f77b8905aff9e440;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_String_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_String_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_String QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_String;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_9b09ec8d6f8aaf91_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_9b09ec8d6f8aaf91_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_9b09ec8d6f8aaf91 QTuple_QTuple_QTuple_Str_9b09ec8d6f8aaf91;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_QVal_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_QVal QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_a23e2b45e53555d4_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_a23e2b45e53555d4_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_a23e2b45e53555d4 QTuple_String_QTuple_QTu_a23e2b45e53555d4;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_f1a4592dcff89e6d_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_f1a4592dcff89e6d_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_f1a4592dcff89e6d QTuple_String_QTuple_QTu_f1a4592dcff89e6d;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_TYPEDEF
typedef struct QTuple_String_QTuple_QTuple_String_Int_3a0c2e3aad3d333a QTuple_String_QTuple_QTuple_String_Int_3a0c2e3aad3d333a;
#endif
#ifndef QUEST_TYPE_QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_TYPEDEF
#define QUEST_TYPE_QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_TYPEDEF
typedef struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_10deebb368c2ced2_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_10deebb368c2ced2_TYPEDEF
typedef struct QTuple_QTuple_String_Int_10deebb368c2ced2 QTuple_QTuple_String_Int_10deebb368c2ced2;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_38c3d6c8d388224b_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_38c3d6c8d388224b_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_38c3d6c8d388224b QTuple_QTuple_QTuple_Str_38c3d6c8d388224b;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_3350f431cf92dfc0_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_3350f431cf92dfc0_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_3350f431cf92dfc0 QTuple_QTuple_QTuple_Str_3350f431cf92dfc0;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_71b79add6d91522c_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_71b79add6d91522c_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_71b79add6d91522c QTuple_String_QTuple_QTu_71b79add6d91522c;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTupl_a23d546c00397ba9_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTupl_a23d546c00397ba9_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTupl_a23d546c00397ba9 QTuple_QVal_QTuple_QTupl_a23d546c00397ba9;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_String_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_String_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_Int_QVal_String QTuple_QTuple_QTuple_String_Int_Int_QVal_String;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_4e51da671e850c1f_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_4e51da671e850c1f_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_4e51da671e850c1f QTuple_QTuple_QTuple_Str_4e51da671e850c1f;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_2200c6a3d5421263_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_2200c6a3d5421263_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_2200c6a3d5421263 QTuple_String_QTuple_QTu_2200c6a3d5421263;
#endif
#ifndef QUEST_TYPE_QOption_exprInt_QTuple_I_97ab61e6abeceed8_TYPEDEF
#define QUEST_TYPE_QOption_exprInt_QTuple_I_97ab61e6abeceed8_TYPEDEF
typedef struct QOption_exprInt_QTuple_I_97ab61e6abeceed8 QOption_exprInt_QTuple_I_97ab61e6abeceed8;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QOption_modeValue_modeVar_modeOut_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_QOption_modeValue_modeVar_modeOut_TYPEDEF
typedef struct QTuple_String_QVal_QOption_modeValue_modeVar_modeOut QTuple_String_QVal_QOption_modeValue_modeVar_modeOut;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QOption_fieldVal_QTuple__168c8db8e15234f1_TYPEDEF
#define QUEST_TYPE_QOption_fieldVal_QTuple__168c8db8e15234f1_TYPEDEF
typedef struct QOption_fieldVal_QTuple__168c8db8e15234f1 QOption_fieldVal_QTuple__168c8db8e15234f1;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_c9ec874b9fad01e5_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_c9ec874b9fad01e5_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_c9ec874b9fad01e5 QTuple_QTuple_QTuple_Str_c9ec874b9fad01e5;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_ca206c534ceb51b5_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_ca206c534ceb51b5_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_ca206c534ceb51b5 QTuple_QTuple_QTuple_Str_ca206c534ceb51b5;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QVal_TYPEDEF
typedef struct QTuple_QTuple_QVal QTuple_QTuple_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_String_QVal_QVal_Bool QTuple_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_QTuple_String_QVal_QVal_Bool QTuple_QTuple_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_String_String_QVal_QVal_Bool QTuple_String_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_QTuple_String_String_QVal_QVal_Bool QTuple_QTuple_String_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QOption_phraseImport_QTu_4d80929bcf4431c0_TYPEDEF
#define QUEST_TYPE_QOption_phraseImport_QTu_4d80929bcf4431c0_TYPEDEF
typedef struct QOption_phraseImport_QTu_4d80929bcf4431c0 QOption_phraseImport_QTu_4d80929bcf4431c0;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_dcab081cbddad95f_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_dcab081cbddad95f_TYPEDEF
typedef struct QTuple_QTuple_String_Int_dcab081cbddad95f QTuple_QTuple_String_Int_dcab081cbddad95f;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_String_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_String_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_String_QVal_QVal QTuple_QVal_String_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_QTuple_QVal_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_QTuple_QVal QTuple_QTuple_String_Int_Int_QTuple_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_DEFINED
struct QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a {
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_078ab958ffb5fc9c_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_078ab958ffb5fc9c_DEFINED
struct QTuple_String_QTuple_QTu_078ab958ffb5fc9c {
    QString * _0;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _2;
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
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_DEFINED
struct QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a {
    QVal _0;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_DEFINED
struct QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal {
    QVal _0;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_DEFINED
struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a {
    QVal _0;
    QVal _1;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_DEFINED
struct QTuple_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal {
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_75e301123974ded1_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_75e301123974ded1_DEFINED
struct QTuple_QTuple_QTuple_Str_75e301123974ded1 {
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
    QString * _1;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _2;
};
#endif
#ifndef QUEST_TYPE_QOption_kindType_kindPow_1cb6727432a97f8f_DEFINED
#define QUEST_TYPE_QOption_kindType_kindPow_1cb6727432a97f8f_DEFINED
struct QOption_kindType_kindPow_1cb6727432a97f8f {
    int64_t tag;
    union {
        struct QOption_kindType_kindPow_1cb6727432a97f8f_kindPower_payload {
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
        } kindPower;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_kindAll_payload {
            QString * _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _2;
        } kindAll;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_kindId_payload {
            QString * _0;
        } kindId;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_kindManifest_payload {
            QString * _0;
            QString * _1;
        } kindManifest;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typePath_payload {
            QVal _0;
        } typePath;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeAll_payload {
            QVal _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
        } typeAll;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeTuple_payload {
            QVal _0;
        } typeTuple;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeRecord_payload {
            QVal _0;
        } typeRecord;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeOption_payload {
            QVal _0;
        } typeOption;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeVariant_payload {
            QVal _0;
        } typeVariant;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeAuto_payload {
            QVal _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QVal _2;
        } typeAuto;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeFun_payload {
            QVal _0;
            QVal _1;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _2;
        } typeFun;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeRec_payload {
            QString * _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _2;
        } typeRec;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeApp_payload {
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
            QVal _1;
        } typeApp;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeInfix_payload {
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
            QString * _1;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _2;
        } typeInfix;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeArray_payload {
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
        } typeArray;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeVar_payload {
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
        } typeVar;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeOut_payload {
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
        } typeOut;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeManifest_payload {
            QString * _0;
            QString * _1;
        } typeManifest;
        struct QOption_kindType_kindPow_1cb6727432a97f8f_typeExternal_payload {
            QString * _0;
        } typeExternal;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_DEFINED
struct QTuple_QTuple_String_Int_3a0c2e3aad3d333a {
    QTuple_String_Int_Int * _0;
    QOption_kindType_kindPow_1cb6727432a97f8f * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_QTuple_String_Int_Int_QVal {
    QTuple_String_Int_Int * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_QTuple_QTuple_String_Int_Int_QVal {
    QTuple_QTuple_String_Int_Int_QVal * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_4f82c651ca64293d_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_4f82c651ca64293d_DEFINED
struct QTuple_String_QTuple_QTu_4f82c651ca64293d {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal {
    QVal _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal {
    QVal _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal {
    QVal _0;
    QVal _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
struct QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_0189c9ffd21fac99_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_0189c9ffd21fac99_DEFINED
struct QTuple_QTuple_QTuple_Str_0189c9ffd21fac99 {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QString * _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QOption_kindType_kindPow_72f4e761a8d49456_DEFINED
#define QUEST_TYPE_QOption_kindType_kindPow_72f4e761a8d49456_DEFINED
struct QOption_kindType_kindPow_72f4e761a8d49456 {
    int64_t tag;
    union {
        struct QOption_kindType_kindPow_72f4e761a8d49456_kindPower_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } kindPower;
        struct QOption_kindType_kindPow_72f4e761a8d49456_kindAll_payload {
            QString * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } kindAll;
        struct QOption_kindType_kindPow_72f4e761a8d49456_kindId_payload {
            QString * _0;
        } kindId;
        struct QOption_kindType_kindPow_72f4e761a8d49456_kindManifest_payload {
            QString * _0;
            QString * _1;
        } kindManifest;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typePath_payload {
            QVal _0;
        } typePath;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeAll_payload {
            QVal _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } typeAll;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeTuple_payload {
            QVal _0;
        } typeTuple;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeRecord_payload {
            QVal _0;
        } typeRecord;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeOption_payload {
            QVal _0;
        } typeOption;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeVariant_payload {
            QVal _0;
        } typeVariant;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeAuto_payload {
            QVal _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QVal _2;
        } typeAuto;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeFun_payload {
            QVal _0;
            QVal _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } typeFun;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeRec_payload {
            QString * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } typeRec;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeApp_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
        } typeApp;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeInfix_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } typeInfix;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeArray_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } typeArray;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeVar_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } typeVar;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeOut_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } typeOut;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeManifest_payload {
            QString * _0;
            QString * _1;
        } typeManifest;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeExternal_payload {
            QString * _0;
        } typeExternal;
    } u;
};
#endif
#ifndef QUEST_TYPE_QOption_modeValue_modeVar_modeOut_DEFINED
#define QUEST_TYPE_QOption_modeValue_modeVar_modeOut_DEFINED
struct QOption_modeValue_modeVar_modeOut {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_e1dfc5ca9f901776_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_e1dfc5ca9f901776_DEFINED
struct QTuple_String_QTuple_QTu_e1dfc5ca9f901776 {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QOption_modeValue_modeVar_modeOut * _2;
    QBool _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut_DEFINED
struct QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut {
    QVal _0;
    QVal _1;
    QOption_modeValue_modeVar_modeOut * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool_DEFINED
struct QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QBool _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_DEFINED
struct QTuple_String_QVal {
    QString * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_String_QTuple_QTuple_String_Int_Int_QVal {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
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
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_dcdf2e3869567e4e_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_dcdf2e3869567e4e_DEFINED
struct QTuple_QTuple_QTuple_Str_dcdf2e3869567e4e {
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_a0ad571f01f1eebe_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_a0ad571f01f1eebe_DEFINED
struct QTuple_QTuple_QTuple_Str_a0ad571f01f1eebe {
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_DEFINED
struct QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2 {
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_71e7552862ef6713_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_71e7552862ef6713_DEFINED
struct QTuple_String_QTuple_QTu_71e7552862ef6713 {
    QString * _0;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
    QBool _2;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _3;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _4;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_DEFINED
struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal {
    QVal _0;
    QVal _1;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_DEFINED
struct QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal {
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_4cbe271f6e457190_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_4cbe271f6e457190_DEFINED
struct QTuple_QTuple_QTuple_Str_4cbe271f6e457190 {
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
    QString * _1;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_DEFINED
struct QTuple_QVal_QVal {
    QVal _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_QVal_DEFINED
struct QTuple_QVal_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_QVal_QVal {
    QVal _0;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_965b2bf3d703d533_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_965b2bf3d703d533_DEFINED
struct QTuple_String_QTuple_QTu_965b2bf3d703d533 {
    QString * _0;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
    QBool _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTupl_f77b8905aff9e440_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTupl_f77b8905aff9e440_DEFINED
struct QTuple_QVal_QTuple_QTupl_f77b8905aff9e440 {
    QVal _0;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_String_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_String_DEFINED
struct QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_String {
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_9b09ec8d6f8aaf91_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_9b09ec8d6f8aaf91_DEFINED
struct QTuple_QTuple_QTuple_Str_9b09ec8d6f8aaf91 {
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_QVal_DEFINED
struct QTuple_QTuple_QTuple_String_Int_10deebb368c2ced2_QVal_QVal {
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_a23e2b45e53555d4_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_a23e2b45e53555d4_DEFINED
struct QTuple_String_QTuple_QTu_a23e2b45e53555d4 {
    QString * _0;
    QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
    QVal _2;
    QVal _3;
    QBool _4;
    QBool _5;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_f1a4592dcff89e6d_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_f1a4592dcff89e6d_DEFINED
struct QTuple_String_QTuple_QTu_f1a4592dcff89e6d {
    QString * _0;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
    QVal _2;
    QVal _3;
    QBool _4;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_3a0c2e3aad3d333a_DEFINED
struct QTuple_String_QTuple_QTuple_String_Int_3a0c2e3aad3d333a {
    QString * _0;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
};
#endif
#ifndef QUEST_TYPE_QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_DEFINED
#define QUEST_TYPE_QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_DEFINED
struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf {
    int64_t tag;
    union {
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprInt_payload {
            QInt _0;
            QString * _1;
        } exprInt;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprReal_payload {
            QReal _0;
            QString * _1;
        } exprReal;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprChar_payload {
            QChar _0;
            QString * _1;
        } exprChar;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprString_payload {
            QString * _0;
            QString * _1;
        } exprString;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprBool_payload {
            QBool _0;
        } exprBool;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprId_payload {
            QString * _0;
        } exprId;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprExternal_payload {
            QString * _0;
        } exprExternal;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_typeArg_payload {
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
        } typeArg;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_kindArg_payload {
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
        } kindArg;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprBlock_payload {
            QVal _0;
        } exprBlock;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprIf_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
            QVal _2;
            QVal _3;
        } exprIf;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprWhile_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
        } exprWhile;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprLoop_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
        } exprLoop;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprFor_payload {
            QString * _0;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
            QBool _2;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _3;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _4;
        } exprFor;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprFun_payload {
            QVal _0;
            QVal _1;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _2;
            QVal _3;
        } exprFun;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprApp_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QVal _1;
        } exprApp;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprInfix_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QString * _1;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _2;
        } exprInfix;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprTuple_payload {
            QVal _0;
        } exprTuple;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprRecord_payload {
            QVal _0;
        } exprRecord;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprArray_payload {
            QVal _0;
            QVal _1;
        } exprArray;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprArrayRep_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
        } exprArrayRep;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprOption_payload {
            QVal _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QVal _2;
            QVal _3;
        } exprOption;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprVariant_payload {
            QString * _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QBool _2;
            QVal _3;
        } exprVariant;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprAuto_payload {
            QVal _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _2;
        } exprAuto;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprSelect_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QString * _1;
        } exprSelect;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprIndex_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
        } exprIndex;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprIndexAssign_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _2;
        } exprIndexAssign;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprAssign_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
        } exprAssign;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprVarCell_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
        } exprVarCell;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprDerefCell_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
        } exprDerefCell;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprVariantCheck_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QString * _1;
        } exprVariantCheck;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprVariantAssert_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QString * _1;
        } exprVariantAssert;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprCase_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QVal _1;
            QVal _2;
        } exprCase;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprInspect_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QVal _1;
            QVal _2;
        } exprInspect;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprException_payload {
            QString * _0;
            QVal _1;
        } exprException;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprRaise_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QVal _1;
            QVal _2;
        } exprRaise;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_exprTry_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
            QVal _1;
            QVal _2;
        } exprTry;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_declLetVal_payload {
            QString * _0;
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _1;
            QVal _2;
            QVal _3;
            QBool _4;
            QBool _5;
        } declLetVal;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_declLetType_payload {
            QString * _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declLetType;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_declDefType_payload {
            QString * _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declDefType;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_declDefKind_payload {
            QString * _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
        } declDefKind;
        struct QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf_declExprStmt_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
        } declExprStmt;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_10deebb368c2ced2_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_10deebb368c2ced2_DEFINED
struct QTuple_QTuple_String_Int_10deebb368c2ced2 {
    QTuple_String_Int_Int * _0;
    QOption_exprInt_QTuple_I_4a7e2e29a4a36ecf * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_38c3d6c8d388224b_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_38c3d6c8d388224b_DEFINED
struct QTuple_QTuple_QTuple_Str_38c3d6c8d388224b {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_3350f431cf92dfc0_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_3350f431cf92dfc0_DEFINED
struct QTuple_QTuple_QTuple_Str_3350f431cf92dfc0 {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_71b79add6d91522c_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_71b79add6d91522c_DEFINED
struct QTuple_String_QTuple_QTu_71b79add6d91522c {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QBool _2;
    QTuple_QTuple_String_Int_Int_QVal * _3;
    QTuple_QTuple_String_Int_Int_QVal * _4;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal {
    QVal _0;
    QVal _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTupl_a23d546c00397ba9_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTupl_a23d546c00397ba9_DEFINED
struct QTuple_QVal_QTuple_QTupl_a23d546c00397ba9 {
    QVal _0;
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_String_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_String_DEFINED
struct QTuple_QTuple_QTuple_String_Int_Int_QVal_String {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_4e51da671e850c1f_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_4e51da671e850c1f_DEFINED
struct QTuple_QTuple_QTuple_Str_4e51da671e850c1f {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal_DEFINED
struct QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_2200c6a3d5421263_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_2200c6a3d5421263_DEFINED
struct QTuple_String_QTuple_QTu_2200c6a3d5421263 {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QVal _2;
    QVal _3;
    QBool _4;
    QBool _5;
};
#endif
#ifndef QUEST_TYPE_QOption_exprInt_QTuple_I_97ab61e6abeceed8_DEFINED
#define QUEST_TYPE_QOption_exprInt_QTuple_I_97ab61e6abeceed8_DEFINED
struct QOption_exprInt_QTuple_I_97ab61e6abeceed8 {
    int64_t tag;
    union {
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprInt_payload {
            QInt _0;
            QString * _1;
        } exprInt;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprReal_payload {
            QReal _0;
            QString * _1;
        } exprReal;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprChar_payload {
            QChar _0;
            QString * _1;
        } exprChar;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprString_payload {
            QString * _0;
            QString * _1;
        } exprString;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprBool_payload {
            QBool _0;
        } exprBool;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprId_payload {
            QString * _0;
        } exprId;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprExternal_payload {
            QString * _0;
        } exprExternal;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_typeArg_payload {
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
        } typeArg;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_kindArg_payload {
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
        } kindArg;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprBlock_payload {
            QVal _0;
        } exprBlock;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprIf_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QVal _2;
            QVal _3;
        } exprIf;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprWhile_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprWhile;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprLoop_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } exprLoop;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprFor_payload {
            QString * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QBool _2;
            QTuple_QTuple_String_Int_Int_QVal * _3;
            QTuple_QTuple_String_Int_Int_QVal * _4;
        } exprFor;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprFun_payload {
            QVal _0;
            QVal _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
            QVal _3;
        } exprFun;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprApp_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
        } exprApp;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprInfix_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } exprInfix;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprTuple_payload {
            QVal _0;
        } exprTuple;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprRecord_payload {
            QVal _0;
        } exprRecord;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprArray_payload {
            QVal _0;
            QVal _1;
        } exprArray;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprArrayRep_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprArrayRep;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprOption_payload {
            QVal _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QVal _2;
            QVal _3;
        } exprOption;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprVariant_payload {
            QString * _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QBool _2;
            QVal _3;
        } exprVariant;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprAuto_payload {
            QVal _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } exprAuto;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprSelect_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
        } exprSelect;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprIndex_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprIndex;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprIndexAssign_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } exprIndexAssign;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprAssign_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprAssign;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprVarCell_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } exprVarCell;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprDerefCell_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } exprDerefCell;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprVariantCheck_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
        } exprVariantCheck;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprVariantAssert_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
        } exprVariantAssert;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprCase_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprCase;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprInspect_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprInspect;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprException_payload {
            QString * _0;
            QVal _1;
        } exprException;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprRaise_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprRaise;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_exprTry_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprTry;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_declLetVal_payload {
            QString * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QVal _2;
            QVal _3;
            QBool _4;
            QBool _5;
        } declLetVal;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_declLetType_payload {
            QString * _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declLetType;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_declDefType_payload {
            QString * _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declDefType;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_declDefKind_payload {
            QString * _0;
            QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _1;
        } declDefKind;
        struct QOption_exprInt_QTuple_I_97ab61e6abeceed8_declExprStmt_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } declExprStmt;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QOption_modeValue_modeVar_modeOut_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_QOption_modeValue_modeVar_modeOut_DEFINED
struct QTuple_String_QVal_QOption_modeValue_modeVar_modeOut {
    QString * _0;
    QVal _1;
    QOption_modeValue_modeVar_modeOut * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_DEFINED
struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool {
    QVal _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QVal _2;
    QBool _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_DEFINED
struct QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool {
    QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool * _0;
};
#endif
#ifndef QUEST_TYPE_QOption_fieldVal_QTuple__168c8db8e15234f1_DEFINED
#define QUEST_TYPE_QOption_fieldVal_QTuple__168c8db8e15234f1_DEFINED
struct QOption_fieldVal_QTuple__168c8db8e15234f1 {
    int64_t tag;
    union {
        struct QOption_fieldVal_QTuple__168c8db8e15234f1_fieldVal_payload {
            QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool * _0;
        } fieldVal;
        struct QOption_fieldVal_QTuple__168c8db8e15234f1_fieldDecl_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } fieldDecl;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal {
    QString * _0;
    QVal _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal {
    QVal _0;
    QVal _1;
    QVal _2;
    QTuple_QTuple_String_Int_Int_QVal * _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_c9ec874b9fad01e5_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_c9ec874b9fad01e5_DEFINED
struct QTuple_QTuple_QTuple_Str_c9ec874b9fad01e5 {
    QTuple_QTuple_String_Int_3a0c2e3aad3d333a * _0;
    QVal _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_ca206c534ceb51b5_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_ca206c534ceb51b5_DEFINED
struct QTuple_QTuple_QTuple_Str_ca206c534ceb51b5 {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QVal _1;
    QVal _2;
    QTuple_QTuple_String_Int_Int_QVal * _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QVal_DEFINED
struct QTuple_QTuple_QVal {
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
#ifndef QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_DEFINED
struct QTuple_QTuple_String_QVal_QVal_Bool {
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
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_DEFINED
struct QTuple_QTuple_String_String_QVal_QVal_Bool {
    QTuple_String_String_QVal_QVal_Bool * _0;
};
#endif
#ifndef QUEST_TYPE_QOption_phraseImport_QTu_4d80929bcf4431c0_DEFINED
#define QUEST_TYPE_QOption_phraseImport_QTu_4d80929bcf4431c0_DEFINED
struct QOption_phraseImport_QTu_4d80929bcf4431c0 {
    int64_t tag;
    union {
        struct QOption_phraseImport_QTu_4d80929bcf4431c0_phraseImport_payload {
            QTuple_QVal * _0;
        } phraseImport;
        struct QOption_phraseImport_QTu_4d80929bcf4431c0_phraseInterface_payload {
            QTuple_String_QVal_QVal_Bool * _0;
        } phraseInterface;
        struct QOption_phraseImport_QTu_4d80929bcf4431c0_phraseModule_payload {
            QTuple_String_String_QVal_QVal_Bool * _0;
        } phraseModule;
        struct QOption_phraseImport_QTu_4d80929bcf4431c0_phraseDecl_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
        } phraseDecl;
        struct QOption_phraseImport_QTu_4d80929bcf4431c0_phraseExpr_payload {
            QTuple_QTuple_String_Int_10deebb368c2ced2 * _0;
        } phraseExpr;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_dcab081cbddad95f_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_dcab081cbddad95f_DEFINED
struct QTuple_QTuple_String_Int_dcab081cbddad95f {
    QTuple_String_Int_Int * _0;
    QOption_phraseImport_QTu_4d80929bcf4431c0 * _1;
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
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_QTuple_QVal_DEFINED
struct QTuple_QTuple_String_Int_Int_QTuple_QVal {
    QTuple_String_Int_Int * _0;
    QTuple_QVal * _1;
};
#endif
typedef QString * (*quest_sig_AstPrint_dumpTypeExpr)(QTuple_QTuple_String_Int_3a0c2e3aad3d333a * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpExpr)(QTuple_QTuple_String_Int_10deebb368c2ced2 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpDecl)(QTuple_QTuple_String_Int_10deebb368c2ced2 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpPhrase)(QTuple_QTuple_String_Int_dcab081cbddad95f * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpProgram)(QTuple_QTuple_String_Int_Int_QTuple_QVal * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dump)(QTuple_QTuple_String_Int_Int_QTuple_QVal * node);
typedef QString * (*quest_sig_AstPrint_dumpWithOptions)(QTuple_QTuple_String_Int_Int_QTuple_QVal * node, QBool showOffsets);
#ifdef __cplusplus
}
#endif
#endif
