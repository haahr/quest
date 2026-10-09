#ifndef QUEST_INTF_DYNAMIC_H
#define QUEST_INTF_DYNAMIC_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "reader.int.h"
#include "writer.int.h"
#ifndef QUEST_TYPE_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_TYPEDEF
typedef struct QTuple_QVal QTuple_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_DEFINED
struct QTuple_QVal {
    QVal _0;
};
#endif
typedef QAuto * quest_type_Dynamic_T;
typedef const QException * quest_sig_Dynamic_error;
typedef QAuto * (*quest_sig_Dynamic_new)(const QTypeDescriptor *desc_A, QVal a);
typedef QVal (*quest_sig_Dynamic_be)(const QTypeDescriptor *desc_A, QAuto * d);
typedef QAuto * (*quest_sig_Dynamic_copy)(QAuto * d);
typedef QAuto * (*quest_sig_Dynamic_intern)(QReader * rd);
typedef void (*quest_sig_Dynamic_extern)(QWriter * wr, QAuto * d);
#ifdef __cplusplus
}
#endif
#endif
