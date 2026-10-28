#ifndef QUEST_INTF_OS__PROCESS_H
#define QUEST_INTF_OS__PROCESS_H
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
#endif
typedef QVal quest_type_os__Process_T;
typedef QTuple_Int_String_String * quest_type_os__Process_Result;
typedef QVal (*quest_sig_os__Process_spawn)(QArray * args);
typedef QVal (*quest_sig_os__Process_spawnIn)(QArray * args, QString * dir);
typedef QInt (*quest_sig_os__Process_pid)(QVal p);
typedef QBool (*quest_sig_os__Process_isDone)(QVal p);
typedef QTuple_Int_String_String * (*quest_sig_os__Process_wait)(QVal p);
typedef QInt (*quest_sig_os__Process_waitAny)(QArray * ps);
typedef void (*quest_sig_os__Process_kill)(QVal p, QInt sig);
#ifdef __cplusplus
}
#endif
#endif
