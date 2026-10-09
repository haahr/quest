#ifndef QUEST_SERIALIZATION_H
#define QUEST_SERIALIZATION_H

#include "quest_runtime.h"

#ifdef __cplusplus
extern "C" {
#endif

void   quest_dynamic_extern(QWriter *wr, const QAuto *d);
QAuto *quest_dynamic_intern(QReader *rd);

#ifdef __cplusplus
}
#endif

#endif /* QUEST_SERIALIZATION_H */
