#ifndef QUEST_INTF_QUESTLANG__CODEGEN__SYNTAX_H
#define QUEST_INTF_QUESTLANG__CODEGEN__SYNTAX_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/vector.int.h"
typedef QString * (*quest_sig_questlang__codegen__Syntax_cInt)(QInt n);
typedef QString * (*quest_sig_questlang__codegen__Syntax_cIntLiteral)(QInt n);
typedef QString * (*quest_sig_questlang__codegen__Syntax_cReal)(QReal r);
typedef QString * (*quest_sig_questlang__codegen__Syntax_cString)(QString * s);
typedef QString * (*quest_sig_questlang__codegen__Syntax_cChar)(QChar c);
typedef QString * (*quest_sig_questlang__codegen__Syntax_indexTable)(QArray * entries);
typedef QString * (*quest_sig_questlang__codegen__Syntax_comma)(QVal items);
typedef QString * (*quest_sig_questlang__codegen__Syntax_call)(QString * f, QVal args);
typedef QString * (*quest_sig_questlang__codegen__Syntax_joined)(QString * separator, QVal items);
typedef QString * (*quest_sig_questlang__codegen__Syntax_linesText)(QVal items);
#ifdef __cplusplus
}
#endif
#endif
