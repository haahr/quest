#ifndef QUEST_INTF_SYSTEM_H
#define QUEST_INTF_SYSTEM_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef const QException * quest_sig_System_error;
typedef QArray * quest_sig_System_args;
typedef void (*quest_sig_System_sysexit)(QInt code);
typedef QString * (*quest_sig_System_getEnv)(QString * name);
typedef QBool (*quest_sig_System_fileExists)(QString * path);
typedef QBool (*quest_sig_System_isFile)(QString * path);
typedef QBool (*quest_sig_System_isDirectory)(QString * path);
typedef void (*quest_sig_System_makeDirectory)(QString * path);
typedef void (*quest_sig_System_removeFile)(QString * path);
typedef void (*quest_sig_System_removeDirectory)(QString * path);
typedef void (*quest_sig_System_renameFile)(QString * oldPath, QString * newPath);
typedef QString * (*quest_sig_System_currentDirectory)(void);
typedef void (*quest_sig_System_changeDirectory)(QString * path);
typedef QArray * (*quest_sig_System_listDirectory)(QString * path);
#ifdef __cplusplus
}
#endif
#endif
