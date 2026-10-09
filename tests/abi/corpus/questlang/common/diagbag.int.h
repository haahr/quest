#ifndef QUEST_INTF_QUESTLANG__COMMON__DIAGBAG_H
#define QUEST_INTF_QUESTLANG__COMMON__DIAGBAG_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/common/location.int.h"
#include "questlang/common/diagnostics.int.h"
#include "collections/vector.int.h"
#include "writer.int.h"
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
#endif
typedef QVal quest_type_questlang__common__DiagBag_T;
typedef const QException * quest_sig_questlang__common__DiagBag_fatalError;
typedef QVal (*quest_sig_questlang__common__DiagBag_new)(void);
typedef void (*quest_sig_questlang__common__DiagBag_add)(QVal bag, QVal d);
typedef void (*quest_sig_questlang__common__DiagBag_addError)(QVal bag, QTuple_String_Int_Int * sp, QString * msg);
typedef void (*quest_sig_questlang__common__DiagBag_addWarning)(QVal bag, QTuple_String_Int_Int * sp, QString * msg);
typedef void (*quest_sig_questlang__common__DiagBag_addFatal)(QVal bag, QTuple_String_Int_Int * sp, QString * msg);
typedef QBool (*quest_sig_questlang__common__DiagBag_hasErrors)(QVal bag);
typedef QInt (*quest_sig_questlang__common__DiagBag_errorCount)(QVal bag);
typedef QInt (*quest_sig_questlang__common__DiagBag_warningCount)(QVal bag);
typedef QInt (*quest_sig_questlang__common__DiagBag_count)(QVal bag);
typedef QVal (*quest_sig_questlang__common__DiagBag_get)(QVal bag, QInt idx);
typedef QVal (*quest_sig_questlang__common__DiagBag_getAll)(QVal bag);
typedef void (*quest_sig_questlang__common__DiagBag_renderAll)(QVal bag, QVal sm, QWriter * w);
#ifdef __cplusplus
}
#endif
#endif
