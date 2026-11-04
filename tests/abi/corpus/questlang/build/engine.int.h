#ifndef QUEST_INTF_QUESTLANG__BUILD__ENGINE_H
#define QUEST_INTF_QUESTLANG__BUILD__ENGINE_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/codegen/choice.int.h"
#include "questlang/modules/graph.int.h"
#include "questlang/modules/manifest.int.h"
#include "questlang/build/logger.int.h"
#include "questlang/codegen/backend.int.h"
#include "util/maybe.int.h"
#include "util/path.int.h"
#ifndef QUEST_TYPE_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_TYPEDEF
typedef struct QTuple_QVal QTuple_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_Bool_TYPEDEF
typedef struct QTuple_QVal_Bool QTuple_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_QArray_QTuple_String_String_end_TYPEDEF
#define QUEST_TYPE_QTuple_String_QArray_QTuple_String_String_end_TYPEDEF
typedef struct QTuple_String_QArray_QTuple_String_String_end QTuple_String_QArray_QTuple_String_String_end;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc_TYPEDEF
typedef struct QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc;
#endif
#ifndef QUEST_TYPE_QOption_interfaceUnit_moduleUnit_programUnit_TYPEDEF
#define QUEST_TYPE_QOption_interfaceUnit_moduleUnit_programUnit_TYPEDEF
typedef struct QOption_interfaceUnit_moduleUnit_programUnit QOption_interfaceUnit_moduleUnit_programUnit;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_String_QVal_String_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_String_QVal_String_TYPEDEF
typedef struct QTuple_QArray_String_QVal_String QTuple_QArray_String_QVal_String;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_interface_d389162375b8ce53_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_interface_d389162375b8ce53_TYPEDEF
typedef struct QTuple_QOption_interface_d389162375b8ce53 QTuple_QOption_interface_d389162375b8ce53;
#endif
#ifndef QUEST_TYPE_QTuple_String_QArray_String_QArray_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_QArray_String_QArray_String_TYPEDEF
typedef struct QTuple_String_QArray_String_QArray_String QTuple_String_QArray_String_QArray_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_String_String_TYPEDEF
typedef struct QTuple_String_String_String_String QTuple_String_String_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_DEFINED
struct QTuple_QVal {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QVal_Bool_DEFINED
struct QTuple_QVal_Bool {
    QVal _0;
    QBoolSlot _1;
};
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
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc_DEFINED
struct QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc {
    QVal _0;
    QTuple_QVal * _1;
    QArray * _2;
    QArray * _3;
    QTuple_QVal_Bool * _4;
    QBoolSlot _5;
    QVal _6;
    QArray * _7;
    QInt _8;
    QString * _9;
    QTuple_String_QArray_QTuple_String_String_end * _10;
};
#endif
#ifndef QUEST_TYPE_QOption_interfaceUnit_moduleUnit_programUnit_DEFINED
#define QUEST_TYPE_QOption_interfaceUnit_moduleUnit_programUnit_DEFINED
struct QOption_interfaceUnit_moduleUnit_programUnit {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_QArray_String_QVal_String_DEFINED
#define QUEST_TYPE_QTuple_QArray_String_QVal_String_DEFINED
struct QTuple_QArray_String_QVal_String {
    QArray * _0;
    QVal _1;
    QString * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QOption_interface_d389162375b8ce53_DEFINED
#define QUEST_TYPE_QTuple_QOption_interface_d389162375b8ce53_DEFINED
struct QTuple_QOption_interface_d389162375b8ce53 {
    QOption_interfaceUnit_moduleUnit_programUnit * _0;
    QString * _1;
    QVal _2;
    QTuple_QArray_String_QVal_String * _3;
    QVal _4;
    QVal _5;
    QVal _6;
    QVal _7;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QArray_String_QArray_String_DEFINED
#define QUEST_TYPE_QTuple_String_QArray_String_QArray_String_DEFINED
struct QTuple_String_QArray_String_QArray_String {
    QString * _0;
    QArray * _1;
    QArray * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_String_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_String_String_DEFINED
struct QTuple_String_String_String_String {
    QString * _0;
    QString * _1;
    QString * _2;
    QString * _3;
};
#endif
typedef QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc * quest_type_questlang__build__Engine_T;
typedef QTuple_String_QArray_String_QArray_String * quest_type_questlang__build__Engine_ImportRef;
typedef const QException * quest_sig_questlang__build__Engine_buildError;
typedef QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc * (*quest_sig_questlang__build__Engine_new)(QVal buildDir, QArray * includePaths, QBool verbose, QBool nogc, QArray * extraObjects, QVal resolver);
typedef QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc * (*quest_sig_questlang__build__Engine_parallel)(QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc * eng, QInt jobs, QString * driver);
typedef QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc * (*quest_sig_questlang__build__Engine_withBackends)(QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc * eng, QTuple_String_QArray_QTuple_String_String_end * backends);
typedef QArray * (*quest_sig_questlang__build__Engine_unitModuleRefs)(QArray * imports, QArray * implicit, QVal currentDir, QArray * includePaths, QVal programDir, QTuple_QVal * res);
typedef QArray * (*quest_sig_questlang__build__Engine_buildModules)(QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc * eng, QArray * roots, QString * importer, QVal programDir);
typedef void (*quest_sig_questlang__build__Engine_buildMain)(QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc * eng, QString * mainFile, QVal output);
typedef void (*quest_sig_questlang__build__Engine_compileMain)(QTuple_QVal_QTuple_QVal__4934f82fbd4d4edc * eng, QString * mainFile);
#ifdef __cplusplus
}
#endif
#endif
