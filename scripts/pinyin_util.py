#!/usr/bin/env python3
"""Shared helpers for example_pinyin QA: syllable splitting, char alignment,
tone detection. Used by fix_yi_bu_zhi.py and example_pinyin_audit.py."""
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import content_check as ccheck  # noqa: E402

_HANZI = ccheck._hanzi
_TABLE = None

# full syllable 儿 in 儿子/女儿; everywhere else a trailing 儿 merges (儿化)
FULL_ER_PAIRS = {"女儿"}
FULL_ER_NEXT = {"子"}  # 儿子

_TONE_COMB = {"̄": "1", "́": "2", "̌": "3", "̀": "4"}


def tone_of(syllable):
    """Tone number of a tone-marked syllable: '1'-'4', '5' for neutral."""
    for ch in unicodedata.normalize("NFD", syllable):
        if ch in _TONE_COMB:
            return _TONE_COMB[ch]
    return "5"


def load_table():
    global _TABLE
    if _TABLE is None:
        _TABLE = ccheck._load_syllables()
    return _TABLE


def _next_base_end(token, i):
    """End index (exclusive) of the base-letter run starting at i: the base
    char plus any following combining marks, stopping before punctuation."""
    import unicodedata
    j = i + 1
    while j < len(token) and unicodedata.combining(token[j]):
        j += 1
    return j


def split_syllables(token):
    """Split a pinyin token into (syllable, covers_two_chars) pairs, keeping
    the original tone marks. A trailing -r that would otherwise not parse is
    treated as a merged 儿 suffix (zhèr, yìdiǎnr) and folded into the last
    syllable. Returns None if the token cannot be parsed."""
    table = load_table()
    stripped = []  # plain letters, one entry per base letter
    spans = []     # (start, end) slices into token for each stripped letter
    i = 0
    while i < len(token):
        ch = token[i]
        if ch == "'":
            j = i + 1
            while j < len(token) and not _is_base(token[j]):
                j += 1
            if j < len(token):
                spans.append((i, _next_base_end(token, j)))
                stripped.append(_base_letter(token[j]))
                i = _next_base_end(token, j)
                continue
            i += 1
            continue
        if _is_base(ch):
            end = _next_base_end(token, i)
            spans.append((i, end))
            stripped.append(_base_letter(ch))
            i = end
            continue
        i += 1
    s = "".join(stripped)
    if not s:
        return []
    for attempt, r_merged in ((s, False),
                              (s[:-1] if s.endswith("r") else None, True)):
        if not attempt:
            continue
        parsed = _parse(attempt, table)
        if parsed is None:
            continue
        out, pos = [], 0
        for k, syl in enumerate(parsed):
            start = sum(len(x) for x in stripped[:pos])
            end = start + len(syl)
            sub = token[spans[start][0]:spans[end - 1][1]]
            pos += len(syl)
            covers = r_merged and k == len(parsed) - 1
            if covers:
                sub = token[spans[start][0]:len(token)]
            out.append((sub, covers))
        return out
    return None


def _is_base(ch):
    import unicodedata
    d = unicodedata.normalize("NFD", ch)
    return len(d) >= 1 and d[0].isalpha() and d[0].isascii()


def _base_letter(ch):
    import unicodedata
    return unicodedata.normalize("NFD", ch)[0].lower()


def _parse(s, table):
    if not s:
        return []
    for ln in range(min(6, len(s)), 0, -1):
        if s[:ln] in table:
            rest = _parse(s[ln:], table)
            if rest is not None:
                return [s[:ln]] + rest
    return None


def is_merged_er(prev_char, char, next_char):
    """True when this 儿 is an r-colored suffix merged into the previous
    syllable; False when it is a full syllable (儿子, 女儿)."""
    if char != "儿":
        return False
    if prev_char is None:
        return False
    if next_char in FULL_ER_NEXT:
        return False
    if prev_char + char in FULL_ER_PAIRS:
        return False
    return True


def hanzi_chars_with_er(zh):
    """Hanzi chars of zh, with merged-儿 characters dropped (they share the
    previous syllable). Returns (chars, merged_flags)."""
    raw = [c for c in zh if _HANZI.match(c)]
    chars, merged = [], []
    for i, c in enumerate(raw):
        prev = raw[i - 1] if i > 0 else None
        nxt = raw[i + 1] if i + 1 < len(raw) else None
        if is_merged_er(prev, c, nxt):
            continue
        chars.append(c)
        merged.append(False)
    return chars, merged


_TOKEN_CLASS = (r"A-Za-züÜ"
                r"ĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ"
                r"āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ''")


def clean_token(t):
    """Strip punctuation attached to a pinyin token, keeping letters, tone
    marks, and apostrophes."""
    return re.sub(r"^[^%s]+|[^%s]+$" % (_TOKEN_CLASS, _TOKEN_CLASS), "", t)


def align(pinyin, zh):
    """Map each hanzi char of zh (raw order) to a syllable from pinyin.
    Merged-儿 chars get syllable '' and loc None. Returns (syllables, locs)
    with one entry per raw hanzi char. Raises ValueError on misalignment."""
    raw = [c for c in zh if _HANZI.match(c)]
    merged = []
    for i, c in enumerate(raw):
        prev = raw[i - 1] if i > 0 else None
        nxt = raw[i + 1] if i + 1 < len(raw) else None
        merged.append(is_merged_er(prev, c, nxt))
    tokens = [clean_token(t) for t in pinyin.split() if clean_token(t)]
    per_tok = []
    for tok in tokens:
        parts = split_syllables(tok)
        if parts is None:
            raise ValueError("unparseable token %r" % tok)
        per_tok.append(parts)
    syllables, locs = [], []
    ti, si = 0, 0
    for i, ch in enumerate(raw):
        if merged[i]:
            syllables.append("")
            locs.append(None)
            continue
        while ti < len(per_tok) and si >= len(per_tok[ti]):
            ti += 1
            si = 0
        if ti >= len(per_tok):
            raise ValueError("ran out of syllables at char %d (%s)" % (i, ch))
        syl, _covers = per_tok[ti][si]
        syllables.append(syl)
        locs.append((ti, si))
        si += 1
    if ti != len(per_tok) - 1 or si != len(per_tok[ti]):
        raise ValueError("leftover syllables after %d chars" % len(raw))
    return syllables, locs
