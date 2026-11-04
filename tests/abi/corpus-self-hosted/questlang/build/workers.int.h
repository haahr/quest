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
static_assert(offsetof(struct QTuple_String_String, _0) == 0, layout_QTuple_String_String__0);
static_assert(offsetof(struct QTuple_String_String, _1) == 8, layout_QTuple_String_String__1);
static_assert(sizeof(struct QTuple_String_String) == 16, layout_QTuple_String_String_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_QArray_QTuple_String_String_end_DEFINED
#define QUEST_TYPE_QTuple_String_QArray_QTuple_String_String_end_DEFINED
struct QTuple_String_QArray_QTuple_String_String_end {
    QString * _0;
    QArray * _1;
};
static_assert(offsetof(struct QTuple_String_QArray_QTuple_String_String_end, _0) == 0, layout_QTuple_String_QArray_QTuple_String_String_end__0);
static_assert(offsetof(struct QTuple_String_QArray_QTuple_String_String_end, _1) == 8, layout_QTuple_String_QArray_QTuple_String_String_end__1);
static_assert(sizeof(struct QTuple_String_QArray_QTuple_String_String_end) == 16, layout_QTuple_String_QArray_QTuple_String_String_end_size);
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
static_assert(offsetof(struct QTuple_String_String_QAr_f515e4cd3bbb8fa0, _0) == 0, layout_QTuple_String_String_QAr_f515e4cd3bbb8fa0__0);
static_assert(offsetof(struct QTuple_String_String_QAr_f515e4cd3bbb8fa0, _1) == 8, layout_QTuple_String_String_QAr_f515e4cd3bbb8fa0__1);
static_assert(offsetof(struct QTuple_String_String_QAr_f515e4cd3bbb8fa0, _2) == 16, layout_QTuple_String_String_QAr_f515e4cd3bbb8fa0__2);
static_assert(offsetof(struct QTuple_String_String_QAr_f515e4cd3bbb8fa0, _3) == 24, layout_QTuple_String_String_QAr_f515e4cd3bbb8fa0__3);
static_assert(offsetof(struct QTuple_String_String_QAr_f515e4cd3bbb8fa0, _4) == 32, layout_QTuple_String_String_QAr_f515e4cd3bbb8fa0__4);
static_assert(offsetof(struct QTuple_String_String_QAr_f515e4cd3bbb8fa0, _5) == 40, layout_QTuple_String_String_QAr_f515e4cd3bbb8fa0__5);
static_assert(offsetof(struct QTuple_String_String_QAr_f515e4cd3bbb8fa0, _6) == 48, layout_QTuple_String_String_QAr_f515e4cd3bbb8fa0__6);
static_assert(offsetof(struct QTuple_String_String_QAr_f515e4cd3bbb8fa0, _7) == 56, layout_QTuple_String_String_QAr_f515e4cd3bbb8fa0__7);
static_assert(offsetof(struct QTuple_String_String_QAr_f515e4cd3bbb8fa0, _8) == 64, layout_QTuple_String_String_QAr_f515e4cd3bbb8fa0__8);
static_assert(sizeof(struct QTuple_String_String_QAr_f515e4cd3bbb8fa0) == 72, layout_QTuple_String_String_QAr_f515e4cd3bbb8fa0_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_String_QVal_DEFINED
struct QTuple_String_String_QVal {
    QString * _0;
    QString * _1;
    QVal _2;
};
static_assert(offsetof(struct QTuple_String_String_QVal, _0) == 0, layout_QTuple_String_String_QVal__0);
static_assert(offsetof(struct QTuple_String_String_QVal, _1) == 8, layout_QTuple_String_String_QVal__1);
static_assert(offsetof(struct QTuple_String_String_QVal, _2) == 16, layout_QTuple_String_String_QVal__2);
static_assert(sizeof(struct QTuple_String_String_QVal) == 24, layout_QTuple_String_String_QVal_size);
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
