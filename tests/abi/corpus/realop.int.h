#ifndef QUEST_INTF_REALOP_H
#define QUEST_INTF_REALOP_H
#include "quest_runtime.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef const QException * quest_sig_RealOp_error;
typedef QReal quest_sig_RealOp_minReal;
typedef QReal quest_sig_RealOp_maxReal;
typedef QReal quest_sig_RealOp_posEpsilon;
typedef QReal quest_sig_RealOp_negEpsilon;
typedef QReal quest_sig_RealOp_e;
typedef QReal (*quest_sig_RealOp_int)(QInt n);
typedef QInt (*quest_sig_RealOp_floor)(QReal r);
typedef QInt (*quest_sig_RealOp_round)(QReal r);
typedef QReal (*quest_sig_RealOp_abs)(QReal r);
typedef QReal (*quest_sig_RealOp_log)(QReal r);
typedef QReal (*quest_sig_RealOp_min)(QReal a, QReal b);
typedef QReal (*quest_sig_RealOp_max)(QReal a, QReal b);
typedef QReal (*quest_sig_RealOp_plus)(QReal a, QReal b);
typedef QReal (*quest_sig_RealOp_diff)(QReal a, QReal b);
typedef QReal (*quest_sig_RealOp_mul)(QReal a, QReal b);
typedef QReal (*quest_sig_RealOp_div)(QReal a, QReal b);
typedef QReal (*quest_sig_RealOp_exp)(QReal a, QReal b);
typedef QBool (*quest_sig_RealOp_smaller)(QReal a, QReal b);
typedef QBool (*quest_sig_RealOp_greater)(QReal a, QReal b);
typedef QBool (*quest_sig_RealOp_smallerEq)(QReal a, QReal b);
typedef QBool (*quest_sig_RealOp_greaterEq)(QReal a, QReal b);
typedef QReal quest_sig_RealOp_pi;
typedef QReal quest_sig_RealOp_infinity;
typedef QReal (*quest_sig_RealOp_sqrt)(QReal r);
typedef QReal (*quest_sig_RealOp_sin)(QReal r);
typedef QReal (*quest_sig_RealOp_cos)(QReal r);
typedef QReal (*quest_sig_RealOp_tan)(QReal r);
typedef QReal (*quest_sig_RealOp_asin)(QReal r);
typedef QReal (*quest_sig_RealOp_acos)(QReal r);
typedef QReal (*quest_sig_RealOp_atan)(QReal r);
typedef QReal (*quest_sig_RealOp_atan2)(QReal y, QReal x);
typedef QReal (*quest_sig_RealOp_exponential)(QReal r);
typedef QReal (*quest_sig_RealOp_sinh)(QReal r);
typedef QReal (*quest_sig_RealOp_cosh)(QReal r);
typedef QReal (*quest_sig_RealOp_tanh)(QReal r);
typedef QInt (*quest_sig_RealOp_ceil)(QReal r);
typedef QInt (*quest_sig_RealOp_trunc)(QReal r);
typedef QString * (*quest_sig_RealOp_format)(QReal r, QChar style, QInt digits);
#ifdef __cplusplus
}
#endif
#endif
