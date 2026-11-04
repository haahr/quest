#ifndef QUEST_INTF_QUESTLANG__BUILD__LOGGER_H
#define QUEST_INTF_QUESTLANG__BUILD__LOGGER_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QTuple_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_Bool_TYPEDEF
typedef struct QTuple_QVal_Bool QTuple_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QVal_Bool_DEFINED
struct QTuple_QVal_Bool {
    QVal _0;
    QBoolSlot _1;
};
#endif
typedef QTuple_QVal_Bool * quest_type_questlang__build__Logger_T;
typedef QTuple_QVal_Bool * (*quest_sig_questlang__build__Logger_new)(QVal logFile, QBool verbose);
typedef void (*quest_sig_questlang__build__Logger_log)(QTuple_QVal_Bool * l, QString * tag, QString * message);
typedef void (*quest_sig_questlang__build__Logger_flush)(QTuple_QVal_Bool * l);
#ifdef __cplusplus
}
#endif
#endif
