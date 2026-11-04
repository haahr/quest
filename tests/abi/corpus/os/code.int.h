#ifndef QUEST_INTF_OS__CODE_H
#define QUEST_INTF_OS__CODE_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "os/value.int.h"
#include "raised.int.h"
#include "util/maybe.int.h"
typedef QVal quest_type_os__Code_Region;
typedef QVal (*quest_sig_os__Code_reserve)(QInt size, QBool executable);
typedef void * (*quest_sig_os__Code_base)(QVal r);
typedef QInt (*quest_sig_os__Code_size)(QVal r);
typedef void (*quest_sig_os__Code_write32)(QVal r, QInt offset, QArray * words);
typedef void (*quest_sig_os__Code_write64)(QVal r, QInt offset, QArray * words);
typedef QVal (*quest_sig_os__Code_symbol)(QString * name);
typedef void * (*quest_sig_os__Code_threadLocalGetter)(void);
typedef QVal (*quest_sig_os__Code_call)(void * entry);
typedef QString * (*quest_sig_os__Code_exceptionName)(QRaised * r);
typedef QString * (*quest_sig_os__Code_raiseSite)(QRaised * r);
typedef QString * (*quest_sig_os__Code_frames)(QRaised * r);
typedef void (*quest_sig_os__Code_addRoots)(void * low, void * high);
typedef void (*quest_sig_os__Code_addFunction)(void * start, void * limit);
typedef void (*quest_sig_os__Code_setArgs)(QArray * args);
#ifdef __cplusplus
}
#endif
#endif
