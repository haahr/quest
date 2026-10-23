"""The standard library's external C functions and values, implemented in Python for the interpreters: each
`external "symbol"` of lib/ resolves to a Python function, value, or exception (resolve_external_symbol), and
system.args is set from the driver's arguments (set_system_args). The library's interfaces and modules, which the
type checker loads, are quest.modules.stdlib's."""

from __future__ import annotations

import math
import os
import struct
import sys
from typing import Any, Callable, Optional

from quest.values.dynamic_json import jsog_decode, jsog_encode
from quest.interpreter.treewalk import (
    ARRAY_OP_ERROR_EXC,
    ASCII_ERROR_EXC,
    INT_ERROR_EXC,
    LIST_ERROR_EXC,
    READER_ERROR_EXC,
    REAL_ERROR_EXC,
    STRING_ERROR_EXC,
    SYSTEM_ERROR_EXC,
    WORD_ERROR_EXC,
    WRITER_ERROR_EXC,
    QuestRuntimeError,
    real_divide,
    real_pow,
)
from quest.values.model import (
    DYNAMIC_ERROR_EXC,
    QuestException,
    FALSE_VALUE,
    OK_VALUE,
    TRUE_VALUE,
    QArray,
    QAutoVal,
    QBool,
    QBuiltinFun,
    QChar,
    QExceptionVal,
    QInt,
    QList,
    QOk,
    QReader,
    QReal,
    QString,
    QStringBuilder,
    QTuple,
    QValue,
    QWord,
    QWriter,
)


def qchecked(error_exc: Optional[QExceptionVal], *expected_types: type) -> Callable:
    """Decorator to validate that arguments passed to a builtin function match expected types.

    If error_exc is provided, raises QuestException(error_exc) on mismatch;
    otherwise, raises QuestRuntimeError with a descriptive message.
    """
    def decorator(fn: Callable) -> Callable:
        def wrapper(*args: Any) -> Any:
            if len(args) != len(expected_types):
                if error_exc is not None:
                    raise QuestException(error_exc)
                raise QuestRuntimeError(f"Expected {len(expected_types)} arguments, got {len(args)}")
            for arg, exp_type in zip(args, expected_types):
                if not isinstance(arg, exp_type):
                    if error_exc is not None:
                        raise QuestException(error_exc)
                    raise QuestRuntimeError(
                        f"Expected argument of type {exp_type.__name__}, got {type(arg).__name__}"
                    )
            return fn(*args)
        return wrapper
    return decorator

def _writer_file(name_val: QString) -> QWriter:
    try:
        f = open(name_val.value, "w", encoding="utf-8", newline="")
        return QWriter(stream=f, is_file=True, file_name=name_val.value)
    except OSError:
        raise QuestException(WRITER_ERROR_EXC)

def _writer_put_string(w: QWriter, s: QString) -> QOk:
    if w.is_closed:
        raise QuestException(WRITER_ERROR_EXC)
    try:
        w.stream.write(s.value)
        return OK_VALUE
    except OSError:
        raise QuestException(WRITER_ERROR_EXC)

def _writer_put_char(w: QWriter, c: QChar) -> QOk:
    if w.is_closed:
        raise QuestException(WRITER_ERROR_EXC)
    try:
        w.stream.write(c.value)
        return OK_VALUE
    except OSError:
        raise QuestException(WRITER_ERROR_EXC)

def _writer_put_sub_string(w: QWriter, s: QString, start: QInt, size: QInt) -> QOk:
    if w.is_closed:
        raise QuestException(WRITER_ERROR_EXC)
    st, sz = start.value, size.value
    if st < 0 or sz < 0 or st + sz > len(s.value):
        raise QuestException(WRITER_ERROR_EXC)
    try:
        w.stream.write(s.value[st : st + sz])
        return OK_VALUE
    except OSError:
        raise QuestException(WRITER_ERROR_EXC)

def _writer_flush(w: QWriter) -> QOk:
    if w.is_closed:
        raise QuestException(WRITER_ERROR_EXC)
    try:
        w.stream.flush()
        return OK_VALUE
    except OSError:
        raise QuestException(WRITER_ERROR_EXC)

def _writer_close(w: QWriter) -> QOk:
    if not w.is_closed:
        try:
            if w.is_file:
                w.stream.close()
            else:
                w.stream.flush()
            w.is_closed = True
        except OSError:
            raise QuestException(WRITER_ERROR_EXC)
    return OK_VALUE

def _reader_file(name_val: QString) -> QReader:
    try:
        f = open(name_val.value, "r", encoding="utf-8", newline="")
        return QReader(stream=f, is_file=True, file_name=name_val.value)
    except OSError:
        raise QuestException(READER_ERROR_EXC)

def _reader_read_one(r: QReader) -> str:
    peek = getattr(r, "_peek_char", None)
    if peek is not None:
        r._peek_char = None
        return peek
    return r.stream.read(1)

def _reader_more(r: QReader) -> QBool:
    if r.is_closed:
        raise QuestException(READER_ERROR_EXC)
    peek = getattr(r, "_peek_char", None)
    if peek is not None:
        return TRUE_VALUE
    try:
        ch = r.stream.read(1)
        if not ch:
            return FALSE_VALUE
        r._peek_char = ch
        return TRUE_VALUE
    except OSError:
        raise QuestException(READER_ERROR_EXC)

def _reader_ready(r: QReader) -> QInt:
    if r.is_closed:
        raise QuestException(READER_ERROR_EXC)
    return QInt(0)

def _reader_get_char(r: QReader) -> QChar:
    if r.is_closed:
        raise QuestException(READER_ERROR_EXC)
    try:
        ch = _reader_read_one(r)
        if not ch:
            raise QuestException(READER_ERROR_EXC)
        return QChar(ch)
    except OSError:
        raise QuestException(READER_ERROR_EXC)

def _reader_get_string(r: QReader, size: QInt) -> QString:
    if r.is_closed:
        raise QuestException(READER_ERROR_EXC)
    sz = size.value
    if sz < 0:
        raise QuestException(READER_ERROR_EXC)
    buf = []
    peek = getattr(r, "_peek_char", None)
    if peek is not None and sz > 0:
        buf.append(peek)
        r._peek_char = None
        sz -= 1
    if sz > 0:
        try:
            chunk = r.stream.read(sz)
            buf.append(chunk)
        except OSError:
            raise QuestException(READER_ERROR_EXC)
    return QString("".join(buf))

def _reader_get_sub_string(r: QReader, s: QString, start: QInt, size: QInt) -> QOk:
    if r.is_closed:
        raise QuestException(READER_ERROR_EXC)
    st, sz = start.value, size.value
    if st < 0 or sz < 0 or st + sz > len(s.value):
        raise QuestException(READER_ERROR_EXC)
    read_str = _reader_get_string(r, size).value
    s.value = s.value[:st] + read_str + s.value[st + len(read_str) :]
    return OK_VALUE

def _reader_close(r: QReader) -> QOk:
    if not r.is_closed:
        try:
            if r.is_file:
                r.stream.close()
            r.is_closed = True
        except OSError:
            raise QuestException(READER_ERROR_EXC)
    return OK_VALUE

def _conv_int(n: QValue) -> QString:
    if not isinstance(n, QInt):
        return QString("")
    val = n.value
    return QString(f"~{-val}" if val < 0 else str(val))

def _conv_real(r: QValue) -> QString:
    if not isinstance(r, QReal):
        return QString("")
    val = r.value
    # Quest writes negation as ~, including for negative zero and negative infinity.
    is_neg = math.copysign(1.0, val) < 0
    abs_val = -val if is_neg else val
    if math.isinf(abs_val):
        return QString("~inf" if is_neg else "inf")
    s = str(abs_val)
    if "." not in s and "e" not in s:
        s += ".0"
    return QString(f"~{s}" if is_neg else s)

def _ascii_char(n: QInt) -> QChar:
    if n.value < 0 or n.value > 255:
        raise QuestException(ASCII_ERROR_EXC)
    return QChar(chr(n.value))

def _ascii_val(c: QChar) -> QInt:
    return QInt(ord(c.value))

def _real_log(r: QReal) -> QReal:
    if r.value <= 0.0:
        raise QuestException(REAL_ERROR_EXC)
    return QReal(math.log(r.value))

def _real_div(a: QReal, b: QReal) -> QReal:
    return QReal(real_divide(a.value, b.value))

def _real_exp(a: QReal, b: QReal) -> QReal:
    return QReal(real_pow(a.value, b.value))

def _real_to_int(r: float) -> QInt:
    """An integral real as an Int; an infinity or a value outside Int's range raises real.error."""
    if not math.isfinite(r) or not (-(2**63) <= r < 2**63):
        raise QuestException(REAL_ERROR_EXC)
    return QInt(int(r))

def _real_round(r: float) -> float:
    """Rounds half away from zero, as C's round does (Python's round rounds half to even)."""
    if not math.isfinite(r):
        return r
    t = float(math.trunc(r))
    if abs(r - t) >= 0.5:
        t += math.copysign(1.0, r)
    return t

def _string_new(size: QInt, init: QChar) -> QString:
    if size.value < 0:
        raise QuestException(STRING_ERROR_EXC)
    return QString(init.value * size.value)

def _string_get_char(s: QString, index: QInt) -> QChar:
    idx = index.value
    if idx < 0 or idx >= len(s.value):
        raise QuestException(STRING_ERROR_EXC)
    return QChar(s.value[idx])

def _string_set_char(s: QString, index: QInt, char: QChar) -> QOk:
    idx = index.value
    if idx < 0 or idx >= len(s.value):
        raise QuestException(STRING_ERROR_EXC)
    s.value = s.value[:idx] + char.value + s.value[idx + 1 :]
    return OK_VALUE

def _string_get_sub(s: QString, start: QInt, size: QInt) -> QString:
    st, sz = start.value, size.value
    if st < 0 or sz < 0 or st + sz > len(s.value):
        raise QuestException(STRING_ERROR_EXC)
    return QString(s.value[st : st + sz])

def _string_set_sub(dest: QString, d_st: QInt, src: QString, s_st: QInt, sz: QInt) -> QOk:
    dst_idx, src_idx, count = d_st.value, s_st.value, sz.value
    if (
        dst_idx < 0
        or src_idx < 0
        or count < 0
        or dst_idx + count > len(dest.value)
        or src_idx + count > len(src.value)
    ):
        raise QuestException(STRING_ERROR_EXC)
    chunk = src.value[src_idx : src_idx + count]
    dest.value = dest.value[:dst_idx] + chunk + dest.value[dst_idx + count :]
    return OK_VALUE

def _string_cat_sub(s1: QString, st1: QInt, sz1: QInt, s2: QString, st2: QInt, sz2: QInt) -> QString:
    sub1 = _string_get_sub(s1, st1, sz1).value
    sub2 = _string_get_sub(s2, st2, sz2).value
    return QString(sub1 + sub2)

def _string_conc(arr: QArray) -> QString:
    parts: list[str] = []
    for elem in arr.elements:
        if not isinstance(elem, QString):
            raise QuestException(STRING_ERROR_EXC)
        parts.append(elem.value)
    return QString("".join(parts))

def _string_equal_sub(s1: QString, st1: QInt, sz1: QInt, s2: QString, st2: QInt, sz2: QInt) -> QBool:
    sub1 = _string_get_sub(s1, st1, sz1).value
    sub2 = _string_get_sub(s2, st2, sz2).value
    return QBool(sub1 == sub2)

def _string_precedes_sub(
    s1: QString, st1: QInt, sz1: QInt, s2: QString, st2: QInt, sz2: QInt
) -> QBool:
    sub1 = _string_get_sub(s1, st1, sz1).value
    sub2 = _string_get_sub(s2, st2, sz2).value
    return QBool(sub1 <= sub2)

def _array_new(size: QInt, init: QValue) -> QArray:
    if size.value < 0:
        raise QuestException(ARRAY_OP_ERROR_EXC)
    return QArray([init for _ in range(size.value)])

def _array_size(arr: QArray) -> QInt:
    return QInt(arr.size())

def _array_get(arr: QArray, idx: QInt) -> QValue:
    i = idx.value
    if i < 0 or i >= arr.size():
        raise QuestException(ARRAY_OP_ERROR_EXC)
    return arr.get(i)

def _array_set(arr: QArray, idx: QInt, item: QValue) -> QOk:
    i = idx.value
    if i < 0 or i >= arr.size():
        raise QuestException(ARRAY_OP_ERROR_EXC)
    arr.set(i, item)
    return OK_VALUE

def _dynamic_copy(d: QAutoVal) -> QAutoVal:
    return QAutoVal(QTuple(d.value.elements, d.value.labels), d.type_val)

def _dynamic_extern(wr: QWriter, d: QAutoVal) -> QOk:
    if wr.is_closed:
        raise QuestException(DYNAMIC_ERROR_EXC)
    json_text = jsog_encode(d)
    try:
        wr.stream.write(json_text)
        return OK_VALUE
    except OSError:
        raise QuestException(DYNAMIC_ERROR_EXC)

def _dynamic_intern(rd: QReader) -> QAutoVal:
    if rd.is_closed:
        raise QuestException(DYNAMIC_ERROR_EXC)

    def read_ch() -> str:
        peek = getattr(rd, "_peek_char", None)
        if peek is not None:
            rd._peek_char = None
            return peek
        try:
            return rd.stream.read(1)
        except OSError:
            raise QuestException(DYNAMIC_ERROR_EXC)

    # Skip leading whitespace
    while True:
        ch = read_ch()
        if not ch:
            raise QuestException(DYNAMIC_ERROR_EXC)
        if ch not in " \t\r\n":
            break

    buf = [ch]
    if ch in "{[":
        depth = 1
        in_str = False
        esc = False
        while depth > 0:
            c = read_ch()
            if not c:
                raise QuestException(DYNAMIC_ERROR_EXC)
            buf.append(c)
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c in "{[":
                    depth += 1
                elif c in "}]":
                    depth -= 1
    elif ch == '"':
        esc = False
        while True:
            c = read_ch()
            if not c:
                raise QuestException(DYNAMIC_ERROR_EXC)
            buf.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                break
    else:
        while True:
            peek = getattr(rd, "_peek_char", None)
            if peek is not None:
                c = peek
            else:
                try:
                    c = rd.stream.read(1)
                    rd._peek_char = c
                except OSError:
                    c = ""
            if not c or c in " \t\r\n,]}":
                break
            rd._peek_char = None
            buf.append(c)

    raw = "".join(buf)
    return jsog_decode(raw)

def _list_nil(*args: Any) -> QList:
    return QList(())

def _list_cons(item: QValue, l: QList) -> QList:
    return QList((item,) + l.elements)

def _list_null(l: QList) -> QBool:
    return TRUE_VALUE if len(l.elements) == 0 else FALSE_VALUE

def _list_head(l: QList) -> QValue:
    if not l.elements:
        raise QuestException(LIST_ERROR_EXC)
    return l.elements[0]

def _list_tail(l: QList) -> QList:
    if not l.elements:
        raise QuestException(LIST_ERROR_EXC)
    return QList(l.elements[1:])

def _list_length(l: QList) -> QInt:
    return QInt(len(l.elements))

def _list_enum(arr: QArray) -> QList:
    return QList(tuple(arr.elements))

def _system_exit(code: QInt) -> QOk:
    sys.exit(code.value)

def _system_getenv(name_val: QString) -> QString:
    return QString(os.environ.get(name_val.value, ""))

def _system_file_exists(path_val: QString) -> QBool:
    return TRUE_VALUE if os.path.exists(path_val.value) else FALSE_VALUE

def _system_is_file(path_val: QString) -> QBool:
    return TRUE_VALUE if os.path.isfile(path_val.value) else FALSE_VALUE

def _system_is_directory(path_val: QString) -> QBool:
    return TRUE_VALUE if os.path.isdir(path_val.value) else FALSE_VALUE

def _system_make_directory(path_val: QString) -> QOk:
    try:
        os.makedirs(path_val.value, exist_ok=True)
        return OK_VALUE
    except OSError:
        raise QuestException(SYSTEM_ERROR_EXC)

def _system_remove_file(path_val: QString) -> QOk:
    try:
        os.remove(path_val.value)
        return OK_VALUE
    except OSError:
        raise QuestException(SYSTEM_ERROR_EXC)

def _system_remove_directory(path_val: QString) -> QOk:
    try:
        os.rmdir(path_val.value)
        return OK_VALUE
    except OSError:
        raise QuestException(SYSTEM_ERROR_EXC)

def _system_rename_file(old_path_val: QString, new_path_val: QString) -> QOk:
    try:
        os.rename(old_path_val.value, new_path_val.value)
        return OK_VALUE
    except OSError:
        raise QuestException(SYSTEM_ERROR_EXC)

def _system_current_directory() -> QString:
    try:
        return QString(os.getcwd())
    except OSError:
        raise QuestException(SYSTEM_ERROR_EXC)

def _system_change_directory(path_val: QString) -> QOk:
    try:
        os.chdir(path_val.value)
        return OK_VALUE
    except OSError:
        raise QuestException(SYSTEM_ERROR_EXC)

def _system_list_directory(path_val: QString) -> QArray:
    try:
        names = sorted(os.listdir(path_val.value))
        return QArray(tuple(QString(n) for n in names))
    except OSError:
        raise QuestException(SYSTEM_ERROR_EXC)

def _word_not_bits(w: QWord) -> QWord:
    return QWord((~w.value) & 0xFFFF_FFFF_FFFF_FFFF)

def _word_and_bits(w1: QWord, w2: QWord) -> QWord:
    return QWord(w1.value & w2.value)

def _word_or_bits(w1: QWord, w2: QWord) -> QWord:
    return QWord(w1.value | w2.value)

def _word_xor_bits(w1: QWord, w2: QWord) -> QWord:
    return QWord(w1.value ^ w2.value)

def _word_shift(w: QWord, count: QInt) -> QWord:
    cnt = count.value
    if cnt >= 64 or cnt <= -64:
        return QWord(0)
    if cnt > 0:
        return QWord((w.value << cnt) & 0xFFFF_FFFF_FFFF_FFFF)
    if cnt < 0:
        return QWord(w.value >> (-cnt))
    return w

def _word_rotate(w: QWord, count: QInt) -> QWord:
    cnt = count.value % 64
    if cnt == 0:
        return w
    val = ((w.value << cnt) & 0xFFFF_FFFF_FFFF_FFFF) | (w.value >> (64 - cnt))
    return QWord(val)

def _word_extract(w: QWord, pos: QInt, width: QInt) -> QWord:
    p = pos.value
    wd = width.value
    if p < 0 or p >= 64 or wd <= 0:
        return QWord(0)
    if wd > 64 - p:
        wd = 64 - p
    mask = 0xFFFF_FFFF_FFFF_FFFF if wd == 64 else ((1 << wd) - 1)
    return QWord((w.value >> p) & mask)

def _word_replace(w: QWord, val: QWord, pos: QInt, width: QInt) -> QWord:
    p = pos.value
    wd = width.value
    if p < 0 or p >= 64 or wd <= 0:
        return w
    if wd > 64 - p:
        wd = 64 - p
    mask = 0xFFFF_FFFF_FFFF_FFFF if wd == 64 else ((1 << wd) - 1)
    cleared = w.value & ~(mask << p)
    inserted = (val.value & mask) << p
    return QWord((cleared | inserted) & 0xFFFF_FFFF_FFFF_FFFF)

def _word_pop_count(w: QWord) -> QInt:
    return QInt(w.value.bit_count())

def _word_count_leading_zeros(w: QWord) -> QInt:
    if w.value == 0:
        return QInt(64)
    return QInt(64 - w.value.bit_length())

def _word_count_trailing_zeros(w: QWord) -> QInt:
    if w.value == 0:
        return QInt(64)
    return QInt((w.value & -w.value).bit_length() - 1)

def _word_get_bit(w: QWord, pos: QInt) -> QBool:
    p = pos.value
    if p < 0 or p >= 64:
        return FALSE_VALUE
    return TRUE_VALUE if ((w.value >> p) & 1) != 0 else FALSE_VALUE

def _word_set_bit(w: QWord, pos: QInt) -> QWord:
    p = pos.value
    if p < 0 or p >= 64:
        return w
    return QWord(w.value | (1 << p))

def _word_clear_bit(w: QWord, pos: QInt) -> QWord:
    p = pos.value
    if p < 0 or p >= 64:
        return w
    return QWord(w.value & ~(1 << p))

def _word_add(w1: QWord, w2: QWord) -> QWord:
    return QWord((w1.value + w2.value) & 0xFFFF_FFFF_FFFF_FFFF)

def _word_sub(w1: QWord, w2: QWord) -> QWord:
    return QWord((w1.value - w2.value) & 0xFFFF_FFFF_FFFF_FFFF)

def _word_mul(w1: QWord, w2: QWord) -> QWord:
    return QWord((w1.value * w2.value) & 0xFFFF_FFFF_FFFF_FFFF)

def _word_div(w1: QWord, w2: QWord) -> QWord:
    if w2.value == 0:
        raise QuestException(WORD_ERROR_EXC, OK_VALUE)
    return QWord(w1.value // w2.value)

def _word_mod(w1: QWord, w2: QWord) -> QWord:
    if w2.value == 0:
        raise QuestException(WORD_ERROR_EXC, OK_VALUE)
    return QWord(w1.value % w2.value)

def _word_to_int(w: QWord) -> QInt:
    val = w.value
    if val >= (1 << 63):
        val -= (1 << 64)
    return QInt(val)

def _word_from_int(n: QInt) -> QWord:
    return QWord(n.value & 0xFFFF_FFFF_FFFF_FFFF)

def _word_to_real(w: QWord) -> QReal:
    r = struct.unpack(">d", struct.pack(">Q", w.value))[0]
    if math.isnan(r):
        # NaN bit patterns have no Real value (docs/type-system.md §6.3.1).
        raise QuestException(WORD_ERROR_EXC, OK_VALUE)
    return QReal(r)

def _word_from_real(r: QReal) -> QWord:
    w = struct.unpack(">Q", struct.pack(">d", r.value))[0]
    return QWord(w)

def _word_lt(w1: QWord, w2: QWord) -> QBool:
    return TRUE_VALUE if w1.value < w2.value else FALSE_VALUE

def _word_le(w1: QWord, w2: QWord) -> QBool:
    return TRUE_VALUE if w1.value <= w2.value else FALSE_VALUE

def _word_gt(w1: QWord, w2: QWord) -> QBool:
    return TRUE_VALUE if w1.value > w2.value else FALSE_VALUE

def _word_ge(w1: QWord, w2: QWord) -> QBool:
    return TRUE_VALUE if w1.value >= w2.value else FALSE_VALUE

def _splitmix64(z: int) -> int:
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9 & 0xFFFF_FFFF_FFFF_FFFF
    z = (z ^ (z >> 27)) * 0x94D049BB133111EB & 0xFFFF_FFFF_FFFF_FFFF
    return (z ^ (z >> 31)) & 0xFFFF_FFFF_FFFF_FFFF

def _quest_hash_mix(w: QWord) -> QWord:
    return QWord(_splitmix64(w.value & 0xFFFF_FFFF_FFFF_FFFF))

def _quest_hash_combine(h1: QWord, h2: QWord) -> QWord:
    combined = (
        h1.value ^ (h2.value + 0x9E3779B97F4A7C15 + (h1.value << 6) + (h1.value >> 2))
    ) & 0xFFFF_FFFF_FFFF_FFFF
    return QWord(combined)

def _quest_identity_hash(v: QValue) -> QWord:
    match v:
        case QInt(value=val) | QWord(value=val):
            raw = val & 0xFFFF_FFFF_FFFF_FFFF
        case QBool(value=val):
            raw = 1 if val else 0
        case QChar(value=val):
            raw = ord(val)
        case QReal(value=val):
            # 0.0 is ~0.0, so both must hash alike; adding 0.0 turns ~0.0 into 0.0.
            raw = struct.unpack(">Q", struct.pack(">d", val + 0.0))[0]
        case QOk():
            raw = 0
        case _:
            raw = id(v) & 0xFFFF_FFFF_FFFF_FFFF
    return QWord(_splitmix64(raw))

def _sb_append(b: QStringBuilder, text: str) -> QOk:
    b.append(text)
    return OK_VALUE

def _sb_append_sub(b: QStringBuilder, s: QString, start: QInt, size: QInt) -> QOk:
    st, sz = start.value, size.value
    if st < 0 or sz < 0 or st + sz > len(s.value):
        raise QuestException(STRING_ERROR_EXC)
    return _sb_append(b, s.value[st : st + sz])

def _sb_append_repeat(b: QStringBuilder, c: QChar, n: QInt) -> QOk:
    if n.value < 0:
        raise QuestException(STRING_ERROR_EXC)
    return _sb_append(b, c.value * n.value)

def _sb_to_string(b: QStringBuilder) -> QString:
    text = "".join(b.pieces)
    b.pieces = [text] if text else []
    return QString(text)

def _sb_clear(b: QStringBuilder) -> QOk:
    b.pieces.clear()
    b.length = 0
    return OK_VALUE


def _sb_append(b: QStringBuilder, text: str) -> QOk:
    b.append(text)
    return OK_VALUE


EXTERNAL_SYMBOLS: dict[str, Any] = {
    # Writer
    "(&quest_exc_writer_error)": WRITER_ERROR_EXC,
    "quest_exc_writer_error": WRITER_ERROR_EXC,
    "quest_writer_output": QWriter(sys.stdout, is_file=False),
    "quest_writer_err": QWriter(sys.stderr, is_file=False),
    "quest_writer_file": _writer_file,
    "quest_writer_put_string": _writer_put_string,
    "quest_writer_put_char": _writer_put_char,
    "quest_writer_put_substring": _writer_put_sub_string,
    "quest_writer_flush": _writer_flush,
    "quest_writer_close": _writer_close,

    # Reader
    "(&quest_exc_reader_error)": READER_ERROR_EXC,
    "quest_exc_reader_error": READER_ERROR_EXC,
    "quest_reader_input": QReader(sys.stdin, is_file=False),
    "quest_reader_file": _reader_file,
    "quest_reader_get_string": _reader_get_string,
    "quest_reader_get_substring": _reader_get_sub_string,
    "quest_reader_get_char": _reader_get_char,
    "quest_reader_more": _reader_more,
    "quest_reader_ready": _reader_ready,
    "quest_reader_close": _reader_close,

    # Conv
    "quest_conv_int": _conv_int,
    "quest_conv_real": _conv_real,
    "quest_conv_string": lambda s: QString(s.to_str() if isinstance(s, QString) else ""),
    "quest_conv_char": lambda c: QString(c.to_str() if isinstance(c, QChar) else ""),
    "quest_conv_bool": lambda b: QString("true" if getattr(b, "value", False) else "false"),
    "quest_conv_okay": lambda _: QString("ok"),

    # Ascii
    "(&quest_exc_ascii_error)": ASCII_ERROR_EXC,
    "quest_exc_ascii_error": ASCII_ERROR_EXC,
    "quest_ascii_val": _ascii_val,
    "quest_ascii_char": _ascii_char,

    # IntOp
    "(&quest_exc_int_error)": INT_ERROR_EXC,
    "quest_exc_int_error": INT_ERROR_EXC,
    "QUEST_INT_MIN": QInt(-(2**63)),
    "QUEST_INT_MAX": QInt(2**63 - 1),
    "quest_int_abs": lambda n: QInt(abs(n.value)),
    "quest_int_min": lambda a, b: QInt(min(a.value, b.value)),
    "quest_int_max": lambda a, b: QInt(max(a.value, b.value)),

    # RealOp
    "(&quest_exc_real_error)": REAL_ERROR_EXC,
    "quest_exc_real_error": REAL_ERROR_EXC,
    "QUEST_REAL_MIN": QReal(-sys.float_info.max),
    "QUEST_REAL_MAX": QReal(sys.float_info.max),
    "QUEST_REAL_POS_EPSILON": QReal(sys.float_info.epsilon),
    "QUEST_REAL_NEG_EPSILON": QReal(-sys.float_info.epsilon),
    "QUEST_REAL_EPSILON": QReal(2.220446049250313e-16),
    "QUEST_REAL_E": QReal(math.e),
    "QUEST_REAL_PI": QReal(math.pi),
    "quest_real_floor": lambda r: _real_to_int(math.floor(r.value) if math.isfinite(r.value) else r.value),
    "quest_real_round": lambda r: _real_to_int(_real_round(r.value)),
    "quest_real_from_int": lambda n: QReal(float(n.value)),
    "quest_real_div": _real_div,
    "quest_real_exp": _real_exp,
    "quest_real_log": _real_log,
    "quest_real_abs": lambda r: QReal(abs(r.value)),
    "quest_real_min": lambda a, b: a if a.value <= b.value else b,
    "quest_real_max": lambda a, b: a if a.value >= b.value else b,

    # Standard math functions
    "sin": lambda r: QReal(math.sin(r.value)),
    "cos": lambda r: QReal(math.cos(r.value)),
    "tan": lambda r: QReal(math.tan(r.value)),
    "asin": lambda r: QReal(math.asin(r.value)),
    "acos": lambda r: QReal(math.acos(r.value)),
    "atan": lambda r: QReal(math.atan(r.value)),
    "atan2": lambda y, x: QReal(math.atan2(y.value, x.value)),
    "exp": lambda r: QReal(math.exp(r.value)),
    "log": lambda r: QReal(math.log(r.value)),
    "sqrt": lambda r: QReal(math.sqrt(r.value)),
    "pow": lambda x, y: QReal(math.pow(x.value, y.value)),
    "floor": lambda r: QReal(math.floor(r.value)),
    "ceil": lambda r: QReal(math.ceil(r.value)),
    "round": lambda r: QReal(round(r.value)),
    "trunc": lambda r: QReal(math.trunc(r.value)),

    # StringOp
    "(&quest_exc_string_error)": STRING_ERROR_EXC,
    "quest_exc_string_error": STRING_ERROR_EXC,
    "quest_string_alloc": _string_new,
    "quest_string_length": lambda s: QInt(len(s.value)),
    "quest_string_is_empty": lambda s: QBool(len(s.value) == 0),
    "quest_string_get_char": _string_get_char,
    "quest_string_set_char": _string_set_char,
    "quest_string_get_sub": _string_get_sub,
    "quest_string_set_sub": _string_set_sub,
    "quest_string_concat": lambda s1, s2: QString(s1.value + s2.value),
    "quest_string_conc": _string_conc,
    "quest_string_cat_sub": _string_cat_sub,
    "quest_string_equal": lambda s1, s2: QBool(s1.value == s2.value),
    "quest_string_equal_sub": _string_equal_sub,
    "quest_string_precedes": lambda s1, s2: QBool(s1.value <= s2.value),
    "quest_string_precedes_sub": _string_precedes_sub,

    # Strutil (strutil.tryToReal has checked the syntax; float rounds correctly, as C's strtod does)
    "quest_strutil_to_real": lambda s: QReal(float(s.value)),

    # StringBuilder
    "quest_sb_new": QStringBuilder,
    "quest_sb_append_string": lambda b, s: _sb_append(b, s.value),
    "quest_sb_append_char": lambda b, c: _sb_append(b, c.value),
    "quest_sb_append_int": lambda b, n: _sb_append(b, _conv_int(n).value),
    "quest_sb_append_real": lambda b, r: _sb_append(b, _conv_real(r).value),
    "quest_sb_append_bool": lambda b, v: _sb_append(b, "true" if v.value else "false"),
    "quest_sb_append_word": lambda b, w: _sb_append(b, str(w.value & 0xFFFF_FFFF_FFFF_FFFF)),
    "quest_sb_append_sub": _sb_append_sub,
    "quest_sb_append_repeat": _sb_append_repeat,
    "quest_sb_clear": _sb_clear,
    "quest_sb_length": lambda b: QInt(b.length),
    "quest_sb_to_string": _sb_to_string,

    # ArrayOp
    "(&quest_exc_arrayOp_error)": ARRAY_OP_ERROR_EXC,
    "quest_exc_arrayOp_error": ARRAY_OP_ERROR_EXC,
    "quest_array_size": lambda arr: QInt(len(arr.elements)),

    # Word
    "(&quest_exc_word_error)": WORD_ERROR_EXC,
    "quest_exc_word_error": WORD_ERROR_EXC,
    "64": QInt(64),
    "quest_word_from_int": _word_from_int,
    "quest_word_to_int": _word_to_int,
    "quest_word_from_real_val": _word_from_real,
    "quest_word_to_real_val": _word_to_real,
    "quest_word_add": _word_add,
    "quest_word_sub": _word_sub,
    "quest_word_mul": _word_mul,
    "quest_word_div": _word_div,
    "quest_word_div_val": _word_div,
    "quest_word_mod": _word_mod,
    "quest_word_mod_val": _word_mod,
    "quest_word_not_bits": _word_not_bits,
    "quest_word_and_bits": _word_and_bits,
    "quest_word_or_bits": _word_or_bits,
    "quest_word_xor_bits": _word_xor_bits,
    "quest_word_shift": _word_shift,
    "quest_word_shift_val": _word_shift,
    "quest_word_rotate_val": _word_rotate,
    "quest_word_extract_val": _word_extract,
    "quest_word_replace_val": _word_replace,
    "quest_word_lt": _word_lt,
    "quest_word_le": _word_le,
    "quest_word_gt": _word_gt,
    "quest_word_ge": _word_ge,
    "quest_word_count_leading_zeros_val": _word_count_leading_zeros,
    "quest_word_count_trailing_zeros_val": _word_count_trailing_zeros,
    "quest_word_pop_count_val": _word_pop_count,
    "quest_word_get_bit_val": _word_get_bit,
    "quest_word_set_bit_val": _word_set_bit,
    "quest_word_clear_bit_val": _word_clear_bit,
    "quest_hash_mix": _quest_hash_mix,
    "quest_hash_combine": _quest_hash_combine,
    "quest_identity_hash": _quest_identity_hash,

    # System
    "(&quest_exc_system_error)": SYSTEM_ERROR_EXC,
    "quest_exc_system_error": SYSTEM_ERROR_EXC,
    "quest_system_args": QArray(tuple(QString(a) for a in sys.argv)),
    "quest_system_getenv": _system_getenv,
    "quest_system_current_directory": _system_current_directory,
    "quest_system_change_directory": _system_change_directory,
    "quest_system_list_directory": _system_list_directory,
    "quest_system_file_exists": _system_file_exists,
    "quest_system_is_file": _system_is_file,
    "quest_system_is_directory": _system_is_directory,
    "quest_system_make_directory": _system_make_directory,
    "quest_system_remove_file": _system_remove_file,
    "quest_system_remove_directory": _system_remove_directory,
    "quest_system_rename_file": _system_rename_file,
    "quest_system_exit": _system_exit,

    # Dynamic
    "(&quest_exc_dynamic_error)": DYNAMIC_ERROR_EXC,
    "quest_exc_dynamic_error": DYNAMIC_ERROR_EXC,
    "quest_dynamic_copy": _dynamic_copy,
    "quest_dynamic_intern": _dynamic_intern,
    "quest_dynamic_extern": _dynamic_extern,
}


def resolve_external_symbol(symbol: str) -> QValue:
    """Resolves an external C symbol into a Python QValue for interpreter evaluation."""
    clean = symbol.strip("(&)").strip()
    val = EXTERNAL_SYMBOLS.get(symbol) or EXTERNAL_SYMBOLS.get(clean)
    if val is None:
        raise QuestRuntimeError(f"Undefined external symbol '{symbol}' in interpreter")
    if callable(val) and not isinstance(val, QValue):
        return QBuiltinFun(symbol, val)
    return val


def set_system_args(args: list[str]) -> None:
    """Updates system.args with the provided argument list."""
    EXTERNAL_SYMBOLS["quest_system_args"] = QArray(tuple(QString(a) for a in args))
