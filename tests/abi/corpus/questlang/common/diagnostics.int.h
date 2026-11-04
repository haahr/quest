#ifndef QUEST_INTF_QUESTLANG__COMMON__DIAGNOSTICS_H
#define QUEST_INTF_QUESTLANG__COMMON__DIAGNOSTICS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/common/location.int.h"
#include "collections/vector.int.h"
#include "util/maybe.int.h"
#include "writer.int.h"
#ifndef QUEST_TYPE_QOption_error_fatal_info_warning_TYPEDEF
#define QUEST_TYPE_QOption_error_fatal_info_warning_TYPEDEF
typedef struct QOption_error_fatal_info_warning QOption_error_fatal_info_warning;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_String_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_String_Bool_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_end_String_Bool QTuple_QTuple_String_Int_Int_end_String_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal_TYPEDEF
typedef struct QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal;
#endif
#ifndef QUEST_TYPE_QOption_error_fatal_info_warning_DEFINED
#define QUEST_TYPE_QOption_error_fatal_info_warning_DEFINED
struct QOption_error_fatal_info_warning {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_String_Bool_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_end_String_Bool_DEFINED
struct QTuple_QTuple_String_Int_Int_end_String_Bool {
    QTuple_String_Int_Int * _0;
    QString * _1;
    QBoolSlot _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal_DEFINED
struct QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal {
    QString * _0;
    QInt _1;
    QInt _2;
    QBoolSlot _3;
    QVal _4;
    QVal _5;
    QVal _6;
    QBoolSlot _7;
    QVal _8;
};
#endif
typedef QOption_error_fatal_info_warning * quest_type_questlang__common__Diagnostics_Severity;
typedef QTuple_QTuple_String_Int_Int_end_String_Bool * quest_type_questlang__common__Diagnostics_Label;
typedef QVal quest_type_questlang__common__Diagnostics_Diagnostic;
typedef QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal * quest_type_questlang__common__Diagnostics_CompilerError;
typedef QVal (*quest_sig_questlang__common__Diagnostics_make)(QOption_error_fatal_info_warning * sev, QString * msg, QTuple_String_Int_Int * sp);
typedef QVal (*quest_sig_questlang__common__Diagnostics_fatal)(QString * msg, QTuple_String_Int_Int * sp);
typedef QVal (*quest_sig_questlang__common__Diagnostics_error)(QString * msg, QTuple_String_Int_Int * sp);
typedef QVal (*quest_sig_questlang__common__Diagnostics_warning)(QString * msg, QTuple_String_Int_Int * sp);
typedef QVal (*quest_sig_questlang__common__Diagnostics_info)(QString * msg, QTuple_String_Int_Int * sp);
typedef QOption_error_fatal_info_warning * (*quest_sig_questlang__common__Diagnostics_severity)(QVal d);
typedef QString * (*quest_sig_questlang__common__Diagnostics_message)(QVal d);
typedef QTuple_String_Int_Int * (*quest_sig_questlang__common__Diagnostics_span)(QVal d);
typedef QVal (*quest_sig_questlang__common__Diagnostics_labels)(QVal d);
typedef QVal (*quest_sig_questlang__common__Diagnostics_notes)(QVal d);
typedef QVal (*quest_sig_questlang__common__Diagnostics_help)(QVal d);
typedef QVal (*quest_sig_questlang__common__Diagnostics_code)(QVal d);
typedef void (*quest_sig_questlang__common__Diagnostics_addLabel)(QVal d, QTuple_String_Int_Int * sp, QString * msg, QBool isPrimary);
typedef void (*quest_sig_questlang__common__Diagnostics_addNote)(QVal d, QString * note);
typedef void (*quest_sig_questlang__common__Diagnostics_setHelp)(QVal d, QString * h);
typedef void (*quest_sig_questlang__common__Diagnostics_setCode)(QVal d, QString * c);
typedef void (*quest_sig_questlang__common__Diagnostics_setTrace)(QVal d, QArray * frames);
typedef QString * (*quest_sig_questlang__common__Diagnostics_severityString)(QOption_error_fatal_info_warning * sev);
typedef void (*quest_sig_questlang__common__Diagnostics_registerSource)(QVal sm);
typedef QString * (*quest_sig_questlang__common__Diagnostics_format)(QVal d, QVal sm);
typedef void (*quest_sig_questlang__common__Diagnostics_render)(QVal d, QVal sm, QWriter * w);
typedef const QException * quest_sig_questlang__common__Diagnostics_compilerError;
typedef QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal * (*quest_sig_questlang__common__Diagnostics_errorAt)(QString * message, QInt offset);
typedef QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal * quest_sig_questlang__common__Diagnostics_silentError;
typedef QVal (*quest_sig_questlang__common__Diagnostics_raiseError)(const QTypeDescriptor *desc_A, QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal * e);
typedef QVal (*quest_sig_questlang__common__Diagnostics_fail)(const QTypeDescriptor *desc_A, QString * message, QInt offset);
typedef QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal * (*quest_sig_questlang__common__Diagnostics_inFile)(QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal * e, QString * file);
typedef QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal * (*quest_sig_questlang__common__Diagnostics_atImport)(QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal * e, QInt offset, QInt length, QString * file);
typedef QVal (*quest_sig_questlang__common__Diagnostics_errorDiagnostic)(QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal * e, QString * file);
typedef QVal (*quest_sig_questlang__common__Diagnostics_warningDiagnostic)(QTuple_String_Int_Int_Bool_QVal_QVal_QVal_Bool_QVal * e, QString * file);
typedef QString * quest_sig_questlang__common__Diagnostics_mainFrame;
typedef QString * (*quest_sig_questlang__common__Diagnostics_initFrame)(QString * moduleName);
typedef QString * (*quest_sig_questlang__common__Diagnostics_frameName)(QString * enclosing, QVal binder);
typedef QString * (*quest_sig_questlang__common__Diagnostics_pyRepr)(QString * s);
#ifdef __cplusplus
}
#endif
#endif
