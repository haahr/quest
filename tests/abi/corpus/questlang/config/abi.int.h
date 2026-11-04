#ifndef QUEST_INTF_QUESTLANG__CONFIG__ABI_H
#define QUEST_INTF_QUESTLANG__CONFIG__ABI_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "util/maybe.int.h"
typedef QInt quest_sig_questlang__config__Abi_abiVersion;
typedef QString * quest_sig_questlang__config__Abi_producer;
typedef QString * quest_sig_questlang__config__Abi_headerStamp;
typedef QVal (*quest_sig_questlang__config__Abi_recordedAbi)(QString * artifact);
typedef QBool (*quest_sig_questlang__config__Abi_hasCurrentAbi)(QString * artifact);
typedef QBool (*quest_sig_questlang__config__Abi_builtFrom)(QString * artifact, QString * source);
typedef QString * (*quest_sig_questlang__config__Abi_incompatibleArtifactMessage)(QString * artifact);
#ifdef __cplusplus
}
#endif
#endif
