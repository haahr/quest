#ifndef QUEST_INTF_COLLECTIONS__HASHSET_H
#define QUEST_INTF_COLLECTIONS__HASHSET_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/vector.int.h"
#include "util/maybe.int.h"
typedef QVal quest_type_collections__HashSet_T;
typedef QVal (*quest_sig_collections__HashSet_new)(const QTypeDescriptor *desc_A, QClosure * equal, QClosure * hash);
typedef QVal (*quest_sig_collections__HashSet_newIdentitySet)(const QTypeDescriptor *desc_A);
typedef QVal (*quest_sig_collections__HashSet_newWithCapacity)(const QTypeDescriptor *desc_A, QInt capacity, QClosure * equal, QClosure * hash);
typedef QVal (*quest_sig_collections__HashSet_newIdentitySetWithCapacity)(const QTypeDescriptor *desc_A, QInt capacity);
typedef QInt (*quest_sig_collections__HashSet_size)(const QTypeDescriptor *desc_A, QVal s);
typedef QBool (*quest_sig_collections__HashSet_empty)(const QTypeDescriptor *desc_A, QVal s);
typedef QBool (*quest_sig_collections__HashSet_contains)(const QTypeDescriptor *desc_A, QVal s, QVal elem);
typedef QBool (*quest_sig_collections__HashSet_insert)(const QTypeDescriptor *desc_A, QVal s, QVal elem);
typedef QBool (*quest_sig_collections__HashSet_delete)(const QTypeDescriptor *desc_A, QVal s, QVal elem);
typedef void (*quest_sig_collections__HashSet_clear)(const QTypeDescriptor *desc_A, QVal s);
typedef QVal (*quest_sig_collections__HashSet_elements)(const QTypeDescriptor *desc_A, QVal s);
typedef void (*quest_sig_collections__HashSet_forEach)(const QTypeDescriptor *desc_A, QVal s, QClosure * action);
typedef QVal (*quest_sig_collections__HashSet_copy)(const QTypeDescriptor *desc_A, QVal s);
typedef QVal (*quest_sig_collections__HashSet_union)(const QTypeDescriptor *desc_A, QVal s1, QVal s2);
typedef QVal (*quest_sig_collections__HashSet_intersection)(const QTypeDescriptor *desc_A, QVal s1, QVal s2);
typedef QVal (*quest_sig_collections__HashSet_difference)(const QTypeDescriptor *desc_A, QVal s1, QVal s2);
typedef QBool (*quest_sig_collections__HashSet_isSubset)(const QTypeDescriptor *desc_A, QVal s1, QVal s2);
typedef QBool (*quest_sig_collections__HashSet_equal)(const QTypeDescriptor *desc_A, QVal s1, QVal s2);
typedef QVal (*quest_sig_collections__HashSet_filter)(const QTypeDescriptor *desc_A, QVal s, QClosure * pred);
typedef QVal (*quest_sig_collections__HashSet_fold)(const QTypeDescriptor *desc_A, const QTypeDescriptor *desc_Acc, QVal s, QVal init, QClosure * f);
typedef QVal (*quest_sig_collections__HashSet_map)(const QTypeDescriptor *desc_A, const QTypeDescriptor *desc_B, QVal s, QClosure * equal, QClosure * hash, QClosure * f);
typedef QVal (*quest_sig_collections__HashSet_filterMap)(const QTypeDescriptor *desc_A, const QTypeDescriptor *desc_B, QVal s, QClosure * equal, QClosure * hash, QClosure * f);
#ifdef __cplusplus
}
#endif
#endif
