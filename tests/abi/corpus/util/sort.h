#ifndef QUEST_INTF_SORT_H
#define QUEST_INTF_SORT_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/vector.h"
#include "util/maybe.h"
typedef QInt (*quest_sig_Sort_intCompare)(QInt a, QInt b);
typedef QInt (*quest_sig_Sort_stringCompare)(QString * a, QString * b);
typedef QInt (*quest_sig_Sort_realCompare)(QReal a, QReal b);
typedef QClosure * (*quest_sig_Sort_reverse)(const QTypeDescriptor *desc_A, QClosure * cmp);
typedef QInt (*quest_sig_Sort_bisectRight)(const QTypeDescriptor *desc_A, QArray * arr, QVal key, QClosure * cmp);
typedef QInt (*quest_sig_Sort_bisectRightVector)(const QTypeDescriptor *desc_A, QVal v, QVal key, QClosure * cmp);
typedef QInt (*quest_sig_Sort_bisectRightRange)(const QTypeDescriptor *desc_A, QArray * arr, QVal key, QInt lo, QInt hi, QClosure * cmp);
typedef QInt (*quest_sig_Sort_bisectLeft)(const QTypeDescriptor *desc_A, QArray * arr, QVal key, QClosure * cmp);
typedef QInt (*quest_sig_Sort_bisectLeftVector)(const QTypeDescriptor *desc_A, QVal v, QVal key, QClosure * cmp);
typedef QInt (*quest_sig_Sort_bisectLeftRange)(const QTypeDescriptor *desc_A, QArray * arr, QVal key, QInt lo, QInt hi, QClosure * cmp);
typedef QVal (*quest_sig_Sort_binarySearch)(const QTypeDescriptor *desc_A, QArray * arr, QVal key, QClosure * cmp);
typedef QVal (*quest_sig_Sort_binarySearchVector)(const QTypeDescriptor *desc_A, QVal v, QVal key, QClosure * cmp);
typedef void (*quest_sig_Sort_sort)(const QTypeDescriptor *desc_A, QArray * arr, QClosure * cmp);
typedef void (*quest_sig_Sort_sortVector)(const QTypeDescriptor *desc_A, QVal v, QClosure * cmp);
typedef QArray * (*quest_sig_Sort_sorted)(const QTypeDescriptor *desc_A, QArray * arr, QClosure * cmp);
typedef QVal (*quest_sig_Sort_sortedVector)(const QTypeDescriptor *desc_A, QVal v, QClosure * cmp);
#ifdef __cplusplus
}
#endif
#endif
