#ifndef QUEST_INTF_WORD_H
#define QUEST_INTF_WORD_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef QVal quest_type_Word_T;
typedef QInt quest_sig_Word_bits;
typedef QVal (*quest_sig_Word_notBits)(QVal w);
typedef QVal (*quest_sig_Word_andBits)(QVal w1, QVal w2);
typedef QVal (*quest_sig_Word_orBits)(QVal w1, QVal w2);
typedef QVal (*quest_sig_Word_xorBits)(QVal w1, QVal w2);
typedef QVal (*quest_sig_Word_shift)(QVal w, QInt count);
typedef QVal (*quest_sig_Word_rotate)(QVal w, QInt count);
typedef QVal (*quest_sig_Word_extract)(QVal w, QInt pos, QInt width);
typedef QVal (*quest_sig_Word_replace)(QVal w, QVal val, QInt pos, QInt width);
typedef QInt (*quest_sig_Word_popCount)(QVal w);
typedef QInt (*quest_sig_Word_countLeadingZeros)(QVal w);
typedef QInt (*quest_sig_Word_countTrailingZeros)(QVal w);
typedef QVal (*quest_sig_Word_add)(QVal w1, QVal w2);
typedef QVal (*quest_sig_Word_sub)(QVal w1, QVal w2);
typedef QVal (*quest_sig_Word_mul)(QVal w1, QVal w2);
typedef QVal (*quest_sig_Word_div)(QVal w1, QVal w2);
typedef QVal (*quest_sig_Word_mod)(QVal w1, QVal w2);
typedef QInt (*quest_sig_Word_toInt)(QVal w);
typedef QVal (*quest_sig_Word_fromInt)(QInt n);
typedef QBool (*quest_sig_Word_lt)(QVal w1, QVal w2);
typedef QBool (*quest_sig_Word_le)(QVal w1, QVal w2);
typedef QBool (*quest_sig_Word_gt)(QVal w1, QVal w2);
typedef QBool (*quest_sig_Word_ge)(QVal w1, QVal w2);
typedef QReal (*quest_sig_Word_toReal)(QVal w);
typedef QVal (*quest_sig_Word_fromReal)(QReal r);
typedef QBool (*quest_sig_Word_getBit)(QVal w, QInt pos);
typedef QVal (*quest_sig_Word_setBit)(QVal w, QInt pos);
typedef QVal (*quest_sig_Word_clearBit)(QVal w, QInt pos);
#ifdef __cplusplus
}
#endif
#endif
