/* External definitions of the runtime's inline helpers (the Q_INLINE functions of quest_runtime.h), for code that
 * cannot inline them to call: native code (docs/arm64.md section 7.5). Every other translation unit keeps its own
 * static inline copies. */
#define Q_INLINE
#include "quest_runtime.h"
