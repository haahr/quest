#ifndef QUEST_INTF_WRITER_H
#define QUEST_INTF_WRITER_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_Writer_T;
typedef const QException * quest_sig_Writer_error;
typedef QVal quest_sig_Writer_output;
typedef QVal quest_sig_Writer_err;
typedef QVal (*quest_sig_Writer_file)(QString * name);
typedef void (*quest_sig_Writer_putString)(QVal writer, QString * string);
typedef void (*quest_sig_Writer_putChar)(QVal writer, QChar q_char);
typedef void (*quest_sig_Writer_putSubString)(QVal writer, QString * string, QInt start, QInt size);
typedef void (*quest_sig_Writer_flush)(QVal writer);
typedef void (*quest_sig_Writer_close)(QVal writer);
#ifdef __cplusplus
}
#endif
#endif
