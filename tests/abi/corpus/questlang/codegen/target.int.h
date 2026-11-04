#ifndef QUEST_INTF_QUESTLANG__CODEGEN__TARGET_H
#define QUEST_INTF_QUESTLANG__CODEGEN__TARGET_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/ssa/nodes.int.h"
#ifndef QUEST_TYPE_QOption_classInt_classReal_TYPEDEF
#define QUEST_TYPE_QOption_classInt_classReal_TYPEDEF
typedef struct QOption_classInt_classReal QOption_classInt_classReal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_TYPEDEF
#define QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_TYPEDEF
typedef struct QTuple_String_QOption_classInt_classReal_end QTuple_String_QOption_classInt_classReal_end;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_TYPEDEF
typedef struct QTuple_QArray_QTuple_Str_822a60fcf247226d QTuple_QArray_QTuple_Str_822a60fcf247226d;
#endif
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_TYPEDEF
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_TYPEDEF
typedef struct QOption_typeInt_typePtr_typeReal_typeVal QOption_typeInt_typePtr_typeReal_typeVal;
#endif
#ifndef QUEST_TYPE_QOption_classInt_classReal_DEFINED
#define QUEST_TYPE_QOption_classInt_classReal_DEFINED
struct QOption_classInt_classReal {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_DEFINED
#define QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_DEFINED
struct QTuple_String_QOption_classInt_classReal_end {
    QString * _0;
    QOption_classInt_classReal * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_DEFINED
#define QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_DEFINED
struct QTuple_QArray_QTuple_Str_822a60fcf247226d {
    QArray * _0;
    QArray * _1;
    QArray * _2;
    QArray * _3;
    QArray * _4;
    QArray * _5;
    QInt _6;
    QInt _7;
};
#endif
#ifndef QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
#define QUEST_TYPE_QOption_typeInt_typePtr_typeReal_typeVal_DEFINED
struct QOption_typeInt_typePtr_typeReal_typeVal {
    int64_t tag;
};
#endif
typedef QOption_classInt_classReal * quest_type_questlang__codegen__Target_Class;
typedef QTuple_String_QOption_classInt_classReal_end * quest_type_questlang__codegen__Target_Register;
typedef QTuple_QArray_QTuple_Str_822a60fcf247226d * quest_type_questlang__codegen__Target_Target;
typedef QInt quest_sig_questlang__codegen__Target_classes;
typedef QInt (*quest_sig_questlang__codegen__Target_index)(QOption_classInt_classReal * c);
typedef QOption_classInt_classReal * (*quest_sig_questlang__codegen__Target_classOfType)(QOption_typeInt_typePtr_typeReal_typeVal * t);
typedef QString * (*quest_sig_questlang__codegen__Target_name)(QTuple_QArray_QTuple_Str_822a60fcf247226d * t, QInt r);
typedef QOption_classInt_classReal * (*quest_sig_questlang__codegen__Target_classOf)(QTuple_QArray_QTuple_Str_822a60fcf247226d * t, QInt r);
#ifdef __cplusplus
}
#endif
#endif
