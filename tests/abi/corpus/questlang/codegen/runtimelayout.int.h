#ifndef QUEST_INTF_QUESTLANG__CODEGEN__RUNTIMELAYOUT_H
#define QUEST_INTF_QUESTLANG__CODEGEN__RUNTIMELAYOUT_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_QArray_QTuple_String_Int_Int_end_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_QArray_QTuple_String_Int_Int_end_TYPEDEF
typedef struct QTuple_String_Int_QArray_QTuple_String_Int_Int_end QTuple_String_Int_QArray_QTuple_String_Int_Int_end;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_TYPEDEF
typedef struct QTuple_String_Int QTuple_String_Int;
#endif
#ifndef QUEST_TYPE_QTuple_String_Real_TYPEDEF
#define QUEST_TYPE_QTuple_String_Real_TYPEDEF
typedef struct QTuple_String_Real QTuple_String_Real;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_QArray_QTuple_String_Int_Int_end_DEFINED
#define QUEST_TYPE_QTuple_String_Int_QArray_QTuple_String_Int_Int_end_DEFINED
struct QTuple_String_Int_QArray_QTuple_String_Int_Int_end {
    QString * _0;
    QInt _1;
    QArray * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_DEFINED
struct QTuple_String_Int {
    QString * _0;
    QInt _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Real_DEFINED
#define QUEST_TYPE_QTuple_String_Real_DEFINED
struct QTuple_String_Real {
    QString * _0;
    QReal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_DEFINED
struct QTuple_String_String {
    QString * _0;
    QString * _1;
};
#endif
typedef QTuple_String_Int_Int * quest_type_questlang__codegen__RuntimeLayout_Member;
typedef QTuple_String_Int_QArray_QTuple_String_Int_Int_end * quest_type_questlang__codegen__RuntimeLayout_Struct;
typedef QTuple_String_Int * quest_type_questlang__codegen__RuntimeLayout_Constant;
typedef QTuple_String_Real * quest_type_questlang__codegen__RuntimeLayout_RealConstant;
typedef QTuple_String_String * quest_type_questlang__codegen__RuntimeLayout_Address;
typedef QArray * quest_sig_questlang__codegen__RuntimeLayout_structs;
typedef QVal (*quest_sig_questlang__codegen__RuntimeLayout_struct)(QString * name);
typedef const QException * quest_sig_questlang__codegen__RuntimeLayout_unknown;
typedef QInt (*quest_sig_questlang__codegen__RuntimeLayout_offset)(QString * structName, QString * member);
typedef QArray * quest_sig_questlang__codegen__RuntimeLayout_constants;
typedef QInt (*quest_sig_questlang__codegen__RuntimeLayout_constant)(QString * name);
typedef QArray * quest_sig_questlang__codegen__RuntimeLayout_realConstants;
typedef QArray * quest_sig_questlang__codegen__RuntimeLayout_addresses;
typedef QArray * quest_sig_questlang__codegen__RuntimeLayout_realBits;
typedef QArray * quest_sig_questlang__codegen__RuntimeLayout_variables;
#ifdef __cplusplus
}
#endif
#endif
