#ifndef QUEST_INTF_STRINGBUILDER_H
#define QUEST_INTF_STRINGBUILDER_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_StringBuilder_T;
typedef QVal (*quest_sig_StringBuilder_new)(void);
typedef QVal (*quest_sig_StringBuilder_newWithCapacity)(QInt capacity);
typedef void (*quest_sig_StringBuilder_append)(QVal b, QString * s);
typedef void (*quest_sig_StringBuilder_appendChar)(QVal b, QChar c);
typedef void (*quest_sig_StringBuilder_appendInt)(QVal b, QInt n);
typedef void (*quest_sig_StringBuilder_appendReal)(QVal b, QReal r);
typedef void (*quest_sig_StringBuilder_appendBool)(QVal b, QBool val);
typedef void (*quest_sig_StringBuilder_appendWord)(QVal b, uint64_t w);
typedef QInt (*quest_sig_StringBuilder_length)(QVal b);
typedef void (*quest_sig_StringBuilder_clear)(QVal b);
typedef QString * (*quest_sig_StringBuilder_toString)(QVal b);
#ifdef __cplusplus
}
#endif
#endif
