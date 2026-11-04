#ifndef QUEST_INTF_QUESTLANG__CODEGEN__C__COMPILERRUNNER_H
#define QUEST_INTF_QUESTLANG__CODEGEN__C__COMPILERRUNNER_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QTuple_Int_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_String_TYPEDEF
typedef struct QTuple_Int_String_String QTuple_Int_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_String_DEFINED
#define QUEST_TYPE_QTuple_Int_String_String_DEFINED
struct QTuple_Int_String_String {
    QInt _0;
    QString * _1;
    QString * _2;
};
static_assert(offsetof(struct QTuple_Int_String_String, _0) == 0, layout_QTuple_Int_String_String__0);
static_assert(offsetof(struct QTuple_Int_String_String, _1) == 8, layout_QTuple_Int_String_String__1);
static_assert(offsetof(struct QTuple_Int_String_String, _2) == 16, layout_QTuple_Int_String_String__2);
static_assert(sizeof(struct QTuple_Int_String_String) == 24, layout_QTuple_Int_String_String_size);
#endif
typedef const QException * quest_sig_questlang__codegen__c__CompilerRunner_failure;
typedef QString * (*quest_sig_questlang__codegen__c__CompilerRunner_findCCompiler)(void);
typedef QString * (*quest_sig_questlang__codegen__c__CompilerRunner_runtimeDir)(void);
typedef QArray * (*quest_sig_questlang__codegen__c__CompilerRunner_baseCFlags)(QString * compiler);
typedef QArray * (*quest_sig_questlang__codegen__c__CompilerRunner_gcFlags)(QBool nogc);
typedef QArray * (*quest_sig_questlang__codegen__c__CompilerRunner_readlineFlags)(void);
typedef void (*quest_sig_questlang__codegen__c__CompilerRunner_compileCToObject)(QString * c, QString * o, QArray * includePaths, QBool nogc, QVal compiler, QArray * extraFlags);
typedef QArray * (*quest_sig_questlang__codegen__c__CompilerRunner_runtimeObjects)(QString * compiler, QBool nogc, QArray * extraFlags);
typedef void (*quest_sig_questlang__codegen__c__CompilerRunner_compileCSource)(QString * source, QString * output, QBool nogc, QVal compiler, QArray * extraObjects, QArray * extraFlags, QBool assembly);
typedef void (*quest_sig_questlang__codegen__c__CompilerRunner_linkObjects)(QArray * objects, QString * output, QBool nogc, QVal compiler, QArray * extraFlags);
typedef QString * (*quest_sig_questlang__codegen__c__CompilerRunner_temporaryBinary)(void);
typedef QTuple_Int_String_String * (*quest_sig_questlang__codegen__c__CompilerRunner_runBinary)(QString * binary, QArray * args);
#ifdef __cplusplus
}
#endif
#endif
