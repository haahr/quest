#ifndef QUEST_INTF_ASTPRINT_H
#define QUEST_INTF_ASTPRINT_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
#include "questlang/syntax/ast.int.h"
#include "questlang/common/location.int.h"
#include "collections/vector.int.h"
#include "util/maybe.int.h"
#ifndef QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
#define QUEST_TYPE_QTuple_String_Int_Int_TYPEDEF
typedef struct QTuple_String_Int_Int QTuple_String_Int_Int;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f78412f68a56aaeb_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f78412f68a56aaeb_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_f78412f68a56aaeb RecGroup0_0_QTuple_Self1_f78412f68a56aaeb;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_0b7afcfe34551732_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_0b7afcfe34551732_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_0b7afcfe34551732 RecGroup0_0_QTuple_Strin_0b7afcfe34551732;
#endif
#ifndef QUEST_TYPE_QTuple_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_TYPEDEF
typedef struct QTuple_String QTuple_String;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_TYPEDEF
typedef struct QTuple_String_String QTuple_String_String;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_TYPEDEF
typedef struct QTuple_QVal QTuple_QVal;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__d0fa852652a6db9b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__d0fa852652a6db9b_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__d0fa852652a6db9b RecGroup0_0_QTuple_QVal__d0fa852652a6db9b;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0a658d477875d8df_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0a658d477875d8df_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__0a658d477875d8df RecGroup0_0_QTuple_QVal__0a658d477875d8df;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__af62c66739068e4e_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__af62c66739068e4e_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__af62c66739068e4e RecGroup0_0_QTuple_QVal__af62c66739068e4e;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_9f3ac1db36972d1e_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_9f3ac1db36972d1e_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_9f3ac1db36972d1e RecGroup0_0_QTuple_Strin_9f3ac1db36972d1e;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_30e5ec085cb1f2bd_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_30e5ec085cb1f2bd_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_30e5ec085cb1f2bd RecGroup0_0_QTuple_Self1_30e5ec085cb1f2bd;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_69551751c5e8c6f3_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_69551751c5e8c6f3_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_69551751c5e8c6f3 RecGroup0_0_QTuple_Self1_69551751c5e8c6f3;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_a62f1c255a3353a9_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_a62f1c255a3353a9_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_a62f1c255a3353a9 RecGroup0_0_QTuple_Self1_a62f1c255a3353a9;
#endif
#ifndef QUEST_TYPE_Rec0_QOption_kindType_kindPow_901999f3784c6fa6_TYPEDEF
#define QUEST_TYPE_Rec0_QOption_kindType_kindPow_901999f3784c6fa6_TYPEDEF
typedef struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6 Rec0_QOption_kindType_kindPow_901999f3784c6fa6;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_TYPEDEF
typedef struct Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 Rec0_QTuple_QTuple_String_Int_fd23880d02a42774;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_QVal QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_Int_QVal QTuple_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_4f82c651ca64293d_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_4f82c651ca64293d_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_4f82c651ca64293d QTuple_String_QTuple_QTu_4f82c651ca64293d;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_0189c9ffd21fac99_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_0189c9ffd21fac99_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_0189c9ffd21fac99 QTuple_QTuple_QTuple_Str_0189c9ffd21fac99;
#endif
#ifndef QUEST_TYPE_QOption_kindType_kindPow_72f4e761a8d49456_TYPEDEF
#define QUEST_TYPE_QOption_kindType_kindPow_72f4e761a8d49456_TYPEDEF
typedef struct QOption_kindType_kindPow_72f4e761a8d49456 QOption_kindType_kindPow_72f4e761a8d49456;
#endif
#ifndef QUEST_TYPE_QOption_modeValue_modeVar_modeOut_TYPEDEF
#define QUEST_TYPE_QOption_modeValue_modeVar_modeOut_TYPEDEF
typedef struct QOption_modeValue_modeVar_modeOut QOption_modeValue_modeVar_modeOut;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_e1dfc5ca9f901776_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_e1dfc5ca9f901776_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_e1dfc5ca9f901776 QTuple_String_QTuple_QTu_e1dfc5ca9f901776;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut_TYPEDEF
typedef struct QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool_TYPEDEF
typedef struct QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_TYPEDEF
typedef struct QTuple_String_QVal QTuple_String_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_String_QTuple_QTuple_String_Int_Int_QVal QTuple_String_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_TYPEDEF
#define QUEST_TYPE_QTuple_Int_String_TYPEDEF
typedef struct QTuple_Int_String QTuple_Int_String;
#endif
#ifndef QUEST_TYPE_QTuple_Real_String_TYPEDEF
#define QUEST_TYPE_QTuple_Real_String_TYPEDEF
typedef struct QTuple_Real_String QTuple_Real_String;
#endif
#ifndef QUEST_TYPE_QTuple_Char_String_TYPEDEF
#define QUEST_TYPE_QTuple_Char_String_TYPEDEF
typedef struct QTuple_Char_String QTuple_Char_String;
#endif
#ifndef QUEST_TYPE_QTuple_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_Bool_TYPEDEF
typedef struct QTuple_Bool QTuple_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_TYPEDEF
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_TYPEDEF
typedef struct QTuple_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 QTuple_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_e13dcd862b05019b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_e13dcd862b05019b_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_e13dcd862b05019b RecGroup0_0_QTuple_Self1_e13dcd862b05019b;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_da465bc6f8fa1834_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_da465bc6f8fa1834_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_da465bc6f8fa1834 RecGroup0_0_QTuple_Self1_da465bc6f8fa1834;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_6369bb69b853749f_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_6369bb69b853749f_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_6369bb69b853749f RecGroup0_0_QTuple_Self1_6369bb69b853749f;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_b0d76f1d850c14c9_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_b0d76f1d850c14c9_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_b0d76f1d850c14c9 RecGroup0_0_QTuple_Strin_b0d76f1d850c14c9;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__a4ef24c0786cdd0e_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__a4ef24c0786cdd0e_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__a4ef24c0786cdd0e RecGroup0_0_QTuple_QVal__a4ef24c0786cdd0e;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_d73d1fb15b7349a9_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_d73d1fb15b7349a9_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_d73d1fb15b7349a9 RecGroup0_0_QTuple_Self1_d73d1fb15b7349a9;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_cb87930f68f7f40b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_cb87930f68f7f40b_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_cb87930f68f7f40b RecGroup0_0_QTuple_Self1_cb87930f68f7f40b;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal QTuple_QVal_QVal;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_e0fe8debd0165e7c_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_e0fe8debd0165e7c_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_e0fe8debd0165e7c RecGroup0_0_QTuple_Self1_e0fe8debd0165e7c;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_Rec0_QTuple__8da641d021d6db4f_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_Rec0_QTuple__8da641d021d6db4f_TYPEDEF
typedef struct QTuple_QVal_Rec0_QTuple__8da641d021d6db4f QTuple_QVal_Rec0_QTuple__8da641d021d6db4f;
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTupl_cf02fdb66371a7c8_TYPEDEF
#define QUEST_TYPE_QTuple_String_Rec0_QTupl_cf02fdb66371a7c8_TYPEDEF
typedef struct QTuple_String_Rec0_QTupl_cf02fdb66371a7c8 QTuple_String_Rec0_QTupl_cf02fdb66371a7c8;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__b66a86a880d0092b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__b66a86a880d0092b_TYPEDEF
typedef struct RecGroup0_0_QTuple_QVal__b66a86a880d0092b RecGroup0_0_QTuple_QVal__b66a86a880d0092b;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_954f42bc31718d79_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_954f42bc31718d79_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_954f42bc31718d79 RecGroup0_0_QTuple_Self1_954f42bc31718d79;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_6cd23faa1c142902_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_6cd23faa1c142902_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_6cd23faa1c142902 RecGroup0_0_QTuple_Self1_6cd23faa1c142902;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_e3dc1d68a63409e2_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_e3dc1d68a63409e2_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_e3dc1d68a63409e2 RecGroup0_0_QTuple_Self1_e3dc1d68a63409e2;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_794fbdf64f431250_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_794fbdf64f431250_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_794fbdf64f431250 RecGroup0_0_QTuple_Self1_794fbdf64f431250;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_cf2c6be6e464256b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_cf2c6be6e464256b_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_cf2c6be6e464256b RecGroup0_0_QTuple_Self1_cf2c6be6e464256b;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_404abe7104fb5711_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_404abe7104fb5711_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_404abe7104fb5711 RecGroup0_0_QTuple_Self1_404abe7104fb5711;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_da199b3b9c821353_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_da199b3b9c821353_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_da199b3b9c821353 RecGroup0_0_QTuple_Self1_da199b3b9c821353;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_3d45869c1d124380_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_3d45869c1d124380_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_3d45869c1d124380 RecGroup0_0_QTuple_Self1_3d45869c1d124380;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_37487d5d7ca3009b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_37487d5d7ca3009b_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_37487d5d7ca3009b RecGroup0_0_QTuple_Self1_37487d5d7ca3009b;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_88d1e5ff79aab177_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_88d1e5ff79aab177_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_88d1e5ff79aab177 RecGroup0_0_QTuple_Self1_88d1e5ff79aab177;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_b47089ae3602c280_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_b47089ae3602c280_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_b47089ae3602c280 RecGroup0_0_QTuple_Self1_b47089ae3602c280;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_364a2bd29ad3663b_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_364a2bd29ad3663b_TYPEDEF
typedef struct RecGroup0_0_QTuple_Strin_364a2bd29ad3663b RecGroup0_0_QTuple_Strin_364a2bd29ad3663b;
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTupl_4c221b057835555b_TYPEDEF
#define QUEST_TYPE_QTuple_String_Rec0_QTupl_4c221b057835555b_TYPEDEF
typedef struct QTuple_String_Rec0_QTupl_4c221b057835555b QTuple_String_Rec0_QTupl_4c221b057835555b;
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_TYPEDEF
#define QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_TYPEDEF
typedef struct QTuple_String_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 QTuple_String_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774;
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f51f6d8f6ba413c1_TYPEDEF
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f51f6d8f6ba413c1_TYPEDEF
typedef struct RecGroup0_0_QTuple_Self1_f51f6d8f6ba413c1 RecGroup0_0_QTuple_Self1_f51f6d8f6ba413c1;
#endif
#ifndef QUEST_TYPE_Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_TYPEDEF
#define QUEST_TYPE_Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_TYPEDEF
typedef struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe;
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36_TYPEDEF
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36_TYPEDEF
typedef struct Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_38c3d6c8d388224b_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_38c3d6c8d388224b_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_38c3d6c8d388224b QTuple_QTuple_QTuple_Str_38c3d6c8d388224b;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_3350f431cf92dfc0_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_3350f431cf92dfc0_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_3350f431cf92dfc0 QTuple_QTuple_QTuple_Str_3350f431cf92dfc0;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_71b79add6d91522c_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_71b79add6d91522c_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_71b79add6d91522c QTuple_String_QTuple_QTu_71b79add6d91522c;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_Rec0_QTuple__1729e55676783dca_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_Rec0_QTuple__1729e55676783dca_TYPEDEF
typedef struct QTuple_QVal_Rec0_QTuple__1729e55676783dca QTuple_QVal_Rec0_QTuple__1729e55676783dca;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_String_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_String_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_Int_QVal_String QTuple_QTuple_QTuple_String_Int_Int_QVal_String;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_4e51da671e850c1f_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_4e51da671e850c1f_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_4e51da671e850c1f QTuple_QTuple_QTuple_Str_4e51da671e850c1f;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal_TYPEDEF
typedef struct QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_2200c6a3d5421263_TYPEDEF
#define QUEST_TYPE_QTuple_String_QTuple_QTu_2200c6a3d5421263_TYPEDEF
typedef struct QTuple_String_QTuple_QTu_2200c6a3d5421263 QTuple_String_QTuple_QTu_2200c6a3d5421263;
#endif
#ifndef QUEST_TYPE_QOption_exprInt_QTuple_I_bc1d62c3376e60de_TYPEDEF
#define QUEST_TYPE_QOption_exprInt_QTuple_I_bc1d62c3376e60de_TYPEDEF
typedef struct QOption_exprInt_QTuple_I_bc1d62c3376e60de QOption_exprInt_QTuple_I_bc1d62c3376e60de;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QOption_modeValue_modeVar_modeOut_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_QOption_modeValue_modeVar_modeOut_TYPEDEF
typedef struct QTuple_String_QVal_QOption_modeValue_modeVar_modeOut QTuple_String_QVal_QOption_modeValue_modeVar_modeOut;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QOption_fieldVal_QTuple__168c8db8e15234f1_TYPEDEF
#define QUEST_TYPE_QOption_fieldVal_QTuple__168c8db8e15234f1_TYPEDEF
typedef struct QOption_fieldVal_QTuple__168c8db8e15234f1 QOption_fieldVal_QTuple__168c8db8e15234f1;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_TYPEDEF
typedef struct QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTupl_bd92283f65796da7_TYPEDEF
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTupl_bd92283f65796da7_TYPEDEF
typedef struct QTuple_Rec0_QTuple_QTupl_bd92283f65796da7 QTuple_Rec0_QTuple_QTupl_bd92283f65796da7;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_ca206c534ceb51b5_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_ca206c534ceb51b5_TYPEDEF
typedef struct QTuple_QTuple_QTuple_Str_ca206c534ceb51b5 QTuple_QTuple_QTuple_Str_ca206c534ceb51b5;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_QVal_TYPEDEF
typedef struct QTuple_QTuple_QVal QTuple_QTuple_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_String_QVal_QVal_Bool QTuple_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_QTuple_String_QVal_QVal_Bool QTuple_QTuple_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_String_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_String_String_QVal_QVal_Bool QTuple_String_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_TYPEDEF
typedef struct QTuple_QTuple_String_String_QVal_QVal_Bool QTuple_QTuple_String_String_QVal_QVal_Bool;
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36_TYPEDEF
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36_TYPEDEF
typedef struct QTuple_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 QTuple_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36;
#endif
#ifndef QUEST_TYPE_QOption_phraseImport_QTu_a682fc37f16b1dcd_TYPEDEF
#define QUEST_TYPE_QOption_phraseImport_QTu_a682fc37f16b1dcd_TYPEDEF
typedef struct QOption_phraseImport_QTu_a682fc37f16b1dcd QOption_phraseImport_QTu_a682fc37f16b1dcd;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_95359d63df53c666_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_95359d63df53c666_TYPEDEF
typedef struct QTuple_QTuple_String_Int_95359d63df53c666 QTuple_QTuple_String_Int_95359d63df53c666;
#endif
#ifndef QUEST_TYPE_QTuple_QVal_String_QVal_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QVal_String_QVal_QVal_TYPEDEF
typedef struct QTuple_QVal_String_QVal_QVal QTuple_QVal_String_QVal_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_QTuple_QVal_TYPEDEF
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_QTuple_QVal_TYPEDEF
typedef struct QTuple_QTuple_String_Int_Int_QTuple_QVal QTuple_QTuple_String_Int_Int_QTuple_QVal;
#endif
#ifndef QUEST_TYPE_QTuple_String_Int_Int_DEFINED
#define QUEST_TYPE_QTuple_String_Int_Int_DEFINED
struct QTuple_String_Int_Int {
    QString * _0;
    QInt _1;
    QInt _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f78412f68a56aaeb_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f78412f68a56aaeb_DEFINED
struct RecGroup0_0_QTuple_Self1_f78412f68a56aaeb {
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_0b7afcfe34551732_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_0b7afcfe34551732_DEFINED
struct RecGroup0_0_QTuple_Strin_0b7afcfe34551732 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_DEFINED
#define QUEST_TYPE_QTuple_String_DEFINED
struct QTuple_String {
    QString * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_String_DEFINED
#define QUEST_TYPE_QTuple_String_String_DEFINED
struct QTuple_String_String {
    QString * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_DEFINED
struct QTuple_QVal {
    QVal _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__d0fa852652a6db9b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__d0fa852652a6db9b_DEFINED
struct RecGroup0_0_QTuple_QVal__d0fa852652a6db9b {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__0a658d477875d8df_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__0a658d477875d8df_DEFINED
struct RecGroup0_0_QTuple_QVal__0a658d477875d8df {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__af62c66739068e4e_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__af62c66739068e4e_DEFINED
struct RecGroup0_0_QTuple_QVal__af62c66739068e4e {
    QVal _0;
    QVal _1;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_9f3ac1db36972d1e_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_9f3ac1db36972d1e_DEFINED
struct RecGroup0_0_QTuple_Strin_9f3ac1db36972d1e {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_30e5ec085cb1f2bd_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_30e5ec085cb1f2bd_DEFINED
struct RecGroup0_0_QTuple_Self1_30e5ec085cb1f2bd {
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_69551751c5e8c6f3_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_69551751c5e8c6f3_DEFINED
struct RecGroup0_0_QTuple_Self1_69551751c5e8c6f3 {
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_a62f1c255a3353a9_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_a62f1c255a3353a9_DEFINED
struct RecGroup0_0_QTuple_Self1_a62f1c255a3353a9 {
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
};
#endif
#ifndef QUEST_TYPE_Rec0_QOption_kindType_kindPow_901999f3784c6fa6_DEFINED
#define QUEST_TYPE_Rec0_QOption_kindType_kindPow_901999f3784c6fa6_DEFINED
struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6 {
    int64_t tag;
    union {
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_kindPower_payload {
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
        } kindPower;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_kindAll_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _2;
        } kindAll;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_kindId_payload {
            QString * _0;
        } kindId;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_kindManifest_payload {
            QString * _0;
            QString * _1;
        } kindManifest;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typePath_payload {
            QVal _0;
        } typePath;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeAll_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
        } typeAll;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeTuple_payload {
            QVal _0;
        } typeTuple;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeRecord_payload {
            QVal _0;
        } typeRecord;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeOption_payload {
            QVal _0;
        } typeOption;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeVariant_payload {
            QVal _0;
        } typeVariant;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeAuto_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            QVal _2;
        } typeAuto;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeFun_payload {
            QVal _0;
            QVal _1;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _2;
        } typeFun;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeRec_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _2;
        } typeRec;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeApp_payload {
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
            QVal _1;
        } typeApp;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeInfix_payload {
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
            QString * _1;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _2;
        } typeInfix;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeArray_payload {
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
        } typeArray;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeVar_payload {
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
        } typeVar;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeOut_payload {
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
        } typeOut;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeManifest_payload {
            QString * _0;
            QString * _1;
        } typeManifest;
        struct Rec0_QOption_kindType_kindPow_901999f3784c6fa6_typeExternal_payload {
            QString * _0;
        } typeExternal;
    } u;
};
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_DEFINED
struct Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 {
    QTuple_String_Int_Int * _0;
    Rec0_QOption_kindType_kindPow_901999f3784c6fa6 * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_QTuple_String_Int_Int_QVal {
    QTuple_String_Int_Int * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_QTuple_QTuple_String_Int_Int_QVal {
    QTuple_QTuple_String_Int_Int_QVal * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_4f82c651ca64293d_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_4f82c651ca64293d_DEFINED
struct QTuple_String_QTuple_QTu_4f82c651ca64293d {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal {
    QVal _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal {
    QVal _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal {
    QVal _0;
    QVal _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
struct QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_0189c9ffd21fac99_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_0189c9ffd21fac99_DEFINED
struct QTuple_QTuple_QTuple_Str_0189c9ffd21fac99 {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QString * _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QOption_kindType_kindPow_72f4e761a8d49456_DEFINED
#define QUEST_TYPE_QOption_kindType_kindPow_72f4e761a8d49456_DEFINED
struct QOption_kindType_kindPow_72f4e761a8d49456 {
    int64_t tag;
    union {
        struct QOption_kindType_kindPow_72f4e761a8d49456_kindPower_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } kindPower;
        struct QOption_kindType_kindPow_72f4e761a8d49456_kindAll_payload {
            QString * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } kindAll;
        struct QOption_kindType_kindPow_72f4e761a8d49456_kindId_payload {
            QString * _0;
        } kindId;
        struct QOption_kindType_kindPow_72f4e761a8d49456_kindManifest_payload {
            QString * _0;
            QString * _1;
        } kindManifest;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typePath_payload {
            QVal _0;
        } typePath;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeAll_payload {
            QVal _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } typeAll;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeTuple_payload {
            QVal _0;
        } typeTuple;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeRecord_payload {
            QVal _0;
        } typeRecord;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeOption_payload {
            QVal _0;
        } typeOption;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeVariant_payload {
            QVal _0;
        } typeVariant;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeAuto_payload {
            QVal _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QVal _2;
        } typeAuto;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeFun_payload {
            QVal _0;
            QVal _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } typeFun;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeRec_payload {
            QString * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } typeRec;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeApp_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
        } typeApp;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeInfix_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } typeInfix;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeArray_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } typeArray;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeVar_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } typeVar;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeOut_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } typeOut;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeManifest_payload {
            QString * _0;
            QString * _1;
        } typeManifest;
        struct QOption_kindType_kindPow_72f4e761a8d49456_typeExternal_payload {
            QString * _0;
        } typeExternal;
    } u;
};
#endif
#ifndef QUEST_TYPE_QOption_modeValue_modeVar_modeOut_DEFINED
#define QUEST_TYPE_QOption_modeValue_modeVar_modeOut_DEFINED
struct QOption_modeValue_modeVar_modeOut {
    int64_t tag;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_e1dfc5ca9f901776_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_e1dfc5ca9f901776_DEFINED
struct QTuple_String_QTuple_QTu_e1dfc5ca9f901776 {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QOption_modeValue_modeVar_modeOut * _2;
    QBool _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut_DEFINED
struct QTuple_QVal_QVal_QOption_modeValue_modeVar_modeOut {
    QVal _0;
    QVal _1;
    QOption_modeValue_modeVar_modeOut * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool_DEFINED
struct QTuple_String_QTuple_QTuple_String_Int_Int_QVal_Bool {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QBool _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_DEFINED
struct QTuple_String_QVal {
    QString * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_String_QTuple_QTuple_String_Int_Int_QVal {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Int_String_DEFINED
#define QUEST_TYPE_QTuple_Int_String_DEFINED
struct QTuple_Int_String {
    QInt _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Real_String_DEFINED
#define QUEST_TYPE_QTuple_Real_String_DEFINED
struct QTuple_Real_String {
    QReal _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Char_String_DEFINED
#define QUEST_TYPE_QTuple_Char_String_DEFINED
struct QTuple_Char_String {
    QChar _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_Bool_DEFINED
#define QUEST_TYPE_QTuple_Bool_DEFINED
struct QTuple_Bool {
    QBool _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_DEFINED
struct QTuple_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 {
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_e13dcd862b05019b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_e13dcd862b05019b_DEFINED
struct RecGroup0_0_QTuple_Self1_e13dcd862b05019b {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_da465bc6f8fa1834_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_da465bc6f8fa1834_DEFINED
struct RecGroup0_0_QTuple_Self1_da465bc6f8fa1834 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_6369bb69b853749f_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_6369bb69b853749f_DEFINED
struct RecGroup0_0_QTuple_Self1_6369bb69b853749f {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_b0d76f1d850c14c9_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_b0d76f1d850c14c9_DEFINED
struct RecGroup0_0_QTuple_Strin_b0d76f1d850c14c9 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
    QBool _2;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _3;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _4;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__a4ef24c0786cdd0e_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__a4ef24c0786cdd0e_DEFINED
struct RecGroup0_0_QTuple_QVal__a4ef24c0786cdd0e {
    QVal _0;
    QVal _1;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_d73d1fb15b7349a9_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_d73d1fb15b7349a9_DEFINED
struct RecGroup0_0_QTuple_Self1_d73d1fb15b7349a9 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_cb87930f68f7f40b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_cb87930f68f7f40b_DEFINED
struct RecGroup0_0_QTuple_Self1_cb87930f68f7f40b {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    QString * _1;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_DEFINED
struct QTuple_QVal_QVal {
    QVal _0;
    QVal _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_e0fe8debd0165e7c_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_e0fe8debd0165e7c_DEFINED
struct RecGroup0_0_QTuple_Self1_e0fe8debd0165e7c {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_Rec0_QTuple__8da641d021d6db4f_DEFINED
#define QUEST_TYPE_QTuple_QVal_Rec0_QTuple__8da641d021d6db4f_DEFINED
struct QTuple_QVal_Rec0_QTuple__8da641d021d6db4f {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTupl_cf02fdb66371a7c8_DEFINED
#define QUEST_TYPE_QTuple_String_Rec0_QTupl_cf02fdb66371a7c8_DEFINED
struct QTuple_String_Rec0_QTupl_cf02fdb66371a7c8 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
    QBool _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_QVal__b66a86a880d0092b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_QVal__b66a86a880d0092b_DEFINED
struct RecGroup0_0_QTuple_QVal__b66a86a880d0092b {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_954f42bc31718d79_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_954f42bc31718d79_DEFINED
struct RecGroup0_0_QTuple_Self1_954f42bc31718d79 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_6cd23faa1c142902_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_6cd23faa1c142902_DEFINED
struct RecGroup0_0_QTuple_Self1_6cd23faa1c142902 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_e3dc1d68a63409e2_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_e3dc1d68a63409e2_DEFINED
struct RecGroup0_0_QTuple_Self1_e3dc1d68a63409e2 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_794fbdf64f431250_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_794fbdf64f431250_DEFINED
struct RecGroup0_0_QTuple_Self1_794fbdf64f431250 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_cf2c6be6e464256b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_cf2c6be6e464256b_DEFINED
struct RecGroup0_0_QTuple_Self1_cf2c6be6e464256b {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_404abe7104fb5711_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_404abe7104fb5711_DEFINED
struct RecGroup0_0_QTuple_Self1_404abe7104fb5711 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_da199b3b9c821353_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_da199b3b9c821353_DEFINED
struct RecGroup0_0_QTuple_Self1_da199b3b9c821353 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_3d45869c1d124380_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_3d45869c1d124380_DEFINED
struct RecGroup0_0_QTuple_Self1_3d45869c1d124380 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_37487d5d7ca3009b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_37487d5d7ca3009b_DEFINED
struct RecGroup0_0_QTuple_Self1_37487d5d7ca3009b {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_88d1e5ff79aab177_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_88d1e5ff79aab177_DEFINED
struct RecGroup0_0_QTuple_Self1_88d1e5ff79aab177 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_b47089ae3602c280_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_b47089ae3602c280_DEFINED
struct RecGroup0_0_QTuple_Self1_b47089ae3602c280 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Strin_364a2bd29ad3663b_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Strin_364a2bd29ad3663b_DEFINED
struct RecGroup0_0_QTuple_Strin_364a2bd29ad3663b {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
    QVal _2;
    QVal _3;
    QBool _4;
    QBool _5;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTupl_4c221b057835555b_DEFINED
#define QUEST_TYPE_QTuple_String_Rec0_QTupl_4c221b057835555b_DEFINED
struct QTuple_String_Rec0_QTupl_4c221b057835555b {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
    QVal _2;
    QVal _3;
    QBool _4;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_DEFINED
#define QUEST_TYPE_QTuple_String_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774_DEFINED
struct QTuple_String_Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 {
    QString * _0;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
};
#endif
#ifndef QUEST_TYPE_RecGroup0_0_QTuple_Self1_f51f6d8f6ba413c1_DEFINED
#define QUEST_TYPE_RecGroup0_0_QTuple_Self1_f51f6d8f6ba413c1_DEFINED
struct RecGroup0_0_QTuple_Self1_f51f6d8f6ba413c1 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
};
#endif
#ifndef QUEST_TYPE_Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_DEFINED
#define QUEST_TYPE_Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_DEFINED
struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe {
    int64_t tag;
    union {
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprInt_payload {
            QInt _0;
            QString * _1;
        } exprInt;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprReal_payload {
            QReal _0;
            QString * _1;
        } exprReal;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprChar_payload {
            QChar _0;
            QString * _1;
        } exprChar;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprString_payload {
            QString * _0;
            QString * _1;
        } exprString;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprBool_payload {
            QBool _0;
        } exprBool;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprId_payload {
            QString * _0;
        } exprId;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprExternal_payload {
            QString * _0;
        } exprExternal;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_typeArg_payload {
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
        } typeArg;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_kindArg_payload {
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
        } kindArg;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprBlock_payload {
            QVal _0;
        } exprBlock;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprIf_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
            QVal _2;
            QVal _3;
        } exprIf;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprWhile_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
        } exprWhile;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprLoop_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
        } exprLoop;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprFor_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
            QBool _2;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _3;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _4;
        } exprFor;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprFun_payload {
            QVal _0;
            QVal _1;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _2;
            QVal _3;
        } exprFun;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprApp_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            QVal _1;
        } exprApp;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprInfix_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            QString * _1;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _2;
        } exprInfix;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprTuple_payload {
            QVal _0;
        } exprTuple;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprRecord_payload {
            QVal _0;
        } exprRecord;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprArray_payload {
            QVal _0;
            QVal _1;
        } exprArray;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprArrayRep_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
        } exprArrayRep;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprOption_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            QVal _2;
            QVal _3;
        } exprOption;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprVariant_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            QBool _2;
            QVal _3;
        } exprVariant;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprAuto_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _2;
        } exprAuto;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprSelect_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            QString * _1;
        } exprSelect;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprIndex_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
        } exprIndex;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprIndexAssign_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _2;
        } exprIndexAssign;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprAssign_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
        } exprAssign;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprVarCell_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
        } exprVarCell;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprDerefCell_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
        } exprDerefCell;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprVariantCheck_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            QString * _1;
        } exprVariantCheck;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprVariantAssert_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            QString * _1;
        } exprVariantAssert;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprCase_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            QVal _1;
            QVal _2;
        } exprCase;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprInspect_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            QVal _1;
            QVal _2;
        } exprInspect;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprException_payload {
            QString * _0;
            QVal _1;
        } exprException;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprRaise_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            QVal _1;
            QVal _2;
        } exprRaise;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_exprTry_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
            QVal _1;
            QVal _2;
        } exprTry;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_declLetVal_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _1;
            QVal _2;
            QVal _3;
            QBool _4;
            QBool _5;
        } declLetVal;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_declLetType_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declLetType;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_declDefType_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declDefType;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_declDefKind_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
        } declDefKind;
        struct Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe_declExprStmt_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
        } declExprStmt;
    } u;
};
#endif
#ifndef QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36_DEFINED
#define QUEST_TYPE_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36_DEFINED
struct Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 {
    QTuple_String_Int_Int * _0;
    Rec0_QOption_exprInt_QTuple_I_704c4abd55f8bffe * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_38c3d6c8d388224b_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_38c3d6c8d388224b_DEFINED
struct QTuple_QTuple_QTuple_Str_38c3d6c8d388224b {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_3350f431cf92dfc0_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_3350f431cf92dfc0_DEFINED
struct QTuple_QTuple_QTuple_Str_3350f431cf92dfc0 {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_71b79add6d91522c_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_71b79add6d91522c_DEFINED
struct QTuple_String_QTuple_QTu_71b79add6d91522c {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QBool _2;
    QTuple_QTuple_String_Int_Int_QVal * _3;
    QTuple_QTuple_String_Int_Int_QVal * _4;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_DEFINED
struct QTuple_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal {
    QVal _0;
    QVal _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_Rec0_QTuple__1729e55676783dca_DEFINED
#define QUEST_TYPE_QTuple_QVal_Rec0_QTuple__1729e55676783dca_DEFINED
struct QTuple_QVal_Rec0_QTuple__1729e55676783dca {
    QVal _0;
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_String_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_String_DEFINED
struct QTuple_QTuple_QTuple_String_Int_Int_QVal_String {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QString * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_4e51da671e850c1f_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_4e51da671e850c1f_DEFINED
struct QTuple_QTuple_QTuple_Str_4e51da671e850c1f {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal_DEFINED
struct QTuple_QTuple_QTuple_String_Int_Int_QVal_QVal_QVal {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QVal _1;
    QVal _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QTuple_QTu_2200c6a3d5421263_DEFINED
#define QUEST_TYPE_QTuple_String_QTuple_QTu_2200c6a3d5421263_DEFINED
struct QTuple_String_QTuple_QTu_2200c6a3d5421263 {
    QString * _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QVal _2;
    QVal _3;
    QBool _4;
    QBool _5;
};
#endif
#ifndef QUEST_TYPE_QOption_exprInt_QTuple_I_bc1d62c3376e60de_DEFINED
#define QUEST_TYPE_QOption_exprInt_QTuple_I_bc1d62c3376e60de_DEFINED
struct QOption_exprInt_QTuple_I_bc1d62c3376e60de {
    int64_t tag;
    union {
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprInt_payload {
            QInt _0;
            QString * _1;
        } exprInt;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprReal_payload {
            QReal _0;
            QString * _1;
        } exprReal;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprChar_payload {
            QChar _0;
            QString * _1;
        } exprChar;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprString_payload {
            QString * _0;
            QString * _1;
        } exprString;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprBool_payload {
            QBool _0;
        } exprBool;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprId_payload {
            QString * _0;
        } exprId;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprExternal_payload {
            QString * _0;
        } exprExternal;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_typeArg_payload {
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
        } typeArg;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_kindArg_payload {
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
        } kindArg;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprBlock_payload {
            QVal _0;
        } exprBlock;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprIf_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QVal _2;
            QVal _3;
        } exprIf;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprWhile_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprWhile;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprLoop_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } exprLoop;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprFor_payload {
            QString * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QBool _2;
            QTuple_QTuple_String_Int_Int_QVal * _3;
            QTuple_QTuple_String_Int_Int_QVal * _4;
        } exprFor;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprFun_payload {
            QVal _0;
            QVal _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
            QVal _3;
        } exprFun;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprApp_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
        } exprApp;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprInfix_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } exprInfix;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprTuple_payload {
            QVal _0;
        } exprTuple;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprRecord_payload {
            QVal _0;
        } exprRecord;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprArray_payload {
            QVal _0;
            QVal _1;
        } exprArray;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprArrayRep_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprArrayRep;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprOption_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            QVal _2;
            QVal _3;
        } exprOption;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprVariant_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            QBool _2;
            QVal _3;
        } exprVariant;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprAuto_payload {
            QVal _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } exprAuto;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprSelect_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
        } exprSelect;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprIndex_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprIndex;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprIndexAssign_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QTuple_QTuple_String_Int_Int_QVal * _2;
        } exprIndexAssign;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprAssign_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
        } exprAssign;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprVarCell_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } exprVarCell;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprDerefCell_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } exprDerefCell;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprVariantCheck_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
        } exprVariantCheck;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprVariantAssert_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QString * _1;
        } exprVariantAssert;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprCase_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprCase;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprInspect_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprInspect;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprException_payload {
            QString * _0;
            QVal _1;
        } exprException;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprRaise_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprRaise;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_exprTry_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
            QVal _1;
            QVal _2;
        } exprTry;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_declLetVal_payload {
            QString * _0;
            QTuple_QTuple_String_Int_Int_QVal * _1;
            QVal _2;
            QVal _3;
            QBool _4;
            QBool _5;
        } declLetVal;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_declLetType_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declLetType;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_declDefType_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
            QVal _2;
            QVal _3;
            QBool _4;
        } declDefType;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_declDefKind_payload {
            QString * _0;
            Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _1;
        } declDefKind;
        struct QOption_exprInt_QTuple_I_bc1d62c3376e60de_declExprStmt_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } declExprStmt;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QOption_modeValue_modeVar_modeOut_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_QOption_modeValue_modeVar_modeOut_DEFINED
struct QTuple_String_QVal_QOption_modeValue_modeVar_modeOut {
    QString * _0;
    QVal _1;
    QOption_modeValue_modeVar_modeOut * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_DEFINED
struct QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool {
    QVal _0;
    QTuple_QTuple_String_Int_Int_QVal * _1;
    QVal _2;
    QBool _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool_DEFINED
struct QTuple_QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool {
    QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool * _0;
};
#endif
#ifndef QUEST_TYPE_QOption_fieldVal_QTuple__168c8db8e15234f1_DEFINED
#define QUEST_TYPE_QOption_fieldVal_QTuple__168c8db8e15234f1_DEFINED
struct QOption_fieldVal_QTuple__168c8db8e15234f1 {
    int64_t tag;
    union {
        struct QOption_fieldVal_QTuple__168c8db8e15234f1_fieldVal_payload {
            QTuple_QVal_QTuple_QTuple_String_Int_Int_QVal_QVal_Bool * _0;
        } fieldVal;
        struct QOption_fieldVal_QTuple__168c8db8e15234f1_fieldDecl_payload {
            QTuple_QTuple_String_Int_Int_QVal * _0;
        } fieldDecl;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_String_QVal_QTuple_QTuple_String_Int_Int_QVal {
    QString * _0;
    QVal _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal_DEFINED
struct QTuple_QVal_QVal_QVal_QTuple_QTuple_String_Int_Int_QVal {
    QVal _0;
    QVal _1;
    QVal _2;
    QTuple_QTuple_String_Int_Int_QVal * _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTupl_bd92283f65796da7_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTupl_bd92283f65796da7_DEFINED
struct QTuple_Rec0_QTuple_QTupl_bd92283f65796da7 {
    Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * _0;
    QVal _1;
    QTuple_QTuple_String_Int_Int_QVal * _2;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QTuple_Str_ca206c534ceb51b5_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QTuple_Str_ca206c534ceb51b5_DEFINED
struct QTuple_QTuple_QTuple_Str_ca206c534ceb51b5 {
    QTuple_QTuple_String_Int_Int_QVal * _0;
    QVal _1;
    QVal _2;
    QTuple_QTuple_String_Int_Int_QVal * _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_QVal_DEFINED
struct QTuple_QTuple_QVal {
    QTuple_QVal * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_QVal_QVal_Bool_DEFINED
struct QTuple_String_QVal_QVal_Bool {
    QString * _0;
    QVal _1;
    QVal _2;
    QBool _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_QVal_QVal_Bool_DEFINED
struct QTuple_QTuple_String_QVal_QVal_Bool {
    QTuple_String_QVal_QVal_Bool * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_String_String_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_String_String_QVal_QVal_Bool_DEFINED
struct QTuple_String_String_QVal_QVal_Bool {
    QString * _0;
    QString * _1;
    QVal _2;
    QVal _3;
    QBool _4;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_String_QVal_QVal_Bool_DEFINED
struct QTuple_QTuple_String_String_QVal_QVal_Bool {
    QTuple_String_String_QVal_QVal_Bool * _0;
};
#endif
#ifndef QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36_DEFINED
#define QUEST_TYPE_QTuple_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36_DEFINED
struct QTuple_Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 {
    Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
};
#endif
#ifndef QUEST_TYPE_QOption_phraseImport_QTu_a682fc37f16b1dcd_DEFINED
#define QUEST_TYPE_QOption_phraseImport_QTu_a682fc37f16b1dcd_DEFINED
struct QOption_phraseImport_QTu_a682fc37f16b1dcd {
    int64_t tag;
    union {
        struct QOption_phraseImport_QTu_a682fc37f16b1dcd_phraseImport_payload {
            QTuple_QVal * _0;
        } phraseImport;
        struct QOption_phraseImport_QTu_a682fc37f16b1dcd_phraseInterface_payload {
            QTuple_String_QVal_QVal_Bool * _0;
        } phraseInterface;
        struct QOption_phraseImport_QTu_a682fc37f16b1dcd_phraseModule_payload {
            QTuple_String_String_QVal_QVal_Bool * _0;
        } phraseModule;
        struct QOption_phraseImport_QTu_a682fc37f16b1dcd_phraseDecl_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
        } phraseDecl;
        struct QOption_phraseImport_QTu_a682fc37f16b1dcd_phraseExpr_payload {
            Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * _0;
        } phraseExpr;
    } u;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_95359d63df53c666_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_95359d63df53c666_DEFINED
struct QTuple_QTuple_String_Int_95359d63df53c666 {
    QTuple_String_Int_Int * _0;
    QOption_phraseImport_QTu_a682fc37f16b1dcd * _1;
};
#endif
#ifndef QUEST_TYPE_QTuple_QVal_String_QVal_QVal_DEFINED
#define QUEST_TYPE_QTuple_QVal_String_QVal_QVal_DEFINED
struct QTuple_QVal_String_QVal_QVal {
    QVal _0;
    QString * _1;
    QVal _2;
    QVal _3;
};
#endif
#ifndef QUEST_TYPE_QTuple_QTuple_String_Int_Int_QTuple_QVal_DEFINED
#define QUEST_TYPE_QTuple_QTuple_String_Int_Int_QTuple_QVal_DEFINED
struct QTuple_QTuple_String_Int_Int_QTuple_QVal {
    QTuple_String_Int_Int * _0;
    QTuple_QVal * _1;
};
#endif
typedef QString * (*quest_sig_AstPrint_dumpTypeExpr)(Rec0_QTuple_QTuple_String_Int_fd23880d02a42774 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpExpr)(Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpDecl)(Rec0_QTuple_QTuple_String_Int_ed6d92a1f6d06f36 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpPhrase)(QTuple_QTuple_String_Int_95359d63df53c666 * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dumpProgram)(QTuple_QTuple_String_Int_Int_QTuple_QVal * node, QInt indent, QBool showOffsets);
typedef QString * (*quest_sig_AstPrint_dump)(QTuple_QTuple_String_Int_Int_QTuple_QVal * node);
typedef QString * (*quest_sig_AstPrint_dumpWithOptions)(QTuple_QTuple_String_Int_Int_QTuple_QVal * node, QBool showOffsets);
#ifdef __cplusplus
}
#endif
#endif
