#ifndef QUEST_INTF_TOKENS_H
#define QUEST_INTF_TOKENS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/common/location.h"
#include "util/maybe.h"
#ifndef QUEST_TYPE_QOption_eof_intLit_realL_402807316f56e5f0_TYPEDEF
#define QUEST_TYPE_QOption_eof_intLit_realL_402807316f56e5f0_TYPEDEF
typedef struct QOption_eof_intLit_realL_402807316f56e5f0 QOption_eof_intLit_realL_402807316f56e5f0;
#endif
#ifndef QUEST_TYPE_QTuple_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_TYPEDEF
typedef struct QTuple_Int QTuple_Int;
#endif
#ifndef QUEST_TYPE_QTuple_Real_TYPEDEF
#define QUEST_TYPE_QTuple_Real_TYPEDEF
typedef struct QTuple_Real QTuple_Real;
#endif
#ifndef QUEST_TYPE_QTuple_Char_TYPEDEF
#define QUEST_TYPE_QTuple_Char_TYPEDEF
typedef struct QTuple_Char QTuple_Char;
#endif
#ifndef QUEST_TYPE_QTuple_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_TYPEDEF
typedef struct QTuple_String QTuple_String;
#endif
#ifndef QUEST_TYPE_QOption_none_intVal_QTup_eee794bf7a376dd2_TYPEDEF
#define QUEST_TYPE_QOption_none_intVal_QTup_eee794bf7a376dd2_TYPEDEF
typedef struct QOption_none_intVal_QTup_eee794bf7a376dd2 QOption_none_intVal_QTup_eee794bf7a376dd2;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_eof_intLi_c440526c91fabf71_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_eof_intLi_c440526c91fabf71_TYPEDEF
typedef struct QTuple_QOption_eof_intLi_c440526c91fabf71 QTuple_QOption_eof_intLi_c440526c91fabf71;
#endif
#ifndef QUEST_TYPE_QOption_eof_intLit_realL_402807316f56e5f0_DEFINED
#define QUEST_TYPE_QOption_eof_intLit_realL_402807316f56e5f0_DEFINED
struct QOption_eof_intLit_realL_402807316f56e5f0 {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_DEFINED
struct QTuple_Int {
    QInt _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Real_DEFINED
#define QUEST_TYPE_QTuple_Real_DEFINED
struct QTuple_Real {
    QReal _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Char_DEFINED
#define QUEST_TYPE_QTuple_Char_DEFINED
struct QTuple_Char {
    QChar _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
#endif
#ifndef QUEST_TYPE_QOption_none_intVal_QTup_eee794bf7a376dd2_DEFINED
#define QUEST_TYPE_QOption_none_intVal_QTup_eee794bf7a376dd2_DEFINED
struct QOption_none_intVal_QTup_eee794bf7a376dd2 {
    int64_t tag;
    union {
        struct QOption_none_intVal_QTup_eee794bf7a376dd2_intVal_payload {
            QInt _0;
        } intVal;
        struct QOption_none_intVal_QTup_eee794bf7a376dd2_realVal_payload {
            QReal _0;
        } realVal;
        struct QOption_none_intVal_QTup_eee794bf7a376dd2_charVal_payload {
            QChar _0;
        } charVal;
        struct QOption_none_intVal_QTup_eee794bf7a376dd2_stringVal_payload {
            QString * _0;
        } stringVal;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QOption_eof_intLi_c440526c91fabf71_DEFINED
#define QUEST_TYPE_QTuple_QOption_eof_intLi_c440526c91fabf71_DEFINED
struct QTuple_QOption_eof_intLi_c440526c91fabf71 {
    QOption_eof_intLit_realL_402807316f56e5f0 * _0;
    QString * _1;
    QOption_none_intVal_QTup_eee794bf7a376dd2 * _2;
    QTuple_String_Int_Int * _3;
};
#endif
typedef QOption_eof_intLit_realL_402807316f56e5f0 * quest_type_Tokens_TokenKind;
typedef QOption_none_intVal_QTup_eee794bf7a376dd2 * quest_type_Tokens_TokenValue;
typedef QTuple_QOption_eof_intLi_c440526c91fabf71 * quest_type_Tokens_Token;
typedef QTuple_QOption_eof_intLi_c440526c91fabf71 * (*quest_sig_Tokens_make)(QOption_eof_intLit_realL_402807316f56e5f0 * kind, QString * lexeme, QOption_none_intVal_QTup_eee794bf7a376dd2 * value, QTuple_String_Int_Int * span);
typedef QOption_none_intVal_QTup_eee794bf7a376dd2 * (*quest_sig_Tokens_valNone)(void);
typedef QOption_none_intVal_QTup_eee794bf7a376dd2 * (*quest_sig_Tokens_valInt)(QInt n);
typedef QOption_none_intVal_QTup_eee794bf7a376dd2 * (*quest_sig_Tokens_valReal)(QReal r);
typedef QOption_none_intVal_QTup_eee794bf7a376dd2 * (*quest_sig_Tokens_valChar)(QChar c);
typedef QOption_none_intVal_QTup_eee794bf7a376dd2 * (*quest_sig_Tokens_valString)(QString * s);
typedef QTuple_QOption_eof_intLi_c440526c91fabf71 * (*quest_sig_Tokens_eofToken)(QString * file, QInt offset);
typedef QString * (*quest_sig_Tokens_tokenKindName)(QOption_eof_intLit_realL_402807316f56e5f0 * kind);
typedef QBool (*quest_sig_Tokens_isKeyword)(QOption_eof_intLit_realL_402807316f56e5f0 * kind);
typedef QBool (*quest_sig_Tokens_isLiteral)(QOption_eof_intLit_realL_402807316f56e5f0 * kind);
typedef QBool (*quest_sig_Tokens_isDelimiter)(QOption_eof_intLit_realL_402807316f56e5f0 * kind);
typedef QBool (*quest_sig_Tokens_isPunctuation)(QOption_eof_intLit_realL_402807316f56e5f0 * kind);
#ifdef __cplusplus
}
#endif
#endif
