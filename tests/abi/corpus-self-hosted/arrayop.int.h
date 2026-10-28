#ifndef QUEST_INTF_ARRAYOP_H
#define QUEST_INTF_ARRAYOP_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef const QException * quest_sig_ArrayOp_error;
typedef QArray * (*quest_sig_ArrayOp_new)(const QTypeDescriptor *desc_A, QInt size, QVal init);
typedef QInt (*quest_sig_ArrayOp_size)(const QTypeDescriptor *desc_A, QArray * a);
typedef QVal (*quest_sig_ArrayOp_get)(const QTypeDescriptor *desc_A, QArray * a, QInt index);
typedef void (*quest_sig_ArrayOp_set)(const QTypeDescriptor *desc_A, QArray * a, QInt index, QVal item);
#ifdef __cplusplus
}
#endif
#endif
