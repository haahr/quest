#ifndef QUEST_INTF_QUESTLANG__CODEGEN__ARM64__TARGET_H
#define QUEST_INTF_QUESTLANG__CODEGEN__ARM64__TARGET_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/codegen/target.int.h"
#ifndef QUEST_TYPE_QOption_classInt_classReal_TYPEDEF
#define QUEST_TYPE_QOption_classInt_classReal_TYPEDEF
typedef struct QOption_classInt_classReal QOption_classInt_classReal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_TYPEDEF
#define QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_TYPEDEF
typedef struct QTuple_String_QOption_classInt_classReal_end QTuple_String_QOption_classInt_classReal_end;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_TYPEDEF
typedef struct QTuple_QArray_QTuple_Str_822a60fcf247226d QTuple_QArray_QTuple_Str_822a60fcf247226d;
#endif
#ifndef QUEST_TYPE_QOption_classInt_classReal_DEFINED
#define QUEST_TYPE_QOption_classInt_classReal_DEFINED
struct QOption_classInt_classReal {
    int64_t tag;
};
static_assert(sizeof(struct QOption_classInt_classReal) == 8, layout_QOption_classInt_classReal_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_DEFINED
#define QUEST_TYPE_QTuple_String_QOption_classInt_classReal_end_DEFINED
struct QTuple_String_QOption_classInt_classReal_end {
    QString * _0;
    QOption_classInt_classReal * _1;
};
static_assert(offsetof(struct QTuple_String_QOption_classInt_classReal_end, _0) == 0, layout_QTuple_String_QOption_classInt_classReal_end__0);
static_assert(offsetof(struct QTuple_String_QOption_classInt_classReal_end, _1) == 8, layout_QTuple_String_QOption_classInt_classReal_end__1);
static_assert(sizeof(struct QTuple_String_QOption_classInt_classReal_end) == 16, layout_QTuple_String_QOption_classInt_classReal_end_size);
#endif
#ifndef QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_DEFINED
#define QUEST_TYPE_QTuple_QArray_QTuple_Str_822a60fcf247226d_DEFINED
struct QTuple_QArray_QTuple_Str_822a60fcf247226d {
    QArray * _0;
    QArray * _1;
    QArray * _2;
    QArray * _3;
    QArray * _4;
    QArray * _5;
    QInt _6;
    QInt _7;
};
static_assert(offsetof(struct QTuple_QArray_QTuple_Str_822a60fcf247226d, _0) == 0, layout_QTuple_QArray_QTuple_Str_822a60fcf247226d__0);
static_assert(offsetof(struct QTuple_QArray_QTuple_Str_822a60fcf247226d, _1) == 8, layout_QTuple_QArray_QTuple_Str_822a60fcf247226d__1);
static_assert(offsetof(struct QTuple_QArray_QTuple_Str_822a60fcf247226d, _2) == 16, layout_QTuple_QArray_QTuple_Str_822a60fcf247226d__2);
static_assert(offsetof(struct QTuple_QArray_QTuple_Str_822a60fcf247226d, _3) == 24, layout_QTuple_QArray_QTuple_Str_822a60fcf247226d__3);
static_assert(offsetof(struct QTuple_QArray_QTuple_Str_822a60fcf247226d, _4) == 32, layout_QTuple_QArray_QTuple_Str_822a60fcf247226d__4);
static_assert(offsetof(struct QTuple_QArray_QTuple_Str_822a60fcf247226d, _5) == 40, layout_QTuple_QArray_QTuple_Str_822a60fcf247226d__5);
static_assert(offsetof(struct QTuple_QArray_QTuple_Str_822a60fcf247226d, _6) == 48, layout_QTuple_QArray_QTuple_Str_822a60fcf247226d__6);
static_assert(offsetof(struct QTuple_QArray_QTuple_Str_822a60fcf247226d, _7) == 56, layout_QTuple_QArray_QTuple_Str_822a60fcf247226d__7);
static_assert(sizeof(struct QTuple_QArray_QTuple_Str_822a60fcf247226d) == 64, layout_QTuple_QArray_QTuple_Str_822a60fcf247226d_size);
#endif
typedef QTuple_QArray_QTuple_Str_822a60fcf247226d * quest_sig_questlang__codegen__arm64__Target_description;
typedef QInt (*quest_sig_questlang__codegen__arm64__Target_x)(QInt n);
typedef QInt (*quest_sig_questlang__codegen__arm64__Target_d)(QInt n);
typedef QInt quest_sig_questlang__codegen__arm64__Target_xzr;
typedef QInt quest_sig_questlang__codegen__arm64__Target_sp;
typedef QInt quest_sig_questlang__codegen__arm64__Target_fp;
typedef QInt quest_sig_questlang__codegen__arm64__Target_lr;
typedef QString * (*quest_sig_questlang__codegen__arm64__Target_name)(QInt r);
typedef QString * (*quest_sig_questlang__codegen__arm64__Target_half)(QInt r);
typedef QBool (*quest_sig_questlang__codegen__arm64__Target_isReal)(QInt r);
#ifdef __cplusplus
}
#endif
#endif
