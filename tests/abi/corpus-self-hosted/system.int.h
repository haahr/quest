#ifndef QUEST_INTF_SYSTEM_H
#define QUEST_INTF_SYSTEM_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
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
typedef QTuple_Int_String_String * (*quest_sig_System_run)(QArray * args);
typedef QBool (*quest_sig_System_isTerminal)(QInt fd);
#ifdef __cplusplus
}
#endif
#endif
