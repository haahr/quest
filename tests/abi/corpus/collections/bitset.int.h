#ifndef QUEST_INTF_COLLECTIONS__BITSET_H
#define QUEST_INTF_COLLECTIONS__BITSET_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_collections__Bitset_T;
typedef const QException * quest_sig_collections__Bitset_error;
typedef QVal (*quest_sig_collections__Bitset_new)(QInt size);
typedef QInt (*quest_sig_collections__Bitset_size)(QVal s);
typedef QBool (*quest_sig_collections__Bitset_contains)(QVal s, QInt i);
typedef QBool (*quest_sig_collections__Bitset_insert)(QVal s, QInt i);
typedef QBool (*quest_sig_collections__Bitset_remove)(QVal s, QInt i);
typedef void (*quest_sig_collections__Bitset_clear)(QVal s);
typedef QInt (*quest_sig_collections__Bitset_count)(QVal s);
typedef QBool (*quest_sig_collections__Bitset_isEmpty)(QVal s);
typedef QVal (*quest_sig_collections__Bitset_copy)(QVal s);
typedef void (*quest_sig_collections__Bitset_assign)(QVal s, QVal t);
typedef QBool (*quest_sig_collections__Bitset_unionWith)(QVal s, QVal t);
typedef QBool (*quest_sig_collections__Bitset_intersectWith)(QVal s, QVal t);
typedef QBool (*quest_sig_collections__Bitset_subtract)(QVal s, QVal t);
typedef QBool (*quest_sig_collections__Bitset_equal)(QVal s, QVal t);
typedef QBool (*quest_sig_collections__Bitset_isSubset)(QVal s, QVal t);
typedef QInt (*quest_sig_collections__Bitset_next)(QVal s, QInt from);
typedef QArray * (*quest_sig_collections__Bitset_elements)(QVal s);
#ifdef __cplusplus
}
#endif
#endif
