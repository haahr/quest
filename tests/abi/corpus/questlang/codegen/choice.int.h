#ifndef QUEST_INTF_QUESTLANG__CODEGEN__CHOICE_H
#define QUEST_INTF_QUESTLANG__CODEGEN__CHOICE_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_QArray_QTuple_String_String_end_TYPEDEF
#define QUEST_TYPE_QTuple_String_QArray_QTuple_String_String_end_TYPEDEF
typedef struct QTuple_String_QArray_QTuple_String_String_end QTuple_String_QArray_QTuple_String_String_end;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_DEFINED
struct QTuple_String_String {
    QString * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QArray_QTuple_String_String_end_DEFINED
#define QUEST_TYPE_QTuple_String_QArray_QTuple_String_String_end_DEFINED
struct QTuple_String_QArray_QTuple_String_String_end {
    QString * _0;
    QArray * _1;
};
#endif
typedef QTuple_String_String * quest_type_questlang__codegen__Choice_Override;
typedef QTuple_String_QArray_QTuple_String_String_end * quest_type_questlang__codegen__Choice_T;
typedef QArray * quest_sig_questlang__codegen__Choice_backends;
typedef QBool (*quest_sig_questlang__codegen__Choice_isBackend)(QString * name);
typedef QTuple_String_QArray_QTuple_String_String_end * quest_sig_questlang__codegen__Choice_standard;
typedef QString * quest_sig_questlang__codegen__Choice_programUnit;
typedef QString * (*quest_sig_questlang__codegen__Choice_forUnit)(QTuple_String_QArray_QTuple_String_String_end * c, QString * unit);
typedef QBool (*quest_sig_questlang__codegen__Choice_allC)(QTuple_String_QArray_QTuple_String_String_end * c);
typedef QVal (*quest_sig_questlang__codegen__Choice_parseOverride)(QString * s);
typedef QArray * (*quest_sig_questlang__codegen__Choice_arguments)(QTuple_String_QArray_QTuple_String_String_end * c);
typedef QBool (*quest_sig_questlang__codegen__Choice_isAssembly)(QString * backend);
typedef QString * (*quest_sig_questlang__codegen__Choice_codeFile)(QString * cFile, QString * backend);
#ifdef __cplusplus
}
#endif
#endif
