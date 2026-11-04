#ifndef QUEST_INTF_OS__VALUE_H
#define QUEST_INTF_OS__VALUE_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_os__Value_T;
typedef const QException * quest_sig_os__Value_error;
typedef QInt quest_sig_os__Value_length;
typedef QVal (*quest_sig_os__Value_new)(const QTypeDescriptor *desc_A, QVal a);
typedef QVal (*quest_sig_os__Value_be)(const QTypeDescriptor *desc_A, QVal v);
typedef QVal (*quest_sig_os__Value_fetch)(QVal addr, QInt displ);
typedef void (*quest_sig_os__Value_store)(QVal addr, QInt displ, QVal w);
#ifdef __cplusplus
}
#endif
#endif
