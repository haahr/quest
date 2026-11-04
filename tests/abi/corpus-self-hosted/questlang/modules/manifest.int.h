#ifndef QUEST_INTF_QUESTLANG__MODULES__MANIFEST_H
#define QUEST_INTF_QUESTLANG__MODULES__MANIFEST_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QTuple_String_String_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_String_String_TYPEDEF
typedef struct QTuple_String_String_String_String QTuple_String_String_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_Real_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_Real_String_String_TYPEDEF
typedef struct QTuple_String_String_Real_String_String QTuple_String_String_Real_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_Strin_d15918df7db23a96_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_Strin_d15918df7db23a96_TYPEDEF
typedef struct QTuple_String_QVal_Strin_d15918df7db23a96 QTuple_String_QVal_Strin_d15918df7db23a96;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_String_String_DEFINED
struct QTuple_String_String_String_String {
    QString * _0;
    QString * _1;
    QString * _2;
    QString * _3;
};
static_assert(offsetof(struct QTuple_String_String_String_String, _0) == 0, layout_QTuple_String_String_String_String__0);
static_assert(offsetof(struct QTuple_String_String_String_String, _1) == 8, layout_QTuple_String_String_String_String__1);
static_assert(offsetof(struct QTuple_String_String_String_String, _2) == 16, layout_QTuple_String_String_String_String__2);
static_assert(offsetof(struct QTuple_String_String_String_String, _3) == 24, layout_QTuple_String_String_String_String__3);
static_assert(sizeof(struct QTuple_String_String_String_String) == 32, layout_QTuple_String_String_String_String_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_String_Real_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_Real_String_String_DEFINED
struct QTuple_String_String_Real_String_String {
    QString * _0;
    QString * _1;
    QReal _2;
    QString * _3;
    QString * _4;
};
static_assert(offsetof(struct QTuple_String_String_Real_String_String, _0) == 0, layout_QTuple_String_String_Real_String_String__0);
static_assert(offsetof(struct QTuple_String_String_Real_String_String, _1) == 8, layout_QTuple_String_String_Real_String_String__1);
static_assert(offsetof(struct QTuple_String_String_Real_String_String, _2) == 16, layout_QTuple_String_String_Real_String_String__2);
static_assert(offsetof(struct QTuple_String_String_Real_String_String, _3) == 24, layout_QTuple_String_String_Real_String_String__3);
static_assert(offsetof(struct QTuple_String_String_Real_String_String, _4) == 32, layout_QTuple_String_String_Real_String_String__4);
static_assert(sizeof(struct QTuple_String_String_Real_String_String) == 40, layout_QTuple_String_String_Real_String_String_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_Strin_d15918df7db23a96_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_Strin_d15918df7db23a96_DEFINED
struct QTuple_String_QVal_Strin_d15918df7db23a96 {
    QString * _0;
    QVal _1;
    QString * _2;
    QString * _3;
    QArray * _4;
    QArray * _5;
    QVal _6;
    QVal _7;
    QString * _8;
};
static_assert(offsetof(struct QTuple_String_QVal_Strin_d15918df7db23a96, _0) == 0, layout_QTuple_String_QVal_Strin_d15918df7db23a96__0);
static_assert(offsetof(struct QTuple_String_QVal_Strin_d15918df7db23a96, _1) == 8, layout_QTuple_String_QVal_Strin_d15918df7db23a96__1);
static_assert(offsetof(struct QTuple_String_QVal_Strin_d15918df7db23a96, _2) == 16, layout_QTuple_String_QVal_Strin_d15918df7db23a96__2);
static_assert(offsetof(struct QTuple_String_QVal_Strin_d15918df7db23a96, _3) == 24, layout_QTuple_String_QVal_Strin_d15918df7db23a96__3);
static_assert(offsetof(struct QTuple_String_QVal_Strin_d15918df7db23a96, _4) == 32, layout_QTuple_String_QVal_Strin_d15918df7db23a96__4);
static_assert(offsetof(struct QTuple_String_QVal_Strin_d15918df7db23a96, _5) == 40, layout_QTuple_String_QVal_Strin_d15918df7db23a96__5);
static_assert(offsetof(struct QTuple_String_QVal_Strin_d15918df7db23a96, _6) == 48, layout_QTuple_String_QVal_Strin_d15918df7db23a96__6);
static_assert(offsetof(struct QTuple_String_QVal_Strin_d15918df7db23a96, _7) == 56, layout_QTuple_String_QVal_Strin_d15918df7db23a96__7);
static_assert(offsetof(struct QTuple_String_QVal_Strin_d15918df7db23a96, _8) == 64, layout_QTuple_String_QVal_Strin_d15918df7db23a96__8);
static_assert(sizeof(struct QTuple_String_QVal_Strin_d15918df7db23a96) == 72, layout_QTuple_String_QVal_Strin_d15918df7db23a96_size);
#endif
typedef QTuple_String_String_String_String * quest_type_questlang__modules__Manifest_ImportedModuleRef;
typedef QTuple_String_String_Real_String_String * quest_type_questlang__modules__Manifest_ImportedInterfaceRef;
typedef QTuple_String_QVal_Strin_d15918df7db23a96 * quest_type_questlang__modules__Manifest_ModuleManifest;
typedef QTuple_String_QVal_Strin_d15918df7db23a96 * (*quest_sig_questlang__modules__Manifest_newManifest)(QString * name, QVal interfaceName, QString * source, QString * object, QArray * importedModules, QArray * importedInterfaces, QString * backend);
typedef void (*quest_sig_questlang__modules__Manifest_writeQm)(QTuple_String_QVal_Strin_d15918df7db23a96 * m, QString * file);
typedef QVal (*quest_sig_questlang__modules__Manifest_readQm)(QString * file);
typedef QBool (*quest_sig_questlang__modules__Manifest_isManifestStale)(QTuple_String_QVal_Strin_d15918df7db23a96 * m, QString * qm);
typedef QVal (*quest_sig_questlang__modules__Manifest_unitStaleness)(QString * source, QString * qm, QString * c, QString * o, QVal importsChanged);
#ifdef __cplusplus
}
#endif
#endif
