#ifndef QUEST_INTF_LIST_H
#define QUEST_INTF_LIST_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_List_T;
typedef const QException * quest_sig_List_error;
typedef QVal (*quest_sig_List_nil)(const QTypeDescriptor *desc_A);
typedef QVal (*quest_sig_List_cons)(const QTypeDescriptor *desc_A, QVal item, QVal list);
typedef QBool (*quest_sig_List_null)(const QTypeDescriptor *desc_A, QVal list);
typedef QVal (*quest_sig_List_head)(const QTypeDescriptor *desc_A, QVal list);
typedef QVal (*quest_sig_List_tail)(const QTypeDescriptor *desc_A, QVal list);
typedef QInt (*quest_sig_List_length)(const QTypeDescriptor *desc_A, QVal list);
typedef QVal (*quest_sig_List_enum)(const QTypeDescriptor *desc_A, QArray * a);
#ifdef __cplusplus
}
#endif
#endif
