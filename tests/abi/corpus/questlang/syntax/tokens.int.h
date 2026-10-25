#ifndef QUEST_INTF_QUESTLANG__SYNTAX__TOKENS_H
#define QUEST_INTF_QUESTLANG__SYNTAX__TOKENS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/common/location.int.h"
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QOption_assign_at_bang_c_9d67c602c649263b_TYPEDEF
#define QUEST_TYPE_QOption_assign_at_bang_c_9d67c602c649263b_TYPEDEF
typedef struct QOption_assign_at_bang_c_9d67c602c649263b QOption_assign_at_bang_c_9d67c602c649263b;
#endif
#ifndef QUEST_TYPE_QTuple_Char_TYPEDEF
#define QUEST_TYPE_QTuple_Char_TYPEDEF
typedef struct QTuple_Char QTuple_Char;
#endif
#ifndef QUEST_TYPE_QTuple_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_TYPEDEF
typedef struct QTuple_Int QTuple_Int;
#endif
#ifndef QUEST_TYPE_QTuple_Real_TYPEDEF
#define QUEST_TYPE_QTuple_Real_TYPEDEF
typedef struct QTuple_Real QTuple_Real;
#endif
#ifndef QUEST_TYPE_QTuple_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_TYPEDEF
typedef struct QTuple_String QTuple_String;
#endif
#ifndef QUEST_TYPE_QOption_charVal_QTuple_C_858f5528ce3cda86_TYPEDEF
#define QUEST_TYPE_QOption_charVal_QTuple_C_858f5528ce3cda86_TYPEDEF
typedef struct QOption_charVal_QTuple_C_858f5528ce3cda86 QOption_charVal_QTuple_C_858f5528ce3cda86;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_QOption_assign_at_723595ebb1959a6e_TYPEDEF
#define QUEST_TYPE_QTuple_QOption_assign_at_723595ebb1959a6e_TYPEDEF
typedef struct QTuple_QOption_assign_at_723595ebb1959a6e QTuple_QOption_assign_at_723595ebb1959a6e;
#endif
#ifndef QUEST_TYPE_QOption_assign_at_bang_c_9d67c602c649263b_DEFINED
#define QUEST_TYPE_QOption_assign_at_bang_c_9d67c602c649263b_DEFINED
struct QOption_assign_at_bang_c_9d67c602c649263b {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_Char_DEFINED
#define QUEST_TYPE_QTuple_Char_DEFINED
struct QTuple_Char {
    QCharSlot _0;
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
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
#endif
#ifndef QUEST_TYPE_QOption_charVal_QTuple_C_858f5528ce3cda86_DEFINED
#define QUEST_TYPE_QOption_charVal_QTuple_C_858f5528ce3cda86_DEFINED
struct QOption_charVal_QTuple_C_858f5528ce3cda86 {
    int64_t tag;
    union {
        struct QOption_charVal_QTuple_C_858f5528ce3cda86_charVal_payload {
            QCharSlot _0;
        } charVal;
        struct QOption_charVal_QTuple_C_858f5528ce3cda86_intVal_payload {
            QInt _0;
        } intVal;
        struct QOption_charVal_QTuple_C_858f5528ce3cda86_realVal_payload {
            QReal _0;
        } realVal;
        struct QOption_charVal_QTuple_C_858f5528ce3cda86_stringVal_payload {
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
#ifndef QUEST_TYPE_QTuple_QOption_assign_at_723595ebb1959a6e_DEFINED
#define QUEST_TYPE_QTuple_QOption_assign_at_723595ebb1959a6e_DEFINED
struct QTuple_QOption_assign_at_723595ebb1959a6e {
    QOption_assign_at_bang_c_9d67c602c649263b * _0;
    QString * _1;
    QOption_charVal_QTuple_C_858f5528ce3cda86 * _2;
    QTuple_String_Int_Int * _3;
};
#endif
typedef QOption_assign_at_bang_c_9d67c602c649263b * quest_type_questlang__syntax__Tokens_TokenKind;
typedef QOption_charVal_QTuple_C_858f5528ce3cda86 * quest_type_questlang__syntax__Tokens_TokenValue;
typedef QTuple_QOption_assign_at_723595ebb1959a6e * quest_type_questlang__syntax__Tokens_Token;
typedef QTuple_QOption_assign_at_723595ebb1959a6e * (*quest_sig_questlang__syntax__Tokens_make)(QOption_assign_at_bang_c_9d67c602c649263b * kind, QString * lexeme, QOption_charVal_QTuple_C_858f5528ce3cda86 * value, QTuple_String_Int_Int * span);
typedef QOption_charVal_QTuple_C_858f5528ce3cda86 * (*quest_sig_questlang__syntax__Tokens_valNone)(void);
typedef QOption_charVal_QTuple_C_858f5528ce3cda86 * (*quest_sig_questlang__syntax__Tokens_valInt)(QInt n);
typedef QOption_charVal_QTuple_C_858f5528ce3cda86 * (*quest_sig_questlang__syntax__Tokens_valReal)(QReal r);
typedef QOption_charVal_QTuple_C_858f5528ce3cda86 * (*quest_sig_questlang__syntax__Tokens_valChar)(QChar c);
typedef QOption_charVal_QTuple_C_858f5528ce3cda86 * (*quest_sig_questlang__syntax__Tokens_valString)(QString * s);
typedef QTuple_QOption_assign_at_723595ebb1959a6e * (*quest_sig_questlang__syntax__Tokens_eofToken)(QString * file, QInt offset);
typedef QString * (*quest_sig_questlang__syntax__Tokens_tokenKindName)(QOption_assign_at_bang_c_9d67c602c649263b * kind);
typedef QBool (*quest_sig_questlang__syntax__Tokens_isKeyword)(QOption_assign_at_bang_c_9d67c602c649263b * kind);
typedef QBool (*quest_sig_questlang__syntax__Tokens_isLiteral)(QOption_assign_at_bang_c_9d67c602c649263b * kind);
typedef QBool (*quest_sig_questlang__syntax__Tokens_isDelimiter)(QOption_assign_at_bang_c_9d67c602c649263b * kind);
typedef QBool (*quest_sig_questlang__syntax__Tokens_isPunctuation)(QOption_assign_at_bang_c_9d67c602c649263b * kind);
#ifdef __cplusplus
}
#endif
#endif
