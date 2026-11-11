"""Pinyin utilities: syllable alignment, numbered forms, tone patterns, sandhi.

The official HSK syllabus pinyin strings are aligned syllable-by-syllable to
the word's hanzi using the per-char candidate readings from pypinyin's char
dict (MIT). Alignment (rather than pure string segmentation) resolves
ambiguous splits such as 唱歌 chànggē -> chàng + gē vs chàng + ē, and
covers neutral-tone forms (di, ge, xi, ...) that are not separate entries
in the char dict. A lone trailing "r" after the final syllable is treated
as an erhua suffix when the word ends in 儿.
"""

import unicodedata

from pypinyin import pinyin_dict
from pypinyin.contrib.tone_convert import to_tone, to_tone3

# All tone-marked / plain syllable forms known to pypinyin (NFC).
SYLLABLES = set()
for _v in pinyin_dict.pinyin_dict.values():
    for _s in _v.split(","):
        if _s:
            SYLLABLES.add(unicodedata.normalize("NFC", _s))

# Separators inside an official pinyin string that are not part of syllables.
SEPARATORS = set(" -'’∥/")

TONE_DIACRITIC = {
    "̄": 1,  # macron
    "́": 2,  # acute
    "̌": 3,  # caron
    "̀": 4,  # grave
}


def nfc(s):
    return unicodedata.normalize("NFC", s)


_TONE_DIACRITICS = {"̄", "́", "̌", "̀"}


def strip_tone_marks(s):
    """Remove tone diacritics but keep the diaeresis of ü ('nǚ' -> 'nü')."""
    out = []
    for c in unicodedata.normalize("NFD", s):
        if unicodedata.category(c) == "Mn" and c in _TONE_DIACRITICS:
            continue
        out.append(c)
    return unicodedata.normalize("NFC", "".join(out))


def tone_of(s):
    """Tone number of a syllable ('hǎo'->3, 'qi'->5, erhua suffix 'r'->None).

    Neutral-tone syllables have no tone mark: tone 5.
    """
    s = s.strip()
    if s == "r":
        return None
    marks = [
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) == "Mn"
    ]
    for c in marks:
        if c in TONE_DIACRITIC:
            return TONE_DIACRITIC[c]
    # tone marks that do not decompose (e.g. 'm̄') via NFC-keyed lookup
    return 5


def numbered(s):
    """'hǎo' -> 'hao3', 'qi' -> 'qi5', erhua suffix 'r' -> 'r'.

    Output is lowercase (pypinyin's to_tone3 does not handle uppercase).
    """
    if s == "r":
        return "r"
    n = to_tone3(nfc(s).lower())
    if n and not n[-1].isdigit():
        n += "5"
    return n


# Special-case readings: sandhi surface tones that pypinyin's char dict
# does not list, plus erhua suffix for 儿.
_EXTRA_READINGS = {
    "一": {"yī", "yí", "yì", "yi"},
    "不": {"bù", "bú", "bu"},
    "儿": {"er", "ér", "ěr", "èr"},
}

# readings -> candidate set per char, with neutralized variants added
_CANDIDATES = {}


def candidates(ch):
    if ch in _CANDIDATES:
        return _CANDIDATES[ch]
    raw = pinyin_dict.pinyin_dict.get(ord(ch))
    cands = set()
    if raw:
        for s in raw.split(","):
            s = nfc(s)
            cands.add(s)
            # allow the neutral-tone (toneless) variant of any reading
            cands.add(strip_tone_marks(s))
    cands |= _EXTRA_READINGS.get(ch, set())
    _CANDIDATES[ch] = cands
    return cands


def align_pinyin(p, hanzi):
    """Align an official pinyin string to its hanzi.

    Handles '/'-separated alternative readings (e.g. 谁 shéi/shuí) by
    aligning each alternative to the full hanzi independently. Returns a
    dict: {alternatives: [{text, syllables}], syllables: <first alt's>},
    or raises ValueError. Syllables carry {text, tone, numbered, erhua,
    char_index, start, end} with offsets into the full string.
    """
    p = p.strip()
    if "/" in p:
        alts = []
        pos = 0
        for seg in p.split("/"):
            seg_pos = p.index(seg, pos)
            try:
                syls = _align_simple(seg, hanzi, seg_pos)
            except ValueError as e:
                raise ValueError(f"in {p!r}: {e}")
            alts.append({"text": seg, "syllables": syls})
            pos = seg_pos + len(seg)
        return {
            "alternatives": alts,
            "syllables": alts[0]["syllables"],
            "numbered": "/".join(numbered_string(seg, a["syllables"]) for seg, a in zip(p.split("/"), alts)),
        }
    syls = _align_simple(p, hanzi, 0)
    return {
        "alternatives": [{"text": p, "syllables": syls}],
        "syllables": syls,
        "numbered": numbered_string(p, syls),
    }


def _align_simple(p, hanzi, offset=0):
    """Align one alternative (no '/') to hanzi; offsets shifted by `offset`."""
    p = p.strip()
    if not p:
        return []

    chunks = []  # (text, start_index_in_string)
    cur = ""
    cur_start = 0
    for i, ch in enumerate(p):
        if ch in SEPARATORS:
            if cur:
                chunks.append((cur, cur_start + offset))
                cur = ""
        else:
            if not cur:
                cur_start = i
            cur += ch
    if cur:
        chunks.append((cur, cur_start + offset))

    def nfc_lower(s):
        return nfc(s).lower()

    def match_len(ci, chunk):
        """Lengths of chunk prefixes that are readings of hanzi[ci]."""
        cands = candidates(hanzi[ci])
        out = []
        for end in range(len(chunk), 0, -1):
            if nfc_lower(chunk[:end]) in cands:
                out.append(end)
        return out

    # erhua handling: strip a trailing 'r' from the last chunk and attach it
    # to the final syllable, with the final 儿 consuming nothing.
    erhua_suffix = False
    work_chunks = list(chunks)
    align_hanzi = hanzi
    if (
        hanzi.endswith("儿")
        and chunks
        and chunks[-1][0].endswith("r")
        and len(chunks[-1][0]) > 1
    ):
        trial = chunks[-1][0][:-1]
        test = _align_chunks(
            work_chunks[:-1] + [(trial, chunks[-1][1])], hanzi[:-1], match_len
        )
        if test is not None:
            erhua_suffix = True
            work_chunks = work_chunks[:-1] + [(trial, chunks[-1][1])]
            align_hanzi = hanzi[:-1]

    spans = _align_chunks(work_chunks, align_hanzi, match_len)
    if spans is None:
        raise ValueError(f"cannot align pinyin {p!r} to hanzi {hanzi!r}")

    syllables = []
    for k, (char_idx, start, end) in enumerate(spans):
        text = p[start:end]
        # with the erhua suffix stripped from the aligned text, the trailing
        # 'r' of the official string stays literal in numbered output
        is_erhua = erhua_suffix and k == len(spans) - 1
        syllables.append(
            {
                "text": text,
                "tone": tone_of(text),
                "numbered": numbered(text),
                "erhua": is_erhua,
                "char_index": char_idx,
                "start": start,
                "end": end,
            }
        )
    return syllables


def _align_chunks(chunks, hanzi, match_len):
    """DP across chunks; each chunk must match hanzi[ci:] in order.

    Returns list of (char_index, abs_start, abs_end) or None.
    """
    # build flat char list; track per-chunk char ranges
    total_chars = len(hanzi)
    memo = {}

    def rec(ck, ci, pos):
        if ck == len(chunks):
            return [] if ci == total_chars else None
        key = (ck, ci, pos)
        if key in memo:
            return memo[key]
        text, base = chunks[ck]
        res = None
        if pos == len(text):
            res = rec(ck + 1, ci, 0)
        elif ci < total_chars:
            for end in match_len(ci, text[pos:]):
                nxt = rec(ck, ci + 1, pos + end)
                if nxt is not None:
                    res = [(ci, base + pos, base + pos + end)] + nxt
                    break
            # a 儿 with no syllable of its own (erhua suffix that was not
            # stripped, e.g. when the 儿 is not word-final in the string)
            if res is None and hanzi[ci] == "儿":
                nxt = rec(ck, ci + 1, pos)
                if nxt is not None:
                    res = [(ci, base + pos, base + pos)] + nxt
        memo[key] = res
        return res

    out = rec(0, 0, 0)
    return out


def numbered_string(p, syllables):
    """Numbered rendering of the official string, preserving separators."""
    parts = []
    cursor = 0
    for syl in syllables:
        s, e = syl["start"], syl["end"]
        if s > cursor:
            parts.append(p[cursor:s])
        parts.append(syl["numbered"])
        cursor = e
    parts.append(p[cursor:])
    return "".join(parts)


def underlying_tones(syllables, hanzi):
    """Dictionary tones per syllable; an erhua base syllable keeps its own
    tone; 一 normalized to 1 and 不 to 4 (official may write the surface
    tone)."""
    tones = []
    for syl in syllables:
        t = syl["tone"]
        ci = syl["char_index"]
        if ci < len(hanzi) and hanzi[ci] in ("一", "不") and t in (1, 2, 4):
            t = 1 if hanzi[ci] == "一" else 4
        tones.append(t)
    return tones


def tone_pattern(syllables, hanzi):
    """Underlying dictionary tones joined with '-' (5 = neutral)."""
    return "-".join(str(t) for t in underlying_tones(syllables, hanzi))


def sandhi_surface(tones, syllables=None, hanzi=None):
    """Rule-derived spoken tones.

    - third-tone sandhi: a 3 followed by another 3 (left-to-right greedy)
      becomes 2;
    - 一 (the character 一, not last): next tone 4 -> 2; next tone 1/2/3
      -> 4; next tone 5/none -> stays 1;
    - 不 (the character 不, not last): next tone 4 -> 2; else stays 4.

    The 一/不 rules apply only where syllables/hanzi identify the character
    as 一 or 不; when syllables is None they are keyed off the tone value
    alone (1 -> treated as 一, 4 -> treated as 不), which callers should
    avoid. Erhua suffix syllables keep their base tone and do not trigger
    sandhi.
    """
    out = list(tones)
    n = len(out)
    for i in range(n):
        t = out[i]
        is_yi = is_bu = False
        if syllables is not None and hanzi is not None:
            ci = syllables[i].get("char_index")
            if ci is not None and ci < len(hanzi):
                is_yi = hanzi[ci] == "一"
                is_bu = hanzi[ci] == "不"
        if t == 3 and i + 1 < n and out[i + 1] == 3:
            out[i] = 2
        elif i + 1 < n:
            nt = out[i + 1]
            if is_yi or (syllables is None and t == 1):
                if nt == 4:
                    out[i] = 2
                elif nt in (1, 2, 3):
                    out[i] = 4
            elif is_bu or (syllables is None and t == 4):
                if nt == 4:
                    out[i] = 2
    return out


def pypinyin_numbered(word):
    """pypinyin phrase-mode reading of a word, tone3, neutral = 5."""
    import pypinyin

    try:
        py = pypinyin.pinyin(
            word,
            style=pypinyin.Style.TONE3,
            neutral_tone_with_five=True,
            heteronym=False,
            errors="ignore",
        )
        return " ".join(p[0] for p in py)
    except Exception:
        return None


def roundtrip_mismatch(numbered_s, official):
    """True if numbered -> tone marks does not reproduce the official string."""
    marks = to_tone(numbered_s)
    if strip_tone_marks(marks).lower() != strip_tone_marks(official).lower():
        return True
    return False
