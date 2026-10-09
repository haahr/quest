#ifndef QUEST_INTF_COLLECTIONS__VECTOR_H
#define QUEST_INTF_COLLECTIONS__VECTOR_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
typedef QVal quest_type_collections__Vector_T;
typedef const QException * quest_sig_collections__Vector_error;
typedef QVal (*quest_sig_collections__Vector_new)(const QTypeDescriptor *desc_A);
typedef QVal (*quest_sig_collections__Vector_newWithCapacity)(const QTypeDescriptor *desc_A, QInt capacity);
typedef QInt (*quest_sig_collections__Vector_length)(const QTypeDescriptor *desc_A, QVal v);
typedef QBool (*quest_sig_collections__Vector_empty)(const QTypeDescriptor *desc_A, QVal v);
typedef QVal (*quest_sig_collections__Vector_get)(const QTypeDescriptor *desc_A, QVal v, QInt index);
typedef void (*quest_sig_collections__Vector_set)(const QTypeDescriptor *desc_A, QVal v, QInt index, QVal value);
typedef QVal (*quest_sig_collections__Vector_first)(const QTypeDescriptor *desc_A, QVal v);
typedef QVal (*quest_sig_collections__Vector_last)(const QTypeDescriptor *desc_A, QVal v);
typedef void (*quest_sig_collections__Vector_append)(const QTypeDescriptor *desc_A, QVal v, QVal value);
typedef QVal (*quest_sig_collections__Vector_pop)(const QTypeDescriptor *desc_A, QVal v);
typedef void (*quest_sig_collections__Vector_delete)(const QTypeDescriptor *desc_A, QVal v, QInt index);
typedef void (*quest_sig_collections__Vector_clear)(const QTypeDescriptor *desc_A, QVal v);
typedef QVal (*quest_sig_collections__Vector_copy)(const QTypeDescriptor *desc_A, QVal v);
typedef QVal (*quest_sig_collections__Vector_concat)(const QTypeDescriptor *desc_A, QVal v1, QVal v2);
typedef QVal (*quest_sig_collections__Vector_fromArray)(const QTypeDescriptor *desc_A, QArray * arr);
typedef QArray * (*quest_sig_collections__Vector_toArray)(const QTypeDescriptor *desc_A, QVal v);
typedef void (*quest_sig_collections__Vector_forEach)(const QTypeDescriptor *desc_A, QVal v, QClosure * action);
typedef QVal (*quest_sig_collections__Vector_map)(const QTypeDescriptor *desc_A, const QTypeDescriptor *desc_B, QVal v, QClosure * f);
typedef QVal (*quest_sig_collections__Vector_filter)(const QTypeDescriptor *desc_A, QVal v, QClosure * pred);
typedef QVal (*quest_sig_collections__Vector_fold)(const QTypeDescriptor *desc_A, const QTypeDescriptor *desc_Acc, QVal v, QVal init, QClosure * f);
typedef QVal (*quest_sig_collections__Vector_filterMap)(const QTypeDescriptor *desc_A, const QTypeDescriptor *desc_B, QVal v, QClosure * f);
#ifdef __cplusplus
}
#endif
#endif
