#ifndef QUEST_INTF_QUESTLANG__JIT__DEBUGOBJECT_H
#define QUEST_INTF_QUESTLANG__JIT__DEBUGOBJECT_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/codegen/arm64/encode.int.h"
#ifndef QUEST_TYPE_QOption_relocAbsolute64__44c66b1db190bdc3_TYPEDEF
#define QUEST_TYPE_QOption_relocAbsolute64__44c66b1db190bdc3_TYPEDEF
typedef struct QOption_relocAbsolute64__44c66b1db190bdc3 QOption_relocAbsolute64__44c66b1db190bdc3;
#endif
#ifndef QUEST_TYPE_QTuple_Int_QOption_reloc_9c145bed7730d35a_TYPEDEF
#define QUEST_TYPE_QTuple_Int_QOption_reloc_9c145bed7730d35a_TYPEDEF
typedef struct QTuple_Int_QOption_reloc_9c145bed7730d35a QTuple_Int_QOption_reloc_9c145bed7730d35a;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_Bool_TYPEDEF
typedef struct QTuple_String_Int_Int_Bool QTuple_String_Int_Int_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_Int_Int_TYPEDEF
typedef struct QTuple_Int_Int_Int_Int QTuple_Int_Int_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_QArray_Int_QArray_f0593bc63ece5e04_TYPEDEF
#define QUEST_TYPE_QTuple_QArray_Int_QArray_f0593bc63ece5e04_TYPEDEF
typedef struct QTuple_QArray_Int_QArray_f0593bc63ece5e04 QTuple_QArray_Int_QArray_f0593bc63ece5e04;
#endif
#ifndef QUEST_TYPE_QOption_relocAbsolute64__44c66b1db190bdc3_DEFINED
#define QUEST_TYPE_QOption_relocAbsolute64__44c66b1db190bdc3_DEFINED
struct QOption_relocAbsolute64__44c66b1db190bdc3 {
    int64_t tag;
};
static_assert(sizeof(struct QOption_relocAbsolute64__44c66b1db190bdc3) == 8, layout_QOption_relocAbsolute64__44c66b1db190bdc3_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_QOption_reloc_9c145bed7730d35a_DEFINED
#define QUEST_TYPE_QTuple_Int_QOption_reloc_9c145bed7730d35a_DEFINED
struct QTuple_Int_QOption_reloc_9c145bed7730d35a {
    QInt _0;
    QOption_relocAbsolute64__44c66b1db190bdc3 * _1;
    QString * _2;
    QInt _3;
};
static_assert(offsetof(struct QTuple_Int_QOption_reloc_9c145bed7730d35a, _0) == 0, layout_QTuple_Int_QOption_reloc_9c145bed7730d35a__0);
static_assert(offsetof(struct QTuple_Int_QOption_reloc_9c145bed7730d35a, _1) == 8, layout_QTuple_Int_QOption_reloc_9c145bed7730d35a__1);
static_assert(offsetof(struct QTuple_Int_QOption_reloc_9c145bed7730d35a, _2) == 16, layout_QTuple_Int_QOption_reloc_9c145bed7730d35a__2);
static_assert(offsetof(struct QTuple_Int_QOption_reloc_9c145bed7730d35a, _3) == 24, layout_QTuple_Int_QOption_reloc_9c145bed7730d35a__3);
static_assert(sizeof(struct QTuple_Int_QOption_reloc_9c145bed7730d35a) == 32, layout_QTuple_Int_QOption_reloc_9c145bed7730d35a_size);
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_Bool_DEFINED
struct QTuple_String_Int_Int_Bool {
    QString * _0;
    QInt _1;
    QInt _2;
    QBoolSlot _3;
};
static_assert(offsetof(struct QTuple_String_Int_Int_Bool, _0) == 0, layout_QTuple_String_Int_Int_Bool__0);
static_assert(offsetof(struct QTuple_String_Int_Int_Bool, _1) == 8, layout_QTuple_String_Int_Int_Bool__1);
static_assert(offsetof(struct QTuple_String_Int_Int_Bool, _2) == 16, layout_QTuple_String_Int_Int_Bool__2);
static_assert(offsetof(struct QTuple_String_Int_Int_Bool, _3) == 24, layout_QTuple_String_Int_Int_Bool__3);
static_assert(sizeof(struct QTuple_String_Int_Int_Bool) == 32, layout_QTuple_String_Int_Int_Bool_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_Int_Int_DEFINED
struct QTuple_Int_Int_Int_Int {
    QInt _0;
    QInt _1;
    QInt _2;
    QInt _3;
};
static_assert(offsetof(struct QTuple_Int_Int_Int_Int, _0) == 0, layout_QTuple_Int_Int_Int_Int__0);
static_assert(offsetof(struct QTuple_Int_Int_Int_Int, _1) == 8, layout_QTuple_Int_Int_Int_Int__1);
static_assert(offsetof(struct QTuple_Int_Int_Int_Int, _2) == 16, layout_QTuple_Int_Int_Int_Int__2);
static_assert(offsetof(struct QTuple_Int_Int_Int_Int, _3) == 24, layout_QTuple_Int_Int_Int_Int__3);
static_assert(sizeof(struct QTuple_Int_Int_Int_Int) == 32, layout_QTuple_Int_Int_Int_Int_size);
#endif
#ifndef QUEST_TYPE_QTuple_QArray_Int_QArray_f0593bc63ece5e04_DEFINED
#define QUEST_TYPE_QTuple_QArray_Int_QArray_f0593bc63ece5e04_DEFINED
struct QTuple_QArray_Int_QArray_f0593bc63ece5e04 {
    QArray * _0;
    QArray * _1;
    QArray * _2;
    QArray * _3;
    QArray * _4;
    QArray * _5;
    QArray * _6;
    QArray * _7;
};
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _0) == 0, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__0);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _1) == 8, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__1);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _2) == 16, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__2);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _3) == 24, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__3);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _4) == 32, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__4);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _5) == 40, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__5);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _6) == 48, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__6);
static_assert(offsetof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04, _7) == 56, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04__7);
static_assert(sizeof(struct QTuple_QArray_Int_QArray_f0593bc63ece5e04) == 64, layout_QTuple_QArray_Int_QArray_f0593bc63ece5e04_size);
#endif
typedef QString * (*quest_sig_questlang__jit__DebugObject_object)(QTuple_QArray_Int_QArray_f0593bc63ece5e04 * e, QInt codeAddress, QArray * files);
#ifdef __cplusplus
}
#endif
#endif
