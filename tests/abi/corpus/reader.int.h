#ifndef QUEST_INTF_READER_H
#define QUEST_INTF_READER_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_Reader_T;
typedef const QException * quest_sig_Reader_error;
typedef QVal quest_sig_Reader_input;
typedef QVal (*quest_sig_Reader_file)(QString * name);
typedef QBool (*quest_sig_Reader_more)(QVal reader);
typedef QInt (*quest_sig_Reader_ready)(QVal reader);
typedef QChar (*quest_sig_Reader_getChar)(QVal reader);
typedef QString * (*quest_sig_Reader_getString)(QVal reader, QInt size);
typedef void (*quest_sig_Reader_getSubString)(QVal reader, QString * string, QInt start, QInt size);
typedef void (*quest_sig_Reader_close)(QVal reader);
#ifdef __cplusplus
}
#endif
#endif
