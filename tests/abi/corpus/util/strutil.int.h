#ifndef QUEST_INTF_UTIL__STRUTIL_H
#define QUEST_INTF_UTIL__STRUTIL_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
#include "collections/vector.int.h"
typedef const QException * quest_sig_util__Strutil_error;
typedef QVal (*quest_sig_util__Strutil_split)(QString * s, QString * delim);
typedef QVal (*quest_sig_util__Strutil_splitlines)(QString * s);
typedef QString * (*quest_sig_util__Strutil_join)(QString * delim, QVal items);
typedef QString * (*quest_sig_util__Strutil_joinArray)(QString * delim, QArray * items);
typedef QBool (*quest_sig_util__Strutil_startsWith)(QString * s, QString * prefix);
typedef QBool (*quest_sig_util__Strutil_endsWith)(QString * s, QString * suffix);
typedef QInt (*quest_sig_util__Strutil_find)(QString * s, QString * sub);
typedef QInt (*quest_sig_util__Strutil_findFrom)(QString * s, QString * sub, QInt start);
typedef QInt (*quest_sig_util__Strutil_rfind)(QString * s, QString * sub);
typedef QBool (*quest_sig_util__Strutil_contains)(QString * s, QString * sub);
typedef QString * (*quest_sig_util__Strutil_strip)(QString * s);
typedef QString * (*quest_sig_util__Strutil_stripLeading)(QString * s);
typedef QString * (*quest_sig_util__Strutil_stripTrailing)(QString * s);
typedef QString * (*quest_sig_util__Strutil_replace)(QString * s, QString * oldSub, QString * newSub);
typedef QString * (*quest_sig_util__Strutil_escapeC)(QString * s);
typedef QString * (*quest_sig_util__Strutil_unescapeC)(QString * s);
typedef QBool (*quest_sig_util__Strutil_isDigit)(QChar c);
typedef QBool (*quest_sig_util__Strutil_isAlpha)(QChar c);
typedef QBool (*quest_sig_util__Strutil_isAlnum)(QChar c);
typedef QBool (*quest_sig_util__Strutil_isSpace)(QChar c);
typedef QInt (*quest_sig_util__Strutil_toInt)(QString * s);
typedef QVal (*quest_sig_util__Strutil_tryToInt)(QString * s);
typedef QInt (*quest_sig_util__Strutil_toIntBase)(QString * s, QInt base);
typedef QVal (*quest_sig_util__Strutil_tryToIntBase)(QString * s, QInt base);
typedef uint64_t (*quest_sig_util__Strutil_toWord)(QString * s);
typedef QVal (*quest_sig_util__Strutil_tryToWord)(QString * s);
typedef uint64_t (*quest_sig_util__Strutil_toWordBase)(QString * s, QInt base);
typedef QVal (*quest_sig_util__Strutil_tryToWordBase)(QString * s, QInt base);
typedef QString * (*quest_sig_util__Strutil_formatWord)(uint64_t w, QInt base);
typedef QString * (*quest_sig_util__Strutil_wordToString)(uint64_t w);
typedef QReal (*quest_sig_util__Strutil_toReal)(QString * s);
typedef QVal (*quest_sig_util__Strutil_tryToReal)(QString * s);
typedef QBool (*quest_sig_util__Strutil_toBool)(QString * s);
typedef QVal (*quest_sig_util__Strutil_tryToBool)(QString * s);
#ifdef __cplusplus
}
#endif
#endif
