#ifndef QUEST_INTF_PATH_H
#define QUEST_INTF_PATH_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/vector.int.h"
typedef const QException * quest_sig_Path_error;
typedef QChar quest_sig_Path_separator;
typedef QString * quest_sig_Path_separatorString;
typedef QString * (*quest_sig_Path_dirName)(QString * path);
typedef QString * (*quest_sig_Path_baseName)(QString * path);
typedef QString * (*quest_sig_Path_extension)(QString * path);
typedef QString * (*quest_sig_Path_stem)(QString * path);
typedef QVal (*quest_sig_Path_parts)(QString * path);
typedef QString * (*quest_sig_Path_join)(QString * part1, QString * part2);
typedef QString * (*quest_sig_Path_joinVector)(QVal items);
typedef QString * (*quest_sig_Path_joinArray)(QArray * items);
typedef QString * (*quest_sig_Path_withExtension)(QString * path, QString * newExt);
typedef QBool (*quest_sig_Path_isAbsolute)(QString * path);
typedef QBool (*quest_sig_Path_isRelative)(QString * path);
typedef QBool (*quest_sig_Path_hasExtension)(QString * path);
typedef QString * (*quest_sig_Path_normalize)(QString * path);
typedef QString * (*quest_sig_Path_relativeTo)(QString * path, QString * base);
typedef QString * (*quest_sig_Path_resolve)(QString * path);
#ifdef __cplusplus
}
#endif
#endif
