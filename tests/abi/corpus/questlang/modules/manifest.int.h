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
