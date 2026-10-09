#ifndef QUEST_INTF_HASHMAP_H
#define QUEST_INTF_HASHMAP_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
#include "collections/vector.int.h"
typedef QVal quest_type_HashMap_T;
typedef QVal quest_type_HashMap_Entry;
typedef const QException * quest_sig_HashMap_error;
typedef QVal (*quest_sig_HashMap_new)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QClosure * equal, QClosure * hash);
typedef QVal (*quest_sig_HashMap_newIdentityMap)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V);
typedef QVal (*quest_sig_HashMap_newWithCapacity)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QInt capacity, QClosure * equal, QClosure * hash);
typedef QVal (*quest_sig_HashMap_newIdentityMapWithCapacity)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QInt capacity);
typedef QInt (*quest_sig_HashMap_size)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m);
typedef QBool (*quest_sig_HashMap_empty)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m);
typedef QVal (*quest_sig_HashMap_get)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m, QVal key);
typedef QBool (*quest_sig_HashMap_contains)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m, QVal key);
typedef QVal (*quest_sig_HashMap_find)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m, QVal key);
typedef QBool (*quest_sig_HashMap_insert)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m, QVal key, QVal value);
typedef QVal (*quest_sig_HashMap_delete)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m, QVal key);
typedef void (*quest_sig_HashMap_clear)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m);
typedef QVal (*quest_sig_HashMap_keys)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m);
typedef QVal (*quest_sig_HashMap_values)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m);
typedef QVal (*quest_sig_HashMap_entries)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m);
typedef void (*quest_sig_HashMap_forEach)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m, QClosure * action);
typedef QVal (*quest_sig_HashMap_map)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, const QTypeDescriptor *desc_W, QVal m, QClosure * f);
typedef QVal (*quest_sig_HashMap_filter)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, QVal m, QClosure * pred);
typedef QVal (*quest_sig_HashMap_fold)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, const QTypeDescriptor *desc_Acc, QVal m, QVal init, QClosure * f);
typedef QVal (*quest_sig_HashMap_filterMap)(const QTypeDescriptor *desc_K, const QTypeDescriptor *desc_V, const QTypeDescriptor *desc_W, QVal m, QClosure * f);
#ifdef __cplusplus
}
#endif
#endif
