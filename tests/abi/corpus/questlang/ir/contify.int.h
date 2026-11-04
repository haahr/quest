#ifndef QUEST_INTF_QUESTLANG__IR__CONTIFY_H
#define QUEST_INTF_QUESTLANG__IR__CONTIFY_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/ir/nodes.int.h"
#include "questlang/ir/clone.int.h"
#include "collections/hashmap.int.h"
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_58570fe494517756_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_58570fe494517756_TYPEDEF
typedef struct RecGroup0_0_QTuple_Int_Q_58570fe494517756 RecGroup0_0_QTuple_Int_Q_58570fe494517756;
#endif
#ifndef QUEST_TYPE_QTuple_Int_TYPEDEF
#define QUEST_TYPE_QTuple_Int_TYPEDEF
typedef struct QTuple_Int QTuple_Int;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_58570fe494517756_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Int_Q_58570fe494517756_DEFINED
struct RecGroup0_0_QTuple_Int_Q_58570fe494517756 {
    QInt _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_DEFINED
#define QUEST_TYPE_QTuple_Int_DEFINED
struct QTuple_Int {
    QInt _0;
};
#endif
typedef QBool (*quest_sig_questlang__ir__Contify_contify)(QArray * bodies, QVal recursive, QVal pinned, QTuple_Int * labels);
#ifdef __cplusplus
}
#endif
#endif
