#ifndef QUEST_INTF_MAYBE_H
#define QUEST_INTF_MAYBE_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_Maybe_T;
typedef const QException * quest_sig_Maybe_error;
typedef QBool (*quest_sig_Maybe_isSome)(const QTypeDescriptor *desc_A, QVal o);
typedef QBool (*quest_sig_Maybe_isNone)(const QTypeDescriptor *desc_A, QVal o);
typedef QVal (*quest_sig_Maybe_unwrap)(const QTypeDescriptor *desc_A, QVal o);
typedef QVal (*quest_sig_Maybe_unwrapOr)(const QTypeDescriptor *desc_A, QVal o, QVal q_default);
typedef QVal (*quest_sig_Maybe_some)(const QTypeDescriptor *desc_A, QVal val);
typedef QVal (*quest_sig_Maybe_none)(const QTypeDescriptor *desc_A);
#ifdef __cplusplus
}
#endif
#endif
