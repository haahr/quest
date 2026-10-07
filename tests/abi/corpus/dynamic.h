#ifndef QUEST_INTF_DYNAMIC_H
#define QUEST_INTF_DYNAMIC_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "reader.h"
#include "writer.h"
typedef QVal quest_type_Dynamic_T;
typedef const QException * quest_sig_Dynamic_error;
typedef QVal (*quest_sig_Dynamic_new)(const QTypeDescriptor *desc_A, QVal a);
typedef QVal (*quest_sig_Dynamic_be)(const QTypeDescriptor *desc_A, QVal d);
typedef QVal (*quest_sig_Dynamic_copy)(QVal d);
typedef QVal (*quest_sig_Dynamic_intern)(QReader * rd);
typedef void (*quest_sig_Dynamic_extern)(QWriter * wr, QVal d);
#ifdef __cplusplus
}
#endif
#endif
