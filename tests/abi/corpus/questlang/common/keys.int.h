#ifndef QUEST_INTF_QUESTLANG__COMMON__KEYS_H
#define QUEST_INTF_QUESTLANG__COMMON__KEYS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
typedef QVal quest_type_questlang__common__Keys_T;
typedef QVal (*quest_sig_questlang__common__Keys_new)(void);
typedef void (*quest_sig_questlang__common__Keys_start)(QVal k);
typedef void (*quest_sig_questlang__common__Keys_int)(QVal k, QInt n);
typedef void (*quest_sig_questlang__common__Keys_bool)(QVal k, QBool v);
typedef void (*quest_sig_questlang__common__Keys_str)(QVal k, QString * s);
typedef QVal (*quest_sig_questlang__common__Keys_find)(QVal k);
typedef QInt (*quest_sig_questlang__common__Keys_intern)(QVal k);
typedef QInt (*quest_sig_questlang__common__Keys_size)(QVal k);
#ifdef __cplusplus
}
#endif
#endif
