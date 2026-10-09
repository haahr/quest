#ifndef QUEST_INTF_ASCII_H
#define QUEST_INTF_ASCII_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef const QException * quest_sig_Ascii_error;
typedef QChar (*quest_sig_Ascii_char)(QInt n);
typedef QInt (*quest_sig_Ascii_val)(QChar c);
#ifdef __cplusplus
}
#endif
#endif
