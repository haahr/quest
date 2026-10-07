#ifndef QUEST_INTF_CONV_H
#define QUEST_INTF_CONV_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QString * (*quest_sig_Conv_okay)(void);
typedef QString * (*quest_sig_Conv_bool)(QBool b);
typedef QString * (*quest_sig_Conv_int)(QInt n);
typedef QString * (*quest_sig_Conv_real)(QReal r);
typedef QString * (*quest_sig_Conv_char)(QChar c);
typedef QString * (*quest_sig_Conv_string)(QString * s);
#ifdef __cplusplus
}
#endif
#endif
