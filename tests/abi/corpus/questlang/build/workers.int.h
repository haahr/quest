#ifndef QUEST_INTF_QUESTLANG__BUILD__WORKERS_H
#define QUEST_INTF_QUESTLANG__BUILD__WORKERS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/codegen/choice.int.h"
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_QArray_QTuple_String_String_end_TYPEDEF
#define QUEST_TYPE_QTuple_String_QArray_QTuple_String_String_end_TYPEDEF
typedef struct QTuple_String_QArray_QTuple_String_String_end QTuple_String_QArray_QTuple_String_String_end;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QAr_f515e4cd3bbb8fa0_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_QAr_f515e4cd3bbb8fa0_TYPEDEF
typedef struct QTuple_String_String_QAr_f515e4cd3bbb8fa0 QTuple_String_String_QAr_f515e4cd3bbb8fa0;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_QVal_TYPEDEF
typedef struct QTuple_String_String_QVal QTuple_String_String_QVal;
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
#ifndef QUEST_TYPE_QTuple_String_String_QAr_f515e4cd3bbb8fa0_DEFINED
#define QUEST_TYPE_QTuple_String_String_QAr_f515e4cd3bbb8fa0_DEFINED
struct QTuple_String_String_QAr_f515e4cd3bbb8fa0 {
    QString * _0;
    QString * _1;
    QArray * _2;
    QVal _3;
    QBoolSlot _4;
    QArray * _5;
    QVal _6;
    QVal _7;
    QTuple_String_QArray_QTuple_String_String_end * _8;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_String_QVal_DEFINED
struct QTuple_String_String_QVal {
    QString * _0;
    QString * _1;
    QVal _2;
};
#endif
typedef QTuple_String_String_QAr_f515e4cd3bbb8fa0 * quest_type_questlang__build__Workers_Job;
typedef QTuple_String_String_QVal * quest_type_questlang__build__Workers_Outcome;
typedef QArray * (*quest_sig_questlang__build__Workers_compileAll)(QArray * jobs, QInt n, QString * driver);
typedef void (*quest_sig_questlang__build__Workers_raiseFailure)(QTuple_String_String_QVal * o);
typedef QBool (*quest_sig_questlang__build__Workers_isUnitMode)(QArray * args);
typedef void (*quest_sig_questlang__build__Workers_unitMain)(QArray * args);
#ifdef __cplusplus
}
#endif
#endif
