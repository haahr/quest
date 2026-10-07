#ifndef QUEST_INTF_STRUTIL_H
#define QUEST_INTF_STRUTIL_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.h"
#include "collections/vector.h"
typedef const QException * quest_sig_Strutil_error;
typedef QVal (*quest_sig_Strutil_split)(QString * s, QString * delim);
typedef QVal (*quest_sig_Strutil_splitlines)(QString * s);
typedef QString * (*quest_sig_Strutil_join)(QString * delim, QVal items);
typedef QString * (*quest_sig_Strutil_joinArray)(QString * delim, QArray * items);
typedef QBool (*quest_sig_Strutil_startsWith)(QString * s, QString * prefix);
typedef QBool (*quest_sig_Strutil_endsWith)(QString * s, QString * suffix);
typedef QInt (*quest_sig_Strutil_find)(QString * s, QString * sub);
typedef QInt (*quest_sig_Strutil_findFrom)(QString * s, QString * sub, QInt start);
typedef QInt (*quest_sig_Strutil_rfind)(QString * s, QString * sub);
typedef QBool (*quest_sig_Strutil_contains)(QString * s, QString * sub);
typedef QString * (*quest_sig_Strutil_strip)(QString * s);
typedef QString * (*quest_sig_Strutil_stripLeading)(QString * s);
typedef QString * (*quest_sig_Strutil_stripTrailing)(QString * s);
typedef QString * (*quest_sig_Strutil_replace)(QString * s, QString * oldSub, QString * newSub);
typedef QString * (*quest_sig_Strutil_escapeC)(QString * s);
typedef QString * (*quest_sig_Strutil_unescapeC)(QString * s);
typedef QBool (*quest_sig_Strutil_isDigit)(QChar c);
typedef QBool (*quest_sig_Strutil_isAlpha)(QChar c);
typedef QBool (*quest_sig_Strutil_isAlnum)(QChar c);
typedef QBool (*quest_sig_Strutil_isSpace)(QChar c);
typedef QInt (*quest_sig_Strutil_toInt)(QString * s);
typedef QVal (*quest_sig_Strutil_tryToInt)(QString * s);
typedef QInt (*quest_sig_Strutil_toIntBase)(QString * s, QInt base);
typedef QVal (*quest_sig_Strutil_tryToIntBase)(QString * s, QInt base);
typedef uint64_t (*quest_sig_Strutil_toWord)(QString * s);
typedef QVal (*quest_sig_Strutil_tryToWord)(QString * s);
typedef uint64_t (*quest_sig_Strutil_toWordBase)(QString * s, QInt base);
typedef QVal (*quest_sig_Strutil_tryToWordBase)(QString * s, QInt base);
typedef QString * (*quest_sig_Strutil_formatWord)(uint64_t w, QInt base);
typedef QString * (*quest_sig_Strutil_wordToString)(uint64_t w);
typedef QReal (*quest_sig_Strutil_toReal)(QString * s);
typedef QVal (*quest_sig_Strutil_tryToReal)(QString * s);
typedef QBool (*quest_sig_Strutil_toBool)(QString * s);
typedef QVal (*quest_sig_Strutil_tryToBool)(QString * s);
#ifdef __cplusplus
}
#endif
#endif
