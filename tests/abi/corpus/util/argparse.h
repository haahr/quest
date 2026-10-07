#ifndef QUEST_INTF_ARGPARSE_H
#define QUEST_INTF_ARGPARSE_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.h"
#include "collections/vector.h"
#include "writer.h"
typedef QVal quest_type_ArgParse_Parser;
typedef QVal quest_type_ArgParse_Results;
typedef const QException * quest_sig_ArgParse_error;
typedef QVal (*quest_sig_ArgParse_new)(QString * prog, QString * description);
typedef void (*quest_sig_ArgParse_addFlag)(QVal p, QString * name, QString * flags, QString * help);
typedef void (*quest_sig_ArgParse_addString)(QVal p, QString * name, QString * flags, QString * defaultVal, QString * help);
typedef void (*quest_sig_ArgParse_addChoice)(QVal p, QString * name, QString * flags, QArray * choices, QString * defaultVal, QString * help);
typedef void (*quest_sig_ArgParse_addInt)(QVal p, QString * name, QString * flags, QInt defaultVal, QString * help);
typedef void (*quest_sig_ArgParse_addMulti)(QVal p, QString * name, QString * flags, QString * help);
typedef void (*quest_sig_ArgParse_addPositional)(QVal p, QString * name, QString * help);
typedef QVal (*quest_sig_ArgParse_parse)(QVal p, QArray * args);
typedef QVal (*quest_sig_ArgParse_parseVector)(QVal p, QVal args);
typedef void (*quest_sig_ArgParse_printHelp)(QVal p, QWriter * w);
typedef QString * (*quest_sig_ArgParse_formatHelp)(QVal p);
typedef QBool (*quest_sig_ArgParse_getBool)(QVal r, QString * name);
typedef QVal (*quest_sig_ArgParse_getString)(QVal r, QString * name);
typedef QString * (*quest_sig_ArgParse_getStringOr)(QVal r, QString * name, QString * defaultVal);
typedef QVal (*quest_sig_ArgParse_getInt)(QVal r, QString * name);
typedef QInt (*quest_sig_ArgParse_getIntOr)(QVal r, QString * name, QInt defaultVal);
typedef QVal (*quest_sig_ArgParse_getMulti)(QVal r, QString * name);
typedef QVal (*quest_sig_ArgParse_positionals)(QVal r);
typedef QVal (*quest_sig_ArgParse_targetArgs)(QVal r);
#ifdef __cplusplus
}
#endif
#endif
