#ifndef QUEST_INTF_QUESTLANG__CODEGEN__SYMBOLS_H
#define QUEST_INTF_QUESTLANG__CODEGEN__SYMBOLS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QBool (*quest_sig_questlang__codegen__Symbols_isSymbolicName)(QString * name);
typedef QString * (*quest_sig_questlang__codegen__Symbols_mangleSymbolicIdent)(QString * name);
typedef QString * (*quest_sig_questlang__codegen__Symbols_mangleIdent)(QString * name);
typedef QString * (*quest_sig_questlang__codegen__Symbols_mangleModuleName)(QString * moduleName);
typedef QString * quest_sig_questlang__codegen__Symbols_moduleRecordPrefix;
typedef QString * (*quest_sig_questlang__codegen__Symbols_moduleRecordIdent)(QString * cleanMod);
typedef QString * (*quest_sig_questlang__codegen__Symbols_fingerprintIdent)(QString * cleanMod);
typedef QString * (*quest_sig_questlang__codegen__Symbols_mangleModuleIdent)(QString * moduleName, QString * name);
#ifdef __cplusplus
}
#endif
#endif
