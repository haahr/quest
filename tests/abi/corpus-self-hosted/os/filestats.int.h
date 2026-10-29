#ifndef QUEST_INTF_OS__FILESTATS_H
#define QUEST_INTF_OS__FILESTATS_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QOption_directory_file_other_symlink_TYPEDEF
#define QUEST_TYPE_QOption_directory_file_other_symlink_TYPEDEF
typedef struct QOption_directory_file_other_symlink QOption_directory_file_other_symlink;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_QOption_d_dd7288ab83960a95_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_QOption_d_dd7288ab83960a95_TYPEDEF
typedef struct QTuple_Int_Int_QOption_d_dd7288ab83960a95 QTuple_Int_Int_QOption_d_dd7288ab83960a95;
#endif
#ifndef QUEST_TYPE_QOption_directory_file_other_symlink_DEFINED
#define QUEST_TYPE_QOption_directory_file_other_symlink_DEFINED
struct QOption_directory_file_other_symlink {
    int64_t tag;
};
static_assert(sizeof(struct QOption_directory_file_other_symlink) == 8, layout_QOption_directory_file_other_symlink_size);
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_QOption_d_dd7288ab83960a95_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_QOption_d_dd7288ab83960a95_DEFINED
struct QTuple_Int_Int_QOption_d_dd7288ab83960a95 {
    QInt _0;
    QInt _1;
    QOption_directory_file_other_symlink * _2;
    QReal _3;
    QReal _4;
    QReal _5;
    QInt _6;
    QInt _7;
    QInt _8;
};
static_assert(offsetof(struct QTuple_Int_Int_QOption_d_dd7288ab83960a95, _0) == 0, layout_QTuple_Int_Int_QOption_d_dd7288ab83960a95__0);
static_assert(offsetof(struct QTuple_Int_Int_QOption_d_dd7288ab83960a95, _1) == 8, layout_QTuple_Int_Int_QOption_d_dd7288ab83960a95__1);
static_assert(offsetof(struct QTuple_Int_Int_QOption_d_dd7288ab83960a95, _2) == 16, layout_QTuple_Int_Int_QOption_d_dd7288ab83960a95__2);
static_assert(offsetof(struct QTuple_Int_Int_QOption_d_dd7288ab83960a95, _3) == 24, layout_QTuple_Int_Int_QOption_d_dd7288ab83960a95__3);
static_assert(offsetof(struct QTuple_Int_Int_QOption_d_dd7288ab83960a95, _4) == 32, layout_QTuple_Int_Int_QOption_d_dd7288ab83960a95__4);
static_assert(offsetof(struct QTuple_Int_Int_QOption_d_dd7288ab83960a95, _5) == 40, layout_QTuple_Int_Int_QOption_d_dd7288ab83960a95__5);
static_assert(offsetof(struct QTuple_Int_Int_QOption_d_dd7288ab83960a95, _6) == 48, layout_QTuple_Int_Int_QOption_d_dd7288ab83960a95__6);
static_assert(offsetof(struct QTuple_Int_Int_QOption_d_dd7288ab83960a95, _7) == 56, layout_QTuple_Int_Int_QOption_d_dd7288ab83960a95__7);
static_assert(offsetof(struct QTuple_Int_Int_QOption_d_dd7288ab83960a95, _8) == 64, layout_QTuple_Int_Int_QOption_d_dd7288ab83960a95__8);
static_assert(sizeof(struct QTuple_Int_Int_QOption_d_dd7288ab83960a95) == 72, layout_QTuple_Int_Int_QOption_d_dd7288ab83960a95_size);
#endif
typedef QOption_directory_file_other_symlink * quest_type_os__FileStats_Kind;
typedef QTuple_Int_Int_QOption_d_dd7288ab83960a95 * quest_type_os__FileStats_T;
typedef QTuple_Int_Int_QOption_d_dd7288ab83960a95 * (*quest_sig_os__FileStats_stat)(QString * path);
typedef QTuple_Int_Int_QOption_d_dd7288ab83960a95 * (*quest_sig_os__FileStats_lstat)(QString * path);
typedef QVal (*quest_sig_os__FileStats_find)(QString * path);
typedef QVal (*quest_sig_os__FileStats_lfind)(QString * path);
#ifdef __cplusplus
}
#endif
#endif
