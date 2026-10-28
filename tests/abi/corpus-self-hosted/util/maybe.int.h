#ifndef QUEST_INTF_UTIL__MAYBE_H
#define QUEST_INTF_UTIL__MAYBE_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_util__Maybe_T;
typedef const QException * quest_sig_util__Maybe_error;
typedef QBool (*quest_sig_util__Maybe_isSome)(const QTypeDescriptor *desc_A, QVal o);
typedef QBool (*quest_sig_util__Maybe_isNone)(const QTypeDescriptor *desc_A, QVal o);
typedef QVal (*quest_sig_util__Maybe_unwrap)(const QTypeDescriptor *desc_A, QVal o);
typedef QVal (*quest_sig_util__Maybe_unwrapOr)(const QTypeDescriptor *desc_A, QVal o, QVal q_default);
typedef QVal (*quest_sig_util__Maybe_some)(const QTypeDescriptor *desc_A, QVal val);
typedef QVal (*quest_sig_util__Maybe_none)(const QTypeDescriptor *desc_A);
#ifdef __cplusplus
}
#endif
#endif
