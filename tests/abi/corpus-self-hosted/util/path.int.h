#ifndef QUEST_INTF_UTIL__PATH_H
#define QUEST_INTF_UTIL__PATH_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/vector.int.h"
#include "util/maybe.int.h"
#include "os/filestats.int.h"
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
typedef QVal quest_type_util__Path_T;
typedef const QException * quest_sig_util__Path_error;
typedef QChar quest_sig_util__Path_separator;
typedef QString * quest_sig_util__Path_separatorString;
typedef QString * (*quest_sig_util__Path_dirName)(QString * path);
typedef QString * (*quest_sig_util__Path_baseName)(QString * path);
typedef QString * (*quest_sig_util__Path_extension)(QString * path);
typedef QString * (*quest_sig_util__Path_stem)(QString * path);
typedef QVal (*quest_sig_util__Path_parts)(QString * path);
typedef QString * (*quest_sig_util__Path_join)(QString * part1, QString * part2);
typedef QString * (*quest_sig_util__Path_joinVector)(QVal items);
typedef QString * (*quest_sig_util__Path_joinArray)(QArray * items);
typedef QString * (*quest_sig_util__Path_withExtension)(QString * path, QString * newExt);
typedef QBool (*quest_sig_util__Path_isAbsolute)(QString * path);
typedef QBool (*quest_sig_util__Path_isRelative)(QString * path);
typedef QBool (*quest_sig_util__Path_hasExtension)(QString * path);
typedef QString * (*quest_sig_util__Path_normalize)(QString * path);
typedef QString * (*quest_sig_util__Path_relativeTo)(QString * path, QString * base);
typedef QString * (*quest_sig_util__Path_resolve)(QString * path);
typedef QVal (*quest_sig_util__Path_fromString)(QString * s);
typedef QString * (*quest_sig_util__Path_toString)(QVal p);
typedef QBool (*quest_sig_util__Path_equal)(QVal a, QVal b);
typedef uint64_t (*quest_sig_util__Path_hash)(QVal p);
typedef QString * (*quest_sig_util__Path_name)(QVal p);
typedef QVal (*quest_sig_util__Path_parent)(QVal p);
typedef QString * (*quest_sig_util__Path_suffix)(QVal p);
typedef QString * (*quest_sig_util__Path_pathStem)(QVal p);
typedef QVal (*quest_sig_util__Path_withSuffix)(QVal p, QString * newSuffix);
typedef QVal (*quest_sig_util__Path_pathParts)(QVal p);
typedef QVal (*quest_sig_util__Path_child)(QVal p, QString * s);
typedef QVal (*quest_sig_util__Path_joinPaths)(QVal p, QVal q);
typedef QBool (*quest_sig_util__Path_pathIsAbsolute)(QVal p);
typedef QVal (*quest_sig_util__Path_normalizePath)(QVal p);
typedef QVal (*quest_sig_util__Path_pathRelativeTo)(QVal p, QVal base);
typedef QVal (*quest_sig_util__Path_resolvePath)(QVal p);
typedef QBool (*quest_sig_util__Path_exists)(QVal p);
typedef QBool (*quest_sig_util__Path_isFile)(QVal p);
typedef QBool (*quest_sig_util__Path_isDir)(QVal p);
typedef QTuple_Int_Int_QOption_d_dd7288ab83960a95 * (*quest_sig_util__Path_stat)(QVal p);
typedef QVal (*quest_sig_util__Path_find)(QVal p);
typedef QArray * (*quest_sig_util__Path_iterDir)(QVal p);
typedef void (*quest_sig_util__Path_mkdir)(QVal p, QBool parents);
typedef void (*quest_sig_util__Path_unlink)(QVal p);
typedef void (*quest_sig_util__Path_rename)(QVal p, QVal q);
typedef QString * (*quest_sig_util__Path_readText)(QVal p);
typedef void (*quest_sig_util__Path_writeText)(QVal p, QString * text);
#ifdef __cplusplus
}
#endif
#endif
