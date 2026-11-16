#ifndef QUEST_INTF_UTIL__STRINGBUILDER_H
#define QUEST_INTF_UTIL__STRINGBUILDER_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_util__StringBuilder_T;
typedef QVal (*quest_sig_util__StringBuilder_new)(void);
typedef void (*quest_sig_util__StringBuilder_str)(QVal b, QString * s);
typedef void (*quest_sig_util__StringBuilder_strShared)(QVal b, QString * s);
typedef void (*quest_sig_util__StringBuilder_char)(QVal b, QChar c);
typedef void (*quest_sig_util__StringBuilder_int)(QVal b, QInt n);
typedef void (*quest_sig_util__StringBuilder_real)(QVal b, QReal r);
typedef void (*quest_sig_util__StringBuilder_bool)(QVal b, QBool v);
typedef void (*quest_sig_util__StringBuilder_word)(QVal b, uint64_t w);
typedef void (*quest_sig_util__StringBuilder_sub)(QVal b, QString * s, QInt start, QInt size);
typedef void (*quest_sig_util__StringBuilder_repeat)(QVal b, QChar c, QInt n);
typedef void (*quest_sig_util__StringBuilder_clear)(QVal b);
typedef QInt (*quest_sig_util__StringBuilder_length)(QVal b);
typedef QString * (*quest_sig_util__StringBuilder_toString)(QVal b);
#ifdef __cplusplus
}
#endif
#endif
