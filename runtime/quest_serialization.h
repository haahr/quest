#ifndef QUEST_SERIALIZATION_H
#define QUEST_SERIALIZATION_H

#include "quest_runtime.h"

#ifdef __cplusplus
extern "C" {
#endif

/* dynamic.extern and dynamic.intern for compiled code (quest_serialization.c;
 * the format is docs/dynamic.md §2, which the interpreters' dynamic_json
 * writes and reads too).
 *
 * quest_dynamic_extern writes the dynamic value d to wr as one JSON document,
 * with no newline after it. It raises dynamic.error, before writing anything,
 * if wr is closed or d holds a value the format cannot express (a function,
 * an exception, a reader or writer, an external type other than word.T;
 * §2.6).
 *
 * quest_dynamic_intern reads one such document from rd, leaving the
 * character after it unread, and returns a new dynamic value, with fresh
 * objects shared and cyclic as the document's "@id"s and "@ref"s say. It
 * raises dynamic.error if rd is closed or the text is malformed or does not
 * fit its types (§2.6).
 *
 * No collection runs during either (quest_gc_hold). */
void   quest_dynamic_extern(QWriter *wr, const QAuto *d);
QAuto *quest_dynamic_intern(QReader *rd);

#ifdef __cplusplus
}
#endif

#endif /* QUEST_SERIALIZATION_H */
