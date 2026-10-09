#ifndef QUEST_INTF_UTIL__HASH_H
#define QUEST_INTF_UTIL__HASH_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QBool (*quest_sig_util__Hash_identityEqual)(const QTypeDescriptor *desc_A, QVal x1, QVal x2);
typedef uint64_t (*quest_sig_util__Hash_identityHash)(const QTypeDescriptor *desc_A, QVal x);
typedef uint64_t (*quest_sig_util__Hash_mix)(uint64_t w);
typedef uint64_t (*quest_sig_util__Hash_combine)(uint64_t h1, uint64_t h2);
typedef uint64_t (*quest_sig_util__Hash_int)(QInt n);
typedef uint64_t (*quest_sig_util__Hash_bool)(QBool b);
typedef uint64_t (*quest_sig_util__Hash_char)(QChar c);
typedef uint64_t (*quest_sig_util__Hash_word)(uint64_t w);
typedef uint64_t (*quest_sig_util__Hash_string)(QString * s);
#ifdef __cplusplus
}
#endif
#endif
