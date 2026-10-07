#ifndef QUEST_INTF_INTOP_H
#define QUEST_INTF_INTOP_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef const QException * quest_sig_IntOp_error;
typedef QInt quest_sig_IntOp_minInt;
typedef QInt quest_sig_IntOp_maxInt;
typedef QInt (*quest_sig_IntOp_abs)(QInt n);
typedef QInt (*quest_sig_IntOp_min)(QInt a, QInt b);
typedef QInt (*quest_sig_IntOp_max)(QInt a, QInt b);
#ifdef __cplusplus
}
#endif
#endif
