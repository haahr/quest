#ifndef QUEST_INTF_QUESTLANG__COMMON__LOCATION_H
#define QUEST_INTF_QUESTLANG__COMMON__LOCATION_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/vector.int.h"
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_Int_TYPEDEF
typedef struct QTuple_Int_Int_Int QTuple_Int_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end_TYPEDEF
typedef struct QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_Int_DEFINED
struct QTuple_Int_Int_Int {
    QInt _0;
    QInt _1;
    QInt _2;
};
static_assert(offsetof(struct QTuple_Int_Int_Int, _0) == 0, layout_QTuple_Int_Int_Int__0);
static_assert(offsetof(struct QTuple_Int_Int_Int, _1) == 8, layout_QTuple_Int_Int_Int__1);
static_assert(offsetof(struct QTuple_Int_Int_Int, _2) == 16, layout_QTuple_Int_Int_Int__2);
static_assert(sizeof(struct QTuple_Int_Int_Int) == 24, layout_QTuple_Int_Int_Int_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
static_assert(offsetof(struct QTuple_String_Int_Int, _0) == 0, layout_QTuple_String_Int_Int__0);
static_assert(offsetof(struct QTuple_String_Int_Int, _1) == 8, layout_QTuple_String_Int_Int__1);
static_assert(offsetof(struct QTuple_String_Int_Int, _2) == 16, layout_QTuple_String_Int_Int__2);
static_assert(sizeof(struct QTuple_String_Int_Int) == 24, layout_QTuple_String_Int_Int_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end_DEFINED
#define QUEST_TYPE_QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end_DEFINED
struct QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end {
    QTuple_Int_Int_Int * _0;
    QTuple_Int_Int_Int * _1;
};
static_assert(offsetof(struct QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end, _0) == 0, layout_QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end__0);
static_assert(offsetof(struct QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end, _1) == 8, layout_QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end__1);
static_assert(sizeof(struct QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end) == 16, layout_QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end_size);
#endif
typedef QTuple_Int_Int_Int * quest_type_questlang__common__Location_Pos;
typedef QTuple_String_Int_Int * quest_type_questlang__common__Location_Span;
typedef QVal quest_type_questlang__common__Location_SourceMap;
typedef QVal (*quest_sig_questlang__common__Location_newSourceMap)(QString * file, QString * text);
typedef QTuple_String_Int_Int * (*quest_sig_questlang__common__Location_span)(QString * file, QInt startOffset, QInt endOffset);
typedef QTuple_String_Int_Int * (*quest_sig_questlang__common__Location_pointSpan)(QString * file, QInt offset);
typedef QString * (*quest_sig_questlang__common__Location_file)(QVal sm);
typedef QString * (*quest_sig_questlang__common__Location_text)(QVal sm);
typedef QInt (*quest_sig_questlang__common__Location_lineCount)(QVal sm);
typedef QTuple_Int_Int_Int * (*quest_sig_questlang__common__Location_locate)(QVal sm, QInt offset);
typedef QTuple_QTuple_Int_Int_Int_end_QTuple_Int_Int_Int_end * (*quest_sig_questlang__common__Location_locateSpan)(QVal sm, QTuple_String_Int_Int * sp);
typedef QString * (*quest_sig_questlang__common__Location_getLine)(QVal sm, QInt lineNum);
typedef QString * (*quest_sig_questlang__common__Location_extractSnippet)(QVal sm, QTuple_String_Int_Int * sp);
#ifdef __cplusplus
}
#endif
#endif
