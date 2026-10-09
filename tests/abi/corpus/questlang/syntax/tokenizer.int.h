#ifndef QUEST_INTF_TOKENIZER_H
#define QUEST_INTF_TOKENIZER_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/common/location.int.h"
#include "questlang/common/diagbag.int.h"
#include "questlang/syntax/tokens.int.h"
#include "collections/vector.int.h"
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
typedef QVal quest_type_Tokenizer_T;
typedef QVal (*quest_sig_Tokenizer_new)(QVal sm, QVal bag);
typedef QTuple_QOption_eof_intLi_c440526c91fabf71 * (*quest_sig_Tokenizer_nextToken)(QVal tok);
typedef QTuple_QOption_eof_intLi_c440526c91fabf71 * (*quest_sig_Tokenizer_peekToken)(QVal tok);
typedef QVal (*quest_sig_Tokenizer_tokenizeAll)(QVal tok);
typedef QString * (*quest_sig_Tokenizer_formatDump)(QVal tokensList, QVal sm, QBool showValues);
#ifdef __cplusplus
}
#endif
#endif
