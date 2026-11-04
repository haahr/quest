#ifndef QUEST_INTF_IO__READLINE_H
#define QUEST_INTF_IO__READLINE_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef const QException * quest_sig_io__Readline_error;
typedef const QException * quest_sig_io__Readline_endOfInput;
typedef const QException * quest_sig_io__Readline_interrupted;
typedef QBool (*quest_sig_io__Readline_editing)(void);
typedef QString * (*quest_sig_io__Readline_readLine)(QString * prompt);
typedef void (*quest_sig_io__Readline_addHistory)(QString * line);
typedef void (*quest_sig_io__Readline_readHistory)(QString * path);
typedef void (*quest_sig_io__Readline_writeHistory)(QString * path, QInt maxLines);
#ifdef __cplusplus
}
#endif
#endif
