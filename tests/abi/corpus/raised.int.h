#ifndef QUEST_INTF_RAISED_H
#define QUEST_INTF_RAISED_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_Raised_T;
typedef QVal (*quest_sig_Raised_reraise)(const QTypeDescriptor *desc_A, QVal r);
#ifdef __cplusplus
}
#endif
#endif
