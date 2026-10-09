#ifndef QUEST_INTF_UTIL__PATH_H
#define QUEST_INTF_UTIL__PATH_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/vector.int.h"
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
#ifdef __cplusplus
}
#endif
#endif
