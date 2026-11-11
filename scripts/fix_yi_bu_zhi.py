#!/usr/bin/env python3
"""Normalize 只/一/不 readings in example_pinyin to the dataset convention:

- measure 只 (after a numeral or demonstrative) -> zhī; adverb 只 'only' -> zhǐ
- 一: yī when counting/ordinal (after 第, after a number word) or standalone
  clause-final; otherwise sandhi: yí before an underlying tone-4 syllable,
  yì before tones 1/2/3
- 不: bú before an underlying tone-4 syllable, otherwise bù; 不 before 一 is
  always bù (一's own sandhi neutralizes the pair)

Usage: python scripts/fix_yi_bu_zhi.py file.jsonl [file.jsonl ...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pinyin_util as pu  # noqa: E402

NUM_PREV = set("一两三四五六七八九十百千万亿几这那哪某各每第")
COUNT_PREV = set("第十百千万亿一")


def target_readings(chars, syllables):
    """Compute new readings for 一/不/只. Returns {char_index: new_syllable}."""
    n = len(chars)
    out = {}

    def next_syllable_tone(i):
        """Underlying tone of the next spoken syllable after char i."""
        j = i + 1
        while j < n and syllables[j] == "":
            j += 1
        if j >= n:
            return None
        return pu.tone_of(syllables[j])

    for i, ch in enumerate(chars):
        if ch == "只":
            prev = chars[i - 1] if i > 0 else None
            out[i] = "zhī" if (prev in NUM_PREV) else "zhǐ"
        elif ch == "一":
            prev = chars[i - 1] if i > 0 else None
            # skip a merged 儿 that carries no syllable
            j = i + 1
            while j < n and syllables[j] == "":
                j += 1
            nxt = chars[j] if j < n else None
            tone_idx = j
            if nxt == "不":
                # 一 followed by 不: use the tone of the syllable after 不
                k = j + 1
                while k < n and syllables[k] == "":
                    k += 1
                tone_idx = k
                nxt = chars[k] if k < n else None
            if prev in COUNT_PREV:
                out[i] = "yī"  # counting / ordinal
            elif nxt is None:
                out[i] = "yī"  # clause-final
            elif pu.tone_of(syllables[tone_idx]) == "4":
                out[i] = "yí"
            else:
                out[i] = "yì"
        elif ch == "不":
            j = i + 1
            while j < n and syllables[j] == "":
                j += 1
            nxt = chars[j] if j < n else None
            if nxt is None:
                out[i] = "bù"
            elif nxt == "一":
                out[i] = "bù"
            elif pu.tone_of(syllables[j]) == "4":
                out[i] = "bú"
            else:
                out[i] = "bù"
    return out


def apply_same_reading(chars, syllables):
    """Current readings of 一/不/只 (used to decide 不 before 一)."""
    cur = {}
    for i, ch in enumerate(chars):
        if ch in "一不只" and syllables[i]:
            cur.setdefault(ch, []).append(pu.tone_of(syllables[i]))
    return cur


def fix_line(obj):
    zh = obj["example_zh"]
    py = obj["example_pinyin"]
    raw = [c for c in zh if pu._HANZI.match(c)]
    syllables, locs = pu.align(py, zh)
    readings = target_readings(raw, syllables)
    if not readings:
        return 0
    tokens = py.split()
    cores = [pu.clean_token(t) for t in tokens]
    # filtered index (as used by align) -> raw token index
    fil2raw = [i for i, c in enumerate(cores) if c]
    parts = {}
    for k, ridx in enumerate(fil2raw):
        parts[k] = pu.split_syllables(cores[ridx])
    edits = {}  # filtered token index -> list of syllable strings (rebuilt)
    for i, new_syl in readings.items():
        loc = locs[i]
        if loc is None:
            continue
        ti, si = loc
        if ti not in edits:
            edits[ti] = [s for s, _cov in parts[ti]]
        old = edits[ti][si]
        edits[ti][si] = _match_case(old, new_syl)
    changed = 0
    out_tokens = []
    for k, ridx in enumerate(fil2raw):
        t = tokens[ridx]
        if k not in edits:
            out_tokens.append(t)
            continue
        new_core = "".join(edits[k])
        # re-attach punctuation stripped by clean_token
        pre = t[:t.index(cores[k])] if cores[k] in t else ""
        suf = t[t.index(cores[k]) + len(cores[k]):] if pre != t else ""
        new_tok = pre + new_core + suf
        if new_tok != t:
            changed += 1
        out_tokens.append(new_tok)
    # keep tokens that were not touched (pure punctuation or untouched)
    result = []
    ki = 0
    for i, t in enumerate(tokens):
        if ki < len(fil2raw) and fil2raw[ki] == i:
            result.append(out_tokens[ki] if ki < len(out_tokens) else t)
            ki += 1
        else:
            result.append(t)
    obj["example_pinyin"] = " ".join(result)
    return changed


def _match_case(old, new):
    if old and old[0].isupper():
        return new[0].upper() + new[1:]
    return new


def main():
    total_tokens, total_lines = 0, 0
    for path in sys.argv[1:]:
        lines = [l for l in open(path, encoding="utf-8") if l.strip()]
        out, errors = [], 0
        n_tok = 0
        for ln in lines:
            o = json.loads(ln)
            try:
                n_tok += fix_line(o)
            except ValueError as e:
                errors += 1
                print(f"  SKIP {o['id']}: {e}")
            out.append(json.dumps(o, ensure_ascii=False))
        Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")
        total_tokens += n_tok
        total_lines += len(lines)
        print(f"{path}: {len(lines)} lines, {n_tok} tokens changed, {errors} errors")
    print(f"TOTAL {total_lines} lines, {total_tokens} tokens changed")


if __name__ == "__main__":
    main()
