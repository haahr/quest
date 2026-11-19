#ifndef QUEST_INTF_OS__FILES_H
#define QUEST_INTF_OS__FILES_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/vector.int.h"
#include "os/filestats.int.h"
#ifndef QUEST_TYPE_QOption_crossDevice_exis_1b45892660c4f20b_TYPEDEF
#define QUEST_TYPE_QOption_crossDevice_exis_1b45892660c4f20b_TYPEDEF
typedef struct QOption_crossDevice_exis_1b45892660c4f20b QOption_crossDevice_exis_1b45892660c4f20b;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QOp_b7d9d0600229f192_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_QOp_b7d9d0600229f192_TYPEDEF
typedef struct QTuple_String_String_QOp_b7d9d0600229f192 QTuple_String_String_QOp_b7d9d0600229f192;
#endif
#ifndef QUEST_TYPE_QOption_directory_file_other_symlink_TYPEDEF
#define QUEST_TYPE_QOption_directory_file_other_symlink_TYPEDEF
typedef struct QOption_directory_file_other_symlink QOption_directory_file_other_symlink;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_QOption_d_dd7288ab83960a95_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_QOption_d_dd7288ab83960a95_TYPEDEF
typedef struct QTuple_Int_Int_QOption_d_dd7288ab83960a95 QTuple_Int_Int_QOption_d_dd7288ab83960a95;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_Int_Int_QOption_d_dd7288ab83960a95_end_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_Int_Int_QOption_d_dd7288ab83960a95_end_Int_TYPEDEF
typedef struct QTuple_String_QTuple_Int_Int_QOption_d_dd7288ab83960a95_end_Int QTuple_String_QTuple_Int_Int_QOption_d_dd7288ab83960a95_end_Int;
#endif
#ifndef QUEST_TYPE_QOption_crossDevice_exis_1b45892660c4f20b_DEFINED
#define QUEST_TYPE_QOption_crossDevice_exis_1b45892660c4f20b_DEFINED
struct QOption_crossDevice_exis_1b45892660c4f20b {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QOp_b7d9d0600229f192_DEFINED
#define QUEST_TYPE_QTuple_String_String_QOp_b7d9d0600229f192_DEFINED
struct QTuple_String_String_QOp_b7d9d0600229f192 {
    QString * _0;
    QString * _1;
    QOption_crossDevice_exis_1b45892660c4f20b * _2;
    QString * _3;
};
#endif
#ifndef QUEST_TYPE_QOption_directory_file_other_symlink_DEFINED
#define QUEST_TYPE_QOption_directory_file_other_symlink_DEFINED
struct QOption_directory_file_other_symlink {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_QOption_d_dd7288ab83960a95_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_QOption_d_dd7288ab83960a95_DEFINED
struct QTuple_Int_Int_QOption_d_dd7288ab83960a95 {
    QInt _0;
    QInt _1;
    QOption_directory_file_other_symlink * _2;
    QReal _3;
    QReal _4;
    QReal _5;
    QInt _6;
    QInt _7;
    QInt _8;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_Int_Int_QOption_d_dd7288ab83960a95_end_Int_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_Int_Int_QOption_d_dd7288ab83960a95_end_Int_DEFINED
struct QTuple_String_QTuple_Int_Int_QOption_d_dd7288ab83960a95_end_Int {
    QString * _0;
    QTuple_Int_Int_QOption_d_dd7288ab83960a95 * _1;
    QInt _2;
};
#endif
typedef QOption_crossDevice_exis_1b45892660c4f20b * quest_type_os__Files_Code;
typedef QTuple_String_String_QOp_b7d9d0600229f192 * quest_type_os__Files_Failure;
typedef QTuple_String_QTuple_Int_Int_QOption_d_dd7288ab83960a95_end_Int * quest_type_os__Files_Entry;
typedef const QException * quest_sig_os__Files_error;
typedef void (*quest_sig_os__Files_remove)(QString * path);
typedef void (*quest_sig_os__Files_removeDirectory)(QString * path);
typedef void (*quest_sig_os__Files_rename)(QString * from, QString * to);
typedef void (*quest_sig_os__Files_makeDirectory)(QString * path, QInt mode);
typedef void (*quest_sig_os__Files_createNew)(QString * path, QInt mode);
typedef QVal (*quest_sig_os__Files_list)(QString * path);
typedef void (*quest_sig_os__Files_symlink)(QString * target, QString * path);
typedef QString * (*quest_sig_os__Files_readLink)(QString * path);
typedef void (*quest_sig_os__Files_setMode)(QString * path, QInt mode);
typedef void (*quest_sig_os__Files_setTimes)(QString * path, QInt accessNs, QInt modifiedNs);
typedef QString * (*quest_sig_os__Files_realPath)(QString * path);
typedef void (*quest_sig_os__Files_makeDirectories)(QString * path);
typedef void (*quest_sig_os__Files_copy)(QString * from, QString * to);
typedef void (*quest_sig_os__Files_copyTree)(QString * from, QString * to);
typedef void (*quest_sig_os__Files_removeTree)(QString * path);
typedef void (*quest_sig_os__Files_move)(QString * from, QString * to);
typedef void (*quest_sig_os__Files_walk)(QString * root, QClosure * visit);
typedef QVal (*quest_sig_os__Files_allFiles)(QString * root);
typedef QVal (*quest_sig_os__Files_glob)(QString * pattern);
typedef QVal (*quest_sig_os__Files_globIn)(QString * root, QString * pattern);
typedef QString * (*quest_sig_os__Files_tempDirectory)(void);
typedef QString * (*quest_sig_os__Files_makeTempDirectory)(QString * prefix);
typedef QString * (*quest_sig_os__Files_makeTempFile)(QString * prefix, QString * suffix);
typedef QVal (*quest_sig_os__Files_withTempDirectory)(const QTypeDescriptor *desc_A, QString * prefix, QClosure * action);
#ifdef __cplusplus
}
#endif
#endif
