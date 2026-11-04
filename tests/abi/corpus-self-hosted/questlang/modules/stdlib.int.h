#ifndef QUEST_INTF_QUESTLANG__MODULES__STDLIB_H
#define QUEST_INTF_QUESTLANG__MODULES__STDLIB_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/types/env.int.h"
#ifndef QUEST_TYPE_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_TYPEDEF
typedef struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_TYPEDEF
typedef struct QTuple_QVal QTuple_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_TYPEDEF
typedef struct QTuple_QTuple_QVal_end_QVal QTuple_QTuple_QVal_end_QVal;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_TYPEDEF
typedef struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QClosure_QClosure_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QClosure_QClosure_TYPEDEF
typedef struct Rec0_QTuple_QClosure_QClosure Rec0_QTuple_QClosure_QClosure;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_DEFINED
struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal {
    QVal _0;
    QString * _1;
    QVal _2;
    QBoolSlot _3;
    QVal _4;
    QVal _5;
    QVal _6;
    QVal _7;
    QVal _8;
    QVal _9;
};
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _0) == 0, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__0);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _1) == 8, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__1);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _2) == 16, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__2);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _3) == 24, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__3);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _4) == 32, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__4);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _5) == 40, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__5);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _6) == 48, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__6);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _7) == 56, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__7);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _8) == 64, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__8);
static_assert(offsetof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal, _9) == 72, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal__9);
static_assert(sizeof(struct Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal) == 80, layout_Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal_size);
#endif
#ifndef QUEST_TYPE_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_DEFINED
struct QTuple_QVal {
    QVal _0;
};
static_assert(offsetof(struct QTuple_QVal, _0) == 0, layout_QTuple_QVal__0);
static_assert(sizeof(struct QTuple_QVal) == 8, layout_QTuple_QVal_size);
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QVal_end_QVal_DEFINED
struct QTuple_QTuple_QVal_end_QVal {
    QTuple_QVal * _0;
    QVal _1;
};
static_assert(offsetof(struct QTuple_QTuple_QVal_end_QVal, _0) == 0, layout_QTuple_QTuple_QVal_end_QVal__0);
static_assert(offsetof(struct QTuple_QTuple_QVal_end_QVal, _1) == 8, layout_QTuple_QTuple_QVal_end_QVal__1);
static_assert(sizeof(struct QTuple_QTuple_QVal_end_QVal) == 16, layout_QTuple_QTuple_QVal_end_QVal_size);
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_DEFINED
#define QUEST_TYPE_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_DEFINED
struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f {
    Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal * _0;
    Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal * _1;
    Rec0_QTuple_QVal_String_QVal_Bool_QVal_QVal_QVal_QVal_QVal_QVal * _2;
    QVal _3;
    QVal _4;
    QVal _5;
    QVal _6;
    QVal _7;
    QVal _8;
    QVal _9;
    QString * _10;
    QVal _11;
    QVal _12;
    QVal _13;
    QTuple_QTuple_QVal_end_QVal * _14;
    QVal _15;
    QVal _16;
    QVal _17;
    QBoolSlot _18;
    QBoolSlot _19;
    QBoolSlot _20;
    QBoolSlot _21;
    QVal _22;
};
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _0) == 0, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__0);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _1) == 8, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__1);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _2) == 16, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__2);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _3) == 24, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__3);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _4) == 32, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__4);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _5) == 40, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__5);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _6) == 48, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__6);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _7) == 56, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__7);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _8) == 64, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__8);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _9) == 72, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__9);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _10) == 80, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__10);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _11) == 88, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__11);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _12) == 96, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__12);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _13) == 104, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__13);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _14) == 112, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__14);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _15) == 120, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__15);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _16) == 128, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__16);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _17) == 136, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__17);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _18) == 144, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__18);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _19) == 152, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__19);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _20) == 160, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__20);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _21) == 168, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__21);
static_assert(offsetof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f, _22) == 176, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f__22);
static_assert(sizeof(struct Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f) == 184, layout_Rec0_QTuple_Rec0_QTuple_QVal__21f904f68978337f_size);
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QClosure_QClosure_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QClosure_QClosure_DEFINED
struct Rec0_QTuple_QClosure_QClosure {
    QClosure * _0;
    QClosure * _1;
};
static_assert(offsetof(struct Rec0_QTuple_QClosure_QClosure, _0) == 0, layout_Rec0_QTuple_QClosure_QClosure__0);
static_assert(offsetof(struct Rec0_QTuple_QClosure_QClosure, _1) == 8, layout_Rec0_QTuple_QClosure_QClosure__1);
static_assert(sizeof(struct Rec0_QTuple_QClosure_QClosure) == 16, layout_Rec0_QTuple_QClosure_QClosure_size);
#endif
typedef Rec0_QTuple_QClosure_QClosure * quest_sig_questlang__modules__Stdlib_registry;
typedef void (*quest_sig_questlang__modules__Stdlib_install)(void);
typedef QArray * quest_sig_questlang__modules__Stdlib_standardModules;
#ifdef __cplusplus
}
#endif
#endif
