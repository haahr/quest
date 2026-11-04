#ifndef QUEST_INTF_QUESTLANG__SYNTAX__PARSER__GRAMMAR_H
#define QUEST_INTF_QUESTLANG__SYNTAX__PARSER__GRAMMAR_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/syntax/parser/engine.int.h"
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal_DEFINED
struct QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal {
    QVal _0;
    QVal _1;
    QVal _2;
    QVal _3;
    QVal _4;
    QVal _5;
    QVal _6;
};
#endif
typedef QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal * quest_type_questlang__syntax__parser__Grammar_T;
typedef QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal * (*quest_sig_questlang__syntax__parser__Grammar_new)(void);
#ifdef __cplusplus
}
#endif
#endif
