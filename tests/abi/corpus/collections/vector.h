#ifndef QUEST_INTF_VECTOR_H
#define QUEST_INTF_VECTOR_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.h"
typedef QVal quest_type_Vector_T;
typedef const QException * quest_sig_Vector_error;
typedef QVal (*quest_sig_Vector_new)(const QTypeDescriptor *desc_A);
typedef QVal (*quest_sig_Vector_newWithCapacity)(const QTypeDescriptor *desc_A, QInt capacity);
typedef QInt (*quest_sig_Vector_length)(const QTypeDescriptor *desc_A, QVal v);
typedef QBool (*quest_sig_Vector_empty)(const QTypeDescriptor *desc_A, QVal v);
typedef QVal (*quest_sig_Vector_get)(const QTypeDescriptor *desc_A, QVal v, QInt index);
typedef void (*quest_sig_Vector_set)(const QTypeDescriptor *desc_A, QVal v, QInt index, QVal value);
typedef QVal (*quest_sig_Vector_first)(const QTypeDescriptor *desc_A, QVal v);
typedef QVal (*quest_sig_Vector_last)(const QTypeDescriptor *desc_A, QVal v);
typedef void (*quest_sig_Vector_append)(const QTypeDescriptor *desc_A, QVal v, QVal value);
typedef QVal (*quest_sig_Vector_pop)(const QTypeDescriptor *desc_A, QVal v);
typedef void (*quest_sig_Vector_delete)(const QTypeDescriptor *desc_A, QVal v, QInt index);
typedef void (*quest_sig_Vector_clear)(const QTypeDescriptor *desc_A, QVal v);
typedef QVal (*quest_sig_Vector_copy)(const QTypeDescriptor *desc_A, QVal v);
typedef QVal (*quest_sig_Vector_concat)(const QTypeDescriptor *desc_A, QVal v1, QVal v2);
typedef QVal (*quest_sig_Vector_fromArray)(const QTypeDescriptor *desc_A, QArray * arr);
typedef QArray * (*quest_sig_Vector_toArray)(const QTypeDescriptor *desc_A, QVal v);
typedef void (*quest_sig_Vector_forEach)(const QTypeDescriptor *desc_A, QVal v, QClosure * action);
typedef QVal (*quest_sig_Vector_map)(const QTypeDescriptor *desc_A, const QTypeDescriptor *desc_B, QVal v, QClosure * f);
typedef QVal (*quest_sig_Vector_filter)(const QTypeDescriptor *desc_A, QVal v, QClosure * pred);
typedef QVal (*quest_sig_Vector_fold)(const QTypeDescriptor *desc_A, const QTypeDescriptor *desc_Acc, QVal v, QVal init, QClosure * f);
typedef QVal (*quest_sig_Vector_filterMap)(const QTypeDescriptor *desc_A, const QTypeDescriptor *desc_B, QVal v, QClosure * f);
#ifdef __cplusplus
}
#endif
#endif
