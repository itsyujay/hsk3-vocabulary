#!/usr/bin/env python3
"""Audit example_pinyin against pypinyin phrase-mode readings.

For every content line, align the tone-marked syllables of example_pinyin to
the hanzi of example_zh and compare with pypinyin (Style.TONE). Differences
are reported only for polyphonic characters; a neutral-vs-marked difference
with the same letters is tolerated. Output: data/content/pinyin_audit.csv

Usage: python scripts/example_pinyin_audit.py [file.jsonl ...]
       (default: data/content/L1-L4)
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pinyin_util as pu  # noqa: E402
import content_check as ccheck  # noqa: E402


def cc_strip(s):
    return ccheck._strip_marks(pu.clean_token(s)).lower()

POLYPHONES = set("只着了得地的还长行重好为种少数觉都发干差处调教乐量当"
                 "相应中正难空散假背落和华降传结系漂冲场转等")

ROOT = Path(__file__).resolve().parents[1]


def pypinyin_syllables(zh):
    from pypinyin import lazy_pinyin, Style
    items = lazy_pinyin(zh, style=Style.TONE)
    ref = []
    for it in items:
        if pu.clean_token(it):
            ref.append(it)
    return ref


def compare(zh, my_syls, ref_syls):
    """Yield (char, my, ref) mismatches on polyphonic chars."""
    raw = [c for c in zh if pu._HANZI.match(c)]
    ri = 0
    for i, ch in enumerate(raw):
        if ch == "儿" and my_syls[i] == "":
            # merged 儿: pypinyin spells a full ér/r syllable; tolerate
            if ri < len(ref_syls) and pu.tone_of(ref_syls[ri]) == "5" \
                    or pu.clean_token(ref_syls[ri]).lower() in ("er", "r") \
                    or ref_syls[ri].endswith("ér") or ref_syls[ri] == "ér":
                ri += 1
            continue
        if ri >= len(ref_syls):
            return
        mine, ref = my_syls[i], ref_syls[ri]
        ri += 1
        if not mine or not ref or ch not in POLYPHONES:
            continue
        lm, lr = pu.tone_of(mine), pu.tone_of(ref)
        same_letters = (cc_strip(mine) == cc_strip(ref))
        if same_letters and (lm == "5" or lr == "5" or lm == lr):
            continue
        if not same_letters or lm != lr:
            yield ch, mine, ref


def main():
    files = sys.argv[1:] or [str(ROOT / f"data/content/L{n}.jsonl") for n in (1, 2, 3, 4)]
    rows, errors, checked = [], 0, 0
    for path in files:
        level = Path(path).stem.lstrip("L")
        for ln in open(path, encoding="utf-8"):
            if not ln.strip():
                continue
            o = json.loads(ln)
            checked += 1
            try:
                my_syls, _ = pu.align(o["example_pinyin"], o["example_zh"])
                ref = pypinyin_syllables(o["example_zh"])
            except ValueError as e:
                errors += 1
                print(f"ALIGN-FAIL {o['id']}: {e}")
                continue
            if len(ref) != len([c for c in o["example_zh"] if pu._HANZI.match(c)]):
                errors += 1
                print(f"REF-COUNT {o['id']}: {len(ref)} ref syllables")
                continue
            for ch, mine, r in compare(o["example_zh"], my_syls, ref):
                rows.append({
                    "level": level, "id": o["id"], "char": ch,
                    "mine": mine, "pypinyin": r, "zh": o["example_zh"],
                })
    out = ROOT / "data/content/pinyin_audit.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["level", "id", "char", "mine", "pypinyin", "zh"])
        w.writeheader()
        w.writerows(rows)
    by_char = {}
    for r in rows:
        by_char[r["char"]] = by_char.get(r["char"], 0) + 1
    print(f"checked {checked} lines, {errors} alignment errors, "
          f"{len(rows)} polyphone mismatches -> {out}")
    for ch in sorted(by_char, key=by_char.get, reverse=True):
        print(f"  {ch} x{by_char[ch]}")


if __name__ == "__main__":
    main()
