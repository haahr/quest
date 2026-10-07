#ifndef QUEST_INTF_LOCATION_H
#define QUEST_INTF_LOCATION_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "collections/vector.h"
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_Int_Int_TYPEDEF
typedef struct QTuple_Int_Int_Int QTuple_Int_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_Int_Int_QTuple_Int_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_Int_Int_Int_QTuple_Int_Int_Int_TYPEDEF
typedef struct QTuple_QTuple_Int_Int_Int_QTuple_Int_Int_Int QTuple_QTuple_Int_Int_Int_QTuple_Int_Int_Int;
#endif
#ifndef QUEST_TYPE_QTuple_Int_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_Int_Int_DEFINED
struct QTuple_Int_Int_Int {
    QInt _0;
    QInt _1;
    QInt _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_Int_Int_Int_QTuple_Int_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_QTuple_Int_Int_Int_QTuple_Int_Int_Int_DEFINED
struct QTuple_QTuple_Int_Int_Int_QTuple_Int_Int_Int {
    QTuple_Int_Int_Int * _0;
    QTuple_Int_Int_Int * _1;
};
#endif
typedef QTuple_Int_Int_Int * quest_type_Location_Pos;
typedef QTuple_String_Int_Int * quest_type_Location_Span;
typedef QVal quest_type_Location_SourceMap;
typedef QVal (*quest_sig_Location_newSourceMap)(QString * file, QString * text);
typedef QTuple_String_Int_Int * (*quest_sig_Location_span)(QString * file, QInt startOffset, QInt endOffset);
typedef QTuple_String_Int_Int * (*quest_sig_Location_pointSpan)(QString * file, QInt offset);
typedef QString * (*quest_sig_Location_file)(QVal sm);
typedef QString * (*quest_sig_Location_text)(QVal sm);
typedef QInt (*quest_sig_Location_lineCount)(QVal sm);
typedef QTuple_Int_Int_Int * (*quest_sig_Location_locate)(QVal sm, QInt offset);
typedef QTuple_QTuple_Int_Int_Int_QTuple_Int_Int_Int * (*quest_sig_Location_locateSpan)(QVal sm, QTuple_String_Int_Int * sp);
typedef QString * (*quest_sig_Location_getLine)(QVal sm, QInt lineNum);
typedef QString * (*quest_sig_Location_extractSnippet)(QVal sm, QTuple_String_Int_Int * sp);
#ifdef __cplusplus
}
#endif
#endif
