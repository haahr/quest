#ifndef QUEST_INTF_QUESTLANG__VALUES__JSON_H
#define QUEST_INTF_QUESTLANG__VALUES__JSON_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/hashmap.int.h"
#include "collections/vector.int.h"
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__2204b2cd00845487_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__2204b2cd00845487_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__2204b2cd00845487 RecGroup0_0_QTuple_QVal__2204b2cd00845487;
#endif
#ifndef QUEST_TYPE_QTuple_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_Bool_TYPEDEF
typedef struct QTuple_Bool QTuple_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_String_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_Bool_TYPEDEF
typedef struct QTuple_String_Bool QTuple_String_Bool;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__121ac62dfb585d0a_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__121ac62dfb585d0a_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__121ac62dfb585d0a RecGroup0_0_QTuple_QVal__121ac62dfb585d0a;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QTupl_69363c8d9b258c5d_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QTupl_69363c8d9b258c5d_TYPEDEF
typedef struct RecGroup0_0_QTuple_QTupl_69363c8d9b258c5d RecGroup0_0_QTuple_QTupl_69363c8d9b258c5d;
#endif
#ifndef QUEST_TYPE_QTuple_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_TYPEDEF
typedef struct QTuple_String QTuple_String;
#endif
#ifndef QUEST_TYPE_Rec0_QOption_jArray_QTuple_QV_48478140734ce89d_TYPEDEF
#define QUEST_TYPE_Rec0_QOption_jArray_QTuple_QV_48478140734ce89d_TYPEDEF
typedef struct Rec0_QOption_jArray_QTuple_QV_48478140734ce89d Rec0_QOption_jArray_QTuple_QV_48478140734ce89d;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__2204b2cd00845487_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__2204b2cd00845487_DEFINED
struct RecGroup0_0_QTuple_QVal__2204b2cd00845487 {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Bool_DEFINED
#define QUEST_TYPE_QTuple_Bool_DEFINED
struct QTuple_Bool {
    QBoolSlot _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_Bool_DEFINED
struct QTuple_String_Bool {
    QString * _0;
    QBoolSlot _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__121ac62dfb585d0a_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__121ac62dfb585d0a_DEFINED
struct RecGroup0_0_QTuple_QVal__121ac62dfb585d0a {
    QVal _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QTupl_69363c8d9b258c5d_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QTupl_69363c8d9b258c5d_DEFINED
struct RecGroup0_0_QTuple_QTupl_69363c8d9b258c5d {
    RecGroup0_0_QTuple_QVal__121ac62dfb585d0a * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
#endif
#ifndef QUEST_TYPE_Rec0_QOption_jArray_QTuple_QV_48478140734ce89d_DEFINED
#define QUEST_TYPE_Rec0_QOption_jArray_QTuple_QV_48478140734ce89d_DEFINED
struct Rec0_QOption_jArray_QTuple_QV_48478140734ce89d {
    int64_t tag;
    union {
        struct Rec0_QOption_jArray_QTuple_QV_48478140734ce89d_jArray_payload {
            QVal _0;
        } qo_jArray;
        struct Rec0_QOption_jArray_QTuple_QV_48478140734ce89d_jBool_payload {
            QBoolSlot _0;
        } qo_jBool;
        struct Rec0_QOption_jArray_QTuple_QV_48478140734ce89d_jNumber_payload {
            QString * _0;
            QBoolSlot _1;
        } qo_jNumber;
        struct Rec0_QOption_jArray_QTuple_QV_48478140734ce89d_jObject_payload {
            RecGroup0_0_QTuple_QVal__121ac62dfb585d0a * _0;
        } qo_jObject;
        struct Rec0_QOption_jArray_QTuple_QV_48478140734ce89d_jString_payload {
            QString * _0;
        } qo_jString;
    } u;
};
#endif
typedef const QException * quest_sig_questlang__values__Json_error;
typedef Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * (*quest_sig_questlang__values__Json_parse)(QString * text);
typedef Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * (*quest_sig_questlang__values__Json_parseShared)(QString * text);
typedef QString * (*quest_sig_questlang__values__Json_dump)(Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * v);
typedef QString * (*quest_sig_questlang__values__Json_dumpIndented)(Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * v, QInt indent);
typedef Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * quest_sig_questlang__values__Json_null;
typedef Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * (*quest_sig_questlang__values__Json_bool)(QBool b);
typedef Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * (*quest_sig_questlang__values__Json_int)(QInt n);
typedef Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * (*quest_sig_questlang__values__Json_real)(QReal r);
typedef Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * (*quest_sig_questlang__values__Json_number)(QString * text, QBool isInteger);
typedef Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * (*quest_sig_questlang__values__Json_string)(QString * s);
typedef Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * (*quest_sig_questlang__values__Json_arrayValue)(QVal items);
typedef RecGroup0_0_QTuple_QVal__121ac62dfb585d0a * (*quest_sig_questlang__values__Json_newObject)(void);
typedef Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * (*quest_sig_questlang__values__Json_object)(RecGroup0_0_QTuple_QVal__121ac62dfb585d0a * o);
typedef void (*quest_sig_questlang__values__Json_put)(RecGroup0_0_QTuple_QVal__121ac62dfb585d0a * o, QString * name, Rec0_QOption_jArray_QTuple_QV_48478140734ce89d * v);
typedef QVal (*quest_sig_questlang__values__Json_get)(RecGroup0_0_QTuple_QVal__121ac62dfb585d0a * o, QString * name);
typedef QArray * (*quest_sig_questlang__values__Json_names)(RecGroup0_0_QTuple_QVal__121ac62dfb585d0a * o);
#ifdef __cplusplus
}
#endif
#endif
