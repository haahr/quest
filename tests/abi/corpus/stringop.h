#ifndef QUEST_INTF_STRINGOP_H
#define QUEST_INTF_STRINGOP_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef const QException * quest_sig_StringOp_error;
typedef QString * (*quest_sig_StringOp_new)(QInt size, QChar init);
typedef QBool (*quest_sig_StringOp_isEmpty)(QString * string);
typedef QInt (*quest_sig_StringOp_length)(QString * string);
typedef QChar (*quest_sig_StringOp_getChar)(QString * string, QInt index);
typedef void (*quest_sig_StringOp_setChar)(QString * string, QInt index, QChar q_char);
typedef QString * (*quest_sig_StringOp_getSub)(QString * source, QInt start, QInt size);
typedef void (*quest_sig_StringOp_setSub)(QString * dest, QInt destStart, QString * source, QInt sourceStart, QInt sourceSize);
typedef QString * (*quest_sig_StringOp_cat)(QString * s1, QString * s2);
typedef QString * (*quest_sig_StringOp_catSub)(QString * s1, QInt start1, QInt size1, QString * s2, QInt start2, QInt size2);
typedef QString * (*quest_sig_StringOp_conc)(QArray * a);
typedef QBool (*quest_sig_StringOp_equal)(QString * s1, QString * s2);
typedef QBool (*quest_sig_StringOp_equalSub)(QString * s1, QInt start1, QInt size1, QString * s2, QInt start2, QInt size2);
typedef QBool (*quest_sig_StringOp_precedes)(QString * s1, QString * s2);
typedef QBool (*quest_sig_StringOp_precedesSub)(QString * s1, QInt start1, QInt size1, QString * s2, QInt start2, QInt size2);
#ifdef __cplusplus
}
#endif
#endif
