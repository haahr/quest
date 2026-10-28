#ifndef QUEST_INTF_UTIL__STRINGBUILDER_H
#define QUEST_INTF_UTIL__STRINGBUILDER_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_util__StringBuilder_T;
typedef QVal (*quest_sig_util__StringBuilder_new)(void);
typedef QVal (*quest_sig_util__StringBuilder_newWithCapacity)(QInt capacity);
typedef void (*quest_sig_util__StringBuilder_append)(QVal b, QString * s);
typedef void (*quest_sig_util__StringBuilder_appendChar)(QVal b, QChar c);
typedef void (*quest_sig_util__StringBuilder_appendInt)(QVal b, QInt n);
typedef void (*quest_sig_util__StringBuilder_appendReal)(QVal b, QReal r);
typedef void (*quest_sig_util__StringBuilder_appendBool)(QVal b, QBool val);
typedef void (*quest_sig_util__StringBuilder_appendWord)(QVal b, uint64_t w);
typedef QInt (*quest_sig_util__StringBuilder_length)(QVal b);
typedef void (*quest_sig_util__StringBuilder_clear)(QVal b);
typedef QString * (*quest_sig_util__StringBuilder_toString)(QVal b);
#ifdef __cplusplus
}
#endif
#endif
