#ifndef QUEST_INTF_QUESTLANG__COMMON__MEMORYFILES_H
#define QUEST_INTF_QUESTLANG__COMMON__MEMORYFILES_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
typedef QString * quest_sig_questlang__common__MemoryFiles_root;
typedef QBool (*quest_sig_questlang__common__MemoryFiles_isMemory)(QString * path);
typedef QVal (*quest_sig_questlang__common__MemoryFiles_read)(QString * path);
typedef void (*quest_sig_questlang__common__MemoryFiles_write)(QString * path, QString * text);
#ifdef __cplusplus
}
#endif
#endif
