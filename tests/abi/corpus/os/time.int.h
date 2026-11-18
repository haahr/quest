#ifndef QUEST_INTF_OS__TIME_H
#define QUEST_INTF_OS__TIME_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QInt (*quest_sig_os__Time_nowInNanoseconds)(void);
typedef QInt (*quest_sig_os__Time_ticks)(void);
typedef QInt (*quest_sig_os__Time_cpuTimeInNanoseconds)(void);
typedef void (*quest_sig_os__Time_sleepNanoseconds)(QInt nanoseconds);
typedef QInt (*quest_sig_os__Time_localOffsetInSeconds)(QInt secondsSinceEpoch);
#ifdef __cplusplus
}
#endif
#endif
