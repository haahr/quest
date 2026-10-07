#ifndef QUEST_INTF_ASTPRINT_H
#define QUEST_INTF_ASTPRINT_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/syntax/ast.h"
#include "questlang/common/location.h"
#include "collections/vector.h"
#include "util/maybe.h"
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
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
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_13c6519c78f02e5d_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_13c6519c78f02e5d_TYPEDEF
typedef struct QTuple_QTuple_String_Int_13c6519c78f02e5d QTuple_QTuple_String_Int_13c6519c78f02e5d;
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
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_13c6519c78f02e5d_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_13c6519c78f02e5d_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_13c6519c78f02e5d QTuple_QTuple_QTuple_String_Int_13c6519c78f02e5d;
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
#ifndef QUEST_TYPE_QTuple_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal QTuple_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_13c6519c78f02e5d_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_13c6519c78f02e5d_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTuple_String_Int_13c6519c78f02e5d_QVal_QVal QTuple_QVal_QTuple_QTuple_String_Int_13c6519c78f02e5d_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_ce1e97614d700b81_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_ce1e97614d700b81_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_ce1e97614d700b81 QTuple_String_QTuple_QTu_ce1e97614d700b81;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTupl_af8ac4a6849de8d5_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTupl_af8ac4a6849de8d5_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTupl_af8ac4a6849de8d5 QTuple_QVal_QTuple_QTupl_af8ac4a6849de8d5;
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
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_664ed25f4ebc542a_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_664ed25f4ebc542a_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_664ed25f4ebc542a QTuple_String_QTuple_QTu_664ed25f4ebc542a;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_13c6519c78f02e5d_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_13c6519c78f02e5d_TYPEDEF
typedef struct QTuple_String_QTuple_QTuple_String_Int_13c6519c78f02e5d QTuple_String_QTuple_QTuple_String_Int_13c6519c78f02e5d;
#endif
#ifndef QUEST_TYPE_QOption_exprInt_QTuple_I_c3f65cd6dff194d6_TYPEDEF
#define QUEST_TYPE_QOption_exprInt_QTuple_I_c3f65cd6dff194d6_TYPEDEF
typedef struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6 QOption_exprInt_QTuple_I_c3f65cd6dff194d6;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_811234aa131d634d_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_811234aa131d634d_TYPEDEF
typedef struct QTuple_QTuple_String_Int_811234aa131d634d QTuple_QTuple_String_Int_811234aa131d634d;
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
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_b9bfb5d5d265e4de_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_b9bfb5d5d265e4de_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_b9bfb5d5d265e4de QTuple_QTuple_QTuple_Str_b9bfb5d5d265e4de;
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
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_811234aa131d634d_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_811234aa131d634d_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_811234aa131d634d QTuple_QTuple_QTuple_String_Int_811234aa131d634d;
#endif
#ifndef QUEST_TYPE_QOption_phraseImport_QTu_1694a934a18c1f37_TYPEDEF
#define QUEST_TYPE_QOption_phraseImport_QTu_1694a934a18c1f37_TYPEDEF
typedef struct QOption_phraseImport_QTu_1694a934a18c1f37 QOption_phraseImport_QTu_1694a934a18c1f37;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_cb8b9093396603d6_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_cb8b9093396603d6_TYPEDEF
typedef struct QTuple_QTuple_String_Int_cb8b9093396603d6 QTuple_QTuple_String_Int_cb8b9093396603d6;
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
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_13c6519c78f02e5d_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_13c6519c78f02e5d_DEFINED
struct QTuple_QTuple_String_Int_13c6519c78f02e5d {
    QTuple_String_Int_Int * _0;
    QOption_kindType_kindPow_72f4e761a8d49456 * _1;
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
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_13c6519c78f02e5d_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_13c6519c78f02e5d_DEFINED
struct QTuple_QTuple_QTuple_String_Int_13c6519c78f02e5d {
    QTuple_QTuple_String_Int_13c6519c78f02e5d * _0;
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
#ifndef QUEST_TYPE_QTuple_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_DEFINED
struct QTuple_QVal_QVal {
    QVal _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_13c6519c78f02e5d_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_13c6519c78f02e5d_QVal_QVal_DEFINED
struct QTuple_QVal_QTuple_QTuple_String_Int_13c6519c78f02e5d_QVal_QVal {
    QVal _0;
    QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_ce1e97614d700b81_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_ce1e97614d700b81_DEFINED
struct QTuple_String_QTuple_QTu_ce1e97614d700b81 {
    QString * _0;
    QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
    QBool _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTupl_af8ac4a6849de8d5_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTupl_af8ac4a6849de8d5_DEFINED
struct QTuple_QVal_QTuple_QTupl_af8ac4a6849de8d5 {
    QVal _0;
    QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
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
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_664ed25f4ebc542a_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_664ed25f4ebc542a_DEFINED
struct QTuple_String_QTuple_QTu_664ed25f4ebc542a {
    QString * _0;
    QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
    QVal _2;
    QVal _3;
    QBool _4;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_13c6519c78f02e5d_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_13c6519c78f02e5d_DEFINED
struct QTuple_String_QTuple_QTuple_String_Int_13c6519c78f02e5d {
    QString * _0;
    QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
};
#endif
#ifndef QUEST_TYPE_QOption_exprInt_QTuple_I_c3f65cd6dff194d6_DEFINED
#define QUEST_TYPE_QOption_exprInt_QTuple_I_c3f65cd6dff194d6_DEFINED
struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6 {
    int64_t tag;
    union {
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprInt_payload {
            QInt _0;
            QString * _1;
        } exprInt;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprReal_payload {
            QReal _0;
            QString * _1;
        } exprReal;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprChar_payload {
            QChar _0;
            QString * _1;
        } exprChar;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprString_payload {
            QString * _0;
            QString * _1;
        } exprString;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprBool_payload {
            QBool _0;
        } exprBool;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprId_payload {
            QString * _0;
        } exprId;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprExternal_payload {
            QString * _0;
        } exprExternal;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_typeArg_payload {
            QTuple_QTuple_String_Int_13c6519c78f02e5d * _0;
        } typeArg;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_kindArg_payload {
            QTuple_QTuple_String_Int_13c6519c78f02e5d * _0;
        } kindArg;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprBlock_payload {
            QVal _0;
        } exprBlock;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprIf_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QVal _2;
            QVal _3;
        } exprIf;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprWhile_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprWhile;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprLoop_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } exprLoop;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprFor_payload {
            QString * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QBool _2;
            QTuple_QTuple_String_Int_Int_QVal * _3;
            QTuple_QTuple_String_Int_Int_QVal * _4;
        } exprFor;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprFun_payload {
            QVal _0;
            QVal _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
            QVal _3;
        } exprFun;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprApp_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
        } exprApp;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprInfix_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } exprInfix;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprTuple_payload {
            QVal _0;
        } exprTuple;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprRecord_payload {
            QVal _0;
        } exprRecord;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprArray_payload {
            QVal _0;
            QVal _1;
        } exprArray;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprArrayRep_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprArrayRep;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprOption_payload {
            QVal _0;
            QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
            QVal _2;
            QVal _3;
        } exprOption;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprVariant_payload {
            QString * _0;
            QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
            QBool _2;
            QVal _3;
        } exprVariant;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprAuto_payload {
            QVal _0;
            QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } exprAuto;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprSelect_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
        } exprSelect;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprIndex_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprIndex;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprIndexAssign_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } exprIndexAssign;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprAssign_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprAssign;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprVarCell_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } exprVarCell;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprDerefCell_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } exprDerefCell;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprVariantCheck_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
        } exprVariantCheck;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprVariantAssert_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
        } exprVariantAssert;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprCase_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprCase;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprInspect_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprInspect;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprException_payload {
            QString * _0;
            QVal _1;
        } exprException;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprRaise_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprRaise;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_exprTry_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprTry;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_declLetVal_payload {
            QString * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QVal _2;
            QVal _3;
            QBool _4;
            QBool _5;
        } declLetVal;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_declLetType_payload {
            QString * _0;
            QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declLetType;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_declDefType_payload {
            QString * _0;
            QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declDefType;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_declDefKind_payload {
            QString * _0;
            QTuple_QTuple_String_Int_13c6519c78f02e5d * _1;
        } declDefKind;
        struct QOption_exprInt_QTuple_I_c3f65cd6dff194d6_declExprStmt_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } declExprStmt;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_811234aa131d634d_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_811234aa131d634d_DEFINED
struct QTuple_QTuple_String_Int_811234aa131d634d {
    QTuple_String_Int_Int * _0;
    QOption_exprInt_QTuple_I_c3f65cd6dff194d6 * _1;
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
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_b9bfb5d5d265e4de_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_b9bfb5d5d265e4de_DEFINED
struct QTuple_QTuple_QTuple_Str_b9bfb5d5d265e4de {
    QTuple_QTuple_String_Int_13c6519c78f02e5d * _0;
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
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_811234aa131d634d_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_811234aa131d634d_DEFINED
struct QTuple_QTuple_QTuple_String_Int_811234aa131d634d {
    QTuple_QTuple_String_Int_811234aa131d634d * _0;
};
#endif
#ifndef QUEST_TYPE_QOption_phraseImport_QTu_1694a934a18c1f37_DEFINED
#define QUEST_TYPE_QOption_phraseImport_QTu_1694a934a18c1f37_DEFINED
struct QOption_phraseImport_QTu_1694a934a18c1f37 {
    int64_t tag;
    union {
        struct QOption_phraseImport_QTu_1694a934a18c1f37_phraseImport_payload {
            QTuple_QVal * _0;
        } phraseImport;
        struct QOption_phraseImport_QTu_1694a934a18c1f37_phraseInterface_payload {
            QTuple_String_QVal_QVal_Bool * _0;
        } phraseInterface;
        struct QOption_phraseImport_QTu_1694a934a18c1f37_phraseModule_payload {
            QTuple_String_String_QVal_QVal_Bool * _0;
        } phraseModule;
        struct QOption_phraseImport_QTu_1694a934a18c1f37_phraseDecl_payload {
            QTuple_QTuple_String_Int_811234aa131d634d * _0;
        } phraseDecl;
        struct QOption_phraseImport_QTu_1694a934a18c1f37_phraseExpr_payload {
            QTuple_QTuple_String_Int_811234aa131d634d * _0;
        } phraseExpr;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_cb8b9093396603d6_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_cb8b9093396603d6_DEFINED
struct QTuple_QTuple_String_Int_cb8b9093396603d6 {
    QTuple_String_Int_Int * _0;
    QOption_phraseImport_QTu_1694a934a18c1f37 * _1;
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
typedef QString * (*quest_sig_AstPrint_dumpTypeExpr)(QTuple_QTuple_String_Int_13c6519c78f02e5d * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpExpr)(QTuple_QTuple_String_Int_811234aa131d634d * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpDecl)(QTuple_QTuple_String_Int_811234aa131d634d * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpPhrase)(QTuple_QTuple_String_Int_cb8b9093396603d6 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpProgram)(QTuple_QTuple_String_Int_Int_QTuple_QVal * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dump)(QTuple_QTuple_String_Int_Int_QTuple_QVal * node);
typedef QString * (*quest_sig_AstPrint_dumpWithOptions)(QTuple_QTuple_String_Int_Int_QTuple_QVal * node, QBool showOffsets);
#ifdef __cplusplus
}
#endif
#endif
