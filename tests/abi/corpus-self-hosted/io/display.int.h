#ifndef QUEST_INTF_IO__DISPLAY_H
#define QUEST_INTF_IO__DISPLAY_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_DEFINED
struct QTuple_String_String {
    QString * _0;
    QString * _1;
};
static_assert(offsetof(struct QTuple_String_String, _0) == 0, layout_QTuple_String_String__0);
static_assert(offsetof(struct QTuple_String_String, _1) == 8, layout_QTuple_String_String__1);
static_assert(sizeof(struct QTuple_String_String) == 16, layout_QTuple_String_String_size);
#endif
typedef QTuple_String_String * quest_type_io__Display_Item;
typedef QBool (*quest_sig_io__Display_inKernel)(void);
typedef void (*quest_sig_io__Display_bundle)(QArray * items);
typedef void (*quest_sig_io__Display_html)(QString * text);
typedef void (*quest_sig_io__Display_markdown)(QString * text);
typedef void (*quest_sig_io__Display_svg)(QString * text);
typedef void (*quest_sig_io__Display_png)(QString * bytes);
#ifdef __cplusplus
}
#endif
#endif
