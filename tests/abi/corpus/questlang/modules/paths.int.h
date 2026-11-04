#ifndef QUEST_INTF_QUESTLANG__MODULES__PATHS_H
#define QUEST_INTF_QUESTLANG__MODULES__PATHS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QTuple_String_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_String_TYPEDEF
typedef struct QTuple_String_String_String QTuple_String_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_String_DEFINED
struct QTuple_String_String_String {
    QString * _0;
    QString * _1;
    QString * _2;
};
#endif
typedef QTuple_String_String_String * quest_type_questlang__modules__Paths_InterfaceDependency;
typedef QString * (*quest_sig_questlang__modules__Paths_lower)(QString * s);
typedef QString * (*quest_sig_questlang__modules__Paths_join)(QString * a, QString * b);
typedef QString * (*quest_sig_questlang__modules__Paths_normalize)(QString * p);
typedef QString * (*quest_sig_questlang__modules__Paths_absolute)(QString * p);
typedef QString * (*quest_sig_questlang__modules__Paths_parent)(QString * p);
typedef QString * (*quest_sig_questlang__modules__Paths_baseName)(QString * p);
typedef QArray * (*quest_sig_questlang__modules__Paths_parts)(QString * p);
typedef QVal (*quest_sig_questlang__modules__Paths_relativeTo)(QString * p, QString * root);
typedef QString * (*quest_sig_questlang__modules__Paths_displayName)(QString * p);
typedef QVal (*quest_sig_questlang__modules__Paths_readText)(QString * file);
typedef QVal (*quest_sig_questlang__modules__Paths_fileTime)(QString * file);
typedef QInt (*quest_sig_questlang__modules__Paths_modifiedNs)(QString * p);
typedef QBool (*quest_sig_questlang__modules__Paths_isFile)(QString * p);
typedef void (*quest_sig_questlang__modules__Paths_writeAtomically)(QString * file, QString * text);
typedef void (*quest_sig_questlang__modules__Paths_setWorkerTag)(QString * tag);
typedef QString * (*quest_sig_questlang__modules__Paths_projectDir)(void);
typedef QString * (*quest_sig_questlang__modules__Paths_libDir)(void);
typedef QVal (*quest_sig_questlang__modules__Paths_libModulePath)(QString * source);
typedef QString * (*quest_sig_questlang__modules__Paths_stripUnitSuffix)(QString * filename);
typedef QString * (*quest_sig_questlang__modules__Paths_declaredModuleName)(QVal file, QString * canonName);
typedef QVal (*quest_sig_questlang__modules__Paths_resolveInterfaceSourceFile)(QString * name, QVal currentDir, QArray * includePaths);
typedef QVal (*quest_sig_questlang__modules__Paths_resolveModuleFile)(QString * name, QVal currentDir, QArray * includePaths);
typedef QVal (*quest_sig_questlang__modules__Paths_resolveObjectFile)(QString * name, QVal currentDir, QArray * includePaths);
typedef QVal (*quest_sig_questlang__modules__Paths_resolveInterfaceFile)(QString * name, QVal currentDir, QArray * includePaths);
typedef QBool (*quest_sig_questlang__modules__Paths_sameSource)(QVal found, QString * recorded);
typedef QVal (*quest_sig_questlang__modules__Paths_recordedDependencies)(QString * qi);
typedef QVal (*quest_sig_questlang__modules__Paths_dependencyChange)(QArray * deps, QArray * includePaths, QInt artifactTime, QClosure * resolveSource);
typedef QArray * (*quest_sig_questlang__modules__Paths_searchedDirs)(QVal currentDir, QArray * includePaths);
typedef QArray * (*quest_sig_questlang__modules__Paths_canonicalRoots)(QArray * includePaths, QVal programDir);
typedef QString * (*quest_sig_questlang__modules__Paths_canonicalizeModulePath)(QString * file, QArray * includePaths, QVal programDir);
typedef QVal (*quest_sig_questlang__modules__Paths_findCanonicalModuleSource)(QString * canonName, QArray * includePaths, QVal programDir);
typedef QString * (*quest_sig_questlang__modules__Paths_canonicalizeInterfaceName)(QVal file, QArray * includePaths, QString * declaredName, QVal programDir);
typedef QString * (*quest_sig_questlang__modules__Paths_canonicalizeModuleName)(QVal file, QArray * includePaths, QString * rawName, QVal programDir);
#ifdef __cplusplus
}
#endif
#endif
