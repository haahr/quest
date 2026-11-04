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
static_assert(offsetof(struct QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal, _0) == 0, layout_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal__0);
static_assert(offsetof(struct QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal, _1) == 8, layout_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal__1);
static_assert(offsetof(struct QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal, _2) == 16, layout_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal__2);
static_assert(offsetof(struct QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal, _3) == 24, layout_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal__3);
static_assert(offsetof(struct QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal, _4) == 32, layout_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal__4);
static_assert(offsetof(struct QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal, _5) == 40, layout_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal__5);
static_assert(offsetof(struct QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal, _6) == 48, layout_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal__6);
static_assert(sizeof(struct QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal) == 56, layout_QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal_size);
#endif
typedef QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal * quest_type_questlang__syntax__parser__Grammar_T;
typedef QTuple_QVal_QVal_QVal_QVal_QVal_QVal_QVal * (*quest_sig_questlang__syntax__parser__Grammar_new)(void);
#ifdef __cplusplus
}
#endif
#endif
