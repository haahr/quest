#ifndef QUEST_INTF_QUESTLANG__DRIVER__INTERRUPTS_H
#define QUEST_INTF_QUESTLANG__DRIVER__INTERRUPTS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QBool (*quest_sig_questlang__driver__Interrupts_install)(void);
typedef QBool (*quest_sig_questlang__driver__Interrupts_take)(void);
typedef void (*quest_sig_questlang__driver__Interrupts_clear)(void);
#ifdef __cplusplus
}
#endif
#endif
