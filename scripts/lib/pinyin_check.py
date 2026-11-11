"""Cross-checks of official HSK syllabus pinyin against pypinyin and the
GF 0025-2021 pinyin in raw/hsk30, producing review.csv rows.

Comparison strategy: the official string is aligned syllable-by-syllable to
the hanzi (lib.pinyin). pypinyin emits exactly one syllable per character,
so the two readings are compared index-aligned, letter-by-letter and
tone-by-tone. GF 0025-2021 strings are aligned with the same DP, seeded
with the readings the official pinyin uses.
"""

import pypinyin

from . import pinyin as P

_TONE_DIGITS = {"̄": "1", "́": "2", "̌": "3", "̀": "4"}


def _letters(s):
    """Comparable letter form: lowercase, tone marks stripped, separators
    gone, ü normalized to v (pypinyin's TONE3 convention)."""
    out = []
    for c in P.strip_tone_marks(s.lower()):
        if "a" <= c <= "z":
            out.append(c)
        elif c == "ü":
            out.append("v")
    return "".join(out)


def _num_letters(s):
    """Letters + tone digits, separators removed, ü normalized to v."""
    out = []
    for c in s.lower():
        if "a" <= c <= "z" or c.isdigit():
            out.append("v" if c == "ü" else c)
    return "".join(out)


def pypinyin_syllables(word):
    """pypinyin phrase-mode reading: list of numbered syllables, one per char."""
    return pypinyin.lazy_pinyin(
        word, style=pypinyin.Style.TONE3, neutral_tone_with_five=True
    )


def pypinyin_numbered(word):
    return " ".join(pypinyin_syllables(word))


def _gf_candidates(hanzi, official_syls):
    """Char candidates = pypinyin readings + readings the official pinyin
    uses, so GF 0025-2021 strings align to the same word."""
    extra = {}
    for syl in official_syls:
        ci = syl.get("char_index")
        if ci is None or ci >= len(hanzi):
            continue
        t = P.strip_tone_marks(P.nfc(syl["text"]).lower())
        extra.setdefault(hanzi[ci], set()).update({t, syl["text"].lower()})
    return lambda ch: P.candidates(ch) | extra.get(ch, set())


def _align_with(p, hanzi, cand_fn):
    """P._align_simple variant driven by a custom candidate function.

    Handles erhua suffix ('-r' after the final syllable) and
    '/'-separated alternative readings (each aligned to the full hanzi).
    """
    def align_one(seg, hz):
        stripped_r = False
        if (
            hz.endswith("儿")
            and seg.endswith("r")
            and len(seg) > 1
            and not seg.endswith("’r")
        ):
            trial = _spans(seg[:-1], hz[:-1], cand_fn)
            if trial is not None:
                return trial, hz[:-1], True
        return _spans(seg, hz, cand_fn), hz, False

    if "/" in p:
        syls = None
        for seg in p.split("/"):
            seg = seg.strip()
            spans, hz_used, _ = align_one(seg, hanzi)
            if spans is None:
                raise ValueError(f"cannot align {p!r}")
            part = [
                {
                    "text": seg[s:e2],
                    "tone": P.tone_of(seg[s:e2]),
                    "numbered": P.numbered(seg[s:e2]),
                    "erhua": False,
                    "char_index": ci,
                    "start": s,
                    "end": e2,
                }
                for ci, s, e2 in spans
            ]
            if syls is None:
                syls = part
        return syls

    spans, hz_used, stripped_r = align_one(p.strip(), hanzi)
    if spans is None:
        raise ValueError(f"cannot align {p!r}")
    syls = []
    for ci, s, e2 in spans:
        text = p[s:e2]
        syls.append(
            {
                "text": text,
                "tone": P.tone_of(text),
                "numbered": P.numbered(text),
                "erhua": False,
                "char_index": ci,
                "start": s,
                "end": e2,
            }
        )
    return syls


def _spans(p, hanzi, cand_fn):
    chunks = []
    cur, cur_start = "", 0
    for i, ch in enumerate(p):
        if ch in P.SEPARATORS:
            if cur:
                chunks.append((cur, cur_start))
                cur = ""
        else:
            if not cur:
                cur_start = i
            cur += ch
    if cur:
        chunks.append((cur, cur_start))

    def match_len(ci, chunk):
        cands = cand_fn(hanzi[ci])
        return [e for e in range(len(chunk), 0, -1) if chunk[:e].lower() in cands]

    return P._align_chunks(chunks, hanzi, match_len)


def _sense_note(rec):
    """Context for GF disagreements on words the 2025 syllabus splits into
    senses (GF 0025-2021 lists the word once, under one reading)."""
    if rec.get("multi"):
        return (
            f" (2025 syllabus lists {rec['hanzi']} as {rec['multi']} entries "
            "with different readings; GF 0025-2021 lists it once)"
        )
    return ""


def compare(rec, parsed):
    """Return review rows for one word record.

    rec needs: id, no, hanzi (cleaned), level, pinyin (official),
    gf2021_pinyin. parsed is P.align_pinyin(rec['pinyin'], rec['hanzi']).
    """
    rows = []
    hz = rec["hanzi"]
    syls = parsed["syllables"]
    pp = pypinyin_numbered(hz)

    base = {
        "id": rec["id"],
        "no": rec["no"],
        "hanzi": hz,
        "level": rec["level"],
        "official_pinyin": rec["pinyin"],
    }

    def row(issue_type, note, status="open", suggested=None):
        r = dict(base)
        r.update(
            {
                "pypinyin": pp,
                "gf2021_pinyin": rec.get("gf2021_pinyin"),
                "issue_type": issue_type,
                "note": note,
                "suggested": suggested,
                "status": status,
            }
        )
        rows.append(r)

    is_erhua = any(s["erhua"] for s in syls) or hz.endswith("儿")
    has_neutral = any(s["tone"] == 5 for s in syls)
    pp_syls = pypinyin_syllables(hz)

    # --- official vs pypinyin, syllable by syllable ----------------------
    # erhua: official has one syllable fewer than characters; compare the
    # shared ones and let the 儿 difference fall to the erhua row below.
    cmp_n = len(syls) if is_erhua else min(len(syls), len(pp_syls))
    letter_diffs = []
    tone_diffs = []
    if not is_erhua and len(syls) != len(pp_syls):
        row("other", f"syllable-count mismatch: official {len(syls)} vs pypinyin {len(pp_syls)}")
    for i in range(cmp_n):
        o, q = syls[i], pp_syls[i]
        o_letters = _letters(o["text"])
        q_letters = _letters(q)
        if o_letters != q_letters:
            letter_diffs.append((i, o_letters, q_letters))
        elif o["numbered"].lower().replace("ü", "v") != q:
            tone_diffs.append((i, o["numbered"], q))
    if letter_diffs:
        det = "; ".join(
            f"char {hz[syls[i]['char_index']] if syls[i]['char_index'] is not None and syls[i]['char_index'] < len(hz) else '?'}: official {a} vs pypinyin {b}"
            for i, a, b in letter_diffs
        )
        if "/" in rec["pinyin"] and any(
            _letters(alt["text"]) == _letters(pp) for alt in parsed["alternatives"]
        ):
            pass  # an official alternative matches pypinyin outright
        elif is_erhua:
            row("erhua", f"official erhua suffix vs pypinyin 'er': {det}", status="info")
        else:
            row("disagreement", f"letters differ: {det}")
    elif tone_diffs:
        det = "; ".join(
            f"position {i}: official {a} vs pypinyin {b}" for i, a, b in tone_diffs
        )
        if is_erhua:
            row("erhua", f"tone differs at erhua syllable: {det}", status="info")
        elif has_neutral:
            row("neutral_tone", f"neutral-tone assignment differs: {det}")
        else:
            row("disagreement", f"tones differ: {det}")

    # --- GF 0025-2021 ----------------------------------------------------
    gfp = rec.get("gf2021_pinyin")
    if gfp:
        try:
            gsyls = _align_with(gfp, hz, _gf_candidates(hz, syls))
            if len(gsyls) != len(syls):
                row(
                    "other",
                    f"gf2021 pinyin {gfp!r} aligns to {len(gsyls)} syllables "
                    f"vs official {len(syls)}",
                )
            else:
                letter_diffs = [
                    (i, _letters(s["text"]), _letters(g["text"]))
                    for i, (s, g) in enumerate(zip(syls, gsyls))
                    if _letters(s["text"]) != _letters(g["text"])
                ]
                tone_diffs = []
                for i, (s, g) in enumerate(zip(syls, gsyls)):
                    if _letters(s["text"]) == _letters(g["text"]) and P.numbered(
                        s["text"]
                    ).lower().replace("ü", "v") != P.numbered(g["text"]).lower().replace("ü", "v"):
                        tone_diffs.append(
                            (i, s["numbered"], P.numbered(g["text"]))
                        )
                if letter_diffs:
                    det = "; ".join(
                        f"position {i}: official {a} vs gf2021 {b}"
                        for i, a, b in letter_diffs
                    )
                    row(
                        "disagreement",
                        f"letters differ vs GF 0025-2021: {det}"
                        + _sense_note(rec),
                    )
                elif tone_diffs:
                    det = "; ".join(
                        f"position {i}: official {a} vs gf2021 {b}"
                        for i, a, b in tone_diffs
                    )
                    ci = syls[tone_diffs[0][0]].get("char_index")
                    ch = hz[ci] if ci is not None and ci < len(hz) else ""
                    if syls[tone_diffs[0][0]]["tone"] == 5 or P.numbered(
                        gsyls[tone_diffs[0][0]]["text"]
                    ).endswith("5"):
                        row(
                            "neutral_tone",
                            f"gf2021 marks tones differently on a neutral-tone "
                            f"word: {det} (GF spells full tones)",
                            status="info",
                        )
                    elif ch in ("一", "不"):
                        row(
                            "sandhi",
                            f"gf2021 writes the underlying tone where the "
                            f"official writes the sandhi surface tone: {det}",
                            status="info",
                        )
                    else:
                        row(
                            "disagreement",
                            f"tones differ vs GF 0025-2021: {det}" + _sense_note(rec),
                        )
        except (ValueError, KeyError) as e:
            row("other", f"gf2021 pinyin {gfp!r} not alignable: {e}")

    # --- info rows -------------------------------------------------------
    if "/" in rec["pinyin"]:
        row("variant", "official lists alternative readings", status="info")
    if is_erhua and not letter_diffs:
        row("erhua", "erhua word (official pinyin has suffix -r)", status="info")
    if has_neutral and not tone_diffs and not letter_diffs:
        row("neutral_tone", "word contains neutral-tone syllable(s)", status="info")

    # 一/不 sandhi
    ut = P.underlying_tones(syls, hz)
    surf = P.sandhi_surface(ut, syls, hz)
    yibu_idx = [
        i
        for i, s in enumerate(syls)
        if s.get("char_index") is not None
        and s["char_index"] < len(hz)
        and hz[s["char_index"]] in ("一", "不")
    ]
    if yibu_idx:
        row("sandhi", "一/不 sandhi word", status="info")
        written = [s["tone"] for s in syls]
        diffs = [
            f"position {i}: official writes tone {written[i]}, rule-derived "
            f"surface tone {surf[i]}"
            for i in yibu_idx
            if written[i] != 5 and written[i] != surf[i]
        ]
        if diffs:
            row(
                "sandhi",
                "; ".join(diffs)
                + " (official may keep tone 1/4 in serial-numeral or "
                "lexicalized use; dataset keeps official pinyin)",
            )

    # polyphone: official reading differs from pypinyin's default for a char
    if not letter_diffs:
        for s in syls:
            ci = s.get("char_index")
            if ci is None or ci >= len(hz) or s["erhua"]:
                continue
            ch = hz[ci]
            if ch in ("一", "不"):
                continue
            heteronyms = pypinyin.pinyin(ch, heteronym=True)
            if not heteronyms or len(heteronyms[0]) <= 1:
                continue  # not a polyphonic character at all
            default = pp_syls[ci] if ci < len(pp_syls) else None
            mine = P.numbered(s["text"]).lower().replace("ü", "v")
            if default and mine != default:
                row(
                    "polyphone",
                    f"character {ch} read {mine} here, pypinyin default "
                    f"{default} (context-dependent)",
                    status="info",
                )
                break
    return rows
